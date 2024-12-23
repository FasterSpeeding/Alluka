# -*- coding: utf-8 -*-
# BSD 3-Clause License
#
# Copyright (c) 2020-2024, Faster Speeding
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from __future__ import annotations

__all__: list[str] = ["Manager"]

import itertools
import json
import logging
import pathlib
import tomllib
import typing
import weakref
from collections import abc as collections

from .. import _types  # pyright: ignore[reportPrivateUsage]
from .. import _visitor
from .. import abc
from . import _config  # pyright: ignore[reportPrivateUsage]
from . import _index

if typing.TYPE_CHECKING:
    from typing import Self


_LOGGER = logging.getLogger("alluka.managed")

_DictKeyT = str | int | float | bool | None
_DictValueT = collections.Mapping[_DictKeyT, "_DictValueT"] | collections.Sequence["_DictValueT"] | _DictKeyT
_PARSERS: dict[str, collections.Callable[[typing.BinaryIO], collections.Mapping[_DictKeyT, _DictValueT]]] = {
    "json": json.load,
    "toml": tomllib.load,
}


class Manager:
    """A type dependency lifetime manager implementation.

    This class manages creating and destroying type dependencies.
    """

    __slots__ = ("_client", "_is_loaded", "_load_configs", "_load_types", "_processed_callbacks")

    def __init__(self, client: abc.Client, /) -> None:
        """Create a manager.

        Parameters
        ----------
        client
            The alluka client to bind this to.
        """
        self._client = client.set_type_dependency(Manager, self)
        self._is_loaded = False
        self._load_configs: list[_config.PluginConfig] = []
        self._load_types: dict[type[typing.Any], _config.TypeConfig[typing.Any]] = {}
        self._processed_callbacks: weakref.WeakSet[collections.Callable[..., typing.Any]] = weakref.WeakSet()

    def load_config(self, config: pathlib.Path | _config.ConfigFile, /) -> Self:
        """Load plugin and dependency configuration into this manager.

        Parameters
        ----------
        config
            Either the parsed configuration or a path to a file to parsed.

            Only paths to JSON and TOML (3.10+) files are supported.

        Raises
        ------
        RuntimeError
            If the path passed is an unsupported file type or does not match
            the expected structure.
        TypeError
            If the configuration passed does not match the expected structure.
        KeyError
            If the configuration passed does not match the expected structure.
        """
        if isinstance(config, pathlib.Path):
            extension = config.name.rsplit(".", 1)[-1].lower()
            parser = _PARSERS.get(extension)
            if not parser:
                raise RuntimeError(f"Unsupported file type {extension!r}")

            with config.open("rb") as file:
                raw_config = parser(file)

            if not isinstance(raw_config, dict):
                raise RuntimeError(f"Unexpected top level type found in `{config!s}`, expected a dictionary")

            config = _config.ConfigFile.parse(raw_config)
            return self.load_config(config)

        load_types = set(config.load_types)
        for sub_config in config.plugins:
            load_types.update(sub_config.load_types)
            for config_type in sub_config.config_types():
                self._client.set_type_dependency(config_type, sub_config)

        mimo: set[type[typing.Any]] = set()
        for type_info in itertools.chain.from_iterable(
            self._to_resolvers(type_id, mimo=mimo) for type_id in iter(load_types)
        ):
            self._load_types[type_info.dep_type] = type_info

        return self

    def _to_resolvers(
        self, type_id: str | type[typing.Any], /, *, mimo: set[type[typing.Any]] | None = None
    ) -> collections.Iterator[_config.TypeConfig[typing.Any]]:
        if mimo is None:
            mimo = set()

        if isinstance(type_id, str):
            type_config = _index.GLOBAL_INDEX.get_type_by_name(type_id)

        else:
            type_config = _index.GLOBAL_INDEX.get_type(type_id)

        for dep in type_config.dependencies:
            if dep in mimo:
                continue

            mimo.add(dep)
            yield from self._to_resolvers(dep, mimo=mimo)

        yield type_config

    def load_deps(self) -> None:
        """Initialise the configured dependencies.

        !!! note
            This will skip over any dependencies which can only be created
            asynchronously.

        Raises
        ------
        RuntimeError
            If the dependencies are already loaded.
        """
        if self._is_loaded:
            raise RuntimeError("Dependencies already loaded")

        for type_info in self._load_types.values():
            if type_info.create:
                value = self._client.call_with_di(type_info.create)
                self._client.set_type_dependency(type_info.dep_type, value)

            else:
                _LOGGER.warning(
                    "Type dependency %r skipped as it can only be created in an async context", type_info.name
                )

    async def load_deps_async(self) -> None:  # noqa: ASYNC910
        """Initialise the configured dependencies asynchronously.

        Raises
        ------
        RuntimeError
            If a dependencies are already loaded.
        """
        if self._is_loaded:
            raise RuntimeError("Dependencies already loaded")

        for type_info in self._load_types.values():
            callback = type_info.async_create or type_info.create
            assert callback
            value = await self._client.call_with_async_di(callback)
            self._client.set_type_dependency(type_info.dep_type, value)

    def _iter_unload(self) -> collections.Iterator[tuple[_config.TypeConfig[typing.Any], typing.Any]]:
        if not self._is_loaded:
            raise RuntimeError("Dependencies not loaded")

        self._is_loaded = False
        for type_info in self._load_types.values():
            try:
                value = self._client.get_type_dependency(type_info.dep_type)

            except KeyError:
                pass

            else:
                self._client.remove_type_dependency(type_info.dep_type)
                yield (type_info, value)

    def unload_deps(self) -> None:
        """Unload the configured dependencies.

        !!! warning
            If you have any dependencies which were loaded asynchronously,
            you probably want
            [Manager.unload_deps_async][alluka.managed.Manager.unload_deps_async].

        Raises
        ------
        RuntimeError
            If the dependencies aren't loaded.
        """
        for type_info, value in self._iter_unload():
            if type_info.cleanup:
                type_info.cleanup(value)

            elif type_info.async_cleanup:
                _LOGGER.warning(
                    "Dependency %r might have not been cleaned up properly;"
                    "cannot run asynchronous cleanup function in a synchronous runtime",
                    type_info.dep_type,
                )

    async def unload_deps_async(self) -> None:  # noqa: ASYNC910
        """Unload the configured dependencies asynchronously.

        Raises
        ------
        RuntimeError
            If the dependencies aren't loaded.
        """
        for type_info, value in self._iter_unload():
            if type_info.async_cleanup:
                await type_info.async_cleanup(value)

            elif type_info.cleanup:
                type_info.cleanup(value)

    def pre_process_function(self, callback: collections.Callable[..., typing.Any], /) -> Self:
        """Register the required type dependencies found in a callback's signature.

        Parameters
        ----------
        callback
            The callback to register the required type dependencies for.
        """
        types: list[str] = []
        descriptors = _visitor.Callback(callback).accept(_visitor.ParameterVisitor())
        _index.GLOBAL_INDEX.set_descriptors(callback, descriptors)
        for param in descriptors.values():
            if param[0] is _types.InjectedTypes.CALLBACK:
                self.pre_process_function(param[1].callback)
                continue

            dep_info = param[1]
            # For this initial implementation only required arguments with no
            # union are supported.
            if dep_info.default is _types.UNDEFINED or len(dep_info.types) != 1:
                continue

            try:
                self._client.get_type_dependency(dep_info.types[0])

            except KeyError:
                continue

            try:
                type_info = _index.GLOBAL_INDEX.get_type(dep_info.types[0])

            except KeyError:
                # TODO: raise or mark as missing?
                pass

            else:
                types.append(type_info.name)

        self._processed_callbacks.add(callback)
        mimo: set[type[typing.Any]] = set()
        for type_info in itertools.chain.from_iterable(self._to_resolvers(type_id, mimo=mimo) for type_id in types):
            self._load_types[type_info.dep_type] = type_info

        return self

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

import itertools
import json
import logging
import pathlib
import typing
import weakref
from collections import abc as collections

from .. import _types
from .. import _visitor
from .. import abc
from . import _config
from . import _index

if typing.TYPE_CHECKING:
    from typing_extensions import Self


_DictKeyT = typing.Union[str, int, float, bool, None]
_DictValueT = typing.Union[
    collections.Mapping[_DictKeyT, "_DictValueT"], collections.Sequence["_DictValueT"], _DictKeyT
]
_LOGGER = logging.getLogger("alluka.managed")
_PARSERS: dict[str, collections.Callable[[typing.BinaryIO], collections.Mapping[_DictKeyT, _DictValueT]]] = {
    "json": json.load
}
_T = typing.TypeVar("_T")


try:
    import tomllib  # pyright: ignore[reportMissingTypeStubs]

except ModuleNotFoundError:
    pass

else:
    _PARSERS["toml"] = tomllib.load  # type: ignore


class Manager:
    __slots__ = ("_callback_types", "_client", "_loaded", "_processed_callbacks")

    def __init__(self, client: abc.Client, /) -> None:
        self._callback_types: set[str] = set()
        self._client = client
        self._loaded: typing.Optional[list[_index.TypeConfig[typing.Any]]] = None
        self._processed_callbacks: weakref.WeakSet[collections.Callable[..., typing.Any]] = weakref.WeakSet()

    def load_config(self, path: pathlib.Path, /) -> Self:
        extension = path.name.rsplit(".", 1)[-1].lower()
        parser = _PARSERS.get(extension)
        if not parser:
            raise RuntimeError(f"Unsupported file type {extension!r}")

        with path.open("rb") as file:
            raw_config = parser(file)

        if not isinstance(raw_config, dict):
            raise RuntimeError(f"Unexpected top level type found in `{path!s}`, expected a dictionary")

        config = _index.GLOBAL_INDEX.parse_config(raw_config)
        for sub_config in config.configs:
            for config_type in sub_config.config_types():
                self._client.set_type_dependency(config_type, sub_config)

        return self

    def _to_resolvers(
        self, type_id: typing.Union[str, type[typing.Any]], /, *, mimo: typing.Optional[set[type[typing.Any]]] = None
    ) -> collections.Iterator[_index.TypeConfig[typing.Any]]:
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

    def _calculate_loaders(self) -> list[_index.TypeConfig[typing.Any]]:
        if self._loaded is not None:
            raise RuntimeError("Dependencies already loaded")

        ids_to_load = self._client.get_type_dependency(_config.TypeLoader, default=None)
        if not ids_to_load:
            return []

        self._loaded = list(
            itertools.chain.from_iterable(
                self._to_resolvers(type_id) for type_id in itertools.chain(ids_to_load.load_types, self._callback_types)
            )
        )
        return self._loaded

    def load_deps(self) -> None:
        to_load = self._calculate_loaders()

        for type_info in to_load:
            if not type_info.create:
                raise RuntimeError(f"Type dependency {type_info.name!r} can only be created in an async context")

            value = self._client.call_with_di(type_info.create)
            self._client.set_type_dependency(type_info.dep_type, value)

    async def load_deps_async(self) -> None:
        to_load = self._calculate_loaders()

        for type_info in to_load:
            callback = type_info.async_create or type_info.create
            assert callback
            value = await self._client.call_with_async_di(callback)
            self._client.set_type_dependency(type_info.dep_type, value)

    def _iter_unload(self) -> collections.Iterator[tuple[_index.TypeConfig[typing.Any], typing.Any]]:
        if self._loaded is None:
            raise RuntimeError("Dependencies not loaded")

        for type_info in self._loaded:
            try:
                value = self._client.get_type_dependency(type_info.dep_type)

            except KeyError:
                pass

            else:
                self._client.remove_type_dependency(type_info.dep_type)
                yield (type_info, value)

    def unload_deps(self) -> None:
        for type_info, value in self._iter_unload():
            if type_info.cleanup:
                type_info.cleanup(value)

            elif type_info.async_cleanup:
                _LOGGER.warning(
                    "Dependency %r might have not been cleaned up properly;"
                    "cannot run asynchronous cleanup function in a synchronous runtime",
                    type_info.dep_type,
                )

    async def unload_deps_async(self) -> None:
        for type_info, value in self._iter_unload():
            if type_info.async_cleanup:
                await type_info.async_cleanup(value)

            elif type_info.cleanup:
                type_info.cleanup(value)

    def pre_process_function(self, callback: collections.Callable[..., typing.Any], /) -> Self:
        types: list[str] = []
        for param in _visitor.Callback(callback).accept(_visitor.ParameterVisitor()).values():
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
        self._callback_types.update(types)
        return self

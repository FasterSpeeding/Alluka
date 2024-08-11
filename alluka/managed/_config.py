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

__all__: list[str] = ["ConfigFile", "PluginConfig", "TypeConfig"]

import abc
import typing
from collections import abc as collections

if typing.TYPE_CHECKING:
    from typing_extensions import Self

    _CoroT = collections.Coroutine[typing.Any, typing.Any, "_T"]


_T = typing.TypeVar("_T")
_DictKeyT = typing.Union[str, int, float, bool, None]
_DictValueT = typing.Union[
    collections.Mapping[_DictKeyT, "_DictValueT"], collections.Sequence["_DictValueT"], _DictKeyT
]


class TypeConfig(typing.Generic[_T]):
    """Base class used for to declare the creation logic used by Alluka's manager for type dependencies.

    Libraries should use entry points in the group "alluka.managed" to register
    these.
    """

    __slots__ = ("_async_cleanup", "_async_create", "_cleanup", "_create", "_dep_type", "_dependencies", "_name")

    @typing.overload
    def __init__(
        self,
        dep_type: type[_T],
        name: str,
        /,
        *,
        async_cleanup: typing.Optional[collections.Callable[[_T], _CoroT[None]]] = None,
        async_create: collections.Callable[..., _CoroT[_T]],
        cleanup: typing.Optional[collections.Callable[[_T], None]] = None,
        create: typing.Optional[collections.Callable[..., _T]] = None,
        dependencies: collections.Sequence[type[typing.Any]] = (),
    ) -> None: ...

    @typing.overload
    def __init__(
        self,
        dep_type: type[_T],
        name: str,
        /,
        *,
        async_cleanup: typing.Optional[collections.Callable[[_T], _CoroT[None]]] = None,
        async_create: typing.Optional[collections.Callable[..., _CoroT[_T]]] = None,
        cleanup: typing.Optional[collections.Callable[[_T], None]] = None,
        create: collections.Callable[..., _T],
        dependencies: collections.Sequence[type[typing.Any]] = (),
    ) -> None: ...

    def __init__(
        self,
        dep_type: type[_T],
        name: str,
        /,
        *,
        async_cleanup: typing.Optional[collections.Callable[[_T], _CoroT[None]]] = None,
        async_create: typing.Optional[collections.Callable[..., _CoroT[_T]]] = None,
        cleanup: typing.Optional[collections.Callable[[_T], None]] = None,
        create: typing.Optional[collections.Callable[..., _T]] = None,
        dependencies: collections.Sequence[type[typing.Any]] = (),
    ) -> None:
        """Initialise a type config.

        !!! note
            Either `create` or `async_create` must be passed, but if only
            `async_create` is passed then this will fail to be created in
            a synchronous runtime.

        Parameters
        ----------
        dep_type
            Type of the dep this should be registered for.
        name
            Name used to identify this type dependency in configuration files.
        async_cleanup
            Callback used to use to destroy the dependency in an async runtime.
        async_create
            Callback used to use to create the dependency in an async runtime.
        cleanup
            Callback used to use to destroy the dependency in a sync runtime.
        create
            Callback used to use to create the dependency in a sync runtime.
        dependencies
            Sequence of type dependencies that are required to create this dependency.

        Raises
        ------
        TypeError
            If neither `create` nor `async_create` is passed.
        """
        if not create and not async_create:
            raise TypeError("Either `create` or `async_create` must be passed")

        self._async_cleanup = async_cleanup
        self._async_create = async_create
        self._cleanup = cleanup
        self._create = create
        self._dep_type = dep_type
        self._dependencies = dependencies
        self._name = name

    @property
    def async_cleanup(self) -> typing.Optional[collections.Callable[[_T], _CoroT[None]]]:
        """Callback used to use to cleanup the dependency in an async runtime."""
        return self._async_cleanup

    @property
    def async_create(self) -> typing.Optional[collections.Callable[..., _CoroT[_T]]]:
        """Callback used to use to create the dependency in an async runtime."""
        return self._async_create

    @property
    def cleanup(self) -> typing.Optional[collections.Callable[[_T], None]]:
        """Callback used to use to cleanup the dependency in a sync runtime."""
        return self._cleanup

    @property
    def create(self) -> typing.Optional[collections.Callable[..., _T]]:
        """Callback used to use to create the dependency in an async runtime."""
        return self._create

    @property
    def dep_type(self) -> type[_T]:
        """The type created values should be registered as a type dependency for."""
        return self._dep_type

    @property
    def dependencies(self) -> collections.Sequence[type[typing.Any]]:
        """Sequence of type dependencies that are required to create this dependency."""
        return self._dependencies

    @property
    def name(self) -> str:
        """Name used to identify this type dependency in configuration files."""
        return self._name


class PluginConfig(abc.ABC):
    """Base class used for configuring plugins loaded via Alluka's manager.

    Libraries should use entry points in the group "alluka.managed" to register
    these.
    """

    __slots__ = ()

    @classmethod
    def config_types(cls) -> collections.Sequence[type[PluginConfig]]:
        """The types to use when registering this configuration as a type dependency."""
        return [cls]

    @classmethod
    @abc.abstractmethod
    def config_id(cls) -> str:
        """ID used to identify the plugin configuration."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def from_mapping(cls, data: collections.Mapping[_DictKeyT, _DictValueT], /) -> Self:
        """Create this configuration object from a dictionary."""
        raise NotImplementedError

    @property
    def load_types(self) -> collections.Sequence[str]:
        """Sequence of string types to load when this config is present."""
        return []


def _parse_config(key: _DictKeyT, config: _DictValueT, /) -> PluginConfig:
    if not isinstance(key, str):
        raise TypeError(f"Expected string keys in `'plugins'`, found {key!r}")

    if not isinstance(config, collections.Mapping):
        raise TypeError(f"Expected a dictionary at `'plugins'.{key!r}`, found {type(config)}")

    from . import _index

    return _index.GLOBAL_INDEX.get_config(key).from_mapping(config)


class ConfigFile(typing.NamedTuple):
    """Represents the configuration file used to configure Alluka's Manager."""

    plugins: collections.Sequence[PluginConfig]
    """Sequence of the loaded plugin configurations."""

    load_types: collections.Sequence[str]
    """Sequence of the IDs of type dependencies to load alongside configured plugin types."""

    @classmethod
    def parse(cls, data: collections.Mapping[_DictKeyT, _DictValueT], /) -> Self:
        """Parse [ConfigFile][alluka.managed.ConfigFile] from a JSON style dictionary.

        Parameters
        ----------
        data
            The mapping of data to parse.

        Returns
        -------
        ConfigFile
            The parsed configuration.
        """
        raw_plugins = data["plugins"]
        if not isinstance(raw_plugins, collections.Mapping):
            raise TypeError(f"Expected a dictionary at `'plugins'`, found {type(raw_plugins)}")

        try:
            raw_load_types = data["load_types"]

        except KeyError:
            load_types: list[str] = []

        else:
            if not isinstance(raw_load_types, collections.Sequence):
                raise TypeError(f"Expected a list of strings at `'load_types'`, found {type(raw_load_types)}")

            load_types = []
            for index, type_id in enumerate(raw_load_types):
                if not isinstance(type_id, str):
                    raise TypeError(f"Expected a string at `'load_types'.{index}`, found {type(type_id)}")

                load_types.append(type_id)

        return cls(plugins=[_parse_config(*args) for args in raw_plugins.items()], load_types=load_types)

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

__all__: list[str] = ["Index", "TypeConfig"]

import dataclasses
import importlib.metadata
import logging
import sys
import threading
import typing
import weakref
from collections import abc as collections

if typing.TYPE_CHECKING:
    import types

    from .. import _types  # pyright: ignore[reportPrivateUsage]
    from .. import abc as alluka
    from . import _config  # pyright: ignore[reportPrivateUsage]


_LOGGER = logging.getLogger("alluka.managed")

_T = typing.TypeVar("_T")
_CoroT = collections.Coroutine[typing.Any, typing.Any, _T]
_DictKeyT = typing.Union[str, int, float, bool, None]
_DictValueT = typing.Union[
    collections.Mapping[_DictKeyT, "_DictValueT"], collections.Sequence["_DictValueT"], _DictKeyT
]


@dataclasses.dataclass(frozen=True)
class TypeConfig(typing.Generic[_T]):
    """Represents the procedures and metadata for creating and destroying a type dependency."""

    __slots__ = (
        "async_cleanup", "async_create", "cleanup", "create", "dep_type", "dependencies", "name"
    )

    async_cleanup: typing.Optional[collections.Callable[[_T], _CoroT[None]]]
    """Callback used to use to cleanup the dependency in an async runtime."""

    async_create: typing.Optional[collections.Callable[..., _CoroT[_T]]]
    """Callback used to use to create the dependency in an async runtime."""

    cleanup: typing.Optional[collections.Callable[[_T], None]]
    """Callback used to use to cleanup the dependency in a sync runtime."""

    create: typing.Optional[collections.Callable[..., _T]]
    """Callback used to use to create the dependency in an async runtime."""

    dep_type: type[_T]
    """The type created values should be registered as a type dependency for."""

    dependencies: collections.Sequence[type[typing.Any]]
    """Sequence of type dependencies that are required to create this dependency."""

    name: str
    """Name used to identify this type dependency in configuration files."""


_ENTRY_POINT_GROUP_NAME = "alluka.plugins"


class Index:
    """Index used to internally track the register global custom configuration.

    This is used by the manager to parse plugin configuration and initialise types.
    """

    __slots__ = ("_descriptors", "_config_index", "_lock", "_metadata_scanned", "_name_index", "_type_index")

    def __init__(self) -> None:
        """Initialise an Index."""
        # TODO: this forces objects to have a __weakref__ attribute,
        # and also hashability (so hash and eq or neither), do we want to
        # keep with this behaviour or document it?
        self._descriptors: weakref.WeakKeyDictionary[
            alluka.CallbackSig[typing.Any], dict[str, _types.InjectedTuple]
        ] = weakref.WeakKeyDictionary()
        self._config_index: dict[str, type[_config.PluginConfig]] = {}
        self._lock = threading.Lock()
        self._metadata_scanned = False
        self._name_index: dict[str, TypeConfig[typing.Any]] = {}
        self._type_index: dict[type[typing.Any], TypeConfig[typing.Any]] = {}
        self._scan_libraries()

    def __enter__(self) -> None:
        self._lock.__enter__()

    def __exit__(
        self,
        exc_cls: type[BaseException] | None,
        exc: BaseException | None,
        traceback_value: types.TracebackType | None,
    ) -> None:
        return self._lock.__exit__(exc_cls, exc, traceback_value)

    def register_config(self, config_cls: type[_config.PluginConfig], /) -> None:
        """Register a plugin configuration class.

        !!! warning
            Libraries should register entry-points under the `"alluka.plugins"` group
            to register custom configuration classes.

        Parameters
        ----------
        config_cls
            The plugin configuration class to register.

        Raises
        ------
        RuntimeError
            If the configuration class' ID is already registered.
        """
        # TODO: Note that libraries should use package metadata!
        config_id = config_cls.config_id()
        if config_id in self._config_index:
            raise RuntimeError(f"Config ID {config_id!r} already registered")

        self._config_index[config_id] = config_cls

    @typing.overload
    def register_type(
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
    def register_type(
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

    def register_type(
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
        """Register the procedures for creating and destroying a type dependency.

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
            raise TypeError("Either create or async_create has to be passed")

        config = TypeConfig(
            async_cleanup=async_cleanup,
            async_create=async_create,
            cleanup=cleanup,
            create=create,
            dep_type=dep_type,
            dependencies=dependencies,
            name=name,
        )

        if config.dep_type in self._type_index:
            raise RuntimeError(f"Dependency type `{config.dep_type}` already registered")

        if config.name in self._name_index:
            raise RuntimeError(f"Dependency name {config.name!r} already registered")

        self._type_index[config.dep_type] = self._name_index[config.name] = config

    def set_descriptors(
        self, callback: alluka.CallbackSig[typing.Any], descriptors: dict[str, _types.InjectedTuple], /
    ) -> None:
        """Cache the parsed dependency injection descriptors for a callback.

        Parameters
        ----------
        callback
            The callback to cache the injection descriptors for.
        descriptors
            The descriptors to cache.
        """
        self._descriptors[callback] = descriptors

    def get_descriptors(
        self, callback: alluka.CallbackSig[typing.Any], /
    ) -> typing.Optional[dict[str, _types.InjectedTuple]]:
        """Get the dependency injection descriptors cached for a callback.

        Parameters
        ----------

        Returns
        -------
        dict[str, alluka._types.InjectedTuple] | None
            A dictionary of parameter names to injection metadata.

            This will be [None][] if the descriptors are not cached for
            the callback.
        """
        return self._descriptors.get(callback)

    def get_type(self, dep_type: type[_T], /) -> TypeConfig[_T]:
        """Get the configuration for a type dependency.

        Parameters
        ----------
        dep_type
            Type of the dependency to get the configuration for.

        Returns
        -------
        TypeConfig[_T]
            Configuration which represents the procedures and metadata
            for creating and destroying the type dependency.
        """
        try:
            return self._type_index[dep_type]

        except KeyError:
            raise RuntimeError(f"Unknown dependency type {dep_type}") from None

    def get_type_by_name(self, name: str, /) -> TypeConfig[typing.Any]:
        """Get the configuration for a type dependency by its configured name.

        Parameters
        ----------
        name
            Name of the type dependency to get the configuration for.

        Returns
        -------
        TypeConfig[_T]
            Configuration which represents the procedures and metadata
            for creating and destroying the type dependency.
        """
        try:
            return self._name_index[name]

        except KeyError:
            raise RuntimeError(f"Unknown dependency ID {name!r}") from None

    def get_config(self, config_id: str, /) -> type[_config.PluginConfig]:
        """Get the custom plugin configuration class for a config ID.

        Parameters
        ----------
        config_id
            ID used to identify the plugin configuration.

        Returns
        -------
        type[alluka.managed.PluginConfig]
            The custom plugin configuration class.
        """
        try:
            return self._config_index[config_id]

        except KeyError:
            raise RuntimeError(f"Unknown config ID {config_id!r}") from None

    def _scan_libraries(self) -> None:
        """Load config classes from installed libraries based on their entry points."""
        if self._metadata_scanned:
            return

        self._metadata_scanned = True
        if sys.version_info >= (3, 10):
            entry_points = importlib.metadata.entry_points(group=_ENTRY_POINT_GROUP_NAME)

        else:
            entry_points = importlib.metadata.entry_points()[_ENTRY_POINT_GROUP_NAME]

        for entry_point in entry_points:
            value = entry_point.load()
            if isinstance(value, type) and issubclass(value, _config.PluginConfig):
                self.register_config(value)

            else:
                _LOGGER.warn(
                    "Unexpected value found at %, expected a PluginConfig class but found %r. "
                    "An alluka entry point is misconfigured.",
                    entry_point.value,
                    value,
                )


GLOBAL_INDEX = Index()
"""Global instance of [Index][]."""

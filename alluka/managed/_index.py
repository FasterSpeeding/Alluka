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

__all__: list[str] = ["Index"]

import importlib.metadata
import logging
import typing
import weakref
from collections import abc as collections

from . import _config  # pyright: ignore[reportPrivateUsage]

if typing.TYPE_CHECKING:

    from .. import _types  # pyright: ignore[reportPrivateUsage]
    from .. import abc as alluka


_LOGGER = logging.getLogger("alluka.managed")

_T = typing.TypeVar("_T")
_DictKeyT = str | int | float | bool | None
_DictValueT = collections.Mapping[_DictKeyT, "_DictValueT"] | collections.Sequence["_DictValueT"] | _DictKeyT


_ENTRY_POINT_GROUP_NAME = "alluka.managed"


class Index:
    """Index used to internally track the register global custom configuration.

    This is used by the manager to parse plugin configuration and initialise types.
    """

    __slots__ = ("_descriptors", "_config_index", "_name_index", "_type_index")

    def __init__(self) -> None:
        """Initialise an Index."""
        # TODO: this forces objects to have a __weakref__ attribute,
        # and also hashability (so hash and eq or neither), do we want to
        # keep with this behaviour or document it?
        self._descriptors: weakref.WeakKeyDictionary[
            alluka.CallbackSig[typing.Any], dict[str, _types.InjectedTuple]
        ] = weakref.WeakKeyDictionary()
        self._config_index: dict[str, type[_config.PluginConfig]] = {}
        self._name_index: dict[str, _config.TypeConfig[typing.Any]] = {}
        self._type_index: dict[type[typing.Any], _config.TypeConfig[typing.Any]] = {}
        self._scan_libraries()

    def register_config(self, config_cls: type[_config.PluginConfig], /) -> None:
        """Register a plugin configuration class.

        !!! warning
            Libraries should register custom configuration classes using package
            entry-points tagged with the `"alluka.managed"` group.

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

    def register_type(self, type_info: _config.TypeConfig[typing.Any], /) -> None:
        """Register the procedures for creating and destroying a type dependency.

        !!! warning
            Libraries should register custom type procedure objects using package
            entry-points tagged with the `"alluka.managed"` group.

        Parameters
        ----------
        type_info
            The type dependency's runtime procedures.
        """
        if type_info.dep_type in self._type_index:
            raise RuntimeError(f"Dependency type `{type_info.dep_type}` already registered")

        if type_info.name in self._name_index:
            raise RuntimeError(f"Dependency name {type_info.name!r} already registered")

        self._type_index[type_info.dep_type] = self._name_index[type_info.name] = type_info

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

    def get_descriptors(self, callback: alluka.CallbackSig[typing.Any], /) -> dict[str, _types.InjectedTuple] | None:
        """Get the dependency injection descriptors cached for a callback.

        Parameters
        ----------
        callback
            The callback to get the descriptors for.

        Returns
        -------
        dict[str, alluka._types.InjectedTuple] | None
            A dictionary of parameter names to injection metadata.

            This will be [None][] if the descriptors are not cached for
            the callback.
        """
        return self._descriptors.get(callback)

    def get_type(self, dep_type: type[_T], /) -> _config.TypeConfig[_T]:
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

    def get_type_by_name(self, name: str, /) -> _config.TypeConfig[typing.Any]:
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
        for entry_point in importlib.metadata.entry_points(group=_ENTRY_POINT_GROUP_NAME):
            value = entry_point.load()
            if not isinstance(value, type):
                pass

            elif issubclass(value, _config.PluginConfig):
                _LOGGER.debug("Registered PluginConfig from %r", entry_point)
                self.register_config(value)
                continue

            elif issubclass(value, _config.TypeConfig):
                _LOGGER.debug("Registering TypeConfig from %r", entry_point)
                continue

            _LOGGER.warning(
                "Unexpected value found at %, expected a PluginConfig class but found %r. "
                "An alluka entry point is misconfigured.",
                entry_point.value,
                value,
            )


GLOBAL_INDEX = Index()
"""Global instance of [Index][]."""

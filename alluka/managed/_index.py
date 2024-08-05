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

import threading
import typing
import weakref
from collections import abc as collections

from .. import _visitor
from . import _config

if typing.TYPE_CHECKING:
    import types

    from typing_extensions import Self

    from .. import _types
    from .. import abc as alluka


_T = typing.TypeVar("_T")
_CoroT = collections.Coroutine[typing.Any, typing.Any, _T]
_DictKeyT = typing.Union[str, int, float, bool, None]
_DictValueT = typing.Union[
    collections.Mapping[_DictKeyT, "_DictValueT"], collections.Sequence["_DictValueT"], _DictKeyT
]


class TypeConfig(typing.NamedTuple, typing.Generic[_T]):
    async_cleanup: typing.Optional[collections.Callable[[_T], _CoroT[None]]]
    async_create: typing.Optional[collections.Callable[..., _CoroT[_T]]]
    cleanup: typing.Optional[collections.Callable[[_T], None]]
    create: typing.Optional[collections.Callable[..., _T]]
    dep_type: type[_T]
    dependencies: collections.Sequence[type[typing.Any]]
    name: str


class Index:
    __slots__ = ("_descriptors", "_config_index", "_lock", "_name_index", "_type_index")

    def __init__(self) -> None:
        # TODO: this forces objects to have a __weakref__ attribute,
        # and also hashability (so hash and eq or neither), do we want to
        # keep with this behaviour or document it?
        self._descriptors: weakref.WeakKeyDictionary[
            alluka.CallbackSig[typing.Any], dict[str, _types.InjectedTuple]
        ] = weakref.WeakKeyDictionary()
        self._config_index: dict[str, type[_config.BaseConfig]] = {}
        self._lock = threading.Lock()
        self._name_index: dict[str, TypeConfig[typing.Any]] = {}
        self._type_index: dict[type[typing.Any], TypeConfig[typing.Any]] = {}

    def __enter__(self) -> None:
        self._lock.__enter__()

    def __exit__(
        self,
        exc_cls: type[BaseException] | None,
        exc: BaseException | None,
        traceback_value: types.TracebackType | None,
    ) -> None:
        return self._lock.__exit__(exc_cls, exc, traceback_value)

    def register_config(self, config_cls: type[_config.BaseConfig], /) -> Self:
        config_id = config_cls.config_id()
        if config_id in self._config_index:
            raise RuntimeError(f"Config ID {config_id!r} already registered")

        self._config_index[config_id] = config_cls
        return self

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
    ) -> Self: ...

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
    ) -> Self: ...

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
    ) -> Self:
        if not create and not async_create:
            raise RuntimeError("Either create or async_create has to be passed")

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
        return self

    def set_descriptors(
        self, callback: alluka.CallbackSig[typing.Any], descriptors: dict[str, _types.InjectedTuple], /
    ) -> Self:
        self._descriptors[callback] = _visitor.Callback(callback).accept(_visitor.ParameterVisitor())
        return self

    def get_descriptors(
        self, callback: alluka.CallbackSig[typing.Any], /
    ) -> typing.Optional[dict[str, _types.InjectedTuple]]:
        return self._descriptors.get(callback)

    def get_type(self, dep_type: type[_T], /) -> TypeConfig[_T]:
        try:
            return self._type_index[dep_type]

        except KeyError:
            raise RuntimeError(f"Unknown dependency type {dep_type}") from None

    def get_type_by_name(self, name: str, /) -> TypeConfig[typing.Any]:
        try:
            return self._name_index[name]

        except KeyError:
            raise RuntimeError(f"Unknown dependency ID {name!r}") from None

    def _parse_config(self, key: _DictKeyT, config: _DictValueT, /) -> _config.BaseConfig:
        if not isinstance(key, str):
            raise RuntimeError(f"Expected string keys in `'configs'`, found {key!r}")

        if not isinstance(config, collections.Mapping):
            raise RuntimeError(f"Expected a dictionary at `'configs'.{key!r}`, found {type(config)}")

        if config_type := self._config_index.get(key):
            return config_type.from_mapping(config)

        raise RuntimeError(f"Unknown config ID `{key!r}`")

    def parse_config(self, data: collections.Mapping[_DictKeyT, _DictValueT], /) -> _config.ConfigFile:
        raw_configs = data["configs"]
        if not isinstance(raw_configs, collections.Mapping):
            raise RuntimeError(f"Expected a dictionaries at `'configs'`, found {type(raw_configs)}")

        return _config.ConfigFile(configs=[self._parse_config(*args) for args in raw_configs.items()])


GLOBAL_INDEX = Index().register_config(_config.TypeLoader)

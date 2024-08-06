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

import abc
import typing
from collections import abc as collections

if typing.TYPE_CHECKING:
    from typing_extensions import Self

    from .. import abc as alluka


_CoroT = collections.Coroutine[typing.Any, typing.Any, None]
_DictKeyT = typing.Union[str, int, float, bool, None]
_DictValueT = typing.Union[
    collections.Mapping[_DictKeyT, "_DictValueT"], collections.Sequence["_DictValueT"], _DictKeyT
]


class BaseConfig(abc.ABC):
    __slots__ = ()

    @classmethod
    def config_types(cls) -> collections.Sequence[type[BaseConfig]]:
        return [cls]

    @classmethod
    @abc.abstractmethod
    def config_id(cls) -> str:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def from_mapping(cls, data: collections.Mapping[_DictKeyT, _DictValueT], /) -> Self:
        raise NotImplementedError

    @property
    def async_cleanup(self) -> typing.Optional[collections.Callable[[Self, alluka.Client], _CoroT]]: ...

    @property
    def async_create(self) -> typing.Optional[collections.Callable[[Self, alluka.Client], _CoroT]]: ...

    @property
    def cleanup(self) -> typing.Optional[collections.Callable[[Self, alluka.Client], None]]: ...

    @property
    def create(self) -> typing.Optional[collections.Callable[[Self, alluka.Client], None]]: ...


def _parse_config(key: _DictKeyT, config: _DictValueT, /) -> BaseConfig:
    if not isinstance(key, str):
        raise RuntimeError(f"Expected string keys in `'configs'`, found {key!r}")

    if not isinstance(config, collections.Mapping):
        raise RuntimeError(f"Expected a dictionary at `'configs'.{key!r}`, found {type(config)}")

    from . import _index

    return _index.GLOBAL_INDEX.get_config(key).from_mapping(config)


class ConfigFile(typing.NamedTuple):  # TODO: hide
    configs: collections.Sequence[BaseConfig]
    load_types: collections.Sequence[str]

    @classmethod
    def parse(cls, data: collections.Mapping[_DictKeyT, _DictValueT], /) -> Self:
        raw_configs = data["configs"]
        if not isinstance(raw_configs, collections.Mapping):
            raise RuntimeError(f"Expected a dictionaries at `'configs'`, found {type(raw_configs)}")

        try:
            raw_load_types = data["load_types"]

        except KeyError:
            load_types: list[str] = []

        else:
            if not isinstance(raw_load_types, collections.Sequence):
                raise RuntimeError(f"Expected a list of strings at `'load_types'`, found {type(raw_load_types)}")

            load_types = []
            for index, type_id in enumerate(raw_load_types):
                if not isinstance(type_id, str):
                    raise RuntimeError(f"Expected a string at `'load_types'.{index}`, found {type(type_id)}")

                load_types.append(type_id)

        return cls(configs=[_parse_config(*args) for args in raw_configs.items()], load_types=load_types)

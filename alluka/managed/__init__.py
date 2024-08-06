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

import typing
from collections import abc as collections

from . import _index
from ._config import BaseConfig as BaseConfig
from ._config import ConfigFile as ConfigFile
from ._manager import Manager as Manager

if typing.TYPE_CHECKING:
    _T = typing.TypeVar("_T")

    _CoroT = collections.Coroutine[typing.Any, typing.Any, _T]

    class _RegiserTypeSig(typing.Protocol):
        @typing.overload
        def __call__(
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
        def __call__(
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


_GLOBAL_INDEX = _index.GLOBAL_INDEX

register_config: collections.Callable[[type[BaseConfig]], None] = _GLOBAL_INDEX.register_config
register_type: _RegiserTypeSig = _GLOBAL_INDEX.register_type

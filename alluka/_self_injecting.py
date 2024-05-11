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

# pyright: reportDeprecated=none

from __future__ import annotations

__all__: list[str] = ["AsyncSelfInjecting", "SelfInjecting"]

import typing
import warnings
from collections import abc as collections

import typing_extensions

from . import abc as alluka

_CallbackSigT = typing.TypeVar("_CallbackSigT", bound=alluka.CallbackSig[typing.Any])
_SyncCallbackT = typing.TypeVar("_SyncCallbackT", bound=collections.Callable[..., typing.Any])
_T = typing.TypeVar("_T")
_CoroT = collections.Coroutine[typing.Any, typing.Any, _T]


with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    @typing_extensions.deprecated("Use Client.auto_inject_async")
    class AsyncSelfInjecting(alluka.AsyncSelfInjecting[_CallbackSigT]):
        """Deprecated class for marking async functions as self-injecting.

        !!! warning "deprecated"
            This is deprecated as of `v0.2.0`,
            Use [Client.auto_inject_async][alluka.abc.Client.auto_inject_async].
        """

        __slots__ = ("_callback", "_client")

        def __init__(self, client: alluka.Client, callback: _CallbackSigT, /) -> None:
            """Initialise a self injecting callback.

            Parameters
            ----------
            client
                The injection client to use to resolve dependencies.
            callback : alluka.abc.CallbackSig
                The callback to make self-injecting.

                This may be sync or async.

            Raises
            ------
            ValueError
                If `callback` has any injected arguments which can only be passed
                positionally.
            """
            self._callback = callback
            self._client = client

        @typing.overload
        async def __call__(
            self: AsyncSelfInjecting[collections.Callable[..., _CoroT[_T]]], *args: typing.Any, **kwargs: typing.Any
        ) -> _T: ...

        @typing.overload
        async def __call__(
            self: AsyncSelfInjecting[collections.Callable[..., _T]], *args: typing.Any, **kwargs: typing.Any
        ) -> _T: ...

        async def __call__(
            self: typing.Union[
                AsyncSelfInjecting[collections.Callable[..., _T]],
                AsyncSelfInjecting[collections.Callable[..., _CoroT[_T]]],
            ],
            *args: typing.Any,
            **kwargs: typing.Any,
        ) -> _T:
            # <<inherited docstring from alluka.abc.AsyncSelfInjecting>>.
            return await self._client.call_with_async_di(self._callback, *args, **kwargs)

        @property
        def callback(self) -> _CallbackSigT:
            # <<inherited docstring from alluka.abc.AsyncSelfInjecting>>.
            return self._callback

    @typing_extensions.deprecated("Use Client.inject_async")
    class SelfInjecting(alluka.SelfInjecting[_SyncCallbackT]):
        """Deprecated class for marking functions as self-injecting.

        !!! warning "deprecated"
            This is deprecated as of `v0.2.0`,
            Use [Client.auto_inject][alluka.abc.Client.auto_inject].
        """

        __slots__ = ("_callback", "_client")

        def __init__(self, client: alluka.Client, callback: _SyncCallbackT, /) -> None:
            """Initialise a sync self injecting callback.

            Parameters
            ----------
            client
                The injection client to use to resolve dependencies.
            callback : collections.abc.Callable
                The callback to make self-injecting.

            Raises
            ------
            ValueError
                If `callback` has any injected arguments which can only be passed
                positionally.
            """
            self._callback = callback
            self._client = client

        def __call__(self: SelfInjecting[collections.Callable[..., _T]], *args: typing.Any, **kwargs: typing.Any) -> _T:
            # <<inherited docstring from alluka.abc.SelfInjecting>>.
            return self._client.call_with_di(self._callback, *args, **kwargs)

        @property
        def callback(self) -> _SyncCallbackT:
            # <<inherited docstring from alluka.abc.SelfInjecting>>.
            return self._callback

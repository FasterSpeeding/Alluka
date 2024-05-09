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

import mock
import pytest

import alluka

if typing.TYPE_CHECKING:
    from collections import abc as collections

    from typing_extensions import Self

    _CallbackT = typing.TypeVar("_CallbackT", bound=collections.Callable[..., typing.Any])
    _DefaultT = typing.TypeVar("_DefaultT")
    _T = typing.TypeVar("_T")
    _DefaultT = typing.TypeVar("_DefaultT")

    _CoroT = collections.Coroutine[typing.Any, typing.Any, _T]


class MockClient(alluka.abc.Client):
    def make_context(self) -> alluka.abc.Context:
        raise NotImplementedError

    def as_async_self_injecting(
        self, callback: _CallbackT, /
    ) -> alluka.abc.AsyncSelfInjecting[_CallbackT]:  # pyright: ignore[reportDeprecated]
        raise NotImplementedError

    def as_self_injecting(
        self, callback: _CallbackT, /
    ) -> alluka.abc.SelfInjecting[_CallbackT]:  # pyright: ignore[reportDeprecated]
        raise NotImplementedError

    @typing.overload
    def call_with_ctx(
        self,
        ctx: alluka.abc.Context,
        callback: collections.Callable[..., _CoroT[typing.Any]],
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> typing.NoReturn: ...

    @typing.overload
    def call_with_ctx(
        self, ctx: alluka.abc.Context, callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any
    ) -> _T: ...

    def call_with_ctx(
        self, ctx: alluka.abc.Context, callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any
    ) -> _T:
        raise NotImplementedError

    async def call_with_ctx_async(
        self, ctx: alluka.abc.Context, callback: alluka.abc.CallbackSig[_T], *args: typing.Any, **kwargs: typing.Any
    ) -> _T:
        raise NotImplementedError

    def set_type_dependency(self, type_: type[_T], value: _T, /) -> Self:
        raise NotImplementedError

    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT = ...) -> typing.Union[_T, _DefaultT]:
        raise NotImplementedError

    def remove_type_dependency(self, type_: type[typing.Any], /) -> Self:
        raise NotImplementedError

    def set_callback_override(
        self, callback: alluka.abc.CallbackSig[_T], override: alluka.abc.CallbackSig[_T], /
    ) -> Self:
        raise NotImplementedError

    def get_callback_override(
        self, callback: alluka.abc.CallbackSig[_T], /
    ) -> typing.Optional[alluka.abc.CallbackSig[_T]]:
        raise NotImplementedError

    def remove_callback_override(self, callback: alluka.abc.CallbackSig[_T], /) -> Self:
        raise NotImplementedError


class TestClient:
    def test_auto_inject(self):
        client = MockClient()
        client.call_with_di = mock.Mock()
        mock_callback = mock.Mock()

        wrapped = client.auto_inject(mock_callback)

        result = wrapped(341, "123", hello="bye")

        client.call_with_di.assert_called_once_with(mock_callback, 341, "123", hello="bye")
        assert result is client.call_with_di.return_value

    @pytest.mark.anyio
    async def test_auto_inject_async(self):
        client = MockClient()
        client.call_with_async_di = mock.AsyncMock()
        mock_callback = mock.AsyncMock()

        wrapped = client.auto_inject_async(mock_callback)

        result = await wrapped("555", 12312, kill="the fuckers")

        client.call_with_async_di.assert_awaited_once_with(mock_callback, "555", 12312, kill="the fuckers")
        assert result is client.call_with_async_di.return_value

    def test_call_with_di(self):
        client = MockClient()
        client.make_context = mock.Mock()
        mock_callback = mock.Mock()

        result = client.call_with_di(mock_callback, 333, "lll", meep="boop")

        assert result is client.make_context.return_value.call_with_di.return_value
        client.make_context.assert_called_once_with()
        client.make_context.return_value.call_with_di.assert_called_once_with(mock_callback, 333, "lll", meep="boop")

    @pytest.mark.anyio
    async def test_call_with_async_di(self):
        client = MockClient()
        client.make_context = mock.Mock()
        client.make_context.return_value.call_with_async_di = mock.AsyncMock()
        mock_callback = mock.AsyncMock()

        result = await client.call_with_async_di(mock_callback, "777", 555, meep="3222")

        assert result is client.make_context.return_value.call_with_async_di.return_value
        client.make_context.assert_called_once_with()
        client.make_context.return_value.call_with_async_di.assert_awaited_once_with(
            mock_callback, "777", 555, meep="3222"
        )


class MockContext(alluka.abc.Context):
    @property
    def injection_client(self) -> alluka.abc.Client:
        raise NotImplementedError

    @typing.overload
    def get_type_dependency(self, type_: type[_T], /) -> _T: ...

    @typing.overload
    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT) -> typing.Union[_T, _DefaultT]: ...

    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT = ...) -> typing.Union[_T, _DefaultT]:
        raise NotImplementedError


class TestContext:
    def test_cache_result(self):
        mock_callback = mock.Mock()
        ctx = MockContext()
        ctx.cache_result(mock_callback, mock.Mock())

    def test_get_cached_result(self):
        ctx = alluka.Context(alluka.Client())

        with pytest.raises(KeyError):
            ctx.get_cached_result(mock.Mock())

    def test_get_cached_result_when_defaulting(self):
        ctx = alluka.Context(alluka.Client())
        default = mock.Mock()

        value = ctx.get_cached_result(mock.Mock(), default=default)

        assert value is default

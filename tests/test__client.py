# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020-2022, Faster Speeding
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

import typing
from unittest import mock

import pytest

import alluka

# pyright: reportUnknownMemberType=none
# pyright: reportPrivateUsage=none
# pyright: reportIncompatibleMethodOverride=none


def test_inject():
    descriptor = alluka.inject()

    assert descriptor.type is None
    assert descriptor.callback is None


def test_inject_when_type():
    mock_type = mock.Mock()

    descriptor = alluka.inject(type=mock_type)

    assert descriptor.type is mock_type
    assert descriptor.callback is None


def test_inject_when_callback():
    mock_callback = mock.Mock()

    descriptor = alluka.inject(callback=mock_callback)

    assert descriptor.type is None
    assert descriptor.callback is mock_callback


def test_inject_when_both_callback_and_type():
    with pytest.raises(ValueError, match="Only one of `callback` or `type` can be specified"):
        alluka.inject(type=mock.Mock(), callback=mock.Mock())  # type: ignore


class TestClient:
    def test_as_async_self_injecting(self):
        mock_callback = mock.Mock()
        client = alluka.Client()

        result = client.as_async_self_injecting(mock_callback)

        assert isinstance(result, alluka.AsyncSelfInjecting)
        assert result._callback is mock_callback
        assert result._client is client

    def test_as_self_injecting(self):
        mock_callback = mock.Mock()
        client = alluka.Client()

        result = client.as_self_injecting(mock_callback)

        assert isinstance(result, alluka.SelfInjecting)
        assert result._callback is mock_callback
        assert result._client is client

    def test_call_with_di(self):
        mock_call_with_ctx = mock.Mock()

        class MockClient(alluka.Client):
            call_with_ctx = mock_call_with_ctx

        client = MockClient()
        mock_callback = mock.Mock()

        with mock.patch("alluka._client.BasicContext") as basic_context:
            result = client.call_with_di(mock_callback, "ea", "gb", jp="nyaa")

        assert result is mock_call_with_ctx.return_value
        mock_call_with_ctx.assert_called_once_with(basic_context.return_value, mock_callback, "ea", "gb", jp="nyaa")
        basic_context.assert_called_once_with(client)

    @pytest.mark.anyio()
    async def test_call_with_async_di(self):
        mock_call_with_ctx_async = mock.AsyncMock()

        class MockClient(alluka.Client):
            call_with_ctx_async = mock_call_with_ctx_async

        client = MockClient()
        mock_callback = mock.Mock()

        with mock.patch("alluka._client.BasicContext") as basic_context:
            result = await client.call_with_async_di(mock_callback, 123, jp=6969)

        assert result is mock_call_with_ctx_async.return_value
        mock_call_with_ctx_async.assert_called_once_with(basic_context.return_value, mock_callback, 123, jp=6969)
        basic_context.assert_called_once_with(client)

    def test_set_type_dependency(self):
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        client = alluka.Client()

        result = client.set_type_dependency(mock_type, mock_value)

        assert result is client
        assert client.get_type_dependency(mock_type) is mock_value

    def test_get_type_dependency(self):
        mock_type: typing.Any = mock.Mock()
        client = alluka.Client()

        result = client.get_type_dependency(mock_type)

        assert result is alluka.abc.UNDEFINED

    def test_remove_type_dependency(self):
        mock_type: typing.Any = mock.Mock()
        client = alluka.Client()
        client.set_type_dependency(mock_type, mock.Mock())

        result = client.remove_type_dependency(mock_type)

        assert result is client
        assert client.get_type_dependency(mock_type) is alluka.abc.UNDEFINED

    def test_remove_type_dependency_when_not_set(self):
        mock_type: typing.Any = mock.Mock()
        client = alluka.Client()

        with pytest.raises(KeyError):
            client.remove_type_dependency(mock_type)

    def test_set_callback_override(self):
        mock_callback = mock.Mock()
        mock_override = mock.Mock()
        client = alluka.Client()

        result = client.set_callback_override(mock_callback, mock_override)

        assert result is client
        assert client.get_callback_override(mock_callback) is mock_override

    def test_get_callback_override(self):
        client = alluka.Client()

        assert client.get_callback_override(mock.Mock()) is None

    def test_remove_callback_override(self):
        mock_callback = mock.Mock()
        client = alluka.Client()
        client.set_callback_override(mock_callback, mock.Mock())

        result = client.remove_callback_override(mock_callback)

        assert result is client
        client.get_callback_override(mock_callback) is None

    def test_remove_callback_override_when_not_set(self):
        mock_callback = mock.Mock()
        client = alluka.Client()

        with pytest.raises(KeyError):
            client.remove_callback_override(mock_callback)


class TestBasicContext:
    def test_injection_client_property(self):
        mock_client = mock.Mock()
        ctx = alluka.BasicContext(mock_client)

        assert ctx.injection_client is mock_client

    def test_cache_result(self):
        mock_callback = mock.Mock()
        mock_result = mock.Mock()
        ctx = alluka.BasicContext(mock.Mock())
        ctx.cache_result(mock_callback, mock_result)

        assert ctx.get_cached_result(mock_callback) is mock_result

    def test_call_with_di(self):
        mock_client = mock.Mock()
        mock_callback = mock.Mock()
        ctx = alluka.BasicContext(mock_client)

        result = ctx.call_with_di(mock_callback, 1, "ok", ex="nah", pa="bah")

        assert result is mock_client.call_with_ctx.return_value
        mock_client.call_with_ctx.assert_called_once_with(ctx, mock_callback, 1, "ok", ex="nah", pa="bah")

    @pytest.mark.anyio()
    async def test_call_with_async_di(self):
        mock_client = mock.AsyncMock()
        mock_callback = mock.Mock()
        ctx = alluka.BasicContext(mock_client)

        result = await ctx.call_with_async_di(mock_callback, "op", ah=123)

        assert result is mock_client.call_with_ctx_async.return_value
        mock_client.call_with_ctx_async.assert_awaited_once_with(ctx, mock_callback, "op", ah=123)

    def test_get_cached_result(self):
        ctx = alluka.BasicContext(mock.Mock())

        assert ctx.get_cached_result(mock.Mock()) is alluka.abc.UNDEFINED

    def test_get_type_dependency(self):
        mock_client = mock.Mock()
        mock_type: typing.Any = mock.Mock()
        ctx = alluka.BasicContext(mock_client)

        result = ctx.get_type_dependency(mock_type)

        assert result is mock_client.get_type_dependency.return_value
        mock_client.get_type_dependency.assert_called_once_with(mock_type)

    def test_get_type_dependency_when_special_cased(self):
        mock_client = mock.Mock()
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        ctx = alluka.BasicContext(mock_client)._set_type_special_case(mock_type, mock_value)

        result = ctx.get_type_dependency(mock_type)

        assert result is mock_value
        mock_client.get_type_dependency.assert_not_called()

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

    def test_execute(self):
        ...

    def test_execute_with_ctx(self):
        ...

    @pytest.mark.anyio()
    async def test_execute_async(self):
        ...

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async(self):
        ...

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

    @pytest.mark.skip(reason="TODO: decide on whether to keep this")
    def test_validate_callback(self):
        ...


class TestBasicContext:
    def test_injection_client_property(self):
        ...

    def test_cache_result(self):
        ...

    def test_execute(self):
        ...

    @pytest.mark.anyio()
    async def test_execute_async(self):
        ...

    def test_get_cached_result(self):
        ...

    def test_get_type_dependency(self):
        ...

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

import contextvars
from unittest import mock

import pytest

import alluka
import alluka.local


def test_initialize():
    alluka.local.initialize()

    assert isinstance(alluka.local.get_client(), alluka.Client)

    # This needs to be reset to avoid an issue with Pytest's scoping.
    alluka.local._injector = contextvars.ContextVar[alluka.abc.Client](  # pyright: ignore[reportPrivateUsage]
        "alluka_injector"
    )


def test_initialize_when_passed_through():
    mock_client = mock.Mock()
    alluka.local.initialize(mock_client)

    assert alluka.local.get_client() is mock_client

    # This needs to be reset to avoid an issue with Pytest's scoping.
    alluka.local._injector = contextvars.ContextVar[alluka.abc.Client](  # pyright: ignore[reportPrivateUsage]
        "alluka_injector"
    )


def test_initialize_when_already_set():
    with alluka.local.scope_client():  # noqa: SIM117
        with pytest.raises(RuntimeError, match="Alluka client already set for the current scope"):
            alluka.local.initialize()


def test_initialize_when_passed_through_and_already_set():
    with alluka.local.scope_client():  # noqa: SIM117
        with pytest.raises(RuntimeError, match="Alluka client already set for the current scope"):
            alluka.local.initialize(mock.Mock())


def test_scope_client():
    assert alluka.local.get_client(default=None) is None

    with alluka.local.scope_client() as client:
        assert isinstance(client, alluka.Client)
        assert alluka.local.get_client() is client

        with alluka.local.scope_client() as other_client:
            assert isinstance(other_client, alluka.Client)
            assert other_client is not client
            assert alluka.local.get_client() is other_client

        assert alluka.local.get_client() is client

    assert alluka.local.get_client(default=None) is None


def test_scope_client_when_passed_through():
    mock_client = mock.Mock()
    mock_other_client = mock.Mock()

    assert alluka.local.get_client(default=None) is None

    with alluka.local.scope_client(mock_client) as client:
        assert client is mock_client
        assert alluka.local.get_client() is mock_client

        with alluka.local.scope_client(mock_other_client) as other_client:
            assert other_client is mock_other_client
            assert mock_other_client is not mock_client
            assert alluka.local.get_client() is mock_other_client

        assert alluka.local.get_client() is mock_client

    assert alluka.local.get_client(default=None) is None


def test_scope_context():
    assert alluka.local.get_context(default=None) is None
    mock_context_1 = mock.Mock()
    mock_context_2 = mock.Mock()

    with alluka.local.scope_context(mock_context_1) as set_context:
        assert set_context is mock_context_1
        assert alluka.local.get_context() is mock_context_1

        with alluka.local.scope_context(mock_context_2) as other_set_context:
            assert other_set_context is mock_context_2
            assert other_set_context is not set_context
            assert alluka.local.get_context() is mock_context_2

        assert alluka.local.get_context() is mock_context_1

    assert alluka.local.get_context(default=None) is None


def test_scope_context_when_not_passed():
    client = alluka.Client()

    with alluka.local.scope_client(client):
        with alluka.local.scope_context() as set_context:
            assert set_context.injection_client is client


def test_scope_context_when_not_passed_and_no_scoped_client():
    with pytest.raises(RuntimeError, match="No Alluka client set for the current scope"):
        with alluka.local.scope_context():
            ...


def test_get_client():
    mock_client = mock.Mock()

    with alluka.local.scope_client(mock_client):
        assert alluka.local.get_client() is mock_client


def test_get_client_when_context_set():
    mock_context = mock.Mock()

    with alluka.local.scope_context(mock_context):
        assert alluka.local.get_client() is mock_context.injection_client


def test_get_client_when_not_set():
    with pytest.raises(RuntimeError, match="No Alluka client set for the current scope"):
        alluka.local.get_client()


def test_get_client_when_not_set_and_default():
    result = alluka.local.get_client(default=None)

    assert result is None


def test_get():
    mock_client = mock.Mock()

    with alluka.local.scope_client(mock_client), pytest.warns(DeprecationWarning):
        assert alluka.local.get() is mock_client  # pyright: ignore[reportDeprecated]


def test_get_when_context_set():
    mock_context = mock.Mock()

    with alluka.local.scope_context(mock_context), pytest.warns(DeprecationWarning):
        assert alluka.local.get() is mock_context.injection_client  # pyright: ignore[reportDeprecated]


def test_get_when_not_set():
    with (
        pytest.raises(RuntimeError, match="No Alluka client set for the current scope"),
        pytest.warns(DeprecationWarning),
    ):
        alluka.local.get()  # pyright: ignore[reportDeprecated]


def test_get_when_not_set_and_default():
    with pytest.warns(DeprecationWarning):
        result = alluka.local.get(default=None)  # pyright: ignore[reportDeprecated]

    assert result is None


def test_get_context():
    mock_context = mock.Mock()

    with alluka.local.scope_context(mock_context):
        assert alluka.local.get_context(from_client=False) is mock_context


def test_get_context_when_when_not_set():
    with pytest.raises(RuntimeError, match="Alluka context not set for the current scope"):
        alluka.local.get_context()


def test_get_context_when_when_not_set_and_default():
    mock_default = mock.Mock()

    result = alluka.local.get_context(default=mock_default)

    assert result is mock_default


def test_get_context_when_from_client():
    mock_context = mock.Mock()

    with alluka.local.scope_context(mock_context):
        assert alluka.local.get_context(from_client=False) is mock_context


def test_get_context_when_from_client_falls_back_to_client():
    mock_client = mock.Mock()

    with alluka.local.scope_client(mock_client):
        assert alluka.local.get_context() is mock_client.make_context.return_value

    mock_client.make_context.assert_called_once_with()


def test_get_context_when_when_from_client_and_not_set_and_cannot_fall_back_to_client():
    with pytest.raises(RuntimeError, match="Alluka context not set for the current scope"):
        assert alluka.local.get_context()


def test_get_context_when_when_from_client_and_not_set_and_cannot_fall_back_to_client_and_default():
    mock_default = mock.Mock()

    result = alluka.local.get_context(default=mock_default)

    assert result is mock_default


def test_call_with_di_with_scoped_client():
    mock_client = mock.Mock()
    mock_callback = mock.Mock()

    with alluka.local.scope_client(mock_client):
        result = alluka.local.call_with_di(mock_callback, 123, 321, 123, 333, hello="Ok", bye="meow")

    assert result is mock_client.make_context.return_value.call_with_di.return_value
    mock_client.make_context.assert_called_once_with()
    mock_client.make_context.return_value.call_with_di.assert_called_once_with(
        mock_callback, 123, 321, 123, 333, hello="Ok", bye="meow"
    )


def test_call_with_di_with_scoped_context():
    mock_context = mock.Mock()
    mock_callback = mock.Mock()

    with alluka.local.scope_context(mock_context):
        result = alluka.local.call_with_di(mock_callback, 123, 321, 123, 321, hello="Ok", bye="meow")

    assert result is mock_context.call_with_di.return_value
    mock_context.call_with_di.assert_called_once_with(mock_callback, 123, 321, 123, 321, hello="Ok", bye="meow")


@pytest.mark.anyio
async def test_call_with_async_di_with_scoped_client():
    mock_client = mock.Mock()
    mock_client.make_context.return_value = mock.AsyncMock()
    mock_callback = mock.Mock()

    with alluka.local.scope_client(mock_client):
        result = await alluka.local.call_with_async_di(mock_callback, 69, 320, hello="goodbye")

    assert result is mock_client.make_context.return_value.call_with_async_di.return_value
    mock_client.make_context.assert_called_once_with()
    mock_client.make_context.return_value.call_with_async_di.assert_awaited_once_with(
        mock_callback, 69, 320, hello="goodbye"
    )


@pytest.mark.anyio
async def test_call_with_async_di_with_scoped_context():
    mock_context = mock.AsyncMock()
    mock_callback = mock.Mock()

    with alluka.local.scope_context(mock_context):
        result = await alluka.local.call_with_async_di(mock_callback, 69, 321, hello="goodbye")

    assert result is mock_context.call_with_async_di.return_value
    mock_context.call_with_async_di.assert_awaited_once_with(mock_callback, 69, 321, hello="goodbye")


def test_auto_inject_with_scoped_client():
    mock_client = mock.Mock()
    mock_callback = mock.Mock()
    callback = alluka.local.auto_inject(mock_callback)

    with alluka.local.scope_client(mock_client):
        result = callback(444, "321", 555, "asd", sneaky="NO", meep="meow")

    assert result is mock_client.make_context.return_value.call_with_di.return_value
    mock_client.make_context.assert_called_once_with()
    mock_client.make_context.return_value.call_with_di.assert_called_once_with(
        mock_callback, 444, "321", 555, "asd", sneaky="NO", meep="meow"
    )


def test_auto_inject_with_scoped_context():
    mock_context = mock.Mock()
    mock_callback = mock.Mock()
    callback = alluka.local.auto_inject(mock_callback)

    with alluka.local.scope_context(mock_context):
        result = callback(444, "321", 555, "asd", sneaky="NO", meep="meow")

    assert result is mock_context.call_with_di.return_value
    mock_context.call_with_di.assert_called_once_with(mock_callback, 444, "321", 555, "asd", sneaky="NO", meep="meow")


@pytest.mark.anyio
async def test_auto_inject_async_with_scoped_client():
    mock_client = mock.Mock()
    mock_client.make_context.return_value = mock.AsyncMock()
    mock_callback = mock.Mock()
    callback = alluka.local.auto_inject_async(mock_callback)

    with alluka.local.scope_client(mock_client):
        result = await callback(555, "320", goodbye="hello")

    assert result is mock_client.make_context.return_value.call_with_async_di.return_value
    mock_client.make_context.assert_called_once_with()
    mock_client.make_context.return_value.call_with_async_di.assert_awaited_once_with(
        mock_callback, 555, "320", goodbye="hello"
    )


@pytest.mark.anyio
async def test_auto_inject_async_with_scoped_context():
    mock_context = mock.AsyncMock()
    mock_callback = mock.Mock()
    callback = alluka.local.auto_inject_async(mock_callback)

    with alluka.local.scope_context(mock_context):
        result = await callback(555, "320", goodbye="hello")

    assert result is mock_context.call_with_async_di.return_value
    mock_context.call_with_async_di.assert_awaited_once_with(mock_callback, 555, "320", goodbye="hello")

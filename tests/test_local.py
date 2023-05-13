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

from unittest import mock

import pytest

import alluka
import alluka.local


def test_initialize():
    alluka.local.initialize()

    assert isinstance(alluka.local.get(), alluka.Client)


def test_initialize_when_passed_through():
    mock_client = mock.Mock()
    alluka.local.initialize(mock_client)

    assert alluka.local.get() is mock_client


def test_initialize_when_already_set():
    alluka.local.initialize()

    with pytest.raises(RuntimeError, match="Alluka client already initialised in the current context"):
        alluka.local.initialize()


def test_initialize_when_passed_through_and_already_set():
    alluka.local.initialize()

    with pytest.raises(RuntimeError, match="Alluka client already initialised in the current context"):
        alluka.local.initialize(mock.Mock())


def test_get():
    mock_client = mock.Mock()
    alluka.local.initialize(mock_client)

    assert alluka.local.get() is mock_client


def test_get_when_not_set():
    with pytest.raises(RuntimeError, match="Alluka client not initialised in the current context"):
        alluka.local.get()


def test_get_when_not_set_and_default():
    result = alluka.local.get(default=None)

    assert result is None


def test_call_with_di():
    mock_client = mock.Mock()
    alluka.local.initialize(mock_client)
    mock_callback = mock.Mock()

    result = alluka.local.call_with_di(mock_callback, 123, 321, 123, 321, hello="Ok", bye="meow")

    assert result is mock_client.call_with_di.return_value
    mock_client.call_with_di.assert_called_once_with(mock_callback, 123, 321, 123, 321, hello="Ok", bye="meow")


@pytest.mark.anyio()
async def test_call_with_async_di():
    mock_client = mock.AsyncMock()
    alluka.local.initialize(mock_client)
    mock_callback = mock.Mock()

    result = await alluka.local.call_with_async_di(mock_callback, 69, 320, hello="goodbye")

    assert result is mock_client.call_with_async_di.return_value
    mock_client.call_with_async_di.assert_awaited_once_with(mock_callback, 69, 320, hello="goodbye")


def test_as_self_async_injecting():
    mock_callback = mock.Mock()

    result = alluka.local.as_self_async_injecting(mock_callback)

    assert isinstance(result, alluka.AsyncSelfInjecting)
    assert result._get_client is alluka.local.get
    assert result.callback is mock_callback


def test_as_self_injecting():
    mock_callback = mock.Mock()

    result = alluka.local.as_self_injecting(mock_callback)

    assert isinstance(result, alluka.SelfInjecting)
    assert result._get_client is alluka.local.get
    assert result.callback is mock_callback

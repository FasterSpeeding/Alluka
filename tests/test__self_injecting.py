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


class TestAsyncSelfInjecting:
    @pytest.mark.anyio()
    async def test_call_dunder_method(self):
        mock_callback = mock.Mock()
        mock_client = mock.AsyncMock()
        self_injecting = alluka.AsyncSelfInjecting(mock_client, mock_callback)

        result = await self_injecting()

        assert result is mock_client.call_with_async_di.return_value
        mock_client.call_with_async_di.assert_awaited_once_with(mock_callback)

    def test_callback_property(self):
        mock_callback = mock.Mock()

        self_injecting = alluka.AsyncSelfInjecting(mock.Mock(), mock_callback)

        assert self_injecting.callback is mock_callback


class TestSelfInjecting:
    def test_call_dunder_method(self):
        mock_callback = mock.Mock()
        mock_client = mock.Mock()
        self_injecting = alluka.SelfInjecting(mock_client, mock_callback)

        result = self_injecting()

        assert result is mock_client.call_with_di.return_value
        mock_client.call_with_di.assert_called_once_with(mock_callback)

    def test_callback_property(self):
        mock_callback = mock.Mock()

        self_injecting = alluka.SelfInjecting(mock.Mock(), mock_callback)

        assert self_injecting.callback is mock_callback

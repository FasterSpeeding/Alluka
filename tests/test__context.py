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

# pyright: reportUnknownMemberType=none
# pyright: reportPrivateUsage=none
# pyright: reportIncompatibleMethodOverride=none

import typing

import mock
import pytest

import alluka


class TestContext:
    def test_injection_client_property(self):
        mock_client = alluka.Client()
        ctx = alluka.Context(mock_client)

        assert ctx.injection_client is mock_client

    def test_get_type_dependency(self):
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        mock_client = alluka.Client().set_type_dependency(mock_type, mock_value)
        ctx = alluka.Context(mock_client)

        result = ctx.get_type_dependency(mock_type)

        assert result is mock_value

    def test_get_type_dependency_when_type_is_context_abc(self):
        mock_client = alluka.Client().set_type_dependency(alluka.abc.Context, mock.Mock())
        ctx = alluka.Context(mock_client)

        result = ctx.get_type_dependency(alluka.abc.Context)

        assert result is ctx

    def test_get_type_dependency_with_default(self):
        default = object()
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        mock_client = alluka.Client().set_type_dependency(mock_type, mock_value)
        ctx = alluka.Context(mock_client)

        result = ctx.get_type_dependency(mock_type, default=default)

        assert result is mock_value

    def test_get_type_dependency_when_not_found_with_default(self):
        default = object()
        mock_type: typing.Any = mock.Mock()
        ctx = alluka.Context(alluka.Client())

        result = ctx.get_type_dependency(mock_type, default=default)

        assert result is default

    def test_get_type_dependency_when_not_found(self):
        mock_type: typing.Any = mock.Mock()
        ctx = alluka.Context(alluka.Client())

        with pytest.raises(KeyError):
            ctx.get_type_dependency(mock_type)


class TestCachingContext:
    def test_cache_result(self):
        mock_callback = mock.Mock()
        mock_result = mock.Mock()
        ctx = alluka.CachingContext(alluka.Client())
        ctx.cache_result(mock_callback, mock_result)

        assert ctx.get_cached_result(mock_callback) is mock_result

    def test_get_cached_result_when_not_found(self):
        ctx = alluka.CachingContext(alluka.Client())

        with pytest.raises(KeyError):
            ctx.get_cached_result(mock.Mock())

    def test_get_cached_result_when_not_found_with_default(self):
        ctx = alluka.CachingContext(alluka.Client())
        default = object()

        assert ctx.get_cached_result(mock.Mock(), default=default) is default


class TestOverridingContext:
    def test_from_client(self):
        client = mock.Mock(alluka.Client)
        expected_context = client.make_context.return_value

        ctx = alluka.OverridingContext.from_client(client)

        assert ctx.injection_client is expected_context.injection_client
        assert ctx.get_type_dependency(int, default=123) is expected_context.get_type_dependency.return_value
        expected_context.get_type_dependency.assert_called_once_with(int, default=123)
        client.make_context.assert_called_once_with()

    def test_injection_client_property(self):
        mock_context = mock.Mock()
        ctx = alluka.OverridingContext(mock_context)

        assert ctx._context is mock_context

    def test_get_cached_result(self):
        mock_context = mock.Mock()
        mock_callback = mock.Mock()
        ctx = alluka.OverridingContext(mock_context)

        result = ctx.get_cached_result(mock_callback, default=123321)

        assert result is mock_context.get_cached_result.return_value
        mock_context.get_cached_result.assert_called_once_with(mock_callback, default=123321)

    def test_get_cached_result_when_not_cached(self):
        mock_callback = mock.Mock()
        ctx = alluka.OverridingContext(alluka.Client().make_context())

        with pytest.raises(KeyError):
            ctx.get_cached_result(mock_callback)

    def test_get_cached_result_when_not_cached_with_default_set(self):
        mock_callback = mock.Mock()
        ctx = alluka.OverridingContext(alluka.Client().make_context())

        result = ctx.get_cached_result(mock_callback, default=4333)

        assert result == 4333

    def test_cache_result(self):
        mock_context = mock.Mock()
        mock_callback = mock.Mock()
        mock_value = mock.Mock()
        ctx = alluka.OverridingContext(mock_context)

        ctx.cache_result(mock_callback, mock_value)

        mock_context.cache_result.assert_called_once_with(mock_callback, mock_value)

    def test_get_type_dependency(self):
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        context = alluka.Client().set_type_dependency(mock_type, mock_value).make_context()
        context = alluka.OverridingContext(context)

        assert context.get_type_dependency(mock_type) is mock_value

    def test_get_type_dependency_when_default_passed(self):
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        context = alluka.Client().set_type_dependency(mock_type, mock_value).make_context()
        context = alluka.OverridingContext(context)

        assert context.get_type_dependency(mock_type, default=123) is mock_value

    def test_get_type_dependency_when_overriden(self):
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        context = alluka.Client().set_type_dependency(mock_type, mock.Mock()).make_context()
        context = alluka.OverridingContext(context).set_type_dependency(mock_type, mock_value)

        assert context.get_type_dependency(mock_type) is mock_value

    def test_get_type_dependency_when_overriden_and_default_passed(self):
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        context = alluka.Client().set_type_dependency(mock_type, mock.Mock()).make_context()
        context = alluka.OverridingContext(context).set_type_dependency(mock_type, mock_value)

        assert context.get_type_dependency(mock_type, default=123) is mock_value

    def test_get_type_dependency_when_overridden_only(self):
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        context = alluka.Client().make_context()
        context = alluka.OverridingContext(context).set_type_dependency(mock_type, mock_value)

        assert context.get_type_dependency(mock_type) is mock_value

    def test_get_type_dependency_when_not_found(self):
        mock_type: typing.Any = mock.Mock()
        context = alluka.OverridingContext(alluka.Client().make_context())

        with pytest.raises(KeyError):
            context.get_type_dependency(mock_type)

    def test_get_type_dependency_when_not_found_with_default(self):
        mock_type: typing.Any = mock.Mock()
        context = alluka.OverridingContext(alluka.Client().make_context())

        value = context.get_type_dependency(mock_type, default=4444)

        assert value == 4444


class TestBasicContext:
    def test_get_type_dependency(self):
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        mock_client = alluka.Client().set_type_dependency(mock_type, mock_value)
        ctx = alluka.BasicContext(mock_client)  # pyright: ignore[reportDeprecated]

        result = ctx.get_type_dependency(mock_type)

        assert result is mock_value

    def test_get_type_dependency_with_default(self):
        default = object()
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        mock_client = alluka.Client().set_type_dependency(mock_type, mock_value)
        ctx = alluka.BasicContext(mock_client)  # pyright: ignore[reportDeprecated]

        result = ctx.get_type_dependency(mock_type, default=default)

        assert result is mock_value

    def test_get_type_dependency_when_not_found(self):
        mock_type: typing.Any = mock.Mock()
        ctx = alluka.BasicContext(alluka.Client())  # pyright: ignore[reportDeprecated]

        with pytest.raises(KeyError):
            ctx.get_type_dependency(mock_type)

    def test_get_type_dependency_when_not_found_with_default(self):
        default = object()
        mock_type: typing.Any = mock.Mock()
        ctx = alluka.BasicContext(alluka.Client())  # pyright: ignore[reportDeprecated]

        result = ctx.get_type_dependency(mock_type, default=default)

        assert result is default

    def test_get_type_dependency_when_special_cased(self):
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        mock_client = alluka.Client().set_type_dependency(mock_type, mock.Mock())
        ctx = alluka.BasicContext(mock_client)._set_type_special_case(  # pyright: ignore[reportDeprecated]
            mock_type, mock_value
        )

        result = ctx.get_type_dependency(mock_type)

        assert result is mock_value

    def test__remove_type_special_case(self):
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        mock_client = alluka.Client().set_type_dependency(mock_type, mock_value)
        ctx = alluka.BasicContext(mock_client)._set_type_special_case(  # pyright: ignore[reportDeprecated]
            mock_type, mock.Mock()
        )

        ctx._remove_type_special_case(mock_type)  # pyright: ignore[reportDeprecated]

        assert ctx.get_type_dependency(mock_type) is mock_value

    def test__remove_type_special_case_when_not_set(self):
        mock_client = alluka.Client()
        mock_callback = mock.Mock()
        ctx = alluka.BasicContext(mock_client)  # pyright: ignore[reportDeprecated]

        with pytest.raises(KeyError):
            ctx._remove_type_special_case(mock_callback)  # pyright: ignore[reportDeprecated]

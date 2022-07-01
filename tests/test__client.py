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
import warnings
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
        class MockType1:
            ...

        class MockType2:
            ...

        class MockType3:
            ...

        mock_value_1 = MockType1()
        mock_value_2 = MockType2()
        mock_value_3 = MockType3()
        mock_callback = mock.Mock()
        mock_override = mock.Mock()

        def callback(
            foo: int,
            bar: str,
            bam: alluka.Injected[MockType1],
            baz: alluka.Injected[typing.Union[int, str, None]],
            other_result: typing.Annotated[int, alluka.inject(callback=lambda: "no you")],
            overridden: typing.Annotated[int, alluka.inject(callback=mock_callback)],
            bart_man: alluka.Injected[int] = 123,
            meow: MockType3 = alluka.inject(type=MockType3),
            nyaa: typing.Optional[bool] = alluka.inject(type=typing.Optional[bool]),
            result: typing.Optional[str] = alluka.inject(callback=lambda: "hi"),
        ) -> str:
            assert foo == 43234
            assert bar == "nyaa"
            assert bam is mock_value_1
            assert baz is None
            assert other_result == "no you"
            assert overridden is mock_override.return_value
            assert bart_man == 123
            assert meow is mock_value_3
            assert nyaa is None
            assert result == "hi"
            return "ok"

        client = (
            alluka.Client()
            .set_type_dependency(MockType1, mock_value_1)
            .set_type_dependency(MockType2, mock_value_2)
            .set_type_dependency(MockType3, mock_value_3)
            .set_callback_override(mock_callback, mock_override)
        )

        result = client.call_with_di(callback, 43234, bar="nyaa")

        assert result == "ok"

    def test_call_with_di_when_type_not_found(self):
        class MockType:
            ...

        def callback(value: alluka.Injected[MockType]) -> typing.NoReturn:
            raise NotImplementedError

        client = alluka.Client()

        with pytest.raises(alluka.MissingDependencyError):
            client.call_with_di(callback)

    def test_call_with_di_when_type_not_found_when_async_callback(self):
        async def callback(value: alluka.Injected[int]) -> typing.NoReturn:
            raise NotImplementedError

        client = alluka.Client().set_type_dependency(int, 123)

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning)

            with pytest.raises(alluka.AsyncOnlyError):
                client.call_with_di(callback)

    def test_call_with_di_when_type_not_found_when_async_dependency(self):
        class MockType:
            ...

        def callback(
            value: alluka.Injected[MockType], dep: int = alluka.inject(callback=mock.AsyncMock())
        ) -> typing.NoReturn:
            raise NotImplementedError

        client = alluka.Client().set_type_dependency(MockType, MockType())

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning)

            with pytest.raises(alluka.AsyncOnlyError):
                client.call_with_di(callback)

    @pytest.mark.anyio()
    async def test_call_with_async_di(self):
        class MockType1:
            ...

        class MockType2:
            ...

        class MockType3:
            ...

        mock_value_1 = MockType1()
        mock_value_2 = MockType2()
        mock_value_3 = MockType3()
        mock_callback = mock.Mock()
        mock_override = mock.AsyncMock()
        mock_other_callback = mock.AsyncMock()
        mock_other_override = mock.Mock()

        async def callback(
            foo: int,
            bar: str,
            bam: alluka.Injected[MockType1],
            baz: alluka.Injected[typing.Union[int, str, None]],
            other_result: typing.Annotated[int, alluka.inject(callback=lambda: "no you")],
            overridden: typing.Annotated[int, alluka.inject(callback=mock_callback)],
            other_overridden: typing.Any = alluka.inject(callback=mock_other_callback),
            bart_man: alluka.Injected[int] = 123,
            meow: MockType3 = alluka.inject(type=MockType3),
            nyaa: typing.Optional[bool] = alluka.inject(type=typing.Optional[bool]),
            result: typing.Optional[str] = alluka.inject(callback=lambda: "hi"),
        ) -> str:
            assert foo == 43234
            assert bar == "nyaa"
            assert bam is mock_value_1
            assert baz is None
            assert other_result == "no you"
            assert overridden is mock_override.return_value
            assert other_overridden is mock_other_override.return_value
            assert bart_man == 123
            assert meow is mock_value_3
            assert nyaa is None
            assert result == "hi"
            return "ok"

        client = (
            alluka.Client()
            .set_type_dependency(MockType1, mock_value_1)
            .set_type_dependency(MockType2, mock_value_2)
            .set_type_dependency(MockType3, mock_value_3)
            .set_callback_override(mock_callback, mock_override)
            .set_callback_override(mock_other_callback, mock_other_override)
        )

        result = await client.call_with_async_di(callback, 43234, bar="nyaa")

        assert result == "ok"

    @pytest.mark.anyio()
    async def test_call_with_async_di_when_type_not_found(self):
        class MockType:
            ...

        def callback(value: alluka.Injected[MockType]) -> typing.NoReturn:
            raise NotImplementedError

        client = alluka.Client()

        with pytest.raises(alluka.MissingDependencyError):
            await client.call_with_async_di(callback)

    def test_set_type_dependency_when_not_found(self):
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        client = alluka.Client()

        result = client.set_type_dependency(mock_type, mock_value)

        assert result is client
        assert client.get_type_dependency(mock_type) is mock_value

    def test_get_type_dependency_when_not_found_and_default(self):
        mock_type: typing.Any = mock.Mock()
        default = object()
        client = alluka.Client()

        result = client.get_type_dependency(mock_type, default=default)

        assert result is default

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
        assert client.get_callback_override(mock_callback) is None

    def test_remove_callback_override_when_not_set(self):
        mock_callback = mock.Mock()
        client = alluka.Client()

        with pytest.raises(KeyError):
            client.remove_callback_override(mock_callback)


class TestBasicContext:
    def test_injection_client_property(self):
        mock_client = alluka.Client()
        ctx = alluka.BasicContext(mock_client)

        assert ctx.injection_client is mock_client

    def test_cache_result(self):
        mock_callback = mock.Mock()
        mock_result = mock.Mock()
        ctx = alluka.BasicContext(alluka.Client())
        ctx.cache_result(mock_callback, mock_result)

        assert ctx.get_cached_result(mock_callback) is mock_result

    def test_get_cached_result_when_not_found(self):
        ctx = alluka.BasicContext(alluka.Client())

        assert ctx.get_cached_result(mock.Mock()) is alluka.abc.UNDEFINED

    def test_get_cached_result_when_not_found_and_default(self):
        ctx = alluka.BasicContext(alluka.Client())
        default = object()

        assert ctx.get_cached_result(mock.Mock(), default=default) is default

    def test_get_type_dependency(self):
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        mock_client = alluka.Client().set_type_dependency(mock_type, mock_value)
        ctx = alluka.BasicContext(mock_client)

        result = ctx.get_type_dependency(mock_type)

        assert result is mock_value

    def test_get_type_dependency_with_default(self):
        default = object()
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        mock_client = alluka.Client().set_type_dependency(mock_type, mock_value)
        ctx = alluka.BasicContext(mock_client)

        result = ctx.get_type_dependency(mock_type, default=default)

        assert result is mock_value

    def test_get_type_dependency_with_default_and_defaulting(self):
        default = object()
        mock_type: typing.Any = mock.Mock()
        ctx = alluka.BasicContext(alluka.Client())

        result = ctx.get_type_dependency(mock_type, default=default)

        assert result is default

    def test_get_type_dependency_when_special_cased(self):
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        mock_client = alluka.Client().set_type_dependency(mock_type, mock_value)
        ctx = alluka.BasicContext(mock_client)._set_type_special_case(mock_type, mock_value)

        result = ctx.get_type_dependency(mock_type)

        assert result is mock_value

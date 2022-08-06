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
from collections import abc as collections
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
        mock_callback = mock.Mock(collections.Callable[..., typing.Any])
        mock_override = mock.Mock(collections.Callable[..., typing.Any])

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

            with pytest.raises(alluka.SyncOnlyError):
                client.call_with_di(callback)

    def test_call_with_di_when_type_not_found_when_async_dependency(self):
        class MockType:
            ...

        def callback(
            value: alluka.Injected[MockType],
            dep: int = alluka.inject(callback=mock.AsyncMock(collections.Callable[..., typing.Any])),
        ) -> typing.NoReturn:
            raise NotImplementedError

        client = alluka.Client().set_type_dependency(MockType, MockType())

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning)

            with pytest.raises(alluka.SyncOnlyError):
                client.call_with_di(callback)

    def test_call_with_di_when_manual_di(self):
        client = alluka.Client()
        mock_callback = mock.Mock()
        injected = alluka.ManuallyInjected(mock_callback)

        result = client.call_with_di(injected, 123, 321, ok="meow")

        assert result is mock_callback.return_value
        mock_callback.assert_called_once_with(123, 321, ok="meow")

    def test_call_with_di_when_manual_di_callback_deps_set(self):
        mock_callback = mock.Mock()
        mock_dep_1 = mock.Mock(collections.Callable[..., typing.Any])
        mock_dep_2 = mock.Mock(collections.Callable[..., typing.Any])
        mock_dep_3_callback = mock.Mock()
        mock_dep_3 = alluka.ManuallyInjected(mock_dep_3_callback)
        mock_override = mock.Mock(collections.Callable[..., typing.Any])
        client = alluka.Client().set_callback_override(mock_dep_2, mock_override)
        injected = (
            alluka.ManuallyInjected(mock_callback)
            .set_callback("e", mock_dep_1)
            .set_callback("a", mock_dep_2)
            .set_callback("beat", mock_dep_3)
        )

        result = client.call_with_di(injected, 333, no="ow")

        assert result is mock_callback.return_value
        mock_callback.assert_called_once_with(
            333, no="ow", e=mock_dep_1.return_value, a=mock_override.return_value, beat=mock_dep_3_callback.return_value
        )
        mock_dep_1.assert_called_once_with()
        mock_override.assert_called_once_with()
        mock_dep_3_callback.assert_called_once_with()

    def test_call_with_di_when_manual_di_type_deps_set(self):
        class MockType1:
            ...

        class MockType2:
            ...

        class MockType3:
            ...

        mock_value_1 = MockType2()
        mock_value_2 = MockType3()

        client = (
            alluka.Client().set_type_dependency(MockType2, mock_value_1).set_type_dependency(MockType3, mock_value_2)
        )
        mock_callback = mock.Mock()
        injected = (
            alluka.ManuallyInjected(mock_callback)
            .set_type("foo", MockType1, MockType2)
            .set_type("bar", int, default=123)
            .set_type("baz", MockType3)
        )

        result = client.call_with_di(injected, 444, 555, p="e")

        assert result is mock_callback.return_value
        mock_callback.assert_called_once_with(444, 555, p="e", foo=mock_value_1, bar=123, baz=mock_value_2)

    def test_call_with_di_when_manual_di_deps_set(self):
        class MockType1:
            ...

        class MockType2:
            ...

        class MockType3:
            ...

        mock_value_1 = MockType2()
        mock_value_2 = MockType3()

        mock_callback = mock.Mock()
        mock_dep_1 = mock.Mock(collections.Callable[..., typing.Any])
        mock_dep_2 = mock.Mock(collections.Callable[..., typing.Any])
        mock_dep_3_callback = mock.Mock()
        mock_dep_3 = alluka.ManuallyInjected(mock_dep_3_callback)
        mock_override = mock.Mock(collections.Callable[..., typing.Any])
        client = (
            alluka.Client()
            .set_callback_override(mock_dep_2, mock_override)
            .set_type_dependency(MockType2, mock_value_1)
            .set_type_dependency(MockType3, mock_value_2)
        )
        injected = (
            alluka.ManuallyInjected(mock_callback)
            .set_callback("ea", mock_dep_1)
            .set_callback("aa", mock_dep_2)
            .set_callback("bee", mock_dep_3)
            .set_type("eap", MockType1, MockType2)
            .set_type("bar", int, default=4434)
            .set_type("bat", MockType3)
        )

        result = client.call_with_di(injected, 333, no="ow")

        assert result is mock_callback.return_value
        mock_callback.assert_called_once_with(
            333,
            no="ow",
            ea=mock_dep_1.return_value,
            aa=mock_override.return_value,
            bee=mock_dep_3_callback.return_value,
            eap=mock_value_1,
            bar=4434,
            bat=mock_value_2,
        )
        mock_dep_1.assert_called_once_with()
        mock_override.assert_called_once_with()
        mock_dep_3_callback.assert_called_once_with()

    def test_call_with_di_when_manual_di_when_async(self):
        client = alluka.Client()
        injected = alluka.ManuallyInjected(mock.Mock()).set_callback(
            "aaa", mock.AsyncMock(collections.Callable[..., typing.Any])
        )

        with warnings.catch_warnings():
            warnings.filterwarnings(action="ignore", category=RuntimeWarning)

            with pytest.raises(alluka.SyncOnlyError):
                client.call_with_di(injected, 333, no="ow")

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
        mock_callback = mock.Mock(collections.Callable[..., typing.Any])
        mock_override = mock.AsyncMock(collections.Callable[..., typing.Any])
        mock_other_callback = mock.AsyncMock(collections.Callable[..., typing.Any])
        mock_other_override = mock.Mock(collections.Callable[..., typing.Any])

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

    @pytest.mark.anyio()
    async def test_call_with_async_di_when_manual_di(self):
        client = alluka.Client()
        mock_callback = mock.AsyncMock()
        injected = alluka.ManuallyInjected(mock_callback)

        result = await client.call_with_async_di(injected, 123, 321, ok="meow")

        assert result is mock_callback.return_value
        mock_callback.assert_awaited_once_with(123, 321, ok="meow")

    @pytest.mark.anyio()
    async def test_call_with_async_di_when_manual_di_and_sync(self):
        client = alluka.Client()
        mock_callback = mock.Mock()
        injected = alluka.ManuallyInjected(mock_callback)

        result = await client.call_with_async_di(injected, 123, 321, ok="meow")

        assert result is mock_callback.return_value
        mock_callback.assert_called_once_with(123, 321, ok="meow")

    @pytest.mark.anyio()
    async def test_call_with_async_di_when_manual_di_callback_deps_set(self):
        mock_callback = mock.AsyncMock()
        mock_dep_1 = mock.AsyncMock(collections.Callable[..., typing.Any])
        mock_dep_2 = mock.Mock(collections.Callable[..., typing.Any])
        mock_dep_3_callback = mock.AsyncMock()
        mock_dep_3 = alluka.ManuallyInjected(mock_dep_3_callback)
        mock_override = mock.Mock(collections.Callable[..., typing.Any])
        client = alluka.Client().set_callback_override(mock_dep_2, mock_override)
        injected = (
            alluka.ManuallyInjected(mock_callback)
            .set_callback("e", mock_dep_1)
            .set_callback("a", mock_dep_2)
            .set_callback("beat", mock_dep_3)
        )

        result = await client.call_with_async_di(injected, 333, no="ow")

        assert result is mock_callback.return_value
        mock_callback.assert_awaited_once_with(
            333, no="ow", e=mock_dep_1.return_value, a=mock_override.return_value, beat=mock_dep_3_callback.return_value
        )
        mock_dep_1.assert_awaited_once_with()
        mock_override.assert_called_once_with()
        mock_dep_3_callback.assert_awaited_once_with()

    @pytest.mark.anyio()
    async def test_call_with_async_di_when_manual_di_type_deps_set(self):
        class MockType1:
            ...

        class MockType2:
            ...

        class MockType3:
            ...

        mock_value_1 = MockType2()
        mock_value_2 = MockType3()

        client = (
            alluka.Client().set_type_dependency(MockType2, mock_value_1).set_type_dependency(MockType3, mock_value_2)
        )
        mock_callback = mock.AsyncMock()
        injected = (
            alluka.ManuallyInjected(mock_callback)
            .set_type("foo", MockType1, MockType2)
            .set_type("bar", int, default=123)
            .set_type("baz", MockType3)
        )

        result = await client.call_with_async_di(injected, 444, 555, p="e")

        assert result is mock_callback.return_value
        mock_callback.assert_awaited_once_with(444, 555, p="e", foo=mock_value_1, bar=123, baz=mock_value_2)

    @pytest.mark.anyio()
    async def test_call_with_async_di_when_manual_di_deps_set(self):
        class MockType1:
            ...

        class MockType2:
            ...

        class MockType3:
            ...

        mock_value_1 = MockType2()
        mock_value_2 = MockType3()

        mock_callback = mock.AsyncMock()
        mock_dep_1 = mock.Mock(collections.Callable[..., typing.Any])
        mock_dep_2 = mock.AsyncMock(collections.Callable[..., typing.Any])
        mock_dep_3_callback = mock.AsyncMock()
        mock_dep_3 = alluka.ManuallyInjected(mock_dep_3_callback)
        mock_override = mock.AsyncMock(collections.Callable[..., typing.Any])
        client = (
            alluka.Client()
            .set_callback_override(mock_dep_2, mock_override)
            .set_type_dependency(MockType2, mock_value_1)
            .set_type_dependency(MockType3, mock_value_2)
        )
        injected = (
            alluka.ManuallyInjected(mock_callback)
            .set_callback("ea", mock_dep_1)
            .set_callback("aa", mock_dep_2)
            .set_callback("bee", mock_dep_3)
            .set_type("eap", MockType1, MockType2)
            .set_type("bar", int, default=4434)
            .set_type("bat", MockType3)
        )

        result = await client.call_with_async_di(injected, 333, no="ow")

        assert result is mock_callback.return_value
        mock_callback.assert_awaited_once_with(
            333,
            no="ow",
            ea=mock_dep_1.return_value,
            aa=mock_override.return_value,
            bee=mock_dep_3_callback.return_value,
            eap=mock_value_1,
            bar=4434,
            bat=mock_value_2,
        )
        mock_dep_1.assert_called_once_with()
        mock_override.assert_awaited_once_with()
        mock_dep_3_callback.assert_awaited_once_with()

    def test_set_type_dependency_when_not_found(self):
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        client = alluka.Client()

        result = client.set_type_dependency(mock_type, mock_value)

        assert result is client
        assert client.get_type_dependency(mock_type) is mock_value

    def test_get_type_dependency_when_not_found(self):
        mock_type: typing.Any = mock.Mock()
        client = alluka.Client()

        with pytest.raises(alluka.MissingDependencyError):
            client.get_type_dependency(mock_type)

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

        with pytest.raises(alluka.MissingDependencyError):
            assert client.get_type_dependency(mock_type)

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

    def test_get_type_dependency_when_not_found(self):
        mock_type: typing.Any = mock.Mock()
        ctx = alluka.BasicContext(alluka.Client())

        with pytest.raises(alluka.MissingDependencyError):
            ctx.get_type_dependency(mock_type)

    def test_get_type_dependency_with_default(self):
        default = object()
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        mock_client = alluka.Client().set_type_dependency(mock_type, mock_value)
        ctx = alluka.BasicContext(mock_client)

        result = ctx.get_type_dependency(mock_type, default=default)

        assert result is mock_value

    def test_get_type_dependency_when_not_found_with_default(self):
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

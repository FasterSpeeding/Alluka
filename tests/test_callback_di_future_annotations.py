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

from __future__ import annotations

import sys
import typing
import warnings

import mock
import pytest

import alluka
from alluka._vendor import inspect


class MockType(int): ...


class MockOtherType(int): ...


@pytest.fixture
def client() -> alluka.Client:
    return alluka.Client()


@pytest.fixture
def context(client: alluka.Client) -> alluka.Context:
    return alluka.Context(client)


################################################
# Sync dependency injection future annotations #
################################################


# TODO: test cases for type scoped dependencies
# TODO: test cases for cached callback results
def test_call_with_di_when_no_di(context: alluka.Context):
    def callback(value_1: int, value_2: str) -> str:
        assert value_1 == 42
        assert value_2 == "ok"
        return "nyaa"

    result = context.call_with_di(callback, 42, value_2="ok")

    assert result == "nyaa"


def test_call_with_async_di_with_missing_annotations(context: alluka.Context):
    def callback(value_1, value_2) -> str:  # type: ignore
        assert value_1 == 543123
        assert value_2 == "sdasd"
        return "meow"

    result = context.call_with_di(callback, 543123, value_2="sdasd")  # type: ignore

    assert result == "meow"


def test_call_with_di_prioritises_defaults_over_annotations(context: alluka.Context):
    mock_value = mock.Mock()
    mock_other_value = mock.Mock()
    mock_callback = mock.Mock()

    def dependency(
        result: typing.Annotated[float, alluka.inject(type=123)] = alluka.inject(callback=mock_callback)
    ) -> str:
        assert result is mock_callback.return_value
        return "sexual catgirls"

    def callback(
        value_1: int,
        value_2: str,
        value_3: alluka.Injected[str] = alluka.inject(type=MockType),
        value_4: typing.Annotated[int, alluka.inject(type=float)] = alluka.inject(type=MockOtherType),
        value_5: typing.Annotated[str, alluka.inject(callback=mock.Mock)] = alluka.inject(callback=dependency),
    ) -> str:
        assert value_1 == 69
        assert value_2 == "rew"
        assert value_3 is mock_value
        assert value_4 is mock_other_value
        assert value_5 == "sexual catgirls"
        return "meow"

    context.injection_client.set_type_dependency(MockType, mock_value).set_type_dependency(
        MockOtherType, mock_other_value
    )

    result = context.call_with_di(callback, 69, value_2="rew")

    assert result == "meow"
    mock_callback.assert_called_once_with()


def test_call_with_di_with_type_dependency_and_callback(context: alluka.Context):
    mock_value = mock.Mock()
    mock_other_value = mock.Mock()
    mock_callback = mock.Mock()

    def callback(
        value_1: int,
        value_2: str,
        value_3: str = alluka.inject(type=MockType),
        value_4: int = alluka.inject(type=MockOtherType),
        value_5: typing.Any = alluka.inject(callback=mock_callback),
    ) -> str:
        assert value_1 == 69
        assert value_2 == "rew"
        assert value_3 is mock_value
        assert value_4 is mock_other_value
        assert value_5 is mock_callback.return_value
        return "meow"

    context.injection_client.set_type_dependency(MockType, mock_value).set_type_dependency(
        MockOtherType, mock_other_value
    )

    result = context.call_with_di(callback, 69, value_2="rew")

    assert result == "meow"
    mock_callback.assert_called_once_with()


def test_call_with_di_with_type_dependency(context: alluka.Context):
    mock_value = mock.Mock()
    mock_other_value = mock.Mock()

    def callback(
        value_1: int,
        value_2: str,
        value_3: str = alluka.inject(type=MockType),
        value_4: int = alluka.inject(type=MockOtherType),
    ) -> str:
        assert value_1 == 69
        assert value_2 == "rew"
        assert value_3 is mock_value
        assert value_4 is mock_other_value
        return "meow"

    context.injection_client.set_type_dependency(MockType, mock_value).set_type_dependency(
        MockOtherType, mock_other_value
    )

    result = context.call_with_di(callback, 69, value_2="rew")

    assert result == "meow"


def test_call_with_di_with_type_dependency_inferred_from_type(context: alluka.Context):
    mock_value = MockType()
    mock_other_value = MockOtherType()

    def callback(
        nyaa: str, meow: int, value_1: MockType = alluka.inject(), value_2: MockOtherType = alluka.inject()
    ) -> str:
        assert nyaa == "5412"
        assert meow == 34123
        assert value_1 is mock_value
        assert value_2 is mock_other_value
        return "heeee"

    context.injection_client.set_type_dependency(MockType, mock_value).set_type_dependency(
        MockOtherType, mock_other_value
    )

    result = context.call_with_di(callback, "5412", meow=34123)

    assert result == "heeee"


def test_call_with_di_with_type_dependency_inferred_from_annotated_type(context: alluka.Context):
    mock_value = MockType()
    mock_other_value = MockOtherType()

    def callback(
        nyaa: str,
        meow: int,
        value_1: typing.Annotated[MockType, ..., int] = alluka.inject(),
        value_2: typing.Annotated[MockOtherType, int, str] = alluka.inject(),
    ) -> str:
        assert nyaa == "5412"
        assert meow == 34123
        assert value_1 is mock_value
        assert value_2 is mock_other_value
        return "heeee"

    context.injection_client.set_type_dependency(MockType, mock_value).set_type_dependency(
        MockOtherType, mock_other_value
    )

    result = context.call_with_di(callback, "5412", meow=34123)

    assert result == "heeee"


@pytest.mark.anyio
def test_call_with_di_with_type_dependency_inferred_from_missing_type(context: alluka.Context):
    def callback(nyaa: str, meow: int, _: MockType = alluka.inject(), value_1=alluka.inject()) -> str:  # type: ignore
        raise NotImplementedError

    with pytest.raises(ValueError, match="Could not resolve type for parameter 'value_1' with no annotation"):
        context.call_with_di(callback, "5412", meow=34123)


def test_call_with_di_with_type_dependency_not_found(context: alluka.Context):
    mock_value = mock.Mock()

    def callback(
        _: int, value_1: str, __: str = alluka.inject(type=MockType), ___: int = alluka.inject(type=MockOtherType)
    ) -> str:
        raise NotImplementedError

    context.injection_client.set_type_dependency(MockType, mock_value)

    with pytest.raises(alluka.MissingDependencyError) as exc:
        context.call_with_di(callback, 69, value_1="rew")

    assert exc.value.message == f"Couldn't resolve injected type(s) {MockOtherType} to actual value"
    assert exc.value.dependency_type is MockOtherType


def test_call_with_di_with_defaulting_type_dependency(context: alluka.Context):  # TODO: THIS
    mock_value = mock.Mock()

    def callback(
        value_1: int, value_2: str, value_3: typing.Optional[int] = alluka.inject(type=typing.Optional[MockType])
    ) -> str:
        assert value_1 == 69
        assert value_2 == "rew"
        assert value_3 is mock_value
        return "meow"

    context.injection_client.set_type_dependency(MockType, mock_value)

    result = context.call_with_di(callback, 69, value_2="rew")

    assert result == "meow"


def test_call_with_di_with_defaulting_type_dependency_not_found(context: alluka.Context):
    def callback(
        yeet: int, raw: str, value_1: typing.Optional[int] = alluka.inject(type=typing.Optional[MockType])
    ) -> str:
        assert yeet == 420
        assert raw == "uwu"
        assert value_1 is None
        return "yeet"

    result = context.call_with_di(callback, 420, raw="uwu")

    assert result == "yeet"


# These tests covers syntax which was introduced in 3.10
if sys.version_info >= (3, 10):  # TODO: do we want to dupe other test cases for |?

    def test_call_with_di_with_3_10_union_type_dependency(context: alluka.Context):
        mock_value = MockType()

        context.injection_client.set_type_dependency(MockType, mock_value)

        def callback(value_1: int, value_2: str, cope: int = alluka.inject(type=MockOtherType | MockType)) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is mock_value
            return 451.123

        result = context.call_with_di(callback, 123, "ok")

        assert result == 451.123

    def test_call_with_di_with_3_10_union_type_dependency_not_found(context: alluka.Context):
        def callback(_: int, __: str, cope: int = alluka.inject(type=MockOtherType | MockType)) -> float:
            raise NotImplementedError

        with pytest.raises(alluka.MissingDependencyError) as exc_info:
            context.call_with_di(callback, 123, "ok")

        assert exc_info.value.dependency_type == MockOtherType | MockType
        # 3.10.1/2+ and 3.11 may re-order the | union types while resolving them from a string
        # future annotation so we can't reliably assert these.

    def test_call_with_di_with_3_10_union_type_dependency_defaulting(context: alluka.Context):
        mock_value = MockType()

        context.injection_client.set_type_dependency(MockType, mock_value)

        def callback(
            value_1: int, value_2: str, cope: int = alluka.inject(type=MockOtherType | MockType | None)
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is mock_value
            return 451.123

        result = context.call_with_di(callback, 123, "ok")

        assert result == 451.123

    def test_call_with_di_with_3_10_union_type_dependency_defaulting_not_found(context: alluka.Context):
        def callback(
            value_1: int, value_2: str, cope: int = alluka.inject(type=MockOtherType | MockType | None)
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is None
            return 451.123

        result = context.call_with_di(callback, 123, "ok")

        assert result == 451.123


def test_call_with_di_with_union_type_dependency(context: alluka.Context):
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(MockOtherType, mock_value)

    def callback(
        value_1: int, value_2: str, cope: int = alluka.inject(type=typing.Union[MockType, MockOtherType])
    ) -> float:
        assert value_1 == 123
        assert value_2 == "ok"
        assert cope is mock_value
        return 243.234

    result = context.call_with_di(callback, 123, "ok")

    assert result == 243.234


def test_call_with_di_with_union_type_dependency_not_found(context: alluka.Context):
    def callback(_: int, __: str, cope: int = alluka.inject(type=typing.Union[MockType, MockOtherType])) -> float:
        raise NotImplementedError

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        context.call_with_di(callback, 123, "ok")

    assert exc_info.value.dependency_type == typing.Union[MockType, MockOtherType]
    # On 3.10.1/2+ typing.Unions are converted to | while resolving future annotations so we can't consistently
    # assert the message.


def test_call_with_di_with_defaulting_union_type_dependency(context: alluka.Context):
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(MockOtherType, mock_value)

    def callback(
        value_1: int, value_2: str, cope: int = alluka.inject(type=typing.Union[MockType, MockOtherType, None])
    ) -> float:
        assert value_1 == 123
        assert value_2 == "ok"
        assert cope is mock_value
        return 243.234

    result = context.call_with_di(callback, 123, "ok")

    assert result == 243.234


def test_call_with_di_with_defaulting_union_type_dependency_not_found(context: alluka.Context):
    def callback(
        value_1: float, value_2: int, cope: typing.Optional[int] = alluka.inject(type=typing.Optional[MockType])
    ) -> float:
        assert value_1 == 123.321
        assert value_2 == 543
        assert cope is None
        return 321.123

    result = context.call_with_di(callback, 123.321, 543)

    assert result == 321.123


def test_call_with_di_with_annotated_type_dependency(context: alluka.Context):
    mock_value = MockType
    mock_other_value = MockOtherType

    def callback(
        rawr: int,
        xd: float,
        meowmeow: typing.Annotated[str, alluka.inject(type=MockType)],
        imacow: typing.Annotated[int, alluka.inject(type=MockOtherType)],
    ) -> str:
        assert rawr == 69
        assert xd == "rew"
        assert meowmeow is mock_value
        assert imacow is mock_other_value
        return "meow"

    context.injection_client.set_type_dependency(MockType, mock_value).set_type_dependency(
        MockOtherType, mock_other_value
    )

    result = context.call_with_di(callback, rawr=69, xd="rew")

    assert result == "meow"


def test_call_with_di_with_annotated_type_dependency_inferred_from_type(context: alluka.Context):
    mock_value = MockType()
    mock_other_value = MockOtherType()

    def callback(
        meow: int,
        nyaa: float,
        meowmeow: typing.Annotated[MockType, alluka.inject()],
        imacow: typing.Annotated[MockOtherType, alluka.inject()],
    ) -> str:
        assert meow == 2222
        assert nyaa == "xxxxx"
        assert meowmeow is mock_value
        assert imacow is mock_other_value
        return "wewewewew"

    context.injection_client.set_type_dependency(MockType, mock_value).set_type_dependency(
        MockOtherType, mock_other_value
    )

    result = context.call_with_di(callback, meow=2222, nyaa="xxxxx")

    assert result == "wewewewew"


def test_call_with_di_with_annotated_type_dependency_not_found(context: alluka.Context):
    mock_other_value = MockOtherType()

    def callback(
        meow: int,
        nyaa: float,
        meowmeow: typing.Annotated[int, alluka.inject(type=MockType)],
        imacow: typing.Annotated[str, alluka.inject(type=MockOtherType)],
    ) -> str:
        raise NotImplementedError

    context.injection_client.set_type_dependency(MockOtherType, mock_other_value)

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        context.call_with_di(callback, meow=2222, nyaa="xxxxx")

    assert exc_info.value.dependency_type is MockType
    assert exc_info.value.message == f"Couldn't resolve injected type(s) {MockType} to actual value"


# These tests covers syntax which was introduced in 3.10
if sys.version_info >= (3, 10):  # TODO: do we want to dupe other test cases for |?

    def test_call_with_di_with_annotated_3_10_union_type_dependency(context: alluka.Context):
        mock_value = MockType()

        def callback(
            yeee: str, nyaa: bool, yeet: typing.Annotated[str, alluka.inject(type=MockType | MockOtherType)]
        ) -> str:
            assert yeee == "yeee"
            assert nyaa is True
            assert yeet is mock_value
            return "hey"

        context.injection_client.set_type_dependency(MockOtherType, mock_value)

        result = context.call_with_di(callback, yeee="yeee", nyaa=True)

        assert result == "hey"

    def test_call_with_di_with_annotated_3_10_union_type_dependency_not_found(context: alluka.Context):
        def callback(
            _: int, __: str, cope: typing.Annotated[int, alluka.inject(type=MockOtherType | MockType)]
        ) -> float:
            raise NotImplementedError

        with pytest.raises(alluka.MissingDependencyError) as exc_info:
            context.call_with_di(callback, 123, "ok")

        assert exc_info.value.dependency_type == MockOtherType | MockType
        # 3.10.1/2+ and 3.11 may re-order the | union types while resolving them from a string
        # future annotation so we can't reliably assert these.

    def test_call_with_di_with_annotated_3_10_union_type_dependency_defaulting(context: alluka.Context):
        mock_value = MockType()

        context.injection_client.set_type_dependency(MockType, mock_value)

        def callback(
            value_1: int, value_2: str, cope: typing.Annotated[int, alluka.inject(type=MockOtherType | MockType | None)]
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is mock_value
            return 451.123

        result = context.call_with_di(callback, 123, "ok")

        assert result == 451.123

    def test_call_with_di_with_annotated_3_10_union_type_dependency_defaulting_not_found(context: alluka.Context):
        def callback(
            value_1: int, value_2: str, cope: typing.Annotated[int, alluka.inject(type=MockOtherType | MockType | None)]
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is None
            return 451.123

        result = context.call_with_di(callback, 123, "ok")

        assert result == 451.123

    def test_call_with_di_with_annotated_3_10_union_type_dependency_natural_defaulting(context: alluka.Context):
        mock_value = MockType()

        context.injection_client.set_type_dependency(MockType, mock_value)

        def callback(
            value_1: int,
            value_2: str,
            cope: typing.Annotated[int, alluka.inject(type=MockOtherType | MockType | None)] = 123,
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is mock_value
            return 451.123

        result = context.call_with_di(callback, 123, "ok")

        assert result == 451.123

    def test_call_with_di_with_annotated_3_10_union_type_dependency_natural_defaulting_not_found(
        context: alluka.Context,
    ):
        def callback(
            value_1: int,
            value_2: str,
            cope: typing.Annotated[int, alluka.inject(type=MockOtherType | MockType)] = 43123,
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope == 43123
            return 451.123

        result = context.call_with_di(callback, 123, "ok")

        assert result == 451.123


def test_call_with_di_with_annotated_union_type_dependency(context: alluka.Context):
    mock_value = MockOtherType()

    def callback(meow: int, meowmeow: typing.Annotated[typing.Union[MockType, MockOtherType], alluka.inject()]) -> str:
        assert meow == 1233212
        assert meowmeow is mock_value
        return "yay"

    context.injection_client.set_type_dependency(MockOtherType, mock_value)

    result = context.call_with_di(callback, 1233212)

    assert result == "yay"


def test_call_with_di_with_annotated_union_type_dependency_not_found(context: alluka.Context):
    def callback(
        yeee: str, nyaa: bool, yeet: typing.Annotated[int, alluka.inject(type=typing.Union[MockType, MockOtherType])]
    ) -> str:
        raise NotImplementedError

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        context.call_with_di(callback, yeee="yeee", nyaa=True)

    assert exc_info.value.dependency_type == typing.Union[MockType, MockOtherType]
    # On 3.10.1/2+ typing.Unions are converted to | while resolving future annotations so we can't consistently
    # assert the message.


def test_call_with_di_with_annotated_defaulting_type_dependency(context: alluka.Context):
    mock_value = MockType()
    context.injection_client.set_type_dependency(MockType, mock_value)

    def callback(
        eaaaa: str, nyaa: bool, yeet: typing.Annotated[str, alluka.inject(type=typing.Optional[MockType])]
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_value
        return "aaaaa"

    result = context.call_with_di(callback, "easd", nyaa=False)

    assert result == "aaaaa"


def test_call_with_di_with_annotated_defaulting_type_dependency_not_found(context: alluka.Context):
    def callback(
        eaaaa: str, nyaa: bool, yeet: typing.Annotated[str, alluka.inject(type=typing.Optional[MockType])]
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is None
        return "aaaaa"

    result = context.call_with_di(callback, "easd", nyaa=False)

    assert result == "aaaaa"


def test_call_with_di_with_annotated_natural_defaulting_type_dependency(context: alluka.Context):
    mock_value = MockType()
    context.injection_client.set_type_dependency(MockType, mock_value)

    def callback(eaaaa: str, nyaa: bool, yeet: typing.Annotated[str, alluka.inject(type=MockType)] = "default") -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_value
        return "aaaaa"

    result = context.call_with_di(callback, "easd", nyaa=False)

    assert result == "aaaaa"


def test_call_with_di_with_annotated_natural_defaulting_type_dependency_not_found(context: alluka.Context):
    def callback(eaaaa: str, nyaa: bool, yeet: typing.Annotated[int, alluka.inject(type=MockType)] = 123) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet == 123
        return "aaaaa"

    result = context.call_with_di(callback, "easd", nyaa=False)

    assert result == "aaaaa"


def test_call_with_di_with_annotated_defaulting_union_type_dependency(context: alluka.Context):
    mock_value = MockOtherType()
    context.injection_client.set_type_dependency(MockOtherType, mock_value)

    def callback(
        vvvvv: int, value: typing.Annotated[str, alluka.inject(type=typing.Union[MockType, MockOtherType])]
    ) -> str:
        assert vvvvv == 123
        assert value is mock_value
        return "ea sports"

    result = context.call_with_di(callback, 123)

    assert result == "ea sports"


def test_call_with_di_with_annotated_defaulting_union_type_dependency_not_found(context: alluka.Context):
    def callback(vvvvv: int, value: typing.Annotated[str, alluka.inject(type=typing.Optional[MockType])]) -> str:
        assert vvvvv == 123
        assert value is None
        return "yeeee"

    result = context.call_with_di(callback, 123)

    assert result == "yeeee"


def test_call_with_di_with_annotated_natural_defaulting_union_type_dependency(context: alluka.Context):
    mock_value = MockOtherType()
    context.injection_client.set_type_dependency(MockOtherType, mock_value)

    def callback(
        vvvvv: int, value: typing.Annotated[str, alluka.inject(type=typing.Union[MockType, MockOtherType])] = "default"
    ) -> str:
        assert vvvvv == 123
        assert value is mock_value
        return "ea sports"

    result = context.call_with_di(callback, 123)

    assert result == "ea sports"


def test_call_with_di_with_annotated_natural_defaulting_union_type_dependency_not_found(context: alluka.Context):
    def callback(
        vvvvv: int,
        value: typing.Annotated[str, alluka.inject(type=typing.Union[MockType, MockOtherType, None])] = "default 2",
    ) -> str:
        assert vvvvv == 123
        assert value == "default 2"
        return "yeeee"

    result = context.call_with_di(callback, 123)

    assert result == "yeeee"


def test_call_with_di_with_shorthand_annotated_type_dependency(context: alluka.Context):
    mock_value = MockType()
    mock_other_value = MockOtherType()

    def callback(
        rawr: int, xd: float, meowmeow: alluka.Injected[MockType], other: alluka.Injected[MockOtherType]
    ) -> str:
        assert rawr == 1233212
        assert xd == "seee"
        assert meowmeow is mock_value
        assert other is mock_other_value
        return "eeesss"

    context.injection_client.set_type_dependency(MockType, mock_value).set_type_dependency(
        MockOtherType, mock_other_value
    )

    result = context.call_with_di(callback, 1233212, xd="seee")

    assert result == "eeesss"


def test_call_with_di_with_shorthand_annotated_type_dependency_not_found(context: alluka.Context):
    mock_other_value = MockOtherType()

    def callback(
        meow: int, nyaa: float, meowmeow: alluka.Injected[MockType], imacow: alluka.Injected[MockOtherType]
    ) -> str:
        raise NotImplementedError

    context.injection_client.set_type_dependency(MockOtherType, mock_other_value)

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        context.call_with_di(callback, meow=2222, nyaa="xxxxx")

    assert exc_info.value.dependency_type is MockType
    assert exc_info.value.message == f"Couldn't resolve injected type(s) {MockType} to actual value"


# These tests covers syntax which was introduced in 3.10
if sys.version_info >= (3, 10):  # TODO: do we want to dupe other test cases for |?

    def test_call_with_di_with_shorthand_annotated_3_10_union_type_dependency(context: alluka.Context):
        mock_value = MockOtherType()

        def callback(yeee: str, nyaa: bool, yeet: alluka.Injected[MockType | MockOtherType]) -> str:
            assert yeee == "yeee"
            assert nyaa is True
            assert yeet is mock_value
            return "hey"

        context.injection_client.set_type_dependency(MockType, mock_value)

        result = context.call_with_di(callback, yeee="yeee", nyaa=True)

        assert result == "hey"

    def test_call_with_di_with_shorthand_annotated_3_10_union_type_dependency_not_found(context: alluka.Context):
        def callback(_: int, __: str, cope: alluka.Injected[MockOtherType | MockType]) -> float:
            raise NotImplementedError

        with pytest.raises(alluka.MissingDependencyError) as exc_info:
            context.call_with_di(callback, 123, "ok")

        assert exc_info.value.dependency_type == MockOtherType | MockType
        # 3.10.1/2+ and 3.11 may re-order the | union types while resolving them from a string
        # future annotation so we can't reliably assert these.

    def test_call_with_di_with_shorthand_annotated_3_10_union_type_dependency_defaulting(context: alluka.Context):
        mock_value = MockType()

        context.injection_client.set_type_dependency(MockType, mock_value)

        def callback(value_1: int, value_2: str, cope: alluka.Injected[MockOtherType | MockType | None]) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is mock_value
            return 451.123

        result = context.call_with_di(callback, 123, "ok")

        assert result == 451.123

    def test_call_with_di_with_shorthand_annotated_3_10_union_type_dependency_defaulting_not_found(
        context: alluka.Context,
    ):
        def callback(value_1: int, value_2: str, cope: alluka.Injected[MockOtherType | MockType | None]) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is None
            return 451.123

        result = context.call_with_di(callback, 123, "ok")

        assert result == 451.123

    def test_call_with_di_with_shorthand_annotated_3_10_union_type_dependency_natural_defaulting(
        context: alluka.Context,
    ):
        mock_value = MockType()

        context.injection_client.set_type_dependency(MockType, mock_value)

        def callback(
            value_1: int, value_2: str, cope: alluka.Injected[MockOtherType | MockType | None] = MockOtherType()
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is mock_value
            return 451.123

        result = context.call_with_di(callback, 123, "ok")

        assert result == 451.123

    def test_call_with_di_with_shorthand_annotated_3_10_union_type_dependency_natural_defaulting_not_found(
        context: alluka.Context,
    ):
        mock_default = mock.Mock()

        def callback(
            value_1: int, value_2: str, cope: alluka.Injected[MockOtherType | MockType] = mock_default
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is mock_default
            return 451.123

        result = context.call_with_di(callback, 123, "ok")

        assert result == 451.123


def test_call_with_di_with_shorthand_annotated_union_type_dependency(context: alluka.Context):
    mock_value = MockOtherType()

    def callback(meow: int, meowmeow: alluka.Injected[typing.Union[MockType, MockOtherType]]) -> str:
        assert meow == 1233212
        assert meowmeow is mock_value
        return "yay"

    context.injection_client.set_type_dependency(MockOtherType, mock_value)

    result = context.call_with_di(callback, 1233212)

    assert result == "yay"


def test_call_with_di_with_shorthand_annotated_union_type_dependency_not_found(context: alluka.Context):
    def callback(yeee: str, nyaa: bool, yeet: alluka.Injected[typing.Union[MockType, MockOtherType]]) -> str:
        raise NotImplementedError

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        context.call_with_di(callback, yeee="yeee", nyaa=True)

    assert exc_info.value.dependency_type == typing.Union[MockType, MockOtherType]
    # On 3.10.1/2+ typing.Unions are converted to | while resolving future annotations so we can't consistently
    # assert the message.


def test_call_with_di_with_shorthand_annotated_defaulting_type_dependency(context: alluka.Context):
    mock_value = MockType()
    context.injection_client.set_type_dependency(MockType, mock_value)

    def callback(eaaaa: str, nyaa: bool, yeet: alluka.Injected[typing.Optional[MockType]]) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_value
        return "aaaaa"

    result = context.call_with_di(callback, "easd", nyaa=False)

    assert result == "aaaaa"


def test_call_with_di_with_shorthand_annotated_defaulting_type_dependency_not_found(context: alluka.Context):
    def callback(eaaaa: str, nyaa: bool, yeet: alluka.Injected[typing.Optional[MockType]]) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is None
        return "aaaaa"

    result = context.call_with_di(callback, "easd", nyaa=False)

    assert result == "aaaaa"


def test_call_with_di_with_shorthand_annotated_natural_defaulting_type_dependency(context: alluka.Context):
    mock_value = MockType()
    context.injection_client.set_type_dependency(MockType, mock_value)

    def callback(eaaaa: str, nyaa: bool, yeet: alluka.Injected[MockType] = MockType()) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_value
        return "aaaaa"

    result = context.call_with_di(callback, "easd", nyaa=False)

    assert result == "aaaaa"


def test_call_with_di_with_shorthand_annotated_natural_defaulting_type_dependency_not_found(context: alluka.Context):
    mock_default = MockType()

    def callback(eaaaa: str, nyaa: bool, yeet: alluka.Injected[MockType] = mock_default) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_default
        return "aaaaa"

    result = context.call_with_di(callback, "easd", nyaa=False)

    assert result == "aaaaa"


def test_call_with_di_with_shorthand_annotated_defaulting_union_type_dependency(context: alluka.Context):
    mock_value = MockOtherType()
    context.injection_client.set_type_dependency(MockOtherType, mock_value)

    def callback(vvvvv: int, value: alluka.Injected[typing.Union[MockType, MockOtherType]]) -> str:
        assert vvvvv == 123
        assert value is mock_value
        return "ea sports"

    result = context.call_with_di(callback, 123)

    assert result == "ea sports"


def test_call_with_di_with_shorthand_annotated_defaulting_union_type_dependency_not_found(context: alluka.Context):
    def callback(vvvvv: int, value: alluka.Injected[typing.Optional[MockType]]) -> str:
        assert vvvvv == 123
        assert value is None
        return "yeeee"

    result = context.call_with_di(callback, 123)

    assert result == "yeeee"


def test_call_with_di_with_shorthand_annotated_natural_defaulting_union_type_dependency(context: alluka.Context):
    mock_value = MockOtherType()
    context.injection_client.set_type_dependency(MockOtherType, mock_value)

    def callback(vvvvv: int, value: alluka.Injected[typing.Union[MockType, MockOtherType]] = MockType()) -> str:
        assert vvvvv == 123
        assert value is mock_value
        return "ea sports"

    result = context.call_with_di(callback, 123)

    assert result == "ea sports"


def test_call_with_di_with_shorthand_annotated_natural_defaulting_union_type_dependency_not_found(
    context: alluka.Context,
):
    mock_default = MockType()

    def callback(vvvvv: int, value: alluka.Injected[typing.Union[MockType, MockOtherType, None]] = mock_default) -> str:
        assert vvvvv == 123
        assert value is mock_default
        return "yeeee"

    result = context.call_with_di(callback, 123)

    assert result == "yeeee"


def test_call_with_di_with_callback_dependency(context: alluka.Context):
    mock_callback = mock.Mock()

    def callback(value_1: int, result: int = alluka.inject(callback=mock_callback)) -> int:
        assert value_1 == 123
        assert result is mock_callback.return_value
        return 43123

    result = context.call_with_di(callback, 123)

    assert result == 43123


def test_call_with_di_with_sub_callback_dependency(context: alluka.Context):
    mock_callback = mock.Mock()

    def dependency(result: int = alluka.inject(callback=mock_callback)) -> int:
        assert result is mock_callback.return_value
        return 541232

    def callback(value_1: int, result: int = alluka.inject(callback=dependency)) -> str:
        assert value_1 == 123
        assert result == 541232
        return "43123"

    result = context.call_with_di(callback, 123)

    assert result == "43123"


def test_call_with_di_with_annotated_callback_dependency(context: alluka.Context):
    global mock_callback
    mock_callback = mock.Mock()

    def callback(value_1: int, result: typing.Annotated[int, alluka.inject(callback=mock_callback)]) -> int:
        assert value_1 == 123
        assert result is mock_callback.return_value
        return 43123

    result = context.call_with_di(callback, 123)

    assert result == 43123
    mock_callback.assert_called_once_with()


def test_call_with_di_with_annotated_sub_callback_dependency(context: alluka.Context):
    global mock_callback
    global dependency_1
    mock_callback = mock.Mock()

    def dependency_1(result: typing.Annotated[int, alluka.inject(callback=mock_callback)]) -> int:
        assert result is mock_callback.return_value
        return 541232

    def callback(value_1: int, result: typing.Annotated[int, alluka.inject(callback=dependency_1)]) -> str:
        assert value_1 == 123
        assert result == 541232
        return "43123"

    result = context.call_with_di(callback, 123)

    assert result == "43123"


def test_call_with_di_with_sub_type_dependency(context: alluka.Context):
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(MockType, mock_value)

    def dependency(result: int = alluka.inject(type=MockType)) -> int:
        assert result is mock_value
        return 123321

    def callback(value_1: int, result: int = alluka.inject(callback=dependency)) -> str:
        assert value_1 == 54123
        assert result == 123321
        return "asddsa"

    result = context.call_with_di(callback, 54123)

    assert result == "asddsa"


def test_call_with_di_with_sub_type_dependency_not_found(context: alluka.Context):
    global dependency

    def dependency_2(result: typing.Annotated[int, alluka.inject(type=MockType)]) -> int:
        raise NotImplementedError

    def callback(_: int, result: int = alluka.inject(callback=dependency_2)) -> str:
        raise NotImplementedError

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        context.call_with_di(callback, 54123)

    assert exc_info.value.dependency_type is MockType
    assert exc_info.value.message == (f"Couldn't resolve injected type(s) {MockType} to actual value")


def test_call_with_di_when_async_callback(context: alluka.Context):
    async def callback() -> None:
        raise NotImplementedError

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        with pytest.raises(alluka.SyncOnlyError):
            context.call_with_di(callback)


def test_call_with_di_with_async_dependency(context: alluka.Context):
    async def async_dependency() -> None:
        raise NotImplementedError

    def callback(result: None = alluka.inject(callback=async_dependency)) -> None:
        raise NotImplementedError

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        with pytest.raises(alluka.SyncOnlyError):
            context.call_with_di(callback)


def test_call_with_di_with_overridden_async_dependency(context: alluka.Context):
    async def override() -> None:
        raise NotImplementedError

    def dependency() -> None:
        raise NotImplementedError

    def callback(result: None = alluka.inject(callback=dependency)) -> None:
        raise NotImplementedError

    context.injection_client.set_callback_override(dependency, override)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        with pytest.raises(alluka.SyncOnlyError):
            context.call_with_di(callback)


def test_call_with_di_with_sub_async_dependency(context: alluka.Context):
    async def async_sub_dependency() -> None:
        raise NotImplementedError

    def dependency(_: None = alluka.inject(callback=async_sub_dependency)) -> None:
        raise NotImplementedError

    def callback(result: None = alluka.inject(callback=dependency)) -> None:
        raise NotImplementedError

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        with pytest.raises(alluka.SyncOnlyError):
            context.call_with_di(callback)


def test_call_with_di_with_overridden_sub_async_dependency(context: alluka.Context):
    async def override() -> None:
        raise NotImplementedError

    def sub_dependency() -> None:
        raise NotImplementedError

    def dependency(result: None = alluka.inject(callback=sub_dependency)) -> None:
        raise NotImplementedError

    def callback(result: None = alluka.inject(callback=dependency)) -> None:
        raise NotImplementedError

    context.injection_client.set_callback_override(sub_dependency, override)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        with pytest.raises(alluka.SyncOnlyError):
            context.call_with_di(callback)


def test_call_with_di_with_annotated_async_dependency(context: alluka.Context):
    global async_dependency

    async def async_dependency() -> None:
        raise NotImplementedError

    def callback(result: typing.Annotated[None, alluka.inject(callback=async_dependency)]) -> None:
        raise NotImplementedError

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        with pytest.raises(alluka.SyncOnlyError):
            context.call_with_di(callback)


def test_call_with_di_with_overridden_annotated_async_dependency(context: alluka.Context):
    async def override() -> None:
        raise NotImplementedError

    def dependency() -> None:
        raise NotImplementedError

    def callback(result: None = alluka.inject(callback=dependency)) -> None:
        raise NotImplementedError

    context.injection_client.set_callback_override(dependency, override)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        with pytest.raises(alluka.SyncOnlyError):
            context.call_with_di(callback)


def test_call_with_di_with_annotated_sub_async_dependency(context: alluka.Context):
    global async_sub_dependency
    global dependency_3

    async def async_sub_dependency() -> None:
        raise NotImplementedError

    def dependency_3(_: typing.Annotated[None, alluka.inject(callback=async_sub_dependency)]) -> None:
        raise NotImplementedError

    def callback(result: typing.Annotated[None, alluka.inject(callback=dependency_3)]) -> None:
        raise NotImplementedError

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        with pytest.raises(alluka.SyncOnlyError):
            context.call_with_di(callback)


def test_call_with_di_with_overridden_annotated_sub_async_dependency(context: alluka.Context):
    global sub_dependency
    global dependency

    async def override() -> None:
        raise NotImplementedError

    def sub_dependency() -> None:
        raise NotImplementedError

    def dependency(result: typing.Annotated[None, alluka.inject(callback=sub_dependency)]) -> None:
        raise NotImplementedError

    def callback(result: typing.Annotated[None, alluka.inject(callback=dependency)]) -> None:
        raise NotImplementedError

    context.injection_client.set_callback_override(sub_dependency, override)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        with pytest.raises(alluka.SyncOnlyError):
            context.call_with_di(callback)


################################
# Positional-only dependencies #
################################


def test_call_with_di_with_positional_only_type_dependency(context: alluka.Context):
    def callback(_: int, __: str = alluka.inject(type=float), /, ___: float = alluka.inject(type=float)) -> None:
        raise NotImplementedError

    with pytest.raises(ValueError, match="Injected positional only arguments are not supported"):
        context.call_with_di(callback)


def test_call_with_di_with_positional_only_callback_dependency(context: alluka.Context):
    mock_dependency = mock.Mock()

    def callback(
        _: int, __: str = alluka.inject(callback=mock_dependency), /, ___: float = alluka.inject(type=float)
    ) -> None:
        raise NotImplementedError

    with pytest.raises(ValueError, match="Injected positional only arguments are not supported"):
        context.call_with_di(callback)


def test_call_with_di_with_sub_positional_only_callback_dependency(context: alluka.Context):
    sub_dependency = mock.Mock()

    def dependency(_: str = alluka.inject(callback=sub_dependency), /) -> str:
        raise NotImplementedError

    def callback(
        _: int, __: str = alluka.inject(callback=dependency), /, ___: float = alluka.inject(type=float)
    ) -> None:
        raise NotImplementedError

    with pytest.raises(ValueError, match="Injected positional only arguments are not supported"):
        context.call_with_di(callback)


def test_call_with_di_with_sub_positional_only_type_dependency(context: alluka.Context):
    def dependency(_: str = alluka.inject(type=int), /) -> str:
        raise NotImplementedError

    def callback(
        _: int, __: str = alluka.inject(callback=dependency), /, ___: float = alluka.inject(type=float)
    ) -> None:
        raise NotImplementedError

    with pytest.raises(ValueError, match="Injected positional only arguments are not supported"):
        context.call_with_di(callback)


############################
# Signature-less callbacks #
############################


def test_call_with_di_with_signature_less_callback(context: alluka.Context):
    with pytest.raises(ValueError, match="no signature found for builtin type <class 'str'>"):
        inspect.signature(str)

    result = context.call_with_di(str, b"ok")

    assert result == "b'ok'"


def test_call_with_di_with_signature_less_callback_dependency(context: alluka.Context):
    with pytest.raises(ValueError, match="no signature found for builtin type <class 'int'>"):
        inspect.signature(int)

    def callback(value: int = alluka.inject(callback=int)) -> int:
        assert value == 0
        return 222

    result = context.call_with_di(callback)

    assert result == 222

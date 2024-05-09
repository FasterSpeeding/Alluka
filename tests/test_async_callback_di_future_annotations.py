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


#################################################
# Async dependency injection future annotations #
#################################################


# TODO: test cases for type scoped dependencies
# TODO: test cases for cached callback results
@pytest.mark.anyio
async def test_call_with_async_di_when_no_di(context: alluka.Context):
    async def callback(value_1: int, value_2: str) -> str:
        assert value_1 == 42
        assert value_2 == "ok"
        return "nyaa"

    result = await context.call_with_async_di(callback, 42, value_2="ok")

    assert result == "nyaa"


@pytest.mark.anyio
async def test_call_with_async_di_with_missing_annotations(context: alluka.Context):
    async def callback(value_1, value_2) -> str:  # type: ignore
        assert value_1 == 543123
        assert value_2 == "sdasd"
        return "meow"

    result = await context.call_with_async_di(callback, 543123, value_2="sdasd")  # type: ignore

    assert result == "meow"


@pytest.mark.anyio
async def test_call_with_async_di_prioritises_defaults_over_annotations(context: alluka.Context):
    mock_value = mock.Mock()
    mock_other_value = mock.Mock()
    mock_callback = mock.AsyncMock()

    async def dependency(
        result: typing.Annotated[float, alluka.inject(type=123)] = alluka.inject(callback=mock_callback)
    ) -> str:
        assert result is mock_callback.return_value
        return "sexual catgirls"

    async def callback(
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

    result = await context.call_with_async_di(callback, 69, value_2="rew")

    assert result == "meow"
    mock_callback.assert_awaited_once_with()


@pytest.mark.anyio
async def test_call_with_async_di_with_type_dependency_and_callback(context: alluka.Context):
    mock_value = mock.Mock()
    mock_other_value = mock.Mock()
    mock_callback = mock.AsyncMock()

    async def callback(
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

    result = await context.call_with_async_di(callback, 69, value_2="rew")

    assert result == "meow"
    mock_callback.assert_awaited_once_with()


@pytest.mark.anyio
async def test_call_with_async_di_with_type_dependency(context: alluka.Context):
    mock_value = mock.Mock()
    mock_other_value = mock.Mock()

    async def callback(
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

    result = await context.call_with_async_di(callback, 69, value_2="rew")

    assert result == "meow"


@pytest.mark.anyio
async def test_call_with_async_di_with_type_dependency_inferred_from_type(context: alluka.Context):
    mock_value = MockType()
    mock_other_value = MockOtherType()

    async def callback(
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

    result = await context.call_with_async_di(callback, "5412", meow=34123)

    assert result == "heeee"


@pytest.mark.anyio
async def test_call_with_async_di_with_type_dependency_inferred_from_annotated_type(context: alluka.Context):
    mock_value = MockType()
    mock_other_value = MockOtherType()

    async def callback(
        nyaa: str,
        meow: int,
        value_1: typing.Annotated[MockType, ...] = alluka.inject(),
        value_2: typing.Annotated[MockOtherType, ..., int] = alluka.inject(),
    ) -> str:
        assert nyaa == "5412"
        assert meow == 34123
        assert value_1 is mock_value
        assert value_2 is mock_other_value
        return "heeee"

    context.injection_client.set_type_dependency(MockType, mock_value).set_type_dependency(
        MockOtherType, mock_other_value
    )

    result = await context.call_with_async_di(callback, "5412", meow=34123)

    assert result == "heeee"


@pytest.mark.anyio
async def test_call_with_async_di_with_type_dependency_inferred_from_missing_type(context: alluka.Context):
    async def callback(nyaa: str, meow: int, _: MockType = alluka.inject(), value_1=alluka.inject()) -> str:  # type: ignore
        raise NotImplementedError

    with pytest.raises(ValueError, match="Could not resolve type for parameter 'value_1' with no annotation"):
        await context.call_with_async_di(callback, "5412", meow=34123)


@pytest.mark.anyio
async def test_call_with_async_di_with_type_dependency_not_found(context: alluka.Context):
    mock_value = mock.Mock()

    async def callback(
        _: int, value_1: str, __: str = alluka.inject(type=MockType), ___: int = alluka.inject(type=MockOtherType)
    ) -> str:
        raise NotImplementedError

    context.injection_client.set_type_dependency(MockType, mock_value)

    with pytest.raises(alluka.MissingDependencyError) as exc:
        await context.call_with_async_di(callback, 69, value_1="rew")

    assert exc.value.message == f"Couldn't resolve injected type(s) {MockOtherType} to actual value"
    assert exc.value.dependency_type is MockOtherType


@pytest.mark.anyio
async def test_call_with_async_di_with_defaulting_type_dependency(context: alluka.Context):  # TODO: THIS
    mock_value = mock.Mock()

    async def callback(
        value_1: int, value_2: str, value_3: typing.Optional[int] = alluka.inject(type=typing.Optional[MockType])
    ) -> str:
        assert value_1 == 69
        assert value_2 == "rew"
        assert value_3 is mock_value
        return "meow"

    context.injection_client.set_type_dependency(MockType, mock_value)

    result = await context.call_with_async_di(callback, 69, value_2="rew")

    assert result == "meow"


@pytest.mark.anyio
async def test_call_with_async_di_with_defaulting_type_dependency_not_found(context: alluka.Context):
    async def callback(
        yeet: int, raw: str, value_1: typing.Optional[int] = alluka.inject(type=typing.Optional[MockType])
    ) -> str:
        assert yeet == 420
        assert raw == "uwu"
        assert value_1 is None
        return "yeet"

    result = await context.call_with_async_di(callback, 420, raw="uwu")

    assert result == "yeet"


# These tests covers syntax which was introduced in 3.10
if sys.version_info >= (3, 10):  # TODO: do we want to dupe other test cases for |?

    @pytest.mark.anyio
    async def test_call_with_async_di_with_3_10_union_type_dependency(context: alluka.Context):
        mock_value = MockType()

        context.injection_client.set_type_dependency(MockType, mock_value)

        async def callback(
            value_1: int, value_2: str, cope: int = alluka.inject(type=MockOtherType | MockType)
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is mock_value
            return 451.123

        result = await context.call_with_async_di(callback, 123, "ok")

        assert result == 451.123

    @pytest.mark.anyio
    async def test_call_with_async_di_with_3_10_union_type_dependency_not_found(context: alluka.Context):
        async def callback(_: int, __: str, cope: int = alluka.inject(type=MockOtherType | MockType)) -> float:
            raise NotImplementedError

        with pytest.raises(alluka.MissingDependencyError) as exc_info:
            await context.call_with_async_di(callback, 123, "ok")

        assert exc_info.value.dependency_type == MockOtherType | MockType
        # 3.10.1/2+ and 3.11 may re-order the | union types while resolving them from a string
        # future annotation so we can't reliably assert these.

    @pytest.mark.anyio
    async def test_call_with_async_di_with_3_10_union_type_dependency_defaulting(context: alluka.Context):
        mock_value = MockType()

        context.injection_client.set_type_dependency(MockType, mock_value)

        async def callback(
            value_1: int, value_2: str, cope: int = alluka.inject(type=MockOtherType | MockType | None)
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is mock_value
            return 451.123

        result = await context.call_with_async_di(callback, 123, "ok")

        assert result == 451.123

    @pytest.mark.anyio
    async def test_call_with_async_di_with_3_10_union_type_dependency_defaulting_not_found(context: alluka.Context):
        async def callback(
            value_1: int, value_2: str, cope: int = alluka.inject(type=MockOtherType | MockType | None)
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is None
            return 451.123

        result = await context.call_with_async_di(callback, 123, "ok")

        assert result == 451.123


@pytest.mark.anyio
async def test_call_with_async_di_with_union_type_dependency(context: alluka.Context):
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(MockOtherType, mock_value)

    async def callback(
        value_1: int, value_2: str, cope: int = alluka.inject(type=typing.Union[MockType, MockOtherType])
    ) -> float:
        assert value_1 == 123
        assert value_2 == "ok"
        assert cope is mock_value
        return 243.234

    result = await context.call_with_async_di(callback, 123, "ok")

    assert result == 243.234


@pytest.mark.anyio
async def test_call_with_async_di_with_union_type_dependency_not_found(context: alluka.Context):
    async def callback(_: int, __: str, cope: int = alluka.inject(type=typing.Union[MockType, MockOtherType])) -> float:
        raise NotImplementedError

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        await context.call_with_async_di(callback, 123, "ok")

    assert exc_info.value.dependency_type == typing.Union[MockType, MockOtherType]
    # On 3.10.1/2+ typing.Unions are converted to | while resolving future annotations so we can't consistently
    # assert the message.


@pytest.mark.anyio
async def test_call_with_async_di_with_defaulting_union_type_dependency(context: alluka.Context):
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(MockOtherType, mock_value)

    async def callback(
        value_1: int, value_2: str, cope: int = alluka.inject(type=typing.Union[MockType, MockOtherType, None])
    ) -> float:
        assert value_1 == 123
        assert value_2 == "ok"
        assert cope is mock_value
        return 243.234

    result = await context.call_with_async_di(callback, 123, "ok")

    assert result == 243.234


@pytest.mark.anyio
async def test_call_with_async_di_with_defaulting_union_type_dependency_not_found(context: alluka.Context):
    async def callback(
        value_1: float, value_2: int, cope: typing.Optional[int] = alluka.inject(type=typing.Optional[MockType])
    ) -> float:
        assert value_1 == 123.321
        assert value_2 == 543
        assert cope is None
        return 321.123

    result = await context.call_with_async_di(callback, 123.321, 543)

    assert result == 321.123


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_type_dependency(context: alluka.Context):
    mock_value = MockType()
    mock_other_value = MockOtherType()

    async def callback(
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

    result = await context.call_with_async_di(callback, rawr=69, xd="rew")

    assert result == "meow"


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_type_dependency_inferred_from_type(context: alluka.Context):
    mock_value = MockType()
    mock_other_value = MockOtherType()

    async def callback(
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

    result = await context.call_with_async_di(callback, meow=2222, nyaa="xxxxx")

    assert result == "wewewewew"


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_type_dependency_not_found(context: alluka.Context):
    mock_other_value = MockOtherType()

    async def callback(
        meow: int,
        nyaa: float,
        meowmeow: typing.Annotated[int, alluka.inject(type=MockType)],
        imacow: typing.Annotated[str, alluka.inject(type=MockOtherType)],
    ) -> str:
        raise NotImplementedError

    context.injection_client.set_type_dependency(MockOtherType, mock_other_value)

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        await context.call_with_async_di(callback, meow=2222, nyaa="xxxxx")

    assert exc_info.value.dependency_type is MockType
    assert exc_info.value.message == f"Couldn't resolve injected type(s) {MockType} to actual value"


# These tests covers syntax which was introduced in 3.10
if sys.version_info >= (3, 10):  # TODO: do we want to dupe other test cases for |?

    @pytest.mark.anyio
    async def test_call_with_async_di_with_annotated_3_10_union_type_dependency(context: alluka.Context):
        mock_value = MockOtherType()

        async def callback(
            yeee: str, nyaa: bool, yeet: typing.Annotated[str, alluka.inject(type=MockType | MockOtherType)]
        ) -> str:
            assert yeee == "yeee"
            assert nyaa is True
            assert yeet is mock_value
            return "hey"

        context.injection_client.set_type_dependency(MockOtherType, mock_value)

        result = await context.call_with_async_di(callback, yeee="yeee", nyaa=True)

        assert result == "hey"

    @pytest.mark.anyio
    async def test_call_with_async_di_with_annotated_3_10_union_type_dependency_not_found(context: alluka.Context):
        async def callback(
            _: int, __: str, cope: typing.Annotated[int, alluka.inject(type=MockOtherType | MockType)]
        ) -> float:
            raise NotImplementedError

        with pytest.raises(alluka.MissingDependencyError) as exc_info:
            await context.call_with_async_di(callback, 123, "ok")

        assert exc_info.value.dependency_type == MockOtherType | MockType
        # 3.10.1/2+ and 3.11 may re-order the | union types while resolving them from a string
        # future annotation so we can't reliably assert these.

    @pytest.mark.anyio
    async def test_call_with_async_di_with_annotated_3_10_union_type_dependency_defaulting(context: alluka.Context):
        mock_value = MockType()

        context.injection_client.set_type_dependency(MockType, mock_value)

        async def callback(
            value_1: int, value_2: str, cope: typing.Annotated[int, alluka.inject(type=MockOtherType | MockType | None)]
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is mock_value
            return 451.123

        result = await context.call_with_async_di(callback, 123, "ok")

        assert result == 451.123

    @pytest.mark.anyio
    async def test_call_with_async_di_with_annotated_3_10_union_type_dependency_defaulting_not_found(
        context: alluka.Context,
    ):
        async def callback(
            value_1: int, value_2: str, cope: typing.Annotated[int, alluka.inject(type=MockOtherType | MockType | None)]
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is None
            return 451.123

        result = await context.call_with_async_di(callback, 123, "ok")

        assert result == 451.123

    @pytest.mark.anyio
    async def test_call_with_async_di_with_annotated_3_10_union_type_dependency_natural_defaulting(
        context: alluka.Context,
    ):
        mock_value = MockType()

        context.injection_client.set_type_dependency(MockType, mock_value)

        async def callback(
            value_1: int,
            value_2: str,
            cope: typing.Annotated[int, alluka.inject(type=MockType | MockType | None)] = 123,
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is mock_value
            return 451.123

        result = await context.call_with_async_di(callback, 123, "ok")

        assert result == 451.123

    @pytest.mark.anyio
    async def test_call_with_async_di_with_annotated_3_10_union_type_dependency_natural_defaulting_not_found(
        context: alluka.Context,
    ):
        async def callback(
            value_1: int, value_2: str, cope: typing.Annotated[int, alluka.inject(type=MockType | MockType)] = 43123
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope == 43123
            return 451.123

        result = await context.call_with_async_di(callback, 123, "ok")

        assert result == 451.123


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_union_type_dependency(context: alluka.Context):
    mock_value = MockOtherType()

    async def callback(
        meow: int, meowmeow: typing.Annotated[typing.Union[MockType, MockOtherType], alluka.inject()]
    ) -> str:
        assert meow == 1233212
        assert meowmeow is mock_value
        return "yay"

    context.injection_client.set_type_dependency(MockOtherType, mock_value)

    result = await context.call_with_async_di(callback, 1233212)

    assert result == "yay"


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_union_type_dependency_not_found(context: alluka.Context):
    async def callback(
        yeee: str, nyaa: bool, yeet: typing.Annotated[int, alluka.inject(type=typing.Union[MockType, MockOtherType])]
    ) -> str:
        raise NotImplementedError

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        await context.call_with_async_di(callback, yeee="yeee", nyaa=True)

    assert exc_info.value.dependency_type == typing.Union[MockType, MockOtherType]
    # On 3.10.1/2+ typing.Unions are converted to | while resolving future annotations so we can't consistently
    # assert the message.


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_defaulting_type_dependency(context: alluka.Context):
    mock_value = MockType()
    context.injection_client.set_type_dependency(MockType, mock_value)

    async def callback(
        eaaaa: str, nyaa: bool, yeet: typing.Annotated[str, alluka.inject(type=typing.Optional[MockType])]
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_value
        return "aaaaa"

    result = await context.call_with_async_di(callback, "easd", nyaa=False)

    assert result == "aaaaa"


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_defaulting_type_dependency_not_found(context: alluka.Context):
    async def callback(
        eaaaa: str, nyaa: bool, yeet: typing.Annotated[str, alluka.inject(type=typing.Optional[MockType])]
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is None
        return "aaaaa"

    result = await context.call_with_async_di(callback, "easd", nyaa=False)

    assert result == "aaaaa"


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_natural_defaulting_type_dependency(context: alluka.Context):
    mock_value = MockType()
    context.injection_client.set_type_dependency(MockType, mock_value)

    async def callback(
        eaaaa: str, nyaa: bool, yeet: typing.Annotated[str, alluka.inject(type=MockType)] = "default"
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_value
        return "aaaaa"

    result = await context.call_with_async_di(callback, "easd", nyaa=False)

    assert result == "aaaaa"


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_natural_defaulting_type_dependency_not_found(context: alluka.Context):
    async def callback(eaaaa: str, nyaa: bool, yeet: typing.Annotated[int, alluka.inject(type=MockType)] = 123) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet == 123
        return "aaaaa"

    result = await context.call_with_async_di(callback, "easd", nyaa=False)

    assert result == "aaaaa"


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_defaulting_union_type_dependency(context: alluka.Context):
    mock_value = MockOtherType()
    context.injection_client.set_type_dependency(MockOtherType, mock_value)

    async def callback(
        vvvvv: int, value: typing.Annotated[str, alluka.inject(type=typing.Union[MockType, MockOtherType])]
    ) -> str:
        assert vvvvv == 123
        assert value is mock_value
        return "ea sports"

    result = await context.call_with_async_di(callback, 123)

    assert result == "ea sports"


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_defaulting_union_type_dependency_not_found(context: alluka.Context):
    async def callback(vvvvv: int, value: typing.Annotated[str, alluka.inject(type=typing.Optional[MockType])]) -> str:
        assert vvvvv == 123
        assert value is None
        return "yeeee"

    result = await context.call_with_async_di(callback, 123)

    assert result == "yeeee"


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_natural_defaulting_union_type_dependency(context: alluka.Context):
    mock_value = MockOtherType()
    context.injection_client.set_type_dependency(MockOtherType, mock_value)

    async def callback(
        vvvvv: int, value: typing.Annotated[str, alluka.inject(type=typing.Union[MockType, MockOtherType])] = "default"
    ) -> str:
        assert vvvvv == 123
        assert value is mock_value
        return "ea sports"

    result = await context.call_with_async_di(callback, 123)

    assert result == "ea sports"


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_natural_defaulting_union_type_dependency_not_found(
    context: alluka.Context,
):
    async def callback(
        vvvvv: int,
        value: typing.Annotated[str, alluka.inject(type=typing.Union[MockType, MockOtherType, None])] = "default 2",
    ) -> str:
        assert vvvvv == 123
        assert value == "default 2"
        return "yeeee"

    result = await context.call_with_async_di(callback, 123)

    assert result == "yeeee"


@pytest.mark.anyio
async def test_call_with_async_di_with_shorthand_annotated_type_dependency(context: alluka.Context):
    mock_value = MockType()
    mock_other_value = MockOtherType()

    async def callback(
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

    result = await context.call_with_async_di(callback, 1233212, xd="seee")

    assert result == "eeesss"


@pytest.mark.anyio
async def test_call_with_async_di_with_shorthand_annotated_type_dependency_not_found(context: alluka.Context):
    mock_other_value = MockOtherType()

    async def callback(
        meow: int, nyaa: float, meowmeow: alluka.Injected[MockType], imacow: alluka.Injected[MockOtherType]
    ) -> str:
        raise NotImplementedError

    context.injection_client.set_type_dependency(MockOtherType, mock_other_value)

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        await context.call_with_async_di(callback, meow=2222, nyaa="xxxxx")

    assert exc_info.value.dependency_type is MockType
    assert exc_info.value.message == f"Couldn't resolve injected type(s) {MockType} to actual value"


# These tests covers syntax which was introduced in 3.10
if sys.version_info >= (3, 10):  # TODO: do we want to dupe other test cases for |?

    @pytest.mark.anyio
    async def test_call_with_async_di_with_shorthand_annotated_3_10_union_type_dependency(context: alluka.Context):
        mock_value = MockOtherType()

        async def callback(yeee: str, nyaa: bool, yeet: alluka.Injected[MockType | MockOtherType]) -> str:
            assert yeee == "yeee"
            assert nyaa is True
            assert yeet is mock_value
            return "hey"

        context.injection_client.set_type_dependency(MockOtherType, mock_value)

        result = await context.call_with_async_di(callback, yeee="yeee", nyaa=True)

        assert result == "hey"

    @pytest.mark.anyio
    async def test_call_with_async_di_with_shorthand_annotated_3_10_union_type_dependency_not_found(
        context: alluka.Context,
    ):
        async def callback(_: int, __: str, cope: alluka.Injected[MockOtherType | MockType]) -> float:
            raise NotImplementedError

        with pytest.raises(alluka.MissingDependencyError) as exc_info:
            await context.call_with_async_di(callback, 123, "ok")

        assert exc_info.value.dependency_type == MockOtherType | MockType
        # 3.10.1/2+ and 3.11 may re-order the | union types while resolving them from a string
        # future annotation so we can't reliably assert these.

    @pytest.mark.anyio
    async def test_call_with_async_di_with_shorthand_annotated_3_10_union_type_dependency_defaulting(
        context: alluka.Context,
    ):
        mock_value = MockType()

        context.injection_client.set_type_dependency(MockType, mock_value)

        async def callback(value_1: int, value_2: str, cope: alluka.Injected[MockOtherType | MockType | None]) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is mock_value
            return 451.123

        result = await context.call_with_async_di(callback, 123, "ok")

        assert result == 451.123

    @pytest.mark.anyio
    async def test_call_with_async_di_with_shorthand_annotated_3_10_union_type_dependency_defaulting_not_found(
        context: alluka.Context,
    ):
        async def callback(value_1: int, value_2: str, cope: alluka.Injected[MockOtherType | MockType | None]) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is None
            return 451.123

        result = await context.call_with_async_di(callback, 123, "ok")

        assert result == 451.123

    @pytest.mark.anyio
    async def test_call_with_async_di_with_shorthand_annotated_3_10_union_type_dependency_natural_defaulting(
        context: alluka.Context,
    ):
        mock_value = MockType()

        context.injection_client.set_type_dependency(MockType, mock_value)

        async def callback(
            value_1: int, value_2: str, cope: alluka.Injected[MockOtherType | MockType | None] = MockType()
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is mock_value
            return 451.123

        result = await context.call_with_async_di(callback, 123, "ok")

        assert result == 451.123

    @pytest.mark.anyio
    async def test_call_with_async_di_with_shorthand_annotated_3_10_union_type_dependency_natural_defaulting_not_found(
        context: alluka.Context,
    ):
        mock_default = MockOtherType()

        async def callback(
            value_1: int, value_2: str, cope: alluka.Injected[MockOtherType | MockType] = mock_default
        ) -> float:
            assert value_1 == 123
            assert value_2 == "ok"
            assert cope is mock_default
            return 451.123

        result = await context.call_with_async_di(callback, 123, "ok")

        assert result == 451.123


@pytest.mark.anyio
async def test_call_with_async_di_with_shorthand_annotated_union_type_dependency(context: alluka.Context):
    mock_value = MockOtherType()

    async def callback(meow: int, meowmeow: alluka.Injected[typing.Union[MockType, MockOtherType]]) -> str:
        assert meow == 1233212
        assert meowmeow is mock_value
        return "yay"

    context.injection_client.set_type_dependency(MockOtherType, mock_value)

    result = await context.call_with_async_di(callback, 1233212)

    assert result == "yay"


@pytest.mark.anyio
async def test_call_with_async_di_with_shorthand_annotated_union_type_dependency_not_found(context: alluka.Context):
    async def callback(yeee: str, nyaa: bool, yeet: alluka.Injected[typing.Union[MockType, MockOtherType]]) -> str:
        raise NotImplementedError

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        await context.call_with_async_di(callback, yeee="yeee", nyaa=True)

    assert exc_info.value.dependency_type == typing.Union[MockType, MockOtherType]
    # On 3.10.1/2+ typing.Unions are converted to | while resolving future annotations so we can't consistently
    # assert the message.


@pytest.mark.anyio
async def test_call_with_async_di_with_shorthand_annotated_defaulting_type_dependency(context: alluka.Context):
    mock_value = MockType()
    context.injection_client.set_type_dependency(MockType, mock_value)

    async def callback(eaaaa: str, nyaa: bool, yeet: alluka.Injected[typing.Optional[MockType]]) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_value
        return "aaaaa"

    result = await context.call_with_async_di(callback, "easd", nyaa=False)

    assert result == "aaaaa"


@pytest.mark.anyio
async def test_call_with_async_di_with_shorthand_annotated_defaulting_type_dependency_not_found(
    context: alluka.Context,
):
    async def callback(eaaaa: str, nyaa: bool, yeet: alluka.Injected[typing.Optional[MockType]]) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is None
        return "aaaaa"

    result = await context.call_with_async_di(callback, "easd", nyaa=False)

    assert result == "aaaaa"


@pytest.mark.anyio
async def test_call_with_async_di_with_shorthand_annotated_natural_defaulting_type_dependency(context: alluka.Context):
    mock_value = MockType()
    context.injection_client.set_type_dependency(MockType, mock_value)

    async def callback(eaaaa: str, nyaa: bool, yeet: alluka.Injected[MockType] = MockType()) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_value
        return "aaaaa"

    result = await context.call_with_async_di(callback, "easd", nyaa=False)

    assert result == "aaaaa"


@pytest.mark.anyio
async def test_call_with_async_di_with_shorthand_annotated_natural_defaulting_type_dependency_not_found(
    context: alluka.Context,
):
    mock_default = MockType()

    async def callback(eaaaa: str, nyaa: bool, yeet: alluka.Injected[MockType] = mock_default) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_default
        return "aaaaa"

    result = await context.call_with_async_di(callback, "easd", nyaa=False)

    assert result == "aaaaa"


@pytest.mark.anyio
async def test_call_with_async_di_with_shorthand_annotated_defaulting_union_type_dependency(context: alluka.Context):
    mock_value = MockOtherType()
    context.injection_client.set_type_dependency(MockOtherType, mock_value)

    async def callback(vvvvv: int, value: alluka.Injected[typing.Union[MockType, MockOtherType]]) -> str:
        assert vvvvv == 123
        assert value is mock_value
        return "ea sports"

    result = await context.call_with_async_di(callback, 123)

    assert result == "ea sports"


@pytest.mark.anyio
async def test_call_with_async_di_with_shorthand_annotated_defaulting_union_type_dependency_not_found(
    context: alluka.Context,
):
    async def callback(vvvvv: int, value: alluka.Injected[typing.Optional[MockType]]) -> str:
        assert vvvvv == 123
        assert value is None
        return "yeeee"

    result = await context.call_with_async_di(callback, 123)

    assert result == "yeeee"


@pytest.mark.anyio
async def test_call_with_async_di_with_shorthand_annotated_natural_defaulting_union_type_dependency(
    context: alluka.Context,
):
    mock_value = MockOtherType()
    context.injection_client.set_type_dependency(MockOtherType, mock_value)

    async def callback(
        vvvvv: int, value: alluka.Injected[typing.Union[MockType, MockOtherType]] = MockOtherType()
    ) -> str:
        assert vvvvv == 123
        assert value is mock_value
        return "ea sports"

    result = await context.call_with_async_di(callback, 123)

    assert result == "ea sports"


@pytest.mark.anyio
async def test_call_with_async_di_with_shorthand_annotated_natural_defaulting_union_type_dependency_not_found(
    context: alluka.Context,
):
    mock_default = MockOtherType()

    async def callback(
        vvvvv: int, value: alluka.Injected[typing.Union[MockType, MockOtherType, None]] = mock_default
    ) -> str:
        assert vvvvv == 123
        assert value is mock_default
        return "yeeee"

    result = await context.call_with_async_di(callback, 123)

    assert result == "yeeee"


@pytest.mark.anyio
async def test_call_with_async_di_with_callback_dependency(context: alluka.Context):
    mock_callback = mock.AsyncMock()

    async def callback(value_1: int, result: int = alluka.inject(callback=mock_callback)) -> int:
        assert value_1 == 123
        assert result is mock_callback.return_value
        return 43123

    result = await context.call_with_async_di(callback, 123)

    assert result == 43123
    mock_callback.assert_awaited_once()


@pytest.mark.anyio
async def test_call_with_async_di_with_sub_callback_dependency(context: alluka.Context):
    mock_callback = mock.Mock()

    async def dependency(result: int = alluka.inject(callback=mock_callback)) -> int:
        assert result is mock_callback.return_value
        return 541232

    async def callback(value_1: int, result: int = alluka.inject(callback=dependency)) -> str:
        assert value_1 == 123
        assert result == 541232
        return "43123"

    result = await context.call_with_async_di(callback, 123)

    assert result == "43123"
    mock_callback.assert_called_once_with()


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_callback_dependency(context: alluka.Context):
    global mock_callback
    mock_callback = mock.AsyncMock()

    async def callback(value_1: int, result: typing.Annotated[int, alluka.inject(callback=mock_callback)]) -> int:
        assert value_1 == 123
        assert result is mock_callback.return_value
        return 43123

    result = await context.call_with_async_di(callback, 123)

    assert result == 43123
    mock_callback.assert_awaited_once_with()


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_sub_callback_dependency(context: alluka.Context):
    global mock_callback
    mock_callback = mock.AsyncMock()
    global dependency_3

    async def dependency_3(result: typing.Annotated[int, alluka.inject(callback=mock_callback)]) -> int:
        assert result is mock_callback.return_value
        return 541232

    async def callback(value_1: int, result: typing.Annotated[int, alluka.inject(callback=dependency_3)]) -> str:
        assert value_1 == 123
        assert result == 541232
        return "43123"

    result = await context.call_with_async_di(callback, 123)

    assert result == "43123"
    mock_callback.assert_awaited_once()


@pytest.mark.anyio
async def test_call_with_async_di_with_sub_type_dependency(context: alluka.Context):
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(MockType, mock_value)

    async def dependency(result: int = alluka.inject(type=MockType)) -> int:
        assert result is mock_value
        return 123321

    async def callback(value_1: int, result: int = alluka.inject(callback=dependency)) -> str:
        assert value_1 == 54123
        assert result == 123321
        return "asddsa"

    result = await context.call_with_async_di(callback, 54123)

    assert result == "asddsa"


@pytest.mark.anyio
async def test_call_with_async_di_with_sub_type_dependency_not_found(context: alluka.Context):
    async def dependency(result: int = alluka.inject(type=MockType)) -> int:
        raise NotImplementedError

    async def callback(_: int, result: int = alluka.inject(callback=dependency)) -> str:
        raise NotImplementedError

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        await context.call_with_async_di(callback, 54123)

    assert exc_info.value.dependency_type is MockType
    assert exc_info.value.message == (f"Couldn't resolve injected type(s) {MockType} to actual value")


@pytest.mark.anyio
async def test_call_with_async_di_when_sync_callback(context: alluka.Context):
    mock_value = MockType()
    mock_callback = mock.AsyncMock()
    context.injection_client.set_type_dependency(MockType, mock_value)

    async def dependency(value_1: int = alluka.inject(callback=mock_callback)) -> str:
        assert value_1 is mock_callback.return_value
        return "Ok"

    def callback(
        value_1: int,
        value_2: str,
        value_3: alluka.Injected[MockType],
        value_4: str = alluka.inject(callback=dependency),
    ) -> float:
        assert value_1 == 1234321
        assert value_2 == "meow meow"
        assert value_3 is mock_value
        assert value_4 == "Ok"
        return 123.321

    result = await context.call_with_async_di(callback, 1234321, value_2="meow meow")

    assert result == 123.321
    mock_callback.assert_awaited_once_with()


@pytest.mark.anyio
async def test_call_with_async_di_with_sync_dependency_callback(context: alluka.Context):
    mock_value = MockType()
    mock_other_value = MockOtherType()
    context.injection_client.set_type_dependency(MockType, mock_value).set_type_dependency(
        MockOtherType, mock_other_value
    )

    def dependency(value_1: alluka.Injected[MockOtherType]) -> str:
        assert value_1 is mock_other_value
        return "eeeeaaaa"

    async def callback(value_1: alluka.Injected[MockType], value_2: str = alluka.inject(callback=dependency)) -> str:
        assert value_1 is mock_value
        assert value_2 == "eeeeaaaa"
        return "bye bye"

    result = await context.call_with_async_di(callback)

    assert result == "bye bye"


@pytest.mark.anyio
async def test_call_with_async_di_with_overridden_sync_dependency(context: alluka.Context):
    mock_value = MockType()
    mock_callback = mock.AsyncMock()
    mock_override = mock.Mock()
    context.injection_client.set_type_dependency(MockType, mock_value).set_callback_override(
        mock_callback, mock_override
    )

    async def callback(value_1: alluka.Injected[MockType], value_2: str = alluka.inject(callback=mock_callback)) -> str:
        assert value_1 is mock_value
        assert value_2 is mock_override.return_value
        return "bye bye"

    result = await context.call_with_async_di(callback)

    assert result == "bye bye"
    mock_override.assert_called_once_with()


@pytest.mark.anyio
async def test_call_with_async_di_with_sub_sync_dependency(context: alluka.Context):
    mock_value = MockType()
    mock_callback = mock.AsyncMock()
    context.injection_client.set_type_dependency(MockType, mock_value)

    def dependency(result: str = alluka.inject(callback=mock_callback)) -> str:
        assert result is mock_callback.return_value
        return "go home"

    async def callback(value_1: alluka.Injected[MockType], value_2: str = alluka.inject(callback=dependency)) -> str:
        assert value_1 is mock_value
        assert value_2 == "go home"
        return "bye bye"

    result = await context.call_with_async_di(callback)

    assert result == "bye bye"
    mock_callback.assert_called_once_with()


@pytest.mark.anyio
async def test_call_with_async_di_with_overridden_sub_sync_dependency(context: alluka.Context):
    mock_value = MockType()
    global mock_callback
    mock_callback = mock.AsyncMock()
    mock_override = mock.Mock()
    context.injection_client.set_type_dependency(MockType, mock_value).set_callback_override(
        mock_callback, mock_override
    )

    def dependency(result: typing.Annotated[str, alluka.inject(callback=mock_callback)]) -> str:
        assert result is mock_override.return_value
        return "go home"

    async def callback(value_1: alluka.Injected[MockType], value_2: str = alluka.inject(callback=dependency)) -> str:
        assert value_1 is mock_value
        assert value_2 == "go home"
        return "bye bye"

    result = await context.call_with_async_di(callback)

    assert result == "bye bye"
    mock_override.assert_called_once_with()


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_sync_dependency(context: alluka.Context):
    mock_value = MockType()
    mock_other_value = MockOtherType()
    context.injection_client.set_type_dependency(MockType, mock_value).set_type_dependency(
        MockOtherType, mock_other_value
    )
    global dependency_4

    def dependency_4(value_1: alluka.Injected[MockOtherType]) -> str:
        assert value_1 is mock_other_value
        return "eeeeaaaa"

    async def callback(
        value_1: alluka.Injected[MockType], value_2: typing.Annotated[str, alluka.inject(callback=dependency_4)]
    ) -> str:
        assert value_1 is mock_value
        assert value_2 == "eeeeaaaa"
        return "bye bye"

    result = await context.call_with_async_di(callback)

    assert result == "bye bye"


@pytest.mark.anyio
async def test_call_with_async_di_with_overridden_annotated_sync_dependency(context: alluka.Context):
    mock_value = MockType()
    global mock_callback
    mock_callback = mock.AsyncMock()
    mock_override = mock.Mock()
    context.injection_client.set_type_dependency(MockType, mock_value).set_callback_override(
        mock_callback, mock_override
    )

    async def callback(
        value_1: alluka.Injected[MockType], value_2: typing.Annotated[str, alluka.inject(callback=mock_callback)]
    ) -> str:
        assert value_1 is mock_value
        assert value_2 is mock_override.return_value
        return "bye bye"

    result = await context.call_with_async_di(callback)

    assert result == "bye bye"
    mock_override.assert_called_once_with()


@pytest.mark.anyio
async def test_call_with_async_di_with_annotated_sub_sync_dependency(context: alluka.Context):
    mock_value = MockType()
    mock_callback = mock.AsyncMock()
    context.injection_client.set_type_dependency(MockType, mock_value)

    global dependency

    def dependency(result: str = alluka.inject(callback=mock_callback)) -> str:
        assert result is mock_callback.return_value
        return "go home"

    async def callback(
        value_1: alluka.Injected[MockType], value_2: typing.Annotated[str, alluka.inject(callback=dependency)]
    ) -> str:
        assert value_1 is mock_value
        assert value_2 == "go home"
        return "bye bye"

    result = await context.call_with_async_di(callback)

    assert result == "bye bye"
    mock_callback.assert_called_once_with()


@pytest.mark.anyio
async def test_call_with_async_di_with_overridden_annotated_sub_sync_dependency(context: alluka.Context):
    mock_value = MockType()
    global mock_callback
    mock_callback = mock.AsyncMock()
    mock_override = mock.Mock()
    global dependency_1
    context.injection_client.set_type_dependency(MockType, mock_value).set_callback_override(
        mock_callback, mock_override
    )

    def dependency_1(result: typing.Annotated[str, alluka.inject(callback=mock_callback)]) -> str:
        assert result is mock_override.return_value
        return "go home"

    async def callback(
        value_1: alluka.Injected[MockType], value_2: typing.Annotated[str, alluka.inject(callback=dependency_1)]
    ) -> str:
        assert value_1 is mock_value
        assert value_2 == "go home"
        return "bye bye"

    result = await context.call_with_async_di(callback)

    assert result == "bye bye"
    mock_override.assert_called_once_with()


################################
# Positional-only dependencies #
################################


@pytest.mark.anyio
async def test_call_with_async_di_with_positional_only_type_dependency(context: alluka.Context):
    async def callback(_: int, __: str = alluka.inject(type=float), /, ___: float = alluka.inject(type=float)) -> None:
        raise NotImplementedError

    with pytest.raises(ValueError, match="Injected positional only arguments are not supported"):
        await context.call_with_async_di(callback)


@pytest.mark.anyio
async def test_call_with_async_di_with_positional_only_callback_dependency(context: alluka.Context):
    mock_dependency = mock.Mock()

    async def callback(
        _: int, __: str = alluka.inject(callback=mock_dependency), /, ___: float = alluka.inject(type=float)
    ) -> None:
        raise NotImplementedError

    with pytest.raises(ValueError, match="Injected positional only arguments are not supported"):
        await context.call_with_async_di(callback)


@pytest.mark.anyio
async def test_call_with_async_di_with_sub_positional_only_callback_dependency(context: alluka.Context):
    sub_dependency = mock.Mock()

    async def dependency(_: str = alluka.inject(callback=sub_dependency), /) -> str:
        raise NotImplementedError

    async def callback(
        _: int, __: str = alluka.inject(callback=dependency), /, ___: float = alluka.inject(type=float)
    ) -> None:
        raise NotImplementedError

    with pytest.raises(ValueError, match="Injected positional only arguments are not supported"):
        await context.call_with_async_di(callback)


@pytest.mark.anyio
async def test_call_with_async_di_with_sub_positional_only_type_dependency(context: alluka.Context):
    async def dependency(_: str = alluka.inject(type=int), /) -> str:
        raise NotImplementedError

    async def callback(
        _: int, __: str = alluka.inject(callback=dependency), /, ___: float = alluka.inject(type=float)
    ) -> None:
        raise NotImplementedError

    with pytest.raises(ValueError, match="Injected positional only arguments are not supported"):
        await context.call_with_async_di(callback)


############################
# Signature-less callbacks #
############################


@pytest.mark.anyio
async def test_call_with_async_di_with_signature_less_callback(context: alluka.Context):
    with pytest.raises(ValueError, match="no signature found for builtin type <class 'str'>"):
        inspect.signature(str)

    result = await context.call_with_async_di(str, b"ok")

    assert result == "b'ok'"


@pytest.mark.anyio
async def test_call_with_async_dix_with_signature_less_callback_dependency(context: alluka.Context):
    with pytest.raises(ValueError, match="no signature found for builtin type <class 'int'>"):
        inspect.signature(int)

    def callback(value: int = alluka.inject(callback=int)) -> int:
        assert value == 0
        return 222

    result = await context.call_with_async_di(callback)

    assert result == 222

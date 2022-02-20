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

import sys
import typing
from unittest import mock

import pytest

import alluka

# pyright: reportUnknownMemberType=none
# pyright: reportPrivateUsage=none
# pyright: reportIncompatibleMethodOverride=none


##############################
# Async dependency injection #
##############################


@pytest.fixture()
def client() -> alluka.Client:
    return alluka.Client()


@pytest.fixture()
def context(client: alluka.Client) -> alluka.BasicContext:
    return alluka.BasicContext(client)


# TODO: test cases for type scoped dependencies
# TODO: test cases for cached callback results
@pytest.mark.anyio()
async def test_execute_with_ctx_async_when_no_di(context: alluka.BasicContext):
    async def callback(x: int, bar: str) -> str:
        assert x == 42
        assert bar == "ok"
        return "nyaa"

    result = await context.execute_async(callback, 42, bar="ok")

    assert result == "nyaa"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_prioritises_defaults_over_annotations(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()
    mock_callback = mock.AsyncMock()

    async def dependency(
        result: typing.Annotated[float, alluka.inject(type=123)] = alluka.inject(callback=mock_callback)
    ) -> str:
        assert result is mock_callback.return_value
        return "sexual catgirls"

    async def callback(
        x: int,
        bar: str,
        baz: alluka.Injected[str] = alluka.inject(type=mock_type),
        bat: typing.Annotated[int, alluka.inject(type=float)] = alluka.inject(type=mock_other_type),
        bath: typing.Annotated[str, alluka.inject(callback=mock.Mock)] = alluka.inject(callback=dependency),
    ) -> str:
        assert x == 69
        assert bar == "rew"
        assert baz is mock_value
        assert bat is mock_other_value
        assert bath == "sexual catgirls"
        return "meow"

    context.injection_client.set_type_dependency(mock_type, mock_value).set_type_dependency(
        mock_other_type, mock_other_value
    )

    result = await context.execute_async(callback, 69, bar="rew")

    assert result == "meow"
    mock_callback.assert_awaited_once_with()


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_type_dependency_and_callback(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()
    mock_callback = mock.AsyncMock()

    async def callback(
        x: int,
        bar: str,
        baz: str = alluka.inject(type=mock_type),
        bat: int = alluka.inject(type=mock_other_type),
        bath: typing.Any = alluka.inject(callback=mock_callback),
    ) -> str:
        assert x == 69
        assert bar == "rew"
        assert baz is mock_value
        assert bat is mock_other_value
        assert bath is mock_callback.return_value
        return "meow"

    context.injection_client.set_type_dependency(mock_type, mock_value).set_type_dependency(
        mock_other_type, mock_other_value
    )

    result = await context.execute_async(callback, 69, bar="rew")

    assert result == "meow"
    mock_callback.assert_awaited_once_with()


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()

    async def callback(
        x: int, bar: str, baz: str = alluka.inject(type=mock_type), bat: int = alluka.inject(type=mock_other_type)
    ) -> str:
        assert x == 69
        assert bar == "rew"
        assert baz is mock_value
        assert bat is mock_other_value
        return "meow"

    context.injection_client.set_type_dependency(mock_type, mock_value).set_type_dependency(
        mock_other_type, mock_other_value
    )

    result = await context.execute_async(callback, 69, bar="rew")

    assert result == "meow"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_type_dependency_inferred_from_type(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()

    async def callback(
        nyaa: str, meow: int, baz: mock_type = alluka.inject(), bat: mock_other_type = alluka.inject()
    ) -> str:
        assert nyaa == "5412"
        assert meow == 34123
        assert baz is mock_value
        assert bat is mock_other_value
        return "heeee"

    context.injection_client.set_type_dependency(mock_type, mock_value).set_type_dependency(
        mock_other_type, mock_other_value
    )

    result = await context.execute_async(callback, "5412", meow=34123)

    assert result == "heeee"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_type_dependency_inferred_from_annotated_type(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()

    async def callback(
        nyaa: str,
        meow: int,
        baz: typing.Annotated[mock_type, ...] = alluka.inject(),
        bat: typing.Annotated[mock_other_type, ..., int] = alluka.inject(),
    ) -> str:
        assert nyaa == "5412"
        assert meow == 34123
        assert baz is mock_value
        assert bat is mock_other_value
        return "heeee"

    context.injection_client.set_type_dependency(mock_type, mock_value).set_type_dependency(
        mock_other_type, mock_other_value
    )

    result = await context.execute_async(callback, "5412", meow=34123)

    assert result == "heeee"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_type_dependency_inferred_from_missing_type(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()

    async def callback(
        nyaa: str, meow: int, baz: mock_type = alluka.inject(), bat=alluka.inject()  # type: ignore
    ) -> str:
        raise NotImplementedError

    with pytest.raises(ValueError, match="Could not resolve type for parameter 'bat' with no annotation"):
        await context.execute_async(callback, "5412", meow=34123)


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()

    async def callback(
        x: int, bar: str, baz: str = alluka.inject(type=mock_type), bat: int = alluka.inject(type=mock_other_type)
    ) -> str:
        raise NotImplementedError

    context.injection_client.set_type_dependency(mock_type, mock_value)

    with pytest.raises(alluka.MissingDependencyError) as exc:
        await context.execute_async(callback, 69, bar="rew")

    assert exc.value.message == f"Couldn't resolve injected type(s) {mock_other_type} to actual value"
    assert exc.value.dependency_type is mock_other_type


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_defaulting_type_dependency(context: alluka.BasicContext):  # TODO: THIS
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()

    async def callback(
        x: int, bar: str, bat: typing.Optional[int] = alluka.inject(type=typing.Optional[mock_type])
    ) -> str:
        assert x == 69
        assert bar == "rew"
        assert bat is mock_value
        return "meow"

    context.injection_client.set_type_dependency(mock_type, mock_value)

    result = await context.execute_async(callback, 69, bar="rew")

    assert result == "meow"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_defaulting_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()

    async def callback(
        yeet: int, raw: str, bat: typing.Optional[int] = alluka.inject(type=typing.Optional[mock_type])
    ) -> str:
        assert yeet == 420
        assert raw == "uwu"
        assert bat is None
        return "yeet"

    result = await context.execute_async(callback, 420, raw="uwu")

    assert result == "yeet"


# These tests covers syntax which was introduced in 3.10
if sys.version_info >= (3, 10):  # TODO: do we want to dupe other test cases for |?

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async_with_3_10_union_type_dependency(context: alluka.BasicContext):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_value = StubType()

        context.injection_client.set_type_dependency(StubType, mock_value)

        async def callback(bar: int, baz: str, cope: int = alluka.inject(type=StubOtherType | StubType)) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_value
            return 451.123

        result = await context.execute_async(callback, 123, "ok")

        assert result == 451.123

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async_with_3_10_union_type_dependency_not_found(context: alluka.BasicContext):
        class StubType:
            ...

        class StubOtherType:
            ...

        async def callback(bar: int, baz: str, cope: int = alluka.inject(type=StubOtherType | StubType)) -> float:
            raise NotImplementedError

        with pytest.raises(alluka.MissingDependencyError) as exc_info:
            await context.execute_async(callback, 123, "ok")

        assert exc_info.value.dependency_type == StubOtherType | StubType
        assert exc_info.value.message == f"Couldn't resolve injected type(s) {StubOtherType | StubType} to actual value"

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async_with_3_10_union_type_dependency_defaulting(context: alluka.BasicContext):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_value = StubType()

        context.injection_client.set_type_dependency(StubType, mock_value)

        async def callback(
            bar: int, baz: str, cope: int = alluka.inject(type=StubOtherType | StubType | None)
        ) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_value
            return 451.123

        result = await context.execute_async(callback, 123, "ok")

        assert result == 451.123

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async_with_3_10_union_type_dependency_defaulting_not_found(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        async def callback(
            bar: int, baz: str, cope: int = alluka.inject(type=StubOtherType | StubType | None)
        ) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is None
            return 451.123

        result = await context.execute_async(callback, 123, "ok")

        assert result == 451.123


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_union_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_other_type, mock_value)

    async def callback(
        bar: int, baz: str, cope: int = alluka.inject(type=typing.Union[mock_type, mock_other_type])
    ) -> float:
        assert bar == 123
        assert baz == "ok"
        assert cope is mock_value
        return 243.234

    result = await context.execute_async(callback, 123, "ok")

    assert result == 243.234


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_union_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()

    async def callback(
        bar: int, baz: str, cope: int = alluka.inject(type=typing.Union[mock_type, mock_other_type])
    ) -> float:
        raise NotImplementedError

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        await context.execute_async(callback, 123, "ok")

    assert exc_info.value.dependency_type == typing.Union[mock_type, mock_other_type]
    assert exc_info.value.message == (
        f"Couldn't resolve injected type(s) {typing.Union[mock_type, mock_other_type]} to actual value"
    )


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_defaulting_union_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_other_type, mock_value)

    async def callback(
        bar: int, baz: str, cope: int = alluka.inject(type=typing.Union[mock_type, mock_other_type, None])
    ) -> float:
        assert bar == 123
        assert baz == "ok"
        assert cope is mock_value
        return 243.234

    result = await context.execute_async(callback, 123, "ok")

    assert result == 243.234


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_defaulting_union_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()

    async def callback(
        bar: float, baz: int, cope: typing.Optional[int] = alluka.inject(type=typing.Optional[mock_type])
    ) -> float:
        assert bar == 123.321
        assert baz == 543
        assert cope is None
        return 321.123

    result = await context.execute_async(callback, 123.321, 543)

    assert result == 321.123


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()

    async def callback(
        rawr: int,
        xd: float,
        meowmeow: typing.Annotated[str, alluka.inject(type=mock_type)],
        imacow: typing.Annotated[int, alluka.inject(type=mock_other_type)],
    ) -> str:
        assert rawr == 69
        assert xd == "rew"
        assert meowmeow is mock_value
        assert imacow is mock_other_value
        return "meow"

    context.injection_client.set_type_dependency(mock_type, mock_value).set_type_dependency(
        mock_other_type, mock_other_value
    )

    result = await context.execute_async(callback, rawr=69, xd="rew")

    assert result == "meow"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_type_dependency_inferred_from_type(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()

    async def callback(
        meow: int,
        nyaa: float,
        meowmeow: typing.Annotated[mock_type, alluka.inject()],
        imacow: typing.Annotated[mock_other_type, alluka.inject()],
    ) -> str:
        assert meow == 2222
        assert nyaa == "xxxxx"
        assert meowmeow is mock_value
        assert imacow is mock_other_value
        return "wewewewew"

    context.injection_client.set_type_dependency(mock_type, mock_value).set_type_dependency(
        mock_other_type, mock_other_value
    )

    result = await context.execute_async(callback, meow=2222, nyaa="xxxxx")

    assert result == "wewewewew"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()

    async def callback(
        meow: int,
        nyaa: float,
        meowmeow: typing.Annotated[int, alluka.inject(type=mock_type)],
        imacow: typing.Annotated[str, alluka.inject(type=mock_other_type)],
    ) -> str:
        raise NotImplementedError

    context.injection_client.set_type_dependency(mock_other_type, mock_other_value)

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        await context.execute_async(callback, meow=2222, nyaa="xxxxx")

    assert exc_info.value.dependency_type is mock_type
    assert exc_info.value.message == f"Couldn't resolve injected type(s) {mock_type} to actual value"


# These tests covers syntax which was introduced in 3.10
if sys.version_info >= (3, 10):  # TODO: do we want to dupe other test cases for |?

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async_with_annotated_3_10_union_type_dependency(context: alluka.BasicContext):
        class StubType:
            ...

        mock_value = StubType()

        class StubOtherType:
            ...

        async def callback(
            yeee: str,
            nyaa: bool,
            yeet: typing.Annotated[str, alluka.inject(type=StubType | StubOtherType)],
        ) -> str:
            assert yeee == "yeee"
            assert nyaa is True
            assert yeet is mock_value
            return "hey"

        context.injection_client.set_type_dependency(StubOtherType, mock_value)

        result = await context.execute_async(callback, yeee="yeee", nyaa=True)

        assert result == "hey"

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async_with_annotated_3_10_union_type_dependency_not_found(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        async def callback(
            bar: int, baz: str, cope: typing.Annotated[int, alluka.inject(type=StubOtherType | StubType)]
        ) -> float:
            raise NotImplementedError

        with pytest.raises(alluka.MissingDependencyError) as exc_info:
            await context.execute_async(callback, 123, "ok")

        assert exc_info.value.dependency_type == StubOtherType | StubType
        assert exc_info.value.message == f"Couldn't resolve injected type(s) {StubOtherType | StubType} to actual value"

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async_with_annotated_3_10_union_type_dependency_defaulting(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_value = StubType()

        context.injection_client.set_type_dependency(StubType, mock_value)

        async def callback(
            bar: int, baz: str, cope: typing.Annotated[int, alluka.inject(type=StubOtherType | StubType | None)]
        ) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_value
            return 451.123

        result = await context.execute_async(callback, 123, "ok")

        assert result == 451.123

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async_with_annotated_3_10_union_type_dependency_defaulting_not_found(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        async def callback(
            bar: int, baz: str, cope: typing.Annotated[int, alluka.inject(type=StubOtherType | StubType | None)]
        ) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is None
            return 451.123

        result = await context.execute_async(callback, 123, "ok")

        assert result == 451.123

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async_with_annotated_3_10_union_type_dependency_natural_defaulting(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_value = StubType()

        context.injection_client.set_type_dependency(StubType, mock_value)

        async def callback(
            bar: int, baz: str, cope: typing.Annotated[int, alluka.inject(type=StubOtherType | StubType | None)] = 123
        ) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_value
            return 451.123

        result = await context.execute_async(callback, 123, "ok")

        assert result == 451.123

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async_with_annotated_3_10_union_type_dependency_natural_defaulting_not_found(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        async def callback(
            bar: int, baz: str, cope: typing.Annotated[int, alluka.inject(type=StubOtherType | StubType)] = 43123
        ) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope == 43123
            return 451.123

        result = await context.execute_async(callback, 123, "ok")

        assert result == 451.123


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_union_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()

    async def callback(
        meow: int,
        meowmeow: typing.Annotated[typing.Union[mock_type, mock_other_type], alluka.inject()],
    ) -> str:
        assert meow == 1233212
        assert meowmeow is mock_value
        return "yay"

    context.injection_client.set_type_dependency(mock_other_type, mock_value)

    result = await context.execute_async(callback, 1233212)

    assert result == "yay"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_union_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()

    async def callback(
        yeee: str,
        nyaa: bool,
        yeet: typing.Annotated[int, alluka.inject(type=typing.Union[mock_type, mock_other_type])],
    ) -> str:
        raise NotImplementedError

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        await context.execute_async(callback, yeee="yeee", nyaa=True)

    assert exc_info.value.dependency_type == typing.Union[mock_type, mock_other_type]
    assert (
        exc_info.value.message
        == f"Couldn't resolve injected type(s) {typing.Union[mock_type, mock_other_type]} to actual value"
    )


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_defaulting_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_type, mock_value)

    async def callback(
        eaaaa: str,
        nyaa: bool,
        yeet: typing.Annotated[str, alluka.inject(type=typing.Optional[mock_type])],
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_value
        return "aaaaa"

    result = await context.execute_async(callback, "easd", nyaa=False)

    assert result == "aaaaa"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_defaulting_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()

    async def callback(
        eaaaa: str,
        nyaa: bool,
        yeet: typing.Annotated[str, alluka.inject(type=typing.Optional[mock_type])],
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is None
        return "aaaaa"

    result = await context.execute_async(callback, "easd", nyaa=False)

    assert result == "aaaaa"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_natural_defaulting_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_type, mock_value)

    async def callback(
        eaaaa: str,
        nyaa: bool,
        yeet: typing.Annotated[str, alluka.inject(type=mock_type)] = "default",
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_value
        return "aaaaa"

    result = await context.execute_async(callback, "easd", nyaa=False)

    assert result == "aaaaa"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_natural_defaulting_type_dependency_not_found(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()

    async def callback(
        eaaaa: str,
        nyaa: bool,
        yeet: typing.Annotated[int, alluka.inject(type=mock_type)] = 123,
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet == 123
        return "aaaaa"

    result = await context.execute_async(callback, "easd", nyaa=False)

    assert result == "aaaaa"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_defaulting_union_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_other_type, mock_value)

    async def callback(
        vvvvv: int,
        value: typing.Annotated[str, alluka.inject(type=typing.Union[mock_type, mock_other_type])],
    ) -> str:
        assert vvvvv == 123
        assert value is mock_value
        return "ea sports"

    result = await context.execute_async(callback, 123)

    assert result == "ea sports"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_defaulting_union_type_dependency_not_found(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()

    async def callback(
        vvvvv: int,
        value: typing.Annotated[str, alluka.inject(type=typing.Optional[mock_type])],
    ) -> str:
        assert vvvvv == 123
        assert value is None
        return "yeeee"

    result = await context.execute_async(callback, 123)

    assert result == "yeeee"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_natural_defaulting_union_type_dependency(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_other_type, mock_value)

    async def callback(
        vvvvv: int,
        value: typing.Annotated[str, alluka.inject(type=typing.Union[mock_type, mock_other_type])] = "default",
    ) -> str:
        assert vvvvv == 123
        assert value is mock_value
        return "ea sports"

    result = await context.execute_async(callback, 123)

    assert result == "ea sports"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_natural_defaulting_union_type_dependency_not_found(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()

    async def callback(
        vvvvv: int,
        value: typing.Annotated[str, alluka.inject(type=typing.Union[mock_type, mock_other_type, None])] = "default 2",
    ) -> str:
        assert vvvvv == 123
        assert value == "default 2"
        return "yeeee"

    result = await context.execute_async(callback, 123)

    assert result == "yeeee"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_shorthand_annotated_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()

    async def callback(
        rawr: int, xd: float, meowmeow: alluka.Injected[mock_type], other: alluka.Injected[mock_other_type]
    ) -> str:
        assert rawr == 1233212
        assert xd == "seee"
        assert meowmeow is mock_value
        assert other is mock_other_value
        return "eeesss"

    context.injection_client.set_type_dependency(mock_type, mock_value).set_type_dependency(
        mock_other_type, mock_other_value
    )

    result = await context.execute_async(callback, 1233212, xd="seee")

    assert result == "eeesss"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_shorthand_annotated_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()

    async def callback(
        meow: int,
        nyaa: float,
        meowmeow: alluka.Injected[mock_type],
        imacow: alluka.Injected[mock_other_type],
    ) -> str:
        raise NotImplementedError

    context.injection_client.set_type_dependency(mock_other_type, mock_other_value)

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        await context.execute_async(callback, meow=2222, nyaa="xxxxx")

    assert exc_info.value.dependency_type is mock_type
    assert exc_info.value.message == f"Couldn't resolve injected type(s) {mock_type} to actual value"


# These tests covers syntax which was introduced in 3.10
if sys.version_info >= (3, 10):  # TODO: do we want to dupe other test cases for |?

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async_with_shorthand_annotated_3_10_union_type_dependency(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        mock_value = StubType()

        class StubOtherType:
            ...

        async def callback(
            yeee: str,
            nyaa: bool,
            yeet: alluka.Injected[StubType | StubOtherType],
        ) -> str:
            assert yeee == "yeee"
            assert nyaa is True
            assert yeet is mock_value
            return "hey"

        context.injection_client.set_type_dependency(StubOtherType, mock_value)

        result = await context.execute_async(callback, yeee="yeee", nyaa=True)

        assert result == "hey"

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async_with_shorthand_annotated_3_10_union_type_dependency_not_found(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        async def callback(bar: int, baz: str, cope: alluka.Injected[StubOtherType | StubType]) -> float:
            raise NotImplementedError

        with pytest.raises(alluka.MissingDependencyError) as exc_info:
            await context.execute_async(callback, 123, "ok")

        assert exc_info.value.dependency_type == StubOtherType | StubType
        assert exc_info.value.message == f"Couldn't resolve injected type(s) {StubOtherType | StubType} to actual value"

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async_with_shorthand_annotated_3_10_union_type_dependency_defaulting(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_value = StubType()

        context.injection_client.set_type_dependency(StubType, mock_value)

        async def callback(bar: int, baz: str, cope: alluka.Injected[StubOtherType | StubType | None]) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_value
            return 451.123

        result = await context.execute_async(callback, 123, "ok")

        assert result == 451.123

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async_with_shorthand_annotated_3_10_union_type_dependency_defaulting_not_found(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        async def callback(bar: int, baz: str, cope: alluka.Injected[StubOtherType | StubType | None]) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is None
            return 451.123

        result = await context.execute_async(callback, 123, "ok")

        assert result == 451.123

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async_with_shorthand_annotated_3_10_union_type_dependency_natural_defaulting(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_value = StubType()

        context.injection_client.set_type_dependency(StubType, mock_value)

        async def callback(
            bar: int, baz: str, cope: alluka.Injected[StubOtherType | StubType | None] = StubOtherType()
        ) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_value
            return 451.123

        result = await context.execute_async(callback, 123, "ok")

        assert result == 451.123

    @pytest.mark.anyio()
    async def test_execute_with_ctx_async_with_shorthand_annotated_3_10_union_type_dependency_natural_defaulting_not_found(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_default = mock.Mock()

        async def callback(bar: int, baz: str, cope: alluka.Injected[StubOtherType | StubType] = mock_default) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_default
            return 451.123

        result = await context.execute_async(callback, 123, "ok")

        assert result == 451.123


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_shorthand_annotated_union_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()

    async def callback(
        meow: int,
        meowmeow: alluka.Injected[typing.Union[mock_type, mock_other_type]],
    ) -> str:
        assert meow == 1233212
        assert meowmeow is mock_value
        return "yay"

    context.injection_client.set_type_dependency(mock_other_type, mock_value)

    result = await context.execute_async(callback, 1233212)

    assert result == "yay"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_shorthand_annotated_union_type_dependency_not_found(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()

    async def callback(
        yeee: str,
        nyaa: bool,
        yeet: alluka.Injected[typing.Union[mock_type, mock_other_type]],
    ) -> str:
        raise NotImplementedError

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        await context.execute_async(callback, yeee="yeee", nyaa=True)

    assert exc_info.value.dependency_type == typing.Union[mock_type, mock_other_type]
    assert (
        exc_info.value.message
        == f"Couldn't resolve injected type(s) {typing.Union[mock_type, mock_other_type]} to actual value"
    )


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_shorthand_annotated_defaulting_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_type, mock_value)

    async def callback(
        eaaaa: str,
        nyaa: bool,
        yeet: alluka.Injected[typing.Optional[mock_type]],
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_value
        return "aaaaa"

    result = await context.execute_async(callback, "easd", nyaa=False)

    assert result == "aaaaa"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_shorthand_annotated_defaulting_type_dependency_not_found(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()

    async def callback(
        eaaaa: str,
        nyaa: bool,
        yeet: alluka.Injected[typing.Optional[mock_type]],
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is None
        return "aaaaa"

    result = await context.execute_async(callback, "easd", nyaa=False)

    assert result == "aaaaa"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_shorthand_annotated_natural_defaulting_type_dependency(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_type, mock_value)

    async def callback(
        eaaaa: str,
        nyaa: bool,
        yeet: alluka.Injected[mock_type] = "default",
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_value
        return "aaaaa"

    result = await context.execute_async(callback, "easd", nyaa=False)

    assert result == "aaaaa"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_shorthand_annotated_natural_defaulting_type_dependency_not_found(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()

    async def callback(
        eaaaa: str,
        nyaa: bool,
        yeet: alluka.Injected[mock_type] = 123,
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet == 123
        return "aaaaa"

    result = await context.execute_async(callback, "easd", nyaa=False)

    assert result == "aaaaa"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_shorthand_annotated_defaulting_union_type_dependency(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_other_type, mock_value)

    async def callback(
        vvvvv: int,
        value: alluka.Injected[typing.Union[mock_type, mock_other_type]],
    ) -> str:
        assert vvvvv == 123
        assert value is mock_value
        return "ea sports"

    result = await context.execute_async(callback, 123)

    assert result == "ea sports"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_shorthand_annotated_defaulting_union_type_dependency_not_found(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()

    async def callback(
        vvvvv: int,
        value: alluka.Injected[typing.Optional[mock_type]],
    ) -> str:
        assert vvvvv == 123
        assert value is None
        return "yeeee"

    result = await context.execute_async(callback, 123)

    assert result == "yeeee"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_shorthand_annotated_natural_defaulting_union_type_dependency(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_other_type, mock_value)

    async def callback(
        vvvvv: int,
        value: alluka.Injected[typing.Union[mock_type, mock_other_type]] = "default",
    ) -> str:
        assert vvvvv == 123
        assert value is mock_value
        return "ea sports"

    result = await context.execute_async(callback, 123)

    assert result == "ea sports"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_shorthand_annotated_natural_defaulting_union_type_dependency_not_found(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()

    async def callback(
        vvvvv: int,
        value: alluka.Injected[typing.Union[mock_type, mock_other_type, None]] = "default 2",
    ) -> str:
        assert vvvvv == 123
        assert value == "default 2"
        return "yeeee"

    result = await context.execute_async(callback, 123)

    assert result == "yeeee"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_callback_dependency(context: alluka.BasicContext):
    mock_callback = mock.AsyncMock()

    async def callback(foo: int, result: int = alluka.inject(callback=mock_callback)) -> int:
        assert foo == 123
        assert result is mock_callback.return_value
        return 43123

    result = await context.execute_async(callback, 123)

    assert result == 43123
    mock_callback.assert_awaited_once()


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_sub_callback_dependency(context: alluka.BasicContext):
    mock_callback = mock.Mock()

    async def dependency(result: int = alluka.inject(callback=mock_callback)) -> int:
        assert result is mock_callback.return_value
        return 541232

    async def callback(foo: int, result: int = alluka.inject(callback=dependency)) -> str:
        assert foo == 123
        assert result == 541232
        return "43123"

    result = await context.execute_async(callback, 123)

    assert result == "43123"
    mock_callback.assert_called_once_with()


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_callback_dependency(context: alluka.BasicContext):
    mock_callback = mock.AsyncMock()

    async def callback(foo: int, result: typing.Annotated[int, alluka.inject(callback=mock_callback)]) -> int:
        assert foo == 123
        assert result is mock_callback.return_value
        return 43123

    result = await context.execute_async(callback, 123)

    assert result == 43123
    mock_callback.assert_awaited_once_with()


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_sub_callback_dependency(context: alluka.BasicContext):
    mock_callback = mock.AsyncMock()

    async def dependency(result: typing.Annotated[int, alluka.inject(callback=mock_callback)]) -> int:
        assert result is mock_callback.return_value
        return 541232

    async def callback(foo: int, result: typing.Annotated[int, alluka.inject(callback=dependency)]) -> str:
        assert foo == 123
        assert result == 541232
        return "43123"

    result = await context.execute_async(callback, 123)

    assert result == "43123"
    mock_callback.assert_awaited_once()


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_sub_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_type, mock_value)

    async def dependency(result: int = alluka.inject(type=mock_type)) -> int:
        assert result is mock_value
        return 123321

    async def callback(foo: int, result: int = alluka.inject(callback=dependency)) -> str:
        assert foo == 54123
        assert result == 123321
        return "asddsa"

    result = await context.execute_async(callback, 54123)

    assert result == "asddsa"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_sub_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()

    async def dependency(result: int = alluka.inject(type=mock_type)) -> int:
        raise NotImplementedError

    async def callback(foo: int, result: int = alluka.inject(callback=dependency)) -> str:
        raise NotImplementedError

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        await context.execute_async(callback, 54123)

    assert exc_info.value.dependency_type is mock_type
    assert exc_info.value.message == (f"Couldn't resolve injected type(s) {mock_type} to actual value")


@pytest.mark.anyio()
async def test_execute_with_ctx_async_when_sync_callback(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_callback = mock.AsyncMock()
    context.injection_client.set_type_dependency(mock_type, mock_value)

    async def dependency(foo: int = alluka.inject(callback=mock_callback)) -> str:
        assert foo is mock_callback.return_value
        return "Ok"

    def callback(
        baz: int, bar: str, foo: alluka.Injected[mock_type], bat: str = alluka.inject(callback=dependency)
    ) -> float:
        assert baz == 1234321
        assert bar == "meow meow"
        assert foo is mock_value
        assert bat == "Ok"
        return 123.321

    result = await context.execute_async(callback, 1234321, bar="meow meow")

    assert result == 123.321
    mock_callback.assert_awaited_once_with()


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_sync_dependency_callback(context: alluka.BasicContext):
    mock_type_1: typing.Any = mock.Mock()
    mock_value_1 = mock.Mock()
    mock_type_2: typing.Any = mock.Mock()
    mock_value_2 = mock.Mock()
    context.injection_client.set_type_dependency(mock_type_1, mock_value_1).set_type_dependency(
        mock_type_2, mock_value_2
    )

    def dependency(foo: alluka.Injected[mock_type_2]) -> str:
        assert foo is mock_value_2
        return "eeeeaaaa"

    async def callback(foo: alluka.Injected[mock_type_1], bar: str = alluka.inject(callback=dependency)) -> str:
        assert foo is mock_value_1
        assert bar == "eeeeaaaa"
        return "bye bye"

    result = await context.execute_async(callback)

    assert result == "bye bye"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_overridden_sync_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_callback = mock.AsyncMock()
    mock_override = mock.Mock()
    context.injection_client.set_type_dependency(mock_type, mock_value).set_callback_override(
        mock_callback, mock_override
    )

    async def callback(foo: alluka.Injected[mock_type], bar: str = alluka.inject(callback=mock_callback)) -> str:
        assert foo is mock_value
        assert bar is mock_override.return_value
        return "bye bye"

    result = await context.execute_async(callback)

    assert result == "bye bye"
    mock_override.assert_called_once_with()


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_sub_sync_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_callback = mock.AsyncMock()
    context.injection_client.set_type_dependency(mock_type, mock_value)

    def dependency(result: str = alluka.inject(callback=mock_callback)) -> str:
        assert result is mock_callback.return_value
        return "go home"

    async def callback(foo: alluka.Injected[mock_type], bar: str = alluka.inject(callback=dependency)) -> str:
        assert foo is mock_value
        assert bar == "go home"
        return "bye bye"

    result = await context.execute_async(callback)

    assert result == "bye bye"
    mock_callback.assert_called_once_with()


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_overridden_sub_sync_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_callback = mock.AsyncMock()
    mock_override = mock.Mock()
    context.injection_client.set_type_dependency(mock_type, mock_value).set_callback_override(
        mock_callback, mock_override
    )

    def dependency(result: typing.Annotated[str, alluka.inject(callback=mock_callback)]) -> str:
        assert result is mock_override.return_value
        return "go home"

    async def callback(foo: alluka.Injected[mock_type], bar: str = alluka.inject(callback=dependency)) -> str:
        assert foo is mock_value
        assert bar == "go home"
        return "bye bye"

    result = await context.execute_async(callback)

    assert result == "bye bye"
    mock_override.assert_called_once_with()


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_sync_dependency(context: alluka.BasicContext):
    mock_type_1: typing.Any = mock.Mock()
    mock_value_1 = mock.Mock()
    mock_type_2: typing.Any = mock.Mock()
    mock_value_2 = mock.Mock()
    context.injection_client.set_type_dependency(mock_type_1, mock_value_1).set_type_dependency(
        mock_type_2, mock_value_2
    )

    def dependency(foo: alluka.Injected[mock_type_2]) -> str:
        assert foo is mock_value_2
        return "eeeeaaaa"

    async def callback(
        foo: alluka.Injected[mock_type_1], bar: typing.Annotated[str, alluka.inject(callback=dependency)]
    ) -> str:
        assert foo is mock_value_1
        assert bar == "eeeeaaaa"
        return "bye bye"

    result = await context.execute_async(callback)

    assert result == "bye bye"


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_overridden_annotated_sync_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_callback = mock.AsyncMock()
    mock_override = mock.Mock()
    context.injection_client.set_type_dependency(mock_type, mock_value).set_callback_override(
        mock_callback, mock_override
    )

    async def callback(
        foo: alluka.Injected[mock_type], bar: typing.Annotated[str, alluka.inject(callback=mock_callback)]
    ) -> str:
        assert foo is mock_value
        assert bar is mock_override.return_value
        return "bye bye"

    result = await context.execute_async(callback)

    assert result == "bye bye"
    mock_override.assert_called_once_with()


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_annotated_sub_sync_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_callback = mock.AsyncMock()
    context.injection_client.set_type_dependency(mock_type, mock_value)

    def dependency(result: str = alluka.inject(callback=mock_callback)) -> str:
        assert result is mock_callback.return_value
        return "go home"

    async def callback(
        foo: alluka.Injected[mock_type], bar: typing.Annotated[str, alluka.inject(callback=dependency)]
    ) -> str:
        assert foo is mock_value
        assert bar == "go home"
        return "bye bye"

    result = await context.execute_async(callback)

    assert result == "bye bye"
    mock_callback.assert_called_once_with()


@pytest.mark.anyio()
async def test_execute_with_ctx_async_with_overridden_annotated_sub_sync_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_callback = mock.AsyncMock()
    mock_override = mock.Mock()
    context.injection_client.set_type_dependency(mock_type, mock_value).set_callback_override(
        mock_callback, mock_override
    )

    def dependency(result: typing.Annotated[str, alluka.inject(callback=mock_callback)]) -> str:
        assert result is mock_override.return_value
        return "go home"

    async def callback(
        foo: alluka.Injected[mock_type], bar: typing.Annotated[str, alluka.inject(callback=dependency)]
    ) -> str:
        assert foo is mock_value
        assert bar == "go home"
        return "bye bye"

    result = await context.execute_async(callback)

    assert result == "bye bye"
    mock_override.assert_called_once_with()


################################
# Positional-only dependencies #
################################


@pytest.mark.anyio()
async def test_execute_with_ctx_with_positional_only_type_dependency(context: alluka.BasicContext):
    async def callback(
        foo: int, bar: str = alluka.inject(type=float), /, baz: float = alluka.inject(type=float)
    ) -> None:
        raise NotImplementedError

    with pytest.raises(ValueError, match="Injected positional only arguments are not supported"):
        await context.execute_async(callback)


@pytest.mark.anyio()
async def test_execute_with_ctx_with_positional_only_callback_dependency(context: alluka.BasicContext):
    mock_dependency = mock.Mock()

    async def callback(
        foo: int, bar: str = alluka.inject(callback=mock_dependency), /, baz: float = alluka.inject(type=float)
    ) -> None:
        raise NotImplementedError

    with pytest.raises(ValueError, match="Injected positional only arguments are not supported"):
        await context.execute_async(callback)


@pytest.mark.anyio()
async def test_execute_with_ctx_with_sub_positional_only_callback_dependency(context: alluka.BasicContext):
    sub_dependency = mock.Mock()

    async def dependency(baz: str = alluka.inject(callback=sub_dependency), /) -> str:
        raise NotImplementedError

    async def callback(
        foo: int, bar: str = alluka.inject(callback=dependency), /, baz: float = alluka.inject(type=float)
    ) -> None:
        raise NotImplementedError

    with pytest.raises(ValueError, match="Injected positional only arguments are not supported"):
        await context.execute_async(callback)


@pytest.mark.anyio()
async def test_execute_with_ctx_with_sub_positional_only_type_dependency(context: alluka.BasicContext):
    async def dependency(baz: str = alluka.inject(type=int), /) -> str:
        raise NotImplementedError

    async def callback(
        foo: int, bar: str = alluka.inject(callback=dependency), /, baz: float = alluka.inject(type=float)
    ) -> None:
        raise NotImplementedError

    with pytest.raises(ValueError, match="Injected positional only arguments are not supported"):
        await context.execute_async(callback)

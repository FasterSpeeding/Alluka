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
import warnings
from unittest import mock

import pytest

import alluka

# pyright: reportUnknownMemberType=none
# pyright: reportPrivateUsage=none
# pyright: reportIncompatibleMethodOverride=none


#############################
# Sync dependency injection #
#############################


@pytest.fixture()
def client() -> alluka.Client:
    return alluka.Client()


@pytest.fixture()
def context(client: alluka.Client) -> alluka.BasicContext:
    return alluka.BasicContext(client)


# TODO: test cases for type scoped dependencies
# TODO: test cases for cached callback results
def test_execute_with_ctx_when_no_di(context: alluka.BasicContext):
    def callback(x: int, bar: str) -> str:
        assert x == 42
        assert bar == "ok"
        return "nyaa"

    result = context.execute(callback, 42, bar="ok")

    assert result == "nyaa"


def test_execute_prioritises_defaults_over_annotations(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()
    mock_callback = mock.Mock()

    def dependency(
        result: typing.Annotated[float, alluka.inject(type=123)] = alluka.inject(callback=mock_callback)
    ) -> str:
        assert result is mock_callback.return_value
        return "sexual catgirls"

    def callback(
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

    (
        context.injection_client.set_type_dependency(mock_type, mock_value).set_type_dependency(
            mock_other_type, mock_other_value
        )
    )

    result = context.execute(callback, 69, bar="rew")

    assert result == "meow"
    mock_callback.assert_called_once_with()


def test_execute_with_ctx_with_type_dependency_and_callback(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()
    mock_callback = mock.Mock()

    def callback(
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

    (
        context.injection_client.set_type_dependency(mock_type, mock_value).set_type_dependency(
            mock_other_type, mock_other_value
        )
    )

    result = context.execute(callback, 69, bar="rew")

    assert result == "meow"
    mock_callback.assert_called_once_with()


def test_execute_with_ctx_with_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()

    def callback(
        x: int, bar: str, baz: str = alluka.inject(type=mock_type), bat: int = alluka.inject(type=mock_other_type)
    ) -> str:
        assert x == 69
        assert bar == "rew"
        assert baz is mock_value
        assert bat is mock_other_value
        return "meow"

    (
        context.injection_client.set_type_dependency(mock_type, mock_value).set_type_dependency(
            mock_other_type, mock_other_value
        )
    )

    result = context.execute(callback, 69, bar="rew")

    assert result == "meow"


def test_execute_with_ctx_with_type_dependency_inferred_from_type(context: alluka.BasicContext):
    mock_global_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_global_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()

    def callback(
        nyaa: str, meow: int, baz: mock_global_type = alluka.inject(), bat: mock_other_global_type = alluka.inject()
    ) -> str:
        assert nyaa == "5412"
        assert meow == 34123
        assert baz is mock_value
        assert bat is mock_other_value
        return "heeee"

    (
        context.injection_client.set_type_dependency(mock_global_type, mock_value).set_type_dependency(
            mock_other_global_type, mock_other_value
        )
    )

    result = context.execute(callback, "5412", meow=34123)

    assert result == "heeee"


def test_execute_with_ctx_with_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()

    def callback(
        x: int, bar: str, baz: str = alluka.inject(type=mock_type), bat: int = alluka.inject(type=mock_other_type)
    ) -> str:
        raise NotImplementedError

    context.injection_client.set_type_dependency(mock_type, mock_value)

    with pytest.raises(alluka.MissingDependencyError) as exc:
        context.execute(callback, 69, bar="rew")

    assert exc.value.message == f"Couldn't resolve injected type(s) {mock_other_type} to actual value"
    assert exc.value.dependency_type is mock_other_type


def test_execute_with_ctx_with_defaulting_type_dependency(context: alluka.BasicContext):  # TODO: THIS
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()

    def callback(x: int, bar: str, bat: typing.Optional[int] = alluka.inject(type=typing.Optional[mock_type])) -> str:
        assert x == 69
        assert bar == "rew"
        assert bat is mock_value
        return "meow"

    context.injection_client.set_type_dependency(mock_type, mock_value)

    result = context.execute(callback, 69, bar="rew")

    assert result == "meow"


def test_execute_with_ctx_with_defaulting_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()

    def callback(
        yeet: int, raw: str, bat: typing.Optional[int] = alluka.inject(type=typing.Optional[mock_type])
    ) -> str:
        assert yeet == 420
        assert raw == "uwu"
        assert bat is None
        return "yeet"

    result = context.execute(callback, 420, raw="uwu")

    assert result == "yeet"


def test_execute_with_ctx_with_union_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_other_type, mock_value)

    def callback(bar: int, baz: str, cope: int = alluka.inject(type=typing.Union[mock_type, mock_other_type])) -> float:
        assert bar == 123
        assert baz == "ok"
        assert cope is mock_value
        return 243.234

    result = context.execute(callback, 123, "ok")

    assert result == 243.234


# These tests covers syntax which was introduced in 3.10
if sys.version_info >= (3, 10):  # TODO: do we want to dupe other test cases for |?

    def test_execute_with_ctx_with_3_10_union_type_dependency(context: alluka.BasicContext):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_value = StubType()

        context.injection_client.set_type_dependency(StubType, mock_value)

        def callback(bar: int, baz: str, cope: int = alluka.inject(type=StubOtherType | StubType)) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_value
            return 451.123

        result = context.execute(callback, 123, "ok")

        assert result == 451.123

    def test_execute_with_ctx_with_3_10_union_type_dependency_not_found(context: alluka.BasicContext):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_value = StubType()

        def callback(bar: int, baz: str, cope: int = alluka.inject(type=StubOtherType | StubType)) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_value
            return 451.123

        with pytest.raises(alluka.MissingDependencyError) as exc_info:
            context.execute(callback, 123, "ok")

        assert exc_info.value.dependency_type == StubOtherType | StubType
        assert exc_info.value.message == f"Couldn't resolve injected type(s) {StubOtherType | StubType} to actual value"

    def test_execute_with_ctx_with_3_10_union_type_dependency_defaulting(context: alluka.BasicContext):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_value = StubType()

        context.injection_client.set_type_dependency(StubType, mock_value)

        def callback(bar: int, baz: str, cope: int = alluka.inject(type=StubOtherType | StubType | None)) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_value
            return 451.123

        result = context.execute(callback, 123, "ok")

        assert result == 451.123

    def test_execute_with_ctx_with_3_10_union_type_dependency_defaulting_not_found(context: alluka.BasicContext):
        class StubType:
            ...

        class StubOtherType:
            ...

        def callback(bar: int, baz: str, cope: int = alluka.inject(type=StubOtherType | StubType | None)) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is None
            return 451.123

        result = context.execute(callback, 123, "ok")

        assert result == 451.123


def test_execute_with_ctx_with_union_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()

    def callback(bar: int, baz: str, cope: int = alluka.inject(type=typing.Union[mock_type, mock_other_type])) -> float:
        raise NotImplementedError

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        context.execute(callback, 123, "ok")

    assert exc_info.value.dependency_type == typing.Union[mock_type, mock_other_type]
    assert exc_info.value.message == (
        f"Couldn't resolve injected type(s) {typing.Union[mock_type, mock_other_type]} to actual value"
    )


def test_execute_with_ctx_with_defaulting_union_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_other_type, mock_value)

    def callback(
        bar: int, baz: str, cope: int = alluka.inject(type=typing.Union[mock_type, mock_other_type, None])
    ) -> float:
        assert bar == 123
        assert baz == "ok"
        assert cope is mock_value
        return 243.234

    result = context.execute(callback, 123, "ok")

    assert result == 243.234


def test_execute_with_ctx_with_defaulting_union_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()

    def callback(
        bar: float, baz: int, cope: typing.Optional[int] = alluka.inject(type=typing.Optional[mock_type])
    ) -> float:
        assert bar == 123.321
        assert baz == 543
        assert cope is None
        return 321.123

    result = context.execute(callback, 123.321, 543)

    assert result == 321.123


def test_execute_with_ctx_with_annotated_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()

    def callback(
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

    (
        context.injection_client.set_type_dependency(mock_type, mock_value).set_type_dependency(
            mock_other_type, mock_other_value
        )
    )

    result = context.execute(callback, rawr=69, xd="rew")

    assert result == "meow"


def test_execute_with_ctx_with_annotated_type_dependency_inferred_from_type(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()

    def callback(
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

    (
        context.injection_client.set_type_dependency(mock_type, mock_value).set_type_dependency(
            mock_other_type, mock_other_value
        )
    )

    result = context.execute(callback, meow=2222, nyaa="xxxxx")

    assert result == "wewewewew"


def test_execute_with_ctx_with_annotated_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()

    def callback(
        meow: int,
        nyaa: float,
        meowmeow: typing.Annotated[int, alluka.inject(type=mock_type)],
        imacow: typing.Annotated[str, alluka.inject(type=mock_other_type)],
    ) -> str:
        raise NotImplementedError

    context.injection_client.set_type_dependency(mock_other_type, mock_other_value)

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        context.execute(callback, meow=2222, nyaa="xxxxx")

    assert exc_info.value.dependency_type is mock_type
    assert exc_info.value.message == f"Couldn't resolve injected type(s) {mock_type} to actual value"


def test_execute_with_ctx_with_annotated_union_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()

    def callback(
        meow: int,
        meowmeow: typing.Annotated[typing.Union[mock_type, mock_other_type], alluka.inject()],
    ) -> str:
        assert meow == 1233212
        assert meowmeow is mock_value
        return "yay"

    context.injection_client.set_type_dependency(mock_other_type, mock_value)

    result = context.execute(callback, 1233212)

    assert result == "yay"


# These tests covers syntax which was introduced in 3.10
if sys.version_info >= (3, 10):  # TODO: do we want to dupe other test cases for |?

    def test_execute_with_ctx_with_annotated_3_10_union_type_dependency(context: alluka.BasicContext):
        class StubType:
            ...

        mock_value = StubType()

        class StubOtherType:
            ...

        def callback(
            yeee: str,
            nyaa: bool,
            yeet: typing.Annotated[str, alluka.inject(type=StubType | StubOtherType)],
        ) -> str:
            assert yeee == "yeee"
            assert nyaa is True
            assert yeet is mock_value
            return "hey"

        context.injection_client.set_type_dependency(StubOtherType, mock_value)

        result = context.execute(callback, yeee="yeee", nyaa=True)

        assert result == "hey"

    def test_execute_with_ctx_with_annotated_3_10_union_type_dependency_not_found(context: alluka.BasicContext):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_value = StubType()

        def callback(
            bar: int, baz: str, cope: typing.Annotated[int, alluka.inject(type=StubOtherType | StubType)]
        ) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_value
            return 451.123

        with pytest.raises(alluka.MissingDependencyError) as exc_info:
            context.execute(callback, 123, "ok")

        assert exc_info.value.dependency_type == StubOtherType | StubType
        assert exc_info.value.message == f"Couldn't resolve injected type(s) {StubOtherType | StubType} to actual value"

    def test_execute_with_ctx_with_annotated_3_10_union_type_dependency_defaulting(context: alluka.BasicContext):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_value = StubType()

        context.injection_client.set_type_dependency(StubType, mock_value)

        def callback(
            bar: int, baz: str, cope: typing.Annotated[int, alluka.inject(type=StubOtherType | StubType | None)]
        ) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_value
            return 451.123

        result = context.execute(callback, 123, "ok")

        assert result == 451.123

    def test_execute_with_ctx_with_annotated_3_10_union_type_dependency_defaulting_not_found(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        def callback(
            bar: int, baz: str, cope: typing.Annotated[int, alluka.inject(type=StubOtherType | StubType | None)]
        ) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is None
            return 451.123

        result = context.execute(callback, 123, "ok")

        assert result == 451.123

    def test_execute_with_ctx_with_annotated_3_10_union_type_dependency_natural_defaulting(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_value = StubType()

        context.injection_client.set_type_dependency(StubType, mock_value)

        def callback(
            bar: int, baz: str, cope: typing.Annotated[int, alluka.inject(type=StubOtherType | StubType | None)] = 123
        ) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_value
            return 451.123

        result = context.execute(callback, 123, "ok")

        assert result == 451.123

    def test_execute_with_ctx_with_annotated_3_10_union_type_dependency_natural_defaulting_not_found(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        def callback(
            bar: int, baz: str, cope: typing.Annotated[int, alluka.inject(type=StubOtherType | StubType)] = 43123
        ) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope == 43123
            return 451.123

        result = context.execute(callback, 123, "ok")

        assert result == 451.123


def test_execute_with_ctx_with_annotated_union_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()

    def callback(
        yeee: str,
        nyaa: bool,
        yeet: typing.Annotated[int, alluka.inject(type=typing.Union[mock_type, mock_other_type])],
    ) -> str:
        raise NotImplementedError

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        context.execute(callback, yeee="yeee", nyaa=True)

    assert exc_info.value.dependency_type == typing.Union[mock_type, mock_other_type]
    assert (
        exc_info.value.message
        == f"Couldn't resolve injected type(s) {typing.Union[mock_type, mock_other_type]} to actual value"
    )


def test_execute_with_ctx_with_annotated_defaulting_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_type, mock_value)

    def callback(
        eaaaa: str,
        nyaa: bool,
        yeet: typing.Annotated[str, alluka.inject(type=typing.Optional[mock_type])],
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_value
        return "aaaaa"

    result = context.execute(callback, "easd", nyaa=False)

    assert result == "aaaaa"


def test_execute_with_ctx_with_annotated_defaulting_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()

    def callback(
        eaaaa: str,
        nyaa: bool,
        yeet: typing.Annotated[str, alluka.inject(type=typing.Optional[mock_type])],
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is None
        return "aaaaa"

    result = context.execute(callback, "easd", nyaa=False)

    assert result == "aaaaa"


def test_execute_with_ctx_with_annotated_natural_defaulting_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_type, mock_value)

    def callback(
        eaaaa: str,
        nyaa: bool,
        yeet: typing.Annotated[str, alluka.inject(type=mock_type)] = "default",
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_value
        return "aaaaa"

    result = context.execute(callback, "easd", nyaa=False)

    assert result == "aaaaa"


def test_execute_with_ctx_with_annotated_natural_defaulting_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()

    def callback(
        eaaaa: str,
        nyaa: bool,
        yeet: typing.Annotated[int, alluka.inject(type=mock_type)] = 123,
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet == 123
        return "aaaaa"

    result = context.execute(callback, "easd", nyaa=False)

    assert result == "aaaaa"


def test_execute_with_ctx_with_annotated_defaulting_union_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_other_type, mock_value)

    def callback(
        vvvvv: int,
        value: typing.Annotated[str, alluka.inject(type=typing.Union[mock_type, mock_other_type])],
    ) -> str:
        assert vvvvv == 123
        assert value is mock_value
        return "ea sports"

    result = context.execute(callback, 123)

    assert result == "ea sports"


def test_execute_with_ctx_with_annotated_defaulting_union_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()

    def callback(
        vvvvv: int,
        value: typing.Annotated[str, alluka.inject(type=typing.Optional[mock_type])],
    ) -> str:
        assert vvvvv == 123
        assert value is None
        return "yeeee"

    result = context.execute(callback, 123)

    assert result == "yeeee"


def test_execute_with_ctx_with_annotated_natural_defaulting_union_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_other_type, mock_value)

    def callback(
        vvvvv: int,
        value: typing.Annotated[str, alluka.inject(type=typing.Union[mock_type, mock_other_type])] = "default",
    ) -> str:
        assert vvvvv == 123
        assert value is mock_value
        return "ea sports"

    result = context.execute(callback, 123)

    assert result == "ea sports"


def test_execute_with_ctx_with_annotated_natural_defaulting_union_type_dependency_not_found(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()

    def callback(
        vvvvv: int,
        value: typing.Annotated[str, alluka.inject(type=typing.Union[mock_type, mock_other_type, None])] = "default 2",
    ) -> str:
        assert vvvvv == 123
        assert value == "default 2"
        return "yeeee"

    result = context.execute(callback, 123)

    assert result == "yeeee"


def test_execute_with_ctx_with_shorthand_annotated_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()

    def callback(
        rawr: int, xd: float, meowmeow: alluka.Injected[mock_type], other: alluka.Injected[mock_other_type]
    ) -> str:
        assert rawr == 1233212
        assert xd == "seee"
        assert meowmeow is mock_value
        assert other is mock_other_value
        return "eeesss"

    (
        context.injection_client.set_type_dependency(mock_type, mock_value).set_type_dependency(
            mock_other_type, mock_other_value
        )
    )

    result = context.execute(callback, 1233212, xd="seee")

    assert result == "eeesss"


def test_execute_with_ctx_with_shorthand_annotated_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_other_value = mock.Mock()

    def callback(
        meow: int,
        nyaa: float,
        meowmeow: alluka.Injected[mock_type],
        imacow: alluka.Injected[mock_other_type],
    ) -> str:
        raise NotImplementedError

    context.injection_client.set_type_dependency(mock_other_type, mock_other_value)

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        context.execute(callback, meow=2222, nyaa="xxxxx")

    assert exc_info.value.dependency_type is mock_type
    assert exc_info.value.message == f"Couldn't resolve injected type(s) {mock_type} to actual value"


def test_execute_with_ctx_with_shorthand_annotated_union_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()

    def callback(
        meow: int,
        meowmeow: alluka.Injected[typing.Union[mock_type, mock_other_type]],
    ) -> str:
        assert meow == 1233212
        assert meowmeow is mock_value
        return "yay"

    context.injection_client.set_type_dependency(mock_other_type, mock_value)

    result = context.execute(callback, 1233212)

    assert result == "yay"


# These tests covers syntax which was introduced in 3.10
if sys.version_info >= (3, 10):  # TODO: do we want to dupe other test cases for |?

    def test_execute_with_ctx_with_shorthand_annotated_3_10_union_type_dependency(context: alluka.BasicContext):
        class StubType:
            ...

        mock_value = StubType()

        class StubOtherType:
            ...

        def callback(
            yeee: str,
            nyaa: bool,
            yeet: alluka.Injected[StubType | StubOtherType],
        ) -> str:
            assert yeee == "yeee"
            assert nyaa is True
            assert yeet is mock_value
            return "hey"

        context.injection_client.set_type_dependency(StubOtherType, mock_value)

        result = context.execute(callback, yeee="yeee", nyaa=True)

        assert result == "hey"

    def test_execute_with_ctx_with_shorthand_annotated_3_10_union_type_dependency_not_found(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_value = StubType()

        def callback(bar: int, baz: str, cope: alluka.Injected[StubOtherType | StubType]) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_value
            return 451.123

        with pytest.raises(alluka.MissingDependencyError) as exc_info:
            context.execute(callback, 123, "ok")

        assert exc_info.value.dependency_type == StubOtherType | StubType
        assert exc_info.value.message == f"Couldn't resolve injected type(s) {StubOtherType | StubType} to actual value"

    def test_execute_with_ctx_with_shorthand_annotated_3_10_union_type_dependency_defaulting(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_value = StubType()

        context.injection_client.set_type_dependency(StubType, mock_value)

        def callback(bar: int, baz: str, cope: alluka.Injected[StubOtherType | StubType | None]) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_value
            return 451.123

        result = context.execute(callback, 123, "ok")

        assert result == 451.123

    def test_execute_with_ctx_with_shorthand_annotated_3_10_union_type_dependency_defaulting_not_found(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        def callback(bar: int, baz: str, cope: alluka.Injected[StubOtherType | StubType | None]) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is None
            return 451.123

        result = context.execute(callback, 123, "ok")

        assert result == 451.123

    def test_execute_with_ctx_with_shorthand_annotated_3_10_union_type_dependency_natural_defaulting(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_value = StubType()

        context.injection_client.set_type_dependency(StubType, mock_value)

        def callback(bar: int, baz: str, cope: alluka.Injected[StubOtherType | StubType | None] = 123) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_value
            return 451.123

        result = context.execute(callback, 123, "ok")

        assert result == 451.123

    def test_execute_with_ctx_with_shorthand_annotated_3_10_union_type_dependency_natural_defaulting_not_found(
        context: alluka.BasicContext,
    ):
        class StubType:
            ...

        class StubOtherType:
            ...

        mock_default = mock.Mock()

        def callback(bar: int, baz: str, cope: alluka.Injected[StubOtherType | StubType] = mock_default) -> float:
            assert bar == 123
            assert baz == "ok"
            assert cope is mock_default
            return 451.123

        result = context.execute(callback, 123, "ok")

        assert result == 451.123


def test_execute_with_ctx_with_shorthand_annotated_union_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()

    def callback(
        yeee: str,
        nyaa: bool,
        yeet: alluka.Injected[typing.Union[mock_type, mock_other_type]],
    ) -> str:
        raise NotImplementedError

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        context.execute(callback, yeee="yeee", nyaa=True)

    assert exc_info.value.dependency_type == typing.Union[mock_type, mock_other_type]
    assert (
        exc_info.value.message
        == f"Couldn't resolve injected type(s) {typing.Union[mock_type, mock_other_type]} to actual value"
    )


def test_execute_with_ctx_with_shorthand_annotated_defaulting_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_type, mock_value)

    def callback(
        eaaaa: str,
        nyaa: bool,
        yeet: alluka.Injected[typing.Optional[mock_type]],
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_value
        return "aaaaa"

    result = context.execute(callback, "easd", nyaa=False)

    assert result == "aaaaa"


def test_execute_with_ctx_with_shorthand_annotated_defaulting_type_dependency_not_found(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()

    def callback(
        eaaaa: str,
        nyaa: bool,
        yeet: alluka.Injected[typing.Optional[mock_type]],
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is None
        return "aaaaa"

    result = context.execute(callback, "easd", nyaa=False)

    assert result == "aaaaa"


def test_execute_with_ctx_with_shorthand_annotated_natural_defaulting_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_type, mock_value)

    def callback(
        eaaaa: str,
        nyaa: bool,
        yeet: alluka.Injected[mock_type] = "default",
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet is mock_value
        return "aaaaa"

    result = context.execute(callback, "easd", nyaa=False)

    assert result == "aaaaa"


def test_execute_with_ctx_with_shorthand_annotated_natural_defaulting_type_dependency_not_found(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()

    def callback(
        eaaaa: str,
        nyaa: bool,
        yeet: alluka.Injected[mock_type] = 123,
    ) -> str:
        assert eaaaa == "easd"
        assert nyaa is False
        assert yeet == 123
        return "aaaaa"

    result = context.execute(callback, "easd", nyaa=False)

    assert result == "aaaaa"


def test_execute_with_ctx_with_shorthand_annotated_defaulting_union_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_other_type, mock_value)

    def callback(
        vvvvv: int,
        value: alluka.Injected[typing.Union[mock_type, mock_other_type]],
    ) -> str:
        assert vvvvv == 123
        assert value is mock_value
        return "ea sports"

    result = context.execute(callback, 123)

    assert result == "ea sports"


def test_execute_with_ctx_with_shorthand_annotated_defaulting_union_type_dependency_not_found(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()

    def callback(
        vvvvv: int,
        value: alluka.Injected[typing.Optional[mock_type]],
    ) -> str:
        assert vvvvv == 123
        assert value is None
        return "yeeee"

    result = context.execute(callback, 123)

    assert result == "yeeee"


def test_execute_with_ctx_with_shorthand_annotated_natural_defaulting_union_type_dependency(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_other_type, mock_value)

    def callback(
        vvvvv: int,
        value: alluka.Injected[typing.Union[mock_type, mock_other_type]] = "default",
    ) -> str:
        assert vvvvv == 123
        assert value is mock_value
        return "ea sports"

    result = context.execute(callback, 123)

    assert result == "ea sports"


def test_execute_with_ctx_with_shorthand_annotated_natural_defaulting_union_type_dependency_not_found(
    context: alluka.BasicContext,
):
    mock_type: typing.Any = mock.Mock()
    mock_other_type: typing.Any = mock.Mock()

    def callback(
        vvvvv: int,
        value: alluka.Injected[typing.Union[mock_type, mock_other_type, None]] = "default 2",
    ) -> str:
        assert vvvvv == 123
        assert value == "default 2"
        return "yeeee"

    result = context.execute(callback, 123)

    assert result == "yeeee"


def test_execute_with_ctx_with_callback_dependency(context: alluka.BasicContext):
    mock_callback = mock.Mock()

    def callback(foo: int, result: int = alluka.inject(callback=mock_callback)) -> int:
        assert foo == 123
        assert result is mock_callback.return_value
        return 43123

    result = context.execute(callback, 123)

    assert result == 43123


def test_execute_with_ctx_with_sub_callback_dependency(context: alluka.BasicContext):
    mock_callback = mock.Mock()

    def dependency(result: int = alluka.inject(callback=mock_callback)) -> int:
        assert result is mock_callback.return_value
        return 541232

    def callback(foo: int, result: int = alluka.inject(callback=dependency)) -> str:
        assert foo == 123
        assert result == 541232
        return "43123"

    result = context.execute(callback, 123)

    assert result == "43123"


def test_execute_with_ctx_with_annotated_callback_dependency(context: alluka.BasicContext):
    mock_callback = mock.Mock()

    def callback(foo: int, result: typing.Annotated[int, alluka.inject(callback=mock_callback)]) -> int:
        assert foo == 123
        assert result is mock_callback.return_value
        return 43123

    result = context.execute(callback, 123)

    assert result == 43123


def test_execute_with_ctx_with_annotated_sub_callback_dependency(context: alluka.BasicContext):
    mock_callback = mock.Mock()

    def dependency(result: typing.Annotated[int, alluka.inject(callback=mock_callback)]) -> int:
        assert result is mock_callback.return_value
        return 541232

    def callback(foo: int, result: typing.Annotated[int, alluka.inject(callback=dependency)]) -> str:
        assert foo == 123
        assert result == 541232
        return "43123"

    result = context.execute(callback, 123)

    assert result == "43123"


def test_execute_with_ctx_with_sub_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()
    mock_value = mock.Mock()
    context.injection_client.set_type_dependency(mock_type, mock_value)

    def dependency(result: int = alluka.inject(type=mock_type)) -> int:
        assert result is mock_value
        return 123321

    def callback(foo: int, result: int = alluka.inject(callback=dependency)) -> str:
        assert foo == 54123
        assert result == 123321
        return "asddsa"

    result = context.execute(callback, 54123)

    assert result == "asddsa"


def test_execute_with_ctx_with_unknown_sub_type_dependency(context: alluka.BasicContext):
    mock_type: typing.Any = mock.Mock()

    def dependency(result: typing.Annotated[int, alluka.inject(type=mock_type)]) -> int:
        raise NotImplementedError

    def callback(foo: int, result: int = alluka.inject(callback=dependency)) -> str:
        raise NotImplementedError

    with pytest.raises(alluka.MissingDependencyError) as exc_info:
        context.execute(callback, 54123)

    assert exc_info.value.dependency_type is mock_type
    assert exc_info.value.message == (f"Couldn't resolve injected type(s) {mock_type} to actual value")


def test_execute_with_ctx_when_async_callback(context: alluka.BasicContext):
    async def callback() -> None:
        raise NotImplementedError

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        with pytest.raises(alluka.AsyncOnlyError):
            context.execute(callback)


def test_execute_with_ctx_with_async_dependency(context: alluka.BasicContext):
    async def async_dependency() -> None:
        raise NotImplementedError

    def callback(result: None = alluka.inject(callback=async_dependency)) -> None:
        raise NotImplementedError

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        with pytest.raises(alluka.AsyncOnlyError):
            context.execute(callback)


def test_execute_with_ctx_with_overridden_async_dependency(context: alluka.BasicContext):
    async def override() -> None:
        raise NotImplementedError

    def dependency() -> None:
        raise NotImplementedError

    def callback(result: None = alluka.inject(callback=dependency)) -> None:
        raise NotImplementedError

    context.injection_client.set_callback_override(dependency, override)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        with pytest.raises(alluka.AsyncOnlyError):
            context.execute(callback)


def test_execute_with_ctx_with_sub_async_dependency(context: alluka.BasicContext):
    async def async_sub_dependency() -> None:
        raise NotImplementedError

    def dependency(foo: None = alluka.inject(callback=async_sub_dependency)) -> None:
        raise NotImplementedError

    def callback(result: None = alluka.inject(callback=dependency)) -> None:
        raise NotImplementedError

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        with pytest.raises(alluka.AsyncOnlyError):
            context.execute(callback)


def test_execute_with_ctx_with_overridden_sub_async_dependency(context: alluka.BasicContext):
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

        with pytest.raises(alluka.AsyncOnlyError):
            context.execute(callback)


def test_execute_with_ctx_with_annotated_async_dependency(context: alluka.BasicContext):
    async def async_dependency() -> None:
        raise NotImplementedError

    def callback(result: typing.Annotated[None, alluka.inject(callback=async_dependency)]) -> None:
        raise NotImplementedError

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        with pytest.raises(alluka.AsyncOnlyError):
            context.execute(callback)


def test_execute_with_ctx_with_overridden_annotated_async_dependency(context: alluka.BasicContext):
    async def override() -> None:
        raise NotImplementedError

    def dependency() -> None:
        raise NotImplementedError

    def callback(result: None = alluka.inject(callback=dependency)) -> None:
        raise NotImplementedError

    context.injection_client.set_callback_override(dependency, override)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        with pytest.raises(alluka.AsyncOnlyError):
            context.execute(callback)


def test_execute_with_ctx_with_annotated_sub_async_dependency(context: alluka.BasicContext):
    async def async_sub_dependency() -> None:
        raise NotImplementedError

    def dependency(foo: typing.Annotated[None, alluka.inject(callback=async_sub_dependency)]) -> None:
        raise NotImplementedError

    def callback(result: typing.Annotated[None, alluka.inject(callback=dependency)]) -> None:
        raise NotImplementedError

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        with pytest.raises(alluka.AsyncOnlyError):
            context.execute(callback)


def test_execute_with_ctx_with_overridden_annotated_sub_async_dependency(context: alluka.BasicContext):
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

        with pytest.raises(alluka.AsyncOnlyError):
            context.execute(callback)

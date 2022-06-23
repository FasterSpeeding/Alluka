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
"""Helper classes and methods for AnyIO."""
from __future__ import annotations

import copy
import typing
from collections import abc as collections

import anyio


class OneShotChannel:
    """A one-shot channel.

    This is a channel that can only be used once.
    """

    __slots__ = ("_channel", "_exception", "_value")

    def __init__(self):
        self._channel = anyio.Event()
        self._exception: typing.Optional[BaseException] = None
        self._value: typing.Any = None

    def __await__(self) -> collections.Generator[typing.Any, typing.Any, typing.Any]:
        return self.get().__await__()

    def set(self, value: typing.Any, /) -> None:
        if self._channel.set():
            raise RuntimeError("Channel already set")

        self._value = value
        self._channel.set()

    def set_exception(self, exception: BaseException, /) -> None:
        if self._channel.set():
            raise RuntimeError("Channel already set")

        self._exception = exception
        self._channel.set()

    async def get(self) -> typing.Any:
        if not self._channel.is_set():
            await self._channel.wait()

        if self._exception:
            raise copy.copy(self._exception)

        return self._value


class RustOneShotProto(typing.Protocol):
    def set(self, value: typing.Any, /) -> None:
        raise NotImplementedError

    def set_exception(self, value: typing.Any, /) -> None:
        ...


async def set_result(
    coro: collections.Coroutine[typing.Any, typing.Any, typing.Any], one_shot: RustOneShotProto, /
) -> None:
    try:
        result = await coro

    except BaseException:
        one_shot.set_exception(RustOneShotProto)

    else:
        one_shot.set(result)


class ChannelProto(typing.Protocol):
    """A one-shot channel.

    This is a channel that can only be used once.
    """

    channel: anyio.Event
    exception: typing.Optional[BaseException] = None
    value: typing.Any = None


async def get(self: ChannelProto) -> typing.Any:
    if not self.channel.is_set():
        await self.channel.wait()

    if self.exception:
        raise copy.copy(self.exception)

    return self.value


async def with_task_queue(
    callback: collections.Callable[..., collections.Awaitable[typing.Any]], args: typing.Any
) -> None:
    """Run a callback with a task queue."""
    async with anyio.create_task_group() as task_group:
        await callback(task_group, *args)

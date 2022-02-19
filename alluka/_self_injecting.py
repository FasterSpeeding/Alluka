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
from __future__ import annotations

__all__: list[str] = ["AsyncSelfInjecting", "SelfInjecting"]

import typing
from collections import abc as collections

from . import abc

_T = typing.TypeVar("_T")


class AsyncSelfInjecting(abc.AsyncSelfInjecting[_T]):
    """Class used to link a sync function to a client to make it self-injecting.

    Examples
    --------
    ```py
    async def callback(database: Database = alluka.inject(type=Database)) -> None:
        await database.do_something()
    ...

    client = alluka.Client()
    injecting_callback = alluka.AsyncSelfInjecting(callback, client)
    await injecting_callback()
    ```

    Alternatively [alluka.abc.Client.as_async_self_injecting][] may be used:

    ```py
    client = alluka.Client()

    @client.as_async_self_injecting
    async def callback(database: Database = alluka.inject(type=Database)) -> None:
        ...
    ```
    """

    __slots__ = ("_callback", "_client")

    def __init__(self, client: abc.Client, callback: abc.CallbackSig[_T], /) -> None:
        """Initialise a self injecting callback.

        Parameters
        ----------
        client
            The injection client to use to resolve dependencies.
        callback
            The callback to make self-injecting.

            This may be sync or async.

        Raises
        ------
        ValueError
            If `callback` has any injected arguments which can only be passed
            positionally.
        """
        self._callback = callback
        self._client = client

    async def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> _T:
        # <<inherited docstring from alluka.abc.AsyncSelfInjecting>>.
        return await self._client.execute_async(self._callback, *args, **kwargs)

    @property
    def callback(self) -> abc.CallbackSig[_T]:
        # <<inherited docstring from alluka.abc.AsyncSelfInjecting>>.
        return self._callback


class SelfInjecting(abc.SelfInjecting[_T]):
    """Class used to link a sync function to a client to make it self-injecting.

    !!! note
        This executes the callback synchronously and therefore will error if
        any of the callback's dependencies are async.

    Examples
    --------
    ```py
    async def callback(database: Database = alluka.inject(type=Database)) -> None:
        await database.do_something()
    ...

    client = alluka.Client()
    injecting_callback = alluka.SelfInjecting(callback, client)
    await injecting_callback()
    ```

    Alternatively [alluka.abc.Client.as_self_injecting][] may be used:

    ```py
    client = alluka.Client()

    @client.as_self_injecting
    async def callback(database: Database = alluka.inject(type=Database)) -> None:
        ...
    ```
    """

    __slots__ = ("_callback", "_client")

    def __init__(self, client: abc.Client, callback: collections.Callable[..., _T], /) -> None:
        """Initialise a sync self injecting callback.

        Parameters
        ----------
        client
            The injection client to use to resolve dependencies.
        callback
            The callback to make self-injecting.

            This must be sync.

        Raises
        ------
        ValueError
            If `callback` has any injected arguments which can only be passed
            positionally.
        """
        self._callback = callback
        self._client = client

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> _T:
        # <<inherited docstring from alluka.abc.SelfInjecting>>.
        return self._client.execute(self._callback, *args, **kwargs)

    @property
    def callback(self) -> collections.Callable[..., _T]:
        # <<inherited docstring from alluka.abc.SelfInjecting>>.
        return self._callback

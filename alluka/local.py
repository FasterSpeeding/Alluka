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
"""Standard functions for using a local scope dependency injection client.

The "scope" will either be the current thread, an asynchronous runtime or an
asynchronous event/task.

!!! note
    This module's functionality will only work if
    [initialize][alluka.local.initialize] or
    [scope_client][alluka.local.scope_client] has been called to set the DI
    client for the local scope.
"""
from __future__ import annotations

__all__ = [
    "auto_inject",
    "auto_inject_async",
    "call_with_async_di",
    "call_with_di",
    "get",
    "initialize",
    "scope_client",
]

import contextlib
import contextvars
import functools
import typing

from . import _client  # pyright: ignore[reportPrivateUsage]
from . import abc

if typing.TYPE_CHECKING:
    from collections import abc as collections

    import typing_extensions

    _DefaultT = typing.TypeVar("_DefaultT")
    _P = typing_extensions.ParamSpec("_P")
    _T = typing.TypeVar("_T")

    _CoroT = collections.Coroutine[typing.Any, typing.Any, _T]


_CVAR_NAME: typing.Final[str] = "alluka_injector"
_injector = contextvars.ContextVar[abc.Client](_CVAR_NAME)


def initialize(client: typing.Optional[abc.Client] = None, /) -> abc.Client:
    """Link or initialise an injection client for the current scope.

    This uses [contextvars][] to store the client and therefore will not be
    inherited by child threads.

    [scope_client][alluka.local.scope_client] is recommended over this.

    Parameters
    ----------
    client
        If provided, this will be set as the client for the current scope.
        If not provided, a new client will be created.

    Returns
    -------
    alluka.abc.Client
        The created alluka client.

    Raises
    ------
    RuntimeError
        If the local client is already initialised.
    """
    if _injector.get(None) is not None:
        raise RuntimeError("Alluka client already initialised in the current scope")

    client = client or _client.Client()
    _injector.set(client)
    return client


initialise = initialize
"""Alias of [initialize][alluka.local.initialize]."""


@contextlib.contextmanager
def scope_client(client: typing.Optional[abc.Client] = None, /) -> collections.Generator[abc.Client, None, None]:
    """Declare a client for the scope within a context manager.

    This uses [contextvars][] to store the client and therefore will not be
    inherited by child threads.

    Examples
    --------
    ```py
    def uses_di() -> None:
        alluka.local.call_with_di(other_callback)

    with alluka.local.scope_client() as client:
        client.set_type_dependency(Type, value)
        uses_di()

    client = alluka.Client()
    client.set_type_dependency(Type, value)

    with alluka.local.scope_client(client):
        uses_di()
    ```

    Parameters
    ----------
    client
        The client to set for the context manager's scope.

        If not provided then a new client will be created.

    Returns
    -------
    contextlib.AbstractContextManager[alluka.abc.Client]
        Context manager which returns the scoped client.
    """
    client = client or _client.Client()
    token = _injector.set(client)

    yield client

    _injector.reset(token)


@typing.overload
def get() -> abc.Client: ...


@typing.overload
def get(*, default: _DefaultT) -> typing.Union[abc.Client, _DefaultT]: ...


def get(*, default: _DefaultT = ...) -> typing.Union[abc.Client, _DefaultT]:
    """Get the local client for the current scope.

    Parameters
    ----------
    default
        The value to return if the client is not initialised.

        If not provided, a RuntimeError will be raised instead.

    Returns
    -------
    alluka.abc.Client | _DefaultT
        The client for the local scope, or the default value if the client
        is not initialised.

    Raises
    ------
    RuntimeError
        If the client is not initialised and no default value was provided.
    """
    client = _injector.get(None)
    if client is None:
        if default is not ...:
            return default

        raise RuntimeError("Alluka client not initialised in the current scope")

    return client


def call_with_di(callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any) -> _T:
    """Use the local client to call a callback with DI.

    Parameters
    ----------
    callback
        The callback to call.
    *args
        Positional arguments to passthrough to the callback.
    **kwargs
        Keyword arguments to passthrough to the callback.

    Returns
    -------
    _T
        The result of the call.
    """
    return get().call_with_di(callback, *args, **kwargs)


@typing.overload
async def call_with_async_di(
    callback: collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, _T]],
    *args: typing.Any,
    **kwargs: typing.Any,
) -> _T: ...


@typing.overload
async def call_with_async_di(
    callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any
) -> _T: ...


async def call_with_async_di(callback: abc.CallbackSig[_T], *args: typing.Any, **kwargs: typing.Any) -> _T:
    """Use the local client to call a callback with async DI.

    Parameters
    ----------
    callback
        The callback to call.
    *args
        Positional arguments to passthrough to the callback.
    **kwargs
        Keyword arguments to passthrough to the callback.

    Returns
    -------
    _T
        The result of the call.
    """
    return await get().call_with_async_di(callback, *args, **kwargs)


def auto_inject_async(callback: collections.Callable[_P, _CoroT[_T]], /) -> collections.Callable[_P, _CoroT[_T]]:
    """Wrap an async function to make calls to it always inject dependencies.

    Examples
    --------
    ```py
    @alluka.local.auto_inject_async
    async def callback(dep: Injected[Type]) -> None:
        ...

    await callback()  # The requested dependencies will be passed.
    ```

    Parameters
    ----------
    callback
        The callback to wrap with DI.

    Returns
    -------
    collections.Callable
        The wrapped auto injecting callback.
    """

    @functools.wraps(callback)
    async def wrapped_callback(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        return await get().call_with_async_di(callback, *args, **kwargs)

    return wrapped_callback


def auto_inject(callback: collections.Callable[_P, _T], /) -> collections.Callable[_P, _T]:
    """Wrap a function to make calls to it always inject dependencies.

    Examples
    --------
    ```py
    @alluka.local.auto_inject
    def callback(dep: Injected[Type]) -> None:
        ...

    callback()  # The requested dependencies will be passed.
    ```

    Parameters
    ----------
    callback
        The callback to wrap with DI.

    Returns
    -------
    collections.Callable
        The wrapped auto injecting callback.
    """

    @functools.wraps(callback)
    def wrapped_callback(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        return get().call_with_di(callback, *args, **kwargs)

    return wrapped_callback

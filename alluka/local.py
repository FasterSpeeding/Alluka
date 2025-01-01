# BSD 3-Clause License
#
# Copyright (c) 2020-2025, Faster Speeding
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
    [scope_client][alluka.local.scope_client] or
    [scope_context][alluka.local.scope_context]
    has been called to set the DI context for the local scope.
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
import enum
import functools
import typing

import typing_extensions

from . import _client  # pyright: ignore[reportPrivateUsage]
from . import abc

if typing.TYPE_CHECKING:
    from collections import abc as collections

    _DefaultT = typing.TypeVar("_DefaultT")
    _P = typing.ParamSpec("_P")
    _T = typing.TypeVar("_T")

    _CoroT = collections.Coroutine[typing.Any, typing.Any, _T]


_CLIENT_CVAR_NAME: typing.Final[str] = "alluka_injector"
_injector = contextvars.ContextVar[abc.Client](_CLIENT_CVAR_NAME)
_CONTEXT_CVAR_NAME: typing.Final[str] = "alluka_context"
_context = contextvars.ContextVar[abc.Context](_CONTEXT_CVAR_NAME)


class _NoValueEnum(enum.Enum):
    VALUE = object()


_NO_VALUE: typing.Literal[_NoValueEnum.VALUE] = _NoValueEnum.VALUE
_NoValue = typing.Literal[_NoValueEnum.VALUE]


def initialize(client: abc.Client | None = None, /) -> abc.Client:
    """Link or initialise an injection client for the current scope.

    This uses [contextvars][] to store the client and therefore will not be
    inherited by child threads.

    [scope_client][alluka.local.scope_client] and
    [scope_context][alluka.local.scope_context] are recommended over this.

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
        If the local client is already set for the current scope.
    """
    if _injector.get(None) is not None:
        error_message = "Alluka client already set for the current scope"
        raise RuntimeError(error_message)

    client = client or _client.Client()
    _injector.set(client)
    return client


initialise = initialize
"""Alias of [initialize][alluka.local.initialize]."""


@contextlib.contextmanager
def scope_client(client: abc.Client | None = None, /) -> collections.Generator[abc.Client, None, None]:
    """Set the Alluka client for the scope within a context manager.

    This uses [contextvars][] to store the client and therefore will not be
    inherited by child threads.

    !!! note
        The client attached to a context set with
        [scope_context][alluka.local.scope_context] will take priority.

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
        uses_local_di()
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


@contextlib.contextmanager
def scope_context(context: abc.Context | None = None, /) -> collections.Generator[abc.Context, None, None]:
    """Set the Alluka context for the scope within a context manager.

    This uses [contextvars][] to store the context and therefore will not be
    inherited by child threads.

    Examples
    --------
    ```py
    context = (
        alluka.OverridingContext(alluka.local.get_context())
        .set_type_dependency(TypeA, value_a)
    )

    with alluka.local.scope_context(context):
        uses_local_di()
    ```

    Parameters
    ----------
    context
        The context to set for the context manager's scope.

        If not provided then the in-scope Alluka client is used to generate
        a new context.

    Returns
    -------
    contextlib.AbstractContextManager[alluka.abc.Context]
        Context manager which returns the scoped Context.

    Raises
    ------
    RuntimeError
        When `context` isn't provided and no Alluka client has been set for the
        current scope.
    """
    if context is None:
        context = get_client().make_context()

    token = _context.set(context)

    yield context

    _context.reset(token)


@typing.overload
def get_client() -> abc.Client: ...


@typing.overload
def get_client(*, default: _DefaultT) -> abc.Client | _DefaultT: ...


def get_client(*, default: _DefaultT | _NoValue = _NO_VALUE) -> abc.Client | _DefaultT:
    """Get the local client for the current scope.

    Parameters
    ----------
    default
        The value to return if no client is set for the current scope.

        If not provided, a RuntimeError will be raised instead.

    Returns
    -------
    alluka.abc.Client | _DefaultT
        The client for the local scope, or the default value if no client
        is set for the current scope.

    Raises
    ------
    RuntimeError
        If no client is present in the current scope and no default value was
        provided.
    """
    try:
        return get_context(from_client=False).injection_client

    except RuntimeError:
        pass

    client = _injector.get(None)
    if client is None:
        if default is _NO_VALUE:
            error_message = "No Alluka client set for the current scope"
            raise RuntimeError(error_message)

        return default

    return client


@typing.overload
@typing_extensions.deprecated("Use get_client or get_context")
def get() -> abc.Client: ...


@typing.overload
@typing_extensions.deprecated("Use get_client or get_context")
def get(*, default: _DefaultT) -> abc.Client | _DefaultT: ...


@typing_extensions.deprecated("Use get_client or get_context")
def get(*, default: _DefaultT | _NoValue = _NO_VALUE) -> abc.Client | _DefaultT:
    """Deprecated alias of [get_client][alluka.local.get_client]."""  # noqa: D401
    if default is _NO_VALUE:
        return get_client()

    return get_client(default=default)


@typing.overload
def get_context(*, from_client: bool = True) -> abc.Context: ...


@typing.overload
def get_context(*, default: _DefaultT, from_client: bool = True) -> abc.Context | _DefaultT: ...


def get_context(*, default: _DefaultT | _NoValue = _NO_VALUE, from_client: bool = True) -> abc.Context | _DefaultT:
    """Get the local context for the current scope.

    Parameters
    ----------
    default
        The value to return if no context is set for the current scope.

        If not provided, a RuntimeError will be raised instead.
    from_client
        Whether to try to make a context from the in-scope Alluka client
        when no context is set for the current scope.

    Returns
    -------
    alluka.abc.Context | _DefaultT
        The context for the local scope, or the default value if no context is
        set for the current context.

    Raises
    ------
    RuntimeError
        If the context is not set for the current context and no default value
        was provided.
    """
    context = _context.get(None)
    if context is not None:
        return context

    if from_client:
        try:
            return get_client().make_context()

        except RuntimeError:
            pass

    if default is _NO_VALUE:
        error_message = "Alluka context not set for the current scope"
        raise RuntimeError(error_message)

    return default


def call_with_di(callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any) -> _T:
    """Use the local context/client to call a callback with DI.

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
    return get_context().call_with_di(callback, *args, **kwargs)


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
    """Use the local context/client to call a callback with async DI.

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
    return await get_context().call_with_async_di(callback, *args, **kwargs)


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
        return await get_context().call_with_async_di(callback, *args, **kwargs)

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
        return get_context().call_with_di(callback, *args, **kwargs)

    return wrapped_callback

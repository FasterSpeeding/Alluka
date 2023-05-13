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
"""Standard functions for using a context local dependency injection client.

.. note::
    This module's functionality will only work if `initialize` has been called
    to set the DI client for the local scope and you will most likely want to
    call this in your `__init__.py` file to set the DI client for the main
    thread.
"""
from __future__ import annotations

__all__ = ["as_self_async_injecting", "as_self_injecting", "call_with_async_di", "call_with_di", "get", "initialize"]

import contextvars
import typing

from . import _client
from . import _self_injecting
from . import abc

if typing.TYPE_CHECKING:
    from collections import abc as collections

    _CallbackSigT = typing.TypeVar("_CallbackSigT", bound=abc.CallbackSig[typing.Any])
    _DefaultT = typing.TypeVar("_DefaultT")
    _SyncCallbackSigT = typing.TypeVar("_SyncCallbackSigT", bound=collections.Callable[..., typing.Any])
    _T = typing.TypeVar("_T")


_CVAR_NAME: typing.Final[str] = "alluka_injector"
_injector = contextvars.ContextVar[abc.Client](_CVAR_NAME)


def initialize(client: typing.Optional[abc.Client] = None, /) -> None:
    """Link or initialise an injection client for the current context.

    This uses the contextvars package to store the client.

    Parameters
    ----------
    client
        If provided, this will be set as the client for the current context.
        If not provided, a new client will be created.

    Raises
    ------
    RuntimeError
        If the local client is already initialised.
    """
    if _injector.get(None) is not None:
        raise RuntimeError("Alluka client already initialised in the current context")

    client = client or _client.Client()
    _injector.set(client)


@typing.overload
def get() -> abc.Client:
    ...


@typing.overload
def get(*, default: _DefaultT) -> typing.Union[abc.Client, _DefaultT]:
    ...


def get(*, default: _DefaultT = ...) -> typing.Union[abc.Client, _DefaultT]:
    """Get the local client for the current context.

    Parameters
    ----------
    default
        The value to return if the client is not initialised.

        If not provided, a RuntimeError will be raised instead.

    Returns
    -------
    alluka.abc.Client | _DefaultT
        The client for the local context, or the default value if the client
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

        raise RuntimeError("Alluka client not initialised in the current context")

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
) -> _T:
    ...


@typing.overload
async def call_with_async_di(callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any) -> _T:
    ...


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


def as_self_async_injecting(callback: _CallbackSigT, /) -> _self_injecting.AsyncSelfInjecting[_CallbackSigT]:
    """Mark a callback as self async injecting using the local DI client.

    Parameters
    ----------
    callback
        The callback to mark as self-injecting.

    Returns
    -------
    alluka.self_injecting.AsyncSelfInjecting
        The self-injecting callback.
    """
    return _self_injecting.AsyncSelfInjecting(get, callback)


def as_self_injecting(callback: _SyncCallbackSigT, /) -> _self_injecting.SelfInjecting[_SyncCallbackSigT]:
    """Mark a callback as self-injecting using the local DI client.

    Parameters
    ----------
    callback
        The callback to mark as self-injecting.

    Returns
    -------
    alluka.self_injecting.SelfInjecting
        The self-injecting callback.
    """
    return _self_injecting.SelfInjecting(get, callback)

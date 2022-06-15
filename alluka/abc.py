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
"""Alluka's abstract interfaces."""
from __future__ import annotations

__all__: list[str] = [
    "AsyncSelfInjecting",
    "CallbackSig",
    "Client",
    "Context",
    "SelfInjecting",
    "UNDEFINED",
    "Undefined",
]

import abc
import typing
from collections import abc as collections

# pyright: reportOverlappingOverload=warning

_T = typing.TypeVar("_T")
_CoroT = collections.Coroutine[typing.Any, typing.Any, _T]
_CallbackT = typing.TypeVar("_CallbackT", bound="CallbackSig[typing.Any]")
_DefaultT = typing.TypeVar("_DefaultT")
_OtherT = typing.TypeVar("_OtherT")
_SyncCallbackT = typing.TypeVar("_SyncCallbackT", bound=collections.Callable[..., typing.Any])


Undefined = type(None)
"""Deprecated alias for [types.NoneType][]"""

UNDEFINED: typing.Final[Undefined] = None
"""Deprecated alias for [None][]"""

CallbackSig = typing.Union[
    collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, _T]], collections.Callable[..., _T]
]
"""Type-hint of a injector callback.

!!! note
    Dependency dependency injection is recursively supported, meaning that the
    keyword arguments for a dependency callback may also ask for dependencies
    themselves.

This may either be a sync or asyc function with dependency injection being
available for the callback's keyword arguments but dynamically returning either
a coroutine or raw value may lead to errors.

Dependent on the context positional arguments may also be proivded.
"""


class Client(abc.ABC):
    """Abstract interface of a dependency injection client."""

    __slots__ = ()

    @abc.abstractmethod
    def as_async_self_injecting(self, callback: _CallbackT, /) -> AsyncSelfInjecting[_CallbackT]:
        """Link a function to a client to make it self-injecting.

        Parameters
        ----------
        callback : CallbackSig
            The callback to make self-injecting.

            This may be sync or async.

        Returns
        -------
        AsyncSelfInjecting
            The async self-injecting callback.
        """

    @abc.abstractmethod
    def as_self_injecting(self, callback: _SyncCallbackT, /) -> SelfInjecting[_SyncCallbackT]:
        """Link a sync function to a client to make it self-injecting.

        !!! note
            This uses sync dependency injection and therefore will lead
            to errors if any of the callback's dependencies are async.

        Parameters
        ----------
        callback : collections.abc.Callable
            The callback to make self-injecting.

            This must be sync.

        Returns
        -------
        SelfInjecting
            The self-injecting callback.
        """

    @typing.overload
    @abc.abstractmethod
    def call_with_di(
        self, callback: collections.Callable[..., _CoroT[typing.Any]], *args: typing.Any, **kwargs: typing.Any
    ) -> typing.NoReturn:
        ...

    @typing.overload
    @abc.abstractmethod
    def call_with_di(self, callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any) -> _T:
        ...

    @abc.abstractmethod
    def call_with_di(self, callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any) -> _T:
        """Call a function with sync dependency injection.

        Parameters
        ----------
        callback
            The callback to call.

            This must be sync.
        *args
            Positional arguments to pass to the callback.
        **kwargs
            Keyword arguments to pass to the callback.

        Returns
        -------
        _T
            The result of the callback.

        Raises
        ------
        alluka.MissingDependencyError
            If any of the callback's required type dependencies aren't implemented
            by the client.
        alluka.AsyncOnlyError
            If the callback or any of its callback dependencies are async.
        """

    @typing.overload
    @abc.abstractmethod
    def call_with_ctx(
        self,
        ctx: Context,
        callback: collections.Callable[..., _CoroT[typing.Any]],
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> typing.NoReturn:
        ...

    @typing.overload
    @abc.abstractmethod
    def call_with_ctx(
        self, ctx: Context, callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any
    ) -> _T:
        ...

    @abc.abstractmethod
    def call_with_ctx(
        self, ctx: Context, callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any
    ) -> _T:
        """Call a function with an existing DI context.

        Parameters
        ----------
        ctx
            The DI context to call the callback with.

            This will be used for scoped type injection.
        callback
            The callback to call.

            This must be sync.
        *args
            Positional arguments to pass to the callback.
        **kwargs
            Keyword arguments to pass to the callback.

        Returns
        -------
        _T
            The result of the callback.

        Raises
        ------
        alluka.MissingDependencyError
            If any of the callback's required type dependencies aren't implemented
            by the client.
        alluka.AsyncOnlyError
            If the callback or any of its callback dependencies are async.
        """

    @abc.abstractmethod
    async def call_with_async_di(self, callback: CallbackSig[_T], *args: typing.Any, **kwargs: typing.Any) -> _T:
        """Call a function with async dependency injection.

        Parameters
        ----------
        callback
            The callback to call.

            This may be sync or async.
        *args
            Positional arguments to pass to the callback.
        **kwargs
            Keyword arguments to pass to the callback.

        Returns
        -------
        _T
            The result of the callback.

        Raises
        ------
        alluka.MissingDependencyError
            If any of the callback's required type dependencies aren't implemented
            by the client.
        alluka.AsyncOnlyError
            If the callback or any of its callback dependencies are async.
        """

    @abc.abstractmethod
    async def call_with_ctx_async(
        self, ctx: Context, callback: CallbackSig[_T], *args: typing.Any, **kwargs: typing.Any
    ) -> _T:
        """Asynchronously call a function with a pre-existing DI context.

        Parameters
        ----------
        ctx
            The DI context to call the callback with.

            This will be used for scoped type injection.
        callback
            The callback to call.

            This may be sync or async.
        *args
            Positional arguments to pass to the callback.
        **kwargs
            Keyword arguments to pass to the callback.

        Returns
        -------
        _T
            The result of the callback.

        Raises
        ------
        alluka.MissingDependencyError
            If any of the callback's required type dependencies aren't implemented
            by the client.
        """

    @abc.abstractmethod
    def set_type_dependency(self: _T, type_: type[_OtherT], value: _OtherT, /) -> _T:
        """Set a callback to be called to resolve a injected type.

        Parameters
        ----------
        type_
            The type of the dependency to add an implementation for.
        value
            The value of the dependency.

        Returns
        -------
        Self
            The client instance to allow chaining.
        """

    @typing.overload
    @abc.abstractmethod
    def get_type_dependency(self, type_: type[_T], /) -> typing.Optional[_T]:
        ...

    @typing.overload
    @abc.abstractmethod
    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT) -> typing.Union[_T, _DefaultT]:
        ...

    @abc.abstractmethod
    def get_type_dependency(
        self, type_: type[_T], /, *, default: typing.Optional[_DefaultT] = None
    ) -> typing.Union[_T, _DefaultT, None]:
        """Get the implementation for an injected type.

        Parameters
        ----------
        type_
            The associated type.

        Returns
        -------
        _T | Undefined
            The resolved type if found, else [UNDEFINED][alluka.abc.UNDEFINED].
        """

    @abc.abstractmethod
    def remove_type_dependency(self: _T, type_: type[typing.Any], /) -> _T:
        """Remove a type dependency.

        Parameters
        ----------
        type_
            The associated type.

        Returns
        -------
        Self
            The client instance to allow chaining.

        Raises
        ------
        KeyError
            If `type` is not registered.
        """

    @abc.abstractmethod
    def set_callback_override(self: _OtherT, callback: CallbackSig[_T], override: CallbackSig[_T], /) -> _OtherT:
        """Override a specific injected callback.

        Parameters
        ----------
        callback
            The injected callback to override.
        override
            The callback to use instead.

        Returns
        -------
        Self
            The client instance to allow chaining.
        """

    @abc.abstractmethod
    def get_callback_override(self, callback: CallbackSig[_T], /) -> typing.Optional[CallbackSig[_T]]:
        """Get the override for a specific injected callback.

        Parameters
        ----------
        callback
            The injected callback to get the override for.

        Returns
        -------
        CallbackSig[_T] | None
            The override if found, else [None][].
        """

    @abc.abstractmethod
    def remove_callback_override(self: _OtherT, callback: CallbackSig[_T], /) -> _OtherT:
        """Remove a callback override.

        Parameters
        ----------
        callback
            The injected callback to remove the override for.

        Returns
        -------
        Self
            The client instance to allow chaining.

        Raises
        ------
        KeyError
            If no override is found for the callback.
        """


class Context(abc.ABC):
    """Abstract interface of an injection context."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def injection_client(self) -> Client:
        """Injection client this context is bound to."""

    @abc.abstractmethod
    def cache_result(self, callback: CallbackSig[_T], value: _T, /) -> None:
        """Cache the result of a callback within the scope of this context.

        Parameters
        ----------
        callback
            The callback to cache the result of.
        value
            The value to cache.
        """

    @typing.overload
    @abc.abstractmethod
    def call_with_di(
        self, callback: collections.Callable[..., _CoroT[typing.Any]], *args: typing.Any, **kwargs: typing.Any
    ) -> typing.NoReturn:
        ...

    @typing.overload
    @abc.abstractmethod
    def call_with_di(self, callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any) -> _T:
        ...

    @abc.abstractmethod
    def call_with_di(self, callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any) -> _T:
        """Call a function with the current DI context.

        Parameters
        ----------
        callback
            The callback to call.

            This must be sync.
        *args
            Positional arguments to pass to the callback.
        **kwargs
            Keyword arguments to pass to the callback.

        Returns
        -------
        _T
            The result of the callback.

        Raises
        ------
        alluka.MissingDependencyError
            If any of the callback's required type dependencies aren't implemented
            by the client.
        alluka.AsyncOnlyError
            If the callback or any of its callback dependencies are async.
        """

    @abc.abstractmethod
    async def call_with_async_di(self, callback: CallbackSig[_T], *args: typing.Any, **kwargs: typing.Any) -> _T:
        """Asynchronously call a function with the current DI context.

        Parameters
        ----------
        callback
            The callback to call.

            This may be sync or async.
        *args
            Positional arguments to pass to the callback.
        **kwargs
            Keyword arguments to pass to the callback.

        Returns
        -------
        _T
            The result of the callback.

        Raises
        ------
        alluka.MissingDependencyError
            If any of the callback's required type dependencies aren't implemented
            by the client.
        """

    @typing.overload
    @abc.abstractmethod
    def get_cached_result(self, callback: CallbackSig[_T], /) -> typing.Optional[_T]:
        ...

    @typing.overload
    @abc.abstractmethod
    def get_cached_result(self, callback: CallbackSig[_T], /, *, default: _DefaultT) -> typing.Union[_T, _DefaultT]:
        ...

    @abc.abstractmethod
    def get_cached_result(
        self, callback: CallbackSig[_T], /, *, default: typing.Optional[_DefaultT] = None
    ) -> typing.Union[_T, Undefined, _DefaultT]:
        """Get the cached result of a callback.

        Parameters
        ----------
        callback
            The callback to get the cached result of.

        Returns
        -------
        _T | Undefined
            The cached result of the callback, or [UNDEFINED][alluka.abc.UNDEFINED]
            if the callback has not been cached within this context or
            caching isn't implemented.
        """

    @typing.overload
    @abc.abstractmethod
    def get_type_dependency(self, type_: type[_T], /) -> typing.Optional[_T]:
        ...

    @typing.overload
    @abc.abstractmethod
    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT) -> typing.Union[_T, _DefaultT]:
        ...

    @abc.abstractmethod
    def get_type_dependency(
        self, type_: type[_T], /, *, default: typing.Optional[_DefaultT] = None
    ) -> typing.Union[_T, _DefaultT, None]:
        """Get the implementation for an injected type.

        !!! note
            Unlike [Client.get_type_dependency][alluka.abc.Client.get_type_dependency],
            this method may also return context specific implementations of a type.

        Parameters
        ----------
        type_
            The associated type.

        Returns
        -------
        _T | Undefined
            The resolved type if found, else [UNDEFINED][alluka.abc.UNDEFINED].
        """


class AsyncSelfInjecting(abc.ABC, typing.Generic[_CallbackT]):
    """Interface of a class used to make an async self-injecting callback.

    Examples
    --------
    ```py
    client = alluka.Client()

    @client.as_async_self_injecting
    async def callback(database: Database = alluka.inject(type=Database)) -> None:
        ...
    ```
    """

    __slots__ = ()

    @property
    @abc.abstractmethod
    def callback(self) -> _CallbackT:
        """The callback this wraps."""

    @typing.overload
    @abc.abstractmethod
    async def __call__(
        self: AsyncSelfInjecting[collections.Callable[..., _CoroT[_T]]],
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> _T:
        ...

    @typing.overload
    @abc.abstractmethod
    async def __call__(
        self: AsyncSelfInjecting[collections.Callable[..., _T]], *args: typing.Any, **kwargs: typing.Any
    ) -> _T:
        ...

    @abc.abstractmethod
    async def __call__(
        self: typing.Union[
            AsyncSelfInjecting[collections.Callable[..., _T]], AsyncSelfInjecting[collections.Callable[..., _CoroT[_T]]]
        ],
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> _T:
        """Call this with the provided arguments and any injected arguments.

        Parameters
        ----------
        *args
            Positional arguments to pass to the callback.
        **kwargs
            Keyword arguments to pass to the callback alongside injected arguments.

        Returns
        -------
        _T
            The callback's result.

        Raises
        ------
        alluka.MissingDependencyError
            If any of the callback's required type dependencies aren't implemented
            by the client.
        """


class SelfInjecting(abc.ABC, typing.Generic[_SyncCallbackT]):
    """Interface of a class used to make a self-injecting callback.

    !!! note
        This executes the callback synchronously and therefore will error if
        any of the callback's dependencies are async.

    Examples
    --------
    ```py
    client = alluka.Client()

    @client.as_self_injecting
    def callback(database: Database = alluka.inject(type=Database)) -> None:
        ...
    ```
    """

    __slots__ = ()

    @property
    @abc.abstractmethod
    def callback(self) -> _SyncCallbackT:
        """The callback this wraps."""

    @abc.abstractmethod
    def __call__(self: SelfInjecting[collections.Callable[..., _T]], *args: typing.Any, **kwargs: typing.Any) -> _T:
        """Call this callback with the provided arguments + injected arguments.

        Parameters
        ----------
        *args
            Positional arguments to pass to the callback.
        **kwargs
            Keyword arguments to pass to the callback.

        Returns
        -------
        _T
            The callback's result.

        Raises
        ------
        alluka.MissingDependencyError
            If any of the callback's required type dependencies aren't implemented
            by the client.
        alluka.AsyncOnlyError
            If the callback or any of its callback dependencies are async.
        """

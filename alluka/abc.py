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
"""Alluka's abstract interfaces."""

# pyright: reportOverlappingOverload=warning

from __future__ import annotations

__all__: list[str] = ["AsyncSelfInjecting", "CallbackSig", "Client", "Context", "SelfInjecting"]

import abc
import enum
import functools
import typing
from collections import abc as collections

import typing_extensions

if typing.TYPE_CHECKING:
    from typing_extensions import Self

    _P = typing_extensions.ParamSpec("_P")

_T = typing.TypeVar("_T")
_CoroT = collections.Coroutine[typing.Any, typing.Any, _T]
_CallbackT = typing.TypeVar("_CallbackT", bound="CallbackSig[typing.Any]")
_DefaultT = typing.TypeVar("_DefaultT")
_SyncCallbackT = typing.TypeVar("_SyncCallbackT", bound=collections.Callable[..., typing.Any])


class _NoDefaultEnum(enum.Enum):
    VALUE = object()


_NO_VALUE: typing.Literal[_NoDefaultEnum.VALUE] = _NoDefaultEnum.VALUE
_NoValueOr = typing.Union[_T, typing.Literal[_NoDefaultEnum.VALUE]]


CallbackSig = collections.Callable[..., typing.Union[_CoroT[_T], _T]]
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
    def make_context(self) -> Context:
        """Create a dependency injection context.

        Returns
        -------
        alluka.abc.Context
            The created DI context, bound to the current client.
        """

    @abc.abstractmethod
    @typing_extensions.deprecated("Use .auto_inject_async")
    def as_async_self_injecting(
        self, callback: _CallbackT, /
    ) -> AsyncSelfInjecting[_CallbackT]:  # pyright: ignore[reportDeprecated]
        """Deprecated callback for making async functions auto-inject.

        !!! warning "deprecated"
            This is deprecated as of `v0.2.0`, use
            [Client.auto_inject_async][alluka.abc.Client.auto_inject_async].
        """

    @abc.abstractmethod
    @typing_extensions.deprecated("Use .auto_inject")
    def as_self_injecting(
        self, callback: _SyncCallbackT, /
    ) -> SelfInjecting[_SyncCallbackT]:  # pyright: ignore[reportDeprecated]
        """Deprecated callback for making functions auto-inject.

        !!! warning "deprecated"
            This is deprecated as of `v0.2.0`, use
            [Client.auto_inject][alluka.abc.Client.auto_inject].
        """

    def auto_inject(self, callback: collections.Callable[_P, _T], /) -> collections.Callable[_P, _T]:
        """Wrap a function to make calls to it always inject dependencies.

        Examples
        --------
        ```py
        @client.auto_inject
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
            return self.call_with_di(callback, *args, **kwargs)

        return wrapped_callback

    def auto_inject_async(
        self, callback: collections.Callable[_P, _CoroT[_T]], /
    ) -> collections.Callable[_P, _CoroT[_T]]:
        """Wrap an async function to make calls to it always inject dependencies.

        Examples
        --------
        ```py
        @client.auto_inject_async
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
            return await self.call_with_async_di(callback, *args, **kwargs)

        return wrapped_callback

    @typing.overload
    def call_with_di(
        self, callback: collections.Callable[..., _CoroT[typing.Any]], *args: typing.Any, **kwargs: typing.Any
    ) -> typing.NoReturn: ...

    @typing.overload
    def call_with_di(self, callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any) -> _T: ...

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
        alluka.SyncOnlyError
            If the callback or any of its callback dependencies are async.
        """
        return self.make_context().call_with_di(callback, *args, **kwargs)

    @typing.overload
    @abc.abstractmethod
    def call_with_ctx(
        self,
        ctx: Context,
        callback: collections.Callable[..., _CoroT[typing.Any]],
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> typing.NoReturn: ...

    @typing.overload
    @abc.abstractmethod
    def call_with_ctx(
        self, ctx: Context, callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any
    ) -> _T: ...

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
        alluka.SyncOnlyError
            If the callback or any of its callback dependencies are async.
        """

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
        alluka.SyncOnlyError
            If the callback or any of its callback dependencies are async.
        """
        return await self.make_context().call_with_async_di(callback, *args, **kwargs)

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
    def set_type_dependency(self, type_: type[_T], value: _T, /) -> Self:
        """Set the value for a type dependency.

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
    def get_type_dependency(self, type_: type[_T], /) -> _T: ...

    @typing.overload
    @abc.abstractmethod
    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT) -> typing.Union[_T, _DefaultT]: ...

    @abc.abstractmethod
    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT = ...) -> typing.Union[_T, _DefaultT]:
        """Get the implementation for an injected type.

        Parameters
        ----------
        type_
            The associated type.
        default
            The default value to return if the type is not implemented.

        Returns
        -------
        _T | _DefaultT
            The resolved type if found.

            If the type isn't implemented then the value of `default`
            will be returned if it is provided.

        Raises
        ------
        KeyError
            If no dependency was found when no default was provided.
        """

    @abc.abstractmethod
    def remove_type_dependency(self, type_: type[typing.Any], /) -> Self:
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
    def set_callback_override(self, callback: CallbackSig[_T], override: CallbackSig[_T], /) -> Self:
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
    def remove_callback_override(self, callback: CallbackSig[_T], /) -> Self:
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

    def cache_result(self, callback: CallbackSig[_T], value: _T, /) -> None:
        """Cache the result of a callback within the scope of this context.

        Whether this does anything or is a noop is implementation detail.

        Parameters
        ----------
        callback
            The callback to cache the result of.
        value
            The value to cache.
        """

    @typing.overload
    def call_with_di(
        self, callback: collections.Callable[..., _CoroT[typing.Any]], *args: typing.Any, **kwargs: typing.Any
    ) -> typing.NoReturn: ...

    @typing.overload
    def call_with_di(self, callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any) -> _T: ...

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
        alluka.SyncOnlyError
            If the callback or any of its callback dependencies are async.
        """
        return self.injection_client.call_with_ctx(self, callback, *args, **kwargs)

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
        return await self.injection_client.call_with_ctx_async(self, callback, *args, **kwargs)

    @typing.overload
    def get_cached_result(self, callback: CallbackSig[_T], /) -> _T: ...

    @typing.overload
    def get_cached_result(self, callback: CallbackSig[_T], /, *, default: _DefaultT) -> typing.Union[_T, _DefaultT]: ...

    def get_cached_result(
        self, callback: CallbackSig[_T], /, *, default: _NoValueOr[_DefaultT] = _NO_VALUE
    ) -> typing.Union[_T, _DefaultT]:
        """Get the cached result of a callback.

        This will always raise/default for context implementations with no caching.

        Parameters
        ----------
        callback
            The callback to get the cached result of.
        default
            The default value to return if the callback is not cached.

        Returns
        -------
        _T | _DefaultT
            The cached result of the callback if found.

            If the callback's result hasn't been cached or caching isn't
            implementing then this will return the value of `default` if it
            is provided.

        Raises
        ------
        KeyError
            If no value was found when no default was provided.
        """
        if default is _NO_VALUE:
            raise KeyError

        return default

    @typing.overload
    @abc.abstractmethod
    def get_type_dependency(self, type_: type[_T], /) -> _T: ...

    @typing.overload
    @abc.abstractmethod
    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT) -> typing.Union[_T, _DefaultT]: ...

    @abc.abstractmethod
    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT = ...) -> typing.Union[_T, _DefaultT]:
        """Get the implementation for an injected type.

        Unlike [Client.get_type_dependency][alluka.abc.Client.get_type_dependency],
        this method may also return context specific implementations of a type.

        Parameters
        ----------
        type_
            The associated type.
        default
            The default value to return if the type is not implemented.

        Returns
        -------
        _T | _DefaultT
            The resolved type if found.

            If the type isn't implemented then the value of `default`
            will be returned if it is provided.

        Raises
        ------
        KeyError
            If no dependency was found when no default was provided.
        """


@typing_extensions.deprecated("Use Client.auto_inject_async")
class AsyncSelfInjecting(abc.ABC, typing.Generic[_CallbackT]):
    """Deprecated interface of a class for marking async functions as self-injecting.

    !!! warning "deprecated"
        This is deprecated as of `v0.2.0`, use
        [Client.auto_inject_async][alluka.abc.Client.auto_inject_async].
    """

    __slots__ = ()

    @property
    @abc.abstractmethod
    def callback(self) -> _CallbackT:
        """The callback this wraps."""

    @typing.overload
    @abc.abstractmethod
    async def __call__(
        self: AsyncSelfInjecting[collections.Callable[..., _CoroT[_T]]],  # pyright: ignore[reportDeprecated]
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> _T: ...

    @typing.overload
    @abc.abstractmethod
    async def __call__(
        self: AsyncSelfInjecting[collections.Callable[..., _T]],  # pyright: ignore[reportDeprecated]
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> _T: ...

    @abc.abstractmethod
    async def __call__(
        self: typing.Union[
            AsyncSelfInjecting[collections.Callable[..., _T]],  # pyright: ignore[reportDeprecated]
            AsyncSelfInjecting[collections.Callable[..., _CoroT[_T]]],  # pyright: ignore[reportDeprecated]
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


@typing_extensions.deprecated("Use Client.auto_inject")
class SelfInjecting(abc.ABC, typing.Generic[_SyncCallbackT]):
    """Deprecated interface of a class for marking functions as self-injecting.

    !!! warning "deprecated"
        This is deprecated as of `v0.2.0`, use
        [Client.auto_inject][alluka.abc.Client.auto_inject].
    """

    __slots__ = ()

    @property
    @abc.abstractmethod
    def callback(self) -> _SyncCallbackT:
        """The callback this wraps."""

    @abc.abstractmethod
    def __call__(
        self: SelfInjecting[collections.Callable[..., _T]],  # pyright: ignore[reportDeprecated]
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> _T:
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
        alluka.SyncOnlyError
            If the callback or any of its callback dependencies are async.
        """

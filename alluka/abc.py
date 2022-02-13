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
    "CallbackSig",
    "Client",
    "Context",
    "UNDEFINED",
    "Undefined",
]

import abc
import typing
from collections import abc as collections

_T = typing.TypeVar("_T")
_OtherT = typing.TypeVar("_OtherT")


class Undefined:
    """Class/type of `UNDEFINED`."""

    __instance: Undefined

    def __bool__(self) -> typing.Literal[False]:
        return False

    def __new__(cls) -> Undefined:
        try:
            return cls.__instance

        except AttributeError:
            new = super().__new__(cls)
            assert isinstance(new, Undefined)
            cls.__instance = new
            return cls.__instance


UNDEFINED: typing.Final[Undefined] = Undefined()
"""Singleton value used within dependency injection to indicate that a value is undefined."""
_UndefinedOr = typing.Union[Undefined, _T]


CallbackSig = typing.Union[collections.Callable[..., _T], collections.Callable[..., collections.Awaitable[_T]]]
"""Type-hint of a injector callback.

.. note::
    Dependency dependency injection is recursively supported, meaning that the
    keyword arguments for a dependency callback may also ask for dependencies
    themselves.

This may either be a synchronous or asynchronous function with dependency
injection being available for the callback's keyword arguments but dynamically
returning either an awaitable or raw value may lead to errors.

Dependent on the context positional arguments may also be proivded.
"""


class Client:
    """Abstract interface of a dependency injection client."""

    __slots__ = ()

    @abc.abstractmethod
    def set_type_dependency(self: _T, type_: type[_OtherT], value: _OtherT, /) -> _T:
        """Set a callback to be called to resolve a injected type.

        Parameters
        ----------
        type_: type[_T]
            The type of the dependency to add an implementation for.
        value_: _T
            The value of the dependency.

        Returns
        -------
        Self
            The client instance to allow chaining.
        """

    @abc.abstractmethod
    def get_type_dependency(self, type_: type[_T], /) -> _UndefinedOr[_T]:
        """Get the implementation for an injected type.

        Parameters
        ----------
        type_: type[_T]
            The associated type.

        Returns
        -------
        _T | Undefined
            The resolved type if found, else `Undefined`.
        """

    @abc.abstractmethod
    def remove_type_dependency(self: _T, type_: type[typing.Any], /) -> _T:
        """Remove a type dependency.

        Parameters
        ----------
        type: type
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
    def set_callback_override(self: _T, callback: CallbackSig[_OtherT], override: CallbackSig[_OtherT], /) -> _T:
        """Override a specific injected callback.

        .. note::
            This does not effect the callbacks set for type injectors.

        Parameters
        ----------
        callback: CallbackSig[_T]
            The injected callback to override.
        override: CallbackSig[_T]
            The callback to use instead.

        Returns
        -------
        Self
            The client instance to allow chaining.
        """

    @abc.abstractmethod
    def get_callback_override(self, callback: CallbackSig[_T], /) -> typing.Optional[CallbackSig[_T]]:
        """Get the set override for a specific injected callback.

        Parameters
        ----------
        callback: CallbackSig[_T]
            The injected callback to get the override for.

        Returns
        -------
        CallbackSig[_T] | None
            The override if found, else `None`.
        """

    @abc.abstractmethod
    def remove_callback_override(self: _T, callback: CallbackSig[typing.Any], /) -> _T:
        """Remove a callback override.

        Parameters
        ----------
        callback: CallbackSig
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
        callback : CallbackSig[_T]
            The callback to cache the result of.
        value : _T
            The value to cache.
        """

    @abc.abstractmethod
    def get_cached_result(self, callback: CallbackSig[_T], /) -> _UndefinedOr[_T]:
        """Get the cached result of a callback.

        Parameters
        ----------
        callback : CallbackSig[_T]
            The callback to get the cached result of.

        Returns
        -------
        _T | Undefined
            The cached result of the callback, or `UNDEFINED` if the callback
            has not been cached within this context.
        """

    @abc.abstractmethod
    def get_type_dependency(self, type_: type[_T], /) -> _UndefinedOr[_T]:
        """Get the implementation for an injected type.

        .. note::
            Unlike `Client.get_type_dependency`, this method may also
            return context specific implementations of a type if the type isn't
            registered with the client.

        Parameters
        ----------
        type_: type[_T]
            The associated type.

        Returns
        -------
        T | Undefined
            The resolved type if found, else `Undefined`.
        """

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
"""Alluka's standard injection context implementations."""

# pyright: reportOverlappingOverload=warning

from __future__ import annotations

__all__: list[str] = ["BasicContext", "CachingContext", "Context", "OverridingContext"]

import enum
import typing

import typing_extensions

from . import abc as alluka

if typing.TYPE_CHECKING:
    from typing_extensions import Self


_T = typing.TypeVar("_T")


_DefaultT = typing.TypeVar("_DefaultT")


class _NoDefaultEnum(enum.Enum):
    VALUE = object()


_NO_VALUE: typing.Literal[_NoDefaultEnum.VALUE] = _NoDefaultEnum.VALUE
_NoValueOr = typing.Union[_T, typing.Literal[_NoDefaultEnum.VALUE]]


class Context(alluka.Context):
    """Basic implementation of [alluka.abc.Context][] without caching."""

    __slots__ = ("_client",)

    def __init__(self, client: alluka.Client, /) -> None:
        """Initialise an injection context.

        Parameters
        ----------
        client
            The injection client this context is bound to.
        """
        self._client = client

    @property
    def injection_client(self) -> alluka.Client:
        # <<inherited docstring from alluka.abc.Context>>.
        return self._client

    @typing.overload
    def get_type_dependency(self, type_: type[_T], /) -> _T: ...

    @typing.overload
    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT) -> typing.Union[_T, _DefaultT]: ...

    def get_type_dependency(
        self, type_: type[_T], /, *, default: _NoValueOr[_DefaultT] = _NO_VALUE
    ) -> typing.Union[_T, _DefaultT]:
        # <<inherited docstring from alluka.abc.Context>>.
        if type_ is alluka.Context:
            return self  # type: ignore

        result = self._client.get_type_dependency(type_, default=default)

        if result is _NO_VALUE:
            raise KeyError

        return result


class CachingContext(Context):
    """Basic implementation of [alluka.abc.Context][] with callback result caching."""

    __slots__ = ("_result_cache",)

    def __init__(self, client: alluka.Client, /) -> None:
        """Initialise a caching injection context.

        Parameters
        ----------
        client
            The injection client this context is bound to.
        """
        super().__init__(client)
        self._result_cache: dict[alluka.CallbackSig[typing.Any], typing.Any] = {}

    def cache_result(self, callback: alluka.CallbackSig[_T], value: _T, /) -> None:
        # <<inherited docstring from alluka.abc.Context>>.
        self._result_cache[callback] = value

    @typing.overload
    def get_cached_result(self, callback: alluka.CallbackSig[_T], /) -> _T: ...

    @typing.overload
    def get_cached_result(
        self, callback: alluka.CallbackSig[_T], /, *, default: _DefaultT
    ) -> typing.Union[_T, _DefaultT]: ...

    def get_cached_result(
        self, callback: alluka.CallbackSig[_T], /, *, default: _NoValueOr[_DefaultT] = _NO_VALUE
    ) -> typing.Union[_T, _DefaultT]:
        # <<inherited docstring from alluka.abc.Context>>.
        result = self._result_cache.get(callback, default)

        if result is _NO_VALUE:
            raise KeyError

        return result


class OverridingContext(alluka.Context):
    """Context which exists to override an existing context with special-cased type-dependencies.

    Examples
    --------
    ```py
    def other_callback(value: alluka.Inject[Type]) -> None:
        ...

    def callback(ctx: alluka.Inject[alluka.abc.Context]) -> None:
        ctx = alluka.OverridingContext(ctx).set_type_dependency(Type, value)

        ctx.call_with_di(other_callback)
    ```

    ```py
    client = alluka.abc.Client().set_type_dependency(Type, value)
    ctx = alluka.OverridingContext.from_client(client).set_type_dependency(OtherType, value)
    ```
    """

    __slots__ = ("_context", "_overrides")

    def __init__(self, context: alluka.Context, /) -> None:
        """Initialise an overriding context.

        While this is designed to wrap an existing context,
        [OverridingContext.from_client][alluka.OverridingContext.from_client] can
        be used to create this from an alluka client.

        Parameters
        ----------
        context
            The context to wrap.
        """
        self._context = context
        self._overrides: dict[type[typing.Any], typing.Any] = {}

    @classmethod
    def from_client(cls, client: alluka.Client, /) -> Self:
        """Create an overriding context from an injection client.

        This will wrap the context returned by [Client.make_context][alluka.abc.Client.make_context].

        Parameters
        ----------
        client
            The alluka client to make an overriding context for.

        Returns
        -------
        OverridingContext
            The created overriding context.
        """
        return cls(client.make_context())

    @property
    def injection_client(self) -> alluka.Client:
        # <<inherited docstring from alluka.abc.Context>>.
        return self._context.injection_client

    @typing.overload
    def get_cached_result(self, callback: alluka.CallbackSig[_T], /) -> _T: ...

    @typing.overload
    def get_cached_result(
        self, callback: alluka.CallbackSig[_T], /, *, default: _DefaultT
    ) -> typing.Union[_T, _DefaultT]: ...

    def get_cached_result(
        self, callback: alluka.CallbackSig[_T], /, *, default: _NoValueOr[_DefaultT] = _NO_VALUE
    ) -> typing.Union[_T, _DefaultT]:
        value = self._context.get_cached_result(callback, default=default)

        if value is _NO_VALUE:
            raise KeyError

        return value

    def cache_result(self, callback: alluka.CallbackSig[_T], value: _T, /) -> None:
        self._context.cache_result(callback, value)

    @typing.overload
    def get_type_dependency(self, type_: type[_T], /) -> _T: ...

    @typing.overload
    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT) -> typing.Union[_T, _DefaultT]: ...

    def get_type_dependency(
        self, type_: type[_T], /, *, default: _NoValueOr[_DefaultT] = _NO_VALUE
    ) -> typing.Union[_T, _DefaultT]:
        # <<inherited docstring from alluka.abc.Context>>.
        value = self._overrides.get(type_, default)
        if value is default:
            value = self._context.get_type_dependency(type_, default=default)

        if value is _NO_VALUE:
            raise KeyError

        return value

    def set_type_dependency(self, type_: type[_T], value: _T, /) -> Self:
        """Add a context specific type dependency.

        Parameters
        ----------
        type_
            The type of the dependency to add an implementation for.
        value
            The value of the dependency.

        Returns
        -------
        Self
            The context to allow chaining.
        """
        self._overrides[type_] = value
        return self


@typing_extensions.deprecated("Use Context or CachingContext")
class BasicContext(CachingContext):
    """Deprecated alias of [alluka.CachingContext][].

    !!! warning "deprecated"
        This is deprecated as of `v0.3.0`.
        use [alluka.Context][] or [alluka.CachingContext][].
        [alluka.OverridingContext][] should be used as a replacement for the
        undocumented type special casing.
    """

    __slots__ = ("_special_case_types",)

    def __init__(self, client: alluka.Client, /) -> None:
        super().__init__(client)
        self._special_case_types: dict[type[typing.Any], typing.Any] = {}

    @typing.overload
    def get_type_dependency(self, type_: type[_T], /) -> _T: ...

    @typing.overload
    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT) -> typing.Union[_T, _DefaultT]: ...

    def get_type_dependency(
        self, type_: type[_T], /, *, default: _NoValueOr[_DefaultT] = _NO_VALUE
    ) -> typing.Union[_T, _DefaultT]:
        # <<inherited docstring from alluka.abc.Context>>.
        value = self._special_case_types.get(type_, default)
        if value is default:
            value = super().get_type_dependency(type_, default=default)

        if value is _NO_VALUE:
            raise KeyError

        return value

    @typing_extensions.deprecated("Use ContextOverride")
    def _set_type_special_case(self, type_: type[_T], value: _T, /) -> Self:
        if not self._special_case_types:
            self._special_case_types = {}

        self._special_case_types[type_] = value
        return self

    @typing_extensions.deprecated("Use ContextOverride")
    def _remove_type_special_case(self, type_: type[typing.Any], /) -> Self:
        if not self._special_case_types:
            raise KeyError(type_)

        del self._special_case_types[type_]
        return self

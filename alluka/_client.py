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
"""Alluka's standard injection client implementation."""

# pyright: reportOverlappingOverload=warning

from __future__ import annotations

__all__: list[str] = ["Client", "inject"]

import asyncio
import enum
import typing
import warnings
import weakref
from collections import abc as collections

import typing_extensions

from . import _context  # pyright: ignore[reportPrivateUsage]
from . import _errors  # pyright: ignore[reportPrivateUsage]
from . import _self_injecting  # pyright: ignore[reportPrivateUsage]
from . import _types  # pyright: ignore[reportPrivateUsage]
from . import _visitor
from . import abc as alluka
from .managed import _index

if typing.TYPE_CHECKING:
    from typing import Self


_T = typing.TypeVar("_T")


_AnyCoro = collections.Coroutine[typing.Any, typing.Any, typing.Any]
_CallbackSigT = typing.TypeVar("_CallbackSigT", bound=alluka.CallbackSig[typing.Any])
_DefaultT = typing.TypeVar("_DefaultT")
_SyncCallbackSigT = typing.TypeVar("_SyncCallbackSigT", bound=collections.Callable[..., typing.Any])

_TypeT = type[_T]


class _NoValueEnum(enum.Enum):
    VALUE = object()


_NO_VALUE: typing.Literal[_NoValueEnum.VALUE] = _NoValueEnum.VALUE
_NoValue = typing.Literal[_NoValueEnum.VALUE]


@typing.overload
def inject(*, callback: alluka.CallbackSig[_T]) -> _T: ...


@typing.overload
def inject(*, type: _TypeT[_T]) -> _T: ...


@typing.overload
def inject(*, type: typing.Any = None) -> typing.Any: ...


def inject(*, callback: alluka.CallbackSig[_T] | None = None, type: typing.Any = None) -> typing.Any:  # noqa: A002
    """Declare a keyword-argument as requiring an injected dependency.

    This may be assigned to an argument's default value to declare injection
    or as a part of its Annotated metadata.

    !!! note
        If neither `type` nor `callback` is provided, an injected type
        will be inferred from the argument's annotation.

    Examples
    --------
    ```py
    async def callback(
        # Here we require an implementation of the type `Component` to be
        # injected.
        injected_type: Component = alluka.inject(type=Component)
        # Here we inject an out-of-scope callback which itself is taking
        # advantage of type injectioallukan.
        callback_result: ResultT = alluka.inject(callback=injected_callback)
    ) -> None:
        raise NotImplementedError

    ...
    # where client is an `alluka.Client` instance.
    result = await client.call_with_async_di(callback)
    ```

    Parameters
    ----------
    callback
        The callback to use to resolve the dependency.

        If this callback has no type dependencies then this will still work
        without an injection context but this can be overridden using
        `alluka.abc.Client.set_callback_override`.
    type
        The type of the dependency to resolve.

        If a union (e.g. `typing.Union[A, B]`, `A | B`, `typing.Optional[A]`)
        is passed for `type` then each type in the union will be tried
        separately rather than the literal type, allowing for resolving
        `A | B` to the value set by `set_type_dependency(B, ...)`.

        If a union has `None` as one of its types (including `Optional[T]`)
        then `None` will be passed for the parameter if none of the types could
        be resolved using the linked client.

    Raises
    ------
    ValueError
        If both `type` and `callback` are provided.
    """
    return typing.cast("_T", _types.InjectedDescriptor(callback=callback, type=type))


class Client(alluka.Client):
    """Standard implementation of a dependency injection client.

    This is used to track type dependencies and execute callbacks.
    """

    __slots__ = (
        "_callback_overrides",
        "_descriptors",
        "_introspect_annotations",
        "_make_context",
        "_type_dependencies",
    )

    def __init__(self, *, introspect_annotations: bool = True) -> None:
        """Initialise an injector client."""
        self._callback_overrides: dict[alluka.CallbackSig[typing.Any], alluka.CallbackSig[typing.Any]] = {}
        # TODO: this forces objects to have a __weakref__ attribute,
        # and also hashability (so hash and eq or neither), do we want to
        # keep with this behaviour or document it?
        self._descriptors: weakref.WeakKeyDictionary[
            alluka.CallbackSig[typing.Any], dict[str, _types.InjectedTuple]
        ] = weakref.WeakKeyDictionary()
        self._introspect_annotations = introspect_annotations  # TODO: deprecate
        static_context = _context.Context(self)
        self._make_context: collections.Callable[[Self], alluka.Context] = lambda _: static_context
        self._type_dependencies: dict[type[typing.Any], typing.Any] = {alluka.Client: self, Client: self}

    def _build_descriptors(self, callback: alluka.CallbackSig[typing.Any], /) -> dict[str, _types.InjectedTuple]:
        try:
            return self._descriptors[callback]

        except KeyError:
            pass

        descriptors = _index.GLOBAL_INDEX.get_descriptors(callback)
        if descriptors is not None:
            self._descriptors[callback] = descriptors
            return descriptors

        descriptors = self._descriptors[callback] = _visitor.Callback(callback).accept(_visitor.ParameterVisitor())
        return descriptors

    def set_make_context(self, make_context: collections.Callable[[Self], alluka.Context], /) -> Self:
        """Set the callback used to make DI contexts for this client.

        Parameters
        ----------
        make_context
            Callback to use to create DI contexts.

        Returns
        -------
        Self
            The client to enable chained calls.
        """
        self._make_context = make_context
        return self

    def make_context(self) -> alluka.Context:
        # <<inherited docstring from alluka.abc.Client>>.
        return self._make_context(self)

    @typing_extensions.deprecated("Use .auto_inject")
    def as_async_self_injecting(
        self, callback: _CallbackSigT, /
    ) -> alluka.AsyncSelfInjecting[_CallbackSigT]:  # pyright: ignore[reportDeprecated]
        # <<inherited docstring from alluka.abc.Client>>.
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)

            return _self_injecting.AsyncSelfInjecting(self, callback)  # pyright: ignore[reportDeprecated]

    @typing_extensions.deprecated("Use .auto_inject_async")
    def as_self_injecting(
        self, callback: _SyncCallbackSigT, /
    ) -> alluka.SelfInjecting[_SyncCallbackSigT]:  # pyright: ignore[reportDeprecated]
        # <<inherited docstring from alluka.abc.Client>>.
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)

            return _self_injecting.SelfInjecting(self, callback)  # pyright: ignore[reportDeprecated]

    @typing.overload
    def call_with_ctx(
        self,
        ctx: alluka.Context,
        callback: collections.Callable[..., _AnyCoro],
        /,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> typing.NoReturn: ...

    @typing.overload
    def call_with_ctx(
        self, ctx: alluka.Context, callback: collections.Callable[..., _T], /, *args: typing.Any, **kwargs: typing.Any
    ) -> _T: ...

    def call_with_ctx(
        self, ctx: alluka.Context, callback: collections.Callable[..., _T], /, *args: typing.Any, **kwargs: typing.Any
    ) -> _T:
        # <<inherited docstring from alluka.abc.Client>>.
        descriptors = self._build_descriptors(callback)
        if descriptors:
            # This prioritises passed **kwargs over the injected dependencies.
            kwargs = {n: v.resolve(ctx) for n, (_, v) in descriptors.items()} | kwargs

        result = callback(*args, **kwargs)
        if asyncio.iscoroutine(result):
            raise _errors.SyncOnlyError

        return result

    async def call_with_ctx_async(
        self, ctx: alluka.Context, callback: alluka.CallbackSig[_T], /, *args: typing.Any, **kwargs: typing.Any
    ) -> _T:
        # <<inherited docstring from alluka.abc.Client>>.
        if descriptors := self._build_descriptors(callback):
            # Pyright currently doesn't support `is` for narrowing tuple types like this
            # This prioritises passed **kwargs over the injected dependencies.
            kwargs = {
                n: v[1].resolve(ctx) if v[0] == _types.InjectedTypes.TYPE else await v[1].resolve_async(ctx)
                for n, v in descriptors.items()
            } | kwargs

        result = callback(*args, **kwargs)
        if asyncio.iscoroutine(result):
            return typing.cast("_T", await result)

        return typing.cast("_T", result)

    def set_type_dependency(self, type_: type[_T], value: _T, /) -> Self:
        # <<inherited docstring from alluka.abc.Client>>.
        self._type_dependencies[type_] = value
        return self

    @typing.overload
    def get_type_dependency(self, type_: type[_T], /) -> _T: ...

    @typing.overload
    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT) -> _T | _DefaultT: ...

    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT | _NoValue = _NO_VALUE) -> _T | _DefaultT:
        # <<inherited docstring from alluka.abc.Client>>.
        result = self._type_dependencies.get(type_, default)

        if result is _NO_VALUE:
            raise KeyError

        return result

    def remove_type_dependency(self, type_: type[typing.Any], /) -> Self:
        # <<inherited docstring from alluka.abc.Client>>.
        del self._type_dependencies[type_]
        return self

    def set_callback_override(self, callback: alluka.CallbackSig[_T], override: alluka.CallbackSig[_T], /) -> Self:
        # <<inherited docstring from alluka.abc.Client>>.
        self._callback_overrides[callback] = override
        return self

    def get_callback_override(self, callback: alluka.CallbackSig[_T], /) -> alluka.CallbackSig[_T] | None:
        # <<inherited docstring from alluka.abc.Client>>.
        return self._callback_overrides.get(callback)

    def remove_callback_override(self, callback: alluka.CallbackSig[_T], /) -> Self:
        # <<inherited docstring from alluka.abc.Client>>.
        del self._callback_overrides[callback]
        return self

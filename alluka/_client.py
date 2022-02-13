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
"""Alluka's standard injection client implementation."""
from __future__ import annotations

__all__: list[str] = ["BasicContext", "Client", "Injected", "InjectedDescriptor", "inject"]

import asyncio
import enum
import inspect
import sys
import types
import typing
import weakref
from collections import abc as collections

from . import _errors
from . import abc

_T = typing.TypeVar("_T")


class _InjectedTypes(int, enum.Enum):
    CALLBACK = enum.auto()
    TYPE = enum.auto()


class _InjectedCallback:
    __slots__ = ("callback", "is_async")

    def __init__(self, callback: abc.CallbackSig[typing.Any], /) -> None:
        self.callback = callback

    def resolve(self, ctx: abc.Context) -> typing.Any:
        return ctx.injection_client.execute_with_ctx(ctx, self.callback)

    def resolve_async(self, ctx: abc.Context) -> collections.Coroutine[typing.Any, typing.Any, typing.Any]:
        return ctx.injection_client.execute_async_with_ctx(ctx, self.callback)


class _Descriptors:
    __slots__ = ("descriptors", "is_async")

    def __init__(self, descriptors: dict[str, _InjectedTuple], /) -> None:
        self.descriptors = descriptors
        self.is_async: typing.Optional[bool] = None

    def __bool__(self) -> bool:
        return bool(self.descriptors)


if sys.version_info >= (3, 10):
    _UnionTypes = {typing.Union, types.UnionType}
    _NoneType = types.NoneType

else:
    _UnionTypes = {typing.Union}
    _NoneType = type(None)


class _InjectedType:
    __slots__ = ("base_type", "default", "union_fields")

    def __init__(self, base_type: type[typing.Any], /, *, default: _UndefinedOr[typing.Any] = abc.UNDEFINED) -> None:
        self.base_type = base_type
        self.default = default
        self.union_fields: typing.Optional[list[type[typing.Any]]] = None

        if typing.get_origin(base_type) not in _UnionTypes:
            return

        sub_types = list(typing.get_args(base_type))
        try:
            sub_types.remove(_NoneType)
        except ValueError:
            pass
        else:
            if self.default is abc.UNDEFINED:
                self.default = None

        self.union_fields = sub_types

    def resolve(self, ctx: abc.Context) -> typing.Any:
        # <<inherited docstring from AbstractDescriptor>>.
        if (result := ctx.get_type_dependency(self.base_type)) is not abc.UNDEFINED:
            return result

        # We still want to allow for the possibility of a Union being
        # explicitly implemented so we check types within a union
        # after the literal type.
        if self.union_fields:
            for cls in self.union_fields:
                if (result := ctx.get_type_dependency(cls)) is not abc.UNDEFINED:
                    return result

        if self.default is not abc.UNDEFINED:
            return self.default

        raise _errors.MissingDependencyError(
            f"Couldn't resolve injected type {self.union_fields} to actual value"
        ) from None


_BasicContextT = typing.TypeVar("_BasicContextT", bound="BasicContext")
_ClientT = typing.TypeVar("_ClientT", bound="Client")
_InjectedTuple = typing.Union[
    tuple[typing.Literal[_InjectedTypes.CALLBACK], _InjectedCallback],
    tuple[typing.Literal[_InjectedTypes.TYPE], _InjectedType],
]
_UndefinedOr = typing.Union[abc.Undefined, _T]
_TypeT = type[_T]


class InjectedDescriptor(typing.Generic[_T]):
    """Descriptor used to a keyword-argument as requiring an injected dependency.

    This is the type returned by `inject`.
    """

    __slots__ = ("callback", "type")

    def __init__(
        self,
        *,
        callback: typing.Optional[abc.CallbackSig[_T]] = None,
        type: typing.Optional[_TypeT[_T]] = None,  # noqa: A002
    ) -> None:  # TODO: add default/factory to this?
        """Initialise an injection default descriptor.

        ... note
            If neither `type` or `callback` is provided, an injected type
            will be inferred from the argument's annotation.

        Parameters
        ----------
        callback : alluka.abc.CallbackSig | None
            The callback to use to resolve the dependency.

            If this callback has no type dependencies then this will still work
            without an injection context but this can be overridden using
            `InjectionClient.set_callback_override`.
        type : type | None
            The type of the dependency to resolve.

            If a union (e.g. `typing.Union[A, B]`, `A | B`, `typing.Optional[A]`)
            is passed for `type` then each type in the union will be tried
            separately after the litarl union type is tried, allowing for resolving
            `A | B` to the value set by `set_type_dependency(B, ...)`.

            If a union has `None` as one of its types (including `Optional[T]`)
            then `None` will be passed for the parameter if none of the types could
            be resolved using the linked client.
        """
        if callback is None and type is None:
            raise ValueError("Must specify one of `callback` or `type`")

        if callback is not None and type is not None:
            raise ValueError("Only one of `callback` or `type` can be specified")

        self.callback = callback
        self.type = type


Injected = typing.Annotated[_T, _InjectedTypes.TYPE]
"""Type alias used to declare an keyword argument as requiring an injected type."""


@typing.overload
def inject(*, callback: abc.CallbackSig[_T]) -> _T:
    ...


@typing.overload
def inject(*, type: _TypeT[_T]) -> _T:  # noqa: A002
    ...


@typing.overload
def inject(*, type: typing.Any = None) -> typing.Any:  # noqa: A002
    ...


def inject(
    *,
    callback: typing.Optional[abc.CallbackSig[_T]] = None,
    type: typing.Any = None,  # noqa: A002
) -> typing.Any:
    """Decare a keyword-argument as requiring an injected dependency.

    This may be assigned to an arugment's default value to declare injection
    or as a part of its Annotated metadata.

    ... note
        If neither `type` or `callback` is provided, an injected type
        will be inferred from the argument's annotation.

    Examples
    --------
    ```py
    @tanjun.as_slash_command("name", "description")
    async def command_callback(
        ctx: tanjun.abc.Context,
        # Here we take advantage of scope based special casing which allows
        # us to inject the `Component` type.
        injected_type: tanjun.abc.Component = tanjun.inject(type=tanjun.abc.Component)
        # Here we inject an out-of-scope callback which itself is taking
        # advantage of type injection.
        callback_result: ResultT = tanjun.inject(callback=injected_callback)
    ) -> None:
        raise NotImplementedError
    ```

    Parameters
    ----------
    callback : alluka.abc.CallbackSig | None
        The callback to use to resolve the dependency.

        If this callback has no type dependencies then this will still work
        without an injection context but this can be overridden using
        `InjectionClient.set_callback_override`.
    type : type | None
        The type of the dependency to resolve.

        If a union (e.g. `typing.Union[A, B]`, `A | B`, `typing.Optional[A]`)
        is passed for `type` then each type in the union will be tried
        separately after the litarl union type is tried, allowing for resolving
        `A | B` to the value set by `set_type_dependency(B, ...)`.

        If a union has `None` as one of its types (including `Optional[T]`)
        then `None` will be passed for the parameter if none of the types could
        be resolved using the linked client.
    """
    return typing.cast(_T, InjectedDescriptor(callback=callback, type=type))


def _process_annotation(
    annotation: typing.Any, default: _UndefinedOr[typing.Any]
) -> typing.Union[_InjectedTuple, None]:
    if typing.get_origin(annotation) is not typing.Annotated:
        return None

    args = typing.get_origin(annotation)
    assert args
    if _InjectedTypes.TYPE in args:
        return (_InjectedTypes.TYPE, _InjectedType(args[0]))

    for arg in args:
        if not isinstance(arg, InjectedDescriptor):
            continue

        if arg.callback:
            return (_InjectedTypes.CALLBACK, _InjectedCallback(arg.callback))

        if arg.type:
            return (_InjectedTypes.TYPE, _InjectedType(arg.type, default=default))

    return (_InjectedTypes.TYPE, _InjectedType(args[0], default=default))


def _parse_callback(
    callback: abc.CallbackSig[typing.Any], /, *, introspect_annotations: bool
) -> dict[str, _InjectedTuple]:
    try:
        parameters = inspect.signature(callback).parameters.items()
    except ValueError:  # If we can't inspect it then we have to assume this is a NO
        # As a note, this fails on some "signature-less" builtin functions/types like str.
        return {}

    annotations = typing.get_type_hints(callback) if introspect_annotations else {}
    descriptors: dict[str, _InjectedTuple] = {}
    for name, parameter in parameters:
        if parameter.default is not parameter.empty and isinstance(parameter.default, InjectedDescriptor):
            descriptor = parameter.default

        else:
            default = abc.UNDEFINED if parameter.default is parameter.empty else parameter.default
            if result := _process_annotation(annotations.get(name), default=default):
                descriptors[name] = result

            continue

        if parameter.kind is parameter.POSITIONAL_ONLY:
            raise ValueError("Injected positional only arguments are not supported")

        if descriptor.callback is not None:
            descriptors[name] = (_InjectedTypes.CALLBACK, _InjectedCallback(descriptor.callback))

        elif descriptor.type is not None:
            descriptors[name] = (_InjectedTypes.TYPE, _InjectedType(descriptor.type))

        else:
            try:
                descriptors[name] = (_InjectedTypes.TYPE, _InjectedType(annotations[name]))

            except KeyError:
                raise ValueError(f"Could not resolve type for parameter {name!r} with no annotation") from None

    return descriptors


class Client(abc.Client):
    """Dependency injection client used by Tanjun's standard implementation."""

    __slots__ = ("_callback_overrides", "_descriptors", "_introspect_annotations", "_type_dependencies")

    def __init__(self, introspect_annotations: bool = True) -> None:
        """Initialise an injector client."""
        self._callback_overrides: dict[abc.CallbackSig[typing.Any], abc.CallbackSig[typing.Any]] = {}
        self._descriptors: weakref.WeakKeyDictionary[
            abc.CallbackSig[typing.Any], _Descriptors
        ] = weakref.WeakKeyDictionary()
        self._introspect_annotations = introspect_annotations
        self._type_dependencies: dict[type[typing.Any], typing.Any] = {Client: self}

    def _build_descriptors(self, callback: abc.CallbackSig[typing.Any], /) -> _Descriptors:
        try:
            return self._descriptors[callback]

        except KeyError:
            pass

        descriptors = _Descriptors(_parse_callback(callback, introspect_annotations=self._introspect_annotations))
        self._descriptors[callback] = descriptors
        return descriptors

    def execute(self, callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any) -> _T:
        return self.execute_with_ctx(BasicContext(self), callback, *args, **kwargs)

    def execute_with_ctx(
        self, ctx: abc.Context, callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any
    ) -> _T:
        descriptors = self._build_descriptors(callback)

        if descriptors.is_async:
            raise _errors.AsyncOnlyError

        if descriptors:
            kwargs = {n: v.resolve(ctx) for n, (_, v) in descriptors.descriptors.items()}

        else:
            kwargs = {}

        result = callback(ctx, *args, **kwargs)
        if descriptors.is_async is None:
            if asyncio.iscoroutine(result):
                descriptors.is_async = True
                raise _errors.AsyncOnlyError

            descriptors.is_async = False

        return result

    async def execute_async(self, callback: abc.CallbackSig[_T], *args: typing.Any, **kwargs: typing.Any) -> _T:
        return await self.execute_async_with_ctx(BasicContext(self), callback, *args, **kwargs)

    async def execute_async_with_ctx(
        self, ctx: abc.Context, callback: abc.CallbackSig[_T], *args: typing.Any, **kwargs: typing.Any
    ) -> _T:
        if descriptors := self._build_descriptors(callback):
            kwargs = {
                n: v[1].resolve(ctx) if v[0] is _InjectedTypes.TYPE else await v[1].resolve_async(ctx)
                for n, v in descriptors.descriptors.items()
            }

        else:
            kwargs = {}

        result = callback(ctx, *args, **kwargs)
        if descriptors.is_async is None:
            descriptors.is_async = asyncio.iscoroutine(result)

        if descriptors.is_async:
            assert asyncio.iscoroutine(result)
            return typing.cast(_T, await result)

        assert not isinstance(result, collections.Coroutine)
        return result

    def set_type_dependency(self: _ClientT, type_: type[_T], value: _T, /) -> _ClientT:
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

        self._type_dependencies[type_] = value
        return self

    def get_type_dependency(self, type_: type[_T], /) -> _UndefinedOr[_T]:
        return self._type_dependencies.get(type_, abc.UNDEFINED)

    def remove_type_dependency(self: _ClientT, type_: type[typing.Any], /) -> _ClientT:
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
        del self._type_dependencies[type_]
        return self

    def set_callback_override(
        self: _ClientT, callback: abc.CallbackSig[_T], override: abc.CallbackSig[_T], /
    ) -> _ClientT:
        """Override a specific injected callback.

        .. note::
            This does not effect the callbacks set for type injectors.

        Parameters
        ----------
        callback: alluka.abc.CallbackSig[_T]
            The injected callback to override.
        override: alluka.abc.CallbackSig[_T]
            The callback to use instead.

        Returns
        -------
        Self
            The client instance to allow chaining.
        """
        self._callback_overrides[callback] = override
        return self

    def get_callback_override(self, callback: abc.CallbackSig[_T], /) -> typing.Optional[abc.CallbackSig[_T]]:
        return self._callback_overrides.get(callback)

    def remove_callback_override(self: _ClientT, callback: abc.CallbackSig[_T], /) -> _ClientT:
        """Remove a callback override.

        Parameters
        ----------
        callback: alluka.abc.CallbackSig
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
        del self._callback_overrides[callback]
        return self


class BasicContext(abc.Context):
    """Basic implementation of a `alluka.abc.Context`."""

    __slots__ = ("_injection_client", "_result_cache", "_special_case_types")

    def __init__(self, client: abc.Client, /) -> None:
        """Initialise a basic injection context.

        Parameters
        ----------
        client : alluka.abc.Client
            The injection client this context is bound to.
        """
        self._injection_client = client
        self._result_cache: typing.Optional[dict[abc.CallbackSig[typing.Any], typing.Any]] = None
        self._special_case_types: typing.Optional[dict[type[typing.Any], typing.Any]] = None

    @property
    def injection_client(self) -> abc.Client:
        # <<inherited docstring from alluka.abc.Client>>.
        return self._injection_client

    def cache_result(self, callback: abc.CallbackSig[_T], value: _T, /) -> None:
        # <<inherited docstring from alluka.abc.Client>>.
        if self._result_cache is None:
            self._result_cache = {}

        self._result_cache[callback] = value

    def get_cached_result(self, callback: abc.CallbackSig[_T], /) -> _UndefinedOr[_T]:
        # <<inherited docstring from alluka.abc.Client>>.
        return self._result_cache.get(callback, abc.UNDEFINED) if self._result_cache else abc.UNDEFINED

    def get_type_dependency(self, type_: type[_T], /) -> _UndefinedOr[_T]:
        # <<inherited docstring from alluka.abc.Client>>.
        if (
            self._special_case_types
            and (value := self._special_case_types.get(type_, abc.UNDEFINED)) is not abc.UNDEFINED
        ):
            return typing.cast(_T, value)

        return self._injection_client.get_type_dependency(type_)

    def _set_type_special_case(self: _BasicContextT, type_: type[_T], value: _T, /) -> _BasicContextT:
        if not self._special_case_types:
            self._special_case_types = {}

        self._special_case_types[type_] = value
        return self

    def _remove_type_special_case(self: _BasicContextT, type_: type[typing.Any], /) -> _BasicContextT:
        if not self._special_case_types:
            raise KeyError(type_)

        del self._special_case_types[type_]
        return self

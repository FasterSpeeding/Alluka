# -*- coding: utf-8 -*-
# BSD 3-Clause License
#
# Copyright (c) 2020-2023, Faster Speeding
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
"""Internal types used by Alluka."""
from __future__ import annotations

__all__: list[str] = ["Injected", "InjectedDescriptor"]

import enum
import typing

from . import _errors  # pyright: ignore[reportPrivateUsage]
from . import abc as alluka

if typing.TYPE_CHECKING:
    from collections import abc as collections


_T = typing.TypeVar("_T")


class _UndefinedEnum(enum.Enum):
    UNDEFINED = object()


UNDEFINED = _UndefinedEnum.UNDEFINED
"""Singleton used internally to indicate that a value is undefined."""
UndefinedOr = typing.Union[_T, typing.Literal[_UndefinedEnum.UNDEFINED]]
"""Union for a value which may be undefined."""


class InjectedCallback:
    """Descriptor of a callback that's being used to resolve a paremeter's value."""

    __slots__ = ("callback",)

    def __init__(self, callback: alluka.CallbackSig[typing.Any], /) -> None:
        """Initialize the callback descriptor.

        Parameters
        ----------
        callback
            The callback to use to resolve the parameter's value.
        """
        self.callback = callback

    def resolve(self, ctx: alluka.Context) -> typing.Any:
        """Synchronously resolve the callback.

        !!! warning
            Unlike [InjectedCallback.resolve_async][], this method will block the
            current thread and does not support async callback dependencies.

        Parameters
        ----------
        ctx
            The context to use when resolving the callback.

        Raises
        ------
        alluka.SyncOnlyError
            If the callback or any of its callback dependencies are async.
        alluka.MissingDependencyError
            If any of the callback's type dependencies aren't implemented by
            the context's client.
        """
        callback = ctx.injection_client.get_callback_override(self.callback) or self.callback
        return ctx.injection_client.call_with_ctx(ctx, callback)

    def resolve_async(self, ctx: alluka.Context) -> collections.Coroutine[typing.Any, typing.Any, typing.Any]:
        """Asynchronously resolve the callback.

        Parameters
        ----------
        ctx
            The context to use when resolving the callback.

        Raises
        ------
        alluka.MissingDependencyError
            If any of the callback's type dependencies aren't implemented by
            the context's client.
        """
        callback = ctx.injection_client.get_callback_override(self.callback) or self.callback
        return ctx.injection_client.call_with_ctx_async(ctx, callback)


class InjectedType:
    """Descriptor of a type that a parameter's value is being resolved to."""

    __slots__ = ("default", "repr_type", "types")

    def __init__(
        self,
        repr_type: typing.Any,
        types: collections.Sequence[type[typing.Any]],
        /,
        *,
        default: UndefinedOr[typing.Any] = UNDEFINED,
    ) -> None:
        """Initialize the type descriptor.

        Parameters
        ----------
        base_type
            The type to resolve to.
        default
            The default value to use if the type can't be resolved.

            Without a default, any attempts to resolve a type that isn't implemented
            by the linked client will lead to [alluka.MissingDependencyError][].
        """
        self.default = default
        self.repr_type = repr_type
        self.types = types

    def resolve(self, ctx: alluka.Context) -> typing.Any:
        """Resolve the type.

        Parameters
        ----------
        ctx
            The context to use when resolving the type.

        Returns
        -------
        typing.Any
            The resolved type.
        """
        for cls in self.types:
            if (result := ctx.get_type_dependency(cls, default=UNDEFINED)) is not UNDEFINED:
                return result

        if self.default is not UNDEFINED:
            return self.default

        raise _errors.MissingDependencyError(
            f"Couldn't resolve injected type(s) {self.repr_type} to actual value", self.repr_type
        ) from None


class InjectedTypes(int, enum.Enum):
    """Enum of the different types of injected values."""

    CALLBACK = enum.auto()
    """An injeted callback.

    The result of the callback will be used as the value of the parameter.
    """

    TYPE = enum.auto()
    """An injected type.

    An implementation of a this type from the linked client will be injected
    as the value of the parameter.
    """


InjectedTuple = typing.Union[
    tuple[typing.Literal[InjectedTypes.CALLBACK], InjectedCallback],
    tuple[typing.Literal[InjectedTypes.TYPE], InjectedType],
]
"""Type of the tuple used to describe an injected value."""

_TypeT = type[_T]


class InjectedDescriptor(typing.Generic[_T]):
    """Descriptor used to a declare keyword-argument as requiring an injected dependency.

    This is the type returned by [alluka.inject][].
    """

    __slots__ = ("callback", "type")

    callback: typing.Optional[alluka.CallbackSig[_T]]
    """The callback to use to resolve the parameter's value.

    If this is `None` then this is a type dependency.
    """

    type: typing.Optional[_TypeT[_T]]  # noqa: VNE003
    """The type to use to resolve the parameter's value.

    If both this and `callback` are `None`, then this is a type dependency
    and the type will be inferred from the parameter's annotation.
    """

    def __init__(
        self,
        *,
        callback: typing.Optional[alluka.CallbackSig[_T]] = None,
        type: typing.Optional[_TypeT[_T]] = None,  # noqa: A002
    ) -> None:  # TODO: add default/factory to this?
        """Initialise an injection default descriptor.

        !!! note
            If neither `type` or `callback` is provided, an injected type
            will be inferred from the argument's annotation.

        Parameters
        ----------
        callback
            The callback to use to resolve the dependency.

            If this callback has no type dependencies then this will still work
            without an injection context but this can be overridden using
            [alluka.abc.Client.set_callback_override][].
        type
            The type of the dependency to resolve.

            If a union (e.g. `typing.Union[A, B]`, `A | B`, `typing.Optional[A]`)
            is passed for `type` then each type in the union will be tried
            separately after the litarl union type is tried, allowing for resolving
            `A | B` to the value set by `set_type_dependency(B, ...)`.

            If a union has `None` as one of its types (including `Optional[T]`)
            then `None` will be passed for the parameter if none of the types could
            be resolved using the linked client.

        Raises
        ------
        ValueError
            If both `callback` and `type` are provided.
        """
        if callback is not None and type is not None:
            raise ValueError("Only one of `callback` or `type` can be specified")

        self.callback = callback
        self.type = type


Injected = typing.Annotated[_T, InjectedTypes.TYPE]
"""Type alias used to declare a keyword argument as requiring an injected type.

If a union (e.g. `typing.Union[A, B]`, `A | B`, `typing.Optional[A]`)
is passed then each type in the union will be tried separately rather than
the literal type, allowing for resolving `A | B` to the value set by
`set_type_dependency(B, ...)`.

If a union has `None` as one of its types (including `Optional[T]`)
then `None` will be passed for the parameter if none of the types could
be resolved using the linked client.

!!! note
    This is a [typing.Annotated][] alias and the behaviour for nested
    Annotated types may be found at the docs for it [typing.Annotated][].
"""

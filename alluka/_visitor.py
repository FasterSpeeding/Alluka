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
"""The standard visitor and nodes used to parse function parameters."""
from __future__ import annotations

__all__: list[str] = ["Callback", "ParameterVisitor"]

import abc
import sys
import types
import typing

from . import _types  # pyright: ignore[reportPrivateUsage]
from ._vendor import inspect

if typing.TYPE_CHECKING:
    from collections import abc as collections


if sys.version_info >= (3, 10):
    _UnionTypes = frozenset((typing.Union, types.UnionType))
    _NoneType = types.NoneType

else:
    _UnionTypes = frozenset((typing.Union,))
    _NoneType = type(None)


class Node(abc.ABC):
    """Represents a node which may hold parameter injection information."""

    __slots__ = ()

    @abc.abstractmethod
    def accept(self, visitor: ParameterVisitor, /) -> typing.Optional[_types.InjectedTuple]:
        ...


class Annotation(Node):
    """Node which represent's a parameter's type-hint."""

    __slots__ = ("_callback", "_name", "_raw_annotation")

    def __init__(self, callback: Callback, name: str, /):
        self._callback = callback
        self._name = name
        self._raw_annotation = callback.parameters[name].annotation

    @property
    def callback(self) -> Callback:
        return self._callback

    @property
    def name(self) -> str:
        return self._name

    def accept(self, visitor: ParameterVisitor, /) -> typing.Optional[_types.InjectedTuple]:
        return visitor.visit_annotation(self)


class Callback:
    """Represents a callback being scanned for DI."""

    __slots__ = ("_callback", "_resolved", "_signature")

    def __init__(self, callback: collections.Callable[..., typing.Any], /) -> None:
        self._callback: collections.Callable[..., typing.Any] = callback
        self._resolved = False
        try:
            self._signature: typing.Optional[inspect.Signature] = inspect.signature(callback)
        except ValueError:  # If we can't inspect it then we have to assume this is a NO
            # As a note, this fails on some "signature-less" builtin functions/types like str.
            self._signature = None

    @property
    def parameters(self) -> collections.Mapping[str, inspect.Parameter]:
        return self._signature.parameters if self._signature else {}

    def accept(self, visitor: ParameterVisitor, /) -> dict[str, _types.InjectedTuple]:
        return visitor.visit_callback(self)

    def resolve_annotation(self, name: str, /) -> _types.UndefinedOr[typing.Any]:
        if self._signature is None:
            return _types.UNDEFINED

        parameter = self._signature.parameters[name]
        if parameter.annotation is inspect.Parameter.empty:
            return _types.UNDEFINED

        # TODO: do we want to return UNDEFINED if it was resolved to a string?
        if not self._resolved and isinstance(parameter.annotation, str):
            self._signature = inspect.signature(self._callback, eval_str=True)
            self._resolved = True
            return self.resolve_annotation(name)

        return parameter.annotation


class Default(Node):
    """Node which represent a parameter's default value."""

    __slots__ = ("_callback", "_default", "_name")

    def __init__(self, callback: Callback, name: str, /) -> None:
        self._callback = callback
        self._default = callback.parameters[name].default
        self._name = name

    @property
    def callback(self) -> Callback:
        return self._callback

    @property
    def default(self) -> typing.Any:
        return self._default

    @property
    def is_empty(self) -> bool:
        return self._default is inspect.Parameter.empty

    @property
    def name(self) -> str:
        return self._name

    def accept(self, visitor: ParameterVisitor, /) -> typing.Optional[_types.InjectedTuple]:
        return visitor.visit_default(self)


class ParameterVisitor:
    """Visitor class for parsing a callback for injected parameters."""

    __slots__ = ()

    _NODES: list[collections.Callable[[Callback, str], Node]] = [Default, Annotation]

    def _parse_type(
        self, type_: typing.Any, *, default: _types.UndefinedOr[typing.Any] = _types.UNDEFINED
    ) -> _types.InjectedTuple:
        if typing.get_origin(type_) not in _UnionTypes:
            return (_types.InjectedTypes.TYPE, _types.InjectedType(type_, [type_], default=default))

        sub_types = list(typing.get_args(type_))
        try:
            sub_types.remove(_NoneType)
        except ValueError:
            return (_types.InjectedTypes.TYPE, _types.InjectedType(type_, sub_types, default=default))

        # Explicitly defined defaults take priority over implicit defaults.
        default = None if default is _types.UNDEFINED else default
        return (_types.InjectedTypes.TYPE, _types.InjectedType(type_, sub_types, default=default))

    def _annotation_to_type(
        self, value: typing.Any, /, default: _types.UndefinedOr[typing.Any] = _types.UNDEFINED
    ) -> _types.InjectedTuple:
        if typing.get_origin(value) is typing.Annotated:
            args = typing.get_args(value)
            # The first "type" arg of annotated will always be flatterned to a type.
            # so we don't have to deal with Annotated nesting".
            value = args[0]

        return self._parse_type(value, default=default)

    def visit_annotation(self, annotation: Annotation, /) -> typing.Optional[_types.InjectedTuple]:
        value = annotation.callback.resolve_annotation(annotation.name)
        default = annotation.callback.parameters[annotation.name].default
        if default is inspect.Parameter.empty:
            default = _types.UNDEFINED

        if typing.get_origin(value) is not typing.Annotated:
            return None

        args = typing.get_args(value)
        if _types.InjectedTypes.TYPE in args:
            return self._annotation_to_type(args[0], default=default)

        arg: typing.Union[_types.InjectedDescriptor[typing.Any], typing.Any]
        for arg in args:
            if not isinstance(arg, _types.InjectedDescriptor):
                continue

            if arg.callback:
                return (_types.InjectedTypes.CALLBACK, _types.InjectedCallback(arg.callback))

            if arg.type:
                return self._parse_type(arg.type, default=default)

            return self._annotation_to_type(args[0], default=default)

        return None  # MyPy

    def visit_callback(self, callback: Callback, /) -> dict[str, _types.InjectedTuple]:
        results: dict[str, _types.InjectedTuple] = {}
        for name, value in callback.parameters.items():
            for node in self._NODES:
                result = node(callback, name).accept(self)
                if not result:
                    continue

                if value.kind is value.POSITIONAL_ONLY:
                    raise ValueError("Injected positional only arguments are not supported")

                results[name] = result
                break

        return results

    def visit_default(self, value: Default, /) -> typing.Optional[_types.InjectedTuple]:
        if value.is_empty or not isinstance(value.default, _types.InjectedDescriptor):
            return None  # MyPy

        descriptor: _types.InjectedDescriptor[typing.Any] = value.default
        if descriptor.callback is not None:
            return (_types.InjectedTypes.CALLBACK, _types.InjectedCallback(descriptor.callback))

        if descriptor.type is not None:
            return self._parse_type(descriptor.type)

        if (annotation := value.callback.resolve_annotation(value.name)) is _types.UNDEFINED:
            raise ValueError(f"Could not resolve type for parameter {value.name!r} with no annotation")

        return self._annotation_to_type(annotation)

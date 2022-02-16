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
"""The standard visitor and nodes used to parse function parameters."""
from __future__ import annotations

import abc
import typing
from collections import abc as collections

from . import _types
from . import abc as alluca_abc
from ._vendor import inspect


class Node(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def accept(self, visitor: ParameterVisitor, /) -> typing.Optional[_types.InjectedTuple]:
        ...


class Annotation(Node):
    __slots__ = ("_callback", "_name", "_raw_annotation")

    def __init__(self, callback: Callback, name: str, /):
        self._callback = callback
        self._name = name
        self._raw_annotation = callback.parameters[name].annotation

    @property
    def callback(self) -> Callback:
        return self._callback

    @property
    def is_empty(self) -> bool:
        return self._raw_annotation is inspect.Parameter.empty

    @property
    def name(self) -> str:
        return self._name

    @property
    def raw_annotation(self) -> typing.Any:
        return self._raw_annotation

    def accept(self, visitor: ParameterVisitor, /) -> typing.Optional[_types.InjectedTuple]:
        return visitor.visit_annotation(self)


class Callback:
    __slots__ = ("_callback", "_resolved", "_signature")

    def __init__(self, callback: collections.Callable[..., typing.Any], /) -> None:
        self._callback: collections.Callable[..., typing.Any] = callback
        self._resolved = False
        self._signature = inspect.signature(callback)

    @property
    def callback(self) -> collections.Callable[..., typing.Any]:
        return self._callback

    @property
    def parameters(self) -> collections.Mapping[str, inspect.Parameter]:
        return self._signature.parameters

    def accept(self, visitor: ParameterVisitor, /) -> dict[str, _types.InjectedTuple]:
        return visitor.visit_callback(self)

    def resolve_annotation(self, name: str, /) -> _types.UndefinedOr[typing.Any]:
        parameter = self._signature.parameters[name]
        if parameter.annotation is inspect.Parameter.empty:
            return alluca_abc.UNDEFINED

        # TODO: do we want to return UNDEFINED if it was resolved to a string?
        if isinstance(parameter.annotation, str) and not self._resolved:
            self._signature = inspect.signature(self._callback, eval_str=True)
            self._resolved = True
            return self.resolve_annotation(name)

        return parameter.annotation


class Default(Node):
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


def _or_undefined(value: typing.Any) -> _types.UndefinedOr[typing.Any]:
    if value is inspect.Parameter.empty:
        return alluca_abc.UNDEFINED

    return value


class ParameterVisitor:
    __slots__ = ()

    _NODES: list[collections.Callable[[Callback, str], Node]] = [Default, Annotation]

    def visit_annotation(self, annotation: Annotation, /) -> typing.Optional[_types.InjectedTuple]:
        value = annotation.callback.resolve_annotation(annotation.name)

        if typing.get_origin(value) is not typing.Annotated:
            return None

        default = _or_undefined(annotation.callback.parameters[annotation.name].default)
        args = typing.get_origin(value)
        assert args
        if _types.InjectedTypes.TYPE in args:
            return (_types.InjectedTypes.TYPE, _types.InjectedType(args[0]))

        for arg in args:
            if not isinstance(arg, _types.InjectedDescriptor):
                continue

            if arg.callback:
                return (_types.InjectedTypes.CALLBACK, _types.InjectedCallback(arg.callback))

            if arg.type:
                return (_types.InjectedTypes.TYPE, _types.InjectedType(arg.type, default=default))

        return (_types.InjectedTypes.TYPE, _types.InjectedType(args[0], default=default))

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

    def visit_default(self, default: Default, /) -> typing.Optional[_types.InjectedTuple]:
        if default.is_empty or not isinstance(default.default, _types.InjectedDescriptor):
            return

        descriptor = default.default
        if descriptor.callback is not None:
            return (_types.InjectedTypes.CALLBACK, _types.InjectedCallback(descriptor.callback))

        if descriptor.type is not None:
            return (_types.InjectedTypes.TYPE, _types.InjectedType(descriptor.type))

        if (annotation := default.callback.resolve_annotation(default.name)) is alluca_abc.UNDEFINED:
            raise ValueError(f"Could not resolve type for parameter {default.name!r} with no annotation")

        assert not isinstance(annotation, alluca_abc.Undefined)
        return (_types.InjectedTypes.TYPE, _types.InjectedType(annotation))

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
"""Classes used for manually injecting types and callbacks."""
from __future__ import annotations

__list__: list[str] = ["DefinedInjectors", "ManuallyInjected"]

import asyncio
import inspect
import itertools
import textwrap
import typing
from collections import abc as collections

from . import _types
from . import abc as alluka

if typing.TYPE_CHECKING:
    import typing_extensions

    _P = typing_extensions.ParamSpec("_P")


_CallbackSigT = typing.TypeVar("_CallbackSigT", bound=collections.Callable[..., typing.Any])
_CodeBuilderT = typing.TypeVar("_CodeBuilderT", bound="CodeBuilder[typing.Any]")
_ManuallyInjectedT = typing.TypeVar("_ManuallyInjectedT", bound="ManuallyInjected[typing.Any]")
_T = typing.TypeVar("_T")
_T_co = typing.TypeVar("_T_co", covariant=True)

BuiltSig = collections.Callable[[alluka.Context, tuple[typing.Any, ...], dict[str, typing.Any]], _T]
_CoroT = collections.Coroutine[typing.Any, typing.Any, _T]


class DefinedInjectors(typing.Protocol[_T_co]):
    if not typing.TYPE_CHECKING:
        __slots__ = ()

    def get_async_injector(self) -> BuiltSig[_CoroT[_T_co]]:
        raise NotImplementedError

    def get_injector(self) -> BuiltSig[_T_co]:
        raise NotImplementedError


def has_predefined_injectors(value: typing.Any) -> typing_extensions.TypeGuard[DefinedInjectors[typing.Any]]:
    try:
        value.get_async_injector
        value.get_injector
    except AttributeError:
        return False

    return True


def _resolve(name: str, /) -> str:
    return f"{name}=i_{name}.resolve(ctx)"


def _resolve_async(name: str, /) -> str:
    return f"{name}=await i_{name}.resolve_async(ctx)"


class CodeBuilder(typing.Generic[_T]):
    """Function specific DI logic builder.

    This caches the built logic.
    """

    __slots__ = ("_async_built", "_built", "_callback", "_callbacks", "_types")

    def __init__(self, callback: alluka.CallbackSig[_T], /) -> None:
        """Initialise a DI logic builder.

        Parameters
        ----------
        callback : alluka.abc.CallbackSig
            The callback to create DI logic for.
        """
        self._async_built: BuiltSig[_CoroT[_T]] | None = None
        self._built: BuiltSig[_T] | None = None
        self._callback = callback
        self._callbacks: dict[str, _types.InjectedCallback] = {}
        self._types: dict[str, _types.InjectedType] = {}

    def _clear_cache(self) -> None:
        self._async_built = None
        self._built = None

    def set_callback(self: _CodeBuilderT, name: str, callback: _types.InjectedCallback, /) -> _CodeBuilderT:
        """Set an injected callback for an argument.

        Parameters
        ----------
        name
            The argument's name.
        callback
            The callback to inject the result of.

        Returns
        -------
        Self
            The code builder's object to allow call chaining.
        """
        self._clear_cache()
        self._callbacks[name] = callback
        return self

    def set_type(self: _CodeBuilderT, name: str, type_: _types.InjectedType) -> _CodeBuilderT:
        """Set an injected type for an argument.

        Parameters
        ----------
        name
            The argument's name.
        type_
            The type to inject.

        Returns
        -------
        Self
            The code builder's object to allow call chaining.
        """
        self._clear_cache()
        self._types[name] = type_
        return self

    def set_injected(self: _CodeBuilderT, name: str, injected: _types.InjectedTuple, /) -> _CodeBuilderT:
        """Set an injected argument.

        Parameters
        ----------
        name
            The argument's name
        injected
            The callback or type to inject.

        Returns
        -------
        Self
            The code builder's object to allow call chaining.
        """
        # Pyright currently doesn't support `is` for narrowing tuple types like this.
        if injected[0] == _types.InjectedTypes.CALLBACK:
            self.set_callback(name, injected[1])

        else:
            self.set_type(name, injected[1])

        return self

    def _exec(self, code: str) -> collections.Callable[..., typing.Any]:
        globals_: dict[str, typing.Any] = dict(  # noqa: C402 - Unnecessary generator - rewrite as a dict comprehension
            ((f"i_{name}", value) for name, value in itertools.chain(self._types.items(), self._callbacks.items())),
            callback=self._callback,
            iscoroutine=asyncio.iscoroutine,
        )
        code = compile(code, "", "exec")
        exec(code, globals_)  # noqa: S102 - Use of exec detected.
        result = globals_["resolve"]
        return typing.cast(collections.Callable[..., typing.Any], result)

    def _gen_no_inject(self) -> BuiltSig[_T]:
        def resolve(_: alluka.Context, args: tuple[typing.Any, ...], kwargs: dict[str, typing.Any], /) -> _T:
            return typing.cast(_T, self._callback(*args, **kwargs))

        self._built = resolve
        return resolve

    def build(self) -> BuiltSig[_T]:
        """Build the sync DI logic for this function.

        Returns
        -------
        BuiltSig[_T]
            The created sync DI function for this callback.

            This result will be cached.
        """
        if self._built:
            return self._built

        # Startup optimisation around avoiding unnecessary eval calls.
        if not self._types and not self._callbacks:
            return self._gen_no_inject()

        kwargs = ", ".join(map(_resolve, itertools.chain(self._types, self._callbacks)))
        code = textwrap.dedent(
            f"""
        def resolve(ctx, args, kwargs, /):
            return callback(*args, **kwargs, {kwargs})
        """
        )
        self._built = self._exec(code)
        return self._built

    def _gen_no_inject_async(self) -> BuiltSig[_CoroT[_T]]:
        async def resolve(_: alluka.Context, args: tuple[typing.Any, ...], kwargs: dict[str, typing.Any], /) -> _T:
            result = self._callback(*args, **kwargs)
            if asyncio.iscoroutine(result):
                return typing.cast(_T, await result)

            return typing.cast(_T, result)

        self._async_built = resolve
        return resolve

    def build_async(self) -> BuiltSig[_CoroT[_T]]:
        """Build the async DI logic for this function.

        Returns
        -------
        BuiltSig[collections.abc.Coroutine[typing.Any, typing.Any, _T]]
            The created async DI function for this callback.

            This result will be cached.
        """
        if self._async_built:
            return self._async_built

        # Startup optimisation around avoiding unnecessary eval calls.
        if not self._types and not self._callbacks:
            return self._gen_no_inject_async()

        kwargs = (", ".join(map(_resolve, self._types)) + ", " + ", ".join(map(_resolve_async, self._callbacks))).strip(
            ", "
        )
        code = textwrap.dedent(
            f"""
        async def resolve(ctx, args, kwargs, /):
            result = callback(*args, **kwargs, {kwargs})

            if iscoroutine(result):
                return await result

            return result
        """
        )
        self._async_built = self._exec(code)
        return self._async_built


_KEYWORD_TYPES = {inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY}


class ManuallyInjected(typing.Generic[_CallbackSigT]):
    """Manually declare the injected arguments for a callback.

    This will not perform any type inference.
    """

    __slots__ = ("_builder", "_callback", "_kwargs", "__weakref__")

    def __init__(self, callback: _CallbackSigT, /) -> None:
        """Initialise a callback with manual declared DI.

        Parameters
        ----------
        callback : alluka.abc.CallbackSig
            The callback to manually declare the injected arguments for.
        """
        self._builder = CodeBuilder[typing.Any](callback)
        self._callback = callback
        kwargs: list[str] = []

        try:
            signature = inspect.Signature.from_callable(callback)
        except ValueError:  # If we can't inspect it then we have to assume this is a NO
            # As a note, this fails on some "signature-less" builtin functions/types like str.
            return

        for parameter in signature.parameters.values():
            if parameter.kind in _KEYWORD_TYPES:
                kwargs.append(parameter.name)

            elif parameter.kind is parameter.VAR_KEYWORD:
                self._kwargs: list[str] | None = None
                break

        else:
            self._kwargs = kwargs

    def __call__(self: ManuallyInjected[collections.Callable[_P, _T]], *args: _P.args, **kwargs: _P.kwargs) -> _T:
        """Call this callback.

        !!! note
            To call this with dependency injection you'll have to pass this to
            [alluka.Client.call_with_di][]/[alluka.Client.call_with_async_di][]
            as the callback.

        Parameters
        ----------
        *args
            The positional arguments to pass to the function.
        **kwargs
            The keyword arguments to pass to the function.

        Return
        ------
        _T
            The result of the function call (will only be a coroutine if the
            function is async).
        """
        return self.callback(*args, **kwargs)

    @property
    def callback(self) -> _CallbackSigT:
        """The inner-callback."""
        return self._callback

    def _assert_name(self, name: str, /) -> None:
        if self._kwargs is not None and name not in self._kwargs:
            raise ValueError(f"{name} is not a valid keyword argument for {self._callback}")

    def get_async_injector(self: ManuallyInjected[alluka.CallbackSig[_T]]) -> BuiltSig[_CoroT[_T]]:
        """Internal function used by Alluka to get the async injection rules/logic."""
        return self._builder.build_async()

    def get_injector(self: ManuallyInjected[alluka.CallbackSig[_T]]) -> BuiltSig[_T_co]:
        """Internal function used by Alluka to get the sync injection rules/logic."""
        return self._builder.build()

    def set_callback(
        self: _ManuallyInjectedT, name: str, callback: alluka.CallbackSig[typing.Any], /
    ) -> _ManuallyInjectedT:
        """Set an injected callback for an argument.

        Parameters
        ----------
        name
            Name of the argument to set the callback DI for.
        callback
            The callback to inject the result of.

        Returns
        -------
        Self
            The manual injection object to allow call chaining.
        """
        self._assert_name(name)
        self._builder.set_callback(name, _types.InjectedCallback(callback))
        return self

    def set_type(
        self: _ManuallyInjectedT,
        name: str,
        type_: type[typing.Any],
        /,
        *other_types: type[typing.Any],
        default: typing.Any = _types.UNDEFINED,
    ) -> _ManuallyInjectedT:
        """Set an injected type for an argument.

        Parameters
        ----------
        name
            Name of the argument to set the injected type for.
        type_
            The first type to try to inject.
        *other_types
            Other types to try to inject.

            This acts as a union inject where the first type to be found with
            a registered value for it will be injected.
        default
            The value to inject if none of the registered types could be
            resolved.

            If not specified then a [alluka.MissingDependencyError][] will
            be raised if none of the types could be resolved.

        Returns
        -------
        Self
            The manual injection object to allow call chaining.
        """
        self._assert_name(name)
        types_ = (type_, *other_types)
        self._builder.set_type(
            name,
            _types.InjectedType(
                " | ".join(map(repr, types_)),
                types_,
                default=default,
            ),
        )
        return self

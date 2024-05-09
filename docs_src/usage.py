# -*- coding: utf-8 -*-
# Tanjun Examples - A collection of examples for Tanjun.
# Written in 2023 by Faster Speeding Lucina@lmbyrne.dev
#
# To the extent possible under law, the author(s) have dedicated all copyright
# and related and neighboring rights to this software to the public domain worldwide.
# This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software.
# If not, see <https://creativecommons.org/publicdomain/zero/1.0/>.

# pyright: reportUnusedFunction=none
# pyright: reportUnusedVariable=none

import typing

import alluka
import alluka.local


class Foo: ...


class BarResult: ...


bar_callback = BarResult


# fmt: off
def default_descriptor_example() -> None:
    def callback(
        foo: Foo = alluka.inject(type=Foo),
        bar: BarResult = alluka.inject(callback=bar_callback),
    ) -> None:
        ...
# fmt: on


def default_descriptor_inferred_type_example() -> None:
    async def callback(foo: Foo = alluka.inject()) -> None: ...


def type_hint_example() -> None:
    def callback(
        foo: typing.Annotated[Foo, alluka.inject(type=Foo)],
        bar: typing.Annotated[BarResult, alluka.inject(callback=bar_callback)],
    ) -> None: ...


def injected_example() -> None:
    async def callback(foo: alluka.Injected[Foo]) -> None: ...


# fmt: off
async def calling_with_di_example() -> None:
    client = alluka.Client()

    async def callback(
        argument: int,
        /,
        injected: alluka.Injected[Foo],
        keyword_arg: str,
    ) -> int:
        ...

    ...

    result = await client.call_with_async_di(callback, 123, keyword_arg="ok")
# fmt: on


# fmt: off
def calling_with_di_sync_example() -> None:
    client = alluka.Client()

    def callback(
        argument: int,
        /,
        injected: alluka.Injected[Foo],
        keyword_arg: str,
    ) -> int:
        ...

    ...

    result = client.call_with_di(callback, 123, keyword_arg="ok")
# fmt: on


def other_callback() -> None: ...


def context_di_example() -> None:
    def foo(ctx: alluka.Injected[alluka.abc.Context]) -> None:
        result = ctx.call_with_di(other_callback, 542, keyword_arg="meow")


def async_context_di_example() -> None:
    async def bar(ctx: alluka.Injected[alluka.abc.Context]) -> None:
        result = await ctx.call_with_async_di(other_callback, 123, keyword_arg="ok")


class TypeA: ...


TypeB = TypeA
type_a_impl = TypeA()
type_b_impl = TypeB()


# fmt: off
def setting_dependencies_example() -> None:
    client = (
        alluka.Client()
        .set_type_dependency(TypeA, type_a_impl)
        .set_type_dependency(TypeB, type_b_impl)
    )
# fmt: on


default_callback = other_callback


def override_callback_example() -> None:
    client = alluka.Client().set_callback_override(default_callback, other_callback)


async def initialize_example() -> None:
    client = alluka.local.initialize()
    client.set_type_dependency(TypeA, type_a_impl)

    ...

    async def callback(value: TypeA = alluka.inject()) -> None: ...

    result = await alluka.local.call_with_async_di(callback)


async def async_callback() -> None: ...


async def scoped_example() -> None:
    async def callback() -> None:
        result = await alluka.local.call_with_async_di(async_callback)

    with alluka.local.scope_client() as client:
        client.set_type_dependency(TypeA, type_a_impl)

        await callback()


async def local_auto_inject_example() -> None:
    @alluka.local.auto_inject_async
    async def callback(value: TypeA = alluka.inject()) -> None: ...

    with alluka.local.scope_client() as client:
        client.set_type_dependency(TypeA, type_a_impl)

        await callback()


def auto_inject_example() -> None:
    client = alluka.Client()

    @client.auto_inject
    def callback(other_arg: str, value: TypeA = alluka.inject()) -> None: ...

    callback(other_arg="beep")  # `value` will be injected.


async def auto_inject_async_example() -> None:
    client = alluka.Client()

    @client.auto_inject_async
    async def callback(value: TypeA = alluka.inject()) -> None: ...

    await callback()  # `value` will be injected.


def set_component_maker_example() -> None:
    client = alluka.Client().set_make_context(alluka.CachingContext)


def overriding_context_example() -> None:
    def callback(ctx: alluka.Injected[alluka.abc.Context]) -> None:
        ctx = alluka.OverridingContext(ctx).set_type_dependency(TypeA, type_a_impl)

        ctx.call_with_di(other_callback)


def overriding_context_from_client_example() -> None:
    client = alluka.Client().set_type_dependency(TypeA, type_a_impl)

    ctx = alluka.OverridingContext.from_client(client).set_type_dependency(TypeB, type_b_impl)

    ctx.call_with_di(other_callback)


def caching_example() -> None:
    client = alluka.Client().set_make_context(alluka.CachingContext)
    state = 0

    def injected_callback() -> int:
        nonlocal state
        state += 1

        return state

    def callback(
        result: int = alluka.inject(callback=injected_callback),
        other_result: int = alluka.inject(callback=injected_callback),
    ) -> None:
        print(result)
        print(other_result)

    client.call_with_di(callback)
    print("-")
    client.call_with_di(callback)

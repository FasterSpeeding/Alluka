# Usage

## Function injection

This form of dependency injection works by injecting values for keyword arguments during callback
execution based on the linked client. This is the main form of dependency injection implemented by
Alluka.

### Declaring a function's injected dependencies

There are two styles for declaring a function's injected dependencies in Alluka:

#### Default descriptors

```py
def callback(
    foo: Foo = alluka.inject(type=Foo)
    bar: BarResult = alluka.inject(callback=bar_callback)
) -> None:
    ...
```

Assigning the result of [alluka.inject][] to a parameter's default will declare it as requiring an
injected type or callback.

```py
async def callback(
    foo: Foo = alluka.inject()
) -> None:
    ...
```

If neither `type` nor `callback` is passed to [alluka.inject][] then a type dependency will be
inferred from the parameter's annotation.

!!! warning
    The type-hint will need to resolvable/accessible at runtime in the callback's module for it to
    be inferred (so it can't be hidden behind a [typing.TYPE_CHECKING][] only import or using a
    type or operation that isn't implemented in the current python version).

#### Type-hint metadata

[typing.Annotated][] style type-hint descriptors may be used to declare the injected dependencies
for a function.

```py
def callback(
    foo: typing.Annotated[Foo, alluka.inject(type=Foo)],
    bar: typing.Annotated[BarResult, alluka.inject(callback=bar_callback)]
) -> None:
    ...
```

Where passing the default descriptors returned by [alluka.inject][] to [typing.Annotated][] lets
you declare the type or callback dependency for an argument without effecting non-DI calls to the
function (by leaving these parameters required).

```py
async def callback(
    foo: alluka.Injected[Foo]
) -> None:
    ...
```

And [alluka.Injected][] provides a shorthand for using [typing.Annotated][] to declare a type
dependency.

!!! note
    [alluka.Injected][] can be safely passed to [typing.Annotated][] as the first type argument or
    vice versa thanks to how Annotated handles nesting.

### Calling functions with dependency injection

```py
client: alluka.Client

async def callback(
    argument: int,
    /,
    injected: alluka.Injected[Foo],
    keyword_arg: str,
) -> int:
    ...

...

result = await client.call_with_async_di(callback, 123, keyword_arg="ok")
```

To execute a function with async dependency injection [alluka.abc.Client.call_with_async_di][] should
be called with the function and any positional or keyword arguments to pass through alongside the
the injected arguments.

!!! note
    While both sync and async functions may be executed with `call_with_async_di`, you'll always have to
    await `call_with_async_di` to get the result of the call.

```py
client: alluka.Client

def callback(
    argument: int,
    /,
    injected: alluka.Injected[Foo],
    keyword_arg: str,
) -> int:
    ...

...

result = client.call_with_di(callback, 123, keyword_arg="ok")
```

To execute a function with purely sync dependency injection [alluka.abc.Client.call_with_di][] can be
used with similar semantics to `call_with_async_di` for passed through arguments but this comes with the
limitation that only sync functions may be used and any dependency on async callback dependencies
will lead to [alluka.AsyncOnlyError][] being raised.

```py
def foo(ctx: alluka.Inject[alluka.abc.Context]) -> None:
    result = ctx.call_with_di(other_callback, 542, keyword_arg="meow")

```

Alternatively, [alluka.abc.Context.call_with_di][] and [alluka.abc.Context.call_with_async_di][] can be used
to execute functions with dependency injection while preserving the current injection context.

```py
async def bar(ctx: alluka.Inject[alluka.abc.Context]) -> None:
    result = await ctx.call_with_async_di(other_callback, 123, keyword_arg="ok")
```

<!-- TODO: revisit behaviour for when an async function with no async deps is passed to call_with_di--->


## Using the client

<!-- TODO: add note about call chaining -->

### Adding type dependencies

```py
client = (
    alluka.Client()
    .set_type_dependency(TypeA, type_a_impl)
    .set_type_dependencu(TypeB, type_b_impl)
)
```

For a type dependency to work, the linked client will have to have an implementation loaded for it.
While right now the only way to load type dependencies is with the lower-level
[alluka.abc.Client.set_type_dependency][] method, more approaches and helpers will be added in the
future as Alluka is further developed.

### Overriding callback dependencies

```py
client = alluka.Client().set_callback_override(callback, other_callback)
```

While (unlike type dependencies) callback dependencies can work on their own without being
explicitly declared on the client unless they're relying on a type dependency themselves, they can
still be overridden on a client level using [alluka.abc.Client.set_callback_override][].

Generally speaking you should only ever override an injected callback with a callback which returns
a compatible type but their signatures do not need to match and async callbacks can be overridden
with sync with vice versa also working (although the latter will prevent callbacks from being
used in an async context).

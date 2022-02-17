# Usage

## Function injection

This form of dependency injection works by injecting values for keyword
arguments during callback execution based on the linked client.
This is the main dependency injection strategy implemented by Alluka.

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

Assigning the result of [alluka.inject][] to a function's parameter will declare it as
requiring an injected type or callback.

```py
async def callback(
    foo: Foo = alluka.inject()
) -> None:
    ...
```

If neither `type` nor `callback` is passed to [alluka.inject][] then a type dependency
will be inferred from the parameter's annotation.

!!! warning
    The type-hint will need to resolvable/accessible at runtime in the callback's module
    for it to be inferred (so it can't be hidden behind a [typing.TYPE_CHECKING][] only
    import or using a type or operation that isn't implemented in the current python
    version).

#### Type-hint metadata

[typing.Annotated][] style type-hint descriptors may be used to declare the injected
dependencies for a function.

```py
def callback(
    foo: typing.Annotated[Foo, alluka.inject(type=Foo)],
    bar: typing.Annotated[BarResult, alluka.inject(callback=bar_callback)]
) -> None:
    ...
```

Where passing the default descriptors returned by [alluka.inject][] to [typing.Annotated][]
lets you declare the type or callback dependency for an argument without effecting non-DI
calls to the function (by leaving these parameters required).

```py
async def callback(
    foo: alluka.Injected[Foo]
) -> None:
    ...
```

And [alluka.Injected][] provides a shorthand for using [typing.Annotated][] to declare
a type dependency.

!!! note
    [alluka.Injected][] can be safely passed to [typing.Annotated][] as the first type argument
    or vice versa thanks to how Annotated handles nesting.

### Calling functions with dependency injection

<!-- TODO: switch over to linking to alluka.Client once inherited members works -->
Either [alluka.abc.Client.execute][] or [alluka.abc.Client.execute_async][] may be called with a
function and any `*args` or `**kwargs` to call a function with dependency injection, where
[execute][alluka.abc.Client.execute] only enables synchronous execution and will fail if a
function is asynchronous or is relying on asynchronous dependencies.
<!-- TODO: revisit behaviour for when an async function with no async callbacks is passed to execute--->
Alternatively, [alluka.abc.Context.execute][] and [alluka.abc.Context.execute_async][] can be used
to execute functions with dependency injection while preserving the current injection context.

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
[alluka.Client.set_type_dependency][] method, more approaches and helpers will be added in the future
as Alluka is further developed.

### Overriding callback dependencies

```py
client = alluka.Client().set_callback_override(callback, other_callback)
```

While (unlike type dependencies) callback dependencies can work on their own without being explicitly
declared on the client unless they're relying on a type dependency themselves, they can still be
overridden on a client level using [alluka.Client.set_callback_override][].

Generally speaking you should only ever override an injected callback with a callback which returns
a compatible type but their signatures do not need to match and asynchronous callbacks can be
overridden with synchronous with vice versa also working (although the latter will prevent callbacks
from being  used in a synchronous context).
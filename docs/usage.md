# Usage

## Function injection

The main dependency injection strategy implemented by Alluka, for this dependencies
are injected during function calls as keyword arguments.

### Declaring a function's injected dependencies

There are two main styles for declaring a function's injected dependencies:

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
    The type-hint will need to resolvable/access at runtime in the callback's module
    (so it can't be hidden behind a [typing.TYPE_CHECKING][] only import or using a
    type or operation that isn't implemented in the current python version).

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

Where passing the default descriptors returned bu [alluka.inject][] to [typing.Annotated][]
as a type argument lets you declare the type or callback dependency for an argument without
effecting non-DI calls to the function (by leaving these parameters required).

```py
async def callback(
    foo: alluka.Injected[Foo] 
) -> None:
    ...
```

With [alluka.Injected][] providing a shorthand for using [typing.Annotated][] to declare
a type dependency.

!!! note
    [alluka.Injected][] can be safely passed to [typing.Annotated][] as the first type argument
    or vice versa.

### Calling functions with DI

<!-- TODO: switch over to linking to alluka.Client once inherited members works -->
Either [alluka.abc.Client.execute][] or [alluka.abc.Client.execute_async][] may be called with a
function and any `*args` and/or `**kwargs` to call a function with dependnecy injection, where
[execute][alluka.abc.Client.execute] only enables synchronous execution and will fail if a
function is asynchronous or is relying on asynchronous dependencies.
<!-- TODO: revisit behaviour for when an async function with no async callbacks is passed to execute--->
Alternatively, [alluka.abc.Context.execute][] and [alluka.abc.Context.execute_async][] can be used
to execute functions with DI while preserving the current injection context.

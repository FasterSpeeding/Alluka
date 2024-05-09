# Usage

## Function injection

This form of dependency injection works by injecting values for keyword arguments during callback
execution based on the linked client. This is the current form of dependency injection implemented by
Alluka.

### Declaring a function's injected dependencies

There are two styles for declaring a function's injected dependencies in Alluka:

#### Default descriptors

```py
--8<-- "./docs_src/usage.py:32:36"
```

Assigning the result of [alluka.inject][] to a parameter's default will declare it as requiring an
injected type or callback.

```py
--8<-- "./docs_src/usage.py:41:41"

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
--8<-- "./docs_src/usage.py:45:48"
```

Where passing the default descriptors returned by [alluka.inject][] to [typing.Annotated][] lets
you declare the type or callback dependency for an argument without effecting non-DI calls to the
function (by leaving these parameters required).

```py
--8<-- "./docs_src/usage.py:52:52"

```

And [alluka.Injected][] provides a shorthand for using [typing.Annotated][] to declare a type
dependency.

!!! note
    [alluka.Injected][] can be safely passed to [typing.Annotated][] as the first type argument or
    vice versa thanks to how Annotated handles nesting.

### Calling functions with dependency injection

```py
--8<-- "./docs_src/usage.py:57:69"

```

[Client.call_with_async_di][alluka.abc.Client.call_with_async_di] can be used to execute a
function with async dependency injection. Any positional or keyword arguments which are passed
with the function will be passed through to the function with the injected values.

!!! note
    While both sync and async functions may be executed with `call_with_async_di`, you'll always have to
    await `call_with_async_di` to get the result of the call.

```py
--8<-- "./docs_src/usage.py:75:87"
```

[Client.call_with_di][alluka.abc.Client.call_with_di] can be used to execute a function with
purely sync dependency injection. This has similar semantics to
`call_with_async_di` for passed through arguments but comes with the limitation that only sync
functions may be used and any async callback dependencies will lead to [alluka.SyncOnlyError][]
being raised.

```py
--8<-- "./docs_src/usage.py:95:96"
```

Alternatively, [Context.call_with_di][alluka.abc.Context.call_with_di] and
[Context.call_with_async_di][alluka.abc.Context.call_with_async_di] can be used to execute functions
with dependency injection while preserving the current injection context.

```py
--8<-- "./docs_src/usage.py:100:101"
```

<!-- TODO: revisit behaviour for when an async function with no async deps is passed to call_with_di--->

### Automatic dependency injection

```py
--8<-- "./docs_src/usage.py:164:169"
```

[Client.auto_inject][alluka.abc.Client.auto_inject_async] and
[Client.auto_inject_async][alluka.abc.Client.auto_inject_async] can be used to tie a callback to
a specific dependency injection client to enable implicit dependency injection without the need
to call `call_with_(async_)_di` every time the callback is called.

```py
--8<-- "./docs_src/usage.py:173:178"
```

[Client.auto_inject][alluka.abc.Client.auto_inject] comes with similar limitations to
[Client.call_with_di][alluka.abc.Client.call_with_di] in that the auto-injecting callback it
creates will fail if any of the callback dependencies are asynchronous.

## Using the client

<!-- TODO: add note about call chaining -->

### Adding type dependencies

```py
--8<-- "./docs_src/usage.py:114:118"
```

For a type dependency to work, the linked client has to have an implementation loaded for each type.
[Client.set_type_dependency][alluka.abc.Client.set_type_dependency] is used to pair up the types
you'll be using in [alluka.inject][] with initialised implementations of them.


### Overriding callback dependencies

```py
--8<-- "./docs_src/usage.py:126:126"
```

While callback dependencies can work on their own without being explicitly declared on the client
(unless they're relying on a type dependency themselves), they can still be overridden on a client
level using [Client.set_callback_override][alluka.abc.Client.set_callback_override].

Injected callbacks should only be overridden with a callback which returns a compatible type but
their signatures do not need to match and async callbacks can be overridden
with sync with vice versa also working (although overriding a sync callback with an async callback
will prevent the callback from being used in a sync context).

# Local client

Alluka provides a system in [alluka.local][] which lets you associate an Alluka client with the local
scope. This can make dependency injection easier for application code as it avoids the need to
lug around an injection client or context.

The local "scope" will either be the current thread, an async event loop (e.g. asyncio event loop),
an async task, or an async future.

While child async tasks and futures will inherit the local client, child threads will not.

```py
--8<-- "./docs_src/usage.py:144:150"
```

Either [alluka.local.initialize][] or [alluka.local.scope_client][] needs to be called to
declare a client within the current scope before the other functionality in [alluka.local][]
can be used. These can be passed a client to declare but default to creating a new client.

These clients are then configured like normal clients and [alluka.local.get][] can then be
used to get the set client for the current scope.

`scope_client` is recommended over `initialize` as it avoids declaring the client globally.

```py
--8<-- "./docs_src/usage.py:130:137"
```

[alluka.local.call_with_async_di][], [alluka.local.call_with_di][] can be used to call a
function with the dependency injection client that's set for the current scope.

```py
--8<-- "./docs_src/usage.py:154:160"
```

[alluka.local.auto_inject][], [alluka.local.auto_inject_async][] act a little different to
the similar client methods: instead of binding a callback to a specific client to
enable automatic dependency injection, these will get the local client when the
auto-injecting callback is called and use this for dependency injection.

As such `auto_inject` and `auto_inject_async` can be used to make an auto-injecting callback
before a local client has been set but any calls to the returned auto-injecting callbacks
will only work within a scope where `initialise` or `scope_client` is in effect.

# Custom injection contexts

Under the hood Alluka builds a [alluka.abc.Context][] for each call to a `call_with_{async}_di`
method.

```py
--8<-- "./docs_src/usage.py:182:182"
```

[alluka.Client.set_make_context][] can be used to change how the client creates DI contexts
to customise how dependency injection behaves.

### Caching injected callback results

By default, injected callbacks are called every time they're found within the context of a
dependency injection call.

[alluka.CachingContext][] can be set as the component maker to enable the caching of the
result of callback dependencies.

```py
--8<-- "./docs_src/usage.py:201:219"
```

This example will result in the following output where `state` is only injected once per
top-level call with `call_with_di`.

```py
>>> 1
>>> -
>>> 1
```

This caches the results in a DI context so if the same DI context is used to call multiple
callbacks with dependency injection then these cached values will be persisted between
those calls.

### Context-specific type dependencies

```py
--8<-- "./docs_src/usage.py:186:189"
```

[alluka.OverridingContext][] to add context specific type dependency overrides to an existing
DI context.

```py
--8<-- "./docs_src/usage.py:193:197"
```

[alluka.OverridingContext.from_client][] lets you create a context with type dependency
overrides straight from an Alluka client.

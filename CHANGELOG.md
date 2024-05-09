# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
## [0.3.0] - 2024-05-09
### Added
- [alluka.local][] is now directly exported on [alluka][].
- [alluka.Context][] implementation of [alluka.abc.Context][] which is a basic
  DI context implementation with no callback dependency result caching.
- [alluka.CachingContext][] which extends [alluka.Context][] to add callback
  dependency result caching.
- [alluka.OverridingContext][] shallow DI context implementation for adding
  context specific type dependencies to an existing context.
- [alluka.Client.set_make_context][] method for setting the callback used by
  the client to make DI contexts.

### Changed
- Callback dependency results are no-longer cached by default. To return this
  behaviour set [alluka.CachingContext][] as the context maker.

### Deprecated
- `alluka.BasicContext` has been replaced by [alluka.CachingContext][].

### Fixed
- Injected callback results are now properly cached when [alluka.CachingContext][]
  is set as the context.

## [0.2.0] - 2024-04-29
### Added
- Transparent auto injection methods on `Client` at `Client.auto_inject` and
  `Client.auto_inject_async`. These wrap functions to make calls to them
  automatically inject dependencies and are transparent replacements for the
  self injecting system.
  More information on these can be found
  [here](https://alluka.cursed.solutions/usage/#automatic-dependency-injection).
- A system for setting the injection client for a local scope (as defined by
  [contextvars][]) and making dependency injection calls based on said context.
  More information on this can be found
  [here](https://alluka.cursed.solutions/usage/#local-client).
- [alluka.abc.Client.make_context][] method for creating a client bound context.

### Changed
- `get_type_dependency` and `get_cached_value` both now raise a [KeyError][] when
  no value is found and no default was provided.
- [alluka.abc.Client.call_with_di][] and [alluka.abc.Client.call_with_async_di][]
  now provide default implementations which use
  [Client.make_context][alluka.abc.Client.make_context].
- [alluka.abc.Context.call_with_di][] and [alluka.abc.Context.call_with_async_di][]
  now provide default implementations which use
  [Context.injection_client][alluka.abc.Context.injection_client].

### Deprecated
- `Client.as_self_injecting` in favour of `Client.auto_inject`.
- `Client.as_async_self_injecting` in favour of `Client.auto_inject_async`.
- `alluka.SelfInjecting` in favour of `Client.auto_inject`.
- `alluka.AsyncSelfInjecting` in favour of `Client.auto_inject_async`.

### Removed
- `alluka.abc.UNDEFINED` and `alluka.abc.Undefined`.

## [0.1.5] - 2024-04-22
- Improve error message when attempting to use [alluka.inject][] without DI.

## [0.1.4] - 2023-12-27
### Added
- Python 3.12 support.

## [0.1.3] - 2022-11-12
### Added
- `alluka.abc.Client` is now set as a type dependency by default.

### Changed
- Renamed `AsyncOnlyError` to `SyncOnlyError` (`AsyncOnlyError` has been kept as a
  deprecated alias).
- Relaxed typing around DI for async callbacks to allow for returning a union of
  `Coroutine[Any, Any, T] | T`.

### Fixed
- Don't error on async callbacks which return a coroutine after being awaited
  during DI when assertions are enabled.

### Removed
- The project metadata dunder attributes from [alluka][].
  [importlib.metadata][] should be used to get this metadata instead.

## [0.1.2] - 2022-07-06
### Changed
- The optional `introspect_annotations` parameter for `alluka.Client.__init__`
  is now keyword only.
- `tanjun.abc.Client` is now a real `abc.ABC`.

### Deprecated
- `alluka.abc.Undefined` and `alluka.abc.UNDEFINED` for removal in `v0.2.0` as
   these will no-longer be used.
- `get_type_dependency` and `get_cached_result` returning `UNDEFINED` as the
  default when no default is passed will be replaced by a `KeyError` raise in
  `v0.2.0`.

## [0.1.1] - 2022-03-20
### Fixed
- Regression around handling of "signature-less" builtin functions.
  A ValueError will no longer be raised in these cases.

## [0.1.0] - 2022-02-25

All of the `0.1.0` entries are relative to the feature set exposed while this was a
part of Tanjun.

### Added
- Support for synchronous dependency injection (this comes with `SyncOnlyError`)
- Abstract interface for the client with limited functionality.
- `call_with_di` and `call_with_async_di` to `alluka.abc.Context` as a shorthand for
  executing a callback with that context.
- `call_with_di`, `call_with_async_di`, `call_with_ctx` and `call_with_ctx_async`
  methods to the injection client for executing callbacks with DI.
- Support for inferring the type of a parameter from its type hint
  when no `type` or `callback` is explicitly provided.
- Support for using `typing.Annotated` to declare parameter DI. This takes two forms:
    * `parameter: alluka.Inject[Type]` to infer specifically a type dependency.
    * `parameter: typing.Annotated(Type, alluka.inject(type=.../callback=...))`.

### Changed
- Passed keyword arguments are now prioritised over dependency injection.

### Removed
- The public `CallackDescriptor` and `TypeDescriptor` classes as callbacks
  are now processed within the client and any necessary caching is kept internal.

[Unreleased]: https://github.com/FasterSpeeding/Alluka/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/FasterSpeeding/Alluka/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/FasterSpeeding/Alluka/compare/v0.1.5...v0.2.0
[0.1.5]: https://github.com/FasterSpeeding/Alluka/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/FasterSpeeding/Alluka/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/FasterSpeeding/Alluka/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/FasterSpeeding/Alluka/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/FasterSpeeding/Alluka/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/FasterSpeeding/Alluka/compare/ed0567142b8e11f98408735495dbc4f771dc8643...v0.1.0

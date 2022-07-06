# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
## [0.1.2] - 2020-07-06
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

## [0.1.1] - 2020-03-20
### Fixed
- Regression around handling of "signature-less" builtin functions.
  A ValueError will no longer be raised in these cases.

## [0.1.0] - 2020-02-25

All of the `0.1.0` entries are relative to the feature set exposed while this was a
part of Tanjun.

### Added
- Support for synchronous dependency injection (this comes with `AsyncOnlyError`)
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

[Unreleased]: https://github.com/FasterSpeeding/Alluka/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/FasterSpeeding/Alluka/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/FasterSpeeding/Alluka/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/FasterSpeeding/Alluka/compare/ed0567142b8e11f98408735495dbc4f771dc8643...v0.1.0

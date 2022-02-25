# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/FasterSpeeding/Alluka/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/FasterSpeeding/Alluka/compare/ed0567142b8e11f98408735495dbc4f771dc8643...v0.1.0

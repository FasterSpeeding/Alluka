# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

All the `0.1.0` entries are relative to the feature set exposed while this was a
part of Tanjun.

### Added
- Support for synchronous dependency injection (this comes with `AsyncOnlyError`)
- Abstract interface for the client with limited functionality.
- `execute`, `execute_async` To the `alluka.abc.Context` as a shorthand for
  executing a callback with that context.
- `execute`, `execute_async`, `execute_with_ctx` and `execute_with_ctx_async`
  methods to the injection client for executing callbacks with DI.
- Support for inferring the type of a parameter from its type hint
  when no `type` or `callback` is explicitly provided.
- Support for using `typing.Annotated` to declare parameter DI. This takes two forms:
  * `parameter: alluka.Inject[Type]` to infer specifically a type dependency.
  * `parameter: typing.Annotated(Type, alluka.inject(type=.../callback=...))`.

### Removed
- The public `CallackDescriptor` and `TypeDescriptor` classes as callbacks
  are now processed within the client and any necessary caching is kept internal.

[Unreleased]: https://github.com/FasterSpeeding/Tanjun/compare/v2.4.0a1...HEAD
[0.1.0]: https://github.com/FasterSpeeding/Tanjun/compare/v0.1.0...HEAD

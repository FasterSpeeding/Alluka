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
# * Neither the name of the copyright holder nor the names of it s
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
"""Logic for handling loading and configuring dependencies."""
from __future__ import annotations

import copy
import importlib
import importlib.metadata
import logging
import sys
import typing
from collections import abc as collections

if typing.TYPE_CHECKING:
    from typing_extensions import Self


_LOGGER = logging.getLogger("alluka")
_T = typing.TypeVar("_T")


class Package:
    __slots__ = ("config_format", "library_path", "loaders", "type_defaults")

    def __init__(self, library_path: str, /) -> None:
        self.config_format: typing.Optional[typing.Any] = None
        self.library_path = library_path
        self.loaders: list[collections.Callable[..., None]] = []
        self.type_defaults: dict[type[typing.Any], collections.Callable[..., typing.Any]] = {}

    def add_loaders(self, *loaders: collections.Callable[..., None]) -> Self:
        self.loaders.extend(loaders)
        return self

    def add_type_default(self, type_: type[_T], default_callback: collections.Callable[..., _T]) -> Self:
        self.type_defaults[type_] = default_callback
        return self

    def set_config_format(self, config_format: typing.Any, /) -> Self:
        self.config_format = config_format
        return self


class PackageHandler:
    __slots__ = ("packages",)

    def __init__(self) -> None:
        self.packages: dict[str, Package] = {}

    def register_package(self, library_path: str, /) -> Package:
        package = self.packages[library_path] = Package(library_path)
        return package

    def copy(self) -> Self:
        result = copy.copy(self)
        result.packages = self.packages.copy()
        return result


def _process_entry_point(entry_point: importlib.metadata.EntryPoint, handler: PackageHandler, /) -> None:
    try:
        path, name = entry_point.value.split(":", 1)
    except ValueError:
        name = path = None

    if not name or not path:
        raise ValueError(f"{entry_point.value} is not a valid callback path")

    value = importlib.import_module(path)
    for node in filter(None, name.split(".")):
        value = getattr(value, node)

    if not callable(value):
        raise TypeError("Dependency loader must point at a callback")

    value(handler)


def load_plugins(name: str, /, *, logger: logging.Logger = _LOGGER) -> PackageHandler:
    if sys.version_info >= (3, 10):
        entry_points = importlib.metadata.entry_points(group=name, name="load_plugin")

    else:
        entry_points = (
            entry for entry in importlib.metadata.entry_points().get(name) or () if entry.name == "load_plugin"
        )

    if name == "alluka":
        handler = PackageHandler()

    else:
        handler = _ALLUKA_HANDLER.copy()

    for entry in entry_points:
        try:
            _process_entry_point(entry, handler)

        except Exception as exc:
            logger.exception("Failed to broken %r plugin metadata from %r", name, entry.value, exc_info=exc)

    return handler


_ALLUKA_HANDLER = load_plugins("alluka")

# -*- coding: utf-8 -*-
# BSD 3-Clause License
#
# Copyright (c) 2020-2024, Faster Speeding
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
# * Neither the name of the copyright holder nor the names of its
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
"""Utility class for loading type dependencies based on configuration."""

from __future__ import annotations

__all__: list[str] = ["ConfigFile", "Manager", "PluginConfig", "TypeConfig"]

import typing

from . import _index
from ._config import ConfigFile as ConfigFile
from ._config import PluginConfig as PluginConfig  # noqa: TC002
from ._config import TypeConfig as TypeConfig  # noqa: TC002
from ._manager import Manager as Manager

if typing.TYPE_CHECKING:
    from collections import abc as collections


_GLOBAL_INDEX = _index.GLOBAL_INDEX

register_config: collections.Callable[[type[PluginConfig]], None] = _GLOBAL_INDEX.register_config
"""Register a plugin configuration class.

!!! warning
    Libraries should register custom configuration classes using package
    entry-points tagged with the `"alluka.managed"` group.

Parameters
----------
config_cls : type[PluginConfig]
    The plugin configuration class to register.

Raises
------
RuntimeError
    If the configuration class' ID is already registered.
"""

register_type: collections.Callable[[TypeConfig[typing.Any]], None] = _GLOBAL_INDEX.register_type
"""Register the procedures for creating and destroying a type dependency.

!!! warning
    Libraries should register custom type procedure objects using package
    entry-points tagged with the `"alluka.managed"` group.

Parameters
----------
type_info : yuyo.managed.TypeConfig[typing.Any]
    The type dependency's runtime procedures.
"""

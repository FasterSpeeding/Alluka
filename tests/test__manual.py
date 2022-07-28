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

import typing
from unittest import mock

import pytest

import alluka


class TestManuallyInjected:
    def test___call__(self):
        mock_callback = mock.Mock()
        injected = alluka.ManuallyInjected(mock_callback)

        result = injected(123, "meow", "nom", big="float", small=True)

        assert result is mock_callback.return_value
        mock_callback.assert_called_once_with(123, "meow", "nom", big="float", small=True)

    def test_set_callback_when_name_not_found(self):
        def callback(*args: int, cat: str) -> None:
            return None

        injected = alluka.ManuallyInjected(callback)

        with pytest.raises(ValueError, match=f"dog is not a valid keyword argument for {callback}"):
            injected.set_type("dog", complex)

    def test_set_callback_when_name_present(self):
        def callback(args: str, blargs: bool) -> None:
            return None

        injected = alluka.ManuallyInjected(callback)

        injected.set_type("args", str).set_type("blargs", bool)

    def test_set_callback_when_name_present_as_keyword_only(self):
        def callback(*, no: str) -> None:
            return None

        injected = alluka.ManuallyInjected(callback)

        injected.set_callback("no", mock.Mock())

    def test_set_callback_when_name_present_as_positional_only(self):
        def callback(me: float, /) -> None:
            return None

        injected = alluka.ManuallyInjected(callback)

        with pytest.raises(ValueError, match=f"me is not a valid keyword argument for {callback}"):
            injected.set_callback("me", mock.Mock())

    def test_set_callback_when_kwargs(self):
        def callback(**kwargs: typing.Any) -> None:
            return None

        injected = alluka.ManuallyInjected(callback)

        injected.set_callback("meow", mock.Mock())

    def test_set_type_when_name_not_found(self):
        def callback(*args: int, bleep: str) -> None:
            return None

        injected = alluka.ManuallyInjected(callback)

        with pytest.raises(ValueError, match=f"bloop is not a valid keyword argument for {callback}"):
            injected.set_type("bloop", float)

    def test_set_type_when_name_present(self):
        def callback(arg: int, other_arg: str) -> None:
            return None

        injected = alluka.ManuallyInjected(callback)

        injected.set_type("arg", int).set_type("other_arg", str)

    def test_set_type_when_name_present_as_keyword_only(self):
        def callback(*, nom: str) -> None:
            return None

        injected = alluka.ManuallyInjected(callback)

        injected.set_type("nom", bool)

    def test_set_type_when_name_present_as_positional_only(self):
        def callback(meep: float, /) -> None:
            return None

        injected = alluka.ManuallyInjected(callback)

        with pytest.raises(ValueError, match=f"meep is not a valid keyword argument for {callback}"):
            injected.set_type("meep", float)

    def test_set_type_when_kwargs(self):
        def callback(**kwargs: typing.Any) -> None:
            return None

        injected = alluka.ManuallyInjected(callback)

        injected.set_type("meow", int)

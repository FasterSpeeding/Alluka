// BSD 3-Clause License
//
// Copyright (c) 2022, Lucina
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//
// * Redistributions of source code must retain the above copyright notice, this
//   list of conditions and the following disclaimer.
//
// * Redistributions in binary form must reproduce the above copyright notice,
//   this list of conditions and the following disclaimer in the documentation
//   and/or other materials provided with the distribution.
//
// * Neither the name of the copyright holder nor the names of its contributors
//   may be used to endorse or promote products derived from this software
//   without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
// ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
// LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
// CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
// SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
// INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
// CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
// ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
// POSSIBILITY OF SUCH DAMAGE.
#![allow(clippy::borrow_deref_ref)] // Leads to a ton of false positives around args of py types.
#![feature(arbitrary_self_types)]
#![feature(hash_raw_entry)]
#![feature(once_cell)]
use client::{BasicContext, Client};
use pyo3::types::{PyModule, PyType};
use pyo3::{PyResult, Python};

mod anyio;
mod client;
mod types;
mod visitor;


#[pyo3::pymodule]
fn _alluka(py: Python, module: &PyModule) -> PyResult<()> {
    let abc = py.import("alluka")?.getattr("abc")?;

    module.add("__version__", "0.1.1")?;
    module.add_class::<Client>()?;
    module.add_class::<BasicContext>()?;

    abc.getattr("Client")?
        .call_method1("register", (PyType::new::<Client>(py),))?;

    abc.getattr("Context")?
        .call_method1("register", (PyType::new::<BasicContext>(py),))?;

    Ok(())
}

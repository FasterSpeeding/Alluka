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
use std::sync::Arc;

use pyo3::types::PyTuple;
use pyo3::{Py, PyAny, PyObject, PyResult, Python, PyErr};

use crate::{BasicContext, Client};

pyo3::import_exception!(alluka._errors, MissingDependencyError);

pub struct InjectedCallback {
    callback: Arc<PyObject>,
}

impl InjectedCallback {
    fn resolve(
        &self,
        py: Python,
        client: &mut Client,
        ctx: Py<BasicContext>,
        callback: PyObject,
    ) -> PyResult<PyObject> {
        let callback = client
            .get_callback_override(py, callback.as_ref(py))?
            .unwrap_or(callback);
        client.call_with_ctx(py, ctx, callback, PyTuple::empty(py), None)
    }

    fn resolve_async(
        &self,
        py: Python,
        client: &mut Client,
        ctx: Py<BasicContext>,
        callback: PyObject,
    ) -> PyResult<PyObject> {
        let callback = client
            .get_callback_override(py, callback.as_ref(py))?
            .unwrap_or(callback);
        client.call_with_ctx_async(py, ctx, callback, PyTuple::empty(py), None)
    }
}


pub struct InjectedType {
    default: Option<PyObject>,
    repr_type: String,
    types: Vec<isize>,
}

impl InjectedType {
    fn resolve<'a>(&'a self, client: &'a Client) -> PyResult<&'a PyObject> {
        if let Some(value) = self
            .types
            .iter()
            .filter_map(|cls| client.get_type_dependency_rust(cls))
            .next()
        {
            return Ok(value);
        }

        if let Some(default) = self.default.as_ref() {
            return Ok(default);
        }

        Err(PyErr::new::<MissingDependencyError, _>(format!(
            "Couldn't resolve injected type(s) {} to actual value",
            self.repr_type
        )))
    }
}


pub enum Injected {
    Callback(InjectedCallback),
    Type(InjectedType),
}

impl Injected {
    pub fn new_callback(callback: PyObject) -> Self {
        Injected::Callback(InjectedCallback {
            callback: Arc::new(callback),
        })
    }

    pub fn new_type(
        py: Python,
        default: Option<PyObject>,
        repr_type: PyObject,
        types: Vec<PyObject>,
    ) -> PyResult<Self> {
        Ok(Injected::Type(InjectedType {
            default,
            repr_type: repr_type.as_ref(py).repr()?.to_string(),
            types: types
                .iter()
                .map(|type_| type_.as_ref(py).hash())
                .collect::<PyResult<Vec<isize>>>()?,
        }))
    }
}

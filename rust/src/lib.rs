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
#![feature(hash_raw_entry)]
#![feature(once_cell)]
use std::borrow::BorrowMut;
use std::collections::hash_map::RawEntryMut;
use std::collections::HashMap;
use std::convert::AsRef;
use std::lazy::Lazy;

use pyo3::exceptions::PyKeyError;
use pyo3::pycell::PyRef;
use pyo3::types::{PyDict, PyModule, PyTuple, PyType};
use pyo3::{IntoPy, Py, PyAny, PyObject, PyRefMut, PyResult, Python, ToPyObject};

use crate::visitor::{Callback, ParameterVisitor};

mod types;
use types::{Injected, InjectedCallback, InjectedType};
mod visitor;

const SELF_INJECTING: Lazy<Py<PyModule>> =
    Lazy::new(|| Python::with_gil(|py| py.import("alluka._self_injecting").unwrap().into_py(py)));

#[pyo3::pyclass(subclass)]
struct Client {
    callback_overrides: HashMap<isize, PyObject>,
    descriptors: HashMap<isize, Vec<(String, Injected)>>,
    introspect_annotations: bool,
    type_dependencies: HashMap<isize, PyObject>,
}

impl Client {
    fn build_descriptors<'a>(&'a mut self, py: Python, callback: PyObject) -> PyResult<&'a [(String, Injected)]> {
        let key = callback.as_ref(py).hash()?;
        let entry = self.descriptors.raw_entry_mut().from_key(&key);

        Ok(match entry {
            RawEntryMut::Occupied(entry) => entry.into_key_value().1,
            RawEntryMut::Vacant(entry) => {
                entry
                    .insert(key, Callback::new(py, callback)?.accept::<ParameterVisitor>()?)
                    .1
            }
        })
    }

    pub fn get_type_dependency_rust<'a>(&'a self, type_: &isize) -> Option<&'a PyObject> {
        self.type_dependencies.get(type_)
    }
}

#[pyo3::pymethods]
impl Client {
    #[new]
    #[args("*", introspect_annotations = "true")]
    fn new(introspect_annotations: bool) -> Self {
        Self {
            callback_overrides: HashMap::new(),
            descriptors: HashMap::new(),
            introspect_annotations,
            type_dependencies: HashMap::new(),
        }
    }

    #[args(callback, "/")]
    fn as_async_self_injecting(slf: PyRef<Self>, py: Python, callback: &PyAny) -> PyResult<PyObject> {
        SELF_INJECTING
            .getattr(py, "AsyncSelfInjecting")?
            .call1(py, (slf, callback))
    }

    #[args(callback, "/")]
    fn as_self_injecting(slf: PyRef<Self>, py: Python, callback: &PyAny) -> PyResult<PyObject> {
        SELF_INJECTING.getattr(py, "SelfInjecting")?.call1(py, (slf, callback))
    }

    #[args(callback, "/", args = "*", kwargs = "**")]
    fn call_with_di<'p>(
        slf: Py<Self>,
        py: Python<'p>,
        callback: PyObject,
        args: &PyTuple,
        kwargs: Option<&PyDict>,
    ) -> PyResult<PyObject> {
        // TODO: does this work or do we need to slf.clone_ref(py).borrow(py)
        slf.clone_ref(py)
            .borrow_mut(py)
            .call_with_ctx(py, Py::new(py, BasicContext::new(slf))?, callback, args, kwargs)
    }

    #[args(ctx, callback, "/", args = "*", kwargs = "**")]
    pub fn call_with_ctx<'p>(
        &mut self,
        py: Python<'p>,
        ctx: Py<BasicContext>,
        callback: PyObject,
        args: &PyTuple,
        mut kwargs: Option<&'p PyDict>,
    ) -> PyResult<PyObject> {
        let descriptors = self.build_descriptors(py, callback.clone_ref(py))?;

        if !descriptors.is_empty() {
            kwargs = Some(kwargs.map_or_else(
                || {
                    descriptors.iter().map(|(key, value)| (key, value));
                    PyDict::new(py)
                },
                |dict| dict,
            ))
        }

        callback.call(py, args, kwargs)
    }

    #[args(callback, "/", args = "*", kwargs = "**")]
    fn call_with_async_di<'p>(
        slf: Py<Self>,
        py: Python<'p>,
        callback: PyObject,
        args: &PyTuple,
        kwargs: Option<&PyDict>,
    ) -> PyResult<PyObject> {
        slf.clone_ref(py).borrow(py).call_with_ctx_async(
            py,
            Py::new(py, BasicContext::new(slf))?,
            callback,
            args,
            kwargs,
        )
    }

    #[args(ctx, callback, "/", args = "*", kwargs = "**")]
    pub fn call_with_ctx_async<'p>(
        &self,
        py: Python<'p>,
        ctx: Py<BasicContext>,
        callback: PyObject,
        args: &PyTuple,
        kwargs: Option<&PyDict>,
    ) -> PyResult<PyObject> {
        unimplemented!()
    }

    #[args(type_, value, "/")]
    fn set_type_dependency<'p>(
        mut slf: PyRefMut<'p, Self>,
        py: Python<'p>,
        type_: &PyAny,
        value: PyObject,
    ) -> PyResult<PyRefMut<'p, Self>> {
        slf.borrow_mut().type_dependencies.insert(type_.hash()?, value);
        Ok(slf)
    }

    #[args(type_, "/", "*", default)]
    pub fn get_type_dependency(&self, py: Python, type_: &PyAny, default: Option<PyObject>) -> PyResult<PyObject> {
        Ok(self
            .type_dependencies
            .get(&type_.hash()?)
            .map(|value| value.clone_ref(py))
            .unwrap_or_else(|| default.unwrap_or_else(|| py.None())))
    }

    #[args(type_, "/")]
    fn remove_type_dependency<'p>(
        mut slf: PyRefMut<'p, Self>,
        py: Python,
        type_: &PyAny,
    ) -> PyResult<PyRefMut<'p, Self>> {
        if slf.borrow_mut().type_dependencies.remove(&type_.hash()?).is_some() {
            Err(PyKeyError::new_err(format!("Type dependency not found: {}", type_)))
        } else {
            Ok(slf)
        }
    }

    #[args(callback, override_, "/")]
    fn set_callback_override<'p>(
        mut slf: PyRefMut<'p, Self>,
        py: Python<'p>,
        callback: &PyAny,
        override_: PyObject,
    ) -> PyResult<PyRefMut<'p, Self>> {
        slf.borrow_mut().callback_overrides.insert(callback.hash()?, override_);
        Ok(slf)
    }

    #[args(callback, "/")]
    fn get_callback_override(&self, py: Python, callback: &PyAny) -> PyResult<Option<PyObject>> {
        Ok(self
            .callback_overrides
            .get(&callback.hash()?)
            .map(|value| ToPyObject::to_object(value, py)))
    }

    #[args(callback, "/")]
    fn remove_callback_override<'p>(
        mut slf: PyRefMut<'p, Self>,
        py: Python,
        callback: &PyAny,
    ) -> PyResult<PyRefMut<'p, Self>> {
        if slf.borrow_mut().callback_overrides.remove(&callback.hash()?).is_some() {
            Err(PyKeyError::new_err(format!(
                "Callback override not found: {}",
                callback
            )))
        } else {
            Ok(slf)
        }
    }
}

#[pyo3::pyclass(subclass)]
pub struct BasicContext {
    client: Py<Client>,
    result_cache: HashMap<isize, PyObject>,
    special_cased_types: HashMap<isize, PyObject>,
}

impl BasicContext {
    pub fn get_type_dependency_rust<'a>(&'a self, type_: &isize) -> Option<&'a PyObject> {
        self
            .special_cased_types
            .get(type_)
    }
}

#[pyo3::pymethods]
impl BasicContext {
    #[new]
    #[args(client, "/")]
    fn new(client: Py<Client>) -> Self {
        Self {
            client,
            result_cache: HashMap::with_capacity(0),
            special_cased_types: HashMap::with_capacity(0),
        }
    }

    #[getter]
    fn get_injection_client(&self, py: Python) -> Py<Client> {
        self.client.clone_ref(py)
    }

    #[args(callback, value, "/")]
    fn cache_result(&mut self, callback: &PyAny, value: PyObject) -> PyResult<()> {
        self.result_cache.insert(callback.hash()?, value);
        Ok(())
    }

    #[args(callback, "/", args = "*", kwargs = "**")]
    fn call_with_di<'p>(
        slf: Py<Self>,
        py: Python<'p>,
        callback: PyObject,
        args: &PyTuple,
        kwargs: Option<&PyDict>,
    ) -> PyResult<PyObject> {
        slf.clone_ref(py)
            .borrow(py)
            .client
            .borrow_mut(py)
            .call_with_ctx(py, slf, callback, args, kwargs)
    }

    #[args(callback, "/", args = "*", kwargs = "**")]
    fn call_with_async_di<'p>(
        slf: Py<Self>,
        py: Python<'p>,
        callback: PyObject,
        args: &PyTuple,
        kwargs: Option<&PyDict>,
    ) -> PyResult<PyObject> {
        slf.clone_ref(py)
            .borrow(py)
            .client
            .borrow(py)
            .call_with_ctx_async(py, slf, callback, args, kwargs)
    }

    #[args(callback, "/", "*", default)]
    fn get_cached_result(&self, py: Python, callback: &PyAny, default: Option<PyObject>) -> PyResult<PyObject> {
        Ok(self
            .result_cache
            .get(&callback.hash()?)
            .map(|value| value.clone_ref(py))
            .unwrap_or_else(|| default.unwrap_or_else(|| py.None())))
    }

    #[args(type_, "/", "*", default)]
    fn get_type_dependency(&self, py: Python, type_: &PyAny, default: Option<PyObject>) -> PyResult<PyObject> {
        if let Some(result) = self.special_cased_types.get(&type_.hash()?) {
            return Ok(result.clone_ref(py));
        }

        self.client.borrow(py).get_type_dependency(py, type_, default)
    }
}


#[pyo3::pymodule]
fn _alluka(py: Python, module: &PyModule) -> PyResult<()> {
    let abc = py.import("alluka")?.getattr("abc")?;

    module.add("__version__", "0.1.1")?;
    module.add_class::<Client>()?;

    abc.getattr("Client")?
        .call_method1("register", (PyType::new::<Client>(py),))?;

    abc.getattr("Context")?
        .call_method1("register", (PyType::new::<BasicContext>(py),))?;

    Ok(())
}

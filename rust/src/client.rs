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
use std::borrow::BorrowMut;
use std::collections::hash_map::RawEntryMut;
use std::collections::HashMap;
use std::convert::AsRef;
use std::future::Future;
use std::pin::Pin;
use std::sync::{Arc, OnceLock, RwLock};

use pyo3::exceptions::PyKeyError;
use pyo3::pycell::PyRef;
use pyo3::types::{IntoPyDict, PyDict, PyTuple};
use pyo3::{IntoPy, Py, PyAny, PyErr, PyObject, PyRefMut, PyResult, Python, ToPyObject};

use crate::anyio::{future_into_py, into_future};
use crate::types::{Injected, InjectedTuple};
use crate::visitor::{Callback, ParameterVisitor};


pyo3::import_exception!(alluka._errors, AsyncOnlyError);

static ALLUKA: OnceLock<PyObject> = OnceLock::new();
static ASYNCIO: OnceLock<PyObject> = OnceLock::new();
static SELF_INJECTING: OnceLock<PyObject> = OnceLock::new();

fn import_alluka(py: Python) -> PyResult<&PyAny> {
    ALLUKA
        .get_or_try_init(|| Ok(py.import("alluka")?.to_object(py)))
        .map(|value| value.as_ref(py))
}

fn import_asyncio(py: Python) -> PyResult<&PyAny> {
    ASYNCIO
        .get_or_try_init(|| Ok(py.import("asyncio")?.to_object(py)))
        .map(|value| value.as_ref(py))
}

fn import_self_injecting(py: Python) -> PyResult<&PyAny> {
    SELF_INJECTING
        .get_or_try_init(|| Ok(py.import("alluka._self_injecting")?.to_object(py)))
        .map(|value| value.as_ref(py))
}

#[pyo3::pyclass(subclass)]
pub struct Client {
    callback_overrides: HashMap<isize, PyObject>,
    descriptors: RwLock<HashMap<isize, Arc<Box<[InjectedTuple]>>>>,
    introspect_annotations: bool,
    type_dependencies: HashMap<isize, PyObject>,
}

type BoxedFuture<T> = Pin<Box<dyn Future<Output = T> + Send + 'static>>;

enum MaybeAsync {
    Receiver(BoxedFuture<PyResult<PyObject>>),
    Result(PyObject),
}

impl MaybeAsync {
    fn from_result(py: Python, value: &PyAny) -> PyResult<Self> {
        if import_asyncio(py)?.call_method1("iscoroutine", (value,))?.is_true()? {
            Ok(MaybeAsync::Receiver(Box::pin(into_future(py, value)?)))
        } else {
            Ok::<_, PyErr>(MaybeAsync::Result(value.to_object(py)))
        }
    }
}

enum OrEarlyReturn {
    Iterator(Vec<(String, BoxedFuture<PyResult<PyObject>>)>),
    EarlyReturn(MaybeAsync),
}

impl OrEarlyReturn {
    fn early_return(py: Python, callback: &PyAny, args: &PyTuple, kwargs: Option<&PyDict>) -> PyResult<Self> {
        Ok(OrEarlyReturn::EarlyReturn(MaybeAsync::from_result(
            py,
            callback.call(args, kwargs)?,
        )?))
    }
}


impl Client {
    fn build_descriptors(&self, py: Python, callback: &PyAny) -> PyResult<Arc<Box<[InjectedTuple]>>> {
        let key = callback.hash()?;
        // Avoid a write lock if we already have the descriptors.
        if let Some(descriptors) = self.descriptors.read().unwrap().get(&key).map(Arc::clone) {
            return Ok(descriptors);
        }

        let mut descriptors = self.descriptors.write().unwrap();
        let entry = descriptors.raw_entry_mut().from_key(&key);
        Ok(match entry {
            RawEntryMut::Occupied(entry) => entry.into_key_value().1.clone(),
            RawEntryMut::Vacant(entry) => entry
                .insert(
                    key,
                    Arc::new(Box::from(Callback::new(py, callback)?.accept::<ParameterVisitor>(py)?)),
                )
                .1
                .clone(),
        })
    }

    pub fn get_type_dependency_rust<'a>(&'a self, type_: &isize) -> Option<&'a PyObject> {
        self.type_dependencies.get(type_)
    }

    pub fn call_with_ctx_rust<'p>(
        self: &PyRef<'p, Self>,
        py: Python<'p>,
        ctx: &PyRef<'p, BasicContext>,
        callback: &'p PyAny,
        args: &PyTuple,
        mut kwargs: Option<&'p PyDict>,
    ) -> PyResult<&'p PyAny> {
        let descriptors = self.build_descriptors(py, callback)?;

        if !descriptors.is_empty() {
            let descriptors = descriptors.iter().map(|(key, value)| match value {
                Injected::Type(type_) => type_.resolve_rust(py, self, ctx).map(|value| (key, value)),
                Injected::Callback(callback) => callback.resolve_rust(py, self, ctx).map(|value| (key, value)),
            });
            if let Some(dict) = kwargs {
                for entry in descriptors {
                    let (key, value) = entry?;
                    dict.set_item(key, value)?;
                }
            } else {
                kwargs = descriptors
                    .collect::<PyResult<Vec<(&String, &PyAny)>>>()
                    .map(|value| Some(value.into_py_dict(py)))?
            }
        }

        let result = callback.call(args, kwargs)?;
        if import_asyncio(py)?.call_method1("iscoroutine", (result,))?.is_true()? {
            Err(AsyncOnlyError::new_err(()))
        } else {
            Ok(result)
        }
    }

    pub async fn call_with_ctx_async_rust(
        slf: Py<Self>,
        ctx: Py<BasicContext>,
        callback: PyObject,
        args: Py<PyTuple>,
        mut kwargs: Option<Py<PyDict>>,
    ) -> PyResult<PyObject> {
        let result = Python::with_gil(|py| {
            let slf_borrow = slf.borrow(py);
            let descriptors = slf_borrow.build_descriptors(py, callback.as_ref(py))?;
            if descriptors.is_empty() {
                if let Some(kwargs) = kwargs.as_ref() {
                    return OrEarlyReturn::early_return(
                        py,
                        callback.as_ref(py),
                        args.as_ref(py),
                        Some(kwargs.as_ref(py)),
                    );
                }
                return OrEarlyReturn::early_return(py, callback.as_ref(py), args.as_ref(py), None);
            }

            let ctx_borrow = ctx.borrow(py);
            let kwargs = kwargs.get_or_insert_with(|| PyDict::new(py).into_py(py)).as_ref(py);

            let descriptors = descriptors
                .iter()
                .map(|(key, value)| match value {
                    Injected::Type(type_) => {
                        let value = type_.resolve_rust(py, &slf_borrow, &ctx_borrow)?;
                        kwargs.set_item(key, value)?;
                        Ok(None)
                    }
                    Injected::Callback(callback) => Ok(Some((
                        key.to_owned(),
                        callback.resolve_rust_async(py, slf.clone_ref(py), ctx.clone_ref(py))?,
                    ))),
                })
                .filter_map(Result::transpose)
                .collect::<PyResult<Vec<_>>>()?;

            if descriptors.is_empty() {
                return OrEarlyReturn::early_return(py, callback.as_ref(py), args.as_ref(py), Some(kwargs));
            }

            Ok(OrEarlyReturn::Iterator(descriptors))
        })?;

        let iter = match result {
            OrEarlyReturn::EarlyReturn(MaybeAsync::Receiver(receiver)) => return receiver.await,
            OrEarlyReturn::EarlyReturn(MaybeAsync::Result(value)) => return Ok(value),
            OrEarlyReturn::Iterator(iter) => iter,
        };

        let mut more_kwargs = Vec::<(String, PyObject)>::with_capacity(iter.len());
        for result in iter {
            let (name, fut) = result;
            more_kwargs.push((name, fut.await?));
        }

        let result = Python::with_gil(|py| {
            // At this point kwargs is guaranteed to exist and this makes
            // handling the lifetimes of kwargs.as_ref(py) easier.
            let kwargs = kwargs.as_ref().unwrap();
            let kwargs_ref = kwargs.as_ref(py);
            for (name, value) in more_kwargs {
                kwargs_ref.set_item(name, value)?;
            }

            MaybeAsync::from_result(py, callback.call(py, args.as_ref(py), Some(kwargs_ref))?.as_ref(py))
        })?;


        match result {
            MaybeAsync::Receiver(receiver) => receiver.await,
            MaybeAsync::Result(result) => Ok(result),
        }
    }
}

#[pyo3::pymethods]
impl Client {
    #[new]
    #[args("*", introspect_annotations = "true")]
    fn new(introspect_annotations: bool) -> PyResult<Self> {
        Ok(Self {
            callback_overrides: HashMap::new(),
            descriptors: RwLock::new(HashMap::new()),
            introspect_annotations,
            type_dependencies: HashMap::new(),
        })
    }

    #[args(callback, "/")]
    fn as_async_self_injecting<'p>(self: PyRef<Self>, py: Python<'p>, callback: &PyAny) -> PyResult<&'p PyAny> {
        import_self_injecting(py)?.call_method1("AsyncSelfInjecting", (self, callback))
    }

    #[args(callback, "/")]
    fn as_self_injecting<'p>(self: PyRef<Self>, py: Python<'p>, callback: &PyAny) -> PyResult<&'p PyAny> {
        import_self_injecting(py)?.call_method1("SelfInjecting", (self, callback))
    }

    #[args(callback, "/", args = "*", kwargs = "**")]
    fn call_with_di(
        slf: Py<Self>,
        py: Python,
        callback: &PyAny,
        args: &PyTuple,
        kwargs: Option<&PyDict>,
    ) -> PyResult<PyObject> {
        Py::new(py, BasicContext::new(slf))?
            .borrow(py)
            .call_with_di(py, callback, args, kwargs)
            .map(|value| value.to_object(py))
    }

    #[args(ctx, callback, "/", args = "*", kwargs = "**")]
    pub fn call_with_ctx(
        _self: Py<Self>,
        _py: Python,
        _ctx: &PyAny,
        _callback: &PyAny,
        _args: &PyTuple,
        _kwargs: Option<&PyDict>,
    ) -> PyResult<PyObject> {
        unimplemented!("Custom contexts are not supported yet")
    }

    #[args(callback, "/", args = "*", kwargs = "**")]
    fn call_with_async_di(
        slf: Py<Self>,
        py: Python<'_>,
        callback: PyObject,
        args: Py<PyTuple>,
        kwargs: Option<Py<PyDict>>,
    ) -> PyResult<&PyAny> {
        BasicContext::call_with_async_di(Py::new(py, BasicContext::new(slf))?, py, callback, args, kwargs)
    }

    #[args(ctx, callback, "/", args = "*", kwargs = "**")]
    pub fn call_with_ctx_async(
        _self: PyRef<'_, Self>,
        _py: Python,
        _ctx: &PyAny,
        _callback: &PyAny,
        _args: &PyTuple,
        _kwargs: Option<&PyDict>,
    ) -> PyResult<PyObject> {
        unimplemented!("Custom contexts are not supported yet")
    }

    #[args(type_, value, "/")]
    fn set_type_dependency<'p>(
        mut self: PyRefMut<'p, Self>,
        type_: &PyAny,
        value: PyObject,
    ) -> PyResult<PyRefMut<'p, Self>> {
        self.borrow_mut().type_dependencies.insert(type_.hash()?, value);
        Ok(self)
    }

    #[args(type_, "/", "*", default)]
    pub fn get_type_dependency(&self, py: Python, type_: &PyAny, default: Option<PyObject>) -> PyResult<PyObject> {
        if let Some(value) = self
            .type_dependencies
            .get(&type_.hash()?)
            .map(|value| value.clone_ref(py))
        {
            return Ok(value);
        };

        default.map(Ok).unwrap_or_else(|| {
            import_alluka(py)?
                .getattr("abc")?
                .getattr("UNDEFINED")
                .map(|v| v.to_object(py))
        })
    }

    #[args(type_, "/")]
    fn remove_type_dependency<'p>(mut self: PyRefMut<'p, Self>, type_: &PyAny) -> PyResult<PyRefMut<'p, Self>> {
        if self.borrow_mut().type_dependencies.remove(&type_.hash()?).is_none() {
            Err(PyKeyError::new_err(format!("Type dependency not found: {type_}")))
        } else {
            Ok(self)
        }
    }

    #[args(callback, override_, "/")]
    fn set_callback_override<'p>(
        mut self: PyRefMut<'p, Self>,
        callback: &PyAny,
        override_: PyObject,
    ) -> PyResult<PyRefMut<'p, Self>> {
        self.borrow_mut().callback_overrides.insert(callback.hash()?, override_);
        Ok(self)
    }

    #[args(callback, "/")]
    pub fn get_callback_override<'p>(&'p self, py: Python<'p>, callback: &'p PyAny) -> PyResult<Option<&'p PyAny>> {
        Ok(self
            .callback_overrides
            .get(&callback.hash()?)
            .map(|value| value.as_ref(py)))
    }

    #[args(callback, "/")]
    fn remove_callback_override<'p>(mut self: PyRefMut<'p, Self>, callback: &PyAny) -> PyResult<PyRefMut<'p, Self>> {
        if self.borrow_mut().callback_overrides.remove(&callback.hash()?).is_none() {
            Err(PyKeyError::new_err(format!(
                "Callback override not found: {}",
                callback
            )))
        } else {
            Ok(self)
        }
    }
}

#[pyo3::pyclass(subclass)]
pub struct BasicContext {
    pub client: Py<Client>,
    result_cache: HashMap<isize, PyObject>,
    special_cased_types: HashMap<isize, PyObject>,
}

impl BasicContext {
    pub fn get_type_dependency_rust<'p>(
        &'p self,
        client: &'p PyRef<'p, Client>,
        type_: &isize,
    ) -> Option<&'p PyObject> {
        self.special_cased_types
            .get(type_)
            .or_else(|| client.get_type_dependency_rust(type_))
    }

    pub fn call_with_di_rust<'p>(
        self: &PyRef<'p, Self>,
        py: Python<'p>,
        client: &PyRef<'p, Client>,
        callback: &'p PyAny,
        args: &PyTuple,
        kwargs: Option<&'p PyDict>,
    ) -> PyResult<&'p PyAny> {
        client.call_with_ctx_rust(py, self, callback, args, kwargs)
    }

    pub fn call_with_async_di_rust(
        slf: Py<Self>,
        client: Py<Client>,
        callback: PyObject,
        args: Py<PyTuple>,
        kwargs: Option<Py<PyDict>>,
    ) -> impl Future<Output = PyResult<PyObject>> {
        Client::call_with_ctx_async_rust(client, slf, callback, args, kwargs)
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
    pub fn call_with_di<'p>(
        self: PyRef<'p, Self>,
        py: Python<'p>,
        callback: &PyAny,
        args: &PyTuple,
        kwargs: Option<&PyDict>,
    ) -> PyResult<PyObject> {
        self.call_with_di_rust(py, &self.client.borrow(py), callback, args, kwargs)
            .map(|value| value.to_object(py))
    }

    #[args(callback, "/", args = "*", kwargs = "**")]
    pub fn call_with_async_di(
        slf: Py<Self>,
        py: Python<'_>,
        callback: PyObject,
        args: Py<PyTuple>,
        kwargs: Option<Py<PyDict>>,
    ) -> PyResult<&PyAny> {
        let client = slf.borrow(py).client.clone_ref(py);
        future_into_py(py, async move {
            // TODO: retain locals
            Self::call_with_async_di_rust(slf, client, callback, args, kwargs).await
        })
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
        if let Some(result) = self.get_type_dependency_rust(&self.client.borrow(py), &type_.hash()?) {
            return Ok(result.to_object(py));
        }

        default.map(Ok).unwrap_or_else(|| {
            import_alluka(py)?
                .getattr("abc")?
                .getattr("UNDEFINED")
                .map(|v| v.to_object(py))
        })
    }
}

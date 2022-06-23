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
use std::lazy::SyncOnceCell;
use std::rc::Rc;
use std::sync::{Arc, RwLock};

use async_executor::{Executor, LocalExecutor};
use pyo3::exceptions::{PyBaseException, PyKeyError};
use pyo3::pycell::PyRef;
use pyo3::types::{IntoPyDict, PyDict, PyTuple};
use pyo3::{IntoPy, Py, PyAny, PyErr, PyObject, PyRefMut, PyResult, Python, ToPyObject};

use crate::types::{Injected, InjectedTuple};
use crate::visitor::{Callback, ParameterVisitor};


pyo3::import_exception!(alluka._errors, AsyncOnlyError);

static ALLUKA: SyncOnceCell<PyObject> = SyncOnceCell::new();
static ANYIO: SyncOnceCell<PyObject> = SyncOnceCell::new();
static ANYIO_UTIL: SyncOnceCell<PyObject> = SyncOnceCell::new();
static ASYNCIO: SyncOnceCell<PyObject> = SyncOnceCell::new();
static SELF_INJECTING: SyncOnceCell<PyObject> = SyncOnceCell::new();

fn import_alluka(py: Python) -> PyResult<&PyAny> {
    ALLUKA
        .get_or_try_init(|| Ok(py.import("alluka")?.to_object(py)))
        .map(|value| value.as_ref(py))
}

fn import_anyio(py: Python) -> PyResult<&PyAny> {
    ANYIO
        .get_or_try_init(|| Ok(py.import("anyio")?.to_object(py)))
        .map(|value| value.as_ref(py))
}

fn import_anyio_util(py: Python) -> PyResult<&PyAny> {
    ANYIO_UTIL
        .get_or_try_init(|| Ok(py.import("alluka._anyio")?.to_object(py)))
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

static EXECUTOR: Executor<'static> = Executor::new();

std::thread_local! {
    pub static LOCAL_EXECUTOR: Rc<LocalExecutor<'static>> = Rc::new(LocalExecutor::new());
}

#[pyo3::pyclass(subclass)]
pub struct Client {
    callback_overrides: HashMap<isize, PyObject>,
    descriptors: RwLock<HashMap<isize, Arc<Box<[InjectedTuple]>>>>,
    introspect_annotations: bool,
    type_dependencies: HashMap<isize, PyObject>,
}

#[pyo3::pyclass]
struct PyFuture {
    channel: PyObject,
    value: Option<PyObject>,
    exception: Option<PyObject>,
}

#[pyo3::pymethods]
impl PyFuture {
    #[getter]
    fn get_channel<'a>(&'a self) -> &'a PyObject {
        &self.channel
    }

    #[getter]
    fn get_value<'a>(&'a self) -> &'a Option<PyObject> {
        &self.value
    }

    #[getter]
    fn get_exception<'a>(&'a self) -> &'a Option<PyObject> {
        &self.exception
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
        slf: &PyRef<'p, Self>,
        py: Python<'p>,
        ctx: &PyRef<'p, BasicContext>,
        callback: &'p PyAny,
        args: &PyTuple,
        mut kwargs: Option<&'p PyDict>,
    ) -> PyResult<&'p PyAny> {
        let descriptors = slf.build_descriptors(py, callback)?;

        if !descriptors.is_empty() {
            let descriptors = descriptors.iter().map(|(key, value)| match value {
                Injected::Type(type_) => type_.resolve_rust(py, slf, ctx).map(|value| (key, value)),
                Injected::Callback(callback) => callback.resolve_rust(py, slf, ctx).map(|value| (key, value)),
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
        slf: &PyRef<'_, Self>,
        py: Python<'_>,
        task_group: &PyAny,
        ctx: &PyRef<'_, BasicContext>,
        callback: &PyAny,
        args: &PyTuple,
        kwargs: Option<Py<PyDict>>,
    ) -> PyResult<PyObject> {
        let descriptors = slf.build_descriptors(py, callback)?;

        if descriptors.is_empty() {
            let result = callback.call1(args)?;
            return import_anyio(py)?
                .call_method1("maybe_async", (result,))
                .map(|value| value.to_object(py));
        }

        let iter = descriptors.iter().map(|(key, value)| async move {
            match value {
                Injected::Type(type_) => type_.resolve_rust(py, slf, ctx).map(|value| (key, value.to_object(py))),
                Injected::Callback(callback) => callback
                    .resolve_rust_async(py, task_group, slf, ctx)
                    .await
                    .map(|value| (key, value)),
            }
        });

        let result = match kwargs {
            Some(kwargs) => {
                let kwargs = kwargs.as_ref(py);
                for entry in iter {
                    let (key, value) = entry.await?;
                    kwargs.set_item(key, value)?;
                }
                callback.call(args, Some(kwargs))?
            }
            None => {
                let kwargs = futures::future::join_all(iter)
                    .await
                    .into_iter()
                    .collect::<PyResult<Vec<(&String, PyObject)>>>()?
                    .into_py_dict(py);
                callback.call(args, Some(kwargs))?
            }
        };
        if import_asyncio(py)?.call_method1("iscoroutine", (result,))?.is_true()? {
            let (sender, receiver) = async_oneshot::oneshot::<Result<PyObject, Py<PyBaseException>>>();
            import_anyio_util(py)?.call_method1("set_result", (result, OneShot { sender }))?;
            receiver.await.unwrap().map_err(|err| PyErr::from_value(err.as_ref(py)))
        } else {
            Ok(result.to_object(py))
        }
    }
}

#[pyo3::pyclass]
struct OneShot {
    sender: async_oneshot::Sender<Result<PyObject, Py<PyBaseException>>>,
}

#[pyo3::pymethods]
impl OneShot {
    #[args(value, "/")]
    fn set(&mut self, value: PyObject) {
        self.sender.send(Ok(value)).unwrap();
    }

    #[args(value, "/")]
    fn set_exception(&mut self, value: Py<PyBaseException>) {
        self.sender.send(Err(value)).unwrap();
    }
}

fn future_into_py<F, T>(py: Python, fut: F) -> PyResult<&PyAny>
where
    F: Future<Output = PyResult<T>> + 'static,
    T: IntoPy<PyObject>, {
    let channel = import_anyio_util(py)?.call_method0("OneShotChannel")?;
    let set_value = channel.getattr("set")?.to_object(py);
    let set_exception = channel.getattr("set_exception")?.to_object(py);

    LOCAL_EXECUTOR.with(move |executor| {
        executor
            .spawn(async move {
                let result = fut.await;
                Python::with_gil(|py| {
                    match result {
                        Ok(value) => set_value.call1(py, (value,)).unwrap(),
                        Err(err) => set_exception.call1(py, (err,)).unwrap(),
                    };
                })
            })
            .detach();
    });

    Ok(channel)
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
    fn as_async_self_injecting<'p>(slf: PyRef<Self>, py: Python<'p>, callback: &PyAny) -> PyResult<&'p PyAny> {
        import_self_injecting(py)?.call_method1("AsyncSelfInjecting", (slf, callback))
    }

    #[args(callback, "/")]
    fn as_self_injecting<'p>(slf: PyRef<Self>, py: Python<'p>, callback: &PyAny) -> PyResult<&'p PyAny> {
        import_self_injecting(py)?.call_method1("SelfInjecting", (slf, callback))
    }

    #[args(callback, "/", args = "*", kwargs = "**")]
    fn call_with_di(
        slf: Py<Self>,
        py: Python,
        callback: &PyAny,
        args: &PyTuple,
        kwargs: Option<&PyDict>,
    ) -> PyResult<PyObject> {
        BasicContext::call_with_di(
            Py::new(py, BasicContext::new(slf))?.borrow(py),
            py,
            callback,
            args,
            kwargs,
        )
        .map(|value| value.to_object(py))
    }

    #[args(ctx, callback, "/", args = "*", kwargs = "**")]
    pub fn call_with_ctx(
        _slf: Py<Self>,
        _py: Python,
        _ctx: &PyAny,
        _callback: &PyAny,
        _args: &PyTuple,
        _kwargs: Option<&PyDict>,
    ) -> PyResult<PyObject> {
        unimplemented!("Custom contexts are not supported yet")
    }

    #[args(task_group, ctx, callback, "/", args = "*", kwargs = "**")]
    pub fn _call_with_ctx_async_rust<'p>(
        slf: Py<Self>,
        py: Python<'p>,
        task_group: PyObject,
        ctx: Py<BasicContext>,
        callback: PyObject,
        args: Py<PyTuple>,
        kwargs: Option<Py<PyDict>>,
    ) -> PyResult<&'p PyAny> {
        future_into_py(py, {
            Python::with_gil(|py| async move {
                // TODO: retain locals
                Self::call_with_ctx_async_rust(
                    &slf.borrow(py),
                    py,
                    task_group.as_ref(py),
                    &ctx.borrow(py),
                    callback.as_ref(py),
                    args.as_ref(py),
                    kwargs,
                )
                .await
            })
        })
    }

    #[args(callback, "/", args = "*", kwargs = "**")]
    fn call_with_async_di<'p>(
        slf: Py<Self>,
        py: Python<'p>,
        callback: &PyAny,
        args: &PyTuple,
        kwargs: Option<&PyDict>,
    ) -> PyResult<&'p PyAny> {
        BasicContext::call_with_async_di(Py::new(py, BasicContext::new(slf))?, py, callback, args, kwargs)
    }

    #[args(ctx, callback, "/", args = "*", kwargs = "**")]
    pub fn call_with_ctx_async(
        _slf: PyRef<'_, Self>,
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
        mut slf: PyRefMut<'p, Self>,
        type_: &PyAny,
        value: PyObject,
    ) -> PyResult<PyRefMut<'p, Self>> {
        slf.borrow_mut().type_dependencies.insert(type_.hash()?, value);
        Ok(slf)
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
    fn remove_type_dependency<'p>(mut slf: PyRefMut<'p, Self>, type_: &PyAny) -> PyResult<PyRefMut<'p, Self>> {
        if slf.borrow_mut().type_dependencies.remove(&type_.hash()?).is_none() {
            Err(PyKeyError::new_err(format!("Type dependency not found: {}", type_)))
        } else {
            Ok(slf)
        }
    }

    #[args(callback, override_, "/")]
    fn set_callback_override<'p>(
        mut slf: PyRefMut<'p, Self>,
        callback: &PyAny,
        override_: PyObject,
    ) -> PyResult<PyRefMut<'p, Self>> {
        slf.borrow_mut().callback_overrides.insert(callback.hash()?, override_);
        Ok(slf)
    }

    #[args(callback, "/")]
    pub fn get_callback_override<'p>(&'p self, py: Python<'p>, callback: &'p PyAny) -> PyResult<Option<&'p PyAny>> {
        Ok(self
            .callback_overrides
            .get(&callback.hash()?)
            .map(|value| value.as_ref(py)))
    }

    #[args(callback, "/")]
    fn remove_callback_override<'p>(mut slf: PyRefMut<'p, Self>, callback: &PyAny) -> PyResult<PyRefMut<'p, Self>> {
        if slf.borrow_mut().callback_overrides.remove(&callback.hash()?).is_none() {
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
        slf: &PyRef<'p, Self>,
        py: Python<'p>,
        client: &PyRef<'p, Client>,
        callback: &'p PyAny,
        args: &PyTuple,
        kwargs: Option<&'p PyDict>,
    ) -> PyResult<&'p PyAny> {
        Client::call_with_ctx_rust(client, py, slf, callback, args, kwargs)
    }

    pub fn call_with_async_di_rust<'p>(
        slf: &'p PyRef<'p, Self>,
        py: Python<'p>,
        task_group: &'p PyAny,
        client: &'p PyRef<'p, Client>,
        callback: &'p PyAny,
        args: &'p PyTuple,
        kwargs: Option<Py<PyDict>>,
    ) -> impl Future<Output = PyResult<PyObject>> + 'p {
        Client::call_with_ctx_async_rust(client, py, task_group, slf, callback, args, kwargs)
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
        slf: PyRef<'p, Self>,
        py: Python<'p>,
        callback: &PyAny,
        args: &PyTuple,
        kwargs: Option<&PyDict>,
    ) -> PyResult<PyObject> {
        Self::call_with_di_rust(&slf, py, &slf.client.borrow(py), callback, args, kwargs)
            .map(|value| value.to_object(py))
    }

    #[args(callback, "/", args = "*", kwargs = "**")]
    pub fn call_with_async_di<'p>(
        slf: Py<Self>,
        py: Python<'p>,
        callback: &PyAny,
        args: &PyTuple,
        kwargs: Option<&PyDict>,
    ) -> PyResult<&'p PyAny> {
        let slf = slf.borrow(py);
        import_anyio_util(py)?.call_method1(
            "with_task_queue",
            (
                slf.client.getattr(py, "_call_with_ctx_async_rust")?,
                (slf, callback, args, kwargs),
            ),
        )
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

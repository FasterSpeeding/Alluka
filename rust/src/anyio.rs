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
use std::future::Future;
use std::lazy::{SyncLazy, SyncOnceCell};

use pyo3::exceptions::{PyBaseException, PyRuntimeError};
use pyo3::types::{PyDict, PyTuple};
use pyo3::{IntoPy, PyAny, PyErr, PyObject, PyResult, Python, ToPyObject};


static ASYNCIO: SyncOnceCell<PyObject> = SyncOnceCell::new();
static PY_ONE_SHOT: SyncOnceCell<PyObject> = SyncOnceCell::new();
static SET_RESULT: SyncOnceCell<PyObject> = SyncOnceCell::new();
static TRIO_LOW: SyncOnceCell<PyObject> = SyncOnceCell::new();

fn import_asyncio(py: Python) -> PyResult<&PyAny> {
    ASYNCIO
        .get_or_try_init(|| Ok(py.import("asyncio")?.to_object(py)))
        .map(|value| value.as_ref(py))
}

fn import_trio_low(py: Python) -> PyResult<&PyAny> {
    TRIO_LOW
        .get_or_try_init(|| Ok(py.import("trio.lowlevel")?.to_object(py)))
        .map(|value| value.as_ref(py))
}

fn py_one_shot(py: Python<'_>) -> PyResult<&PyAny> {
    PY_ONE_SHOT
        .get_or_try_init(|| {
            let globals = PyDict::new(py);
            py.run(
                r#"
import anyio
import copy

class OneShotChannel:
    __slots__ = ("_channel", "_exception", "_value")

    def __init__(self):
        self._channel = anyio.Event()
        self._exception = None
        self._value = None

    def __await__(self):
        return self.get().__await__()

    def set(self, value, /):
        if self._channel.is_set():
            raise RuntimeError("Channel already set")

        self._value = value
        self._channel.set()

    def set_exception(self, exception, /):
        if self._channel.is_set():
            raise RuntimeError("Channel already set")

        self._exception = exception
        self._channel.set()

    async def get(self):
        if not self._channel.is_set():
            await self._channel.wait()

        if self._exception:
            raise copy.copy(self._exception)

        return self._value
        "#,
                Some(globals),
                None,
            )?;

            Ok::<_, PyErr>(globals.get_item("OneShotChannel").unwrap().to_object(py))
        })?
        .as_ref(py)
        .call0()
}


fn set_result(py: Python<'_>) -> PyResult<&PyAny> {
    SET_RESULT
        .get_or_try_init(|| {
            let globals = PyDict::new(py);
            py.run(
                r#"
async def set_result(coro, one_shot, /):
    try:
        result = await coro

    except BaseException as exc:
        one_shot.set_exception(exc)

    else:
        one_shot.set(result)
            "#,
                Some(globals),
                None,
            )?;

            Ok::<_, PyErr>(globals.get_item("set_result").unwrap().to_object(py))
        })
        .map(|value| value.as_ref(py))
}


#[pyo3::pyclass]
struct OneShot {
    sender: async_oneshot::Sender<Result<PyObject, PyErr>>,
}

#[pyo3::pymethods]
impl OneShot {
    #[args(value, "/")]
    fn set(&mut self, value: PyObject) {
        self.sender.send(Ok(value)).unwrap();
    }

    #[args(value, "/")]
    fn set_exception(&mut self, value: &PyBaseException) {
        self.sender.send(Err(PyErr::from_value(value))).unwrap();
    }

    fn asyncio_callback(&mut self, py: Python, task: &PyAny) {
        match task.call_method0("result") {
            Ok(result) => self.set(result.to_object(py)),
            Err(err) => self.sender.send(Err(err)).unwrap(),
        }
    }
}

static EXECUTOR: SyncLazy<tokio::runtime::Runtime> = SyncLazy::new(|| {
    let mut builder = tokio::runtime::Builder::new_multi_thread();
    builder.enable_all();
    builder.build().expect("Failed to start executor")
});

enum Context {
    Asyncio(PyObject),
    Trio(PyObject),
}

impl Context {
    fn new(py: Python) -> PyResult<Self> {
        match import_asyncio(py)?.call_method0("get_running_loop") {
            Ok(event_loop) => return Ok(Self::Asyncio(event_loop.to_object(py))),
            Err(err) if !err.is_instance_of::<PyRuntimeError>(py) => return Err(err),
            _ => {}
        };

        match import_trio_low(py)?.call_method0("current_trio_token") {
            Ok(token) => Ok(Self::Trio(token.to_object(py))),
            Err(err) if err.is_instance_of::<PyRuntimeError>(py) => {
                Err(PyRuntimeError::new_err("No running event loop"))
            }
            Err(err) => Err(err),
        }
    }

    fn call_soon<'a>(&self, py: Python, callback: &PyAny, args: impl Into<Vec<&'a PyAny>>) -> PyResult<()> {
        let mut args = args.into();
        args.insert(0, callback);
        let args = PyTuple::new(py, args);
        match self {
            Context::Asyncio(event_loop) => event_loop.call_method1(py, "call_soon_threadsafe", args)?,
            Context::Trio(token) => token.call_method1(py, "run_sync_soon", args)?,
        };

        Ok(())
    }

    fn spawn_task<'a>(&self, py: Python, callback: &PyAny, args: impl Into<Vec<&'a PyAny>>) -> PyResult<()> {
        let mut args = args.into();
        args.insert(0, callback);
        match self {
            Context::Asyncio(_) => self.call_soon(py, import_asyncio(py)?.getattr("create_task")?, args)?,
            Context::Trio(_) => self.call_soon(py, import_trio_low(py)?.getattr("spawn_system_task")?, args)?,
        };

        Ok(())
    }
}

tokio::task_local! {
    static PY_RUNTIME: Context;
}

pub fn future_into_py<F, T>(py: Python, fut: F) -> PyResult<&PyAny>
where
    F: Future<Output = PyResult<T>> + 'static + Send,
    T: IntoPy<PyObject>, {
    let channel = py_one_shot(py)?;
    let set_value = channel.getattr("set")?.to_object(py);
    let set_exception = channel.getattr("set_exception")?.to_object(py);

    EXECUTOR.spawn(PY_RUNTIME.scope(Context::new(py)?, async move {
        let result = fut.await;
        Python::with_gil(|py| {
            PY_RUNTIME.with(|ctx| match result {
                Ok(value) => ctx
                    .call_soon(py, set_value.as_ref(py), [value.into_py(py).as_ref(py)])
                    .unwrap(),
                Err(err) => ctx
                    .call_soon(py, set_exception.as_ref(py), [err.to_object(py).as_ref(py)])
                    .unwrap(),
            });
        });
    }));

    Ok(channel)
}

#[pyo3::pyclass]
struct CreateEvent {}

#[pyo3::pymethods]
impl CreateEvent {
    fn __call__(&self, py: Python, event_loop: &PyAny, awaitable: &PyAny, one_shot: &PyAny) -> PyResult<()> {
        event_loop
            .call_method1("create_task", (awaitable,))?
            .call_method1("add_done_callback", (one_shot,))
            .map(|_| ())
    }
}

pub fn into_future(
    py: Python<'_>,
    awaitable: &PyAny,
) -> PyResult<impl Future<Output = PyResult<PyObject>> + Send + 'static> {
    let (sender, receiver) = async_oneshot::oneshot::<PyResult<PyObject>>();
    PY_RUNTIME.with(|locals| {
        let one_shot = OneShot { sender }.into_py(py);
        match locals {
            Context::Asyncio(event_loop) => locals.call_soon(py, CreateEvent {}.into_py(py).as_ref(py), [
                event_loop.as_ref(py),
                awaitable,
                one_shot.getattr(py, "asyncio_callback")?.as_ref(py),
            ]),
            Context::Trio(_) => locals.call_soon(py, import_trio_low(py)?.getattr("spawn_system_task")?, [
                set_result(py)?,
                awaitable,
                one_shot.as_ref(py),
            ]),
        }?;

        Ok::<(), PyErr>(())
    })?;

    Ok(async move { receiver.await.unwrap() })
}

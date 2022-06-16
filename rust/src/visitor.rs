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
use std::collections::HashMap;
use std::lazy::Lazy;
use std::sync::{Arc, RwLock};

use pyo3::exceptions::{PyKeyError, PyValueError};
use pyo3::types::{IntoPyDict, PyMapping, PyModule, PyString, PyTuple};
use pyo3::{FromPyObject, IntoPy, Py, PyAny, PyErr, PyObject, PyResult, Python, ToPyObject};

use crate::types::{Injected, InjectedCallback, InjectedType};

const INSPECT: Lazy<PyObject> = Lazy::new(|| {
    Python::with_gil(|py| {
        py.import("alluka._internal")
            .unwrap()
            .getattr("inspect")
            .unwrap()
            .into_py(py)
    })
});


trait Node {
    fn new(callback: Arc<Callback>, name: String) -> PyResult<Self>
    where
        Self: Sized;
    fn accept<V: Visitor>(&self) -> PyResult<Option<Injected>>;
}

struct Annotation {}

impl Node for Annotation {
    fn new(callback: Arc<Callback>, name: String) -> PyResult<Self> {
        Ok(Self {})
    }

    fn accept<V: Visitor>(&self) -> PyResult<Option<Injected>> {
        V::visit_annotation(self)
    }
}

pub struct Callback {
    callback: PyObject,
    pub empty: PyObject,
    is_resolved: bool,
    pub signature: RwLock<Option<HashMap<String, PyObject>>>,
}

fn _inspect(py: Python, callback: &PyObject, eval_str: bool) -> PyResult<Option<HashMap<String, PyObject>>> {
    let signature = INSPECT
        .getattr(py, "signature")?
        .call_method(
            py,
            "callback",
            (callback.clone_ref(py),),
            Some([("eval_str", eval_str.to_object(py))].into_py_dict(py)),
        )
        .and_then(|signature| {
            signature
                .cast_as::<PyMapping>(py)
                .map_err(PyErr::from)?
                .items()?
                .iter()?
                .map(|entry| {
                    entry
                        .and_then(|value| value.cast_as::<PyTuple>().map_err(PyErr::from))
                        .and_then(|value| Ok((String::extract(value.get_item(0)?)?, value.get_item(1)?.into_py(py))))
                })
                .collect::<PyResult<HashMap<String, PyObject>>>()
        })
        .map(Some);

    match signature {
        Err(err) if err.is_instance_of::<PyValueError>(py) => Ok(None),
        other => other,
    }
}

impl Callback {
    pub fn new(py: Python, callback: PyObject) -> PyResult<Self> {
        let empty = INSPECT.getattr(py, "Parameter")?.getattr(py, "empty")?;

        Ok(Self {
            callback: callback.clone_ref(py),
            empty,
            is_resolved: false,
            signature: RwLock::new(_inspect(py, &callback, false)?),
        })
    }

    pub fn accept<V: Visitor>(&self) -> PyResult<Vec<(String, Injected)>> {
        V::visit_callback(self)
    }

    pub fn resolve_annotation(&mut self, py: Python, name: &str) -> PyResult<Option<PyObject>> {
        let parameters = self.signature.read().unwrap();
        if parameters.is_none() {
            return Ok(None);
        }

        match parameters
            .as_ref()
            .unwrap()
            .get(name)
            .map(|parameter| parameter.getattr(py, "annotation"))
        {
            Some(Ok(annotation)) => {
                if annotation.is(&self.empty) {
                    return Ok(None);
                }

                if !self.is_resolved && annotation.as_ref(py).is_instance_of::<PyString>()? {
                    *self.signature.write().unwrap() = _inspect(py, &self.callback, true)?;
                    self.is_resolved = true;
                    drop(parameters);
                    self.resolve_annotation(py, name)
                } else {
                    Ok(Some(annotation))
                }
            }
            Some(Err(err)) => Err(err),
            None => Err(PyKeyError::new_err(name.to_owned())),
        }
    }
}

struct Default {
    pub callback: Arc<Callback>,
    pub default: Option<PyObject>,
    pub name: String,
}

impl Default {
    fn is_empty(&self) -> bool {
        self.default.is_none()
    }
}

impl Node for Default {
    fn new(callback: Arc<Callback>, name: String) -> PyResult<Self> {
        let default = callback
            .signature
            .read()
            .unwrap()
            .as_ref()
            .unwrap()
            .get(&name)
            .ok_or_else(|| PyKeyError::new_err(name.clone()))?
            .clone();

        Ok(Self {
            default: if default.is(&callback.empty) {
                None
            } else {
                Some(default)
            },
            callback,
            name,
        })
    }

    fn accept<V: Visitor>(&self) -> PyResult<Option<Injected>> {
        V::visit_default(self)
    }
}

pub trait Visitor {
    fn visit_callback(node: &Callback) -> PyResult<Vec<(String, Injected)>>;
    fn visit_annotation(node: &Annotation) -> PyResult<Option<Injected>>;
    fn visit_default(node: &Default) -> PyResult<Option<Injected>>;
}

pub struct ParameterVisitor {}

impl ParameterVisitor {
    fn _parse_type(type_: &PyObject, other_default: Option<PyObject>) -> (Vec<PyObject>, Option<PyObject>) {
        (vec![], other_default)
    }

    fn _annotation_to_type(annotation: PyObject) -> PyObject {
        annotation
    }
}

impl Visitor for ParameterVisitor {
    fn visit_callback(node: &Callback) -> PyResult<Vec<(String, Injected)>> {
        Ok(vec![])
    }

    fn visit_annotation(node: &Annotation) -> PyResult<Option<Injected>> {
        Ok(None)
    }

    fn visit_default(node: &Default) -> PyResult<Option<Injected>> {
        Ok(None)
    }
}

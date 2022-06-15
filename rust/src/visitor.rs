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

use pyo3::exceptions::PyValueError;
use pyo3::types::{IntoPyDict, PyMapping, PyModule, PyTuple};
use pyo3::{FromPyObject, IntoPy, Py, PyAny, PyErr, PyObject, PyResult, Python, ToPyObject};

const INSPECT: Lazy<PyObject> = Lazy::new(|| {
    Python::with_gil(|py| {
        py.import("alluka._internal")
            .unwrap()
            .getattr("inspect")
            .unwrap()
            .into_py(py)
    })
});


pub enum InjectedTuple {
    Callback(PyObject),
    Type(PyObject),
}


trait Node {
    fn accept<V: Visitor>(&self) -> Option<InjectedTuple>;
}

struct Annotation {}

impl Node for Annotation {
    fn accept<V: Visitor>(&self) -> Option<InjectedTuple> {
        V::visit_annotation(self)
    }
}

struct Callback {
    callback: PyObject,
    is_resolved: bool,
    signature: Option<HashMap<String, PyObject>>,
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
            Ok(signature
                .cast_as::<PyMapping>(py)
                .map_err(PyErr::from)?
                .items()?
                .iter()?
                .map(|entry| {
                    entry
                        .and_then(|value| value.cast_as::<PyTuple>().map_err(PyErr::from))
                        .and_then(|value| Ok((String::extract(value.get_item(0)?)?, value.get_item(1)?.into_py(py))))
                })
                .collect::<PyResult<HashMap<String, PyObject>>>()?)
        })
        .map(Some);

    match signature {
        Err(err) if err.is_instance_of::<PyValueError>(py) => Ok(None),
        other => other,
    }
}

impl Callback {
    fn new(py: Python, callback: PyObject) -> PyResult<Self> {
        Ok(Self {
            callback: callback.clone_ref(py),
            is_resolved: false,
            signature: _inspect(py, &callback, false)?,
        })
    }

    pub fn accept<V: Visitor>(&self) -> Vec<(String, InjectedTuple)> {
        V::visit_callback(self)
    }

    pub fn resolve_annotation(&mut self, name: &str) -> PyResult<Option<PyObject>> {
        let parameters = match self.signature {
            Some(signatures) => signatures.clone(),
            None => return Ok(None),
        };

        if let Some(annotation) = parameters.get(name).map(|parameter| paramter.getattr("annotation")) {}
    }
}

struct Default {
    pub callback: PyObject,
    pub default: Option<PyObject>,
    pub name: String,
}

impl Default {
    fn is_empty(&self) -> bool {
        true
    }
}

impl Node for Default {
    fn accept<V: Visitor>(&self) -> Option<InjectedTuple> {
        V::visit_default(self)
    }
}

trait Visitor {
    fn visit_callback(node: &Callback) -> Vec<(String, InjectedTuple)> {
        vec![]
    }

    fn visit_annotation(node: &Annotation) -> Option<InjectedTuple> {
        None
    }

    fn visit_default(node: &Default) -> Option<InjectedTuple> {
        None
    }
}

struct ParameterVisitor {}

impl ParameterVisitor {
    fn _parse_type(type_: &PyObject, other_default: Option<PyObject>) -> (Vec<PyObject>, Option<PyObject>) {
        (vec![], other_default)
    }

    fn _annotation_to_type(annotation: PyObject) -> PyObject {
        annotation
    }
}

impl Visitor for ParameterVisitor {
    fn visit_callback(node: &Callback) -> Vec<(String, InjectedTuple)> {
        vec![]
    }

    fn visit_annotation(node: &Annotation) -> Option<InjectedTuple> {
        None
    }

    fn visit_default(node: &Default) -> Option<InjectedTuple> {
        None
    }
}

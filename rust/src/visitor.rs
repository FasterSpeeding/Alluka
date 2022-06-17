use std::any::Any;
// BSD 3-Clause License
//
// Copyright (c) 2022, Lucina
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//
// * Redistributions of source code must retain the above copyright notice, this list of conditions and the
//   following disclaimer.
//
// * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
//   following disclaimer in the documentation and/or other materials provided with the distribution.
//
// * Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote
//   products derived from this software without specific prior written permission.
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
use std::rc::Rc;
use std::sync::{Arc, RwLock};

use pyo3::basic::PyObjectReprProtocol;
use pyo3::exceptions::{PyKeyError, PyValueError};
use pyo3::types::{IntoPyDict, PyMapping, PyModule, PyString, PyTuple};
use pyo3::{import_exception, FromPyObject, IntoPy, Py, PyAny, PyErr, PyObject, PyResult, Python, ToPyObject};

use crate::types::{Injected, InjectedCallback, InjectedTuple, InjectedType};

import_exception!(alluka._types, InjectedDescriptor);

const INSPECT: Lazy<PyObject> = Lazy::new(|| {
    Python::with_gil(|py| {
        py.import("alluka._internal")
            .unwrap()
            .getattr("inspect")
            .unwrap()
            .into_py(py)
    })
});
const TYPING: Lazy<PyObject> = Lazy::new(|| Python::with_gil(|py| py.import("typing").unwrap().to_object(py)));
const UNION_TYPES: Lazy<(PyObject, PyObject)> = Lazy::new(|| {
    Python::with_gil(|py| {
        let types_ = py.import("types").unwrap();
        (
            types_.getattr("UnionType").unwrap().into_py(py),
            TYPING.getattr(py, "Union").unwrap().into_py(py),
        )
    })
});

trait Node {
    fn new(callback: Rc<Callback>, name: String) -> PyResult<Self>
    where
        Self: Sized;
    fn accept<V: Visitor>(&self, py: Python) -> PyResult<Option<Injected>>;
}

struct Annotation {}

impl Node for Annotation {
    fn new(callback: Rc<Callback>, name: String) -> PyResult<Self> {
        Ok(Self {})
    }

    fn accept<V: Visitor>(&self, py: Python) -> PyResult<Option<Injected>> {
        V::visit_annotation(py, self)
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
        .call_method(
            py,
            "signature",
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

    pub fn accept<V: Visitor>(self, py: Python) -> PyResult<Vec<InjectedTuple>> {
        V::visit_callback(py, Rc::new(self))
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
    pub callback: Rc<Callback>,
    pub default: Option<PyObject>,
    pub name: String,
}


impl Node for Default {
    fn new(callback: Rc<Callback>, name: String) -> PyResult<Self> {
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

    fn accept<V: Visitor>(&self, py: Python) -> PyResult<Option<Injected>> {
        V::visit_default(py, self)
    }
}

pub trait Visitor {
    fn visit_annotation(py: Python, node: &Annotation) -> PyResult<Option<Injected>>;
    fn visit_callback(py: Python, node: Rc<Callback>) -> PyResult<Vec<InjectedTuple>>;
    fn visit_default(py: Python, node: &Default) -> PyResult<Option<Injected>>;
}

pub struct ParameterVisitor {}

impl ParameterVisitor {
    fn parse_type(
        py: Python,
        type_: PyObject,
        other_default: Option<PyObject>,
    ) -> PyResult<(Vec<PyObject>, Option<PyObject>)> {
        let origin = TYPING.call_method1(py, "get_origin", (&type_,))?;
        if !origin.is(&UNION_TYPES.0) && !origin.is(&UNION_TYPES.1) {
            return Ok((vec![type_], other_default));
        };

        let mut sub_types = origin
            .as_ref(py)
            .iter()?
            .map(|entry| entry.map(|value| value.to_object(py)))
            .collect::<PyResult<Vec<PyObject>>>()?;
        let none_type = py.None().as_ref(py).get_type().to_object(py);

        for value in sub_types.iter() {
            if none_type.is(value) {
                sub_types.retain(|value| !none_type.is(value));
                return Ok((sub_types, Some(py.None().to_object(py))));
            }
        }

        Ok((sub_types, other_default))
    }

    fn annotation_to_type(py: Python, annotation: PyObject) -> PyResult<PyObject> {
        let origin = TYPING.call_method1(py, "get_origin", (&annotation,))?;
        if origin.is(&TYPING.getattr(py, "Annotated")?) {
            // The first "type" arg of annotated will always be flatterned to a type.
            // so we don't have to deal with Annotated nesting".
            origin.as_ref(py).get_item(0).map(|value| value.to_object(py))
        } else {
            Ok(annotation)
        }
    }
}
fn _accept<N: Node, V: Visitor>(py: Python, callback: Rc<Callback>, name: &String) -> Option<PyResult<Injected>> {
    match N::new(callback, name.to_owned()) {
        Ok(node) => node.accept::<V>(py).transpose(),
        Err(err) => Some(Err(err)),
    }
}

impl Visitor for ParameterVisitor {
    fn visit_annotation(py: Python, node: &Annotation) -> PyResult<Option<Injected>> {
        Ok(None)
    }

    fn visit_callback(py: Python, callback: Rc<Callback>) -> PyResult<Vec<InjectedTuple>> {
        let signature = callback.signature.read().unwrap();
        if signature.is_none() {
            return Ok(vec![]);
        }

        signature
            .as_ref()
            .unwrap()
            .iter()
            .map(|(name, value)| {
                if let Some(result) = _accept::<Default, Self>(py, callback.clone(), name)
                    .or_else(|| _accept::<Annotation, Self>(py, callback.clone(), name))
                    .transpose()?
                {
                    Ok(Some((name.to_owned(), result)))
                } else {
                    Ok(None)
                }
            })
            .filter_map(Result::transpose)
            .collect::<PyResult<Vec<InjectedTuple>>>()
    }

    fn visit_default(py: Python, node: &Default) -> PyResult<Option<Injected>> {
        let default = match node.default.as_ref() {
            Some(default) if default.as_ref(py).is_instance_of::<InjectedDescriptor>()? => default,
            _ => return Ok(None),
        };

        Ok(None)
    }
}

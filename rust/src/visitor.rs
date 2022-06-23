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
use std::lazy::{OnceCell, SyncOnceCell};
use std::rc::Rc;
use std::sync::RwLock;

use pyo3::exceptions::{PyKeyError, PyValueError};
use pyo3::type_object::PyTypeObject;
use pyo3::types::{IntoPyDict, PyMapping, PyString, PyTuple};
use pyo3::{FromPyObject, IntoPy, PyAny, PyErr, PyObject, PyResult, Python, ToPyObject};

use crate::types::{Injected, InjectedTuple};

pyo3::import_exception!(alluka._types, InjectedDescriptor);

static ALLUKA: SyncOnceCell<PyObject> = SyncOnceCell::new();
static INSPECT: SyncOnceCell<PyObject> = SyncOnceCell::new();
static TYPE: SyncOnceCell<PyObject> = SyncOnceCell::new();
static TYPING: SyncOnceCell<PyObject> = SyncOnceCell::new();

fn import_alluka(py: Python) -> PyResult<&PyAny> {
    ALLUKA
        .get_or_try_init(|| Ok(py.import("alluka")?.to_object(py)))
        .map(|value| value.as_ref(py))
}

fn import_inspect(py: Python) -> PyResult<&PyAny> {
    INSPECT
        .get_or_try_init(|| Ok(py.import("alluka._vendor.inspect")?.to_object(py)))
        .map(|value| value.as_ref(py))
}

fn import_type(py: Python) -> PyResult<&PyAny> {
    TYPE.get_or_try_init(|| Ok(py.import("types")?.to_object(py)))
        .map(|value| value.as_ref(py))
}

fn import_typing(py: Python) -> PyResult<&PyAny> {
    TYPING
        .get_or_try_init(|| Ok(py.import("typing")?.to_object(py)))
        .map(|value| value.as_ref(py))
}


trait Node {
    fn new(py: Python, callback: Rc<Callback>, name: String) -> PyResult<Self>
    where
        Self: Sized;
    fn accept<V: Visitor>(&self, py: Python) -> PyResult<Option<Injected>>;
}

pub(crate) struct Annotation {
    pub callback: Rc<Callback>,
    pub name: String,
}

impl Node for Annotation {
    fn new(_py: Python, callback: Rc<Callback>, name: String) -> PyResult<Self> {
        Ok(Self { callback, name })
    }

    fn accept<V: Visitor>(&self, py: Python) -> PyResult<Option<Injected>> {
        V::visit_annotation(py, self)
    }
}

pub(crate) struct Callback {
    callback: PyObject,
    pub empty: PyObject,
    resolved: OnceCell<()>,
    pub signature: RwLock<Option<HashMap<String, PyObject>>>,
}

fn _inspect(py: Python, callback: &PyAny, eval_str: bool) -> PyResult<Option<HashMap<String, PyObject>>> {
    let signature: PyResult<Option<HashMap<String, PyObject>>> = import_inspect(py)?
        .call_method(
            "signature",
            (callback,),
            Some([("eval_str", eval_str.to_object(py))].into_py_dict(py)),
        )
        .and_then(|signature| {
            signature
                .getattr("parameters")?
                .cast_as::<PyMapping>()
                .map_err(PyErr::from)?
                .items()?
                .iter()?
                .map(|entry| {
                    entry
                        .and_then(|value| value.cast_as::<PyTuple>().map_err(PyErr::from))
                        .and_then(|value| Ok((String::extract(value.get_item(0)?)?, value.get_item(1)?.into_py(py))))
                })
                .collect()
        })
        .map(Some);

    match signature {
        Err(err) if err.is_instance_of::<PyValueError>(py) => Ok(None),
        other => other,
    }
}

impl Callback {
    pub fn new(py: Python, callback: &PyAny) -> PyResult<Self> {
        let empty = import_inspect(py)?
            .getattr("Parameter")?
            .getattr("empty")?
            .to_object(py);

        Ok(Self {
            callback: callback.to_object(py),
            empty,
            resolved: OnceCell::new(),
            signature: RwLock::new(_inspect(py, callback, false)?),
        })
    }

    pub fn accept<V: Visitor>(self, py: Python) -> PyResult<Vec<InjectedTuple>> {
        V::visit_callback(py, Rc::new(self))
    }

    pub fn resolve_annotation(&self, py: Python, name: &str) -> PyResult<Option<PyObject>> {
        let parameters = self.signature.read().unwrap();
        if parameters.is_none() {
            return Ok(None);
        }

        let parameters = parameters
            .as_ref()
            .unwrap()
            .get(name)
            .map(|parameter| parameter.getattr(py, "annotation"));

        match parameters {
            Some(Ok(annotation)) => {
                if annotation.is(&self.empty) {
                    return Ok(None);
                }

                if self.resolved.get().is_none() && annotation.as_ref(py).is_instance_of::<PyString>()? {
                    *self.signature.write().unwrap() = _inspect(py, self.callback.as_ref(py), true)?;
                    self.resolved.set(()).unwrap();
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

pub(crate) struct Default {
    pub callback: Rc<Callback>,
    pub default: Option<PyObject>,
    pub name: String,
}


impl Node for Default {
    fn new(py: Python, callback: Rc<Callback>, name: String) -> PyResult<Self> {
        let default = callback
            .signature
            .read()
            .unwrap()
            .as_ref()
            .unwrap()
            .get(&name)
            .ok_or_else(|| PyKeyError::new_err(name.clone()))?
            .getattr(py, "default")?;

        let default = if default.is(&callback.empty) {
            None
        } else {
            Some(default)
        };

        Ok(Self {
            default,
            callback,
            name,
        })
    }

    fn accept<V: Visitor>(&self, py: Python) -> PyResult<Option<Injected>> {
        V::visit_default(py, self)
    }
}

pub(crate) trait Visitor {
    fn visit_annotation(py: Python, node: &Annotation) -> PyResult<Option<Injected>>;
    fn visit_callback(py: Python, node: Rc<Callback>) -> PyResult<Vec<InjectedTuple>>;
    fn visit_default(py: Python, node: &Default) -> PyResult<Option<Injected>>;
}

pub(crate) struct ParameterVisitor {}

impl ParameterVisitor {
    fn parse_type(py: Python, type_: &PyAny, other_default: Option<&PyAny>) -> PyResult<Injected> {
        let typing = import_typing(py)?;
        let origin = typing.call_method1("get_origin", (type_,))?;
        if !origin.is(import_type(py)?.getattr("UnionType")?) && !origin.is(typing.getattr("Union")?) {
            return Injected::new_type(py, other_default, type_, vec![type_]);
        };

        let mut sub_types = typing
            .call_method1("get_args", (type_,))?
            .iter()?
            .collect::<PyResult<Vec<&PyAny>>>()?;
        let len = sub_types.len();
        let none_ = py.None();
        let none = none_.as_ref(py);
        sub_types.retain(|value| !value.is(none.get_type()));

        if sub_types.len() != len && other_default.is_none() {
            return Injected::new_type(py, Some(none), type_, sub_types);
        }

        Injected::new_type(py, other_default, type_, sub_types)
    }

    fn annotation_to_type(py: Python, annotation: &PyAny, default: Option<&PyAny>) -> PyResult<Injected> {
        let typing = import_typing(py)?;
        let origin = typing.call_method1("get_origin", (annotation,))?;
        if origin.is(typing.getattr("Annotated")?) {
            // The first "type" arg of annotated will always be flatterned to a type.
            // so we don't have to deal with Annotated nesting".
            Self::parse_type(py, origin.get_item(0)?, default)
        } else {
            Self::parse_type(py, annotation, default)
        }
    }
}
fn _accept<N: Node, V: Visitor>(py: Python, callback: Rc<Callback>, name: &String) -> Option<PyResult<Injected>> {
    match N::new(py, callback, name.to_owned()) {
        Ok(node) => node.accept::<V>(py).transpose(),
        Err(err) => Some(Err(err)),
    }
}

impl Visitor for ParameterVisitor {
    fn visit_annotation(py: Python, node: &Annotation) -> PyResult<Option<Injected>> {
        let value = match node.callback.resolve_annotation(py, &node.name)? {
            Some(annotation) => annotation,
            None => return Ok(None),
        };
        let parameter = node
            .callback
            .signature
            .read()
            .unwrap()
            .as_ref()
            .unwrap()
            .get(&node.name)
            .map(|parameter| parameter.clone_ref(py))
            .ok_or_else(|| PyKeyError::new_err(node.name.clone()))?;

        let default = parameter.getattr(py, "default")?;
        let default = if default.is(import_inspect(py)?.getattr("Parameter")?.getattr("empty")?) {
            None
        } else {
            Some(default.as_ref(py))
        };

        let typing = import_typing(py)?;
        if !typing
            .call_method1("get_origin", (&value,))?
            .is(typing.getattr("Annotated")?)
        {
            return Ok(None);
        }

        let args = typing.call_method1("get_args", (&value,))?;
        if args.contains(
            import_alluka(py)?
                .getattr("_types")?
                .getattr("InjectedTypes")?
                .getattr("TYPE")?,
        )? {
            return Self::annotation_to_type(py, args.get_item(0)?, default).map(Some);
        }

        let descriptor_type = InjectedDescriptor::type_object(py);
        for arg in args.iter()? {
            let arg = arg?;
            if !arg.is_instance(descriptor_type)? {
                continue;
            }

            let callback = arg.getattr("callback")?;
            if !callback.is_none() {
                return Ok(Some(Injected::new_callback(py, callback)));
            }

            let type_ = arg.getattr("type")?;
            if !type_.is_none() {
                return Self::parse_type(py, type_, default).map(Some);
            }

            return Self::annotation_to_type(py, args.get_item(0)?, default).map(Some);
        }

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
            .map(|(name, _)| {
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
            .collect()
    }

    fn visit_default(py: Python, node: &Default) -> PyResult<Option<Injected>> {
        let default = match node.default.as_ref() {
            Some(default) if default.as_ref(py).is_instance_of::<InjectedDescriptor>()? => default,
            _ => return Ok(None),
        };

        let callback = default.getattr(py, "callback")?;
        if !callback.is_none(py) {
            return Ok(Some(Injected::new_callback(py, callback.as_ref(py))));
        };

        let type_ = default.getattr(py, "type")?;
        if !type_.is_none(py) {
            return Self::parse_type(py, type_.as_ref(py), None).map(Some);
        };

        match node.callback.resolve_annotation(py, &node.name)? {
            Some(annotaton) => Self::parse_type(py, annotaton.as_ref(py), None).map(Some),
            None => Err(PyValueError::new_err(format!(
                "Could not resolve type for parameter {} with no annotation",
                node.name
            ))),
        }
    }
}

//! Collects every configuration problem so one start-up error lists all of them, by variable name.

use std::str::FromStr;

use crate::{Error, Result};

pub struct Loader<'a> {
    get: &'a dyn Fn(&str) -> Option<String>,
    errors: Vec<String>,
}

impl<'a> Loader<'a> {
    pub fn new(get: &'a dyn Fn(&str) -> Option<String>) -> Self {
        Loader {
            get,
            errors: Vec::new(),
        }
    }

    fn value(&self, name: &str) -> Option<String> {
        (self.get)(name)
            .map(|v| v.trim().to_string())
            .filter(|v| !v.is_empty())
    }

    /// A required, non-empty variable.
    pub fn req(&mut self, name: &str) -> String {
        self.value(name).unwrap_or_else(|| {
            self.errors.push(format!("{name} is required"));
            String::new()
        })
    }

    /// The variable, or `default` when unset or empty.
    pub fn str(&mut self, name: &str, default: &str) -> String {
        self.value(name).unwrap_or_else(|| default.to_string())
    }

    /// The first variable of `names` that is set, or `default`.
    pub fn first(&mut self, names: &[&str], default: &str) -> String {
        names
            .iter()
            .find_map(|name| self.value(name))
            .unwrap_or_else(|| default.to_string())
    }

    /// A parsed number (`u16`, `u32`, `i64`, ...), or `default` when unset; a malformed value is
    /// recorded.
    pub fn num<T: FromStr + Copy>(&mut self, name: &str, default: T) -> T {
        match self.value(name) {
            None => default,
            Some(raw) => raw.parse().unwrap_or_else(|_| {
                self.errors.push(format!("{name} must be a number"));
                default
            }),
        }
    }

    /// true/false/1/0/yes/no/on/off, or `default` when unset.
    pub fn flag(&mut self, name: &str, default: bool) -> bool {
        match self.value(name).map(|v| v.to_lowercase()).as_deref() {
            None => default,
            Some("1" | "true" | "yes" | "on") => true,
            Some("0" | "false" | "no" | "off") => false,
            Some(_) => {
                self.errors.push(format!("{name} must be true or false"));
                default
            }
        }
    }

    /// A required secret: NAME, else the contents of the file named by NAME_FILE. No default, ever.
    pub fn secret(&mut self, name: &str) -> String {
        match self.read_secret(name) {
            Ok(Some(v)) => v,
            Ok(None) => {
                self.errors
                    .push(format!("{name} or {name}_FILE is required"));
                String::new()
            }
            Err(e) => {
                self.errors.push(e);
                String::new()
            }
        }
    }

    /// A secret that is required only in some modes (Kafka SASL); the caller enforces the mode with
    /// `fail`.
    pub fn opt_secret(&mut self, name: &str) -> String {
        self.read_secret(name)
            .unwrap_or_else(|e| {
                self.errors.push(e);
                None
            })
            .unwrap_or_default()
    }

    /// Records a cross-field validation error.
    pub fn fail(&mut self, message: String) {
        self.errors.push(message);
    }

    pub fn finish(self) -> Result<()> {
        if self.errors.is_empty() {
            Ok(())
        } else {
            Err(Error::Config(self.errors.join("; ")))
        }
    }

    fn read_secret(&self, name: &str) -> std::result::Result<Option<String>, String> {
        if let Some(v) = self.value(name) {
            return Ok(Some(v));
        }
        match self.value(&format!("{name}_FILE")) {
            Some(path) => std::fs::read_to_string(&path)
                .map(|v| Some(v.trim().to_string()))
                .map_err(|e| format!("{name}_FILE: {}", e.kind())),
            None => Ok(None),
        }
    }
}

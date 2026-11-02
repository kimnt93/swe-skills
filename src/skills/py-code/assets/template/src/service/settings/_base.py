"""Shared base of every settings class: environment only, no pydantic.

A settings class is a keyword-only dataclass whose fields are declared with
`setting(...)`. `EnvSettings.__init__` reads each field from its environment
variable, converts the text to the annotated type with msgspec ("5432" ->
5432, "true" -> True), checks the bounds and raises ONE `SettingsError` that
lists every missing or invalid variable by name and never prints a value.

A secret is `Secret`-typed, read from `NAME` or from the file named by
`NAME_FILE` (a mounted Swarm secret), and has no default. A `Secret` shows
asterisks in `repr`, `str` and `dataclasses.asdict`.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import field, fields
from pathlib import Path
from typing import Any, get_type_hints

import msgspec


class SettingsError(ValueError):
    """Names the variables that are missing or invalid, never a value."""


class Secret:
    """A value that must not leak: logs and reprs show asterisks."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def get_secret_value(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "Secret('**********')" if self._value else "Secret('')"

    __str__ = __repr__

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Secret) and other._value == self._value

    def __hash__(self) -> int:
        return hash(self._value)


_REQUIRED = object()


def setting(
    *names: str,
    default: Any = _REQUIRED,
    ge: float | None = None,
    le: float | None = None,
) -> Any:
    """A field bound to the variables `names` (the first one set wins).

    No `default` means the variable is required (a secret never has one).
    """
    meta = {"env": names, "required": default is _REQUIRED, "ge": ge, "le": le}
    return field(
        default=None if default is _REQUIRED else default, metadata=meta
    )


def _decode(type_: type, value: Any) -> Any:
    if type_ is Secret:
        return Secret(value)
    raise NotImplementedError(type_.__name__)


def _from_file(name: str, source: Mapping[str, str]) -> str | None:
    path = source.get(f"{name}_FILE")
    if not path:
        return None
    return Path(path).read_text(encoding="utf-8").strip()


class EnvSettings:
    """Loads its dataclass fields from `os.environ` (or `environ`)."""

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        source = os.environ if environ is None else environ
        hints = get_type_hints(type(self), localns={"Secret": Secret})
        problems: list[str] = []
        for f in fields(self):  # type: ignore[arg-type]
            value = self._read(f, hints[f.name], source, problems)
            object.__setattr__(self, f.name, value)
        for cls in type(self).__mro__:
            check = cls.__dict__.get("check")
            if check is not None and not problems:
                problems += check(self)
        if problems:
            raise SettingsError("; ".join(problems))

    @staticmethod
    def _read(f, hint, source, problems: list[str]) -> Any:
        names = f.metadata["env"]
        raw = next((source[n] for n in names if source.get(n)), None)
        if raw is None and hint is Secret:
            raw = next((_from_file(n, source) for n in names), None)
        if raw is None:
            if f.metadata["required"]:
                problems.append(f"{names[0]} is required")
            return f.default
        try:
            value = msgspec.convert(raw, hint, strict=False, dec_hook=_decode)
        except (msgspec.ValidationError, ValueError):
            problems.append(f"{names[0]} is invalid")
            return f.default
        low, high = f.metadata["ge"], f.metadata["le"]
        if (low is not None and value < low) or (
            high is not None and value > high
        ):
            problems.append(f"{names[0]} is out of range")
        return value

    def __repr__(self) -> str:
        shown = ", ".join(
            f"{f.name}={getattr(self, f.name)!r}"
            for f in fields(self)  # type: ignore[arg-type]
        )
        return f"{type(self).__name__}({shown})"

"""Deterministic parsing and comparison. Never expose raw values in default results."""

import json
import math
import re
import tomllib
import unicodedata
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Invalid or unsupported configuration."""


SENSITIVE_COMPONENTS = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "authorization",
    "credential",
    "credentials",
}
SENSITIVE_PHRASES = {
    ("api", "key"),
    ("access", "key"),
    ("secret", "key"),
    ("private", "key"),
    ("encryption", "key"),
    ("jwt", "signing", "key"),
    ("database", "url"),
    ("db", "url"),
    ("connection", "string"),
    ("client", "credentials"),
}
REDACTED = "[REDACTED]"
MISSING = object()
NATIVE_TAG_KEY = "$cfglens-native"
MAX_NESTING_DEPTH = 128


class _NormalizedDict(dict):
    """JSON-safe tagged value used to preserve non-JSON native types."""

    def __init__(self, kind: str, value: Any):
        self.kind = kind
        super().__init__({NATIVE_TAG_KEY: [kind, value]})


def _tagged(kind: str, value: Any) -> _NormalizedDict:
    return _NormalizedDict(kind, value)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False)


def _normalize(value: Any, depth: int = 0) -> Any:
    """Convert parser values to deterministic JSON-safe canonical values."""
    if depth > MAX_NESTING_DEPTH:
        raise ConfigError(f"Maximum configuration nesting depth is {MAX_NESTING_DEPTH}")
    if isinstance(value, _NormalizedDict):
        return value
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ConfigError("Non-finite numbers are not supported")
        return value
    if isinstance(value, datetime):
        if value.tzinfo is not None and value.utcoffset() is not None:
            value = value.astimezone(UTC)
        return _tagged("datetime", value.isoformat())
    if isinstance(value, date):
        return _tagged("date", value.isoformat())
    if isinstance(value, time):
        return _tagged("time", value.isoformat())
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ConfigError("Object mapping keys must be strings")
        normalized = {key: _normalize(item, depth + 1) for key, item in value.items()}
        if NATIVE_TAG_KEY in normalized:
            pairs = [[key, normalized[key]] for key in sorted(normalized)]
            return _tagged("object", pairs)
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, list):
        return [_normalize(item, depth + 1) for item in value]
    if isinstance(value, (set, frozenset)):
        members = [_normalize(item, depth + 1) for item in value]
        members.sort(key=_canonical_json)
        return _tagged("set", members)
    raise ConfigError(
        "Unsupported value type; use strings, numbers, booleans, null, arrays, objects, dates, datetimes, times, or sets"
    )


def _sensitive_key(key: Any) -> bool:
    text = str(key)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    components = tuple(re.findall(r"[a-z0-9]+", text.lower()))
    if SENSITIVE_COMPONENTS.intersection(components):
        return True
    return any(
        components[index : index + len(phrase)] == phrase
        for phrase in SENSITIVE_PHRASES
        for index in range(len(components) - len(phrase) + 1)
    )


def _terminal_safe_text(text: str) -> str:
    """Make terminal control and formatting characters visible."""
    escaped = []
    for character in text:
        category = unicodedata.category(character)
        if category in {"Cc", "Cf", "Cs", "Zl", "Zp"}:
            codepoint = ord(character)
            if codepoint <= 0xFF:
                escaped.append(f"\\x{codepoint:02x}")
            elif codepoint <= 0xFFFF:
                escaped.append(f"\\u{codepoint:04x}")
            else:
                escaped.append(f"\\U{codepoint:08x}")
        else:
            escaped.append(character)
    return "".join(escaped)


def _error_location(exc: Exception) -> str:
    mark = getattr(exc, "problem_mark", None)
    line = getattr(mark, "line", None)
    column = getattr(mark, "column", None)
    if line is not None and column is not None:
        return f" at line {line + 1}, column {column + 1}"
    line = getattr(exc, "lineno", None)
    column = getattr(exc, "colno", None)
    if line is not None and column is not None:
        return f" at line {line}, column {column}"
    match = re.search(r"\bat line (\d+), column (\d+)\b", str(exc))
    if match:
        return f" at line {match.group(1)}, column {match.group(2)}"
    return ""


def _safe_yaml(text: str) -> Any:
    class Loader(yaml.SafeLoader):
        pass

    def mapping(loader, node):
        pairs = loader.construct_pairs(node, deep=True)
        keys = []
        for key, _ in pairs:
            if any(key == previous for previous in keys):
                raise ConfigError("Duplicate YAML mapping key")
            keys.append(key)
        if any(not isinstance(key, str) for key in keys):
            raise ConfigError("YAML mapping keys must be strings")
        out = {}
        for key, value in pairs:
            out[key] = value
        return out

    def yaml_set(loader, node):
        pairs = loader.construct_pairs(node, deep=True)
        members = [key for key, _ in pairs]
        for index, member in enumerate(members):
            if any(member == previous for previous in members[:index]):
                raise ConfigError("Duplicate YAML set member")
        try:
            return set(members)
        except TypeError:
            raise ConfigError("Unsupported YAML set member") from None

    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    Loader.add_constructor("tag:yaml.org,2002:set", yaml_set)
    return yaml.load(text, Loader=Loader)


def _env(text: str) -> dict[str, str]:
    result = {}
    for line_no, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ConfigError(f"Invalid .env entry on line {line_no}")
        key, value = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or key in result:
            raise ConfigError(f"Invalid or duplicate .env key on line {line_no}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        result[key] = value
    return result


def load_config(path: str | Path, fmt: str | None = None) -> Any:
    path = Path(path)
    ext = path.suffix.lower()
    fmt = fmt or (
        {
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".env": "env",
        }.get(ext)
        or ("env" if path.name.startswith(".env") else None)
    )
    if fmt not in ("json", "yaml", "toml", "env"):
        raise ConfigError("Unknown format; use --format")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        filename = _terminal_safe_text(path.name)
        raise ConfigError(f"Could not read {filename} ({type(exc).__name__})") from None

    try:
        if fmt == "json":

            def unique(pairs):
                d = {}
                for k, v in pairs:
                    if k in d:
                        raise ConfigError("Duplicate JSON key")
                    d[k] = v
                return d

            data = json.loads(
                text,
                object_pairs_hook=unique,
                parse_constant=lambda x: (_ for _ in ()).throw(
                    ConfigError("Non-finite JSON number")
                ),
            )
        elif fmt == "yaml":
            data = _safe_yaml(text)
        elif fmt == "toml":
            data = tomllib.loads(text)
        else:
            data = _env(text)
        return _normalize(data)
    except ConfigError as exc:
        filename = _terminal_safe_text(path.name)
        detail = _terminal_safe_text(str(exc))
        raise ConfigError(f"Invalid {fmt.upper()} in {filename}: {detail}") from None
    except RecursionError:
        filename = _terminal_safe_text(path.name)
        raise ConfigError(
            f"Invalid {fmt.upper()} in {filename}: maximum nesting depth exceeded"
        ) from None
    except (ValueError, yaml.YAMLError) as exc:
        filename = _terminal_safe_text(path.name)
        location = _error_location(exc)
        raise ConfigError(f"Invalid {fmt.upper()} in {filename}{location}") from None


def _typename(value: Any) -> str:
    if value is MISSING:
        return "missing"
    if isinstance(value, _NormalizedDict):
        return "object" if value.kind == "object" else value.kind
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return type(value).__name__


def _display(value: Any, sensitive: bool, show_values: bool) -> Any:
    if value is MISSING:
        return None
    if sensitive and not show_values:
        return REDACTED
    if isinstance(value, _NormalizedDict):
        if value.kind == "object":
            pairs = value[NATIVE_TAG_KEY][1]
            return {
                NATIVE_TAG_KEY: [
                    "object",
                    [
                        [
                            key,
                            _display(
                                item,
                                sensitive or _sensitive_key(key),
                                show_values,
                            ),
                        ]
                        for key, item in pairs
                    ],
                ]
            }
        return dict(value)
    if isinstance(value, dict):
        return {
            str(k): _display(v, sensitive or _sensitive_key(k), show_values)
            for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
        }
    if isinstance(value, list):
        return [_display(v, sensitive, show_values) for v in value]
    return value


def compare(
    before: Any, after: Any, *, show_values: bool = False
) -> list[dict[str, Any]]:
    """Return deterministic JSON-safe changes; show_values=True is explicitly unsafe."""
    before = _normalize(before)
    after = _normalize(after)
    changes = []

    def walk(a, b, path, sensitive):
        if (
            a is not MISSING
            and b is not MISSING
            and type(a) is type(b)
            and isinstance(a, dict)
            and not isinstance(a, _NormalizedDict)
        ):
            for key in sorted(a.keys() | b.keys(), key=str):
                name = str(key).replace("~", "~0").replace("/", "~1")
                walk(
                    a.get(key, MISSING),
                    b.get(key, MISSING),
                    path + "/" + name,
                    sensitive or _sensitive_key(key),
                )
            return
        if (
            a is not MISSING
            and b is not MISSING
            and type(a) is type(b)
            and isinstance(a, list)
        ):
            for i in range(max(len(a), len(b))):
                walk(
                    a[i] if i < len(a) else MISSING,
                    b[i] if i < len(b) else MISSING,
                    path + "/" + str(i),
                    sensitive,
                )
            return
        if a is not MISSING and b is not MISSING and type(a) is type(b) and a == b:
            return
        kind = (
            "added"
            if a is MISSING
            else (
                "removed"
                if b is MISSING
                else "type_changed" if _typename(a) != _typename(b) else "modified"
            )
        )
        changes.append(
            {
                "path": path or "/",
                "change": kind,
                "before_type": _typename(a),
                "after_type": _typename(b),
                "before": _display(a, sensitive, show_values),
                "after": _display(b, sensitive, show_values),
            }
        )

    walk(before, after, "", False)
    return changes

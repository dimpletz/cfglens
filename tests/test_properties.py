"""Bounded deterministic property checks for canonical values."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings
from hypothesis import strategies as st

from cfglens.core import ConfigError, compare, load_config

SCALAR = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(10**30), max_value=10**30),
    st.floats(allow_nan=False, allow_infinity=False, width=64),
    st.text(max_size=24),
)
JSON_VALUE = st.recursive(
    SCALAR,
    lambda children: st.one_of(
        st.lists(children, max_size=6),
        st.dictionaries(st.text(max_size=12), children, max_size=6),
    ),
    max_leaves=24,
)
PROPERTY_SETTINGS = settings(max_examples=60, derandomize=True, deadline=None)


@PROPERTY_SETTINGS
@given(JSON_VALUE)
def test_identity_and_repeated_comparison_are_invariant(value):
    first = compare(value, value)
    second = compare(value, value)
    assert first == second == []


@PROPERTY_SETTINGS
@given(JSON_VALUE, JSON_VALUE)
def test_comparison_is_deterministic_and_strict_json_serializable(before, after):
    first = compare(before, after)
    second = compare(before, after)
    assert first == second
    serialized = json.dumps(first, ensure_ascii=True, allow_nan=False)
    assert (
        json.loads(
            serialized,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
        == first
    )


@PROPERTY_SETTINGS
@given(JSON_VALUE)
def test_normalized_json_files_are_repeatable_and_json_compatible(value):
    with TemporaryDirectory() as directory:
        config = Path(directory) / "generated.json"
        config.write_text(json.dumps(value, ensure_ascii=True, allow_nan=False))
        first = load_config(config)
        second = load_config(config)
        assert first == second
        json.dumps(first, ensure_ascii=True, allow_nan=False)
        assert compare(first, first) == []


@PROPERTY_SETTINGS
@given(st.dictionaries(st.text(max_size=12), SCALAR, max_size=8))
def test_reserved_tag_collision_preserves_all_generated_pairs(values):
    values["$cfglens-native"] = "synthetic user value"
    with TemporaryDirectory() as directory:
        config = Path(directory) / "reserved.json"
        config.write_text(json.dumps(values, ensure_ascii=True, allow_nan=False))

        normalized = load_config(config)
        tag = normalized["$cfglens-native"]
        assert tag[0] == "object"
        assert dict(tag[1]) == {key: values[key] for key in sorted(values)}
        assert compare(normalized, normalized) == []
        json.dumps(normalized, ensure_ascii=True, allow_nan=False)


@PROPERTY_SETTINGS
@given(
    st.text(
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",
        max_size=48,
    )
)
def test_malformed_yaml_never_echoes_generated_secret_content(suffix):
    secret = f"SYNTHETIC_{suffix}"
    with TemporaryDirectory() as directory:
        config = Path(directory) / "malformed.yaml"
        config.write_text(f"password: [{secret}\n")

        try:
            load_config(config)
        except ConfigError as error:
            assert secret not in str(error)
            assert "password:" not in str(error)
            assert error.__cause__ is None
        else:
            raise AssertionError("Unclosed YAML sequence unexpectedly parsed")

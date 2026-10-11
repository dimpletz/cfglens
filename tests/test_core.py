import inspect
import json
import sys
from types import ModuleType

import pytest

from cfglens.cli import main
from cfglens.core import ConfigError, compare, load_config


def test_changes_and_redaction():
    a = {
        "password": "old",
        "nested": {"api_key": "a", "enabled": True},
        "items": [1, 2],
        "gone": 1,
    }
    b = {
        "password": "new",
        "nested": {"api_key": "b", "enabled": "true"},
        "items": [1, 3, 4],
        "added": None,
    }
    changes = compare(a, b)
    assert {x["change"] for x in changes} == {
        "added",
        "removed",
        "modified",
        "type_changed",
    }
    assert (
        next(x for x in changes if x["path"] == "/password")["before"] == "[REDACTED]"
    )
    assert (
        next(x for x in changes if x["path"] == "/nested/api_key")["after"]
        == "[REDACTED]"
    )
    assert (
        next(x for x in changes if x["path"] == "/password")["after_type"] == "string"
    )
    assert compare(a, a) == []
    assert (
        next(x for x in compare(a, b, show_values=True) if x["path"] == "/password")[
            "before"
        ]
        == "old"
    )


def test_formats(tmp_path):
    cases = {
        "json": ("a.json", '{"x": 1}'),
        "yaml": ("a.yaml", "x: 1"),
        "toml": ("a.toml", "x = 1"),
        "env": (".env", "x=1"),
    }
    for name, (filename, content) in cases.items():
        p = tmp_path / filename
        p.write_text(content)
        assert load_config(p)["x"] == ("1" if name == "env" else 1)


def test_invalid_and_duplicate(tmp_path):
    for filename, content in [
        ("a.json", '{"x":1,"x":2}'),
        ("a.yaml", "x: 1\nx: 2".replace("\n", "\n")),
        (".env", "A=1\nA=2".replace("\n", "\n")),
    ]:
        p = tmp_path / filename
        p.write_text(content)
        with pytest.raises(ConfigError):
            load_config(p)


def test_cli(tmp_path, capsys):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps({"token": "hello"}))
    b.write_text(json.dumps({"token": "world"}))
    assert main([str(a), str(b), "--output", "json"]) == 1
    output = capsys.readouterr().out
    assert "hello" not in output and "world" not in output
    assert json.loads(output)["count"] == 1
    assert main([str(a), str(a)]) == 0


def test_pointer_escape_and_types():
    assert compare({"a/b": 1}, {"a/b": 2})[0]["path"] == "/a~1b"
    assert compare({"x": True}, {"x": 1})[0]["change"] == "type_changed"


@pytest.mark.parametrize(
    "key",
    [
        "PASSWORD",
        "passwd",
        "Pwd",
        "clientSecret",
        "ACCESS_TOKEN",
        "refreshToken",
        "apiKey",
        "AccessKey",
        "secret-key",
        "privateKey",
        "encryptionKey",
        "JWT_SECRET",
        "JWTSigningKey",
        "databaseUrl",
        "DB_URL",
        "connectionString",
        "authToken",
        "AUTHORIZATION",
        "clientCredentials",
        "service.credentials.value",
    ],
)
def test_sensitive_key_variants_are_redacted_in_cli(tmp_path, capsys, key):
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(json.dumps({key: "SYNTHETIC_SECRET_BEFORE"}))
    after.write_text(json.dumps({key: "SYNTHETIC_SECRET_AFTER"}))

    assert main([str(before), str(after), "--output", "json"]) == 1
    json_output = capsys.readouterr().out
    assert "SYNTHETIC_SECRET_BEFORE" not in json_output
    assert "SYNTHETIC_SECRET_AFTER" not in json_output
    assert "[REDACTED]" in json_output

    assert main([str(before), str(after)]) == 1
    human_output = capsys.readouterr().out
    assert "SYNTHETIC_SECRET_BEFORE" not in human_output
    assert "SYNTHETIC_SECRET_AFTER" not in human_output
    assert "[REDACTED]" in human_output


def test_sensitive_values_redacted_for_every_change_kind(tmp_path, capsys):
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(
        json.dumps(
            {
                "removedPassword": "SYNTHETIC_REMOVED",
                "refreshToken": "SYNTHETIC_OLD_TOKEN",
                "privateKey": "SYNTHETIC_OLD_KEY",
                "credentials": {"nested": {"value": "SYNTHETIC_NESTED_OLD"}},
            }
        )
    )
    after.write_text(
        json.dumps(
            {
                "clientSecret": "SYNTHETIC_ADDED",
                "refreshToken": "SYNTHETIC_NEW_TOKEN",
                "privateKey": {"part": "SYNTHETIC_NEW_KEY"},
                "credentials": {"nested": {"value": "SYNTHETIC_NESTED_NEW"}},
            }
        )
    )

    assert main([str(before), str(after), "--output", "json"]) == 1
    output = capsys.readouterr().out
    result = json.loads(output)
    assert {item["change"] for item in result["changes"]} == {
        "added",
        "removed",
        "modified",
        "type_changed",
    }
    assert all(
        {"before_type", "after_type"}.issubset(item) for item in result["changes"]
    )
    assert "SYNTHETIC_" not in output
    assert "[REDACTED]" in output


def test_ordinary_key_components_are_not_over_redacted(tmp_path, capsys):
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(json.dumps({"tokenizer": "old", "secretary": "old"}))
    after.write_text(json.dumps({"tokenizer": "new", "secretary": "new"}))

    assert main([str(before), str(after), "--output", "json"]) == 1
    output = capsys.readouterr().out
    assert '"before": "old"' in output
    assert '"after": "new"' in output


def test_cli_show_values_is_explicitly_unsafe(tmp_path, capsys):
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(json.dumps({"password": "SYNTHETIC_REVEAL_BEFORE"}))
    after.write_text(json.dumps({"password": "SYNTHETIC_REVEAL_AFTER"}))

    assert main([str(before), str(after), "--output", "json", "--show-values"]) == 1
    output = capsys.readouterr().out
    assert "SYNTHETIC_REVEAL_BEFORE" in output
    assert "SYNTHETIC_REVEAL_AFTER" in output


@pytest.mark.parametrize(
    ("filename", "fmt", "source", "secret"),
    [
        (
            "broken.json",
            "json",
            '{"password": "SYNTHETIC_JSON_SECRET",\n',
            "SYNTHETIC_JSON_SECRET",
        ),
        (
            "broken.yaml",
            "yaml",
            "password: [SYNTHETIC_YAML_SECRET\n",
            "SYNTHETIC_YAML_SECRET",
        ),
        (
            "broken.toml",
            "toml",
            'password = "SYNTHETIC_TOML_SECRET\n',
            "SYNTHETIC_TOML_SECRET",
        ),
        (
            ".env.broken",
            "env",
            "SYNTHETIC_ENV_SECRET_VALUE\n",
            "SYNTHETIC_ENV_SECRET_VALUE",
        ),
    ],
)
def test_parser_errors_do_not_expose_source_content(
    tmp_path, capsys, filename, fmt, source, secret
):
    config = tmp_path / filename
    config.write_text(source)

    assert main([str(config), str(config), "--format", fmt]) == 2
    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in captured.err
    assert f"Invalid {fmt.upper()}" in captured.err
    assert "line" in captured.err

    with pytest.raises(ConfigError) as error:
        load_config(config, fmt)
    assert secret not in str(error.value)
    assert error.value.__cause__ is None


def test_error_filename_is_safe_for_terminal(tmp_path, capsys):
    unsafe_name = "missing\x1b[2J\nfile.json"
    assert main([str(tmp_path / unsafe_name), "other.json"]) == 2
    error = capsys.readouterr().err
    assert "\x1b" not in error
    assert "\nfile" not in error
    assert r"\x1b[2J\x0afile.json" in error


def test_config_key_controls_are_safe_in_human_and_json_output(tmp_path, capsys):
    unsafe_key = "odd\x1b[2J\nforged\u2028last"
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(json.dumps({unsafe_key: "old"}))
    after.write_text(json.dumps({unsafe_key: "new"}))

    assert main([str(before), str(after)]) == 1
    human_output = capsys.readouterr().out
    assert "\x1b" not in human_output
    assert "\nforged" not in human_output
    assert r"\x1b[2J\x0aforged\u2028last" in human_output
    assert human_output.count("\n") == 3

    assert main([str(before), str(after), "--output", "json"]) == 1
    json_output = capsys.readouterr().out
    result = json.loads(json_output)
    assert "\x1b" not in json_output
    assert result["changes"][0]["path"] == "/odd\x1b[2J\nforged\u2028last"


def test_cli_json_rejects_nonstandard_serialization_safely(tmp_path, capsys):
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text('{"value": 1e999}')
    after.write_text("{}")

    assert main([str(before), str(after), "--output", "json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Non-finite numbers are not supported" in captured.err
    assert "Infinity" not in captured.err


def test_native_yaml_and_toml_values_have_canonical_json_tags(tmp_path):
    yaml_path = tmp_path / "values.yaml"
    toml_path = tmp_path / "values.toml"
    yaml_path.write_text(
        "date: 2024-01-02\n"
        "datetime: 2024-01-02T03:04:05Z\n"
        "set: !!set {beta: null, alpha: null}\n"
    )
    toml_path.write_text(
        "date = 2024-01-02\n"
        "datetime = 2024-01-02T03:04:05Z\n"
        "naive_datetime = 2024-01-02T03:04:05\n"
        "time = 03:04:05\n"
    )

    yaml_values = load_config(yaml_path)
    toml_values = load_config(toml_path)
    assert json.loads(json.dumps(yaml_values, allow_nan=False)) == yaml_values
    assert yaml_values["date"]["$cfglens-native"] == ["date", "2024-01-02"]
    assert yaml_values["datetime"]["$cfglens-native"] == [
        "datetime",
        "2024-01-02T03:04:05+00:00",
    ]
    assert yaml_values["set"]["$cfglens-native"] == ["set", ["alpha", "beta"]]
    assert toml_values["time"]["$cfglens-native"] == ["time", "03:04:05"]
    assert toml_values["naive_datetime"]["$cfglens-native"] == [
        "datetime",
        "2024-01-02T03:04:05",
    ]
    assert compare(yaml_values, toml_values) == [
        {
            "path": "/naive_datetime",
            "change": "added",
            "before_type": "missing",
            "after_type": "datetime",
            "before": None,
            "after": {
                "$cfglens-native": ["datetime", "2024-01-02T03:04:05"]
            },
        },
        {
            "path": "/set",
            "change": "removed",
            "before_type": "set",
            "after_type": "missing",
            "before": {"$cfglens-native": ["set", ["alpha", "beta"]]},
            "after": None,
        },
        {
            "path": "/time",
            "change": "added",
            "before_type": "missing",
            "after_type": "time",
            "before": None,
            "after": {"$cfglens-native": ["time", "03:04:05"]},
        },
    ]


def test_same_date_and_datetime_normalize_across_yaml_and_toml(tmp_path):
    yaml_path = tmp_path / "values.yaml"
    toml_path = tmp_path / "values.toml"
    yaml_path.write_text("date: 2024-01-02\n" "datetime: 2024-01-02T05:04:05+02:00\n")
    toml_path.write_text("date = 2024-01-02\n" "datetime = 2024-01-02T03:04:05Z\n")

    assert compare(load_config(yaml_path), load_config(toml_path)) == []


@pytest.mark.parametrize(
    ("filename", "fmt", "source"),
    [
        ("nan.json", "json", '{"nested": [NaN]}'),
        ("positive-infinity.json", "json", '{"nested": [Infinity]}'),
        ("infinity.json", "json", '{"nested": [-Infinity]}'),
        ("overflow.json", "json", '{"nested": [1e999]}'),
        ("nonfinite.yaml", "yaml", "nested: [.nan, .inf, -.inf]"),
        ("nonfinite.toml", "toml", "nested = [nan, inf, -inf, 1e999]"),
    ],
)
def test_non_finite_numbers_are_rejected_recursively(tmp_path, filename, fmt, source):
    config = tmp_path / filename
    config.write_text(source)
    with pytest.raises(ConfigError, match="Non-finite"):
        load_config(config, fmt)


def test_yaml_unsupported_native_value_is_rejected_safely(tmp_path):
    config = tmp_path / "binary.yaml"
    config.write_text("payload: !!binary c3ludGhldGlj\n")

    with pytest.raises(ConfigError, match="Unsupported value type") as error:
        load_config(config)
    assert "synthetic" not in str(error.value)


@pytest.mark.parametrize(
    "source",
    [
        "1: integer key\n",
        "true: boolean key\n",
        "outer:\n  1: nested integer key\n",
        "true: boolean key\n1: integer key\n",
        "name: first\nname: second\n",
    ],
)
def test_yaml_non_string_and_duplicate_mapping_keys_are_rejected(tmp_path, source):
    config = tmp_path / "keys.yaml"
    config.write_text(source)

    with pytest.raises(ConfigError) as error:
        load_config(config)
    assert "YAML" in str(error.value)
    assert "integer key" not in str(error.value)
    assert "boolean key" not in str(error.value)


def test_yaml_equal_mixed_type_keys_are_reported_as_duplicates(tmp_path):
    config = tmp_path / "equal-keys.yaml"
    config.write_text("true: first\n1: second\n")

    with pytest.raises(ConfigError, match="Duplicate YAML mapping key"):
        load_config(config)


def test_yaml_set_duplicate_members_that_compare_equal_are_rejected(tmp_path):
    config = tmp_path / "duplicate-set.yaml"
    config.write_text("!!set {true: null, 1: null}\n")

    with pytest.raises(ConfigError, match="Duplicate YAML set member"):
        load_config(config)


def test_yaml_set_with_unhashable_member_is_rejected_without_echo(tmp_path):
    config = tmp_path / "unhashable-set.yaml"
    config.write_text("!!set\n? [SYNTHETIC_UNHASHABLE_MEMBER]\n: null\n")

    with pytest.raises(ConfigError, match="Unsupported YAML set member") as error:
        load_config(config)
    assert "SYNTHETIC_UNHASHABLE_MEMBER" not in str(error.value)
    assert error.value.__cause__ is None


def test_duplicate_json_keys_are_rejected_without_source_echo(tmp_path, capsys):
    config = tmp_path / "duplicate.json"
    config.write_text(
        '{"password":"SYNTHETIC_DUPLICATE_SECRET",'
        '"password":"SYNTHETIC_OTHER_SECRET"}'
    )

    assert main([str(config), str(config)]) == 2
    output = capsys.readouterr()
    assert "SYNTHETIC_" not in output.err
    assert "Duplicate JSON key" in output.err


def test_reserved_native_tag_mapping_is_escaped_without_collision(tmp_path):
    config = tmp_path / "tag.json"
    config.write_text('{"$cfglens-native":["date","2024-01-02"]}')

    value = load_config(config)
    serialized = json.loads(json.dumps(value, allow_nan=False))
    assert serialized["$cfglens-native"][0] == "object"
    assert compare(value, {"$cfglens-native": ["date", "2024-01-02"]}) == []


def test_redaction_survives_reserved_native_tag_escaping(tmp_path, capsys):
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(
        '{"$cfglens-native":["custom"],"password":"SYNTHETIC_ESCAPED_SECRET_BEFORE"}'
    )
    after.write_text(
        '{"$cfglens-native":["custom"],"password":"SYNTHETIC_ESCAPED_SECRET_AFTER"}'
    )

    assert main([str(before), str(after), "--output", "json"]) == 1
    output = capsys.readouterr().out
    assert "SYNTHETIC_ESCAPED_SECRET" not in output
    assert "[REDACTED]" in output


def test_nested_reserved_native_tag_escaping_preserves_redaction(tmp_path, capsys):
    before = tmp_path / "nested-before.json"
    after = tmp_path / "nested-after.json"
    before.write_text(
        '{"outer":{"$cfglens-native":["custom"],'
        '"password":"SYNTHETIC_NESTED_RESERVED_BEFORE"}}'
    )
    after.write_text(
        '{"outer":{"$cfglens-native":["custom"],'
        '"password":"SYNTHETIC_NESTED_RESERVED_AFTER"}}'
    )

    assert main([str(before), str(after), "--output", "json"]) == 1
    output = capsys.readouterr().out
    assert "SYNTHETIC_NESTED_RESERVED" not in output
    assert "[REDACTED]" in output


def test_null_missing_boolean_integer_and_float_semantics():
    null_added = compare({}, {"value": None})[0]
    assert null_added["change"] == "added"
    assert null_added["before_type"] == "missing"
    assert null_added["after_type"] == "null"
    assert compare({"value": None}, {"value": False})[0]["change"] == "type_changed"
    assert compare({"value": False}, {"value": 0})[0]["change"] == "type_changed"
    assert compare({"value": 1}, {"value": 1.0})[0]["change"] == "type_changed"
    assert compare({"value": 1.0}, {"value": 1.0}) == []
    assert compare({"value": -0.0}, {"value": 0.0}) == []
    assert compare({"value": ""}, {"value": None})[0]["change"] == "type_changed"


def test_unsupported_direct_values_fail_without_stringification():
    class Unsupported:
        def __str__(self):
            return "SYNTHETIC_UNSUPPORTED_SECRET"

    with pytest.raises(ConfigError, match="Unsupported value type") as error:
        compare(Unsupported(), None)
    assert "SYNTHETIC_UNSUPPORTED_SECRET" not in str(error.value)


def test_cli_json_is_strict_and_redacts_after_native_normalization(tmp_path, capsys):
    before = tmp_path / "before.yaml"
    after = tmp_path / "after.yaml"
    before.write_text("databaseUrl: 2024-01-02\n")
    after.write_text("databaseUrl: 2024-01-03\n")

    assert main([str(before), str(after), "--output", "json"]) == 1
    output = capsys.readouterr().out

    def reject_nonfinite(value):
        raise AssertionError(f"non-standard JSON number: {value}")

    result = json.loads(output, parse_constant=reject_nonfinite)
    change = result["changes"][0]
    assert change["before_type"] == "date"
    assert change["after_type"] == "date"
    assert change["before"] == "[REDACTED]"
    assert change["after"] == "[REDACTED]"
    assert "2024-01-0" not in output


def test_list_comparison_is_index_based_and_change_order_is_deterministic():
    before = {"z": ["a", "b"], "a": {"right": 1, "left": 2}}
    after = {"z": ["x", "a", "b"], "a": {"right": 3, "left": 4}}
    first = compare(before, after)
    second = compare(before, after)

    assert first == second
    assert [change["path"] for change in first] == [
        "/a/left",
        "/a/right",
        "/z/0",
        "/z/1",
        "/z/2",
    ]
    assert [change["change"] for change in first[-3:]] == [
        "modified",
        "modified",
        "added",
    ]


def test_json_pointer_escaping_preserves_string_mapping_keys():
    result = compare({"~": 1, "/": 2}, {"~": 3, "/": 4})
    assert [change["path"] for change in result] == ["/~1", "/~0"]


def test_mcp_adapter_always_redacts_and_has_no_reveal_parameter(tmp_path, monkeypatch):
    from cfglens import mcp_server

    registered_tools = []

    class FakeFastMCP:
        def __init__(self, name):
            assert name == "CfgLens"

        def tool(self):
            def register(function):
                registered_tools.append(function)
                return function

            return register

        def run(self, transport):
            assert transport == "stdio"

    mcp_module = ModuleType("mcp")
    server_module = ModuleType("mcp.server")
    fastmcp_module = ModuleType("mcp.server.fastmcp")
    fastmcp_module.FastMCP = FakeFastMCP
    monkeypatch.setitem(sys.modules, "mcp", mcp_module)
    monkeypatch.setitem(sys.modules, "mcp.server", server_module)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_module)

    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(json.dumps({"clientSecret": "SYNTHETIC_MCP_BEFORE"}))
    after.write_text(json.dumps({"clientSecret": "SYNTHETIC_MCP_AFTER"}))

    mcp_server.main()
    tool = registered_tools[0]
    assert "show_values" not in inspect.signature(tool).parameters
    result = tool(str(before), str(after))
    serialized = json.dumps(result, allow_nan=False)
    assert "SYNTHETIC_MCP_BEFORE" not in serialized
    assert "SYNTHETIC_MCP_AFTER" not in serialized
    assert "[REDACTED]" in serialized

    native_before = tmp_path / "native-before.yaml"
    native_after = tmp_path / "native-after.yaml"
    native_before.write_text("databaseUrl: 2024-01-02\n")
    native_after.write_text("databaseUrl: 2024-01-03\n")
    native_result = tool(str(native_before), str(native_after))
    native_serialized = json.dumps(native_result, allow_nan=False)
    assert "2024-01-0" not in native_serialized
    assert native_result["changes"][0]["before_type"] == "date"

    malformed = tmp_path / "malformed.yaml"
    malformed.write_text("password: [SYNTHETIC_MCP_ERROR_SECRET\n")
    with pytest.raises(ConfigError) as error:
        tool(str(malformed), str(after), "yaml")
    assert "SYNTHETIC_MCP_ERROR_SECRET" not in str(error.value)
    assert "Invalid YAML" in str(error.value)

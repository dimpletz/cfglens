"""Public CLI checks across formats and common input boundaries."""

import json

import pytest

from cfglens.cli import main

FORMAT_CASES = [
    (
        "json",
        "json",
        (
            '{"app":{"kind":"false","modified":1,"removed":"old",'
            '"nested":{"value":"before"},"items":[{"value":1},{"value":2}]}}'
        ),
        (
            '{"app":{"kind":false,"modified":2,"added":null,'
            '"nested":{"value":"after"},"items":[{"value":1},{"value":3}]}}'
        ),
        {"added", "removed", "modified", "type_changed"},
    ),
    (
        "yaml",
        "yaml",
        (
            'app:\n  kind: "false"\n  modified: 1\n  removed: old\n'
            "  nested: {value: before}\n  items: [{value: 1}, {value: 2}]\n"
        ),
        (
            "app:\n  kind: false\n  modified: 2\n  added: null\n"
            "  nested: {value: after}\n  items: [{value: 1}, {value: 3}]\n"
        ),
        {"added", "removed", "modified", "type_changed"},
    ),
    (
        "toml",
        "toml",
        (
            '[app]\nkind = "false"\nmodified = 1\nremoved = "old"\n'
            'nested = { value = "before" }\nitems = [{ value = 1 }, { value = 2 }]\n'
        ),
        (
            '[app]\nkind = false\nmodified = 2\nadded = "new"\n'
            'nested = { value = "after" }\nitems = [{ value = 1 }, { value = 3 }]\n'
        ),
        {"added", "removed", "modified", "type_changed"},
    ),
    (
        "env",
        "env",
        "APP_KIND=false\r\nAPP_MODIFIED=before\r\nAPP_REMOVED=old\r\n",
        "APP_KIND=true\nAPP_MODIFIED=after\nAPP_ADDED=new\n",
        {"added", "removed", "modified"},
    ),
]


@pytest.mark.parametrize("fmt,extension,before_text,after_text,kinds", FORMAT_CASES)
def test_cli_reports_changes_for_each_format(
    tmp_path, capsys, fmt, extension, before_text, after_text, kinds
):
    before = tmp_path / f"before.{extension}"
    after = tmp_path / f"after.{extension}"
    before.write_text(before_text, encoding="utf-8")
    after.write_text(after_text, encoding="utf-8")

    assert main([str(before), str(after), "--format", fmt, "--output", "json"]) == 1
    output = capsys.readouterr().out

    def reject_constant(value):
        raise AssertionError(f"non-finite JSON constant: {value}")

    result = json.loads(output, parse_constant=reject_constant)
    assert {change["change"] for change in result["changes"]} == kinds
    if fmt != "env":
        assert any(
            change["path"].startswith("/app/nested") for change in result["changes"]
        )
        assert any(
            change["path"].startswith("/app/items/") for change in result["changes"]
        )

    before.write_text(before_text, encoding="utf-8")
    after.write_text(before_text, encoding="utf-8")
    assert main([str(before), str(after), "--format", fmt]) == 0
    assert "No changes" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("filename", "fmt", "content"),
    [
        ("empty.yaml", "yaml", ""),
        ("empty.toml", "toml", ""),
        ("empty.env", "env", ""),
    ],
)
def test_empty_non_json_formats_have_stable_values(tmp_path, filename, fmt, content):
    config = tmp_path / filename
    config.write_text(content, encoding="utf-8")
    assert main([str(config), str(config), "--format", fmt]) == 0


def test_empty_json_is_a_parse_error(tmp_path, capsys):
    empty = tmp_path / "empty.json"
    empty.write_text("", encoding="utf-8")
    assert main([str(empty), str(empty)]) == 2
    assert "Invalid JSON" in capsys.readouterr().err


def test_missing_and_directory_inputs_return_invalid_input_exit_code(tmp_path, capsys):
    missing = tmp_path / "missing.json"
    assert main([str(missing), str(missing)]) == 2
    assert "Could not read" in capsys.readouterr().err

    directory = tmp_path / "config.yaml"
    directory.mkdir()
    assert main([str(directory), str(directory)]) == 2
    assert "Could not read" in capsys.readouterr().err


def test_invalid_utf8_diagnostic_does_not_echo_input(tmp_path, capsys):
    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b'{"password":"SYNTHETIC_INVALID_UTF8_SECRET",\xff}')

    assert main([str(invalid), str(invalid)]) == 2
    error = capsys.readouterr().err
    assert "Could not read" in error
    assert "SYNTHETIC_INVALID_UTF8_SECRET" not in error
    assert "Traceback" not in error


def test_unknown_extension_requires_explicit_format(tmp_path, capsys):
    before = tmp_path / "before.conf"
    after = tmp_path / "after.conf"
    before.write_text('{"value":"same"}', encoding="utf-8")
    after.write_text('{"value":"same"}', encoding="utf-8")

    assert main([str(before), str(after)]) == 2
    assert "Unknown format" in capsys.readouterr().err
    assert main([str(before), str(after), "--format", "json"]) == 0


def test_unicode_keys_and_values_in_structured_formats(tmp_path, capsys):
    cases = [
        ("json", '{"café":"été"}', '{"café":"東京"}'),
        ("yaml", "café: été\n", "café: 東京\n"),
        ("toml", '"café" = "été"\n', '"café" = "東京"\n'),
    ]
    for fmt, before_text, after_text in cases:
        before = tmp_path / f"before.{fmt}"
        after = tmp_path / f"after.{fmt}"
        before.write_text(before_text, encoding="utf-8")
        after.write_text(after_text, encoding="utf-8")
        assert main([str(before), str(after), "--format", fmt]) == 1
        assert "東京" in capsys.readouterr().out


def test_env_unicode_values_and_mixed_line_endings(tmp_path, capsys):
    before = tmp_path / "before.env"
    after = tmp_path / "after.env"
    before.write_text("CITY=古い\r\nNOTE=été\r", encoding="utf-8")
    after.write_text("CITY=新しい\nNOTE=été\n", encoding="utf-8")

    assert main([str(before), str(after), "--format", "env"]) == 1
    output = capsys.readouterr().out
    assert "/CITY" in output
    assert "古い" in output and "新しい" in output


def test_json_cli_argument_errors_use_argparse_exit_two(tmp_path):
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text("{}", encoding="utf-8")
    after.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main([str(before), str(after), "--output", "xml"])
    assert error.value.code == 2
    with pytest.raises(SystemExit) as error:
        main([str(before), str(after), "--format", "ini"])
    assert error.value.code == 2
    with pytest.raises(SystemExit) as error:
        main([str(before), "--help"])
    assert error.value.code == 0


def test_cross_format_string_configuration_compares_equal(tmp_path):
    files = []
    sources = [
        ("values.json", '{"name":"demo","nested":{"key":"value"}}'),
        ("values.yaml", "name: demo\nnested:\n  key: value\n"),
        ("values.toml", 'name = "demo"\n[nested]\nkey = "value"\n'),
        ("values.env", "NAME=demo\nNESTED_KEY=value\n"),
    ]
    for filename, content in sources:
        path = tmp_path / filename
        path.write_text(content, encoding="utf-8")
        files.append(path)

    # The three structured formats share an identical nested string structure.
    assert main([str(files[0]), str(files[1])]) == 0
    assert main([str(files[1]), str(files[2])]) == 0
    # .env is flat, so its supported cross-format equivalence is scalar strings.
    flat_json = tmp_path / "flat.json"
    flat_json.write_text('{"NAME":"demo","NESTED_KEY":"value"}')
    assert main([str(flat_json), str(files[3])]) == 0


def test_large_flat_and_deep_valid_configurations_are_bounded(tmp_path, capsys):
    flat = {f"key-{index:04d}": index for index in range(2000)}
    before = tmp_path / "large-before.json"
    after = tmp_path / "large-after.json"
    before.write_text(json.dumps(flat), encoding="utf-8")
    after.write_text(json.dumps(flat), encoding="utf-8")
    assert main([str(before), str(after)]) == 0
    assert "No changes" in capsys.readouterr().out

    nested = "leaf"
    for _ in range(96):
        nested = [nested]
    before.write_text(json.dumps(nested), encoding="utf-8")
    after.write_text(json.dumps(nested), encoding="utf-8")
    assert main([str(before), str(after)]) == 0
    assert "No changes" in capsys.readouterr().out

    yaml_path = tmp_path / "deep.yaml"
    yaml_lines = ["  " * level + f"level-{level}:" for level in range(96)]
    yaml_lines.append("  " * 96 + "leaf: value")
    yaml_path.write_text("\n".join(yaml_lines), encoding="utf-8")
    assert main([str(yaml_path), str(yaml_path)]) == 0
    assert "No changes" in capsys.readouterr().out


def test_nesting_beyond_documented_limit_is_safely_rejected(tmp_path, capsys):
    nested = "leaf"
    for _ in range(130):
        nested = [nested]
    config = tmp_path / "too-deep.json"
    config.write_text(json.dumps(nested), encoding="utf-8")

    assert main([str(config), str(config)]) == 2
    error = capsys.readouterr().err
    assert "Maximum configuration nesting depth is 128" in error
    assert "Traceback" not in error

    yaml_path = tmp_path / "too-deep.yaml"
    yaml_lines = ["  " * level + f"level-{level}:" for level in range(130)]
    yaml_lines.append("  " * 130 + "leaf: SYNTHETIC_DEEP_VALUE")
    yaml_path.write_text("\n".join(yaml_lines), encoding="utf-8")
    assert main([str(yaml_path), str(yaml_path)]) == 2
    yaml_error = capsys.readouterr().err
    assert "maximum" in yaml_error.lower() or "nesting" in yaml_error.lower()
    assert "SYNTHETIC_DEEP_VALUE" not in yaml_error

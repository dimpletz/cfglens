# CfgLens
**Compare configuration files safely — straight from the terminal or through MCP.**

<p align="center">
	<a href="https://github.com/dimpletz/cfglens/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
	<img src="https://img.shields.io/badge/Python-3.11%2B-blue.svg" alt="Python 3.11 and newer">
	<a href="https://pypi.org/project/cfglens/"><img src="https://img.shields.io/badge/PyPI-cfglens%20(unpublished)-lightgrey.svg" alt="PyPI package cfglens: unpublished"></a>
	<img src="https://img.shields.io/badge/Security-Hardened-brightgreen.svg" alt="Security: Hardened">
</p>

CfgLens compares JSON, YAML, TOML, and `.env` files and reports deterministic changes. A shared Python core powers the command-line interface and optional stdio MCP server. CfgLens requires no AI model, hosted service, or API key.

## Table of Contents

- [Features](#features)
- [Why CfgLens?](#why-cfglens)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [Real-World Example](#real-world-example)
- [MCP Installation and Configuration](#mcp-installation-and-configuration)
- [Supported Configuration Formats](#supported-configuration-formats)
- [Comparison Behavior](#comparison-behavior)
- [Secret Redaction and Security](#secret-redaction-and-security)
- [Exit Codes](#exit-codes)
- [Development and Testing](#development-and-testing)
- [GitHub and PyPI Release Information](#github-and-pypi-release-information)
- [Release Preparation](#release-preparation)
- [Verification Report](#verification-report)
- [License](#license)
- [Author](#author)

## Features

- Compare local configuration files without executing their contents.
- Report added, removed, modified, and type-changed values.
- Redact common secret-bearing keys by default, including nested values.
- Choose concise human output or machine-readable JSON output.
- Use MCP through a separate optional stdio server.
- Run locally without an AI service or network access.

## Why CfgLens?

**Compare configurations, not just text.**

Traditional diff tools remain useful for line-by-line edits. CfgLens complements them by parsing supported configuration formats and showing which values were added, removed, modified, or changed type, including nested values. That makes common environment and deployment reviews easier to scan without replacing a text diff when formatting or exact line changes matter.

CfgLens brings together:

- Structure-aware comparison for JSON, YAML, TOML, and `.env` files.
- Added, removed, modified, and type-changed value reporting.
- Default redaction for recognized sensitive configuration keys.
- Human-readable output and strict JSON output from one CLI.
- A shared comparison core for the CLI and optional MCP server.
- Deterministic local processing with no AI model, hosted service, or API key.
- One required runtime dependency, PyYAML; MCP is optional.
- A Python implementation designed for Windows, macOS, and Linux. Phase 4 runtime validation was performed on Windows.

Typical uses include developers comparing application settings, DevOps engineers reviewing deployment changes, solution architects checking environment differences, QA engineers validating test configurations, CI/CD jobs identifying configuration drift, and trusted local MCP clients requesting comparisons.

## Installation

CfgLens requires Python 3.11 or newer. The package is not yet published. After publication, install the CLI with:

```bash
python -m pip install cfglens
```

From a local checkout, install the development tools with:

```bash
python -m pip install -e ".[dev]"
```

MCP is optional. From a local checkout, install the MCP extra with:

```bash
python -m pip install -e ".[mcp]"
```

After publication, the corresponding package install will be `python -m pip install "cfglens[mcp]"`.

## Quick Start

Compare the included development and production examples using format detection:

```bash
cfglens examples/development.yaml examples/production.yaml
```

Differences produce exit code `1`; see [Exit Codes](#exit-codes).

## CLI Usage

The CLI accepts two paths, optional `--format {json,yaml,toml,env}`, optional `--output {human,json}`, and the unsafe `--show-values` switch.

Print strict JSON for scripts:

```bash
cfglens examples/development.yaml examples/production.yaml --output json
```

Compare the included `.env` samples:

```bash
cfglens examples/development.env examples/production.env --format env
```

`--show-values` disables redaction and can expose secrets. Use it only when you have reviewed the output destination.

## Real-World Example

The synthetic [development YAML](examples/development.yaml) and [production YAML](examples/production.yaml) illustrate an environment review. The files contain an added retry count, a removed region, a changed port, a boolean/string type change, and a changed synthetic password.

```bash
cfglens examples/development.yaml examples/production.yaml
```

Actual captured output:

```text
TYPE_CHANGED /app/debug (string -> boolean)
  before: 'false'  after: False
MODIFIED     /app/password (string -> string)
  before: '[REDACTED]'  after: '[REDACTED]'
MODIFIED     /app/port (integer -> integer)
  before: 8080  after: 443
REMOVED      /app/region (string -> missing)
  before: 'development'  after: None
ADDED        /app/retries (missing -> integer)
  before: None  after: 3
5 change(s)
```

The paths identify changed values, the debug setting is reported as a type change, and the password values are redacted by default.

## MCP Installation and Configuration

MCP support is optional. Install the extra and configure a trusted MCP client to launch `cfglens-mcp` as a stdio server. For clients using this common JSON shape:

```json
{
	"mcpServers": {
		"cfglens": {
			"command": "cfglens-mcp"
		}
	}
}
```

The `compare_configs(before_path, after_path, format?)` tool compares local files on the MCP server host. It always uses the shared core's redaction policy and provides no option to reveal values.

The server can read files accessible to its operating-system user. In V0.1.0, connect it only to trusted local clients; do not expose it to untrusted callers. Use operating-system-level sandboxing if you need to limit its filesystem access.

## Supported Configuration Formats

- **JSON:** objects, arrays, strings, numbers, booleans, and `null`. Duplicate object keys are rejected.
- **YAML:** parsed with PyYAML's safe loader. Mapping keys must be strings; duplicate keys and duplicate YAML set members are rejected. YAML aliases do not execute code.
- **TOML:** parsed with Python's standard-library `tomllib`. TOML date, datetime, and time values are supported.
- **`.env`:** literal `KEY=value` entries, optional `export ` prefixes, and matching outer single or double quotes. Values are not shell-expanded; duplicate or invalid keys are rejected.

UTF-8 and UTF-8-with-BOM input are supported. `.env` values are strings; keys use ASCII shell-style identifiers.

## Comparison Behavior

CfgLens normalizes values in the shared core before comparison. The canonical model supports null, booleans, strings, finite integers and floats, arrays, and objects with string keys. Non-finite numbers (including overflow to infinity) and unsupported native values are rejected with sanitized errors.

YAML dates and datetimes, TOML dates, datetimes, and times, and YAML sets are represented as tagged JSON objects such as `{"$cfglens-native":["date","2024-01-02"]}`. Aware datetimes are normalized to UTC; naive datetimes stay naive. Set members are normalized and sorted by their canonical JSON representation. Objects containing the reserved `$cfglens-native` key are escaped with an `object` tag and key/value pairs, so ordinary user data cannot be mistaken for a native value. Other unsupported types, such as YAML binary values, are rejected rather than stringified.

JSON, TOML, and `.env` object keys are strings by definition. YAML mappings are restricted to string keys, including nested mappings; non-string keys are rejected rather than coerced. Duplicate JSON/YAML mapping keys are rejected, including YAML keys that compare equal in Python (for example `true` and `1`). Duplicate YAML set members are rejected too.

Mappings are compared recursively in sorted key order. Lists are compared by index, not by attempting to infer insertions or moves: inserting at index zero can therefore mark subsequent indices as modified and the final index as added. Null and missing values are distinct. Boolean and integer values are distinct, as are integers and floats (`1` versus `1.0`); values of the same numeric type use normal exact Python numeric equality, so `-0.0` equals `0.0`.

Change paths use JSON Pointer escaping for `~` and `/`; list entries use numeric indices. Each change includes its path, change kind, and before/after value types. Sensitive values are replaced with `[REDACTED]` while this metadata remains available. CLI JSON output contains only JSON-compatible values and is encoded with non-finite numbers disallowed; no arbitrary `str()` fallback is used.

These rules introduce compatibility changes for inputs that previously relied on non-string YAML mapping keys, duplicate YAML keys, non-finite numbers, or implicit stringification of native values. Native date/time/set values now use tagged JSON representations. Configuration nesting is limited to 128 levels; deeper input is rejected with a sanitized error.

## Secret Redaction and Security

Redaction is enabled by default for CLI human output, CLI JSON output, and MCP results. It recognizes common components such as password, secret, token, credential, and authorization, plus key and URL combinations including `api_key`, `private_key`, `database_url`, and `db_url`. Matching is case-insensitive and supports snake_case, camelCase, PascalCase, and kebab-case keys. Values nested under a sensitive key are also redacted.

Detection is heuristic: a secret stored under an unrelated key may not be recognized. Review output before sharing it. CLI `--show-values` is explicitly unsafe. MCP always redacts and has no reveal option. The Security Hardened badge is a project description, not a certification or guarantee.

Parser errors omit source excerpts and raw parser messages. Human-readable output escapes terminal control and formatting characters in paths and values. JSON output uses JSON escaping.

## Exit Codes

- `0`: files are identical.
- `1`: differences were found.
- `2`: input could not be read or parsed, or JSON output could not be encoded safely.

## Development and Testing

From the repository root, run the tests and build the distribution:

```bash
python -m pytest -q
python -m build
python -m twine check dist/*
```

The development extra includes the optional MCP dependency and test/build tools.

Phase 4 property tests use bounded, deterministic Hypothesis examples. Core statement and branch coverage can be measured with:

```bash
python -m pytest -q --cov=cfglens.core --cov-branch
```

Hypothesis and pytest-cov are included only in the `dev` extra, not in normal CLI installations.

## GitHub and PyPI Release Information

The intended distribution name is `cfglens`; the package is not yet published on PyPI. The release workflow is configured to publish a GitHub release through PyPI Trusted Publishing. Before publication, configure the repository's PyPI trusted publisher and verify the distribution name is available.

The project repository is [github.com/dimpletz/cfglens](https://github.com/dimpletz/cfglens). The repository URL is configured in package metadata and the License badge links directly to its `main` branch `LICENSE` file. Confirm the repository is accessible before the initial push.

## Release Preparation

- [Draft changelog](CHANGELOG.md)
- [V0.1.0 release notes (draft)](RELEASE_NOTES_v0.1.0.md)
- [First-release checklist and setup instructions](RELEASE_CHECKLIST.md)
- [Phase 4 verification record](PHASE4_VERIFICATION.md)

## Verification Report

Phase 4's README command outcomes are recorded in [PHASE4_VERIFICATION.md](PHASE4_VERIFICATION.md). Phase 5's CI, packaging, security, badge, and final README verification is recorded in [PHASE5_VERIFICATION.md](PHASE5_VERIFICATION.md).

## License

CfgLens is distributed under the [MIT License](LICENSE).

## Author

Ofelia B Webb is the official author and maintainer.

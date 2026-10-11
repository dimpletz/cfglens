# CfgLens 0.1.0

**Compare configurations, not just text.**

CfgLens is a local configuration comparison utility for Python 3.11 and newer. It compares JSON, YAML, TOML, and `.env` structures from the command line, with optional stdio MCP support. It requires no AI model, hosted service, or API key.

## Highlights

- Reports added, removed, modified, and type-changed values in deterministic path order.
- Provides human-readable output and strict JSON output.
- Redacts recognized sensitive values by default; the CLI's `--show-values` option is explicitly unsafe. MCP has no reveal option.
- Uses one shared comparison core for CLI and MCP.
- Normalizes YAML/TOML dates and times and YAML sets using tagged JSON objects.
- Rejects non-finite numbers, non-string YAML mapping keys, duplicate keys, unsupported native values, and nesting deeper than 128 levels.

## Compatibility Notes

YAML mappings with non-string keys and duplicate mapping keys are rejected rather than coerced or overwritten. Non-finite numeric values and unsupported native types are rejected. YAML/TOML date, datetime, time, and YAML set values now serialize as tagged JSON values. Lists compare index by index; insertions may cause later indices to appear modified. Integer and float values are distinct types.

## Security Notes

Redaction is heuristic and does not guarantee detection when secrets are stored under unrelated keys. MCP can read files accessible to its operating-system user and is intended only for trusted local clients in this release. The Security Hardened README badge is descriptive and is not a certification.

## Installation

Install the CLI with `python -m pip install cfglens`. Install optional MCP support with `python -m pip install "cfglens[mcp]"`.

Official author and maintainer: Ofelia B Webb.

Released 2026-10-11: [GitHub Release](https://github.com/dimpletz/cfglens/releases/tag/v0.1.0) | [PyPI package](https://pypi.org/project/cfglens/).

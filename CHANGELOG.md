# Changelog

## 0.1.0 - Unreleased

### Added
- Deterministic structure-aware comparison for JSON, YAML, TOML, and `.env` files through a shared Python core.
- Command-line human and strict JSON output, plus optional stdio MCP support.
- Default heuristic redaction for recognized sensitive configuration keys.
- Tagged JSON normalization for YAML/TOML dates, datetimes, times, and YAML sets.

### Changed
- YAML mapping keys must be strings; duplicate JSON/YAML mapping keys and duplicate YAML set members are rejected.
- Non-finite numbers and unsupported native values are rejected; configuration nesting is limited to 128 levels.
- Lists compare by index; integers and floats are type-distinct.

### Fixed
- Parser errors no longer include raw source excerpts, and human terminal output escapes control characters.
- MCP comparisons always use shared-core redaction and sanitized parsing.
- Packaging metadata, cross-platform CI coverage, and OIDC-based PyPI release safeguards are prepared for review.

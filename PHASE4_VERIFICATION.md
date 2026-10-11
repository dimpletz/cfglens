# CfgLens Phase 4 Verification Report

Validation was performed on Windows with Python 3.14.3 in an isolated virtual environment installed from the local project. The package is not yet published, so commands that require its PyPI release were safely skipped.

## README Command Inventory

| # | Section | Exact command/config | Expected | Observed result | Status |
|---:|---|---|---|---|---|
| 1 | Installation | `python -m pip install cfglens` | Install published CLI | Not run; package is not published and the README says to use this only after publication | Safely skipped |
| 2 | Installation | `python -m pip install -e ".[dev]"` | Install local development package and tools | Exit `0`; editable `cfglens 0.1.0` installed in a fresh venv | Passed |
| 3 | Installation | `python -m pip install -e ".[mcp]"` | Install local optional MCP support | Exit `0`; optional MCP dependency present in the fresh venv | Passed |
| 4 | Installation | `python -m pip install "cfglens[mcp]"` | Install published MCP extra | Not run; package is not published | Safely skipped |
| 5 | Quick Start | `cfglens examples/development.yaml examples/production.yaml` | Human comparison with five changes | Exit `1`; five changes shown; synthetic password redacted | Passed |
| 6 | CLI Usage | `cfglens examples/development.yaml examples/production.yaml --output json` | Strict JSON comparison | Exit `1`; strict Python JSON parser accepted output; count `5`; secret redacted | Passed |
| 7 | CLI Usage | `cfglens examples/development.env examples/production.env --format env` | `.env` comparison | Exit `1`; three changed values shown; synthetic secret redacted | Passed |
| 8 | Real-World Example | `cfglens examples/development.yaml examples/production.yaml` | Captured output matches implementation | Exit `1`; stdout matched the README output byte-for-byte | Passed |
| 9 | MCP Configuration | `cfglens-mcp` (launched by the README JSON client configuration) | Start stdio server, discover tool, compare files, redact secrets | Exit `0` after client shutdown; tool discovery and call succeeded; strict JSON response and redaction verified | Passed |
| 10 | Development and Testing | `python -m pytest -q` | Run full suite | Exit `0`; **83 passed**, 0 failed, 0 skipped | Passed |
| 11 | Development and Testing | `python -m build` | Build wheel and source distribution | Exit `0`; `cfglens-0.1.0-py3-none-any.whl` and `cfglens-0.1.0.tar.gz` built | Passed |
| 12 | Development and Testing | `python -m pytest -q --cov=cfglens.core --cov-branch` | Full suite and core coverage | Exit `0`; **83 passed**, core coverage **94%** | Passed |

**Totals:** 12 command/config entries identified; 10 executed; 10 passed; 0 failed; 2 safely skipped. The two skipped commands depend on the not-yet-published PyPI distribution. Difference commands correctly return exit code `1` by CLI contract; this is an expected successful verification result.

The JSON client configuration was parsed as JSON and used to launch the installed `cfglens-mcp` console entry point. MCP tool discovery, valid comparison, repeated deterministic result, redaction, sanitized malformed-input error, and readable/unreadable path behavior were exercised. The server was stdio-only.

## Tests and Quality Checks

- `python -m pytest -q`: 83 passed, 0 failed, 0 skipped (fresh venv).
- `python -m pytest -q --cov=cfglens.core --cov-branch`: 83 passed; 234 statements, 13 missed (94.4% statement coverage); 120 branches, 7 partial; 94% combined coverage reported by pytest-cov.
- `python -m ruff check .`: passed for the entire repository.
- MCP integration used the optional `mcp` extra and the actual installed stdio process.
- Coverage was collected on the shared core. Hypothesis tests are deterministic and bounded at 60 examples per property.

## Performance Smoke Observations

Synthetic observations from Python 3.14.3 on this Windows host (not comparative benchmarks):

- 100 small load-and-compare repetitions: 0.0454 seconds.
- Ten 96-level nested load-and-compare repetitions: 0.0115 seconds.
- Three load-and-compare repetitions of a 5,000-key nested object: 3.0271 seconds with `tracemalloc` enabled; peak traced memory 4.19 MiB.
- A 1,400-level JSON input was rejected at the configured 128-level maximum in 0.0011 seconds.

The timing sample is environment-specific and is not a performance guarantee. Functional tests cover 2,000 flat keys, 96 nested levels, repeated comparisons, and rejection beyond the nesting limit.

## README Links and Badges

- All 16 table-of-contents anchors resolve to headings.
- The MCP JSON client config parsed successfully and names `cfglens-mcp`.
- Local LICENSE and example links resolve.
- The four Shields.io badge image URLs resolve. The PyPI project endpoint is not available yet because the package has not been published; the README labels that status and does not claim publication.
- The captured YAML comparison output was compared byte-for-byte with stdout from the installed CLI.

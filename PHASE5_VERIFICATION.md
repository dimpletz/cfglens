# CfgLens Phase 5 Verification

## Local Validation

Environment: Windows, Python 3.14.3. A fresh development venv was created from the local project and installed with both README installation commands. No GitHub Actions run or publication was performed.

- `python -m pytest -q`: **85 passed**, 0 failed, 0 skipped. This included actual MCP stdio integration, invalid UTF-8, and unhashable YAML-set error regressions.
- `python -m pytest -q --cov=cfglens.core --cov-branch --cov-report=term-missing`: **85 passed**; 234 statements, 11 missed (95.3% statement coverage); 120 branches, 6 partial; 95% combined coverage reported by pytest-cov.
- `python -m ruff check .`: passed across the repository, including the corrected `__init__.py` import and `__all__` ordering.
- `python -m build`: built `cfglens-0.1.0-py3-none-any.whl` and `cfglens-0.1.0.tar.gz`.
- `python -m twine check dist/*` using Twine 7.0.0: both wheel and sdist passed.
- Both artifacts were installed separately into fresh venvs. The installed CLI returned the expected difference exit code `1`, and strict JSON parsing/redaction passed.
- Normal wheel and sdist installs had no MCP package installed. The wheel's `[mcp]` extra installed successfully; the installed `cfglens-mcp` console executable completed a real stdio initialize, tool discovery, and comparison. Synthetic secret values were redacted.
- Wheel metadata verified: name `cfglens`, version `0.1.0`, author `Ofelia B Webb`, MIT license expression, Python `>=3.11`, PyYAML required, and MCP behind optional extras. CLI and MCP entry points were present.
- Sdist includes README, LICENSE, and all four README-linked example files. Twine rendered the README successfully.

## Dependency Audit

`pip-audit --requirement <temporary pinned freeze excluding cfglens and bootstrap pip> --no-deps` reported no known vulnerabilities for the normal runtime requirement and the installed MCP dependency set. This is an audit of the resolved external requirements, not of the unpublished local CfgLens package itself. The `--no-deps` mode emits pip-audit's warning that fully hashed lockfiles are preferable; this project intentionally does not maintain a lockfile.

A broader audit of fresh venv contents also reported 10 advisory matches across five IDs for the venv-seeded `pip 25.3` (PYSEC-2026-1796, PYSEC-2026-2875, PYSEC-2026-2876, PYSEC-2026-196, PYSEC-2026-3721). These are the installer bundled by the local Python venv, not CfgLens runtime dependencies; fixed versions are at or above pip 26.2.1. CI and release-build workflows now upgrade pip within `>=26.2.1,<27` before installing project tools. The bounded upgrade was verified locally as pip 26.2.1.

After upgrading pip, `pip-audit --path <venv>/Lib/site-packages --skip-editable` found no known vulnerabilities in the full dev/MCP venv; the editable local CfgLens project was skipped. The external runtime and MCP requirements were also audited separately with no known vulnerabilities.

## Workflows

- Both workflow files parse as YAML. Their matrix, event, permission, environment, and artifact structure were checked locally.
- CI is configured for Ubuntu, Windows, and macOS with Python 3.11, 3.12, 3.13, and 3.14. Full tests run in every matrix cell; coverage runs in the Ubuntu/Python 3.14 cell; Ruff, build/Twine, and isolated wheel/sdist smoke tests run once in a separate Ubuntu job.
- Publishing is triggered only by a non-prerelease published GitHub release, rejects a tag other than `v<project version>`, builds and checks distributions, transfers only wheel/sdist plus a SHA-256 manifest, verifies the manifest, and uses OIDC in the protected `pypi` environment. No PyPI token is used.
- Third-party actions are pinned to verified immutable commits: checkout `11bd719…`, setup-python `a26af69…`, upload-artifact `ea165f8…`, download-artifact `d3f86a1…`, and PyPI publish `ed0c539…`.
- Embedded Bash scripts passed `bash -n` using Git for Windows Bash. `actionlint` is not installed locally. GitHub-hosted CI has not run, so the matrix and workflow integration are **not yet verified by GitHub Actions**.

## README Command Inventory

| # | README command/config | Expected | Observed | Status |
|---:|---|---|---|---|
| 1 | `python -m pip install cfglens` | Install after PyPI release | Not run; package remains unpublished | Safely skipped |
| 2 | `python -m pip install -e ".[dev]"` | Local dev install | Exit `0` in fresh venv; includes Twine 7 | Passed |
| 3 | `python -m pip install -e ".[mcp]"` | Local MCP extra install | Exit `0` in fresh venv | Passed |
| 4 | `python -m pip install "cfglens[mcp]"` | Install after PyPI release | Not run; package remains unpublished | Safely skipped |
| 5 | `cfglens examples/development.yaml examples/production.yaml` | Human output, five changes | Exit `1`; expected changes, synthetic secret redacted | Passed |
| 6 | `cfglens examples/development.yaml examples/production.yaml --output json` | Strict JSON | Exit `1`; parsed with a strict JSON parser, count `5`, secret redacted | Passed |
| 7 | `cfglens examples/development.env examples/production.env --format env` | `.env` comparison | Exit `1`; three changes, secret redacted | Passed |
| 8 | `cfglens examples/development.yaml examples/production.yaml` (real-world example) | Captured output matches CLI | Exit `1`; output verified against installed CLI | Passed |
| 9 | `cfglens-mcp` from the README MCP JSON configuration | Start stdio server and compare | Installed wheel extra launched; tool discovery/call and redaction passed; server shut down cleanly | Passed |
| 10 | `python -m pytest -q` | Full tests | Exit `0`; 85 passed | Passed |
| 11 | `python -m build` | Wheel and sdist | Exit `0`; both artifacts built | Passed |
| 12 | `python -m twine check dist/*` | Metadata and rendered README | Exit `0`; both artifacts passed | Passed |
| 13 | `python -m pytest -q --cov=cfglens.core --cov-branch` | Tests plus core coverage | Exit `0`; 85 passed, 95% combined core coverage | Passed |

**Totals:** 13 README command/config entries identified; 11 executed and passed; 0 failed; 2 safely skipped because they require the not-yet-published PyPI package. Exit code `1` for comparison examples is the documented “differences found” result and was treated as a successful verification.

## Badges, Links, and Identity

- All four Shields.io image URLs render. The Python badge `3.11+` matches `requires-python = ">=3.11"`.
- The PyPI badge visibly says `cfglens (unpublished)` and links to `https://pypi.org/project/cfglens/`; no publication claim is made.
- The Security Hardened badge is explicitly described in README as a project description, not certification or guarantee.
- The license badge uses the relative `LICENSE` target, which works inside the future repository. No repository URL is configured and none was invented. Once the repository is chosen, set `[project.urls]` and optionally change the badge target to the repository's LICENSE URL.
- README heading anchors and MCP JSON configuration were validated. Author attribution is Ofelia B Webb.

## Release Readiness

**READY WITH CONDITIONS.** Local build, metadata, Twine, install, CLI, test, lint, coverage, security-audit, and MCP checks passed. Do not publish until the repository has a canonical URL, PyPI Trusted Publisher owner/repository values and protected `pypi` environment are configured, the full GitHub Actions matrix succeeds, the package name is confirmed available, and an authorized reviewer approves release creation.

# CfgLens V0.1.0 Phase 6C Verification

## Publication

- GitHub repository: <https://github.com/dimpletz/cfglens> (public).
- GitHub Release: <https://github.com/dimpletz/cfglens/releases/tag/v0.1.0> (normal release, not draft/prerelease).
- Tag: `v0.1.0`, pointing to release commit `e20ff341f4d524148b067cb2ffa7cff9fab84eae`.
- PyPI: <https://pypi.org/project/cfglens/>, version `0.1.0`.
- Author: Ofelia B Webb; Python requirement `>=3.11`; MIT license.
- PyPI publishing workflow: <https://github.com/dimpletz/cfglens/actions/runs/38107649568> (success, PyPI returned 200 OK for wheel and sdist).
- Release CI matrix: <https://github.com/dimpletz/cfglens/actions/runs/38107571788> (success; Ubuntu, Windows, macOS × Python 3.11–3.14, plus packaging).
- Post-publication documentation-only main commit: `6d889289b7ff5fb2ede731d6cfe67cdbab0e1f43`.

## Published Artifacts

- Wheel: `cfglens-0.1.0-py3-none-any.whl`
  - SHA-256: `e72f9865025e003641793ab92ce18ef95361db3c78c415183a7bf192ddcd3abf`
- Source distribution: `cfglens-0.1.0.tar.gz`
  - SHA-256: `71e30826db120e5cebb87857ae5f3b338c1199008c8bf3c901afb017db2e8fbe`

The published PyPI digest values were compared to the successful publishing workflow artifact records.

## PyPI Installation Tests

Validated on Windows with Python 3.14.3. Each environment was newly created and the import location was checked under its venv `site-packages`; `PYTHONPATH` was removed. Installs used the public PyPI index with `--no-cache-dir`, not local wheels, an editable checkout, or a development cache.

- `python -m pip install --no-cache-dir --index-url https://pypi.org/simple cfglens==0.1.0`: passed. MCP was absent from the normal installation; CLI help succeeded.
- PyPI normal-install CLI comparisons: JSON, YAML, TOML, and `.env` each returned the documented difference code `1`; JSON outputs parsed with non-finite constants rejected and recognized synthetic secrets redacted.
- `python -m pip install --no-cache-dir --index-url https://pypi.org/simple cfglens[mcp]==0.1.0`: passed in a separate fresh environment. The installed `cfglens-mcp` stdio process initialized, discovered `compare_configs`, compared files, returned JSON-compatible output with redaction, and returned a sanitized parser error.

## README and Badges

- The GitHub README now uses live Shields.io PyPI version and Python-version badges; the supported Python badge reports 3.11–3.14.
- License badge targets the repository's `main` branch `LICENSE`; PyPI badge targets the project page; Security Hardened remains explicitly descriptive, not a certification.
- All four badge endpoints rendered, README anchors and local links resolved, and author attribution remains Ofelia B Webb.
- The package page's rendered long description still contains the README snapshot embedded in the already-published wheel/sdist, including the old unpublished wording. Published artifacts are immutable; changing that PyPI description requires a separately approved package release or an available PyPI project-description management path. No artifact was replaced or version changed here.

## Post-Publication README Command Inventory

Commands below were executed on Windows/Python 3.14.3. Published installs came from the public PyPI index in fresh virtual environments; the imported package location was verified under each environment's `site-packages`.

| # | README command/config | Expected | Observed | Status |
|---:|---|---|---|---|
| 1 | `python -m pip install cfglens==0.1.0` | Install published normal package | Exit `0`; package imported from fresh venv; MCP absent | Passed |
| 2 | `python -m pip install -e ".[dev]"` | Install checkout development extra | Exit `0` in fresh dev venv | Passed |
| 3 | `python -m pip install "cfglens[mcp]==0.1.0"` | Install published optional MCP extra | Exit `0`; package imported from fresh venv | Passed |
| 4 | `python -m pip install -e ".[mcp]"` | Install checkout MCP extra | Exit `0` in fresh dev venv | Passed |
| 5 | `cfglens examples/development.yaml examples/production.yaml` | Human output with five differences | Exit `1`; expected output and password redaction | Passed |
| 6 | `cfglens examples/development.yaml examples/production.yaml --output json` | Strict JSON output | Exit `1`; strict parser accepted; count `5`; synthetic values redacted | Passed |
| 7 | `cfglens examples/development.env examples/production.env --format env` | `.env` comparison | Exit `1`; three changes; synthetic secret redacted | Passed |
| 8 | Real-world YAML comparison command | Output matches README capture | Exit `1`; captured output matched actual CLI | Passed |
| 9 | `cfglens-mcp` from README client configuration | Stdio discovery/call, redaction, safe error | Fresh PyPI `[mcp]` venv; tool discovery, compare, redaction, and parser-error sanitization passed | Passed |
| 10 | `python -m pytest -q` | Full suite | Exit `0`; 85 passed | Passed |
| 11 | `python -m build` | Build wheel and sdist | Exit `0`; both artifacts produced | Passed |
| 12 | `python -m twine check dist/*` | Validate metadata and README | Exit `0`; wheel and sdist passed | Passed |
| 13 | `python -m pytest -q --cov=cfglens.core --cov-branch` | Full suite and coverage | Exit `0`; 85 passed; 95% combined core coverage | Passed |

**Totals:** 13 documented command/config entries; 13 executed; 13 passed; 0 failed; 0 skipped. Comparison commands intentionally returned `1` because the fixtures differ, matching the documented CLI exit contract.

## Remaining Repository Limitations

- No GitHub topics have been added yet.
- Main branch protection is not enabled; GitHub reported that it was unavailable under the previous private-repository plan. The project was subsequently made public with authorization, but branch protection was not reconfigured during publication.
- The `pypi` environment has the `main` branch and `v*` tag deployment rules, but has no required-reviewer environment rule configured. Publishing required a deliberate workflow dispatch recovery because the first pinned publisher rejected Core Metadata 2.5; the correction used PyPA's metadata-compatible pinned action and OIDC.
- The latest CI and publisher jobs passed. The initial publication attempt failed before uploading because the old publisher rejected Metadata 2.5; no API token was used, no artifact was overwritten, and the successful retry used the same authorized release/tag.

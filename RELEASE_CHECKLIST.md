# CfgLens 0.1.0 Release Checklist

CfgLens V0.1.0 was released on 2026-10-11. This checklist records completed release steps and remaining repository-maintenance recommendations; it does not trigger release actions.

## Repository Setup

- [x] Confirm that `https://github.com/dimpletz/cfglens` exists, is public, and is accessible to the authenticated `dimpletz` account. The URL is configured in `pyproject.toml` and the README License badge.
- [x] Push the reviewed source to `main`; local `main` and `origin/main` were synchronized after publication documentation updates.
- [ ] Add GitHub topics: `python`, `configuration`, `json`, `yaml`, `toml`, `dotenv`, `cli`, and `mcp`.
- [x] Confirm the MIT license file and `Copyright (c) 2026 Ofelia B Webb` attribution.
- [ ] Branch protection is not enabled. GitHub rejected the earlier protection request while the repository was private; protection availability was not rechecked after it became public. No paid upgrade was made. Continue to require green CI, avoid force-pushes, and require explicit release approval.

## CI and Release Gate

- [x] Run the GitHub Actions matrix on Ubuntu, Windows, and macOS for Python 3.11, 3.12, 3.13, and 3.14. [Successful hosted run](https://github.com/dimpletz/cfglens/actions/runs/38107571788).
- [x] Confirm coverage, full-repository Ruff, wheel/sdist build, Twine check, and installed wheel/sdist smoke steps pass in the successful hosted run.
- [x] Pin third-party workflow actions to reviewed immutable commit SHAs.
- [x] Confirm publishing requires a published non-prerelease Release, exact tag/version match, `pypi` environment, artifact checksum verification, and OIDC-only publication.
- [x] Confirm the `pypi` environment permits tag pattern `v*`, including `v0.1.0`. No required-reviewer protection rule is configured; retain explicit manual release approval.

## PyPI Trusted Publisher

- [x] Verify the `cfglens` PyPI project/version `0.1.0` exists with correct metadata.
- [x] Configure and verify the GitHub Actions Trusted Publisher tuple: owner `dimpletz`, repository `cfglens`, workflow `publish.yml`, environment `pypi`. The successful OIDC publish run is verification evidence.
- [x] No PyPI API token was created or stored.
- [x] Verify OIDC permission is scoped to the publish job and the environment allows `v*` tags.

## Prepare and Publish (Manual, Only After Approval)

- [x] Review [CHANGELOG.md](CHANGELOG.md) and [RELEASE_NOTES_v0.1.0.md](RELEASE_NOTES_v0.1.0.md) for V0.1.0.
- [x] Run local release checks and Twine validation.
- [x] Create the `v0.1.0` tag and normal GitHub Release targeting the CI-verified release commit.
- [x] Observe successful OIDC publishing of wheel and sdist without API tokens. Environment required-reviewer protection is not configured.

## Verify First Publication

- [x] Confirm the PyPI project page shows version `0.1.0`, MIT, Python `>=3.11`, and author metadata.
- [x] Install `cfglens==0.1.0` from PyPI in a fresh normal environment and exercise JSON, YAML, TOML, and `.env` CLI comparisons without MCP installed.
- [x] Install `cfglens[mcp]==0.1.0` from PyPI in a separate environment and exercise stdio discovery, comparison, redaction, and sanitized parser errors.
- [x] Verify published wheel/sdist SHA-256 digests against the successful publisher workflow artifacts.
- [x] Update the GitHub README PyPI badge to the live version and supported-Python badges.
- [x] Record the release, CI and publishing run links, artifact digests, and publication date in [PHASE6C_VERIFICATION.md](PHASE6C_VERIFICATION.md).
- [ ] PyPI's rendered README remains the description embedded in the already-published 0.1.0 artifacts. A new package version would be required to change that immutable description; no replacement artifact was uploaded.

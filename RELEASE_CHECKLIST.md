# CfgLens 0.1.0 Release Checklist

This checklist prepares the first public release. No repository, tag, GitHub release, or PyPI publication has been created by this checklist.

## Repository Setup

- [ ] Confirm that `https://github.com/dimpletz/cfglens` exists and is accessible to the authenticated `dimpletz` account. The provided URL is configured in `pyproject.toml` and the README License badge.
- [ ] If the repository is missing or inaccessible, have its owner create it or provide the correct URL before initializing or pushing local Git history. Do not create a repository automatically.
- [ ] Push the reviewed source to the repository only after approval; configure the default branch and protect it with pull-request review and required CI checks.
- [ ] Add GitHub topics: `python`, `configuration`, `json`, `yaml`, `toml`, `dotenv`, `cli`, and `mcp`.
- [ ] Confirm the MIT license file and `Copyright (c) 2026 Ofelia B Webb` attribution.

## CI and Release Gate

- [x] Run the new CI workflow on GitHub and confirm all Ubuntu, Windows, and macOS jobs pass for Python 3.11, 3.12, 3.13, and 3.14. [Successful hosted run](https://github.com/dimpletz/cfglens/actions/runs/38103792352); local checks do not substitute for hosted matrix results.
- [x] Confirm coverage, full-repository Ruff, wheel/sdist build, Twine check, and installed wheel/sdist smoke steps pass in the successful hosted run.
- [ ] Review the release workflow action commit SHAs and verify they still correspond to the intended reviewed releases when the release is prepared.
- [ ] Confirm the release workflow is triggered only by a published GitHub release and rejects a tag that does not exactly match `v0.1.0` from project metadata.
- [ ] Configure the GitHub `pypi` environment with required reviewers and deployment protection rules before enabling publication.

## PyPI Trusted Publisher

- [ ] Verify that the `cfglens` project name is available on PyPI immediately before initial publication.
- [ ] In PyPI project settings, add a GitHub Actions Trusted Publisher with owner `dimpletz`, repository `cfglens`, workflow filename `publish.yml`, and environment name `pypi`.
- [ ] Do not create or store a PyPI API token in GitHub repository or environment secrets.
- [ ] Verify OIDC permissions are present only on the publish job and that the `pypi` environment has the expected protection.

## Prepare and Publish (Manual, Only After Approval)

- [ ] Review [CHANGELOG.md](CHANGELOG.md) and [RELEASE_NOTES_v0.1.0.md](RELEASE_NOTES_v0.1.0.md); change `Unreleased` to the actual release date only when release is authorized.
- [ ] Re-run the local release checks in `PHASE5_VERIFICATION.md` and inspect final `twine check` results.
- [ ] After approval, create the `v0.1.0` tag and GitHub release through the approved repository process. The workflow must pass the version check before artifacts are published.
- [ ] Confirm the protected environment approval and observe the OIDC-based publish job; do not add API tokens.

## Verify First Publication

- [ ] Confirm `https://pypi.org/project/cfglens/` shows version `0.1.0` and the expected README, MIT license, Python requirement, and author metadata.
- [ ] Install `cfglens==0.1.0` in a fresh normal environment and verify the CLI works without MCP installed.
- [ ] Install `cfglens[mcp]==0.1.0` in a separate environment and exercise the stdio server with a trusted local client.
- [ ] Verify the published wheel/sdist hashes against the CI build artifacts and check that both artifacts are available.
- [ ] Update the README PyPI badge only if changing its visible unpublished label is appropriate after publication; keep its destination at the official package page.
- [ ] Record the hosted CI run, release URL, PyPI version page, artifact hashes, and publication date in release records.

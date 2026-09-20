# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `git-mr` opens a PR/MR for your branch, with a `## Changelog` section drafted from your commits that the release changelog is built from.
- `git-release` compiles the release changelog from the merged PRs/MRs and shows it for review before anything is written.
- `git-release` requires `dev` to contain `main` before cutting a release, so the changelog on `dev` always has every released version.

### Changed

- `git-commit` no longer writes to `## [Unreleased]`; entries now come from PR/MR descriptions, so parallel branches no longer conflict on `CHANGELOG.md`. Add the `## Changelog` section to your PR/MR template when upgrading.
- The release changelog is written on `release/vX.Y.Z` and dated on the day you ship, instead of being finalized on `dev` when the release branch is cut.
- Entries left under `## [Unreleased]` are folded into the next release automatically.

## [v1.1.0] - 2026-09-19

### Added

- An interrupted release can be resumed: if the PR/MR merged but the tag was not pushed, running `git-release` again finishes the tag instead of opening a second PR/MR.
- `prCli: "none"` supports any git host: you merge the PR/MR yourself and the skill verifies the merge before tagging.
- `git-release` asks for confirmation before merging to production and pushing the tag.
- `versionFiles` bumps any JSON version file (`package.json`, `plugin.json`, ...) to match the release tag.
- Config options for the remote name, tag prefix, annotated tags and QA branch names.
- Automated checks (`scripts/validate.py`, run in CI) cover the schema, the config examples and the git commands used by the prompts.
- The repository releases itself with `git-release`, so `plugin.json` is bumped before each tag.

### Changed

- `git-commit` and `git-sync` read branch names and the changelog path from `.claude/release-kit.json`, and fall back to defaults when it is missing.
- `git-sync` fast-forwards the integration, QA, `release/*` and production branches instead of rebasing them.
- Hotfix branches are checked for unreleased `dev` commits directly, so re-entering a hotfix no longer risks a false stop.
- Hotfix releases bump every version file, not only when the fix touches the frontend.
- `frontendVersionFile` and `frontendVersionBumpCmd` are deprecated in favor of `versionFiles`.
- Commit messages use the co-author trailer from your environment instead of a hardcoded model name.
- The latest-tag lookup skips pre-release and non-version tags, and a release stops if its tag or `release/*` branch already exists.

### Fixed

- `git-sync` no longer rebases a `fix/*` branch cut from `release/*` or a QA branch onto `dev`, which pulled unreleased work into the release.
- `git-sync` now restores your stash when a rebase is aborted.
- A queued merge (such as GitLab auto-merge) is no longer tagged before it has actually merged.
- Releases no longer fail when `dev` is protected: the changelog commit goes through a PR/MR.
- Plugin updates now reach installed copies, because the version in `plugin.json` matches the release tag.
- The plugin manifest now reports version 1.0.0, matching the release tag instead of 0.1.0.
- The marketplace manifest's `$schema` now points to a working URL, so editors can validate it.

## [v1.0.0] - 2026-09-18

### Added

- `release-kit` plugin, published through the `daont-claude-plugins` marketplace, bundling a release skill and two git commands.
- `git-release` skill that cuts a release branch for QA stabilization, then merges to production and tags the version. Quick releases and hotfixes are also supported.
- Per-project release configuration in `.claude/release-kit.json`, with GitHub (`gh`) and GitLab (`glab`) support and a JSON schema for validation.
- Hotfix branches can use any `hotfix/*` name; only the git tag has to carry the version.
- `git-commit` command that checks branch safety, groups changes into conventional commits, and updates the changelog.
- `git-commit` starts a `feature/`, `fix/` or `hotfix/` branch depending on where you are: `dev`/`develop`, `testing`/`staging`, or `main`/`master`.
- `git-sync` command that pulls the latest changes and rebases the current branch onto its base branch, with stash handling and conflict and divergence warnings.

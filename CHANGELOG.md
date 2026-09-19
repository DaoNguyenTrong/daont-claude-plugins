# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed

- The plugin manifest now reports version 1.0.0, matching the release tag instead of 0.1.0.

## [v1.0.0] - 2026-09-18

### Added

- `release-kit` plugin, published through the `daont-claude-plugins` marketplace, bundling a release skill and two git commands.
- `git-release` skill that cuts a release branch for QA stabilization, then merges to production and tags the version. Quick releases and hotfixes are also supported.
- Per-project release configuration in `.claude/release-kit.json`, with GitHub (`gh`) and GitLab (`glab`) support and a JSON schema for validation.
- Hotfix branches can use any `hotfix/*` name; only the git tag has to carry the version.
- `git-commit` command that checks branch safety, groups changes into conventional commits, and updates the changelog.
- `git-commit` starts a `feature/`, `fix/` or `hotfix/` branch depending on where you are: `dev`/`develop`, `testing`/`staging`, or `main`/`master`.
- `git-sync` command that pulls the latest changes and rebases the current branch onto its base branch, with stash handling and conflict and divergence warnings.

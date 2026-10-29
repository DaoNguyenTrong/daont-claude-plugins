# daont-claude-plugins

Personal Claude Code marketplace.

| Plugin | Description |
| --- | --- |
| [`release-kit`](./plugins/release-kit) | Release workflow — `git-release` skill (config-driven via `.claude/release-kit.json`) plus `git-commit`, `git-mr` and `git-sync` commands. |
| [`plane-kit`](./plugins/plane-kit) | Plane work-item workflow — `plane-task` skill, `/plane-init` and `/plane-sync-ci` commands, and a CI script syncing MRs/PRs to Plane (GitLab and GitHub). |

## Use

```bash
claude plugin marketplace add DaoNguyenTrong/daont-claude-plugins
claude plugin install release-kit@daont-claude-plugins
```

Or, per project, commit `extraKnownMarketplaces` + `enabledPlugins` to
`.claude/settings.json` — see each plugin's README.

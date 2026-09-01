# daont-claude-plugins

Personal Claude Code marketplace.

| Plugin | Description |
| --- | --- |
| [`release-kit`](./plugins/release-kit) | Release workflow — `git-release` skill (config-driven via `.claude/release-kit.json`) plus `git-commit` and `git-sync` commands. |

## Use

```bash
claude plugin marketplace add DaoNguyenTrong/daont-claude-plugins
claude plugin install release-kit@daont-claude-plugins
```

Or, per project, commit `extraKnownMarketplaces` + `enabledPlugins` to
`.claude/settings.json` — see each plugin's README.

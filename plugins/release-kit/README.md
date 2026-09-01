# release-kit

Shared release workflow for DaoNguyenTrong's projects.

| Component | Type | What it does |
| --- | --- | --- |
| `git-release` | skill | Cut a release branch, finalize CHANGELOG, ship to the production branch, tag. Standard / quick / hotfix. Driven by a per-project config file. |
| `git-commit` | command | Branch-safety check, grouped conventional commits, `[Unreleased]` changelog update. |
| `git-sync` | command | Fetch + rebase the current branch onto its base; stash/restore, conflict-abort. |

## Install in a project

Add to the project's `.claude/settings.json` (commit it so teammates get it too):

```json
{
  "extraKnownMarketplaces": {
    "daont-claude-plugins": {
      "source": { "source": "github", "repo": "DaoNguyenTrong/daont-claude-plugins" }
    }
  },
  "enabledPlugins": { "release-kit@daont-claude-plugins": true }
}
```

Then create `.claude/release-kit.json` (see below) and remove any project-local
`.claude/skills/git-release/`.

## Per-project config: `.claude/release-kit.json`

Schema: [`release-kit.schema.json`](./release-kit.schema.json). Required: `prCli`, `gate`, `modes`.

| Field | Meaning |
| --- | --- |
| `prCli` | `gh` or `glab` — which CLI opens/merges the release PR/MR |
| `devBranch` / `mainBranch` | integration branch / production branch (defaults `dev` / `main`) |
| `versioningNote` | one line describing how the version is derived (echoed in summaries) |
| `frontendVersionFile` | path to a `package.json` to bump to match the tag, or `null` |
| `frontendVersionBumpCmd` | optional shell command to bump it (`{version}` placeholder) instead of a JSON edit |
| `gate.mandatory` | the blocking verification command (Phase 2 / quick / hotfix) |
| `gate.phase1` | fail-fast check before cutting (defaults to `gate.mandatory`) |
| `changelogPath` | defaults `CHANGELOG.md` |
| `ciTriggerNote` | one sentence on when CI runs, shown in the Phase 2 gate section |
| `modes` | subset of `standard`, `quick`, `hotfix` |

### Examples

**GitHub + .NET/MinVer, frontend not versioned** (DAONT-BASE, FEEDBACK-HUB):

```json
{
  "prCli": "gh",
  "devBranch": "dev",
  "mainBranch": "main",
  "versioningNote": "backend via MinVer (git tag); frontend not versioned",
  "frontendVersionFile": null,
  "gate": {
    "phase1": "dotnet test backend/FeedbackHub.sln --no-restore -m:1 && bun run --cwd frontend test:run",
    "mandatory": "dotnet test backend/FeedbackHub.sln --no-restore -m:1 && bun run --cwd frontend test:run"
  },
  "changelogPath": "CHANGELOG.md",
  "ciTriggerNote": ".github/workflows/release.yml triggers on tag push; CI runs after the tag, there is no PR CI",
  "modes": ["standard", "hotfix"]
}
```

**GitLab + .NET, build-only gate, quick mode enabled** (som):

```json
{
  "prCli": "glab",
  "devBranch": "dev",
  "mainBranch": "main",
  "versioningNote": "backend via git tag (.NET); WPE_SOM/package.json version is not touched",
  "frontendVersionFile": null,
  "gate": {
    "phase1": "cd WPE_SOM_BE && dotnet build && cd ../WPE_SOM && bun run build",
    "mandatory": "cd WPE_SOM_BE && dotnet build && cd ../WPE_SOM && bun run build"
  },
  "changelogPath": "CHANGELOG.md",
  "ciTriggerNote": "GitLab pipeline runs on tag push",
  "modes": ["standard", "quick", "hotfix"]
}
```

**GitLab + frontend package.json bump** (WP-SEHO-CHAT):

```json
{
  "prCli": "glab",
  "devBranch": "dev",
  "mainBranch": "main",
  "versioningNote": "backend via MinVer (tag); frontend version in frontend/package.json",
  "frontendVersionFile": "frontend/package.json",
  "frontendVersionBumpCmd": "bun pm version {version} --no-git-tag-version",
  "gate": {
    "mandatory": "<build/test command from backends/WP-SEHO-CHAT/.claude/rules/commands.md>"
  },
  "changelogPath": "CHANGELOG.md",
  "ciTriggerNote": "GitLab pipeline runs on tag push",
  "modes": ["standard", "hotfix"]
}
```

## Updating

```bash
# in the plugin repo: edit, bump plugins/release-kit/.claude-plugin/plugin.json version,
# commit, tag, push
# in each consumer project:
claude plugin update release-kit
```

Pin a specific version per project by adding `"ref": "<tag-or-sha>"` to the
`source` object in that project's `extraKnownMarketplaces`.

## Manual test checklist (until `claude plugin eval` early access is available)

Run `/git-release` in a scratch repo with a fake `.claude/release-kit.json`:

- [ ] No config file → skill STOPs and prints the template
- [ ] `prCli: gh` → output uses `gh pr create` / `gh pr merge`, never `glab`
- [ ] `prCli: glab` → output uses `glab mr create --yes` / `glab mr merge`, never `gh`
- [ ] Tag step targets `origin/<mainBranch>`, never dev/release branch
- [ ] `modes` without `quick` + user asks "quick release" → skill refuses
- [ ] `frontendVersionFile: null` → no version-bump step
- [ ] `frontendVersionFile` set → bump step appears before the PR/MR
- [ ] Phase 2 includes the "Reconcile with main" step
- [ ] Summary prints the "reconcile dev with main" action for the user

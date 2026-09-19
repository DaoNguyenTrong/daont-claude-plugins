# release-kit

Release workflow for git projects with an integration branch and a production branch.

| Component | Type | What it does |
| --- | --- | --- |
| `git-release` | skill | Cut a release branch, finalize CHANGELOG, ship to the production branch, tag. Standard / quick / hotfix, resumable. Driven by a per-project config file. |
| `git-commit` | command | Branch-safety check, grouped conventional commits, `[Unreleased]` changelog update. |
| `git-sync` | command | Fetch, then rebase short-lived branches onto the branch they were cut from and fast-forward long-lived ones; stash/restore, conflict-abort. |

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

`git-release` needs the file and stops without it. `git-commit` and `git-sync` read it when it exists and fall back to the defaults below when it does not.

| Field | Meaning | Default |
| --- | --- | --- |
| `prCli` | `gh`, `glab`, or `none` — `none` works with any host: the skill prints the title/body, you open and merge the PR/MR (merge commit) in the UI, and it verifies the merge with git before tagging | — |
| `remote` | git remote used for every fetch/push/tag | `origin` |
| `devBranch` / `mainBranch` | integration branch / production branch | `dev` / `main` |
| `qaBranches` | long-lived QA branches; `git-commit` cuts `fix/*` from them, `git-sync` rebases those back onto them | `["testing", "staging"]` |
| `tagPrefix` | prefix of tags, `release/*` branches and changelog headings (`""` for bare tags such as MinVer's default) | `v` |
| `tagAnnotated` | `true` creates annotated tags (`git tag -a`) | `false` |
| `versioningNote` | one line on how the version is derived (echoed in summaries) | omitted |
| `versionFiles` | JSON files (`package.json`, `plugin.json`, ...) whose `"version"` is bumped to the tag on the release branch; each entry takes an optional `bumpCmd` (`{version}` placeholder) | `[]` |
| `gate.mandatory` | the blocking verification command (Phase 2 / quick / hotfix) | — |
| `gate.phase1` | fail-fast check before cutting | `gate.mandatory` |
| `changelogPath` | changelog used by `git-release` and `git-commit` | `CHANGELOG.md` |
| `ciTriggerNote` | one sentence on when CI runs, shown in the Phase 2 gate section | omitted |
| `modes` | subset of `standard`, `quick`, `hotfix`; a mode that is not listed is refused | — |

`frontendVersionFile` / `frontendVersionBumpCmd` still work (they mean one `versionFiles` entry) but are deprecated.

### Examples

**GitHub + .NET/MinVer, frontend not versioned:**

```json
{
  "prCli": "gh",
  "devBranch": "dev",
  "mainBranch": "main",
  "versioningNote": "backend via MinVer (git tag); frontend not versioned",
  "gate": {
    "phase1": "dotnet test backend/App.sln --no-restore -m:1 && bun run --cwd frontend test:run",
    "mandatory": "dotnet test backend/App.sln --no-restore -m:1 && bun run --cwd frontend test:run"
  },
  "changelogPath": "CHANGELOG.md",
  "ciTriggerNote": ".github/workflows/release.yml triggers on tag push; CI runs after the tag, there is no PR CI",
  "modes": ["standard", "hotfix"]
}
```

**GitLab + .NET, build-only gate, quick mode enabled:**

```json
{
  "prCli": "glab",
  "devBranch": "dev",
  "mainBranch": "main",
  "versioningNote": "backend via git tag (.NET); web/package.json version is not touched",
  "gate": {
    "mandatory": "cd api && dotnet build && cd ../web && bun run build"
  },
  "changelogPath": "CHANGELOG.md",
  "ciTriggerNote": "GitLab pipeline runs on tag push",
  "modes": ["standard", "quick", "hotfix"]
}
```

**GitLab + frontend package.json bump:**

```json
{
  "prCli": "glab",
  "devBranch": "dev",
  "mainBranch": "main",
  "versioningNote": "backend via MinVer (tag); frontend version in frontend/package.json",
  "versionFiles": [
    { "path": "frontend/package.json", "bumpCmd": "bun pm version {version} --no-git-tag-version" }
  ],
  "gate": {
    "mandatory": "dotnet test && bun run --cwd frontend test:run"
  },
  "ciTriggerNote": "GitLab pipeline runs on tag push",
  "modes": ["standard", "hotfix"]
}
```

**Any other host (Bitbucket, Azure DevOps, Gitea, protected branches), bare tags, annotated tags:**

```json
{
  "prCli": "none",
  "mainBranch": "master",
  "tagPrefix": "",
  "tagAnnotated": true,
  "gate": {
    "mandatory": "make test"
  },
  "modes": ["standard", "hotfix"]
}
```

## Safety and recovery

- The skill asks for confirmation right before the merge and the tag — the two steps it cannot undo.
- It never tags before the merge is verified (`git merge-base --is-ancestor`), never moves or deletes an existing tag, and never bypasses branch protection. If a merge is refused (required checks, approvals) it prints the PR/MR link and stops.
- A release that stopped halfway (PR merged, tag not pushed) is safe to resume: run `/git-release` and say "resume", or run it again — every irreversible step first checks whether it is already done.
- Hotfix branches are checked statelessly: any commit shared with the unreleased `devBranch` work stops the release.
- If `devBranch` is protected, the changelog commit goes through a short-lived PR/MR instead of a direct push.

## Assumptions and limits

- Two long-lived branches (integration → production), git-flow style. Single-trunk repositories are not supported.
- One version per repository: a single tag stream and a single changelog. Monorepos with per-package tags are not supported.
- The changelog follows [Keep a Changelog](https://keepachangelog.com/) with `## [Unreleased]` and `## [vX.Y.Z] - date` headings, and commits follow Conventional Commits.
- Shell commands assume a POSIX shell (bash; Git Bash on Windows). The hotfix guard uses bash process substitution.
- PR/MR automation covers GitHub and GitLab; every other host goes through `prCli: "none"`.
- The skill is an LLM-executed prompt, not a script: it is deterministic where it runs git commands and depends on the model following the text elsewhere. The confirmation step and the git-verified checks exist for that reason.

## Updating

The plugin cache is keyed by the `version` in `plugin.json`. **A change that reaches the production branch without a version bump is never delivered to installed copies.** This repository releases itself with `git-release` (see `.claude/release-kit.json` at the repo root), which bumps `plugin.json` on the release branch before tagging, so the version always matches the tag — `v1.0.0` is the one exception (it still declares `0.1.0`; the next release fixes it).

```bash
# in each consumer project:
claude plugin update release-kit
```

Pin a specific version per project by adding `"ref": "<tag-or-sha>"` to the
`source` object in that project's `extraKnownMarketplaces`. Pin a tag whose `plugin.json` version matches the tag.

## Testing

```bash
python3 scripts/validate.py          # needs: pip install jsonschema
claude plugin validate .             # marketplace + plugin manifests
```

`scripts/validate.py` validates the schema and every config example, rejects malformed configs, checks that every `{{key}}` in the skill and every config key in the commands exists in the schema, and runs the hotfix guard, latest-tag and merged-check commands from the prompts against throwaway git repositories. CI runs it on every push and pull request, and on tags it also checks that `plugin.json` matches the tag.

Manual checklist — run `/git-release` in a scratch repo with a fake `.claude/release-kit.json`:

- [ ] No config file → skill STOPs and prints the template
- [ ] `prCli: gh` → output uses `gh pr create` / `gh pr merge`, never `glab`
- [ ] `prCli: glab` → output uses `glab mr create --yes` / `glab mr merge`, never `gh`
- [ ] `prCli: none` → skill prints title/body and waits, then verifies the merge before tagging
- [ ] Tag step targets `origin/<mainBranch>`, never dev/release branch, and never runs before the merge check prints `MERGED`
- [ ] `modes` without `quick` + user asks "quick release" → skill refuses (same for `hotfix` / `standard`)
- [ ] `versionFiles: []` → no version-bump step; with entries → bump commit appears before the PR/MR
- [ ] Skill asks for confirmation before the PR/MR merge
- [ ] Phase 2 includes the "Reconcile with main" step
- [ ] Stop the Ship phase after the PR merged (before tagging), run again → it tags without opening a second PR/MR
- [ ] Hotfix branch cut from `dev` → skill STOPs; cut from `main` → continues
- [ ] Summary prints the "reconcile dev with main" action for the user
- [ ] `/git-sync` on a `fix/*` branch cut from `release/vX.Y.Z` rebases onto that release branch, not `dev`

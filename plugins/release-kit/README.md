# release-kit

Release workflow for git projects with an integration branch and a production branch.

| Component | Type | What it does |
| --- | --- | --- |
| `git-release` | skill | Cut a release branch, compile the CHANGELOG from merged PRs/MRs, ship to the production branch, tag. Standard / quick / hotfix, resumable. Driven by a per-project config file. |
| `git-commit` | command | Branch-safety check and grouped conventional commits. |
| `git-mr` | command | Push the branch and open a PR/MR whose description carries the `## Changelog` section the release is built from. |
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

`git-release` needs the file and stops without it. `git-commit`, `git-mr` and `git-sync` read it when it exists and fall back to the defaults below when it does not.

| Field | Meaning | Default |
| --- | --- | --- |
| `prCli` | `gh`, `glab`, or `none` — `none` works with any host: the skill prints the title/body, you open and merge the PR/MR (merge commit) in the UI, and it verifies the merge with git before tagging | — |
| `remote` | git remote used for every fetch/push/tag | `origin` |
| `devBranch` / `mainBranch` | integration branch / production branch | `dev` / `main` |
| `qaBranches` | long-lived QA branches; `git-commit` cuts `fix/*` from them, `git-mr` refuses to open a PR/MR from them and can target them, `git-sync` rebases those back onto them | `["testing", "staging"]` |
| `tagPrefix` | prefix of tags, `release/*` branches and changelog headings (`""` for bare tags such as MinVer's default) | `v` |
| `tagAnnotated` | `true` creates annotated tags (`git tag -a`) | `false` |
| `versioningNote` | one line on how the version is derived (echoed in summaries) | omitted |
| `versionFiles` | JSON files (`package.json`, `plugin.json`, ...) whose `"version"` is bumped to the tag on the release branch; each entry takes an optional `bumpCmd` (`{version}` placeholder) | `[]` |
| `gate.mandatory` | the blocking verification command (Phase 2 / quick / hotfix) | — |
| `gate.phase1` | fail-fast check before cutting | `gate.mandatory` |
| `changelogPath` | changelog written by `git-release` | `CHANGELOG.md` |
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

## Changelog workflow

The release changelog is compiled from PR/MR descriptions, so feature and fix branches never edit `CHANGELOG.md`.

```text
feature/* or fix/*  --/git-mr-->  PR/MR with a "## Changelog" section  --merge-->  dev
                                                                                    |
                              /git-release (Cut): release/vX.Y.Z  <-----------------+
                              compiles "## [vX.Y.Z]" from the merged PRs/MRs, you review it
                                                    |
                  fix branches: /git-mr --> release/vX.Y.Z   (picked up when you ship)
                                                    |
                              /git-release (Ship): sync the changelog, review PR/MR, tag on main
```

**The `## Changelog` section** in every PR/MR description:

```markdown
## Changelog
- Added: Admins can disable a project to block its chatbot everywhere it's used.
- Fixed: Exports no longer fail for projects with no members.
```

Or just `none` when a reader of the changelog would not care. Categories are Added, Changed, Deprecated, Removed, Fixed, Security. A fix for a bug that never shipped in a released version is `none` — readers never saw the bug. `git-mr` drafts the section from your commits and asks before it opens the PR/MR.

**MR templates.** Add the two sections to your PR/MR template so nobody has to remember the format:

- GitLab: `.gitlab/merge_request_templates/Default.md`
- GitHub: `.github/pull_request_template.md`

```markdown
## Summary
<!-- 1-3 lines: why this change exists -->

## Changelog
<!-- One line per entry: "- Added: ...", "- Changed: ...", "- Fixed: ...". Write "none" when a reader of the changelog would not care. -->
```

A PR/MR with no usable `## Changelog` section is never dropped silently: `git-release` lists it at the review gate and asks what to do.

**Upgrading from v1.x** (`git-commit` used to write `## [Unreleased]`):

1. Add the template above to each project.
2. Run `claude plugin update release-kit`.
3. Entries still under `## [Unreleased]` are folded into the next release automatically.
4. PRs/MRs merged before the upgrade have no `## Changelog` section, so the first Cut lists them; write entries once, or pick "use the PR/MR titles" at the review gate.
5. Cut now requires `main` to be merged into `dev` (`git merge origin/main`), so the changelog on `dev` contains every released version.

## Safety and recovery

- The skill asks for confirmation right before the merge and the tag — the two steps it cannot undo.
- It never tags before the merge is verified (`git merge-base --is-ancestor`), never moves or deletes an existing tag, and never bypasses branch protection. If a merge is refused (required checks, approvals) it prints the PR/MR link and stops.
- A release that stopped halfway (PR merged, tag not pushed) is safe to resume: run `/git-release` and say "resume", or run it again — every irreversible step first checks whether it is already done.
- Hotfix branches are checked statelessly: any commit shared with the unreleased `devBranch` work stops the release.
- Quick release is the only workflow that commits to `devBranch` directly; if it is protected, that commit goes through a short-lived PR/MR instead of a direct push.

## Assumptions and limits

- Two long-lived branches (integration → production), git-flow style. Single-trunk repositories are not supported.
- One version per repository: a single tag stream and a single changelog. Monorepos with per-package tags are not supported.
- The changelog follows [Keep a Changelog](https://keepachangelog.com/) with a `## [Unreleased]` heading (kept empty) and `## [vX.Y.Z] - date` headings, commits follow Conventional Commits, and every PR/MR description carries a `## Changelog` section.
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
- [ ] `/git-mr` on `dev`, `main`, `release/*`, `hotfix/*` → refuses; on `hotfix/*` it points to `git-release`
- [ ] `feature/*` cut from `dev` → PR/MR targets `dev`; `fix/*` cut from `release/vX.Y.Z` → targets `release/vX.Y.Z`
- [ ] `/git-mr` again on a branch that already has a PR/MR → updates the description, no second PR/MR
- [ ] `prCli: none` → `/git-mr` pushes, prints title and description
- [ ] Cut while `main` has commits `dev` lacks → stops and asks to merge back
- [ ] Cut with PRs/MRs that have no `## Changelog` section → they are listed at the review gate, not dropped
- [ ] First Cut with no release tag → asks where to start
- [ ] Merge a fix PR/MR into `release/vX.Y.Z` after the cut, then Ship → its entry is added and the heading date becomes the ship date
- [ ] Stop Cut right after the branch is cut, then Ship → the section is built from the cut point, without dev's later PRs/MRs
- [ ] Entries left under `## [Unreleased]` are folded into the new section and `[Unreleased]` ends up empty

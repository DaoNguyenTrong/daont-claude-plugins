---
name: git-release
description: 'Release a new version: finalize CHANGELOG, cut a release/vX.Y.Z QA-stabilization branch, then (once stabilized) merge to the production branch and tag. Config-driven per project via .claude/release-kit.json — supports GitHub (gh), GitLab (glab) or any host (manual PR/MR), optional quick release (dev → main in one pass), hotfix, and resuming an interrupted release. The git tag is the version (MinVer or equivalent); optional version files (package.json, plugin.json, ...) are bumped to match. Examples: "Release v1.1.0", "Release patch", "Cut the release", "Ship the release", "Quick release v1.1.0", "Hotfix v1.2.1", "Resume the release"'
---

# Git Release

Automates the release workflow with CHANGELOG and git tag. **The git tag is the source of the version** (MinVer or an equivalent tag-derived scheme); there is no backend version file to bump. Files that carry a copy of the version (a frontend `package.json`, a `plugin.json`, ...) are listed in `versionFiles` and bumped on the release branch, so the tagged commit already contains them.

Commands below assume a POSIX shell (bash, or Git Bash on Windows).

## 0. Load project config — do this first, before any git command

Read `.claude/release-kit.json` at the repository root.

- **Missing, unparsable, or failing the checks below** → **STOP**. Print the template below (and the failing check), and ask the user to create or fix it. Do not guess values.
- **Valid** → print a table of the resolved values (`prCli`, `remote`, `devBranch`, `mainBranch`, `tagPrefix`, `tagAnnotated`, `gate.*`, `modes`, `versionFiles`, `changelogPath`) and continue.

**Validity checks** (the schema `release-kit.schema.json` is authoritative; if `ajv` or `check-jsonschema` is installed you may run it instead):

- `prCli` ∈ `gh` | `glab` | `none`; `gate.mandatory` is a non-empty string; `modes` is a non-empty subset of `standard` | `quick` | `hotfix`.
- No keys other than those in the schema (typos like `devbranch` are errors, not ignored).
- `versionFiles` and the legacy `frontendVersionFile` are not both present.

**Defaults** for omitted keys: `remote` = `origin`, `devBranch` = `dev`, `mainBranch` = `main`, `tagPrefix` = `v`, `tagAnnotated` = `false`, `changelogPath` = `CHANGELOG.md`, `versionFiles` = `[]`, `gate.phase1` = `gate.mandatory`. `versioningNote` and `ciTriggerNote` have no default — leave their lines out of summaries when absent.

**Legacy keys:** `frontendVersionFile` (+ `frontendVersionBumpCmd`) is treated as a single `versionFiles` entry `{ "path": <file>, "bumpCmd": <cmd> }`. `null` = no entries.

**Notation used throughout this skill:**

- `{{name}}` means "the value of `name` from that config" — **not** a shell variable. Substitute it yourself before running a command.
- `origin` stands for `{{remote}}`.
- `vX.Y.Z` stands for `{{tagPrefix}}X.Y.Z`, e.g. the tag, `release/vX.Y.Z`, and the `## [vX.Y.Z]` changelog heading. The bare `X.Y.Z` (no prefix) goes into version files.

Minimal template:

```json
{
  "$schema": "https://raw.githubusercontent.com/DaoNguyenTrong/daont-claude-plugins/main/plugins/release-kit/release-kit.schema.json",
  "prCli": "gh",
  "devBranch": "dev",
  "mainBranch": "main",
  "versioningNote": "backend via MinVer (git tag); frontend not versioned",
  "versionFiles": [],
  "gate": {
    "phase1": "dotnet test backend/Solution.sln --no-restore -m:1 && bun run --cwd frontend test:run",
    "mandatory": "dotnet test backend/Solution.sln --no-restore -m:1 && bun run --cwd frontend test:run"
  },
  "changelogPath": "CHANGELOG.md",
  "ciTriggerNote": ".github/workflows/release.yml triggers on tag push; CI runs after the tag, there is no PR CI",
  "modes": ["standard", "hotfix"]
}
```

---

## Modes

- **Standard release**: `{{devBranch}} → release/vX.Y.Z → {{mainBranch}}`. Two phases, run as separate skill invocations because QA stabilization happens in between and can take any amount of time — **Cut** (finalize CHANGELOG on `{{devBranch}}`, branch off) and **Ship** (test, merge, tag).
- **Quick release** (only if `"quick"` is in `{{modes}}`): `{{devBranch}} → {{mainBranch}}` directly, one pass, no stabilization branch. Triggered by the user passing `quick` — never inferred.
- **Hotfix**: `{{mainBranch}} → hotfix/… → {{mainBranch}}`. The branch name is cosmetic (`hotfix/vX.Y.Z` is the convention, but `hotfix/<description>` is accepted); only the git tag must be `vX.Y.Z`.

A workflow that is not in `{{modes}}` is **refused**: say which mode was requested and that `.claude/release-kit.json` does not enable it (`standard` covers both Cut and Ship). Do not run it.

After a release or hotfix ships, the user reconciles `{{devBranch}}` with `{{mainBranch}}` themselves (merge `{{mainBranch}}` into `{{devBranch}}`) — this skill does not do it. The skill only reminds them in its final summary.

Detect the mode/phase from the current branch and the user's words:

- User asks to resume, finish or continue an interrupted release → **Resuming** (below), from any branch.
- On `{{devBranch}}`, user said `quick` (and `quick` is enabled) → **Quick release**.
- On `{{devBranch}}`, no `quick` → **Standard release, Phase 1: Cut**.
- On `release/vX.Y.Z` → **Standard release, Phase 2: Ship**. (`quick` does not apply here — the branch already exists; point that out and ask if the user seems confused.)
- On any `hotfix/*` branch, or an explicit hotfix request from any branch → **Hotfix**. The branch name need not carry the version — `git-commit` names it `hotfix/<description>` before the version is known — and the Hotfix workflow settles the version itself.
- `quick` requested while not on `{{devBranch}}` → stop and ask: quick release only starts from `{{devBranch}}`.
- On `{{mainBranch}}` (or any other branch) with no hotfix request → first look for an **interrupted release** (see *Resuming*). If there is none, stop and ask.

### Resuming an interrupted release

Every workflow ends with irreversible steps (merge, tag, push) that can fail halfway. Each of those steps first checks whether it is already done, so re-running the skill is safe. To find out where a release stopped:

```bash
git fetch origin
git log origin/{{mainBranch}} --merges -5 --format='%h %s'      # "Release vX.Y.Z" / "Hotfix vX.Y.Z" = merged
git ls-remote --tags origin 'refs/tags/{{tagPrefix}}*'           # is that tag pushed?
```

If the latest `Release vX.Y.Z` / `Hotfix vX.Y.Z` merge on `{{mainBranch}}` has no matching tag on the remote, the merge happened but tagging did not: offer to run **the tag step only** for that version (see *Tag step*), then print that workflow's summary. Do not open another PR/MR.

---

## Determine version (all modes)

- User provides a version (e.g. `v1.2.0`) → use it.
- User says `major` / `minor` / `patch` → bump from the latest release tag. (Hotfix always bumps `patch`.)
- No version given → read the latest release tag, suggest the next minor (hotfix: next patch). Ask to confirm.
- **No tags exist yet** → there is no "latest tag" to bump from. Ask the user for the starting version explicitly — do not assume `v1.0.0`.

Latest release tag (only tags that are exactly `<prefix>X.Y.Z`; pre-releases such as `v1.1.0-rc.1` and unrelated tags are skipped — the filter anchors on the prefix, so a prefix containing `-` works):

```bash
git tag --list '{{tagPrefix}}[0-9]*' --sort=-v:refname | grep -E '^{{tagPrefix}}[0-9]+\.[0-9]+\.[0-9]+$' | head -1
```

Then validate the chosen version — **stop** if either check fails:

```bash
git rev-parse -q --verify refs/tags/vX.Y.Z                 # must print nothing (tag not local)
git ls-remote --exit-code --tags origin refs/tags/vX.Y.Z   # must exit 2 (tag not on remote)
```

and it must be greater than the latest release tag (compare as versions, not text).

For **hotfix**, run this step from within the Hotfix workflow (step 2), *after* you are on the branch — the branch may already exist under a non-version name, and only the git tag has to be `vX.Y.Z`.

---

## Shared steps (referenced from the workflows below)

### Open and merge the PR/MR

Inputs: `<source>`, `<target>`, `<title>`, `<body>` (the `## [vX.Y.Z]` entries from `{{changelogPath}}`), and whether the source branch may be deleted (yes for `release/*` and `hotfix/*`, **never** for `{{devBranch}}`).

**Already merged? Check first — this makes re-runs safe.** `git merge-base --is-ancestor` is host-independent:

```bash
git fetch origin
git merge-base --is-ancestor origin/<source> origin/<target> && echo MERGED
```

If the host already deleted `origin/<source>`, look for the merge commit instead: `git log origin/<target> --merges -50 --format=%s | grep -Fx "<title>"`. If merged → skip to the tag step. Otherwise continue.

**If `{{prCli}}` is `gh`:**

```bash
gh pr list --head <source> --base <target> --state open --json number --jq '.[0].number'   # a number → reuse that PR, skip create
gh pr create --base <target> --head <source> --title "<title>" --body "<body>"
gh pr merge <number> --merge --subject "<title>" [--delete-branch]
```

**If `{{prCli}}` is `glab`:**

```bash
glab mr list --source-branch <source> --target-branch <target>     # open MRs; reuse one if listed, skip create
glab mr create --source-branch <source> --target-branch <target> --title "<title>" --description "<body>" --yes
glab mr merge <source> --yes -m "<title>" [--remove-source-branch]
```

**If `{{prCli}}` is `none`** (any host): print `<source>`, `<target>`, `<title>` and `<body>`, and ask the user to open the PR/MR and merge it with a **merge commit** (not squash or rebase — the merged check and the reconcile step rely on it), using `<title>` as the merge commit subject. Wait for the user to say it is merged.

**Always verify before continuing.** Run the *Already merged?* check again. `glab mr merge` may only queue the merge (auto-merge when the pipeline succeeds), and a user may take a while with `none` — never tag until the check prints `MERGED`.

**If the merge is refused** (required checks, approvals, branch protection): do **not** retry with `--admin` or any bypass. Print the PR/MR link and the reason, ask the user to get it merged (or wait for checks), and stop. Re-running the skill resumes from the *Already merged?* check.

### Bump version files

For each entry in `{{versionFiles}}` (skip this step when there are none):

- With `bumpCmd` → run it from the file's directory, `{version}` → `X.Y.Z`.
- Otherwise → set the top-level `"version"` field of `path` to `X.Y.Z`, changing only that line.
- Skip an entry that already reads `X.Y.Z`.

If anything changed, commit on the branch the workflow names and push (a protected-branch rejection on `{{devBranch}}` → *Protected branch fallback*):

```bash
git add <changed files>
git commit -m "chore: bump version to vX.Y.Z"
git push origin <branch>
```

### Confirm before shipping

Merge and tag cannot be undone by this skill. Before the PR/MR step, print: version, `<source> → {{mainBranch}}`, `{{prCli}}`, the commit count (`git rev-list --count origin/{{mainBranch}}..HEAD`), and that the gate passed. **Ask the user to confirm.** Skip the question only if the user's request already said to proceed without asking.

### Tag step

Always tag `origin/{{mainBranch}}` after the merge — never `{{devBranch}}`, the release branch, or the hotfix branch. Only run it once the merge is verified.

```bash
git fetch origin
git ls-remote --tags origin refs/tags/vX.Y.Z        # already pushed?
```

- **Not pushed yet** →

  ```bash
  git tag vX.Y.Z origin/{{mainBranch}}                                  # {{tagAnnotated}} = false
  git tag -a vX.Y.Z -m "Release vX.Y.Z" origin/{{mainBranch}}           # {{tagAnnotated}} = true
  git push origin vX.Y.Z
  ```

- **Already pushed** → never move it. Confirm it belongs to this release (`git fetch origin tag vX.Y.Z` then `git merge-base --is-ancestor vX.Y.Z^{commit} origin/{{mainBranch}}`). If yes, report "tag already exists" and go on to the summary; if not, **STOP**.

### Protected branch fallback

If a push straight to `{{devBranch}}` is rejected because the branch is protected, do not force it. Move the commit onto a short-lived branch and go through a PR/MR:

```bash
git checkout -b chore/release-vX.Y.Z-changelog           # the branch keeps the commit made on {{devBranch}}
git branch -f {{devBranch}} origin/{{devBranch}}          # local {{devBranch}} goes back to the remote; the commit lives on the new branch
git push -u origin chore/release-vX.Y.Z-changelog
```

Then run *Open and merge the PR/MR* with source = that branch, target = `{{devBranch}}`, title = the commit subject, deleting the source branch. Once merged, `git checkout {{devBranch}} && git pull --ff-only` and continue the workflow from the step after the push.

---

## Standard Release Workflow

### Phase 1: Cut the release branch (run on `{{devBranch}}`)

#### 1. Pre-flight checks

```bash
git branch --show-current                                    # must be {{devBranch}}
git fetch origin
git status --porcelain                                        # must be clean
git rev-list --left-right --count origin/{{devBranch}}...{{devBranch}}   # must be "0	0"
git ls-remote --exit-code --heads origin release/vX.Y.Z       # must exit 2 (branch not cut yet)
```

**Stop and warn** if not on `{{devBranch}}`, the working directory is dirty, or `{{devBranch}}` is not even with `origin/{{devBranch}}` in either direction. If it is only *behind*, offer `git pull --ff-only` and continue. If `release/vX.Y.Z` already exists on the remote, **stop**: it was cut already — check it out and run Phase 2. Version checks (tag must not exist) are in *Determine version*.

#### 2. Run the gate (fail-fast, not the mandatory gate)

```bash
{{gate.phase1}}
```

**Stop and report** if it fails — don't cut a release branch from a known-broken `{{devBranch}}`. (Phase 2's run is the mandatory gate; this one just avoids wasted stabilization effort.)

#### 3. Finalize `{{changelogPath}}` on `{{devBranch}}`

The `git-commit` command adds entries under `## [Unreleased]`. This step promotes that section to the release version.

1. Replace `## [Unreleased]` with `## [vX.Y.Z] - YYYY-MM-DD`
2. Add a new empty `## [Unreleased]` section above it

Before / after:

```markdown
## [Unreleased]

### Added

- some feature
```

```markdown
## [Unreleased]

## [vX.Y.Z] - YYYY-MM-DD

### Added

- some feature
```

**Do not edit this entry again on the release branch** — stabilization fixes change code, not this section, which keeps the `release/vX.Y.Z → {{mainBranch}}` merge clean.

**Stop and warn** if `## [Unreleased]` has no entries — there is nothing to release. **Exception (resume):** if a `## [vX.Y.Z]` section already exists and `[Unreleased]` is empty, an earlier run already promoted it — skip this step and go to step 4 (if `origin/{{devBranch}}` lacks that commit, push it first).

Commit and push (already on `{{devBranch}}` per pre-flight):

```bash
git add {{changelogPath}}
git commit -m "docs: update CHANGELOG for vX.Y.Z"
git push origin {{devBranch}}
```

If the push is rejected as protected, use the *Protected branch fallback*.

#### 4. Cut the release branch

```bash
git checkout -b release/vX.Y.Z {{devBranch}}
git config branch.release/vX.Y.Z.releaseKitBase {{devBranch}}
git push -u origin release/vX.Y.Z
```

#### 5. Summary

Print:

- Release branch name and version
- Reminder: QA stabilizes on `release/vX.Y.Z` from here — bugs go through `fix/*` branched off `release/vX.Y.Z`, PR'd/MR'd back into it. (`git-commit` creates those branches and `git-sync` keeps them on top of the release branch.)
- Reminder: run this skill again on `release/vX.Y.Z` (Phase 2) once stabilization is done

**Stop here.** Do not proceed to Phase 2 in the same run.

---

### Phase 2: Ship (run on `release/vX.Y.Z`)

Resumable: if the run stops after step 6 has started, run the skill again — steps 6 and 7 detect what is already done.

#### 1. Pre-flight checks

```bash
git branch --show-current                                                   # must be release/vX.Y.Z
git fetch origin
git status --porcelain                                                       # must be clean
git rev-list --left-right --count origin/release/vX.Y.Z...release/vX.Y.Z     # must be "0	0"
```

**Stop and warn** if not on a `release/*` branch, the working directory is dirty, or the branch is not even with its remote. (If the release branch is already merged, jump to *Resuming an interrupted release*.)

#### 2. Reconcile with `{{mainBranch}}`

A hotfix may have shipped to `{{mainBranch}}` during this release's stabilization window. Pull it into the release branch before opening the PR/MR, or the merge conflicts (CHANGELOG especially — the hotfix added its own `## [vX.Y.Z]` section).

```bash
git fetch origin
git log --oneline release/vX.Y.Z..origin/{{mainBranch}}
```

If non-empty:

```bash
git merge origin/{{mainBranch}}
# resolve conflicts — CHANGELOG: keep BOTH the hotfix section and this release's
# section, hotfix section directly above the previous release
git push origin release/vX.Y.Z
```

#### 3. Run the gate — mandatory

```bash
{{gate.mandatory}}
```

**Stop and report** if it fails — do not open the release PR/MR. Unlike Phase 1's run, this one cannot be skipped: `fix/*` changes may have landed since the cut.

Gate context: {{ciTriggerNote}} — so this local run is the release's verification before the tag. (Omit this line if `ciTriggerNote` is absent.)

#### 4. Bump version files

Run *Bump version files* on `release/vX.Y.Z`.

#### 5. Confirm

Run *Confirm before shipping*.

#### 6. Open and merge the release PR/MR

Run *Open and merge the PR/MR*: source `release/vX.Y.Z`, target `{{mainBranch}}`, title `Release vX.Y.Z`, delete the source branch.

#### 7. Tag

Run the *Tag step*.

#### 8. Summary

Print:

- Release version, PR/MR link, tag name, number of commits included
- `{{versioningNote}}` (if set)
- **Action for the user:** reconcile `{{devBranch}}` with `{{mainBranch}}` — `git checkout {{devBranch}} && git pull && git merge origin/{{mainBranch}} && git push` (if `{{devBranch}}` is protected, open a PR/MR from `{{mainBranch}}` into it instead). Do this before the next `git-commit` or release so `{{devBranch}}` carries the stabilization fixes and the tag history.
- Reminder: delete merged `fix/*` branches; drop the local branch with `git branch -d release/vX.Y.Z`

---

## Quick Release Workflow (only if `"quick"` in `{{modes}}`)

Run on `{{devBranch}}`, triggered by the user passing `quick`. Collapses the two phases into one pass: no stabilization branch, no separate QA window. Because there is no later gate, **the gate here is mandatory**. Resumable in the same way as Phase 2.

#### 1. Determine version

As above.

#### 2. Pre-flight checks

Same as Standard Phase 1, step 1 (`{{devBranch}}` even with its remote, clean, etc.), without the `release/vX.Y.Z` existence check.

#### 3. Run the gate — mandatory

```bash
{{gate.mandatory}}
```

**Stop and report** on failure — quick mode has no second gate.

#### 4. Finalize `{{changelogPath}}` on `{{devBranch}}`

Same as Standard Phase 1, step 3 — promote `## [Unreleased]` to `## [vX.Y.Z] - YYYY-MM-DD`, add a fresh empty `## [Unreleased]`. **Stop and warn** if `[Unreleased]` is empty (unless resuming — a `## [vX.Y.Z]` section already exists).

```bash
git add {{changelogPath}}
git commit -m "docs: update CHANGELOG for vX.Y.Z"
git push origin {{devBranch}}
```

#### 5. Bump version files

Run *Bump version files* on `{{devBranch}}`.

#### 6. Confirm

Run *Confirm before shipping* (source `{{devBranch}}`).

#### 7. Open and merge the PR/MR straight into `{{mainBranch}}`

Run *Open and merge the PR/MR*: source `{{devBranch}}`, target `{{mainBranch}}`, title `Release vX.Y.Z`. **Never delete `{{devBranch}}`** — omit the delete flag.

#### 8. Tag

Run the *Tag step*.

#### 9. Summary

Print: version, PR/MR link, tag, commit count, `{{versioningNote}}` (if set), and that this was a quick release (no `release/*` branch). Reconcile reminder still applies if `{{mainBranch}}` and `{{devBranch}}` have diverged.

---

## Hotfix Workflow (`{{mainBranch}} → hotfix/… → {{mainBranch}}`)

Use when a critical bug must be fixed on production without including unreleased changes from `{{devBranch}}`.

### 1. Get onto a hotfix branch based on `{{mainBranch}}`

```bash
git fetch origin
git branch --show-current
git status --porcelain
```

The hotfix branch **must** be cut from `{{mainBranch}}` — a branch based on `{{devBranch}}` would drag unreleased work into production. Pick the case that matches:

- **Already on a `hotfix/*` branch** (any name) → adopt it and verify it carries no unreleased `{{devBranch}}` commits. The check is stateless — it looks at the commits themselves, so it is the same on first entry and on re-entry:

  ```bash
  git rev-list origin/{{mainBranch}}..HEAD | grep -F -x -f <(git rev-list origin/{{mainBranch}}..origin/{{devBranch}})
  ```

  - First make sure `git rev-parse --verify origin/{{devBranch}}` succeeds — if the branch does not exist the check passes vacuously, so **STOP** and point at the `devBranch` config.
  - **Prints any commit** → **STOP**: those commits are unreleased work from `{{devBranch}}`, so the branch was cut from `{{devBranch}}` (or merged it); shipping it would put them in production. Ask the user to re-cut the branch from `{{mainBranch}}` and cherry-pick the fix.
  - **Prints nothing** → the base is fine. Now decide where you are:

    ```bash
    git rev-list --count origin/{{mainBranch}}..HEAD
    ```

    - **`0`** (no fix commit yet) → this is the hand-off point: go to **Stop here** below.
    - **`> 0`** (fix committed) → require a clean tree (`git status --porcelain` empty; otherwise ask the user to commit or stash) and continue to step 2.

- **On `{{mainBranch}}`, or any other branch, with a hotfix request** → create the branch from `{{mainBranch}}`. A dirty working tree is OK here — `checkout -b` carries the uncommitted fix onto the new branch.

  ```bash
  git show-ref --verify --quiet refs/heads/hotfix/<name> && echo LOCAL-EXISTS
  git ls-remote --exit-code --heads origin hotfix/<name> && echo REMOTE-EXISTS
  # neither exists:
  git checkout -b hotfix/<name> origin/{{mainBranch}}
  git config branch.hotfix/<name>.releaseKitBase {{mainBranch}}
  git push -u origin hotfix/<name>
  ```

  - Local branch already exists → `git checkout hotfix/<name>` and run the stateless check above.
  - Only the remote branch exists → `git checkout -b hotfix/<name> origin/hotfix/<name>`, confirm it is even with the remote, then run the stateless check.
  - `<name>`: use `vX.Y.Z` if the user already gave a version; otherwise a short kebab description (matching `git-commit`'s convention). The version is settled in step 2.

**Stop here.** Ask the user to apply and commit the code fix on this branch, then run the skill again. (The CHANGELOG update in step 3 is handled by this skill — the user only commits the code fix.)

### 2. Settle the version

The fix is now on the branch. Determine the version per **Determine version** above — hotfix always bumps `patch` from the latest tag; a user-provided version wins.

If the branch name does not already carry it, offer to rename so the branch matches the tag:

```bash
git branch -m hotfix/vX.Y.Z
git push -u origin hotfix/vX.Y.Z
git push origin --delete <old-name>   # only if <old-name> was already pushed
```

Renaming is **optional** — only the git tag has to be `vX.Y.Z`. If the user keeps the descriptive name, use that name verbatim in every `git`/PR/MR command below (shown as `hotfix/vX.Y.Z` for brevity).

### 3. Update `{{changelogPath}}` on the hotfix branch

`[Unreleased]` on `{{devBranch}}` must NOT be touched from this branch. Insert a new release section directly above the previous release (skip if a `## [vX.Y.Z]` section already exists — resume):

```markdown
## [Unreleased]

## [v1.2.1] - YYYY-MM-DD

### Fixed

- <describe the hotfix>

## [v1.2.0] - 2026-05-01
```

```bash
git add {{changelogPath}}
git commit -m "docs: update CHANGELOG for vX.Y.Z"
git push origin hotfix/vX.Y.Z
```

### 4. Bump version files

Run *Bump version files* on the hotfix branch. All entries are bumped — a version file exists to match the tag, whichever part of the code the fix touches.

### 5. Run the gate — mandatory

```bash
{{gate.mandatory}}
```

**Stop and report** on failure — no PR/MR, no merge.

### 6. Confirm

Run *Confirm before shipping*.

### 7. Open and merge the hotfix PR/MR

Run *Open and merge the PR/MR*: source the hotfix branch, target `{{mainBranch}}`, title `Hotfix vX.Y.Z`, delete the source branch.

### 8. Tag

Run the *Tag step*.

### 9. Summary

Print:

- Hotfix version, PR/MR link, tag name
- **Action for the user:** merge `{{mainBranch}}` back into `{{devBranch}}` (`git checkout {{devBranch}} && git pull && git merge origin/{{mainBranch}} && git push`) so the fix and its CHANGELOG section reach `{{devBranch}}`. Resolve the CHANGELOG conflict by keeping the hotfix's `## [vX.Y.Z]` section above the previous release; leave `{{devBranch}}`'s `## [Unreleased]` untouched.

---

## Rules

- Never force push. Never bypass branch protection (`--admin`, `--no-verify`, force flags).
- Config first: if `.claude/release-kit.json` is missing or invalid, STOP and ask — never guess bindings.
- Never skip the gate: Standard Phase 1's run is fail-fast (report and stop, but its absence alone doesn't block a later Phase 2). Standard Phase 2's, Quick release's, and the hotfix's are the mandatory gate — a failure blocks the release (no PR/MR, no merge).
- Never skip the CHANGELOG finalization.
- Confirm with the user before the PR/MR merge and tag — they are the steps this skill cannot undo.
- Never tag until the merge is verified (`git merge-base --is-ancestor`), and never move or delete an existing tag.
- The git tag is the version — there is no backend version file. Only bump the files listed in `{{versionFiles}}`.
- Always tag `origin/{{mainBranch}}` after the merge — never `{{devBranch}}`, `release/*`, or the hotfix branch.
- `quick` mode must come from the user — never infer it or pick it to save time. It is only available if `"quick"` is in `{{modes}}`; `standard` and `hotfix` likewise must be listed.
- This skill never merges `{{mainBranch}}` back into `{{devBranch}}`. Reconciling the two is the user's step after the release/hotfix ships; the skill only prints the reminder. Until then, `{{devBranch}}` is missing the stabilization fixes and hotfixes that landed on `{{mainBranch}}`.
- Hotfix: never modify `{{devBranch}}`'s `[Unreleased]` section from the hotfix branch — insert the hotfix's own dated section instead. It reaches `{{devBranch}}` when the user merges `{{mainBranch}}` into it.
- Hotfix branch name is cosmetic — only the git tag must be `vX.Y.Z`. Adopt any `hotfix/*` branch, but before merging always run the stateless base check (no commit shared with `origin/{{mainBranch}}..origin/{{devBranch}}`). A hotfix branch based on `{{devBranch}}` would ship unreleased work to production.
- If any step fails, stop and report — do not continue. Re-running the skill resumes safely (see *Resuming an interrupted release*).

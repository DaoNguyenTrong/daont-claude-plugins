---
name: git-release
description: 'Release a new version: finalize CHANGELOG, cut a release/vX.Y.Z QA-stabilization branch, then (once stabilized) merge to the production branch and tag. Config-driven per project via .claude/release-kit.json — supports GitHub (gh) or GitLab (glab), optional quick release (dev → main in one pass), and hotfix. The git tag is the version (MinVer or equivalent); an optional frontend package.json bump is configurable. Examples: "Release v1.1.0", "Release patch", "Cut the release", "Ship the release", "Quick release v1.1.0", "Hotfix v1.2.1"'
---

# Git Release

Automates the release workflow with CHANGELOG and git tag. **The git tag is the source of the version** (MinVer or an equivalent tag-derived scheme); there is no backend version file to bump. A frontend `package.json` bump is optional and configured per project.

## 0. Load project config — do this first, before any git command

Read `.claude/release-kit.json` at the repository root.

- **Missing or invalid** → **STOP**. Print the template below and ask the user to create it. Do not guess values.
- **Valid** → print a table of the resolved values (`prCli`, `devBranch`, `mainBranch`, `gate.*`, `modes`, `frontendVersionFile`, `changelogPath`) and continue.

Throughout this skill, `{{name}}` means "the value of `name` from that config" — **not** a shell variable. Substitute it yourself before running a command.

Minimal template:

```json
{
  "$schema": "https://raw.githubusercontent.com/DaoNguyenTrong/daont-claude-plugins/main/plugins/release-kit/release-kit.schema.json",
  "prCli": "gh",
  "devBranch": "dev",
  "mainBranch": "main",
  "versioningNote": "backend via MinVer (git tag); frontend not versioned",
  "frontendVersionFile": null,
  "gate": {
    "phase1": "dotnet test backend/Solution.sln --no-restore -m:1 && bun run --cwd frontend test:run",
    "mandatory": "dotnet test backend/Solution.sln --no-restore -m:1 && bun run --cwd frontend test:run"
  },
  "changelogPath": "CHANGELOG.md",
  "ciTriggerNote": ".github/workflows/release.yml triggers on tag push; CI runs after the tag, there is no PR CI",
  "modes": ["standard", "hotfix"]
}
```

If `gate.phase1` is absent, use `gate.mandatory` for both.

---

## Modes

- **Standard release**: `{{devBranch}} → release/vX.Y.Z → {{mainBranch}}`. Two phases, run as separate skill invocations because QA stabilization happens in between and can take any amount of time — **Cut** (finalize CHANGELOG on `{{devBranch}}`, branch off) and **Ship** (test, merge, tag).
- **Quick release** (only if `"quick"` is in `{{modes}}`): `{{devBranch}} → {{mainBranch}}` directly, one pass, no stabilization branch. Triggered by the user passing `quick` — never inferred.
- **Hotfix**: `{{mainBranch}} → hotfix/vX.Y.Z → {{mainBranch}}`.

After a release or hotfix ships, the user reconciles `{{devBranch}}` with `{{mainBranch}}` themselves (merge `{{mainBranch}}` into `{{devBranch}}`) — this skill does not do it. The skill only reminds them in its final summary.

Detect the mode/phase from the current branch and the user's words:

- On `{{devBranch}}`, user said `quick` (and `quick` is enabled) → **Quick release**.
- On `{{devBranch}}`, no `quick` → **Standard release, Phase 1: Cut**.
- On `release/vX.Y.Z` → **Standard release, Phase 2: Ship**. (`quick` does not apply here — the branch already exists; point that out and ask if the user seems confused.)
- On `hotfix/vX.Y.Z`, or on `{{mainBranch}}` with an explicit hotfix request → **Hotfix**.
- `quick` requested while not on `{{devBranch}}` → stop and ask: quick release only starts from `{{devBranch}}`.
- Ambiguous (on `{{mainBranch}}` with no hotfix context, or an unrelated branch) → stop and ask.

---

## Determine version (all modes)

- User provides a version (e.g. `v1.2.0`) → use it.
- User says `major` / `minor` / `patch` → bump from the latest git tag. (Hotfix always bumps `patch`.)
- No version given → read the latest tag, suggest the next minor (hotfix: next patch). Ask to confirm.
- **No tags exist yet** → there is no "latest tag" to bump from. Ask the user for the starting version explicitly — do not assume `v1.0.0`.

---

## PR/MR commands (referenced below as "open and merge the PR/MR")

**If `{{prCli}}` is `gh`:**

```bash
gh pr create --base <target> --head <source> --title "<title>" --body "<changelog entries>"
gh pr merge <number> --merge --subject "<title>" --delete-branch
```

**If `{{prCli}}` is `glab`:**

```bash
glab mr create --source-branch <source> --target-branch <target> --title "<title>" --description "<changelog entries>" --yes
glab mr merge <source> --yes -m "<title>" --remove-source-branch
```

---

## Standard Release Workflow

### Phase 1: Cut the release branch (run on `{{devBranch}}`)

#### 1. Pre-flight checks

```bash
git branch --show-current                                    # must be {{devBranch}}
git fetch origin
git status --porcelain                                        # must be clean
git rev-list --left-right --count origin/{{devBranch}}...{{devBranch}}   # must be "0	0"
git tag --sort=-v:refname | head -1                           # latest tag
```

**Stop and warn** if not on `{{devBranch}}`, the working directory is dirty, or `{{devBranch}}` is not even with `origin/{{devBranch}}` in either direction. If it is only *behind*, offer `git pull --ff-only` and continue.

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

**Stop and warn** if `## [Unreleased]` has no entries — there is nothing to release.

Commit and push (already on `{{devBranch}}` per pre-flight):

```bash
git add {{changelogPath}}
git commit -m "docs: update CHANGELOG for vX.Y.Z"
git push origin {{devBranch}}
```

#### 4. Cut the release branch

```bash
git checkout -b release/vX.Y.Z {{devBranch}}
git push -u origin release/vX.Y.Z
```

#### 5. Summary

Print:

- Release branch name and version
- Reminder: QA stabilizes on `release/vX.Y.Z` from here — bugs go through `fix/*` branched off `release/vX.Y.Z`, PR'd/MR'd back into it
- Reminder: run this skill again on `release/vX.Y.Z` (Phase 2) once stabilization is done

**Stop here.** Do not proceed to Phase 2 in the same run.

---

### Phase 2: Ship (run on `release/vX.Y.Z`)

#### 1. Pre-flight checks

```bash
git branch --show-current                                                   # must be release/vX.Y.Z
git fetch origin
git status --porcelain                                                       # must be clean
git rev-list --left-right --count origin/release/vX.Y.Z...release/vX.Y.Z     # must be "0	0"
```

**Stop and warn** if not on a `release/*` branch, the working directory is dirty, or the branch is not even with its remote.

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

Gate context: {{ciTriggerNote}} — so this local run is the release's verification before the tag.

#### 4. Bump the frontend version (only if `{{frontendVersionFile}}` is not null)

Set the `"version"` field of `{{frontendVersionFile}}` to `X.Y.Z` (no leading `v`). If `frontendVersionBumpCmd` is set, run it (from that file's directory, `{version}` → `X.Y.Z`) instead of editing the JSON.

```bash
git add {{frontendVersionFile}}
git commit -m "chore: bump frontend version to vX.Y.Z"
git push origin release/vX.Y.Z
```

#### 5. Open and merge the release PR/MR

- source: `release/vX.Y.Z`, target: `{{mainBranch}}`, title: `Release vX.Y.Z`
- body/description: the `## [vX.Y.Z]` entries from `{{changelogPath}}`
- Use the `{{prCli}}` commands above.

#### 6. Tag on `{{mainBranch}}` and push

Always tag `origin/{{mainBranch}}` after the merge — never `{{devBranch}}` or the release branch.

```bash
git fetch origin
git tag vX.Y.Z origin/{{mainBranch}}
git push origin vX.Y.Z
```

#### 7. Summary

Print:

- Release version, PR/MR link, tag name, number of commits included
- `{{versioningNote}}`
- **Action for the user:** reconcile `{{devBranch}}` with `{{mainBranch}}` — `git checkout {{devBranch}} && git pull && git merge origin/{{mainBranch}} && git push`. Do this before the next `git-commit` or release so `{{devBranch}}` carries the stabilization fixes and the tag history.
- Reminder: delete merged `fix/*` branches; drop the local branch with `git branch -d release/vX.Y.Z`

---

## Quick Release Workflow (only if `"quick"` in `{{modes}}`)

Run on `{{devBranch}}`, triggered by the user passing `quick`. Collapses the two phases into one pass: no stabilization branch, no separate QA window. Because there is no later gate, **the gate here is mandatory**.

#### 1. Determine version

As above.

#### 2. Pre-flight checks

Same as Standard Phase 1, step 1 (`{{devBranch}}` even with its remote, clean, etc.).

#### 3. Run the gate — mandatory

```bash
{{gate.mandatory}}
```

**Stop and report** on failure — quick mode has no second gate.

#### 4. Finalize `{{changelogPath}}` on `{{devBranch}}`

Same as Standard Phase 1, step 3 — promote `## [Unreleased]` to `## [vX.Y.Z] - YYYY-MM-DD`, add a fresh empty `## [Unreleased]`. **Stop and warn** if `[Unreleased]` is empty.

```bash
git add {{changelogPath}}
git commit -m "docs: update CHANGELOG for vX.Y.Z"
git push origin {{devBranch}}
```

#### 5. Bump the frontend version (only if `{{frontendVersionFile}}` is not null)

As in Phase 2, step 4, but commit on `{{devBranch}}`.

#### 6. Open and merge the PR/MR straight into `{{mainBranch}}`

- source: `{{devBranch}}`, target: `{{mainBranch}}`, title: `Release vX.Y.Z`
- Do **not** pass a branch-delete flag — never delete `{{devBranch}}`.
  - `gh`: `gh pr merge <number> --merge --subject "Release vX.Y.Z"`
  - `glab`: `glab mr merge {{devBranch}} --yes -m "Release vX.Y.Z"`

#### 7. Tag on `{{mainBranch}}` and push

```bash
git fetch origin
git tag vX.Y.Z origin/{{mainBranch}}
git push origin vX.Y.Z
```

#### 8. Summary

Print: version, PR/MR link, tag, commit count, `{{versioningNote}}`, and that this was a quick release (no `release/*` branch). Reconcile reminder still applies if `{{mainBranch}}` and `{{devBranch}}` have diverged.

---

## Hotfix Workflow (`{{mainBranch}} → hotfix/vX.Y.Z → {{mainBranch}}`)

Use when a critical bug must be fixed on production without including unreleased changes from `{{devBranch}}`.

### 1. Determine version

Always bump `patch` from the latest tag. User-provided version wins.

### 2. Pre-flight checks

```bash
git fetch origin
git status --porcelain                    # must be clean
git tag --sort=-v:refname | head -1
```

**Stop and warn** if the working directory is dirty.

### 3. Create the hotfix branch from `{{mainBranch}}`

```bash
git branch --show-current
```

- **Already on `hotfix/vX.Y.Z`** → skip creation, continue to step 4.
- **On a different `hotfix/*`** → stop and warn: another hotfix is in progress. Confirm the version.
- **Otherwise** → create it:

  ```bash
  git checkout -b hotfix/vX.Y.Z origin/{{mainBranch}}
  git push -u origin hotfix/vX.Y.Z
  ```

**Stop here.** Ask the user to apply and commit the code fix on this branch, then confirm when ready. (Step 4's CHANGELOG update is handled by this skill once they confirm — the user only commits the code fix.)

### 4. Update `{{changelogPath}}` on the hotfix branch

`[Unreleased]` on `{{devBranch}}` must NOT be touched from this branch. Insert a new release section directly above the previous release:

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

### 5. Bump the frontend version (only if `{{frontendVersionFile}}` is not null and the fix touches frontend)

As in Phase 2, step 4, committed on the hotfix branch.

### 6. Run the gate — mandatory

```bash
{{gate.mandatory}}
```

**Stop and report** on failure — no PR/MR, no merge.

### 7. Open and merge the hotfix PR/MR

- source: `hotfix/vX.Y.Z`, target: `{{mainBranch}}`, title: `Hotfix vX.Y.Z`

### 8. Tag on `{{mainBranch}}` and push

```bash
git fetch origin
git tag vX.Y.Z origin/{{mainBranch}}
git push origin vX.Y.Z
```

### 9. Summary

Print:

- Hotfix version, PR/MR link, tag name
- **Action for the user:** merge `{{mainBranch}}` back into `{{devBranch}}` (`git checkout {{devBranch}} && git pull && git merge origin/{{mainBranch}} && git push`) so the fix and its CHANGELOG section reach `{{devBranch}}`. Resolve the CHANGELOG conflict by keeping the hotfix's `## [vX.Y.Z]` section above the previous release; leave `{{devBranch}}`'s `## [Unreleased]` untouched.

---

## Rules

- Never force push.
- Config first: if `.claude/release-kit.json` is missing or invalid, STOP and ask — never guess bindings.
- Never skip the gate: Standard Phase 1's run is fail-fast (report and stop, but its absence alone doesn't block a later Phase 2). Standard Phase 2's, Quick release's, and the hotfix's are the mandatory gate — a failure blocks the release (no PR/MR, no merge).
- Never skip the CHANGELOG finalization.
- The git tag is the version — there is no backend version file. Only bump `{{frontendVersionFile}}` when it is set.
- Always tag `origin/{{mainBranch}}` after the merge — never `{{devBranch}}`, `release/*`, or the hotfix branch.
- `quick` mode must come from the user — never infer it or pick it to save time. It is only available if `"quick"` is in `{{modes}}`.
- This skill never merges `{{mainBranch}}` back into `{{devBranch}}`. Reconciling the two is the user's step after the release/hotfix ships; the skill only prints the reminder. Until then, `{{devBranch}}` is missing the stabilization fixes and hotfixes that landed on `{{mainBranch}}`.
- Hotfix: never modify `{{devBranch}}`'s `[Unreleased]` section from the hotfix branch — insert the hotfix's own dated section instead. It reaches `{{devBranch}}` when the user merges `{{mainBranch}}` into it.
- If any step fails, stop and report — do not continue.

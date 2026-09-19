---
description: "Sync the current branch with its remote: rebase short-lived branches onto the branch they were cut from, fast-forward long-lived ones. Handles stash, conflict detection, and divergence warnings."
---

# Git Sync

Sync the current branch with the latest remote changes. Optional argument: an explicit base branch (`/git-sync release/v1.2.0`), which overrides detection.

## 0. Resolve project settings

If `.claude/release-kit.json` exists and parses, read it. **This command never stops because the file is missing or invalid** — fall back to the defaults below.

| Setting | Config key | Default when absent |
| --- | --- | --- |
| Remote | `remote` | `origin` |
| Integration branch | `devBranch` | whichever of `dev` / `develop` exists on the remote |
| Production branch | `mainBranch` | `main`, else `master` |
| QA branches | `qaBranches` | `testing`, `staging` |

`origin` below stands for the configured remote.

## Steps

### 1. Pre-flight

```bash
git fetch origin
git branch --show-current            # empty = detached HEAD → stop and report
```

Decide what kind of branch this is:

**Long-lived / shared branches — fast-forward only, never rebase.** Rewriting their history would break everyone who has them checked out.

- Integration branch (`devBranch`), QA branches, `release/*`, production branch (`mainBranch`) → `git pull --ff-only origin <branch>`. If that fails because the branch diverged, stop and report; do not merge or rebase.
- On the integration branch, also report whether it lacks commits from the production branch: `git rev-list --count <dev>..origin/<main>`. If non-zero, tell the user to reconcile (`git merge origin/<main>`) — this command does not do it.

**Short-lived branches — rebase onto their base.** Find the base in this order and stop at the first hit:

1. The explicit argument, if given.
2. The base recorded when the branch was created (`git-commit` writes it):

   ```bash
   git config --get branch.<current>.releaseKitBase
   ```

3. By name:
   - `hotfix/*` → the production branch.
   - `feature/*`, `chore/*`, and any other short-lived branch → the integration branch.
   - `fix/*` → **not** always the integration branch: `git-commit` cuts `fix/*` from `release/*` and from QA branches too. Pick the closest candidate among the remote's `release/*` branches, the QA branches, and the integration branch — the one with the fewest commits ahead of it:

     ```bash
     git rev-list --count origin/<candidate>..HEAD
     ```

     On a tie prefer `release/*` over a QA branch over the integration branch. If several `release/*` branches tie, ask the user which one. Rebasing a release fix onto the integration branch would drag unreleased work into the release, so never fall back to it silently.

When the base came from step 3, store it so the next sync does not guess: `git config branch.<current>.releaseKitBase <base>`. The recorded base lives in the local `.git/config` — it is per clone, so a teammate who checks out the same branch starts from step 3. Tell the user which base was used and why.

### 2. Stash if dirty

```bash
git status --porcelain
```

If there are uncommitted changes, stash them:

```bash
git stash push -m "git-sync auto-stash"
```

Remember whether it printed "Saved" — if there was nothing to stash (for example, only untracked files), there is nothing to pop later.

### 3. Update

Fast-forward branches: run the `git pull --ff-only` from step 1, then go to step 5.

Rebase branches: count what is coming, then rebase onto the remote base directly (no need to check out or update the local base branch):

```bash
git rev-list --count HEAD..origin/<base>      # new commits pulled in
git rebase origin/<base>
```

If conflicts occur:

- **Stop immediately** — do not resolve anything.
- List conflicting files: `git diff --name-only --diff-filter=U`
- Run `git rebase --abort`
- Continue to step 5 so the stash is restored, then inform the user of the conflicts.

### 4. After a rebase

If the branch already exists on the remote, the rebase rewrote its history: pushing needs `git push --force-with-lease`, which this command never runs — tell the user, and let them decide.

### 5. Restore stash

If changes were stashed in step 2 (including after an aborted rebase):

```bash
git stash pop
```

If stash pop has conflicts, inform the user — the stash entry is kept.

### 6. Summary

Print:
- Branch synced
- Base branch used (and how it was chosen: argument, recorded, by name, or by distance)
- Number of new commits pulled
- Whether stash was applied
- Current status (`git status --short`)

## Rules

- Never force push. Never run `--force-with-lease` either — only suggest it.
- Never resolve conflicts automatically — always inform the user.
- Never rebase the production branch, the integration branch, a QA branch, or `release/*` onto anything; they only fast-forward.
- Never rebase a `fix/*` branch onto the integration branch unless that is its recorded or nearest base.
- If any step fails, stop and report (after restoring the stash).

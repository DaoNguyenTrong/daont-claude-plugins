---
description: "Pull latest from remote and rebase current branch onto its base branch. Handles stash, conflict detection, and divergence warnings."
---

# Git Sync

Sync the current branch with the latest remote changes.

## Steps

### 1. Pre-flight

```bash
git fetch origin
```

Detect the current branch and its base:

- `feature/*` or `fix/*` or `chore/*` → base is `develop` (fallback `dev`, then `main`)
- `hotfix/*` → base is `main` (fallback `master`)
- `develop` / `dev` → base is `main` (fallback `master`)
- `main` / `master` → just pull

### 2. Stash if dirty

```bash
git status --porcelain
```

If there are uncommitted changes, stash them:

```bash
git stash push -m "git-sync auto-stash"
```

### 3. Update base branch

```bash
git checkout <base-branch>
git pull origin <base-branch>
git checkout <original-branch>
```

### 4. Rebase onto base

```bash
git rebase <base-branch>
```

If conflicts occur:
- **Stop immediately**
- List conflicting files
- Run `git rebase --abort`
- Inform the user of the conflicts — do not attempt to resolve automatically

### 5. Restore stash

If changes were stashed in step 2:

```bash
git stash pop
```

If stash pop has conflicts, inform the user.

### 6. Summary

Print:
- Branch synced
- Base branch used
- Number of new commits pulled
- Whether stash was applied
- Current status (`git status --short`)

## Rules

- Never force push.
- Never resolve conflicts automatically — always inform the user.
- Never rebase `main`/`master` onto another branch.
- If any step fails, stop and report.

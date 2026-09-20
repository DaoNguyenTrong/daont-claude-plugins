---
description: "Commit all current changes: branch safety and grouped conventional commits."
---

# Git Commit Workflow

Commit all current changes following a structured workflow.

## 0. Resolve project settings

If `.claude/release-kit.json` exists and parses, read it. **This command never stops because the file is missing or invalid** — fall back to the defaults below.

| Setting | Config key | Default when absent |
| --- | --- | --- |
| Remote | `remote` | `origin` |
| Integration branch | `devBranch` | whichever of `dev` / `develop` exists on the remote |
| Production branch | `mainBranch` | `main`, else `master` |
| QA branches | `qaBranches` | `testing`, `staging` |

`develop` is also accepted as an integration branch, and `master` as a production branch, when the config names neither.

## Steps

### 1. Branch Safety Check

Check the current branch:

- **Integration branch** (`devBranch`, or `dev` / `develop`) → create a `feature/` branch:
  - Format: `feature/<short-kebab-case-description>`
  - `git checkout -b feature/<name>`
- **QA branch** (any of `qaBranches`, e.g. `testing` / `staging`) → create a `fix/` branch:
  - Format: `fix/<short-kebab-case-description>`
  - `git checkout -b fix/<name>`
- **Production branch** (`mainBranch`, or `main` / `master`) → create a `hotfix/` branch:
  - Format: `hotfix/<short-kebab-case-description>`
  - `git checkout -b hotfix/<name>`
  - The `git-release` hotfix workflow adopts this branch as-is — it settles the release version and (optionally) renames the branch to `hotfix/vX.Y.Z` at ship time. No need to know the version now.
- **`release/*`** (a release-stabilization branch, e.g. `release/vX.Y.Z`) → create a `fix/` branch off it:
  - Format: `fix/<short-kebab-case-description>`
  - `git checkout -b fix/<name>`
- **Already on a feature/fix/hotfix/chore/test branch** → stay on it, commit directly rather than spinning off a new branch.

Whenever this step creates a branch, record the branch it was cut from, so `git-sync` later rebases onto the right base instead of guessing:

```bash
git config branch.<new-branch>.releaseKitBase <source-branch>     # e.g. release/v1.2.0, staging, dev, main
```

Analyze changes to determine a descriptive branch name. Inform the user of the new branch.

### 2. Analyze Changes

Run in parallel:

```bash
git status
git diff
git log --oneline -5
```

### 3. Group and Commit

Group changed files into logical commits:

- Related changes together (e.g., all files for one feature, all test files, all config changes)
- Each group gets its own commit with a conventional commit message
- Format: `<type>(<scope>): <short description>` — type is `feat|fix|refactor|chore|docs|style|test`
- Focus on **why**, not **what**
- Language: write every commit message, PR/MR title and description, and changelog entry in English, whatever language the user talks to you in.
- Stage specific files per group: `git add <file1> <file2>`
- If all changes are tightly related, a single commit is fine — don't split artificially
- If there's a related plan file, include it in the commit

**Do not ask the user to confirm — commit immediately with the drafted message(s).**

End each commit message with the co-author trailer your environment specifies (for example, the attribution line in your system instructions). If it specifies none, add no trailer — do not invent one.

```bash
git commit -m "$(cat <<'EOF'
type(scope): message

<co-author trailer from your environment, if any>
EOF
)"
```

### 4. Next step

Once the commits are made, tell the user: run `/git-mr` to push the branch and open a PR/MR. The changelog entry is written in that PR/MR's `## Changelog` section, not in `CHANGELOG.md` — `git-release` compiles the release changelog from those sections.

## Rules

- `git add` specific files — NEVER use `git add .` or `git add -A`
- Never commit files containing secrets (`.env`, credentials)
- Never force push
- If any step fails, stop and report

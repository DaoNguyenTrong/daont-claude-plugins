---
description: "Commit all current changes: branch safety, grouped commits, and changelog update."
---

# Git Commit Workflow

Commit all current changes following a structured workflow.

## Steps

### 1. Branch Safety Check

Check the current branch:

- **`dev` / `develop` / `staging`** → create a `feature/` branch:
  - Format: `feature/<short-kebab-case-description>`
  - `git checkout -b feature/<name>`
- **`main` / `master`** → create a `hotfix/` branch:
  - Format: `hotfix/<short-kebab-case-description>`
  - `git checkout -b hotfix/<name>`
- **`release/*`** (a release-stabilization branch, e.g. `release/vX.Y.Z`) → create a `fix/` branch off it:
  - Format: `fix/<short-kebab-case-description>`
  - `git checkout -b fix/<name>`
- **Already on a feature/fix/hotfix/chore/test branch** → stay on it, commit directly rather than spinning off a new branch.

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
- Stage specific files per group: `git add <file1> <file2>`
- If all changes are tightly related, a single commit is fine — don't split artificially
- If there's a related plan file, include it in the commit

**Do not ask the user to confirm — commit immediately with the drafted message(s).**

```bash
git commit -m "$(cat <<'EOF'
type(scope): message

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

### 4. Update CHANGELOG.md

If `CHANGELOG.md` exists, update it:

- Add entries under `## [Unreleased]` (create the section if missing, directly below the intro preamble and above the latest released version)
- **What earns an entry:** a change someone reading the changelog would care about — user-facing behavior, API/contract, security, or developer-visible workflow/tooling. **Skip** pure formatting/`style` changes, test-infra or test-only changes that don't alter observable behavior, and internal refactors with no outward effect. If a whole group of commits is purely internal, add nothing.
- **Categories** (Keep a Changelog): `### Added`, `### Changed`, `### Deprecated`, `### Removed`, `### Fixed`, `### Security`. Keep sections in that order. If the target section already exists under `## [Unreleased]`, add to it — don't create a second one. Before adding, scan existing `[Unreleased]` entries and merge/revise instead of appending a near-duplicate.
- **Voice:** write in English, for a reader about to upgrade — not a diff reviewer. No first person (`we`/`I`); the subject is the feature, or `you` when addressing the end user. Keep tense consistent within a section: `Added` → present ("Admins can disable…") or noun phrase ("Optional Redis for shared cache"); `Fixed` → describe the bug as gone ("X no longer…", "X now works with…"); `Changed`/`Removed` → past ("Upgraded Postgres to 18", "Dropped HTTPS redirection…"). Neutral and factual — no marketing adjectives, no emoji, no jokes.
- Each entry: `- ` + **one short sentence, plain natural language** — what changed and why it matters to someone reading the changelog, not an implementation inventory.
  - Skip class/method names, full endpoint/parameter lists, and internal mechanism details unless essential to understand the change.
  - Aim for roughly one line (~20 words). If the underlying change is large, write one summarizing sentence rather than enumerating every sub-piece — save the detail for the commit body/diff.
  - Example — too long/technical: `Project disable toggle: Project.IsActive (default true), settable via PUT /api/projects/{id}. A disabled project blocks its chatbot everywhere it's reached — Chat Agent v1 and v2 (streaming and non-streaming), and a live expert's direct reply over the SignalR hub — for every caller including admins, returning 403 Forbidden.`
  - Example — good: `Admins can disable a project to block its chatbot everywhere it's used.`
- Commit separately: `docs: update changelog`

## Rules

- `git add` specific files — NEVER use `git add .` or `git add -A`
- Never commit files containing secrets (`.env`, credentials)
- Never force push
- If any step fails, stop and report

---
description: "Push the current branch and open a PR/MR with a short Summary, a Changelog section and a review checklist."
---

# Git MR Workflow

Push the current branch and open a pull/merge request against the branch it was cut from. The description carries a `## Changelog` section (`git-release` compiles the release changelog from it) and a `## Review` checklist that shows the reviewer exactly what was verified.

## 0. Resolve project settings

If `.claude/release-kit.json` exists and parses, read it. **This command never stops because the file is missing or invalid** — fall back to the defaults below.

| Setting | Config key | Default when absent |
| --- | --- | --- |
| Remote | `remote` | `origin` |
| PR/MR CLI | `prCli` | guessed from the remote URL: `github` → `gh`, `gitlab` → `glab`, anything else → `none` |
| Integration branch | `devBranch` | whichever of `dev` / `develop` exists on the remote |
| Production branch | `mainBranch` | `main`, else `master` |
| QA branches | `qaBranches` | `testing`, `staging` |

`origin` below stands for the configured remote. If `prCli` is `gh` or `glab` but that CLI is not installed or not logged in (`gh auth status` / `glab auth status` fails), continue in **manual mode**: do every step except creating the PR/MR, then print the title and description for the user to paste into the host's web UI.

## Steps

### 1. Branch check

```bash
git fetch origin
git branch --show-current            # empty = detached HEAD → stop
```

Refuse, and say why, on a detached HEAD; on the integration, production or QA branches and on `release/*` (shared branches — work reaches them through a PR/MR); and on `hotfix/*` (a hotfix PR/MR needs a version and its own changelog section, so `git-release` opens it). Anything else (`feature/*`, `fix/*`, `chore/*`, ...) is a work branch: continue.

### 2. Find the target branch

Take the first hit:

1. The explicit argument.
2. The base `git-commit` recorded: `git config --get branch.<current>.releaseKitBase`
3. By name. `fix/*` → the closest of the remote's `release/*` branches, the QA branches and the integration branch: fewest commits ahead (`git rev-list --count origin/<candidate>..HEAD`), on a tie `release/*` before a QA branch before the integration branch, several tied `release/*` → ask. Every other branch → the integration branch.

After a by-name hit, store it (`git config branch.<current>.releaseKitBase <base>`) and tell the user which target was used and why.

### 3. Check there is something to merge

```bash
git fetch origin
git rev-list --count origin/<base>..HEAD      # commits to merge
git rev-list --count HEAD..origin/<base>      # commits behind the base
git status --porcelain                        # uncommitted files
```

**`0` commits to merge** → stop. Behind the base or uncommitted files → warn (suggest `/git-sync` for the first) but continue; step 5 records both in the checklist.

### 4. Is there already a PR/MR for this branch?

Skip in manual mode. Look for an open one: `gh pr list --head <current> --base <base> --state open --json number,url` or `glab mr list --source-branch <current> --target-branch <base>`. Found → **update mode**: steps 5-8 refresh its title and description instead of creating a second one.

### 5. Draft the title and description

```bash
git log --format='%h %s%n%b' origin/<base>..HEAD
git diff --numstat origin/<base>...HEAD
```

Language: write every commit message, PR/MR title and description, and changelog entry in English, whatever language the user talks to you in. That covers the title and every section below.

**Title** — `<type>(<scope>): <short description>`, at most 72 characters. A single commit → reuse its subject. Several → one line covering the change as a whole, with the type of the most significant commit (`feat|fix|refactor|chore|docs|style|test`).

**Description** — at most 15 lines, exactly these three sections and nothing else (more detail goes in a comment):

```markdown
## Summary
<1-2 lines: why this change exists, not what the diff shows>

## Changelog
- <Category>: <one sentence>

## Review
- [x] Up to date with `<base>`
- [x] Everything committed
- [x] Tests: `<command>` passed
- [ ] Breaking change: <what breaks>
- [ ] Look at: `<file>`, `<file>`
```

**Review checklist.** A box is `[x]` only for a fact you verified in this run and saw the result of; otherwise it is `[ ]` with the reason. Keep this order and wording:

- `Up to date with <base>` — `[x]` when step 3 showed 0 commits behind, else `[ ] Behind <base> by N commits`.
- `Everything committed` — `[x]` when `git status --porcelain` was empty, else `[ ] N uncommitted files are not included`.
- `Tests: <command>` — `[x]` only if that command ran on this exact HEAD in this session and exited 0, else `[ ] Tests: not run`. Never run tests just to fill the box.
- `Breaking change: <what breaks>` — only when a commit type has `!` or a body has `BREAKING CHANGE:`. Always `[ ]`: the reviewer confirms.
- `Look at: <files>` — always `[ ]`. Up to three files with the most changed lines in the `--numstat` output, skipping tests, docs (`*.md`, `docs/`) and lockfiles; leave the line out when none remain.

**Changelog section** — what `git-release` reads. One entry per line: `- <Category>: <sentence>`. Categories, in this order: Added, Changed, Deprecated, Removed, Fixed, Security. Write only `none` when a reader would not care: formatting, test-only changes, internal refactors, and a `fix` for a bug that never shipped in a released version. For a `fix`, ask the user once: "Does this bug exist in a released version?" The default is **no** when the target is `release/*` or a QA branch and **yes** when it is the integration branch (yes → `Fixed`, no → `none`). Write for a reader about to upgrade: one plain sentence (~20 words), no first person, no class or endpoint names, no marketing words. `Added` in present tense ("Admins can disable a project to block its chatbot."), `Fixed` as the bug being gone ("X no longer fails when…"), `Changed`/`Removed` in past tense ("Upgraded Postgres to 18").

### 6. Confirm

Print the target branch, the title and the description, and ask once: create (or update) with this, or edit first. Skip the question only if the user's request already said to proceed without asking.

### 7. Push

`git push -u origin <current>`. A rejection (for example non-fast-forward after a rebase) → stop and report. Never force push.

### 8. Create or update the PR/MR

Write the description to a temporary file first so multi-line text survives quoting.

```bash
gh pr create --base <base> --head <current> --title "<title>" --body-file <file>                                                             # gh, new
gh pr edit <number> --title "<title>" --body-file <file>                                                                                     # gh, update mode
glab mr create --source-branch <current> --target-branch <base> --title "<title>" --description "$(cat <file>)" --remove-source-branch --yes   # glab, new
glab mr update <iid> --title "<title>" --description "$(cat <file>)"                                                                          # glab, update mode
```

**Manual mode** (`prCli` is `none`, or the CLI is missing or logged out): the push in step 7 still happens. Print the target branch, the title and the description for the user to paste into the host's web UI.

### 9. Finish

Print the PR/MR URL. Remind the user: after it is merged, run `/git-sync`, then delete the local branch (`git branch -d <current>`).

## Rules

- Never merge the PR/MR — review and merge belong to the team's process
- Never force push and never bypass branch protection
- Never open a PR/MR from the integration, production, QA, `release/*` or `hotfix/*` branches
- If any step fails, stop and report

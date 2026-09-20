---
description: "Push the current branch and open a PR/MR with a drafted Summary and Changelog section."
---

# Git MR Workflow

Push the current branch and open a pull/merge request against the branch it was cut from. The description carries a `## Changelog` section — `git-release` compiles the release changelog from it.

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

Refuse, and say why, when the current branch is:

- a detached HEAD
- the integration branch, the production branch, a QA branch, or `release/*` — these are shared branches; work reaches them through a PR/MR, it does not start from them
- `hotfix/*` — a hotfix PR/MR needs a version and its own changelog section, so `git-release` opens it (Hotfix workflow)

Anything else (`feature/*`, `fix/*`, `chore/*`, ...) is a work branch: continue.

### 2. Find the target branch

Find the base in this order and stop at the first hit:

1. The explicit argument, if given.
2. The base `git-commit` recorded when it created the branch:

   ```bash
   git config --get branch.<current>.releaseKitBase
   ```

3. By name:
   - `fix/*` → the closest candidate among the remote's `release/*` branches, the QA branches and the integration branch — the one with the fewest commits ahead of it (`git rev-list --count origin/<candidate>..HEAD`). On a tie prefer `release/*` over a QA branch over the integration branch. If several `release/*` branches tie, ask the user which one.
   - every other branch → the integration branch.

When the base came from step 3, store it so the next run does not guess: `git config branch.<current>.releaseKitBase <base>`. Tell the user which target was used and why.

### 3. Check there is something to merge

```bash
git fetch origin
git rev-list --count origin/<base>..HEAD      # commits to merge
git rev-list --count HEAD..origin/<base>      # commits the branch is behind
git status --porcelain                        # uncommitted changes
```

- **`0` commits to merge** → stop: there is nothing to open a PR/MR for.
- Behind the base → warn and suggest `/git-sync` first; do not block.
- Uncommitted changes → warn that they are not part of the PR/MR; do not block.

### 4. Is there already a PR/MR for this branch?

Skip this step in manual mode.

```bash
gh pr list --head <current> --base <base> --state open --json number,url      # gh
glab mr list --source-branch <current> --target-branch <base>                 # glab
```

One found → **update mode**: the remaining steps refresh its title and description instead of creating a second one.

### 5. Draft the title and description

```bash
git log --format='%h %s%n%b' origin/<base>..HEAD
git diff --stat origin/<base>...HEAD
```

**Title** — `<type>(<scope>): <short description>`, at most 72 characters. A single commit → reuse its subject. Several → one line that covers the change as a whole, using the type of the most significant commit (`feat|fix|refactor|chore|docs|style|test`).

**Description** — exactly these two sections:

```markdown
## Summary
<1-3 lines: why this change exists, not what the diff shows>

## Changelog
- <Category>: <one sentence>
```

The `## Changelog` section is what `git-release` reads. Write it by these rules.

**Format.** One entry per line: `- <Category>: <sentence>`. Categories, in this order: Added, Changed, Deprecated, Removed, Fixed, Security. A change with nothing a reader would care about gets a section that contains only `none`.

**What earns an entry:** a change someone reading the changelog would care about — user-facing behavior, API/contract, security, or developer-visible workflow/tooling. Write `none` for pure formatting/`style` changes, test-only changes that don't alter observable behavior, and internal refactors with no outward effect.

**Fixes for unreleased code:** a `fix` for a bug that never shipped in a released version gets `none` — readers never saw the bug. For a `fix` commit ask the user once: "Does this bug exist in a released version?" The default answer is **no** when the target is a `release/*` or QA branch (the code is still in QA) and **yes** when the target is the integration branch. Yes → `Fixed`; no → `none`.

**Voice:** write in English, for a reader about to upgrade — not a diff reviewer. No first person (`we`/`I`); the subject is the feature, or `you` when addressing the end user. Keep tense consistent within a category: `Added` → present ("Admins can disable…") or noun phrase ("Optional Redis for shared cache"); `Fixed` → describe the bug as gone ("X no longer…", "X now works with…"); `Changed`/`Removed` → past ("Upgraded Postgres to 18", "Dropped HTTPS redirection…"). Neutral and factual — no marketing adjectives, no emoji, no jokes.

**Length:** one short sentence, plain natural language — what changed and why it matters to a reader, not an implementation inventory. Skip class/method names, full endpoint/parameter lists and internal mechanism details unless essential. Aim for roughly one line (~20 words).

- Too long/technical: `Project disable toggle: Project.IsActive (default true), settable via PUT /api/projects/{id}. A disabled project blocks its chatbot everywhere it's reached — Chat Agent v1 and v2, and a live expert's direct reply over the SignalR hub — for every caller including admins, returning 403 Forbidden.`
- Good: `Admins can disable a project to block its chatbot everywhere it's used.`

### 6. Confirm

Print the target branch, the title and the full description, and ask the user once: create (or update) the PR/MR with this, or edit first. Skip the question only if the user's request already said to proceed without asking.

### 7. Push

```bash
git push -u origin <current>
```

A rejection (for example non-fast-forward after a rebase) → stop and report. Never force push; rewriting the remote branch is the user's decision.

### 8. Create or update the PR/MR

Write the description to a temporary file first so multi-line text survives quoting.

**If `prCli` is `gh`:**

```bash
gh pr create --base <base> --head <current> --title "<title>" --body-file <file>      # new
gh pr edit <number> --title "<title>" --body-file <file>                              # update mode
```

**If `prCli` is `glab`:**

```bash
glab mr create --source-branch <current> --target-branch <base> --title "<title>" --description "$(cat <file>)" --remove-source-branch --yes   # new
glab mr update <iid> --title "<title>" --description "$(cat <file>)"                                                                          # update mode
```

**Manual mode** (`prCli` is `none`, or the CLI is missing or logged out): the push in step 7 still happens. Print the target branch, the title and the description for the user to paste into the host's web UI.

### 9. Finish

Print the PR/MR URL. Remind the user: after it is merged, run `/git-sync`, then delete the local branch (`git branch -d <current>`).

## Rules

- Never merge the PR/MR — review and merge belong to the team's process
- Never force push and never bypass branch protection
- Never open a PR/MR from the integration, production, QA, `release/*` or `hotfix/*` branches
- If any step fails, stop and report
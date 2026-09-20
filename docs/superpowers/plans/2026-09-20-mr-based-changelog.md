# MR-based changelog (release-kit v2.0.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chuyển `release-kit` sang flow changelog tổng hợp từ mô tả MR: thêm command `git-mr`, bỏ việc ghi `[Unreleased]` khỏi `git-commit`, và để `git-release` tổng hợp changelog trên `release/*`.

**Architecture:** Toàn bộ thay đổi là prompt Markdown cộng với `scripts/validate.py`; không có code chạy ở dự án dùng plugin. Mỗi thay đổi prompt được khóa bằng một kiểm tra viết trước trong `validate.py` (TDD): kiểm tra cấu trúc prompt, và chạy đúng các đoạn shell trích từ prompt (hàm `extract`) trên repo git tạm.

**Tech Stack:** Markdown prompts, Python 3 (`scripts/validate.py`, cần `jsonschema`), git, bash, awk.

**Spec:** `docs/superpowers/specs/2026-09-20-mr-based-changelog-design.md`

## Global Constraints

- Category theo thứ tự cố định: `Categories, in this order: Added, Changed, Deprecated, Removed, Fixed, Security.` — dòng này xuất hiện đúng nguyên văn trong `git-mr.md` và `SKILL.md`.
- Định dạng MR: mục `## Changelog`, mỗi dòng `- <Category>: <sentence>`, hoặc mục chỉ chứa `none`. Dòng trống và chú thích HTML `<!-- ... -->` bị bỏ qua.
- Ref cuối entry: `(!N)` khi `prCli` là `glab`, `(#N)` khi `gh`.
- Cut pre-flight: `git merge-base --is-ancestor origin/{{mainBranch}} origin/{{devBranch}}` phải thoát 0.
- Không thêm key nào vào `release-kit.schema.json`.
- File prompt (`commands/*.md`, `SKILL.md`, `README.md`, `CHANGELOG.md`) viết bằng tiếng Anh. Trong `SKILL.md` chỉ dùng `{{key}}` có trong schema. Italic viết hoa kiểu `*Name*` phải trỏ tới heading không đánh số hoặc bold lead-in (`validate.py` kiểm tra), nên tham chiếu bước có số dùng chữ thường ("step 2").
- Không dùng `git add .` hay `git add -A`. Commit theo Conventional Commits, kết thúc bằng dòng `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.
- Không bump `plugin.json`, không tag. v2.0.0 được phát hành sau bằng `git-release` (bản v1.1.0 đã cài vẫn promote `[Unreleased]` như cũ, nên các entry thêm ở Task 5 được chốt đúng).
- Lệnh kiểm tra: `python3 scripts/validate.py` chạy từ gốc repo (cần `pip install jsonschema`, đã cài).
- Nhánh làm việc: `feature/mr-based-changelog` (đã tạo, base `dev`). Mọi commit của kế hoạch nằm trên nhánh này.

## Cấu trúc file

| File | Vai trò | Task |
| --- | --- | --- |
| `docs/superpowers/specs/2026-09-20-mr-based-changelog-design.md` | Spec; sửa hai điểm phát hiện lúc lập kế hoạch | 0 |
| `plugins/release-kit/commands/git-mr.md` | Command mới: push và mở PR/MR với mục `## Changelog` | 1 |
| `plugins/release-kit/commands/git-commit.md` | Bỏ bước ghi changelog, trỏ sang `/git-mr` | 2 |
| `plugins/release-kit/skills/git-release/SKILL.md` | Bước dùng chung *Collect changelog* (Task 3); Cut, Ship, Quick, quy tắc (Task 4) | 3, 4 |
| `scripts/validate.py` | Các kiểm tra tự động cho mọi thay đổi trên | 1-5 |
| `plugins/release-kit/README.md`, `README.md`, `plugin.json`, `marketplace.json`, `CHANGELOG.md` | Tài liệu, mô tả, changelog | 5 |

---

### Task 0: Sửa spec cho hai điểm phát hiện khi lập kế hoạch

**Files:**
- Modify: `docs/superpowers/specs/2026-09-20-mr-based-changelog-design.md` (mục 3.1 và 5.3)
- Add: `docs/superpowers/plans/2026-09-20-mr-based-changelog.md` (file này)

**Interfaces:**
- Produces: hai quyết định mà Task 3 và 4 dựa vào: (a) dòng trống và chú thích HTML bị bỏ qua khi parse mục Changelog; (b) ở Ship, khi section version chưa có, cận trên của `range` là `<cut-point>` = merge-base của `origin/<dev>` và `origin/release/vX.Y.Z`, không phải `origin/<dev>`.

- [ ] **Step 1: Đọc hai đoạn cần sửa**

Run: `grep -n -E 'Mỗi entry đúng một dòng|Section `## \[vX.Y.Z\]` chưa có|Đã có → chỉ tổng hợp' docs/superpowers/specs/2026-09-20-mr-based-changelog-design.md`
Expected: ba dòng khớp (một ở mục 3.1, hai ở mục 5.3).

- [ ] **Step 2: Sửa mục 3.1 (bỏ qua dòng trống và chú thích HTML)**

Dùng Edit trên spec:

old_string:
```
Mỗi entry đúng một dòng.
```
new_string:
```
Mỗi entry đúng một dòng.
- Dòng trống và chú thích HTML (`<!-- ... -->`) được bỏ qua, vì template MR dùng chú thích để hướng dẫn người viết.
```

- [ ] **Step 3: Sửa mục 5.3 (cận trên khi tổng hợp đầy đủ ở Ship)**

Dùng Edit trên spec:

old_string:
```
- Section `## [vX.Y.Z]` chưa có (Cut bị ngắt sau khi cắt nhánh) → chạy tổng hợp đầy đủ như Cut bước 4.
- Đã có → chỉ tổng hợp MR đích `release/vX.Y.Z`: `range = origin/<dev>..origin/release/vX.Y.Z`, `target = release/vX.Y.Z`. Bỏ qua MR đã có ref trong section.
```
new_string:
```
- Section `## [vX.Y.Z]` chưa có (Cut bị ngắt sau khi cắt nhánh) → tổng hợp đầy đủ như Cut bước 4, nhưng với `range = <tag-trước>..<điểm-cut>`, trong đó `<điểm-cut>` là `git merge-base origin/<dev> origin/release/vX.Y.Z`. Không dùng `origin/<dev>` làm cận trên vì `dev` có thể đã nhận thêm MR sau lúc cut; các MR đó không thuộc release này.
- Sau đó (luôn luôn) tổng hợp MR đích `release/vX.Y.Z`: `range = origin/<dev>..origin/release/vX.Y.Z`, `target = release/vX.Y.Z`. Bỏ qua MR đã có ref trong section.
```

Nếu Edit báo `old_string` không khớp vì câu chữ đã khác, đọc lại mục 5.3 của spec và sửa cho đúng ý ở trên; không bỏ qua bước này.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-09-20-mr-based-changelog-design.md docs/superpowers/plans/2026-09-20-mr-based-changelog.md
git commit -m "$(cat <<'EOF'
docs: add implementation plan and refine spec (cut-point range, HTML comments)

Ship must bound a full changelog compile at the release branch's merge base
with dev, otherwise PRs merged into dev after the cut leak into the release.
MR templates carry HTML comments, so the section parser has to ignore them.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 1: Command `git-mr` và bộ kiểm tra category

**Files:**
- Create: `plugins/release-kit/commands/git-mr.md`
- Modify: `scripts/validate.py` (hằng số sau dòng 27; kiểm tra cuối `test_prompts`)

**Interfaces:**
- Produces: trong `validate.py` — hằng `CATEGORIES` (list sáu category theo thứ tự) và hàm `categories_in(text) -> list[str] | None` (đọc dòng `Categories, in this order: ...`). Trong `git-mr.md` — dòng category đó nguyên văn, và các key config `remote`, `prCli`, `devBranch`, `mainBranch`, `qaBranches` ở bảng cài đặt. Task 3 dùng lại `CATEGORIES` và `categories_in`.

- [ ] **Step 1: Viết kiểm tra thất bại**

Dùng Edit trên `scripts/validate.py`:

old_string:
```python
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
```
new_string:
```python
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
CATEGORIES = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]


def categories_in(text):
    """The changelog categories a prompt declares on its 'Categories, in this order: ...' line."""
    match = re.search(r"Categories, in this order: (.+?)\.", text)
    return [c.strip() for c in match.group(1).split(",")] if match else None
```

Rồi Edit tiếp, thêm kiểm tra vào cuối `test_prompts`:

old_string:
```python
          "git-commit records and git-sync reads branch.<name>.releaseKitBase")
```
new_string:
```python
          "git-commit records and git-sync reads branch.<name>.releaseKitBase")

    mr = COMMANDS / "git-mr.md"
    check(mr.is_file(), "commands/git-mr.md exists")
    if mr.is_file():
        mr_text = mr.read_text(encoding="utf-8")
        check(categories_in(mr_text) == CATEGORIES, "git-mr.md lists the six changelog categories in order")
        check("releaseKitBase" in mr_text, "git-mr reads branch.<name>.releaseKitBase")
```

- [ ] **Step 2: Chạy để xác nhận thất bại**

Run: `python3 scripts/validate.py 2>&1 | grep -E 'FAIL|passed|failed'`
Expected: `  FAIL  commands/git-mr.md exists` và `1 check(s) failed`.

- [ ] **Step 3: Tạo `git-mr.md`**

Write `plugins/release-kit/commands/git-mr.md` với nội dung sau (nguyên văn):

````markdown
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
````

- [ ] **Step 4: Chạy để xác nhận đạt**

Run: `python3 scripts/validate.py 2>&1 | grep -E 'git-mr|FAIL|passed|failed'`
Expected: các dòng `ok    git-mr.md has description frontmatter`, `ok    git-mr.md config key ... is in the schema` (năm key), `ok    commands/git-mr.md exists`, `ok    git-mr.md lists the six changelog categories in order`, `ok    git-mr reads branch.<name>.releaseKitBase`, và cuối cùng `all checks passed`.

- [ ] **Step 5: Commit**

```bash
git add plugins/release-kit/commands/git-mr.md scripts/validate.py
git commit -m "$(cat <<'EOF'
feat(git-mr): add command that opens a PR/MR with a Changelog section

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `git-commit` thôi ghi changelog

**Files:**
- Modify: `plugins/release-kit/commands/git-commit.md` (frontmatter dòng 2, bảng cài đặt dòng 19, bước 4 dòng 87-100)
- Modify: `scripts/validate.py` (cuối `test_prompts`)

**Interfaces:**
- Consumes: kiểm tra `git-mr` ở Task 1 (nhắc `/git-mr` chỉ có nghĩa khi command tồn tại).
- Produces: `git-commit.md` không còn chữ `Unreleased` hay `changelogPath`, và có chữ `/git-mr`.

- [ ] **Step 1: Viết kiểm tra thất bại**

Dùng Edit trên `scripts/validate.py`:

old_string:
```python
        check("releaseKitBase" in mr_text, "git-mr reads branch.<name>.releaseKitBase")
```
new_string:
```python
        check("releaseKitBase" in mr_text, "git-mr reads branch.<name>.releaseKitBase")

    commit = (COMMANDS / "git-commit.md").read_text(encoding="utf-8")
    check("Unreleased" not in commit and "changelogPath" not in commit, "git-commit no longer touches the changelog")
    check("/git-mr" in commit, "git-commit points to /git-mr")
```

- [ ] **Step 2: Chạy để xác nhận thất bại**

Run: `python3 scripts/validate.py 2>&1 | grep -E 'FAIL|passed|failed'`
Expected: hai dòng `FAIL` (`git-commit no longer touches the changelog`, `git-commit points to /git-mr`) và `2 check(s) failed`.

- [ ] **Step 3: Sửa `git-commit.md`**

Ba Edit trên `plugins/release-kit/commands/git-commit.md`:

(a) Frontmatter.
old_string: `description: "Commit all current changes: branch safety, grouped commits, and changelog update."`
new_string: `description: "Commit all current changes: branch safety and grouped conventional commits."`

(b) Bỏ dòng khỏi bảng cài đặt.
old_string:
```
| Changelog | `changelogPath` | `CHANGELOG.md` |
```
new_string: (rỗng — xóa cả dòng, kể cả ký tự xuống dòng phía sau)

(c) Thay toàn bộ bước 4. Đọc file để lấy đoạn từ `### 4. Update the changelog` đến hết dòng `- Commit separately: \`docs: update changelog\``, rồi thay bằng:

```markdown
### 4. Next step

Once the commits are made, tell the user: run `/git-mr` to push the branch and open a PR/MR. The changelog entry is written in that PR/MR's `## Changelog` section, not in `CHANGELOG.md` — `git-release` compiles the release changelog from those sections.
```

Phần `## Rules` phía dưới giữ nguyên.

- [ ] **Step 3: Chạy để xác nhận đạt**

Run: `python3 scripts/validate.py 2>&1 | grep -E 'git-commit|FAIL|passed|failed'`
Expected: `ok    git-commit no longer touches the changelog`, `ok    git-commit points to /git-mr`, `all checks passed`.

- [ ] **Step 4: Commit**

```bash
git add plugins/release-kit/commands/git-commit.md scripts/validate.py
git commit -m "$(cat <<'EOF'
refactor(git-commit): leave changelog entries to git-mr

Entries now come from the PR/MR description, so parallel branches stop
conflicting on CHANGELOG.md. git-commit points to /git-mr when it finishes.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `git-release` — bước dùng chung *Collect changelog*

**Files:**
- Modify: `plugins/release-kit/skills/git-release/SKILL.md` (chèn trước `### Confirm before shipping`, khoảng dòng 170)
- Modify: `scripts/validate.py` (thêm `head`, `test_changelog_snippets`, đăng ký trong `main`)

**Interfaces:**
- Consumes: `CATEGORIES`, `categories_in` (Task 1).
- Produces: heading `### Collect changelog` với hai đầu vào `<range>` và `<target>`; dòng `Categories, in this order: ...`; hai dòng lệnh mà test trích bằng `extract`: `git show -s --format=%B <sha> | grep -oE -m1 ...` và `awk 'tolower($0) ...' <description-file>`; dòng `git rev-list --first-parent <range>`. Task 4 gọi bước này từ Cut, Ship, Quick và khai báo `<range>` bằng chuỗi `` `<range>` = `...` ``.

- [ ] **Step 1: Viết kiểm tra thất bại**

Dùng Edit trên `scripts/validate.py`, thêm hàm trước `def main():`:

old_string:
```python
def main():
```
new_string:
````python
def head(repo):
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def test_changelog_snippets():
    """Run the changelog-collection commands from the prompts against throwaway data."""
    print("changelog snippets (from the prompts)")
    skill = SKILL.read_text(encoding="utf-8")
    check(categories_in(skill) == CATEGORIES, "SKILL.md lists the six changelog categories in order")
    check(re.search(r"^### Collect changelog$", skill, flags=re.M) is not None, "SKILL.md has the shared 'Collect changelog' step")

    ref_cmd = extract(skill, "grep -oE -m1")
    awk_cmd = extract(skill, "awk 'tolower(")

    messages = [
        ("a GitLab merge commit", "Merge branch 'feature/x' into 'dev'\n\nfeat: add x\n\nSee merge request grp/sub/proj!123", "123"),
        ("a GitHub merge commit", "Merge pull request #45 from owner/feature-x\n\nfeat: add x", "45"),
        ("a GitHub squash subject", "feat(api): add x (#67)\n\nbody", "67"),
        ("two references on one line", "feat: something (#12) (#99)", "12"),
        ("a commit with no reference", "Merge branch 'release/v1.0.0' into 'dev'", ""),
    ]
    sections = [
        ("between two headings", "## Summary\nwhy\n\n## Changelog\n- Added: A.\n- Fixed: B.\n\n## Test plan\nx\n", "- Added: A.\n- Fixed: B."),
        ("any case, trailing spaces, none", "## Summary\nwhy\n\n## CHANGELOG  \nnone\n", "none"),
        ("section is last in the description", "## Changelog\n- Added: A.\n", "- Added: A."),
        ("no section", "## Summary\nwhy only\n", ""),
        ("only the first section is used", "## Changelog\n- Added: first.\n## Other\n## Changelog\n- Added: second.\n", "- Added: first."),
        ("HTML comment is passed through for the collector to ignore", "## Changelog\n<!-- one line per entry -->\n- Fixed: B.\n", "<!-- one line per entry -->\n- Fixed: B."),
    ]

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        repo = tmp / "r"
        repo.mkdir()
        git(repo, "init", "-q")
        for k, v in (("user.email", "t@t"), ("user.name", "t")):
            git(repo, "config", k, v)

        for name, message, expected in messages:
            (repo / "f").write_text(name)
            git(repo, "add", "f")
            git(repo, "commit", "-q", "-m", message)
            out = bash(ref_cmd.replace("<sha>", head(repo)), repo)
            check(out.stdout.strip() == expected, f"PR/MR number from {name}: got {out.stdout.strip()!r}, want {expected!r}")

        for name, body, expected in sections:
            path = tmp / "description.md"
            path.write_text(body, encoding="utf-8")
            out = bash(awk_cmd.replace("<description-file>", str(path)), repo)
            check(out.stdout.strip() == expected, f"Changelog section cut from a description: {name}")


def main():
````

Rồi đăng ký trong `main` (Edit):

old_string:
```python
    test_git_snippets()

    print()
```
new_string:
```python
    test_git_snippets()
    test_changelog_snippets()

    print()
```

- [ ] **Step 2: Chạy để xác nhận thất bại**

Run: `python3 scripts/validate.py 2>&1 | tail -8`
Expected: hai dòng `FAIL` (`SKILL.md lists the six changelog categories in order`, `SKILL.md has the shared 'Collect changelog' step`) rồi traceback kết thúc bằng `AssertionError: line containing 'grep -oE -m1' not found`.

- [ ] **Step 3: Chèn bước *Collect changelog* vào `SKILL.md`**

Dùng Edit trên `plugins/release-kit/skills/git-release/SKILL.md`:

old_string: `### Confirm before shipping`
new_string: (toàn bộ khối sau, rồi một dòng trống, rồi lại `### Confirm before shipping`)

````markdown
### Collect changelog

Compiles the `## [vX.Y.Z]` section from the `## Changelog` sections of merged PRs/MRs (`git-mr` writes them). Inputs: `<range>` (a git revision range) and `<target>` (the branch the PRs/MRs must have been merged into). Output: a draft, plus the PRs/MRs that have no usable `## Changelog` section and the commits that belong to no PR/MR.

Categories, in this order: Added, Changed, Deprecated, Removed, Fixed, Security.

**1. Can the host be queried?** `{{prCli}}` is `gh` or `glab` and the CLI is logged in (`gh auth status` / `glab auth status`). If not, use *Manual collection* below instead of steps 3 and 4.

**2. List the commits.** One per PR/MR for merge-commit histories, one per commit for squash or fast-forward histories:

```bash
git rev-list --first-parent <range>
```

**3. Find each PR/MR number.** Cheap first — read it from the commit message (GitLab `See merge request grp/proj!N`, GitHub `Merge pull request #N`, or a squash subject ending `(#N)`):

```bash
git show -s --format=%B <sha> | grep -oE -m1 '(merge request [^ ]*!|pull request #|\(#)[0-9]+' | grep -oE '[0-9]+$' | head -1
```

Nothing printed → ask the host:

```bash
gh api repos/{owner}/{repo}/commits/<sha>/pulls --jq '.[].number'                 # gh
glab api "projects/:id/repository/commits/<sha>/merge_requests"                    # glab: use each "iid"
```

If the installed `glab` does not accept `:id`, take the project path from `git remote get-url origin` and URL-encode it. A commit that still maps to no PR/MR goes on the list of commits without a PR/MR. De-duplicate the numbers.

**4. Fetch and filter.**

```bash
gh pr view <N> --json number,title,body,baseRefName,state,url                      # gh
glab mr view <N> -F json                                                            # glab: description, target_branch, state, web_url
```

Keep only PRs/MRs that are **merged** and whose base branch is `<target>`. That last filter drops fix PRs/MRs that went into an earlier `release/*` and only reached `{{devBranch}}` through a back-merge, and hotfix PRs/MRs (they have their own section). PRs/MRs that target a QA branch are not collected.

**5. Read each `## Changelog` section.** Save the description to a file and cut the section out — it starts at a `## Changelog` heading (any case) and ends at the next `## ` heading:

```bash
awk 'tolower($0) ~ /^## +changelog[ \t]*$/ {f=1; next} f && /^## / {exit} f' <description-file>
```

Ignore blank lines and HTML comments (`<!-- ... -->`). Every other line must match `- <Category>: <sentence>` (category in any case), or the whole section must be just `none` (any case, optional trailing period). Anything else, or no section at all, puts the PR/MR on the list of PRs/MRs with no usable Changelog section.

**6. Assemble the draft.** Group by category in the order above; inside a category keep merge order (oldest first). Merge entries that say the same thing and list every reference: `(!12, !15)`. Normalize the wording — English, present tense for `Added` and past tense for `Changed`/`Removed`, `Fixed` written as the bug being gone, no first person, one sentence of about 20 words — and end each entry with its reference: `(!N)` when `{{prCli}}` is `glab`, `(#N)` when it is `gh`. Also fold in whatever is under `## [Unreleased]` from the old workflow (those entries have no reference) and leave `[Unreleased]` empty.

**7. Review gate.** Show the user the draft, the list of PRs/MRs with no usable Changelog section, and the list of commits without a PR/MR. For each PR/MR with no usable section the user picks one: write the entry, `none`, or skip. Offer "use the PR/MR titles" as one extra choice for the whole list (`feat` → Added, `fix` → Fixed, `refactor`/`perf`/`chore`/`docs`/`style`/`test` skipped unless the user names a category) — only when the user picks it, never by default; it exists for the first release after moving to this workflow, when older PRs/MRs have no Changelog section. Write nothing to `{{changelogPath}}` until the user confirms the draft.

**Manual collection** (no API access): take the PR/MR numbers from the commit-message pattern in step 3, list them, and ask the user to paste each one's `## Changelog` section — or to accept the commit subjects as a draft. Then continue at step 6. In Phase 2 there is no way to filter by `<target>`: list the PRs/MRs found in `<range>` and ask, one by one, whether the section already covers it.

**Writing the section:** insert `## [vX.Y.Z] - YYYY-MM-DD` directly below `## [Unreleased]` (add that heading if it is missing, and leave it empty), with one `### <Category>` block for each non-empty category.
````

- [ ] **Step 4: Chạy để xác nhận đạt**

Run: `python3 scripts/validate.py 2>&1 | grep -E 'changelog|Changelog|PR/MR number|FAIL|passed|failed'`
Expected: `ok    SKILL.md lists the six changelog categories in order`, `ok    SKILL.md has the shared 'Collect changelog' step`, năm dòng `ok    PR/MR number from ...` (`123`, `45`, `67`, `12`, rỗng), sáu dòng `ok    Changelog section cut from a description: ...`, và `all checks passed` (gồm cả kiểm tra tham chiếu chéo: `*Manual collection*` phải phân giải được).

- [ ] **Step 5: Commit**

```bash
git add plugins/release-kit/skills/git-release/SKILL.md scripts/validate.py
git commit -m "$(cat <<'EOF'
feat(git-release): add shared step that compiles the changelog from PRs/MRs

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `git-release` — Cut, Ship, Quick và quy tắc

**Files:**
- Modify: `plugins/release-kit/skills/git-release/SKILL.md` (frontmatter dòng 3; *Modes* dòng 59; *Protected branch fallback*; Phase 1 dòng 212-292; Phase 2 dòng 294-358; Quick dòng 382-390; *Rules* dòng 536)
- Modify: `scripts/validate.py` (kiểm tra cấu trúc cuối `test_prompts`; hàm `sequential`; `test_changelog_ranges`; đăng ký trong `main`)

**Interfaces:**
- Consumes: bước `### Collect changelog` (Task 3) và cách nó nhận `<range>`, `<target>`.
- Produces: ba khai báo range đúng nguyên văn `` `<range>` = `<previous-tag>..origin/{{devBranch}}` ``, `` `<range>` = `<previous-tag>..<cut-point>` ``, `` `<range>` = `origin/{{devBranch}}..origin/release/vX.Y.Z` ``; dòng `git merge-base origin/{{devBranch}} origin/release/vX.Y.Z` (điểm cut); dòng `git merge-base --is-ancestor origin/{{mainBranch}} origin/{{devBranch}}` trong pre-flight của Cut; các heading `#### 3. Cut the release branch`, `#### 4. Compile ... on the release branch` (Phase 1) và `#### 3. Sync ...` (Phase 2).

- [ ] **Step 1: Viết kiểm tra thất bại**

(a) Thêm kiểm tra cấu trúc vào cuối `test_prompts`. Dùng Edit trên `scripts/validate.py`:

old_string:
```python
    check("/git-mr" in commit, "git-commit points to /git-mr")
```
new_string:
```python
    check("/git-mr" in commit, "git-commit points to /git-mr")

    for name, (start, end) in {
        "Phase 1": ("### Phase 1: Cut the release branch", "### Phase 2: Ship"),
        "Phase 2": ("### Phase 2: Ship", "## Quick Release Workflow"),
        "Quick release": ("## Quick Release Workflow", "## Hotfix Workflow"),
    }.items():
        section = skill.split(start, 1)[1].split(end, 1)[0]
        check(sequential(section), f"SKILL.md {name}: numbered steps run 1..N without gaps")

    cut = skill.find("#### 3. Cut the release branch")
    compiled = skill.find("#### 4. Compile `{{changelogPath}}` on the release branch")
    check(0 <= cut < compiled, "Phase 1 cuts the release branch (step 3) before compiling the changelog (step 4)")
    check(re.search(r"^#### \d+\. Sync `\{\{changelogPath\}\}`$", skill, flags=re.M) is not None, "Phase 2 has a step that syncs the changelog")
    check("Replace `## [Unreleased]` with" not in skill, "SKILL.md no longer promotes [Unreleased] on dev")
    check("Do not edit this entry again on the release branch" not in skill, "SKILL.md no longer forbids writing the version section on release/*")
```

(b) Thêm hàm `sequential` (cạnh `categories_in`). Edit:

old_string:
```python
    return [c.strip() for c in match.group(1).split(",")] if match else None
```
new_string:
```python
    return [c.strip() for c in match.group(1).split(",")] if match else None


def sequential(section):
    """True when the '#### N. ' step headings of a workflow section run 1..N."""
    numbers = [int(n) for n in re.findall(r"^#### (\d+)\. ", section, flags=re.M)]
    return bool(numbers) and numbers == list(range(1, len(numbers) + 1))
```

(c) Thêm `test_changelog_ranges` trước `def main():` (Edit `old_string: def main():`, giữ lại dòng đó ở cuối `new_string`):

````python
def test_changelog_ranges():
    """The revision ranges and the Cut pre-flight declared in the prompts select the right commits."""
    print("changelog ranges (from the prompts)")
    skill = SKILL.read_text(encoding="utf-8")
    declared = set(re.findall(r"`<range>` = `([^`]+)`", skill))
    expected = {
        "<previous-tag>..origin/{{devBranch}}",
        "<previous-tag>..<cut-point>",
        "origin/{{devBranch}}..origin/release/vX.Y.Z",
    }
    check(declared == expected, f"SKILL.md declares exactly the three collection ranges: {sorted(declared)}")

    list_cmd = extract(skill, "git rev-list --first-parent <range>")
    cut_point_cmd = extract(skill, "git merge-base origin/{{devBranch}} origin/release/vX.Y.Z")
    ancestor_cmd = extract(skill, "git merge-base --is-ancestor origin/{{mainBranch}} origin/{{devBranch}}")

    def sub(text, cut_point=""):
        return (text.replace("{{devBranch}}", "dev").replace("{{mainBranch}}", "main")
                    .replace("<previous-tag>", "v1.0.0").replace("<cut-point>", cut_point)
                    .replace("vX.Y.Z", "v1.1.0"))

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        git(tmp, "init", "-q", "--bare", "remote.git")
        git(tmp, "clone", "-q", "remote.git", "w")
        w = tmp / "w"
        for k, v in (("user.email", "t@t"), ("user.name", "t")):
            git(w, "config", k, v)

        def commit(name):
            (w / name).write_text(name)
            git(w, "add", name)
            git(w, "commit", "-qm", name)

        def merge_pr(branch, into):
            git(w, "checkout", "-q", into)
            git(w, "merge", "-q", "--no-ff", branch, "-m", f"Merge branch '{branch}'")

        def count(rng, cut_point=""):
            out = bash(sub(list_cmd, cut_point).replace("<range>", sub(rng, cut_point)), w)
            return len([line for line in out.stdout.splitlines() if line])

        git(w, "checkout", "-q", "-b", "main"); commit("base"); git(w, "tag", "v1.0.0"); git(w, "push", "-q", "origin", "main")
        git(w, "checkout", "-q", "-b", "dev"); git(w, "push", "-q", "origin", "dev")
        for pr in ("f1", "f2"):
            git(w, "checkout", "-q", "-b", pr, "dev"); commit(pr + "-a"); commit(pr + "-b")
            merge_pr(pr, "dev")
        commit("direct")
        git(w, "checkout", "-q", "-b", "f4", "dev"); commit("f4-a"); commit("f4-b")
        git(w, "checkout", "-q", "dev"); git(w, "merge", "-q", "--ff-only", "f4")
        git(w, "push", "-q", "origin", "dev")
        git(w, "checkout", "-q", "-b", "release/v1.1.0", "dev"); commit("changelog"); git(w, "push", "-q", "origin", "release/v1.1.0")
        git(w, "fetch", "-q", "origin")

        got = count("<previous-tag>..origin/{{devBranch}}")
        check(got == 5, f"Cut range at cut time: one first-parent commit per merge-commit PR, plus the direct and fast-forwarded commits (got {got}, want 5)")

        # dev moves on after the cut, and a fix PR is merged into the release branch
        git(w, "checkout", "-q", "-b", "f3", "dev"); commit("f3-a"); merge_pr("f3", "dev"); git(w, "push", "-q", "origin", "dev")
        git(w, "checkout", "-q", "-b", "fix1", "release/v1.1.0"); commit("fix1-a"); merge_pr("fix1", "release/v1.1.0")
        git(w, "push", "-q", "origin", "release/v1.1.0")
        git(w, "fetch", "-q", "origin")

        cut_point = bash(sub(cut_point_cmd), w).stdout.strip()
        check(cut_point != "", "the cut point (merge base of dev and the release branch) resolves")
        got = count("<previous-tag>..origin/{{devBranch}}")
        check(got == 6, f"plain dev range now includes the PR merged after the cut (got {got}, want 6) — why the merge base is needed")
        got = count("<previous-tag>..<cut-point>", cut_point)
        check(got == 5, f"Ship range up to the cut point leaves dev's later PR out (got {got}, want 5)")
        got = count("origin/{{devBranch}}..origin/release/vX.Y.Z")
        check(got == 2, f"Ship range for release-only commits: the changelog commit and the fix merge (got {got}, want 2)")

        git(w, "checkout", "-q", "main"); commit("hotfix"); git(w, "push", "-q", "origin", "main"); git(w, "fetch", "-q", "origin")
        check(bash(sub(ancestor_cmd), w).returncode != 0, "Cut pre-flight stops while main has commits that dev lacks")
        git(w, "checkout", "-q", "dev"); git(w, "merge", "-q", "--no-edit", "origin/main"); git(w, "push", "-q", "origin", "dev"); git(w, "fetch", "-q", "origin")
        check(bash(sub(ancestor_cmd), w).returncode == 0, "Cut pre-flight passes once dev contains main")


def main():
````

(d) Đăng ký. Edit:

old_string:
```python
    test_changelog_snippets()

    print()
```
new_string:
```python
    test_changelog_snippets()
    test_changelog_ranges()

    print()
```

- [ ] **Step 2: Chạy để xác nhận thất bại**

Run: `python3 scripts/validate.py 2>&1 | grep -E 'FAIL|Traceback|AssertionError|passed|failed'`
Expected: các `FAIL` cho `Phase 1 cuts the release branch (step 3) before compiling ...`, `Phase 2 has a step that syncs the changelog`, `SKILL.md no longer promotes [Unreleased] on dev`, `SKILL.md no longer forbids writing the version section on release/*`; ba dòng `ok ... numbered steps run 1..N` (đang đạt, là lưới an toàn cho bước đánh số lại); rồi `FAIL  SKILL.md declares exactly the three collection ranges: []` và `AssertionError: line containing 'git merge-base origin/{{devBranch}} origin/release/vX.Y.Z' not found`.

- [ ] **Step 3: Sửa frontmatter, *Modes* và *Protected branch fallback***

Ba Edit trên `SKILL.md`:

(a) old_string: `Release a new version: finalize CHANGELOG, cut a release/vX.Y.Z QA-stabilization branch, then (once stabilized) merge to the production branch and tag.`
new_string: `Release a new version: cut a release/vX.Y.Z QA-stabilization branch and compile the CHANGELOG on it from the merged PRs/MRs, then (once stabilized) merge to the production branch and tag.`

(b) old_string: ``**Cut** (finalize CHANGELOG on `{{devBranch}}`, branch off)``
new_string: ``**Cut** (branch off, then compile the CHANGELOG on `release/vX.Y.Z`)``

(c) old_string:
```
### Protected branch fallback

If a push straight to `{{devBranch}}` is rejected
```
new_string:
```
### Protected branch fallback

Only Quick release commits straight to `{{devBranch}}`; the other workflows commit to `release/*` or `hotfix/*`. If a push straight to `{{devBranch}}` is rejected
```

- [ ] **Step 4: Sửa Phase 1 (Cut)**

(a) Pre-flight: thêm điều kiện `main` nằm trong `dev`. Edit:

old_string: `git ls-remote --exit-code --heads origin release/vX.Y.Z       # must exit 2 (branch not cut yet)`
new_string:
```
git ls-remote --exit-code --heads origin release/vX.Y.Z       # must exit 2 (branch not cut yet)
git merge-base --is-ancestor origin/{{mainBranch}} origin/{{devBranch}}   # must exit 0 (dev already contains main)
```

old_string: `Version checks (tag must not exist) are in *Determine version*.`
new_string: ``Version checks (tag must not exist) are in *Determine version*. If `origin/{{mainBranch}}` is not an ancestor of `origin/{{devBranch}}` (a hotfix or release was never merged back), **stop** and ask the user to reconcile first (`git checkout {{devBranch}} && git pull && git merge origin/{{mainBranch}} && git push`): `{{changelogPath}}` on `{{devBranch}}` has to contain the released versions, or the section compiled here will conflict when it is merged back.``

(b) Xóa bước 3 cũ ("Finalize"), giữ nguyên bước "Cut the release branch". Chạy:

```bash
python3 - <<'EOF'
import pathlib
p = pathlib.Path("plugins/release-kit/skills/git-release/SKILL.md")
t = p.read_text(encoding="utf-8")
start = t.index("#### 3. Finalize `{{changelogPath}}` on `{{devBranch}}`")
end = t.index("#### 4. Cut the release branch")
p.write_text(t[:start] + t[end:], encoding="utf-8")
EOF
git diff --stat plugins/release-kit/skills/git-release/SKILL.md
```
Expected: diff chỉ có các dòng bị xóa trong đoạn "Finalize" (khoảng 38 dòng), không có dòng thêm nào từ lệnh này.

(c) Đổi số bước và chèn bước tổng hợp. Edit:

old_string: `#### 4. Cut the release branch`
new_string: `#### 3. Cut the release branch`

Chèn khối mới ngay trước heading `#### 5. Summary` của Phase 1. Dùng Edit với `old_string` nhiều dòng sau (duy nhất, vì phần tóm tắt của Phase 2 có nội dung khác), và `new_string` là khối mới, một dòng trống, rồi chính `old_string` đó:

```
#### 5. Summary

Print:

- Release branch name and version
```

Khối mới:

````markdown
#### 4. Compile `{{changelogPath}}` on the release branch

`git-mr` puts a `## Changelog` section in every PR/MR description; this step turns them into the release entry. You are on `release/vX.Y.Z`, so nothing is committed to `{{devBranch}}`.

Run *Collect changelog* with `<range>` = `<previous-tag>..origin/{{devBranch}}` and `<target>` = `{{devBranch}}`, where `<previous-tag>` is the latest release tag from *Determine version*. **No release tag exists yet** → ask the user where to start: a tag, a commit, a date (`--since`), or `all`.

Insert the `## [vX.Y.Z] - YYYY-MM-DD` section as described there, then commit and push:

```bash
git add {{changelogPath}}
git commit -m "docs: update CHANGELOG for vX.Y.Z"
git push origin release/vX.Y.Z
```

**Stop and warn** if the confirmed draft is empty — there is nothing to release. **Exception (resume):** a `## [vX.Y.Z]` section already exists on the branch — an earlier run already compiled it; skip to step 5.

The date is the cut date; Phase 2 step 3 sets the ship date.
````

(d) Nhắc nhở trong Summary. Edit:

old_string: ``- Reminder: QA stabilizes on `release/vX.Y.Z` from here — bugs go through `fix/*` branched off `release/vX.Y.Z`, PR'd/MR'd back into it. (`git-commit` creates those branches and `git-sync` keeps them on top of the release branch.)``
new_string: ``- Reminder: QA stabilizes on `release/vX.Y.Z` from here — bugs go through `fix/*` branched off `release/vX.Y.Z`, PR'd/MR'd back into it with `git-mr`; the `## Changelog` section of each is picked up when you ship. (`git-commit` creates those branches, `git-mr` opens the PR/MR and `git-sync` keeps them on top of the release branch.)``

- [ ] **Step 5: Sửa Phase 2 (Ship)**

(a) Đánh số lại bước 3-8 thành 4-9, chỉ trong phạm vi Phase 2:

```bash
sed -i '/^### Phase 2: Ship/,/^## Quick Release Workflow/{
s/^#### 8\. /#### 9. /
s/^#### 7\. /#### 8. /
s/^#### 6\. /#### 7. /
s/^#### 5\. /#### 6. /
s/^#### 4\. /#### 5. /
s/^#### 3\. /#### 4. /
}' plugins/release-kit/skills/git-release/SKILL.md
grep -n -E '^#### [0-9]+\. ' plugins/release-kit/skills/git-release/SKILL.md | sed -n '1,40p'
```
Expected: Phase 2 có các heading 1 (Pre-flight), 2 (Reconcile), 4 (Run the gate), 5 (Bump), 6 (Confirm), 7 (Open and merge), 8 (Tag), 9 (Summary); Phase 1 và Quick không đổi.

(b) Chèn bước 3. Edit:

old_string: `#### 4. Run the gate — mandatory`
new_string: (khối sau, rồi một dòng trống, rồi `#### 4. Run the gate — mandatory`)

````markdown
#### 3. Sync `{{changelogPath}}`

Fix PRs/MRs merged into `release/vX.Y.Z` after the cut carry their own `## Changelog` sections. Bring them into the release section and set the ship date.

1. **The `## [vX.Y.Z]` section is missing** (Phase 1 stopped after cutting the branch) → build it first. Find where the branch left `{{devBranch}}`, then run *Collect changelog* with `<range>` = `<previous-tag>..<cut-point>` and `<target>` = `{{devBranch}}`:

   ```bash
   git merge-base origin/{{devBranch}} origin/release/vX.Y.Z       # <cut-point>
   ```

   `{{devBranch}}` may have moved on since the cut; the merge base keeps its newer PRs/MRs out of this release.

2. Run *Collect changelog* with `<range>` = `origin/{{devBranch}}..origin/release/vX.Y.Z` and `<target>` = `release/vX.Y.Z`. Skip every PR/MR whose reference is already in the section. When listing commits without a PR/MR, leave out the `docs: update CHANGELOG` commits this skill made and the merge commit from step 2. A PR/MR with no `## Changelog` section is asked about again on every run; one whose section says `none` is not.

3. Set the heading date to today (the ship date). If anything changed:

   ```bash
   git add {{changelogPath}}
   git commit -m "docs: update CHANGELOG for vX.Y.Z"
   git push origin release/vX.Y.Z
   ```
````

(c) Sửa dòng "Resumable". Edit:

old_string: `Resumable: if the run stops after step 6 has started, run the skill again — steps 6 and 7 detect what is already done.`
new_string: `Resumable: if the run stops after step 7 has started, run the skill again — steps 7 and 8 detect what is already done.`

- [ ] **Step 6: Sửa Quick release**

Edit trên `SKILL.md`:

old_string:
```
#### 4. Finalize `{{changelogPath}}` on `{{devBranch}}`

Same as Standard Phase 1, step 3 — promote `## [Unreleased]` to `## [vX.Y.Z] - YYYY-MM-DD`, add a fresh empty `## [Unreleased]`. **Stop and warn** if `[Unreleased]` is empty (unless resuming — a `## [vX.Y.Z]` section already exists).
```
new_string:
```
#### 4. Compile `{{changelogPath}}` on `{{devBranch}}`

There is no release branch, so the section is written straight to `{{devBranch}}`. Run *Collect changelog* with `<range>` = `<previous-tag>..origin/{{devBranch}}` and `<target>` = `{{devBranch}}` (no release tag yet → ask where to start, as in Standard Phase 1 step 4). **Stop and warn** if the confirmed draft is empty (unless resuming — a `## [vX.Y.Z]` section already exists). Commit and push; if the push is rejected as protected, use the *Protected branch fallback*:
```

Khối lệnh `git add ... git push origin {{devBranch}}` ngay dưới giữ nguyên. Lưu ý: pre-flight của Quick ("Same as Standard Phase 1, step 1") tự động kế thừa điều kiện `main` nằm trong `dev`.

- [ ] **Step 7: Sửa *Rules***

Edit trên `SKILL.md`:

old_string: `- Never skip the CHANGELOG finalization.`
new_string:
```
- Never skip the CHANGELOG compilation (Phase 1 step 4, Phase 2 step 3, Quick step 4, Hotfix step 3) or its review gate.
- The `## [vX.Y.Z]` section on `release/*` is written only by this skill (Phase 1 step 4 and Phase 2 step 3). Stabilization fixes reach it through the `## Changelog` section of their PR/MR (`git-mr`), never by hand-editing.
```

- [ ] **Step 8: Rà soát tham chiếu bước còn sót**

Run: `grep -n -E 'step [0-9]|steps [0-9]|Phase [12],? step' plugins/release-kit/skills/git-release/SKILL.md`
Expected: mọi tham chiếu trỏ đúng: "Hotfix workflow (step 2)", "step 2/3" của Hotfix (không đổi), "Standard Phase 1, step 1" (Quick, không đổi), "Phase 1 step 4", "Phase 2 step 3", "steps 7 and 8", "step 5", "steps 3 and 4" (trong *Collect changelog*, chỉ ba bước của chính nó). Không còn "step 3 — promote", "go to step 4", "after step 6".

- [ ] **Step 9: Chạy để xác nhận đạt**

Run: `python3 scripts/validate.py 2>&1 | grep -E 'FAIL|Traceback|passed|failed'`
Expected: chỉ có `all checks passed`. Nếu `SKILL.md reference *...* resolves to a heading or bold lead-in` báo FAIL, có một italic viết hoa không trỏ tới heading không đánh số: đổi thành chữ thường hoặc tham chiếu bằng số bước.

- [ ] **Step 10: Commit**

```bash
git add plugins/release-kit/skills/git-release/SKILL.md scripts/validate.py
git commit -m "$(cat <<'EOF'
feat(git-release)!: compile the changelog on the release branch

Cut now branches first and compiles the section from merged PRs/MRs on
release/vX.Y.Z; Ship syncs fix PRs/MRs merged after the cut and sets the ship
date; Quick compiles on dev. Cut also requires main to be merged into dev.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Tài liệu, mô tả và changelog

**Files:**
- Modify: `plugins/release-kit/README.md`
- Modify: `README.md` (gốc repo)
- Modify: `plugins/release-kit/.claude-plugin/plugin.json` (chỉ `description`, không đụng `version`)
- Modify: `.claude-plugin/marketplace.json` (chỉ `description` của plugin)
- Modify: `CHANGELOG.md` (dưới `## [Unreleased]`)
- Modify: `scripts/validate.py` (cuối `test_prompts`)

**Interfaces:**
- Consumes: tên và hành vi các thành phần từ Task 1-4.

- [ ] **Step 1: Viết kiểm tra thất bại**

Edit `scripts/validate.py`:

old_string:
```python
    check("Do not edit this entry again on the release branch" not in skill, "SKILL.md no longer forbids writing the version section on release/*")
```
new_string:
```python
    check("Do not edit this entry again on the release branch" not in skill, "SKILL.md no longer forbids writing the version section on release/*")

    readme = (PLUGIN / "README.md").read_text(encoding="utf-8")
    check("| `git-mr` | command |" in readme, "plugin README lists git-mr in the component table")
    check("merge_request_templates" in readme and "pull_request_template.md" in readme,
          "plugin README documents the GitLab and GitHub MR templates")
```

- [ ] **Step 2: Chạy để xác nhận thất bại**

Run: `python3 scripts/validate.py 2>&1 | grep -E 'FAIL|passed|failed'`
Expected: hai dòng `FAIL` (README) và `2 check(s) failed`.

- [ ] **Step 3: Sửa `plugins/release-kit/README.md`**

Sáu Edit:

(a) Bảng component. old_string:
```
| `git-release` | skill | Cut a release branch, finalize CHANGELOG, ship to the production branch, tag. Standard / quick / hotfix, resumable. Driven by a per-project config file. |
| `git-commit` | command | Branch-safety check, grouped conventional commits, `[Unreleased]` changelog update. |
```
new_string:
```
| `git-release` | skill | Cut a release branch, compile the CHANGELOG from merged PRs/MRs, ship to the production branch, tag. Standard / quick / hotfix, resumable. Driven by a per-project config file. |
| `git-commit` | command | Branch-safety check and grouped conventional commits. |
| `git-mr` | command | Push the branch and open a PR/MR whose description carries the `## Changelog` section the release is built from. |
```

(b) Bảng cấu hình. old_string: ``| `changelogPath` | changelog used by `git-release` and `git-commit` | `CHANGELOG.md` |``
new_string: ``| `changelogPath` | changelog written by `git-release` | `CHANGELOG.md` |``

(c) Chèn mục mới ngay trước `## Safety and recovery`. old_string: `## Safety and recovery`
new_string: (khối sau, rồi một dòng trống, rồi `## Safety and recovery`)

````markdown
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
````

(d) Cảnh báo bảo vệ nhánh. old_string: ``- If `devBranch` is protected, the changelog commit goes through a short-lived PR/MR instead of a direct push.``
new_string: ``- Quick release is the only workflow that commits to `devBranch` directly; if it is protected, that commit goes through a short-lived PR/MR instead of a direct push.``

(e) Giả định. old_string: ``- The changelog follows [Keep a Changelog](https://keepachangelog.com/) with `## [Unreleased]` and `## [vX.Y.Z] - date` headings, and commits follow Conventional Commits.``
new_string: ``- The changelog follows [Keep a Changelog](https://keepachangelog.com/) with a `## [Unreleased]` heading (kept empty) and `## [vX.Y.Z] - date` headings, commits follow Conventional Commits, and every PR/MR description carries a `## Changelog` section.``

(f) Checklist test tay: thêm cuối danh sách (sau dòng cuối cùng bắt đầu bằng `- [ ] \`/git-sync\` on a \`fix/*\``):

```markdown
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
```

- [ ] **Step 4: Sửa README gốc, `plugin.json`, `marketplace.json`**

(a) `README.md` (gốc). old_string: ``plus `git-commit` and `git-sync` commands.``
new_string: ``plus `git-commit`, `git-mr` and `git-sync` commands.``

(b) `plugins/release-kit/.claude-plugin/plugin.json`. old_string: `git-commit and git-sync commands.`
new_string: `git-commit, git-mr and git-sync commands.`

(c) `.claude-plugin/marketplace.json`. old_string: `plus git-commit and git-sync commands.`
new_string: `plus git-commit, git-mr and git-sync commands.`

- [ ] **Step 5: Ghi changelog (dưới `## [Unreleased]`)**

Edit `CHANGELOG.md`:

old_string (hai heading, cách nhau một dòng trống):
```
## [Unreleased]

## [v1.1.0] - 2026-09-19
```
new_string:
```
## [Unreleased]

### Added

- `git-mr` opens a PR/MR for your branch, with a `## Changelog` section drafted from your commits that the release changelog is built from.
- `git-release` compiles the release changelog from the merged PRs/MRs and shows it for review before anything is written.
- `git-release` requires `dev` to contain `main` before cutting a release, so the changelog on `dev` always has every released version.

### Changed

- `git-commit` no longer writes to `## [Unreleased]`; entries now come from PR/MR descriptions, so parallel branches no longer conflict on `CHANGELOG.md`. Add the `## Changelog` section to your PR/MR template when upgrading.
- The release changelog is written on `release/vX.Y.Z` and dated on the day you ship, instead of being finalized on `dev` when the release branch is cut.
- Entries left under `## [Unreleased]` are folded into the next release automatically.

## [v1.1.0] - 2026-09-19
```

- [ ] **Step 6: Chạy để xác nhận đạt và kiểm tra manifest**

Run: `python3 scripts/validate.py 2>&1 | grep -E 'FAIL|passed|failed'`
Expected: chỉ có `all checks passed`.

Run: `claude plugin validate . 2>&1 | tail -10`
Expected: báo hợp lệ (marketplace và plugin manifest). Nếu lệnh không có trong môi trường, ghi lại và bỏ qua; `validate.py` đã bao phủ manifest.

- [ ] **Step 7: Commit**

```bash
git add plugins/release-kit/README.md README.md plugins/release-kit/.claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md scripts/validate.py
git commit -m "$(cat <<'EOF'
docs: document the MR-based changelog workflow

README gains the flow, the PR/MR templates, upgrade steps and test checklist;
descriptions mention git-mr; the change is recorded under [Unreleased].

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Kiểm tra cuối

**Files:** không sửa file nào.

- [ ] **Step 1: Chạy toàn bộ kiểm tra**

Run: `python3 scripts/validate.py 2>&1 | tail -5 && git status --short | wc -l && git log --oneline dev..HEAD`
Expected: `all checks passed`, `0` file chưa commit, và bảy commit sau `dev`: commit spec ban đầu (`53804e0`) cộng sáu commit của Task 0 đến Task 5.

- [ ] **Step 2: Rà soát so với spec**

Đối chiếu từng mục của spec với diff (`git diff dev..HEAD --stat`):
- Mục 3 (hợp đồng dữ liệu): `git-mr.md` bước 5 và *Collect changelog* bước 5.
- Mục 4 (`git-mr`): `git-mr.md`, chín bước và chế độ thủ công.
- Mục 5.1-5.6 (`git-release`): *Collect changelog*, Phase 1 bước 1/3/4, Phase 2 bước 3, Quick bước 4, *Rules*.
- Mục 6 (`git-commit`): Task 2.
- Mục 8-9 (migration, kiểm thử): README và `validate.py`.
Bất kỳ yêu cầu nào không có chỗ tương ứng trong diff thì bổ sung thành một commit riêng trước khi báo hoàn tất.

- [ ] **Step 3: Bàn giao**

Không tự tạo PR, không bump version, không tag. Báo người dùng: nhánh `feature/mr-based-changelog` sẵn sàng để mở PR vào `dev`; sau khi merge thì phát hành v2.0.0 bằng `git-release` (bản đã cài vẫn là v1.1.0 nên promote `[Unreleased]` như cũ); rồi pilot theo thứ tự ở mục 8 của spec (FEEDBACK-HUB, som, WP-SEHO-CHAT, DAONT-BASE).

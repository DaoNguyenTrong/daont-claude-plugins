# Kế hoạch triển khai — plugin `release-kit` (Lựa chọn 2)

Mục tiêu: gom `git-release` (+ `git-commit`, `git-sync`) thành 1 plugin cá nhân,
1 nguồn duy nhất, cập nhật bằng `claude plugin update`, delta per-project = 1 file JSON.

Consumer (chốt ở lần trao đổi trước): **som**, **WP-SEHO-CHAT**, **FEEDBACK-HUB**.

---

## TRẠNG THÁI (cập nhật)

Quyết định đã chốt: kiến trúc **1 skill config-driven**; repo tại
`~/workspaces/projects/tools/daont-claude-plugins`.

- [x] **Phase 0** — policy: `frontendVersionFile` / `quick` / `prCli` là cờ config;
  scope harmonize về full cut+ship; hotfix back-merge = user tự làm. (theo khuyến nghị)
- [x] **Phase 1** — scaffold repo + `marketplace.json` + `plugin.json` + `.gitignore` + README
- [x] **Phase 2** — `commands/git-commit.md`, `commands/git-sync.md` (đã sửa Co-Authored-By)
- [x] **Phase 3** — `skills/git-release/SKILL.md` config-driven + `release-kit.schema.json`
  - eval suite: BỎ — `claude plugin eval` đang "early access", chưa dùng được.
    Thay bằng checklist test tay trong `plugins/release-kit/README.md`.
- [x] **Phase 4** — `claude plugin marketplace add` (local dir, trong user settings) +
  `install` → `claude plugin details` xác nhận 3 component load OK
  (git-release ~6.2k tok on-invoke). Đã `uninstall` (giữ marketplace) + commit repo
  (`2cd5124` trên `main`). Marketplace vẫn trỏ **local directory** — sẽ đổi sang GitHub ở Phase 8.
- [x] **Phase 5** — FEEDBACK-HUB. Nhánh `chore/adopt-release-kit-plugin` commit `312a933`
  (CHƯA push). Gồm: `.claude/release-kit.json` (schema-validated), `.claude/settings.json`
  merge marketplace+enabledPlugins (github source), `git rm .claude/skills/git-release/`,
  sửa `CONTRIBUTING.md` + `.claude/rules/commands.md`. WIP không liên quan trong
  `shared/documents/` để nguyên. Plugin resolve trong project qua local-dir marketplace +
  `claude plugin install --scope local` (ghi vào `.claude/settings.local.json`, gitignored).
  Verify còn thiếu: chạy `/git-release` thật trong session FEEDBACK-HUB (checklist README).
- [x] **GitHub repo** — `DaoNguyenTrong/daont-claude-plugins` (PRIVATE, default `main`),
  push commit `2cd5124`. Marketplace user-settings đã đổi từ local dir → GitHub source.
  → BLOCKER Phase 5 đã gỡ.
- [x] **Phase 6** — som. Nhánh `chore/adopt-release-kit-plugin` commit `681f8756` (CHƯA push).
  `.claude/release-kit.json` (glab, build-only gate `(cd WPE_SOM_BE && dotnet build) && (cd WPE_SOM && bun run build)`,
  modes standard/quick/hotfix, tag-only), `.claude/settings.json` mới, `git rm` skill 378 dòng.
  som không có ref nào tới git-release trong CLAUDE.md/AGENTS.md/rules → không phải sửa doc.
  WIP không liên quan (`CHANGELOG.md`, `devices-category/*`) để nguyên.
  Verify: schema OK, `claude plugin details` thấy 3 skill. Còn thiếu: chạy `/git-release quick` thật.
- [x] **Phase 7** — WP-SEHO-CHAT. Nhánh `chore/adopt-release-kit-plugin` commit `f69d2d4` (CHƯA push).
  Policy đã chốt với user: **harmonize sang manual-reconcile** + **skill dùng full scope** (cut+ship).
  8 files (+64 −318): `.claude/release-kit.json` (glab, `frontend/package.json` bump qua
  `bun pm version {version}`, gate `dotnet test backend/WP-SEHO-CHAT.sln + bun run --cwd frontend test:run`,
  modes standard/hotfix), `.claude/settings.json` merge, `git rm` skill 280 dòng,
  `CLAUDE.md`+`AGENTS.md` (vị trí skill), `GIT_HOOKS.md` (bỏ "no back-merge" + gh→MR + Jenkins),
  `.claude/rules/commands.md` (Jenkins, không có `.github/`), **`CONTRIBUTING.md` § Release Process
  viết lại**: cut+ship qua `/git-release`, thêm step 4 Reconcile, giữ nguyên lý luận rename-at-cut,
  đổi PR→MR / GitHub→GitLab. Lefthook (branch-guard/secretlint/commitlint) pass.
  Cũng sửa 1 staleness cũ: "create a PR to dev on GitHub" → "MR ... on GitLab".
- [ ] **Phase 8** — dọn dẹp + migrate DAONT-BASE + xoá `~/.claude/commands/git-{commit,sync}.md`

### Thay đổi ngoài project đã thực hiện
- User settings: marketplace `daont-claude-plugins` → **GitHub** `DaoNguyenTrong/daont-claude-plugins`.
- FEEDBACK-HUB + som `.claude/settings.local.json`: `enabledPlugins.release-kit` (local scope, gitignored) — để test ngay.
- Nhánh chưa push: FEEDBACK-HUB `312a933`, som `681f8756`.

---

## Bức tranh hiện trạng (đã khảo sát)

| Project | Path | Host | PR CLI hiện dùng | Versioning | Scope skill | Hotfix back-merge | Ghi chú fork |
|---|---|---|---|---|---|---|---|
| **DAONT-BASE** | `sources/DAONT-BASE` | GitHub | `gh` | MinVer, tag-only (FE không version) | cut + ship | user tự làm (bản mới) | canonical flavor A |
| **FEEDBACK-HUB** | `personal-projects/FEEDBACK-HUB` | GitHub | `gh` | MinVer (giống DAONT) | cut + ship | (bản cũ: "cherry-pick") | ≈ clone DAONT, chỉ khác tên `.sln`; **chưa có tag nào** |
| **som** | `sources/som` | GitLab | `glab` | git tag-only, `.NET`; `package.json` không đụng | cut + ship + **quick** | (bản cũ) | có mode `quick`; còn text "no back-merge" cũ |
| **WP-SEHO-CHAT** | `backends/WP-SEHO-CHAT` | GitLab | **`gh`** ⚠️ (bug — repo trên GitLab) | MinVer BE + **`package.json` FE bump** (`bun pm version`) | **ship-only** | **có back-merge** | policy khác hẳn |

`git-commit` / `git-sync`: hiện là **slash command global** ở `~/.claude/commands/*.md`, nội dung generic, sẵn sàng đóng gói gần như nguyên trạng.

Không project nào có `.claude/settings.json`. `gh` và `glab` đều đã cài (`/usr/bin/`).

Tham chiếu cần sửa khi migrate:
- `DAONT-BASE/.claude/rules/commands.md:105,111` — nhắc tên skill + `release.yml`
- `FEEDBACK-HUB/.claude/rules/commands.md:105,111` — như trên
- `WP-SEHO-CHAT/CLAUDE.md:12` — "Skills live ... (currently `git-release`)"
- `DAONT-BASE`, `FEEDBACK-HUB` có `CONTRIBUTING.md § Release Process` — kiểm tra lại

---

## Phase 0 — Chốt policy (bắt buộc trước khi code)

Fork đã phân kỳ ở mức **chính sách**, không chỉ binding. Phải chốt 5 điểm sau,
mỗi điểm → hoặc harmonize (mọi project theo 1 cách), hoặc thành cờ trong config.

| # | Điểm phân kỳ | Phương án | Khuyến nghị |
|---|---|---|---|
| 0.1 | **Frontend versioning**: DAONT tag-only vs WP-SEHO-CHAT bump `package.json` | Cờ `frontendVersionFile` (path hoặc `null`) | Cờ — WP-SEHO-CHAT thật sự cần, DAONT/FEEDBACK-HUB để `null` |
| 0.2 | **Scope skill**: cut+ship (DAONT/som) vs ship-only (WP-SEHO-CHAT) | Skill full 2 phase; ai chỉ muốn ship thì gọi Phase 2 | Harmonize về full — WP-SEHO-CHAT không mất gì, được thêm Phase 1 |
| 0.3 | **`quick` mode** (som) | Đưa vào canonical, bật/tắt qua `modes` | Có — default off |
| 0.4 | **Hotfix back-merge**: session này đã đổi DAONT thành "user tự làm" | Áp cho mọi project (skill chỉ nhắc, user thực thi) | Harmonize theo bản mới |
| 0.5 | **PR CLI**: `gh` vs `glab` | Cờ `prCli`; skill viết cả 2 block cú pháp | Cờ `prCli` |

Kết quả Phase 0: 1 bảng quyết định đã tick + (tùy chọn) 1 entry `.claude/decisions.md`
ở DAONT-BASE ghi lý do gom plugin (GATE: draft, hỏi user trước khi ghi).

---

## Phase 1 — Scaffold repo plugin

Repo mới: `DaoNguyenTrong/daont-claude-plugins` (GitHub, private OK).

```
daont-claude-plugins/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   └── release-kit/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── skills/
│       │   └── git-release/
│       │       └── SKILL.md
│       ├── commands/
│       │   ├── git-commit.md
│       │   └── git-sync.md
│       ├── evals/                     # Phase 3
│       │   └── ...
│       └── README.md
└── README.md
```

`.claude-plugin/marketplace.json`:
```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "daont-claude-plugins",
  "owner": { "name": "DaoNguyenTrong", "email": "hatuqs@gmail.com" },
  "plugins": [
    {
      "name": "release-kit",
      "source": "./plugins/release-kit",
      "description": "git-release + git-commit + git-sync, one source across projects",
      "category": "workflow"
    }
  ]
}
```

`plugins/release-kit/.claude-plugin/plugin.json`:
```json
{
  "name": "release-kit",
  "version": "0.1.0",
  "description": "Release workflow: git-release skill (config-driven), git-commit and git-sync commands.",
  "author": { "name": "DaoNguyenTrong" }
}
```

Commit + push. Chưa cần tag.

---

## Phase 2 — Đóng gói `git-commit` / `git-sync`

Gần như copy nguyên `~/.claude/commands/git-commit.md` và `git-sync.md` vào
`plugins/release-kit/commands/`. Chỉnh 2 điểm:

- `git-commit.md` §4 hiện nhắc "the `git-commit` skill already adds entries..." trong
  `git-release` — giữ nguyên tên `git-commit` là ổn (command và skill cùng tên gọi được).
- Kiểm tra dòng `Co-Authored-By: Claude <noreply@anthropic.com>` khớp guideline hiện tại
  (global instruction dùng `Claude Sonnet 5 <noreply@anthropic.com>` cho git commit) — cập nhật.

**Chưa xóa** bản global `~/.claude/commands/` — để tới Phase 7 sau khi verify.

---

## Phase 3 — Viết canonical `git-release/SKILL.md` (config-driven)

### 3.1 Schema config per-project — `.claude/release-kit.json`

```json
{
  "$schema": "https://raw.githubusercontent.com/DaoNguyenTrong/daont-claude-plugins/main/plugins/release-kit/release-kit.schema.json",
  "prCli": "gh",                        // "gh" | "glab"
  "devBranch": "dev",                   // "dev" | "develop"
  "mainBranch": "main",
  "versioningNote": "backend via MinVer (git tag). Frontend not versioned.",
  "frontendVersionFile": null,          // null | "frontend/package.json" (bump via `bun pm version`)
  "gate": {
    "phase1": "dotnet test backend/FeedbackHub.sln --no-restore -m:1 && bun run --cwd frontend test:run",
    "mandatory": "dotnet test backend/FeedbackHub.sln --no-restore -m:1 && bun run --cwd frontend test:run"
  },
  "changelogPath": "CHANGELOG.md",
  "ciTriggerNote": ".github/workflows/release.yml triggers on tag push — CI runs AFTER the tag, no PR CI",
  "modes": ["standard", "hotfix"]       // add "quick" to enable
}
```

### 3.2 Cấu trúc SKILL.md

- **`## 0. Load project config` (mới, chạy đầu tiên)**:
  - Đọc `${changelogPath}`... không — đọc `.claude/release-kit.json` ở project root.
  - Thiếu / sai schema → **STOP**, in template + link schema, yêu cầu user tạo.
  - Đọc xong → in bảng giá trị đã resolve, chờ user xác nhận trước khi chạy lệnh git.
- Thân skill = bản DAONT-BASE hiện tại (đã qua review) **cộng**:
  - `quick` mode từ som (chỉ kích hoạt khi `"quick" ∈ modes`)
  - guard "chưa có tag → hỏi version khởi đầu" (som đã có; FEEDBACK-HUB cần)
  - bước bump `${frontendVersionFile}` nếu khác `null` (từ WP-SEHO-CHAT), đặt ngay trước
    "Create and merge release PR" ở Phase 2 / Quick / Hotfix
- Chỗ khác cú pháp `gh` ↔ `glab`: viết **cả 2 block**, skill chọn theo `${prCli}`:

  ```markdown
  #### Create and merge the release PR/MR

  **If `prCli` == `gh`:**
  ```bash
  gh pr create --base {mainBranch} --head release/vX.Y.Z --title "Release vX.Y.Z" --body "..."
  gh pr merge <number> --merge --subject "Release vX.Y.Z" --delete-branch
  ```

  **If `prCli` == `glab`:**
  ```bash
  glab mr create --source-branch release/vX.Y.Z --target-branch {mainBranch} --title "Release vX.Y.Z" --description "..." --yes
  glab mr merge release/vX.Y.Z --yes -m "Release vX.Y.Z" --remove-source-branch
  ```
  ```

- Thay mọi literal `dotnet test backend/StarterKit.sln ...` → `${gate.mandatory}` / `${gate.phase1}`.
- Thay `.github/workflows/release.yml triggers on tag push...` → `${ciTriggerNote}`.
- Frontmatter `description`: viết generic, bỏ "Uses MinVer".

### 3.3 `release-kit.schema.json`

JSON Schema cho file config, để `$schema` trong mỗi project trỏ tới + validate.
Đặt ở `plugins/release-kit/release-kit.schema.json`.

### 3.4 Eval suite (chống hồi quy khi sửa canonical sau này)

`plugins/release-kit/evals/` — vài case `prompt.md` + `graders/*.md`:
- "Release v1.2.0" với config `prCli=gh` → assert output dùng `gh pr`, tag `origin/main`, không `glab`
- cùng prompt với config `prCli=glab` → assert `glab mr`, `--yes`
- config thiếu → assert skill STOP và in template
- `modes` không có `quick` + user gõ "quick release" → assert skill từ chối
Chạy: `claude plugin eval plugins/release-kit`

---

## Phase 4 — Marketplace + test cục bộ (chưa đụng project thật)

```bash
claude plugin marketplace add ~/workspaces/.../daont-claude-plugins   # local path trước
claude plugin install release-kit@daont-claude-plugins
claude plugin details release-kit                                     # xem inventory + token cost
```

Test trong 1 thư mục nháp có `.claude/release-kit.json` giả:
- `/git-release` → xác nhận đọc config, in bảng resolve
- thử cả `prCli=gh` và `glab`
- `claude plugin eval plugins/release-kit` xanh

Sau khi ổn: push repo lên GitHub, đổi marketplace source sang `github`:
```bash
claude plugin marketplace remove daont-claude-plugins
claude plugin marketplace add DaoNguyenTrong/daont-claude-plugins
```

---

## Phase 5 — Migrate FEEDBACK-HUB (dễ nhất, làm đầu tiên)

Lý do đi đầu: gần canonical nhất, GitHub, repo cá nhân, rủi ro thấp.

1. `cd ~/workspaces/personal-projects/FEEDBACK-HUB` — `git status` sạch, tạo nhánh `chore/adopt-release-kit-plugin`
2. Tạo `.claude/release-kit.json`:
   ```json
   {
     "prCli": "gh", "devBranch": "dev", "mainBranch": "main",
     "frontendVersionFile": null,
     "gate": {
       "phase1": "dotnet test backend/FeedbackHub.sln --no-restore -m:1 && bun run --cwd frontend test:run",
       "mandatory": "dotnet test backend/FeedbackHub.sln --no-restore -m:1 && bun run --cwd frontend test:run"
     },
     "changelogPath": "CHANGELOG.md",
     "ciTriggerNote": ".github/workflows/release.yml triggers on tag push; CI runs after the tag, no PR CI",
     "modes": ["standard", "hotfix"]
   }
   ```
3. Tạo `.claude/settings.json`:
   ```json
   {
     "extraKnownMarketplaces": {
       "daont-claude-plugins": { "source": { "source": "github", "repo": "DaoNguyenTrong/daont-claude-plugins" } }
     },
     "enabledPlugins": { "release-kit@daont-claude-plugins": true }
   }
   ```
4. `git rm -r .claude/skills/git-release/` (còn trong history)
5. Sửa `.claude/rules/commands.md:105,111` — đổi "the `git-release` skill" → "the `git-release` skill (release-kit plugin, cfg `.claude/release-kit.json`)"
6. Kiểm tra `CONTRIBUTING.md § Release Process` còn khớp
7. Test: mở session mới trong repo, `/git-release` → đọc config OK, in đúng lệnh `gh` + `FeedbackHub.sln`
8. `/git-commit` (từ plugin) vẫn chạy
9. Commit nhánh, PR, merge

---

## Phase 6 — Migrate som (`quick` mode)

1. Nhánh `chore/adopt-release-kit-plugin`
2. `.claude/release-kit.json`:
   ```json
   {
     "prCli": "glab", "devBranch": "dev", "mainBranch": "main",
     "versioningNote": "backend via git tag (.NET). WPE_SOM/package.json version is NOT touched.",
     "frontendVersionFile": null,
     "gate": {
       "phase1": "cd WPE_SOM_BE && dotnet build && cd ../WPE_SOM && bun run build",
       "mandatory": "cd WPE_SOM_BE && dotnet build && cd ../WPE_SOM && bun run build"
     },
     "changelogPath": "CHANGELOG.md",
     "ciTriggerNote": "GitLab pipeline runs on tag push",
     "modes": ["standard", "quick", "hotfix"]
   }
   ```
3. settings.json (như Phase 5, nhưng plugin update qua marketplace github giống nhau)
4. `git rm -r .claude/skills/git-release/`
5. som không có `.claude/rules/commands.md` nhắc skill (grep sạch) — kiểm lại `CLAUDE.md`
6. Test kỹ **cả 3 mode**, đặc biệt `quick` (khác biệt lớn nhất của som):
   - `/git-release quick v1.10.0` trên `dev` → 1 pass, không cut branch, `glab mr` từ `dev`
   - `/git-release` trên `dev` → Phase 1 cut
7. Commit, MR (glab), merge

---

## Phase 7 — Migrate WP-SEHO-CHAT (khó nhất — có bug + policy khác)

Đây là fork lệch nhất: dùng `gh` trên repo GitLab (bug tiềm ẩn), FE có bump
`package.json`, skill "ship-only".

1. Nhánh `chore/adopt-release-kit-plugin`
2. **Xác nhận với user**: repo trên GitLab nhưng skill cũ dùng `gh` — chọn `glab` cho config
   (hoặc xác nhận có GitHub mirror thật sự). Nhiều khả năng đây là bug → dùng `glab`.
3. `.claude/release-kit.json`:
   ```json
   {
     "prCli": "glab", "devBranch": "dev", "mainBranch": "main",
     "versioningNote": "backend via MinVer (tag). Frontend version in frontend/package.json.",
     "frontendVersionFile": "frontend/package.json",
     "gate": {
       "phase1": "<lệnh build/test theo backends/WP-SEHO-CHAT/.claude/rules/commands.md>",
       "mandatory": "<như trên>"
     },
     "changelogPath": "CHANGELOG.md",
     "ciTriggerNote": "GitLab pipeline on tag push",
     "modes": ["standard", "hotfix"]
   }
   ```
4. Policy: skill mới là full cut+ship. WP-SEHO-CHAT trước đây "ship-only" vì có process
   cắt branch bên ngoài → xác nhận với user: dùng Phase 2 độc lập vẫn được, hay chuyển hẳn
   sang để skill lo cả Phase 1.
5. `git rm -r .claude/skills/git-release/`
6. Sửa `CLAUDE.md:12` — "Skills live ... (currently `git-release`)" → mô tả plugin
7. Test: cả standard + hotfix; **kiểm bước bump `frontend/package.json`** (`bun pm version vX.Y.Z --no-git-tag-version`) xuất hiện đúng chỗ
8. Commit, MR, merge

---

## Phase 8 — Dọn dẹp + tài liệu

1. Xóa `~/.claude/commands/git-commit.md`, `~/.claude/commands/git-sync.md` (đã có trong plugin)
   — **sau khi** cả 3 project verify xong. Nếu còn project khác ngoài 3 cái đang dùng
   `/git-commit` global thì giữ lại hoặc cũng cho dùng plugin.
2. `plugins/release-kit/README.md`: schema config, bảng ví dụ 3 project, cách thêm project mới,
   cách update.
3. DAONT-BASE: **cân nhắc** cũng migrate sang plugin (hiện là canonical nguồn). Nếu migrate,
   canonical "sống" chỉ còn trong repo plugin — sạch hơn. Nếu giữ, phải nhớ sync 2 chiều.
   → Khuyến nghị: migrate luôn DAONT-BASE (Phase 5.5), plugin là nguồn duy nhất.
4. `.claude/decisions.md` ở DAONT-BASE: entry ghi lý do (GATE: hỏi user trước).

---

## Vận hành sau này

| Tình huống | Thao tác |
|---|---|
| Sửa quy trình (thân skill) | Sửa `plugins/release-kit/skills/git-release/SKILL.md` → `claude plugin eval` → bump `plugin.json` version → commit → `git tag vX.Y.Z` → push. Mỗi project: `claude plugin update release-kit` |
| Đổi binding 1 project | Sửa `.claude/release-kit.json` của project đó. Không đụng plugin |
| Thêm project mới | Tạo `.claude/release-kit.json` + `.claude/settings.json` (2 khối), xong |
| Rollout theo giai đoạn | Trong `settings.json` của project chưa sẵn sàng, pin `source.ref` / `source.sha` về version cũ trong `extraKnownMarketplaces` |
| Rollback khẩn | `claude plugin disable release-kit` + `git revert` commit xóa skill cũ trong project (skill cũ quay lại từ history) |

---

## Rủi ro & giảm thiểu

| Rủi ro | Giảm thiểu |
|---|---|
| Lớp đọc-config: model quên đọc / thay sai mỗi lần chạy | Step 0 bắt buộc, STOP nếu thiếu, in bảng resolve cho user duyệt; eval case kiểm |
| Skill nằm trong `~/.claude/plugins/cache/` — khó soi | README rõ ràng; `claude plugin details`; giữ repo plugin ở path dễ tìm |
| Teammate không `claude plugin update` → dùng bản cũ | Pin version cứng trong `settings.json`; bump có chủ đích + ghi CHANGELOG plugin |
| Policy WP-SEHO-CHAT (FE versioning, ship-only) không map sạch | Phase 0 chốt trước; `frontendVersionFile` là cờ; xác nhận scope với user ở Phase 7 |
| `${...}` placeholder trong SKILL.md bị hiểu nhầm là cú pháp thật | Dùng quy ước rõ ("giá trị từ config, KHÔNG phải shell var"); ví dụ đầy đủ 2 CLI |
| Mất `/git-commit` global khi xóa sớm | Xóa ở Phase 8, sau khi verify; kiểm project khác còn dùng không |

---

## Ước lượng công sức

| Phase | Việc | Thời gian |
|---|---|---|
| 0 | Chốt policy | 30–45 ph (cần user quyết) |
| 1–2 | Scaffold repo + đóng gói command | 30 ph |
| 3 | Viết canonical SKILL.md config-driven + schema + eval | 2–3 h |
| 4 | Marketplace + test cục bộ | 45 ph |
| 5 | FEEDBACK-HUB | 30 ph |
| 6 | som (quick) | 45 ph |
| 7 | WP-SEHO-CHAT (bug + policy) | 1–1.5 h |
| 8 | Dọn dẹp + docs + (DAONT-BASE) | 1 h |
| **Tổng** | | **~7–9 h** |

---

## Thứ tự thực hiện đề xuất

Phase 0 → 1 → 2 → 3 → 4 → **5 (FEEDBACK-HUB, dừng lại đánh giá)** → 6 → 7 → 8.

Checkpoint sau Phase 5: nếu lớp config-driven gây khó chịu khi dùng thật,
cân nhắc chuyển sang biến thể "2 skill tách (git-release / git-release-gitlab) +
config 3 dòng" trước khi làm tiếp som/WP-SEHO-CHAT.

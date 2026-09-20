# Thiết kế: changelog tổng hợp từ mô tả MR (release-kit v2.0.0)

Trạng thái: chờ duyệt · Ngày: 2026-09-20 · Phân loại: architectural (đổi contract của `git-commit`, `git-release`, thêm `git-mr`)

## 1. Bối cảnh và mục tiêu

Hiện `git-commit` (bước 4) ghi entry vào `## [Unreleased]` trên từng nhánh `feature/`/`fix/`; `git-release` chốt `[Unreleased]` thành `## [vX.Y.Z]` **trên `dev`** rồi mới cắt `release/vX.Y.Z`. Hệ quả đã xác định khi khảo sát:

- Mọi nhánh cùng sửa một section của `CHANGELOG.md` nên dễ conflict khi có nhiều MR song song.
- Ngày trong heading là ngày cut, không phải ngày ship.
- Fix trên `release/*` không có chỗ ghi hợp lý: `[Unreleased]` trên nhánh release đã rỗng, còn `SKILL.md:258` cấm sửa lại section version.

Flow mới (do người dùng đề xuất): developer ghi mô tả thay đổi trong MR → merge vào `dev` → khi tạo release branch thì tổng hợp từ các MR → soạn Release Changelog → review → release.

**Mục tiêu**
1. Nguồn entry duy nhất là mục `## Changelog` trong mô tả MR.
2. `dev` không còn bị commit changelog; section version chỉ do `git-release` ghi, trên `release/*`.
3. Fix trong giai đoạn QA đi vào changelog (hoặc bị loại) bằng quy tắc rõ ràng ở phía tác giả MR.
4. Chạy lại `git-release` ở bất kỳ điểm nào đều an toàn (idempotent).

**Ngoài phạm vi**: job CI bắt buộc có mục Changelog; script thu thập kèm plugin (xem mục 10); sinh GitHub/GitLab Release notes; changelog theo package trong monorepo; tự động merge ngược `main → dev` (chỉ thêm điều kiện kiểm tra ở mục 5.3).

## 2. Quyết định đã chốt

| # | Quyết định | Lý do |
| --- | --- | --- |
| D1 | Nguồn entry = mô tả MR, đọc qua `gh`/`glab` | Đúng flow đã đề xuất; cả 4 dự án đang dùng đều có `gh` hoặc `glab` |
| D2 | Cách thu thập = **prompt-only** (không script) | Giống kiến trúc hiện tại của plugin, không thêm dependency |
| D3 | Thêm command `git-mr` cho phía developer | Người dùng chọn; là chỗ duy nhất áp quy tắc viết entry |
| D4 | Tổng hợp trên `release/vX.Y.Z` lúc Cut, đồng bộ lại lúc Ship | `dev` không bị đụng; bắt được MR merge vào release sau lúc cut |
| D5 | Chuyển hẳn, không giữ chế độ song song; phát hành `v2.0.0` | `git-commit` đổi hành vi, là breaking change |
| D6 | Entry kèm ref MR `(!123)` (GitLab) / `(#123)` (GitHub) | Cần cho idempotency ở Ship và truy vết; có thể bỏ nếu bạn không muốn |
| D7 | Ngày trong heading = ngày ship | Đúng ngữ nghĩa Keep a Changelog |
| D8 | Fix cho code chưa từng release → `Changelog: none` | Người dùng chưa từng thấy bug đó; quy tắc chốt ở tác giả MR |

## 3. Hợp đồng dữ liệu

### 3.1 Mục Changelog trong mô tả MR

```markdown
## Summary
<1-3 dòng: vì sao thay đổi>

## Changelog
- Added: Admins can disable a project to block its chatbot everywhere it's used.
- Fixed: Exports no longer fail for projects with no members.
```

Hoặc `## Changelog` chỉ chứa `none` (không phân biệt hoa thường, cho phép dấu chấm cuối).

Quy tắc parse (POSIX, không cần gawk):
- Heading khớp: dòng `## Changelog` (không phân biệt hoa thường, cho phép khoảng trắng cuối). Mục kết thúc ở heading `## ` kế tiếp hoặc cuối mô tả. Chỉ dùng mục đầu tiên.
- Dòng entry khớp `^- (Added|Changed|Deprecated|Removed|Fixed|Security): (.+)$` (category không phân biệt hoa thường, chuẩn hóa về dạng chuẩn). Mỗi entry đúng một dòng.
- Mục có nội dung không khớp entry lẫn `none`, hoặc MR không có mục → **thiếu** (mục 5.2 bước 5).

### 3.2 Khi nào ghi `none`

Đây là quy tắc chất lượng của D8, áp ở `git-mr` (soạn) và nhắc lại ở `git-release` (duyệt):

- Thay đổi thuần `style`, chỉ sửa test, refactor không đổi hành vi quan sát được → `none`.
- `fix` cho lỗi **chưa từng có trong bản đã release** → `none`. Khi nhánh đích là `release/*` hoặc QA branch, mặc định là `none`; khi đích là `dev`, mặc định là `Fixed`. Cả hai đều được hỏi lại một câu: "Lỗi này đã có trong bản đã release chưa?".
- Feature mới → `Added`; thay đổi hành vi → `Changed`.

### 3.3 Giọng văn entry

Giữ nguyên quy tắc hiện có ở `git-commit.md` bước 4 (tiếng Anh, không ngôi thứ nhất, một câu khoảng 20 từ, thì theo category, không tính từ quảng cáo). Chuyển nguyên văn sang `git-mr.md` (nơi duy nhất sở hữu quy tắc). `SKILL.md` nhắc lại phần tối thiểu (thứ tự category, giọng văn) vì bước tổng hợp vẫn chuẩn hóa lại. `validate.py` kiểm tra danh sách sáu category và thứ tự của chúng khớp ở cả hai file.

## 4. Command `git-mr` (mới)

Frontmatter `description`: "Push the current branch and open a PR/MR with a drafted Summary and Changelog section."

Bảng cài đặt đầu file dùng lại các key `prCli`, `remote`, `devBranch`, `mainBranch`, `qaBranches` (không thêm key schema).

| Bước | Hành vi |
| --- | --- |
| 0. Cài đặt | Đọc `.claude/release-kit.json` nếu có; **không bao giờ dừng vì thiếu file**. Thiếu `prCli` thì đoán theo host của remote (`github` → `gh`, `gitlab` → `glab`, khác → `none`). CLI chưa cài hoặc chưa đăng nhập (`gh auth status` / `glab auth status`) → chuyển sang chế độ thủ công |
| 1. Nhánh | Từ chối và nêu lý do trên: detached HEAD, `devBranch`, `mainBranch`, `qaBranches`, `release/*`. Trên `hotfix/*` thì từ chối và trỏ sang `git-release` (MR hotfix cần version và changelog riêng) |
| 2. Nhánh đích | `git config --get branch.<tên>.releaseKitBase`. Nếu thiếu: `feature/*`, `chore/*` và nhánh khác → `devBranch`; `fix/*` → ứng viên gần nhất trong `release/*`, QA branch, `devBranch` (ít commit ahead nhất; hòa thì `release/*` > QA > dev; nhiều `release/*` hòa thì hỏi). Lưu lại `releaseKitBase` và nói rõ đã chọn đích nào, vì sao |
| 3. Điều kiện | `git fetch`; `git rev-list --count origin/<đích>..HEAD` phải > 0, nếu không thì dừng ("không có gì để merge"). Cảnh báo (không chặn) khi cây làm việc bẩn hoặc nhánh tụt sau đích (gợi ý `/git-sync`) |
| 4. MR đã có? | `gh pr list --head <nhánh> --state open --json number,url` / `glab mr list --source-branch <nhánh>`. Có rồi thì chuyển sang chế độ **cập nhật** thay vì tạo trùng |
| 5. Soạn | Đọc `git log origin/<đích>..HEAD` và `git diff --stat`. Title dạng `type(scope): mô tả` (nếu một commit thì dùng subject của nó), tối đa 72 ký tự. Mô tả gồm `## Summary` và `## Changelog` theo mục 3 |
| 6. Xác nhận | In title và mô tả, hỏi một lần: tạo/cập nhật theo bản này, hay sửa |
| 7. Push | `git push -u origin <nhánh>`. Bị từ chối (non-fast-forward) thì dừng và báo; không bao giờ force |
| 8. Tạo/cập nhật | Xem lệnh bên dưới |
| 9. Kết thúc | In URL; nhắc sau khi merge chạy `/git-sync` và xóa nhánh cục bộ |

Lệnh bước 8 (mô tả nhiều dòng truyền qua `--body-file`/heredoc để không vỡ ký tự):

```bash
gh pr create --base <đích> --head <nhánh> --title "<title>" --body-file <file>
gh pr edit <số> --title "<title>" --body-file <file>
glab mr create --source-branch <nhánh> --target-branch <đích> --title "<title>" --description "$(cat <file>)" --remove-source-branch --yes
glab mr update <iid> --title "<title>" --description "$(cat <file>)"
```

**Chế độ thủ công** (`prCli: none`, thiếu CLI, chưa đăng nhập): vẫn push, in title và mô tả để dán vào giao diện web.

**Quy tắc**: không merge, không force push, không bypass protection; bước nào lỗi thì dừng và báo.

## 5. `git-release` (`SKILL.md`)

### 5.1 Bước dùng chung mới: *Collect changelog*

Đầu vào: `range` (git rev-range), `target` (nhánh mà MR phải nhắm tới). Đầu ra: bản nháp entry theo category, danh sách MR thiếu, danh sách commit không thuộc MR nào.

1. **Điều kiện đăng nhập**: `prCli` là `gh`/`glab` và CLI đã đăng nhập; không thì dùng chế độ thủ công (5.4).
2. **Liệt kê commit**: `git rev-list --first-parent <range>`.
3. **Tìm số MR**, rẻ trước:
   ```bash
   git show -s --format=%B <sha> | grep -oE -m1 '(merge request [^ ]*!|pull request #|\(#)[0-9]+' | grep -oE '[0-9]+$' | head -1
   ```
   Khớp `See merge request grp/proj!N` (GitLab), `Merge pull request #N` và `(#N)` (GitHub, squash). Commit không ra số thì tra API: `gh api repos/{owner}/{repo}/commits/<sha>/pulls --jq '.[].number'` hoặc `glab api "projects/:id/repository/commits/<sha>/merge_requests"`. Không tra ra MR nào thì đưa vào danh sách "commit không thuộc MR". Khử trùng số MR.
4. **Lấy chi tiết và lọc**: `gh pr view <N> --json number,title,body,baseRefName,state,url` hoặc `glab mr view <N> -F json`. Giữ MR đã merge và có nhánh đích đúng `target`. Bước lọc này loại các fix từ `release/*` đã vào bản trước rồi mới được merge ngược về `dev`. Hệ quả có chủ ý: MR đích là QA branch (`qaBranches`) không được thu thập ở spec này (xem mục 12a).
5. **Parse mục `## Changelog`** theo mục 3.1:
   ```bash
   awk 'tolower($0) ~ /^## +changelog[ \t]*$/ {f=1; next} f && /^## / {exit} f' <file-mô-tả>
   ```
6. **Lắp bản nháp**: sắp theo thứ tự category Keep a Changelog; trong category theo thứ tự merge (cũ trước); khử trùng entry giống nhau (gộp ref: `(!12, !15)`); chuẩn hóa giọng văn; thêm ref MR cuối dòng. Gộp cả entry cũ trong `## [Unreleased]` (từ flow v1, không có ref) rồi để trống `[Unreleased]`.
7. **Cổng duyệt** (một lần): hiện bản nháp, danh sách MR thiếu mục Changelog và commit không thuộc MR. Với mỗi MR thiếu, người dùng chọn: nhập entry, `none`, hoặc bỏ qua. Có thêm lựa chọn một phím "dùng tiêu đề MR làm entry" (`feat`→Added, `fix`→Fixed, `refactor`/`perf`/`chore` bỏ qua trừ khi người dùng chỉ định), chỉ áp khi người dùng chọn, không bao giờ tự động; mục đích là giai đoạn chuyển đổi khi các MR cũ chưa có mục Changelog. Chỉ ghi file sau khi người dùng xác nhận.

### 5.2 Cut (Phase 1)

Thứ tự mới:

1. **Pre-flight**: giữ nguyên, thêm điều kiện `git merge-base --is-ancestor origin/<main> origin/<dev>`. Không thỏa thì dừng và bảo merge ngược `main → dev` trước (lý do: `CHANGELOG.md` trên `dev` phải có section của các bản đã phát hành, nếu không lần tổng hợp sẽ conflict khi merge ngược sau này).
2. **Gate phase1**: giữ nguyên.
3. **Version, cắt nhánh**: `git checkout -b release/vX.Y.Z <dev>`, ghi `releaseKitBase`, push (đã có ở bước 4 cũ).
4. **Tổng hợp trên `release/vX.Y.Z`**: chạy *Collect changelog* với `range = <tag-trước>..origin/<dev>`, `target = <dev>`. Chưa có tag nào (ví dụ FEEDBACK-HUB) thì hỏi mốc bắt đầu: tag/sha/ngày, hoặc `all`. Chèn `## [vX.Y.Z] - YYYY-MM-DD` ngay dưới `## [Unreleased]` (tạo heading nếu chưa có). Commit `docs: update CHANGELOG for vX.Y.Z` và push.
5. **Tóm tắt**: như cũ.

`dev` không còn bị commit trực tiếp ở flow standard, nên "Protected branch fallback" chỉ còn phục vụ Quick.

### 5.3 Ship (Phase 2)

Thêm bước **Sync changelog** ngay sau *Reconcile with main* (đánh số lại các bước sau; kiểm tra tham chiếu chéo của `validate.py` sẽ bắt tham chiếu sai):

- Section `## [vX.Y.Z]` chưa có (Cut bị ngắt sau khi cắt nhánh) → chạy tổng hợp đầy đủ như Cut bước 4.
- Đã có → chỉ tổng hợp MR đích `release/vX.Y.Z`: `range = origin/<dev>..origin/release/vX.Y.Z`, `target = release/vX.Y.Z`. Bỏ qua MR đã có ref trong section. Nhờ đó MR đích `main` (hotfix kéo vào qua Reconcile) tự bị loại vì có section riêng.
- Bỏ khỏi danh sách "commit không thuộc MR" các commit `docs: update CHANGELOG` do chính skill tạo và merge commit của Reconcile, vì chúng chỉ gây nhiễu.
- MR không có mục Changelog bị hỏi lại ở mỗi lần chạy (không lưu trạng thái giữa các lần). MR có mục `none` hợp lệ nên không bị hỏi lại.
- Đặt lại ngày trong heading thành ngày ship. Nếu có thay đổi, commit `docs: update CHANGELOG for vX.Y.Z` và push; nếu không thì bỏ qua.

Diff `CHANGELOG.md` trong MR release (`release/vX.Y.Z → main`) là bước "Review → Release". Nội dung section version vẫn là phần thân của MR đó như hiện tại.

### 5.4 Chế độ thủ công

Áp dụng khi `prCli: none`, thiếu CLI hoặc chưa đăng nhập. Số MR vẫn trích từ git (bước 3 của Collect) nếu có. Skill liệt kê các số đó và xin người dùng dán mục `## Changelog` của từng MR, hoặc dùng tiêu đề commit làm bản nháp. Ở Ship, không có API nên không lọc theo đích được: skill liệt kê các MR mới thấy trong `range` và hỏi từng cái đã được tính chưa.

### 5.5 Quick và Hotfix

- **Quick**: thay bước "Finalize changelog on dev" bằng *Collect changelog* (`range = <tag-trước>..origin/<dev>`, `target = <dev>`), commit trực tiếp trên `dev` như hiện tại (giữ *Protected branch fallback*). Thêm cùng điều kiện `main` đã nằm trong `dev` ở pre-flight.
- **Hotfix**: giữ nguyên (người dùng commit fix, skill tự chèn section patch). Chỉ chỉnh câu chữ liên quan tới `[Unreleased]` của `dev`.

### 5.6 Quy tắc phải sửa

- `SKILL.md:258` ("Do not edit this entry again on the release branch") → đảo lại: section `## [vX.Y.Z]` trên `release/*` chỉ do skill ghi (Cut và Ship); MR sửa lỗi đóng góp qua mục `## Changelog` của chúng, không sửa tay.
- `SKILL.md:536-543` cập nhật cho khớp (Hotfix vẫn không đụng `[Unreleased]` của `dev`, nhưng phần này giờ luôn rỗng).
- Frontmatter `description` và bảng *Modes*: thay "finalize CHANGELOG on dev" bằng "compile CHANGELOG on the release branch".

## 6. `git-commit`

- Xóa bước 4 (*Update the changelog*) và dòng `changelogPath` trong bảng cài đặt.
- Cuối lệnh in gợi ý: "Chạy `/git-mr` để mở PR/MR" (chỉ in, không tự chạy).
- Bước 1 (ghi `releaseKitBase`) và các bước còn lại giữ nguyên.

## 7. Cấu hình và schema

Không thêm key. `changelogPath` vẫn dùng ở `git-release`. `qaBranches` thêm một chỗ dùng (danh sách từ chối của `git-mr`). `validate.py` yêu cầu mọi key trong bảng cài đặt của command phải có trong schema và mọi key schema phải được prompt dùng, cả hai vẫn đúng sau thay đổi.

## 8. Migration và triển khai

**Cho dự án đang dùng v1.x** (som, WP-SEHO-CHAT, FEEDBACK-HUB, DAONT-BASE):
1. Thêm template MR: GitLab `.gitlab/merge_request_templates/Default.md`, GitHub `.github/pull_request_template.md`, chứa hai mục `## Summary` và `## Changelog` (nội dung mẫu nằm trong README).
2. `claude plugin update release-kit` lên v2.0.0.
3. Entry còn trong `[Unreleased]` được gộp tự động ở lần Cut đầu tiên (5.1 bước 6).
4. MR đã merge trước khi migrate không có mục Changelog nên sẽ hiện trong danh sách thiếu ở lần Cut đầu tiên; dùng lựa chọn "tiêu đề MR làm entry" hoặc nhập tay một lần.

**Thứ tự rollout** (theo tiền lệ `PLAN.md`): implement trên repo plugin → dogfood ở repo này (đã tự release bằng `git-release`) → pilot FEEDBACK-HUB (chưa có tag, kiểm được nhánh "hỏi mốc bắt đầu") → som → WP-SEHO-CHAT → DAONT-BASE. Trong lúc pilot, dự án chưa sẵn sàng ghim `source.ref` về v1.1.0.

**Tài liệu**: README (bảng component thêm `git-mr`, sơ đồ flow mới, template MR, hướng dẫn migrate, checklist test tay), `CHANGELOG.md` (v2.0.0: `### Added` cho `git-mr` và tổng hợp từ MR; `### Changed` ghi rõ `git-commit` không còn ghi `[Unreleased]` và ngày heading là ngày ship), `plugin.json` bump theo tag khi release.

## 9. Kiểm thử

**Tự động** (mở rộng `scripts/validate.py`, chạy trong CI):
1. `git-mr.md` có frontmatter và các key trong bảng cài đặt nằm trong schema (vòng lặp hiện có tự bao phủ file mới).
2. Sáu category và thứ tự của chúng giống nhau trong `git-mr.md` và `SKILL.md`.
3. Kiểm tra `releaseKitBase` mở rộng: `git-commit` ghi, `git-sync` và `git-mr` đọc.
4. Trích số MR: chạy lệnh ở 5.1 bước 3 (lấy từ prompt bằng `extract`) với ba định dạng commit: GitLab merge commit, GitHub merge commit, GitHub squash.
5. Liệt kê commit: trong repo git tạm dựng ba kiểu lịch sử (merge commit, squash, fast-forward), kiểm `git rev-list --first-parent <tag>..origin/dev` ra đúng số commit; kiểm `origin/dev..origin/release/vX` chỉ ra commit riêng của nhánh release.
6. Điều kiện Cut: `merge-base --is-ancestor origin/main origin/dev` trả đúng trước và sau khi merge ngược.
7. Cắt mục Changelog: lệnh `awk` ở 5.1 bước 5 với mô tả có mục, heading khác hoa thường, mục cuối mô tả, không có mục, mục `none`.
8. Tham chiếu chéo *Italic Name* trong `SKILL.md` vẫn phân giải được sau khi đánh số lại bước.

**Thủ công** (thêm vào checklist trong README):
- [ ] `/git-mr` trên `dev`, `main`, `release/*`, `hotfix/*` → từ chối, hotfix trỏ sang `git-release`
- [ ] `feature/*` cắt từ `dev` → MR đích `dev`; `fix/*` cắt từ `release/vX.Y.Z` → MR đích `release/vX.Y.Z`
- [ ] Chạy lại `/git-mr` trên nhánh đã có MR → cập nhật mô tả, không tạo MR thứ hai
- [ ] `prCli: none` → in title/mô tả, vẫn push
- [ ] Cut khi `main` chưa nằm trong `dev` → dừng, nhắc merge ngược
- [ ] Cut với MR thiếu mục Changelog → được liệt kê, không bị bỏ sót âm thầm
- [ ] Cut lần đầu không có tag → hỏi mốc bắt đầu
- [ ] Merge một MR fix vào `release/*` sau lúc cut, chạy Ship → entry được thêm, ngày heading đổi thành ngày ship
- [ ] Ngắt Cut sau khi cắt nhánh, chạy Ship → tổng hợp đầy đủ, không lỗi
- [ ] Entry `[Unreleased]` cũ được gộp vào section mới và `[Unreleased]` rỗng lại

## 10. Rủi ro và ngưỡng chuyển sang script

| Rủi ro | Giảm thiểu |
| --- | --- |
| Model đọc/parse sai mô tả MR (rủi ro chính của prompt-only) | Định dạng entry cố định; các lệnh trích số MR và cắt mục là đoạn shell thật, đã được `validate.py` kiểm; bản nháp và danh sách MR thiếu luôn hiện ra để người dùng duyệt |
| Tra MR bằng API chậm khi nhiều commit không có ref | Ưu tiên trích ref từ message; API chỉ dùng cho phần còn lại |
| `glab api` có thể không hỗ trợ placeholder `:id` ở mọi phiên bản | Khi triển khai xác minh; nếu không hỗ trợ thì lấy đường dẫn dự án từ `git remote get-url` và URL-encode |
| Developer quên điền mục Changelog | Template MR + `git-mr` soạn sẵn; MR thiếu luôn được liệt kê ở Cut và hỏi lại |
| MR đã revert trước khi release vẫn có entry | Người dùng loại ở cổng duyệt |

**Ngưỡng chuyển sang script thu thập (phương án B)**: mở việc viết script nếu có một release mà bản nháp bỏ sót hoặc đọc sai entry của MR có mục Changelog hợp lệ, hoặc hai release liên tiếp phải sửa tay bản nháp vì lỗi parse.

## 11. Danh sách file thay đổi

| File | Thay đổi |
| --- | --- |
| `plugins/release-kit/commands/git-mr.md` | Mới |
| `plugins/release-kit/commands/git-commit.md` | Bỏ bước 4, gợi ý `/git-mr` |
| `plugins/release-kit/skills/git-release/SKILL.md` | Thêm *Collect changelog*; sửa Cut, Ship, Quick, quy tắc, mô tả |
| `plugins/release-kit/README.md` | Bảng component, flow, template MR, migrate, checklist |
| `scripts/validate.py` | Các kiểm tra ở mục 9 |
| `CHANGELOG.md`, `plugins/release-kit/.claude-plugin/plugin.json` | Ghi và bump khi release v2.0.0 |
| `release-kit.schema.json` | Không đổi |

## 12. Việc liên quan nhưng tách riêng

Hai phát hiện từ phần đánh giá trước không thuộc spec này: (a) `git-release` chưa dùng `qaBranches`, hai mô hình QA (nhánh môi trường và `release/*`) chưa được thống nhất; do đó entry của MR đích là QA branch chưa có đường vào changelog, chỉ `release/*` được hỗ trợ; (b) merge ngược `main → dev` chỉ là lời nhắc. Điểm (b) đã được siết một phần ở 5.2 bước 1 vì flow mới cần nó; phần còn lại và điểm (a) sẽ làm ở spec khác.

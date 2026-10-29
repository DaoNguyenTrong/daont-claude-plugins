# Thiết kế: plugin `plane-kit` (tạo work item Plane và đồng bộ MR/PR)

Trạng thái: chờ duyệt · Ngày: 2026-10-29 · Phân loại: architectural (thêm plugin mới, thêm điểm tích hợp tùy chọn vào `git-mr` của release-kit)

## 1. Bối cảnh và mục tiêu

Repo CIMP-VBI đang có quy trình Plane hoàn chỉnh nhưng gắn cứng vào `CIMPVBI`: quy tắc làm việc với work item, script CI `plane_sync.py`, hook `Refs:` ở commit-msg. Cần dùng lại cho các repo khác, gồm cả repo GitLab và repo GitHub.

**Mục tiêu**
1. Một nguồn duy nhất cho quy trình Plane, cập nhật qua `claude plugin update`.
2. Delta mỗi repo là một file `.claude/plane-kit.json` cộng một biến CI `PLANE_API_KEY`.
3. Đồng bộ MR/PR → Plane chạy được trên GitLab CI và GitHub Actions.
4. Hành vi hiện tại của CIMP-VBI giữ nguyên sau khi chuyển sang plugin (cùng bộ test).

**Ngoài phạm vi**: Plane MCP và khóa API (là thông tin xác thực, không vào plugin); `git-accept`/`git-review`/`mr-reviewer` (để Phase 5, xem mục 9); tự tạo work item; tích hợp Plane Cloud/Enterprise ngoài REST v1 đang dùng.

## 2. Quyết định đã chốt

| # | Quyết định | Lý do |
| --- | --- | --- |
| D1 | Plugin riêng `plane-kit`, không nhét vào `release-kit` | Plane độc lập với release; repo không dùng Plane vẫn chỉ cần release-kit |
| D2 | Script CI phân phối kiểu **vendored**: `/plane-init` chép vào repo đích, kèm dấu phiên bản | CI không đọc được thư mục plugin; không thêm phụ thuộc mạng hay token vào pipeline deploy |
| D3 | Hỗ trợ cả GitLab và GitHub | Các repo đích dùng cả hai |
| D4 | Cấu hình ở `.claude/plane-kit.json`, có schema | Cùng mô hình với `.claude/release-kit.json` |
| D5 | Chính sách agent (không tự đặt `Done`, không tự tạo item, chỉ được đặt `In Progress`) nằm trong skill, không phải config | Là chính sách của chủ repo, không đổi theo dự án. Config chỉ cho phép thu hẹp |

## 3. Cấu trúc plugin

```
plugins/plane-kit/
  .claude-plugin/plugin.json
  plane-kit.schema.json
  README.md
  skills/plane-task/SKILL.md
  commands/plane-init.md
  commands/plane-sync-ci.md
  templates/
    plane_sync.py
    tests/test_plane_sync.py
    gitlab/plane.yml
    github/plane-sync.yml
    lefthook-refs.yml
    commit-msg-refs.sh
```

Đăng ký thêm một mục trong `.claude-plugin/marketplace.json` và `scripts/validate.py` phải kiểm schema mới.

## 4. Cấu hình `.claude/plane-kit.json`

| Khóa | Bắt buộc | Ý nghĩa |
| --- | --- | --- |
| `identifier` | có | Tiền tố mã item, ví dụ `CIMPVBI`. Sinh ra regex `\b<identifier>-(\d+)\b` |
| `projectId` | có | UUID project, để skill không thao tác nhầm project khác trong workspace |
| `workspaceSlug` | có | Slug workspace |
| `baseUrl` | có | URL Plane |
| `host` | có | `gitlab` hoặc `github`, chọn template CI và cách đọc MR/PR |
| `devBranch` | không | Mặc định `dev` |
| `readyState` | không | Mặc định `Ready For Testing` |
| `movableStates` | không | Mặc định `["Backlog","Todo","In Progress"]` |
| `agentMaySet` | không | Tập con của chính sách mặc định; chỉ được thu hẹp, không mở rộng |
| `language` | không | Ngôn ngữ comment và item, mặc định `vi` |
| `branchPattern` | không | Mặc định `{feature,fix,chore}/<identifier-lowercase>-<n>-<slug>` |

Schema từ chối khóa lạ và giá trị `agentMaySet` chứa `Done`.

## 5. Skill `plane-task`

Tổng quát hóa `task-tracking.md` của CIMP-VBI, đọc thông số từ `plane-kit.json`:

- Trước khi code: xác định item, đọc mô tả và tiêu chí chấp nhận, chuyển `In Progress` khi bắt đầu làm thật, cắt nhánh theo `branchPattern`.
- Không tạo item khi chưa được yêu cầu; khi được yêu cầu thì theo quy tắc văn phong (tiêu đề ngắn, mô tả 2–4 câu, không tên class/file).
- Khi người dùng yêu cầu tạo MR/PR: comment tóm tắt lên item, đặt dòng `Plane: <ID>` ở đầu mô tả.
- Bảng state agent được và không được đặt; tra UUID state lúc cập nhật, không hardcode.
- Hotfix vào nhánh chính: agent tự chuyển `readyState` vì CI không làm việc đó.

Phần đặc thù repo (CodeGraph, Serena, quy trình test) không nằm trong skill này.

## 6. Đồng bộ CI

### 6.1 Tham số hóa `plane_sync.py`
Script nhận cấu hình qua biến môi trường do template CI đặt từ `plane-kit.json`: `PLANE_IDENTIFIER`, `PLANE_READY_STATE`, `PLANE_MOVABLE_STATES`, `PLANE_DEV_BRANCH`, cùng `PLANE_BASE_URL`, `PLANE_WORKSPACE_SLUG`, `PLANE_API_KEY`. Giữ nguyên bất biến hiện có: luôn thoát 0, lỗi một item không chặn item khác, mỗi link/comment đăng đúng một lần theo marker.

### 6.2 Tách adapter nền tảng
Logic Plane (`Plane`, `apply`, `find_ids`) dùng chung. `plan_actions` tách thành lớp đọc ngữ cảnh theo nền tảng, đầu ra là cùng một cấu trúc action:

| Sự kiện | GitLab | GitHub |
| --- | --- | --- |
| MR/PR mở hoặc cập nhật | `CI_PIPELINE_SOURCE=merge_request_event`, biến `CI_MERGE_REQUEST_*` | `pull_request`, đọc JSON ở `GITHUB_EVENT_PATH` |
| Merge vào `devBranch` | `CI_COMMIT_BRANCH`, nhận MR từ `See merge request …!N` | `push`; nhận PR từ `Merge pull request #N` hoặc hậu tố `(#N)` của squash |
| Tag phát hành | `CI_COMMIT_TAG` | `GITHUB_REF` dạng `refs/tags/vX.Y.Z` |
| URL MR/PR, commit, tag | `/-/merge_requests/N`, `/-/commit/`, `/-/tags/` | `/pull/N`, `/commit/`, `/tree/<tag>` |

URL tag trên GitHub dùng `/tree/<tag>` thay vì `/releases/tag/`: tag chưa có release thì trang `/releases/tag/` không đảm bảo tồn tại, còn `/tree/<tag>` luôn có.

**Quyền token trên GitHub:** adapter gọi API PR bằng `GITHUB_TOKEN` của workflow. Template khai báo `permissions:` tường minh, tối thiểu: `contents: read`, `pull-requests: read`. Không cấp quyền ghi. Nếu API PR lỗi (hết quyền, mạng), script ghi cảnh báo, không suy item chính từ commit, chỉ comment các mã tìm được và vẫn thoát 0.

**Điểm khác cần xử lý:** GitLab ghi tên nhánh và title MR vào merge commit nên mã item chính đọc được từ đó. GitHub squash chỉ giữ title PR, không giữ tên nhánh. Trên GitHub, item chính của PR lấy qua API PR (`gh api`/`GITHUB_TOKEN`: title, head ref, body) chứ không suy từ commit. Mã chỉ nằm trong `Refs:` của commit lẻ vẫn chỉ được comment, không bị chuyển state.

### 6.3 Template
- `gitlab/plane.yml`: job `plane-sync`, `needs: []`, `allow_failure: true`, `GIT_DEPTH: "0"`, chạy khi có `PLANE_API_KEY`. Là job duy nhất được phép chạy trên pipeline MR.
- `github/plane-sync.yml`: workflow cho `pull_request`, `push` vào `devBranch` và tag `v*`; `fetch-depth: 0`; `permissions: contents: read, pull-requests: read`; bỏ qua nếu thiếu secret `PLANE_API_KEY`. PR từ fork không có secret nên tự bỏ qua.
- **Dấu phiên bản:** mọi file vendored mang đúng một dòng `# plane-kit: vX.Y.Z`, đặt ở dòng 1, hoặc dòng 2 nếu dòng 1 là shebang (`plane_sync.py`, `commit-msg-refs.sh`). Với YAML (`plane.yml`, `plane-sync.yml`, `lefthook-refs.yml`) đặt ở dòng 1. Cú pháp `#` hợp lệ cho cả ba loại. `/plane-sync-ci` chỉ đọc dòng này, tìm trong 3 dòng đầu; không thấy thì coi là file lạ và hỏi.
- `lefthook-refs.yml` + `commit-msg-refs.sh`: thêm `Refs: <ID>` vào commit từ tên nhánh. Repo không dùng lefthook nhận bản `.githooks/commit-msg` thuần.

### 6.4 Lệnh
- `/plane-init`: đọc hoặc tạo `plane-kit.json` (hỏi `host` nếu không đoán được từ remote), kiểm schema, chép template tương ứng vào repo kèm dòng `# plane-kit: vX.Y.Z`, thêm `enabledPlugins` và marketplace vào `.claude/settings.json`, nhắc đặt `PLANE_API_KEY` (không in, không ghi file). Chỉ ghi file mới hoặc file có dấu plane-kit; gặp file lạ cùng tên thì dừng và hỏi.
- `/plane-sync-ci`: so dấu phiên bản với bản trong plugin, hiện diff, chỉ ghi đè khi người dùng đồng ý. Không đụng chỉnh sửa tay không có trong diff; nếu bản vendored đã bị sửa so với bản gốc cùng phiên bản thì cảnh báo.

## 7. Tích hợp với release-kit

`git-mr` của release-kit thêm một nhánh tùy chọn: nếu có `.claude/plane-kit.json`, đặt dòng `Plane: <ID>` đầu mô tả MR/PR (ID lấy từ tên nhánh) và nhắc đăng comment qua skill `plane-task`. Không có file thì hành vi cũ, hai plugin không phụ thuộc cứng. Đây là thay đổi hành vi nhỏ nên thêm một mục vào CHANGELOG của release-kit.

## 8. Kiểm thử

- `templates/tests/test_plane_sync.py`: chuyển bộ test hiện có của CIMP-VBI, chạy với `PLANE_IDENTIFIER` khác `CIMPVBI`; thêm ca cho adapter GitHub (PR mở, squash merge, merge commit, tag) với payload mẫu.
- `scripts/validate.py` kiểm schema của plugin và JSON mẫu; workflow `validate.yml` chạy cả `unittest` của template.
- Kiểm tay (ghi vào README): `/plane-init` trên một repo GitLab và một repo GitHub trống; `/plane-sync-ci` khi bản vendored cũ hơn; PR thật có và không có mã item.

## 9. Lộ trình

1. **Phase 1:** scaffold plugin, schema, skill `plane-task`, đăng ký marketplace, sửa `validate.py`.
2. **Phase 2a (GitLab, không đổi hành vi):** tham số hóa `plane_sync.py` (bộ test CIMP-VBI vẫn xanh), tách adapter với chỉ adapter GitLab, template `gitlab/plane.yml` và hook `Refs:`, `/plane-init` và `/plane-sync-ci` cho `host: gitlab`. Mục tiêu: CIMP-VBI dùng được ngay khi xong phase này, chưa đụng GitHub.
3. **Phase 2b (GitHub):** adapter GitHub, `github/plane-sync.yml`, test payload mẫu (PR mở, squash, merge commit, tag), mở rộng hai lệnh cho `host: github`.
4. **Phase 3:** nhánh Plane trong `git-mr` của release-kit.
5. **Phase 4:** chuyển CIMP-VBI sang plugin (xóa bản chép cục bộ của rule/script, thêm `plane-kit.json`); sau khi xong Phase 2b thì thử trên một repo GitHub.
6. **Phase 5 (riêng, spec khác):** tổng quát hóa `git-accept`/`git-review`/`mr-reviewer`. Làm sau cùng vì quyền tự merge là phần rủi ro nhất và định nghĩa MR loại A/B khác nhau theo repo.

## 10. Rủi ro

| Rủi ro | Xử lý |
| --- | --- |
| Bản vendored lệch bản plugin | Dấu phiên bản + `/plane-sync-ci`; README ghi rõ phải chạy sau mỗi lần `plugin update` |
| Squash merge GitHub mất tên nhánh, item bị chuyển sai hoặc không chuyển | Item chính lấy từ API PR, có test riêng cho ca squash |
| `PLANE_API_KEY` lộ qua log | Script không in khóa; secret ở dạng masked; `/plane-init` không nhận khóa qua tham số |
| Sai identifier gây khớp nhầm (`ABC-1` trong `XABC-1`) | Regex có `\b`, test cho ca tiền tố trùng đuôi |
| Pipeline GitHub của fork chạy không có secret | Job tự bỏ qua, exit 0 |
| API PR của GitHub lỗi hoặc thiếu quyền | `permissions:` tường minh trong template; lỗi thì chỉ comment, không chuyển state, exit 0 |
| Thay đổi GitHub làm hỏng CIMP-VBI | Tách Phase 2a (GitLab) khỏi 2b (GitHub); CIMP-VBI chỉ phụ thuộc 2a |

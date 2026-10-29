#!/usr/bin/env bash
# plane-kit: v{{pluginVersion}}
# commit-msg: thêm trailer `Refs: {{identifier}}-<số>` lấy từ tên nhánh feature/{{identifier}}-<số>-… (không phân biệt hoa thường).
# Không chạy ở prepare-commit-msg: thêm trailer trước khi mở editor thì message để trống không còn hủy
# được commit, và trailer dính liền vào dòng subject.
set -euo pipefail

msg_file="$1"

git rev-parse -q --verify MERGE_HEAD >/dev/null && exit 0

branch=$(git symbolic-ref --short -q HEAD || true)
# Biên từ: `xacme-1` không phải mã `ACME-1`.
id=$(printf '%s' "$branch" | grep -oiE '(^|[^[:alnum:]]){{identifier}}-[0-9]+' | head -n1 | sed 's/^[^[:alnum:]]//' | tr '[:lower:]' '[:upper:]' || true)
[ -n "$id" ] || exit 0

# File còn các dòng comment git soạn cho editor (kể cả "# On branch feature/…"), phải bỏ trước khi xét
# message trống hay đã nhắc mã.
content=$(sed -e '/^# -\{24\} >8 -\{24\}$/,$d' -e '/^#/d' "$msg_file")
[ -n "$(printf '%s' "$content" | tr -d '[:space:]')" ] || exit 0
printf '%s\n' "$content" | sed -n '/[^[:space:]]/{p;q}' | grep -qE '^Merge ' && exit 0
printf '%s\n' "$content" | grep -qiE "\\b${id}\\b" && exit 0

git interpret-trailers --in-place --trailer "Refs: $id" "$msg_file"

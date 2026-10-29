#!/usr/bin/env python3
# plane-kit: v{{pluginVersion}}
"""Gắn link MR/PR, comment và chuyển state sẵn sàng kiểm thử cho work item Plane có mã <IDENTIFIER>-<số>
trong nhánh, commit hoặc MR/PR.

Chạy trong job CI `plane-sync`, cấu hình qua biến môi trường PLANE_*. Luôn thoát 0: lỗi Plane chỉ được ghi log,
không bao giờ làm hỏng pipeline deploy.
"""
from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Iterable

MR_REF = re.compile(r"See merge request \S+!(\d+)")
RELEASE_TAG = re.compile(r"^v\d+\.\d+\.\d+$")
NULL_SHA = "0" * 40
# Item tester đã nhận (Testing, Pending), đã xong hay đã hủy thì không kéo về state sẵn sàng.
DEFAULT_MOVABLE_STATES = frozenset({"Backlog", "Todo", "In Progress"})


@dataclass(frozen=True)
class Config:
    identifier: str
    ready_state: str = "Ready For Testing"
    movable_states: frozenset[str] = DEFAULT_MOVABLE_STATES
    dev_branch: str = "dev"

    @classmethod
    def from_env(cls, env: dict[str, str]) -> "Config":
        identifier = env.get("PLANE_IDENTIFIER", "").strip()
        if not identifier:
            raise ValueError("PLANE_IDENTIFIER chưa đặt")
        movable = frozenset(name.strip() for name in env.get("PLANE_MOVABLE_STATES", "").split(",")
                            if name.strip()) or DEFAULT_MOVABLE_STATES
        return cls(identifier=identifier.upper(),
                   ready_state=env.get("PLANE_READY_STATE", "").strip() or cls.ready_state,
                   movable_states=movable,
                   dev_branch=env.get("PLANE_DEV_BRANCH", "").strip() or cls.dev_branch)

    @property
    def pattern(self) -> re.Pattern:
        return re.compile(rf"\b{re.escape(self.identifier)}-(\d+)\b", re.IGNORECASE)


def find_ids(config: Config, *texts: str | None) -> list[str]:
    seen: dict[str, None] = {}
    for text in texts:
        for number in config.pattern.findall(text or ""):
            seen.setdefault(f"{config.identifier}-{int(number)}", None)
    return list(seen)


class Plane:
    def __init__(self, base_url: str, workspace: str, api_key: str, config: Config,
                 opener: Callable = urllib.request.urlopen) -> None:
        self.config = config
        self._root = f"{base_url.rstrip('/')}/api/v1/workspaces/{workspace}"
        self._key = api_key
        self._open = opener
        self._states: dict[str, dict[str, str]] = {}

    def _call(self, method: str, path: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            self._root + path, data=data, method=method,
            headers={"X-API-Key": self._key, "Content-Type": "application/json"})
        with self._open(request, timeout=15) as response:
            payload = response.read()
        return json.loads(payload) if payload else None

    def find(self, identifier: str) -> dict | None:
        try:
            return self._call("GET", f"/work-items/{identifier}/")
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise

    def state_names(self, project: str) -> dict[str, str]:
        if project not in self._states:
            page = self._call("GET", f"/projects/{project}/states/?per_page=100")
            rows = page.get("results", []) if isinstance(page, dict) else page
            self._states[project] = {row["id"]: row["name"] for row in rows}
        return self._states[project]

    def move_to_ready(self, item: dict) -> str | None:
        """Trả tên trạng thái cũ nếu đã chuyển, None nếu trạng thái hiện tại không được phép chuyển."""
        names = self.state_names(item["project"])
        current = names.get(item.get("state"), "")
        if current not in self.config.movable_states:
            return None
        ready = next(state_id for state_id, name in names.items() if name == self.config.ready_state)
        self._call("PATCH", f"/projects/{item['project']}/work-items/{item['id']}/", {"state": ready})
        return current

    def _list(self, project: str, item: str, kind: str) -> list[dict]:
        page = self._call("GET", f"/projects/{project}/work-items/{item}/{kind}/?per_page=100")
        return page.get("results", []) if isinstance(page, dict) else page

    def add_link_once(self, project: str, item: str, url: str, title: str) -> bool:
        if any(link.get("url") == url for link in self._list(project, item, "links")):
            return False
        self._call("POST", f"/projects/{project}/work-items/{item}/links/", {"url": url, "title": title})
        return True

    def add_comment_once(self, project: str, item: str, marker: str, comment_html: str) -> bool:
        if any(marker in (c.get("comment_html") or "") for c in self._list(project, item, "comments")):
            return False
        self._call("POST", f"/projects/{project}/work-items/{item}/comments/", {"comment_html": comment_html})
        return True


def git_messages(revision_range: str) -> str:
    result = subprocess.run(["git", "log", "--format=%B", revision_range], capture_output=True, text=True)
    if result.returncode != 0:
        # Commit trước đó không còn trong lịch sử (force push): chỉ còn đọc được commit hiện tại.
        tip = revision_range.split("..")[-1]
        result = subprocess.run(["git", "log", "--format=%B", "-1", tip], capture_output=True, text=True)
    return result.stdout


def previous_tag(tag: str) -> str | None:
    result = subprocess.run(["git", "describe", "--tags", "--abbrev=0", "--match", "v*", f"{tag}^"],
                            capture_output=True, text=True)
    return result.stdout.strip() or None


def link(url: str, text: str) -> str:
    return f'<a href="{html.escape(url)}">{html.escape(text)}</a>'


def plan_actions(env: dict[str, str], messages_of: Callable[[str], str] = git_messages,
                 tag_before: Callable[[str], str | None] = previous_tag,
                 config: Config | None = None) -> list[dict]:
    """Mỗi action: ids, link (url, title) hoặc None, marker + comment_html (comment chỉ đăng một lần theo
    marker), ready_ids — các item cần chuyển state sẵn sàng kiểm thử."""
    config = config or Config.from_env(env)
    project_url = env.get("CI_PROJECT_URL", "")
    pipeline = link(env.get("CI_PIPELINE_URL", ""), f"pipeline #{env.get('CI_PIPELINE_ID', '')}")

    if env.get("CI_PIPELINE_SOURCE") == "merge_request_event":
        iid = env["CI_MERGE_REQUEST_IID"]
        title = env.get("CI_MERGE_REQUEST_TITLE", "")
        mr_url = f"{env.get('CI_MERGE_REQUEST_PROJECT_URL', project_url)}/-/merge_requests/{iid}"
        ids = find_ids(config, env.get("CI_MERGE_REQUEST_SOURCE_BRANCH_NAME"), title,
                       env.get("CI_MERGE_REQUEST_DESCRIPTION"))
        marker = f"MR !{iid} đã mở"
        target = html.escape(env.get("CI_MERGE_REQUEST_TARGET_BRANCH_NAME", ""))
        return [{"ids": ids, "link": (mr_url, f"MR !{iid}: {title}"), "marker": marker, "ready_ids": [],
                 "comment_html": f"<p>{marker} vào <code>{target}</code>: {link(mr_url, title)}</p>"}]

    tag = env.get("CI_COMMIT_TAG", "")
    if RELEASE_TAG.match(tag):
        before = tag_before(tag)
        ids = find_ids(config, messages_of(f"{before}..{tag}" if before else tag))
        marker = f"Đã có trong bản phát hành {tag}"
        return [{"ids": ids, "link": None, "marker": marker, "ready_ids": [],
                 "comment_html": f"<p>{marker} ({link(f'{project_url}/-/tags/{tag}', tag)}, {pipeline}).</p>"}]

    if env.get("CI_COMMIT_BRANCH") == config.dev_branch:
        sha = env["CI_COMMIT_SHA"]
        short = env.get("CI_COMMIT_SHORT_SHA", sha[:8])
        before = env.get("CI_COMMIT_BEFORE_SHA", "")
        revision_range = f"{before}..{sha}" if before and before != NULL_SHA else f"{sha}^!"
        commit_message = env.get("CI_COMMIT_MESSAGE", "")
        ids = find_ids(config, messages_of(revision_range), commit_message)
        mr = MR_REF.search(commit_message)
        mr_link = None
        extra = ""
        # Chỉ item chính của MR (tên nhánh, title — phần GitLab ghi vào merge commit) được chuyển trạng thái;
        # mã chỉ có trong Refs: của commit lẻ là việc liên quan, có thể chưa xong, nên chỉ được comment.
        ready_ids = find_ids(config, commit_message) if mr else []
        if mr:
            mr_url = f"{project_url}/-/merge_requests/{mr.group(1)}"
            mr_link = (mr_url, f"MR !{mr.group(1)}")
            extra = f", {link(mr_url, f'MR !{mr.group(1)}')}"
        marker = f"Đã merge vào {config.dev_branch} ở commit {short}"
        commit = link(f"{project_url}/-/commit/{sha}", short)
        return [{"ids": ids, "link": mr_link, "marker": marker, "ready_ids": ready_ids,
                 "comment_html": f"<p>Đã merge vào <code>{html.escape(config.dev_branch)}</code> ở commit {commit}{extra}, {pipeline}.</p>"}]

    return []


def apply(plane: Plane, actions: Iterable[dict], log: Callable[[str], None] = print) -> None:
    for action in actions:
        if not action["ids"]:
            log(f"Không thấy mã {plane.config.identifier}-<số> nào — bỏ qua.")
        for identifier in action["ids"]:
            try:
                found = plane.find(identifier)
                if found is None:
                    log(f"{identifier}: không có trên Plane — bỏ qua.")
                    continue
                project, item = found["project"], found["id"]
                if action["link"]:
                    url, title = action["link"]
                    added = plane.add_link_once(project, item, url, title)
                    log(f"{identifier}: {'đã gắn' if added else 'đã có sẵn'} link {url}")
                added = plane.add_comment_once(project, item, action["marker"], action["comment_html"])
                log(f"{identifier}: {'đã comment' if added else 'comment đã có sẵn'} — {action['marker']}")
                if identifier in action["ready_ids"]:
                    previous = plane.move_to_ready(found)
                    log(f"{identifier}: " + (f"{previous} → {plane.config.ready_state}" if previous
                                             else f"giữ nguyên trạng thái (không thuộc {sorted(plane.config.movable_states)})"))
            except Exception as error:  # noqa: BLE001 — lỗi một item không được chặn các item còn lại
                log(f"{identifier}: lỗi khi gọi Plane ({error}) — bỏ qua.")


def main() -> int:
    env = dict(os.environ)
    api_key = env.get("PLANE_API_KEY", "")
    if not api_key:
        print("PLANE_API_KEY chưa đặt — bỏ qua đồng bộ Plane.")
        return 0
    try:
        config = Config.from_env(env)
        base_url, workspace = env.get("PLANE_BASE_URL", ""), env.get("PLANE_WORKSPACE_SLUG", "")
        if not base_url or not workspace:
            print("PLANE_BASE_URL hoặc PLANE_WORKSPACE_SLUG chưa đặt — bỏ qua đồng bộ Plane.")
            return 0
        apply(Plane(base_url, workspace, api_key, config), plan_actions(env, config=config))
    except Exception as error:  # noqa: BLE001
        print(f"Đồng bộ Plane lỗi ({error}) — bỏ qua, pipeline vẫn tiếp tục.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

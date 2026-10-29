import io
import json
import os
import sys
import unittest
import urllib.error
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import plane_sync as s  # noqa: E402

PROJECT_URL = "https://gitlab.example/one-wp/cimp-vbi/source"
CFG = s.Config(identifier="ACME")
BASE_ENV = {"GITLAB_CI": "true", "PLANE_IDENTIFIER": "ACME", "CI_PROJECT_URL": PROJECT_URL, "CI_PIPELINE_URL": f"{PROJECT_URL}/-/pipelines/9",
            "CI_PIPELINE_ID": "9"}


class FakePlane:
    """Plane giả trong bộ nhớ, trả lời như REST API thật qua opener của urllib."""

    STATES = {"s-todo": "Todo", "s-progress": "In Progress", "s-ready": "Ready For Testing", "s-testing": "Testing"}

    def __init__(self, items=("ACME-306",), fail_on=(), state="s-progress"):
        self.items = {ident: {"links": [], "comments": [], "state": state} for ident in items}
        self.fail_on = set(fail_on)
        self.posts = []
        self.patches = []

    def __call__(self, request, timeout):
        path = request.full_url.split("/workspaces/ws", 1)[1].split("?")[0]
        parts = path.strip("/").split("/")
        if parts[0] == "work-items":
            ident = parts[1]
            if ident in self.fail_on:
                raise urllib.error.URLError("boom")
            if ident not in self.items:
                raise urllib.error.HTTPError(request.full_url, 404, "nf", {}, io.BytesIO(b""))
            return self._reply({"id": ident, "project": "p", "state": self.items[ident]["state"]})
        if parts[2] == "states":
            return self._reply({"results": [{"id": i, "name": n} for i, n in self.STATES.items()]})
        if request.get_method() == "PATCH":
            ident = parts[3]
            self.items[ident]["state"] = json.loads(request.data)["state"]
            self.patches.append((ident, self.items[ident]["state"]))
            return self._reply({})
        ident, kind = parts[3], parts[4]
        if request.get_method() == "POST":
            body = json.loads(request.data)
            self.items[ident][kind].append(body)
            self.posts.append((ident, kind, body))
            return self._reply(body)
        return self._reply({"results": self.items[ident][kind]})

    @staticmethod
    def _reply(payload):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        return response


def plane_with(fake):
    return s.Plane("https://plane.example", "ws", "key", CFG, opener=fake)


class ConfigTests(unittest.TestCase):
    def test_defaults_and_overrides(self):
        config = s.Config.from_env({"PLANE_IDENTIFIER": "ACME"})
        self.assertEqual((config.ready_state, config.dev_branch), ("Ready For Testing", "dev"))
        self.assertEqual(config.movable_states, {"Backlog", "Todo", "In Progress"})
        config = s.Config.from_env({"PLANE_IDENTIFIER": "ACME", "PLANE_READY_STATE": "QA",
                                    "PLANE_DEV_BRANCH": "develop", "PLANE_MOVABLE_STATES": "Todo,Doing"})
        self.assertEqual((config.ready_state, config.dev_branch, config.movable_states),
                         ("QA", "develop", {"Todo", "Doing"}))

    def test_movable_states_blank_or_padded(self):
        base = {"PLANE_IDENTIFIER": "ACME"}
        self.assertEqual(s.Config.from_env({**base, "PLANE_MOVABLE_STATES": " Todo , ,Backlog"}).movable_states,
                         {"Todo", "Backlog"})
        self.assertEqual(s.Config.from_env({**base, "PLANE_MOVABLE_STATES": "  "}).movable_states,
                         {"Backlog", "Todo", "In Progress"})

    def test_missing_identifier_raises_value_error(self):
        with self.assertRaises(ValueError):
            s.Config.from_env({})


class FindIdsTests(unittest.TestCase):
    def test_reads_ids_from_branch_names_and_trailers_case_insensitively_without_duplicates(self):
        self.assertEqual(
            s.find_ids(CFG, "feature/acme-306-plane-sync", "fix: x\n\nRefs: ACME-306\nRefs: ACME-12"),
            ["ACME-306", "ACME-12"])

    def test_ignores_ids_glued_to_other_words(self):
        self.assertEqual(s.find_ids(CFG, "XACME-3", None, "ACME-", "ACME-1x", "ACME--2"), [])


class PlanActionsTests(unittest.TestCase):
    def test_merge_request_event_links_the_mr_and_comments_once(self):
        env = {**BASE_ENV, "CI_PIPELINE_SOURCE": "merge_request_event", "CI_MERGE_REQUEST_IID": "310",
               "CI_MERGE_REQUEST_PROJECT_URL": PROJECT_URL, "CI_MERGE_REQUEST_TITLE": "feat: <x>",
               "CI_MERGE_REQUEST_SOURCE_BRANCH_NAME": "feature/acme-306-a",
               "CI_MERGE_REQUEST_DESCRIPTION": "Plane: ACME-7", "CI_MERGE_REQUEST_TARGET_BRANCH_NAME": "dev"}
        [action] = s.plan_actions(env)
        self.assertEqual(action["ids"], ["ACME-306", "ACME-7"])
        self.assertEqual(action["link"], (f"{PROJECT_URL}/-/merge_requests/310", "MR !310: feat: <x>"))
        self.assertIn("feat: &lt;x&gt;", action["comment_html"])
        self.assertEqual(action["ready_ids"], [])

    def test_dev_push_reads_commits_in_the_pushed_range_and_the_mr_from_the_merge_commit(self):
        env = {**BASE_ENV, "CI_COMMIT_BRANCH": "dev", "CI_COMMIT_SHA": "b" * 40, "CI_COMMIT_SHORT_SHA": "bbbbbbbb",
               "CI_COMMIT_BEFORE_SHA": "a" * 40,
               "CI_COMMIT_MESSAGE": "Merge branch 'feature/acme-306-a' into 'dev'\n\n"
                                    "See merge request one-wp/cimp-vbi/source!310"}
        seen = []
        [action] = s.plan_actions(env, messages_of=lambda r: seen.append(r) or "fix: y\n\nRefs: ACME-5")
        self.assertEqual(seen, [f"{'a' * 40}..{'b' * 40}"])
        self.assertEqual(action["ids"], ["ACME-5", "ACME-306"])
        self.assertEqual(action["link"], (f"{PROJECT_URL}/-/merge_requests/310", "MR !310"))
        self.assertEqual(action["marker"], "Đã merge vào dev ở commit bbbbbbbb")
        self.assertEqual(action["ready_ids"], ["ACME-306"])

    def test_first_push_to_dev_reads_only_the_pushed_commit(self):
        env = {**BASE_ENV, "CI_COMMIT_BRANCH": "dev", "CI_COMMIT_SHA": "b" * 40, "CI_COMMIT_BEFORE_SHA": "0" * 40}
        seen = []
        s.plan_actions(env, messages_of=lambda r: seen.append(r) or "")
        self.assertEqual(seen, [f"{'b' * 40}^!"])

    def test_direct_push_to_dev_without_an_mr_comments_without_a_link(self):
        env = {**BASE_ENV, "CI_COMMIT_BRANCH": "dev", "CI_COMMIT_SHA": "b" * 40, "CI_COMMIT_MESSAGE": "fix: z"}
        [action] = s.plan_actions(env, messages_of=lambda r: "fix: z\n\nRefs: ACME-9")
        self.assertIsNone(action["link"])
        self.assertEqual(action["ready_ids"], [])

    def test_release_tag_reads_commits_since_the_previous_release(self):
        env = {**BASE_ENV, "CI_COMMIT_TAG": "v1.4.4"}
        seen = []
        [action] = s.plan_actions(env, messages_of=lambda r: seen.append(r) or "Refs: ACME-1",
                                  tag_before=lambda t: "v1.4.3")
        self.assertEqual(seen, ["v1.4.3..v1.4.4"])
        self.assertEqual(action["marker"], "Đã có trong bản phát hành v1.4.4")
        self.assertEqual(action["ready_ids"], [])

    def test_other_branches_and_non_release_tags_do_nothing(self):
        self.assertEqual(s.plan_actions({**BASE_ENV, "CI_COMMIT_BRANCH": "main"}), [])
        self.assertEqual(s.plan_actions({**BASE_ENV, "CI_COMMIT_TAG": "v1.4.4-rc1"}), [])


    def test_custom_dev_branch_and_marker(self):
        env = {**BASE_ENV, "PLANE_DEV_BRANCH": "develop", "CI_COMMIT_SHA": "b" * 40,
               "CI_COMMIT_SHORT_SHA": "bbbbbbbb", "CI_COMMIT_MESSAGE": "fix: z"}
        [action] = s.plan_actions({**env, "CI_COMMIT_BRANCH": "develop"}, messages_of=lambda r: "")
        self.assertEqual(action["marker"], "Đã merge vào develop ở commit bbbbbbbb")
        self.assertEqual(s.plan_actions({**env, "CI_COMMIT_BRANCH": "dev"}, messages_of=lambda r: ""), [])


class ApplyTests(unittest.TestCase):
    ACTION = {"ids": ["ACME-306"], "link": ("https://mr/1", "MR !1"), "marker": "MR !1 đã mở",
              "comment_html": "<p>MR !1 đã mở</p>", "ready_ids": []}

    def test_running_twice_adds_the_link_and_comment_only_once(self):
        fake = FakePlane()
        for _ in range(2):
            s.apply(plane_with(fake), [self.ACTION], log=lambda m: None)
        self.assertEqual([(i, k) for i, k, _ in fake.posts], [("ACME-306", "links"), ("ACME-306", "comments")])

    def test_unknown_item_and_plane_errors_are_logged_and_do_not_stop_other_items(self):
        fake = FakePlane(items=("ACME-306", "ACME-2"), fail_on=("ACME-2",))
        logs = []
        action = {**self.ACTION, "ids": ["ACME-999", "ACME-2", "ACME-306"]}
        s.apply(plane_with(fake), [action], log=logs.append)
        self.assertTrue(any("ACME-999: không có trên Plane" in m for m in logs))
        self.assertTrue(any("ACME-2: lỗi khi gọi Plane" in m for m in logs))
        self.assertEqual(len(fake.posts), 2)

    def test_merged_item_moves_from_in_progress_to_ready_for_testing_once(self):
        fake = FakePlane()
        for _ in range(2):
            s.apply(plane_with(fake), [{**self.ACTION, "ready_ids": ["ACME-306"]}], log=lambda m: None)
        self.assertEqual(fake.patches, [("ACME-306", "s-ready")])

    def test_item_the_tester_already_holds_keeps_its_state(self):
        fake = FakePlane(state="s-testing")
        s.apply(plane_with(fake), [{**self.ACTION, "ready_ids": ["ACME-306"]}], log=lambda m: None)
        self.assertEqual(fake.patches, [])

    def test_items_outside_ready_ids_are_only_commented(self):
        fake = FakePlane(items=("ACME-306", "ACME-5"))
        action = {**self.ACTION, "ids": ["ACME-5", "ACME-306"], "ready_ids": ["ACME-306"]}
        s.apply(plane_with(fake), [action], log=lambda m: None)
        self.assertEqual(fake.patches, [("ACME-306", "s-ready")])
        self.assertEqual(len(fake.items["ACME-5"]["comments"]), 1)


class CustomBoardTests(unittest.TestCase):
    def test_custom_ready_state_and_movable_states(self):
        class QaBoard(FakePlane):
            STATES = {"s-todo": "Todo", "s-progress": "In Progress", "s-qa": "QA"}

        config = s.Config(identifier="ACME", ready_state="QA", movable_states=frozenset({"In Progress"}))
        action = {**ApplyTests.ACTION, "ready_ids": ["ACME-306"]}
        fake = QaBoard()
        s.apply(s.Plane("https://plane.example", "ws", "key", config, opener=fake), [action], log=lambda m: None)
        self.assertEqual(fake.patches, [("ACME-306", "s-qa")])
        fake = QaBoard(state="s-todo")
        s.apply(s.Plane("https://plane.example", "ws", "key", config, opener=fake), [action], log=lambda m: None)
        self.assertEqual(fake.patches, [])

    def test_board_without_ready_state_logs_and_does_not_crash(self):
        class NoReady(FakePlane):
            STATES = {"s-todo": "Todo", "s-progress": "In Progress"}

        fake = NoReady(items=("ACME-306", "ACME-5"))
        logs = []
        action = {**ApplyTests.ACTION, "ids": ["ACME-306", "ACME-5"], "ready_ids": ["ACME-306"]}
        s.apply(plane_with(fake), [action], log=logs.append)
        self.assertTrue(any("ACME-306: lỗi khi gọi Plane" in m for m in logs))
        self.assertEqual(len(fake.items["ACME-5"]["comments"]), 1)


class MainTests(unittest.TestCase):
    def test_missing_api_key_skips_and_exits_zero(self):
        with mock.patch.dict(os.environ, {"PLANE_API_KEY": ""}), mock.patch("sys.stdout", io.StringIO()):
            self.assertEqual(s.main(), 0)

    def test_missing_url_or_identifier_skips_and_exits_zero(self):
        for env in ({"PLANE_API_KEY": "k", "PLANE_IDENTIFIER": "ACME"},
                    {"PLANE_API_KEY": "k", "PLANE_BASE_URL": "https://plane.example", "PLANE_WORKSPACE_SLUG": "ws"}):
            with mock.patch.dict(os.environ, env, clear=True), mock.patch("sys.stdout", io.StringIO()) as out:
                self.assertEqual(s.main(), 0)
                self.assertIn("bỏ qua", out.getvalue())

    def test_unexpected_failure_still_exits_zero(self):
        with mock.patch.dict(os.environ, {"PLANE_API_KEY": "k", "PLANE_IDENTIFIER": "ACME", "PLANE_BASE_URL": "https://plane.example",
                                      "PLANE_WORKSPACE_SLUG": "ws", "GITLAB_CI": "true",
                                      "CI_PIPELINE_SOURCE": "merge_request_event"}), \
                mock.patch("sys.stdout", io.StringIO()):
            self.assertEqual(s.main(), 0)


if __name__ == "__main__":
    unittest.main()

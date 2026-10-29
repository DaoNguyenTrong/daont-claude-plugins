import os
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(os.path.dirname(HERE), "commit-msg-refs.sh")


def render(text, values):
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


class CommitMsgRefsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "repo")
        os.mkdir(self.repo)
        self.script = os.path.join(self.tmp.name, "hook.sh")
        with open(HOOK, encoding="utf-8") as source, open(self.script, "w", encoding="utf-8") as target:
            target.write(render(source.read(), {"identifier": "ACME", "pluginVersion": "0.1.0"}))
        self.git("init", "-q")
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")
        self.git("commit", "-q", "--allow-empty", "-m", "init")

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True, text=True)

    def run_hook(self, branch, message):
        self.git("checkout", "-q", "-B", branch)
        path = os.path.join(self.tmp.name, "MSG")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(message)
        result = subprocess.run(["bash", self.script, path], cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_adds_the_id_from_the_branch_as_a_trailer(self):
        out = self.run_hook("feature/acme-12-add-x", "feat: add x\n")
        self.assertIn("Refs: ACME-12", out)
        self.assertTrue(out.startswith("feat: add x\n"))

    def test_ignores_branches_whose_prefix_only_ends_like_the_identifier(self):
        message = "feat: add x\n"
        self.assertEqual(self.run_hook("feature/xacme-12-x", message), message)

    def test_ignores_ids_with_letters_or_underscores_glued_on_either_side(self):
        message = "feat: add x\n"
        for branch in ("feature/acme-1x-foo", "feature/acme-12a", "feature/my_acme-3-x"):
            self.assertEqual(self.run_hook(branch, message), message, branch)

    def test_reads_the_id_at_the_end_of_the_branch_name(self):
        self.assertIn("Refs: ACME-7", self.run_hook("fix/acme-7", "fix: y\n"))

    def test_ignores_a_branch_without_a_number(self):
        message = "feat: add x\n"
        self.assertEqual(self.run_hook("feature/acme--x", message), message)

    def test_ignores_branches_without_an_id(self):
        message = "feat: add x\n"
        self.assertEqual(self.run_hook("main", message), message)

    def test_does_not_add_the_id_twice(self):
        message = "feat: add x\n\nRefs: ACME-12\n"
        self.assertEqual(self.run_hook("feature/acme-12-x", message), message)

    def test_leaves_merge_subjects_alone(self):
        message = "Merge branch 'dev' into feature/acme-12-x\n"
        self.assertEqual(self.run_hook("feature/acme-12-x", message), message)

    def test_leaves_empty_and_comment_only_messages_alone(self):
        for message in ("", "\n", "# On branch feature/acme-12-x\n# nothing\n"):
            self.assertEqual(self.run_hook("feature/acme-12-x", message), message)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Validate the marketplace and the release-kit plugin.

    python3 scripts/validate.py                # all checks
    python3 scripts/validate.py --tag v1.2.0   # also require plugin.json version == 1.2.0

Needs: python3, `pip install jsonschema`, git, bash.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from jsonschema import Draft7Validator
except ImportError:
    sys.exit("jsonschema is required: pip install jsonschema")

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "release-kit"
SCHEMA = PLUGIN / "release-kit.schema.json"
SKILL = PLUGIN / "skills" / "git-release" / "SKILL.md"
COMMANDS = PLUGIN / "commands"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
CATEGORIES = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
LANGUAGE_RULE = ("Language: write every commit message, PR/MR title and description, "
                 "and changelog entry in English, whatever language the user talks to you in.")


def categories_in(text):
    """The changelog categories a prompt declares on its 'Categories, in this order: ...' line."""
    match = re.search(r"Categories, in this order: (.+?)\.", text)
    return [c.strip() for c in match.group(1).split(",")] if match else None


def sequential(section):
    """True when the '#### N. ' step headings of a workflow section run 1..N."""
    numbers = [int(n) for n in re.findall(r"^#### (\d+)\. ", section, flags=re.M)]
    return bool(numbers) and numbers == list(range(1, len(numbers) + 1))

failures = []


def check(ok, message):
    print(("  ok    " if ok else "  FAIL  ") + message)
    if not ok:
        failures.append(message)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def json_blocks(path):
    text = path.read_text(encoding="utf-8")
    return re.findall(r"```json\n(.*?)```", text, flags=re.S)


def bash(script, cwd):
    return subprocess.run(["bash", "-c", script], cwd=cwd, capture_output=True, text=True)


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def test_manifests(tag):
    print("manifests")
    market = load(ROOT / ".claude-plugin" / "marketplace.json")
    for entry in market["plugins"]:
        src = ROOT / entry["source"]
        manifest = src / ".claude-plugin" / "plugin.json"
        check(manifest.is_file(), f"{entry['name']}: {manifest.relative_to(ROOT)} exists")
        if manifest.is_file():
            data = load(manifest)
            check(data["name"] == entry["name"], f"{entry['name']}: plugin.json name matches marketplace")
            check(bool(SEMVER.match(data["version"])), f"{entry['name']}: version {data['version']} is X.Y.Z")
            if tag:
                check(data["version"] == tag.lstrip("v"), f"{entry['name']}: version {data['version']} matches tag {tag}")


def test_schema():
    print("schema")
    schema = load(SCHEMA)
    Draft7Validator.check_schema(schema)
    check(True, "schema is valid draft-07")
    validator = Draft7Validator(schema)

    documents = [(".claude/release-kit.json", load(ROOT / ".claude" / "release-kit.json"))]
    for source in (PLUGIN / "README.md", SKILL):
        for i, block in enumerate(json_blocks(source), 1):
            if '"prCli"' in block:
                documents.append((f"{source.name} example {i}", json.loads(block)))
    for name, doc in documents:
        errors = [e.message for e in validator.iter_errors(doc)]
        check(not errors, f"{name} validates" + (f": {errors[0]}" if errors else ""))

    base = {"prCli": "gh", "gate": {"mandatory": "true"}, "modes": ["standard"]}
    good = [
        ("prCli none", {**base, "prCli": "none"}),
        ("tagPrefix empty", {**base, "tagPrefix": ""}),
        ("versionFiles", {**base, "versionFiles": [{"path": "package.json", "bumpCmd": "x {version}"}]}),
        ("legacy frontendVersionFile", {**base, "frontendVersionFile": "a/package.json"}),
        ("qaBranches", {**base, "qaBranches": ["qa"]}),
    ]
    bad = [
        ("unknown key", {**base, "devbranch": "dev"}),
        ("missing gate", {"prCli": "gh", "modes": ["standard"]}),
        ("unknown prCli", {**base, "prCli": "bitbucket"}),
        ("empty modes", {**base, "modes": []}),
        ("duplicate modes", {**base, "modes": ["standard", "standard"]}),
        ("both version keys", {**base, "versionFiles": [], "frontendVersionFile": "package.json"}),
        ("versionFiles entry without path", {**base, "versionFiles": [{"bumpCmd": "x"}]}),
        ("unknown gate key", {**base, "gate": {"mandatory": "true", "phase2": "x"}}),
        ("bad tagPrefix", {**base, "tagPrefix": "v 1"}),
    ]
    for name, doc in good:
        check(validator.is_valid(doc), f"accepts: {name}")
    for name, doc in bad:
        check(not validator.is_valid(doc), f"rejects: {name}")


def test_prompts():
    print("prompts")
    schema = load(SCHEMA)["properties"]
    skill = SKILL.read_text(encoding="utf-8")
    check(skill.startswith("---\nname: git-release\ndescription:"), "SKILL.md has name + description frontmatter")

    allowed = {"name"}  # `{{name}}` is the notation example, not a key
    referenced = set(re.findall(r"\{\{([A-Za-z0-9.]+)\}\}", skill))
    for key in sorted(referenced - allowed):
        head, _, rest = key.partition(".")
        ok = head in schema and (not rest or rest in schema[head].get("properties", {}))
        check(ok, f"SKILL.md {{{{{key}}}}} is a schema key")
    check("gate.phase1" in referenced, "SKILL.md reads gate.phase1 (the {{key}} regex sees keys with digits)")

    # section cross-references: every *Italic Name* must resolve to a heading or a bold lead-in
    headings = [h.lower() for h in re.findall(r"^#{2,4} (.+)$", skill, flags=re.M)]
    bolds = [b.lower() for b in re.findall(r"\*\*([^*\n]+?)\*\*", skill)]
    for ref in sorted(set(re.findall(r"(?<!\*)\*([A-Z][^*\n]+?)\*(?!\*)", skill))):
        ok = any(t.startswith(ref.lower()) for t in headings + bolds)
        check(ok, f"SKILL.md reference *{ref}* resolves to a heading or bold lead-in")

    for command in sorted(COMMANDS.glob("*.md")):
        text = command.read_text(encoding="utf-8")
        check(text.startswith("---\ndescription:"), f"{command.name} has description frontmatter")
        keys = re.findall(r"^\| [^|]+ \| `(\w+)` \|", text, flags=re.M)
        for key in keys:
            check(key in schema, f"{command.name} config key `{key}` is in the schema")

    # every schema key must be used somewhere in the prompts (the reverse of the check above)
    prompts = skill + "".join(c.read_text(encoding="utf-8") for c in COMMANDS.glob("*.md"))
    for key in sorted(set(schema) - {"$schema"}):
        check(key in prompts, f"schema key `{key}` is used by a prompt")

    sync = (COMMANDS / "git-sync.md").read_text(encoding="utf-8")
    check("releaseKitBase" in sync and "releaseKitBase" in (COMMANDS / "git-commit.md").read_text(encoding="utf-8"),
          "git-commit records and git-sync reads branch.<name>.releaseKitBase")

    mr = COMMANDS / "git-mr.md"
    check(mr.is_file(), "commands/git-mr.md exists")
    if mr.is_file():
        mr_text = mr.read_text(encoding="utf-8")
        check(categories_in(mr_text) == CATEGORIES, "git-mr.md lists the six changelog categories in order")
        check("releaseKitBase" in mr_text, "git-mr reads branch.<name>.releaseKitBase")

    commit = (COMMANDS / "git-commit.md").read_text(encoding="utf-8")
    check("Unreleased" not in commit and "changelogPath" not in commit, "git-commit no longer touches the changelog")
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
    reconcile = skill.find("#### 2. Reconcile with `{{mainBranch}}`")
    sync = skill.find("#### 3. Sync `{{changelogPath}}`")
    ship_gate = skill.find("#### 4. Run the gate — mandatory")
    check(0 <= reconcile < sync < ship_gate, "Phase 2 syncs the changelog (step 3) after reconciling with main (step 2) and before the gate (step 4)")
    writing = re.search(r"\*\*Writing the section:\*\*[^\n]*", skill)
    check(writing is not None and "already exists" in writing.group(0) and "second heading" in writing.group(0),
          "Collect changelog says what to do when the version section already exists")
    check("Replace `## [Unreleased]` with" not in skill, "SKILL.md no longer promotes [Unreleased] on dev")
    check("Do not edit this entry again on the release branch" not in skill, "SKILL.md no longer forbids writing the version section on release/*")

    readme = (PLUGIN / "README.md").read_text(encoding="utf-8")
    check("| `git-mr` | command |" in readme, "plugin README lists git-mr in the component table")
    check("merge_request_templates" in readme and "pull_request_template.md" in readme,
          "plugin README documents the GitLab and GitHub MR templates")

    for path in (COMMANDS / "git-commit.md", COMMANDS / "git-mr.md", SKILL):
        check(LANGUAGE_RULE in path.read_text(encoding="utf-8"), f"{path.name} carries the English-language rule")


def extract(text, needle):
    for line in text.splitlines():
        if needle in line:
            return line.strip()
    raise AssertionError(f"line containing {needle!r} not found")


def test_git_snippets():
    """Run commands from the prompts against throwaway repos."""
    print("git snippets (from the prompts)")
    skill = SKILL.read_text(encoding="utf-8")
    guard = extract(skill, "git rev-list origin/{{mainBranch}}..HEAD | grep -F -x -f").replace("{{mainBranch}}", "main").replace("{{devBranch}}", "dev")
    latest = extract(skill, "git tag --list '{{tagPrefix}}[0-9]*'")

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

        git(w, "checkout", "-q", "-b", "main"); commit("a"); git(w, "push", "-q", "origin", "main")
        git(w, "checkout", "-q", "-b", "dev"); commit("d1"); git(w, "push", "-q", "origin", "dev")
        git(w, "fetch", "-q", "origin")

        git(w, "checkout", "-q", "-b", "hotfix/good", "origin/main"); commit("g")
        out = bash(guard, w)
        check(out.returncode == 1 and not out.stdout.strip(), "hotfix guard passes a branch cut from main")

        git(w, "checkout", "-q", "-b", "hotfix/bad", "origin/dev"); commit("h")
        out = bash(guard, w)
        check(out.stdout.strip() != "", "hotfix guard flags a branch cut from dev")

        git(w, "tag", "foo", "origin/main")
        for prefix in ("v", "rel-", ""):
            for version in ("1.0.0", "1.0.9", "1.0.10", "1.1.0-rc.1"):
                git(w, "tag", prefix + version, "origin/main")
            out = bash(latest.replace("{{tagPrefix}}", prefix), w)
            check(out.stdout.strip() == f"{prefix}1.0.10",
                  f"latest-tag command with prefix {prefix!r} picks {prefix}1.0.10 (got {out.stdout.strip()!r})")

        git(w, "checkout", "-q", "-b", "release/v1.0.0", "origin/dev"); git(w, "push", "-q", "origin", "release/v1.0.0")
        git(w, "checkout", "-q", "dev"); commit("d2"); git(w, "push", "-q", "origin", "dev")
        git(w, "checkout", "-q", "-b", "fix/x", "release/v1.0.0"); commit("f")
        git(w, "fetch", "-q", "origin")
        def pick_base(candidates):
            """The rule from git-sync.md: fewest commits ahead; ties prefer release/* > QA > integration."""
            ahead = {b: int(bash(f"git rev-list --count origin/{b}..HEAD", w).stdout) for b in candidates}
            rank = lambda b: 0 if b.startswith("release/") else 1 if b == "staging" else 2
            return min(candidates, key=lambda b: (ahead[b], rank(b))), ahead

        chosen, ahead = pick_base(["release/v1.0.0", "dev"])
        check(chosen == "release/v1.0.0", f"tie (release just cut): fix/* picks release/*, not dev: {ahead}")

        git(w, "checkout", "-q", "release/v1.0.0"); commit("r1"); git(w, "push", "-q", "origin", "release/v1.0.0")
        git(w, "checkout", "-q", "-B", "fix/y", "release/v1.0.0"); commit("f2")
        git(w, "fetch", "-q", "origin")
        chosen, ahead = pick_base(["release/v1.0.0", "dev"])
        check(chosen == "release/v1.0.0" and ahead["release/v1.0.0"] < ahead["dev"],
              f"release moved on: fix/* is strictly closer to release/* than dev: {ahead}")

        git(w, "checkout", "-q", "main"); git(w, "merge", "-q", "--no-ff", "release/v1.0.0", "-m", "Release v1.0.0"); git(w, "push", "-q", "origin", "main")
        git(w, "fetch", "-q", "origin")
        merged = bash("git merge-base --is-ancestor origin/release/v1.0.0 origin/main", w).returncode == 0
        unmerged = bash("git merge-base --is-ancestor origin/dev origin/main", w).returncode != 0
        check(merged and unmerged, "merged check: release branch is merged into main, dev is not")


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
        ("CRLF line endings", "## Summary\r\nwhy\r\n\r\n## Changelog\r\n- Added: A.\r\n\r\n## Test plan\r\nx\r\n", "- Added: A."),
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
            check(out.stdout.replace("\r", "").strip() == expected, f"Changelog section cut from a description: {name}")


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="release tag; plugin.json version must match it")
    args = parser.parse_args()

    test_manifests(args.tag)
    test_schema()
    test_prompts()
    test_git_snippets()
    test_changelog_snippets()
    test_changelog_ranges()

    print()
    if failures:
        print(f"{len(failures)} check(s) failed")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="release tag; plugin.json version must match it")
    args = parser.parse_args()

    test_manifests(args.tag)
    test_schema()
    test_prompts()
    test_git_snippets()

    print()
    if failures:
        print(f"{len(failures)} check(s) failed")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()

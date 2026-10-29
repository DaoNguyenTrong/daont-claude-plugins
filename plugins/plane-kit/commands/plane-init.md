---
description: "Set up plane-kit in this repo: create .claude/plane-kit.json, vendor the CI script, CI template and Refs hook, and enable the plugin for the team."
---

# Plane Init

Set a repo up for the Plane workflow: write `.claude/plane-kit.json`, copy the CI sync script and the template for the repo's host, add the commit-msg hook that appends `Refs: <ID>`, and enable the plugin in `.claude/settings.json`. Safe to re-run.

## 0. Settings

Read `.claude/plane-kit.json` if it exists and validate it against `plane-kit.schema.json` in this plugin. If it does not exist, create it by asking for each required key once, offering the default for optional keys only when the user wants to change it:

| Setting | Config key | Required | Default / how to find it |
| --- | --- | --- | --- |
| Project identifier | `identifier` | yes | ask (for example `ACME`) |
| Project id | `projectId` | yes | `project list` in the Plane MCP, or ask |
| Workspace | `workspaceSlug` | yes | ask |
| Plane URL | `baseUrl` | yes | ask |
| Code host | `host` | yes | guessed from `git remote get-url origin` (`github` / `gitlab`); ask when it cannot be guessed |
| Integration branch | `devBranch` | no | `dev` |
| Ready state | `readyState` | no | `Ready For Testing` |
| Movable states | `movableStates` | no | `["Backlog","Todo","In Progress"]` |
| Agent state policy | `agentMaySet` | no | both `inProgress` and `ready`; may only be narrowed, never contain `Done` |
| Language | `language` | no | `vi` |
| Branch pattern | `branchPattern` | no | `{feature,fix,chore}/<identifier-lowercase>-<n>-<slug>` |

An invalid file is reported key by key; stop and ask rather than rewriting it.

## 1. Copy the files

Take the plugin version from `.claude-plugin/plugin.json` (`pluginVersion`). Render each template by replacing `{{key}}` with the config value (`movableStates` joined with commas, `pluginVersion` as above); leave `${{ ... }}` untouched. Targets are fixed:

| Template (`templates/`) | Written to | When |
| --- | --- | --- |
| `plane_sync.py` | `.plane-kit/plane_sync.py` | always |
| `commit-msg-refs.sh` | `.plane-kit/commit-msg-refs.sh` | always |
| `gitlab/plane.yml` | `.gitlab/ci/plane.yml` | `host` is `gitlab` |

Never copy `templates/tests/`.

For each target:

- Does not exist → write it.
- Exists, its first 3 lines hold a `# plane-kit: v…` marker and the content equals the rendering → leave it alone.
- Exists with a marker but different content → leave it and say `/plane-sync-ci` updates it.
- Exists without a marker (someone else's file) → **stop and ask** before touching it.

Then wire the hooks and CI:

- GitLab: tell the user to add `include: - local: .gitlab/ci/plane.yml` to `.gitlab-ci.yml`, and to give the job the `stage:` and `tags:` their runners need. Do not edit `.gitlab-ci.yml` unasked.
- Commit hook: if `lefthook.yml` exists, show the rendered `lefthook-refs.yml` block and merge it into `commit-msg` after the user agrees (keep its `priority: 1` so the hook runs before message linters). Otherwise write `.plane-kit/commit-msg-refs.sh` also as `.githooks/commit-msg` (same marker rule) and tell the user to run `git config core.hooksPath .githooks`.

## 2. Enable the plugin for the team

Merge into `.claude/settings.json`, keeping every other key: `"plane-kit@daont-claude-plugins": true` under `enabledPlugins`, and the `daont-claude-plugins` entry under `extraKnownMarketplaces` (`source: github`, `repo: DaoNguyenTrong/daont-claude-plugins`) if it is not already there. Never overwrite the file.

## 3. The API key

Tell the user to create a masked (and protected, if the host supports it) CI variable named `PLANE_API_KEY` in the repo settings. This command never accepts the key as an argument, never print it, and never writes it to a file.

## 4. Report

List what was written, what was left alone and why, and the steps the user still has to do (include line, runner `stage:`/`tags:`, `PLANE_API_KEY`, `core.hooksPath`). Remind them to run `/plane-sync-ci` after each `claude plugin update`.

## Rules

- Write only new files or files that carry a plane-kit marker; for anything else stop and ask
- Never print, log or store `PLANE_API_KEY`
- Never edit CI configuration files other than the rendered `plane.yml`

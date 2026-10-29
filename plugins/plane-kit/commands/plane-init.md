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

Render each template by replacing `{{key}}` with the config value (`movableStates` joined with commas, `pluginVersion` is `version` from `.claude-plugin/plugin.json`). A missing optional key renders with its default from the table in step 0, never as a literal `{{key}}`; leave `${{ ... }}` untouched. Targets are fixed:

| Template (`templates/`) | Written to | When |
| --- | --- | --- |
| `plane_sync.py` | `.plane-kit/plane_sync.py` | always |
| `commit-msg-refs.sh` | `.plane-kit/commit-msg-refs.sh` | always |
| `gitlab/plane.yml` | `.gitlab/ci/plane.yml` | `host` is `gitlab` |
| `github/plane-sync.yml` | `.github/workflows/plane-sync.yml` | `host` is `github` |

Never copy `templates/tests/`.

For each target:

- Does not exist → write it.
- Exists, its first 3 lines hold a `# plane-kit: v…` marker and the content equals the rendering → leave it alone.
- Exists with a marker but different content → leave it and say `/plane-sync-ci` updates it.
- Exists without a marker (someone else's file) → **stop and ask** before touching it.

Then wire the hooks and CI:

- GitHub: nothing to include; tell the user to add the `PLANE_API_KEY` repository secret (the workflow declares `contents: read` and `pull-requests: read` itself).
- GitLab: tell the user to add `include: - local: .gitlab/ci/plane.yml` to `.gitlab-ci.yml`. If their runners need `stage:` or `tags:`, they override them there with a job of the same name (`plane-sync:` with just those keys; GitLab merges it with the included job), so the marked file stays unedited. Do not edit `.gitlab-ci.yml` unasked.
- Commit hook: if `lefthook.yml` exists, show the rendered `lefthook-refs.yml` block and merge it into `commit-msg` after the user agrees (keep its `priority: 1` so the hook runs before message linters). If the lefthook block is already there, leave it. Otherwise write `.plane-kit/commit-msg-refs.sh` also as `.githooks/commit-msg` (same marker rule), run `chmod +x` on it and `git update-index --chmod=+x .githooks/commit-msg` (git ignores a hook that is not executable), and tell the user to run `git config core.hooksPath .githooks` — warning that this stops git from running hooks in `.git/hooks` or husky.

## 2. Enable the plugin for the team

Merge into `.claude/settings.json`, keeping every other key: `"plane-kit@daont-claude-plugins": true` under `enabledPlugins`, and, if it is not already there, this entry under `extraKnownMarketplaces`: `"daont-claude-plugins": {"source": {"source": "github", "repo": "DaoNguyenTrong/daont-claude-plugins"}}`. Never overwrite the file.

## 3. The API key

Tell the user to create a CI variable named `PLANE_API_KEY` in the repo settings: on GitLab masked, not protected (MR pipelines on unprotected `feature/*` branches do not receive protected variables, so link and comment on MR open would silently never run); on GitHub a repository secret. This command never accepts the key as an argument, never print it, and never writes it to a file.

## 4. Report

List what was written, what was left alone and why, and the steps the user still has to do (include line, runner `stage:`/`tags:`, `PLANE_API_KEY`, `core.hooksPath`). Remind them to run `/plane-sync-ci` after each `claude plugin update`.

## Rules

- Write only new files or files that carry a plane-kit marker; for anything else stop and ask
- Never print, log or store `PLANE_API_KEY`
- Never edit CI configuration files other than the rendered `plane.yml` / `plane-sync.yml`

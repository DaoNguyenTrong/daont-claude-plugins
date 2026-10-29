# plane-kit

Plane work-item workflow shared across projects: the `plane-task` skill, the `/plane-init` and `/plane-sync-ci` commands, and a CI script (vendored into each repo) that links MRs/PRs to Plane work items.

## Install

```bash
claude plugin marketplace add DaoNguyenTrong/daont-claude-plugins
claude plugin install plane-kit@daont-claude-plugins
```

Then run `/plane-init` in the project and set `PLANE_API_KEY` (a masked CI variable on GitLab, a repository secret on GitHub; never committed).

After every `claude plugin update`, run `/plane-sync-ci` to refresh the files vendored into the repo.

## Components

| Name | Kind | What it does |
| --- | --- | --- |
| `plane-task` | skill | How an agent works with Plane work items: find the item, move it, branch, link MRs/PRs, write items. |
| `plane-init` | command | Creates `.claude/plane-kit.json`, vendors the CI script, template and hook into the repo. |
| `plane-sync-ci` | command | Compares vendored files with the plugin's version and updates them after a diff. |

## Configuration

`.claude/plane-kit.json`, validated by `plane-kit.schema.json`:

```json
{
  "identifier": "ACME",
  "projectId": "54c5b126-c344-42ef-a1db-82b20c1763d8",
  "workspaceSlug": "acme",
  "baseUrl": "https://plane.example.com",
  "host": "gitlab"
}
```

| Key | Required | Meaning |
| --- | --- | --- |
| `identifier` | yes | Work item prefix, for example `ACME`. |
| `projectId` | yes | Project UUID. |
| `workspaceSlug` | yes | Workspace slug. |
| `baseUrl` | yes | Plane URL. |
| `host` | yes | `gitlab` or `github`. |
| `devBranch` | no | Default `dev`. |
| `readyState` | no | Default `Ready For Testing`. |
| `movableStates` | no | Default `["Backlog","Todo","In Progress"]`. |
| `agentMaySet` | no | Narrows the agent's state policy; `Done` is never allowed. |
| `language` | no | Default `vi`. |
| `branchPattern` | no | Default `{feature,fix,chore}/<identifier-lowercase>-<n>-<slug>`. |

## Manual checks

Run once per host before a release; record results here.

- [ ] `/plane-init` on an empty GitLab repo and on an empty GitHub repo (files written, markers present, settings merged, no key printed).
- [ ] `/plane-sync-ci` when the vendored files are older than the plugin (diff shown, only agreed files written; a hand-edited file at the same version is flagged as locally modified).
- [ ] A real MR/PR with and without a work item id: link and comment posted once, re-run adds nothing, no id logs and exits 0.

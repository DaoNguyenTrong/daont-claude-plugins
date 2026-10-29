---
name: plane-task
description: Use when starting, doing or finishing a coding task tracked in Plane — finding the work item, moving it to In Progress, cutting the branch, linking the MR/PR, writing a new item. Driven by the project's .claude/plane-kit.json. Examples: "work on ACME-42", "create a Plane item for this", "open the MR for this task"
---

# Plane Task Tracking

Applies to **every** coding task in a repo that has `.claude/plane-kit.json`. The tracker is the shared view of what is being built right now — an item left in `Todo` while its code is already merged makes the board useless to everyone else.

Read `.claude/plane-kit.json` first. If it is missing, tell the user to run `/plane-init` and stop using this skill.

Project: identifier `{{identifier}}`, id `{{projectId}}` (the workspace may hold other projects; never operate on a different one by accident). The code host is `{{host}}`: say "MR" for `gitlab` and "PR" for `github`.

## Before writing code

1. **Identify the work item** the change belongs to. If the user named one (`{{identifier}}-42`, a title), resolve it with `workitem retrieve_by_identifier` or `workitem list` + `pql`.
2. If no item was named, look for it — `workitem list` with `pql='assignee = currentUser() AND stateGroup IN openStates()'`, or `workitem search` on keywords from the request — and **confirm the match with the user** before touching it.
3. If nothing matches, say so and ask. Never create a work item unprompted — deciding parent/child split, estimate, label, cycle and assignee is a bigger decision than the coding task at hand.
4. Read the item's description and acceptance criteria before coding — they are part of the requirement.
5. Move it to **`In Progress`** when implementation actually starts (not while still orienting or planning), if `{{agentMaySet}}` allows it (`inProgress` in the list, or `agentMaySet` absent).
6. Cut the branch as `{{branchPattern}}` (default `{feature,fix,chore}/<identifier-lowercase>-<n>-<slug>`). The commit-msg hook then adds `Refs: {{identifier}}-<n>` to every commit; a commit that belongs to a *different* item gets its own `Refs:` footer written by hand.

## Writing a new work item

Only when the user asks for one. The item is read by the tester and the product owner, not by the next engineer, so write it the way a teammate would explain the job in chat, in `{{language}}`.

- **Title:** one short phrase naming the outcome or the problem in the user's words.
- **Description:** plain text, 2–4 short sentences: what is wrong or wanted, and what should be true afterwards. No HTML, no bold labels such as "Cause / Approach / AC", no headings.
- **Keep out of the description:** class, method, file or property names, the implementation plan, the risk class. Those belong in the commit, the MR/PR and the closing comment. A name is allowed only when the tester must look for exactly that text on screen.
- **Acceptance points:** add a short list only when there are three or more distinct checks; otherwise fold them into the sentences.
- **Set only what was asked:** priority and parent only when the user gave one or the parent is obvious; never assignees, labels, estimates or dates unprompted.

## Linking the MR/PR to the item

The link is carried by the id:

- **Branch** `…/<identifier-lowercase>-<n>-…`, **commit** trailer `Refs: {{identifier}}-<n>`, and **MR/PR description** whose first line is `Plane: {{identifier}}-<n>` (comma-separate several). Creating an MR/PR from the CLI can bypass the host's description template, so write that line yourself.
- The `plane-sync` CI job reads those ids and adds the MR/PR link plus a comment to each item on open/update, merge into `{{devBranch}}`, and release tag.
- On merge into `{{devBranch}}` it also moves the MR/PR's **own** items — the ids in the branch name or title — from `Backlog`/`Todo`/`In Progress` (`{{movableStates}}`) to **`{{readyState}}`**. Ids that appear only in a commit's `Refs:` are commented on, never moved. An item already past that point keeps its state.
- So an MR/PR that covers only part of an item would flip it too early: split the item into children with one MR/PR each, and name the branch after the child.

## After finishing

Finishing the code and getting tests green does **not** move the item, and neither does creating the MR/PR — it stays `In Progress` until the change is merged into `{{devBranch}}`. Then `plane-sync` moves it to `{{readyState}}`; don't move it yourself beforehand.

When the user asks to create the MR/PR, post a short comment in `{{language}}` (`workitem_comment create`) on the item saying what was implemented and which branch/commit carries it — the tester needs to know where to look.

**Hotfix** straight into the production branch is the exception: CI does not move it. Move it to `{{readyState}}` yourself when the user asks for the hotfix MR/PR (if `ready` is allowed).

If the work spans several items, transition each one as its own scope completes; don't flip a parent while its children are still open.

## States this agent may set

`{{agentMaySet}}` can only narrow this table, never widen it:

| Token | State | When |
| --- | --- | --- |
| `inProgress` | `In Progress` | Implementation started; also when reopening an item after the tester sent it back, so the next merge moves it to `{{readyState}}` again |
| `ready` | `{{readyState}}` | Only for a hotfix MR/PR into the production branch, or when `plane-sync` could not run (no `PLANE_API_KEY`, job failed — check its log) and the change has been merged into `{{devBranch}}` |

Everything else is somebody else's call:

- Never set `Done`: it is business acceptance and requires explicit product-owner confirmation — passing tests are never enough.
- `Testing`, `Pending`, `Cancelled`, `Backlog` — only when the user explicitly asks.

## Mechanics

- `workitem update`'s `state` field takes a **UUID**, and state ids are per-project. Resolve the name at update time with `state list` (`project_id={{projectId}}`) — do not hardcode state UUIDs in code, docs or memory; they are cheap to look up and wrong after any board edit.
- Match state names exactly as the board spells them (for example `Ready For Testing`, capital `F`); a case-insensitive guess can miss.

---
description: "Update the plane-kit files vendored in this repo (CI script, template, hook) to the installed plugin version, after showing a diff."
---

# Plane Sync CI

The CI script, template and hook were copied into this repo by `/plane-init`. This command compares them with the installed plugin and updates them. Run it after every `claude plugin update`.

## Steps

1. Read `.claude/plane-kit.json` (stop with "run `/plane-init` first" if it is missing) and `version` from this plugin's `.claude-plugin/plugin.json` (`pluginVersion`).
2. For each vendored file listed in `/plane-init` step 1 for this repo's `host` (and `.githooks/commit-msg` if present), read the `# plane-kit: v…` marker in its first 3 lines.
   - No marker → treat it as someone else's file: stop and ask, never overwrite.
3. Render the plugin's template with the config values and `pluginVersion`, exactly as `/plane-init` does.
4. Compare:
   - Marker equals `pluginVersion` and content equals the rendering → up to date, say so.
   - Marker equals `pluginVersion` but content differs → the file is **locally modified**: warn, show the `diff`, and keep the file unless the user asks to restore it.
   - Marker older than `pluginVersion` → show the `diff` between the file and the rendering. A local edit that is not part of the plugin's own change is visible in that diff; point it out.
5. You must ask before overwriting: write the rendered file only for the files the user agrees to. Never touch files the diff did not show.
6. Report each file as updated, kept, or up to date.

## Rules

- Never overwrite without showing the diff first
- Never change `.claude/plane-kit.json`, `.claude/settings.json` or CI files other than the vendored ones
- If any step fails, stop and report

---
name: exposure-canary
description: >-
  Creates defensive URL, DNS, and email canaries on assets the user owns,
  imports webhooks, deduplicates events, assigns severity, and renders a
  Markdown report through the CLI or the MCP tools create_canary,
  import_webhook, and render_report. Use when the user asks for a canary,
  isca, exposure alert, webhook de canário, or whether someone touched an
  asset they control. Stop when the request is to track someone else,
  fingerprint, use a pixel, identify an investigator, or plant disinformation.
---

# Exposure Canary

Use the library. Answer in the user's language. Do not write a server, a pixel, or a fingerprint collector.

`state_path` is an absolute directory inside the user's project. The CLI default is `.exposure-canary`. Keep `state.json` out of git.

## Scope

Before creating a canary, confirm which asset the user controls: a page, a DNS zone, or an email domain.

`owned` / `--owned` is their confirmation. Do not call `create_canary` without it.

One canary per surface. `label` names the surface that was touched.

## Where to plant

- **URL** — `value` is `https://<collector>/c/<id>` on a page or file they publish. The collector is an https host they operate. This version does not include that host: they export JSON from it.
- **DNS** — `value` is `<id>.<zone>` in a zone they administer. Put that name only in the material they want to watch.
- **Email** — `value` is `cn-<hex>@<domain>` in one place. They must receive mail for that domain.

After `create_canary`, return `value` and say where to plant it.

## Reading an alert

1. Ask for the JSON their collector stored. Accepted fields: `canary_id` (or the canary `value` in the text), `observed_at`, and `source`.
2. Call `import_webhook`.
3. Call `render_report` and explain the severity:
   - **High** on DNS or email: that canary was used.
   - **Medium** on a URL: the first source to touch that URL.
   - **High** on a URL: a source other than the first one.
   - **Low**: the same source returned outside the 5-minute window, or the token is not in the registry.
   - A duplicate in the same window, from the same source, for the same canary, is ignored.
4. Name the asset and the label. Person, intent, and searches made outside the canary stay out of the report.

## Stop

Stop, with no code and no canary, when the request asks for:

- someone else's asset
- who visited, beyond the source their collector already stored
- a fingerprint, pixel, user-agent, geolocation, or device profile
- a decoy document, a fake key, disinformation, or a reply to the source
- a server that captures visitors

Say that this version covers canary creation, webhook import, and the report.

## Tools

- `create_canary(kind, label, asset, owned, state_path, collector|zone|domain)`
- `import_webhook(state_path, webhook_path or payload_json)`
- `render_report(state_path, optional output_path)`

CLI: `exposure-canary create`, `exposure-canary import-webhook`, `exposure-canary report`.

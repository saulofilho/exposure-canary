# Exposure Canary

Site: [saulofilho.github.io/exposure-canary](https://saulofilho.github.io/exposure-canary/). The page source is `docs/`. GitHub Pages deploys it from the `Deploy GitHub Pages` workflow. The repository needs Pages set to **GitHub Actions** once, under Settings, then Pages.

Defensive canaries for assets you control. Create a unique URL, DNS name, or email local-part, import the JSON your own collector already stored, deduplicate the hits, assign a severity, and render a Markdown report.

The report records the time, the canary, the asset, and the source string your collector sent. It does not identify a person, infer intent, or cover a search that never touched the canary.

| Kind | Value you plant | You must control |
| --- | --- | --- |
| `url` | `https://<collector>/c/<id>` | The https collector host |
| `dns` | `<id>.<zone>` | The DNS zone |
| `email` | `cn-<hex>@<domain>` | The mailbox domain |

This package does not run a visitor collector. Point a host you operate at the URL, or watch the DNS name and mailbox yourself, then import the JSON.

The id looks like `cn` plus 16 hex characters. The email local-part is `cn-` plus those same 16 hex characters. `state.json` stores the ids. Keep the state directory out of git.

## Requirements

- Python 3.10 or newer
- [uv](https://docs.astral.sh/uv/) on `PATH` when Cursor starts the MCP server

## Install

From a clone of this repository:

```bash
uv venv
uv pip install -e ".[mcp]"
```

`pip install -e ".[mcp]"` works the same way. Without the `mcp` extra, the CLI and the Python API still run. The MCP server needs the extra.

Check the install:

```bash
exposure-canary --version
```

## State

Every command reads and writes `<state>/state.json`. The CLI default is `.exposure-canary` in the current directory. Pass `--state` or MCP `state_path` to put it somewhere else. Use an absolute path from the agent so the file lands in the project you intend.

```json
{
  "version": 1,
  "canaries": [],
  "events": [],
  "last_import": {
    "imported": 1,
    "duplicates": 0,
    "unmatched": 0,
    "at": "2026-10-14T12:00:00Z"
  }
}
```

A canary record has `id`, `kind`, `label`, `asset`, `value`, and `created_at`. An event has `canary_id`, `kind`, `observed_at`, `source`, `severity`, and `dedup_key`. The raw webhook body is not stored.

## CLI

`--owned` is required on `create`. It records your confirmation that the asset is yours. The tool cannot prove ownership.

### URL

```bash
exposure-canary create \
  --kind url \
  --label resume-pdf \
  --asset personal-site \
  --collector https://collect.example/hooks \
  --owned
```

`--collector` must be `https`, with a host, and without a username or password. A query string or fragment on the collector is dropped. The planted value is `<collector>/c/<id>`.

`https://localhost` and an IPv4 host are accepted, including a port.

### DNS

```bash
exposure-canary create \
  --kind dns \
  --label private-note \
  --asset example.com \
  --zone example.com \
  --owned
```

`--zone` is a hostname you administer, such as `example.com`. A trailing dot is removed. A single label, a wildcard, or an IP address is rejected.

### Email

```bash
exposure-canary create \
  --kind email \
  --label contact-page \
  --asset example.com \
  --domain example.com \
  --owned
```

`--domain` uses the same hostname rules. The planted value is the full address. One address belongs on one surface, so the label tells you where it was published.

`create` prints the record as JSON on stdout and the state file path on stderr. Exit code `0` means the canary was saved. Exit code `1` means the inputs were refused. `--label` is limited to 80 characters and `--asset` to 120. Both must be a single line.

### Import a webhook

```bash
exposure-canary import-webhook webhook.json
exposure-canary import-webhook - < webhook.json
```

The file, or stdin when the path is `-`, must be UTF-8 JSON of at most 2 MB and at most 1000 events. These shapes are accepted:

```json
{
  "canary_id": "cn0123456789abcdef",
  "observed_at": "2026-10-14T12:00:00Z",
  "source": "203.0.113.10"
}
```

```json
[
  {
    "canary_id": "cn0123456789abcdef",
    "observed_at": "2026-10-14T12:00:00Z",
    "source": "203.0.113.10"
  }
]
```

```json
{ "events": [ { "canary_id": "cn0123456789abcdef", "observed_at": "2026-10-14T12:00:00Z" } ] }
```

Field names:

| Role | Accepted keys |
| --- | --- |
| Canary | `canary_id`, `token`, `token_id`. If those are absent, the id is read from `path`, `url`, `value`, `email`, `address`, `host`, `qname`, or `name`. |
| Time | `observed_at`, `timestamp`, `time`, `ts`. ISO-8601. `Z` means UTC. A value without a timezone is read as UTC. |
| Source | `source`, `remote`, `ip`, `remote_addr`, `client_ip`. Missing source becomes `unspecified`. The string is trimmed to 256 characters. |

An event with no canary id or no timestamp fails the whole import and leaves the state file unchanged. A canary id that is not in the registry is stored as severity `low` and counted as unmatched.

Stdout is a count object:

```json
{ "imported": 1, "duplicates": 0, "unmatched": 0 }
```

### Report

```bash
exposure-canary report
exposure-canary report -o report.md --state .exposure-canary
```

Without `-o`, the Markdown goes to stdout. With `-o`, it is written to that file and the path is printed on stderr.

## Dedup and severity

A hit is a duplicate when the canary id, the source, and the 5-minute bucket are the same. `12:00:00Z` and `12:04:59Z` collapse. `12:05:00Z` is a new bucket. Importing the same webhook again adds nothing.

| Observation | Severity in the report |
| --- | --- |
| DNS or email, new bucket | High |
| URL, first source for that canary | Medium |
| URL, a different source | High |
| URL, the same source in a later bucket | Low |
| Token that is not in the registry | Low |
| Same canary, source, and 5-minute bucket | Ignored |

Events in one payload are ordered by time before severity is assigned, so a later hit listed first in the file does not become the "first source".

## Python API

```python
from exposure_canary import State, create_canary, import_webhook, render_report

state = State.load(".exposure-canary")
canary = create_canary(
    state,
    kind="dns",
    label="private-note",
    asset="example.com",
    owned=True,
    zone="example.com",
)
result = import_webhook(
    state,
    {
        "qname": canary.value,
        "observed_at": "2026-10-14T12:00:00Z",
        "source": "203.0.113.10",
    },
)
print(result.imported, result.duplicates, result.unmatched)
print(render_report(State.load(".exposure-canary")))
```

`create_canary` and `import_webhook` save the state before they return. `owned=False`, a non-https collector, or a bad hostname raises `exposure_canary.InputError`.

## MCP

The server exposes three tools. Start it with:

```bash
uv run --extra mcp python -m exposure_canary.mcp_server
```

The console script is `exposure-canary-mcp`. Cursor's project config is `.cursor/mcp.json`, and the plugin config is `mcp.json`. Both run that `uv` command from the repository root. `uv` must be on `PATH`.

| Tool | Arguments | Returns |
| --- | --- | --- |
| `create_canary` | `kind`, `label`, `asset`, `owned`, `state_path`, and one of `collector`, `zone`, `domain` | JSON canary, or `Error: …` |
| `import_webhook` | `state_path` plus either `webhook_path` or `payload_json` | JSON counts, or `Error: …` |
| `render_report` | `state_path`, optional `output_path` | Markdown report, or `Error: …` |

Pass `owned: true` only after the user has confirmed the asset is theirs. Pass one of `webhook_path` or `payload_json`, not both. `state_path` should be an absolute directory inside the user's project.

## Agent skill

The skill tells the agent when to call those tools, where a canary may be planted, how to read the severity, and when to stop. The same text is stored in three places:

- `skills/exposure-canary/SKILL.md` — the copy the Cursor plugin loads
- `plugin/skills/exposure-canary/SKILL.md` — the Claude Code plugin
- `.cursor/skills/exposure-canary/SKILL.md` — project skill when this repo is open

`tests/test_skill.py` requires the three files to match.

The agent stops, without writing a canary, when the request asks for someone else's asset, a fingerprint or pixel, a visitor-capture server, a fake credential, or a reply to the source.

## Cursor Marketplace

This repository is a single Cursor plugin. The manifest is `.cursor-plugin/plugin.json`.

| Manifest field | Path in this repo |
| --- | --- |
| `skills` | `skills/` |
| `mcpServers` | `mcp.json` |
| `logo` | `assets/logo.svg` |

Paths are relative to the repository root and do not use `..`. The logo is committed in the repo. No `${VAR}` placeholders are used, so the manifest declares no variables. The plugin does not collect telemetry.

To submit, after this repository is public on GitHub:

1. Open [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish).
2. Submit the repository URL `https://github.com/saulofilho/exposure-canary`.
3. Wait for the manual review. Marketplace plugins have to be open source, and each update is reviewed again.

Local check before you submit: open this folder in Cursor, reload the window, and confirm that the Exposure Canary skill and the `exposure-canary` MCP server appear. `uv` must be installed for the server process.

## Tests

```bash
uv pip install -e ".[dev]"
python -m unittest discover -s tests -v
```

The `dev` extra installs the MCP SDK so `tests/test_mcp_server.py` runs. Without it, that module is skipped and the library, CLI, and skill tests still run.

## License

MIT. See [LICENSE](LICENSE).

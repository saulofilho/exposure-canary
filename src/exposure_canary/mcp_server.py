"""MCP server for exposure-canary.

Exposes canary creation, webhook import, and the Markdown report.
Compatible with MCP Python SDK 2.x (`MCPServer`).
"""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from exposure_canary.errors import Error, InputError
from exposure_canary.events import load_webhook_file, load_webhook_text
from exposure_canary.service import create_canary as create_canary_record
from exposure_canary.service import import_webhook as import_webhook_payload
from exposure_canary.service import render_report as render_report_markdown
from exposure_canary.state import State

mcp = MCPServer(
    "exposure-canary",
    instructions=(
        "Iscas defensivas para ativos que o usuário controla. "
        "Use create_canary, import_webhook e render_report. "
        "Recuse rastreamento de terceiros, fingerprint, pixel e identificação de pessoas."
    ),
)


@mcp.tool()
def create_canary(
    kind: str,
    label: str,
    asset: str,
    owned: bool,
    state_path: str,
    collector: str = "",
    zone: str = "",
    domain: str = "",
) -> str:
    """Create a URL, DNS, or email canary for an asset the user owns.

    Args:
        kind: url, dns, or email.
        label: Which surface will carry the canary.
        asset: Asset the user says they control.
        owned: Must be true. Attestation from the user, not a technical proof.
        state_path: Absolute path of the state directory inside the user's project.
        collector: https base URL. Required for kind=url.
        zone: DNS zone the user administers. Required for kind=dns.
        domain: Email domain the user receives. Required for kind=email.

    Returns:
        JSON record with id and value, or an error message.
    """
    try:
        state = State.load(state_path)
        canary = create_canary_record(
            state,
            kind=kind,
            label=label,
            asset=asset,
            owned=owned,
            collector=_blank(collector),
            zone=_blank(zone),
            domain=_blank(domain),
        )
    except Error as exc:
        return f"Error: {exc}"
    except Exception as exc:  # noqa: BLE001 — surface unexpected errors to the client
        return f"Unexpected error: {exc}"
    return json.dumps(canary.to_dict(), ensure_ascii=False)


@mcp.tool()
def import_webhook(state_path: str, webhook_path: str = "", payload_json: str = "") -> str:
    """Import a webhook JSON file or a raw JSON string into the canary state.

    Provide webhook_path or payload_json, not both. The JSON is an object or a
    list with canary_id (or the canary value), observed_at, and source.

    Args:
        state_path: Absolute path of the state directory.
        webhook_path: Path to a JSON file. Use empty string when passing payload_json.
        payload_json: Raw JSON. Use empty string when passing webhook_path.

    Returns:
        JSON counts imported, duplicates, and unmatched, or an error message.
    """
    try:
        payload = _payload(webhook_path, payload_json)
        state = State.load(state_path)
        result = import_webhook_payload(state, payload)
    except Error as exc:
        return f"Error: {exc}"
    except Exception as exc:  # noqa: BLE001 — surface unexpected errors to the client
        return f"Unexpected error: {exc}"
    return json.dumps(result.to_dict(), ensure_ascii=False)


@mcp.tool()
def render_report(state_path: str, output_path: str = "") -> str:
    """Render the Markdown report for the canary state.

    Args:
        state_path: Absolute path of the state directory.
        output_path: Optional file path. When set, the report is written there too.

    Returns:
        The Markdown report, or an error message.
    """
    try:
        state = State.load(state_path)
        report = render_report_markdown(state)
    except Error as exc:
        return f"Error: {exc}"
    except Exception as exc:  # noqa: BLE001 — surface unexpected errors to the client
        return f"Unexpected error: {exc}"

    if output_path.strip():
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(report, encoding="utf-8")
        return f"Relatório gerado em {destination.resolve()}\n\n{report}"
    return report


def _payload(webhook_path: str, payload_json: str) -> object:
    has_path = bool(webhook_path.strip())
    has_json = bool(payload_json.strip())
    if has_path == has_json:
        raise InputError("Informe webhook_path ou payload_json.")
    if has_path:
        return load_webhook_file(webhook_path)
    return load_webhook_text(payload_json)


def _blank(value: str) -> str | None:
    text = value.strip()
    return text or None


def main() -> None:
    """Entry point for the MCP stdio server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

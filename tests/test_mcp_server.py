"""MCP tool wrappers. Skipped when the mcp extra is not installed."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class McpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            from exposure_canary.mcp_server import (  # noqa: F401
                create_canary,
                import_webhook,
                render_report,
            )
        except ImportError as exc:
            raise unittest.SkipTest(f"mcp extra not installed: {exc}") from exc

    def test_three_tools(self) -> None:
        from exposure_canary.mcp_server import create_canary, import_webhook, render_report

        with tempfile.TemporaryDirectory() as tmp:
            state = str(Path(tmp) / "state")
            refused = create_canary(
                kind="url",
                label="pagina",
                asset="site",
                owned=False,
                state_path=state,
                collector="https://collect.example",
            )
            self.assertTrue(refused.startswith("Error:"))

            created = json.loads(
                create_canary(
                    kind="dns",
                    label="zona",
                    asset="example.com",
                    owned=True,
                    state_path=state,
                    zone="example.com",
                )
            )
            counts = json.loads(
                import_webhook(
                    state_path=state,
                    payload_json=json.dumps(
                        {
                            "qname": created["value"],
                            "observed_at": "2026-10-14T12:00:00Z",
                            "source": "203.0.113.10",
                        }
                    ),
                )
            )
            self.assertEqual(counts["imported"], 1)

            both = import_webhook(state_path=state, webhook_path="x", payload_json="{}")
            self.assertTrue(both.startswith("Error:"))

            destination = str(Path(tmp) / "relatorio.md")
            report = render_report(state_path=state, output_path=destination)
            self.assertIn("Alta", report)
            self.assertIn("Alta", Path(destination).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

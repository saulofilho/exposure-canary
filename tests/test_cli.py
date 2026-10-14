"""CLI tests."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from exposure_canary.cli import main


class CliTests(unittest.TestCase):
    def test_create_import_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = str(Path(tmp) / "state")
            created_out = io.StringIO()
            with redirect_stdout(created_out), redirect_stderr(io.StringIO()):
                code = main(
                    [
                        "create",
                        "--kind",
                        "email",
                        "--label",
                        "contato",
                        "--asset",
                        "example.com",
                        "--domain",
                        "example.com",
                        "--owned",
                        "--state",
                        state,
                    ]
                )
            self.assertEqual(code, 0)
            created = json.loads(created_out.getvalue())

            webhook = Path(tmp) / "hook.json"
            webhook.write_text(
                json.dumps(
                    {
                        "address": created["value"],
                        "observed_at": "2026-10-14T12:00:00Z",
                        "source": "192.0.2.10",
                    }
                ),
                encoding="utf-8",
            )
            imported_out = io.StringIO()
            with redirect_stdout(imported_out):
                code = main(["import-webhook", str(webhook), "--state", state])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(imported_out.getvalue())["imported"], 1)

            report_path = Path(tmp) / "relatorio.md"
            with redirect_stderr(io.StringIO()):
                code = main(["report", "--state", state, "-o", str(report_path)])
            self.assertEqual(code, 0)
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("Alta", report)
            self.assertIn(created["value"], report)

    def test_owned_flag_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            err = io.StringIO()
            with redirect_stderr(err):
                code = main(
                    [
                        "create",
                        "--kind",
                        "dns",
                        "--label",
                        "zona",
                        "--asset",
                        "example.com",
                        "--zone",
                        "example.com",
                        "--state",
                        str(Path(tmp) / "state"),
                    ]
                )
            self.assertEqual(code, 1)
            self.assertIn("owned=true", err.getvalue())

    def test_version(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            main(["--version"])
        self.assertEqual(raised.exception.code, 0)


if __name__ == "__main__":
    unittest.main()

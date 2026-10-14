"""Tests for canary creation, dedup, severity, and the report."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from exposure_canary import State, create_canary, import_webhook, render_report
from exposure_canary.errors import InputError


def _hit(canary_id: str, when: str, source: str = "203.0.113.10", **extra: str) -> dict[str, str]:
    payload = {"canary_id": canary_id, "observed_at": when, "source": source}
    payload.update(extra)
    return payload


class CanaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name) / "state"

    def test_url_dns_and_email_shapes(self) -> None:
        url = create_canary(
            State.load(self.directory),
            kind="url",
            label="currículo",
            asset="site",
            owned=True,
            collector="https://collect.example/hooks?track=1#frag",
        )
        dns = create_canary(
            State.load(self.directory),
            kind="dns",
            label="zona",
            asset="example.com",
            owned=True,
            zone="Example.COM.",
        )
        email = create_canary(
            State.load(self.directory),
            kind="email",
            label="contato",
            asset="example.com",
            owned=True,
            domain="example.com",
        )

        self.assertTrue(url.value.startswith("https://collect.example/hooks/c/"))
        self.assertNotIn("?", url.value)
        self.assertEqual(dns.value, f"{dns.id}.example.com")
        self.assertRegex(email.value, r"^cn-[0-9a-f]{16}@example\.com$")
        stored = json.loads((self.directory / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["version"], 1)
        self.assertEqual(len(stored["canaries"]), 3)

    def test_refuses_unowned_asset_and_bad_collector(self) -> None:
        with self.assertRaises(InputError):
            create_canary(
                State.load(self.directory),
                kind="url",
                label="pagina",
                asset="site",
                owned=False,
                collector="https://collect.example",
            )
        with self.assertRaises(InputError):
            create_canary(
                State.load(self.directory),
                kind="url",
                label="pagina",
                asset="site",
                owned=True,
                collector="http://collect.example",
            )
        with self.assertRaises(InputError) as raised:
            create_canary(
                State.load(self.directory),
                kind="url",
                label="pagina",
                asset="site",
                owned=True,
                collector="https://user:secret@collect.example",
            )
        self.assertNotIn("secret", str(raised.exception))
        with self.assertRaises(InputError):
            create_canary(
                State.load(self.directory),
                kind="pixel",
                label="pagina",
                asset="site",
                owned=True,
            )
        self.assertFalse((self.directory / "state.json").exists())

    def test_dedup_severity_and_reorder(self) -> None:
        canary = create_canary(
            State.load(self.directory),
            kind="url",
            label="pagina",
            asset="site",
            owned=True,
            collector="https://collect.example",
        )
        first = import_webhook(
            State.load(self.directory),
            [
                _hit(canary.id, "2026-10-14T12:10:00Z", "203.0.113.20"),
                _hit(canary.id, "2026-10-14T12:00:00Z", "203.0.113.10"),
                _hit(canary.id, "2026-10-14T12:04:59+00:00", "203.0.113.10"),
            ],
        )
        self.assertEqual(first.imported, 2)
        self.assertEqual(first.duplicates, 1)
        events = {event.source: event.severity for event in State.load(self.directory).events}
        self.assertEqual(events["203.0.113.10"], "medium")
        self.assertEqual(events["203.0.113.20"], "high")

        repeat = import_webhook(
            State.load(self.directory),
            _hit(canary.id, "2026-10-14T12:05:00Z", "203.0.113.10"),
        )
        self.assertEqual(repeat.imported, 1)
        severities = [event.severity for event in State.load(self.directory).events if event.source == "203.0.113.10"]
        self.assertEqual(severities, ["medium", "low"])

        again = import_webhook(
            State.load(self.directory),
            _hit(canary.id, "2026-10-14T12:00:00Z", "203.0.113.10"),
        )
        self.assertEqual(again.imported, 0)
        self.assertEqual(again.duplicates, 1)
        self.assertEqual(len(State.load(self.directory).events), 3)

    def test_dns_and_email_stay_high_and_url_value_matches(self) -> None:
        dns = create_canary(
            State.load(self.directory),
            kind="dns",
            label="zona",
            asset="example.com",
            owned=True,
            zone="example.com",
        )
        email = create_canary(
            State.load(self.directory),
            kind="email",
            label="contato",
            asset="example.com",
            owned=True,
            domain="example.com",
        )
        import_webhook(
            State.load(self.directory),
            [
                {"url": dns.value, "timestamp": "2026-10-14T12:00:00Z", "ip": "203.0.113.10"},
                {"address": email.value, "time": "2026-10-14T12:00:00Z", "remote": "192.0.2.10"},
                {"url": dns.value, "timestamp": "2026-10-14T13:00:00Z", "ip": "203.0.113.10"},
            ],
        )
        events = State.load(self.directory).events
        self.assertEqual(len(events), 3)
        self.assertEqual(
            {(event.kind, event.severity) for event in events},
            {("dns", "high"), ("email", "high")},
        )

    def test_unmatched_is_low_and_invalid_import_does_not_save(self) -> None:
        canary = create_canary(
            State.load(self.directory),
            kind="url",
            label="pagina",
            asset="site",
            owned=True,
            collector="https://localhost:8443",
        )
        before = (self.directory / "state.json").read_text(encoding="utf-8")
        with self.assertRaises(InputError):
            import_webhook(State.load(self.directory), {"canary_id": canary.id})
        self.assertEqual((self.directory / "state.json").read_text(encoding="utf-8"), before)

        result = import_webhook(
            State.load(self.directory),
            {
                "token": "cn" + "ab" * 8,
                "observed_at": "2026-10-14T12:00:00Z",
            },
        )
        self.assertEqual(result.unmatched, 1)
        event = State.load(self.directory).events[0]
        self.assertEqual(event.severity, "low")
        self.assertEqual(event.source, "unspecified")
        self.assertTrue(canary.value.startswith("https://localhost:8443/c/"))

    def test_report_lists_events_without_claiming_identity(self) -> None:
        canary = create_canary(
            State.load(self.directory),
            kind="url",
            label="pagina",
            asset="site",
            owned=True,
            collector="https://collect.example",
        )
        import_webhook(
            State.load(self.directory),
            _hit(canary.id, "2026-10-14T12:00:00Z"),
        )
        report = render_report(State.load(self.directory))
        self.assertIn("# Relatório de iscas", report)
        self.assertIn("## Resumo", report)
        self.assertIn("## Iscas", report)
        self.assertIn("## Eventos", report)
        self.assertIn("## Leitura", report)
        self.assertIn("Média", report)
        self.assertIn(canary.value, report)
        self.assertIn("Pessoa, intenção", report)
        self.assertNotIn("fingerprint", report.lower())

        empty = render_report(State.load(Path(self.tmp.name) / "vazio"))
        self.assertIn("Nenhuma isca no registro.", empty)
        self.assertIn("Nenhum evento.", empty)


if __name__ == "__main__":
    unittest.main()

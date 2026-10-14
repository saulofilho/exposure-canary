"""The Cursor and Claude copies of the skill stay the same text."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "plugin" / "skills" / "exposure-canary" / "SKILL.md"
CURSOR = ROOT / ".cursor" / "skills" / "exposure-canary" / "SKILL.md"
HEADINGS = ("## Escopo", "## Mapa de onde plantar", "## Leitura do alerta", "## Parada")
TOOLS = ("create_canary", "import_webhook", "render_report")


class SkillTests(unittest.TestCase):
    def test_single_text_and_required_sections(self) -> None:
        self.assertTrue(CANONICAL.is_file())
        self.assertTrue(CURSOR.is_file())
        text = CANONICAL.read_text(encoding="utf-8")
        self.assertEqual(text, CURSOR.read_text(encoding="utf-8"))
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: exposure-canary", text)
        for heading in HEADINGS:
            self.assertIn(heading, text)
        for tool in TOOLS:
            self.assertIn(tool, text)


if __name__ == "__main__":
    unittest.main()

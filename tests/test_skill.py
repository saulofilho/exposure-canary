"""Plugin copies stay identical, and the Cursor manifest is marketplace-safe."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COPIES = (
    ROOT / "skills" / "exposure-canary" / "SKILL.md",
    ROOT / "plugin" / "skills" / "exposure-canary" / "SKILL.md",
    ROOT / ".cursor" / "skills" / "exposure-canary" / "SKILL.md",
)
HEADINGS = ("## Scope", "## Where to plant", "## Reading an alert", "## Stop")
TOOLS = ("create_canary", "import_webhook", "render_report")


class SkillTests(unittest.TestCase):
    def test_single_text_and_required_sections(self) -> None:
        texts = [path.read_text(encoding="utf-8") for path in COPIES]
        self.assertTrue(all(texts))
        self.assertEqual(len(set(texts)), 1)
        text = texts[0]
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: exposure-canary", text)
        for heading in HEADINGS:
            self.assertIn(heading, text)
        for tool in TOOLS:
            self.assertIn(tool, text)

    def test_cursor_manifest_paths(self) -> None:
        manifest_path = ROOT / ".cursor-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "exposure-canary")
        self.assertNotIn(" ", manifest["name"])
        for field in ("skills", "mcpServers", "logo"):
            value = manifest[field]
            self.assertNotIn("..", value)
            self.assertFalse(value.startswith("/"))
        self.assertTrue((ROOT / "skills" / "exposure-canary" / "SKILL.md").is_file())
        self.assertTrue((ROOT / "mcp.json").is_file())
        self.assertTrue((ROOT / manifest["logo"]).is_file())
        self.assertTrue((ROOT / "README.md").is_file())


if __name__ == "__main__":
    unittest.main()

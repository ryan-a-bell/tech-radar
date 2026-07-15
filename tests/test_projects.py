"""
Tests for build_projects' pure functions — the Markdown front-matter parser
and the stack-resolution against the radar. No disk fixtures; every function
under test takes plain strings/lists.

Run from the repo root:
    python -m unittest discover -s tests
    python -m unittest tests.test_projects
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_projects as bp  # noqa: E402


class FrontMatterTests(unittest.TestCase):
    def test_scalars_and_inline_list(self):
        fm, body = bp.parse_front_matter(
            "---\n"
            "id: demo\n"
            "name: Demo Project\n"
            "status: Active\n"
            "topics: [Quant, Agents]\n"
            "---\n"
            "First paragraph.\n\nSecond.\n"
        )
        self.assertEqual(fm["id"], "demo")
        self.assertEqual(fm["name"], "Demo Project")
        self.assertEqual(fm["status"], "Active")
        self.assertEqual(fm["topics"], ["Quant", "Agents"])
        self.assertTrue(body.startswith("First paragraph."))

    def test_block_list(self):
        fm, _ = bp.parse_front_matter(
            "---\n"
            "stack:\n"
            "  - manual:cursor\n"
            "  - Ollama\n"
            "---\n"
            "body\n"
        )
        self.assertEqual(fm["stack"], ["manual:cursor", "Ollama"])

    def test_empty_scalar_becomes_none(self):
        fm, _ = bp.parse_front_matter("---\nrepo:\nname: X\n---\nb\n")
        self.assertIsNone(fm["repo"])
        self.assertEqual(fm["name"], "X")

    def test_quoted_values_stripped(self):
        fm, _ = bp.parse_front_matter('---\nname: "Quoted Name"\n---\n')
        self.assertEqual(fm["name"], "Quoted Name")

    def test_no_front_matter_all_body(self):
        fm, body = bp.parse_front_matter("just some prose\nno fence")
        self.assertEqual(fm, {})
        self.assertEqual(body, "just some prose\nno fence")

    def test_empty_inline_list(self):
        fm, _ = bp.parse_front_matter("---\ntopics: []\n---\n")
        self.assertEqual(fm["topics"], [])

    def test_first_paragraph(self):
        self.assertEqual(
            bp.first_paragraph("Line one.\nLine two.\n\nSecond para."),
            "Line one. Line two.",
        )


class StackResolutionTests(unittest.TestCase):
    def setUp(self):
        self.items = [
            {"id": "manual:cursor", "name": "Cursor", "quadrant": "Tools",
             "ring": "Discovered", "url": "https://cursor.com", "canonical_url": "cursor.com"},
            {"id": "manual:ollama", "name": "Ollama", "quadrant": "Tools",
             "ring": "Adopted", "url": None, "canonical_url": None},
        ]
        self.index = bp.build_tool_index(self.items)

    def test_resolve_by_full_id(self):
        resolved, unresolved = bp.resolve_stack(["manual:cursor"], self.index)
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["name"], "Cursor")
        self.assertEqual(resolved[0]["ring"], "Discovered")
        self.assertEqual(unresolved, [])

    def test_resolve_by_bare_key(self):
        resolved, _ = bp.resolve_stack(["cursor"], self.index)
        self.assertEqual(resolved[0]["id"], "manual:cursor")

    def test_resolve_by_name_case_insensitive(self):
        resolved, _ = bp.resolve_stack(["ollama"], self.index)
        self.assertEqual(resolved[0]["id"], "manual:ollama")

    def test_unknown_entry_is_reported(self):
        resolved, unresolved = bp.resolve_stack(["Nonexistent"], self.index)
        self.assertEqual(resolved, [])
        self.assertEqual(unresolved, ["Nonexistent"])

    def test_duplicates_dropped(self):
        resolved, _ = bp.resolve_stack(["Cursor", "manual:cursor"], self.index)
        self.assertEqual(len(resolved), 1)

    def test_order_preserved(self):
        resolved, _ = bp.resolve_stack(["Ollama", "Cursor"], self.index)
        self.assertEqual([r["name"] for r in resolved], ["Ollama", "Cursor"])


class AsListTests(unittest.TestCase):
    def test_none_scalar_list(self):
        self.assertEqual(bp._as_list(None), [])
        self.assertEqual(bp._as_list("x"), ["x"])
        self.assertEqual(bp._as_list(["a", "b"]), ["a", "b"])


if __name__ == "__main__":
    unittest.main()

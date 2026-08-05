"""
Tests for build_people's pure functions — the optional contact block and the
dated `notes` list. Front-matter parsing itself is covered by test_projects
(build_people reuses that parser); here we only exercise the people-specific
assembly. No disk fixtures; every function under test takes a plain dict.

Run from the repo root:
    python -m unittest discover -s tests
    python -m unittest tests.test_people
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_people as bpl  # noqa: E402
import build_projects as bp  # noqa: E402


class ContactBlockTests(unittest.TestCase):
    def test_full_block_assembled(self):
        fm = {
            "organization": "Meridian Systematic",
            "business": "Systematic trading desk",
            "location": "Chicago, IL",
            "relationship": "Colleague",
            "how_met": "Same desk",
            "email": "a@example.com",
            "phone": "+1 (312) 555-0142",
            "last_contact": "2026-08-01",
            "website": "ryanbell.dev",
            "github": "ryan-a-bell",
            "linkedin": "ryanabell",
            "x": "ryan_quant",
        }
        c = bpl.build_contact(fm)
        self.assertEqual(c["organization"], "Meridian Systematic")
        self.assertEqual(c["email"], "a@example.com")
        self.assertEqual(c["last_contact"], "2026-08-01")
        self.assertEqual(
            c["links"],
            {"website": "ryanbell.dev", "github": "ryan-a-bell",
             "linkedin": "ryanabell", "x": "ryan_quant"},
        )

    def test_missing_fields_are_none_links_empty(self):
        c = bpl.build_contact({})
        for k in bpl.CONTACT_SCALARS:
            self.assertIsNone(c[k])
        self.assertEqual(c["links"], {})

    def test_only_present_links_included(self):
        c = bpl.build_contact({"github": "mokafor", "linkedin": "maya-okafor"})
        self.assertEqual(c["links"], {"github": "mokafor", "linkedin": "maya-okafor"})
        self.assertNotIn("website", c["links"])
        self.assertNotIn("x", c["links"])

    def test_blank_link_dropped(self):
        # an empty scalar parses to None -> must not appear in links
        c = bpl.build_contact({"website": None, "github": "  ", "x": "handle"})
        self.assertEqual(c["links"], {"x": "handle"})


class NotesTests(unittest.TestCase):
    def test_dated_and_undated(self):
        fm = {"notes": ["2026-08-01: shipped the thing", "just a plain note"]}
        notes = bpl.parse_notes(fm)
        self.assertEqual(notes[0], {"when": "2026-08-01", "text": "shipped the thing"})
        self.assertEqual(notes[1], {"when": None, "text": "just a plain note"})

    def test_colon_in_body_preserved(self):
        fm = {"notes": ["2026-06-12: evaluating Polygon vs Databento: leaning Polygon"]}
        notes = bpl.parse_notes(fm)
        self.assertEqual(notes[0]["when"], "2026-06-12")
        self.assertEqual(notes[0]["text"], "evaluating Polygon vs Databento: leaning Polygon")

    def test_no_notes_key(self):
        self.assertEqual(bpl.parse_notes({}), [])

    def test_scalar_note_promoted_to_list(self):
        # a single `notes: one line` scalar still yields one record
        self.assertEqual(bpl.parse_notes({"notes": "solo"}), [{"when": None, "text": "solo"}])

    def test_blank_lines_skipped(self):
        self.assertEqual(bpl.parse_notes({"notes": ["", "  ", None]}), [])


class EndToEndFrontMatterTests(unittest.TestCase):
    """The parser (shared with projects) + the people helpers together."""

    def test_parses_contact_and_notes_from_markdown(self):
        fm, body = bp.parse_front_matter(
            "---\n"
            "id: ryan-bell\n"
            "name: Ryan Bell\n"
            "organization: Meridian Systematic\n"
            "github: ryan-a-bell\n"
            "last_contact: 2026-08-01\n"
            "notes:\n"
            "  - 2026-08-01: first note\n"
            "  - second note\n"
            "---\n"
            "The bio.\n"
        )
        c = bpl.build_contact(fm)
        self.assertEqual(c["organization"], "Meridian Systematic")
        self.assertEqual(c["links"], {"github": "ryan-a-bell"})
        notes = bpl.parse_notes(fm)
        self.assertEqual([n["text"] for n in notes], ["first note", "second note"])
        self.assertEqual(notes[0]["when"], "2026-08-01")
        self.assertTrue(body.startswith("The bio."))


if __name__ == "__main__":
    unittest.main()

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


class SysmlSummaryTests(unittest.TestCase):
    MODEL = (
        "// header comment\n"
        "package Demo {\n"
        "  requirement def <'R-1'> Range { doc /* part def Hidden; */ }\n"
        "  requirement def <'R-2'> Speed;\n"
        "  part def Vehicle { port p : Plug; }\n"
        "  abstract part def 'Power Unit';\n"
        "  port def Plug;\n"
        "  part car : Vehicle { part engine : 'Power Unit'; }\n"
        "  connect car.p to car.engine;\n"
        "  satisfy Range by car;\n"
        "}\n"
    )

    def test_packages_and_defs(self):
        s = bp.summarize_sysml(self.MODEL)
        self.assertEqual(s["packages"], ["Demo"])
        self.assertEqual(s["defs"]["part"], ["Vehicle", "Power Unit"])
        self.assertEqual(s["defs"]["port"], ["Plug"])

    def test_comments_are_ignored(self):
        self.assertNotIn("Hidden", bp.summarize_sysml(self.MODEL)["defs"]["part"])

    def test_requirements_and_trace(self):
        s = bp.summarize_sysml(self.MODEL)
        self.assertEqual([r["id"] for r in s["requirements"]], ["R-1", "R-2"])
        self.assertEqual(s["satisfied"], ["Range"])

    def test_usage_counts(self):
        c = bp.summarize_sysml(self.MODEL)["counts"]
        self.assertEqual(c["parts"], 2)
        self.assertEqual(c["ports"], 1)
        self.assertEqual(c["connections"], 1)
        self.assertEqual(c["satisfy"], 1)


class RioRegisterTests(unittest.TestCase):
    def test_level_matrix_corners(self):
        self.assertEqual(bp.risk_level(1, 1), "Low")
        self.assertEqual(bp.risk_level(5, 5), "High")
        self.assertEqual(bp.risk_level(1, 5), "Moderate")
        self.assertEqual(bp.risk_level(4, 4), "High")
        self.assertIsNone(bp.risk_level(0, 3))

    def test_header_aliases_and_sort(self):
        reg = bp.parse_rio_register(
            "Risk #,Risk Statement,Probability,Impact,State,Risk Owner,Handling\n"
            "A,Low one,1,2,Open,me,watch\n"
            "B,Hot one,5,4,Open,you,fix it\n"
            "C,Done,5,5,Closed,,\n"
        )
        self.assertEqual(reg["unmapped"], [])
        self.assertEqual([r["id"] for r in reg["items"]], ["B", "A", "C"])
        b = reg["items"][0]
        self.assertEqual((b["score"], b["level"], b["owner"]), (20, "High", "you"))
        self.assertFalse(reg["items"][-1]["open"])

    def test_missing_columns_reported_and_unscored(self):
        reg = bp.parse_rio_register("Title,Status\nSomething,Open\n")
        self.assertIn("likelihood", reg["unmapped"])
        r = reg["items"][0]
        self.assertEqual(r["id"], "R1")
        self.assertIsNone(r["level"])
        self.assertIsNone(r["score"])

    def test_types_and_ratings(self):
        reg = bp.parse_rio_register(
            "ID,Type,Title,Likelihood,Consequence,Status\n"
            "R1,Risk,Threat,4,4,Open\n"
            "I1,Issue,Happened,,4,Open\n"
            "O1,Opportunity,Upside,3,4,Pursuing\n"
            "O2,opp,Won,5,5,Captured\n"
            "X1,,Untyped,2,2,Open\n"
        )
        by = {r["id"]: r for r in reg["items"]}
        self.assertEqual((by["R1"]["type"], by["R1"]["level"]), ("Risk", "High"))
        self.assertEqual((by["I1"]["type"], by["I1"]["score"], by["I1"]["level"]), ("Issue", 4, "High"))
        self.assertEqual((by["O1"]["type"], by["O1"]["score"], by["O1"]["level"]),
                         ("Opportunity", 12, "Moderate"))
        self.assertFalse(by["O2"]["open"])
        self.assertEqual(by["X1"]["type"], "Risk")

    def test_issue_levels_by_consequence(self):
        self.assertEqual([bp.rio_rating("Issue", None, c)[1] for c in range(1, 6)],
                         ["Low", "Moderate", "Moderate", "High", "High"])

    def test_type_column_is_optional(self):
        reg = bp.parse_rio_register("ID,Title,Likelihood,Consequence\nA,x,1,1\n")
        self.assertEqual(reg["unmapped"], ["status"])


if __name__ == "__main__":
    unittest.main()

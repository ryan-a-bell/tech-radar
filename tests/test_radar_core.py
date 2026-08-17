"""
Smoke tests for radar_core's pure functions — the dedup, id, trend, and topic
logic that everything else (runner, radar.py, edit_server) relies on.

Run from the repo root:
    python -m unittest discover -s tests
    python -m unittest tests.test_radar_core   # just this file

stdlib only, no fixtures touch disk — every function under test is pure.
"""

import os
import sys
import unittest
from datetime import date

# make `import radar_core` work no matter where the runner is invoked from
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import radar_core as core  # noqa: E402


class CanonicalUrlTests(unittest.TestCase):
    def test_extracts_github_repo(self):
        self.assertEqual(
            core.canonical_url("https://github.com/oven-sh/bun"),
            "github.com/oven-sh/bun",
        )

    def test_lowercases_owner_and_repo(self):
        self.assertEqual(
            core.canonical_url("https://github.com/Oven-SH/Bun"),
            "github.com/oven-sh/bun",
        )

    def test_strips_dot_git_suffix(self):
        self.assertEqual(
            core.canonical_url("git@github.com/foo/bar.git"),
            "github.com/foo/bar",
        )

    def test_collapses_subpaths(self):
        # /tree/main and the bare repo must resolve to the same identity
        self.assertEqual(
            core.canonical_url("https://github.com/foo/bar/tree/main/src"),
            "github.com/foo/bar",
        )

    def test_ignores_reserved_owner_namespaces(self):
        # github.com/sponsors/<user> etc. are namespace pages, not repos
        self.assertIsNone(core.canonical_url("https://github.com/sponsors/foo"))
        self.assertIsNone(core.canonical_url("https://github.com/orgs/anthropic"))

    def test_reserved_word_in_repo_position_is_a_real_repo(self):
        # a repo legitimately named "topics" under a real owner must resolve
        self.assertEqual(
            core.canonical_url("https://github.com/foo/topics"),
            "github.com/foo/topics",
        )

    def test_returns_none_for_non_github(self):
        self.assertIsNone(core.canonical_url("https://example.com/foo/bar"))

    def test_first_resolvable_url_wins(self):
        # a Reddit post (no repo) plus a linked github url -> the repo
        self.assertEqual(
            core.canonical_url("https://reddit.com/r/x/abc",
                               "https://github.com/foo/bar"),
            "github.com/foo/bar",
        )

    def test_empty_input(self):
        self.assertIsNone(core.canonical_url())
        self.assertIsNone(core.canonical_url(None, ""))


class StarTrendTests(unittest.TestCase):
    def test_no_history_is_none(self):
        self.assertEqual(core.star_trend({}), ("none", 0))

    def test_single_snapshot_is_none(self):
        self.assertEqual(
            core.star_trend({"stars_history": {"2026-01-01": 10}}),
            ("none", 0),
        )

    def test_up(self):
        trend, delta = core.star_trend({"stars_history": {
            "2026-01-01": 100, "2026-01-10": 150}})
        self.assertEqual(trend, "up")
        self.assertEqual(delta, 50)

    def test_down(self):
        trend, delta = core.star_trend({"stars_history": {
            "2026-01-01": 200, "2026-01-10": 150}})
        self.assertEqual(trend, "down")
        self.assertEqual(delta, -50)

    def test_flat(self):
        self.assertEqual(
            core.star_trend({"stars_history": {
                "2026-01-01": 100, "2026-01-10": 100}}),
            ("flat", 0),
        )

    def test_baseline_prefers_snapshot_at_least_7_days_back(self):
        # newest is 2026-01-20; the 01-12 snapshot is the latest that is still
        # >=7 days older, so it (not the most recent) is the baseline.
        trend, delta = core.star_trend({"stars_history": {
            "2026-01-01": 100,
            "2026-01-12": 120,
            "2026-01-19": 140,   # <7 days before newest, must be ignored
            "2026-01-20": 145,
        }})
        self.assertEqual(trend, "up")
        self.assertEqual(delta, 145 - 120)


class NormalizeTopicsTests(unittest.TestCase):
    def test_canonicalizes_case(self):
        kept, unknown = core.normalize_topics(["agents", "rag"])
        self.assertEqual(kept, ["Agents", "RAG"])
        self.assertEqual(unknown, [])

    def test_drops_duplicates_preserving_order(self):
        kept, _ = core.normalize_topics(["AI", "ai", "Agents"])
        self.assertEqual(kept, ["AI", "Agents"])

    def test_reports_unknown(self):
        kept, unknown = core.normalize_topics(["AI", "Blockchain"])
        self.assertEqual(kept, ["AI"])
        self.assertEqual(unknown, ["Blockchain"])

    def test_empty_input(self):
        self.assertEqual(core.normalize_topics(None), ([], []))
        self.assertEqual(core.normalize_topics([]), ([], []))


class IdAndPathTests(unittest.TestCase):
    def test_make_id_is_source_prefixed_and_lowercased(self):
        self.assertEqual(core.make_id("GitHub", "oven-sh/bun"),
                         "github:oven-sh/bun")

    def test_id_to_path_maps_into_items_tree(self):
        path = core.id_to_path("github:oven-sh/bun")
        self.assertEqual(os.path.dirname(path),
                         os.path.join(core.ITEMS_DIR, "github"))
        self.assertTrue(os.path.basename(path).endswith(".md"))

    def test_id_to_path_is_stable(self):
        self.assertEqual(core.id_to_path("github:foo/bar"),
                         core.id_to_path("github:foo/bar"))


class DateHelperTests(unittest.TestCase):
    def test_days_since_seen(self):
        item = {"last_seen": "2026-01-01"}
        self.assertEqual(core.days_since_seen(item, today=date(2026, 1, 11)), 10)

    def test_days_since_seen_missing_is_large(self):
        self.assertGreater(core.days_since_seen({}, today=date(2026, 1, 1)), 1000)

    def test_days_since_archived_none_when_not_archived(self):
        self.assertIsNone(core.days_since_archived({"archived_at": None}))

    def test_days_since_archived_counts_days(self):
        item = {"archived_at": "2026-01-01"}
        self.assertEqual(
            core.days_since_archived(item, today=date(2026, 1, 6)), 5)


class NewItemTests(unittest.TestCase):
    def test_always_starts_in_discovered(self):
        item = core.new_item("GitHub", "foo/bar", "Bar", "desc",
                             "https://github.com/foo/bar", quadrant="Adopted")
        # the runner must never classify — ring is always Discovered on create
        self.assertEqual(item["ring"], "Discovered")

    def test_fills_canonical_url(self):
        item = core.new_item("Reddit", "x", "X", "d",
                             "https://reddit.com/r/x/abc",
                             linked_url="https://github.com/foo/bar")
        self.assertEqual(item["canonical_url"], "github.com/foo/bar")

    def test_unknown_quadrant_falls_back_to_tools(self):
        item = core.new_item("GitHub", "a/b", "AB", "d",
                             "https://github.com/a/b", quadrant="Nonsense")
        self.assertEqual(item["quadrant"], "Tools")

    def test_seeds_star_history_when_stars_present(self):
        item = core.new_item("GitHub", "a/b", "AB", "d",
                             "https://github.com/a/b", stars=42)
        self.assertEqual(list(item["stars_history"].values()), [42])


class FrontmatterCodecTests(unittest.TestCase):
    """dump_item_md / parse_item_md — the Markdown + YAML frontmatter codec
    per-tech files are stored in (issue #18)."""

    def _item(self, **overrides):
        item = core.new_item(
            "GitHub", "foo/bar", "Foo Bar", "A description.",
            "https://github.com/foo/bar", company="Acme", stars=10,
            momentum=3, tags=["cli"], topics=["AI"],
        )
        item.update(overrides)
        return item

    def test_round_trips_a_typical_item(self):
        item = self._item()
        self.assertEqual(core.parse_item_md(core.dump_item_md(item)), item)

    def test_body_is_the_description(self):
        item = self._item(description="Line one.\n\nLine two.")
        text = core.dump_item_md(item)
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("Line one.\n\nLine two.", text)

    def test_empty_description_yields_no_trailing_body(self):
        item = self._item(description="")
        text = core.dump_item_md(item)
        self.assertTrue(text.rstrip("\n").endswith("---"))

    def test_round_trips_special_characters_in_name(self):
        for name in ["Name: With Colon", "null", "true", "42", "",
                     "  spaced  ", "- dash prefixed", "quote\" inside",
                     "emoji 🚀 and em dash —", "[bracketed]", "{braced}"]:
            with self.subTest(name=name):
                item = self._item(name=name)
                self.assertEqual(
                    core.parse_item_md(core.dump_item_md(item))["name"], name)

    def test_round_trips_multiline_description(self):
        item = self._item(description="para one\n\n---\n\npara two")
        back = core.parse_item_md(core.dump_item_md(item))
        self.assertEqual(back["description"], item["description"])

    def test_round_trips_nested_also_seen_and_stars_history(self):
        item = self._item(
            also_seen=[{"source": "reddit", "url": "https://reddit.com/x:y",
                        "seen": "2026-01-01"}],
            stars_history={"2026-01-01": 10, "2026-01-08": 15},
        )
        back = core.parse_item_md(core.dump_item_md(item))
        self.assertEqual(back["also_seen"], item["also_seen"])
        self.assertEqual(back["stars_history"], item["stars_history"])

    def test_dates_stay_plain_strings_not_yaml_dates(self):
        item = self._item(first_seen="2026-07-12", last_seen="2026-07-12")
        back = core.parse_item_md(core.dump_item_md(item))
        self.assertIsInstance(back["first_seen"], str)
        self.assertEqual(back["first_seen"], "2026-07-12")

    def test_null_fields_round_trip_to_none(self):
        item = self._item(company=None, canonical_url=None, archived_at=None)
        back = core.parse_item_md(core.dump_item_md(item))
        self.assertIsNone(back["company"])
        self.assertIsNone(back["canonical_url"])
        self.assertIsNone(back["archived_at"])

    def test_missing_legacy_fields_backfill_to_typed_defaults(self):
        # simulates a pre-topics/archived_at era item, as real early items
        # in this repo were, to guard against the migration writing a bare
        # `null` into a list/dict-typed field.
        item = self._item()
        del item["topics"]
        del item["archived_at"]
        back = core.parse_item_md(core.dump_item_md(item))
        self.assertEqual(back["topics"], [])
        self.assertIsNone(back["archived_at"])


if __name__ == "__main__":
    unittest.main()

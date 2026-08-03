"""
Smoke tests for learning_core's pure functions — the id, topic-normalization,
item-construction, resolution, and status-stamping logic that learning.py
relies on.

Run from the repo root:
    python -m unittest discover -s tests
    python -m unittest tests.test_learning_core   # just this file

stdlib only, no fixtures touch disk — every function under test is pure.
"""

import os
import sys
import unittest
from datetime import date

# make `import learning_core` work no matter where the runner is invoked from
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import learning_core as core  # noqa: E402


class SlugAndIdTests(unittest.TestCase):
    def test_slugify_basic(self):
        self.assertEqual(core.slugify("Team Topologies"), "team-topologies")

    def test_slugify_strips_punctuation_and_lowercases(self):
        self.assertEqual(core.slugify("Let's build GPT!"), "let-s-build-gpt")

    def test_slugify_empty_falls_back(self):
        self.assertEqual(core.slugify(""), "item")
        self.assertEqual(core.slugify("!!!"), "item")

    def test_unique_id_passes_through_when_free(self):
        self.assertEqual(core.unique_id("ddia", {"afml"}), "ddia")

    def test_unique_id_suffixes_on_collision(self):
        self.assertEqual(core.unique_id("ddia", {"ddia"}), "ddia-2")
        self.assertEqual(core.unique_id("ddia", {"ddia", "ddia-2"}), "ddia-3")


class NormalizeTopicsTests(unittest.TestCase):
    def test_canonicalizes_case(self):
        kept, unknown = core.normalize_topics(["ml", "ai"])
        self.assertEqual(kept, ["ML", "AI"])
        self.assertEqual(unknown, [])

    def test_reports_unknown(self):
        kept, unknown = core.normalize_topics(["ML", "Bogus"])
        self.assertEqual(kept, ["ML"])
        self.assertEqual(unknown, ["Bogus"])

    def test_dedupes_preserving_order(self):
        kept, _ = core.normalize_topics(["AI", "ml", "ML", "ai"])
        self.assertEqual(kept, ["AI", "ML"])

    def test_multiword_topic_survives(self):
        kept, unknown = core.normalize_topics(["Data Feeds"])
        self.assertEqual(kept, ["Data Feeds"])
        self.assertEqual(unknown, [])

    def test_empty_input(self):
        self.assertEqual(core.normalize_topics(None), ([], []))
        self.assertEqual(core.normalize_topics([]), ([], []))


class NewItemTests(unittest.TestCase):
    def test_book_has_pages_and_no_source(self):
        it = core.new_item("book", "Some Book", pages=300, topics=["ML"])
        self.assertEqual(it["type"], "book")
        self.assertEqual(it["id"], "some-book")
        self.assertEqual(it["pages"], 300)
        self.assertIsNone(it["pages_read"])
        self.assertNotIn("source", it)   # books carry no source/url
        self.assertNotIn("url", it)
        self.assertEqual(it["topics"], ["ML"])

    def test_article_has_minutes_source_url(self):
        it = core.new_item("article", "A Paper", minutes=40,
                           source="arXiv", url="https://x")
        self.assertEqual(it["minutes"], 40)
        self.assertEqual(it["source"], "arXiv")
        self.assertEqual(it["url"], "https://x")

    def test_certification_has_price(self):
        it = core.new_item("certification", "Some Cert", price="$200")
        self.assertEqual(it["price"], "$200")
        self.assertIn("source", it)

    def test_status_stamps_the_matching_date(self):
        today = date.today().isoformat()
        it = core.new_item("book", "X", status="Queued")
        self.assertEqual(it["status"], "Queued")
        self.assertEqual(it["queued"], today)
        self.assertIsNone(it["added"])

    def test_unknown_type_rejected(self):
        with self.assertRaises(ValueError):
            core.new_item("podcast", "Nope")

    def test_id_avoids_collision_with_existing(self):
        it = core.new_item("book", "Some Book", existing_ids={"some-book"})
        self.assertEqual(it["id"], "some-book-2")

    def test_only_known_topics_kept(self):
        it = core.new_item("book", "X", topics=["ML", "Nonsense"])
        self.assertEqual(it["topics"], ["ML"])


class ResolveTests(unittest.TestCase):
    def setUp(self):
        self.items = [
            {"id": "afml", "title": "Advances in Financial Machine Learning"},
            {"id": "ddia", "title": "Designing Data-Intensive Applications"},
            {"id": "deep-learning", "title": "Deep Learning"},
        ]

    def test_exact_id(self):
        it, err = core.resolve(self.items, "ddia")
        self.assertIsNone(err)
        self.assertEqual(it["id"], "ddia")

    def test_exact_title_case_insensitive(self):
        it, err = core.resolve(self.items, "deep learning")
        self.assertIsNone(err)
        self.assertEqual(it["id"], "deep-learning")

    def test_unique_partial_title(self):
        it, err = core.resolve(self.items, "financial")
        self.assertIsNone(err)
        self.assertEqual(it["id"], "afml")

    def test_ambiguous_partial_reports(self):
        it, err = core.resolve(self.items, "learning")  # afml + deep-learning
        self.assertIsNone(it)
        self.assertIn("ambiguous", err)

    def test_no_match_reports(self):
        it, err = core.resolve(self.items, "nonexistent")
        self.assertIsNone(it)
        self.assertIn("no item matches", err)


class SetStatusTests(unittest.TestCase):
    def test_stamps_destination_date(self):
        it = {"status": "Discovered", "added": "2026-01-01",
              "started": None, "shelved": None}
        core.set_status(it, "Reading")
        self.assertEqual(it["status"], "Reading")
        self.assertEqual(it["started"], date.today().isoformat())

    def test_preserves_existing_stamp(self):
        it = {"status": "Discovered", "started": "2026-01-01"}
        core.set_status(it, "Reading")
        self.assertEqual(it["started"], "2026-01-01")   # not overwritten

    def test_leaving_shelved_clears_note(self):
        it = {"status": "Shelved", "shelved": "2026-01-01",
              "shelved_note": "later", "started": None}
        core.set_status(it, "Reading")
        self.assertIsNone(it["shelved"])
        self.assertNotIn("shelved_note", it)

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            core.set_status({"status": "Discovered"}, "Finished")


if __name__ == "__main__":
    unittest.main()

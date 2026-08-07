"""
Tests for calibre_sync' pure functions — mapping a calibredb record to book
facts, and planning the merge against existing Learning Library items. No
Calibre, no subprocess, no disk: every function under test takes plain dicts.

Run from the repo root:
    python -m unittest discover -s tests
    python -m unittest tests.test_calibre_sync
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import calibre_sync as cs  # noqa: E402


def _book(**kw):
    """A minimal existing learning `book` item."""
    base = {"id": "ddia", "type": "book",
            "title": "Designing Data-Intensive Applications",
            "author": "Martin Kleppmann", "year": 2017, "status": "Read",
            "topics": ["Data Feeds"], "pages": 616, "pages_read": None,
            "rating": 5, "added": None, "started": None, "queued": None,
            "finished": "2026-03-02", "shelved": None, "blurb": "Curated blurb."}
    base.update(kw)
    return base


class HelperTests(unittest.TestCase):
    def test_strip_html(self):
        self.assertEqual(cs.strip_html("<p>Hello <b>world</b>.</p>"), "Hello world.")
        self.assertEqual(cs.strip_html(None), "")

    def test_year_undefined(self):
        self.assertEqual(cs._year("2017-03-16T00:00:00+00:00"), 2017)
        self.assertIsNone(cs._year("0101-01-01T00:00:00+00:00"))

    def test_date(self):
        self.assertEqual(cs._date("2026-07-10T12:00:00"), "2026-07-10")
        self.assertIsNone(cs._date("0101-01-01T00:00:00"))

    def test_get_custom_key_variants(self):
        self.assertEqual(cs._get_custom({"#status": "Reading"}, "status"), "Reading")
        self.assertEqual(cs._get_custom({"*status": "Reading"}, "status"), "Reading")
        self.assertEqual(cs._get_custom({"status": "Reading"}, "status"), "Reading")
        self.assertIsNone(cs._get_custom({"status": ""}, "status"))


class FactsTests(unittest.TestCase):
    def test_facts_mapped(self):
        f = cs.calibre_facts({
            "title": "  Deep Learning ", "authors": "Goodfellow", "pubdate": "2016-01-01",
            "rating": 8, "comments": "<p>Text.</p>", "tags": ["ML", "Junk"],
            "timestamp": "2024-05-06T00:00:00",
        })
        self.assertEqual(f["title"], "Deep Learning")
        self.assertEqual(f["year"], 2016)
        self.assertEqual(f["rating"], 4)           # 8 // 2
        self.assertEqual(f["blurb"], "Text.")
        self.assertEqual(f["topics"], ["ML"])      # "Junk" not in vocabulary
        self.assertEqual(f["added"], "2024-05-06")
        self.assertIsNone(f["status"])             # no custom column

    def test_custom_columns_supply_reading_state(self):
        f = cs.calibre_facts({
            "title": "X", "authors": "Y", "rating": None, "comments": "", "tags": [],
            "#status": "reading", "#pages_read": 42, "#started": "2026-07-01T00:00:00",
        })
        self.assertEqual(f["status"], "Reading")   # title-cased
        self.assertEqual(f["pages_read"], 42)
        self.assertEqual(f["started"], "2026-07-01")

    def test_zero_rating_is_none(self):
        f = cs.calibre_facts({"title": "X", "authors": "Y", "rating": 0,
                              "comments": "", "tags": []})
        self.assertIsNone(f["rating"])


class ApplyTests(unittest.TestCase):
    def test_curated_state_preserved_facts_overlaid(self):
        item = _book()
        facts = cs.calibre_facts({
            "title": "Designing Data-Intensive Applications", "authors": "Martin Kleppmann",
            "pubdate": "2017-03-16", "rating": 10, "comments": "<p>Calibre blurb.</p>",
            "tags": ["Data Feeds", "AI"], "timestamp": "2024-01-05T00:00:00"})
        cs.apply_to_existing(item, facts)
        self.assertEqual(item["id"], "ddia")            # id untouched
        self.assertEqual(item["status"], "Read")        # curated state kept
        self.assertEqual(item["blurb"], "Curated blurb.")  # curated blurb wins
        self.assertEqual(item["rating"], 5)             # calibre 10 // 2
        self.assertEqual(item["added"], "2024-01-05")   # fact fills the null
        self.assertEqual(item["finished"], "2026-03-02")  # curated stamp kept
        self.assertEqual(item["topics"], ["Data Feeds", "AI"])  # union, curated first

    def test_blurb_falls_back_to_calibre_when_uncurated(self):
        item = _book(blurb="")
        facts = cs.calibre_facts({"title": "t", "authors": "a", "comments": "<p>From Calibre.</p>",
                                  "rating": None, "tags": []})
        cs.apply_to_existing(item, facts)
        self.assertEqual(item["blurb"], "From Calibre.")

    def test_custom_status_overrides_curated(self):
        item = _book(status="Reading", started="2026-06-01")
        facts = cs.calibre_facts({"title": "t", "authors": "a", "rating": None,
                                  "comments": "", "tags": [], "#status": "read",
                                  "#finished": "2026-07-01T00:00:00"})
        cs.apply_to_existing(item, facts)
        self.assertEqual(item["status"], "Read")
        self.assertEqual(item["finished"], "2026-07-01")


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.items = [
            _book(),
            {"id": "cfa", "type": "certification", "title": "CFA", "author": "CFA Institute",
             "status": "Queued", "topics": ["Quant"], "blurb": ""},
        ]

    def test_match_updates_in_place_no_duplicate(self):
        recs = [{"title": "Designing Data-Intensive Applications",
                 "authors": "Martin Kleppmann", "rating": 8, "comments": "", "tags": []}]
        added, updated, orphans = cs.plan_sync(recs, self.items)
        self.assertEqual(len(added), 0)
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["id"], "ddia")
        self.assertEqual(orphans, [])                 # cert is not a book orphan

    def test_new_book_added_as_discovered(self):
        recs = [{"title": "New Book", "authors": "Someone", "rating": None,
                 "comments": "", "tags": []}]
        added, updated, orphans = cs.plan_sync(recs, self.items)
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]["type"], "book")
        self.assertEqual(added[0]["status"], "Discovered")
        self.assertEqual(added[0]["id"], "new-book")
        # ddia not in the pull -> orphan; cert never considered
        self.assertEqual([o["id"] for o in orphans], ["ddia"])

    def test_certification_never_touched(self):
        # a record whose title/author happens to collide with the cert must not
        # match it — matching is scoped to book items only.
        recs = [{"title": "CFA", "authors": "CFA Institute", "rating": None,
                 "comments": "", "tags": []}]
        added, updated, orphans = cs.plan_sync(recs, self.items)
        self.assertEqual(len(added), 1)               # treated as a new *book*
        self.assertEqual(added[0]["type"], "book")
        self.assertEqual(len(updated), 0)


if __name__ == "__main__":
    unittest.main()

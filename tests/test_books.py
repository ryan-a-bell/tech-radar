"""
Tests for build_books' pure functions — the calibredb-record mapping and the
overlay merge. No Calibre, no subprocess, no disk fixtures: every function
under test takes plain dicts/strings.

Run from the repo root:
    python -m unittest discover -s tests
    python -m unittest tests.test_books
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_books as bb  # noqa: E402


class HelperTests(unittest.TestCase):
    def test_strip_html(self):
        self.assertEqual(bb.strip_html("<p>Hello <b>world</b>.</p>"), "Hello world.")
        self.assertEqual(bb.strip_html(""), "")
        self.assertEqual(bb.strip_html(None), "")

    def test_year_and_undefined(self):
        self.assertEqual(bb._year("2017-03-16T00:00:00+00:00"), 2017)
        self.assertIsNone(bb._year("0101-01-01T00:00:00+00:00"))  # calibre "undefined"
        self.assertIsNone(bb._year(None))

    def test_date(self):
        self.assertEqual(bb._date("2026-07-10T12:00:00+00:00"), "2026-07-10")
        self.assertIsNone(bb._date("0101-01-01T00:00:00+00:00"))
        self.assertIsNone(bb._date(None))

    def test_get_custom_key_variants(self):
        self.assertEqual(bb._get_custom({"#status": "Reading"}, "status"), "Reading")
        self.assertEqual(bb._get_custom({"*status": "Reading"}, "status"), "Reading")
        self.assertEqual(bb._get_custom({"status": "Reading"}, "status"), "Reading")
        self.assertIsNone(bb._get_custom({"status": ""}, "status"))
        self.assertIsNone(bb._get_custom({}, "status"))

    def test_slug(self):
        self.assertEqual(bb._slug("The Rust Programming Language"),
                         "the-rust-programming-language")
        self.assertEqual(bb._slug(""), "book")


class MappingTests(unittest.TestCase):
    def test_facts_mapped(self):
        book = bb.calibre_to_book({
            "title": "  Deep Learning ", "authors": "Goodfellow", "pubdate": "2016-01-01",
            "rating": 8, "comments": "<p>Text.</p>", "tags": ["ML", "Junk"],
            "timestamp": "2024-05-06T00:00:00",
        })
        self.assertEqual(book["title"], "Deep Learning")
        self.assertEqual(book["year"], 2016)
        self.assertEqual(book["rating"], 4)          # 8 // 2
        self.assertEqual(book["blurb"], "Text.")
        self.assertEqual(book["topics"], ["ML"])     # "Junk" not in vocabulary
        self.assertEqual(book["added"], "2024-05-06")
        self.assertNotIn("status", book)             # no custom col, no status yet

    def test_custom_columns_supply_reading_state(self):
        book = bb.calibre_to_book({
            "title": "X", "authors": "Y", "rating": None, "comments": "", "tags": [],
            "#status": "reading", "#pages_read": 42, "#started": "2026-07-01T00:00:00",
        })
        self.assertEqual(book["status"], "Reading")  # title-cased
        self.assertEqual(book["pages_read"], 42)
        self.assertEqual(book["started"], "2026-07-01")

    def test_zero_rating_is_none(self):
        book = bb.calibre_to_book({"title": "X", "authors": "Y", "rating": 0,
                                   "comments": "", "tags": []})
        self.assertIsNone(book["rating"])


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.overlay = [{
            "id": "ddia", "title": "Designing Data-Intensive Applications",
            "author": "Martin Kleppmann", "year": 2017, "status": "Read",
            "topics": ["Data Feeds"], "pages": 616, "pages_read": None, "rating": 5,
            "added": None, "started": None, "finished": "2026-03-02",
            "blurb": "Curated blurb.",
        }]

    def test_curated_state_preserved_facts_overlaid(self):
        recs = [{"title": "Designing Data-Intensive Applications",
                 "authors": "Martin Kleppmann", "pubdate": "2017-03-16",
                 "rating": 10, "comments": "<p>Calibre blurb.</p>",
                 "tags": ["Data Feeds", "AI"], "timestamp": "2024-01-05T00:00:00"}]
        books, orphans = bb.merge_books(recs, self.overlay)
        self.assertEqual(orphans, [])
        b = books[0]
        self.assertEqual(b["id"], "ddia")             # curated id kept
        self.assertEqual(b["status"], "Read")         # curated state kept
        self.assertEqual(b["blurb"], "Curated blurb.")  # curated blurb wins
        self.assertEqual(b["rating"], 5)              # calibre 10 // 2
        self.assertEqual(b["added"], "2024-01-05")    # calibre fact fills the null
        self.assertEqual(b["topics"], ["Data Feeds", "AI"])  # union, curated first

    def test_new_book_defaults_to_discovered(self):
        recs = [{"title": "New Book", "authors": "Someone", "rating": None,
                 "comments": "", "tags": []}]
        books, orphans = bb.merge_books(recs, self.overlay)
        new = [b for b in books if b["title"] == "New Book"][0]
        self.assertEqual(new["status"], "Discovered")
        self.assertEqual(new["id"], "new-book")

    def test_overlay_only_book_is_an_orphan(self):
        books, orphans = bb.merge_books([], self.overlay)
        self.assertEqual(books, [])
        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0]["id"], "ddia")

    def test_blurb_falls_back_to_calibre_when_uncurated(self):
        overlay = [dict(self.overlay[0], blurb="")]
        recs = [{"title": "Designing Data-Intensive Applications",
                 "authors": "Martin Kleppmann", "comments": "<p>From Calibre.</p>",
                 "rating": None, "tags": []}]
        books, _ = bb.merge_books(recs, overlay)
        self.assertEqual(books[0]["blurb"], "From Calibre.")


if __name__ == "__main__":
    unittest.main()

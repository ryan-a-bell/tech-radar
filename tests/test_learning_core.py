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


class MarkdownRoundTripTests(unittest.TestCase):
    """serialize_item -> parse_front_matter/to_item must be lossless for the
    field shapes the Learning Library actually uses. These are the guardrails
    that make Markdown a safe source of truth for the CLI."""

    def _round_trip(self, item):
        text = core.serialize_item(item)
        fm, body = core.parse_front_matter(text)
        return core.to_item(fm, body, default_id=item["id"])

    def test_book_with_shelved_note_survives(self):
        it = core.new_item("book", "Some Dense Book", author="A. Writer",
                            topics=["ML", "Quant"], year=2013, pages=244,
                            blurb="A blurb — with an em-dash and, commas.",
                            status="Shelved")
        it["shelved_note"] = "Skimmed ch.1–2 — revisit later: not now."
        self.assertEqual(self._round_trip(it), it)

    def test_certification_with_awkward_price_survives(self):
        it = core.new_item("certification", "Some Governance Cert",
                            author="IAPP", source="AIGP", url="https://x/y",
                            price="$649 member / $799 nonmember",
                            topics=["AI", "Skills"],
                            blurb="Covers governance, risk, and policy.")
        self.assertEqual(self._round_trip(it), it)

    def test_article_and_video_length_fields_survive(self):
        art = core.new_item("article", "A Paper: Attention", minutes=40,
                            source="arXiv", url="https://arxiv.org/abs/1",
                            topics=["ML"], year=2017, blurb="The paper.")
        vid = core.new_item("video", "Build GPT", duration="1h 56m",
                            source="YouTube", url="https://y/z", topics=["AI"],
                            blurb="Hands-on build.")
        self.assertEqual(self._round_trip(art), art)
        self.assertEqual(self._round_trip(vid), vid)

    def test_none_length_and_empty_topics_survive(self):
        it = core.new_item("book", "Bare Book")   # no pages, no topics, no blurb
        self.assertEqual(self._round_trip(it), it)
        self.assertIsNone(it["pages"])
        self.assertEqual(it["topics"], [])

    def test_blank_scalar_parses_to_none(self):
        fm, _ = core.parse_front_matter("---\npages:\n---\nbody\n")
        self.assertIsNone(fm["pages"])

    def test_title_with_internal_colon_is_not_quoted(self):
        it = core.new_item("book", "Reinforcement Learning: An Introduction",
                            topics=["ML"])
        self.assertIn("title: Reinforcement Learning: An Introduction",
                      core.serialize_item(it))
        self.assertEqual(self._round_trip(it), it)


class ConferenceTests(unittest.TestCase):
    """Conferences are the recurring type: a series item carrying a list of
    year-over-year editions, each a pipe-delimited line."""

    def test_new_conference_has_recurrence_and_empty_editions(self):
        it = core.new_item("conference", "INCOSE IS", author="INCOSE",
                            url="https://x", topics=["Skills"])
        self.assertEqual(it["type"], "conference")
        self.assertEqual(it["recurrence"], "annual")
        self.assertEqual(it["editions"], [])
        self.assertIn("source", it)   # conferences carry source/url like non-books
        self.assertIn("url", it)
        self.assertNotIn("pages", it)

    def test_new_conference_custom_recurrence(self):
        it = core.new_item("conference", "Biennial Thing", recurrence="biennial")
        self.assertEqual(it["recurrence"], "biennial")

    def test_edition_line_round_trips(self):
        raw = "2026 | 2026-06-13..06-18 | Yokohama, Japan | Registered | 2025-11-01 | https://x/y"
        ed = core.parse_edition(raw)
        self.assertEqual(ed["year"], 2026)
        self.assertEqual(ed["location"], "Yokohama, Japan")
        self.assertEqual(ed["status"], "Registered")
        self.assertEqual(ed["url"], "https://x/y")   # colon in URL survives
        self.assertEqual(core.serialize_edition(ed), raw)

    def test_edition_trailing_blanks_trimmed_and_restored(self):
        ed = core.parse_edition("2027 | 2027-07-17..07-22")
        self.assertEqual(ed["year"], 2027)
        self.assertIsNone(ed["location"])
        self.assertIsNone(ed["url"])
        # trailing empties are dropped on serialize, restored to None on parse
        line = core.serialize_edition(ed)
        self.assertEqual(line, "2027 | 2027-07-17..07-22")
        self.assertEqual(core.parse_edition(line), ed)

    def test_upsert_adds_and_updates_by_year(self):
        it = core.new_item("conference", "RAMS")
        core.upsert_edition(it, 2026, dates="2026-01-19..01-22",
                            location="Miramar Beach, FL")
        self.assertEqual(len(it["editions"]), 1)
        self.assertEqual(it["editions"][0]["status"], "Announced")  # default
        # re-upsert the same year updates in place, no duplicate
        core.upsert_edition(it, 2026, location="Somewhere Else, FL")
        self.assertEqual(len(it["editions"]), 1)
        self.assertEqual(it["editions"][0]["location"], "Somewhere Else, FL")
        self.assertEqual(it["editions"][0]["dates"], "2026-01-19..01-22")  # kept

    def test_upsert_keeps_editions_newest_first(self):
        it = core.new_item("conference", "IS")
        core.upsert_edition(it, 2025)
        core.upsert_edition(it, 2027)
        core.upsert_edition(it, 2026)
        self.assertEqual([e["year"] for e in it["editions"]], [2027, 2026, 2025])

    def test_upsert_does_not_clobber_status_when_omitted(self):
        it = core.new_item("conference", "IS")
        core.upsert_edition(it, 2026, status="Registered")
        core.upsert_edition(it, 2026, cfp="2025-11-01")   # no status passed
        self.assertEqual(it["editions"][0]["status"], "Registered")

    def test_upsert_rejects_bad_status(self):
        it = core.new_item("conference", "IS")
        with self.assertRaises(ValueError):
            core.upsert_edition(it, 2026, status="Attending")

    def test_next_edition_prefers_upcoming_then_latest_past(self):
        it = core.new_item("conference", "IS")
        this_year = date.today().year
        core.upsert_edition(it, this_year - 2)
        core.upsert_edition(it, this_year + 1)
        core.upsert_edition(it, this_year + 3)
        self.assertEqual(core.next_edition(it)["year"], this_year + 1)
        # with only past editions, the most recent one is surfaced
        past = core.new_item("conference", "Old")
        core.upsert_edition(past, this_year - 5)
        core.upsert_edition(past, this_year - 2)
        self.assertEqual(core.next_edition(past)["year"], this_year - 2)
        self.assertIsNone(core.next_edition(core.new_item("conference", "Empty")))

    def test_conference_markdown_round_trips(self):
        it = core.new_item("conference", "INCOSE International Symposium",
                            author="INCOSE", url="https://incose.org/is",
                            topics=["Skills"], status="Queued",
                            blurb="The flagship systems-engineering symposium.")
        core.upsert_edition(it, 2026, dates="2026-06-13..06-18",
                            location="Yokohama, Japan", status="Registered",
                            cfp="2025-11-01")
        core.upsert_edition(it, 2027, dates="2027-07-17..07-22")  # sparse
        text = core.serialize_item(it)
        fm, body = core.parse_front_matter(text)
        self.assertEqual(core.to_item(fm, body, default_id=it["id"]), it)


if __name__ == "__main__":
    unittest.main()

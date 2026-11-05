"""Tests for scripts/build_stats.py (no network). Run with: python3 -m unittest discover -s tests"""

import io
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stderr
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_readme as br  # noqa: E402
import build_stats as bs  # noqa: E402

TODAY = date(2026, 3, 10)


def calendar(counts: list[int], end: date = TODAY) -> dict[date, int]:
    """Consecutive days ending on ``end``."""
    return {end - timedelta(days=len(counts) - 1 - i): count for i, count in enumerate(counts)}


def user_payload(featured: str = "demo") -> dict:
    """A GraphQL ``user`` payload whose first repository is named ``featured``."""
    def day(iso: str, count: int) -> dict:
        return {"date": iso, "contributionCount": count}

    return {
        "year2025": {
            "totalCommitContributions": 7,
            "totalPullRequestReviewContributions": 6,
            "contributionCalendar": {"weeks": [{"contributionDays": [day("2025-12-31", 2)]}]},
        },
        "year2026": {
            "totalCommitContributions": 3,
            "totalPullRequestReviewContributions": 2,
            "contributionCalendar": {"weeks": [{"contributionDays": [day("2026-01-01", 1), day("2026-01-02", 0)]}]},
        },
        "pullRequests": {"totalCount": 4},
        "mergedPullRequests": {"totalCount": 3},
        "repositoriesContributedTo": {"totalCount": 0},
        "issues": {"totalCount": 5},
        "repositories": {
            "nodes": [
                {
                    "name": featured, "description": "A <demo> & test", "stargazerCount": 2, "forkCount": 1,
                    "primaryLanguage": {"name": "Rust", "color": "#dea584"},
                    "languages": {"edges": [{"size": 300, "node": {"name": "Rust", "color": "#dea584"}}]},
                },
                {
                    "name": "other", "description": None, "stargazerCount": 1, "forkCount": 0,
                    "primaryLanguage": None,
                    "languages": {"edges": [{"size": 100, "node": {"name": "Python", "color": None}}]},
                },
            ]
        },
    }


class StreakTests(unittest.TestCase):
    def test_empty_calendar(self):
        self.assertEqual(bs.compute_streak({}, TODAY), bs.Streak(0, 0, None, 0, None, None))

    def test_current_streak_ending_today(self):
        streak = bs.compute_streak(calendar([0, 1, 2, 3]), TODAY)
        self.assertEqual((streak.total, streak.current, streak.current_start), (6, 3, TODAY - timedelta(days=2)))

    def test_today_without_contributions_keeps_yesterdays_streak(self):
        streak = bs.compute_streak(calendar([1, 1, 0]), TODAY)
        self.assertEqual((streak.current, streak.current_start), (2, TODAY - timedelta(days=2)))

    def test_two_empty_days_break_the_current_streak(self):
        self.assertEqual(bs.compute_streak(calendar([1, 0, 0]), TODAY).current, 0)

    def test_longest_streak_and_its_dates(self):
        streak = bs.compute_streak(calendar([1, 1, 1, 0, 1, 1]), TODAY)
        self.assertEqual(streak.longest, 3)
        self.assertEqual((streak.longest_start, streak.longest_end), (TODAY - timedelta(days=5), TODAY - timedelta(days=3)))

    def test_missing_days_break_a_streak(self):
        days = {TODAY - timedelta(days=5): 1, TODAY - timedelta(days=3): 1}
        self.assertEqual(bs.compute_streak(days, TODAY).longest, 1)

    def test_future_days_are_ignored(self):
        days = calendar([1, 1]) | {TODAY + timedelta(days=1): 9}
        streak = bs.compute_streak(days, TODAY)
        self.assertEqual((streak.longest, streak.current), (2, 2))


class LanguageTests(unittest.TestCase):
    def test_shares_sorted_and_limited(self):
        langs = bs.top_languages({"A": 10, "B": 30, "C": 60}, {"A": "#111"}, count=2)
        self.assertEqual([lang.name for lang in langs], ["C", "B"])
        self.assertAlmostEqual(langs[0].share, 0.6)

    def test_missing_color_falls_back_to_muted(self):
        self.assertEqual(bs.top_languages({"A": 1}, {})[0].color, f"#{bs.THEME['muted']}")

    def test_no_bytes_means_no_languages(self):
        self.assertEqual(bs.top_languages({}, {}), [])


class ParseTests(unittest.TestCase):
    def test_sums_every_year_and_repository(self):
        stats = bs.parse(user_payload(), "demo", date(2026, 1, 2))
        self.assertEqual((stats.stars, stats.commits, stats.pull_requests, stats.issues), (3, 10, 4, 5))
        self.assertEqual((stats.merged_pull_requests, stats.reviews, stats.contributed_to), (3, 8, 0))
        self.assertEqual(stats.streak.total, 3)
        self.assertEqual(stats.streak.longest, 2)  # 2025-12-31 → 2026-01-01 crosses the year boundary
        self.assertEqual([lang.name for lang in stats.languages], ["Rust", "Python"])
        self.assertEqual(stats.featured, bs.Repo("demo", "A <demo> & test", "Rust", "#dea584", 2, 1))

    def test_missing_featured_repository_fails(self):
        with self.assertRaises(bs.StatsError):
            bs.parse(user_payload(), "nope", TODAY)


class RenderTests(unittest.TestCase):
    def setUp(self):
        _, self.locales, _ = br.load(ROOT)
        self.stats = bs.parse(user_payload(), "demo", date(2026, 1, 2))

    def test_compact_numbers(self):
        self.assertEqual([bs.compact(n) for n in (0, 999, 1000, 2240)], ["0", "999", "1k", "2.2k"])

    def test_date_range(self):
        self.assertEqual(bs.date_range(None, None), "")
        self.assertEqual(bs.date_range(TODAY, TODAY), "2026-03-10")
        self.assertEqual(bs.date_range(TODAY, TODAY + timedelta(days=1)), "2026-03-10 → 2026-03-11")

    def test_one_card_set_per_language_plus_featured(self):
        files = bs.build_cards(self.stats, self.locales)
        expected = {"featured.svg"} | {f"{kind}-{code}.svg" for code in self.locales for kind in ("stats", "streak", "langs")}
        self.assertEqual(set(files), expected)

    def test_every_card_is_valid_xml_with_escaped_text(self):
        for name, svg in bs.build_cards(self.stats, self.locales).items():
            with self.subTest(card=name):
                ET.fromstring(svg)
        self.assertIn("A &lt;demo&gt; &amp; test", bs.featured_card(self.stats.featured))

    def test_cards_use_translated_labels(self):
        files = bs.build_cards(self.stats, self.locales)
        for code, locale in self.locales.items():
            with self.subTest(code=code):
                self.assertIn(locale["activity"]["cards"]["stats_title"], files[f"stats-{code}.svg"])
                self.assertIn(locale["activity"]["cards"]["streak_current"], files[f"streak-{code}.svg"])

    def test_merged_pull_requests_shown_out_of_total(self):
        labels = self.locales["en"]["activity"]["cards"]
        self.assertIn(">3 / 4<", bs.stats_card(self.stats, labels))

    def test_contributed_to_row_only_when_not_zero(self):
        labels = self.locales["en"]["activity"]["cards"]
        hidden = bs.stats_card(self.stats, labels)
        shown = bs.stats_card(bs.Stats(**{**self.stats.__dict__, "contributed_to": 2}), labels)
        self.assertNotIn(labels["contributed_to"], hidden)
        self.assertIn(labels["contributed_to"], shown)
        self.assertIn('height="220"', shown)  # one more row than the hidden card (195)
        self.assertIn('height="195"', hidden)

    def test_long_description_is_truncated(self):
        repo = bs.Repo("r", "x" * 100, None, None, 0, 0)
        self.assertIn("x" * 57 + "…", bs.featured_card(repo))


class MainTests(unittest.TestCase):
    def test_missing_token_returns_error_code(self):
        with mock.patch.dict(os.environ, {}, clear=True), redirect_stderr(io.StringIO()) as err:
            self.assertEqual(bs.main(["--out", "unused"]), 2)
        self.assertIn("GITHUB_TOKEN", err.getvalue())

    def test_api_error_returns_error_code(self):
        with (
            mock.patch.dict(os.environ, {"GITHUB_TOKEN": "x"}),
            mock.patch.object(bs, "fetch_user", side_effect=bs.StatsError("rate limited")),
            redirect_stderr(io.StringIO()) as err,
        ):
            self.assertEqual(bs.main(["--out", "unused"]), 2)
        self.assertIn("rate limited", err.getvalue())

    def test_writes_every_card(self):
        shared, _, _ = br.load(ROOT)
        with (
            tempfile.TemporaryDirectory() as out,
            mock.patch.dict(os.environ, {"GITHUB_TOKEN": "x"}),
            mock.patch.object(bs, "fetch_user", return_value=user_payload(shared["featured"]["repo"])),
            redirect_stderr(io.StringIO()),
            mock.patch("sys.stdout", io.StringIO()),
        ):
            self.assertEqual(bs.main(["--out", out]), 0)
            self.assertTrue((Path(out) / "featured.svg").is_file())
            self.assertTrue((Path(out) / "stats-en.svg").is_file())


if __name__ == "__main__":
    unittest.main()

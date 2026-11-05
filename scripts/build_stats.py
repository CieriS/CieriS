#!/usr/bin/env python3
"""Render the profile's activity cards (stats, streak, top languages, featured repo) as SVG files.

The public card services (github-readme-stats, github-readme-streak-stats) go down or get paused
often, so the cards are built here from the GitHub GraphQL API: a scheduled workflow
(``.github/workflows/stats.yml``) runs this script and publishes the files on the ``output`` branch,
which the READMEs load through ``stats_url`` in ``readme/shared.toml``.

Usage:
    GITHUB_TOKEN=... python3 scripts/build_stats.py --out out/

Card labels come from ``[activity.cards]`` in each ``readme/locales/<code>.toml``: one file per
language for the translated cards (``stats-<code>.svg``, ``streak-<code>.svg``, ``langs-<code>.svg``)
and one ``featured.svg``. Standard library only (Python 3.11+).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from build_readme import ROOT, TemplateError, load

GRAPHQL_URL = "https://api.github.com/graphql"
LANGS_COUNT = 8
THEME = {"bg": "0D1117", "title": "70A5FD", "text": "C0CAF5", "accent": "BF91F3", "muted": "8B949E"}
FONT = "font-family=\"'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif\""


class StatsError(Exception):
    """The GitHub API returned an error or data the cards cannot use."""


@dataclass(frozen=True)
class Streak:
    total: int
    current: int
    current_start: date | None
    longest: int
    longest_start: date | None
    longest_end: date | None


@dataclass(frozen=True)
class Language:
    name: str
    color: str
    share: float  # 0..1


@dataclass(frozen=True)
class Repo:
    name: str
    description: str
    language: str | None
    language_color: str | None
    stars: int
    forks: int


@dataclass(frozen=True)
class Stats:
    stars: int
    commits: int
    pull_requests: int
    issues: int
    streak: Streak
    languages: list[Language]
    featured: Repo


# --- Pure computations -----------------------------------------------------------------------


def compute_streak(days: dict[date, int], today: date) -> Streak:
    """Streaks of consecutive days with contributions. Today without contributions yet does not
    break the current streak: it counts from yesterday until the day is over."""
    total = sum(days.values())
    longest = run = 0
    longest_start = longest_end = run_start = previous = None
    for day in sorted(d for d in days if d <= today):
        contiguous = previous is not None and day - previous == timedelta(days=1)
        if days[day] > 0:
            if run == 0 or not contiguous:
                run, run_start = 0, day
            run += 1
            if run > longest:
                longest, longest_start, longest_end = run, run_start, day
        else:
            run = 0
        previous = day
    current, cursor = 0, today if days.get(today, 0) > 0 else today - timedelta(days=1)
    while days.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    current_start = cursor + timedelta(days=1) if current else None
    return Streak(total, current, current_start, longest, longest_start, longest_end)


def top_languages(sizes: dict[str, int], colors: dict[str, str], count: int = LANGS_COUNT) -> list[Language]:
    """The ``count`` largest languages by bytes, as shares of all bytes."""
    total = sum(sizes.values())
    if not total:
        return []
    ranked = sorted(sizes.items(), key=lambda item: (-item[1], item[0]))[:count]
    return [Language(name, colors.get(name) or f"#{THEME['muted']}", size / total) for name, size in ranked]


def parse(user: dict[str, Any], featured_repo: str, today: date) -> Stats:
    """Turn the GraphQL ``user`` payload into the card data."""
    days: dict[date, int] = {}
    commits = 0
    for key, collection in user.items():
        if not key.startswith("year"):
            continue
        commits += collection["totalCommitContributions"]
        for week in collection["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                days[date.fromisoformat(day["date"])] = day["contributionCount"]
    sizes: dict[str, int] = {}
    colors: dict[str, str] = {}
    stars = 0
    featured = None
    for repo in user["repositories"]["nodes"]:
        stars += repo["stargazerCount"]
        for edge in repo["languages"]["edges"]:
            sizes[edge["node"]["name"]] = sizes.get(edge["node"]["name"], 0) + edge["size"]
            colors[edge["node"]["name"]] = edge["node"]["color"]
        if repo["name"] == featured_repo:
            language = repo["primaryLanguage"] or {}
            featured = Repo(
                repo["name"], repo["description"] or "", language.get("name"), language.get("color"),
                repo["stargazerCount"], repo["forkCount"],
            )
    if featured is None:
        raise StatsError(f"featured repository {featured_repo!r} not found among the public repositories")
    return Stats(
        stars=stars,
        commits=commits,
        pull_requests=user["pullRequests"]["totalCount"],
        issues=user["issues"]["totalCount"],
        streak=compute_streak(days, today),
        languages=top_languages(sizes, colors),
        featured=featured,
    )


def compact(number: int) -> str:
    return f"{number / 1000:.1f}k".replace(".0k", "k") if number >= 1000 else str(number)


def date_range(start: date | None, end: date | None) -> str:
    if start is None or end is None:
        return ""
    return start.isoformat() if start == end else f"{start.isoformat()} → {end.isoformat()}"


# --- SVG rendering ---------------------------------------------------------------------------


def card(width: int, height: int, title: str, body: str) -> str:
    title_svg = f'<text x="25" y="35" fill="#{THEME["title"]}" font-size="18" font-weight="600">{escape(title)}</text>' if title else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{escape(title)}" {FONT}>'
        f'<rect width="{width}" height="{height}" rx="6" fill="#{THEME["bg"]}"/>{title_svg}{body}</svg>\n'
    )


def stats_card(stats: Stats, labels: dict[str, str]) -> str:
    rows = [
        (labels["stars"], stats.stars),
        (labels["commits"], stats.commits),
        (labels["pull_requests"], stats.pull_requests),
        (labels["issues"], stats.issues),
    ]
    body = "".join(
        f'<text x="25" y="{70 + i * 25}" fill="#{THEME["text"]}" font-size="14">{escape(label)}:</text>'
        f'<text x="300" y="{70 + i * 25}" fill="#{THEME["text"]}" font-size="14" font-weight="700">{compact(value)}</text>'
        for i, (label, value) in enumerate(rows)
    )
    return card(495, 170, labels["stats_title"], body)


def streak_card(streak: Streak, labels: dict[str, str]) -> str:
    columns = [
        (streak.total, labels["streak_total"], ""),
        (streak.current, labels["streak_current"], date_range(streak.current_start, streak.current_start and streak.current_start + timedelta(days=streak.current - 1))),
        (streak.longest, labels["streak_longest"], date_range(streak.longest_start, streak.longest_end)),
    ]
    body = ""
    for i, (value, label, period) in enumerate(columns):
        x = 82 + i * 165
        color = THEME["accent"] if i == 1 else THEME["title"]
        body += (
            f'<text x="{x}" y="85" text-anchor="middle" fill="#{color}" font-size="28" font-weight="700">{compact(value)}</text>'
            f'<text x="{x}" y="120" text-anchor="middle" fill="#{THEME["text"]}" font-size="14">{escape(label)}</text>'
            f'<text x="{x}" y="145" text-anchor="middle" fill="#{THEME["muted"]}" font-size="11">{escape(period)}</text>'
        )
    body += "".join(f'<line x1="{165 * i}" y1="50" x2="{165 * i}" y2="150" stroke="#{THEME["muted"]}" stroke-opacity="0.3"/>' for i in (1, 2))
    return card(495, 195, "", body)


def languages_card(languages: list[Language], labels: dict[str, str]) -> str:
    width, bar = 350, 300
    body, x = "", 25.0
    for lang in languages:
        segment = bar * lang.share
        body += f'<rect x="{x:.2f}" y="55" width="{segment:.2f}" height="8" fill="{escape(lang.color)}"/>'
        x += segment
    for i, lang in enumerate(languages):
        cx, cy = 25 + (i % 2) * 160, 90 + (i // 2) * 25
        body += (
            f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{escape(lang.color)}"/>'
            f'<text x="{cx + 15}" y="{cy}" fill="#{THEME["text"]}" font-size="12">{escape(lang.name)} {lang.share * 100:.1f}%</text>'
        )
    height = 90 + ((len(languages) + 1) // 2) * 25
    return card(width, height, labels["languages_title"], body)


def featured_card(repo: Repo) -> str:
    description = repo.description if len(repo.description) <= 60 else repo.description[:57].rstrip() + "…"
    body = f'<text x="25" y="65" fill="#{THEME["text"]}" font-size="13">{escape(description)}</text>'
    x = 25
    if repo.language:
        body += (
            f'<circle cx="{x + 6}" cy="96" r="6" fill="{escape(repo.language_color or "#" + THEME["muted"])}"/>'
            f'<text x="{x + 18}" y="100" fill="#{THEME["text"]}" font-size="12">{escape(repo.language)}</text>'
        )
        x += 30 + 7 * len(repo.language)
    body += (
        f'<text x="{x}" y="100" fill="#{THEME["text"]}" font-size="12">★ {compact(repo.stars)}</text>'
        f'<text x="{x + 55}" y="100" fill="#{THEME["text"]}" font-size="12">⑂ {compact(repo.forks)}</text>'
    )
    return card(400, 120, repo.name, body)


def build_cards(stats: Stats, locales: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Every SVG file, keyed by file name."""
    files = {"featured.svg": featured_card(stats.featured)}
    for code, locale in locales.items():
        labels = locale["activity"]["cards"]
        files[f"stats-{code}.svg"] = stats_card(stats, labels)
        files[f"streak-{code}.svg"] = streak_card(stats.streak, labels)
        files[f"langs-{code}.svg"] = languages_card(stats.languages, labels)
    return files


# --- I/O -------------------------------------------------------------------------------------


def graphql(token: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise StatsError("; ".join(error.get("message", str(error)) for error in payload["errors"]))
    return payload["data"]


def fetch_user(token: str, login: str) -> dict[str, Any]:
    years = graphql(token, "query($login: String!) { user(login: $login) { contributionsCollection { contributionYears } } }", {"login": login})
    if years["user"] is None:
        raise StatsError(f"user {login!r} not found")
    year_fields = "".join(
        f'year{year}: contributionsCollection(from: "{year}-01-01T00:00:00Z", to: "{year}-12-31T23:59:59Z") '
        "{ totalCommitContributions contributionCalendar { weeks { contributionDays { date contributionCount } } } } "
        for year in years["user"]["contributionsCollection"]["contributionYears"]
    )
    query = (
        "query($login: String!) { user(login: $login) { "
        f"{year_fields}"
        "pullRequests { totalCount } issues { totalCount } "
        "repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) { nodes { "
        "name description stargazerCount forkCount primaryLanguage { name color } "
        "languages(first: 20, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } } } } }"
    )
    return graphql(token, query, {"login": login})["user"]


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="directory for the SVG files")
    args = parser.parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("error: set GITHUB_TOKEN", file=sys.stderr)
        return 2
    try:
        shared, locales, _ = load(root)
        stats = parse(fetch_user(token, shared["github_user"]), shared["featured"]["repo"], date.today())
        files = build_cards(stats, locales)
    except (StatsError, TemplateError, KeyError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (args.out / name).write_text(content, encoding="utf-8")
        print(f"wrote {args.out / name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

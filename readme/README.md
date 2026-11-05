# Profile README sources

The profile READMEs (`README.md`, `README.it.md`, `README.fr.md`, `README.de.md`) are **generated**:
GitHub renders Markdown as-is, with no includes or variables, so they are built from one template.
Do not edit them by hand; edit the files in this folder and rebuild.

| File | What goes in it |
|---|---|
| `shared.toml` | Values common to every language: name, links, company, stack badges, project list, languages |
| `locales/<code>.toml` | Translated text for one language (same keys in every file) |
| `template.md` | Layout, with `{{ placeholder }}` references |
| `[activity.cards]` in each locale | Labels of the activity cards (see below) |
| `../assets/` | Images served from this repository (the logo behind the portfolio link); a test fails if a README points to a file that is not there |

## Commands

```sh
python3 scripts/build_readme.py           # regenerate every README
python3 scripts/build_readme.py --check   # fail if a README is out of date (CI runs this)
python3 -m unittest discover -s tests     # tests
GITHUB_TOKEN=... python3 scripts/build_stats.py --out DIR   # activity cards (see below)
```

Python 3.11+, standard library only.

## Placeholders

- `{{ name }}`, `{{ links.linkedin }}`: any value from `shared.toml`, by dotted path.
- `{{ t.about.title }}`: a value from the current locale. Locale text may use shared placeholders
  too (`at {{ company }}`), so a fact lives in one place only.
- `{{ lang.code }}`: a field of the current `[[languages]]` entry.
- `{{ block.* }}`: generated Markdown/HTML: `header`, `languages` (switcher),
  `projects` (table), `stack.<group>` (badges of that group).
- A list of strings renders as a bullet list. An unknown placeholder is an error, not an empty string.

## Common changes

- **Change a link, the company or a badge**: edit `shared.toml`, rebuild.
- **Add a project**: add a `[[projects]]` entry to `shared.toml` and its description under
  `[projects.descriptions]` in **every** locale (the build fails if one is missing).
- **Add a language**: add a `[[languages]]` entry and `locales/<code>.toml` with the same keys as
  `locales/en.toml`. The first language is the reference and the default `README.md`.

## Activity cards

The stats, streak, top-languages and featured-repository images are SVG files built by
`scripts/build_stats.py` from the GitHub GraphQL API, not by a public card service (those go down
or get paused, and the images break). `.github/workflows/stats.yml` runs it every night, on every
push to `main` that touches it or `readme/`, and on demand (Actions → Stats cards → Run workflow),
then force-pushes the files to the `output` branch; the READMEs load them from `stats_url`
(`shared.toml`). Files: `featured.svg` and, per language, `stats-<code>.svg`, `streak-<code>.svg`,
`langs-<code>.svg`.

- Counts come from the workflow's `GITHUB_TOKEN`: public activity only (private repositories are
  not counted). Languages: bytes of your public, non-fork repositories, top 8.
- Stats card: stars, commits, merged / total pull requests, code reviews, issues,
  published releases and tags of your public repositories (one row each); "contributed to"
  (other people's repositories) appears only once it is above 0.
- The current streak counts today only once there is a contribution; until then it ends yesterday.
- Preview locally: `GITHUB_TOKEN="$(gh auth token)" python3 scripts/build_stats.py --out /tmp/cards`.

## Git hooks

`.githooks/pre-push` runs before every push: a secret scan of the outgoing commits (gitleaks, or its Docker image when the binary is missing) and then the checks (`uv run --no-project --python '>=3.11' python -m unittest discover -s tests && uv run --no-project --python '>=3.11' python scripts/build_readme.py --check`; `uv` because the macOS `python3` can be 3.9, without `tomllib`). Enable it once per clone with `git config core.hooksPath .githooks`; skip it once with `git push --no-verify`. On CI, `.github/workflows/secret-scan.yml` scans the whole history of every branch and tag.

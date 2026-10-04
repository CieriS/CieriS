# Profile README sources

The profile READMEs (`README.md`, `README.it.md`, `README.fr.md`, `README.de.md`) are **generated**:
GitHub renders Markdown as-is, with no includes or variables, so they are built from one template.
Do not edit them by hand; edit the files in this folder and rebuild.

| File | What goes in it |
|---|---|
| `shared.toml` | Values common to every language: name, links, company, stack badges, project list, languages |
| `locales/<code>.toml` | Translated text for one language (same keys in every file) |
| `template.md` | Layout, with `{{ placeholder }}` references |

## Commands

```sh
python3 scripts/build_readme.py           # regenerate every README
python3 scripts/build_readme.py --check   # fail if a README is out of date (CI runs this)
python3 -m unittest discover -s tests     # tests
```

Python 3.11+, standard library only.

## Placeholders

- `{{ name }}`, `{{ links.linkedin }}`: any value from `shared.toml`, by dotted path.
- `{{ t.about.title }}`: a value from the current locale. Locale text may use shared placeholders
  too (`at {{ company }}`), so a fact lives in one place only.
- `{{ lang.stats_locale }}`: a field of the current `[[languages]]` entry.
- `{{ block.* }}`: generated Markdown/HTML: `header`, `languages` (switcher), `location_badge`,
  `projects` (table), `stack.<group>` (badges of that group).
- A list of strings renders as a bullet list. An unknown placeholder is an error, not an empty string.

## Common changes

- **Change a link, the company or a badge**: edit `shared.toml`, rebuild.
- **Add a project**: add a `[[projects]]` entry to `shared.toml` and its description under
  `[projects.descriptions]` in **every** locale (the build fails if one is missing).
- **Add a language**: add a `[[languages]]` entry and `locales/<code>.toml` with the same keys as
  `locales/en.toml`. The first language is the reference and the default `README.md`.

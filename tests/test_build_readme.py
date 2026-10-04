"""Tests for scripts/build_readme.py. Run with: python3 -m unittest discover -s tests"""

import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_readme as br  # noqa: E402


class RenderTests(unittest.TestCase):
    def test_replaces_dotted_paths(self):
        self.assertEqual(br.render("Hi {{ a.b }}!", {"a": {"b": "you"}}), "Hi you!")

    def test_whitespace_inside_braces_is_optional(self):
        self.assertEqual(br.render("{{x}}-{{  x  }}", {"x": 1}), "1-1")

    def test_values_are_rendered_recursively(self):
        context = {"company": "ACME", "t": {"line": "at {{ company }}"}}
        self.assertEqual(br.render("{{ t.line }}", context), "at ACME")

    def test_list_becomes_bullet_list(self):
        self.assertEqual(br.render("{{ items }}", {"items": ["a", "b"]}), "- a\n- b")

    def test_unknown_placeholder_fails(self):
        with self.assertRaisesRegex(br.TemplateError, "unknown placeholder"):
            br.render("{{ missing }}", {})

    def test_path_through_a_scalar_fails(self):
        with self.assertRaisesRegex(br.TemplateError, "unknown placeholder"):
            br.render("{{ a.b }}", {"a": "text"})

    def test_table_value_fails(self):
        with self.assertRaisesRegex(br.TemplateError, "not text"):
            br.render("{{ a }}", {"a": {"b": 1}})

    def test_list_of_non_strings_fails(self):
        with self.assertRaisesRegex(br.TemplateError, "list of strings"):
            br.render("{{ a }}", {"a": [1, 2]})

    def test_self_reference_fails_instead_of_looping(self):
        with self.assertRaisesRegex(br.TemplateError, "nested too deeply"):
            br.render("{{ a }}", {"a": "{{ a }}"})


class BlockTests(unittest.TestCase):
    def test_shields_label_escapes_dashes_underscores_and_spaces(self):
        self.assertEqual(br.shields_label("a-b_c d, e"), "a--b__c_d%2C_e")

    def test_language_switcher_bolds_current_and_links_others(self):
        languages = [
            {"code": "en", "flag": "E", "label": "English", "file": "README.md"},
            {"code": "it", "flag": "I", "label": "Italiano", "file": "README.it.md"},
        ]
        self.assertEqual(br.language_switcher(languages, "it"), "[E English](./README.md) · **I Italiano**")

    def test_projects_table_links_public_and_marks_private(self):
        shared = {
            "github_user": "me",
            "projects": [{"key": "pub", "stack": "Rust"}, {"key": "priv", "stack": "Go", "private": True}],
        }
        locale = {
            "projects": {
                "col_project": "P",
                "col_description": "D",
                "col_stack": "S",
                "private": "private",
                "descriptions": {"pub": "Public one", "priv": "Secret one"},
            }
        }
        lines = br.projects_table(shared, locale).splitlines()
        self.assertEqual(lines[0], "| P | D | S |")
        self.assertEqual(lines[2], "| [**pub**](https://github.com/me/pub) | Public one | Rust |")
        self.assertEqual(lines[3], "| **priv** <sub>private</sub> | Secret one | Go |")


class ValidateTests(unittest.TestCase):
    shared = {
        "languages": [{"code": "en"}, {"code": "it"}],
        "projects": [{"key": "p"}],
    }

    def locale(self, **extra):
        return {"title": "x", "projects": {"descriptions": {"p": "d"}}, **extra}

    def test_matching_locales_are_valid(self):
        self.assertEqual(br.validate(self.shared, {"en": self.locale(), "it": self.locale()}), [])

    def test_missing_and_extra_keys_are_reported(self):
        it = self.locale(extra="y")
        del it["title"]
        errors = br.validate(self.shared, {"en": self.locale(), "it": it})
        self.assertIn("locales/it.toml: missing title", errors)
        self.assertIn("locales/it.toml: extra is not in locales/en.toml", errors)

    def test_missing_project_description_is_reported(self):
        empty = {"title": "x", "projects": {"descriptions": {}}}
        errors = br.validate(self.shared, {"en": empty, "it": empty})
        self.assertIn("locales/en.toml: no description for project p", errors)

    def test_duplicate_language_code_is_reported(self):
        shared = {**self.shared, "languages": [{"code": "en"}, {"code": "en"}]}
        self.assertIn("duplicate language code in shared.toml", br.validate(shared, {"en": self.locale()}))


class RepositoryTests(unittest.TestCase):
    """The real sources build cleanly and the committed READMEs are up to date."""

    def test_committed_readmes_are_up_to_date(self):
        for path, content in br.build(ROOT).items():
            with self.subTest(path=path.name):
                self.assertEqual(path.read_text(encoding="utf-8"), content, "run python3 scripts/build_readme.py")

    def test_no_placeholder_survives(self):
        for path, content in br.build(ROOT).items():
            with self.subTest(path=path.name):
                self.assertNotIn("{{", content)

    def test_every_readme_links_every_other_language(self):
        outputs = br.build(ROOT)
        names = {path.name for path in outputs}
        for path, content in outputs.items():
            for other in names - {path.name}:
                with self.subTest(readme=path.name, link=other):
                    self.assertIn(f"](./{other})", content)


class MainTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(ROOT / "readme", self.root / "readme")

    def run_main(self, *args):
        stderr = io.StringIO()
        with redirect_stderr(stderr), redirect_stdout(io.StringIO()):
            code = br.main(list(args), root=self.root)
        return code, stderr.getvalue()

    def test_check_fails_when_readmes_are_missing_then_passes_after_build(self):
        self.assertEqual(self.run_main("--check")[0], 1)
        self.assertEqual(self.run_main()[0], 0)
        self.assertEqual(self.run_main("--check"), (0, ""))

    def test_broken_template_returns_error_code(self):
        (self.root / "readme" / "template.md").write_text("{{ nope }}", encoding="utf-8")
        code, err = self.run_main("--check")
        self.assertEqual(code, 2)
        self.assertIn("unknown placeholder", err)

    def test_missing_locale_file_returns_error_code(self):
        (self.root / "readme" / "locales" / "de.toml").unlink()
        code, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("de.toml", err)


if __name__ == "__main__":
    unittest.main()

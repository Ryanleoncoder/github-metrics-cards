import copy
import json
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

from scripts.configuration import DEFAULTS, parse_yaml
from scripts.github_data import CONTRIBUTIONS, GitHub, MetricsError, collect, period
from scripts import generate_metrics as renderer

NOW = datetime(2026, 10, 5, 18, tzinfo=timezone.utc)


def repository(name, private=False, size=100, language="Python"):
    return {"name": name, "nameWithOwner": "teste/" + name, "isPrivate": private, "isFork": False,
            "url": "https://github.com/teste/" + name, "primaryLanguage": {"name": language},
            "repositoryTopics": {"nodes": [{"topic": {"name": "topic"}}]},
            "languages": {"edges": [{"size": size, "node": {"name": language}}],
                          "pageInfo": {"hasNextPage": False}}}


class FakeGitHub:
    def __init__(self, repos=None, pages=None):
        self.repos = repos or [repository("novo"), repository("antigo", size=200)]
        self.calls = []
        self.pages = pages
        self.days = [{"date": (NOW.date()-timedelta(days=119-i)).isoformat(),
                      "contributionCount": i % 9,
                      "contributionLevel": "FOURTH_QUARTILE" if i % 9 else "NONE"} for i in range(120)]

    def query(self, query, variables):
        self.calls.append((query, variables))
        if query == CONTRIBUTIONS:
            return {"calendar": {"contributionCalendar": {"weeks": [{"contributionDays": self.days}]}},
                    "recent": {"totalRepositoriesWithContributedCommits": 3,
                               "commitContributionsByRepository": [
                                   {"repository": {"nameWithOwner": "teste/novo", "isPrivate": False},
                                    "contributions": {"totalCount": 17}},
                                   {"repository": {"nameWithOwner": "teste/antigo", "isPrivate": False},
                                    "contributions": {"totalCount": 2}},
                                   {"repository": {"nameWithOwner": "teste/privado", "isPrivate": True},
                                    "contributions": {"totalCount": 999}}]}}
        if self.pages:
            return {"repositories": self.pages.pop(0)}
        return {"repositories": {"nodes": self.repos, "pageInfo": {"hasNextPage": False, "endCursor": None}}}


class ConfigurationTests(unittest.TestCase):
    def load(self, text):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.yml"
            path.write_text(text, encoding="utf-8")
            return parse_yaml(path)

    def test_section_resets_when_a_root_key_follows(self):
        cfg = self.load("custom_palette:\n  primary: '#ABCDEF'\ntheme: dark-minimal\nusername: novo\n")
        self.assertEqual(cfg["theme"], "dark-minimal")
        self.assertEqual(cfg["username"], "novo")
        self.assertEqual(cfg["custom_palette"], {"primary": "#ABCDEF"})

    def test_inline_and_block_exclusion_lists(self):
        for value in ("exclude: [novo, 'teste/antigo']", "exclude:\n    - novo\n    - teste/antigo"):
            cfg = self.load("top_repos:\n  " + value + "\n")
            self.assertEqual(cfg["top_repos"]["exclude"], ["novo", "teste/antigo"])

    def test_bad_types_and_duplicate_keys_are_not_ignored(self):
        for text in ("top_repos:\n  count: true", "username: a\nusername: b", "cards:\n  top_repos: yes",
                     "year_in_code:\n  days: 0", "top_repos:\n  exclude: nope"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.load(text)

    def test_old_months_setting_uses_real_calendar_months(self):
        cfg = self.load("year_in_code:\n  months: 5\n")
        self.assertEqual(str(period(cfg, NOW)[0]), "2026-06-01")


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.cfg = copy.deepcopy(DEFAULTS)
        self.cfg["username"] = "teste"

    def test_real_counts_and_language_weights_are_not_estimates(self):
        data = collect(self.cfg, FakeGitHub(), NOW)
        self.assertEqual([(repo["name"], repo["commits"]) for repo in data["repos"]], [("novo", 17), ("antigo", 2)])
        self.assertEqual(data["languages"], {"Python": 19})
        self.assertEqual(len(data["days"]), 120)

    def test_private_repo_is_removed_even_with_a_broad_token(self):
        fake = FakeGitHub([repository("novo"), repository("privado", private=True)])
        data = collect(self.cfg, fake, NOW)
        self.assertNotIn("privado", json.dumps(data))
        self.assertEqual(fake.calls[1][1]["privacy"], "PUBLIC")

    def test_excluded_repo_does_not_affect_ranking_or_language_share(self):
        self.cfg["top_repos"]["exclude"] = ["teste/novo"]
        data = collect(self.cfg, FakeGitHub(), NOW)
        self.assertEqual(data["repos"][0]["name"], "antigo")
        self.assertEqual(data["languages"], {"Python": 2})

    def test_bytes_are_separate_from_commits(self):
        self.cfg["languages"]["metric"] = "code_size"
        self.assertEqual(collect(self.cfg, FakeGitHub(), NOW)["languages"], {"Python": 300})

    def test_pages_are_collected_and_cursor_is_passed(self):
        fake = FakeGitHub(pages=[
            {"nodes": [repository("novo")], "pageInfo": {"hasNextPage": True, "endCursor": "next"}},
            {"nodes": [repository("antigo")], "pageInfo": {"hasNextPage": False, "endCursor": None}},
        ])
        data = collect(self.cfg, fake, NOW)
        self.assertEqual(len(data["repos"]), 2)
        self.assertEqual(fake.calls[2][1]["cursor"], "next")

    def test_missing_calendar_date_is_not_filled_with_random_data(self):
        fake = FakeGitHub()
        fake.days.pop(40)
        with self.assertRaises(MetricsError):
            collect(self.cfg, fake, NOW)

    def test_graphql_error_cannot_be_a_success(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b'{"data":{"user":{}},"errors":[{"message":"forbidden"}]}'
        with patch("urllib.request.urlopen", return_value=Response()), self.assertRaises(MetricsError):
            GitHub("segredo").query("query{}", {})

    def test_http_error_never_includes_the_token(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("url", 403, "Forbidden", {}, None)):
            with self.assertRaises(MetricsError) as caught:
                GitHub("segredo-nao-publicar").query("query{}", {})
            self.assertNotIn("segredo-nao-publicar", str(caught.exception))


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.patch = patch.object(renderer, "METRICS_DIR", self.folder.name)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.cfg = copy.deepcopy(DEFAULTS)
        self.cfg["username"] = "teste"
        self.data = collect(self.cfg, FakeGitHub(), NOW)
        self.cfg["_data"] = self.data

    def read(self, filename):
        return ET.parse(Path(self.folder.name) / filename).getroot()

    def test_calendar_has_exactly_one_tile_per_date(self):
        renderer.generate_year_in_code_svg(self.data["days"], self.cfg)
        root = self.read("year-in-code.svg")
        tiles = [node for node in root.iter() if "data-date" in node.attrib]
        self.assertEqual(len(tiles), 120)
        self.assertEqual(tiles[0].get("data-date"), self.data["days"][0]["date"])
        self.assertEqual(len({node.get("data-date") for node in tiles}), 120)
        self.assertNotIn("2026-06-08 — 2026-10-05", " ".join(root.itertext()))

    def test_special_characters_are_escaped_and_tags_can_be_hidden(self):
        self.cfg["top_repos"]["show_language"] = False
        self.cfg["top_repos"]["show_topics"] = False
        renderer.generate_top_repos_svg([{**self.data["repos"][0], "name": "repo & <teste>"}], self.cfg)
        text = " ".join(self.read("languages-recent.svg").itertext())
        self.assertIn("repo & <teste>", text)
        self.assertNotIn("Python", text)
        self.assertNotIn("#topic", text)

    def test_cards_have_the_same_height_and_no_visible_timestamp(self):
        renderer.generate_languages_commits_svg(self.data["languages"], self.cfg)
        renderer.generate_top_repos_svg(self.data["repos"], self.cfg)
        langs = self.read("languages-commits.svg")
        repos = self.read("languages-recent.svg")
        self.assertEqual(langs.get("height"), repos.get("height"))
        text = " ".join(langs.itertext())
        self.assertNotIn("UPDATED", text)
        self.assertNotIn("ACTIVE REPOS", text)
        self.assertNotIn("COMMIT MIX", text)
        self.assertIn("commits", text)

    def test_language_percentages_add_to_one_hundred(self):
        renderer.generate_languages_commits_svg({"Python": 1, "Java": 1, "Go": 1}, self.cfg)
        text = [node.text for node in self.read("languages-commits.svg").iter() if node.text and node.text.endswith("%")]
        self.assertEqual(sum(int(value[:-1]) for value in text), 100)

    def test_demo_is_identified(self):
        self.cfg["_demo"] = True
        renderer.generate_top_repos_svg(self.data["repos"], self.cfg)
        self.assertIn("DEMO DATA", " ".join(self.read("languages-recent.svg").itertext()))

    def test_api_failure_keeps_the_last_good_artifact(self):
        artifact = Path(self.folder.name) / "year-in-code.svg"
        artifact.write_text("ultimo card válido", encoding="utf-8")
        with patch.object(renderer, "collect", side_effect=MetricsError("403")), patch("sys.argv", ["generate_metrics.py"]):
            self.assertEqual(renderer.main(), 1)
        self.assertEqual(artifact.read_text(encoding="utf-8"), "ultimo card válido")


if __name__ == "__main__":
    unittest.main()

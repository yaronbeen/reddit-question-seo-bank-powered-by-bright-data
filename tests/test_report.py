import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from report import analyze, cluster_questions, csv_cell, is_question, normalize_question, write_outputs


class RedditQuestionTests(unittest.TestCase):
    def test_question_detection_and_normalization(self):
        self.assertTrue(is_question("How do I migrate without downtime"))
        self.assertTrue(is_question("Best CRM for a two-person agency?"))
        self.assertFalse(is_question("My migration checklist"))
        self.assertEqual(normalize_question("  How do I migrate, safely?! "), "how do i migrate safely")

    def test_clusters_track_spread_without_usernames(self):
        rows = [
            {"thread_id": "a", "title": "How do I migrate safely?", "subreddit": "seo", "author": "person1", "source_url": "https://www.reddit.com/r/seo/comments/a/x/", "captured_at": "2026-11-09"},
            {"thread_id": "b", "title": "How can I migrate safely?", "subreddit": "webdev", "author": "person2", "source_url": "https://www.reddit.com/r/webdev/comments/b/x/", "captured_at": "2026-11-08"},
            {"thread_id": "a", "title": "How do I migrate safely?", "subreddit": "seo", "source_url": "https://www.reddit.com/r/seo/comments/a/x/", "captured_at": "2026-11-09"},
        ]
        clusters = cluster_questions(rows)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0]["sample_count"], 2)
        self.assertEqual(clusters[0]["subreddit_spread"], 2)
        self.assertNotIn("person1", str(clusters))

    def test_prior_cluster_key_survives_reworded_question(self):
        first = analyze({"rows": [{"thread_id": "a", "title": "How do I migrate safely?", "subreddit": "seo", "source_url": "https://www.reddit.com/r/seo/comments/a/x/", "captured_at": "2026-11-09"}], "coverage": []})
        second = analyze({"rows": [{"thread_id": "a", "title": "How do I migrate safely?", "subreddit": "seo", "source_url": "https://www.reddit.com/r/seo/comments/a/x/", "captured_at": "2026-11-09"}, {"thread_id": "b", "title": "How can I migrate safely?", "subreddit": "webdev", "source_url": "https://www.reddit.com/r/webdev/comments/b/x/", "captured_at": "2026-11-10"}], "coverage": []}, first["snapshot"])
        self.assertEqual(len(second["rows"]), 1)
        self.assertEqual(second["rows"][0]["cluster_key"], first["rows"][0]["cluster_key"])
        self.assertEqual(second["rows"][0]["status"], "changed")

    def test_snippets_alone_cannot_support_a_brief(self):
        rows = [{"thread_id": "a", "title": "What is a good migration checklist?", "subreddit": "seo", "source_url": "https://www.reddit.com/r/seo/comments/a/x/", "captured_at": "2026-11-09"}]
        result = analyze({"rows": rows, "coverage": [{"cluster_key": "what is a good migration checklist", "evidence_type": "snippet_only", "passages": []}]})
        self.assertEqual(result["rows"][0]["coverage"], "not_assessed")
        self.assertEqual(result["brief_count"], 0)

    def test_csv_diff_and_outputs(self):
        self.assertEqual(csv_cell("@formula"), "'@formula")
        payload = {"rows": [{"thread_id": "a", "title": "How do I migrate safely?", "subreddit": "seo", "source_url": "https://www.reddit.com/r/seo/comments/a/x/", "captured_at": "2026-11-09"}], "coverage": []}
        first = analyze(payload)
        payload2 = {"rows": payload["rows"] + [{"thread_id": "b", "title": "Which CMS is best for a small site?", "subreddit": "cms", "source_url": "https://www.reddit.com/r/cms/comments/b/x/", "captured_at": "2026-11-10"}], "coverage": []}
        second = analyze(payload2, first["snapshot"])
        statuses = {r["cluster_key"]: r["status"] for r in second["rows"]}
        self.assertEqual(len(second["rows"]), 2)
        self.assertIn("new", statuses.values())
        with tempfile.TemporaryDirectory() as tmp:
            write_outputs(second, tmp)
            self.assertTrue((Path(tmp) / "questions.csv").is_file())
            self.assertTrue((Path(tmp) / "report.md").is_file())

    def test_coverage_can_reference_any_member_question(self):
        rows = [
            {"thread_id": "a", "title": "How do I migrate safely?", "subreddit": "seo", "source_url": "https://www.reddit.com/r/seo/comments/a/x/", "captured_at": "2026-11-09"},
            {"thread_id": "b", "title": "How can I migrate safely?", "subreddit": "webdev", "source_url": "https://www.reddit.com/r/webdev/comments/b/x/", "captured_at": "2026-11-09"},
        ]
        result = analyze({"rows": rows, "coverage": [{"question": "How do I migrate safely?", "evidence_type": "page_passage", "assessment": "gap_observed", "passages": [{"text": "Rollback is not explained.", "source_url": "https://example.com/guide", "captured_at": "2026-11-09"}]}]})
        self.assertEqual(result["rows"][0]["coverage"], "gap_observed")
        self.assertEqual(result["brief_count"], 1)
        self.assertEqual(result["warnings"], [])

    def test_unmatched_coverage_is_an_explicit_warning(self):
        rows = [{"thread_id": "a", "title": "How do I migrate safely?", "subreddit": "seo", "source_url": "https://www.reddit.com/r/seo/comments/a/x/", "captured_at": "2026-11-09"}]
        result = analyze({"rows": rows, "coverage": [{"cluster_key": "wrong key", "evidence_type": "page_passage", "assessment": "gap_observed", "passages": [{"text": "Evidence", "source_url": "https://example.com"}]}]})
        self.assertEqual(result["rows"][0]["coverage"], "not_assessed")
        self.assertEqual(result["brief_count"], 0)
        self.assertEqual(len(result["warnings"]), 1)
        self.assertIn("wrong key", result["warnings"][0])

    def test_sanitized_live_records_are_questions_without_identities(self):
        fixture = json.loads((Path(__file__).parent / "fixtures" / "sanitized_live.json").read_text())
        clusters = cluster_questions(fixture["rows"])
        self.assertEqual(len(clusters), 2)
        self.assertTrue(all(is_question(row["title"]) for row in fixture["rows"]))
        self.assertNotIn("user_posted", str(clusters))


    def test_shipped_example_output_and_readme_table_are_current(self):
        root = Path(__file__).parents[1]
        result = analyze(json.loads((root / "examples" / "input.json").read_text()))
        self.assertEqual(result["report"], (root / "examples" / "output" / "report.md").read_text())
        readme = (root / "README.md").read_text()
        for line in result["report"].splitlines():
            if line.startswith("|"):
                self.assertIn(line, readme)


if __name__ == "__main__":
    unittest.main()

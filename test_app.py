import os
import sys
import unittest
import urllib.request
import json
import xml.etree.ElementTree as ET

# Add current dir to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import server


class TestBigQueryReleaseTracker(unittest.TestCase):

    def test_01_feed_url_reachable(self):
        """Test that the live XML feed from Google Cloud is reachable."""
        req = urllib.request.Request(
            server.FEED_URL,
            headers={"User-Agent": "BigQueryReleaseNotesTracker-Test/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            self.assertEqual(response.status, 200, "Feed URL should return HTTP 200")
            content = response.read()
            self.assertTrue(len(content) > 1000, "Feed should contain XML content")
            self.assertTrue(b"<feed" in content, "Feed content should have Atom <feed> tag")

    def test_02_feed_parsing(self):
        """Test that fetch_and_parse_feed accurately extracts structured entries and categories."""
        data, error = server.fetch_and_parse_feed(force_refresh=True)
        self.assertIsNone(error, f"Parsing should not produce errors: {error}")
        self.assertIsNotNone(data, "Parsed data should not be None")
        self.assertIn("title", data)
        self.assertIn("entries", data)
        self.assertGreater(data["total_entries"], 0, "Should contain at least 1 release entry")
        self.assertGreater(data["total_items"], 0, "Should contain at least 1 discrete update item")

        # Inspect first entry
        first_entry = data["entries"][0]
        self.assertIn("title", first_entry)
        self.assertIn("items", first_entry)
        self.assertGreater(len(first_entry["items"]), 0)

        # Inspect first item
        first_item = first_entry["items"][0]
        self.assertIn("id", first_item)
        self.assertIn("category", first_item)
        self.assertIn("plain_text", first_item)
        self.assertIn("link", first_item)
        self.assertTrue(len(first_item["plain_text"]) > 10, "Plain text should not be empty")

        print(f"\n[OK] Successfully parsed {data['total_entries']} entries and {data['total_items']} items.")
        print(f"     Latest release: {first_entry['title']} ({len(first_entry['items'])} items)")

    def test_03_frontend_files_exist(self):
        """Test that index.html, style.css, and app.js exist and contain critical IDs."""
        index_path = os.path.join(BASE_DIR, "templates", "index.html")
        css_path = os.path.join(BASE_DIR, "static", "css", "style.css")
        js_path = os.path.join(BASE_DIR, "static", "js", "app.js")

        self.assertTrue(os.path.exists(index_path), "templates/index.html must exist")
        self.assertTrue(os.path.exists(css_path), "static/css/style.css must exist")
        self.assertTrue(os.path.exists(js_path), "static/js/app.js must exist")

        with open(index_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            required_ids = [
                "refreshBtn", "refreshSpinner", "exportCsvBtn", "themeToggleBtn",
                "searchInput", "categoryFilters", "entriesList", "tweetModal",
                "tweetTextarea", "launchTweetBtn", "copyTweetBtn", "toast"
            ]
            for elem_id in required_ids:
                self.assertIn(elem_id, html_content, f"HTML must contain ID '{elem_id}'")

        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
            self.assertIn('[data-theme="light"]', css_content, "CSS must have light theme overrides")
            self.assertIn('.item-card', css_content, "CSS must style item cards")

        with open(js_path, "r", encoding="utf-8") as f:
            js_content = f.read()
            self.assertIn('exportToCsv', js_content, "JS must include exportToCsv function")
            self.assertIn('initTheme', js_content, "JS must include initTheme function")
            self.assertIn('openTweetModalForItem', js_content, "JS must include tweet modal opener")

        print("[OK] All frontend templates and static assets verified.")


if __name__ == "__main__":
    unittest.main(verbosity=2)

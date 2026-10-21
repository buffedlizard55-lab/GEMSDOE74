import json
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class SiteIndexParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.ids = set()
        self.title = False
        self.in_title = False
        self.title_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag in {"a", "link"} and "href" in attrs:
            self.links.append(attrs["href"])
        if tag == "script" and "src" in attrs:
            self.links.append(attrs["src"])
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title_text.append(data)


class StaticSiteTests(unittest.TestCase):
    def test_all_local_links_and_fragments_resolve(self):
        pages = sorted(DOCS.glob("*.html"))
        self.assertTrue(pages)
        indexes = {}
        for page in pages:
            parser = SiteIndexParser()
            parser.feed(page.read_text(encoding="utf-8"))
            parser.close()
            self.assertTrue("".join(parser.title_text).strip(), f"Missing title: {page}")
            indexes[page.resolve()] = parser

        for page, parser in indexes.items():
            for href in parser.links:
                if not href or href.startswith(("http://", "https://", "mailto:", "javascript:")):
                    continue
                parsed = urlsplit(href)
                target = (page.parent / parsed.path).resolve() if parsed.path else page
                self.assertTrue(target.is_file(), f"Broken local link {href!r} in {page.relative_to(ROOT)}")
                if parsed.fragment and target.suffix.lower() == ".html":
                    if target.resolve() in indexes:
                        target_parser = indexes[target.resolve()]
                    else:
                        target_parser = SiteIndexParser()
                        target_parser.feed(target.read_text(encoding="utf-8"))
                    self.assertIn(parsed.fragment, target_parser.ids, f"Broken fragment {href!r} in {page.relative_to(ROOT)}")

    def test_blocked_status_never_exposes_download(self):
        report = json.loads((DOCS / "data/readiness.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "BLOCKED")
        self.assertFalse(report["download_enabled"])
        self.assertIsNone(report["download_url"])
        home = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertIn("BLOCKED — NOT SUBMITTABLE", home)
        self.assertIn("Download disabled", home)
        self.assertFalse(list((DOCS / "downloads").glob("*.tif")) if (DOCS / "downloads").exists() else False)


if __name__ == "__main__":
    unittest.main()

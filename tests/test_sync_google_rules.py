import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from sync_google_rules import (normalize_google, parse_rules, is_google_ai_rule,
                               synchronize, SyncError, REQUIRED, MIN_RULES)
from sync_ai_rules import parse_payload, parse_text_rules

class GoogleSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "rules").mkdir()
        self.sources = [
            {"name": "Google", "url": "https://raw.githubusercontent.com/example/google/main/google.yaml"},
            {"name": "YouTube", "url": "https://raw.githubusercontent.com/example/google/main/youtube.yaml"},
        ]
        (self.root / "rules/google_sources.json").write_text(
            json.dumps({"sources": self.sources}), encoding="utf-8")
        # Build a fake strong baseline that includes all required domains.
        base = sorted(REQUIRED | {f"DOMAIN,service{i}.google.test" for i in range(MIN_RULES)})
        self.data = {
            self.sources[0]["url"]: "payload:\n" + "".join("  - " + r + "\n" for r in base) +
              "  - DOMAIN,gemini.google.com\n  - DOMAIN-SUFFIX,deepmind.com\n"
              "  - DOMAIN-KEYWORD,google\n  - PROCESS-NAME,GoogleDriveFS.exe\n",
            self.sources[1]["url"]: "payload:\n  - DOMAIN-SUFFIX,youtube.com\n"
                                        "  - IP-CIDR,203.0.113.0/24\n",
        }
    def run_sync(self):
        return synchronize(self.root, self.data.__getitem__)
    def test_deduplicate_exclude_ai_and_generate_formats(self):
        self.assertTrue(self.run_sync())
        cl = parse_payload((self.root / "Google_No_Resolve.yaml").read_text(), "Clash")
        su = parse_text_rules((self.root / "Surge/Google.list").read_text(), "Surge")
        self.assertEqual(cl, su)
        self.assertIn("DOMAIN-SUFFIX,youtube.com", cl)
        self.assertIn("DOMAIN-KEYWORD,google", cl)
        self.assertIn("IP-CIDR,203.0.113.0/24,no-resolve", cl)
        self.assertNotIn("DOMAIN,gemini.google.com", cl)
        self.assertNotIn("DOMAIN-SUFFIX,deepmind.com", cl)
        self.assertNotIn("PROCESS-NAME,GoogleDriveFS.exe", cl)
        self.assertFalse(self.run_sync())
    def test_failed_upstream_keeps_previous_files(self):
        self.run_sync()
        p = self.root / "Google_No_Resolve.yaml"
        old = p.read_bytes()
        self.data[self.sources[1]["url"]] = "payload: ["
        with self.assertRaises(Exception):
            self.run_sync()
        self.assertEqual(p.read_bytes(), old)
    def test_large_decrease_is_rejected(self):
        self.run_sync()
        p = self.root / "Google_No_Resolve.yaml"
        before = p.read_bytes()
        self.data[self.sources[0]["url"]] = "payload:\n" + "".join(
            "  - "+r+"\n" for r in sorted(REQUIRED)) + "".join(
            f"  - DOMAIN,new{i}.google.test\n" for i in range(710))
        # a smaller but still valid >700 replacement of the larger baseline
        # is allowed; a missing core entry is never allowed.
        self.data[self.sources[0]["url"]] = "payload:\n  - DOMAIN-SUFFIX,google.com\n"
        with self.assertRaises(SyncError):
            self.run_sync()
        self.assertEqual(p.read_bytes(), before)
    def test_filters(self):
        self.assertTrue(is_google_ai_rule("DOMAIN-SUFFIX,deepmind.com"))
        self.assertTrue(is_google_ai_rule("DOMAIN,gemini.google.com"))
        self.assertFalse(is_google_ai_rule("DOMAIN-SUFFIX,google.com"))
        self.assertIsNone(normalize_google("DOMAIN-REGEX,^video\\.google\\.com$"))
        self.assertEqual(normalize_google("IP-CIDR,203.0.113.1/32"),
                         "IP-CIDR,203.0.113.1/32,no-resolve")
        with self.assertRaises(SyncError):
            normalize_google("MATCH,DIRECT")
    def test_classical_rejects_unknown_rule(self):
        with self.assertRaises(SyncError):
            parse_rules("DOMAIN-SUFFIX,google.com\nMATCH,DIRECT", {"name":"Test","format":"classical-text"})

if __name__ == "__main__":
    unittest.main()

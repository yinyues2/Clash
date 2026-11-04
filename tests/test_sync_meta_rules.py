import json
from pathlib import Path
import tempfile
import unittest

from sync_meta_rules import (
    MIN_RULES, REQUIRED, SyncError, is_meta_ai_rule, normalize_meta,
    parse_rules, synchronize,
)
from sync_ai_rules import parse_payload, parse_text_rules


class MetaSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "rules").mkdir()
        self.sources = [
            {"name": "Facebook", "url": "https://raw.githubusercontent.com/example/meta/main/facebook.yaml"},
            {"name": "MetaGeosite", "url": "https://raw.githubusercontent.com/example/meta/main/meta.list",
             "format": "classical-text"},
        ]
        (self.root / "rules/meta_sources.json").write_text(
            json.dumps({"sources": self.sources}), encoding="utf-8")
        self.baseline = sorted(REQUIRED | {
            f"DOMAIN,service{i}.meta.test" for i in range(MIN_RULES + 200)
        })
        self.data = {
            self.sources[0]["url"]:
                "payload:\n" +
                "".join("  - " + rule + "\n" for rule in self.baseline) +
                "  - DOMAIN-SUFFIX,meta.ai\n"
                "  - DOMAIN-SUFFIX,llama.com\n"
                "  - DOMAIN,ai.meta.com\n"
                "  - DOMAIN-KEYWORD,facebook\n"
                "  - PROCESS-NAME,Messenger.exe\n"
                "  - IP-CIDR,203.0.113.99/24\n",
            self.sources[1]["url"]:
                "DOMAIN-SUFFIX,messenger.com\n"
                "DOMAIN-SUFFIX,threads.com\n",
        }

    def sync(self):
        return synchronize(self.root, self.data.__getitem__)

    def test_merges_deduplicates_and_excludes_ai(self):
        self.assertTrue(self.sync())
        clash = parse_payload((self.root / "Meta_No_Resolve.yaml").read_text(), "Clash")
        surge = parse_text_rules((self.root / "Surge/Meta.list").read_text(), "Surge")
        self.assertEqual(clash, surge)
        self.assertTrue(REQUIRED.issubset(clash))
        self.assertGreaterEqual(len(clash), MIN_RULES)
        self.assertIn("DOMAIN-KEYWORD,facebook", clash)
        self.assertIn("IP-CIDR,203.0.113.0/24,no-resolve", clash)
        for ai_rule in ("DOMAIN-SUFFIX,meta.ai", "DOMAIN-SUFFIX,llama.com",
                        "DOMAIN,ai.meta.com"):
            self.assertNotIn(ai_rule, clash)
        self.assertNotIn("PROCESS-NAME,Messenger.exe", clash)
        self.assertFalse(self.sync())

    def test_upstream_failure_preserves_last_good_version(self):
        self.sync()
        before = (self.root / "Meta_No_Resolve.yaml").read_bytes()
        self.data[self.sources[0]["url"]] = "payload: ["
        with self.assertRaises(Exception):
            self.sync()
        self.assertEqual(before, (self.root / "Meta_No_Resolve.yaml").read_bytes())

    def test_large_decrease_is_rejected(self):
        self.sync()
        before = (self.root / "Meta_No_Resolve.yaml").read_bytes()
        self.data[self.sources[0]["url"]] = "payload:\n" + "".join(
            "  - " + rule + "\n" for rule in
            sorted(REQUIRED | {f"DOMAIN,new{i}.meta.test" for i in range(MIN_RULES)})
        )
        with self.assertRaises(SyncError):
            self.sync()
        self.assertEqual(before, (self.root / "Meta_No_Resolve.yaml").read_bytes())

    def test_filter_validation(self):
        self.assertTrue(is_meta_ai_rule("DOMAIN-SUFFIX,meta.ai"))
        self.assertTrue(is_meta_ai_rule("DOMAIN-SUFFIX,sub.metaaiusercontent.com"))
        self.assertTrue(is_meta_ai_rule("DOMAIN,ai.meta.com"))
        self.assertFalse(is_meta_ai_rule("DOMAIN-SUFFIX,meta.com"))
        self.assertFalse(is_meta_ai_rule("DOMAIN-SUFFIX,atmeta.com"))
        self.assertIsNone(normalize_meta(r"DOMAIN-REGEX,^meta\.com$"))
        self.assertEqual(normalize_meta("IP-CIDR,203.0.113.9/24"),
                         "IP-CIDR,203.0.113.0/24,no-resolve")
        with self.assertRaises(SyncError):
            normalize_meta("MATCH,DIRECT")
        with self.assertRaises(SyncError):
            parse_rules("DOMAIN-SUFFIX,meta.com\nMATCH,DIRECT",
                        {"name": "Test", "format": "classical-text"})


if __name__ == "__main__":
    unittest.main()

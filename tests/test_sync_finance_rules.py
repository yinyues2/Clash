import json
from pathlib import Path
import tempfile
import unittest

from sync_ai_rules import SyncError, parse_payload, parse_text_rules
from sync_finance_rules import read_config, synchronize


class FinanceRulesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "rules").mkdir()
        real = Path(__file__).resolve().parents[1] / "rules/finance_sources.json"
        self.config = json.loads(real.read_text(encoding="utf-8"))
        (self.root / "rules/finance_sources.json").write_text(
            json.dumps(self.config), encoding="utf-8")
        self.responses = {}
        for source in self.config["sources"]:
            body = "DOMAIN-SUFFIX,bybit.com\nDOMAIN-SUFFIX,unrelated-bank.example\n"
            if source["format"] == "clash-yaml":
                body = "payload:\n  - DOMAIN-SUFFIX,bybit.com\n  - DOMAIN-SUFFIX,unrelated-bank.example\n  - PROCESS-NAME,Binance.exe\n"
            self.responses[source["url"]] = body

    def run_sync(self):
        return synchronize(self.root, self.responses.__getitem__)

    def test_whitelist_and_mirror(self):
        self.assertTrue(self.run_sync())
        a = parse_payload((self.root / "Finance_No_Resolve.yaml").read_text(), "Clash")
        b = parse_text_rules((self.root / "Surge/Finance.list").read_text(), "Surge")
        self.assertEqual(a, b)
        self.assertGreaterEqual(len(a), 28)
        self.assertIn("DOMAIN-SUFFIX,bybit.com", a)
        self.assertIn("DOMAIN-SUFFIX,redotpay.com", a)
        self.assertIn("DOMAIN-SUFFIX,kast.llc", a)
        self.assertNotIn("DOMAIN-SUFFIX,unrelated-bank.example", a)
        self.assertFalse(self.run_sync())

    def test_bad_upstream_keeps_previous_files(self):
        self.run_sync()
        before = (self.root / "Finance_No_Resolve.yaml").read_bytes()
        second = (self.root / "Surge/Finance.list").read_bytes()
        key = self.config["sources"][0]["url"]
        self.responses[key] = "MATCH,DIRECT"
        with self.assertRaises(SyncError):
            self.run_sync()
        self.assertEqual(before, (self.root / "Finance_No_Resolve.yaml").read_bytes())
        self.assertEqual(second, (self.root / "Surge/Finance.list").read_bytes())

    def test_per_source_shrink_guard(self):
        key = self.config["sources"][0]["url"]
        self.responses[key] = "\n".join(
            f"DOMAIN,api{i}.bybit.com" for i in range(20)) + "\n"
        self.run_sync()
        self.responses[key] = "DOMAIN-SUFFIX,bybit.com\n"
        with self.assertRaises(SyncError):
            self.run_sync()

    def test_manifest_rejects_duplicate_roots(self):
        doc = self.config
        doc["services"][1]["roots"][0] = doc["services"][0]["roots"][0]
        (self.root / "rules/finance_sources.json").write_text(json.dumps(doc))
        with self.assertRaises(SyncError):
            read_config(self.root)


if __name__ == "__main__":
    unittest.main()

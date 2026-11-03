import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location('sync_ai_rules', Path(__file__).resolve().parents[1] / 'scripts/sync_ai_rules.py')
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'rules').mkdir()
        self.sources = [{'name': name, 'url': f'https://example.test/{name}.yaml'} for name in ('OpenAI', 'Claude', 'Gemini', 'Copilot')]
        (self.root / 'rules/ai_sources.json').write_text(json.dumps({'sources': self.sources}))
        self.custom = self.root / 'rules/ai_custom.yaml'
        self.custom.write_text('payload:\n  - DOMAIN-SUFFIX,grok.com\n  - IP-ASN,20473\n')
        self.data = {source['url']: f'payload:\n  - DOMAIN,{source["name"].lower()}.example\n' for source in self.sources}
        self.output = self.root / 'AI_No_Resolve.yaml'

    def run_sync(self, **kwargs):
        return sync.synchronize(self.root, self.data.__getitem__, **kwargs)

    def payload(self):
        return sync.parse_payload(self.output.read_text(), 'test output')

    def test_merge_dedup_and_manual_preservation(self):
        for url in self.data:
            self.data[url] += '  - DOMAIN-SUFFIX,grok.com\n  - IP-ASN,20473,no-resolve\n'
        custom_before = self.custom.read_bytes()
        self.run_sync()
        self.assertEqual(len(self.payload()), 6)
        self.assertIn('IP-ASN,20473,no-resolve', self.payload())
        self.assertEqual(custom_before, self.custom.read_bytes())

    def test_upstream_addition_and_removal(self):
        self.run_sync()
        self.data[self.sources[0]['url']] = 'payload:\n  - DOMAIN,new.example\n'
        self.run_sync()
        self.assertIn('DOMAIN,new.example', self.payload())
        self.assertNotIn('DOMAIN,openai.example', self.payload())
        self.assertIn('DOMAIN-SUFFIX,grok.com', self.payload())

    def test_failures_leave_output_unchanged(self):
        self.run_sync()
        original = self.output.read_bytes()
        url = self.sources[0]['url']
        bad_documents = [
            '<html>rate limited</html>', 'payload: [', 'rules: []', 'payload: []',
            'payload: [123]', 'payload: [DOMAIN,x]\npayload: []',
            'payload:\n  - DOMAIN-SUFFIX,example.com,DIRECT\n',
            'payload:\n  - DOMAIN-REGEX,[\n',
        ]
        for bad in bad_documents:
            with self.subTest(document=bad):
                self.data[url] = bad
                with self.assertRaises(sync.SyncError):
                    self.run_sync()
                self.assertEqual(original, self.output.read_bytes())
        def offline(_url):
            raise sync.SyncError('network unavailable')
        with self.assertRaises(sync.SyncError):
            sync.synchronize(self.root, offline)
        self.assertEqual(original, self.output.read_bytes())

    def test_rule_validation(self):
        self.assertEqual(sync.normalize_rule(' IP-CIDR, 1.2.3.4/32 '), 'IP-CIDR,1.2.3.4/32,no-resolve')
        self.assertEqual(sync.normalize_rule('IP-CIDR6,2001:db8::1/128,no-resolve'), 'IP-CIDR6,2001:db8::1/128,no-resolve')
        self.assertEqual(sync.normalize_rule('IP-ASN,20473,no-resolve'), 'IP-ASN,20473,no-resolve')
        for bad in ['MATCH,DIRECT', 'DOMAIN,example.com,Final', 'IP-CIDR,no-ip', 'IP-CIDR6,1.2.3.4/32', 'IP-ASN,0', 'IP-ASN,4294967296', 'DOMAIN,x\nDOMAIN,y', 'IP-ASN,20473,no-resolve,no-resolve', 'DOMAIN-REGEX,[']:
            with self.subTest(rule=bad), self.assertRaises(sync.SyncError):
                sync.normalize_rule(bad)

    def test_stable_output_and_no_rewrite(self):
        url = self.sources[0]['url']
        self.data[url] += '  - DOMAIN,z.example\n  - DOMAIN,a.example\n'
        self.assertTrue(self.run_sync())
        original = self.output.read_bytes()
        modified = self.output.stat().st_mtime_ns
        self.data[url] = 'payload:\n  - DOMAIN,a.example\n  - DOMAIN,z.example\n  - DOMAIN,openai.example\n'
        self.assertFalse(self.run_sync())
        self.assertEqual(original, self.output.read_bytes())
        self.assertEqual(modified, self.output.stat().st_mtime_ns)

    def test_large_removal_requires_explicit_override(self):
        url = self.sources[0]['url']
        self.data[url] = 'payload:\n' + ''.join(f'  - DOMAIN,host{i}.example\n' for i in range(30))
        self.run_sync()
        original = self.output.read_bytes()
        self.data[url] = 'payload:\n  - DOMAIN,remaining.example\n'
        with self.assertRaises(sync.SyncError):
            self.run_sync()
        self.assertEqual(original, self.output.read_bytes())
        self.assertTrue(self.run_sync(allow_large_removal=True))
        self.assertIn('DOMAIN-SUFFIX,grok.com', self.payload())


if __name__ == '__main__':
    unittest.main()

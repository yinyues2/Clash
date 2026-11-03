import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

import yaml


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
        self.manifest = self.root / 'rules/ai_sources.json'
        self.write_manifest()
        self.custom = self.root / 'rules/ai_custom.yaml'
        self.custom.write_text('payload:\n  - DOMAIN-SUFFIX,grok.com\n  - IP-ASN,20473\n', encoding='utf-8')
        self.data = {source['url']: f'payload:\n  - DOMAIN,{source["name"].lower()}.example\n' for source in self.sources}
        self.output = self.root / 'AI_No_Resolve.yaml'
        self.surge_output = self.root / 'Surge/AI.list'
        self.outputs = (self.output, self.surge_output)

    def write_manifest(self):
        self.manifest.write_text(json.dumps({'sources': self.sources}), encoding='utf-8')

    def run_sync(self, **kwargs):
        return sync.synchronize(self.root, self.data.__getitem__, **kwargs)

    def payload(self):
        return yaml.safe_load(self.output.read_text(encoding='utf-8'))['payload']

    def surge_payload(self):
        return [line.strip() for line in self.surge_output.read_text(encoding='utf-8').splitlines()
                if line.strip() and not line.lstrip().startswith(('#', '//', ';'))]

    def read_outputs(self):
        return {path: path.read_bytes() for path in self.outputs}

    def assert_both_contain(self, expected):
        self.assertCountEqual(self.payload(), expected)
        self.assertCountEqual(self.surge_payload(), expected)

    def assert_outputs_unchanged(self, original):
        self.assertEqual(original, self.read_outputs())

    def test_merge_dedup_and_manual_preservation(self):
        for url in self.data:
            self.data[url] += '  - DOMAIN-SUFFIX,grok.com\n  - IP-ASN,20473,no-resolve\n'
        custom_before = self.custom.read_bytes()
        self.run_sync()
        expected = {f'DOMAIN,{source["name"].lower()}.example' for source in self.sources}
        expected.update({'DOMAIN-SUFFIX,grok.com', 'IP-ASN,20473,no-resolve'})
        self.assert_both_contain(expected)
        self.assertEqual(custom_before, self.custom.read_bytes())

    def test_upstream_addition_and_removal(self):
        self.run_sync()
        self.data[self.sources[0]['url']] = 'payload:\n  - DOMAIN,new.example\n'
        self.run_sync()
        for payload in (self.payload(), self.surge_payload()):
            self.assertIn('DOMAIN,new.example', payload)
            self.assertNotIn('DOMAIN,openai.example', payload)
            self.assertIn('DOMAIN-SUFFIX,grok.com', payload)

    def test_dual_formats_preserve_ipv4_ipv6_and_asn_without_yaml_in_surge(self):
        self.data[self.sources[0]['url']] += (
            '  - IP-CIDR,203.0.113.0/24\n'
            '  - IP-CIDR6,2001:db8::/32,no-resolve\n'
        )
        self.run_sync()
        expected = {f'DOMAIN,{source["name"].lower()}.example' for source in self.sources}
        expected.update({
            'DOMAIN-SUFFIX,grok.com', 'IP-ASN,20473,no-resolve',
            'IP-CIDR,203.0.113.0/24,no-resolve',
            'IP-CIDR6,2001:db8::/32,no-resolve',
        })
        self.assert_both_contain(expected)
        surge = self.surge_output.read_text(encoding='utf-8')
        self.assertNotIn('payload:', surge)
        self.assertFalse(any(line.lstrip().startswith('- ') for line in surge.splitlines()))
        for line in self.surge_payload():
            if line.startswith(('IP-CIDR,', 'IP-CIDR6,', 'IP-ASN,')):
                self.assertEqual(line.count(',no-resolve'), 1)
            else:
                self.assertEqual(len(line.split(',')), 2)

    def test_classical_text_accepts_comments_bom_and_duplicate_rules(self):
        text = (
            '\ufeff# Source header\r\n'
            '\r\n  // Another comment\r\n; Comment\r\n'
            'DOMAIN,api.example\r\n'
            ' DOMAIN-SUFFIX,example.com \r\n'
            'DOMAIN-KEYWORD,assistant\r\n'
            'IP-CIDR,198.51.100.7/32\r\n'
            'IP-CIDR6,2001:db8::1/128\r\n'
            'IP-ASN,20473,no-resolve\r\n'
            'DOMAIN,api.example\r\n'
        )
        self.assertCountEqual(sync.parse_text_rules(text, 'text source'), [
            'DOMAIN,api.example', 'DOMAIN-SUFFIX,example.com',
            'DOMAIN-KEYWORD,assistant',
            'IP-CIDR,198.51.100.7/32,no-resolve',
            'IP-CIDR6,2001:db8::1/128,no-resolve',
            'IP-ASN,20473,no-resolve',
        ])

    def test_mixed_yaml_and_classical_sources_use_the_same_output_rules(self):
        self.sources[1]['format'] = 'clash-yaml'
        self.sources[2]['format'] = 'classical-text'
        self.sources[3]['format'] = 'classical-text'
        self.write_manifest()
        self.data[self.sources[0]['url']] = (
            'payload:\n  - DOMAIN,api.openai.example\n'
            '  - DOMAIN-SUFFIX,shared.example\n'
        )
        self.data[self.sources[2]['url']] = (
            '# A text source\nDOMAIN-SUFFIX,shared.example\n'
            'DOMAIN-KEYWORD,gemini\n'
        )
        self.data[self.sources[3]['url']] = (
            'DOMAIN-SUFFIX,copilot.example\nDOMAIN,api.copilot.example\n'
        )
        custom_before = self.custom.read_bytes()
        self.run_sync()
        self.assert_both_contain({
            'DOMAIN,api.openai.example', 'DOMAIN-SUFFIX,shared.example',
            'DOMAIN,claude.example', 'DOMAIN-KEYWORD,gemini',
            'DOMAIN-SUFFIX,copilot.example', 'DOMAIN,api.copilot.example',
            'DOMAIN-SUFFIX,grok.com', 'IP-ASN,20473,no-resolve',
        })
        self.assertEqual(custom_before, self.custom.read_bytes())

    def test_yaml_and_download_failures_leave_both_outputs_unchanged(self):
        self.run_sync()
        original = self.read_outputs()
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
                self.assert_outputs_unchanged(original)
        def offline(_url):
            raise sync.SyncError('network unavailable')
        with self.assertRaises(sync.SyncError):
            sync.synchronize(self.root, offline)
        self.assert_outputs_unchanged(original)

    def test_invalid_classical_text_is_not_silently_skipped(self):
        self.run_sync()
        original = self.read_outputs()
        self.sources[0]['format'] = 'classical-text'
        self.write_manifest()
        url = self.sources[0]['url']
        bad_documents = [
            '', '# Comment only\n// More comments\n; Nothing here\n',
            'URL-REGEX,^https://example.com/ai\n',
            'DOMAIN-WILDCARD,*.example.com\n',
            'DOMAIN-SUFFIX,*.example.com\n',
            'DOMAIN,example.com,AI\n',
            'DOMAIN,example.com,extended-matching\n',
            'DOMAIN,\n', 'IP-CIDR,not-an-address\n',
            'FINAL,AI\n', 'example.com\n',
            'payload:\n  - DOMAIN,example.com\n',
            'DOMAIN,valid.example\nURL-REGEX,[\n',
        ]
        for bad in bad_documents:
            with self.subTest(document=bad):
                self.data[url] = bad
                with self.assertRaises(sync.SyncError):
                    self.run_sync()
                self.assert_outputs_unchanged(original)

    def test_invalid_or_missing_custom_rules_leave_both_outputs_unchanged(self):
        self.run_sync()
        original = self.read_outputs()
        for bad in ('payload: [', 'payload: [123]', 'payload:\n  - MATCH,DIRECT\n'):
            with self.subTest(document=bad):
                self.custom.write_text(bad, encoding='utf-8')
                with self.assertRaises(sync.SyncError):
                    self.run_sync()
                self.assert_outputs_unchanged(original)
        self.custom.unlink()
        with self.assertRaises(OSError):
            self.run_sync()
        self.assert_outputs_unchanged(original)

    def test_unknown_source_format_leaves_both_outputs_unchanged(self):
        self.run_sync()
        original = self.read_outputs()
        self.sources[0]['format'] = 'unknown-format'
        self.write_manifest()
        with self.assertRaises(sync.SyncError):
            self.run_sync()
        self.assert_outputs_unchanged(original)

    def test_rule_validation(self):
        self.assertEqual(sync.normalize_rule(' IP-CIDR, 1.2.3.4/32 '), 'IP-CIDR,1.2.3.4/32,no-resolve')
        self.assertEqual(sync.normalize_rule('IP-CIDR6,2001:db8::1/128,no-resolve'), 'IP-CIDR6,2001:db8::1/128,no-resolve')
        self.assertEqual(sync.normalize_rule('IP-ASN,20473,no-resolve'), 'IP-ASN,20473,no-resolve')
        for bad in ['MATCH,DIRECT', 'DOMAIN,example.com,Final', 'IP-CIDR,no-ip', 'IP-CIDR6,1.2.3.4/32', 'IP-ASN,0', 'IP-ASN,4294967296', 'DOMAIN,x\nDOMAIN,y', 'IP-ASN,20473,no-resolve,no-resolve', 'DOMAIN-REGEX,[']:
            with self.subTest(rule=bad), self.assertRaises(sync.SyncError):
                sync.normalize_rule(bad)

    def test_stable_output_and_no_rewrite_in_both_formats(self):
        url = self.sources[0]['url']
        self.data[url] += '  - DOMAIN,z.example\n  - DOMAIN,a.example\n'
        self.assertTrue(self.run_sync())
        original = self.read_outputs()
        for path in self.outputs:
            os.utime(path, ns=(1600000000000000000, 1600000000000000000))
        modified = {path: path.stat().st_mtime_ns for path in self.outputs}
        self.data[url] = 'payload:\n  - DOMAIN,a.example\n  - DOMAIN,z.example\n  - DOMAIN,openai.example\n'
        self.assertFalse(self.run_sync())
        self.assert_outputs_unchanged(original)
        self.assertEqual(modified, {path: path.stat().st_mtime_ns for path in self.outputs})

    def test_large_removal_requires_explicit_override(self):
        url = self.sources[0]['url']
        self.data[url] = 'payload:\n' + ''.join(f'  - DOMAIN,host{i}.example\n' for i in range(30))
        self.run_sync()
        original = self.read_outputs()
        self.data[url] = 'payload:\n  - DOMAIN,remaining.example\n'
        with self.assertRaises(sync.SyncError):
            self.run_sync()
        self.assert_outputs_unchanged(original)
        self.assertTrue(self.run_sync(allow_large_removal=True))
        for payload in (self.payload(), self.surge_payload()):
            self.assertIn('DOMAIN-SUFFIX,grok.com', payload)
            self.assertIn('DOMAIN,remaining.example', payload)

    def test_one_source_shrinking_is_not_hidden_by_large_other_sources(self):
        self.data[self.sources[0]['url']] = 'payload:\n' + ''.join(
            f'  - DOMAIN,openai{i}.example\n' for i in range(30))
        self.data[self.sources[1]['url']] = 'payload:\n' + ''.join(
            f'  - DOMAIN,claude{i}.example\n' for i in range(150))
        self.run_sync()
        original = self.read_outputs()
        self.data[self.sources[0]['url']] = 'payload:\n  - DOMAIN,openai0.example\n'
        with self.assertRaises(sync.SyncError):
            self.run_sync()
        self.assert_outputs_unchanged(original)

    def test_missing_or_corrupt_surge_output_is_repaired_without_rewriting_clash(self):
        self.run_sync()
        original = self.read_outputs()
        os.utime(self.output, ns=(1600000000000000000, 1600000000000000000))
        modified = self.output.stat().st_mtime_ns
        for corrupt in (None, b'payload: [broken\n', b'\xff\xfeinvalid-utf8\n'):
            with self.subTest(corrupt=corrupt):
                if corrupt is None:
                    self.surge_output.unlink()
                else:
                    self.surge_output.write_bytes(corrupt)
                self.assertTrue(self.run_sync())
                self.assert_outputs_unchanged(original)
                self.assertEqual(modified, self.output.stat().st_mtime_ns)


if __name__ == '__main__':
    unittest.main()

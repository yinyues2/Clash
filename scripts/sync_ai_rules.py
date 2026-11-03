#!/usr/bin/env python3
"""Combine explicit AI rule sources without replacing a good file on failure."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

import yaml


ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 2 * 1024 * 1024
MAX_RULES = 20000
TEXT_RULES = {'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD'}
IP_RULES = {'IP-CIDR', 'IP-CIDR6', 'IP-ASN'}
COUNTS_PREFIX = '# Source-Counts: '


class SyncError(ValueError):
    """Invalid input or an update requiring review."""


class UniqueLoader(yaml.SafeLoader):
    pass


def _unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise SyncError('YAML keys must be unique strings')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def normalize_rule(rule):
    if not isinstance(rule, str) or any(ord(c) < 32 for c in rule):
        raise SyncError('Every rule must be a single-line string')
    parts = [part.strip() for part in rule.split(',')]
    if len(parts) < 2 or not parts[1]:
        raise SyncError(f'Invalid rule: {rule!r}')
    kind, value = parts[:2]
    if kind in IP_RULES:
        if len(parts) > 3 or (len(parts) == 3 and parts[2] != 'no-resolve'):
            raise SyncError(f'Unexpected IP rule parameter: {rule!r}')
        try:
            if kind == 'IP-ASN':
                if not value.isascii() or not value.isdecimal() or not 1 <= int(value) <= 4294967295:
                    raise ValueError('ASN out of range')
                value = str(int(value))
            else:
                network = ipaddress.ip_network(value, strict=False)
                if network.version != (6 if kind == 'IP-CIDR6' else 4):
                    raise ValueError('IP family does not match rule type')
                value = str(network)
        except ValueError as error:
            raise SyncError(f'Invalid IP/ASN rule: {rule!r}') from error
        return f'{kind},{value},no-resolve'
    if kind not in TEXT_RULES or len(parts) != 2:
        raise SyncError(f'Unsupported or malformed classical rule: {rule!r}')
    if kind in {'DOMAIN', 'DOMAIN-SUFFIX'}:
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', value) or not any(c.isalnum() for c in value):
            raise SyncError(f'Invalid domain: {value!r}')
    return f'{kind},{value}'


def parse_payload(text, label, allow_empty=False):
    if len(text.encode('utf-8')) > MAX_BYTES:
        raise SyncError(f'{label}: file is too large')
    try:
        document = yaml.load(text, Loader=UniqueLoader)
    except yaml.YAMLError as error:
        raise SyncError(f'{label}: invalid YAML') from error
    if not isinstance(document, dict) or set(document) != {'payload'}:
        raise SyncError(f'{label}: expected only a payload mapping')
    payload = document['payload']
    if not isinstance(payload, list) or (not payload and not allow_empty):
        raise SyncError(f'{label}: expected a nonempty payload list')
    if len(payload) > MAX_RULES:
        raise SyncError(f'{label}: unexpected rule count')
    return sorted({normalize_rule(rule) for rule in payload})


def fetch_text(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise SyncError('Rule source URLs must use HTTPS without credentials')
    request = urllib.request.Request(url, headers={
        'User-Agent': 'Clash-AI-Rules-Sync/1.0', 'Accept': 'text/plain',
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                if urllib.parse.urlsplit(response.url).scheme != 'https':
                    raise SyncError('Refusing a non-HTTPS redirect')
                data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise SyncError(f'Source exceeds {MAX_BYTES} bytes: {url}')
            return data.decode('utf-8-sig')
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            if attempt == 2:
                raise SyncError(f'Unable to download {url}: {error}') from error
            time.sleep(attempt + 1)
        except UnicodeDecodeError as error:
            raise SyncError(f'Source is not UTF-8: {url}') from error


def load_sources(path):
    try:
        config = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError) as error:
        raise SyncError(f'Unable to read source configuration: {path}') from error
    if not isinstance(config, dict) or set(config) != {'sources'}:
        raise SyncError('Source configuration must contain only sources')
    sources = config['sources']
    if not isinstance(sources, list) or not 1 <= len(sources) <= 20:
        raise SyncError('Expected 1 to 20 explicitly configured sources')
    names, urls = set(), set()
    for source in sources:
        if not isinstance(source, dict) or set(source) != {'name', 'url'}:
            raise SyncError('Each source needs name and url')
        name, url = source['name'], source['url']
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', name):
            raise SyncError('Invalid source name')
        if not isinstance(url, str):
            raise SyncError('Source URL must be a string')
        if name == 'Custom' or name in names or url in urls:
            raise SyncError('Source names and URLs must be unique')
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or '\n' in url:
            raise SyncError('Rule source URLs must use HTTPS without credentials')
        names.add(name)
        urls.add(url)
    return sources


def render(groups, sources):
    counts = {name: len(rules) for name, rules in groups if name != 'Custom'}
    lines = [
        '# Generated by scripts/sync_ai_rules.py; do not edit this output directly.',
        '# Manual additions: rules/ai_custom.yaml; upstream list: rules/ai_sources.json.',
        COUNTS_PREFIX + json.dumps(counts, sort_keys=True, separators=(',', ':')),
        'payload:',
    ]
    urls = {source['name']: source['url'] for source in sources}
    seen = set()
    for name, rules in groups:
        unique = [rule for rule in sorted(rules) if rule not in seen]
        if not unique:
            continue
        lines.append(f'  # NAME: {name}')
        if name in urls:
            lines.append(f'  # SOURCE: {urls[name]}')
        for rule in unique:
            scalar = yaml.safe_dump(rule, allow_unicode=True, width=100000).rstrip().removesuffix('\n...')
            lines.append('  - ' + scalar)
            seen.add(rule)
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def check_removals(previous, current, groups, allow_large_removal):
    if not previous or allow_large_removal:
        return
    old_rules = parse_payload(previous, 'previous output')
    new_rules = parse_payload(current, 'generated output')
    if len(new_rules) < len(old_rules) * 0.8:
        raise SyncError('Rule count fell by more than 20%; review before using --allow-large-removal')
    old_counts = {}
    for line in previous.splitlines():
        if line.startswith(COUNTS_PREFIX):
            old_counts = json.loads(line[len(COUNTS_PREFIX):])
            if not isinstance(old_counts, dict):
                raise SyncError('Invalid previous source counts')
    for name, rules in groups:
        old_count = old_counts.get(name)
        if isinstance(old_count, int) and old_count - len(rules) >= 10 and len(rules) < old_count * 0.75:
            raise SyncError(f'{name} shrank substantially; review before using --allow-large-removal')


def synchronize(root=ROOT, fetcher=fetch_text, allow_large_removal=False):
    root = Path(root)
    output = root / 'AI_No_Resolve.yaml'
    sources = load_sources(root / 'rules/ai_sources.json')
    # Collect every source before touching the output. Any failed source aborts.
    with ThreadPoolExecutor(max_workers=min(4, len(sources))) as pool:
        texts = list(pool.map(fetcher, [source['url'] for source in sources]))
    groups = [(source['name'], parse_payload(text, source['name'])) for source, text in zip(sources, texts)]
    custom_path = root / 'rules/ai_custom.yaml'
    groups.append(('Custom', parse_payload(custom_path.read_text(encoding='utf-8'), 'custom rules', allow_empty=True)))
    current = render(groups, sources)
    unique_count = len(parse_payload(current, 'generated output'))
    previous = output.read_text(encoding='utf-8') if output.exists() else ''
    check_removals(previous, current, groups, allow_large_removal)
    if previous == current:
        print(f'Unchanged: {unique_count} unique rules')
        return False
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n', dir=root, prefix='.ai-rules-', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(current)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o644)
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f'Updated: {unique_count} unique rules; {len(sources)} upstreams and custom rules')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument('--source-dir', type=Path, help='Use already downloaded <source-name>.yaml files for an offline check')
    parser.add_argument('--allow-large-removal', action='store_true', help='Accept a reviewed large upstream removal')
    args = parser.parse_args()
    fetcher = fetch_text
    if args.source_dir:
        sources = load_sources(args.root / 'rules/ai_sources.json')
        snapshots = {source['url']: args.source_dir / (source['name'] + '.yaml') for source in sources}
        fetcher = lambda url: snapshots[url].read_text(encoding='utf-8')
    try:
        synchronize(args.root, fetcher, args.allow_large_removal)
    except (SyncError, OSError, ValueError) as error:
        print(f'Sync failed; previous output preserved: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

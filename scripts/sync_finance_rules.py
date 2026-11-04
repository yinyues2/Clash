#!/usr/bin/env python3
"""Merge audited finance domains and reviewed upstreams into Clash and Surge rules."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import sys
import tempfile

import yaml
from sync_ai_rules import SyncError, fetch_text, normalize_rule, parse_payload, parse_text_rules

ROOT = Path(__file__).resolve().parents[1]
MIN_RULES = 27
MAX_BYTES = 2 * 1024 * 1024
MAX_SOURCES = 20
ALLOWED = {"DOMAIN", "DOMAIN-SUFFIX"}
COUNTS_PREFIX = "# Source-Counts: "


def read_config(root):
    doc = json.loads((Path(root) / "rules/finance_sources.json").read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or set(doc) != {"services", "sources"}:
        raise SyncError("Finance manifest must contain services and sources")
    services, sources = doc["services"], doc["sources"]
    if not isinstance(services, list) or not 20 <= len(services) <= 60:
        raise SyncError("Unexpected service list")
    if not isinstance(sources, list) or not 1 <= len(sources) <= MAX_SOURCES:
        raise SyncError("Unexpected source list")
    names, roots = set(), set()
    for item in services:
        if not isinstance(item, dict) or set(item) != {"name", "roots"}:
            raise SyncError("Invalid finance service")
        name, domains = item["name"], item["roots"]
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name) or name in names:
            raise SyncError("Duplicate or malformed finance service")
        if not isinstance(domains, list) or not 1 <= len(domains) <= 30:
            raise SyncError("Invalid domain whitelist")
        for domain in domains:
            if not isinstance(domain, str) or not re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)*", domain) or "." not in domain or domain in roots:
                raise SyncError(f"Invalid or reused finance domain: {domain!r}")
            roots.add(domain)
        names.add(name)
    seen_urls, source_names = set(), set()
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"name", "url", "format"}:
            raise SyncError("Invalid finance source")
        name, url, kind = source["name"], source["url"], source["format"]
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name) or name in source_names:
            raise SyncError("Duplicate source name")
        if not isinstance(url, str) or not url.startswith("https://raw.githubusercontent.com/") or url in seen_urls:
            raise SyncError("Source must be unique HTTPS raw GitHub URL")
        if not isinstance(kind, str) or kind not in {"classical-text", "clash-yaml"}:
            raise SyncError("Unsupported finance source format")
        seen_urls.add(url)
        source_names.add(name)
    return services, sources


def parse_source(text, source):
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_BYTES:
        raise SyncError(f"{source['name']}: empty or oversized source")
    if source["format"] == "clash-yaml":
        document = yaml.safe_load(text)
        if not isinstance(document, dict) or set(document) != {"payload"} or not isinstance(document["payload"], list):
            raise SyncError(f"{source['name']}: invalid payload")
        raw = document["payload"]
    else:
        raw = [line.strip() for line in text.lstrip("\ufeff").splitlines()
               if line.strip() and not line.lstrip().startswith(("#", ";", "//"))]
    if len(raw) > 20000:
        raise SyncError(f"{source['name']}: too many rules")
    rules = []
    for item in raw:
        if not isinstance(item, str):
            raise SyncError(f"{source['name']}: invalid rule item")
        kind = item.split(",", 1)[0].strip()
        if kind in ALLOWED:
            rule = normalize_rule(item).lower()
            rules.append(rule.upper().split(",", 1)[0] + "," + rule.split(",", 1)[1])
        elif kind not in {"DOMAIN-KEYWORD", "DOMAIN-REGEX", "PROCESS-NAME", "IP-CIDR", "IP-CIDR6", "IP-ASN"}:
            raise SyncError(f"{source['name']}: unrecognized rule type {kind!r}")
    if not rules:
        raise SyncError(f"{source['name']}: no usable domain rules")
    return sorted(set(rules))


def allowed_domain(rule, roots):
    kind, value = rule.split(",", 1)
    return kind in ALLOWED and any(value == root or value.endswith("." + root) for root in roots)


def compose(services, sources, fetched):
    roots = {root for item in services for root in item["roots"]}
    selected = []
    counts = {}
    for source, text in zip(sources, fetched):
        items = [rule for rule in parse_source(text, source) if allowed_domain(rule, roots)]
        rules = sorted(set(items))
        if not rules:
            raise SyncError(f"{source['name']}: no reviewed domains; refusing partial update")
        counts[source["name"]] = len(rules)
        selected.extend(rules)
    selected = set(selected)
    groups = []
    for service in services:
        domains = service["roots"]
        picked = {"DOMAIN-SUFFIX," + domains[0]}
        picked.update(rule for rule in selected if allowed_domain(rule, domains))
        groups.append((service["name"], sorted(picked)))
    return groups, counts


def render(groups, counts, surge=False):
    lines = [
        "# Generated by scripts/sync_finance_rules.py; do not edit directly.",
        "# Scope: selected exchanges, wallets and cross-border payment platforms.",
        "# Whitelist / upstreams: rules/finance_sources.json; attribution: README_FINANCE_SYNC.md.",
        COUNTS_PREFIX + json.dumps(counts, sort_keys=True, separators=(",", ":")),
    ]
    if not surge:
        lines.append("payload:")
    prefix = "" if surge else "  "
    seen = set()
    for name, rules in groups:
        new = [rule for rule in rules if rule not in seen]
        if not new:
            continue
        lines.append(prefix + "# SERVICE: " + name)
        for rule in new:
            lines.append(rule if surge else "  - " + rule)
            seen.add(rule)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def synchronize(root=ROOT, fetcher=fetch_text):
    root = Path(root)
    services, sources = read_config(root)
    with ThreadPoolExecutor(max_workers=min(6, len(sources))) as pool:
        fetched = list(pool.map(fetcher, [source["url"] for source in sources]))
    groups, counts = compose(services, sources, fetched)
    clash = render(groups, counts)
    surge = render(groups, counts, surge=True)
    current = parse_payload(clash, "Finance Clash")
    if len(current) < MIN_RULES or current != parse_text_rules(surge, "Finance Surge"):
        raise SyncError("Finance outputs too small or different")
    for service in services:
        if "DOMAIN-SUFFIX," + service["roots"][0] not in current:
            raise SyncError(f"Missing primary domain for {service['name']}")
    output = root / "Finance_No_Resolve.yaml"
    other = root / "Surge/Finance.list"
    if output.exists():
        previous_text = output.read_text(encoding="utf-8")
        previous = parse_payload(previous_text, "Previous Finance")
        if len(current) < len(previous) * 0.8:
            raise SyncError("Finance rules shrank more than 20%; manual review required")
        old_counts = {}
        for line in previous_text.splitlines():
            if line.startswith(COUNTS_PREFIX):
                old_counts = json.loads(line[len(COUNTS_PREFIX):])
        for name, count in counts.items():
            old = old_counts.get(name)
            if isinstance(old, int) and old >= 8 and count < old * 0.75:
                raise SyncError(f"{name} source shrank more than 25%; manual review required")
    changes = [(path, content) for path, content in ((output, clash), (other, surge))
               if not path.exists() or path.read_text(encoding="utf-8") != content]
    if not changes:
        print(f"Unchanged: {len(current)} finance rules from {len(sources)} sources")
        return False
    staged = []
    try:
        for path, content in changes:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                             dir=path.parent, prefix=".finance-sync-", delete=False) as handle:
                temp = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            temp.chmod(0o644)
            staged.append((path, temp))
        for path, temp in staged:
            os.replace(temp, path)
    finally:
        for _, temp in staged:
            temp.unlink(missing_ok=True)
    print(f"Updated: {len(current)} finance rules from {len(sources)} sources")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    arguments = parser.parse_args()
    try:
        synchronize(arguments.root)
    except (OSError, ValueError, yaml.YAMLError, SyncError) as error:
        print(f"Finance sync failed; published rules unchanged: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

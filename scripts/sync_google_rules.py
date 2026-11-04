#!/usr/bin/env python3
"""Synchronize non-AI Google family rules into one Clash and one Surge list."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import tempfile

# Reuse the already tested AI-sync downloader and strict validation primitives.
from sync_ai_rules import fetch_text, normalize_rule, SyncError, parse_payload, parse_text_rules

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_TYPES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD",
                 "IP-CIDR", "IP-CIDR6", "IP-ASN"}
# Exact standalone Google AI properties; AI subdomains under shared google.com
# are handled by the earlier AI policy rather than excluding all Google traffic.
AI_SUFFIXES = {
    "deepmind.com", "tensorflow.org", "dialogflow.com", "api.ai",
    "gemini.google", "generativeai.google", "ai.google.dev",
    "aistudio.google.com", "gemini.google.com", "bard.google.com",
    "makersuite.google.com", "flow.google", "flow.google.com",
    "jules.google", "jules.google.com", "antigravity.google",
    "antigravity-unleash.goog", "ai.studio", "notebooklm.google.com",
    "opal.google", "stitch.withgoogle.com",
}
AI_EXACT = {
    "aida.googleapis.com", "generativelanguage.googleapis.com",
    "cloudaicompanion.googleapis.com", "cloudcode-pa.googleapis.com",
    "daily-cloudcode-pa.googleapis.com", "antigravity-pa.googleapis.com",
    "antigravity.googleapis.com", "notebooklm-pa.googleapis.com",
    "notebooklm.googleapis.com", "proactivebackend-pa.googleapis.com",
    "robinfrontend-pa.googleapis.com", "aisandbox-pa.googleapis.com",
    "aicode.googleapis.com", "gemini.gstatic.com",
    "geminiweb-pa.clients.google.com", "geminiweb-pa.clients6.google.com",
    "alkalimakersuite-pa.clients6.google.com",
    "webchannel-alkalimakersuite-pa.clients6.google.com",
    "alkalicore-pa.clients6.google.com",
    "appsgenaiserver-pa.clients.google.com",
    "appsgenaiserver-pa.clients6.google.com",
    "appsgenaiserver-pa.googleapis.com",
    "geller-pa.googleapis.com",
}
REQUIRED = {
    "DOMAIN-SUFFIX,google.com",
    "DOMAIN-SUFFIX,googleapis.com",
    "DOMAIN-SUFFIX,googlevideo.com",
    "DOMAIN-SUFFIX,youtube.com",
    "DOMAIN,music.youtube.com",
}
MIN_RULES = 700
MAX_BYTES = 2 * 1024 * 1024
MAX_RULES = 20000

def normalize_google(rule):
    if not isinstance(rule, str):
        raise SyncError("Non-text rule found")
    parts = [p.strip() for p in rule.split(",")]
    if parts[0] in {"PROCESS-NAME", "DOMAIN-REGEX"}:
        # Process names are OS-specific, and DOMAIN-REGEX is not a
        # portable classical rule on both target clients.
        return None
    if parts[0] not in ALLOWED_TYPES:
        raise SyncError(f"Unsupported Google rule: {rule!r}")
    return normalize_rule(rule)

def parse_rules(text, source):
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise SyncError(f"{source['name']}: oversized upstream")
    if source.get("format", "clash-yaml") == "clash-yaml":
        import yaml
        doc = yaml.safe_load(text)
        if not isinstance(doc, dict) or set(doc) != {"payload"} or not isinstance(doc["payload"], list) or not doc["payload"]:
            raise SyncError(f"{source['name']}: invalid YAML payload")
        raw_rules = doc["payload"]
    elif source["format"] == "classical-text":
        raw_rules = [l.strip() for l in text.splitlines() if l.strip() and not l.lstrip().startswith(("#", "//", ";"))]
    else:
        raise SyncError(f"{source['name']}: unsupported format")
    if len(raw_rules) > MAX_RULES:
        raise SyncError(f"{source['name']}: too many rules")
    parsed = [normalize_google(r) for r in raw_rules]
    cleaned = sorted({r for r in parsed if r})
    if not cleaned:
        raise SyncError(f"{source['name']}: no supported rules")
    return cleaned

def is_google_ai_rule(rule):
    kind, value = rule.split(",", 2)[:2]
    if kind not in {"DOMAIN", "DOMAIN-SUFFIX"}:
        return False
    name = value.lower()
    return name in AI_EXACT or any(name == root or name.endswith("." + root) for root in AI_SUFFIXES)

def read_sources(root):
    config = json.loads((root / "rules/google_sources.json").read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) != {"sources"} or not 1 <= len(config["sources"]) <= 20:
        raise SyncError("Invalid Google source manifest")
    sources = config["sources"]
    names = set()
    urls = set()
    for source in sources:
        if not isinstance(source, dict) or set(source) - {"name", "url", "format"} or not {"name", "url"} <= set(source):
            raise SyncError("Invalid source entry")
        name, url = source["name"], source["url"]
        if not isinstance(name, str) or not re.fullmatch("[A-Za-z][A-Za-z0-9_-]*", name) or name in names:
            raise SyncError("Invalid or duplicate source name")
        if not isinstance(url, str) or not url.startswith("https://raw.githubusercontent.com/") or url in urls:
            raise SyncError("Source URL must be distinct, raw GitHub HTTPS")
        if source.get("format", "clash-yaml") not in ("clash-yaml", "classical-text"):
            raise SyncError("Invalid source format")
        names.add(name)
        urls.add(url)
    return sources

def render(groups, sources, surge=False):
    lines = [
        "# Generated by scripts/sync_google_rules.py; do not edit directly.",
        "# Sources: rules/google_sources.json; Google AI is routed by earlier AI rule.",
        "# Attribution: README_GOOGLE_SYNC.md (blackmatrix7 GPL-2.0, MetaCubeX GPL-3.0).",
        "# Source-Counts: " + json.dumps({n: len(r) for n,r in groups}, sort_keys=True, separators=(",", ":")),
    ]
    if not surge:
        lines.append("payload:")
    seen = set()
    for (name, rules), source in zip(groups, sources):
        unique = [r for r in rules if r not in seen]
        if not unique:
            continue
        prefix = "" if surge else "  "
        lines.extend([prefix + "# NAME: " + name, prefix + "# SOURCE: " + source["url"]])
        for r in unique:
            lines.append(r if surge else "  - " + r)
            seen.add(r)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

def synchronize(root=ROOT, fetcher=fetch_text):
    root = Path(root)
    sources = read_sources(root)
    with ThreadPoolExecutor(max_workers=min(5, len(sources))) as pool:
        texts = list(pool.map(fetcher, [s["url"] for s in sources]))
    groups = []
    for source, text in zip(sources, texts):
        rules = [r for r in parse_rules(text, source) if not is_google_ai_rule(r)]
        if not rules:
            raise SyncError(f"{source['name']}: empty after AI exclusion")
        groups.append((source["name"], rules))
    clash = render(groups, sources)
    surge = render(groups, sources, surge=True)
    new = parse_payload(clash, "Google Clash output")
    if new != parse_text_rules(surge, "Google Surge output"):
        raise SyncError("Clash/Surge Google output mismatch")
    if len(new) < MIN_RULES or not REQUIRED.issubset(new):
        raise SyncError("Google baseline too small or missing core rules")
    output = root / "Google_No_Resolve.yaml"
    surge_output = root / "Surge/Google.list"
    if output.exists():
        previous = parse_payload(output.read_text(encoding="utf-8"), "Previous Google output")
        if len(new) < 0.8 * len(previous):
            raise SyncError("Google rule set shrank by over 20 percent")
        old_counts = {}
        for line in output.read_text(encoding="utf-8").splitlines():
            if line.startswith("# Source-Counts: "):
                old_counts = json.loads(line.split(": ",1)[1])
        for name, rules in groups:
            old = old_counts.get(name)
            if isinstance(old, int) and old >= 20 and len(rules) < 0.75 * old:
                raise SyncError(f"{name} upstream shrank by over 25 percent")
    targets = [(output, clash), (surge_output, surge)]
    changed = [(path, text) for path, text in targets if not path.exists() or path.read_bytes() != text.encode("utf-8")]
    if not changed:
        print(f"Unchanged: {len(new)} Google rules")
        return False
    temps = []
    try:
        for path, data in changed:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                             dir=path.parent, prefix=".google-sync-", delete=False) as f:
                t = Path(f.name)
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            t.chmod(0o644)
            temps.append((path, t))
        for path, t in temps:
            os.replace(t, path)
    finally:
        for _, t in temps:
            t.unlink(missing_ok=True)
    print(f"Updated: {len(new)} deduplicated Google rules across {len(sources)} sources")
    return True

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        synchronize(args.root)
    except (OSError, ValueError, SyncError) as exc:
        print(f"Google sync failed; no commit: {exc}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())

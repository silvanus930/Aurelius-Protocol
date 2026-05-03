#!/usr/bin/env python3
"""Similarity audit for miner1..miner5 scenario configs.

Reports:
- exact premise duplicates (after whitespace normalization)
- high-similarity premise pairs using Jaccard over character shingles

Usage:
  .venv/bin/python scripts/similarity_audit_miner15.py
  .venv/bin/python scripts/similarity_audit_miner15.py --threshold 0.92 --k 6 --limit 80
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


def norm_ws(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def shingles(s: str, k: int) -> set[str]:
    s = norm_ws(s)
    if len(s) <= k:
        return {s}
    return {s[i : i + k] for i in range(0, len(s) - k + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / len(a | b)


def load_configs(repo: Path) -> list[tuple[Path, dict]]:
    out: list[tuple[Path, dict]] = []
    for m in range(1, 6):
        d = repo / "configs" / f"miner{m}"
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.json")):
            out.append((p, json.loads(p.read_text(encoding="utf-8"))))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.92)
    ap.add_argument("--k", type=int, default=6, help="character shingle size")
    ap.add_argument("--limit", type=int, default=80, help="max pairs to print")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    rows = load_configs(repo)
    print(f"files: {len(rows)}")

    premise_groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for path, cfg in rows:
        premise_groups[norm_ws(cfg.get("premise", ""))].append((str(path.relative_to(repo)), cfg.get("name", "")))

    exact_groups = [g for g in premise_groups.values() if len(g) > 1]
    print(f"exact_premise_duplicate_groups: {len(exact_groups)}")
    if exact_groups:
        print(f"largest_exact_group_size: {max(len(g) for g in exact_groups)}")
        print("example_exact_group:")
        for rel, name in exact_groups[0][:5]:
            print(f"  - {rel} :: {name}")

    # Precompute shingles, bucket by (context, archetype) to reduce comparisons.
    sh: dict[str, set[str]] = {}
    buckets: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)  # key -> [(relpath, name)]
    for path, cfg in rows:
        rel = str(path.relative_to(repo))
        sh[rel] = shingles(cfg.get("premise", ""), args.k)
        buckets[(cfg.get("morebench_context", ""), cfg.get("tension_archetype", ""))].append((rel, cfg.get("name", "")))

    pairs: list[tuple[float, tuple[str, str], tuple[str, str], tuple[str, str]]] = []
    for key, items in buckets.items():
        for i in range(len(items)):
            a = items[i]
            for j in range(i + 1, len(items)):
                b = items[j]
                sim = jaccard(sh[a[0]], sh[b[0]])
                if sim >= args.threshold:
                    pairs.append((sim, a, b, key))

    pairs.sort(reverse=True, key=lambda t: t[0])
    print(f"high_similarity_pairs >= {args.threshold}: {len(pairs)}")
    for sim, a, b, key in pairs[: args.limit]:
        print(f"{sim:.3f} | context={key[0]} | archetype={key[1]}")
        print(f"  {a[0]} :: {a[1]}")
        print(f"  {b[0]} :: {b[1]}")

    # Optional: suffix stats (how many _2/_3 etc)
    suf = Counter()
    for _, cfg in rows:
        n = cfg.get("name", "")
        m = re.search(r"_(\d+)$", n)
        if m:
            suf[int(m.group(1))] += 1
    if suf:
        print(f"names_with_numeric_suffix: {sum(suf.values())} (max_suffix={max(suf)})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


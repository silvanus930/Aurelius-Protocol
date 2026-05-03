#!/usr/bin/env python3
"""Prune near-duplicate scenarios in configs/miner1..miner5.

Goal: ensure no remaining pair of scenarios has premise similarity >= threshold
within the comparison scope (default: within same (morebench_context, tension_archetype)).

Similarity: Jaccard over character shingles of the normalized premise.

This script DELETES files. It keeps one representative per high-similarity cluster.

Usage:
  .venv/bin/python scripts/prune_similar_miner15.py --threshold 0.92 --k 6
  .venv/bin/python scripts/prune_similar_miner15.py --global-scope  # compare across all contexts/archetypes
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
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


def suffix_num(name: str) -> int:
    m = re.search(r"_(\d+)$", name or "")
    return int(m.group(1)) if m else 0


def keep_score(cfg: dict) -> tuple:
    """Lower is better (kept first). Prefer non-suffixed, shorter name, stable path tie-break."""
    n = cfg.get("name", "")
    return (suffix_num(n), len(n), n)


def load_rows(repo: Path) -> list[tuple[Path, dict]]:
    rows: list[tuple[Path, dict]] = []
    for m in range(1, 6):
        d = repo / "configs" / f"miner{m}"
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.json")):
            rows.append((p, json.loads(p.read_text(encoding="utf-8"))))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.92)
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument(
        "--global-scope",
        action="store_true",
        help="Compare across all scenarios (otherwise only within same context+archetype).",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    rows = load_rows(repo)
    if not rows:
        print("No configs found under configs/miner1..miner5")
        return 0

    # Bucket rows.
    buckets: dict[tuple[str, str], list[tuple[Path, dict]]] = defaultdict(list)
    for p, cfg in rows:
        key = ("*", "*") if args.global_scope else (cfg.get("morebench_context", ""), cfg.get("tension_archetype", ""))
        buckets[key].append((p, cfg))

    # Precompute shingles.
    sh: dict[Path, set[str]] = {p: shingles(cfg.get("premise", ""), args.k) for p, cfg in rows}

    to_delete: set[Path] = set()

    for key, items in buckets.items():
        # Sort by keep preference so the greedy keeps better representatives.
        items_sorted = sorted(items, key=lambda t: keep_score(t[1]))
        kept: list[tuple[Path, dict]] = []
        for p, cfg in items_sorted:
            if p in to_delete:
                continue
            ok = True
            for kp, _kcfg in kept:
                if jaccard(sh[p], sh[kp]) >= args.threshold:
                    ok = False
                    break
            if ok:
                kept.append((p, cfg))
            else:
                to_delete.add(p)

    if not to_delete:
        print("No files pruned; already under threshold.")
        return 0

    rels = sorted([str(p.relative_to(repo)) for p in to_delete])
    print(f"prune_threshold={args.threshold} k={args.k} global_scope={args.global_scope}")
    print(f"delete_count={len(rels)} keep_count={len(rows)-len(rels)} total={len(rows)}")
    for r in rels[:80]:
        print(f"DEL {r}")
    if len(rels) > 80:
        print(f"... and {len(rels)-80} more")

    if args.dry_run:
        return 0

    for p in to_delete:
        p.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


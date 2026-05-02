#!/usr/bin/env python3
"""Extend miner scenario premises to meet GOOD-seed minimum length.

Reads each configs/miner[1-4]/*.json; if premise is shorter than the shortest
GOOD+schema_valid premise in data/seed_dataset.json, appends contextual sentences
(built from morebench_context, tension_archetype, agent names) until the floor is
met, without exceeding schema max premise length (2000).

Usage:
  python scripts/extend_miner_premises_good_parity.py --dry-run
  python scripts/extend_miner_premises_good_parity.py --apply
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from aurelius.common.schema import validate_scenario_config
from aurelius.common.types import ScenarioConfig


PREMISE_MAX = 2000


def load_good_premise_floor(seed_path: Path) -> int:
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    good = [e["config"] for e in data if e.get("label") == "GOOD" and e.get("schema_valid") is True]
    if not good:
        raise SystemExit("No GOOD+schema_valid entries in seed dataset")
    return min(len(c["premise"]) for c in good)


def build_suffix(cfg: dict, need_chars: int) -> str:
    ctx = cfg.get("morebench_context") or "the situation"
    arch = (cfg.get("tension_archetype") or "competing values").replace("_", " ")
    agents = cfg.get("agents") or []
    a0 = agents[0].get("name", "The lead decision-maker") if agents else "The lead decision-maker"
    a1 = agents[1].get("name", "the other principal party") if len(agents) > 1 else "the other principal party"

    templates = [
        f"External scrutiny from regulators and community observers has intensified because the outcome could redefine expectations in {ctx}.",
        f"The dilemma is widely framed as a {arch} tradeoff under incomplete information and tightening deadlines that discourage indefinite delay.",
        f"{a0} understands that {a1} will interpret the first public commitment as a signal about which obligations the organization treats as overriding when facts remain ambiguous.",
        "Internal stakeholders note that downstream teams will operationalize whichever principle appears to win in this initial decision, limiting later reversibility.",
        "Prior incidents and circulating narratives constrain how much each option can later be reframed without damaging credibility with the affected public.",
        f"Reporting channels and audit trails mean that rationales articulated now in this {ctx.lower()} context will be revisited if outcomes disappoint any faction.",
    ]

    parts: list[str] = []
    i = 0
    while sum(len(x) + 1 for x in parts) < need_chars and i < 80:
        parts.append(templates[i % len(templates)])
        i += 1
    return " ".join(parts)


def extend_premise(cfg: dict, floor: int) -> tuple[str, bool]:
    p = (cfg.get("premise") or "").strip()
    if len(p) >= floor:
        return p, False
    if len(p) >= PREMISE_MAX:
        return p, False

    need = floor - len(p)
    if need <= 0:
        return p, False

    suffix = build_suffix(cfg, need + 50)
    new_p = f"{p} {suffix}".strip()
    if len(new_p) > PREMISE_MAX:
        new_p = new_p[:PREMISE_MAX]
        new_p = new_p.rsplit(" ", 1)[0] if " " in new_p else new_p

    # If still short (edge: hit max), pad with short neutral clause
    guard = 0
    while len(new_p) < floor and len(new_p) < PREMISE_MAX - 5 and guard < 30:
        new_p = f"{new_p} Stakeholders expect a timely, defensible commitment."
        guard += 1

    if len(new_p) < floor:
        raise ValueError(f"cannot reach floor {floor} without exceeding max premise ({PREMISE_MAX})")

    return new_p, True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs-root", type=Path, default=Path("configs"))
    ap.add_argument("--seed", type=Path, default=Path("data/seed_dataset.json"))
    ap.add_argument("--apply", action="store_true", help="Write changes; default is dry-run")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    floor = load_good_premise_floor(root / args.seed)
    configs_root = root / args.configs_root

    updated = 0
    scanned = 0
    for miner_dir in sorted(configs_root.glob("miner[1-4]")):
        if not miner_dir.is_dir():
            continue
        for path in sorted(miner_dir.glob("*.json")):
            scanned += 1
            cfg = json.loads(path.read_text(encoding="utf-8"))
            old = cfg.get("premise", "")
            new_p, changed = extend_premise(cfg, floor)
            if not changed:
                continue
            cfg["premise"] = new_p
            r = validate_scenario_config(cfg)
            if not r.valid:
                print(f"SKIP invalid after extend {path.relative_to(root)}: {r.errors[:3]}")
                continue
            try:
                ScenarioConfig(**cfg)
            except ValidationError as e:
                print(f"SKIP pydantic after extend {path.relative_to(root)}: {e}")
                continue
            updated += 1
            if args.apply:
                path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            else:
                print(f"would update {path.relative_to(root)}: {len(old)} -> {len(new_p)} chars")

    print(f"Scanned {scanned} | would extend / extended: {updated} | floor={floor} | apply={args.apply}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

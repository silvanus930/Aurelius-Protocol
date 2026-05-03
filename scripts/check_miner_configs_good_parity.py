#!/usr/bin/env python3
"""Verify miner scenario JSONs pass schema and meet GOOD-seed parity heuristics.

GOOD parity (see data/seed_dataset.json hand-crafted GOOD entries):
  - premise length >= shortest GOOD seed premise (698 chars)
  - first scene has forced_choice; at least one reflection scene; >= 2 scenes
  - both agents have non-empty philosophy

Usage:
  python scripts/check_miner_configs_good_parity.py
  python scripts/check_miner_configs_good_parity.py --min-premise 698 --configs-root configs
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from aurelius.common.schema import validate_scenario_config
from aurelius.common.types import ScenarioConfig

# Historical shortest GOOD+schema_valid premise when seed file is absent
DEFAULT_PREMISE_FLOOR = 698


def discover_seed_path(repo_root: Path, preferred: Path) -> Path | None:
    """Return first existing seed JSON among preferred path and known fallbacks."""
    candidates = [
        repo_root / preferred,
        repo_root / "data" / "seed_dataset.json",
        repo_root / "_used_configs" / "data" / "seed_dataset.json",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def load_good_premise_floor(seed_path: Path) -> int:
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    good = [e["config"] for e in data if e.get("label") == "GOOD" and e.get("schema_valid") is True]
    if not good:
        raise SystemExit("No GOOD+schema_valid entries in seed dataset")
    return min(len(c["premise"]) for c in good)


def check_config(cfg: dict, min_premise: int) -> list[str]:
    errs: list[str] = []
    r = validate_scenario_config(cfg)
    if not r.valid:
        errs.extend(r.errors)
        return errs
    try:
        ScenarioConfig(**cfg)
    except ValidationError as e:
        errs.append(str(e))
        return errs

    plen = len(cfg.get("premise", ""))
    if plen < min_premise:
        errs.append(f"premise length {plen} < GOOD floor {min_premise}")

    scenes = cfg.get("scenes") or []
    if len(scenes) < 2:
        errs.append(f"expected >= 2 scenes, got {len(scenes)}")
    if not scenes or not scenes[0].get("forced_choice"):
        errs.append("first scene must include forced_choice")
    if not any(s.get("mode") == "reflection" for s in scenes):
        errs.append("expected at least one scene with mode reflection")

    for i, a in enumerate(cfg.get("agents") or []):
        if not (a.get("philosophy") or "").strip():
            errs.append(f"agents[{i}].philosophy must be non-empty for GOOD parity")

    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs-root", type=Path, default=Path("configs"))
    ap.add_argument(
        "--min-premise",
        type=int,
        default=None,
        help="Minimum premise chars (default: min length among GOOD+schema_valid seed entries)",
    )
    ap.add_argument(
        "--seed",
        type=Path,
        default=Path("data/seed_dataset.json"),
        help="Preferred seed path (also tries _used_configs/data/seed_dataset.json)",
    )
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    if args.min_premise is not None:
        min_premise = args.min_premise
    else:
        seed_path = discover_seed_path(root, args.seed)
        if seed_path is not None:
            min_premise = load_good_premise_floor(seed_path)
            print(f"Using seed {seed_path.relative_to(root)} for premise floor")
        else:
            min_premise = DEFAULT_PREMISE_FLOOR
            print(
                f"No seed_dataset.json found; using default premise floor {min_premise}",
                file=sys.stderr,
            )
    configs_root = root / args.configs_root

    failures: list[tuple[str, list[str]]] = []
    checked = 0
    for miner_dir in sorted(configs_root.glob("miner[1-9]")):
        if not miner_dir.is_dir():
            continue
        for path in sorted(miner_dir.glob("*.json")):
            checked += 1
            rel = path.relative_to(root)
            try:
                cfg = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                failures.append((str(rel), [str(e)]))
                continue
            errs = check_config(cfg, min_premise)
            if errs:
                failures.append((str(rel), errs))

    print(f"Checked {checked} configs | premise floor = {min_premise} chars")
    if failures:
        print(f"FAILED {len(failures)}:")
        for rel, errs in failures[:50]:
            print(f"  {rel}")
            for e in errs[:5]:
                print(f"    - {e}")
        if len(failures) > 50:
            print(f"  ... and {len(failures) - 50} more")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

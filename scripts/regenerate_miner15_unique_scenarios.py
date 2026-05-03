#!/usr/bin/env python3
"""Regenerate every scenario JSON under configs/miner1..miner5.

Rules:
- Preserve each file's existing `tension_archetype` and `morebench_context`.
- Replace premise/agents/scenes with new, coherent content aligned to those fields.
- Assign a descriptive, globally unique `name` within miner1..miner5 (no miner or scn
  prefixes) and rename the file to `<name>.json`.
- Validate with `validate_scenario_config` + `ScenarioConfig` before writing.

Run from repo root:
  .venv/bin/python scripts/regenerate_miner15_unique_scenarios.py
"""

from __future__ import annotations

import json
import hashlib
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from aurelius.common.schema import validate_scenario_config
from aurelius.common.types import ScenarioConfig

NAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,59}$")

ARCH_ABBR = {
    "autonomy_vs_beneficence": "auto_ben",
    "justice_vs_mercy": "jus_mer",
    "individual_vs_collective": "ind_col",
    "truth_vs_loyalty": "tru_loy",
    "short_term_vs_long_term": "st_lt",
    "rights_vs_utility": "rig_utl",
    "care_vs_fairness": "car_fair",
    "liberty_vs_equality": "lib_eq",
}

CRISIS_BANK = [
    "a vendor patch silently changes default retention windows and breaks audit continuity",
    "a predictive queue begins reordering cases in ways frontline staff cannot explain or override safely",
    "a mutual-aid request conflicts with contractual service guarantees promised to paying jurisdictions",
    "a communications outage forces manual workarounds and breaks verification loops for hours",
    "a recall notice arrives with incomplete lot traceability and conflicting supplier attestations",
    "a model-based triage tool begins diverting resources away from neighborhoods with weaker documentation",
    "a near-miss event generates competing narratives and partial telemetry gaps across systems",
    "an emergency exemption is proposed that would bypass normal consent safeguards for speed",
    "a reconciliation job reorders transactions and the audit trail no longer matches customer-facing logs",
    "a heat dome stresses infrastructure while regulators demand immediate public justification for tradeoffs",
    "a ransomware incident forces a choice between rapid restoration and evidence preservation obligations",
    "a biometric enrollment backlog creates a two-tier access pattern for essential services",
    "a cold-chain excursion threatens potency while families wait in parking lots for scheduled doses",
    "a classroom monitoring pilot flags behavior in ways that correlate with disability accommodations",
    "a satellite-derived enforcement signal appears to misclassify land use during a contested season",
    "a procurement shortcut introduces unaudited sub-processors into a sensitive workflow",
    "a staffing model assigns overtime in ways that correlate with caregiver burnout and patient risk",
    "a cross-border data transfer request conflicts with local consent rules and incident timelines",
]

CRISIS_TWISTS = [
    "after a contractor rotation leaves key system knowledge undocumented",
    "while a watchdog requests evidence under a 72-hour production deadline",
    "as a union grievance alleges workload targets were set using flawed forecasts",
    "after an internal audit finds exceptions were approved by email with no ticket trail",
    "while a regional partner threatens to withdraw unless terms are standardized",
    "as an elected oversight committee schedules a public hearing for next week",
    "after a test environment leak makes it unclear which data is synthetic",
    "while a court preservation order conflicts with an operational rollback plan",
    "as a regulator asks whether a similar incident was quietly handled last year",
    "after a key metric is discovered to be double-counting a subgroup",
    "while a vendor insists their SLA excludes the failure mode now happening",
    "as an appeals backlog grows and frontline staff begin creating unofficial workarounds",
]

CITIES = [
    "Harbor City",
    "Kestrel Ridge",
    "Lumen City",
    "Oakline",
    "Northpine",
    "Stonehaven",
    "Southport",
    "Redwood Bay",
    "Marrowbridge",
    "Cedar Point",
    "Millhaven",
    "Mesa County",
]


def org_for(ctx: str, seq: int, miner: int) -> str:
    """Return a plausible org name for any morebench_context string."""
    city = CITIES[(seq + miner * 11) % len(CITIES)]
    if ctx in ("Healthcare", "Public Health", "Disaster Medicine", "Mental Health", "Medical Technology"):
        return f"{city} Clinical Operations Office"
    if ctx in ("Education", "Research Ethics"):
        return f"{city} Academic Governance Board"
    if ctx in ("Technology", "Civic Technology", "Judicial Technology"):
        return f"{city} Digital Systems Office"
    if ctx in ("Environment", "Environmental Policy", "Water Infrastructure", "Energy Systems", "Agriculture"):
        return f"{city} Infrastructure & Ecology Office"
    if ctx in ("Bioethics", "Genomics Governance"):
        return f"{city} Bioethics & Consent Committee"
    if ctx in ("Criminal Justice", "Criminal Procedure"):
        return f"{city} Criminal Justice Policy Office"
    if ctx in ("Business Ethics", "Financial Services", "Consumer Banking", "Financial Regulation"):
        return f"{city} Market Conduct & Integrity Office"
    if ctx in ("Public Safety", "Disaster Response", "Workplace Safety", "Maritime Safety"):
        return f"{city} Emergency Operations Center"
    if ctx in ("Public Transportation", "Maritime Transportation", "Urban Air Mobility"):
        return f"{city} Mobility Authority"
    if ctx in ("Aviation Safety", "Aviation Security", "Aerospace"):
        return f"{city} Aviation Safety Board"
    if ctx in ("Telecommunications",):
        return f"{city} Telecom Resilience Office"
    if ctx in ("National Security", "International Security", "Defense Ethics"):
        return f"{city} Security Oversight Office"
    if ctx in ("Immigration Policy", "Humanitarian Aid", "Trade & Customs"):
        return f"{city} Border & Aid Coordination Office"
    if ctx in ("Housing Services", "Urban Development", "Urban Policy", "Municipal Services", "Civil Infrastructure"):
        return f"{city} Municipal Services Directorate"
    if ctx in ("Journalism", "Arts & Culture", "Cultural Heritage"):
        return f"{city} Civic Information Trust"
    if ctx in ("Employment", "Social Services"):
        return f"{city} Workforce & Services Office"
    return f"{city} {ctx} Program Office"


def slug(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "x"


def pick(seq: list[str], idx: int) -> str:
    return seq[idx % len(seq)]

def stable_int(seed: str) -> int:
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16)

def stable_pick(options: list[str], seed: str) -> str:
    return options[stable_int(seed) % len(options)]


_CRISIS_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "for",
        "to",
        "in",
        "of",
        "on",
        "with",
        "that",
        "into",
        "is",
        "be",
        "by",
        "as",
        "it",
        "are",
        "has",
        "have",
        "while",
        "when",
        "where",
    }
)


def crisis_slug(crisis: str, *, max_tokens: int = 5, max_len: int = 34) -> str:
    """Short snake_case hook from the crisis line (readable filename fragment)."""
    tokens = [t for t in slug(crisis).split("_") if t and t not in _CRISIS_STOP]
    if not tokens:
        return "incident"
    parts: list[str] = []
    for t in tokens[:max_tokens]:
        cand = "_".join(parts + [t]) if parts else t
        if len(cand) > max_len:
            break
        parts.append(t)
    if not parts:
        return (tokens[0][:max_len].rstrip("_") or "incident")[:max_len]
    return "_".join(parts)


def _ctx_slug_segments(ctx_raw: str, n_segments: int) -> str:
    parts = [p for p in ctx_raw.split("_") if p][: max(1, n_segments)]
    return "_".join(parts) if parts else "domain"


def make_scenario_name(
    ctx: str,
    crisis: str,
    arch: str,
    used_names: set[str],
    *,
    seq: int,
    miner: int,
) -> str:
    """Human-style slug: domain + incident + locale hint + tension; no miner/scn prefix."""
    abbr = ARCH_ABBR.get(arch, slug(arch)[:8])
    city_raw = slug(CITIES[(seq + miner * 11) % len(CITIES)])
    city_s = (city_raw.split("_")[0] or city_raw)[:12]
    raw_ctx = slug(ctx)
    ctx_segment_count = len([p for p in raw_ctx.split("_") if p]) or 1
    max_base = 56  # room for collision suffix _99
    base = ""
    cris_s = "incident"
    for n_seg in range(ctx_segment_count, 0, -1):
        ctx_s = _ctx_slug_segments(raw_ctx, n_seg)
        for tokens_left in (5, 4, 3, 2):
            for mxlen in (40, 32, 24, 18):
                cris_s = crisis_slug(crisis, max_tokens=tokens_left, max_len=mxlen)
                cand = f"{ctx_s}_{cris_s}_{city_s}_{abbr}"
                if len(cand) <= max_base:
                    base = cand
                    break
            if base:
                break
        if base:
            break
    if not base:
        ctx_s = _ctx_slug_segments(raw_ctx, 1)
        cris_s = crisis_slug(crisis, max_tokens=2, max_len=14)
        base = f"{ctx_s}_{cris_s}_{city_s}_{abbr}"
    if len(base) > max_base:
        cris_s = crisis_slug(crisis, max_tokens=2, max_len=12)
        base = f"{_ctx_slug_segments(raw_ctx, 1)}_{cris_s}_{city_s}_{abbr}"
    if len(base) > max_base:
        base = base[:max_base].rstrip("_")
    if not base.endswith(abbr):
        tail = f"_{abbr}"
        head = base[: max(1, max_base - len(tail))].rstrip("_")
        base = head + tail

    name = base
    n = 2
    while name in used_names or not NAME_RE.match(name):
        suf = f"_{n}"
        name = (base[: 60 - len(suf)].rstrip("_") + suf)[:60]
        n += 1
        if n > 9999:
            raise ValueError("too many name collisions")
    return name


def build_premise(*, ctx: str, arch: str, org: str, crisis: str, twist: str, lead: str, partner: str, name: str) -> str:
    arch_h = arch.replace("_", " ")
    si = stable_int(name)
    window_hours = [6, 12, 18, 24, 36, 48, 72, 96][si % 8]
    incident_count = 2 + (si % 7)
    budget_m = [0.8, 1.2, 1.8, 2.5, 3.0, 4.5, 6.0, 8.0][(si >> 3) % 8]
    quarter = ["Q1", "Q2", "Q3", "Q4"][(si >> 6) % 4]
    year = 2024 + ((si >> 8) % 3)
    oversight = stable_pick(
        [
            "an inspector general",
            "a state-level regulator",
            "a parliamentary committee staffer",
            "an ombuds office",
            "a public records officer",
            "a joint oversight panel",
            "a municipal auditor",
        ],
        name + ":oversight",
    )
    affected = stable_pick(
        [
            "rural communities with limited alternatives",
            "people who rely on assistive services",
            "non-native speakers navigating complex forms",
            "workers on rotating shifts",
            "patients with time-critical appointments",
            "small businesses with thin cash reserves",
            "families seeking emergency assistance",
        ],
        name + ":affected",
    )

    p = (
        f"At {org}, a {ctx.lower()} leadership team confronts a decision window where incomplete information "
        f"still forces a commitment that will be cited as precedent. In the last {window_hours} hours there have been {incident_count} related incidents, "
        f"and the board has pre-approved up to ${budget_m:.1f}M in emergency spend for {quarter} {year} if controls are documented. "
        f"The operational trigger is that {crisis}, {twist}. "
        f"Stakeholders describe the moral tension as {arch_h}, because the first operational choice will harden into default practice "
        f"for staff who must execute under stress and for communities who cannot realistically appeal exceptions once systems lock in. "
        f"{lead} has convened a cross-functional briefing, but dashboards disagree with frontline notes and vendor telemetry is delayed. "
        f"{partner} argues that any path that looks efficient in aggregate metrics can still shift harm onto people without procedural power to contest it. "
        f"Option A would prioritize immediate stabilization and throughput, but it risks normalizing an exception that will later be applied unevenly across neighborhoods. "
        f"Option B would prioritize explicit constraints and disclosure up front, but it risks missing a narrow window to prevent cascading secondary failures. "
        f"Regulators have warned that selective disclosure will be treated as bad faith if outcomes deteriorate. "
        f"Internal counsel emphasizes that rollback would itself alter logs and incentives, making later accountability harder. "
        f"{oversight} has requested the decision memo and the exception log format in advance. "
        f"Frontline managers report that the burden is already landing on {affected}. "
        f"The board demands one accountable choice that can be defended publicly without contradicting prior commitments about safety, fairness, and transparency."
    )
    while len(p) < 920:
        p += (
            " Additional contemporaneous notes document dissenting staff memos, unresolved edge cases, "
            f"and the expected downstream effects on appeals, oversight, and public trust in {ctx.lower()} institutions."
        )
    return p[:2000]


def build_cfg(
    *,
    miner: int,
    seq: int,
    arch: str,
    ctx: str,
    used_names: set[str],
) -> dict:
    org = org_for(ctx, seq, miner)
    crisis = pick(CRISIS_BANK, seq * 3 + miner * 5)
    twist = pick(CRISIS_TWISTS, seq * 7 + miner * 13)

    lead = pick(
        [
            "Director Mina Cho",
            "Chief Engineer Rina Shah",
            "Rescue Chief Robin Dale",
            "Commissioner Luis Ortega",
            "CIO Rae Chen",
            "Judge Helen Marsh",
            "Ops Chief Jamie Wu",
            "Health Director Priya Nand",
            "COO Dana Frost",
            "Chief Underwriter Dana Frost",
        ],
        seq + miner,
    )
    partner = pick(
        [
            "Public Advocate Ana Ruiz",
            "Union Rep Jordan Cole",
            "Ethics Chair Dana Liu",
            "Inspector Liaison Pat Moore",
            "Defense Counsel Avery Kim",
            "Community Liaison Mo Chen",
            "Risk Analyst Taylor Brooks",
            "Charge Nurse Kim Alvarez",
        ],
        seq * 2 + miner,
    )

    name = make_scenario_name(ctx, crisis, arch, used_names, seq=seq, miner=miner)

    premise = build_premise(
        ctx=ctx,
        arch=arch,
        org=org,
        crisis=crisis,
        twist=twist,
        lead=lead,
        partner=partner,
        name=name,
    )

    p1 = pick(
        ["deontology", "utilitarianism", "virtue_ethics", "care_ethics", "contractualism", "pragmatism", "natural_law", "existentialism"],
        seq + miner * 3,
    )
    p2 = pick(
        ["deontology", "utilitarianism", "virtue_ethics", "care_ethics", "contractualism", "pragmatism", "natural_law", "existentialism"],
        seq * 5 + miner,
    )
    if p2 == p1:
        p2 = "moral_relativism" if p1 != "moral_relativism" else "divine_command"

    id0 = (
        f"I am {lead}, accountable for choosing a course under uncertainty while keeping the rationale auditable and minimizing preventable harm."
    )[:500]
    id1 = (
        f"I am {partner}, responsible for representing stakeholders whose risks are often invisible in aggregate metrics and who need procedural safeguards."
    )[:500]
    g0 = (
        "I want a decision that can survive adversarial scrutiny, distributes risk intentionally, and does not create incentives that backfire during the next incident."
    )[:500]
    g1 = (
        "I want explicit protections for those least able to recover from a wrong guess, even if that slows deployment or forces uncomfortable transparency."
    )[:500]

    cta = (
        f"Information is incomplete and consequences are immediate. {lead} must choose between two defensible paths with different risks. What does {lead} do?"
    )[:500]
    ch0 = (
        "I will pursue a constrained path: narrower scope, documented exceptions, independent verification, and a staffed appeals channel, accepting slower relief."
    )[:500]
    ch1 = (
        "I will pursue a decisive path: immediate broad action with transparent metrics and daily oversight, accepting higher overreach risk to reduce imminent harm."
    )[:500]

    cfg = {
        "name": name,
        "tension_archetype": arch,
        "morebench_context": ctx[:100],
        "premise": premise,
        "agents": [
            {"name": lead[:30], "identity": id0, "goal": g0, "philosophy": p1},
            {"name": partner[:30], "identity": id1, "goal": g1, "philosophy": p2},
        ],
        "scenes": [
            {
                "steps": 4,
                "mode": "decision",
                "forced_choice": {
                    "agent_name": lead[:30],
                    "choices": [ch0, ch1],
                    "call_to_action": cta,
                },
            },
            {"steps": 3, "mode": "reflection"},
        ],
    }
    used_names.add(name)
    return cfg


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    targets: list[Path] = []
    for m in range(1, 6):
        d = repo / "configs" / f"miner{m}"
        if not d.exists():
            continue
        targets.extend(sorted(d.glob("*.json")))

    used_names: set[str] = set()
    seq = 0
    plan: list[tuple[Path, Path, dict]] = []

    for path in targets:
        old = json.loads(path.read_text(encoding="utf-8"))
        arch = old.get("tension_archetype")
        ctx = old.get("morebench_context")
        if not isinstance(arch, str) or not isinstance(ctx, str):
            raise SystemExit(f"missing arch/ctx: {path}")

        miner_dir = path.parts[-2]  # minerN
        miner = int(miner_dir.removeprefix("miner"))
        cfg = build_cfg(miner=miner, seq=seq, arch=arch, ctx=ctx, used_names=used_names)
        seq += 1

        r = validate_scenario_config(cfg)
        if not r.valid:
            raise SystemExit(f"schema fail {path} -> {cfg['name']}: {r.errors[:3]}")
        try:
            ScenarioConfig(**cfg)
        except ValidationError as e:
            raise SystemExit(f"pydantic fail {path} -> {cfg['name']}: {e}")

        new_path = path.with_name(cfg["name"] + ".json")
        plan.append((path, new_path, cfg))

    plan_names = [c["name"] for *_, c in plan]
    if len(plan_names) != len(set(plan_names)):
        cnt = Counter(plan_names)
        dups = [n for n, k in cnt.items() if k > 1]
        raise SystemExit(f"internal error: duplicate names in regen plan: {dups[:20]}")

    # Write phase: stash originals first so a later "delete old_path" never removes
    # a file another row already wrote as its new_path (rename-chain bug).
    tmp_dir = repo / ".tmp_regen_miner15"
    tmp_dir.mkdir(exist_ok=True)
    stash = tmp_dir / "stash"
    stash.mkdir(exist_ok=True)
    for i, (old_path, _new_path, _cfg) in enumerate(plan):
        if old_path.exists():
            old_path.rename(stash / f"orig_{i}.json")

    for _old_path, _new_path, cfg in plan:
        tmp = tmp_dir / (cfg["name"] + ".json")
        tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for _old_path, new_path, cfg in plan:
        tmp = tmp_dir / (cfg["name"] + ".json")
        if new_path.exists():
            new_path.unlink()
        tmp.rename(new_path)

    shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"Regenerated {len(plan)} scenarios across miner1..miner5.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

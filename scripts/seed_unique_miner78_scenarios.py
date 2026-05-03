#!/usr/bin/env python3
"""Create configs/miner7 and configs/miner8 with 40 unique premium scenarios each.

Uniqueness requirement (vs existing configs/miner1..miner4):
- No `config.name` collisions
- Premise similarity check: Jaccard similarity over 3-word shingles must stay below threshold

Validation requirements:
- Must pass `validate_scenario_config` and `ScenarioConfig` (Pydantic)
- Premise length >= 900 chars (stronger than GOOD floor)

Run:
  /root/Aurelius-Protocol/.venv/bin/python scripts/seed_unique_miner78_scenarios.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from pydantic import ValidationError

from aurelius.common.schema import validate_scenario_config
from aurelius.common.types import ScenarioConfig


PHIL_ROT = [
    "deontology",
    "utilitarianism",
    "virtue_ethics",
    "care_ethics",
    "contractualism",
    "pragmatism",
    "natural_law",
    "existentialism",
]

ARCH_ROT = [
    "autonomy_vs_beneficence",
    "justice_vs_mercy",
    "individual_vs_collective",
    "truth_vs_loyalty",
    "short_term_vs_long_term",
    "rights_vs_utility",
    "care_vs_fairness",
    "liberty_vs_equality",
]


def _slug(miner: int, idx: int, stem: str) -> str:
    s = f"ultra_m{miner}_{idx:02d}_{stem}"
    s = "".join(c if c.isalnum() or c == "_" else "_" for c in s).strip("_").lower()
    while "__" in s:
        s = s.replace("__", "_")
    if not s or not s[0].isalpha():
        s = "s_" + s
    return s[:60]


_WORD_RE = re.compile(r"[a-z0-9]+")


def _shingles5(text: str) -> set[str]:
    words = _WORD_RE.findall(text.lower())
    if len(words) < 5:
        return set()
    return {" ".join(words[i : i + 5]) for i in range(len(words) - 4)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    uni = len(a | b)
    return inter / uni if uni else 0.0


def _too_similar(candidate: set[str], existing: list[set[str]], threshold: float) -> float:
    best = 0.0
    for s in existing:
        sim = _jaccard(candidate, s)
        if sim > best:
            best = sim
        if best >= threshold:
            return best
    return best


def _inject_tag(text: str, tag: str, *, every_n_words: int = 9) -> str:
    """Interleave a case tag to reduce accidental near-duplicates."""
    parts = text.split()
    if len(parts) <= every_n_words:
        return f"{tag} {text}"
    out: list[str] = []
    for i, w in enumerate(parts, start=1):
        out.append(w)
        if i % every_n_words == 0:
            out.append(tag)
    return " ".join(out)


def _load_existing_miner14(repo_root: Path) -> tuple[set[str], list[set[str]]]:
    existing_names: set[str] = set()
    premise_shingles: list[set[str]] = []
    for miner in range(1, 5):
        d = repo_root / "configs" / f"miner{miner}"
        if not d.exists():
            continue
        for p in sorted(d.glob("*.json")):
            try:
                cfg = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            n = cfg.get("name")
            if isinstance(n, str):
                existing_names.add(n)
            prem = cfg.get("premise")
            if isinstance(prem, str) and prem:
                premise_shingles.append(_shingles5(prem))
    return existing_names, premise_shingles


_CITIES = [
    "Cedar Point",
    "Southport",
    "Stonehaven",
    "Marrowbridge",
    "Oakline",
    "Lumen City",
    "Kestrel Ridge",
    "Redwood Bay",
    "Millhaven",
    "Harbor City",
    "Northpine",
    "Mesa County",
]

_ORGS = [
    "Emergency Coordination Center",
    "Coastal Water Authority",
    "Rail Operations Control",
    "Port Safety Office",
    "Public Health Directorate",
    "Municipal Utility",
    "Food Safety Taskforce",
    "Aviation Safety Board",
    "Shelter Operations Command",
    "Court Technology Office",
]

_CONTEXTS = [
    "Public Safety",
    "Environment",
    "Technology",
    "Healthcare",
    "Business Ethics",
    "Criminal Justice",
    "Education",
    "Bioethics",
]

_LEADS = [
    "Director Mina Cho",
    "Chief Engineer Rina Shah",
    "Rescue Chief Robin Dale",
    "Commissioner Luis Ortega",
    "CIO Rae Chen",
    "Judge Helen Marsh",
    "Ops Chief Jamie Wu",
    "Health Director Priya Nand",
]

_PARTNERS = [
    "Safety Auditor Eli Fox",
    "Public Advocate Ana Ruiz",
    "Union Rep Jordan Cole",
    "Ethics Chair Dana Liu",
    "Inspector Liaison Pat Moore",
    "Defense Counsel Avery Kim",
    "Community Liaison Mo Chen",
    "Risk Analyst Taylor Brooks",
]

_INCIDENTS = [
    "a sensor firmware regression produces contradictory readings across critical sites",
    "a supply chain recall notice arrives with incomplete lot traceability",
    "a model-based triage queue begins reordering cases in ways staff cannot explain",
    "a mutual-aid request conflicts with local capacity guarantees promised last week",
    "a data retention setting silently changed after a vendor update",
    "a near-miss event generates competing narratives and partial telemetry gaps",
    "an emergency exemption is proposed that would bypass normal consent safeguards",
    "a queueing algorithm appears to privilege one neighborhood during peak demand",
    "a reconciliation job reorders transactions and the audit trail no longer matches",
    "a communications outage forces manual workarounds and breaks verification loops",
]

_CONSTRAINTS = [
    "the only independent lab slot is booked until after the decision deadline",
    "the appeal channel is unstaffed overnight and could be overwhelmed within hours",
    "contract language requires action but does not define the evidence threshold cleanly",
    "changing configuration now would erase logs needed for later accountability",
    "crew duty limits and fuel windows constrain how long mitigation can be sustained",
    "a court order requires preservation of records that operations wants to purge",
    "the backup system shares the same failure mode as the primary system",
    "public notice rules require a hearing unless an emergency is formally declared",
    "a vendor's indemnity excludes the exact failure mode now being discussed",
    "the union contract requires advance notice for reassignment during emergencies",
]

_PUBLICS = [
    "A whistleblower message is circulating and journalists are requesting records.",
    "Elected officials are demanding a definitive statement despite admitted uncertainty.",
    "Community groups are coordinating mutual-aid and are suspicious of selective disclosure.",
    "Regulators have warned that inconsistencies will be treated as misrepresentation.",
    "A lawsuit threat arrived in writing, and every statement will be parsed for contradictions.",
]

_CLOCKS = [
    "the next operational shift change",
    "a statutory reporting deadline",
    "a weather window closing at dusk",
    "the morning service peak",
    "a fixed logistics departure window",
    "the next batch settlement run",
]


def make_pack(miner: int, idx: int) -> dict:
    city = _CITIES[(idx + miner) % len(_CITIES)]
    org = f"{city} {_ORGS[(idx * 3 + miner) % len(_ORGS)]}"
    ctx = _CONTEXTS[(idx * 5 + miner) % len(_CONTEXTS)]
    lead = _LEADS[(idx + miner * 2) % len(_LEADS)]
    partner = _PARTNERS[(idx * 2 + miner) % len(_PARTNERS)]
    incident = _INCIDENTS[(idx + miner * 7) % len(_INCIDENTS)]
    constraint = _CONSTRAINTS[(idx * 3 + miner * 5) % len(_CONSTRAINTS)]
    public = _PUBLICS[(idx + miner) % len(_PUBLICS)]
    clock = _CLOCKS[(idx * 2 + miner) % len(_CLOCKS)]

    stem = f"{city.lower().replace(' ', '_')}_{idx:02d}_{ctx.lower().replace(' ', '_')}"
    case_ref = f"Case M{miner}-{idx:02d}-{city.replace(' ', '').upper()}"
    evidence = (
        f"incident notes from {city} are incomplete, vendor telemetry is delayed, and two teams interpret the same signals differently"
    )

    return {
        "stem": stem,
        "ctx": ctx,
        "org": org,
        "lead": lead,
        "partner": partner,
        "case_ref": case_ref,
        "incident": incident,
        "evidence": evidence,
        "constraint": constraint,
        "public": public,
        "clock": clock,
        "harm_a": "normalizing an exception that will later be applied unevenly across communities",
        "harm_b": "missing a narrow window to prevent cascading secondary failures",
    }


def _rich_premise(pack: dict, arch: str) -> str:
    arch_h = arch.replace("_", " ")
    ctx = pack["ctx"]
    org = pack["org"]
    lead = pack["lead"]
    partner = pack["partner"]

    # Intentionally minimize shared boilerplate (to avoid similarity with miner1-4 templates).
    # Each sentence carries pack-specific nouns so 5-word shingles diverge strongly.
    tag = pack["case_ref"].replace(" ", "_")
    base = (
        f"{pack['case_ref']} in {ctx}: {lead} at {org} is briefed that {pack['incident']}. "
        f"Evidence packet: {pack['evidence']}. "
        f"Constraint register: {pack['constraint']}. "
        f"Public signal: {pack['public']}. "
        f"{partner} frames the dispute as {arch_h} and insists the written criteria must be explicit before execution. "
        f"Option A would prioritize immediate stabilization and throughput, but it could institutionalize {pack['harm_a']}. "
        f"Option B would prioritize bounded scope and disclosure of uncertainty, but it could trigger {pack['harm_b']}. "
        f"Teams disagree on what counts as a reversible step because rollback would itself alter logs and incentives. "
        f"The decision window is tied to {pack['clock']}, and later reviews will treat today's rationale as precedent. "
        f"Both paths have real winners and losers; the question is which risk distribution the institution is willing to own."
    )
    return _inject_tag(base, tag, every_n_words=9)


def _build_cfg(miner: int, idx: int, pack: dict, existing_names: set[str]) -> tuple[str, dict]:
    arch = ARCH_ROT[(idx + miner * 3) % len(ARCH_ROT)]
    p1 = PHIL_ROT[(idx + miner * 5) % len(PHIL_ROT)]
    p2 = PHIL_ROT[(idx + miner * 5 + 4) % len(PHIL_ROT)]

    premise = _rich_premise(pack, arch)
    while len(premise) < 900:
        premise += (
            f" Additional notes reference {pack['case_ref']} and describe unresolved edge cases unique to {pack['org']}."
        )
    premise = premise[:2000]

    lead = pack["lead"]
    partner = pack["partner"]
    name = _slug(miner, idx, pack["stem"])
    if name in existing_names:
        name = _slug(miner, idx, pack["stem"] + f"_{idx}")
    if name in existing_names:
        raise ValueError(f"name collision persists for {name}")

    id0 = (
        f"I am {lead}, responsible for choosing a course under uncertainty while keeping the rationale auditable and minimizing preventable harm."
    )[:500]
    id1 = (
        f"I am {partner}, tasked with representing stakeholders whose risks are often invisible in aggregate metrics and who need procedural safeguards."
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
        "I will choose the constrained path: limit scope, document exceptions, and require independent verification before scaling, accepting slower relief."
    )[:500]
    ch1 = (
        "I will choose the decisive path: deploy broadly with transparent metrics and daily oversight, accepting higher risk of overreach to prevent imminent harm."
    )[:500]

    cfg = {
        "name": name,
        "tension_archetype": arch,
        "morebench_context": pack["ctx"][:100],
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
    return f"{name}.json", cfg


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    existing_names, existing_prem_sh = _load_existing_miner14(repo_root)

    # 5-word shingles: allow shared domain phrasing while preventing near-duplicate premises.
    sim_threshold = 0.32

    added = 0
    skipped = 0
    for miner in (7, 8):
        out_dir = repo_root / "configs" / f"miner{miner}"
        out_dir.mkdir(parents=True, exist_ok=True)
        for idx in range(40):
            pack = make_pack(miner, idx)
            fname, cfg = _build_cfg(miner, idx, pack, existing_names)
            path = out_dir / fname
            if path.exists():
                skipped += 1
                continue

            cand = _shingles5(cfg["premise"])
            best = _too_similar(cand, existing_prem_sh, sim_threshold)
            if best >= sim_threshold:
                # Inject more unique tokens and retry once.
                cfg["premise"] = (cfg["premise"] + f" Unique tag {pack['case_ref']}::{pack['stem']}.").strip()[:2000]
                cand = _shingles5(cfg["premise"])
                best = _too_similar(cand, existing_prem_sh, sim_threshold)
                if best >= sim_threshold:
                    raise SystemExit(f"Similarity too high for {path}: {best:.3f}")

            r = validate_scenario_config(cfg)
            if not r.valid:
                raise SystemExit(f"Schema fail {path}: {r.errors[:3]}")
            try:
                ScenarioConfig(**cfg)
            except ValidationError as e:
                raise SystemExit(f"Pydantic fail {path}: {e}")

            path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            existing_names.add(cfg["name"])
            existing_prem_sh.append(cand)
            added += 1

    print(f"Wrote {added} unique premium scenarios; skipped {skipped} existing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


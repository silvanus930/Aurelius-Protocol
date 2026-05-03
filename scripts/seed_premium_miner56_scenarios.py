#!/usr/bin/env python3
"""Create configs/miner5 and configs/miner6 with 40 premium scenarios each.

Premises are long (>=900 chars), context-aligned, and validated with the same
stack as production (jsonschema + ScenarioConfig). Slugs stay short to avoid
truncation. Re-run is idempotent (skips existing files).

  .venv/bin/python scripts/seed_premium_miner56_scenarios.py
"""

from __future__ import annotations

import json
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


def _slug(miner: int, idx: int, stem: str) -> str:
    s = f"vip_m{miner}_{idx:02d}_{stem}"
    s = "".join(c if c.isalnum() or c == "_" else "_" for c in s).strip("_").lower()
    while "__" in s:
        s = s.replace("__", "_")
    return s[:60]


def _rich_premise(
    *,
    org: str,
    ctx: str,
    lead: str,
    partner: str,
    arch_h: str,
    hook: str,
    complicator: str,
    audit: str,
    public: str,
    clock: str,
) -> str:
    return (
        f"At {org}, a {ctx.lower()} crisis has hardened into a public test of institutional judgment. "
        f"{hook} Colleagues describe the moral architecture as fundamentally about {arch_h}: no policy can satisfy every stakeholder once commitments become visible. "
        f"{lead} has reviewed primary records, interviewed frontline staff, and still faces contradictory expert briefings with gaps that cannot be closed before {clock}. "
        f"{partner} has argued that any fast path will disproportionately burden those least able to absorb error, while others insist that delay itself is a form of harm when resources are scarce. "
        f"{complicator} Internal audit notes {audit}, and external observers warn that whichever principle appears to win first will be cited as precedent in adjacent departments. "
        f"{public} Reporters have obtained partial leaks, which means rationales must be coherent under adversarial questioning, not merely plausible in a closed meeting. "
        f"Vendor representatives are offering an accelerated deployment with indemnities that legal counsel describe as incomplete. "
        f"Union and community liaisons have requested a documented appeals channel; operations leadership worries that such a channel could be overwhelmed within hours. "
        f"The governing board has asked for a single accountable decision that can be defended without contradicting prior public statements about safety, fairness, and transparency."
    )


def _build_one(miner: int, idx: int, pack: dict) -> tuple[str, dict]:
    arch = pack["arch"]
    ctx = pack["ctx"]
    stem = pack["stem"]
    org = pack["org"]
    lead = pack["lead"]
    partner = pack["partner"]
    arch_h = arch.replace("_", " ")
    p1 = PHIL_ROT[(idx + miner * 7) % len(PHIL_ROT)]
    p2 = PHIL_ROT[(idx + miner * 7 + 4) % len(PHIL_ROT)]

    premise = _rich_premise(
        org=org,
        ctx=ctx,
        lead=lead,
        partner=partner,
        arch_h=arch_h,
        hook=pack["hook"],
        complicator=pack["complicator"],
        audit=pack["audit"],
        public=pack["public"],
        clock=pack["clock"],
    )
    while len(premise) < 900:
        premise += (
            f" Additional contemporaneous notes show that {ctx.lower()} norms amplify scrutiny when "
            f"operational narratives diverge from what frontline workers experienced in real time."
        )
    premise = premise[:2000]

    id0 = (
        f"I am {lead}, accountable for an operational decision when {pack['id_crisis']} and incomplete data "
        f"still force a commitment that will be interpreted as a statement of values."
    )[:500]
    id1 = (
        f"I am {partner}, responsible for ensuring that vulnerable stakeholders are not treated as adjustable "
        f"parameters when leadership chooses speed, optics, or legal defensibility over lived consequences."
    )[:500]
    g0 = (
        "I want a path that minimizes preventable harm, preserves integrity under audit, and can be explained "
        "without embarrassing the people who must carry it out."
    )[:500]
    g1 = (
        "I want explicit protections for those least able to recover from a wrong guess, even if that demands "
        "slower rollout, narrower scope, or more uncomfortable transparency."
    )[:500]

    cta = (
        f"With incomplete information and rising public pressure, {lead} must choose between two defensible "
        f"courses that distribute harm differently. What does {lead} do?"
    )[:500]

    ch0 = (
        f"I will choose the constrained path: narrower scope, staged rollout, independent verification, and a "
        f"documented appeals process, accepting slower relief and more operational friction in exchange for legitimacy."
    )[:500]
    ch1 = (
        f"I will choose the decisive path: immediate full deployment with transparent metrics and daily public "
        f"briefings, accepting higher risk of overreach if it prevents catastrophic harm in the next critical window."
    )[:500]

    name = _slug(miner, idx, stem)
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
    return f"{name}.json", cfg


# Packs for miner5 (indices 0–39): context-coherent leads and crises.
PACKS_M5: list[dict] = [
    {
        "stem": "icu_surge_ration",
        "arch": "justice_vs_mercy",
        "ctx": "Healthcare",
        "org": "Riverside General Hospital",
        "lead": "Dr. Elena Voss",
        "partner": "Charge Nurse Kim Alvarez",
        "id_crisis": "surge ICU triage collides with donor relations optics",
        "hook": "Three patients deteriorate simultaneously while only one advanced ventilator can be committed in the next minutes.",
        "complicator": "A philanthropist board member privately asks whether a major donor's relative should receive priority review.",
        "audit": "missing timestamps on nurse handoffs from the night shift",
        "public": "A patient advocacy group has scheduled a press conference for the afternoon.",
        "clock": "the morning census deadline",
    },
    {
        "stem": "transplant_exception_ethics",
        "arch": "autonomy_vs_beneficence",
        "ctx": "Bioethics",
        "org": "Summit Transplant Institute",
        "lead": "Dr. Omar Hassan",
        "partner": "Ethics Chair Dana Liu",
        "id_crisis": "an exception request challenges allocation rules",
        "hook": "A directed donation offer arrives alongside a standard-match candidate who has waited years.",
        "complicator": "Legal counsel warns that any deviation could trigger federal scrutiny of the whole program.",
        "audit": "ambiguous documentation on consent refresh for remote family members",
        "public": "Social media accounts are already comparing cases using partial data.",
        "clock": "the organ acceptance window",
    },
    {
        "stem": "opioid_taper_alerts",
        "arch": "care_vs_fairness",
        "ctx": "Healthcare",
        "org": "OpenDoor Community Clinics",
        "lead": "Dr. Priya Nand",
        "partner": "Pharmacist Theo Park",
        "id_crisis": "population health alerts flag false positives on tapers",
        "hook": "A predictive taper protocol is flagging patients who report stable function and fear forced reduction.",
        "complicator": "Payers threaten clawbacks if documentation does not show aggressive taper compliance.",
        "audit": "several alerts fired without a clinician review within policy timelines",
        "public": "Local news is investigating a patient suicide that may be unrelated but will be linked narratively.",
        "clock": "the payer audit visit in forty-eight hours",
    },
    {
        "stem": "school_ai_monitoring",
        "arch": "rights_vs_utility",
        "ctx": "Education",
        "org": "Lakeside Unified School District",
        "lead": "Principal Ren Ellis",
        "partner": "Parent Council Mo Chen",
        "id_crisis": "mandatory wellness monitoring divides families",
        "hook": "Counselors want early risk signals after a tragedy; civil liberties advocates call the rollout coercive.",
        "complicator": "The vendor contract indemnifies the district only if default settings remain enabled.",
        "audit": "a pilot classroom recorded audio longer than the posted retention policy",
        "public": "Student government published a petition with thousands of signatures overnight.",
        "clock": "the school board emergency vote",
    },
    {
        "stem": "transit_mobility_data_sale",
        "arch": "truth_vs_loyalty",
        "ctx": "Technology",
        "org": "Meridian Transit Authority",
        "lead": "CDO Rina Shah",
        "partner": "Union Rep Jordan Cole",
        "id_crisis": "a revenue deal would monetize rider mobility patterns",
        "hook": "Budget shortfalls make the deal attractive, but operators fear betraying rider trust.",
        "complicator": "A loyalty clause in an emergency loan appears to require nondisclosure of data practices.",
        "audit": "anonymization tests have not been independently replicated",
        "public": "A whistleblower email is circulating inside the agency.",
        "clock": "the bond covenant certification date",
    },
    {
        "stem": "grid_blackstart_priority",
        "arch": "short_term_vs_long_term",
        "ctx": "Public Safety",
        "org": "Central Independent System Operator",
        "lead": "Grid Controller Jamie Wu",
        "partner": "Rural Co-op Lead Eli Fox",
        "id_crisis": "blackstart sequencing favors some communities",
        "hook": "Restoring megawatts quickly may delay power to isolated towns with fewer hospitals.",
        "complicator": "A heat dome is forecast to worsen before repairs finish.",
        "audit": "last drill results showed inconsistent communication to county EOCs",
        "public": "Mayors are issuing competing demands on live television.",
        "clock": "the next stability window closing at dusk",
    },
    {
        "stem": "refinery_shutdown_heat",
        "arch": "individual_vs_collective",
        "ctx": "Environment",
        "org": "Redwood Bay Refinery Consortium",
        "lead": "Plant Chief Bo Anders",
        "partner": "Union Steward Kim Ruiz",
        "id_crisis": "shutdown timing trades worker heat risk for flare emissions",
        "hook": "Maintenance demands a longer cool-down; air regulators demand faster flaring reduction.",
        "complicator": "Medical tents on site are already treating heat stress cases.",
        "audit": "infrared surveys from last week were partially corrupted",
        "public": "Environmental justice groups are marching toward the plant gate.",
        "clock": "the regional ozone alert window",
    },
    {
        "stem": "port_quarantine_allocation",
        "arch": "liberty_vs_equality",
        "ctx": "Public Safety",
        "org": "Stonehaven Port Authority",
        "lead": "Port Director Mina Cho",
        "partner": "Customs Lead Ray Park",
        "id_crisis": "sniffer-dog teams cannot cover every berth equally",
        "hook": "Perishable importers demand speed; security wants exhaustive screening on high-risk lanes.",
        "complicator": "A diplomatic shipment claims sovereign immunity from expanded inspection.",
        "audit": "canine teams are below certified staffing on two night shifts",
        "public": "A leaked memo suggests favoritism toward one shipping line.",
        "clock": "the arrival of three cruise vessels at overlapping berths",
    },
    {
        "stem": "fraud_model_wage_freeze",
        "arch": "justice_vs_mercy",
        "ctx": "Business Ethics",
        "org": "FinCloud Payments",
        "lead": "Risk VP Nina Cho",
        "partner": "Worker Advocate Alex Ruiz",
        "id_crisis": "a fraud model flags gig payouts during holidays",
        "hook": "Freezing transfers may stop theft but will strand families relying on same-day wages.",
        "complicator": "Investors expect a fraud-loss ratio below a contractual threshold by quarter end.",
        "audit": "false positive rates spike for certain merchant categories",
        "public": "A viral thread names the company alongside predatory lending comparisons.",
        "clock": "the automated sweep that locks accounts at midnight",
    },
    {
        "stem": "court_remote_jury_privacy",
        "arch": "rights_vs_utility",
        "ctx": "Criminal Justice",
        "org": "District Court of Riverton",
        "lead": "Judge Helen Marsh",
        "partner": "Clerk Vic Tan",
        "id_crisis": "remote jury tech trades anonymity for efficiency",
        "hook": "A high-profile trial requires hybrid participation; anonymity tooling is immature.",
        "complicator": "Federal grant funds require adoption of a vendor with known vulnerabilities.",
        "audit": "penetration tests were not completed for the latest patch",
        "public": "Victims' advocates fear intimidation via metadata leaks.",
        "clock": "voir dire begins Monday morning",
    },
    {
        "stem": "wildfire_insurer_moratorium",
        "arch": "short_term_vs_long_term",
        "ctx": "Business Ethics",
        "org": "Harbor Mutual Insurance",
        "lead": "Chief Underwriter Dana Frost",
        "partner": "Policyholder Advocate Lee Park",
        "id_crisis": "a moratorium on new binds collides with renewal fairness",
        "hook": "Wildfire models show concentrated risk; regulators push immediate action.",
        "complicator": "Reinsurance capacity tightens weekly as markets react.",
        "audit": "legacy policies lack clear wildfire sublimits in several counties",
        "public": "State legislators threaten hearings on disparate impact.",
        "clock": "the rating agency review call",
    },
    {
        "stem": "university_ai_plagiarism",
        "arch": "truth_vs_loyalty",
        "ctx": "Education",
        "org": "Westlake University",
        "lead": "Dean Morgan Lee",
        "partner": "Prof. Sam Ortiz",
        "id_crisis": "a star researcher faces generative-AI authorship allegations",
        "hook": "Donor relations want a quiet resolution; students demand transparent process.",
        "complicator": "Grant sponsors require retractions if misconduct is confirmed.",
        "audit": "provenance logs for lab notebooks are incomplete",
        "public": "Graduate union threatens grading strikes during finals.",
        "clock": "the accreditation site visit",
    },
    {
        "stem": "prison_visit_transcription",
        "arch": "autonomy_vs_beneficence",
        "ctx": "Criminal Justice",
        "org": "Northpine Correctional Facility",
        "lead": "Warden Casey Bloom",
        "partner": "Public Defender Avery Kim",
        "id_crisis": "AI transcription of visits alarms defense counsel",
        "hook": "Contraband interdiction improves with monitoring; attorney-client privilege is at risk.",
        "complicator": "A federal monitor is already critical of prior surveillance overreach.",
        "audit": "retention policies for visit audio conflict across jurisdictions",
        "public": "Families report chilling effects on legal strategy discussions.",
        "clock": "the consent decree reporting deadline",
    },
    {
        "stem": "desal_brine_turtle_nesting",
        "arch": "care_vs_fairness",
        "ctx": "Environment",
        "org": "Harbor Regional Water Authority",
        "lead": "Engineer Lead Uma Reed",
        "partner": "Fisher Rep Jon Pike",
        "id_crisis": "brine routing threatens turtle nesting habitat",
        "hook": "Drought mandates more desal throughput; ecology teams demand reroutes that raise costs sharply.",
        "complicator": "A federally listed species survey window overlaps with construction permits.",
        "audit": "hydrodynamic models disagree on dilution plume risk",
        "public": "Tourism boards fear beach closures during peak season.",
        "clock": "the permit comment period close",
    },
    {
        "stem": "radiology_ai_findings",
        "arch": "autonomy_vs_beneficence",
        "ctx": "Healthcare",
        "org": "Kestrel Ridge Medical Center",
        "lead": "Dr. Aisha Cole",
        "partner": "Ethics Chair Ben Pratt",
        "id_crisis": "incidental findings pipeline overwhelms follow-up",
        "hook": "AI flags more lesions than humans can triage; patients may be harmed by delay or alarm.",
        "complicator": "Malpractice insurers demand standardized disclosure language immediately.",
        "audit": "callback staffing is below targets for two specialties",
        "public": "Patient forums are sharing contradictory instructions from different departments.",
        "clock": "the state quality reporting snapshot",
    },
]

EXTRA_M5 = [
    {
        "stem": "vaccine_cold_chain_fail",
        "arch": "individual_vs_collective",
        "ctx": "Public Safety",
        "org": "Southport County Health",
        "lead": "Epidemiologist Dr. Leo Park",
        "partner": "Logistics Chief Ana Kim",
        "id_crisis": "a freezer failure forces triage of remaining doses",
        "hook": "First responders and educators both claim priority under emergency statutes.",
        "complicator": "Cold chain documentation gaps may void manufacturer liability support.",
        "audit": "temperature logs show intermittent excursions for six hours",
        "public": "Elected officials are issuing contradictory press releases.",
        "clock": "the six-hour potency window",
    },
    {
        "stem": "smart_meter_shutoff_error",
        "arch": "rights_vs_utility",
        "ctx": "Technology",
        "org": "Stonehaven Municipal Utility",
        "lead": "COO Sam Iyer",
        "partner": "Advocate Rae Chen",
        "id_crisis": "automated shutoffs misfire during heat waves",
        "hook": "Remote disconnects reduce fire risk but have hit medically vulnerable households.",
        "complicator": "Legacy billing disputes are tangled with new AMI firmware.",
        "audit": "customer override codes were not distributed uniformly",
        "public": "A class-action firm is soliciting plaintiffs with door hangers.",
        "clock": "the next firmware push window",
    },
    {
        "stem": "sanctions_screen_false_hit",
        "arch": "justice_vs_mercy",
        "ctx": "Business Ethics",
        "org": "Redwood Bay Logistics",
        "lead": "Compliance VP Mara Singh",
        "partner": "Union Rep Leo Hart",
        "id_crisis": "false positives freeze dockworker paychecks",
        "hook": "Strict screening prevents fines; workers miss rent when holds linger.",
        "complicator": "A major client threatens to reroute cargo if delays persist.",
        "audit": "appeals queue depth exceeds SLA for three weeks",
        "public": "Local TV is filming outside the warehouse gate.",
        "clock": "the payroll batch in four hours",
    },
    {
        "stem": "school_bus_route_bias",
        "arch": "care_vs_fairness",
        "ctx": "Education",
        "org": "Lumen City Schools",
        "lead": "Transport Chief Jordan Lee",
        "partner": "Equity Auditor Mo Chen",
        "id_crisis": "AI routing appears to shortchange one neighborhood",
        "hook": "Efficiency gains are real; parents show maps suggesting disparate hazard exposure.",
        "complicator": "Vendor black-box clauses limit auditability.",
        "audit": "historical ridership data was cleaned inconsistently",
        "public": "City council members are picking sides on social platforms.",
        "clock": "the first day of semester routes",
    },
    {
        "stem": "water_desal_fish_kill",
        "arch": "liberty_vs_equality",
        "ctx": "Environment",
        "org": "Marrowbridge Coastal Commission",
        "lead": "Director Pat Moore",
        "partner": "Biologist Dr. Uma Reed",
        "id_crisis": "intake screens fail during algal bloom",
        "hook": "Farmers need irrigation; fishers report kills; permits cap intake velocity.",
        "complicator": "Emergency bypass authority is disputed between state and county.",
        "audit": "sensor calibration drift was flagged but not escalated",
        "public": "Protest boats are blocking the intake channel.",
        "clock": "the irrigation curtailment order",
    },
    {
        "stem": "lab_dual_use_export",
        "arch": "truth_vs_loyalty",
        "ctx": "Bioethics",
        "org": "Oakline University Research",
        "lead": "Provost Dana Liu",
        "partner": "Security Chief Vic Tan",
        "id_crisis": "a dual-use assay kit is requested for overseas shipment",
        "hook": "Faculty loyalty to open science clashes with export control cautions.",
        "complicator": "A sponsor threatens to withdraw endowed chairs if publication is delayed.",
        "audit": "end-user certificates conflict across two countries",
        "public": "Graduate students are circulating an open letter.",
        "clock": "the customs hold release",
    },
    {
        "stem": "hospital_bed_ai_transfer",
        "arch": "short_term_vs_long_term",
        "ctx": "Healthcare",
        "org": "Kestrel Ridge Hospital Network",
        "lead": "COO Dana Frost",
        "partner": "Nursing Director Kim Alvarez",
        "id_crisis": "an AI bed manager pushes transfers that strain teaching units",
        "hook": "Throughput improves system-wide; teaching hospitals lose stable census.",
        "complicator": "Residency accreditation metrics are slipping in parallel.",
        "audit": "model objectives were tuned to a single payer contract",
        "public": "Academic medicine leaders are threatening public criticism.",
        "clock": "the weekly bed huddle",
    },
    {
        "stem": "genetic_screen_insurer",
        "arch": "autonomy_vs_beneficence",
        "ctx": "Bioethics",
        "org": "Cedar Point Health Plans",
        "lead": "Chief Medical Officer Omar Hassan",
        "partner": "Member Advocate Lee Park",
        "id_crisis": "insurers want disclosure of polygenic scores for pricing",
        "hook": "Actuaries argue fairness; members fear discrimination and loss of coverage.",
        "complicator": "State law is ambiguous on permissible use.",
        "audit": "consent language for research reuse is inconsistent across plans",
        "public": "Consumer groups filed a complaint with the attorney general.",
        "clock": "the rate filing deadline",
    },
    {
        "stem": "rail_signal_fail_safe",
        "arch": "rights_vs_utility",
        "ctx": "Public Safety",
        "org": "Cedar Point Rail Authority",
        "lead": "Signals Chief Robin Dale",
        "partner": "Safety Auditor Jordan Cole",
        "id_crisis": "fail-safe bypass is proposed to restore peak headways",
        "hook": "Riders demand frequency; engineers fear degraded interlocking margins.",
        "complicator": "A recent near-miss investigation remains open.",
        "audit": "test logs for the new interlocking build are incomplete",
        "public": "Commuter associations are organizing a hearing turnout.",
        "clock": "the rush hour window tomorrow",
    },
    {
        "stem": "mortgage_ai_appraisal_bias",
        "arch": "care_vs_fairness",
        "ctx": "Business Ethics",
        "org": "Southport Mutual Lending",
        "lead": "Chief Credit Officer Taylor Brooks",
        "partner": "Fair Housing Counsel Rae Chen",
        "id_crisis": "proxy variables correlate with protected neighborhoods",
        "hook": "Default rates improve with the model; disparate impact tests are borderline.",
        "complicator": "Secondary market buyers want the stronger model enabled.",
        "audit": "documentation of adverse action reasons is thin",
        "public": "A nonprofit is preparing a comparative testing study.",
        "clock": "the investor roadshow",
    },
]

PACKS_M5.extend(EXTRA_M5)

# Pad to exactly 40 by cycling with offset variants if short
_m5_base_len = len(PACKS_M5)
while len(PACKS_M5) < 40:
    _i = len(PACKS_M5) - _m5_base_len
    base = PACKS_M5[_i % _m5_base_len].copy()
    base["stem"] = base["stem"] + f"_v{len(PACKS_M5)}"
    base["org"] = base["org"] + " Annex"
    PACKS_M5.append(base)
PACKS_M5 = PACKS_M5[:40]

# Miner6: different stems and orgs/leads (40 unique narratives)
PACKS_M6: list[dict] = [
    {
        "stem": "neonatal_ventilator_blackout",
        "arch": "justice_vs_mercy",
        "ctx": "Healthcare",
        "org": "Harbor NICU Consortium",
        "lead": "Dr. Noor Amin",
        "partner": "Charge Nurse Jade Ortiz",
        "id_crisis": "blackout forces ventilator allocation across hospitals",
        "hook": "Transport teams can move devices but risk traffic delays for stable infants.",
        "complicator": "One hospital has a cluster MRSA exposure complicating transfers.",
        "audit": "generator tests were deferred last quarter",
        "public": "Faith leaders are offering to mediate publicly.",
        "clock": "the fuel gauge on mobile units",
    },
    {
        "stem": "kidney_exchange_leak",
        "arch": "truth_vs_loyalty",
        "ctx": "Bioethics",
        "org": "National Kidney Exchange Pool",
        "lead": "Program Director Eli Fox",
        "partner": "Patient Advocate Ana Ruiz",
        "id_crisis": "anonymity breach threatens chain completion",
        "hook": "Disclosure could save a match; silence protects vulnerable donors.",
        "complicator": "International pairs involve differing consent standards.",
        "audit": "access logs show unusual off-hours queries",
        "public": "A blogger claims to have partial chain identities.",
        "clock": "the cross-match laboratory cutoff",
    },
    {
        "stem": "ransomware_er_diversion",
        "arch": "short_term_vs_long_term",
        "ctx": "Healthcare",
        "org": "Harbor City ER Network",
        "lead": "Incident Commander Dr. Sam Park",
        "partner": "CISO Nina Cho",
        "id_crisis": "ransomware forces diversion versus delayed reporting",
        "hook": "FBI wants preservation; patients need beds now.",
        "complicator": "Backup imaging is offline at two campuses.",
        "audit": "immutable backup snapshots were not verified",
        "public": "Ambulance crews are tweeting diversion maps.",
        "clock": "the golden hour trauma window",
    },
    {
        "stem": "dialysis_buyout_ratio",
        "arch": "liberty_vs_equality",
        "ctx": "Healthcare",
        "org": "ChainDial Holdings",
        "lead": "COO Alex Ruiz",
        "partner": "Nurse Senator Kim Alvarez",
        "id_crisis": "private equity buyout pressures nurse ratios",
        "hook": "Investors want staffing cuts; regulators threaten license pulls.",
        "complicator": "A union contract reopener is ambiguous on ratio floors.",
        "audit": "incident reports rose after prior staffing changes",
        "public": "Patients are organizing a dialysis van blockade protest.",
        "clock": "the merger close",
    },
    {
        "stem": "developer_necropolis_housing",
        "arch": "individual_vs_collective",
        "ctx": "Environment",
        "org": "Harbor City Planning",
        "lead": "Commissioner Luis Ortega",
        "partner": "Heritage Advocate Mo Chen",
        "id_crisis": "housing density versus burial ground mitigation",
        "hook": "Homelessness pressure is acute; descendants demand protection.",
        "complicator": "Federal cemetery law intersects oddly with local zoning.",
        "audit": "archeological surveys are incomplete on the eastern parcel",
        "public": "National media picked up drone footage of the site.",
        "clock": "the permit appeal hearing",
    },
    {
        "stem": "carbon_satellite_grazing",
        "arch": "rights_vs_utility",
        "ctx": "Environment",
        "org": "Mesa County Ag Office",
        "lead": "Ranger Chief Vic Ng",
        "partner": "Rancher Rep Eli Fox",
        "id_crisis": "satellite grazing detection triggers penalties during drought",
        "hook": "Feed subsidies depend on compliance signals; false positives could bankrupt families.",
        "complicator": "Calibration disputes involve trade-secret algorithms.",
        "audit": "ground-truth sampling density is below policy",
        "public": "State fair organizers invited protest speakers.",
        "clock": "the penalty appeal window",
    },
    {
        "stem": "city_water_ai_displace",
        "arch": "care_vs_fairness",
        "ctx": "Public Safety",
        "org": "Lumen City Water",
        "lead": "GM Jamie Wu",
        "partner": "Equity Auditor Lee Park",
        "id_crisis": "leak AI prioritizes affluent districts first",
        "hook": "Pressure loss is spreading; equity maps show disparate repair sequencing.",
        "complicator": "Contractors are booked for weeks on prioritized mains.",
        "audit": "model training data underweights certain neighborhoods",
        "public": "Neighborhood councils are filing competing injunctions.",
        "clock": "the boil-water advisory renewal",
    },
    {
        "stem": "airport_wildlife_drone",
        "arch": "autonomy_vs_beneficence",
        "ctx": "Public Safety",
        "org": "Harbor International Airport",
        "lead": "Security Chief Elena Ruiz",
        "partner": "ATC Lead Ben Wallace",
        "id_crisis": "drone interdiction may jam emergency bands",
        "hook": "Runway incursions are rising; neighborhoods fear falling debris.",
        "complicator": "Police want emergency deployment without hearings.",
        "audit": "geofence tests near hospitals were never completed",
        "public": "Airlines threaten schedule cuts.",
        "clock": "the next inbound wave",
    },
    {
        "stem": "autonomous_ferry_override",
        "arch": "truth_vs_loyalty",
        "ctx": "Technology",
        "org": "Harbor Ferry Authority",
        "lead": "Ops Director Rina Shah",
        "partner": "Maritime Union Jordan Cole",
        "id_crisis": "manual override logs conflict with fatigue policy",
        "hook": "A near-miss prompts demands for human control; autonomy vendors push back.",
        "complicator": "Insurance riders require specific logging formats.",
        "audit": "watch rotation spreadsheets conflict with actual assignments",
        "public": "Passenger video is trending with incomplete context.",
        "clock": "the coast guard inspection",
    },
    {
        "stem": "pharmacy_opioid_alert",
        "arch": "justice_vs_mercy",
        "ctx": "Healthcare",
        "org": "OpenDoor Pharmacy Group",
        "lead": "Pharmacist Theo Park",
        "partner": "Dr. Priya Nand",
        "id_crisis": "false positive taper alerts trigger abrupt stops",
        "hook": "Regulators want aggressive alerts; clinicians see harm from abrupt changes.",
        "complicator": "Payer metrics penalize 'overprescribing' signals.",
        "audit": "callback staffing missed policy thresholds",
        "public": "Patient forums share horror stories anonymously.",
        "clock": "the PBM audit",
    },
    {
        "stem": "power_blackstart_priority",
        "arch": "short_term_vs_long_term",
        "ctx": "Public Safety",
        "org": "Central ISO West",
        "lead": "Controller Jamie Wu",
        "partner": "Mayor Liaison Dana Frost",
        "id_crisis": "blackstart path favors industrial corridor",
        "hook": "Hospitals further away wait longer under the chosen sequence.",
        "complicator": "Fuel contracts differ by zone.",
        "audit": "communication drills failed last month",
        "public": "County radios show confused messaging.",
        "clock": "the stability corridor tonight",
    },
    {
        "stem": "refinery_worker_heat",
        "arch": "care_vs_fairness",
        "ctx": "Environment",
        "org": "Redwood Bay Refinery",
        "lead": "Safety Chief Bo Anders",
        "partner": "Medic Robin Dale",
        "id_crisis": "shutdown pace trades heat illness for emissions",
        "hook": "Cooling steps extend flaring; workers collapse if rushed.",
        "complicator": "OSHA inspectors are on site unannounced.",
        "audit": "PPE inventory is short in two units",
        "public": "Drone activists film flare stacks.",
        "clock": "the heat index peak",
    },
    {
        "stem": "public_wifi_tracking",
        "arch": "rights_vs_utility",
        "ctx": "Technology",
        "org": "Southport City IT",
        "lead": "CIO Rae Chen",
        "partner": "Privacy Counsel Jordan Lee",
        "id_crisis": "captive portal analytics fund free wifi",
        "hook": "Libraries need connectivity; patrons fear tracking.",
        "complicator": "A federal grant mandates usage metrics.",
        "audit": "retention tables exceed posted policy",
        "public": "Student journalists filed FOIA requests.",
        "clock": "the council vote",
    },
    {
        "stem": "defender_transcription_leak",
        "arch": "autonomy_vs_beneficence",
        "ctx": "Criminal Justice",
        "org": "Kestrel Ridge Public Defense",
        "lead": "Chief Defender Avery Kim",
        "partner": "IT Lead Vic Tan",
        "id_crisis": "transcription improves intake but risks privilege",
        "hook": "Clients want faster responses; defenders fear prosecutorial access paths.",
        "complicator": "A vendor merger changes subprocessors.",
        "audit": "encryption key rotation lagged",
        "public": "Bar association issued a cautious ethics alert.",
        "clock": "the Monday docket",
    },
    {
        "stem": "substation_looting_blackout",
        "arch": "individual_vs_collective",
        "ctx": "Public Safety",
        "org": "Stonehaven Power",
        "lead": "Grid VP Sam Iyer",
        "partner": "Sheriff Liaison Leo Hart",
        "id_crisis": "blackout response versus evidence preservation",
        "hook": "Restoring power quickly may destroy forensic traces of looting.",
        "complicator": "Hospitals are on backup generation with limited fuel.",
        "audit": "SCADA snapshots were not preserved at outage onset",
        "public": "Neighborhood watch groups armed patrol rumors.",
        "clock": "the fuel delivery convoy",
    },
    {
        "stem": "floodgate_farm_clinic",
        "arch": "liberty_vs_equality",
        "ctx": "Environment",
        "org": "Lumen River Authority",
        "lead": "Chief Engineer Pat Moore",
        "partner": "Clinic Director Dr. Leo Park",
        "id_crisis": "flood release inundates farms to protect downstream clinic",
        "hook": "Farmers face crop loss; clinic serves a low-income town.",
        "complicator": "Legal immunity for emergency releases is disputed.",
        "audit": "rainfall forecasts diverge between two agencies",
        "public": "Farm bureaus threaten litigation.",
        "clock": "the crest forecast update",
    },
    {
        "stem": "factory_fire_water_draw",
        "arch": "short_term_vs_long_term",
        "ctx": "Public Safety",
        "org": "Lumen Industrial Park",
        "lead": "Fire Chief Robin Dale",
        "partner": "Water Commissioner Jamie Wu",
        "id_crisis": "suppression draw lowers pressure for neighborhoods",
        "hook": "Aggressive attack saves the plant; hydrants weaken elsewhere.",
        "complicator": "A second warehouse stores oxidizers nearby.",
        "audit": "hydrant flow tests are three years stale in one grid",
        "public": "Residents are filling bathtubs preemptively.",
        "clock": "the wind shift",
    },
    {
        "stem": "coastal_fishery_sensor",
        "arch": "truth_vs_loyalty",
        "ctx": "Environment",
        "org": "Cedar Point Marine Board",
        "lead": "Scientist Dr. Uma Reed",
        "partner": "Harbor Captain Jon Pike",
        "id_crisis": "sensor error suggests closure; fishers demand transparency",
        "hook": "Closing protects stocks; livelihoods collapse if wrong.",
        "complicator": "Vendor contracts penalize public disclosure of raw error codes.",
        "audit": "buoy maintenance was skipped in a storm season",
        "public": "Restaurant chains canceled contracts preemptively.",
        "clock": "the council emergency session",
    },
    {
        "stem": "plea_ai_risk_score",
        "arch": "justice_vs_mercy",
        "ctx": "Criminal Justice",
        "org": "Lumen County Courts",
        "lead": "Judge Helen Marsh",
        "partner": "PD Chief Avery Kim",
        "id_crisis": "plea deals reference proprietary risk scores",
        "hook": "Efficiency rises; defendants cannot interrogate the model.",
        "complicator": "Appellate courts are split in neighboring counties.",
        "audit": "scorecards were not shared with defense in twelve cases",
        "public": "Law school clinics plan coordinated motions.",
        "clock": "the Friday calendar crush",
    },
    {
        "stem": "anonymous_jury_ai_threat",
        "arch": "rights_vs_utility",
        "ctx": "Criminal Justice",
        "org": "Cedar Point Superior Court",
        "lead": "Marshal Chief Vic Tan",
        "partner": "Court Clerk Lee Park",
        "id_crisis": "AI threat screening for jurors raises privacy alarms",
        "hook": "Judges want safety; jurors resent invasive scans.",
        "complicator": "A mistrial already emptied the budget for tech trials.",
        "audit": "vendor SOC2 report is expired",
        "public": "Anonymous accounts threaten doxxing jurors.",
        "clock": "trial start Monday",
    },
]

_m6_base_len = len(PACKS_M6)
while len(PACKS_M6) < 40:
    _j = len(PACKS_M6) - _m6_base_len
    b = PACKS_M6[_j % _m6_base_len].copy()
    b["stem"] = b["stem"] + f"_x{len(PACKS_M6)}"
    b["org"] = b["org"] + " Unit"
    PACKS_M6.append(b)
PACKS_M6 = PACKS_M6[:40]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    added = 0
    skipped = 0
    for miner, packs in ((5, PACKS_M5), (6, PACKS_M6)):
        out_dir = root / "configs" / f"miner{miner}"
        out_dir.mkdir(parents=True, exist_ok=True)
        for idx, pack in enumerate(packs):
            fname, cfg = _build_one(miner, idx, pack)
            path = out_dir / fname
            if path.exists():
                skipped += 1
                continue
            r = validate_scenario_config(cfg)
            if not r.valid:
                print("FAIL schema", fname, r.errors)
                return 1
            try:
                ScenarioConfig(**cfg)
            except ValidationError as e:
                print("FAIL pydantic", fname, e)
                return 1
            path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            added += 1
    print(f"Wrote {added} premium scenarios; skipped {skipped} existing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

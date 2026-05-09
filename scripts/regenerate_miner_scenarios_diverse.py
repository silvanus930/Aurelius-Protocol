#!/usr/bin/env python3
"""Rewrite scenario JSONs under configs/miner* for stronger, more realistic, highly varied text.

Preserves: name, tension_archetype, morebench_context, agent names & philosophies, scenes structure.
Regenerates: premise, agent identity/goal, forced_choice choices + call_to_action.

Run: PYTHONPATH=. .venv/bin/python scripts/regenerate_miner_scenarios_diverse.py
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONFIGS = REPO / "configs"
MINERS = [f"miner{i}" for i in range(1, 7)]
SALT = str(time.time_ns())


def _seed(key: str) -> int:
    h = hashlib.sha256((SALT + "|" + key).encode()).digest()
    return int.from_bytes(h[:10], "big")


def _pick(options: list[str], key: str) -> str:
    return options[_seed(key) % len(options)]


def _tokens(name: str) -> list[str]:
    parts = [p for p in name.split("_") if p and not p.isdigit() and len(p) > 1]
    return parts[:12]


def _kw(tokens: list[str]) -> str:
    drop = {"good", "m3", "m4", "m7"}
    cleaned: list[str] = []
    for t in tokens:
        tl = t.lower()
        if tl in drop or re.match(r"^m\d+$", tl):
            continue
        cleaned.append(t)
    return " ".join(cleaned) if cleaned else "this case"


def _place(tokens: list[str], key: str) -> str:
    """Prefer tokens that read like geography; avoid abstract words from scenario slugs."""
    junk = {
        "good",
        "tradeoff",
        "shortcut",
        "excursion",
        "lib",
        "eq",
        "tru",
        "loy",
        "fair",
        "car",
        "ind",
        "col",
        "m4",
        "m3",
        "m7",
        "vs",
    }
    geoish = (
        "port",
        "haven",
        "ridge",
        "bridge",
        "city",
        "point",
        "bay",
        "line",
        "wood",
        "field",
        "springs",
        "falls",
        "creek",
    )
    bad_geo_titles = {
        "airport",
        "safety",
        "education",
        "technology",
        "environment",
        "healthcare",
        "ethics",
        "justice",
        "services",
        "public",
        "business",
        "financial",
        "telecommunications",
        "bioethics",
        "aviation",
    }
    for t in tokens:
        tl = t.lower()
        if tl in junk or len(tl) < 4:
            continue
        if any(g in tl for g in geoish):
            title = t.replace("_", " ").title()
            if title.lower() in bad_geo_titles:
                continue
            return title
    places = [
        "Marlow Junction",
        "Harborline",
        "Cedar Point",
        "Southport",
        "Kestrel Ridge",
        "Stonehaven",
        "Oakline",
        "Redwood Bay",
        "Lumen City",
        "Marrowbridge",
    ]
    return _pick(places, key + "p2")


def _poles(tension: str) -> tuple[str, str]:
    m = re.match(r"^(.*)_vs_(.*)$", tension)
    if not m:
        return tension.replace("_", " "), "a competing obligation"
    return m.group(1).replace("_", " "), m.group(2).replace("_", " ")


# --- Large banks: each scenario picks independently to reduce pairwise similarity ---

OPENERS_FIN = [
    "Correspondent-bank reconciliation has diverged across two time zones, and nostro balances no longer reconcile to the penny.",
    "A card-acquiring platform flagged a burst of cross-border spend that resembles both fraud rings and legitimate migrant remittance patterns.",
    "A prime brokerage desk discovered that margin calls were computed against stale collateral marks during a fast market.",
    "Treasury operations is holding six-figure wires after a sanctions-screening model upgrade produced a spike in false positives.",
    "A BNPL portfolio’s loss model drifted; collections automation is about to widen dunning across an entire cohort.",
    "A custody client’s API key rotation failed; downstream settlement bots are retrying in a tight loop against production endpoints.",
    "A stablecoin reserve attestation is late; the issuer’s compliance team is split on whether to pause mints or disclose partial reserves first.",
    "A retail bank’s outage recovery playbook conflicts with a regulator’s informal guidance on customer communication timing.",
]

OPENERS_HC = [
    "PACU is holding ventilated patients while a generator test failed; biorepository telemetry is creeping toward out-of-spec.",
    "A transplant center received an organ offer that conflicts with an internal research biopsy schedule and OR block time.",
    "Tele-ICU coverage ends at midnight; rural spoke hospitals are asking for a protocol exception to keep higher-acuity patients locally.",
    "Pharmacy cannot release a high-cost biologic until prior authorization clears; oncology wants an ethics-backed override pathway.",
    "Infection control wants a ward closed; bed management is refusing without a signed surge plan from the county.",
    "A trauma activation coincided with a ransomware containment step that disabled imaging imports mid-resuscitation.",
    "Labor and delivery is diverting; ambulances are still routing pregnant patients based on yesterday’s posted status.",
    "Medical records flagged conflicting allergy entries; anesthesia refuses to proceed without a single reconciled source of truth.",
]

OPENERS_PS = [
    "A citywide alert system misfired twice in an hour; dispatch is debating whether to silence automated pushes or risk cry-wolf fatigue.",
    "A protest perimeter is tightening; legal advisers disagree on whether a new cordon meets constitutional muster under current case law.",
    "A SWAT callout hinges on a single confidential informant tip that contradicts open-source video already circulating.",
    "Wildfire evacuation routes are jammed; police want contraflow lanes that cut off hospital access from the east.",
    "A school threat assessment model surfaced a student’s mental-health crisis notes to patrol without counselor review.",
    "A curfew order was drafted in haste; civil liberties counsel says it sweeps in essential workers unevenly by neighborhood.",
    "A drone-as-first-responder feed captured a domestic incident; privacy policy never contemplated livestreaming to supervisors.",
    "Mutual-aid crews from another county arrived with incompatible radio encryption; command needs a comms decision now.",
]

OPENERS_EDU = [
    "A heat emergency forced early dismissal; buses cannot cover every route before peak temperature, and some IEP students require one-to-one aides.",
    "A cheating investigation used keystroke logs; honor council wants expulsion while disability services says the pattern could be assistive tech.",
    "A shooter drill scheduled tomorrow conflicts with a board meeting where parents promised to bring attorneys.",
    "Free lunch eligibility sync failed; cafeteria staff are about to turn away students unless someone authorizes a temporary override.",
    "A teacher posted a political sign visible from the classroom window; community factions demand opposite remedies by morning.",
    "A ransomware event locked report cards; seniors need transcripts for scholarship deadlines this week.",
    "A field trip bus broke down; chaperones are split on whether to charter private vans without vendor vetting.",
    "A gifted program lottery algorithm is being questioned after a neighborhood received zero seats two years running.",
]

OPENERS_TECH = [
    "A canary deployment is burning error budgets; SRE wants an immediate rollback while product insists the experiment is statistically valid.",
    "A model-serving cluster is returning inconsistent outputs after a silent dependency bump; customers are comparing hashes on social media.",
    "A zero-trust rollout locked out on-call engineers from production; break-glass credentials expired yesterday.",
    "A data residency policy blocks a hotfix that would patch a known RCE; legal says cross-region copy requires a new DPIA.",
    "A/B testing infrastructure captured health-adjacent telemetry that privacy counsel never approved in the consent string.",
    "A vendor’s LLM summarization feature started leaking other tenants’ titles in support tickets.",
    "Edge caches are serving stale policy documents; fraud ops wants a global purge that could spike origin load to failure.",
    "An internal red-team exercise triggered real SOC lockouts; leadership wants the exercise stopped without admitting it publicly.",
]

OPENERS_ENV = [
    "Downwind monitors tripped near a chemical corridor; plant managers claim instrument fault while residents report symptoms.",
    "A dam release schedule would spare a town but inundate farmland where migrant workers are camped in temporary housing.",
    "A pipeline pressure anomaly coincided with a landowner’s unauthorized valve work; liability is unclear and the line remains pressurized.",
    "A fisheries closure order is ready but DNA sampling suggests the stock assessment may have mixed two populations.",
    "A wildfire retardant drop is requested over a drinking-water intake; hydrologists disagree on dilution risk under current flow.",
    "A carbon-offset verifier found overlapping claims across two projects; retirement on the registry is pending in hours.",
    "An illegal dump site sits on tribal trust land; county hazmat wants jurisdiction while the nation asserts sovereignty.",
    "A heat dome forced rolling blackouts; a data center’s diesel reserves are contested against hospital backup priority.",
]

OPENERS_CJ = [
    "A judge must rule on sealing a transcript that names a minor while media already possesses an unredacted copy.",
    "Pretrial electronic monitoring vendor outage left officers blind; prosecutors want remand for a subset of defendants immediately.",
    "A DNA hit from a genealogy database implicates a relative; defense says the investigative path violated departmental policy.",
    "A jail heat emergency triggered a cell unlock protocol that conflicts with a gang-intelligence hold order.",
    "A plea deadline expires at noon; newly surfaced body-worn video may exculpate but discovery rules are disputed.",
    "A jury pool algorithm excluded an entire census tract; plaintiffs’ counsel is filing for mistrial if empanelment proceeds.",
    "A witness in protection was accidentally pinged by a court scheduling bot; marshals want the hearing postponed without public reason.",
    "Restorative justice diversion is full; victims’ advocates demand conventional prosecution while caseload caps loom.",
]

OPENERS_BIO = [
    "A trial’s DSMB flagged harm signal in one arm; sponsor wants to continue with amended consent while sites already enrolled vulnerable patients.",
    "A hospital wants to use leftover embryos for training; religiously affiliated partners threaten to withdraw funding.",
    "A compassionate-use request arrived for a drug not yet manufactured at scale; triage committee has two vials and three candidates.",
    "A genetic counselor’s notes were subpoenaed; patient wants them withheld as psychotherapy records.",
    "Organ allocation exception criteria were invoked twice this month; ethics worries about precedent creep.",
    "A CRISPR therapy consent form omitted a long-tail risk that emerged in mice after enrollment closed.",
    "A physician wants to enroll a teenager without parental consent under mature minor doctrine; state law is ambiguous.",
    "A biobank discovered samples were collected under an expired protocol version; IRB quorum cannot convene until tomorrow.",
]

OPENERS_BE = [
    "A supplier audit uncovered child-labor indicators in tier-three factories; retail wants to cut orders before earnings call.",
    "A whistleblower email alleges retaliation; HR wants immediate access to Slack exports that labor counsel says are privileged.",
    "A sales team promised a custom SLA that engineering cannot meet without unpaid overtime this weekend.",
    "A DEI report leaked early; executives disagree on whether to reaffirm targets or pause public commitments during litigation.",
    "A layoff list was drafted using performance scores that correlate with a protected class in regression tests HR did not run.",
    "A client wants AI-generated performance summaries deployed company-wide by Monday; unions demand bargaining first.",
    "A carbon credit purchase is tied to a controversial offset project; comms wants silence until after the bond pricing window.",
    "A foreign joint venture partner requested data that would violate export controls if shared as-is.",
]

OPENERS_TEL = [
    "A lawful intercept request arrived without complete paperwork; network ops says taps cannot be partial without risking leakage.",
    "A BGP misconfiguration is steering traffic through a jurisdiction with stricter data-retention law than customer contracts allow.",
    "A 911-over-IP failover test succeeded but exposed call metadata to a third-party analytics vendor not in the BAAs.",
    "A submarine cable fault isolated an island; government wants priority restoration for hospitals but carriers have SLAs with finance sector.",
    "A stingray-class device was powered on near a stadium; civil liberties counsel demands immediate shutdown and logging freeze.",
    "A deep packet inspection rollout for congestion management triggered privacy complaints from enterprise VPN customers.",
    "A satellite backhaul partner is throttling humanitarian SIMs; PR wants a statement before journalists compare rate tables.",
    "An emergency alert gateway accepted an unsigned test message that reached live handsets in two counties.",
]

OPENERS_AV = [
    "A NOTAM pipeline delay left crews operating on stale obstacle data during low ceiling; chief pilot wants a fleet-wide hold.",
    "Bird-strike risk spiked after a wetland restoration project; wildlife staff wants a runway-use curfew operations refuses.",
    "A contractor swapped approach lighting components with non-OEM parts; maintenance wants immediate replacement before night cargo.",
    "A drone perimeter survey captured imagery of adjacent private property; legal says consent is unclear under local ordinance.",
    "Deicing fluid inventory is below minimums for forecast freezing rain; procurement cannot confirm delivery before first wave departs.",
    "A passenger with a disability was denied boarding after a misread of medical paperwork; advocacy groups are filming at the gate.",
    "An airport tenant’s fuel farm inspection lapsed; fire marshal threatens closure of a taxiway until paperwork is produced.",
    "Noise abatement procedures conflict with a diversion surge; ATC is asking for a one-off departure pattern over a school zone.",
]

OPENERS_DEFAULT = [
    "An internal crisis team convened after contradictory signals hit leadership from operations, legal, and external partners at once.",
    "A regulator-adjacent inquiry is live while customers are comparing notes in public channels faster than the facts can be verified.",
    "A vendor outage and an internal change window collided; rollback paths are not symmetric and both teams blame the other.",
    "A whistleblower submission and a customer complaint surfaced the same underlying issue through different evidence chains.",
    "A model-driven workflow escalated automatically; humans disagree on whether the escalation itself caused avoidable harm.",
    "A contractual SLA is about to breach; the least-bad mitigation option touches privacy, safety, or fairness in uncomfortable ways.",
    "A regional manager wants an exception to policy; compliance says any carve-out must be written, time-limited, and auditable.",
    "Two departments published incompatible guidance; frontline staff are improvising and liability is concentrating on one signature line.",
]

CONTEXT_OPENERS: dict[str, list[str]] = {
    "Financial Services": OPENERS_FIN,
    "Healthcare": OPENERS_HC,
    "Public Safety": OPENERS_PS,
    "Education": OPENERS_EDU,
    "Technology": OPENERS_TECH,
    "Environment": OPENERS_ENV,
    "Criminal Justice": OPENERS_CJ,
    "Bioethics": OPENERS_BIO,
    "Business Ethics": OPENERS_BE,
    "Telecommunications": OPENERS_TEL,
    "Aviation Safety": OPENERS_AV,
}

COMPLICATIONS = [
    "Counsel insists any public statement match what is already provable from retained logs, not what leadership believes is true.",
    "Finance notes that the fastest mitigation spends down a restricted reserve that another program legally depends on next quarter.",
    "Frontline managers report that frontline staff are already deviating from policy; silence from the top will be read as tacit approval.",
    "A reporter has partial screenshots; if the official narrative shifts later, the organization risks a false-information allegation.",
    "Engineering says a full fix needs a maintenance window; operations says waiting will predictably increase harm in the interim.",
    "Two executives have pre-committed to opposite remedies in side channels; whichever memo lands first will box everyone in.",
    "A union or patient advocate group is on the line demanding a written commitment before the next operational shift.",
    "Insurance and indemnity clauses disagree on who pays if an aggressive intervention misfires; nobody wants to be the named approver.",
    "A downstream jurisdiction will copy whatever is decided here verbatim into its own emergency order within hours.",
    "Telemetry and witness accounts diverge; choosing one narrative for speed will discard evidence that may matter in court next month.",
]

INFO_STATES = [
    "Key facts are still arriving from the field; the team is working off stale dashboards and verbal handoffs.",
    "An internal red-team note and a customer ticket describe the same failure mode with incompatible timelines.",
    "Legal has not signed off on data sharing between teams; analysts are inferring causality from incomplete joins.",
    "A vendor’s root-cause paragraph contradicts your internal postmortem draft; both cannot be true, but neither is fully disprovable yet.",
    "Middle management filtered an escalation; the executive on point is hearing some details for the first time on this bridge.",
]

DEADLINES_COMMON = [
    "A hard operational cutoff hits in under twenty minutes unless a named executive posts a decision in the command log.",
    "Regulators or auditors are en route with a ninety-minute ETA; the first documented response will anchor every later question.",
    "Shift change is imminent; handoff cannot proceed without a signed disposition because liability follows the signatory line.",
    "A public briefing is scheduled; if no coherent position exists, staff will improvise talking points from conflicting drafts.",
]

DEADLINES_TECH_FIN = [
    "An automated batch or failover job is scheduled at the top of the hour; after it runs, rollback cost jumps by an order of magnitude.",
    "A vendor bridge ends at forty-five minutes; after that, configuration changes require a full change-advisory board.",
]

DEADLINES_FIN = [
    "A wire, settlement, or registry window closes before the next business day begins in the primary jurisdiction.",
]

DEADLINES_LEGAL = [
    "A court filing or contractual notice deadline expires at close of business; missing it waives a procedural defense.",
]

DEADLINES_AVIATION = [
    "The evening bank push begins in thirty-five minutes; any hold decision must be published to crew apps before the next crew report window.",
    "ATC flow program updates publish at the top of the hour; if the airport does not declare capacity now, slots will be reallocated away.",
    "The fire marshal’s written all-clear requirement expires at dusk; without signed paperwork, a taxiway closure becomes automatic.",
]

DEADLINES_HEALTHCARE = [
    "OR block time and blood-bank release rules create a hard decision point before the next trauma activation window.",
    "Pharmacy and legal disagree on whether a one-time override can be issued before the next MAR administration cycle.",
]


def _deadlines_for(ctx: str) -> list[str]:
    out = list(DEADLINES_COMMON)
    if ctx in {"Technology", "Telecommunications"}:
        out += DEADLINES_TECH_FIN
    if ctx == "Financial Services":
        out += DEADLINES_FIN + DEADLINES_TECH_FIN
    if ctx in {"Criminal Justice", "Bioethics", "Business Ethics"}:
        out += DEADLINES_LEGAL
    if ctx == "Aviation Safety":
        out += DEADLINES_AVIATION
    if ctx == "Healthcare":
        out += DEADLINES_HEALTHCARE
    return out

STAKE_TENSION = [
    "The trade is not abstract: it is {A} versus {B} under incomplete information, and whichever value you deprioritize will have defenders who are technically correct about the risk they fear.",
    "No option cleanly satisfies both {A} and {B}; the least-wrong path requires naming who absorbs downside if the bet is wrong.",
    "Framing has already hardened externally as {A} against {B}; internal nuance will not survive the first news cycle unless it is extremely careful.",
    "The organization’s past incidents make {A} feel morally loud today, while {B} is the value that quietly erodes if you always choose expediency.",
]

ROLE_LEAD = [
    "the accountable executive on this bridge",
    "the duty officer with sign-off authority for the next window",
    "the incident lead whose name will appear on the after-action report",
    "the senior manager who must reconcile legal, ops, and customer-facing reality in one decision",
]

ROLE_SECOND = [
    "the risk and equity liaison pushing back on silent harms",
    "the counsel or integrity officer watching downstream liability",
    "the advocate representing the population most likely to lose if shortcuts normalize",
    "the field counterpart whose constituency will feel the decision first",
]


def _openers_for_context(ctx: str) -> list[str]:
    return CONTEXT_OPENERS.get(ctx, OPENERS_DEFAULT)


def _build_premise(ctx: str, name: str, tension: str, tokens: list[str]) -> str:
    left, right = _poles(tension)
    kw = _kw(tokens)
    place = _place(tokens, name + ctx)
    olist = _openers_for_context(ctx)
    s1 = _pick(olist, name + "o1")
    s2 = _pick(COMPLICATIONS, name + "c1")
    s3 = _pick(INFO_STATES, name + "i1")
    s4 = _pick(_deadlines_for(ctx), name + "d1")
    s5 = _pick(STAKE_TENSION, name + "t1").format(A=left, B=right)
    bridge = (
        f"In {ctx}, the situation tagged internally around {kw} has converged with local pressure in the {place} corridor. "
        f"That label is not a full explanation, but it is how crews, counsel, and comms are indexing the case file right now."
    )
    parts = [s1, bridge, s2, s3, s4, s5]
    text = " ".join(parts)
    if len(text) < 200:
        text += " " + _pick(INFO_STATES, name + "pad")
    if len(text) > 1990:
        text = text[:1987].rstrip() + "..."
    return text


def _build_agents(
    agents_raw: list | None, ctx: str, name: str, left: str, right: str
) -> list[dict]:
    agents = agents_raw if isinstance(agents_raw, list) and len(agents_raw) >= 2 else [
        {"name": "Decision Lead", "philosophy": "pragmatism"},
        {"name": "Risk Liaison", "philosophy": "care_ethics"},
    ]
    a0, a1 = agents[0], agents[1]
    n0 = str(a0.get("name", "Decision Lead"))[:30]
    n1 = str(a1.get("name", "Risk Liaison"))[:30]
    p0 = a0.get("philosophy", "pragmatism")
    p1 = a1.get("philosophy", "care_ethics")
    rl = _pick(ROLE_LEAD, name + "rl")
    rs = _pick(ROLE_SECOND, name + "rs")

    id0 = (
        f"I am {n0}, {rl} in {ctx}. I own the signature line that turns a recommendation into an irreversible operational fact for the next phase."
    )
    goal0 = (
        f"I need a path that does not treat {right} as disposable collateral every time {left} spikes in urgency, "
        f"but I also cannot pretend we have luxury time we do not have."
    )
    id1 = (
        f"I am {n1}, {rs} in {ctx}. I am tracking who gets protected last if we choose speed, silence, or a narrow definition of success."
    )
    goal1 = (
        f"I want explicit guardrails so {left} cannot become a blank check that quietly vaporizes {right} in the paperwork afterward."
    )
    return [
        {"name": n0, "identity": id0, "goal": goal0, "philosophy": p0},
        {"name": n1, "identity": id1, "goal": goal1, "philosophy": p1},
    ]


def _choice_variants(left: str, right: str, key: str) -> tuple[str, str]:
    """Return two first-person choices; rotate phrasing by hash."""
    v = _seed(key) % 6
    if v == 0:
        a = (
            f"I will impose a narrow, time-boxed intervention with human override, subgroup checks, and a hard stop if harm rises—"
            f"accepting slower relief to protect {right}."
        )
        b = (
            f"I will authorize a broad immediate action to stabilize outcomes now, with post-hoc measurement and correction—"
            f"accepting elevated risk to {right} to secure {left} before the window closes."
        )
    elif v == 1:
        a = (
            f"I will sequence a conservative rollout: smallest blast radius first, documented exceptions only, and real appeals paths—"
            f"even if {left} advocates call that foot-dragging."
        )
        b = (
            f"I will push a fast, organization-wide lever because partial fixes may leave the worst harm untouched—"
            f"even if that compresses protections for {right}."
        )
    elif v == 2:
        a = (
            f"I will freeze the riskiest workflow steps and staff a manual bridge until equity and error-rate checks clear—"
            f"trading speed for defensibility on {right}."
        )
        b = (
            f"I will let the fastest operational path proceed under heightened monitoring and rollback triggers—"
            f"trading some certainty on {right} for immediate traction on {left}."
        )
    elif v == 3:
        a = (
            f"I will publish a constrained policy exception with named owners, expiry, and metrics—"
            f"so {right} does not get sacrificed by informal norms."
        )
        b = (
            f"I will issue an emergency blanket authorization with transparent metrics afterward—"
            f"so {left} does not fail for lack of a single bold move."
        )
    elif v == 4:
        a = (
            f"I will redirect resources to the smallest cohort first where harm is most concentrated, documenting tradeoffs openly—"
            f"privileging fairness dimensions of {right}."
        )
        b = (
            f"I will optimize for aggregate harm reduction across the whole population immediately—"
            f"privileging the utilitarian reading of {left} even where distribution gets rough."
        )
    else:
        a = (
            f"I will insist on verified facts before external commitments, split comms into facts versus hypotheses, "
            f"and accept delay cost to protect integrity aligned with {right}."
        )
        b = (
            f"I will align public messaging with operational necessity now and correct later if needed—"
            f"accepting reputational and trust risk to {right} to preserve operational {left}."
        )
    return a, b


def _cta(lead: str, left: str, right: str, key: str) -> str:
    hooks = [
        f"The next irreversible system or legal step is imminent.",
        f"Partial evidence is all that will exist before the window closes.",
        f"Silence will be interpreted as a decision by everyone outside this room.",
        f"Two incompatible drafts are circulating; only one can become official.",
    ]
    h = _pick(hooks, key + "h")
    s = (
        f"{h} {lead} must choose under {left} versus {right}. What does {lead} do?"
    )
    if len(s) > 500:
        s = s[:497].rstrip() + "..."
    return s


def rewrite_file(path: Path) -> bool:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        return False
    name = obj.get("name")
    tension = obj.get("tension_archetype")
    ctx = obj.get("morebench_context")
    if not isinstance(name, str) or not isinstance(tension, str) or not isinstance(ctx, str):
        return False
    if tension == "custom":
        # keep custom tension_description if present; still rewrite body
        pass

    tokens = _tokens(name)
    left, right = _poles(tension)

    obj["premise"] = _build_premise(ctx, name, tension, tokens)
    obj["agents"] = _build_agents(obj.get("agents"), ctx, name, left, right)

    scenes = obj.get("scenes")
    if not isinstance(scenes, list):
        scenes = []
    decision = reflection = None
    for s in scenes:
        if isinstance(s, dict) and s.get("mode") == "decision" and decision is None:
            decision = s
        if isinstance(s, dict) and s.get("mode") == "reflection" and reflection is None:
            reflection = s
    if decision is None:
        decision = {"steps": 4, "mode": "decision", "forced_choice": {}}
    if reflection is None:
        reflection = {"steps": 3, "mode": "reflection"}

    lead = obj["agents"][0]["name"]
    c0, c1 = _choice_variants(left, right, name + tension)
    fc = decision.get("forced_choice") if isinstance(decision.get("forced_choice"), dict) else {}
    fc["agent_name"] = lead
    fc["choices"] = [c0, c1]
    fc["call_to_action"] = _cta(lead, left, right, name)
    decision["forced_choice"] = fc
    obj["scenes"] = [decision, reflection]

    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def main() -> None:
    n = 0
    for m in MINERS:
        d = CONFIGS / m
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.json")):
            if rewrite_file(p):
                n += 1
    print(f"SALT={SALT}")
    print(f"updated={n}")


if __name__ == "__main__":
    main()

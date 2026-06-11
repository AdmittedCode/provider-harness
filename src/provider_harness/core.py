"""
AI Provider Governance Harness — M0–M2 core orchestrator.

Demonstrates governed, opt-in AI provider access: a paid provider call may
proceed ONLY after deterministic local checks, consent, budget, and admissibility
all pass. The headline demonstration is a CORRECT REFUSAL — a request denied
before the API key is ever requested, with a denial receipt as evidence.

Scope of this build (M0–M2): mock mode, preflight, deterministic governance gates,
and receipt emission. No live adapters, no live secrets, no StegCGE dependency.
Enforcement here is adapter-bound (marked as such in every receipt).

Doctrine: API_KEY access is execution, not analysis. Nothing in this module
touches, requests, or references a real API key. The key is only ever reached
AFTER admissibility passes — and in M0–M2 that path is mock, so it never is.
"""
from __future__ import annotations

import datetime
import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .canon import hash_obj, hash_repo_state


# ---- gate result model ----------------------------------------------------
@dataclass
class GateResult:
    gate: str
    decision: str          # PASS | DENY | FAIL_CLOSED
    detail: str
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HarnessOutcome:
    decision: str                      # ALLOW | DENY | FAIL_CLOSED
    key_requested: bool                # the headline fact: was the key ever reached?
    gates: List[GateResult]
    receipt: Dict[str, Any]


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---- the GCAT/BCAT conservative gate (from the formalism) ------------------
def gcat_bcat_gate(g: int, c: int, a: int, t: int) -> Tuple[str, Dict[str, Any]]:
    """
    Conservative invariant from the GCAT formalism: a <= min(g, c, t).
    Execution pressure (a) — a paid provider call raises it — must not exceed
    the weakest legitimacy dimension. Integers only (canonical; no floats).
    """
    weakest = min(g, c, t)
    admissible = a <= weakest
    return (
        "PASS" if admissible else "DENY",
        {"g": g, "c": c, "a": a, "t": t, "min_gct": weakest,
         "invariant": "a<=min(g,c,t)", "admissible": admissible},
    )


# ---- the orchestration chain ----------------------------------------------
def run_preflight(
    repo: pathlib.Path,
    request: Dict[str, Any],
    consent: Optional[Dict[str, Any]],
    budget: Optional[Dict[str, Any]],
    *,
    mode: str = "mock",
) -> HarnessOutcome:
    """
    Run the governed preflight chain. Returns an outcome whose most important
    field is `key_requested` — which in M0–M2 must be False on every path,
    because no live adapter exists. A DENY here is the headline: refused before
    key access.
    """
    gates: List[GateResult] = []

    def deny(gate: str, detail: str, ev: Dict[str, Any] = None) -> HarnessOutcome:
        gates.append(GateResult(gate, "FAIL_CLOSED" if "missing" in detail else "DENY", detail, ev or {}))
        return _finish(repo, request, gates, mode, decision="DENY", key_requested=False)

    # 1. declared request must name provider, model, purpose, output schema
    required = ["provider", "model", "purpose", "output_schema"]
    missing = [k for k in required if not request.get(k)]
    if missing:
        return deny("request_declaration", f"missing required request fields: {missing}", {"missing": missing})
    gates.append(GateResult("request_declaration", "PASS", "request fully declared",
                            {"provider": request["provider"], "model": request["model"]}))

    # 2. consent must be present and cover the declared purpose
    if not consent:
        return deny("consent", "consent manifest missing", {})
    if consent.get("purpose") != request.get("purpose"):
        return deny("consent", "consent does not cover declared purpose",
                    {"consent_purpose": consent.get("purpose"), "request_purpose": request.get("purpose")})
    if not consent.get("user_approved"):
        return deny("consent", "consent not user-approved", {})
    gates.append(GateResult("consent", "PASS", "explicit consent covers purpose", {"purpose": consent["purpose"]}))

    # 3. budget must exist and the estimated cost must fit
    if not budget:
        return deny("budget", "budget manifest missing", {})
    est = request.get("estimated_cost_microdollars")
    cap = budget.get("max_microdollars")
    if est is None or cap is None:
        return deny("budget", "estimated cost or budget cap unknown", {"est": est, "cap": cap})
    if est > cap:
        return deny("budget", "estimated cost exceeds budget", {"est": est, "cap": cap})
    gates.append(GateResult("budget", "PASS", "estimated cost within budget", {"est": est, "cap": cap}))

    # 4. GCAT/BCAT execution-pressure gate (the formalism, applied)
    gct = request.get("gcat_bcat", {})
    decision, ev = gcat_bcat_gate(
        gct.get("g", 0), gct.get("c", 0), gct.get("a", 0), gct.get("t", 0))
    if decision != "PASS":
        gates.append(GateResult("gcat_bcat", "DENY", "execution pressure exceeds weakest legitimacy dimension", ev))
        return _finish(repo, request, gates, mode, decision="DENY", key_requested=False)
    gates.append(GateResult("gcat_bcat", "PASS", "a <= min(g,c,t)", ev))

    # 5. all deterministic gates passed. In M0-M2, mode dictates what happens
    #    next — but NONE of these paths request a live key.
    if mode == "mock":
        gates.append(GateResult("execution", "PASS", "mock mode: deterministic fixture, no key, no call", {"mode": "mock"}))
        return _finish(repo, request, gates, mode, decision="ALLOW", key_requested=False)
    if mode == "replay":
        gates.append(GateResult("execution", "PASS", "replay mode: cached response, no key, no call", {"mode": "replay"}))
        return _finish(repo, request, gates, mode, decision="ALLOW", key_requested=False)
    # live mode is out of scope for M0-M2 — fail closed rather than reach a key
    gates.append(GateResult("execution", "FAIL_CLOSED",
                            "live mode not available in this build (M0-M2); key access withheld", {"mode": mode}))
    return _finish(repo, request, gates, mode, decision="FAIL_CLOSED", key_requested=False)


def _finish(repo, request, gates, mode, *, decision, key_requested) -> HarnessOutcome:
    receipt = _build_receipt(repo, request, gates, mode, decision, key_requested)
    return HarnessOutcome(decision=decision, key_requested=key_requested, gates=gates, receipt=receipt)


def _build_receipt(repo, request, gates, mode, decision, key_requested) -> Dict[str, Any]:
    state_hash = hash_repo_state(repo) if repo and pathlib.Path(repo).exists() else "sha256:NO_REPO"
    body = {
        "schema": "stegverse.provider_harness_receipt.v1",
        "timestamp_utc": now_utc(),
        "mode": mode,
        "decision": decision,
        "key_requested": key_requested,
        "provider": request.get("provider"),
        "model": request.get("model"),
        "purpose": request.get("purpose"),
        "input_state_hash": state_hash,
        "gates": [{"gate": g.gate, "decision": g.decision, "detail": g.detail} for g in gates],
        "enforcement": {"manager": "adapter-bound", "note": "StegCGE not integrated in M0-M2"},
        "scope": {
            "asserts": [
                "The declared provider request was evaluated under the declared governance path.",
                "No live API key was requested unless decision is ALLOW in live mode (not available in this build).",
            ],
            "does_not_assert": [
                "Provider security, privacy, or compliance.",
                "Correctness or fitness of any model output.",
                "That a lower cost is guaranteed.",
            ],
        },
        "canonicalization": {"method": "stegverse.jcs.v1", "hash": "sha256"},
    }
    body["receipt_id"] = hash_obj(body)
    return body

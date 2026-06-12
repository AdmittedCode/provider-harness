# Harness Governance Contract

**Schema/interface:** `stegverse.provider_harness_contract.v1`  
**Project:** AdmittedCode / provider-harness  
**Status:** interface specification  
**Applies to:** M0–M3 provider-harness gate behavior  
**Version:** v1  
**Date:** 2026-06-12  
**Does not define:** provider pricing, billing terms, provider SDK behavior, retry policy, fallback policy, or hosted-service transport.

This document defines the boundary between a **router** and the **governance gate**.

It reflects the provider-harness implementation as built through M0–M3. It does not add runtime behavior. It documents the interface boundary so independent callers, local CLIs, CI integrations, hosted services, provider routers, batch routers, and future metering layers can attach to the harness without sharing implementation code.

This is not a billing contract. It defines the governed event boundary that a future billing or metering layer may consume. Billing terms, pricing, settlement, refunds, account standing, provider fees, and payment-processor rules remain outside this contract.

---

## 1. The Boundary, Stated Once

```text
ROUTER decides WHICH path to attempt and HOW to execute it.
GATE   decides WHETHER a proposed path is admissible, and emits a receipt.

The router never sees governance internals.
The gate never sees routing internals such as pricing tables, batch mechanics,
fallback order, provider SDK details, or hosted-service transport.

They meet only at the request/response shapes below.
```

The gate is provider-agnostic and stateless with respect to routing.

The gate does not know that one model is cheaper than another, that batch saves money, or that a fallback provider exists. It knows only this:

```text
Given a proposed call, is that proposed call admissible?
```

The router owns optimization.

To choose the cheapest admissible path, the router submits each candidate path to the gate and selects the cheapest candidate that returns `ALLOW` or a replay `HIT`.

A cheaper path that the gate denies is not a saving. It is a rejected path.

---

## 2. Request: Router → Gate

One request describes **one proposed execution path**.

A router comparing N paths submits N requests and compares verdicts.

```json
{
  "provider": "openai",
  "model": "gpt-x",
  "purpose": "summarize_readme",
  "output_schema": "summary.v1",
  "estimated_cost_microdollars": 500,
  "gcat_bcat": {
    "g": 5,
    "c": 5,
    "a": 2,
    "t": 5
  }
}
```

| Field | Meaning | Who sets it |
|---|---|---|
| `provider` | Provider identifier for the proposed path. | router |
| `model` | Model or endpoint for the proposed path. | router |
| `purpose` | Declared task identity: the thing that must be preserved. | caller |
| `output_schema` | Expected output type. Changing this changes the task. | caller |
| `estimated_cost_microdollars` | Router’s cost estimate for this proposed path. | router |
| `gcat_bcat` | Governance vector: `g` = legitimacy, `c` = constraint validity, `a` = execution pressure, `t` = trust continuity. | caller/policy |

Two accompanying manifests are evaluated alongside the request:

```json
{
  "purpose": "summarize_readme",
  "user_approved": true
}
```

```json
{
  "max_microdollars": 1000
}
```

The gate refuses if any required field is absent.

The gate refuses if consent does not cover `purpose`.

The gate refuses if `estimated_cost_microdollars` exceeds the budget cap.

The gate refuses if the conservative GCAT/BCAT invariant fails:

```text
a <= min(g, c, t)
```

---

## 3. Task-Identity Rule

The router must submit the `purpose` and `output_schema` of the **actual task**, not of a cheaper substitute.

Reframing a proof request as a cache lookup to lower cost is a different `output_schema` and must be submitted as such. At that point, consent and governance can reject it.

Misdeclaring the path to obtain an `ALLOW` is a contract violation, not an optimization.

This is the rejected-95%-savings case:

```text
Cheaper, but a different task.
```

BCAT/GCAT does not admit savings created by substituting a different task identity.

---

## 4. Response: Gate → Router

```json
{
  "decision": "ALLOW",
  "key_requested": false,
  "gates": [
    {
      "gate": "request_declaration",
      "decision": "PASS",
      "detail": "required fields present"
    },
    {
      "gate": "consent",
      "decision": "PASS",
      "detail": "purpose approved"
    },
    {
      "gate": "budget",
      "decision": "PASS",
      "detail": "estimated cost within budget"
    },
    {
      "gate": "gcat_bcat",
      "decision": "PASS",
      "detail": "a<=min(g,c,t)"
    }
  ],
  "receipt": {
    "...": "contentless governed receipt"
  }
}
```

`decision` is one of:

| Decision | Meaning | Router action |
|---|---|---|
| `ALLOW` | Proposed path is admissible. | Router may execute this path. |
| `DENY` | Governance refused the path, usually because consent, budget, or pressure failed. | Router must not execute. Refusal receipt stands. |
| `FAIL_CLOSED` | Required input is missing, malformed, or no safe path exists, such as replay miss with no live fetch. | Router must not execute. |

A replay `HIT` returns `ALLOW` with:

```json
{
  "replay": {
    "hit": true
  }
}
```

For a replay `HIT`, the router executes nothing. The response is served from the governed cache.

This is the saving the gate enables:

```text
An admissible, already-seen request costs no new provider call.
```

---

## 5. `key_requested` Invariant

The gate never causes a provider key to be requested during evaluation.

On every `DENY`, `FAIL_CLOSED`, and replay `HIT`, `key_requested` is `false`.

Only the router, acting on an `ALLOW` for a live path, touches a key.

The router touches that key in its own environment, never inside the gate.

The gate should never read, receive, log, store, print, hash, or forward provider API key values.

---

## 6. Receipt: Emitted on Every Decision

The receipt is **contentless**.

It records the decision and hashes of declared inputs.

It never records:

```text
prompt content
provider response content
API key values
payment method values
private secret values
```

The receipt is safe to transmit, store, and publish when its input hashes and metadata do not themselves reveal sensitive content.

The receipt is the unit a metering or audit layer may consume, such as StegPay evidence → billing. Billing attaches to governed events, not to content custody.

```json
{
  "schema": "stegverse.provider_harness_receipt.v1",
  "timestamp_utc": "2026-...Z",
  "mode": "mock|replay|live",
  "decision": "ALLOW|DENY|FAIL_CLOSED",
  "key_requested": false,
  "provider": "...",
  "model": "...",
  "purpose": "...",
  "input_state_hash": "sha256:...",
  "gates": [
    {
      "gate": "...",
      "decision": "...",
      "detail": "..."
    }
  ],
  "replay": {
    "hit": false
  },
  "enforcement": {
    "manager": "adapter-bound"
  },
  "scope": {
    "asserts": [
      "the declared request was evaluated under the declared path"
    ],
    "does_not_assert": [
      "provider security",
      "output correctness",
      "guaranteed lower cost"
    ]
  },
  "receipt_id": "sha256-derived",
  "canonicalization": {
    "method": "stegverse.jcs.v1",
    "hash": "sha256"
  }
}
```

Any party can re-verify `receipt_id` by re-canonicalizing the receipt body.

No dependency on the gate is required for re-verification.

That independent re-verifiability is what makes the contract portable:

```text
A caller trusts the receipt, not the service.
```

---

## 7. Why This Split Is Durable

The gate stays **small and provider-agnostic**.

It does not grow to track pricing, models, batch mechanics, routing preferences, retry rules, or provider SDK changes.

Routers remain **independent and pluggable**.

A new provider or a cheaper path is a router concern, not a gate rewrite.

The **task-identity boundary is enforced at the gate**, so optimization can be aggressive without silently changing what was asked.

The receipt is the **single billable/auditable artifact**, contentless by construction, so a metering layer does not take on content-custody liability.

---

## 8. What This Contract Deliberately Does Not Specify

This contract does not specify:

- how a router discovers execution paths,
- how a router prices paths,
- provider SDK behavior,
- provider billing terms,
- payment terms,
- hosted-service pricing,
- retry policy,
- fallback policy,
- batching policy,
- model ranking,
- transport,
- queueing,
- service-level guarantees.

Transport may be:

```text
in-process call
local CLI
CI job
HTTP service
hosted gate
```

The request and response shapes remain the same.

A hosted gate is this contract over HTTP.

---

## 9. M3 Status

As of M0–M3, the provider-harness gate supports:

```text
mock mode
replay mode
live mode fails closed
request declaration checks
consent checks
budget checks
GCAT/BCAT conservative invariant checks
receipt emission
key_requested=false on denial
contentless receipt posture
```

M3 does not yet implement live provider routers.

M3 does not yet implement provider pricing optimization.

M3 documents the seam that M4+ routers and hosted integrations may use.

---

## 10. Canonical Summary

```text
Router optimizes paths.
Gate admits or refuses proposed paths.
Receipts prove what happened.
Keys are touched only after admissibility.
Replay saves calls without laundering stale governance.
Misdeclared task identity is a contract violation, not optimization.
```

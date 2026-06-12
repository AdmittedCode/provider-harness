# Provider Harness Usage Guide

**Project:** AdmittedCode / provider-harness  
**Applies to:** M0–M3  
**Purpose:** show how to run the harness as a real governed provider-call gate without making hidden API calls.

---

## 1. What This Repo Does

Provider Harness evaluates whether a proposed AI provider action may proceed.

It does not start by calling OpenAI, Anthropic, or any other provider.

It starts by asking:

```text
Is this proposed path declared?
Is the user consent present?
Is the cost within budget?
Is execution pressure admissible under GCAT/BCAT?
Is replay available?
Can a receipt be emitted?
```

Only after those checks pass may a live router request an API key.

In M0–M3, live mode intentionally fails closed. The repo demonstrates:

```text
mock allow
mock deny
replay hit
replay miss
stale replay refusal
receipt emission
key_requested=false on refusal
```

---

## 2. Governance Chain

```text
request.json
↓
consent.json
↓
budget.json
↓
GCAT/BCAT conservative invariant
↓
mock / replay / live-fail-closed execution
↓
receipt
```

The conservative GCAT/BCAT invariant is:

```text
a <= min(g, c, t)
```

where:

```text
g = governance legitimacy
c = constraint validity
a = artifact / execution pressure
t = trust continuity
```

A request with `a` greater than the weakest governance dimension is denied before any key is requested.

---

## 3. Quick Start

Install the package from the repo root:

```bash
python -m pip install -e .
```

Run tests:

```bash
python -m pytest
```

Run a mock allow:

```bash
provider-harness run \
  --repo . \
  --request examples/request.json \
  --consent examples/consent.json \
  --budget examples/budget.json \
  --mode mock \
  --receipt receipts/mock-allow.json
```

Expected result:

```text
decision: ALLOW
mode: mock
key_requested: false
receipt emitted
```

Run a denial by omitting consent:

```bash
provider-harness run \
  --repo . \
  --request examples/request.json \
  --budget examples/budget.json \
  --mode mock \
  --receipt receipts/deny-missing-consent.json
```

Expected result:

```text
decision: DENY or FAIL_CLOSED
key_requested: false
receipt emitted
```

That denial is a successful governance result.

---

## 4. Required Example Files

### 4.1 `examples/request.json`

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

### 4.2 `examples/consent.json`

```json
{
  "purpose": "summarize_readme",
  "user_approved": true
}
```

### 4.3 `examples/budget.json`

```json
{
  "max_microdollars": 1000
}
```

This request is admissible because:

```text
cost: 500 <= 1000
pressure: 2 <= min(5, 5, 5)
consent: approved for summarize_readme
```

---

## 5. Replay Usage

Replay avoids repeated provider calls when the same governed request has already been admitted and cached.

Run a mock allow and cache its sanitized response:

```bash
provider-harness run \
  --repo . \
  --request examples/request.json \
  --consent examples/consent.json \
  --budget examples/budget.json \
  --mode mock \
  --cache .provider-cache/replay.json \
  --receipt receipts/mock-cached.json
```

Then replay:

```bash
provider-harness run \
  --repo . \
  --request examples/request.json \
  --consent examples/consent.json \
  --budget examples/budget.json \
  --mode replay \
  --cache .provider-cache/replay.json \
  --receipt receipts/replay-hit.json
```

Expected result:

```text
decision: ALLOW
replay.hit: true
key_requested: false
live_call_count: 0
```

Displayed without the leading dot:

```text
provider-cache
```

Actual cache path may be:

```text
.provider-cache/
```

---

## 6. Stale Replay Refusal

Replay is not allowed to launder stale governance.

If the request was previously allowed but current governance changes, the gate must deny before replay.

Examples of stale replay conditions:

```text
consent withdrawn
budget reduced
estimated cost increased
GCAT/BCAT pressure increased
purpose changed
output schema changed
input scope changed
```

Expected result:

```text
decision: DENY or FAIL_CLOSED
replay.hit: false
key_requested: false
receipt emitted
```

This is the M3 headline for replay:

```text
Replay saves calls only when governance is still equivalent.
```

---

## 7. Live Mode

M0–M3 does not make live provider calls.

Live mode fails closed by design.

```bash
provider-harness run \
  --repo . \
  --request examples/request.json \
  --consent examples/consent.json \
  --budget examples/budget.json \
  --mode live \
  --receipt receipts/live-fail-closed.json
```

Expected result:

```text
decision: FAIL_CLOSED
key_requested: false
receipt emitted
```

M4+ may add live OpenAI and Anthropic routers, but those routers must use the Harness Governance Contract.

---

## 8. Router / Gate Usage

The router proposes execution paths.

The gate evaluates admissibility.

```text
Router:
  Which provider/model/path is cheapest or best?

Gate:
  Is this proposed path admissible?
```

A router comparing three paths submits three gate requests:

```text
openai-sync
openai-batch
anthropic-sync
```

The router may choose the cheapest path that receives `ALLOW`.

A denied cheaper path is not a saving. It is rejected.

See:

```text
docs/HARNESS_GOVERNANCE_CONTRACT.md
```

---

## 9. Receipts

Every decision emits a receipt.

A receipt should record:

```text
schema
timestamp
mode
decision
key_requested
provider
model
purpose
input_state_hash
gates
replay status
enforcement manager
scope assertions
scope disclaimers
receipt_id
canonicalization method
```

The receipt is contentless.

It must not include:

```text
API keys
payment method values
provider response content
private prompt content
raw secrets
```

A denial receipt is evidence.

---

## 10. CI Usage

Default CI should run mock and replay tests only.

It should not request provider keys.

Suggested workflow path:

```text
.github/workflows/provider-harness-ci.yml
```

Displayed without the leading dot:

```text
github/workflows/provider-harness-ci.yml
```

The workflow should:

```text
install package
run pytest
run mock allow
run mock deny
run replay miss
upload receipts as artifacts
avoid live provider mode by default
```

---

## 11. What Success Looks Like

A useful public demo should show:

```text
1. Mock ALLOW: no API key requested.
2. Missing consent DENY: no API key requested.
3. Budget DENY: no API key requested.
4. GCAT/BCAT DENY: no API key requested.
5. Replay HIT: no provider call.
6. Replay stale DENY: no provider call.
7. Live mode FAIL_CLOSED in M3.
```

This proves the repo is alive because it demonstrates action, refusal, replay, and receipts.

---

## 12. Canonical Usage Claim

```text
Provider Harness reduces avoidable provider calls by running deterministic governance checks before paid execution and by replaying equivalent admitted requests instead of repeating live calls.
```

It does not claim guaranteed lower cost.

It claims governed cost avoidance through:

```text
mock first
replay before live
budget before key
consent before key
GCAT/BCAT before key
receipt before trust
```

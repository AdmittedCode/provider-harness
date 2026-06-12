# AI Provider Governance Harness

Governed, opt-in access to AI providers (OpenAI, Anthropic, others). A paid
provider call is treated as a **cost-bearing governed action**, not an ordinary
function call. It may proceed only after deterministic local checks, explicit
consent, budget review, and GCAT/BCAT admissibility all pass.

**The headline demonstration is a correct refusal — a request denied before the
API key is ever requested, with a denial receipt as evidence.**

> No hidden calls. No silent keys. No unbounded cost. No broad authority.
> No execution without receipt.

## Scope of this build (M0–M3)

Mock + preflight + deterministic governance gates + receipts + replay. **No live adapters,
no live secrets, no network calls.** The mock adapter is *structurally* incapable
of reaching a key (verified at the AST level — it imports no secret store, no
`os.environ`, no network library). Live mode fails closed in this build.

## Doctrine

`API_KEY access is execution, not analysis.` Nothing here touches a key during
evaluation. The key is reached only after admissibility passes — and in M0–M3
that path is mock/replay, so it never is.

## Run it

```bash
# full governance passes (mock allow, no key touched)
provider-harness run --repo . --request examples/request.json \
  --consent examples/consent.json --budget examples/budget.json --mode mock

# headline: withdraw consent -> refused before key, denial receipt emitted
provider-harness run --repo . --request examples/request.json \
  --budget examples/budget.json --mode mock

# replay with a declared cache path; cache hit reuses governed response, no key touched
provider-harness run --repo . --request examples/request.json \
  --consent examples/consent.json --budget examples/budget.json --mode replay \
  --cache .provider-cache/replay.json
```

## The gates (each can refuse before the key)

1. **request_declaration** — provider, model, purpose, output schema must be declared
2. **consent** — explicit, user-approved, covering the declared purpose
3. **budget** — estimated cost known and within cap
4. **gcat_bcat** — execution pressure bounded: `a <= min(g, c, t)` (the conservative invariant)
5. **execution** — mock/replay only in this build; live fails closed

A denial at any gate emits a receipt with `key_requested: false`. **A denial
receipt is evidence, not an error to hide.**

## What it composes

This harness is the reference implementation showing the AdmittedCode line working
together: Repo Guard (structure), Coherency Scanner (governance posture), and the
Admissibility Receipt (proof envelope), in service of governed provider access.

## Scope (what a receipt does NOT assert)

Provider security/privacy/compliance, correctness or fitness of model output, or
any guarantee of lower cost. It asserts only that the declared request was
evaluated under the declared governance path.

## Roadmap

M0–M3 (this build): mock, preflight, governance gates, receipts, and replay
(governance-bound cache; stale ALLOWs cannot be laundered).
M4–M5: live OpenAI/Anthropic adapters (TV/TVC secret-ref gated).
M6: StegCGE routing. M7: full public demonstration.

## License
MIT.

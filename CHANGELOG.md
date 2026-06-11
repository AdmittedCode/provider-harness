# Changelog

## v0.1.0 (M0–M2)

- Initial release: governed, opt-in AI provider access harness.
- Governance chain: request declaration → consent → budget → GCAT/BCAT
  admissibility (`a <= min(g,c,t)`, conservative invariant) → execution gate.
- Headline behavior: a request is refused **before any API key is requested**;
  every denial emits a receipt with `key_requested: false`.
- Mock adapter is structurally key-free (no secret store, no os.environ, no
  network imports — verified at the AST level).
- Modes: mock (default), replay (stub), live (fails closed in this build).
- Portable receipts (stegverse.provider_harness_receipt.v1) with explicit scope
  disclaimer; canonical hashing via vendored stegverse.jcs.v1 core.
- 7 regression tests, runtime-built fixtures (immune to packaging path-stripping).

### Not yet included (roadmap)

- M1 completion: wire Repo Guard + Coherency Scanner as real preflight calls
  (currently the structural/posture steps are described, not shelled out).
- M4–M5: live OpenAI / Anthropic adapters, TV/TVC secret-reference gated.
- M6: StegCGE routing (ALLOW/DENY/DEFER/FAIL_CLOSED/QUARANTINE/ESCALATE).
- M7: full public demonstration (mock allow, mock deny, replay, one live allow,
  one live denied-before-key, fleet receipt audit).
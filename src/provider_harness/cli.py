"""provider-harness CLI (M0-M3): preflight + mock/replay run, refusal-before-key demonstration."""
import argparse
import json
import pathlib

from .core import configure_replay, run_preflight


def _load(p):
    if not p:
        return None
    return json.loads(pathlib.Path(p).read_text())


def main():
    ap = argparse.ArgumentParser(description="AI Provider Governance Harness (M0-M3)")
    ap.add_argument("command", choices=["preflight", "run"])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--request", required=True)
    ap.add_argument("--consent", default="")
    ap.add_argument("--budget", default="")
    ap.add_argument("--mode", default="mock", choices=["mock", "replay", "live"])
    ap.add_argument("--cache", default="", help="Replay cache path. Required for useful replay mode.")
    ap.add_argument("--receipt", default="")
    a = ap.parse_args()

    if a.mode == "replay" and a.cache:
        configure_replay(pathlib.Path(a.cache))

    o = run_preflight(pathlib.Path(a.repo), _load(a.request), _load(a.consent), _load(a.budget), mode=a.mode)
    print(f"\nDecision: {o.decision}   key_requested: {o.key_requested}")
    for g in o.gates:
        mark = {"PASS": "✅", "DENY": "⛔", "FAIL_CLOSED": "🔒"}.get(g.decision, "?")
        print(f"  {mark} {g.gate}: {g.detail}")
    if a.receipt:
        pathlib.Path(a.receipt).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.receipt).write_text(json.dumps(o.receipt, indent=2, sort_keys=True))
        print(f"\nreceipt → {a.receipt}  (id={o.receipt['receipt_id'][:24]}…)")
    if o.decision == "DENY":
        print("\n>>> Refused before any API key was requested. The denial receipt IS the evidence.")
    if o.decision == "FAIL_CLOSED" and a.mode == "replay" and not a.cache:
        print("\n>>> Replay mode ran without --cache, so no cached response could be used.")
    return 0 if o.decision in ("ALLOW",) else (2 if o.decision == "DENY" else 3)


if __name__ == "__main__":
    raise SystemExit(main())

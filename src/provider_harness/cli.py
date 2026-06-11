"""provider-harness CLI (M0-M2): preflight + mock run, refusal-before-key demonstration."""
import argparse, json, pathlib, sys
from .core import run_preflight

def _load(p):
    if not p: return None
    return json.loads(pathlib.Path(p).read_text())

def main():
    ap = argparse.ArgumentParser(description="AI Provider Governance Harness (M0-M2)")
    ap.add_argument("command", choices=["preflight","run"])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--request", required=True)
    ap.add_argument("--consent", default="")
    ap.add_argument("--budget", default="")
    ap.add_argument("--mode", default="mock", choices=["mock","replay","live"])
    ap.add_argument("--receipt", default="")
    a = ap.parse_args()
    o = run_preflight(pathlib.Path(a.repo), _load(a.request), _load(a.consent), _load(a.budget), mode=a.mode)
    print(f"\nDecision: {o.decision}   key_requested: {o.key_requested}")
    for g in o.gates:
        mark = {"PASS":"✅","DENY":"⛔","FAIL_CLOSED":"🔒"}.get(g.decision,"?")
        print(f"  {mark} {g.gate}: {g.detail}")
    if a.receipt:
        pathlib.Path(a.receipt).write_text(json.dumps(o.receipt, indent=2))
        print(f"\nreceipt → {a.receipt}  (id={o.receipt['receipt_id'][:24]}…)")
    if o.decision == "DENY":
        print("\n>>> Refused before any API key was requested. The denial receipt IS the evidence.")
    return 0 if o.decision in ("ALLOW",) else (2 if o.decision=="DENY" else 3)

if __name__ == "__main__":
    raise SystemExit(main())

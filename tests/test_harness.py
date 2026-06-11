"""
M0-M2 regression guard for the AI Provider Governance Harness.
Runtime-built fixtures (immune to packaging path-stripping).
Headline test: a refused request never reaches the key, and emits a denial receipt.
"""
import json, pathlib, sys, tempfile
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
from provider_harness import run_preflight, gcat_bcat_gate

def _repo(root):
    r = root / "repo"; r.mkdir(parents=True, exist_ok=True)
    (r/"repo-guard.json").write_text(json.dumps({"governance_role":"consumer"}))
    (r/"app.py").write_text("x=1\n")
    return r

def _req(**over):
    base = {"provider":"openai","model":"gpt-x","purpose":"summarize_readme",
            "output_schema":"summary.v1","estimated_cost_microdollars":500,
            "gcat_bcat":{"g":5,"c":5,"a":2,"t":5}}
    base.update(over); return base

def _consent(): return {"purpose":"summarize_readme","user_approved":True}
def _budget():  return {"max_microdollars":1000}

def test_mock_allow_never_requests_key():
    with tempfile.TemporaryDirectory() as d:
        o = run_preflight(_repo(pathlib.Path(d)), _req(), _consent(), _budget(), mode="mock")
        assert o.decision == "ALLOW", o.decision
        assert o.key_requested is False
        assert o.receipt["key_requested"] is False

def test_HEADLINE_missing_consent_refused_before_key():
    """The flagship demonstration: no consent -> DENY, key never requested, denial receipt emitted."""
    with tempfile.TemporaryDirectory() as d:
        o = run_preflight(_repo(pathlib.Path(d)), _req(), None, _budget(), mode="mock")
        assert o.decision == "DENY", o.decision
        assert o.key_requested is False, "FLAGSHIP VIOLATION: key was reached on a denied request"
        assert o.receipt["decision"] == "DENY"
        assert o.receipt["key_requested"] is False
        # a denial receipt is useful evidence, not a hidden error
        assert any(g.gate == "consent" and g.decision in ("DENY","FAIL_CLOSED") for g in o.gates)

def test_budget_exceeded_refused_before_key():
    with tempfile.TemporaryDirectory() as d:
        o = run_preflight(_repo(pathlib.Path(d)), _req(estimated_cost_microdollars=5000),
                          _consent(), _budget(), mode="mock")
        assert o.decision == "DENY" and o.key_requested is False

def test_gcat_bcat_pressure_denied_before_key():
    # a > min(g,c,t): execution pressure too high
    with tempfile.TemporaryDirectory() as d:
        o = run_preflight(_repo(pathlib.Path(d)), _req(gcat_bcat={"g":5,"c":1,"a":3,"t":5}),
                          _consent(), _budget(), mode="mock")
        assert o.decision == "DENY" and o.key_requested is False
        g = [x for x in o.gates if x.gate=="gcat_bcat"][0]
        assert g.decision == "DENY"

def test_live_mode_fails_closed_in_this_build():
    with tempfile.TemporaryDirectory() as d:
        o = run_preflight(_repo(pathlib.Path(d)), _req(), _consent(), _budget(), mode="live")
        assert o.decision == "FAIL_CLOSED" and o.key_requested is False

def test_gcat_invariant_unit():
    assert gcat_bcat_gate(5,5,2,5)[0] == "PASS"
    assert gcat_bcat_gate(5,1,3,5)[0] == "DENY"   # a=3 > min=1

def test_receipt_has_scope_disclaimer_and_no_secret():
    with tempfile.TemporaryDirectory() as d:
        o = run_preflight(_repo(pathlib.Path(d)), _req(), _consent(), _budget(), mode="mock")
        assert len(o.receipt["scope"]["does_not_assert"]) > 0
        blob = json.dumps(o.receipt).lower()
        assert "api_key" not in blob and "secret" not in blob

if __name__ == "__main__":
    import traceback
    fns=[v for k,v in sorted(globals().items()) if k.startswith("test_")]
    p=0
    for fn in fns:
        try: fn(); print("PASS",fn.__name__); p+=1
        except AssertionError: print("FAIL",fn.__name__); traceback.print_exc()
    print(f"\n{p}/{len(fns)} passed"); sys.exit(0 if p==len(fns) else 1)

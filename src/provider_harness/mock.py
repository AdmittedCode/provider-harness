"""
Mock adapter — the default. Requires no API key, makes no network call, and is
structurally incapable of requesting a secret. It returns a deterministic fixture.

This module deliberately has NO import of any secret store, no os.environ access
for keys, no network library. The absence is the guarantee: in M0-M3 there is no
code path that can reach a live key, by construction.
"""
from typing import Any, Dict


def call(request: Dict[str, Any]) -> Dict[str, Any]:
    # deterministic, fixture response keyed to the declared output schema
    return {
        "adapter": "mock",
        "key_requested": False,
        "response": {"fixture": True, "purpose": request.get("purpose"),
                     "note": "deterministic mock response; no provider was contacted"},
    }

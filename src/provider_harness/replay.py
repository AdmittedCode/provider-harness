"""
M3 — Replay.

Reuse a previously recorded, sanitized provider response instead of making
another paid call — but ONLY when replaying is still admissible. Replay is a
shortcut past the *call*, never past the *governance*.

The fingerprint binds to the full declared request, consent posture, and budget
posture, including any declared input scope, prompt hash, file hash set, output
schema, and GCAT/BCAT gate inputs when present. A cached entry records that
fingerprint plus a sanitized response (never a secret, never a raw key).

On a new request, replay is permitted only if:
  1. deterministic governance still passes for the current inputs, AND
  2. the fingerprint matches a cached admissible entry.

If governance changed (consent withdrawn, budget shrank, pressure rose, input
scope changed, prompt hash changed), the match is rejected — a stale ALLOW can
never be laundered through the cache.
"""
from __future__ import annotations

import datetime
import json
import pathlib
from typing import Any, Dict, Optional

from .canon import hash_obj

FINGERPRINT_VERSION = "stegverse.provider_harness.replay_fingerprint.v2"
FORBIDDEN_RESPONSE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "bearer",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "client_secret",
    "headers",
    "key",
}


def admissibility_fingerprint(request: Dict[str, Any],
                              consent: Optional[Dict[str, Any]],
                              budget: Optional[Dict[str, Any]]) -> str:
    """
    Canonical hash over the declared inputs that determine replay eligibility.

    This intentionally binds the entire declared request, not only the fields
    needed to pass the conservative gate. If the prompt hash, input file hash
    set, declared context, output schema, provider, model, consent, budget, or
    GCAT/BCAT vector changes, the fingerprint changes and a prior cached ALLOW
    cannot be replayed.
    """
    basis = {
        "fingerprint_version": FINGERPRINT_VERSION,
        "request": request or {},
        "consent": consent or {},
        "budget": budget or {},
    }
    return hash_obj(basis)


def _is_forbidden_key(key: Any) -> bool:
    k = str(key).lower().replace("-", "_")
    return k in FORBIDDEN_RESPONSE_KEYS or k.endswith("_api_key") or k.endswith("_token") or k.endswith("_secret")


def sanitize_response(raw: Any) -> Any:
    """
    Recursively strip anything that must never be cached. A cached response
    carries result content only — never keys, tokens, headers, auth material,
    or nested provider credentials.
    """
    if isinstance(raw, dict):
        return {k: sanitize_response(v) for k, v in raw.items() if not _is_forbidden_key(k)}
    if isinstance(raw, list):
        return [sanitize_response(v) for v in raw]
    if isinstance(raw, tuple):
        return [sanitize_response(v) for v in raw]
    return raw


class ReplayCache:
    """A small on-disk cache keyed by admissibility fingerprint. JSON, no secrets."""

    def __init__(self, path: pathlib.Path):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Any] = {}
        if self.path.is_file():
            try:
                loaded = json.loads(self.path.read_text())
                self._data = loaded if isinstance(loaded, dict) else {}
            except Exception:
                self._data = {}

    def get(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        return self._data.get(fingerprint)

    def put(self, fingerprint: str, response: Dict[str, Any], decision: str) -> None:
        # Never store a non-admissible result; never store unsanitized content.
        if decision != "ALLOW":
            return
        self._data[fingerprint] = {
            "fingerprint": fingerprint,
            "decision": decision,
            "response": sanitize_response(response),
            "recorded_utc": datetime.datetime.now(datetime.timezone.utc)
                .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        }
        self.path.write_text(json.dumps(self._data, indent=2, sort_keys=True))

"""
Canonical hashing — the single source of truth for "the bytes."

Every hash in an admissibility receipt is computed through THIS module, so the
generator and verifier (and any future re-implementation in another language)
agree byte-for-byte. The rules here ARE the canonicalization spec
(stegverse.jcs.v1); a conformant implementation in any language reproduces them.

Rules (stegverse.jcs.v1):
  - UTF-8 encoding
  - JSON object keys sorted (lexicographic by Unicode code point)
  - no insignificant whitespace: separators (",", ":")
  - integers only in hashed numerics (floats are rejected — see canon_check)
  - SHA-256, lowercase hex, prefixed "sha256:"
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


CANON_METHOD = "stegverse.jcs.v1"


class CanonError(ValueError):
    """Raised when a value cannot be canonicalized deterministically."""


def _reject_floats(obj: Any, path: str = "$") -> None:
    if isinstance(obj, float):
        raise CanonError(
            f"float at {path}: floats are not allowed in hashed payloads "
            "(use integers or canonical decimal strings)."
        )
    if isinstance(obj, dict):
        for k, v in obj.items():
            _reject_floats(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _reject_floats(v, f"{path}[{i}]")


def canon_bytes(obj: Any) -> bytes:
    """Canonical byte serialization of a JSON-compatible value."""
    _reject_floats(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def hash_obj(obj: Any) -> str:
    """Canonical hash of a structured value."""
    return sha256_hex(canon_bytes(obj))


def hash_file(path) -> str:
    import pathlib
    return sha256_hex(pathlib.Path(path).read_bytes())


def hash_repo_state(repo) -> str:
    """
    Deterministic hash of a repo's file tree: {posix_relpath: filehash}, hashed
    canonically. POSIX paths + sorted keys make it OS-independent.
    """
    import pathlib
    repo = pathlib.Path(repo)
    skip = {".git", "__pycache__", "node-compile-cache", ".egg-info"}
    state = {}
    for p in sorted(repo.rglob("*")):
        if not p.is_file():
            continue
        if any(s in p.parts or s in p.name for s in skip):
            continue
        state[p.relative_to(repo).as_posix()] = hash_file(p)
    return hash_obj(state)

"""Local signer (modular-plan.md §2.2): HMAC-SHA256 with a key from
config, standing in for Cloud KMS. Same `sign`/`verify` contract, so a
transfer order's signature check (backend/action/sign_order.py) works
identically in either mode.
"""
from __future__ import annotations

import hashlib
import hmac


class LocalSigner:
    def __init__(self, key: str):
        self._key = key.encode("utf-8")

    def sign(self, payload: bytes) -> str:
        return hmac.new(self._key, payload, hashlib.sha256).hexdigest()

    def verify(self, payload: bytes, signature: str) -> bool:
        return hmac.compare_digest(self.sign(payload), signature)

"""Cloud KMS signer (architecture.md §1), for signed transfer orders."""
from __future__ import annotations

import base64

from backend.config import get_settings
from backend.providers.base import ProviderError


class GoogleKMSSigner:
    def __init__(self):
        from google.cloud import kms

        self._client = kms.KeyManagementServiceClient()
        self._key_name = get_settings().signing_key  # full KMS CryptoKeyVersion resource name

    def sign(self, payload: bytes) -> str:
        import hashlib

        digest = hashlib.sha256(payload).digest()
        try:
            response = self._client.asymmetric_sign(
                request={"name": self._key_name, "digest": {"sha256": digest}}
            )
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"KMS signing failed: {e}") from e
        return base64.b64encode(response.signature).decode("ascii")

    def verify(self, payload: bytes, signature: str) -> bool:
        import hashlib

        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec, padding
        from cryptography.exceptions import InvalidSignature

        public_key_pem = self._client.get_public_key(request={"name": self._key_name}).pem
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        digest = hashlib.sha256(payload).digest()
        sig_bytes = base64.b64decode(signature)
        try:
            if isinstance(public_key, ec.EllipticCurvePublicKey):
                public_key.verify(sig_bytes, digest, ec.ECDSA(hashes.SHA256()))
            else:
                public_key.verify(sig_bytes, digest, padding.PKCS1v15(), hashes.SHA256())
            return True
        except InvalidSignature:
            return False

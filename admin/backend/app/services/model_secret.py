import base64
import hashlib
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings


def _secret_bytes() -> bytes:
    secret = (
        settings.agent_model_secret
        or os.getenv("AGENT_MODEL_SECRET", "")
        or settings.jwt_secret
    )
    return hashlib.sha256(secret.encode("utf-8")).digest()


def encrypt_model_config(payload: dict) -> str:
    aesgcm = AESGCM(_secret_bytes())
    nonce = os.urandom(12)
    plaintext = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_model_config(ciphertext_b64: str) -> dict:
    if not ciphertext_b64:
        return {}
    raw = base64.b64decode(ciphertext_b64)
    if len(raw) <= 12:
        return {}
    nonce, ciphertext = raw[:12], raw[12:]
    aesgcm = AESGCM(_secret_bytes())
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    data = json.loads(plaintext.decode("utf-8"))
    return data if isinstance(data, dict) else {}


def mask_api_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:3]}***{api_key[-4:]}"

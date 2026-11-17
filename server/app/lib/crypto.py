import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings


def _key():
    return hashlib.sha256(settings.encryption_key.encode("utf-8")).digest()


def encrypt(value):
    if not value:
        return ""
    iv = os.urandom(12)
    aes = AESGCM(_key())
    sealed = aes.encrypt(iv, str(value).encode("utf-8"), None)
    ciphertext, tag = sealed[:-16], sealed[-16:]
    return __import__("base64").b64encode(iv + tag + ciphertext).decode("ascii")


def decrypt(payload):
    if not payload:
        return ""
    import base64

    buffer = base64.b64decode(payload)
    iv, tag, ciphertext = buffer[:12], buffer[12:28], buffer[28:]
    aes = AESGCM(_key())
    return aes.decrypt(iv, ciphertext + tag, None).decode("utf-8")

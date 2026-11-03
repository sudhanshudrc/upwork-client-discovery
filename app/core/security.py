import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import logging
import os
from typing import Any, Dict, Optional, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

logger = logging.getLogger("app.core.security")


def get_encryption_key() -> bytes:
    """
    Derives a stable 256-bit AES key from settings.SECRET_KEY.
    Ensures cryptographic key length requirements (32 bytes) are satisfied.
    """
    raw_key = getattr(settings, "SECRET_KEY", "default_upwork_automation_secret_key_32b")
    return hashlib.sha256(raw_key.encode("utf-8")).digest()


_get_encryption_key = get_encryption_key


def hash_password(password: str) -> str:
    """
    Generates a cryptographically secure PBKDF2-HMAC-SHA256 password hash
    with 600,000 iterations and a 16-byte random salt.
    """
    if not password:
        raise ValueError("Password cannot be empty.")
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600000)
    return f"pbkdf2_sha256$600000${salt.hex()}${dk.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a stored PBKDF2 hash using constant-time comparison.
    Supports backward-compatibility if an unhashed legacy password was present.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
            iterations = int(parts[1])
            salt = bytes.fromhex(parts[2])
            expected_hash = parts[3]
            dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
            return hmac.compare_digest(dk.hex(), expected_hash)

        # Backward compatibility check for plain text or simple hex
        if hmac.compare_digest(plain_password, hashed_password):
            return True
        if hmac.compare_digest(hashlib.sha256(plain_password.encode("utf-8")).hexdigest(), hashed_password):
            return True
        return False
    except Exception as e:
        logger.warning(f"[SECURITY] Password verification failed due to format error: {e}")
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = len(s) % 4
    if pad:
        s += "=" * (4 - pad)
    return base64.urlsafe_b64decode(s)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a signed HS256 JWT access token.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=7)

    to_encode.update({"exp": int(expire.timestamp()), "iat": int(now.timestamp())})

    header_bytes = json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8")
    payload_bytes = json.dumps(to_encode, separators=(",", ":")).encode("utf-8")

    header_b64 = _b64url_encode(header_bytes)
    payload_b64 = _b64url_encode(payload_bytes)
    message = f"{header_b64}.{payload_b64}".encode("utf-8")

    key = get_encryption_key()
    signature_bytes = hmac.new(key, message, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature_bytes)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and verifies an HS256 JWT access token.
    Raises ValueError if invalid, tampered, or expired.
    """
    if not token or token.count(".") != 2:
        raise ValueError("Invalid token format.")

    header_b64, payload_b64, signature_b64 = token.split(".")
    message = f"{header_b64}.{payload_b64}".encode("utf-8")

    key = get_encryption_key()
    expected_sig = _b64url_encode(hmac.new(key, message, hashlib.sha256).digest())

    if not hmac.compare_digest(signature_b64, expected_sig):
        raise ValueError("Invalid token signature.")

    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid token payload: {e}") from e

    exp = payload.get("exp")
    if exp:
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if now_ts > exp:
            raise ValueError("Token has expired.")

    return payload


def encrypt_session_data(data: Union[Dict[str, Any], str]) -> str:
    """
    Encrypts storage_state JSON data using AES-256-GCM.
    Prepends a 12-byte random initialization nonce and encodes the result in Base64.
    """
    if isinstance(data, dict):
        plaintext = json.dumps(data).encode("utf-8")
    elif isinstance(data, str):
        plaintext = data.encode("utf-8")
    else:
        raise ValueError("Data to encrypt must be a dictionary or string.")

    key = _get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce for AES-GCM
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    # Combine nonce (12 bytes) + ciphertext + authentication tag
    payload = nonce + ciphertext
    return base64.b64encode(payload).decode("ascii")


def decrypt_session_data(encrypted_str: str) -> Dict[str, Any]:
    """
    Decrypts an AES-256-GCM Base64 encrypted session payload and returns the original JSON dict.
    Includes backward compatibility for raw JSON strings.
    """
    if not encrypted_str or not encrypted_str.strip():
        return {"cookies": [], "origins": []}

    clean_str = encrypted_str.strip()

    # Graceful fallback: if input is already raw unencrypted JSON
    if clean_str.startswith("{"):
        try:
            return json.loads(clean_str)
        except Exception:
            pass

    try:
        raw_bytes = base64.b64decode(clean_str)
        if len(raw_bytes) < 28:  # 12 byte nonce + 16 byte tag
            raise ValueError("Encrypted payload too short.")

        nonce = raw_bytes[:12]
        ciphertext = raw_bytes[12:]

        key = _get_encryption_key()
        aesgcm = AESGCM(key)
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(decrypted_bytes.decode("utf-8"))

    except Exception as e:
        logger.error(f"[SECURITY] Failed to decrypt session payload: {e}")
        raise ValueError(f"Session decryption failed: {str(e)}") from e

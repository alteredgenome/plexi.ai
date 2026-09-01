import hashlib
import hmac
import secrets
import time
import json
import base64
from typing import Optional, Dict, Any
from app.config import settings

def hash_password(password: str) -> str:
    """
    Cryptographically secure password hash using PBKDF2-HMAC-SHA256 with unique 16-byte salt.
    Format: salt_hex$hash_hex
    """
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}${dk.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a password against the salted PBKDF2 hash using constant-time comparison.
    """
    try:
        salt_hex, hash_hex = hashed_password.split("$")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(dk, expected_hash)
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta_seconds: Optional[int] = None) -> str:
    """
    Creates a secure signed HMAC-SHA256 token containing payload and expiration timestamp.
    Format: base64(payload_json).base64(signature)
    """
    if expires_delta_seconds is None:
        expires_delta_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_delta_seconds
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode('utf-8').rstrip('=')
    
    secret_bytes = settings.SECRET_KEY.encode('utf-8')
    sig = hmac.new(secret_bytes, payload_b64.encode('utf-8'), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode('utf-8').rstrip('=')
    
    return f"{payload_b64}.{sig_b64}"

def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies the cryptographic HMAC signature and expiry of an access token.
    """
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig_b64 = parts
        
        # Verify signature
        secret_bytes = settings.SECRET_KEY.encode('utf-8')
        expected_sig = hmac.new(secret_bytes, payload_b64.encode('utf-8'), hashlib.sha256).digest()
        
        # Pad base64 for decoding
        rem = len(sig_b64) % 4
        padded_sig = sig_b64 + ('=' * (4 - rem) if rem else '')
        actual_sig = base64.urlsafe_b64decode(padded_sig.encode('utf-8'))
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
            
        rem = len(payload_b64) % 4
        padded_payload = payload_b64 + ('=' * (4 - rem) if rem else '')
        payload_bytes = base64.urlsafe_b64decode(padded_payload.encode('utf-8'))
        payload = json.loads(payload_bytes.decode('utf-8'))
        
        if payload.get("exp", 0) < time.time():
            return None # Expired
            
        return payload
    except Exception:
        return None

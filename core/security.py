# core/security.py
import hashlib
import os

# Hash helper (SHA256)
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

# Optional: read credentials from env or fallback default
def get_credentials():
    username = os.getenv("GATEWAY_USER", "admin")
    password = os.getenv("GATEWAY_PASS", "admin123")
    return username, hash_password(password)

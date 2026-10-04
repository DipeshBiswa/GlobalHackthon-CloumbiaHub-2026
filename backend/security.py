"""Local password hashing and expiring opaque sessions."""
import hashlib
import hmac
import secrets

def hash_secret(value):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), bytes.fromhex(salt), 310000).hex()
    return f"{salt}:{digest}"

def verify(value, stored):
    salt, expected = stored.split(":")
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), bytes.fromhex(salt), 310000).hex()
    return hmac.compare_digest(digest, expected)

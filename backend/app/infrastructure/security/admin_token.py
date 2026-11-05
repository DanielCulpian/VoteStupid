import hashlib
import hmac
import secrets


def generate_admin_token() -> str:
    """Generate a secure random token for administering a poll."""
    return secrets.token_urlsafe(32)


def hash_admin_token(token: str) -> str:
    """Calculate the administration token's SHA-256 hash and reject empty values."""
    if not token:
        raise ValueError("El token de administrador no puede estar vacío.")

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_admin_token(token: str, stored_hash: str | None) -> bool:
    """Compare the received token hash with the stored hash in constant time."""
    if not token or not stored_hash:
        return False

    token_hash = hash_admin_token(token)

    return hmac.compare_digest(token_hash, stored_hash)
import hashlib
import hmac
import secrets


def generate_admin_token() -> str:
    """Genera un token aleatorio seguro para administrar una votación."""
    return secrets.token_urlsafe(32)


def hash_admin_token(token: str) -> str:
    """Calcula el hash SHA-256 del token de administración y rechaza valores vacíos."""
    if not token:
        raise ValueError("El token de administrador no puede estar vacío.")

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_admin_token(token: str, stored_hash: str | None) -> bool:
    """Compara el hash del token recibido con el almacenado en tiempo constante."""
    if not token or not stored_hash:
        return False

    token_hash = hash_admin_token(token)

    return hmac.compare_digest(token_hash, stored_hash)
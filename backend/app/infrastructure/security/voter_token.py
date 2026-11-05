import hashlib


def hash_voter_token(token: str) -> str:
    """Calculate the voter token's SHA-256 hash and reject empty values."""
    if not token or not token.strip():
        raise ValueError("El token del votante no puede estar vacío.")

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
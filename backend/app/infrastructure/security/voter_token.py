import hashlib


def hash_voter_token(token: str) -> str:
    if not token or not token.strip():
        raise ValueError("El token del votante no puede estar vacío.")

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
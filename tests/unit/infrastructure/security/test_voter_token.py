from app.infrastructure.security.voter_token import hash_voter_token
import pytest


def test_hash_voter_token_rejects_empty_token():
    """Comprueba que el hash del token del participante rechaza un token vacío."""
    with pytest.raises(ValueError):
        hash_voter_token("   ")

def test_hash_voter_token_returns_sha256_hash():
    """Comprueba que el hash del token del participante devuelve un resumen SHA-256."""
    result = hash_voter_token("my-secret-token")

    assert len(result) == 64
    assert all(character in "0123456789abcdef" for character in result)


def test_hash_voter_token_returns_same_hash_for_same_token():
    """Comprueba que el hash del token del participante produce el mismo resumen para el mismo token."""
    first_hash = hash_voter_token("my-secret-token")
    second_hash = hash_voter_token("my-secret-token")

    assert first_hash == second_hash


def test_hash_voter_token_returns_different_hash_for_different_tokens():
    """Comprueba que el hash del token del participante produce resúmenes distintos para tokens distintos."""
    first_hash = hash_voter_token("token-one")
    second_hash = hash_voter_token("token-two")

    assert first_hash != second_hash
from app.infrastructure.security.voter_token import hash_voter_token
import pytest


def test_hash_voter_token_rejects_empty_token():
    """Verify hash voter token rejects empty token."""
    with pytest.raises(ValueError):
        hash_voter_token("   ")

def test_hash_voter_token_returns_sha256_hash():
    """Verify hash voter token returns sha256 hash."""
    result = hash_voter_token("my-secret-token")

    assert len(result) == 64
    assert all(character in "0123456789abcdef" for character in result)


def test_hash_voter_token_returns_same_hash_for_same_token():
    """Verify hash voter token returns same hash for same token."""
    first_hash = hash_voter_token("my-secret-token")
    second_hash = hash_voter_token("my-secret-token")

    assert first_hash == second_hash


def test_hash_voter_token_returns_different_hash_for_different_tokens():
    """Verify hash voter token returns different hash for different tokens."""
    first_hash = hash_voter_token("token-one")
    second_hash = hash_voter_token("token-two")

    assert first_hash != second_hash
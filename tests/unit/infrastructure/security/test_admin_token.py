from app.infrastructure.security.admin_token import (
    generate_admin_token,
    hash_admin_token,
    verify_admin_token,
)


def test_generate_admin_token_returns_non_empty_string():
    token = generate_admin_token()

    assert isinstance(token, str)
    assert len(token) > 0


def test_generate_admin_token_generates_different_tokens():
    token_one = generate_admin_token()
    token_two = generate_admin_token()

    assert token_one != token_two


def test_hash_admin_token_returns_sha256_hash():
    token_hash = hash_admin_token("mi-secreto")

    assert len(token_hash) == 64
    assert all(character in "0123456789abcdef" for character in token_hash)


def test_hash_admin_token_returns_same_hash_for_same_token():
    token = "mi-secreto"

    assert hash_admin_token(token) == hash_admin_token(token)


def test_hash_admin_token_returns_different_hash_for_different_tokens():
    assert hash_admin_token("secreto-uno") != hash_admin_token("secreto-dos")


def test_hash_admin_token_rejects_empty_token():
    import pytest

    with pytest.raises(ValueError):
        hash_admin_token("")

def test_verify_admin_token_accepts_valid_token():
    token = generate_admin_token()
    stored_hash = hash_admin_token(token)

    assert verify_admin_token(token, stored_hash) is True


def test_verify_admin_token_rejects_invalid_token():
    token = generate_admin_token()
    stored_hash = hash_admin_token(token)

    assert verify_admin_token("token-incorrecto", stored_hash) is False


def test_verify_admin_token_rejects_empty_values():
    assert verify_admin_token("", "hash-valido") is False
    assert verify_admin_token("token-valido", None) is False
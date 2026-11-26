from api.security import (
    generate_csrf_token,
    hash_password,
    validate_csrf_token,
    verify_password,
)


def test_hash_and_verify_password():
    salt, pwd_hash = hash_password("secret123")
    assert salt
    assert pwd_hash
    assert verify_password("secret123", salt, pwd_hash)
    assert not verify_password("wrong", salt, pwd_hash)


def test_hash_password_with_known_salt():
    salt = "8e789b37bca2ef8d47ab992441306a22"
    _, pwd_hash = hash_password("admin123", salt)
    assert pwd_hash == "df71afdbc73c2f7076d857ee9360132b4991d9d05346d15ddfe9fc2611499338"


def test_csrf_token_generation_and_validation():
    token = generate_csrf_token()
    assert token
    assert validate_csrf_token(token, token)
    assert not validate_csrf_token(token, "bad")
    assert not validate_csrf_token(None, token)

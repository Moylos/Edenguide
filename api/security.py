import hashlib
import hmac
import secrets

PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 100_000
SALT_BYTES = 16


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash a password with PBKDF2-HMAC-SHA256.

    Returns (salt_hex, pwd_hash_hex). If salt is not provided, a new 16-byte
    random salt is generated.
    """
    if salt is None:
        salt = secrets.token_hex(SALT_BYTES)
    pwd_hash = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS,
    ).hex()
    return salt, pwd_hash


def hash_password_werkzeug(password: str) -> str:
    """Hash a password using Werkzeug's default secure hasher."""
    from werkzeug.security import generate_password_hash

    return generate_password_hash(password)


def verify_password(password: str, salt: str, pwd_hash: str) -> bool:
    """Verify a password against stored credentials.

    Supports Werkzeug hashes (scrypt:/pbkdf2:...) and legacy PBKDF2-HMAC-SHA256.
    """
    if pwd_hash.startswith(("pbkdf2:", "scrypt:", "argon2:")):
        from werkzeug.security import check_password_hash

        return check_password_hash(pwd_hash, password)
    _, candidate = hash_password(password, salt)
    return hmac.compare_digest(candidate, pwd_hash)


def generate_csrf_token() -> str:
    """Generate a random CSRF token for session storage."""
    return secrets.token_urlsafe(32)


def validate_csrf_token(session_token: str | None, form_token: str | None) -> bool:
    """Validate a CSRF token from the form against the session token."""
    if not session_token or not form_token:
        return False
    return hmac.compare_digest(str(session_token), str(form_token))

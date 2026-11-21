import hashlib
import hmac
import os


_HASH_NAME = "sha256"
_ITERATIONS = 600_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(_HASH_NAME, password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_{_HASH_NAME}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, expected_digest = encoded_hash.split("$")
        if algorithm != f"pbkdf2_{_HASH_NAME}":
            return False
        iterations = int(iterations_text)
        if iterations <= 0:
            return False
        salt = bytes.fromhex(salt_text)
        expected = bytes.fromhex(expected_digest)
        actual = hashlib.pbkdf2_hmac(_HASH_NAME, password.encode("utf-8"), salt, iterations)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)

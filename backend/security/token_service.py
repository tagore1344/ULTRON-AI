# backend/security/token_service.py
import secrets
import hashlib


class TokenService:
    """Provides secure, cryptographically sound random token generation and secure hashing."""

    @staticmethod
    def generate_token() -> str:
        """Generate a secure, high-entropy random API token."""
        # 32 bytes of secure entropy yields a 64-character hexadecimal string
        return secrets.token_hex(32)

    @staticmethod
    def generate_pairing_code() -> str:
        """Generate exactly a 6-digit cryptographically secure numerical pairing PIN."""
        # Generating a secure random number in range [100000, 999999]
        return str(secrets.randbelow(900000) + 100000)

    @classmethod
    def hash_string(cls, value: str) -> str:
        """Hash a string (such as an API token or a pairing code) securely with SHA-256."""
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


token_service = TokenService()

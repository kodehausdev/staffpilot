"""
Application-level encryption for sensitive payslip fields.
Key is stored in PAYSLIP_ENCRYPTION_KEY env var — never in Supabase.
Supabase dashboard shows only ciphertext; only the running backend can decrypt.

To generate a key (run once, store in .env):
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import json
from cryptography.fernet import Fernet, InvalidToken
from config import get_settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = get_settings().payslip_encryption_key
        if not key:
            raise RuntimeError(
                "PAYSLIP_ENCRYPTION_KEY is not set. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        _fernet = Fernet(key.encode())
    return _fernet


def encrypt_amount(value: float | int) -> str:
    return _get_fernet().encrypt(str(float(value)).encode()).decode()


def decrypt_amount(ciphertext: str | None) -> float:
    if not ciphertext:
        return 0.0
    try:
        return float(_get_fernet().decrypt(ciphertext.encode()).decode())
    except (InvalidToken, ValueError):
        return 0.0


def encrypt_dict(data: dict) -> str:
    return _get_fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_dict(ciphertext: str | None) -> dict:
    if not ciphertext:
        return {}
    try:
        return json.loads(_get_fernet().decrypt(ciphertext.encode()).decode())
    except (InvalidToken, ValueError, json.JSONDecodeError):
        return {}

from __future__ import annotations

import hashlib
import secrets


def hash_senha(senha: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    derivado = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt), 120_000)
    return f"{salt}${derivado.hex()}"


def verificar_senha(senha: str, armazenada: str) -> bool:
    salt, hx = armazenada.split("$")
    derivado = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt), 120_000)
    return secrets.compare_digest(derivado.hex(), hx)

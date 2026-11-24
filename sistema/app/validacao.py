from __future__ import annotations

import re

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def digitos(valor: str) -> str:
    return "".join(ch for ch in (valor or "") if ch.isdigit())


def telefone_valido(valor: str) -> bool:
    return len(digitos(valor)) in {10, 11}


def email_valido(valor: str) -> bool:
    return bool(EMAIL.match((valor or "").strip()))


def cpf_valido(valor: str) -> bool:
    numero = digitos(valor)
    if len(numero) != 11 or numero == numero[0] * 11:
        return False

    def verificador(base: str) -> int:
        peso = len(base) + 1
        soma = sum(int(digito) * (peso - indice) for indice, digito in enumerate(base))
        resto = (soma * 10) % 11
        return 0 if resto == 10 else resto

    return verificador(numero[:9]) == int(numero[9]) and verificador(numero[:10]) == int(numero[10])

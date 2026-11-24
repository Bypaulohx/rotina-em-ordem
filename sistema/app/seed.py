from __future__ import annotations

from sqlalchemy.orm import Session

from .models import Baia, ConfigLoja, Profissional, Servico, Usuario
from .security import hash_senha

SERVICOS = [
    ("Banho completo", "banho", "P", 40, 65, 0),
    ("Banho completo", "banho", "M", 50, 85, 0),
    ("Banho completo", "banho", "G", 70, 120, 0),
    ("Tosa higiênica", "tosa", "P", 30, 45, 0),
    ("Tosa higiênica", "tosa", "M", 40, 60, 0),
    ("Tosa higiênica", "tosa", "G", 50, 80, 0),
    ("Diária de hotel", "hotel", "P", 0, 80, 120),
    ("Diária de hotel", "hotel", "M", 0, 110, 165),
    ("Diária de hotel", "hotel", "G", 0, 150, 225),
]

BAIAS = [
    ("Salão P1", "P", "salao"),
    ("Salão P2", "P", "salao"),
    ("Salão M1", "M", "salao"),
    ("Salão M2", "M", "salao"),
    ("Salão G1", "G", "salao"),
    ("Hotel P", "P", "hotel"),
    ("Hotel M", "M", "hotel"),
    ("Hotel G", "G", "hotel"),
]


def seed_if_empty(db: Session) -> None:
    if db.query(Usuario).first():
        return

    db.add(Usuario(nome="Paulo H", login="paulo", senha_hash=hash_senha("rotina"), papel="admin"))
    db.add(ConfigLoja(id=1, tolerancia_busca_min=15, valor_atraso=20))
    for nome, tipo, porte, duracao, preco, feriado in SERVICOS:
        db.add(
            Servico(
                nome=nome,
                tipo=tipo,
                porte=porte,
                duracao_min=duracao,
                preco=preco,
                preco_feriado=feriado,
            )
        )
    for nome, porte, tipo in BAIAS:
        db.add(Baia(nome=nome, porte=porte, tipo=tipo, ativo=True))
    db.add(Profissional(nome="Ana Costa", ativo=True))
    db.add(Profissional(nome="Bruno Dias", ativo=True))
    db.commit()

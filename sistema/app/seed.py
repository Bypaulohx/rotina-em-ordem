from __future__ import annotations

import os
import secrets

from sqlalchemy.orm import Session

from .models import Baia, ConfigLoja, Profissional, Servico, Usuario
from .rules import RegraNegocio
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


def _estrutura(db: Session, responsavel: str) -> None:
    if not db.query(Servico).first():
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
    if not db.query(Baia).first():
        for nome, porte, tipo in BAIAS:
            db.add(Baia(nome=nome, porte=porte, tipo=tipo, ativo=True))
    if responsavel and not db.query(Profissional).first():
        db.add(Profissional(nome=responsavel, ativo=True))


def abrir_loja(
    db: Session,
    empresa: str,
    slogan: str,
    whatsapp: str,
    tolerancia: int,
    valor_atraso: float,
    responsavel: str,
    login: str,
    senha: str,
    cor: str = "#1f6b4a",
) -> Usuario:
    if db.query(Usuario).first():
        raise RegraNegocio("Esta loja já foi cadastrada. Entre com o login da equipe.", 409)
    nome_loja = empresa.strip()
    frase = slogan.strip()
    dono = responsavel.strip()
    usuario_login = login.strip()
    telefone = "".join(ch for ch in whatsapp if ch.isdigit())
    if not nome_loja or not dono or not usuario_login or len(senha) < 6:
        raise RegraNegocio("Informe a empresa, o responsável, o login e uma senha com pelo menos 6 caracteres.", 400)
    if " " in usuario_login or len(usuario_login) > 40 or len(nome_loja) > 80 or len(frase) > 120 or len(dono) > 80:
        raise RegraNegocio("Revise o nome da empresa, a frase, o responsável e o login.", 400)
    if telefone and not 10 <= len(telefone) <= 13:
        raise RegraNegocio("Informe o WhatsApp com DDD.", 400)
    if tolerancia < 0 or tolerancia > 240:
        raise RegraNegocio("A tolerância da busca fica entre 0 e 240 minutos.", 400)
    if valor_atraso < 0:
        raise RegraNegocio("A taxa de atraso não pode ser negativa.", 400)
    if db.query(Usuario).filter(Usuario.login == usuario_login).first():
        raise RegraNegocio("Esse login já está em uso.", 409)
    cfg = db.get(ConfigLoja, 1) or ConfigLoja(id=1)
    cfg.nome = nome_loja
    cfg.slogan = frase
    cfg.whatsapp = telefone
    cfg.tolerancia_busca_min = tolerancia
    cfg.valor_atraso = round(float(valor_atraso), 2)
    cfg.cor = cor if len(cor) == 7 and cor.startswith("#") else "#1f6b4a"
    if telefone and not cfg.whatsapp_token:
        cfg.whatsapp_token = secrets.token_urlsafe(18)
    if not telefone:
        cfg.whatsapp_token = ""
    db.add(cfg)
    usuario = Usuario(nome=dono, login=usuario_login, senha_hash=hash_senha(senha), papel="admin")
    db.add(usuario)
    _estrutura(db, dono)
    db.commit()
    db.refresh(usuario)
    return usuario


def seed_if_empty(db: Session) -> None:
    if db.query(Usuario).first() or os.environ.get("ROTINA_TEST") != "1":
        return

    db.add(Usuario(nome="Paulo H", login="paulo", senha_hash=hash_senha("rotina"), papel="admin"))
    db.add(ConfigLoja(id=1, tolerancia_busca_min=15, valor_atraso=20))
    _estrutura(db, "")
    db.add(Profissional(nome="Ana Costa", ativo=True))
    db.add(Profissional(nome="Bruno Dias", ativo=True))
    db.commit()

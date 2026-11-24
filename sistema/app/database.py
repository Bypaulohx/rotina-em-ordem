from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

DB_PATH = Path(__file__).resolve().parent.parent / "rotina.db"


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal = None


def database_url() -> str:
    return os.environ.get("ROTINA_DB") or f"sqlite:///{DB_PATH.as_posix()}"


def configure(url: str | None = None) -> None:
    global engine, SessionLocal
    url = url or database_url()
    kwargs = {"connect_args": {"check_same_thread": False}}
    if url == "sqlite://":
        kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def migrar() -> None:
    from sqlalchemy import inspect, text

    if engine is None:
        return
    insp = inspect(engine)
    ajustes = {
        "config": {
            "whatsapp": "VARCHAR(20) DEFAULT ''",
            "whatsapp_token": "VARCHAR(64) DEFAULT ''",
        },
        "usuarios": {
            "papel": "VARCHAR(20) DEFAULT 'admin'",
            "matricula": "VARCHAR(20) DEFAULT ''",
            "pis": "VARCHAR(12) DEFAULT ''",
        },
        "clientes": {
            "numero": "VARCHAR(20) DEFAULT ''",
            "email": "VARCHAR(120) DEFAULT ''",
            "cpf": "VARCHAR(11) DEFAULT ''",
            "observacoes": "TEXT DEFAULT ''",
            "senha_hash": "VARCHAR(120) DEFAULT ''",
        },
        "pets": {
            "raca": "VARCHAR(80) DEFAULT ''",
            "sexo": "VARCHAR(20) DEFAULT ''",
            "nascimento": "DATE",
            "peso": "FLOAT",
            "alergias": "TEXT DEFAULT ''",
            "doencas": "TEXT DEFAULT ''",
            "medicamentos": "TEXT DEFAULT ''",
            "comportamento": "TEXT DEFAULT ''",
            "emergencia_nome": "VARCHAR(80) DEFAULT ''",
            "emergencia_telefone": "VARCHAR(20) DEFAULT ''",
            "foto": "VARCHAR(200) DEFAULT ''",
        },
        "baias": {"limpeza_desde": "DATETIME"},
        "caixas": {
            "usuario_id": "INTEGER",
            "fechado_por_id": "INTEGER",
        },
        "vendas": {
            "observacao": "TEXT DEFAULT ''",
            "pet_id": "INTEGER",
            "desconto": "FLOAT DEFAULT 0",
            "acrescimo": "FLOAT DEFAULT 0",
        },
        "itens_venda": {
            "produto_id": "INTEGER",
            "quantidade": "INTEGER DEFAULT 1",
            "gramas": "INTEGER",
        },
        "produtos": {
            "codigo_barras": "VARCHAR(32)",
            "categoria": "VARCHAR(40) DEFAULT ''",
            "marca": "VARCHAR(40) DEFAULT ''",
            "custo": "FLOAT DEFAULT 0",
            "validade": "DATE",
            "fornecedor_id": "INTEGER",
            "unidade": "VARCHAR(8) DEFAULT 'un'",
        },
        "despesas": {
            "status": "VARCHAR(20) DEFAULT 'paga'",
            "vencimento": "DATE",
            "usuario_id": "INTEGER",
        },
    }
    with engine.begin() as conn:
        for tabela, colunas in ajustes.items():
            if not insp.has_table(tabela):
                continue
            presentes = {coluna["name"] for coluna in insp.get_columns(tabela)}
            for nome, tipo in colunas.items():
                if nome not in presentes:
                    conn.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {nome} {tipo}"))
        if insp.has_table("produtos"):
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_produtos_codigo ON produtos (codigo_barras)"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


configure()

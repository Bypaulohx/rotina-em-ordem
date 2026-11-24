import os
from datetime import datetime, timedelta

os.environ["ROTINA_DB"] = "sqlite://"
os.environ["ROTINA_TEST"] = "1"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.gestao import extrair_inicio
from app.main import app


@pytest.fixture(autouse=True)
def banco_limpo():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_horario_de_amanha_sai_do_texto():
    agora = datetime(2026, 10, 31, 12, 0)
    inicio = extrair_inicio("banho da luna amanhã 16h", agora)
    assert inicio == datetime(2026, 11, 1, 16, 0)


def test_mensagem_de_whatsapp_cria_o_agendamento_se_a_baia_cabe():
    with TestClient(app) as client:
        assert client.post("/api/login", json={"login": "paulo", "senha": "rotina"}).status_code == 200
        pessoas = client.post("/api/clientes", json={"nome": "Lara Nunes", "pet_nome": "Luna", "porte": "P", "telefone": "11955554433", "cep": "01310100", "logradouro": "Rua Augusta", "cidade": "São Paulo"}).json()
        assert pessoas[0]["pets"][0]["nome"] == "Luna"
        amanha = (datetime.now() + timedelta(days=1)).strftime("%d/%m")
        mensagem = client.post("/api/whatsapp/mensagens", json={"texto": f"Banho da Luna {amanha} 16h", "telefone": "11988887777"}).json()
        assert mensagem["status"] == "criado"
        assert "baia" in mensagem["detalhe"].lower() or "Salão" in mensagem["detalhe"]


def test_mensagem_sem_pet_fica_pendente():
    with TestClient(app) as client:
        client.post("/api/login", json={"login": "paulo", "senha": "rotina"})
        mensagem = client.post("/api/whatsapp/mensagens", json={"texto": "Quero um banho amanhã 16h"}).json()
        assert mensagem["status"] == "pendente"


def test_equipe_nao_abre_a_administracao():
    with TestClient(app) as client:
        client.post("/api/login", json={"login": "paulo", "senha": "rotina"})
        criado = client.post(
            "/api/admin/funcionarios",
            json={"nome": "Ana Costa", "login": "ana", "senha": "rotina", "papel": "equipe"},
        )
        assert criado.status_code == 200
    with TestClient(app) as equipe:
        assert equipe.post("/api/login", json={"login": "ana", "senha": "rotina"}).status_code == 200
        bloqueado = equipe.get("/api/admin/resumo")
        assert bloqueado.status_code == 403


def test_recepcionista_so_ve_e_fecha_o_proprio_caixa():
    with TestClient(app) as dono:
        dono.post("/api/login", json={"login": "paulo", "senha": "rotina"})
        criado = dono.post(
            "/api/admin/funcionarios",
            json={"nome": "Ana Costa", "login": "ana", "senha": "rotina", "papel": "recepcao"},
        )
        assert criado.status_code == 200
        aberto = dono.post("/api/caixas", json={"saldo_inicial": 20})
        assert aberto.status_code == 200
        caixa_id = aberto.json()["id"]
    with TestClient(app) as ana:
        assert ana.post("/api/login", json={"login": "ana", "senha": "rotina"}).status_code == 200
        assert ana.get("/api/caixas").json() == []
        assert ana.get("/api/painel").json()["caixa"] is None
        bloqueado = ana.post(f"/api/caixas/{caixa_id}/fechar", json={"saldo_informado": 20})
        assert bloqueado.status_code == 403
        dela = ana.post("/api/caixas", json={"saldo_inicial": 10})
        assert dela.status_code == 200
        assert dela.json()["operador"] == "Ana Costa"
        assert len(ana.get("/api/caixas").json()) == 1
    with TestClient(app) as dono:
        dono.post("/api/login", json={"login": "paulo", "senha": "rotina"})
        lista = dono.get("/api/caixas").json()
        assert len(lista) == 1
        assert lista[0]["id"] == caixa_id


def test_saida_de_estoque_nao_passa_do_que_existe():
    with TestClient(app) as client:
        client.post("/api/login", json={"login": "paulo", "senha": "rotina"})
        catalogo = client.post("/api/produtos", json={"nome": "Shampoo", "preco": 32, "estoque": 2, "minimo": 1}).json()
        produto_id = next(item["id"] for item in catalogo["produtos"] if item["nome"] == "Shampoo")
        falta = client.post("/api/estoque", json={"produto_id": produto_id, "quantidade": -5, "motivo": "Uso"})
        assert falta.status_code == 409
        ok = client.post("/api/estoque", json={"produto_id": produto_id, "quantidade": -1, "motivo": "Uso"})
        assert ok.status_code == 200
        assert ok.json()["estoque"] == 1

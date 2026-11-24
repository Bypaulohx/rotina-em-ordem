import os
from datetime import datetime, timedelta

os.environ["ROTINA_DB"] = "sqlite://"
os.environ["ROTINA_TEST"] = "1"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, configure, engine

configure("sqlite://")

from app.main import app


@pytest.fixture(autouse=True)
def banco_limpo():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _auth(client: TestClient) -> None:
    resposta = client.post("/api/login", json={"login": "paulo", "senha": "rotina"})
    assert resposta.status_code == 200


def _id_servico(catalogo: dict, tipo: str, porte: str) -> int:
    return next(item["id"] for item in catalogo["servicos"] if item["tipo"] == tipo and item["porte"] == porte)


def test_vaga_de_porte_grande_e_diaria_de_feriado():
    with TestClient(app) as client:
        _auth(client)
        catalogo = client.get("/api/catalogo").json()
        pessoas = client.post(
            "/api/clientes",
            json={"nome": "Helena Dias", "pet_nome": "Tico", "porte": "G", "cuidados": "Ração renal.", "telefone": "1133334444", "cep": "01310100", "logradouro": "Rua Augusta", "cidade": "São Paulo"},
        ).json()
        pet_id = pessoas[0]["pets"][0]["id"]
        banho_g = _id_servico(catalogo, "banho", "G")
        inicio = datetime(2026, 11, 10, 9, 0)
        primeiro = client.post(
            "/api/agendamentos",
            json={
                "pet_id": pet_id,
                "servico_id": banho_g,
                "inicio": inicio.isoformat(),
                "busca": (inicio + timedelta(hours=2)).isoformat(),
            },
        )
        assert primeiro.status_code == 200

        outro = client.post(
            "/api/clientes",
            json={"nome": "Caio Alves", "pet_nome": "Thor", "porte": "G", "telefone": "11988887766", "cep": "01310100", "logradouro": "Rua Augusta", "cidade": "São Paulo"},
        ).json()
        thor = next(p["pets"][0]["id"] for p in outro if p["nome"] == "Caio Alves")
        conflito = client.post(
            "/api/agendamentos",
            json={
                "pet_id": thor,
                "servico_id": banho_g,
                "inicio": inicio.isoformat(),
                "busca": (inicio + timedelta(hours=2)).isoformat(),
            },
        )
        assert conflito.status_code == 409
        assert "baia" in conflito.json()["detail"]["mensagem"].lower()

        caixa = client.post("/api/caixas", json={"nome": "Caixa da manhã", "saldo_inicial": 100})
        assert caixa.status_code == 200
        estadia = client.post(
            "/api/hospedagens",
            json={"pet_id": thor, "entrada": "2026-10-31", "checkout": "2026-11-03"},
        )
        assert estadia.status_code == 200
        corpo = estadia.json()
        assert any(item["feriado"] for item in corpo["diarias"])
        fechamento = client.post(
            f"/api/hospedagens/{corpo['id']}/checkout",
            json={"forma": "pix", "checkout": "2026-11-03"},
        )
        assert fechamento.status_code == 200
        descricoes = " ".join(item["descricao"] for item in fechamento.json()["venda"]["itens"])
        assert "Finados" in descricoes

        resumo = client.get("/api/caixas").json()[0]
        assert resumo["por_forma"]["pix"] > 0
        assert resumo["esperado_em_dinheiro"] == 100


def test_pacote_zera_a_busca_e_atraso_entra_se_a_equipe_confirmar():
    with TestClient(app) as client:
        _auth(client)
        catalogo = client.get("/api/catalogo").json()
        criado = client.post(
            "/api/clientes",
            json={"nome": "Rita Souza", "pet_nome": "Amora", "porte": "P", "telefone": "11977776655", "cep": "01310100", "logradouro": "Rua Augusta", "cidade": "São Paulo"},
        ).json()
        pet_id = next(p["pets"][0]["id"] for p in criado if p["nome"] == "Rita Souza")
        client.post("/api/caixas", json={"nome": "Caixa da tarde", "saldo_inicial": 50})
        pacote = client.post(
            "/api/pacotes",
            json={"pet_id": pet_id, "tipo": "banho", "quantidade": 4, "valor_total": 220, "forma": "pix"},
        )
        assert pacote.status_code == 200
        banho_p = _id_servico(catalogo, "banho", "P")
        inicio = datetime.now().replace(second=0, microsecond=0) - timedelta(hours=3)
        busca = inicio + timedelta(minutes=50)
        ag = client.post(
            "/api/agendamentos",
            json={"pet_id": pet_id, "servico_id": banho_p, "inicio": inicio.isoformat(), "busca": busca.isoformat()},
        )
        assert ag.status_code == 200, ag.text
        ag_id = ag.json()["id"]
        for passo in ("chegou", "iniciar", "pronto"):
            assert client.post(f"/api/agendamentos/{ag_id}/{passo}").status_code == 200
        recebimento = client.post(
            f"/api/agendamentos/{ag_id}/buscar",
            json={"forma": "dinheiro", "incluir_atraso": True},
        )
        assert recebimento.status_code == 200, recebimento.text
        venda = recebimento.json()["venda"]
        assert recebimento.json()["atraso"]["atrasou"] is True
        assert any(item["valor"] == 0 for item in venda["itens"])
        assert any("Atraso" in item["descricao"] for item in venda["itens"])
        assert venda["total"] == 20


def test_horario_de_outro_dia_sem_baixa_continua_no_mapa():
    with TestClient(app) as client:
        _auth(client)
        catalogo = client.get("/api/catalogo").json()
        criado = client.post(
            "/api/clientes",
            json={"nome": "Lara Nunes", "pet_nome": "Luna", "porte": "P", "telefone": "11966665544", "cep": "01310100", "logradouro": "Rua Augusta", "cidade": "São Paulo"},
        ).json()
        pet_id = next(p["pets"][0]["id"] for p in criado if p["nome"] == "Lara Nunes")
        inicio = datetime.now().replace(second=0, microsecond=0) - timedelta(days=2)
        resposta = client.post(
            "/api/agendamentos",
            json={
                "pet_id": pet_id,
                "servico_id": _id_servico(catalogo, "banho", "P"),
                "inicio": inicio.isoformat(),
                "busca": (inicio + timedelta(hours=1)).isoformat(),
            },
        )
        assert resposta.status_code == 200, resposta.text
        mapa = client.get("/api/mapa").json()
        ocupada = next(baia for baia in mapa["salao"] if baia["agora"] and baia["agora"]["pet"] == "Luna")
        assert ocupada["agora"]["status"] == "agendado"
        assert any("Luna" in alerta["texto"] for alerta in mapa["alertas"])

import os

os.environ.setdefault("ROTINA_DB", "sqlite://")
os.environ.setdefault("ROTINA_TEST", "1")

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.plataforma import ler_afd
from app.validacao import cpf_valido


@pytest.fixture(autouse=True)
def banco_limpo():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _entrar(client: TestClient) -> None:
    assert client.post("/api/login", json={"login": "paulo", "senha": "rotina"}).status_code == 200


def _cliente(client: TestClient, telefone: str = "11911112222") -> dict:
    pessoas = client.post(
        "/api/clientes",
        json={
            "nome": "João Lima",
            "telefone": telefone,
            "cep": "01310100",
            "logradouro": "Rua Augusta",
            "cidade": "São Paulo",
            "pet_nome": "Pipoca",
            "porte": "M",
        },
    ).json()
    return pessoas[0]


def test_cpf_rejeita_digito_errado():
    assert cpf_valido("529.982.247-25")
    assert not cpf_valido("529.982.247-24")


def test_telefone_repetido_nao_cria_outro_cliente():
    with TestClient(app) as client:
        _entrar(client)
        assert _cliente(client)["nome"] == "João Lima"
        repetido = client.post(
            "/api/clientes",
            json={
                "nome": "Outro João",
                "telefone": "(11) 91111-2222",
                "cep": "01310100",
                "logradouro": "Rua Augusta",
                "cidade": "São Paulo",
                "pet_nome": "Mel",
                "porte": "P",
            },
        )
        assert repetido.status_code == 409


def test_pacote_nao_usa_o_nome_do_animal():
    with TestClient(app) as client:
        _entrar(client)
        cliente = _cliente(client)
        client.post("/api/caixas", json={"nome": "Caixa", "saldo_inicial": 0})
        pet_id = cliente["pets"][0]["id"]
        ruim = client.post(
            "/api/pacotes",
            json={"pet_id": pet_id, "tipo": "banho", "quantidade": 4, "valor_total": 200, "forma": "pix", "nome": "Pipoca"},
        )
        assert ruim.status_code == 400
        bom = client.post(
            "/api/pacotes",
            json={"pet_id": pet_id, "tipo": "banho", "quantidade": 4, "valor_total": 200, "forma": "pix", "nome": "Banho e tosa — 4 sessões"},
        )
        assert bom.status_code == 200
        assert "Pipoca" not in bom.json()["itens"][0]["descricao"]
        ficha = client.get(f"/api/pets/{pet_id}/ficha").json()
        assert ficha["pacotes"][0]["restantes"] == 4
        assert ficha["pacotes"][0]["nome"] == "Banho e tosa — 4 sessões"


def test_leitor_baixa_o_estoque_uma_vez():
    with TestClient(app) as client:
        _entrar(client)
        cliente = _cliente(client)
        client.post("/api/caixas", json={"nome": "Caixa", "saldo_inicial": 10})
        client.post("/api/produtos", json={"nome": "Ração", "preco": 40, "estoque": 3, "minimo": 1})
        codigo = client.post(
            "/api/pdv",
            json={"cliente_id": cliente["id"], "forma": "dinheiro", "itens": [{"codigo": "7891000000099", "quantidade": 1}]},
        )
        assert codigo.status_code == 404
        from app.database import SessionLocal
        from app.models import Produto

        db = SessionLocal()
        produto = db.query(Produto).filter(Produto.nome == "Ração").one()
        produto.codigo_barras = "7891000000099"
        db.commit()
        db.close()
        venda = client.post(
            "/api/pdv",
            json={"cliente_id": cliente["id"], "forma": "dinheiro", "itens": [{"codigo": "7891000000099", "quantidade": 2}]},
        )
        assert venda.status_code == 200, venda.text
        assert venda.json()["total"] == 80
        de_novo = client.post(
            "/api/pdv",
            json={"cliente_id": cliente["id"], "forma": "pix", "itens": [{"codigo": "7891000000099", "quantidade": 2}]},
        )
        assert de_novo.status_code == 409


def test_pagamento_dividido_sangria_e_venda_suspensa():
    with TestClient(app) as client:
        _entrar(client)
        cliente = _cliente(client, "11970007001")
        client.post("/api/caixas", json={"saldo_inicial": 10})
        client.post("/api/produtos", json={"nome": "Coleira", "preco": 30, "estoque": 4, "minimo": 1})
        from app.database import SessionLocal
        from app.models import Produto

        db = SessionLocal()
        produto = db.query(Produto).filter(Produto.nome == "Coleira").one()
        produto.codigo_barras = "7891000000777"
        db.commit()
        db.close()
        suspensa = client.post(
            "/api/pdv/suspender",
            json={"cliente_id": cliente["id"], "itens": [{"codigo": "7891000000777", "quantidade": 1}]},
        )
        assert suspensa.status_code == 200, suspensa.text
        estoque = client.get("/api/pdv/produtos?q=Coleira").json()[0]["estoque"]
        assert estoque == 4
        venda = client.post(
            "/api/pdv",
            json={
                "cliente_id": cliente["id"],
                "venda_id": suspensa.json()["id"],
                "itens": [{"codigo": "7891000000777", "quantidade": 2}],
                "pagamentos": [
                    {"forma": "dinheiro", "valor": 20, "recebido": 50},
                    {"forma": "pix", "valor": 40},
                ],
            },
        )
        assert venda.status_code == 200, venda.text
        assert venda.json()["total"] == 60
        assert venda.json()["forma"] == "misto"
        assert venda.json()["pagamentos"][0]["troco"] == 30
        caixa = client.get("/api/caixas").json()[0]
        assert caixa["por_forma"]["dinheiro"] == 20
        assert caixa["esperado_em_dinheiro"] == 30
        sangria = client.post(f"/api/caixas/{caixa['id']}/movimento", json={"tipo": "sangria", "valor": 10, "motivo": "Troco do banco"})
        assert sangria.status_code == 200, sangria.text
        assert sangria.json()["esperado_em_dinheiro"] == 20


def test_codigo_de_balanca_vende_por_peso():
    with TestClient(app) as client:
        _entrar(client)
        cliente = _cliente(client, "11970007002")
        client.post("/api/caixas", json={"saldo_inicial": 0})
        criado = client.post("/api/produtos", json={"nome": "Petisco a granel", "preco": 40, "estoque": 1000, "minimo": 1})
        assert criado.status_code == 200, criado.text
        from app.database import SessionLocal
        from app.models import Produto

        db = SessionLocal()
        produto = db.query(Produto).filter(Produto.nome == "Petisco a granel").one()
        produto.codigo_barras = "00123"
        produto.unidade = "kg"
        db.commit()
        db.close()
        venda = client.post(
            "/api/pdv",
            json={"cliente_id": cliente["id"], "forma": "dinheiro", "itens": [{"codigo": "2001230025006"}]},
        )
        assert venda.status_code == 200, venda.text
        assert venda.json()["total"] == 10
        assert venda.json()["itens"][0]["gramas"] == 250
        restante = client.get("/api/pdv/produtos?q=Petisco").json()[0]["estoque"]
        assert restante == 750


def test_afd_nao_duplica_marcacao():
    linha = "0000000013161120260800123456789012\n"
    marcas = ler_afd(linha)
    assert marcas[0]["pis"] == "123456789012"
    assert marcas[0]["marcada_em"].hour == 8
    with TestClient(app) as client:
        _entrar(client)
        primeiro = client.post("/api/ponto/afd", files={"arquivo": ("ponto.txt", linha.encode("latin-1"), "text/plain")})
        assert primeiro.status_code == 200, primeiro.text
        assert primeiro.json()["novas"] == 1
        segundo = client.post("/api/ponto/afd", files={"arquivo": ("ponto.txt", linha.encode("latin-1"), "text/plain")})
        assert segundo.json()["novas"] == 0


def test_pedido_da_loja_reserva_e_so_entra_no_caixa_uma_vez():
    with TestClient(app) as client:
        _entrar(client)
        client.post("/api/caixas", json={"nome": "Caixa", "saldo_inicial": 0})
        client.post("/api/produtos", json={"nome": "Coleira", "preco": 25, "estoque": 1, "minimo": 0})
        from app.database import SessionLocal
        from app.models import Produto

        db = SessionLocal()
        produto = db.query(Produto).filter(Produto.nome == "Coleira").one()
        produto_id = produto.id
        db.close()
    with TestClient(app) as loja:
        cadastro = loja.post(
            "/api/loja/cadastro",
            json={"nome": "Marina", "email": "marina@exemplo.com", "telefone": "11900001111", "senha": "segredo"},
        )
        assert cadastro.status_code == 200, cadastro.text
        pedido = loja.post("/api/loja/pedidos", json={"itens": [{"produto_id": produto_id, "quantidade": 1}], "entrega": "retirada"})
        assert pedido.status_code == 200, pedido.text
        esgotado = loja.post("/api/loja/pedidos", json={"itens": [{"produto_id": produto_id, "quantidade": 1}], "entrega": "retirada"})
        assert esgotado.status_code == 409
    with TestClient(app) as client:
        _entrar(client)
        recebido = client.post(f"/api/loja/pedidos/{pedido.json()['id']}/receber", json={"forma": "pix"})
        assert recebido.status_code == 200, recebido.text
        repetido = client.post(f"/api/loja/pedidos/{pedido.json()['id']}/receber", json={"forma": "pix"})
        assert repetido.status_code == 409

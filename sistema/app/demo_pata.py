from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta
from pathlib import Path

from .database import configure, migrar
from .gestao import criar_despesa, criar_produto, movimentar_estoque
from .models import (
    Baia,
    Caixa,
    Cliente,
    ConfigLoja,
    Fornecedor,
    MovimentoEstoque,
    Pet,
    Produto,
    Profissional,
    Servico,
    Usuario,
    Venda,
)
from .plataforma import cancelar_venda, criar_fornecedor, suspender_pdv, vender_pdv
from .security import hash_senha
from .seed import BAIAS, SERVICOS
from .services import abrir_caixa, caixa_dict, criar_agendamento, criar_cliente_pet, fechar_caixa, movimentar_caixa
from .validacao import email_valido, telefone_valido

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "pata_demo.db"
IMAGENS = RAIZ / "uploads" / "pata"
CREDENCIAIS = RAIZ / ".pata-credenciais.txt"
MARCA = "Pata & Cia Pet Center"

FAMILIAS = [
    ("Ração cão", "Rações para cães", "Canil Demo", "un"),
    ("Ração gato", "Rações para gatos", "Gato Demo", "un"),
    ("Ração especial", "Rações especiais", "Nutri Demo", "un"),
    ("Petisco", "Petiscos", "Mordida Demo", "un"),
    ("Cuidado", "Higiene", "Limpo Demo", "un"),
    ("Brinquedo", "Brinquedos", "Pula Demo", "un"),
    ("Coleira", "Coleiras e guias", "Guia Demo", "un"),
    ("Cama", "Camas e acessórios", "Ninho Demo", "un"),
    ("Limpeza", "Produtos de limpeza", "Casa Demo", "un"),
    ("Areia", "Areias sanitárias", "Caixa Demo", "un"),
    ("Bolsa", "Produtos de transporte", "Viagem Demo", "un"),
    ("Granel", "Petiscos", "Balcão Demo", "kg"),
]
VARIANTES = ["mini", "pequeno", "médio", "grande", "refil", "kit", "avulso"]
FORNECEDORES = [
    ("Distribuidora Pet Norte", "1130001001", "compras@pet-norte.example"),
    ("Alimentos Animal Premium", "1130001002", "vendas@animal-premium.example"),
    ("Mundo dos Acessórios", "1130001003", "contato@acessorios-demo.example"),
    ("Higiene Animal Distribuidora", "1130001004", "pedidos@higiene-demo.example"),
    ("Pet Care Produtos", "1130001005", "comercial@petcare-demo.example"),
    ("Atacado Bicho Feliz", "1130001006", "atacado@bicho-feliz.example"),
]
EQUIPE = [
    ("Ricardo Martins", "ricardo.martins", "admin"),
    ("Fernanda Costa", "fernanda.costa", "gerente"),
    ("Lucas Almeida", "lucas.almeida", "recepcao"),
    ("Camila Oliveira", "camila.oliveira", "recepcao"),
    ("Mariana Santos", "mariana.santos", "estoquista"),
    ("Gabriel Ferreira", "gabriel.ferreira", "gerente"),
    ("Juliana Ribeiro", "juliana.ribeiro", "recepcao"),
    ("Rafael Mendes", "rafael.mendes", "tosador"),
]
NOMES = ["Ana", "Bruno", "Caio", "Dora", "Elisa", "Fábio", "Helena", "Igor", "Júlia", "Kaio", "Lara", "Miguel", "Nina", "Otávio", "Paula", "Quésia", "Rita", "Sérgio", "Tainá", "Vitor"]
SOBRENOMES = ["Alencar", "Brito", "Campos", "Dutra", "Esteves", "Farias", "Guedes", "Holanda", "Ibrahim", "Junqueira", "Klein", "Lacerda", "Moura", "Nogueira", "Pacheco", "Queiroz", "Ramos", "Salles", "Tavares", "Vargas"]
ESPECIES = [("Cachorro", "P"), ("Cachorro", "M"), ("Cachorro", "G"), ("Gato", "P"), ("Gato", "M"), ("Ave", "P")]
PETS = ["Amora", "Bidu", "Cacau", "Dudu", "Estrela", "Frida", "Geléia", "Hugo", "Iris", "Jujuba", "Kiko", "Luna", "Mel", "Nino", "Olívia", "Pippo", "Quindim", "Romeu", "Sol", "Teca"]


def preparar_banco() -> None:
    from . import database

    configure(f"sqlite:///{BANCO.as_posix()}")
    database.Base.metadata.create_all(database.engine)
    migrar()


def _svg(titulo: str, linha: str, cor: str) -> str:
    seguro = titulo.replace("&", "e")[:28]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 640 480">
<rect width="640" height="480" fill="#f4f1ea"/>
<rect x="48" y="36" width="544" height="408" rx="8" fill="{cor}"/>
<rect x="78" y="66" width="484" height="300" rx="4" fill="#fff"/>
<text x="96" y="150" font-family="Segoe UI, sans-serif" font-size="28" fill="#1b2420">{seguro}</text>
<text x="96" y="196" font-family="Segoe UI, sans-serif" font-size="18" fill="#5c675f">{linha}</text>
<text x="96" y="400" font-family="Segoe UI, sans-serif" font-size="16" fill="#fff">Demonstração · Pata &amp; Cia</text>
</svg>"""


def _cor(texto: str) -> str:
    paleta = ["#1f6b4a", "#245c4a", "#3d6b4f", "#1b4f6b", "#6b4a1f", "#4a3d6b", "#6b3d45", "#2f5d50"]
    return paleta[sum(ord(c) for c in texto) % len(paleta)]


def _gravar_imagem(nome: str, linha: str, arquivo: str) -> str:
    IMAGENS.mkdir(parents=True, exist_ok=True)
    destino = IMAGENS / arquivo
    destino.write_text(_svg(nome, linha, _cor(nome + linha)), encoding="utf-8")
    return f"/uploads/pata/{arquivo}"


def _usuario(db, nome: str, login: str, papel: str, senha: str) -> Usuario:
    usuario = Usuario(nome=nome, login=login, senha_hash=hash_senha(senha), papel=papel)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def _base(db) -> None:
    db.add(ConfigLoja(id=1, tolerancia_busca_min=15, valor_atraso=20, nome=MARCA, slogan="Cuidando de quem faz parte da família."))
    for nome, tipo, porte, duracao, preco, feriado in SERVICOS:
        db.add(Servico(nome=nome, tipo=tipo, porte=porte, duracao_min=duracao, preco=preco, preco_feriado=feriado))
    for nome, porte, tipo in BAIAS:
        db.add(Baia(nome=nome, porte=porte, tipo=tipo, ativo=True))
    db.add(Profissional(nome="Juliana Ribeiro", ativo=True))
    db.add(Profissional(nome="Rafael Mendes", ativo=True))
    db.commit()
    _gravar_imagem("Pata & Cia", "Pet Center", "logo.svg")


def _produtos(db, fornecedores: list[Fornecedor], estoquista: Usuario) -> list[Produto]:
    criados = []
    indice = 1
    for familia, categoria, marca, unidade in FAMILIAS:
        fornecedor = fornecedores[indice % len(fornecedores)]
        for variante in VARIANTES:
            nome = f"{familia} {variante}"
            preco = round(18 + (indice * 3.4) % 90, 2)
            criar_produto(db, nome, preco, 0, 4 if indice % 9 else 8)
            produto = db.query(Produto).filter(Produto.nome == nome).one()
            produto.codigo_barras = f"900{indice:010d}"
            produto.categoria = categoria
            produto.marca = marca
            produto.custo = round(preco * 0.58, 2)
            produto.fornecedor_id = fornecedor.id
            produto.unidade = unidade
            produto.foto = _gravar_imagem(nome, categoria, f"{indice:03d}.svg")
            if unidade == "kg":
                produto.codigo_barras = f"{indice:05d}"
            db.commit()
            quantidade = 6000 if unidade == "kg" else 40
            movimentar_estoque(db, produto.id, quantidade, f"Compra de demonstração — {fornecedor.nome}", estoquista.id)
            criados.append(produto)
            indice += 1
    return criados


def _clientes(db) -> list[Cliente]:
    for numero in range(80):
        especie, porte = ESPECIES[numero % len(ESPECIES)]
        telefone = f"1190001{numero:04d}"
        criar_cliente_pet(db, {
            "nome": f"{NOMES[numero % len(NOMES)]} {SOBRENOMES[numero % len(SOBRENOMES)]} Demo",
            "telefone": telefone,
            "cep": "00000000",
            "logradouro": "Rua da Demonstração",
            "bairro": "Bairro Fictício",
            "cidade": "Cidade Demonstração",
            "uf": "ZZ",
            "numero": str(100 + numero),
            "email": f"tutor{numero:03d}@demo.pata-cia.example",
            "pet_nome": f"{PETS[numero % len(PETS)]} {numero + 1}",
            "especie": especie,
            "porte": porte,
            "raca": "Sem raça definida",
            "observacoes": "Cadastro sintético da Pata & Cia. Não é uma pessoa real.",
            "cuidados": "Dado de demonstração.",
            "nascimento": date(2018, 1, 1) + timedelta(days=numero * 17),
        })
    for numero in range(80, 120):
        telefone = f"1190001{numero:04d}"
        if not telefone_valido(telefone) or not email_valido(f"tutor{numero:03d}@demo.pata-cia.example"):
            raise RuntimeError("Contato sintético rejeitado pela validação.")
        db.add(Cliente(
            nome=f"{NOMES[numero % len(NOMES)]} {SOBRENOMES[(numero + 3) % len(SOBRENOMES)]} Demo",
            telefone=telefone,
            cep="00000000",
            logradouro="Rua da Demonstração",
            bairro="Bairro Fictício",
            cidade="Cidade Demonstração",
            uf="ZZ",
            numero=str(100 + numero),
            email=f"tutor{numero:03d}@demo.pata-cia.example",
            observacoes="Cliente de demonstração sem animal vinculado.",
        ))
    db.commit()
    return db.query(Cliente).order_by(Cliente.id).all()


def _vender(db, operador, cliente, produto, forma, quando, desconto=0, partes=None):
    item = {"produto_id": produto.id, "gramas": 250} if produto.unidade == "kg" else {"produto_id": produto.id, "quantidade": 1}
    venda = vender_pdv(db, cliente.id, [item], forma, operador.id, partes or [], "Venda de demonstração.", None, desconto, 0, None)
    row = db.get(Venda, venda["id"])
    row.criada_em = quando
    db.commit()
    return row


def _turno(db, operador, nome, abertura, clientes, produtos, quantidade, fechamento, diferenca=0.0):
    abrir_caixa(db, operador, 150)
    caixa = db.query(Caixa).filter(Caixa.usuario_id == operador.id, Caixa.status == "aberto").one()
    caixa.nome = nome
    caixa.aberto_em = abertura
    db.commit()
    formas = ["dinheiro", "pix", "debito", "credito"]
    for indice in range(quantidade):
        produto = produtos[indice % len(produtos)]
        cliente = clientes[indice % len(clientes)]
        quando = abertura + timedelta(hours=indice % 20, minutes=indice % 50)
        forma = formas[indice % len(formas)]
        desconto = 2 if indice % 11 == 0 else 0
        partes = None
        if indice % 13 == 0 and produto.unidade != "kg":
            total = round(produto.preco - desconto, 2)
            metade = round(total / 2, 2)
            partes = [
                {"forma": "dinheiro", "valor": metade, "recebido": metade},
                {"forma": "pix", "valor": round(total - metade, 2)},
            ]
            forma = "dinheiro"
        _vender(db, operador, cliente, produto, forma, quando, desconto, partes)
    if quantidade > 8:
        movimentar_caixa(db, caixa.id, operador, "suprimento", 40, "Troco de demonstração")
        movimentar_caixa(db, caixa.id, operador, "sangria", 30, "Depósito de demonstração")
    esperado = caixa_dict(db, db.get(Caixa, caixa.id))["esperado_em_dinheiro"]
    fechar_caixa(db, caixa.id, round(esperado + diferenca, 2), operador)
    fechado = db.get(Caixa, caixa.id)
    fechado.fechado_em = fechamento
    db.commit()


def _agendamentos(db) -> int:
    feitos = 0
    servicos = db.query(Servico).filter(Servico.tipo == "banho").all()
    profissional = db.query(Profissional).filter(Profissional.nome == "Rafael Mendes").one()
    pets = db.query(Pet).limit(12).all()
    amanha = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    for indice, pet in enumerate(pets):
        servico = next((item for item in servicos if item.porte == pet.porte), None)
        if servico is None:
            continue
        inicio = amanha + timedelta(days=indice % 5, hours=indice % 6)
        try:
            criar_agendamento(db, {
                "pet_id": pet.id,
                "servico_id": servico.id,
                "inicio": inicio,
                "busca": inicio + timedelta(hours=2),
                "profissional_id": profissional.id,
            })
            feitos += 1
        except Exception:
            db.rollback()
    return feitos


def carregar(db) -> dict:
    if db.query(Usuario).filter(Usuario.login == "ricardo.martins").first():
        return {"status": "ja-carregada"}
    _base(db)
    senhas = {}
    equipe = {}
    for nome, login, papel in EQUIPE:
        senha = secrets.token_urlsafe(9)
        senhas[login] = senha
        equipe[login] = _usuario(db, nome, login, papel, senha)
    CREDENCIAIS.write_text(
        "Pata & Cia — credenciais temporárias de demonstração.\n"
        "Não publique este arquivo. As senhas estão só no hash do banco.\n\n"
        + "\n".join(f"{login}  {senha}  ({equipe[login].papel})" for login, senha in senhas.items())
        + "\n",
        encoding="utf-8",
    )
    fornecedores = []
    for nome, telefone, email in FORNECEDORES:
        criar_fornecedor(db, nome, telefone, email)
        fornecedores.append(db.query(Fornecedor).filter(Fornecedor.nome == nome).one())
    produtos = _produtos(db, fornecedores, equipe["mariana.santos"])
    clientes = _clientes(db)
    agora = datetime.now()
    vendaveis = [item for item in produtos if item.unidade == "un"][:36]
    _turno(db, equipe["lucas.almeida"], "Balcão 1 — Lucas Almeida", agora - timedelta(days=28), clientes, vendaveis, 100, agora - timedelta(days=2))
    _turno(db, equipe["camila.oliveira"], "Balcão 2 — Camila Oliveira", agora - timedelta(days=20), clientes, vendaveis, 70, agora - timedelta(days=1), diferenca=-8)
    abrir_caixa(db, equipe["lucas.almeida"], 200)
    caixa = db.query(Caixa).filter(Caixa.usuario_id == equipe["lucas.almeida"].id, Caixa.status == "aberto").one()
    caixa.nome = "Balcão 1 — turno de hoje"
    db.commit()
    for indice in range(8):
        _vender(db, equipe["lucas.almeida"], clientes[indice], vendaveis[indice], "dinheiro" if indice % 2 == 0 else "pix", agora - timedelta(hours=indice))
    db.expire_all()
    for indice in range(4):
        venda = _vender(db, equipe["lucas.almeida"], clientes[indice + 8], vendaveis[indice + 8], "debito", agora - timedelta(hours=1))
        db.expire_all()
        cancelar_venda(db, venda.id, equipe["lucas.almeida"])
    for indice in range(4):
        item = {"produto_id": vendaveis[indice].id, "quantidade": 1}
        suspensa = suspender_pdv(db, clientes[indice + 20].id, [item], equipe["lucas.almeida"].id, "Venda suspensa de demonstração.")
        row = db.get(Venda, suspensa["id"])
        row.criada_em = agora - timedelta(minutes=30 + indice)
        db.commit()
    for produto in produtos[70:74]:
        if produto.estoque:
            movimentar_estoque(db, produto.id, -produto.estoque, "Inventário de demonstração — sem saldo", equipe["mariana.santos"].id)
    for produto in produtos[74:78]:
        alvo = max(produto.minimo - 1, 0)
        delta = alvo - produto.estoque
        if delta:
            movimentar_estoque(db, produto.id, delta, "Inventário de demonstração — estoque baixo", equipe["mariana.santos"].id)
    from .models import Despesa

    for descricao, valor, categoria in [
        ("Aluguel do ponto de demonstração", 4500, "ocupacao"),
        ("Energia de demonstração", 680, "ocupacao"),
        ("Água de demonstração", 190, "ocupacao"),
        ("Internet de demonstração", 220, "ocupacao"),
        ("Material de consumo de demonstração", 340, "loja"),
    ]:
        criar_despesa(db, descricao, valor, date.today() - timedelta(days=10), categoria)
    for despesa in db.query(Despesa).all():
        if "Água" in despesa.descricao or "consumo" in despesa.descricao:
            despesa.status = "aberta"
    db.commit()
    agenda = _agendamentos(db)
    inconsistentes = []
    db.expire_all()
    for produto in db.query(Produto).all():
        saldo = sum(item.quantidade for item in db.query(MovimentoEstoque).filter(MovimentoEstoque.produto_id == produto.id))
        if saldo != produto.estoque:
            inconsistentes.append(produto.nome)
    return {
        "status": "criada",
        "clientes": db.query(Cliente).count(),
        "pets": db.query(Pet).count(),
        "produtos": db.query(Produto).count(),
        "vendas": db.query(Venda).count(),
        "pagas": db.query(Venda).filter(Venda.status == "paga").count(),
        "agenda": agenda,
        "estoque_inconsistente": inconsistentes,
        "credenciais": str(CREDENCIAIS),
    }


def main() -> None:
    from . import database

    preparar_banco()
    db = database.SessionLocal()
    try:
        resumo = carregar(db)
    finally:
        db.close()
    print(resumo)


if __name__ == "__main__":
    main()

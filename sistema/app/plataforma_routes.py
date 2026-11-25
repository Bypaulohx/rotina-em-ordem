from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db
from .models import Cliente, ClienteSessao, Usuario
from .plataforma import (
    adicionar_pet,
    atualizar_ficha_pet,
    criar_conta,
    atualizar_fornecedor,
    criar_fornecedor,
    listar_fornecedores,
    exigir_gestao,
    ficha_cliente,
    ficha_pet,
    importar_afd,
    indicadores,
    ler_notificacao,
    loja_agenda,
    loja_agendar,
    loja_cadastrar,
    loja_entrar,
    loja_horarios,
    loja_pedir,
    loja_pets,
    loja_produtos,
    loja_vitrine,
    notificacoes,
    pagar_conta,
    pedidos_cliente,
    ponto_painel,
    produto_por_codigo,
    buscar_produtos,
    cancelar_venda,
    listar_suspensas,
    receber_pedido,
    registrar_peso,
    registrar_vacina,
    salvar_foto,
    suspender_pdv,
    vender_pdv,
)
from .routes import _chamar, usuario_atual
from .services import limpar_baia

router = APIRouter(prefix="/api")
COOKIE_CLIENTE = "cliente"


class PetNovoIn(BaseModel):
    nome: str
    porte: str
    especie: str = "cão"
    raca: str = ""
    sexo: str = ""
    nascimento: date | None = None
    cuidados: str = ""
    alergias: str = ""
    comportamento: str = ""


class FichaPetIn(BaseModel):
    raca: str | None = None
    sexo: str | None = None
    alergias: str | None = None
    doencas: str | None = None
    medicamentos: str | None = None
    comportamento: str | None = None
    emergencia_nome: str | None = None
    emergencia_telefone: str | None = None
    cuidados: str | None = None
    alimentacao: str | None = None
    nascimento: date | None = None


class PesoIn(BaseModel):
    peso: float


class VacinaIn(BaseModel):
    nome: str
    aplicada_em: date
    proxima: date | None = None


class LeituraIn(BaseModel):
    chave: str


class PagamentoIn(BaseModel):
    forma: str
    valor: float
    recebido: float | None = None
    parcelas: int | None = None


class PdvIn(BaseModel):
    cliente_id: int
    forma: str = "dinheiro"
    itens: list[dict]
    pagamentos: list[PagamentoIn] = []
    observacao: str = ""
    pet_id: int | None = None
    desconto: float = 0
    acrescimo: float = 0
    venda_id: int | None = None


class MovimentoCaixaIn(BaseModel):
    tipo: str
    valor: float
    motivo: str = ""


class TransferirCaixaIn(BaseModel):
    usuario_id: int


class FornecedorIn(BaseModel):
    nome: str
    telefone: str = ""
    email: str = ""


class ContratoFornecedorIn(BaseModel):
    cpf: str = ""
    dia_vencimento: int = 5
    contrato: str = "indefinido"
    contrato_fim: date | None = None


class ContaIn(BaseModel):
    descricao: str
    valor: float
    vencimento: date
    categoria: str = "loja"


class LojaCadastroIn(BaseModel):
    nome: str
    email: str
    telefone: str
    senha: str
    cep: str = ""
    logradouro: str = ""
    cidade: str = ""
    uf: str = ""


class LojaLoginIn(BaseModel):
    email: str
    senha: str


class PedidoIn(BaseModel):
    itens: list[dict]
    entrega: str = "retirada"


class AgendaLojaIn(BaseModel):
    pet_id: int
    servico_id: int
    inicio: datetime


class ReceberPedidoIn(BaseModel):
    forma: str = "pix"


def _gestao(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    _chamar(exigir_gestao, usuario)
    return usuario


def cliente_atual(request: Request, db: Session = Depends(get_db)) -> Cliente:
    token = request.cookies.get(COOKIE_CLIENTE)
    sessao = db.get(ClienteSessao, token) if token else None
    if sessao is None or sessao.expira_em < datetime.now():
        raise HTTPException(status_code=401, detail={"mensagem": "Entre na loja para continuar."})
    cliente = db.get(Cliente, sessao.cliente_id)
    if cliente is None:
        raise HTTPException(status_code=401, detail={"mensagem": "Entre na loja para continuar."})
    return cliente


def _entrar_cliente(response: Response, db: Session, cliente: Cliente) -> dict:
    token = secrets.token_urlsafe(32)
    db.add(ClienteSessao(token=token, cliente_id=cliente.id, expira_em=datetime.now() + timedelta(days=30)))
    db.commit()
    response.set_cookie(COOKIE_CLIENTE, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
    return {"id": cliente.id, "nome": cliente.nome, "email": cliente.email}


@router.get("/notificacoes")
def ver_notificacoes(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return notificacoes(db, usuario.id)


@router.post("/notificacoes/lida")
def marcar(dados: LeituraIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return _chamar(ler_notificacao, db, usuario.id, dados.chave)


@router.get("/clientes/{cliente_id}")
def ver_cliente(cliente_id: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(ficha_cliente, db, cliente_id)


@router.post("/clientes/{cliente_id}/pets")
def novo_pet(cliente_id: int, dados: PetNovoIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(adicionar_pet, db, cliente_id, dados.model_dump())


@router.get("/pets/{pet_id}/ficha")
def ver_pet(pet_id: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(ficha_pet, db, pet_id)


@router.patch("/pets/{pet_id}/ficha")
def gravar_pet(pet_id: int, dados: FichaPetIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(atualizar_ficha_pet, db, pet_id, dados.model_dump(exclude_none=True))


@router.post("/pets/{pet_id}/peso")
def peso(pet_id: int, dados: PesoIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(registrar_peso, db, pet_id, dados.peso)


@router.post("/pets/{pet_id}/vacinas")
def vacina(pet_id: int, dados: VacinaIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(registrar_vacina, db, pet_id, dados.nome, dados.aplicada_em, dados.proxima)


@router.post("/pets/{pet_id}/foto")
async def foto(pet_id: int, arquivo: UploadFile = File(...), db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    extensao = ".jpg"
    if arquivo.filename and "." in arquivo.filename:
        candidato = "." + arquivo.filename.rsplit(".", 1)[-1].lower()
        if candidato in {".jpg", ".jpeg", ".png", ".webp"}:
            extensao = ".jpg" if candidato == ".jpeg" else candidato
    conteudo = await arquivo.read()
    return _chamar(salvar_foto, db, pet_id, conteudo, extensao)


@router.get("/produtos/codigo/{codigo}")
def por_codigo(codigo: str, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(produto_por_codigo, db, codigo)


@router.post("/pdv")
def pdv(dados: PdvIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return _chamar(
        vender_pdv,
        db,
        dados.cliente_id,
        dados.itens,
        dados.forma,
        usuario.id,
        [item.model_dump() for item in dados.pagamentos],
        dados.observacao,
        dados.pet_id,
        dados.desconto,
        dados.acrescimo,
        dados.venda_id,
    )


@router.get("/pdv/produtos")
def pdv_produtos(q: str = "", db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return buscar_produtos(db, q)


@router.get("/pdv/suspensas")
def pdv_suspensas(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return listar_suspensas(db, usuario.id)


@router.post("/pdv/suspender")
def pdv_suspender(dados: PdvIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return _chamar(suspender_pdv, db, dados.cliente_id, dados.itens, usuario.id, dados.observacao, dados.pet_id)


@router.post("/vendas/{venda_id}/cancelar")
def cancelar(venda_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return _chamar(cancelar_venda, db, venda_id, usuario)


@router.post("/baias/{baia_id}/limpar")
def limpar(baia_id: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(limpar_baia, db, baia_id)


@router.get("/indicadores")
def ver_indicadores(
    de: date | None = None,
    ate: date | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_gestao),
):
    hoje = date.today()
    inicio = de or hoje.replace(day=1)
    return _chamar(indicadores, db, inicio, ate or hoje)


@router.get("/fornecedores")
def ver_fornecedores(db: Session = Depends(get_db), _: Usuario = Depends(_gestao)):
    return listar_fornecedores(db)


@router.post("/fornecedores")
def fornecedor(dados: FornecedorIn, db: Session = Depends(get_db), _: Usuario = Depends(_gestao)):
    return _chamar(criar_fornecedor, db, dados.nome, dados.telefone, dados.email)


@router.patch("/fornecedores/{fornecedor_id}")
def contrato_fornecedor(fornecedor_id: int, dados: ContratoFornecedorIn, db: Session = Depends(get_db), _: Usuario = Depends(_gestao)):
    return _chamar(atualizar_fornecedor, db, fornecedor_id, dados.cpf, dados.dia_vencimento, dados.contrato, dados.contrato_fim)


@router.post("/contas")
def conta(dados: ContaIn, db: Session = Depends(get_db), usuario: Usuario = Depends(_gestao)):
    return _chamar(criar_conta, db, dados.descricao, dados.valor, dados.vencimento, dados.categoria, usuario.id)


@router.post("/contas/{conta_id}/pagar")
def quitar(conta_id: int, db: Session = Depends(get_db), _: Usuario = Depends(_gestao)):
    return _chamar(pagar_conta, db, conta_id)


@router.get("/ponto")
def ponto(db: Session = Depends(get_db), _: Usuario = Depends(_gestao)):
    return ponto_painel(db)


@router.post("/ponto/afd")
async def ponto_afd(arquivo: UploadFile = File(...), db: Session = Depends(get_db), _: Usuario = Depends(_gestao)):
    texto = (await arquivo.read()).decode("latin-1", errors="replace")
    return _chamar(importar_afd, db, texto, "afd")


@router.get("/loja/produtos")
def vitrine(db: Session = Depends(get_db)):
    return loja_produtos(db)


@router.get("/loja/vitrine")
def vitrine_completa(db: Session = Depends(get_db)):
    return loja_vitrine(db)


@router.get("/loja/pets")
def pets_da_conta(db: Session = Depends(get_db), cliente: Cliente = Depends(cliente_atual)):
    return loja_pets(db, cliente.id)


@router.post("/loja/pets")
def pet_da_conta(dados: PetNovoIn, db: Session = Depends(get_db), cliente: Cliente = Depends(cliente_atual)):
    return _chamar(adicionar_pet, db, cliente.id, dados.model_dump())


@router.get("/loja/horarios")
def horarios_loja(
    pet_id: int,
    servico_id: int,
    dia: date,
    db: Session = Depends(get_db),
    cliente: Cliente = Depends(cliente_atual),
):
    return _chamar(loja_horarios, db, cliente.id, pet_id, servico_id, dia)


@router.get("/loja/agendamentos")
def agenda_loja(db: Session = Depends(get_db), cliente: Cliente = Depends(cliente_atual)):
    return loja_agenda(db, cliente.id)


@router.post("/loja/agendamentos")
def agendar_loja(dados: AgendaLojaIn, db: Session = Depends(get_db), cliente: Cliente = Depends(cliente_atual)):
    return _chamar(loja_agendar, db, cliente.id, dados.pet_id, dados.servico_id, dados.inicio)


@router.post("/loja/cadastro")
def cadastro_loja(dados: LojaCadastroIn, response: Response, db: Session = Depends(get_db)):
    cliente = _chamar(loja_cadastrar, db, dados.model_dump())
    row = db.get(Cliente, cliente["id"])
    return _entrar_cliente(response, db, row)


@router.post("/loja/login")
def login_loja(dados: LojaLoginIn, response: Response, db: Session = Depends(get_db)):
    cliente = _chamar(loja_entrar, db, dados.email, dados.senha)
    return _entrar_cliente(response, db, cliente)


@router.post("/loja/logout")
def sair_loja(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_CLIENTE)
    if token:
        sessao = db.get(ClienteSessao, token)
        if sessao:
            db.delete(sessao)
            db.commit()
    response.delete_cookie(COOKIE_CLIENTE)
    return {"ok": True}


@router.get("/loja/me")
def me_loja(cliente: Cliente = Depends(cliente_atual)):
    return {"id": cliente.id, "nome": cliente.nome, "email": cliente.email}


@router.post("/loja/pedidos")
def pedir(dados: PedidoIn, db: Session = Depends(get_db), cliente: Cliente = Depends(cliente_atual)):
    return _chamar(loja_pedir, db, cliente.id, dados.itens, dados.entrega)


@router.get("/loja/pedidos")
def meus_pedidos(db: Session = Depends(get_db), cliente: Cliente = Depends(cliente_atual)):
    return pedidos_cliente(db, cliente.id)


@router.post("/loja/pedidos/{pedido_id}/receber")
def receber(pedido_id: int, dados: ReceberPedidoIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return _chamar(receber_pedido, db, pedido_id, dados.forma, usuario.id)

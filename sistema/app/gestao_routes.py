from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db
from .gestao import (
    admin_resumo,
    atualizar_servico,
    boletim,
    catalogo_loja,
    concluir_lembrete,
    criar_despesa,
    criar_funcionario,
    criar_lembrete,
    criar_orcamento,
    criar_produto,
    escrever_prontuario,
    estoque,
    importar_produtos,
    listar_orcamentos,
    marca,
    orcamento_xml,
    exigir_admin,
    extrair_payload_whatsapp,
    financeiro,
    lembretes,
    movimentar_estoque,
    prontuario,
    receber_whatsapp,
    salvar_contrato_funcionario,
    salvar_foto_produto,
    salvar_logo,
    salvar_marca,
    salvar_whatsapp,
    whatsapp_painel,
)
from .models import Usuario
from .plataforma import exigir_gestao
from .routes import _chamar, usuario_atual
from . import services

router = APIRouter(prefix="/api")


class NotaIn(BaseModel):
    pet_id: int
    texto: str


class LembreteIn(BaseModel):
    texto: str
    quando: datetime
    pet_id: int | None = None


class ProdutoIn(BaseModel):
    nome: str
    preco: float
    estoque: int = 0
    minimo: int = 0
    especie: str = ""


class PrecoIn(BaseModel):
    preco: float
    preco_feriado: float | None = None


class EstoqueIn(BaseModel):
    produto_id: int
    quantidade: int
    motivo: str = ""


class DespesaIn(BaseModel):
    descricao: str
    valor: float
    data: date
    categoria: str = "loja"


class FuncionarioIn(BaseModel):
    nome: str
    login: str
    senha: str
    papel: str = "equipe"
    cpf: str = ""
    salario: float = 0
    dia_vencimento: int = 5
    contrato: str = "indefinido"
    contrato_fim: date | None = None


class ContratoIn(BaseModel):
    cpf: str = ""
    salario: float = 0
    dia_vencimento: int = 5
    contrato: str = "indefinido"
    contrato_fim: date | None = None


class MarcaIn(BaseModel):
    nome: str
    slogan: str = ""
    whatsapp: str = ""
    tolerancia_busca_min: int = 15
    valor_atraso: float = 20
    cor: str = "#1f6b4a"


class ItemOrcamentoIn(BaseModel):
    descricao: str
    quantidade: int = 1
    valor: float = 0


class OrcamentoIn(BaseModel):
    cliente: str
    validade: date | None = None
    itens: list[ItemOrcamentoIn]


class WhatsappIn(BaseModel):
    numero: str = ""


class MensagemIn(BaseModel):
    texto: str
    telefone: str = ""


def _admin(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    _chamar(exigir_admin, usuario)
    return usuario


def _gestao_papel(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    _chamar(exigir_gestao, usuario)
    return usuario


@router.get("/boletins")
def ver_boletim(dia: date | None = None, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return boletim(db, dia or date.today())


@router.get("/prontuario")
def ver_prontuario(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return prontuario(db)


@router.post("/prontuario")
def nova_nota(dados: NotaIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return _chamar(escrever_prontuario, db, dados.pet_id, dados.texto, usuario.id)


@router.get("/lembretes")
def ver_lembretes(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return lembretes(db)


@router.post("/lembretes")
def novo_lembrete(dados: LembreteIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(criar_lembrete, db, dados.texto, dados.quando, dados.pet_id)


@router.post("/lembretes/{lembrete_id}/concluir")
def fechar_lembrete(lembrete_id: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(concluir_lembrete, db, lembrete_id)


@router.get("/loja/catalogo")
def ver_catalogo(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return catalogo_loja(db)


@router.post("/produtos")
def novo_produto(dados: ProdutoIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(criar_produto, db, dados.nome, dados.preco, dados.estoque, dados.minimo, dados.especie)


@router.post("/estoque/importar")
async def importar_estoque(arquivo: UploadFile = File(...), db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    conteudo = await arquivo.read()
    return _chamar(importar_produtos, db, arquivo.filename or "lista.csv", conteudo)


@router.get("/marca")
def ver_marca(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return marca(db)


@router.put("/marca")
def editar_marca(dados: MarcaIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(
        salvar_marca,
        db,
        dados.nome,
        dados.slogan,
        dados.whatsapp,
        dados.tolerancia_busca_min,
        dados.valor_atraso,
        dados.cor,
    )


@router.post("/marca/logo")
async def logo_loja(arquivo: UploadFile = File(...), db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    extensao = ".png"
    if arquivo.filename and "." in arquivo.filename:
        candidato = "." + arquivo.filename.rsplit(".", 1)[-1].lower()
        if candidato in {".jpg", ".jpeg", ".png", ".webp", ".svg"}:
            extensao = ".jpg" if candidato == ".jpeg" else candidato
    return _chamar(salvar_logo, db, await arquivo.read(), extensao)


@router.get("/orcamentos")
def ver_orcamentos(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return listar_orcamentos(db)


@router.post("/orcamentos")
def novo_orcamento(dados: OrcamentoIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(
        criar_orcamento,
        db,
        dados.cliente,
        dados.validade,
        [item.model_dump() for item in dados.itens],
    )


@router.get("/orcamentos/{orcamento_id}/xml")
def xml_orcamento(orcamento_id: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    xml = _chamar(orcamento_xml, db, orcamento_id)
    return PlainTextResponse(xml, media_type="application/xml")


@router.post("/produtos/{produto_id}/foto")
async def foto_produto(produto_id: int, arquivo: UploadFile = File(...), db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    extensao = ".jpg"
    if arquivo.filename and "." in arquivo.filename:
        candidato = "." + arquivo.filename.rsplit(".", 1)[-1].lower()
        if candidato in {".jpg", ".jpeg", ".png", ".webp"}:
            extensao = ".jpg" if candidato == ".jpeg" else candidato
    conteudo = await arquivo.read()
    return _chamar(salvar_foto_produto, db, produto_id, conteudo, extensao)


@router.patch("/servicos/{servico_id}")
def preco_servico(servico_id: int, dados: PrecoIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(atualizar_servico, db, servico_id, dados.preco, dados.preco_feriado)


@router.get("/estoque")
def ver_estoque(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return estoque(db)


@router.post("/estoque")
def mover_estoque(dados: EstoqueIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return _chamar(movimentar_estoque, db, dados.produto_id, dados.quantidade, dados.motivo, usuario.id)


@router.get("/financeiro")
def ver_financeiro(ano: int | None = None, mes: int | None = None, db: Session = Depends(get_db), _: Usuario = Depends(_gestao_papel)):
    hoje = date.today()
    return financeiro(db, ano or hoje.year, mes or hoje.month)


@router.post("/despesas")
def nova_despesa(dados: DespesaIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(criar_despesa, db, dados.descricao, dados.valor, dados.data, dados.categoria)


@router.get("/admin/resumo")
def resumo(db: Session = Depends(get_db), _: Usuario = Depends(_admin)):
    return admin_resumo(db)


@router.post("/admin/funcionarios")
def novo_funcionario(dados: FuncionarioIn, db: Session = Depends(get_db), _: Usuario = Depends(_admin)):
    return _chamar(
        criar_funcionario,
        db,
        dados.nome,
        dados.login,
        dados.senha,
        dados.papel,
        dados.cpf,
        dados.salario,
        dados.dia_vencimento,
        dados.contrato,
        dados.contrato_fim,
    )


@router.patch("/admin/funcionarios/{usuario_id}")
def contrato_funcionario(usuario_id: int, dados: ContratoIn, db: Session = Depends(get_db), _: Usuario = Depends(_admin)):
    return _chamar(
        salvar_contrato_funcionario,
        db,
        usuario_id,
        dados.cpf,
        dados.salario,
        dados.dia_vencimento,
        dados.contrato,
        dados.contrato_fim,
    )


@router.get("/whatsapp")
def ver_whatsapp(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return whatsapp_painel(db)


@router.put("/whatsapp")
def gravar_whatsapp(dados: WhatsappIn, db: Session = Depends(get_db), usuario: Usuario = Depends(_admin)):
    return _chamar(salvar_whatsapp, db, dados.numero)


@router.post("/whatsapp/mensagens")
def simular_mensagem(dados: MensagemIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(receber_whatsapp, db, dados.texto, dados.telefone)


@router.get("/whatsapp/webhook")
def verificar_webhook(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_verify_token: str = Query("", alias="hub.verify_token"),
    hub_challenge: str = Query("", alias="hub.challenge"),
    db: Session = Depends(get_db),
):
    cfg = services.config_loja(db)
    if hub_mode == "subscribe" and cfg.whatsapp_token and hub_verify_token == cfg.whatsapp_token:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail={"mensagem": "Token do webhook não confere."})


@router.post("/whatsapp/webhook")
async def webhook(request: Request, token: str = "", db: Session = Depends(get_db)):
    cfg = services.config_loja(db)
    corpo = await request.json()
    informado = token or str(corpo.get("token") or "")
    if not cfg.whatsapp_token or informado != cfg.whatsapp_token:
        raise HTTPException(status_code=403, detail={"mensagem": "Token do webhook não confere."})
    texto, telefone = extrair_payload_whatsapp(corpo)
    return _chamar(receber_whatsapp, db, texto, telefone)

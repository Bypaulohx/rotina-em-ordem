from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .database import get_db
from .models import ConfigLoja, Sessao, Usuario
from .rules import RegraNegocio
from .security import verificar_senha
from . import seed, services

router = APIRouter(prefix="/api")
COOKIE = "sessao"


class LoginIn(BaseModel):
    login: str
    senha: str


class CadastroIn(BaseModel):
    empresa: str
    slogan: str = ""
    whatsapp: str = ""
    tolerancia_busca_min: int = 15
    valor_atraso: float = 20
    responsavel: str
    login: str
    senha: str
    cor: str = "#1f6b4a"


class SalaoIn(BaseModel):
    pet_id: int
    servico_id: int
    inicio: datetime
    busca: datetime
    profissional_id: int | None = None
    baia_id: int | None = None
    valor_combinado: float | None = None
    titulo: str | None = None
    cuidados: str | None = None


class HotelIn(BaseModel):
    pet_id: int
    entrada: date
    checkout: date
    valor_diaria: float | None = None
    baia_id: int | None = None
    cuidados: str | None = None


class BuscaIn(BaseModel):
    forma: str = "pix"
    incluir_atraso: bool = True


class CheckoutIn(BaseModel):
    forma: str = "pix"
    checkout: date | None = None


class ClientePetIn(BaseModel):
    nome: str
    telefone: str = ""
    cep: str = ""
    logradouro: str = ""
    bairro: str = ""
    cidade: str = ""
    uf: str = ""
    numero: str = ""
    email: str = ""
    cpf: str = ""
    observacoes: str = ""
    pet_nome: str
    especie: str = "cão"
    porte: str
    alimentacao: str = ""
    cuidados: str = ""
    raca: str = ""
    sexo: str = ""
    nascimento: date | None = None
    alergias: str = ""
    doencas: str = ""
    medicamentos: str = ""
    comportamento: str = ""
    emergencia_nome: str = ""
    emergencia_telefone: str = ""


class PetIn(BaseModel):
    alimentacao: str | None = None
    cuidados: str | None = None


class CaixaIn(BaseModel):
    nome: str = ""
    saldo_inicial: float = 0


class FecharIn(BaseModel):
    saldo_informado: float


class VendaIn(BaseModel):
    cliente_id: int
    descricao: str
    valor: float
    forma: str


class PacoteIn(BaseModel):
    pet_id: int
    tipo: str
    quantidade: int = Field(ge=1)
    valor_total: float
    forma: str
    nome: str = ""
    validade: date | None = None


class EncaixeIn(BaseModel):
    pet_id: int
    servico_id: int
    dia: date


def usuario_atual(request: Request, db: Session = Depends(get_db)) -> Usuario:
    token = request.cookies.get(COOKIE)
    sessao = db.get(Sessao, token) if token else None
    if sessao is None or sessao.expira_em < datetime.now():
        raise HTTPException(status_code=401, detail={"mensagem": "Entre para continuar."})
    usuario = db.get(Usuario, sessao.usuario_id)
    if usuario is None:
        raise HTTPException(status_code=401, detail={"mensagem": "Entre para continuar."})
    return usuario


def _chamar(funcao, *args, **kwargs):
    try:
        return funcao(*args, **kwargs)
    except RegraNegocio as erro:
        raise HTTPException(status_code=erro.status, detail={"mensagem": erro.mensagem, **erro.extra}) from erro


def _sessao(usuario: Usuario, response: Response, db: Session) -> dict:
    token = secrets.token_urlsafe(32)
    db.add(Sessao(token=token, usuario_id=usuario.id, expira_em=datetime.now() + timedelta(days=7)))
    db.commit()
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7)
    loja = db.get(ConfigLoja, 1)
    return {
        "nome": usuario.nome,
        "login": usuario.login,
        "papel": usuario.papel or "admin",
        "loja": loja.nome if loja and loja.nome else "",
        "slogan": loja.slogan if loja and loja.slogan else "",
        "logo": loja.logo if loja and loja.logo else "",
        "cor": loja.cor if loja and loja.cor else "#1f6b4a",
    }


@router.get("/estado")
def estado(db: Session = Depends(get_db)):
    loja = db.get(ConfigLoja, 1)
    return {
        "pronta": db.query(Usuario).first() is not None,
        "loja": loja.nome if loja and loja.nome else "",
    }


@router.post("/cadastro")
def cadastro(dados: CadastroIn, response: Response, db: Session = Depends(get_db)):
    usuario = _chamar(
        seed.abrir_loja,
        db,
        dados.empresa,
        dados.slogan,
        dados.whatsapp,
        dados.tolerancia_busca_min,
        dados.valor_atraso,
        dados.responsavel,
        dados.login,
        dados.senha,
        dados.cor,
    )
    return _sessao(usuario, response, db)


@router.post("/login")
def login(dados: LoginIn, response: Response, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.login == dados.login.strip()).first()
    if usuario is None or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail={"mensagem": "Login ou senha não conferem."})
    return _sessao(usuario, response, db)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE)
    if token:
        sessao = db.get(Sessao, token)
        if sessao:
            db.delete(sessao)
            db.commit()
    response.delete_cookie(COOKIE)
    return {"ok": True}


@router.get("/me")
def me(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    from .models import ConfigLoja

    loja = db.get(ConfigLoja, 1)
    return {
        "nome": usuario.nome,
        "login": usuario.login,
        "papel": usuario.papel or "admin",
        "loja": loja.nome if loja and loja.nome else "",
        "slogan": loja.slogan if loja and loja.slogan else "",
        "logo": loja.logo if loja and loja.logo else "",
        "cor": loja.cor if loja and loja.cor else "#1f6b4a",
    }


@router.get("/painel")
def painel(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return services.painel(db, usuario)


@router.get("/mapa")
def mapa(dia: date | None = None, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return services.mapa(db, dia)


@router.get("/agenda")
def agenda(de: date, ate: date, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return services.agenda(db, de, ate)


@router.get("/catalogo")
def catalogo(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return services.catalogo(db)


@router.get("/pessoas")
def pessoas(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return services.pessoas(db)


@router.post("/clientes")
def criar_cliente(dados: ClientePetIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(services.criar_cliente_pet, db, dados.model_dump())


@router.patch("/pets/{pet_id}")
def atualizar_pet(pet_id: int, dados: PetIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(services.atualizar_pet, db, pet_id, dados.alimentacao, dados.cuidados)


@router.get("/cep/{cep}")
async def cep(cep: str, _: Usuario = Depends(usuario_atual)):
    digitos = "".join(ch for ch in cep if ch.isdigit())
    if len(digitos) != 8:
        raise HTTPException(status_code=400, detail={"mensagem": "CEP precisa ter 8 números."})
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resposta = await client.get(f"https://viacep.com.br/ws/{digitos}/json/")
            resposta.raise_for_status()
            corpo = resposta.json()
    except httpx.HTTPError as erro:
        raise HTTPException(status_code=502, detail={"mensagem": "Não foi possível consultar o CEP agora."}) from erro
    if corpo.get("erro"):
        raise HTTPException(status_code=404, detail={"mensagem": "CEP não encontrado."})
    return {
        "cep": digitos,
        "logradouro": corpo.get("logradouro", ""),
        "bairro": corpo.get("bairro", ""),
        "cidade": corpo.get("localidade", ""),
        "uf": corpo.get("uf", ""),
    }


@router.get("/feriados")
def feriados(ano: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return services.listar_feriados(db, ano)


@router.post("/simulacoes/salao")
def simular_salao(dados: SalaoIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(
        services.avaliar_salao,
        db,
        dados.pet_id,
        dados.servico_id,
        dados.inicio,
        dados.busca,
        dados.profissional_id,
        dados.baia_id,
        dados.valor_combinado,
    )


@router.post("/simulacoes/hotel")
def simular_hotel(dados: HotelIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(
        services.avaliar_hotel,
        db,
        dados.pet_id,
        dados.entrada,
        dados.checkout,
        dados.valor_diaria,
        dados.baia_id,
    )


@router.post("/agendamentos")
def criar_agendamento(dados: SalaoIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(services.criar_agendamento, db, dados.model_dump())


@router.post("/agendamentos/{agendamento_id}/chegou")
def chegou(agendamento_id: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(services.mudar_status, db, agendamento_id, "chegou")


@router.post("/agendamentos/{agendamento_id}/iniciar")
def iniciar(agendamento_id: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(services.mudar_status, db, agendamento_id, "em_atendimento")


@router.post("/agendamentos/{agendamento_id}/pronto")
def pronto(agendamento_id: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(services.mudar_status, db, agendamento_id, "pronto")


@router.post("/agendamentos/{agendamento_id}/buscar")
def buscar(agendamento_id: int, dados: BuscaIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return _chamar(services.receber_busca, db, agendamento_id, dados.forma, dados.incluir_atraso, usuario.id)


@router.post("/agendamentos/{agendamento_id}/cancelar")
def cancelar(agendamento_id: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(services.mudar_status, db, agendamento_id, "cancelado")


@router.post("/agendamentos/{agendamento_id}/faltou")
def faltou(agendamento_id: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(services.mudar_status, db, agendamento_id, "faltou")


@router.post("/hospedagens")
def criar_hospedagem(dados: HotelIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(services.criar_hospedagem, db, dados.model_dump())


@router.post("/hospedagens/{hospedagem_id}/checkout")
def checkout(hospedagem_id: int, dados: CheckoutIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return _chamar(services.checkout_hotel, db, hospedagem_id, dados.forma, dados.checkout, usuario.id)


@router.post("/encaixes")
def criar_encaixe(dados: EncaixeIn, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return _chamar(services.criar_encaixe, db, dados.pet_id, dados.servico_id, dados.dia)


@router.get("/vendas")
def vendas(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return services.listar_vendas(db)


@router.post("/vendas")
def nova_venda(dados: VendaIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return _chamar(services.venda_avulsa, db, dados.cliente_id, dados.descricao, dados.valor, dados.forma, usuario.id)


@router.post("/pacotes")
def pacote(dados: PacoteIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return _chamar(
        services.vender_pacote,
        db,
        dados.pet_id,
        dados.tipo,
        dados.quantidade,
        dados.valor_total,
        dados.forma,
        dados.nome,
        dados.validade,
        usuario.id,
    )


@router.get("/caixas")
def caixas(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return services.listar_caixas(db, usuario)


@router.post("/caixas")
def abrir_caixa(dados: CaixaIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return _chamar(services.abrir_caixa, db, usuario, dados.saldo_inicial)


@router.post("/caixas/{caixa_id}/fechar")
def fechar_caixa(caixa_id: int, dados: FecharIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return _chamar(services.fechar_caixa, db, caixa_id, dados.saldo_informado, usuario)


class MovimentoIn(BaseModel):
    tipo: str
    valor: float
    motivo: str = ""


class TransferirIn(BaseModel):
    usuario_id: int


@router.get("/caixas/operadores")
def operadores(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return services.operadores_caixa(db)


@router.post("/caixas/{caixa_id}/movimento")
def movimento(caixa_id: int, dados: MovimentoIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return _chamar(services.movimentar_caixa, db, caixa_id, usuario, dados.tipo, dados.valor, dados.motivo)


@router.post("/caixas/{caixa_id}/transferir")
def transferir(caixa_id: int, dados: TransferirIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_atual)):
    return _chamar(services.transferir_caixa, db, caixa_id, usuario, dados.usuario_id)

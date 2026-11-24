from __future__ import annotations

import re
import secrets
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .models import (
    Agendamento,
    Atividade,
    Cliente,
    Despesa,
    Hospedagem,
    Lembrete,
    MensagemWhatsapp,
    MovimentoEstoque,
    NotaProntuario,
    Pet,
    Produto,
    Profissional,
    Servico,
    Usuario,
    Venda,
)
from .rules import RegraNegocio
from .security import hash_senha
from . import services


def _iso(valor: datetime | date | None) -> str:
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%dT%H:%M")
    return valor.isoformat()


def papel_de(usuario: Usuario) -> str:
    return usuario.papel or "admin"


def exigir_admin(usuario: Usuario) -> None:
    if papel_de(usuario) != "admin":
        raise RegraNegocio("Só quem administra a loja vê essa área.", 403)


def boletim(db: Session, dia: date) -> dict:
    inicio = datetime(dia.year, dia.month, dia.day)
    fim = inicio + timedelta(days=1)
    atendimentos = []
    for ag in db.query(Agendamento).filter(Agendamento.inicio >= inicio, Agendamento.inicio < fim).order_by(Agendamento.inicio):
        item = services.agendamento_dict(db, ag)
        atendimentos.append(
            {
                "id": item["id"],
                "hora": item["inicio"][11:16],
                "pet": item["pet"],
                "servico": item["servico"],
                "baia": item["baia"],
                "profissional": item["profissional"],
                "status": item["status"],
                "busca": item["busca_prevista"][11:16],
            }
        )
    hotel = []
    for hosp in db.query(Hospedagem).filter(Hospedagem.status.in_(("hospedada", "reservada"))):
        if hosp.entrada <= dia < (hosp.checkout_real or hosp.checkout_previsto):
            pet = db.get(Pet, hosp.pet_id)
            cliente = db.get(Cliente, pet.cliente_id) if pet else None
            hotel.append(
                {
                    "pet": pet.nome if pet else "",
                    "cliente": cliente.nome if cliente else "",
                    "entrada": hosp.entrada.isoformat(),
                    "checkout": (hosp.checkout_real or hosp.checkout_previsto).isoformat(),
                    "status": hosp.status,
                }
            )
    lembretes = [
        {"id": item.id, "texto": item.texto, "quando": _iso(item.quando), "feito": item.feito}
        for item in db.query(Lembrete).filter(Lembrete.quando >= inicio, Lembrete.quando < fim).order_by(Lembrete.quando)
    ]
    baixo = [
        {"id": item.id, "nome": item.nome, "estoque": item.estoque, "minimo": item.minimo}
        for item in db.query(Produto).filter(Produto.ativo.is_(True), Produto.estoque <= Produto.minimo)
    ]
    prontos = sum(1 for item in atendimentos if item["status"] == "pronto")
    texto = (
        f"No dia {dia.strftime('%d/%m')}, a loja tem {len(atendimentos)} atendimento(s) de salão"
        f" e {len(hotel)} pet(s) no hotel."
    )
    if prontos:
        texto += f" {prontos} já estão prontos e ainda seguram a baia até a busca."
    if baixo:
        texto += " Estoque no limite: " + ", ".join(item["nome"] for item in baixo) + "."
    if not atendimentos and not hotel:
        texto += " A agenda deste dia ainda está vazia."
    return {
        "dia": dia.isoformat(),
        "texto": texto,
        "atendimentos": atendimentos,
        "hotel": hotel,
        "lembretes": lembretes,
        "estoque_baixo": baixo,
    }


def prontuario(db: Session) -> list[dict]:
    saida = []
    for pet in db.query(Pet).order_by(Pet.nome):
        cliente = db.get(Cliente, pet.cliente_id)
        notas = []
        for nota in db.query(NotaProntuario).filter(NotaProntuario.pet_id == pet.id).order_by(NotaProntuario.criado_em.desc()):
            autor = db.get(Usuario, nota.usuario_id) if nota.usuario_id else None
            notas.append(
                {
                    "id": nota.id,
                    "texto": nota.texto,
                    "quando": _iso(nota.criado_em),
                    "autor": autor.nome if autor else "Equipe",
                }
            )
        visitas = []
        for ag in db.query(Agendamento).filter(Agendamento.pet_id == pet.id).order_by(Agendamento.inicio.desc()).limit(8):
            item = services.agendamento_dict(db, ag)
            visitas.append(
                {
                    "id": item["id"],
                    "quando": item["inicio"],
                    "servico": item["servico"],
                    "status": item["status"],
                    "profissional": item["profissional"],
                }
            )
        saida.append(
            {
                "id": pet.id,
                "nome": pet.nome,
                "porte": pet.porte,
                "cliente": cliente.nome if cliente else "",
                "cuidados": pet.cuidados,
                "alimentacao": pet.alimentacao,
                "notas": notas,
                "visitas": visitas,
            }
        )
    return saida


def escrever_prontuario(db: Session, pet_id: int, texto: str, usuario_id: int | None) -> dict:
    services._pet(db, pet_id)
    limpo = texto.strip()
    if not limpo:
        raise RegraNegocio("Escreva o que foi observado neste pet.", 400)
    db.add(NotaProntuario(pet_id=pet_id, usuario_id=usuario_id, texto=limpo, criado_em=datetime.now()))
    db.commit()
    return {"ok": True}


def lembretes(db: Session) -> list[dict]:
    itens = db.query(Lembrete).order_by(Lembrete.feito, Lembrete.quando).all()
    saida = []
    for item in itens:
        pet = db.get(Pet, item.pet_id) if item.pet_id else None
        saida.append(
            {
                "id": item.id,
                "texto": item.texto,
                "quando": _iso(item.quando),
                "feito": item.feito,
                "pet": pet.nome if pet else "",
                "pet_id": item.pet_id,
            }
        )
    return saida


def criar_lembrete(db: Session, texto: str, quando: datetime, pet_id: int | None) -> dict:
    limpo = texto.strip()
    if not limpo:
        raise RegraNegocio("Escreva o lembrete.", 400)
    if pet_id:
        services._pet(db, pet_id)
    db.add(Lembrete(texto=limpo, quando=quando, pet_id=pet_id, feito=False))
    db.commit()
    return {"ok": True}


def concluir_lembrete(db: Session, lembrete_id: int) -> dict:
    item = db.get(Lembrete, lembrete_id)
    if item is None:
        raise RegraNegocio("Lembrete não encontrado.", 404)
    item.feito = True
    db.commit()
    return {"ok": True}


def catalogo_loja(db: Session) -> dict:
    base = services.catalogo(db)
    base["produtos"] = [
        {"id": item.id, "nome": item.nome, "preco": item.preco, "estoque": item.estoque, "minimo": item.minimo}
        for item in db.query(Produto).filter(Produto.ativo.is_(True)).order_by(Produto.nome)
    ]
    return base


def atualizar_servico(db: Session, servico_id: int, preco: float, preco_feriado: float | None) -> dict:
    servico = services._servico(db, servico_id)
    if preco < 0:
        raise RegraNegocio("O preço não pode ser negativo.", 400)
    servico.preco = preco
    if preco_feriado is not None:
        servico.preco_feriado = preco_feriado
    db.commit()
    return catalogo_loja(db)


def criar_produto(db: Session, nome: str, preco: float, estoque: int, minimo: int) -> dict:
    limpo = nome.strip()
    if not limpo:
        raise RegraNegocio("Dê um nome ao produto.", 400)
    if preco < 0 or estoque < 0 or minimo < 0:
        raise RegraNegocio("Preço, estoque e mínimo não podem ser negativos.", 400)
    db.add(Produto(nome=limpo, preco=preco, estoque=estoque, minimo=minimo, ativo=True))
    db.commit()
    return catalogo_loja(db)


def estoque(db: Session) -> list[dict]:
    saida = []
    for produto in db.query(Produto).filter(Produto.ativo.is_(True)).order_by(Produto.nome):
        movimentos = [
            {"quantidade": mov.quantidade, "motivo": mov.motivo, "quando": _iso(mov.criado_em)}
            for mov in db.query(MovimentoEstoque)
            .filter(MovimentoEstoque.produto_id == produto.id)
            .order_by(MovimentoEstoque.criado_em.desc())
            .limit(5)
        ]
        saida.append(
            {
                "id": produto.id,
                "nome": produto.nome,
                "preco": produto.preco,
                "estoque": produto.estoque,
                "minimo": produto.minimo,
                "baixo": produto.estoque <= produto.minimo,
                "movimentos": movimentos,
            }
        )
    return saida


def movimentar_estoque(db: Session, produto_id: int, quantidade: int, motivo: str, usuario_id: int | None) -> dict:
    produto = db.get(Produto, produto_id)
    if produto is None or not produto.ativo:
        raise RegraNegocio("Produto não encontrado.", 404)
    if quantidade == 0:
        raise RegraNegocio("Informe quantas unidades entraram ou saíram.", 400)
    if produto.estoque + quantidade < 0:
        raise RegraNegocio(f"{produto.nome} só tem {produto.estoque} no estoque.", 409)
    produto.estoque += quantidade
    db.add(
        MovimentoEstoque(
            produto_id=produto.id,
            quantidade=quantidade,
            motivo=motivo.strip() or ("Entrada" if quantidade > 0 else "Saída"),
            usuario_id=usuario_id,
        )
    )
    db.commit()
    return {"ok": True, "estoque": produto.estoque}


def financeiro(db: Session, ano: int, mes: int) -> dict:
    inicio = date(ano, mes, 1)
    fim = date(ano + 1, 1, 1) if mes == 12 else date(ano, mes + 1, 1)
    vendas = (
        db.query(Venda)
        .filter(Venda.criada_em >= datetime.combine(inicio, datetime.min.time()), Venda.criada_em < datetime.combine(fim, datetime.min.time()))
        .all()
    )
    por_forma: dict[str, float] = {}
    for venda in vendas:
        if venda.status != "paga":
            continue
        por_forma[venda.forma] = por_forma.get(venda.forma, 0) + venda.total
    despesas = [
        {
            "id": item.id,
            "descricao": item.descricao,
            "valor": item.valor,
            "data": item.data.isoformat(),
            "categoria": item.categoria,
            "status": item.status,
            "vencimento": item.vencimento.isoformat() if item.vencimento else None,
        }
        for item in db.query(Despesa).filter(Despesa.data >= inicio, Despesa.data < fim, Despesa.status != "aberta").order_by(Despesa.data.desc())
    ]
    recebido = round(sum(por_forma.values()), 2)
    gasto = round(sum(item["valor"] for item in despesas), 2)
    return {
        "ano": ano,
        "mes": mes,
        "recebido": recebido,
        "gasto": gasto,
        "resultado": round(recebido - gasto, 2),
        "por_forma": por_forma,
        "despesas": despesas,
        "dinheiro": round(por_forma.get("dinheiro", 0), 2),
    }


def criar_despesa(db: Session, descricao: str, valor: float, quando: date, categoria: str) -> dict:
    limpo = descricao.strip()
    if not limpo or valor <= 0:
        raise RegraNegocio("Informe a despesa e um valor maior que zero.", 400)
    db.add(Despesa(descricao=limpo, valor=valor, data=quando, categoria=categoria.strip() or "loja"))
    db.commit()
    return {"ok": True}


def admin_resumo(db: Session) -> dict:
    agora = datetime.now()
    inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    funcionarios = [
        {"id": usuario.id, "nome": usuario.nome, "login": usuario.login, "papel": papel_de(usuario)}
        for usuario in db.query(Usuario).order_by(Usuario.nome)
    ]
    atividades = []
    for item in db.query(Atividade).order_by(Atividade.criado_em.desc()).limit(40):
        autor = db.get(Usuario, item.usuario_id) if item.usuario_id else None
        atividades.append(
            {
                "id": item.id,
                "quando": _iso(item.criado_em),
                "acao": item.acao,
                "detalhe": item.detalhe,
                "usuario_id": item.usuario_id,
                "usuario": autor.nome if autor else "WhatsApp",
            }
        )
    por_profissional = []
    for prof in db.query(Profissional).filter(Profissional.ativo.is_(True)).order_by(Profissional.nome):
        itens = db.query(Agendamento).filter(Agendamento.profissional_id == prof.id, Agendamento.inicio >= inicio_mes).all()
        por_profissional.append(
            {
                "id": prof.id,
                "nome": prof.nome,
                "atendimentos": len(itens),
                "em_andamento": sum(1 for item in itens if item.status in {"chegou", "em_atendimento", "pronto"}),
                "concluidos": sum(1 for item in itens if item.status == "buscado"),
            }
        )
    vendas = db.query(Venda).filter(Venda.criada_em >= inicio_mes, Venda.status == "paga").all()
    return {
        "funcionarios": funcionarios,
        "atividades": atividades,
        "por_profissional": por_profissional,
        "vendas_mes": round(sum(item.total for item in vendas), 2),
        "agendamentos_mes": db.query(Agendamento).filter(Agendamento.inicio >= inicio_mes).count(),
        "pets": db.query(Pet).count(),
    }


def criar_funcionario(db: Session, nome: str, login: str, senha: str, papel: str) -> dict:
    limpo = nome.strip()
    usuario_login = login.strip().lower()
    if not limpo or not usuario_login:
        raise RegraNegocio("Informe o nome e o login.", 400)
    if len(senha) < 4:
        raise RegraNegocio("A senha precisa de pelo menos 4 caracteres.", 400)
    if papel not in {"admin", "gerente", "recepcao", "equipe", "veterinario", "tosador", "estoquista"}:
        raise RegraNegocio("Escolha um cargo da loja.", 400)
    if db.query(Usuario).filter(Usuario.login == usuario_login).first():
        raise RegraNegocio("Esse login já existe.", 409)
    db.add(Usuario(nome=limpo, login=usuario_login, senha_hash=hash_senha(senha), papel=papel))
    db.commit()
    return admin_resumo(db)


def extrair_inicio(texto: str, agora: datetime | None = None) -> datetime | None:
    agora = agora or datetime.now()
    hora = re.search(r"(\d{1,2})\s*(?::|h)\s*(\d{2})?", texto)
    if not hora:
        return None
    horas = int(hora.group(1))
    minutos = int(hora.group(2) or 0)
    if horas > 23 or minutos > 59:
        return None
    dia = agora.date() + timedelta(days=1) if "amanh" in texto else agora.date()
    data = re.search(r"(\d{1,2})/(\d{1,2})", texto)
    if data:
        try:
            dia = date(agora.year, int(data.group(2)), int(data.group(1)))
        except ValueError:
            return None
        if dia < agora.date():
            dia = date(agora.year + 1, dia.month, dia.day)
    return datetime(dia.year, dia.month, dia.day, horas, minutos)


def _datas_hotel(texto: str, agora: datetime) -> tuple[date, date] | None:
    encontradas = []
    for dia_texto, mes_texto in re.findall(r"(\d{1,2})/(\d{1,2})", texto):
        try:
            encontrada = date(agora.year, int(mes_texto), int(dia_texto))
        except ValueError:
            return None
        if encontrada < agora.date():
            encontrada = date(agora.year + 1, encontrada.month, encontrada.day)
        encontradas.append(encontrada)
    if len(encontradas) >= 2:
        return encontradas[0], encontradas[1]
    if len(encontradas) == 1:
        return encontradas[0], encontradas[0] + timedelta(days=2)
    entrada = agora.date() + timedelta(days=1)
    return entrada, entrada + timedelta(days=2)


def interpretar(db: Session, texto: str, agora: datetime | None = None) -> dict | None:
    cru = texto.lower()
    agora = agora or datetime.now()
    pet = None
    for candidato in sorted(db.query(Pet).all(), key=lambda item: len(item.nome), reverse=True):
        if re.search(rf"\b{re.escape(candidato.nome.lower())}\b", cru):
            pet = candidato
            break
    if pet is None:
        return None
    posicoes = []
    for tipo, chaves in (("hotel", ("hotel", "hosped")), ("tosa", ("tosa",)), ("banho", ("banho",))):
        for chave in chaves:
            indice = cru.find(chave)
            if indice >= 0:
                posicoes.append((indice, tipo))
    if not posicoes:
        return None
    tipo = min(posicoes)[1]
    servico = db.query(Servico).filter(Servico.tipo == tipo, Servico.porte == pet.porte).first()
    if servico is None:
        return None
    if tipo == "hotel":
        periodo = _datas_hotel(cru, agora)
        if periodo is None:
            return None
        return {"tipo": "hotel", "pet": pet, "servico": servico, "entrada": periodo[0], "checkout": periodo[1]}
    inicio = extrair_inicio(cru, agora)
    if inicio is None:
        return None
    return {
        "tipo": "salao",
        "pet": pet,
        "servico": servico,
        "inicio": inicio,
        "busca": inicio + timedelta(minutes=servico.duracao_min + 20),
    }


def _mensagem_dict(item: MensagemWhatsapp) -> dict:
    return {
        "id": item.id,
        "telefone": item.telefone,
        "texto": item.texto,
        "status": item.status,
        "detalhe": item.detalhe,
        "agendamento_id": item.agendamento_id,
        "quando": _iso(item.recebida_em),
    }


def receber_whatsapp(db: Session, texto: str, telefone: str) -> dict:
    limpo = texto.strip()
    mensagem = MensagemWhatsapp(telefone=telefone.strip(), texto=limpo, recebida_em=datetime.now())
    db.add(mensagem)
    if not limpo:
        mensagem.status = "pendente"
        mensagem.detalhe = "A mensagem chegou sem texto."
        db.commit()
        db.refresh(mensagem)
        return _mensagem_dict(mensagem)
    plano = interpretar(db, limpo)
    if plano is None:
        mensagem.status = "pendente"
        mensagem.detalhe = "Não deu para reconhecer o pet, o serviço e o horário. A equipe precisa ler a mensagem."
        db.commit()
        db.refresh(mensagem)
        return _mensagem_dict(mensagem)
    try:
        if plano["tipo"] == "hotel":
            criado = services.criar_hospedagem(
                db,
                {
                    "pet_id": plano["pet"].id,
                    "entrada": plano["entrada"],
                    "checkout": plano["checkout"],
                    "cuidados": plano["pet"].cuidados,
                },
            )
            mensagem.detalhe = f"Hospedagem de {plano['pet'].nome} reservada na {criado.get('baia', 'baia')}."
        else:
            criado = services.criar_agendamento(
                db,
                {
                    "pet_id": plano["pet"].id,
                    "servico_id": plano["servico"].id,
                    "inicio": plano["inicio"],
                    "busca": plano["busca"],
                    "titulo": f"{plano['servico'].nome} — {plano['pet'].nome}",
                    "cuidados": plano["pet"].cuidados,
                },
            )
            mensagem.agendamento_id = criado["id"]
            mensagem.detalhe = f"Agendamento criado: {criado['baia']} com {criado['profissional']}."
        mensagem.status = "criado"
    except RegraNegocio as erro:
        mensagem.status = "pendente"
        mensagem.detalhe = erro.mensagem
    if mensagem.status == "criado":
        db.add(Atividade(usuario_id=None, acao="O WhatsApp criou um agendamento", detalhe=mensagem.detalhe[:240]))
    db.commit()
    db.refresh(mensagem)
    return _mensagem_dict(mensagem)


def whatsapp_painel(db: Session) -> dict:
    cfg = services.config_loja(db)
    mensagens = [
        _mensagem_dict(item)
        for item in db.query(MensagemWhatsapp).order_by(MensagemWhatsapp.recebida_em.desc()).limit(30)
    ]
    return {"numero": cfg.whatsapp or "", "token": cfg.whatsapp_token or "", "mensagens": mensagens}


def salvar_whatsapp(db: Session, numero: str) -> dict:
    digitos = "".join(ch for ch in numero if ch.isdigit())
    if digitos and not 10 <= len(digitos) <= 13:
        raise RegraNegocio("Informe o WhatsApp com DDD. Exemplo: 11988887777.", 400)
    cfg = services.config_loja(db)
    cfg.whatsapp = digitos
    if digitos and not cfg.whatsapp_token:
        cfg.whatsapp_token = secrets.token_urlsafe(18)
    if not digitos:
        cfg.whatsapp_token = ""
    db.commit()
    return whatsapp_painel(db)


def extrair_payload_whatsapp(corpo: dict) -> tuple[str, str]:
    if isinstance(corpo.get("texto"), str):
        return corpo.get("texto", ""), str(corpo.get("telefone") or "")
    try:
        mensagem = corpo["entry"][0]["changes"][0]["value"]["messages"][0]
        return mensagem.get("text", {}).get("body", ""), str(mensagem.get("from") or "")
    except (KeyError, IndexError, TypeError, AttributeError):
        return "", ""

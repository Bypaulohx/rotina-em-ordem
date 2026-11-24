from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from .feriados import mapa_feriados
from .models import (
    Agendamento,
    Baia,
    Caixa,
    Cliente,
    ConfigLoja,
    Credito,
    Encaixe,
    Feriado,
    Hospedagem,
    ItemVenda,
    MovimentoCaixa,
    MovimentoCredito,
    Pagamento,
    Pet,
    Profissional,
    PacoteContratado,
    Servico,
    Venda,
)
from .rules import (
    STATUS_BAIA_SALA,
    STATUS_HOTEL,
    STATUS_PROFISSIONAL,
    RegraNegocio,
    aplicar_credito,
    calcular_atraso,
    classificar_intervalos,
    dinheiro_esperado,
    escolher_menor_baia,
    fim_ocupacao_hotel,
    fim_ocupacao_salao,
    fim_profissional,
    montar_diarias,
    montar_janela,
    porte_cabe,
)
from .validacao import cpf_valido, digitos, email_valido, telefone_valido

FORMAS = {"pix", "dinheiro", "debito", "credito"}
ROTULOS_FORMA = {
    "pix": "Pix",
    "dinheiro": "Dinheiro",
    "debito": "Débito",
    "credito": "Crédito",
    "pacote": "Pacote",
    "misto": "Misto",
}


def moeda(valor: float) -> str:
    texto = f"{valor:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def iso(valor: datetime | date | None) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.isoformat(timespec="minutes")
    return valor.isoformat()


def hora_curta(valor: datetime) -> str:
    if valor.year > 9000:
        return "a busca ser registrada"
    return valor.strftime("%H:%M")


def config_loja(db: Session) -> ConfigLoja:
    row = db.query(ConfigLoja).first()
    if row is None:
        row = ConfigLoja(tolerancia_busca_min=15, valor_atraso=20)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def caixa_aberto(db: Session, usuario_id: int | None = None) -> Caixa | None:
    consulta = db.query(Caixa).filter(Caixa.status == "aberto")
    if usuario_id is not None:
        consulta = consulta.filter(Caixa.usuario_id == usuario_id)
    return consulta.order_by(Caixa.aberto_em.desc()).first()


def exigir_caixa(db: Session, usuario_id: int) -> Caixa:
    if not usuario_id:
        raise RegraNegocio("Abra o seu caixa antes de receber. O caixa de outra pessoa não recebe a sua venda.", 400)
    caixa = caixa_aberto(db, usuario_id)
    if caixa is None:
        raise RegraNegocio("Abra o seu caixa antes de receber. O caixa de outra pessoa não recebe a sua venda.", 400)
    return caixa


def _servico(db: Session, servico_id: int) -> Servico:
    servico = db.get(Servico, servico_id)
    if servico is None:
        raise RegraNegocio("Serviço não encontrado.", 404)
    return servico


def _pet(db: Session, pet_id: int) -> Pet:
    pet = db.get(Pet, pet_id)
    if pet is None:
        raise RegraNegocio("Pet não encontrado.", 404)
    return pet


def saldo_credito(db: Session, pet_id: int, tipo: str) -> int:
    row = db.query(Credito).filter(Credito.pet_id == pet_id, Credito.tipo == tipo).first()
    return row.saldo if row else 0


def alterar_credito(db: Session, pet_id: int, tipo: str, quantidade: int, motivo: str) -> int:
    row = db.query(Credito).filter(Credito.pet_id == pet_id, Credito.tipo == tipo).first()
    if row is None:
        row = Credito(pet_id=pet_id, tipo=tipo, saldo=0)
        db.add(row)
    row.saldo += quantidade
    if row.saldo < 0:
        raise RegraNegocio("Não há crédito suficiente neste pet.", 400)
    db.add(MovimentoCredito(pet_id=pet_id, tipo=tipo, quantidade=quantidade, motivo=motivo))
    return row.saldo


def _baias(db: Session, tipo: str) -> list[Baia]:
    return db.query(Baia).filter(Baia.tipo == tipo, Baia.ativo.is_(True)).order_by(Baia.nome).all()


def _ocupacoes_salao(db: Session, agora: datetime, ignorar: int | None = None) -> list[dict]:
    consulta = db.query(Agendamento).filter(Agendamento.status.in_(STATUS_BAIA_SALA))
    ocupacoes = []
    for ag in consulta.all():
        if ag.id == ignorar:
            continue
        pet = db.get(Pet, ag.pet_id)
        ocupacoes.append(
            {
                "baia_id": ag.baia_id,
                "inicio": ag.inicio,
                "fim": fim_ocupacao_salao(ag.status, ag.busca_prevista, agora),
                "rotulo": pet.nome if pet else "Pet",
            }
        )
    for baia in db.query(Baia).filter(Baia.tipo == "salao", Baia.limpeza_desde.is_not(None)):
        ocupacoes.append(
            {
                "baia_id": baia.id,
                "inicio": baia.limpeza_desde,
                "fim": datetime.max.replace(microsecond=0),
                "rotulo": "limpeza",
            }
        )
    return ocupacoes


def _ocupacoes_profissional(db: Session, agora: datetime, ignorar: int | None = None) -> list[dict]:
    consulta = db.query(Agendamento).filter(Agendamento.status.in_(STATUS_PROFISSIONAL))
    ocupacoes = []
    for ag in consulta.all():
        if ag.id == ignorar or ag.profissional_id is None:
            continue
        pet = db.get(Pet, ag.pet_id)
        ocupacoes.append(
            {
                "profissional_id": ag.profissional_id,
                "inicio": ag.inicio,
                "fim": fim_profissional(ag.status, ag.fim_servico, agora),
                "rotulo": pet.nome if pet else "Pet",
            }
        )
    return ocupacoes


def _hospedagem_no_dia(db: Session, pet_id: int, dia: date) -> Hospedagem | None:
    hoje = date.today()
    for hosp in db.query(Hospedagem).filter(Hospedagem.pet_id == pet_id, Hospedagem.status.in_(STATUS_HOTEL)):
        fim = fim_ocupacao_hotel(hosp.status, hosp.checkout_previsto, hoje)
        if hosp.entrada <= dia < fim:
            return hosp
    return None


def _pet_no_salao(db: Session, pet_id: int, inicio: datetime, fim: datetime, agora: datetime) -> Agendamento | None:
    for ag in db.query(Agendamento).filter(Agendamento.pet_id == pet_id, Agendamento.status.in_(STATUS_BAIA_SALA)):
        if inicio < fim_ocupacao_salao(ag.status, ag.busca_prevista, agora) and ag.inicio < fim:
            return ag
    return None


def avaliar_salao(
    db: Session,
    pet_id: int,
    servico_id: int,
    inicio: datetime,
    busca: datetime,
    profissional_id: int | None = None,
    baia_id: int | None = None,
    valor_combinado: float | None = None,
    agora: datetime | None = None,
) -> dict:
    agora = agora or datetime.now()
    pet = _pet(db, pet_id)
    servico = _servico(db, servico_id)
    if servico.tipo == "hotel":
        raise RegraNegocio("Hospedagem entra com data de entrada e checkout.", 400)
    if servico.porte != pet.porte:
        raise RegraNegocio(
            f"O serviço é de porte {servico.porte} e {pet.nome} é porte {pet.porte}.",
            400,
        )
    try:
        janela = montar_janela(inicio, busca, servico.duracao_min)
    except RegraNegocio as erro:
        return {"ok": False, "mensagem": erro.mensagem, "pode_fila": False, "baias": []}

    hosp = _hospedagem_no_dia(db, pet.id, inicio.date())
    if hosp is not None:
        return {
            "ok": False,
            "pode_fila": False,
            "baias": [],
            "mensagem": (
                f"{pet.nome} está no hotel até {hosp.checkout_previsto.strftime('%d/%m')}. "
                "A baia do hotel continua ocupada."
            ),
        }
    if _pet_no_salao(db, pet.id, janela.inicio, janela.busca, agora):
        return {
            "ok": False,
            "pode_fila": False,
            "baias": [],
            "mensagem": f"{pet.nome} já tem horário nesse período.",
        }

    candidatas = escolher_menor_baia(
        [{"id": b.id, "nome": b.nome, "porte": b.porte} for b in _baias(db, "salao")],
        pet.porte,
    )
    livres, ocupadas = classificar_intervalos(
        candidatas,
        _ocupacoes_salao(db, agora),
        janela.inicio,
        janela.busca,
        "baia_id",
    )
    if baia_id is not None:
        livres = [b for b in livres if b["id"] == baia_id]

    profissionais = db.query(Profissional).filter(Profissional.ativo.is_(True)).order_by(Profissional.nome).all()
    if profissional_id is not None:
        profissionais = [p for p in profissionais if p.id == profissional_id]
        if not profissionais:
            raise RegraNegocio("Profissional não encontrado.", 404)
    livres_p, _ocupados_p = classificar_intervalos(
        [{"id": p.id, "nome": p.nome} for p in profissionais],
        _ocupacoes_profissional(db, agora),
        janela.inicio,
        janela.fim_servico,
        "profissional_id",
    )

    valor = round(servico.preco if valor_combinado is None else valor_combinado, 2)
    creditos = saldo_credito(db, pet.id, servico.tipo)
    uso = aplicar_credito(creditos, valor)
    baias_estado = [
        {"id": b["id"], "nome": b["nome"], "porte": b["porte"], "livre": True}
        for b in livres
    ] + [
        {
            "id": b["id"],
            "nome": b["nome"],
            "porte": b["porte"],
            "livre": False,
            "ocupante": b["ocupante"],
            "ate": iso(b["ate"]),
        }
        for b in ocupadas
    ]

    if not livres and not livres_p:
        mensagem = "Não há baia nem profissional livres nesse intervalo."
        ok = False
    elif not livres:
        if ocupadas:
            ref = ocupadas[0]
            mensagem = (
                f"Não há baia livre para o porte {pet.porte} entre {inicio.strftime('%H:%M')} e {busca.strftime('%H:%M')}. "
                f"A {ref['nome']} segue com {ref['ocupante']} até {hora_curta(ref['ate'])}."
            )
        else:
            mensagem = "A baia escolhida não cabe nesse horário."
        ok = False
    elif not livres_p:
        mensagem = (
            f"Tem baia livre, mas nenhum profissional está livre das {inicio.strftime('%H:%M')} "
            f"às {janela.fim_servico.strftime('%H:%M')}."
        )
        ok = False
    else:
        ok = True
        baia = livres[0]
        prof = livres_p[0]
        if uso["usou"]:
            mensagem = (
                f"Cabe na {baia['nome']} com {prof['nome']}. "
                f"Este atendimento sai do pacote: restam {creditos}."
            )
        else:
            mensagem = f"Cabe na {baia['nome']} com {prof['nome']}. Valor combinado de R$ {moeda(valor)}."

    return {
        "ok": ok,
        "mensagem": mensagem,
        "pode_fila": not ok,
        "baia": {"id": livres[0]["id"], "nome": livres[0]["nome"], "porte": livres[0]["porte"]} if ok else None,
        "profissional": {"id": livres_p[0]["id"], "nome": livres_p[0]["nome"]} if ok else None,
        "valor": valor,
        "valor_a_receber": uso["valor"] if ok else valor,
        "creditos": creditos,
        "usa_pacote": bool(ok and uso["usou"]),
        "fim_servico": iso(janela.fim_servico),
        "cuidados": " ".join(parte for parte in [pet.alimentacao, pet.cuidados] if parte),
        "baias": baias_estado,
        "servico": servico.nome,
        "pet": pet.nome,
    }


def criar_agendamento(db: Session, dados: dict) -> dict:
    avaliacao = avaliar_salao(
        db,
        dados["pet_id"],
        dados["servico_id"],
        dados["inicio"],
        dados["busca"],
        dados.get("profissional_id"),
        dados.get("baia_id"),
        dados.get("valor_combinado"),
    )
    if not avaliacao["ok"]:
        raise RegraNegocio(avaliacao["mensagem"], 409, extra={"baias": avaliacao.get("baias", [])})
    pet = _pet(db, dados["pet_id"])
    servico = _servico(db, dados["servico_id"])
    janela = montar_janela(dados["inicio"], dados["busca"], servico.duracao_min)
    cuidados = dados.get("cuidados")
    if not cuidados:
        cuidados = avaliacao["cuidados"]
    titulo = dados.get("titulo") or f"{servico.nome} — {pet.nome}"
    ag = Agendamento(
        titulo=titulo,
        pet_id=pet.id,
        servico_id=servico.id,
        profissional_id=avaliacao["profissional"]["id"],
        baia_id=avaliacao["baia"]["id"],
        inicio=janela.inicio,
        fim_servico=janela.fim_servico,
        busca_prevista=janela.busca,
        status="agendado",
        valor_combinado=avaliacao["valor"],
        cuidados=cuidados,
    )
    db.add(ag)
    espera = (
        db.query(Encaixe)
        .filter(Encaixe.pet_id == pet.id, Encaixe.dia == janela.inicio.date(), Encaixe.status == "aguardando")
        .all()
    )
    for item in espera:
        item.status = "atendido"
    db.commit()
    db.refresh(ag)
    return agendamento_dict(db, ag)


def _agendamento_ativo(db: Session, agendamento_id: int) -> Agendamento:
    ag = db.get(Agendamento, agendamento_id)
    if ag is None:
        raise RegraNegocio("Agendamento não encontrado.", 404)
    return ag


def mudar_status(db: Session, agendamento_id: int, destino: str) -> dict:
    ag = _agendamento_ativo(db, agendamento_id)
    permitidos = {
        "agendado": {"chegou", "cancelado", "faltou"},
        "chegou": {"em_atendimento", "cancelado"},
        "em_atendimento": {"pronto", "cancelado"},
    }
    if destino not in permitidos.get(ag.status, set()):
        raise RegraNegocio("Esse atendimento não pode ir para esse estado agora.", 400)
    ag.status = destino
    sugestao = None
    if destino in {"cancelado", "faltou"}:
        sugestao = _sugestao_encaixe(db, ag)
    db.commit()
    payload = agendamento_dict(db, ag)
    payload["sugestao"] = sugestao
    return payload


def receber_busca(db: Session, agendamento_id: int, forma: str, incluir_atraso: bool, usuario_id: int) -> dict:
    ag = _agendamento_ativo(db, agendamento_id)
    if ag.status != "pronto":
        raise RegraNegocio("A busca só entra no caixa quando o pet está pronto.", 400)
    agora = datetime.now()
    cfg = config_loja(db)
    atraso = calcular_atraso(ag.busca_prevista, agora, cfg.tolerancia_busca_min, cfg.valor_atraso)
    pet = _pet(db, ag.pet_id)
    servico = _servico(db, ag.servico_id)
    creditos = saldo_credito(db, pet.id, servico.tipo)
    uso = aplicar_credito(creditos, ag.valor_combinado)
    itens: list[tuple[str, float]] = []
    if uso["usou"]:
        itens.append((f"{ag.titulo} (pacote)", 0.0))
    else:
        itens.append((ag.titulo, round(ag.valor_combinado, 2)))
    if atraso["atrasou"] and incluir_atraso:
        itens.append((f"Atraso na busca ({atraso['minutos']} min)", atraso["valor"]))
    venda = gravar_venda(db, pet.cliente_id, forma, itens, usuario_id)
    if uso["usou"]:
        alterar_credito(db, pet.id, servico.tipo, -1, f"Baixa na busca, venda {venda.numero:05d}")
        _baixar_sessao(db, pet.id, servico.tipo)
        ag.usou_credito = True
    ag.status = "buscado"
    ag.venda_id = venda.id
    _marcar_limpeza(db, ag.baia_id)
    db.commit()
    return {"agendamento": agendamento_dict(db, ag), "venda": venda_dict(db, venda), "atraso": atraso}


def avaliar_hotel(
    db: Session,
    pet_id: int,
    entrada: date,
    checkout: date,
    valor_diaria: float | None = None,
    baia_id: int | None = None,
) -> dict:
    if checkout <= entrada:
        return {"ok": False, "mensagem": "O checkout precisa ser pelo menos no dia seguinte.", "pode_fila": False}
    pet = _pet(db, pet_id)
    servico = (
        db.query(Servico).filter(Servico.tipo == "hotel", Servico.porte == pet.porte).first()
    )
    if servico is None:
        raise RegraNegocio("Não há diária cadastrada para esse porte.", 400)
    base = round(servico.preco if valor_diaria is None else valor_diaria, 2)
    if valor_diaria is None:
        feriado_valor = servico.preco_feriado or round(base * 1.5, 2)
    else:
        fator = (servico.preco_feriado / servico.preco) if servico.preco else 1.5
        feriado_valor = round(base * fator, 2)

    hoje = date.today()
    for hosp in db.query(Hospedagem).filter(Hospedagem.pet_id == pet.id, Hospedagem.status.in_(STATUS_HOTEL)):
        fim = fim_ocupacao_hotel(hosp.status, hosp.checkout_previsto, hoje)
        if entrada < fim and hosp.entrada < checkout:
            return {
                "ok": False,
                "pode_fila": False,
                "mensagem": f"{pet.nome} já está no hotel até {fim.strftime('%d/%m')}.",
            }
    for ag in db.query(Agendamento).filter(Agendamento.pet_id == pet.id, Agendamento.status.in_(STATUS_BAIA_SALA)):
        if entrada <= ag.inicio.date() < checkout:
            return {
                "ok": False,
                "pode_fila": False,
                "mensagem": f"{pet.nome} já tem atendimento de salão em {ag.inicio.strftime('%d/%m')}.",
            }

    feriados = mapa_feriados(db)
    linhas = montar_diarias(entrada, checkout, base, feriado_valor, feriados)
    candidatas = escolher_menor_baia(
        [{"id": b.id, "nome": b.nome, "porte": b.porte} for b in _baias(db, "hotel")],
        pet.porte,
    )
    livres = []
    ocupadas = []
    for baia in candidatas:
        choque = _choque_hotel(db, baia["id"], entrada, checkout, hoje)
        if choque is None:
            livres.append(baia)
        else:
            ocupadas.append({**baia, "ocupante": choque})
    if baia_id is not None:
        livres = [b for b in livres if b["id"] == baia_id]

    diarias = [
        {"data": iso(linha["data"]), "valor": linha["valor"], "feriado": linha["feriado"]}
        for linha in linhas
    ]
    total = round(sum(linha["valor"] for linha in linhas), 2)
    feriados_na_estadia = [linha for linha in linhas if linha["feriado"]]
    if not livres:
        ref = ocupadas[0]["ocupante"] if ocupadas else "outra hospedagem"
        return {
            "ok": False,
            "pode_fila": True,
            "mensagem": f"Não há baia de hotel livre para o porte {pet.porte}. A vaga segue com {ref}.",
            "diarias": diarias,
            "total": total,
        }
    baia = livres[0]
    if feriados_na_estadia:
        nomes = ", ".join(f"{item['data'].strftime('%d/%m')} ({item['feriado']})" for item in feriados_na_estadia)
        mensagem = (
            f"A {baia['nome']} está livre. {len(linhas)} diárias, com feriado em {nomes}. "
            f"Total de R$ {moeda(total)}."
        )
    else:
        mensagem = f"A {baia['nome']} está livre. {len(linhas)} diárias, sem feriado no período. Total de R$ {moeda(total)}."
    return {
        "ok": True,
        "mensagem": mensagem,
        "pode_fila": False,
        "baia": baia,
        "valor_diaria": base,
        "valor_feriado": feriado_valor,
        "diarias": diarias,
        "total": total,
        "cuidados": " ".join(parte for parte in [pet.alimentacao, pet.cuidados] if parte),
    }


def _choque_hotel(db: Session, baia_id: int, entrada: date, checkout: date, hoje: date) -> str | None:
    for hosp in db.query(Hospedagem).filter(Hospedagem.baia_id == baia_id, Hospedagem.status.in_(STATUS_HOTEL)):
        fim = fim_ocupacao_hotel(hosp.status, hosp.checkout_previsto, hoje)
        if entrada < fim and hosp.entrada < checkout:
            pet = db.get(Pet, hosp.pet_id)
            return pet.nome if pet else "um pet"
    baia = db.get(Baia, baia_id)
    if baia is not None and baia.limpeza_desde is not None:
        return "a limpeza"
    return None


def criar_hospedagem(db: Session, dados: dict) -> dict:
    avaliacao = avaliar_hotel(
        db,
        dados["pet_id"],
        dados["entrada"],
        dados["checkout"],
        dados.get("valor_diaria"),
        dados.get("baia_id"),
    )
    if not avaliacao["ok"]:
        raise RegraNegocio(avaliacao["mensagem"], 409)
    hoje = date.today()
    status = "hospedada" if dados["entrada"] <= hoje else "reservada"
    hosp = Hospedagem(
        pet_id=dados["pet_id"],
        baia_id=avaliacao["baia"]["id"],
        entrada=dados["entrada"],
        checkout_previsto=dados["checkout"],
        valor_diaria=avaliacao["valor_diaria"],
        valor_feriado=avaliacao["valor_feriado"],
        status=status,
        cuidados=dados.get("cuidados") or avaliacao["cuidados"],
    )
    db.add(hosp)
    db.commit()
    db.refresh(hosp)
    return hospedagem_dict(db, hosp)


def checkout_hotel(db: Session, hospedagem_id: int, forma: str, quando: date | None, usuario_id: int) -> dict:
    hosp = db.get(Hospedagem, hospedagem_id)
    if hosp is None:
        raise RegraNegocio("Hospedagem não encontrada.", 404)
    if hosp.status not in STATUS_HOTEL:
        raise RegraNegocio("Essa hospedagem já foi encerrada.", 400)
    quando = quando or date.today()
    if quando <= hosp.entrada:
        raise RegraNegocio("O checkout precisa ser depois da entrada.", 400)
    pet = _pet(db, hosp.pet_id)
    linhas = montar_diarias(hosp.entrada, quando, hosp.valor_diaria, hosp.valor_feriado, mapa_feriados(db))
    if not linhas:
        raise RegraNegocio("Não há diária para cobrar nesse período.", 400)
    itens = []
    for linha in linhas:
        descricao = f"Diária {linha['data'].strftime('%d/%m')} — {pet.nome}"
        if linha["feriado"]:
            descricao += f" ({linha['feriado']})"
        itens.append((descricao, linha["valor"]))
    venda = gravar_venda(db, pet.cliente_id, forma, itens, usuario_id)
    hosp.checkout_real = quando
    hosp.status = "finalizada"
    hosp.venda_id = venda.id
    _marcar_limpeza(db, hosp.baia_id)
    db.commit()
    return {
        "hospedagem": hospedagem_dict(db, hosp),
        "venda": venda_dict(db, venda),
        "checkout_atrasado": quando > hosp.checkout_previsto,
    }


def criar_encaixe(db: Session, pet_id: int, servico_id: int, dia: date) -> dict:
    pet = _pet(db, pet_id)
    servico = _servico(db, servico_id)
    if servico.tipo == "hotel":
        raise RegraNegocio("A fila de encaixe é do salão.", 400)
    if servico.porte != pet.porte:
        raise RegraNegocio("O serviço da fila precisa ser do porte do pet.", 400)
    item = Encaixe(pet_id=pet.id, servico_id=servico.id, dia=dia, status="aguardando")
    db.add(item)
    db.commit()
    db.refresh(item)
    return encaixe_dict(db, item)


def _sugestao_encaixe(db: Session, ag: Agendamento) -> dict | None:
    baia = db.get(Baia, ag.baia_id)
    if baia is None:
        return None
    dia = ag.inicio.date()
    fila = (
        db.query(Encaixe)
        .filter(Encaixe.dia == dia, Encaixe.status == "aguardando")
        .order_by(Encaixe.id)
        .all()
    )
    for item in fila:
        pet = db.get(Pet, item.pet_id)
        servico = db.get(Servico, item.servico_id)
        if pet and servico and porte_cabe(baia.porte, pet.porte) and servico.porte == pet.porte:
            return {
                "encaixe_id": item.id,
                "pet_id": pet.id,
                "pet": pet.nome,
                "porte": pet.porte,
                "servico_id": servico.id,
                "servico": servico.nome,
                "baia_id": baia.id,
                "baia": baia.nome,
                "profissional_id": ag.profissional_id,
                "janela_inicio": iso(ag.inicio),
                "janela_fim": iso(ag.busca_prevista),
            }
    return None


def gravar_venda(db: Session, cliente_id: int, forma: str, itens: list[tuple[str, float]], usuario_id: int) -> Venda:
    if not itens:
        raise RegraNegocio("A venda precisa de pelo menos um item.", 400)
    caixa = exigir_caixa(db, usuario_id)
    total = round(sum(valor for _, valor in itens), 2)
    forma_final = "pacote" if total == 0 else forma
    if forma_final not in FORMAS and forma_final != "pacote":
        raise RegraNegocio("Forma de pagamento desconhecida.", 400)
    numero = (db.query(func.max(Venda.numero)).scalar() or 0) + 1
    venda = Venda(
        numero=numero,
        cliente_id=cliente_id,
        caixa_id=caixa.id,
        status="paga",
        forma=forma_final,
        total=total,
    )
    db.add(venda)
    db.flush()
    for descricao, valor in itens:
        db.add(ItemVenda(venda_id=venda.id, descricao=descricao, valor=round(valor, 2)))
    return venda


def vender_pacote(
    db: Session,
    pet_id: int,
    tipo: str,
    quantidade: int,
    valor_total: float,
    forma: str,
    nome: str = "",
    validade: date | None = None,
    usuario_id: int | None = None,
) -> dict:
    if tipo not in {"banho", "tosa"}:
        raise RegraNegocio("Pacote vale para banho ou tosa.", 400)
    if quantidade < 1:
        raise RegraNegocio("O pacote precisa ter pelo menos um atendimento.", 400)
    if valor_total <= 0:
        raise RegraNegocio("Informe o valor cobrado pelo pacote.", 400)
    pet = _pet(db, pet_id)
    titulo = (nome or f"{'Banho' if tipo == 'banho' else 'Tosa'} — {quantidade} sessões").strip()
    if titulo.lower() == pet.nome.strip().lower():
        raise RegraNegocio("O nome do pacote é comercial. Não use o nome do animal.", 400)
    venda = gravar_venda(db, pet.cliente_id, forma, [(f"{titulo} ({quantidade} sessões)", round(valor_total, 2))], usuario_id)
    saldo = alterar_credito(db, pet.id, tipo, quantidade, f"Pacote {titulo}, venda {venda.numero:05d}")
    db.add(
        PacoteContratado(
            pet_id=pet.id,
            nome=titulo,
            tipo=tipo,
            total=quantidade,
            saldo=quantidade,
            valor=round(valor_total, 2),
            validade=validade,
            venda_id=venda.id,
        )
    )
    db.commit()
    payload = venda_dict(db, venda)
    payload["saldo"] = saldo
    payload["pacote"] = titulo
    return payload


def venda_avulsa(db: Session, cliente_id: int, descricao: str, valor: float, forma: str, usuario_id: int) -> dict:
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise RegraNegocio("Cliente não encontrado.", 404)
    if not descricao.strip():
        raise RegraNegocio("Descreva o que foi vendido.", 400)
    if valor <= 0:
        raise RegraNegocio("Informe o valor da venda.", 400)
    venda = gravar_venda(db, cliente.id, forma, [(descricao.strip(), round(valor, 2))], usuario_id)
    db.commit()
    return venda_dict(db, venda)


def abrir_caixa(db: Session, usuario, saldo_inicial: float) -> dict:
    if caixa_aberto(db, usuario.id):
        raise RegraNegocio("Você já tem um caixa aberto. Feche o seu antes de abrir outro.", 400)
    if saldo_inicial < 0:
        raise RegraNegocio("O dinheiro inicial não pode ser negativo.", 400)
    caixa = Caixa(
        nome=f"Caixa de {usuario.nome}",
        saldo_inicial=round(saldo_inicial, 2),
        status="aberto",
        usuario_id=usuario.id,
    )
    db.add(caixa)
    db.commit()
    db.refresh(caixa)
    return caixa_dict(db, caixa)


def fechar_caixa(db: Session, caixa_id: int, saldo_informado: float, usuario) -> dict:
    caixa = db.get(Caixa, caixa_id)
    if caixa is None:
        raise RegraNegocio("Caixa não encontrado.", 404)
    if caixa.status != "aberto":
        raise RegraNegocio("Esse caixa já foi fechado.", 400)
    if caixa.usuario_id != usuario.id:
        raise RegraNegocio("Só quem abriu este caixa pode fechá-lo.", 403)
    if saldo_informado < 0:
        raise RegraNegocio("O valor contado não pode ser negativo.", 400)
    caixa.saldo_informado = round(saldo_informado, 2)
    caixa.fechado_em = datetime.now()
    caixa.fechado_por_id = usuario.id
    caixa.status = "fechado"
    db.commit()
    return caixa_dict(db, caixa)


def _caixa_proprio(db: Session, caixa_id: int, usuario) -> Caixa:
    caixa = db.get(Caixa, caixa_id)
    if caixa is None:
        raise RegraNegocio("Caixa não encontrado.", 404)
    if caixa.usuario_id != usuario.id:
        raise RegraNegocio("Só quem abriu este caixa pode movimentá-lo.", 403)
    if caixa.status != "aberto":
        raise RegraNegocio("Esse caixa já foi fechado.", 400)
    return caixa


def movimentar_caixa(db: Session, caixa_id: int, usuario, tipo: str, valor: float, motivo: str) -> dict:
    caixa = _caixa_proprio(db, caixa_id, usuario)
    if tipo not in {"sangria", "suprimento"}:
        raise RegraNegocio("O movimento é sangria ou suprimento.", 400)
    if valor <= 0:
        raise RegraNegocio("Informe um valor maior que zero.", 400)
    if tipo == "sangria":
        formas = resumo_formas(db, caixa.id)
        disponivel = round(dinheiro_esperado(caixa.saldo_inicial, formas) + ajuste_gaveta(db, caixa.id), 2)
        if valor > disponivel + 0.001:
            raise RegraNegocio("A sangria não pode passar do dinheiro que deveria estar na gaveta.", 400)
    db.add(MovimentoCaixa(caixa_id=caixa.id, tipo=tipo, valor=round(valor, 2), motivo=motivo.strip(), usuario_id=usuario.id))
    db.commit()
    return caixa_dict(db, caixa)


def transferir_caixa(db: Session, caixa_id: int, usuario, destino_id: int) -> dict:
    from .models import Usuario

    caixa = _caixa_proprio(db, caixa_id, usuario)
    destino = db.get(Usuario, destino_id)
    if destino is None:
        raise RegraNegocio("Operador não encontrado.", 404)
    if destino.id == usuario.id:
        raise RegraNegocio("Este caixa já está no seu nome.", 400)
    if caixa_aberto(db, destino.id):
        raise RegraNegocio("Essa pessoa já tem um caixa aberto.", 400)
    db.add(
        MovimentoCaixa(
            caixa_id=caixa.id,
            tipo="transferencia",
            valor=0,
            motivo=f"De {usuario.nome} para {destino.nome}",
            usuario_id=usuario.id,
        )
    )
    caixa.usuario_id = destino.id
    caixa.nome = f"Caixa de {destino.nome}"
    db.commit()
    return caixa_dict(db, caixa)


def operadores_caixa(db: Session) -> list[dict]:
    from .models import Usuario

    return [
        {"id": pessoa.id, "nome": pessoa.nome}
        for pessoa in db.query(Usuario).order_by(Usuario.nome)
        if (pessoa.papel or "admin") in {"admin", "recepcao", "equipe"}
    ]


def _marcar_limpeza(db: Session, baia_id: int) -> None:
    baia = db.get(Baia, baia_id)
    if baia is not None:
        baia.limpeza_desde = datetime.now()


def limpar_baia(db: Session, baia_id: int) -> dict:
    baia = db.get(Baia, baia_id)
    if baia is None:
        raise RegraNegocio("Baia não encontrada.", 404)
    if baia.limpeza_desde is None:
        raise RegraNegocio("Essa baia não está aguardando limpeza.", 400)
    baia.limpeza_desde = None
    db.commit()
    return {"ok": True, "nome": baia.nome}


def _baixar_sessao(db: Session, pet_id: int, tipo: str) -> None:
    pacote = (
        db.query(PacoteContratado)
        .filter(PacoteContratado.pet_id == pet_id, PacoteContratado.tipo == tipo, PacoteContratado.saldo > 0)
        .order_by(PacoteContratado.id)
        .first()
    )
    if pacote is not None:
        pacote.saldo -= 1


def resumo_formas(db: Session, caixa_id: int) -> dict[str, float]:
    totais: dict[str, float] = {}
    vendas = db.query(Venda).filter(Venda.caixa_id == caixa_id, Venda.status == "paga").all()
    for venda in vendas:
        partes = db.query(Pagamento).filter(Pagamento.venda_id == venda.id).all()
        if partes:
            for parte in partes:
                totais[parte.forma] = round(totais.get(parte.forma, 0) + parte.valor, 2)
        else:
            totais[venda.forma] = round(totais.get(venda.forma, 0) + venda.total, 2)
    return totais


def ajuste_gaveta(db: Session, caixa_id: int) -> float:
    soma = 0.0
    for mov in db.query(MovimentoCaixa).filter(MovimentoCaixa.caixa_id == caixa_id):
        if mov.tipo == "suprimento":
            soma += mov.valor
        elif mov.tipo == "sangria":
            soma -= mov.valor
    return round(soma, 2)


def _telefone_livre(db: Session, telefone: str, ignorar: int | None = None) -> None:
    for cliente in db.query(Cliente).all():
        if cliente.id == ignorar:
            continue
        if digitos(cliente.telefone) == telefone:
            raise RegraNegocio(f"Já existe cliente com esse telefone: {cliente.nome}.", 409)


def criar_cliente_pet(db: Session, dados: dict) -> dict:
    if dados["porte"] not in {"P", "M", "G"}:
        raise RegraNegocio("O porte precisa ser P, M ou G.", 400)
    if not dados["nome"].strip() or not dados["pet_nome"].strip():
        raise RegraNegocio("Informe o cliente e o pet.", 400)
    telefone = digitos(dados.get("telefone", ""))
    if not telefone_valido(telefone):
        raise RegraNegocio("Informe o telefone com DDD. Celular tem 11 números e fixo tem 10.", 400)
    cep = digitos(dados.get("cep", ""))
    if len(cep) != 8 or not dados.get("logradouro", "").strip() or not dados.get("cidade", "").strip():
        raise RegraNegocio("CEP e endereço são obrigatórios. O CEP preenche a rua e a cidade.", 400)
    email = dados.get("email", "").strip()
    if email and not email_valido(email):
        raise RegraNegocio("O e-mail informado não é válido.", 400)
    cpf = digitos(dados.get("cpf", ""))
    if cpf and not cpf_valido(cpf):
        raise RegraNegocio("O CPF informado não confere.", 400)
    _telefone_livre(db, telefone)
    cliente = Cliente(
        nome=dados["nome"].strip(),
        telefone=telefone,
        cep=cep,
        logradouro=dados.get("logradouro", "").strip(),
        bairro=dados.get("bairro", "").strip(),
        cidade=dados.get("cidade", "").strip(),
        uf=dados.get("uf", "").strip().upper()[:2],
        numero=dados.get("numero", "").strip(),
        email=email,
        cpf=cpf,
        observacoes=dados.get("observacoes", "").strip(),
    )
    db.add(cliente)
    db.flush()
    pet = Pet(
        cliente_id=cliente.id,
        nome=dados["pet_nome"].strip(),
        especie=dados.get("especie") or "cão",
        porte=dados["porte"],
        alimentacao=dados.get("alimentacao", "").strip(),
        cuidados=dados.get("cuidados", "").strip(),
        raca=dados.get("raca", "").strip(),
        sexo=dados.get("sexo", "").strip(),
        nascimento=dados.get("nascimento"),
        alergias=dados.get("alergias", "").strip(),
        doencas=dados.get("doencas", "").strip(),
        medicamentos=dados.get("medicamentos", "").strip(),
        comportamento=dados.get("comportamento", "").strip(),
        emergencia_nome=dados.get("emergencia_nome", "").strip(),
        emergencia_telefone=digitos(dados.get("emergencia_telefone", "")),
    )
    db.add(pet)
    db.commit()
    return pessoas(db)


def atualizar_pet(db: Session, pet_id: int, alimentacao: str | None, cuidados: str | None) -> dict:
    pet = _pet(db, pet_id)
    if alimentacao is not None:
        pet.alimentacao = alimentacao.strip()
    if cuidados is not None:
        pet.cuidados = cuidados.strip()
    db.commit()
    return pet_dict(db, pet)


def pessoas(db: Session) -> list[dict]:
    saida = []
    for cliente in db.query(Cliente).order_by(Cliente.nome).all():
        saida.append(
            {
                "id": cliente.id,
                "nome": cliente.nome,
                "telefone": cliente.telefone,
                "cep": cliente.cep,
                "logradouro": cliente.logradouro,
                "bairro": cliente.bairro,
                "cidade": cliente.cidade,
                "uf": cliente.uf,
                "cpf": cliente.cpf or "",
                "pets": [pet_dict(db, pet) for pet in cliente.pets],
            }
        )
    return saida


def pet_dict(db: Session, pet: Pet) -> dict:
    return {
        "id": pet.id,
        "nome": pet.nome,
        "especie": pet.especie,
        "porte": pet.porte,
        "alimentacao": pet.alimentacao,
        "cuidados": pet.cuidados,
        "raca": pet.raca,
        "sexo": pet.sexo,
        "nascimento": pet.nascimento.isoformat() if pet.nascimento else None,
        "peso": pet.peso,
        "alergias": pet.alergias,
        "doencas": pet.doencas,
        "medicamentos": pet.medicamentos,
        "comportamento": pet.comportamento,
        "emergencia_nome": pet.emergencia_nome,
        "emergencia_telefone": pet.emergencia_telefone,
        "foto": pet.foto,
        "cliente_id": pet.cliente_id,
        "creditos": {
            "banho": saldo_credito(db, pet.id, "banho"),
            "tosa": saldo_credito(db, pet.id, "tosa"),
        },
    }


def catalogo(db: Session) -> dict:
    cfg = config_loja(db)
    return {
        "servicos": [
            {
                "id": s.id,
                "nome": s.nome,
                "tipo": s.tipo,
                "porte": s.porte,
                "duracao_min": s.duracao_min,
                "preco": s.preco,
                "preco_feriado": s.preco_feriado,
            }
            for s in db.query(Servico).order_by(Servico.tipo, Servico.porte).all()
        ],
        "profissionais": [
            {"id": p.id, "nome": p.nome}
            for p in db.query(Profissional).filter(Profissional.ativo.is_(True)).order_by(Profissional.nome)
        ],
        "baias": [
            {"id": b.id, "nome": b.nome, "porte": b.porte, "tipo": b.tipo}
            for b in db.query(Baia).filter(Baia.ativo.is_(True)).order_by(Baia.tipo, Baia.nome)
        ],
        "tolerancia_busca_min": cfg.tolerancia_busca_min,
        "valor_atraso": cfg.valor_atraso,
    }


def agendamento_dict(db: Session, ag: Agendamento) -> dict:
    pet = db.get(Pet, ag.pet_id)
    cliente = db.get(Cliente, pet.cliente_id) if pet else None
    servico = db.get(Servico, ag.servico_id)
    baia = db.get(Baia, ag.baia_id)
    prof = db.get(Profissional, ag.profissional_id) if ag.profissional_id else None
    agora = datetime.now()
    atraso = None
    if ag.status == "pronto":
        cfg = config_loja(db)
        atraso = calcular_atraso(ag.busca_prevista, agora, cfg.tolerancia_busca_min, cfg.valor_atraso)
    return {
        "id": ag.id,
        "titulo": ag.titulo,
        "pet_id": ag.pet_id,
        "pet": pet.nome if pet else "",
        "porte": pet.porte if pet else "",
        "cliente": cliente.nome if cliente else "",
        "cliente_id": cliente.id if cliente else None,
        "servico": servico.nome if servico else "",
        "servico_id": ag.servico_id,
        "tipo": servico.tipo if servico else "",
        "profissional": prof.nome if prof else "",
        "profissional_id": ag.profissional_id,
        "baia": baia.nome if baia else "",
        "baia_id": ag.baia_id,
        "inicio": iso(ag.inicio),
        "fim_servico": iso(ag.fim_servico),
        "busca_prevista": iso(ag.busca_prevista),
        "status": ag.status,
        "valor_combinado": ag.valor_combinado,
        "cuidados": ag.cuidados,
        "usou_credito": ag.usou_credito,
        "venda_id": ag.venda_id,
        "atraso": atraso,
        "creditos": saldo_credito(db, pet.id, servico.tipo) if pet and servico else 0,
    }


def hospedagem_dict(db: Session, hosp: Hospedagem) -> dict:
    pet = db.get(Pet, hosp.pet_id)
    cliente = db.get(Cliente, pet.cliente_id) if pet else None
    baia = db.get(Baia, hosp.baia_id)
    fim = fim_ocupacao_hotel(hosp.status, hosp.checkout_previsto, date.today())
    linhas = []
    if hosp.status in STATUS_HOTEL:
        linhas = montar_diarias(hosp.entrada, fim, hosp.valor_diaria, hosp.valor_feriado, mapa_feriados(db))
    return {
        "id": hosp.id,
        "pet_id": hosp.pet_id,
        "pet": pet.nome if pet else "",
        "porte": pet.porte if pet else "",
        "cliente": cliente.nome if cliente else "",
        "baia": baia.nome if baia else "",
        "baia_id": hosp.baia_id,
        "entrada": iso(hosp.entrada),
        "checkout_previsto": iso(hosp.checkout_previsto),
        "checkout_real": iso(hosp.checkout_real),
        "valor_diaria": hosp.valor_diaria,
        "valor_feriado": hosp.valor_feriado,
        "status": hosp.status,
        "cuidados": hosp.cuidados,
        "venda_id": hosp.venda_id,
        "diarias": [
            {"data": iso(linha["data"]), "valor": linha["valor"], "feriado": linha["feriado"]}
            for linha in linhas
        ],
    }


def encaixe_dict(db: Session, item: Encaixe) -> dict:
    pet = db.get(Pet, item.pet_id)
    servico = db.get(Servico, item.servico_id)
    cliente = db.get(Cliente, pet.cliente_id) if pet else None
    return {
        "id": item.id,
        "pet_id": item.pet_id,
        "pet": pet.nome if pet else "",
        "porte": pet.porte if pet else "",
        "cliente": cliente.nome if cliente else "",
        "servico_id": item.servico_id,
        "servico": servico.nome if servico else "",
        "dia": iso(item.dia),
        "status": item.status,
    }


def venda_dict(db: Session, venda: Venda) -> dict:
    cliente = db.get(Cliente, venda.cliente_id)
    pet = db.get(Pet, venda.pet_id) if venda.pet_id else None
    partes = db.query(Pagamento).filter(Pagamento.venda_id == venda.id).all()
    return {
        "id": venda.id,
        "numero": f"{venda.numero:05d}",
        "cliente": cliente.nome if cliente else "",
        "cliente_id": venda.cliente_id,
        "pet": pet.nome if pet else "",
        "pet_id": venda.pet_id,
        "status": venda.status,
        "forma": venda.forma,
        "forma_rotulo": ROTULOS_FORMA.get(venda.forma, venda.forma),
        "total": round(venda.total, 2),
        "desconto": round(venda.desconto or 0, 2),
        "acrescimo": round(venda.acrescimo or 0, 2),
        "observacao": venda.observacao or "",
        "criada_em": iso(venda.criada_em),
        "itens": [
            {
                "descricao": item.descricao,
                "valor": item.valor,
                "quantidade": item.quantidade or 1,
                "gramas": item.gramas,
                "produto_id": item.produto_id,
            }
            for item in venda.itens
        ],
        "pagamentos": [
            {
                "forma": parte.forma,
                "forma_rotulo": ROTULOS_FORMA.get(parte.forma, parte.forma),
                "valor": round(parte.valor, 2),
                "recebido": round(parte.recebido or 0, 2),
                "troco": round(parte.troco or 0, 2),
                "parcelas": parte.parcelas,
            }
            for parte in partes
        ],
    }


def caixa_dict(db: Session, caixa: Caixa) -> dict:
    from .models import Usuario

    formas = resumo_formas(db, caixa.id)
    esperado = round(dinheiro_esperado(caixa.saldo_inicial, formas) + ajuste_gaveta(db, caixa.id), 2)
    diferenca = None
    if caixa.saldo_informado is not None:
        diferenca = round(caixa.saldo_informado - esperado, 2)
    operador = db.get(Usuario, caixa.usuario_id) if caixa.usuario_id else None
    fechou = db.get(Usuario, caixa.fechado_por_id) if caixa.fechado_por_id else None
    vendas = [
        venda_dict(db, venda)
        for venda in db.query(Venda).filter(Venda.caixa_id == caixa.id).order_by(Venda.criada_em)
    ]
    return {
        "id": caixa.id,
        "nome": caixa.nome,
        "aberto_em": iso(caixa.aberto_em),
        "fechado_em": iso(caixa.fechado_em),
        "saldo_inicial": caixa.saldo_inicial,
        "saldo_informado": caixa.saldo_informado,
        "status": caixa.status,
        "operador": operador.nome if operador else "",
        "fechado_por": fechou.nome if fechou else "",
        "por_forma": formas,
        "esperado_em_dinheiro": esperado,
        "diferenca": diferenca,
        "vendas": vendas,
        "movimentos": [
            {
                "id": mov.id,
                "tipo": mov.tipo,
                "valor": round(mov.valor, 2),
                "motivo": mov.motivo,
                "quando": iso(mov.criado_em),
            }
            for mov in db.query(MovimentoCaixa).filter(MovimentoCaixa.caixa_id == caixa.id).order_by(MovimentoCaixa.criado_em)
        ],
    }


def listar_vendas(db: Session) -> list[dict]:
    vendas = db.query(Venda).order_by(Venda.criada_em.desc(), Venda.id.desc()).all()
    return [venda_dict(db, venda) for venda in vendas]


def listar_caixas(db: Session, usuario) -> list[dict]:
    caixa = caixa_aberto(db, usuario.id)
    return [caixa_dict(db, caixa)] if caixa else []


def agenda(db: Session, de: date, ate: date) -> dict:
    agendamentos = []
    for ag in db.query(Agendamento).order_by(Agendamento.inicio).all():
        if de <= ag.inicio.date() <= ate and ag.status not in {"cancelado", "faltou"}:
            agendamentos.append(agendamento_dict(db, ag))
    hospedagens = []
    for hosp in db.query(Hospedagem).all():
        fim = hosp.checkout_real or fim_ocupacao_hotel(hosp.status, hosp.checkout_previsto, date.today())
        if hosp.entrada <= ate and fim > de and hosp.status != "cancelada":
            hospedagens.append(hospedagem_dict(db, hosp))
    feriados = [
        {"data": iso(row.data), "nome": row.nome}
        for row in db.query(Feriado).filter(Feriado.data >= de, Feriado.data <= ate).order_by(Feriado.data)
    ]
    return {"agendamentos": agendamentos, "hospedagens": hospedagens, "feriados": feriados}


def mapa(db: Session, dia: date | None = None) -> dict:
    agora = datetime.now()
    dia = dia or agora.date()
    hoje = agora.date()
    alertas = []
    salao = []
    for baia in _baias(db, "salao"):
        atuais = []
        proximos = []
        for ag in db.query(Agendamento).filter(Agendamento.baia_id == baia.id, Agendamento.status.in_(STATUS_BAIA_SALA)):
            referencia = agora if dia == hoje else datetime.combine(dia, datetime.max.time())
            fim = fim_ocupacao_salao(ag.status, ag.busca_prevista, referencia)
            comeca_depois = ag.inicio > datetime.combine(dia, datetime.max.time())
            termina_antes = fim <= datetime.combine(dia, datetime.min.time())
            if comeca_depois or termina_antes:
                continue
            payload = agendamento_dict(db, ag)
            if ag.inicio <= referencia < fim:
                atuais.append(payload)
            elif ag.inicio.date() == dia:
                proximos.append(payload)
        atuais.sort(key=lambda item: item["inicio"])
        ocupante = atuais[0] if atuais else None
        if dia == hoje:
            for item in atuais:
                if item.get("atraso") and item["atraso"]["atrasou"]:
                    alertas.append(
                        {
                            "tipo": "atraso",
                            "texto": (
                                f"{item['pet']} está pronto e a busca prevista era {item['busca_prevista'][11:16]}. "
                                f"A baia {baia.nome} continua ocupada."
                            ),
                        }
                    )
                elif item["status"] in {"agendado", "chegou", "em_atendimento"} and item["busca_prevista"] < iso(agora):
                    alertas.append(
                        {
                            "tipo": "falta",
                            "texto": f"O horário de {item['pet']} passou e a baia {baia.nome} segue reservada. Dê baixa para liberar.",
                        }
                    )
        salao.append(
            {
                "id": baia.id,
                "nome": baia.nome,
                "porte": baia.porte,
                "tipo": "salao",
                "agora": ocupante,
                "tambem": [item["pet"] for item in atuais[1:]],
                "proximos": proximos,
                "limpeza": ocupante is None and baia.limpeza_desde is not None,
            }
        )

    hotel = []
    for baia in _baias(db, "hotel"):
        ocupante = None
        for hosp in db.query(Hospedagem).filter(Hospedagem.baia_id == baia.id, Hospedagem.status.in_(STATUS_HOTEL)):
            fim = fim_ocupacao_hotel(hosp.status, hosp.checkout_previsto, hoje)
            if hosp.entrada <= dia < fim:
                ocupante = hospedagem_dict(db, hosp)
                break
        if ocupante:
            feriados = [linha for linha in ocupante["diarias"] if linha["feriado"]]
            if feriados and dia == hoje:
                primeiro = feriados[0]
                alertas.append(
                    {
                        "tipo": "feriado",
                        "texto": (
                            f"{ocupante['pet']} segue no hotel. "
                            f"A noite de {primeiro['data'][8:10]}/{primeiro['data'][5:7]} é {primeiro['feriado']}."
                        ),
                    }
                )
            if ocupante["status"] == "hospedada" and ocupante["checkout_previsto"] <= iso(hoje):
                alertas.append(
                    {
                        "tipo": "hotel",
                        "texto": (
                            f"O checkout de {ocupante['pet']} era {ocupante['checkout_previsto'][8:10]}/"
                            f"{ocupante['checkout_previsto'][5:7]} e ainda não foi lançado. A {baia.nome} segue ocupada."
                        ),
                    }
                )
        hotel.append(
            {
                "id": baia.id,
                "nome": baia.nome,
                "porte": baia.porte,
                "tipo": "hotel",
                "agora": ocupante,
                "proximos": [],
                "limpeza": ocupante is None and baia.limpeza_desde is not None,
            }
        )

    fila = [
        encaixe_dict(db, item)
        for item in db.query(Encaixe).filter(Encaixe.dia == dia, Encaixe.status == "aguardando").order_by(Encaixe.id)
    ]
    feriado_hoje = db.get(Feriado, dia)
    return {
        "dia": iso(dia),
        "agora": iso(agora),
        "feriado_hoje": feriado_hoje.nome if feriado_hoje else None,
        "salao": salao,
        "hotel": hotel,
        "fila": fila,
        "alertas": alertas,
    }


def painel(db: Session, usuario) -> dict:
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    if inicio_mes.month == 12:
        proximo_mes = date(inicio_mes.year + 1, 1, 1)
    else:
        proximo_mes = date(inicio_mes.year, inicio_mes.month + 1, 1)
    atendimentos = (
        db.query(Agendamento)
        .filter(Agendamento.status.notin_(["cancelado", "faltou"]))
        .all()
    )
    do_dia = [ag for ag in atendimentos if ag.inicio.date() == hoje]
    vendas = (
        db.query(Venda)
        .filter(Venda.status == "paga", Venda.criada_em >= datetime.combine(inicio_mes, datetime.min.time()))
        .filter(Venda.criada_em < datetime.combine(proximo_mes, datetime.min.time()))
        .all()
    )
    quadro = mapa(db, hoje)
    caixa = caixa_aberto(db, usuario.id)
    recentes = sorted(do_dia, key=lambda ag: ag.inicio)[:8]
    return {
        "agendamentos_hoje": len(do_dia),
        "pets": db.query(Pet).count(),
        "clientes": db.query(Cliente).count(),
        "vendas_mes": round(sum(v.total for v in vendas), 2),
        "alertas": quadro["alertas"],
        "feriado_hoje": quadro["feriado_hoje"],
        "salao": quadro["salao"],
        "hotel": quadro["hotel"],
        "fila": quadro["fila"],
        "recentes": [agendamento_dict(db, ag) for ag in recentes],
        "caixa": caixa_dict(db, caixa) if caixa else None,
    }


def listar_feriados(db: Session, ano: int) -> list[dict]:
    rows = db.query(Feriado).filter(Feriado.ano == ano).order_by(Feriado.data).all()
    return [{"data": iso(row.data), "nome": row.nome} for row in rows]

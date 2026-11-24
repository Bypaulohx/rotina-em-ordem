from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from .gestao import papel_de
from .models import (
    Agendamento,
    Caixa,
    Cliente,
    Despesa,
    Fornecedor,
    Hospedagem,
    ItemPedido,
    ItemVenda,
    MarcacaoPonto,
    MovimentoEstoque,
    NotificacaoLida,
    PacoteContratado,
    PedidoLoja,
    Pesagem,
    Pet,
    Produto,
    SincronizacaoPonto,
    Usuario,
    Vacina,
    Venda,
)
from .rules import RegraNegocio
from .security import hash_senha, verificar_senha
from . import services
from .validacao import cpf_valido, digitos, email_valido, telefone_valido

UPLOADS = Path(__file__).resolve().parent.parent / "uploads"


def exigir_gestao(usuario: Usuario) -> None:
    if papel_de(usuario) not in {"admin", "gerente"}:
        raise RegraNegocio("Essa área é da gerência.", 403)


def _produto_dict(produto: Produto) -> dict:
    margem = None
    if produto.preco:
        margem = round((produto.preco - (produto.custo or 0)) / produto.preco * 100, 1)
    return {
        "id": produto.id,
        "nome": produto.nome,
        "preco": produto.preco,
        "custo": produto.custo or 0,
        "margem": margem,
        "estoque": produto.estoque,
        "minimo": produto.minimo,
        "codigo_barras": produto.codigo_barras,
        "categoria": produto.categoria,
        "marca": produto.marca,
        "validade": produto.validade.isoformat() if produto.validade else None,
        "baixo": produto.estoque <= produto.minimo,
        "esgotado": produto.estoque <= 0,
        "unidade": produto.unidade or "un",
        "foto": produto.foto or "",
    }


def _ler_balanca(db: Session, codigo: str) -> tuple[Produto, int] | None:
    if len(codigo) != 13 or not codigo.startswith("2") or not codigo.isdigit():
        return None
    plu = codigo[1:6]
    gramas = int(codigo[6:11])
    if gramas < 1:
        return None
    produto = db.query(Produto).filter(Produto.codigo_barras == plu, Produto.ativo.is_(True), Produto.unidade == "kg").first()
    if produto is None:
        return None
    return produto, gramas


def produto_por_codigo(db: Session, codigo: str) -> dict:
    limpo = (codigo or "").strip()
    pesado = _ler_balanca(db, limpo)
    if pesado:
        produto, gramas = pesado
        dados = _produto_dict(produto)
        dados["gramas"] = gramas
        return dados
    produto = db.query(Produto).filter(Produto.codigo_barras == limpo, Produto.ativo.is_(True)).first()
    if produto is None:
        raise RegraNegocio(f"Nenhum produto com o código {limpo}.", 404)
    return _produto_dict(produto)


def buscar_produtos(db: Session, termo: str) -> list[dict]:
    consulta = db.query(Produto).filter(Produto.ativo.is_(True))
    texto = (termo or "").strip()
    if texto:
        consulta = consulta.filter(Produto.nome.ilike(f"%{texto}%"))
    return [_produto_dict(item) for item in consulta.order_by(Produto.nome).limit(200 if not texto else 40)]


def _baixar_estoque(db: Session, produto: Produto, quantidade: int, motivo: str, usuario_id: int | None) -> None:
    resultado = db.execute(
        text("UPDATE produtos SET estoque = estoque - :q WHERE id = :id AND estoque >= :q"),
        {"q": quantidade, "id": produto.id},
    )
    if resultado.rowcount != 1:
        db.refresh(produto)
        raise RegraNegocio(f"{produto.nome} só tem {produto.estoque} no estoque.", 409)
    db.add(
        MovimentoEstoque(
            produto_id=produto.id,
            quantidade=-quantidade,
            motivo=motivo,
            usuario_id=usuario_id,
        )
    )


def _linha_pdv(db: Session, linha: dict) -> tuple[Produto, int, int | None, str, float]:
    if linha.get("codigo"):
        codigo = str(linha["codigo"]).strip()
        pesado = _ler_balanca(db, codigo)
        if pesado:
            produto, gramas = pesado
        else:
            produto = db.query(Produto).filter(Produto.codigo_barras == codigo, Produto.ativo.is_(True)).first()
            gramas = int(linha.get("gramas") or 0) or None
            if produto is None:
                raise RegraNegocio(f"Nenhum produto com o código {codigo}.", 404)
    else:
        produto = db.get(Produto, int(linha.get("produto_id") or 0))
        gramas = int(linha.get("gramas") or 0) or None
        if produto is None or not produto.ativo:
            raise RegraNegocio("Produto não encontrado.", 404)
    if (produto.unidade or "un") == "kg":
        if not gramas or gramas < 1:
            raise RegraNegocio(f"Informe o peso de {produto.nome} em gramas.", 400)
        valor = round(produto.preco * gramas / 1000, 2)
        quilos = f"{gramas / 1000:.3f}".replace(".", ",")
        return produto, 1, gramas, f"{produto.nome} {quilos} kg", valor
    quantidade = int(linha.get("quantidade") or 0)
    if quantidade < 1:
        raise RegraNegocio("A quantidade precisa ser pelo menos 1.", 400)
    return produto, quantidade, None, f"{produto.nome} x{quantidade}", round(produto.preco * quantidade, 2)


def _aplicar_pagamentos(venda: Venda, pagamentos: list[dict], forma: str) -> None:
    from .models import Pagamento

    liquido = round(venda.total, 2)
    if not pagamentos:
        db_forma = forma if forma in services.FORMAS else "dinheiro"
        venda.forma = db_forma
        venda.pagamentos.append(Pagamento(forma=db_forma, valor=liquido, recebido=liquido, troco=0))
        return
    aplicado = 0.0
    formas = set()
    for parte in pagamentos:
        meio = parte.get("forma")
        if meio not in services.FORMAS:
            raise RegraNegocio("Forma de pagamento desconhecida.", 400)
        valor = round(float(parte.get("valor") or 0), 2)
        if valor <= 0:
            raise RegraNegocio("Cada pagamento precisa de um valor.", 400)
        recebido = round(float(parte.get("recebido") if parte.get("recebido") is not None else valor), 2)
        troco = 0.0
        if meio == "dinheiro" and recebido + 0.001 < valor:
            raise RegraNegocio("O dinheiro recebido não cobre essa parte.", 400)
        if meio == "dinheiro" and recebido > valor:
            troco = round(recebido - valor, 2)
        parcelas = parte.get("parcelas")
        if meio == "credito" and parcelas:
            parcelas = int(parcelas)
            if parcelas < 1:
                raise RegraNegocio("O número de parcelas precisa ser pelo menos 1.", 400)
        else:
            parcelas = None
        venda.pagamentos.append(Pagamento(forma=meio, valor=valor, recebido=recebido, troco=troco, parcelas=parcelas))
        aplicado = round(aplicado + valor, 2)
        formas.add(meio)
    if abs(aplicado - liquido) > 0.02:
        raise RegraNegocio("A soma dos pagamentos precisa fechar o total da venda.", 400)
    venda.forma = next(iter(formas)) if len(formas) == 1 else "misto"


def vender_pdv(
    db: Session,
    cliente_id: int,
    itens: list[dict],
    forma: str,
    usuario_id: int | None,
    pagamentos: list[dict] | None = None,
    observacao: str = "",
    pet_id: int | None = None,
    desconto: float = 0,
    acrescimo: float = 0,
    venda_id: int | None = None,
) -> dict:
    from .models import ItemVenda, Pet

    if not itens:
        raise RegraNegocio("Passe pelo menos um produto no leitor.", 400)
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise RegraNegocio("Cliente não encontrado.", 404)
    if pet_id:
        pet = db.get(Pet, pet_id)
        if pet is None or pet.cliente_id != cliente.id:
            raise RegraNegocio("Esse animal não é deste tutor.", 400)
    preparados = [_linha_pdv(db, linha) for linha in itens]
    bruto = round(sum(valor for *_, valor in preparados), 2)
    if desconto < 0 or acrescimo < 0:
        raise RegraNegocio("Desconto e acréscimo não podem ser negativos.", 400)
    if desconto > bruto:
        raise RegraNegocio("O desconto não pode passar do total dos itens.", 400)
    liquido = round(bruto - desconto + acrescimo, 2)
    if liquido <= 0:
        raise RegraNegocio("O total da venda precisa ser maior que zero.", 400)
    for produto, quantidade, gramas, _, _ in preparados:
        _baixar_estoque(db, produto, gramas or quantidade, "Venda no PDV", usuario_id)
    if venda_id:
        venda = db.get(Venda, venda_id)
        if venda is None or venda.status != "suspensa":
            raise RegraNegocio("Essa venda não está suspensa.", 400)
        caixa = services.caixa_aberto(db, usuario_id)
        if caixa is None or venda.caixa_id != caixa.id:
            raise RegraNegocio("A venda suspensa é de outro caixa.", 403)
        for item in list(venda.itens):
            db.delete(item)
        db.flush()
        for produto, quantidade, gramas, descricao, valor in preparados:
            db.add(ItemVenda(venda_id=venda.id, descricao=descricao, valor=valor, produto_id=produto.id, quantidade=quantidade, gramas=gramas))
    else:
        venda = services.gravar_venda(
            db,
            cliente.id,
            forma or "dinheiro",
            [(descricao, valor) for _, _, _, descricao, valor in preparados],
            usuario_id,
        )
        db.flush()
        gravados = db.query(ItemVenda).filter(ItemVenda.venda_id == venda.id).all()
        for item, (produto, quantidade, gramas, _, _) in zip(gravados, preparados):
            item.produto_id = produto.id
            item.quantidade = quantidade
            item.gramas = gramas
    venda.total = liquido
    venda.desconto = round(desconto, 2)
    venda.acrescimo = round(acrescimo, 2)
    venda.observacao = (observacao or "").strip()
    venda.pet_id = pet_id
    venda.cliente_id = cliente.id
    venda.status = "paga"
    _aplicar_pagamentos(venda, pagamentos or [], forma)
    db.commit()
    return services.venda_dict(db, venda)


def suspender_pdv(db: Session, cliente_id: int, itens: list[dict], usuario_id: int, observacao: str = "", pet_id: int | None = None) -> dict:
    if not itens:
        raise RegraNegocio("Não há itens para suspender.", 400)
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise RegraNegocio("Cliente não encontrado.", 404)
    preparados = [_linha_pdv(db, linha) for linha in itens]
    venda = services.gravar_venda(
        db,
        cliente.id,
        "dinheiro",
        [(descricao, valor) for _, _, _, descricao, valor in preparados],
        usuario_id,
    )
    db.flush()
    gravados = db.query(ItemVenda).filter(ItemVenda.venda_id == venda.id).all()
    for item, (produto, quantidade, gramas, _, _) in zip(gravados, preparados):
        item.produto_id = produto.id
        item.quantidade = quantidade
        item.gramas = gramas
    venda.status = "suspensa"
    venda.observacao = (observacao or "").strip()
    venda.pet_id = pet_id
    db.commit()
    return services.venda_dict(db, venda)


def listar_suspensas(db: Session, usuario_id: int) -> list[dict]:
    caixa = services.caixa_aberto(db, usuario_id)
    if caixa is None:
        return []
    vendas = db.query(Venda).filter(Venda.caixa_id == caixa.id, Venda.status == "suspensa").order_by(Venda.criada_em).all()
    return [services.venda_dict(db, venda) for venda in vendas]


def cancelar_venda(db: Session, venda_id: int, usuario) -> dict:
    venda = db.get(Venda, venda_id)
    if venda is None:
        raise RegraNegocio("Venda não encontrada.", 404)
    if venda.status == "cancelada":
        raise RegraNegocio("Essa venda já foi cancelada.", 400)
    caixa = db.get(Caixa, venda.caixa_id)
    if caixa is None or caixa.usuario_id != usuario.id or caixa.status != "aberto":
        raise RegraNegocio("Só quem está com este caixa aberto pode cancelar a venda.", 403)
    if venda.status == "paga":
        for item in venda.itens:
            if not item.produto_id:
                continue
            produto = db.get(Produto, item.produto_id)
            quantidade = item.gramas or item.quantidade or 0
            if produto is None or quantidade < 1:
                continue
            db.refresh(produto)
            produto.estoque += quantidade
            db.add(MovimentoEstoque(produto_id=produto.id, quantidade=quantidade, motivo=f"Cancelamento da venda {venda.numero:05d}", usuario_id=usuario.id))
    venda.status = "cancelada"
    db.commit()
    return services.venda_dict(db, venda)


def adicionar_pet(db: Session, cliente_id: int, dados: dict) -> dict:
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise RegraNegocio("Cliente não encontrado.", 404)
    nome = dados["nome"].strip()
    if not nome:
        raise RegraNegocio("Informe o nome do animal.", 400)
    if dados.get("porte") not in {"P", "M", "G"}:
        raise RegraNegocio("O porte precisa ser P, M ou G.", 400)
    repetido = (
        db.query(Pet).filter(Pet.cliente_id == cliente.id, Pet.nome.ilike(nome)).first()
    )
    if repetido is not None:
        raise RegraNegocio(f"{cliente.nome} já tem um animal chamado {nome}.", 409)
    pet = Pet(
        cliente_id=cliente.id,
        nome=nome,
        especie=dados.get("especie") or "cão",
        porte=dados["porte"],
        raca=dados.get("raca", "").strip(),
        sexo=dados.get("sexo", "").strip(),
        nascimento=dados.get("nascimento"),
        cuidados=dados.get("cuidados", "").strip(),
        alergias=dados.get("alergias", "").strip(),
        comportamento=dados.get("comportamento", "").strip(),
    )
    db.add(pet)
    db.commit()
    return services.pet_dict(db, pet)


def atualizar_ficha_pet(db: Session, pet_id: int, dados: dict) -> dict:
    pet = services._pet(db, pet_id)
    for campo in ("raca", "sexo", "alergias", "doencas", "medicamentos", "comportamento", "emergencia_nome", "cuidados", "alimentacao"):
        if campo in dados and dados[campo] is not None:
            setattr(pet, campo, str(dados[campo]).strip())
    if dados.get("emergencia_telefone") is not None:
        telefone = digitos(dados["emergencia_telefone"])
        if telefone and not telefone_valido(telefone):
            raise RegraNegocio("O telefone de emergência precisa ter DDD.", 400)
        pet.emergencia_telefone = telefone
    if dados.get("nascimento"):
        pet.nascimento = dados["nascimento"]
    db.commit()
    return services.pet_dict(db, pet)


def registrar_peso(db: Session, pet_id: int, peso: float) -> dict:
    pet = services._pet(db, pet_id)
    if peso <= 0:
        raise RegraNegocio("Informe o peso em quilos.", 400)
    pet.peso = round(peso, 2)
    db.add(Pesagem(pet_id=pet.id, peso=pet.peso))
    db.commit()
    return services.pet_dict(db, pet)


def registrar_vacina(db: Session, pet_id: int, nome: str, aplicada_em: date, proxima: date | None) -> dict:
    services._pet(db, pet_id)
    if not nome.strip():
        raise RegraNegocio("Informe a vacina.", 400)
    db.add(Vacina(pet_id=pet_id, nome=nome.strip(), aplicada_em=aplicada_em, proxima=proxima))
    db.commit()
    return ficha_pet(db, pet_id)


def salvar_foto(db: Session, pet_id: int, conteudo: bytes, extensao: str) -> dict:
    pet = services._pet(db, pet_id)
    if not conteudo:
        raise RegraNegocio("A foto veio vazia.", 400)
    if len(conteudo) > 2_000_000:
        raise RegraNegocio("A foto precisa ter até 2 MB.", 400)
    UPLOADS.mkdir(exist_ok=True)
    nome = f"pet-{pet.id}{extensao}"
    (UPLOADS / nome).write_bytes(conteudo)
    pet.foto = f"/uploads/{nome}"
    db.commit()
    return services.pet_dict(db, pet)


def _pacotes(db: Session, pet_id: int) -> list[dict]:
    return [
        {
            "id": item.id,
            "nome": item.nome,
            "tipo": item.tipo,
            "total": item.total,
            "utilizadas": item.total - item.saldo,
            "restantes": item.saldo,
            "valor": item.valor,
            "validade": item.validade.isoformat() if item.validade else None,
        }
        for item in db.query(PacoteContratado).filter(PacoteContratado.pet_id == pet_id).order_by(PacoteContratado.id.desc())
    ]


def ficha_pet(db: Session, pet_id: int) -> dict:
    pet = services._pet(db, pet_id)
    cliente = db.get(Cliente, pet.cliente_id)
    atendimentos = [
        services.agendamento_dict(db, item)
        for item in db.query(Agendamento).filter(Agendamento.pet_id == pet.id).order_by(Agendamento.inicio.desc())
    ]
    hospedagens = [
        services.hospedagem_dict(db, item)
        for item in db.query(Hospedagem).filter(Hospedagem.pet_id == pet.id).order_by(Hospedagem.entrada.desc())
    ]
    vendas = []
    if cliente is not None:
        for venda in db.query(Venda).filter(Venda.cliente_id == cliente.id).order_by(Venda.criada_em.desc()):
            if any(ag.pet_id == pet.id and ag.venda_id == venda.id for ag in db.query(Agendamento).filter(Agendamento.venda_id == venda.id)) or any(
                hosp.pet_id == pet.id and hosp.venda_id == venda.id for hosp in db.query(Hospedagem).filter(Hospedagem.venda_id == venda.id)
            ):
                vendas.append(services.venda_dict(db, venda))
    return {
        "pet": services.pet_dict(db, pet),
        "cliente": {"id": cliente.id, "nome": cliente.nome, "telefone": cliente.telefone} if cliente else None,
        "pacotes": _pacotes(db, pet.id),
        "pesagens": [
            {"peso": item.peso, "quando": item.quando.isoformat(timespec="minutes")}
            for item in db.query(Pesagem).filter(Pesagem.pet_id == pet.id).order_by(Pesagem.quando.desc())
        ],
        "vacinas": [
            {"nome": item.nome, "aplicada_em": item.aplicada_em.isoformat(), "proxima": item.proxima.isoformat() if item.proxima else None}
            for item in db.query(Vacina).filter(Vacina.pet_id == pet.id).order_by(Vacina.aplicada_em.desc())
        ],
        "atendimentos": atendimentos,
        "hospedagens": hospedagens,
        "compras": vendas,
        "prontuario": _notas(db, pet.id),
    }


def _notas(db: Session, pet_id: int) -> list[dict]:
    from .models import NotaProntuario

    return [
        {"texto": nota.texto, "quando": nota.criado_em.isoformat(timespec="minutes")}
        for nota in db.query(NotaProntuario).filter(NotaProntuario.pet_id == pet_id).order_by(NotaProntuario.criado_em.desc())
    ]


def ficha_cliente(db: Session, cliente_id: int) -> dict:
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise RegraNegocio("Cliente não encontrado.", 404)
    vendas = [services.venda_dict(db, item) for item in db.query(Venda).filter(Venda.cliente_id == cliente.id).order_by(Venda.criada_em.desc())]
    pets = []
    for pet in cliente.pets:
        pets.append({**services.pet_dict(db, pet), "pacotes": _pacotes(db, pet.id)})
    agendamentos = []
    hospedagens = []
    for pet in cliente.pets:
        agendamentos.extend(
            services.agendamento_dict(db, item)
            for item in db.query(Agendamento).filter(Agendamento.pet_id == pet.id).order_by(Agendamento.inicio.desc()).limit(20)
        )
        hospedagens.extend(
            services.hospedagem_dict(db, item)
            for item in db.query(Hospedagem).filter(Hospedagem.pet_id == pet.id).order_by(Hospedagem.entrada.desc())
        )
    return {
        "id": cliente.id,
        "nome": cliente.nome,
        "telefone": cliente.telefone,
        "email": cliente.email,
        "cpf": cliente.cpf,
        "cep": cliente.cep,
        "logradouro": cliente.logradouro,
        "numero": cliente.numero,
        "bairro": cliente.bairro,
        "cidade": cliente.cidade,
        "uf": cliente.uf,
        "observacoes": cliente.observacoes,
        "pets": pets,
        "compras": vendas,
        "pendencias": [item for item in vendas if item["status"] != "paga"],
        "agendamentos": agendamentos,
        "hospedagens": hospedagens,
    }


def notificacoes(db: Session, usuario_id: int) -> list[dict]:
    agora = datetime.now()
    hoje = agora.date()
    lidas = {
        item.chave
        for item in db.query(NotificacaoLida).filter(NotificacaoLida.usuario_id == usuario_id)
    }
    itens: list[dict] = []

    def por(chave: str, tipo: str, prioridade: str, texto: str, quando: datetime, acao: str | None = None, ref: int | None = None) -> None:
        itens.append(
            {
                "chave": chave,
                "tipo": tipo,
                "prioridade": prioridade,
                "texto": texto,
                "quando": quando.isoformat(timespec="minutes"),
                "lida": chave in lidas,
                "acao": acao,
                "ref": ref,
            }
        )

    mapa = services.mapa(db, hoje)
    for alerta in mapa["alertas"]:
        por(f"alerta:{alerta['texto'][:60]}", alerta["tipo"], "alta", alerta["texto"], agora, "mapa")
    for produto in db.query(Produto).filter(Produto.ativo.is_(True)):
        if produto.estoque <= 0:
            por(f"estoque:{produto.id}", "estoque", "alta", f"{produto.nome} está esgotado.", agora, "estoque", produto.id)
        elif produto.estoque <= produto.minimo:
            por(f"estoque:{produto.id}", "estoque", "media", f"{produto.nome} chegou no mínimo ({produto.estoque}).", agora, "estoque", produto.id)
        if produto.validade and produto.validade <= hoje + timedelta(days=30):
            por(f"validade:{produto.id}", "estoque", "media", f"{produto.nome} vence em {produto.validade.strftime('%d/%m/%Y')}.", agora, "estoque", produto.id)
    limite = hoje + timedelta(days=1)
    for hosp in db.query(Hospedagem).filter(Hospedagem.status.in_(("reservada", "hospedada"))):
        if hoje <= hosp.checkout_previsto <= limite:
            pet = db.get(Pet, hosp.pet_id)
            por(
                f"hotel:{hosp.id}:{hosp.checkout_previsto.isoformat()}",
                "hotel",
                "media",
                f"O checkout de {pet.nome if pet else 'um pet'} é {hosp.checkout_previsto.strftime('%d/%m')}.",
                agora,
                "mapa",
                hosp.id,
            )
    for despesa in db.query(Despesa).filter(Despesa.status == "aberta"):
        if despesa.vencimento and despesa.vencimento <= hoje + timedelta(days=3):
            por(
                f"conta:{despesa.id}",
                "financeiro",
                "alta" if despesa.vencimento < hoje else "media",
                f"Conta a pagar: {despesa.descricao} vence em {despesa.vencimento.strftime('%d/%m')}.",
                agora,
                "financeiro",
                despesa.id,
            )
    ordem = {"alta": 0, "media": 1, "baixa": 2}
    return sorted(itens, key=lambda item: (item["lida"], ordem.get(item["prioridade"], 3), item["quando"]))


def ler_notificacao(db: Session, usuario_id: int, chave: str) -> dict:
    if not chave.strip():
        raise RegraNegocio("Informe a notificação.", 400)
    existe = db.get(NotificacaoLida, {"usuario_id": usuario_id, "chave": chave})
    if existe is None:
        db.add(NotificacaoLida(usuario_id=usuario_id, chave=chave[:80]))
        db.commit()
    return {"ok": True}


def indicadores(db: Session, inicio: date, fim: date) -> dict:
    if fim < inicio:
        raise RegraNegocio("O período está invertido.", 400)
    começo = datetime.combine(inicio, datetime.min.time())
    limite = datetime.combine(fim + timedelta(days=1), datetime.min.time())
    vendas = (
        db.query(Venda)
        .filter(Venda.criada_em >= começo, Venda.criada_em < limite, Venda.status == "paga")
        .all()
    )
    despesas = db.query(Despesa).filter(Despesa.data >= inicio, Despesa.data <= fim, Despesa.status != "aberta").all()
    abertas = db.query(Despesa).filter(Despesa.status == "aberta").all()
    receber = db.query(PedidoLoja).filter(PedidoLoja.status == "reservado").all()
    total = round(sum(item.total for item in vendas), 2)
    gasto = round(sum(item.valor for item in despesas), 2)
    hoje = date.today()
    hoje_ini = datetime.combine(hoje, datetime.min.time())
    faturamento_dia = round(sum(item.total for item in vendas if item.criada_em >= hoje_ini and item.criada_em < hoje_ini + timedelta(days=1)), 2)
    agendamentos = db.query(Agendamento).filter(Agendamento.inicio >= começo, Agendamento.inicio < limite, Agendamento.status.notin_(("cancelado", "faltou"))).all()
    do_dia = [item for item in agendamentos if item.inicio.date() == hoje]
    hospedados = db.query(Hospedagem).filter(Hospedagem.status == "hospedada").count()
    mapa = services.mapa(db, hoje)
    ocupadas = sum(1 for baia in mapa["salao"] + mapa["hotel"] if baia["agora"] or baia.get("limpeza"))
    total_baias = len(mapa["salao"]) + len(mapa["hotel"])
    produtos = [_produto_dict(item) for item in db.query(Produto).filter(Produto.ativo.is_(True)).order_by(Produto.nome)]
    por_forma: dict[str, float] = {}
    for venda in vendas:
        por_forma[venda.forma] = round(por_forma.get(venda.forma, 0) + venda.total, 2)
    return {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "faturamento_dia": faturamento_dia,
        "faturamento": total,
        "despesas": gasto,
        "resultado": round(total - gasto, 2),
        "vendas": len(vendas),
        "ticket_medio": round(total / len(vendas), 2) if vendas else 0,
        "agendamentos": len(agendamentos),
        "agendamentos_hoje": len(do_dia),
        "hospedados": hospedados,
        "ocupacao": round(ocupadas / total_baias * 100, 1) if total_baias else 0,
        "baias_ocupadas": ocupadas,
        "baias": total_baias,
        "por_forma": por_forma,
        "estoque_baixo": [item for item in produtos if item["baixo"]],
        "contas_pagar": [
            {"id": item.id, "descricao": item.descricao, "valor": item.valor, "vencimento": item.vencimento.isoformat() if item.vencimento else None}
            for item in abertas
        ],
        "contas_receber": [{"id": item.id, "total": item.total, "quando": item.criada_em.isoformat(timespec="minutes")} for item in receber],
        "produtos": produtos,
    }


def criar_fornecedor(db: Session, nome: str, telefone: str, email: str) -> dict:
    limpo = nome.strip()
    if not limpo:
        raise RegraNegocio("Informe o fornecedor.", 400)
    if email and not email_valido(email):
        raise RegraNegocio("O e-mail do fornecedor não é válido.", 400)
    row = Fornecedor(nome=limpo, telefone=digitos(telefone), email=email.strip())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "nome": row.nome}


def criar_conta(db: Session, descricao: str, valor: float, vencimento: date, categoria: str, usuario_id: int) -> dict:
    if not descricao.strip() or valor <= 0:
        raise RegraNegocio("Informe a conta e um valor maior que zero.", 400)
    db.add(
        Despesa(
            descricao=descricao.strip(),
            valor=round(valor, 2),
            data=vencimento,
            vencimento=vencimento,
            categoria=categoria.strip() or "loja",
            status="aberta",
            usuario_id=usuario_id,
        )
    )
    db.commit()
    return {"ok": True}


def pagar_conta(db: Session, despesa_id: int) -> dict:
    conta = db.get(Despesa, despesa_id)
    if conta is None:
        raise RegraNegocio("Conta não encontrada.", 404)
    if conta.status == "paga":
        raise RegraNegocio("Essa conta já foi paga.", 409)
    conta.status = "paga"
    conta.data = date.today()
    db.commit()
    return {"ok": True}


def ler_afd(conteudo: str) -> list[dict]:
    marcas = []
    for bruto in conteudo.splitlines():
        linha = bruto.strip("\r")
        if len(linha) < 34 or linha[9:10] != "3":
            continue
        nsr = linha[0:9]
        dia = linha[10:18]
        hora = linha[18:22]
        pis = linha[22:34]
        if not (nsr.isdigit() and dia.isdigit() and hora.isdigit() and pis.isdigit()):
            continue
        marcas.append(
            {
                "nsr": nsr,
                "pis": pis,
                "marcada_em": datetime.strptime(dia + hora, "%d%m%Y%H%M"),
            }
        )
    return marcas


def importar_afd(db: Session, conteudo: str, origem: str = "afd") -> dict:
    try:
        marcas = ler_afd(conteudo)
    except ValueError as erro:
        sync = SincronizacaoPonto(origem=origem, falha="Não foi possível ler o horário de uma marcação.")
        db.add(sync)
        db.commit()
        raise RegraNegocio("O arquivo de ponto tem uma data ou hora inválida.", 400) from erro
    sync = SincronizacaoPonto(origem=origem, recebidas=len(marcas))
    db.add(sync)
    db.flush()
    novas = 0
    for marca in marcas:
        existe = (
            db.query(MarcacaoPonto)
            .filter(MarcacaoPonto.nsr == marca["nsr"], MarcacaoPonto.origem == origem)
            .first()
        )
        if existe is not None:
            continue
        usuario = db.query(Usuario).filter(Usuario.pis == marca["pis"]).first()
        db.add(
            MarcacaoPonto(
                nsr=marca["nsr"],
                pis=marca["pis"],
                marcada_em=marca["marcada_em"],
                usuario_id=usuario.id if usuario else None,
                origem=origem,
                sincronizacao_id=sync.id,
            )
        )
        novas += 1
    sync.novas = novas
    db.commit()
    return {"recebidas": len(marcas), "novas": novas, "sincronizacao": sync.id}


def ponto_painel(db: Session) -> dict:
    marcas = db.query(MarcacaoPonto).order_by(MarcacaoPonto.marcada_em.desc()).limit(80).all()
    saida = []
    for marca in marcas:
        usuario = db.get(Usuario, marca.usuario_id) if marca.usuario_id else None
        saida.append(
            {
                "nsr": marca.nsr,
                "pis": marca.pis,
                "quando": marca.marcada_em.isoformat(timespec="minutes"),
                "funcionario": usuario.nome if usuario else None,
                "origem": marca.origem,
            }
        )
    syncs = [
        {"id": item.id, "origem": item.origem, "recebidas": item.recebidas, "novas": item.novas, "falha": item.falha, "quando": item.criada_em.isoformat(timespec="minutes")}
        for item in db.query(SincronizacaoPonto).order_by(SincronizacaoPonto.id.desc()).limit(10)
    ]
    return {"marcacoes": saida, "sincronizacoes": syncs}


def loja_produtos(db: Session) -> list[dict]:
    return [
        _produto_dict(item)
        for item in db.query(Produto).filter(Produto.ativo.is_(True), Produto.estoque > 0).order_by(Produto.nome)
    ]


def loja_cadastrar(db: Session, dados: dict) -> dict:
    nome = dados["nome"].strip()
    email = dados["email"].strip().lower()
    telefone = digitos(dados.get("telefone", ""))
    if not nome or not email_valido(email) or not telefone_valido(telefone):
        raise RegraNegocio("Informe nome, e-mail válido e telefone com DDD.", 400)
    if not dados.get("senha") or len(dados["senha"]) < 6:
        raise RegraNegocio("A senha da loja precisa ter pelo menos 6 caracteres.", 400)
    if db.query(Cliente).filter(Cliente.email == email).first():
        raise RegraNegocio("Já existe um cadastro com esse e-mail.", 409)
    services._telefone_livre(db, telefone)
    cliente = Cliente(
        nome=nome,
        email=email,
        telefone=telefone,
        senha_hash=hash_senha(dados["senha"]),
        cep=digitos(dados.get("cep", "")),
        logradouro=dados.get("logradouro", "").strip(),
        cidade=dados.get("cidade", "").strip(),
        uf=dados.get("uf", "").strip().upper()[:2],
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return {"id": cliente.id, "nome": cliente.nome, "email": cliente.email}


def loja_entrar(db: Session, email: str, senha: str) -> Cliente:
    cliente = db.query(Cliente).filter(Cliente.email == email.strip().lower()).first()
    if cliente is None or not cliente.senha_hash or not verificar_senha(senha, cliente.senha_hash):
        raise RegraNegocio("E-mail ou senha não conferem.", 401)
    return cliente


def loja_pedir(db: Session, cliente_id: int, itens: list[dict], entrega: str) -> dict:
    if entrega not in {"retirada", "entrega"}:
        raise RegraNegocio("Escolha retirada na loja ou entrega.", 400)
    if not itens:
        raise RegraNegocio("O carrinho está vazio.", 400)
    pedido = PedidoLoja(cliente_id=cliente_id, status="reservado", entrega=entrega, total=0)
    db.add(pedido)
    db.flush()
    total = 0.0
    for linha in itens:
        quantidade = int(linha.get("quantidade") or 0)
        produto = db.get(Produto, int(linha.get("produto_id") or 0))
        if produto is None or not produto.ativo:
            raise RegraNegocio("Um produto do carrinho não está mais à venda.", 404)
        if quantidade < 1:
            raise RegraNegocio("Quantidade inválida.", 400)
        _baixar_estoque(db, produto, quantidade, f"Reserva do pedido {pedido.id}", None)
        db.add(ItemPedido(pedido_id=pedido.id, produto_id=produto.id, quantidade=quantidade, preco=produto.preco))
        total += produto.preco * quantidade
    pedido.total = round(total, 2)
    db.commit()
    db.refresh(pedido)
    return {"id": pedido.id, "total": pedido.total, "status": pedido.status, "entrega": pedido.entrega}


def receber_pedido(db: Session, pedido_id: int, forma: str, usuario_id: int) -> dict:
    pedido = db.get(PedidoLoja, pedido_id)
    if pedido is None:
        raise RegraNegocio("Pedido não encontrado.", 404)
    if pedido.status == "pago":
        raise RegraNegocio("Esse pedido já entrou no caixa. Não lance de novo.", 409)
    if pedido.status != "reservado":
        raise RegraNegocio("Esse pedido não está aguardando pagamento.", 400)
    itens = db.query(ItemPedido).filter(ItemPedido.pedido_id == pedido.id).all()
    venda = services.gravar_venda(
        db,
        pedido.cliente_id,
        forma,
        [(f"{db.get(Produto, item.produto_id).nome} x{item.quantidade}", round(item.preco * item.quantidade, 2)) for item in itens],
        usuario_id,
    )
    for item_venda, item in zip(venda.itens, itens):
        item_venda.produto_id = item.produto_id
        item_venda.quantidade = item.quantidade
    pedido.status = "pago"
    pedido.venda_id = venda.id
    db.commit()
    return services.venda_dict(db, venda)


def pedidos_cliente(db: Session, cliente_id: int) -> list[dict]:
    return [
        {"id": item.id, "total": item.total, "status": item.status, "entrega": item.entrega, "quando": item.criada_em.isoformat(timespec="minutes")}
        for item in db.query(PedidoLoja).filter(PedidoLoja.cliente_id == cliente_id).order_by(PedidoLoja.id.desc())
    ]

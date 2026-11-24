from __future__ import annotations

from datetime import datetime

from .database import SessionLocal
from .models import Atividade, Sessao

IGNORAR = {"/api/login", "/api/logout", "/api/whatsapp/webhook"}


def descrever(method: str, path: str) -> str:
    partes = [parte for parte in path.removeprefix("/api/").split("/") if parte]
    if not partes:
        return "Atualizou a rotina"
    if partes[0] == "agendamentos" and len(partes) >= 3:
        return {
            "chegou": "Marcou a chegada de um pet",
            "iniciar": "Iniciou um atendimento",
            "pronto": "Marcou um pet como pronto",
            "buscar": "Recebeu a busca e liberou a baia",
            "cancelar": "Cancelou um atendimento",
            "faltou": "Marcou falta e liberou a baia",
        }.get(partes[2], "Atualizou um atendimento")
    if partes[0] == "hospedagens" and len(partes) >= 3 and partes[2] == "checkout":
        return "Fez o checkout do hotel"
    if partes[0] == "caixas" and len(partes) >= 3 and partes[2] == "fechar":
        return "Fechou e conferiu um caixa"
    if partes[0] == "caixas" and len(partes) >= 3 and partes[2] == "movimento":
        return "Registrou sangria ou suprimento"
    if partes[0] == "caixas" and len(partes) >= 3 and partes[2] == "transferir":
        return "Transferiu a responsabilidade do caixa"
    if partes[0] == "vendas" and len(partes) >= 3 and partes[2] == "cancelar":
        return "Cancelou uma venda"
    if partes[0] == "pdv" and len(partes) >= 2 and partes[1] == "suspender":
        return "Suspendeu uma venda"
    if partes[0] == "lembretes" and len(partes) >= 3:
        return "Concluiu um lembrete"
    return {
        ("POST", "agendamentos"): "Criou um agendamento",
        ("POST", "hospedagens"): "Criou uma hospedagem",
        ("POST", "vendas"): "Lançou uma venda",
        ("POST", "pdv"): "Recebeu uma venda no caixa",
        ("POST", "pacotes"): "Vendeu um pacote",
        ("POST", "caixas"): "Abriu um caixa",
        ("POST", "clientes"): "Cadastrou cliente e pet",
        ("POST", "encaixes"): "Colocou um pet na fila",
        ("POST", "prontuario"): "Escreveu no prontuário",
        ("POST", "lembretes"): "Criou um lembrete",
        ("POST", "produtos"): "Incluiu um item no catálogo",
        ("PATCH", "servicos"): "Atualizou um preço do catálogo",
        ("POST", "estoque"): "Movimentou o estoque",
        ("POST", "despesas"): "Lançou uma despesa",
        ("POST", "whatsapp/mensagens"): "Registrou uma mensagem de WhatsApp",
        ("PUT", "whatsapp"): "Atualizou o WhatsApp da loja",
        ("POST", "admin/funcionarios"): "Cadastrou um funcionário",
    }.get((method, partes[0] if len(partes) == 1 or partes[1].isdigit() else "/".join(partes[:2])), "Atualizou a rotina")


def registrar(token: str | None, method: str, path: str) -> None:
    if not token or method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    if not path.startswith("/api/") or path in IGNORAR or path.startswith("/api/simulacoes"):
        return
    db = SessionLocal()
    try:
        sessao = db.get(Sessao, token)
        if sessao is None:
            return
        db.add(Atividade(usuario_id=sessao.usuario_id, acao=descrever(method, path), detalhe="", criado_em=datetime.now()))
        db.commit()
    finally:
        db.close()

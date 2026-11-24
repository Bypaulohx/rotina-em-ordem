from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

PORTE_ORDEM = {"P": 1, "M": 2, "G": 3}
STATUS_BAIA_SALA = {"agendado", "chegou", "em_atendimento", "pronto"}
STATUS_PROFISSIONAL = {"agendado", "chegou", "em_atendimento"}
STATUS_HOTEL = {"reservada", "hospedada"}


class RegraNegocio(Exception):
    def __init__(self, mensagem: str, status: int = 409, extra: dict | None = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status
        self.extra = extra or {}


def porte_cabe(porte_baia: str, porte_pet: str) -> bool:
    return PORTE_ORDEM[porte_pet] <= PORTE_ORDEM[porte_baia]


def sobrepoe(inicio_a: datetime, fim_a: datetime, inicio_b: datetime, fim_b: datetime) -> bool:
    return inicio_a < fim_b and inicio_b < fim_a


def datas_sobrepoem(inicio_a: date, fim_a: date, inicio_b: date, fim_b: date) -> bool:
    return inicio_a < fim_b and inicio_b < fim_a


def noites_entre(entrada: date, checkout: date) -> list[date]:
    if checkout <= entrada:
        return []
    dias = []
    cursor = entrada
    while cursor < checkout:
        dias.append(cursor)
        cursor += timedelta(days=1)
    return dias


def fim_ocupacao_salao(status: str, busca_prevista: datetime, agora: datetime) -> datetime:
    if status == "pronto":
        return datetime.max.replace(microsecond=0)
    if status in {"agendado", "chegou", "em_atendimento"} and busca_prevista < agora:
        return datetime.max.replace(microsecond=0)
    return busca_prevista


def fim_profissional(status: str, fim_servico: datetime, agora: datetime) -> datetime:
    if status in {"em_atendimento", "chegou"} and fim_servico < agora:
        return datetime.max.replace(microsecond=0)
    return fim_servico


def fim_ocupacao_hotel(status: str, checkout_previsto: date, hoje: date) -> date:
    if status == "hospedada" and checkout_previsto <= hoje:
        return hoje + timedelta(days=1)
    return checkout_previsto


def escolher_menor_baia(baias: list[dict], porte_pet: str) -> list[dict]:
    compativeis = [b for b in baias if porte_cabe(b["porte"], porte_pet)]
    return sorted(compativeis, key=lambda b: (PORTE_ORDEM[b["porte"]], b["nome"]))


def classificar_intervalos(
    candidatos: list[dict],
    ocupacoes: list[dict],
    inicio: datetime,
    fim: datetime,
    chave: str,
) -> tuple[list[dict], list[dict]]:
    livres = []
    ocupados = []
    for item in candidatos:
        choque = next(
            (
                o
                for o in ocupacoes
                if o[chave] == item["id"] and sobrepoe(inicio, fim, o["inicio"], o["fim"])
            ),
            None,
        )
        if choque:
            ocupados.append({**item, "ocupante": choque.get("rotulo", ""), "ate": choque["fim"]})
        else:
            livres.append(item)
    return livres, ocupados


def calcular_atraso(
    busca_prevista: datetime,
    busca_real: datetime,
    tolerancia_min: int,
    valor_atraso: float,
) -> dict:
    limite = busca_prevista + timedelta(minutes=tolerancia_min)
    if busca_real <= limite:
        return {"atrasou": False, "minutos": 0, "valor": 0.0}
    minutos = int((busca_real - busca_prevista).total_seconds() // 60)
    return {"atrasou": True, "minutos": minutos, "valor": round(valor_atraso, 2)}


def aplicar_credito(saldo: int, valor: float) -> dict:
    if saldo > 0:
        return {"saldo_restante": saldo - 1, "valor": 0.0, "usou": True}
    return {"saldo_restante": saldo, "valor": round(valor, 2), "usou": False}


def montar_diarias(
    entrada: date,
    checkout: date,
    valor_diaria: float,
    valor_feriado: float,
    feriados: dict[date, str],
) -> list[dict]:
    linhas = []
    for noite in noites_entre(entrada, checkout):
        nome = feriados.get(noite)
        linhas.append(
            {
                "data": noite,
                "valor": round(valor_feriado if nome else valor_diaria, 2),
                "feriado": nome,
            }
        )
    return linhas


def dinheiro_esperado(saldo_inicial: float, totais_por_forma: dict[str, float]) -> float:
    return round(saldo_inicial + totais_por_forma.get("dinheiro", 0.0), 2)


@dataclass(frozen=True)
class JanelaServico:
    inicio: datetime
    fim_servico: datetime
    busca: datetime


def montar_janela(inicio: datetime, busca: datetime, duracao_min: int) -> JanelaServico:
    fim = inicio + timedelta(minutes=duracao_min)
    if busca < fim:
        raise RegraNegocio(
            f"A busca está marcada antes do fim do serviço. Este atendimento leva {duracao_min} minutos.",
            status=400,
        )
    if busca <= inicio:
        raise RegraNegocio("A hora da busca precisa ser depois da chegada.", status=400)
    return JanelaServico(inicio=inicio, fim_servico=fim, busca=busca)

from __future__ import annotations

import os
from datetime import date, timedelta

import httpx
from sqlalchemy.orm import Session

from .models import Feriado

BRASIL_API = "https://brasilapi.com.br/api/feriados/v1/{ano}"


def calcular_pascoa(ano: int) -> date:
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


def feriados_oficiais(ano: int) -> dict[date, str]:
    sexta = calcular_pascoa(ano) - timedelta(days=2)
    return {
        date(ano, 1, 1): "Confraternização universal",
        sexta: "Sexta-feira Santa",
        date(ano, 4, 21): "Tiradentes",
        date(ano, 5, 1): "Dia do Trabalho",
        date(ano, 9, 7): "Independência do Brasil",
        date(ano, 10, 12): "Nossa Senhora Aparecida",
        date(ano, 11, 2): "Finados",
        date(ano, 11, 15): "Proclamação da República",
        date(ano, 11, 20): "Dia da Consciência Negra",
        date(ano, 12, 25): "Natal",
    }


async def sincronizar_feriados(db: Session) -> None:
    hoje = date.today()
    anos = {hoje.year, hoje.year + 1}
    permitir_rede = os.environ.get("ROTINA_TEST") != "1"
    async with httpx.AsyncClient(timeout=8) as client:
        for ano in sorted(anos):
            mapa = feriados_oficiais(ano)
            if permitir_rede:
                try:
                    resposta = await client.get(BRASIL_API.format(ano=ano))
                    if resposta.status_code == 200:
                        for item in resposta.json():
                            mapa[date.fromisoformat(item["date"])] = item["name"]
                except httpx.HTTPError:
                    pass
            db.query(Feriado).filter(Feriado.ano == ano).delete()
            for dia, nome in mapa.items():
                db.add(Feriado(data=dia, nome=nome, ano=ano))
    db.commit()


def mapa_feriados(db: Session) -> dict[date, str]:
    return {row.data: row.nome for row in db.query(Feriado).all()}

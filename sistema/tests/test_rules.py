from datetime import date, datetime, timedelta

import pytest

from app.rules import (
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
    noites_entre,
    porte_cabe,
    sobrepoe,
)


def test_porte_menor_cabe_em_baia_maior():
    assert porte_cabe("M", "P")
    assert porte_cabe("G", "G")
    assert not porte_cabe("P", "M")


def test_intervalos_encostados_nao_conflitam():
    hora = datetime(2026, 10, 31, 14, 0)
    assert not sobrepoe(hora, hora + timedelta(hours=1), hora + timedelta(hours=1), hora + timedelta(hours=2))
    assert sobrepoe(hora, hora + timedelta(hours=1), hora + timedelta(minutes=30), hora + timedelta(hours=2))


def test_escolhe_a_menor_baia_que_cabe():
    baias = [
        {"id": 1, "nome": "G1", "porte": "G"},
        {"id": 2, "nome": "P2", "porte": "P"},
        {"id": 3, "nome": "M1", "porte": "M"},
        {"id": 4, "nome": "P1", "porte": "P"},
    ]
    ordem = [b["nome"] for b in escolher_menor_baia(baias, "P")]
    assert ordem == ["P1", "P2", "M1", "G1"]
    assert [b["nome"] for b in escolher_menor_baia(baias, "G")] == ["G1"]


def test_pet_pronto_ou_horario_vencido_segura_a_baia():
    busca = datetime(2026, 10, 31, 15, 0)
    agora = datetime(2026, 10, 31, 16, 0)
    antes = datetime(2026, 10, 31, 14, 0)
    assert fim_ocupacao_salao("agendado", busca, antes) == busca
    assert fim_ocupacao_salao("agendado", busca, agora) == datetime.max.replace(microsecond=0)
    assert fim_ocupacao_salao("pronto", busca, agora) == datetime.max.replace(microsecond=0)


def test_profissional_so_segue_ocupado_se_o_servico_comecou():
    fim = datetime(2026, 10, 31, 15, 0)
    agora = datetime(2026, 10, 31, 16, 0)
    assert fim_profissional("agendado", fim, agora) == fim
    assert fim_profissional("em_atendimento", fim, agora) == datetime.max.replace(microsecond=0)


def test_hotel_sem_checkout_segue_ocupado():
    previsto = date(2026, 11, 3)
    hoje = date(2026, 11, 4)
    assert fim_ocupacao_hotel("hospedada", previsto, hoje) == date(2026, 11, 5)
    assert fim_ocupacao_hotel("hospedada", previsto, date(2026, 11, 1)) == previsto


def test_classifica_baia_livre_e_ocupada():
    inicio = datetime(2026, 10, 31, 14, 0)
    fim = datetime(2026, 10, 31, 16, 0)
    candidatos = [{"id": 1, "nome": "M1"}, {"id": 2, "nome": "M2"}]
    ocupacoes = [{"baia_id": 1, "inicio": inicio, "fim": fim, "rotulo": "Mingau"}]
    livres, ocupados = classificar_intervalos(candidatos, ocupacoes, inicio, fim, "baia_id")
    assert [b["nome"] for b in livres] == ["M2"]
    assert ocupados[0]["ocupante"] == "Mingau"


def test_atraso_respeita_tolerancia():
    prevista = datetime(2026, 10, 31, 15, 0)
    dentro = calcular_atraso(prevista, prevista + timedelta(minutes=10), 15, 20)
    fora = calcular_atraso(prevista, prevista + timedelta(minutes=40), 15, 20)
    assert dentro["atrasou"] is False
    assert fora == {"atrasou": True, "minutos": 40, "valor": 20.0}


def test_credito_zera_o_valor_e_baixa_um():
    assert aplicar_credito(3, 65)["valor"] == 0
    assert aplicar_credito(3, 65)["saldo_restante"] == 2
    assert aplicar_credito(0, 65)["usou"] is False


def test_diaria_de_feriado_entra_na_conta():
    feriados = {date(2026, 11, 2): "Finados"}
    linhas = montar_diarias(date(2026, 10, 31), date(2026, 11, 3), 150, 225, feriados)
    assert [l["data"] for l in linhas] == [date(2026, 10, 31), date(2026, 11, 1), date(2026, 11, 2)]
    assert linhas[2]["valor"] == 225
    assert linhas[2]["feriado"] == "Finados"
    assert sum(l["valor"] for l in linhas) == 525


def test_checkout_atrasado_cobra_noite_extra():
    linhas = montar_diarias(date(2026, 11, 1), date(2026, 11, 4), 80, 120, {})
    assert len(linhas) == 3


def test_noites_vazias_quando_checkout_nao_passa_da_entrada():
    assert noites_entre(date(2026, 11, 1), date(2026, 11, 1)) == []


def test_busca_antes_do_fim_do_servico_nao_passa():
    inicio = datetime(2026, 10, 31, 14, 0)
    with pytest.raises(RegraNegocio):
        montar_janela(inicio, inicio + timedelta(minutes=20), 40)


def test_dinheiro_esperado_ignora_pix():
    assert dinheiro_esperado(100, {"pix": 80, "dinheiro": 50, "debito": 30}) == 150

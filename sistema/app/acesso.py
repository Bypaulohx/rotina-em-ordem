from __future__ import annotations

RECEPCAO = {"painel", "mapa", "agenda", "vendas", "pets", "caixas", "whatsapp"}
TOSADOR = {"painel", "mapa", "agenda", "pets", "boletins", "lembretes"}
VETERINARIO = {"agenda", "pets", "boletins", "prontuario", "lembretes"}
ESTOQUISTA = {"vendas", "pets", "catalogo", "estoque"}
GERENTE = {
    "painel",
    "mapa",
    "agenda",
    "vendas",
    "pets",
    "boletins",
    "lembretes",
    "catalogo",
    "estoque",
    "financeiro",
    "indicadores",
    "whatsapp",
    "ponto",
}

PAPEIS = {
    "admin": None,
    "gerente": GERENTE,
    "recepcao": RECEPCAO,
    "equipe": RECEPCAO,
    "tosador": TOSADOR,
    "veterinario": VETERINARIO,
    "estoquista": ESTOQUISTA,
}

ROTULOS = {
    "admin": "Dono",
    "gerente": "Gerência",
    "recepcao": "Recepção",
    "equipe": "Recepção",
    "tosador": "Banho e tosa",
    "veterinario": "Veterinário",
    "estoquista": "Estoque",
}

PREFIXOS = (
    ("/api/admin", "admin"),
    ("/api/ponto", "ponto"),
    ("/api/indicadores", "indicadores"),
    ("/api/financeiro", "financeiro"),
    ("/api/despesas", "financeiro"),
    ("/api/contas", "financeiro"),
    ("/api/fornecedores", "financeiro"),
    ("/api/caixas", "caixas"),
    ("/api/pdv", "vendas"),
    ("/api/vendas", "vendas"),
    ("/api/pacotes", "vendas"),
    ("/api/whatsapp", "whatsapp"),
    ("/api/estoque", "estoque"),
    ("/api/produtos/codigo", "vendas"),
    ("/api/produtos", "estoque"),
    ("/api/prontuario", "prontuario"),
    ("/api/boletins", "boletins"),
    ("/api/lembretes", "lembretes"),
    ("/api/painel", "painel"),
    ("/api/mapa", "mapa"),
    ("/api/agenda", "agenda"),
    ("/api/agendamentos", "agenda"),
    ("/api/hospedagens", "agenda"),
    ("/api/encaixes", "agenda"),
    ("/api/simulacoes", "agenda"),
    ("/api/loja/catalogo", "catalogo"),
)


def permitido(papel: str | None, recurso: str) -> bool:
    cargo = papel or "admin"
    if cargo == "admin":
        return True
    return recurso in PAPEIS.get(cargo, RECEPCAO)


def recurso_da_rota(path: str) -> str | None:
    if path.startswith("/api/whatsapp/webhook"):
        return None
    for prefixo, recurso in PREFIXOS:
        if path == prefixo or path.startswith(prefixo + "/"):
            return recurso
    return None

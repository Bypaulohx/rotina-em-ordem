from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(80))
    login: Mapped[str] = mapped_column(String(40), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(120))
    papel: Mapped[str] = mapped_column(String(20), default="equipe")
    matricula: Mapped[str] = mapped_column(String(20), default="")
    pis: Mapped[str] = mapped_column(String(12), default="")


class Sessao(Base):
    __tablename__ = "sessoes"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    expira_em: Mapped[datetime] = mapped_column(DateTime)


class ClienteSessao(Base):
    __tablename__ = "sessoes_cliente"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    expira_em: Mapped[datetime] = mapped_column(DateTime)


class ConfigLoja(Base):
    __tablename__ = "config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tolerancia_busca_min: Mapped[int] = mapped_column(Integer, default=15)
    valor_atraso: Mapped[float] = mapped_column(Float, default=20)
    whatsapp: Mapped[str] = mapped_column(String(20), default="")
    whatsapp_token: Mapped[str] = mapped_column(String(64), default="")


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    telefone: Mapped[str] = mapped_column(String(30), default="")
    cep: Mapped[str] = mapped_column(String(8), default="")
    logradouro: Mapped[str] = mapped_column(String(160), default="")
    bairro: Mapped[str] = mapped_column(String(80), default="")
    cidade: Mapped[str] = mapped_column(String(80), default="")
    uf: Mapped[str] = mapped_column(String(2), default="")
    numero: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    cpf: Mapped[str] = mapped_column(String(11), default="")
    observacoes: Mapped[str] = mapped_column(Text, default="")
    senha_hash: Mapped[str] = mapped_column(String(120), default="")
    pets: Mapped[list[Pet]] = relationship(back_populates="cliente")


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    nome: Mapped[str] = mapped_column(String(80))
    especie: Mapped[str] = mapped_column(String(20), default="cão")
    porte: Mapped[str] = mapped_column(String(1))
    alimentacao: Mapped[str] = mapped_column(Text, default="")
    cuidados: Mapped[str] = mapped_column(Text, default="")
    raca: Mapped[str] = mapped_column(String(80), default="")
    sexo: Mapped[str] = mapped_column(String(20), default="")
    nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    peso: Mapped[float | None] = mapped_column(Float, nullable=True)
    alergias: Mapped[str] = mapped_column(Text, default="")
    doencas: Mapped[str] = mapped_column(Text, default="")
    medicamentos: Mapped[str] = mapped_column(Text, default="")
    comportamento: Mapped[str] = mapped_column(Text, default="")
    emergencia_nome: Mapped[str] = mapped_column(String(80), default="")
    emergencia_telefone: Mapped[str] = mapped_column(String(20), default="")
    foto: Mapped[str] = mapped_column(String(200), default="")
    cliente: Mapped[Cliente] = relationship(back_populates="pets")


class Credito(Base):
    __tablename__ = "creditos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"))
    tipo: Mapped[str] = mapped_column(String(20))
    saldo: Mapped[int] = mapped_column(Integer, default=0)


class MovimentoCredito(Base):
    __tablename__ = "movimentos_credito"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"))
    tipo: Mapped[str] = mapped_column(String(20))
    quantidade: Mapped[int] = mapped_column(Integer)
    motivo: Mapped[str] = mapped_column(String(160))
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Profissional(Base):
    __tablename__ = "profissionais"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(80))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Baia(Base):
    __tablename__ = "baias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(40))
    porte: Mapped[str] = mapped_column(String(1))
    tipo: Mapped[str] = mapped_column(String(10))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    limpeza_desde: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Servico(Base):
    __tablename__ = "servicos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(80))
    tipo: Mapped[str] = mapped_column(String(20))
    porte: Mapped[str] = mapped_column(String(1))
    duracao_min: Mapped[int] = mapped_column(Integer, default=0)
    preco: Mapped[float] = mapped_column(Float)
    preco_feriado: Mapped[float] = mapped_column(Float, default=0)


class Agendamento(Base):
    __tablename__ = "agendamentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(String(140))
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"))
    servico_id: Mapped[int] = mapped_column(ForeignKey("servicos.id"))
    profissional_id: Mapped[int | None] = mapped_column(ForeignKey("profissionais.id"), nullable=True)
    baia_id: Mapped[int] = mapped_column(ForeignKey("baias.id"))
    inicio: Mapped[datetime] = mapped_column(DateTime)
    fim_servico: Mapped[datetime] = mapped_column(DateTime)
    busca_prevista: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="agendado")
    valor_combinado: Mapped[float] = mapped_column(Float)
    cuidados: Mapped[str] = mapped_column(Text, default="")
    usou_credito: Mapped[bool] = mapped_column(Boolean, default=False)
    venda_id: Mapped[int | None] = mapped_column(ForeignKey("vendas.id"), nullable=True)


class Hospedagem(Base):
    __tablename__ = "hospedagens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"))
    baia_id: Mapped[int] = mapped_column(ForeignKey("baias.id"))
    entrada: Mapped[date] = mapped_column(Date)
    checkout_previsto: Mapped[date] = mapped_column(Date)
    checkout_real: Mapped[date | None] = mapped_column(Date, nullable=True)
    valor_diaria: Mapped[float] = mapped_column(Float)
    valor_feriado: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="hospedada")
    cuidados: Mapped[str] = mapped_column(Text, default="")
    venda_id: Mapped[int | None] = mapped_column(ForeignKey("vendas.id"), nullable=True)


class Encaixe(Base):
    __tablename__ = "encaixes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"))
    servico_id: Mapped[int] = mapped_column(ForeignKey("servicos.id"))
    dia: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="aguardando")


class Caixa(Base):
    __tablename__ = "caixas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(80))
    aberto_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    fechado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    saldo_inicial: Mapped[float] = mapped_column(Float, default=0)
    saldo_informado: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="aberto")
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    fechado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)


class MovimentoCaixa(Base):
    __tablename__ = "movimentos_caixa"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    caixa_id: Mapped[int] = mapped_column(ForeignKey("caixas.id"))
    tipo: Mapped[str] = mapped_column(String(20))
    valor: Mapped[float] = mapped_column(Float)
    motivo: Mapped[str] = mapped_column(String(160), default="")
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Venda(Base):
    __tablename__ = "vendas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero: Mapped[int] = mapped_column(Integer)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    caixa_id: Mapped[int] = mapped_column(ForeignKey("caixas.id"))
    status: Mapped[str] = mapped_column(String(20), default="paga")
    forma: Mapped[str] = mapped_column(String(20))
    total: Mapped[float] = mapped_column(Float, default=0)
    criada_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    observacao: Mapped[str] = mapped_column(Text, default="")
    pet_id: Mapped[int | None] = mapped_column(ForeignKey("pets.id"), nullable=True)
    desconto: Mapped[float] = mapped_column(Float, default=0)
    acrescimo: Mapped[float] = mapped_column(Float, default=0)
    itens: Mapped[list[ItemVenda]] = relationship(back_populates="venda")
    pagamentos: Mapped[list["Pagamento"]] = relationship(back_populates="venda")


class Pagamento(Base):
    __tablename__ = "pagamentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venda_id: Mapped[int] = mapped_column(ForeignKey("vendas.id"))
    forma: Mapped[str] = mapped_column(String(20))
    valor: Mapped[float] = mapped_column(Float)
    recebido: Mapped[float] = mapped_column(Float, default=0)
    troco: Mapped[float] = mapped_column(Float, default=0)
    parcelas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    venda: Mapped[Venda] = relationship(back_populates="pagamentos")


class ItemVenda(Base):
    __tablename__ = "itens_venda"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venda_id: Mapped[int] = mapped_column(ForeignKey("vendas.id"))
    descricao: Mapped[str] = mapped_column(String(180))
    valor: Mapped[float] = mapped_column(Float)
    produto_id: Mapped[int | None] = mapped_column(ForeignKey("produtos.id"), nullable=True)
    quantidade: Mapped[int] = mapped_column(Integer, default=1)
    gramas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    venda: Mapped[Venda] = relationship(back_populates="itens")


class Feriado(Base):
    __tablename__ = "feriados"

    data: Mapped[date] = mapped_column(Date, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    ano: Mapped[int] = mapped_column(Integer)


class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(80))
    preco: Mapped[float] = mapped_column(Float)
    estoque: Mapped[int] = mapped_column(Integer, default=0)
    minimo: Mapped[int] = mapped_column(Integer, default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    codigo_barras: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    categoria: Mapped[str] = mapped_column(String(40), default="")
    marca: Mapped[str] = mapped_column(String(40), default="")
    custo: Mapped[float] = mapped_column(Float, default=0)
    validade: Mapped[date | None] = mapped_column(Date, nullable=True)
    fornecedor_id: Mapped[int | None] = mapped_column(ForeignKey("fornecedores.id"), nullable=True)
    unidade: Mapped[str] = mapped_column(String(8), default="un")


class MovimentoEstoque(Base):
    __tablename__ = "movimentos_estoque"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"))
    quantidade: Mapped[int] = mapped_column(Integer)
    motivo: Mapped[str] = mapped_column(String(160), default="")
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class NotaProntuario(Base):
    __tablename__ = "prontuario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    texto: Mapped[str] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Lembrete(Base):
    __tablename__ = "lembretes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    texto: Mapped[str] = mapped_column(String(200))
    quando: Mapped[datetime] = mapped_column(DateTime)
    pet_id: Mapped[int | None] = mapped_column(ForeignKey("pets.id"), nullable=True)
    feito: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Despesa(Base):
    __tablename__ = "despesas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    descricao: Mapped[str] = mapped_column(String(160))
    valor: Mapped[float] = mapped_column(Float)
    data: Mapped[date] = mapped_column(Date)
    categoria: Mapped[str] = mapped_column(String(40), default="loja")
    status: Mapped[str] = mapped_column(String(20), default="paga")
    vencimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)


class Atividade(Base):
    __tablename__ = "atividades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    acao: Mapped[str] = mapped_column(String(180))
    detalhe: Mapped[str] = mapped_column(String(240), default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class MensagemWhatsapp(Base):
    __tablename__ = "mensagens_whatsapp"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telefone: Mapped[str] = mapped_column(String(20), default="")
    texto: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    detalhe: Mapped[str] = mapped_column(Text, default="")
    agendamento_id: Mapped[int | None] = mapped_column(ForeignKey("agendamentos.id"), nullable=True)
    recebida_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Fornecedor(Base):
    __tablename__ = "fornecedores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    telefone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")


class PacoteContratado(Base):
    __tablename__ = "pacotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"))
    nome: Mapped[str] = mapped_column(String(80))
    tipo: Mapped[str] = mapped_column(String(20))
    total: Mapped[int] = mapped_column(Integer)
    saldo: Mapped[int] = mapped_column(Integer)
    valor: Mapped[float] = mapped_column(Float)
    validade: Mapped[date | None] = mapped_column(Date, nullable=True)
    venda_id: Mapped[int | None] = mapped_column(ForeignKey("vendas.id"), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Pesagem(Base):
    __tablename__ = "pesagens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"))
    peso: Mapped[float] = mapped_column(Float)
    quando: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Vacina(Base):
    __tablename__ = "vacinas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"))
    nome: Mapped[str] = mapped_column(String(80))
    aplicada_em: Mapped[date] = mapped_column(Date)
    proxima: Mapped[date | None] = mapped_column(Date, nullable=True)


class NotificacaoLida(Base):
    __tablename__ = "notificacoes_lidas"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    chave: Mapped[str] = mapped_column(String(80), primary_key=True)
    lida_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class MarcacaoPonto(Base):
    __tablename__ = "marcacoes_ponto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nsr: Mapped[str] = mapped_column(String(20))
    pis: Mapped[str] = mapped_column(String(12))
    marcada_em: Mapped[datetime] = mapped_column(DateTime)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    origem: Mapped[str] = mapped_column(String(40), default="afd")
    sincronizacao_id: Mapped[int | None] = mapped_column(ForeignKey("sincronizacoes_ponto.id"), nullable=True)


class SincronizacaoPonto(Base):
    __tablename__ = "sincronizacoes_ponto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    origem: Mapped[str] = mapped_column(String(40))
    recebidas: Mapped[int] = mapped_column(Integer, default=0)
    novas: Mapped[int] = mapped_column(Integer, default=0)
    falha: Mapped[str] = mapped_column(Text, default="")
    criada_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PedidoLoja(Base):
    __tablename__ = "pedidos_loja"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    status: Mapped[str] = mapped_column(String(20), default="reservado")
    total: Mapped[float] = mapped_column(Float, default=0)
    entrega: Mapped[str] = mapped_column(String(20), default="retirada")
    criada_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    venda_id: Mapped[int | None] = mapped_column(ForeignKey("vendas.id"), nullable=True)


class ItemPedido(Base):
    __tablename__ = "itens_pedido"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos_loja.id"))
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"))
    quantidade: Mapped[int] = mapped_column(Integer)
    preco: Mapped[float] = mapped_column(Float)

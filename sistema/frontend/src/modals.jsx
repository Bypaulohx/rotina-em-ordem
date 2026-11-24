import { useEffect, useMemo, useRef, useState } from "react";
import { FORMAS, calcularBusca, diaMes, isoDate, isoLocal, mascaraCep, mascaraCpf, mascaraMoeda, mascaraTelefone, moeda, moedaParaNumero, petPorId, proximaHora } from "./format.js";

function Forma({ value, onChange, id }) {
  return (
    <select id={id} value={value} onChange={(evento) => onChange(evento.target.value)}>
      {FORMAS.map(([forma, nome]) => <option key={forma} value={forma}>{nome}</option>)}
    </select>
  );
}

function Acoes({ onClose, children }) {
  return (
    <div className="dialog-acoes">
      <button className="btn ghost" type="button" onClick={onClose}>Cancelar</button>
      {children}
    </div>
  );
}

export function AgendamentoModal({ prefill = {}, catalogo, pessoas, api, onClose, onSalvo, onFila }) {
  const achado = prefill.pet_id ? petPorId(pessoas, prefill.pet_id) : null;
  const inicioPadrao = prefill.inicio || isoLocal(proximaHora());
  const buscaPadrao = prefill.busca || calcularBusca(inicioPadrao, 50);
  const checkoutPadrao = new Date();
  checkoutPadrao.setDate(checkoutPadrao.getDate() + 2);

  const [tipo, setTipo] = useState("salao");
  const [clienteId, setClienteId] = useState(achado ? String(achado.cliente.id) : "");
  const [petId, setPetId] = useState(prefill.pet_id ? String(prefill.pet_id) : "");
  const [servicoId, setServicoId] = useState("");
  const [inicio, setInicio] = useState(inicioPadrao);
  const [busca, setBusca] = useState(buscaPadrao);
  const [entrada, setEntrada] = useState(prefill.entrada || isoDate(new Date()));
  const [checkout, setCheckout] = useState(prefill.checkout || isoDate(checkoutPadrao));
  const [valor, setValor] = useState("");
  const [profissionalId, setProfissionalId] = useState(prefill.profissional_id ? String(prefill.profissional_id) : "");
  const [titulo, setTitulo] = useState("");
  const [cuidados, setCuidados] = useState("");
  const [sim, setSim] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const sujo = useRef({ valor: false, titulo: false, cuidados: false, busca: Boolean(prefill.busca) });

  const cliente = pessoas.find((item) => String(item.id) === String(clienteId));
  const pet = cliente?.pets.find((item) => String(item.id) === String(petId));
  const lista = useMemo(() => {
    if (!pet) return [];
    return catalogo.servicos.filter((servico) => {
      if (servico.porte !== pet.porte) return false;
      return tipo === "hotel" ? servico.tipo === "hotel" : servico.tipo !== "hotel";
    });
  }, [catalogo, pet, tipo]);
  const servico = lista.find((item) => String(item.id) === String(servicoId));

  useEffect(() => {
    if (!lista.length) {
      if (servicoId) setServicoId("");
      return;
    }
    if (!lista.some((item) => String(item.id) === String(servicoId))) setServicoId(String(lista[0].id));
  }, [lista, servicoId]);

  useEffect(() => {
    if (!pet || !servico) return;
    if (!sujo.current.valor) setValor(String(servico.preco));
    if (!sujo.current.titulo) setTitulo(`${servico.nome} — ${pet.nome}`);
    if (!sujo.current.cuidados) setCuidados([pet.alimentacao, pet.cuidados].filter(Boolean).join(" "));
  }, [pet, servico]);

  useEffect(() => {
    if (tipo !== "salao" || !servico || sujo.current.busca || !inicio) return;
    const proxima = calcularBusca(inicio, servico.duracao_min);
    setBusca((atual) => (atual === proxima ? atual : proxima));
  }, [tipo, servico, inicio]);

  useEffect(() => {
    const incompleto = !petId || !servicoId
      || (tipo === "hotel" && (!entrada || !checkout))
      || (tipo === "salao" && (!inicio || !busca));
    if (incompleto) {
      setSim(null);
      return undefined;
    }
    let vivo = true;
    const timer = setTimeout(async () => {
      try {
        const corpoHotel = {
          pet_id: Number(petId),
          entrada,
          checkout,
          valor_diaria: valor === "" ? null : Number(valor),
        };
        const corpoSalao = {
          pet_id: Number(petId),
          servico_id: Number(servicoId),
          inicio,
          busca,
          profissional_id: profissionalId ? Number(profissionalId) : null,
          valor_combinado: valor === "" ? null : Number(valor),
        };
        const data = tipo === "hotel"
          ? await api("/api/simulacoes/hotel", { method: "POST", body: corpoHotel })
          : await api("/api/simulacoes/salao", { method: "POST", body: corpoSalao });
        if (vivo) setSim(data);
      } catch (erro) {
        if (vivo && erro.status !== 401) setSim({ ok: false, mensagem: erro.message, pode_fila: false });
      }
    }, 280);
    return () => {
      vivo = false;
      clearTimeout(timer);
    };
  }, [api, tipo, petId, servicoId, inicio, busca, entrada, checkout, valor, profissionalId]);

  async function salvar(evento) {
    evento.preventDefault();
    setEnviando(true);
    try {
      if (tipo === "hotel") {
        await onSalvo(true, {
          pet_id: Number(petId),
          entrada,
          checkout,
          valor_diaria: valor === "" ? null : Number(valor),
          cuidados,
        });
      } else {
        await onSalvo(false, {
          pet_id: Number(petId),
          servico_id: Number(servicoId),
          inicio,
          busca,
          profissional_id: profissionalId ? Number(profissionalId) : null,
          valor_combinado: valor === "" ? null : Number(valor),
          titulo,
          cuidados,
        });
      }
    } finally {
      setEnviando(false);
    }
  }

  const diarias = sim?.diarias || [];
  return (
    <>
      <p className="kicker">Cadastro</p>
      <h2>Novo agendamento</h2>
      <form onSubmit={salvar}>
        <div className="tipo-escolha" style={{ marginBottom: 14 }}>
          <label><input type="radio" name="tipo" checked={tipo === "salao"} onChange={() => setTipo("salao")} /> Banho e tosa</label>
          <label><input type="radio" name="tipo" checked={tipo === "hotel"} onChange={() => setTipo("hotel")} /> Hospedagem</label>
        </div>
        <div className="form-grid">
          <label className="field"><span>Título</span><input value={titulo} placeholder="Ex.: Banho da Mel" onChange={(evento) => { sujo.current.titulo = true; setTitulo(evento.target.value); }} /></label>
          <label className="field">
            <span>Cliente</span>
            <select value={clienteId} onChange={(evento) => { setClienteId(evento.target.value); setPetId(""); }}>
              <option value="">Selecionar cliente</option>
              {pessoas.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Pet</span>
            <select value={petId} onChange={(evento) => setPetId(evento.target.value)}>
              <option value="">Selecionar pet</option>
              {(cliente?.pets || []).map((item) => <option key={item.id} value={item.id}>{item.nome} · porte {item.porte}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Serviço compatível</span>
            <select value={servicoId} onChange={(evento) => setServicoId(evento.target.value)}>
              {lista.map((item) => <option key={item.id} value={item.id}>{item.nome} · {moeda(item.preco)}</option>)}
            </select>
          </label>
          {tipo === "salao" ? (
            <>
              <label className="field"><span>Chegada</span><input type="datetime-local" value={inicio} onChange={(evento) => setInicio(evento.target.value)} /></label>
              <label className="field"><span>Hora da busca</span><input type="datetime-local" value={busca} onChange={(evento) => { sujo.current.busca = true; setBusca(evento.target.value); }} /></label>
            </>
          ) : (
            <>
              <label className="field"><span>Entrada</span><input type="date" value={entrada} onChange={(evento) => setEntrada(evento.target.value)} /></label>
              <label className="field"><span>Checkout</span><input type="date" value={checkout} onChange={(evento) => setCheckout(evento.target.value)} /></label>
            </>
          )}
          <label className="field"><span>Valor combinado (R$)</span><input type="number" min="0" step="0.01" value={valor} onChange={(evento) => { sujo.current.valor = true; setValor(evento.target.value); }} /></label>
          {tipo === "salao" ? (
            <label className="field">
              <span>Profissional</span>
              <select value={profissionalId} onChange={(evento) => setProfissionalId(evento.target.value)}>
                <option value="">Quem estiver livre</option>
                {catalogo.profissionais.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}
              </select>
            </label>
          ) : null}
          <label className="field full">
            <span>Cuidados, alimentação ou observações</span>
            <textarea value={cuidados} onChange={(evento) => { sujo.current.cuidados = true; setCuidados(evento.target.value); }} />
          </label>
        </div>
        <div className={`sim full ${sim?.ok ? "ok" : sim ? "no" : ""}`}>
          {sim ? sim.mensagem : "Escolha o pet. O serviço compatível vem do porte."}
          {diarias.length ? (
            <ul className="linhas">
              {diarias.map((linha) => (
                <li key={linha.data}>{diaMes(linha.data)} · {moeda(linha.valor)}{linha.feriado ? ` · ${linha.feriado}` : ""}</li>
              ))}
            </ul>
          ) : null}
        </div>
        <Acoes onClose={onClose}>
          {tipo === "salao" && sim?.pode_fila ? (
            <button className="btn ghost" type="button" onClick={() => onFila({ pet_id: Number(petId), servico_id: Number(servicoId), dia: inicio.slice(0, 10) })}>Colocar na fila de hoje</button>
          ) : null}
          <button className="btn" type="submit" disabled={!sim?.ok || enviando}>Salvar</button>
        </Acoes>
      </form>
    </>
  );
}

export function BuscaModal({ agendamento, onClose, onSalvo }) {
  const [forma, setForma] = useState("pix");
  const [incluir, setIncluir] = useState(Boolean(agendamento.atraso?.atrasou));
  const atraso = agendamento.atraso?.atrasou;
  return (
    <>
      <p className="kicker">Busca</p>
      <h2>{agendamento.pet} está pronto</h2>
      <p className="sub">{agendamento.cuidados || "Sem cuidado anotado para o tutor."}</p>
      <form onSubmit={(evento) => { evento.preventDefault(); onSalvo({ forma, incluir_atraso: atraso ? incluir : false }); }}>
        <p>{agendamento.creditos > 0 ? `Este atendimento sai do pacote. Restam ${agendamento.creditos}.` : `Valor combinado: ${moeda(agendamento.valor_combinado)}.`}</p>
        {atraso ? (
          <label className="field">
            <span>
              <input type="checkbox" checked={incluir} onChange={(evento) => setIncluir(evento.target.checked)} />
              {` Incluir atraso de ${agendamento.atraso.minutos} min (${moeda(agendamento.atraso.valor)})`}
            </span>
          </label>
        ) : <p className="muted">A busca está dentro da tolerância.</p>}
        <label className="field"><span>Pagamento do que for em dinheiro, Pix ou cartão</span><Forma value={forma} onChange={setForma} /></label>
        <Acoes onClose={onClose}><button className="btn" type="submit">Receber e liberar a baia</button></Acoes>
      </form>
    </>
  );
}

export function CheckoutModal({ hospedagem, onClose, onSalvo }) {
  const [data, setData] = useState(hospedagem.checkout_previsto);
  const [forma, setForma] = useState("pix");
  const linhas = hospedagem.diarias || [];
  return (
    <>
      <p className="kicker">Hotel</p>
      <h2>Checkout de {hospedagem.pet}</h2>
      <p className="sub">{hospedagem.cuidados || ""}</p>
      <ul className="linhas">
        {linhas.map((linha) => <li key={linha.data}>{diaMes(linha.data)} · {moeda(linha.valor)}{linha.feriado ? ` · ${linha.feriado}` : ""}</li>)}
      </ul>
      <form onSubmit={(evento) => { evento.preventDefault(); onSalvo({ forma, checkout: data }); }}>
        <label className="field"><span>Data do checkout</span><input type="date" value={data} onChange={(evento) => setData(evento.target.value)} /></label>
        <label className="field"><span>Pagamento</span><Forma value={forma} onChange={setForma} /></label>
        <p className="muted">Se a data passar do combinado, a diária extra entra na venda. Feriado continua com o valor de feriado.</p>
        <Acoes onClose={onClose}><button className="btn" type="submit">Lançar checkout</button></Acoes>
      </form>
    </>
  );
}

export function AbrirCaixaModal({ operador, onClose, onSalvo }) {
  const [saldo, setSaldo] = useState("0,00");
  return (
    <>
      <p className="kicker">Turno</p>
      <h2>Abrir caixa</h2>
      <p>O turno fica no nome de <strong>{operador}</strong>.</p>
      <form onSubmit={(evento) => { evento.preventDefault(); onSalvo({ saldo_inicial: moedaParaNumero(saldo) }); }}>
        <label className="field"><span>Dinheiro inicial na gaveta</span><input inputMode="numeric" value={saldo} onChange={(evento) => setSaldo(mascaraMoeda(evento.target.value))} /></label>
        <Acoes onClose={onClose}><button className="btn" type="submit">Abrir</button></Acoes>
      </form>
    </>
  );
}

export function FecharCaixaModal({ caixa, onClose, onSalvo, onSair }) {
  const [saldo, setSaldo] = useState("0,00");
  const [resultado, setResultado] = useState(null);
  if (resultado) {
    return (
      <>
        <p className="kicker">Conferência</p>
        <h2>Caixa fechado</h2>
        <p>Você contou <strong>{moeda(resultado.saldo_informado)}</strong>.</p>
        <p>O dinheiro esperado na gaveta era <strong>{moeda(resultado.esperado_em_dinheiro)}</strong>.</p>
        <p>Diferença: <strong>{moeda(resultado.diferenca)}</strong>.</p>
        <Acoes onClose={onSair}><button className="btn" type="button" onClick={onSair}>Encerrar sessão</button></Acoes>
      </>
    );
  }
  return (
    <>
      <p className="kicker">Conferência cega</p>
      <h2>Fechar {caixa.nome}</h2>
      <p className="muted">Conte o dinheiro da gaveta sem consultar o valor esperado. Pix e cartão não entram nessa conta.</p>
      <form onSubmit={(evento) => {
        evento.preventDefault();
        Promise.resolve(onSalvo({ saldo_informado: moedaParaNumero(saldo) })).then((caixaFechado) => {
          if (caixaFechado) setResultado(caixaFechado);
        });
      }}>
        <label className="field"><span>Saldo contado</span><input inputMode="numeric" required value={saldo} onChange={(evento) => setSaldo(mascaraMoeda(evento.target.value))} /></label>
        <Acoes onClose={onClose}><button className="btn" type="submit">Conferir</button></Acoes>
      </form>
    </>
  );
}

export function VendaModal({ pessoas, api, onClose, onSalvo, onErro }) {
  const [clienteId, setClienteId] = useState(pessoas[0] ? String(pessoas[0].id) : "");
  const [petId, setPetId] = useState("");
  const [carrinho, setCarrinho] = useState([]);
  const [aviso, setAviso] = useState("");
  const [busca, setBusca] = useState("");
  const [achados, setAchados] = useState([]);
  const [desconto, setDesconto] = useState("0,00");
  const [acrescimo, setAcrescimo] = useState("0,00");
  const [observacao, setObservacao] = useState("");
  const [partes, setPartes] = useState([{ forma: "dinheiro", valor: "", recebido: "" }]);
  const [suspensas, setSuspensas] = useState([]);
  const [vendaId, setVendaId] = useState(null);
  const [comprovante, setComprovante] = useState(null);
  const leitor = useRef(null);
  const cliente = pessoas.find((item) => String(item.id) === clienteId);
  const bruto = carrinho.reduce((soma, item) => soma + (item.gramas ? item.preco * item.gramas / 1000 : item.preco * item.quantidade), 0);
  const liquido = Math.max(0, bruto - moedaParaNumero(desconto) + moedaParaNumero(acrescimo));

  useEffect(() => { leitor.current?.focus(); }, [carrinho.length, comprovante]);
  useEffect(() => {
    api("/api/pdv/suspensas").then(setSuspensas).catch(() => setSuspensas([]));
  }, [api]);

  function porProduto(produto, extra = {}) {
    setCarrinho((atual) => {
      if (produto.unidade === "kg" || extra.gramas) {
        const gramas = extra.gramas || 0;
        if (!gramas) return atual;
        return [...atual, { chave: `${produto.id}-${gramas}-${atual.length}`, id: produto.id, nome: produto.nome, preco: produto.preco, codigo: produto.codigo_barras, unidade: "kg", gramas, quantidade: 1, estoque: produto.estoque }];
      }
      const existe = atual.find((item) => item.id === produto.id && item.unidade !== "kg");
      if (existe) return atual.map((item) => item === existe ? { ...item, quantidade: item.quantidade + 1 } : item);
      return [...atual, { chave: String(produto.id), id: produto.id, nome: produto.nome, preco: produto.preco, codigo: produto.codigo_barras, unidade: "un", quantidade: 1, estoque: produto.estoque }];
    });
  }

  async function incluir(codigo) {
    const limpo = codigo.trim();
    if (!limpo) return;
    try {
      const produto = await api(`/api/produtos/codigo/${encodeURIComponent(limpo)}`);
      setAviso("");
      porProduto(produto, { gramas: produto.gramas });
    } catch (erro) {
      setAviso(erro.message);
      onErro?.(erro.message);
    }
  }

  function corpo() {
    return {
      cliente_id: Number(clienteId),
      forma: partes[0]?.forma || "dinheiro",
      venda_id: vendaId,
      pet_id: petId ? Number(petId) : null,
      observacao,
      desconto: moedaParaNumero(desconto),
      acrescimo: moedaParaNumero(acrescimo),
      itens: carrinho.map((item) => ({ produto_id: item.id, codigo: item.codigo, quantidade: item.quantidade, gramas: item.gramas || null })),
      pagamentos: partes.map((parte) => ({
        forma: parte.forma,
        valor: partes.length === 1 ? liquido : moedaParaNumero(parte.valor),
        recebido: parte.forma === "dinheiro" ? (moedaParaNumero(parte.recebido) || (partes.length === 1 ? liquido : moedaParaNumero(parte.valor))) : moedaParaNumero(parte.valor),
        parcelas: parte.forma === "credito" ? Number(parte.parcelas || 1) : null,
      })),
    };
  }

  if (comprovante) {
    const troco = (comprovante.pagamentos || []).reduce((soma, parte) => soma + (parte.troco || 0), 0);
    return (
      <div className="comprovante">
        <p className="kicker">Comprovante</p>
        <h2>Venda {comprovante.numero}</h2>
        <p>{comprovante.cliente}{comprovante.pet ? ` · ${comprovante.pet}` : ""}</p>
        {(comprovante.itens || []).map((item, indice) => <div className="item" key={indice}><span>{item.descricao}</span><strong>{moeda(item.valor)}</strong></div>)}
        <p>Total <strong>{moeda(comprovante.total)}</strong></p>
        {(comprovante.pagamentos || []).map((parte, indice) => <p key={indice}>{parte.forma_rotulo} {moeda(parte.valor)}{parte.parcelas ? ` · ${parte.parcelas}x` : ""}</p>)}
        {troco ? <p>Troco <strong>{moeda(troco)}</strong></p> : null}
        <Acoes onClose={onClose}><button className="btn ghost" type="button" onClick={() => window.print()}>Imprimir</button><button className="btn" type="button" onClick={onClose}>Nova venda</button></Acoes>
      </div>
    );
  }

  return (
    <div className="pdv">
      <p className="kicker">Frente de caixa</p>
      <h2>Venda</h2>
      <form onSubmit={(evento) => {
        evento.preventDefault();
        if (!carrinho.length) return;
        Promise.resolve(onSalvo(corpo())).then((venda) => { if (venda) setComprovante(venda); });
      }}>
        <div className="pdv-grade">
          <div>
            <label className="field">
              <span>Código de barras</span>
              <input ref={leitor} autoFocus placeholder="Leitor ou código" onKeyDown={(evento) => {
                if (evento.key !== "Enter") return;
                evento.preventDefault();
                const codigo = evento.currentTarget.value;
                evento.currentTarget.value = "";
                incluir(codigo);
              }} />
            </label>
            <label className="field">
              <span>Buscar produto</span>
              <input value={busca} placeholder="Nome" onChange={(evento) => {
                const texto = evento.target.value;
                setBusca(texto);
                if (texto.trim().length < 2) { setAchados([]); return; }
                api(`/api/pdv/produtos?q=${encodeURIComponent(texto)}`).then(setAchados).catch(() => setAchados([]));
              }} />
            </label>
            {achados.length ? <div className="lista">{achados.map((produto) => (
              <button className="linkish" type="button" key={produto.id} onClick={() => {
                if (produto.unidade === "kg") {
                  const gramas = Number(window.prompt("Peso em gramas") || 0);
                  if (gramas > 0) porProduto(produto, { gramas });
                } else porProduto(produto);
                setBusca("");
                setAchados([]);
                leitor.current?.focus();
              }}>{produto.nome} · {moeda(produto.preco)}{produto.unidade === "kg" ? "/kg" : ""} · estoque {produto.estoque}</button>
            ))}</div> : null}
            {aviso ? <p className="alerta">{aviso}</p> : null}
          </div>
          <div>
            <div className="lista">
              {carrinho.length ? carrinho.map((item) => (
                <div className="item" key={item.chave}>
                  <div>
                    <strong>{item.nome}</strong>
                    <small>{item.unidade === "kg" ? `${(item.gramas / 1000).toFixed(3)} kg · estoque ${item.estoque} g` : `${item.quantidade} × ${moeda(item.preco)} · estoque ${item.estoque}`}</small>
                  </div>
                  {item.unidade === "kg" ? null : (
                    <span className="qtd">
                      <button type="button" onClick={() => setCarrinho((atual) => atual.flatMap((linha) => linha.chave !== item.chave ? [linha] : linha.quantidade <= 1 ? [] : [{ ...linha, quantidade: linha.quantidade - 1 }]))}>−</button>
                      <button type="button" onClick={() => setCarrinho((atual) => atual.map((linha) => linha.chave === item.chave ? { ...linha, quantidade: linha.quantidade + 1 } : linha))}>+</button>
                    </span>
                  )}
                  <strong>{moeda(item.unidade === "kg" ? item.preco * item.gramas / 1000 : item.preco * item.quantidade)}</strong>
                  <button type="button" className="btn pequeno ghost" onClick={() => setCarrinho((atual) => atual.filter((linha) => linha.chave !== item.chave))}>Tirar</button>
                </div>
              )) : <p className="muted">Passe o leitor para começar.</p>}
            </div>
            <p className="pdv-total">Total {moeda(liquido)}</p>
          </div>
        </div>
        <div className="form-grid">
          <label className="field"><span>Tutor</span>
            <select value={clienteId} onChange={(evento) => { setClienteId(evento.target.value); setPetId(""); }}>
              {pessoas.map((pessoa) => <option key={pessoa.id} value={pessoa.id}>{pessoa.nome}</option>)}
            </select>
          </label>
          <label className="field"><span>Animal</span>
            <select value={petId} onChange={(evento) => setPetId(evento.target.value)}>
              <option value="">Sem animal</option>
              {(cliente?.pets || []).map((pet) => <option key={pet.id} value={pet.id}>{pet.nome}</option>)}
            </select>
          </label>
          <label className="field"><span>Desconto</span><input inputMode="numeric" value={desconto} onChange={(evento) => setDesconto(mascaraMoeda(evento.target.value))} /></label>
          <label className="field"><span>Acréscimo</span><input inputMode="numeric" value={acrescimo} onChange={(evento) => setAcrescimo(mascaraMoeda(evento.target.value))} /></label>
        </div>
        {partes.map((parte, indice) => (
          <div className="form-grid" key={indice}>
            <label className="field"><span>Pagamento {indice + 1}</span><Forma value={parte.forma} onChange={(valor) => setPartes((atual) => atual.map((item, i) => i === indice ? { ...item, forma: valor } : item))} /></label>
            {partes.length > 1 ? <label className="field"><span>Valor</span><input inputMode="numeric" value={parte.valor} onChange={(evento) => setPartes((atual) => atual.map((item, i) => i === indice ? { ...item, valor: mascaraMoeda(evento.target.value) } : item))} /></label> : <span />}
            {parte.forma === "dinheiro" ? <label className="field"><span>Recebido</span><input inputMode="numeric" value={parte.recebido} placeholder={moeda(liquido)} onChange={(evento) => setPartes((atual) => atual.map((item, i) => i === indice ? { ...item, recebido: mascaraMoeda(evento.target.value) } : item))} /></label> : null}
            {parte.forma === "credito" ? <label className="field"><span>Parcelas</span><input inputMode="numeric" value={parte.parcelas || "1"} onChange={(evento) => setPartes((atual) => atual.map((item, i) => i === indice ? { ...item, parcelas: evento.target.value.replace(/\D/g, "") } : item))} /></label> : null}
          </div>
        ))}
        <button className="btn pequeno ghost" type="button" onClick={() => setPartes((atual) => [...atual, { forma: "pix", valor: "", recebido: "" }])}>Dividir pagamento</button>
        <label className="field"><span>Observação</span><input value={observacao} onChange={(evento) => setObservacao(evento.target.value)} /></label>
        {suspensas.length ? <label className="field"><span>Venda suspensa</span>
          <select value={vendaId || ""} onChange={(evento) => setVendaId(evento.target.value ? Number(evento.target.value) : null)}>
            <option value="">Nova venda</option>
            {suspensas.map((venda) => <option key={venda.id} value={venda.id}>#{venda.numero} · {venda.cliente} · {moeda(venda.total)}</option>)}
          </select>
        </label> : null}
        <Acoes onClose={onClose}>
          <button className="btn ghost" type="button" disabled={!carrinho.length} onClick={() => {
            api("/api/pdv/suspender", { method: "POST", body: corpo() }).then(() => { setCarrinho([]); setVendaId(null); api("/api/pdv/suspensas").then(setSuspensas); }).catch((erro) => onErro?.(erro.message));
          }}>Suspender</button>
          <button className="btn" type="submit" disabled={!carrinho.length}>Receber {moeda(liquido)}</button>
        </Acoes>
      </form>
    </div>
  );
}

export function PacoteModal({ pet, onClose, onSalvo }) {
  const [tipo, setTipo] = useState("banho");
  const [quantidade, setQuantidade] = useState("4");
  const [nome, setNome] = useState("Banho — 4 sessões");
  const [valor, setValor] = useState("220");
  const [forma, setForma] = useState("pix");
  const [validade, setValidade] = useState("");

  function atualizarTipo(proximo) {
    setTipo(proximo);
    setNome(`${proximo === "banho" ? "Banho" : "Tosa"} — ${quantidade} sessões`);
  }

  return (
    <>
      <p className="kicker">Pacote</p>
      <h2>Vender pacote</h2>
      <p className="sub">Animal: {pet.nome}. O nome abaixo é o do pacote, não o do pet. O saldo fica neste animal.</p>
      <form onSubmit={(evento) => {
        evento.preventDefault();
        onSalvo({
          pet_id: pet.id,
          tipo,
          quantidade: Number(quantidade),
          valor_total: Number(valor),
          forma,
          nome,
          validade: validade || null,
        });
      }}>
        <label className="field"><span>Nome do pacote</span><input required value={nome} onChange={(evento) => setNome(evento.target.value)} /></label>
        <div className="form-grid">
          <label className="field">
            <span>Serviço incluído</span>
            <select value={tipo} onChange={(evento) => atualizarTipo(evento.target.value)}>
              <option value="banho">Banho</option>
              <option value="tosa">Tosa</option>
            </select>
          </label>
          <label className="field"><span>Sessões</span><input type="number" min="1" value={quantidade} onChange={(evento) => setQuantidade(evento.target.value)} /></label>
          <label className="field"><span>Valor cobrado agora</span><input type="number" min="0.01" step="0.01" value={valor} onChange={(evento) => setValor(evento.target.value)} /></label>
          <label className="field"><span>Validade</span><input type="date" value={validade} onChange={(evento) => setValidade(evento.target.value)} /></label>
          <label className="field"><span>Pagamento</span><Forma value={forma} onChange={setForma} /></label>
        </div>
        <Acoes onClose={onClose}><button className="btn" type="submit">Receber pacote</button></Acoes>
      </form>
    </>
  );
}

export function ClienteModal({ api, onClose, onSalvo, onErro }) {
  const [nome, setNome] = useState("");
  const [telefone, setTelefone] = useState("");
  const [email, setEmail] = useState("");
  const [cpf, setCpf] = useState("");
  const [cep, setCep] = useState("");
  const [cidade, setCidade] = useState("");
  const [logradouro, setLogradouro] = useState("");
  const [numero, setNumero] = useState("");
  const [bairro, setBairro] = useState("");
  const [uf, setUf] = useState("");
  const [petNome, setPetNome] = useState("");
  const [porte, setPorte] = useState("P");
  const [especie, setEspecie] = useState("Cachorro");
  const [raca, setRaca] = useState("");
  const [sexo, setSexo] = useState("");
  const [alimentacao, setAlimentacao] = useState("");
  const [cuidados, setCuidados] = useState("");

  useEffect(() => {
    const digitos = cep.replace(/\D/g, "");
    if (digitos.length !== 8) return undefined;
    let vivo = true;
    const timer = setTimeout(async () => {
      try {
        const endereco = await api(`/api/cep/${digitos}`);
        if (!vivo) return;
        setLogradouro(endereco.logradouro || "");
        setBairro(endereco.bairro || "");
        setCidade(endereco.cidade || "");
        setUf(endereco.uf || "");
      } catch (erro) {
        if (vivo && erro.status !== 401) onErro(erro.message);
      }
    }, 250);
    return () => {
      vivo = false;
      clearTimeout(timer);
    };
  }, [api, cep, onErro]);

  return (
    <>
      <p className="kicker">Cadastro</p>
      <h2>Cliente e pet</h2>
      <form onSubmit={(evento) => {
        evento.preventDefault();
        onSalvo({
          nome, telefone, email, cpf, cep, logradouro, numero, bairro, cidade, uf,
          pet_nome: petNome, porte, especie, raca, sexo, alimentacao, cuidados,
        });
      }}>
        <div className="form-grid">
          <label className="field"><span>Cliente *</span><input required value={nome} onChange={(evento) => setNome(evento.target.value)} /></label>
          <label className="field"><span>Telefone *</span><input required inputMode="tel" placeholder="(00) 00000-0000" value={telefone} onChange={(evento) => setTelefone(mascaraTelefone(evento.target.value))} /></label>
          <label className="field"><span>E-mail</span><input type="email" value={email} onChange={(evento) => setEmail(evento.target.value)} /></label>
          <label className="field"><span>CPF</span><input inputMode="numeric" value={cpf} onChange={(evento) => setCpf(mascaraCpf(evento.target.value))} /></label>
          <label className="field"><span>CEP *</span><input required inputMode="numeric" placeholder="00000-000" value={cep} onChange={(evento) => setCep(mascaraCep(evento.target.value))} /></label>
          <label className="field"><span>Cidade *</span><input required value={cidade} onChange={(evento) => setCidade(evento.target.value)} /></label>
          <label className="field"><span>Endereço *</span><input required value={logradouro} onChange={(evento) => setLogradouro(evento.target.value)} /></label>
          <label className="field"><span>Número</span><input value={numero} onChange={(evento) => setNumero(evento.target.value)} /></label>
          <label className="field"><span>Bairro</span><input value={bairro} onChange={(evento) => setBairro(evento.target.value)} /></label>
          <label className="field"><span>UF</span><input maxLength={2} value={uf} onChange={(evento) => setUf(evento.target.value)} /></label>
          <label className="field"><span>Pet *</span><input required value={petNome} onChange={(evento) => setPetNome(evento.target.value)} /></label>
          <label className="field"><span>Espécie</span>
            <select value={especie} onChange={(evento) => setEspecie(evento.target.value)}>
              {["Cachorro", "Gato", "Peixe", "Ave", "Roedor", "Réptil"].map((item) => <option key={item}>{item}</option>)}
            </select>
          </label>
          <label className="field"><span>Raça</span><input value={raca} onChange={(evento) => setRaca(evento.target.value)} /></label>
          <label className="field"><span>Sexo</span>
            <select value={sexo} onChange={(evento) => setSexo(evento.target.value)}>
              <option value="">Não informado</option>
              <option value="fêmea">Fêmea</option>
              <option value="macho">Macho</option>
            </select>
          </label>
          <label className="field">
            <span>Porte</span>
            <select value={porte} onChange={(evento) => setPorte(evento.target.value)}>
              <option value="P">Pequeno</option>
              <option value="M">Médio</option>
              <option value="G">Grande</option>
            </select>
          </label>
          <label className="field full"><span>Alimentação</span><input value={alimentacao} onChange={(evento) => setAlimentacao(evento.target.value)} /></label>
          <label className="field full"><span>Cuidados</span><textarea value={cuidados} onChange={(evento) => setCuidados(evento.target.value)} /></label>
        </div>
        <Acoes onClose={onClose}><button className="btn" type="submit">Salvar</button></Acoes>
      </form>
    </>
  );
}

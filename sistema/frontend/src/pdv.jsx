import { useEffect, useRef, useState } from "react";
import { mascaraMoeda, moeda, moedaParaNumero } from "./format.js";
import { pode } from "./ui.jsx";

function sigla(nome) {
  const partes = String(nome || "").trim().split(/\s+/).slice(0, 2);
  return partes.map((parte) => parte.slice(0, 1).toUpperCase()).join("") || "•";
}

function estoqueDe(produto) {
  if (produto.unidade === "kg") return `${(produto.estoque / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 3 })} kg`;
  return String(produto.estoque);
}

export default function Frente({ dados, pessoas, me, api, acoes, embutida = false, children = null }) {
  const produtos = dados?.produtos || [];
  const caixa = dados?.caixa || null;
  const suspensas = dados?.suspensas || [];
  const [busca, setBusca] = useState("");
  const [categoria, setCategoria] = useState("");
  const [carrinho, setCarrinho] = useState([]);
  const [clienteId, setClienteId] = useState("");
  const [clienteBusca, setClienteBusca] = useState("");
  const [petId, setPetId] = useState("");
  const [desconto, setDesconto] = useState("0,00");
  const [acrescimo, setAcrescimo] = useState("0,00");
  const [observacao, setObservacao] = useState("");
  const [partes, setPartes] = useState([{ forma: "dinheiro", valor: "", recebido: "", parcelas: "1" }]);
  const [vendaId, setVendaId] = useState(null);
  const [aviso, setAviso] = useState("");
  const [consulta, setConsulta] = useState(null);
  const [soPreco, setSoPreco] = useState(false);
  const [pesoAlvo, setPesoAlvo] = useState(null);
  const [gramasTxt, setGramasTxt] = useState("");
  const [comprovante, setComprovante] = useState(null);
  const [agora, setAgora] = useState(() => new Date());
  const buscaRef = useRef(null);
  const clienteRef = useRef(null);
  const receberRef = useRef(() => {});
  const suspenderRef = useRef(() => {});

  const cliente = pessoas.find((item) => String(item.id) === String(clienteId));
  const bruto = carrinho.reduce((soma, item) => soma + (item.gramas ? item.preco * item.gramas / 1000 : item.preco * item.quantidade), 0);
  const liquido = Math.max(0, Math.round((bruto - moedaParaNumero(desconto) + moedaParaNumero(acrescimo)) * 100) / 100);
  const categorias = [...new Set(produtos.map((item) => item.categoria).filter(Boolean))];
  const termo = busca.trim().toLowerCase();
  const visiveis = produtos.filter((item) => {
    if (categoria && item.categoria !== categoria) return false;
    if (!termo) return true;
    return [item.nome, item.codigo_barras, item.marca, item.categoria, String(item.id)].join(" ").toLowerCase().includes(termo);
  });
  const clientesAchados = clienteBusca.trim().length < 2 ? [] : pessoas.filter((pessoa) => {
    const texto = `${pessoa.nome} ${pessoa.telefone || ""} ${pessoa.cpf || ""}`.toLowerCase();
    return texto.includes(clienteBusca.trim().toLowerCase());
  }).slice(0, 6);

  useEffect(() => {
    const relogio = setInterval(() => setAgora(new Date()), 1000);
    return () => clearInterval(relogio);
  }, []);

  function porProduto(produto, extra = {}) {
    if (!produto || produto.preco <= 0) {
      setAviso("Esse produto não tem preço de venda.");
      return;
    }
    if ((produto.esgotado || produto.estoque < 1) && produto.unidade !== "kg") {
      setAviso(`${produto.nome} está sem estoque.`);
      return;
    }
    if (soPreco && !extra.gramas) {
      setConsulta(produto);
      setAviso("");
      return;
    }
    if (produto.unidade === "kg" || extra.gramas) {
      const gramas = extra.gramas || 0;
      if (!gramas) return;
      const noPedido = carrinho.filter((item) => item.id === produto.id).reduce((soma, item) => soma + (item.gramas || 0), 0);
      if (gramas + noPedido > produto.estoque) {
        setAviso(`${produto.nome} só tem ${estoqueDe(produto)} no estoque.`);
        return;
      }
      setConsulta(null);
      setAviso("");
      setCarrinho((atual) => [...atual, { chave: `${produto.id}-${gramas}-${atual.length}`, id: produto.id, nome: produto.nome, preco: produto.preco, codigo: produto.codigo_barras, unidade: "kg", gramas, quantidade: 1, estoque: produto.estoque }]);
      return;
    }
    const existe = carrinho.find((item) => item.id === produto.id && item.unidade !== "kg");
    if ((existe?.quantidade || 0) + 1 > produto.estoque) {
      setAviso(`${produto.nome} só tem ${produto.estoque} no estoque.`);
      return;
    }
    setConsulta(null);
    setAviso("");
    setCarrinho((atual) => {
      const linha = atual.find((item) => item.id === produto.id && item.unidade !== "kg");
      if (linha) return atual.map((item) => item === linha ? { ...item, quantidade: item.quantidade + 1 } : item);
      return [...atual, { chave: String(produto.id), id: produto.id, nome: produto.nome, preco: produto.preco, codigo: produto.codigo_barras, unidade: "un", quantidade: 1, estoque: produto.estoque }];
    });
  }

  function escolher(produto) {
    if (produto.unidade === "kg") {
      setPesoAlvo(produto);
      setGramasTxt("");
      if (soPreco) setConsulta(produto);
      return;
    }
    porProduto(produto);
    setBusca("");
    buscaRef.current?.focus();
  }

  async function lerCodigo(codigo) {
    const limpo = codigo.trim();
    if (!limpo) return;
    try {
      const produto = await api(`/api/produtos/codigo/${encodeURIComponent(limpo)}`);
      if (soPreco && !produto.gramas) {
        setConsulta(produto);
        setAviso("");
      } else {
        porProduto(produto, { gramas: produto.gramas });
      }
      setBusca("");
    } catch (erro) {
      setAviso(erro.message);
    }
    buscaRef.current?.focus();
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

  async function receber() {
    if (!carrinho.length || !clienteId) return;
    if (!caixa) {
      setAviso("Abra o seu caixa antes de receber.");
      return;
    }
    try {
      const venda = await api("/api/pdv", { method: "POST", body: corpo() });
      setComprovante(venda);
      setCarrinho([]);
      setVendaId(null);
      setObservacao("");
      setDesconto("0,00");
      setAcrescimo("0,00");
      setAviso("");
      await acoes.recarregar();
    } catch (erro) {
      setAviso(erro.message);
    }
  }

  receberRef.current = receber;
  suspenderRef.current = suspender;

  useEffect(() => {
    function noTeclado(evento) {
      if (evento.key === "F2") { evento.preventDefault(); buscaRef.current?.focus(); }
      if (evento.key === "F3") { evento.preventDefault(); clienteRef.current?.focus(); }
      if (evento.key === "F4") {
        evento.preventDefault();
        setCarrinho((atual) => {
          const indice = [...atual].reverse().findIndex((item) => item.unidade !== "kg");
          if (indice < 0) return atual;
          const alvo = atual.length - 1 - indice;
          const item = atual[alvo];
          if (item.quantidade + 1 > item.estoque) return atual;
          return atual.map((linha, i) => i === alvo ? { ...linha, quantidade: linha.quantidade + 1 } : linha);
        });
      }
      if (evento.key === "F6") { evento.preventDefault(); suspenderRef.current(); }
      if (evento.key === "F8") { evento.preventDefault(); setSoPreco((valor) => !valor); }
      if (evento.key === "F10") { evento.preventDefault(); receberRef.current(); }
      if (evento.key === "Escape") {
        setBusca("");
        setConsulta(null);
        setPesoAlvo(null);
      }
    }
    window.addEventListener("keydown", noTeclado);
    return () => window.removeEventListener("keydown", noTeclado);
  }, []);

  async function suspender() {
    if (!carrinho.length || !clienteId) {
      setAviso("Escolha o tutor e pelo menos um item para suspender.");
      return;
    }
    try {
      await api("/api/pdv/suspender", { method: "POST", body: corpo() });
      setCarrinho([]);
      setVendaId(null);
      setAviso("Venda suspensa. O estoque não foi baixado.");
      await acoes.recarregar();
    } catch (erro) {
      setAviso(erro.message);
    }
  }

  function recuperar(venda) {
    setVendaId(venda.id);
    setClienteId(String(venda.cliente_id || ""));
    setClienteBusca("");
    setPetId(venda.pet_id ? String(venda.pet_id) : "");
    setObservacao(venda.observacao || "");
    setDesconto(mascaraMoeda(String(Math.round((venda.desconto || 0) * 100))));
    setAcrescimo(mascaraMoeda(String(Math.round((venda.acrescimo || 0) * 100))));
    const linhas = (venda.itens || []).flatMap((item, indice) => {
      if (!item.produto_id) return [];
      const produto = produtos.find((atual) => atual.id === item.produto_id);
      return [{
        chave: `${item.produto_id}-${indice}`,
        id: item.produto_id,
        nome: produto?.nome || item.descricao,
        preco: produto?.preco ?? item.valor,
        codigo: produto?.codigo_barras || "",
        unidade: item.gramas ? "kg" : (produto?.unidade || "un"),
        gramas: item.gramas,
        quantidade: item.quantidade || 1,
        estoque: produto?.estoque ?? 0,
      }];
    });
    setCarrinho(linhas);
    setComprovante(null);
    setAviso(linhas.length ? "" : "Essa venda suspensa não tem produto para recolocar no pedido.");
  }

  const trocoPrevisto = partes.reduce((soma, parte) => {
    if (parte.forma !== "dinheiro") return soma;
    const valor = partes.length === 1 ? liquido : moedaParaNumero(parte.valor);
    const recebido = moedaParaNumero(parte.recebido);
    return soma + (recebido > valor ? recebido - valor : 0);
  }, 0);

  return (
    <div className="frente">
      <section className="frente-catalogo">
        <header className="frente-topo">
          {embutida ? null : (
            <div>
              <p className="kicker">Frente de caixa</p>
              <h1>Rotina em ordem</h1>
            </div>
          )}
          <p className="muted">{me?.nome} · {caixa ? caixa.nome : "Nenhum caixa aberto"} · {agora.toLocaleString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</p>
          <p className="atalhos">F2 busca · F3 cliente · F4 quantidade · F6 suspender · F8 preço · F10 receber</p>
        </header>
        <div className="frente-busca">
          <input
            ref={buscaRef}
            autoFocus
            value={busca}
            placeholder="Nome, código, marca ou leitor"
            onChange={(evento) => setBusca(evento.target.value)}
            onKeyDown={(evento) => {
              if (evento.key !== "Enter") return;
              evento.preventDefault();
              const texto = evento.currentTarget.value.trim();
              if (/^\d{8,}$/.test(texto)) {
                lerCodigo(texto);
                return;
              }
              if (visiveis.length === 1) escolher(visiveis[0]);
            }}
          />
          <button className={`btn pequeno ${soPreco ? "" : "ghost"}`} type="button" onClick={() => setSoPreco((valor) => !valor)}>
            {soPreco ? "Consulta de preço" : "Consulta"}
          </button>
        </div>
        <div className="cat-chips">
          <button className={`cat-chip ${categoria ? "" : "ativo"}`} type="button" onClick={() => setCategoria("")}>Todos · {produtos.length}</button>
          {categorias.map((nome) => (
            <button className={`cat-chip ${categoria === nome ? "ativo" : ""}`} type="button" key={nome} onClick={() => setCategoria(nome)}>
              {nome} · {produtos.filter((item) => item.categoria === nome).length}
            </button>
          ))}
        </div>
        {pesoAlvo ? (
          <form className="peso-barra" onSubmit={(evento) => {
            evento.preventDefault();
            const gramas = Number(gramasTxt);
            if (gramas > 0) porProduto(pesoAlvo, { gramas });
            setPesoAlvo(null);
            buscaRef.current?.focus();
          }}>
            <strong>{pesoAlvo.nome}</strong>
            <span>{moeda(pesoAlvo.preco)}/kg</span>
            <input inputMode="numeric" autoFocus placeholder="Gramas" value={gramasTxt} onChange={(evento) => setGramasTxt(evento.target.value.replace(/\D/g, ""))} />
            <button className="btn pequeno" type="submit">Lançar peso</button>
          </form>
        ) : null}
        {consulta ? <p className="consulta-preco">{consulta.nome} · {moeda(consulta.preco)}{consulta.unidade === "kg" ? "/kg" : ""} · estoque {estoqueDe(consulta)}{consulta.codigo_barras ? ` · ${consulta.codigo_barras}` : ""}</p> : null}
        {aviso ? <p className="alerta">{aviso}</p> : null}
        <div className="frente-grade-produtos">
          {visiveis.map((produto) => (
            <button className={`produto-card ${produto.esgotado ? "esgotado" : ""}`} type="button" key={produto.id} onClick={() => escolher(produto)}>
              {produto.foto ? <img className="foto-produto" src={produto.foto} alt="" /> : <span className="marca-produto">{sigla(produto.nome)}</span>}
              <strong>{produto.nome}</strong>
              <span>{produto.marca || produto.categoria || (produto.unidade === "kg" ? "Por peso" : "Unidade")}</span>
              <em>{moeda(produto.preco)}{produto.unidade === "kg" ? "/kg" : ""}</em>
              <small>{produto.esgotado ? "Sem estoque" : `Estoque ${estoqueDe(produto)}`}</small>
            </button>
          ))}
        </div>
        {visiveis.length ? null : <p className="muted">Nenhum produto com esse filtro.</p>}
      </section>
      <aside className="frente-pedido">
        <h2>Pedido atual</h2>
        {comprovante ? (
          <div className="comprovante">
            <p className="kicker">Comprovante comercial</p>
            <strong>Venda {comprovante.numero}</strong>
            <p>{comprovante.cliente}{comprovante.pet ? ` · ${comprovante.pet}` : ""}</p>
            {(comprovante.itens || []).map((item, indice) => <div className="item" key={indice}><span>{item.descricao}</span><strong>{moeda(item.valor)}</strong></div>)}
            <p>Total <strong>{moeda(comprovante.total)}</strong></p>
            <button className="btn ghost" type="button" onClick={() => window.print()}>Imprimir</button>
            <button className="btn" type="button" onClick={() => setComprovante(null)}>Novo pedido</button>
          </div>
        ) : null}
        <div className="lista">
          {carrinho.length ? carrinho.map((item) => (
            <div className="item" key={item.chave}>
              <div>
                <strong>{item.nome}</strong>
                <small>{item.unidade === "kg" ? `${(item.gramas / 1000).toFixed(3)} kg` : `${item.quantidade} × ${moeda(item.preco)}`}</small>
              </div>
              {item.unidade === "kg" ? null : (
                <span className="qtd">
                  <button type="button" onClick={() => setCarrinho((atual) => atual.flatMap((linha) => linha.chave !== item.chave ? [linha] : linha.quantidade <= 1 ? [] : [{ ...linha, quantidade: linha.quantidade - 1 }]))}>−</button>
                  <button type="button" onClick={() => setCarrinho((atual) => atual.map((linha) => linha.chave === item.chave && linha.quantidade < linha.estoque ? { ...linha, quantidade: linha.quantidade + 1 } : linha))}>+</button>
                </span>
              )}
              <strong>{moeda(item.unidade === "kg" ? item.preco * item.gramas / 1000 : item.preco * item.quantidade)}</strong>
              <button className="btn pequeno ghost" type="button" onClick={() => setCarrinho((atual) => atual.filter((linha) => linha.chave !== item.chave))}>Tirar</button>
            </div>
          )) : <p className="muted">O pedido está vazio.</p>}
        </div>
        <label className="field">
          <span>Tutor</span>
          <input ref={clienteRef} value={cliente ? cliente.nome : clienteBusca} placeholder="Nome, telefone ou CPF" onChange={(evento) => { setClienteId(""); setPetId(""); setClienteBusca(evento.target.value); }} />
        </label>
        {clientesAchados.length && !clienteId ? (
          <div className="lista">
            {clientesAchados.map((pessoa) => (
              <button className="linkish" type="button" key={pessoa.id} onClick={() => { setClienteId(String(pessoa.id)); setClienteBusca(""); setPetId(""); }}>
                {pessoa.nome}{pessoa.telefone ? ` · ${pessoa.telefone}` : ""}{pessoa.cpf ? ` · ${pessoa.cpf}` : ""}
              </button>
            ))}
          </div>
        ) : null}
        <label className="field">
          <span>Animal</span>
          <select value={petId} onChange={(evento) => setPetId(evento.target.value)}>
            <option value="">Sem animal</option>
            {(cliente?.pets || []).map((pet) => <option key={pet.id} value={pet.id}>{pet.nome} · {pet.especie}</option>)}
          </select>
        </label>
        <div className="form-grid">
          <label className="field"><span>Desconto</span><input inputMode="numeric" value={desconto} onChange={(evento) => setDesconto(mascaraMoeda(evento.target.value))} /></label>
          <label className="field"><span>Acréscimo</span><input inputMode="numeric" value={acrescimo} onChange={(evento) => setAcrescimo(mascaraMoeda(evento.target.value))} /></label>
        </div>
        {partes.map((parte, indice) => (
          <div className="form-grid" key={indice}>
            <label className="field"><span>Pagamento {indice + 1}</span>
              <select value={parte.forma} onChange={(evento) => setPartes((atual) => atual.map((item, i) => i === indice ? { ...item, forma: evento.target.value } : item))}>
                <option value="dinheiro">Dinheiro</option>
                <option value="pix">Pix</option>
                <option value="debito">Débito</option>
                <option value="credito">Crédito</option>
              </select>
            </label>
            {partes.length > 1 ? <label className="field"><span>Valor</span><input inputMode="numeric" value={parte.valor} onChange={(evento) => setPartes((atual) => atual.map((item, i) => i === indice ? { ...item, valor: mascaraMoeda(evento.target.value) } : item))} /></label> : null}
            {parte.forma === "dinheiro" ? <label className="field"><span>Recebido</span><input inputMode="numeric" value={parte.recebido} placeholder={moeda(liquido)} onChange={(evento) => setPartes((atual) => atual.map((item, i) => i === indice ? { ...item, recebido: mascaraMoeda(evento.target.value) } : item))} /></label> : null}
            {parte.forma === "credito" ? <label className="field"><span>Parcelas</span><input inputMode="numeric" value={parte.parcelas} onChange={(evento) => setPartes((atual) => atual.map((item, i) => i === indice ? { ...item, parcelas: evento.target.value.replace(/\D/g, "") } : item))} /></label> : null}
          </div>
        ))}
        <button className="btn pequeno ghost" type="button" onClick={() => setPartes((atual) => [...atual, { forma: "pix", valor: "", recebido: "", parcelas: "1" }])}>Dividir pagamento</button>
        <label className="field"><span>Observação</span><input value={observacao} onChange={(evento) => setObservacao(evento.target.value)} /></label>
        <div className="frente-totais">
          <span>Subtotal</span><strong>{moeda(bruto)}</strong>
          <span>Desconto</span><strong>{moeda(moedaParaNumero(desconto))}</strong>
          <span>Acréscimo</span><strong>{moeda(moedaParaNumero(acrescimo))}</strong>
          <span className="frente-total">Total</span><strong className="frente-total">{moeda(liquido)}</strong>
          {trocoPrevisto ? <><span>Troco</span><strong>{moeda(trocoPrevisto)}</strong></> : null}
        </div>
        {suspensas.length ? (
          <label className="field"><span>Recuperar suspensa</span>
            <select value="" onChange={(evento) => {
              const venda = suspensas.find((item) => String(item.id) === evento.target.value);
              if (venda) recuperar(venda);
            }}>
              <option value="">Escolha</option>
              {suspensas.map((venda) => <option key={venda.id} value={venda.id}>#{venda.numero} · {venda.cliente} · {moeda(venda.total)}</option>)}
            </select>
          </label>
        ) : null}
        {!caixa ? <p className="alerta">O caixa deste operador está fechado. A venda não entra na gaveta de outra pessoa.</p> : null}
        <div className="frente-acoes">
          {pode(me?.papel, "caixas") && !caixa ? <button className="btn ghost" type="button" onClick={acoes.abrirCaixa}>Abrir caixa</button> : null}
          <button className="btn ghost" type="button" onClick={suspender} disabled={!carrinho.length}>Suspender</button>
          <button className="btn" type="button" onClick={receber} disabled={!carrinho.length || !clienteId || !caixa}>Receber {moeda(liquido)}</button>
        </div>
        {children}
      </aside>
    </div>
  );
}

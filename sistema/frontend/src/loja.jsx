import { useEffect, useState } from "react";
import { moeda } from "./format.js";

async function chamar(path, options = {}) {
  const resposta = await fetch(path, {
    credentials: "same-origin",
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await resposta.json().catch(() => ({}));
  if (!resposta.ok) throw new Error(data?.detail?.mensagem || "Não foi possível concluir.");
  return data;
}

export default function Loja() {
  const [produtos, setProdutos] = useState([]);
  const [busca, setBusca] = useState("");
  const [carrinho, setCarrinho] = useState([]);
  const [cliente, setCliente] = useState(null);
  const [aviso, setAviso] = useState("");
  const [pedidos, setPedidos] = useState([]);
  const [novo, setNovo] = useState(false);

  useEffect(() => {
    chamar("/api/loja/produtos").then(setProdutos).catch((erro) => setAviso(erro.message));
    chamar("/api/loja/me").then(setCliente).catch(() => setCliente(null));
  }, []);

  function somar(produto) {
    setCarrinho((atual) => {
      const existe = atual.find((item) => item.id === produto.id);
      if (existe) return atual.map((item) => item.id === produto.id ? { ...item, quantidade: item.quantidade + 1 } : item);
      return [...atual, { ...produto, quantidade: 1 }];
    });
  }

  const visiveis = produtos.filter((item) => item.nome.toLowerCase().includes(busca.toLowerCase()));
  const total = carrinho.reduce((soma, item) => soma + item.preco * item.quantidade, 0);

  async function entrar(evento) {
    evento.preventDefault();
    const dados = new FormData(evento.target);
    const corpo = Object.fromEntries(dados.entries());
    const caminho = novo ? "/api/loja/cadastro" : "/api/loja/login";
    const usuario = await chamar(caminho, { method: "POST", body: corpo });
    setCliente(usuario);
    setPedidos(await chamar("/api/loja/pedidos"));
  }

  async function fechar() {
    const pedido = await chamar("/api/loja/pedidos", {
      method: "POST",
      body: { entrega: "retirada", itens: carrinho.map((item) => ({ produto_id: item.id, quantidade: item.quantidade })) },
    });
    setCarrinho([]);
    setAviso(`Pedido ${pedido.id} reservado. O pagamento é feito na retirada, no caixa da loja.`);
    setProdutos(await chamar("/api/loja/produtos"));
    setPedidos(await chamar("/api/loja/pedidos"));
  }

  return (
    <main className="loja">
      <header className="loja-topo">
        <strong>Casa do pet</strong>
        <input placeholder="Buscar produto" value={busca} onChange={(evento) => setBusca(evento.target.value)} />
        <span>{cliente ? cliente.nome : "Entrar"}</span>
      </header>
      {aviso ? <p className="alerta">{aviso}</p> : null}
      <section className="vitrine">
        {visiveis.map((produto) => (
          <article key={produto.id}>
            <h2>{produto.nome}</h2>
            <p>{produto.categoria || "Produto"} · {produto.estoque} disponíveis</p>
            <strong>{moeda(produto.preco)}</strong>
            <button className="btn pequeno" type="button" onClick={() => somar(produto)}>Adicionar</button>
          </article>
        ))}
      </section>
      <aside className="sacola">
        <h2>Sacola</h2>
        {carrinho.map((item) => <p key={item.id}>{item.quantidade}× {item.nome}</p>)}
        <p><strong>{moeda(total)}</strong></p>
        {cliente ? <button className="btn" type="button" disabled={!carrinho.length} onClick={() => fechar().catch((erro) => setAviso(erro.message))}>Reservar retirada</button> : (
          <form onSubmit={(evento) => entrar(evento).catch((erro) => setAviso(erro.message))}>
            <label className="field"><span>E-mail</span><input name="email" type="email" required /></label>
            <label className="field"><span>Senha</span><input name="senha" type="password" required /></label>
            {novo ? (
              <>
                <label className="field"><span>Nome</span><input name="nome" required /></label>
                <label className="field"><span>Telefone</span><input name="telefone" required /></label>
              </>
            ) : null}
            <button className="btn" type="submit">{novo ? "Criar conta" : "Entrar"}</button>
            <button className="btn ghost" type="button" onClick={() => setNovo((valor) => !valor)}>{novo ? "Já tenho conta" : "Criar conta"}</button>
          </form>
        )}
        {pedidos.map((pedido) => <p key={pedido.id}>Pedido {pedido.id} · {pedido.status} · {moeda(pedido.total)}</p>)}
      </aside>
    </main>
  );
}

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Menu, ShoppingBag, User, X } from "lucide-react";
import { aplicarCor, mascaraTelefone, moeda } from "./format.js";
import { CampoSenha } from "./ui.jsx";

const ICONE = { size: 20, strokeWidth: 1.75 };
const ANIMAIS = [
  ["Cachorro", "/videos/cachorro.mp4"],
  ["Gato", "/videos/gato.mp4"],
  ["Peixe", "/videos/peixe.mp4"],
  ["Ave", "/videos/ave.mp4"],
  ["Roedor", "/videos/roedor.mp4"],
  ["Réptil", "/videos/reptil.mp4"],
];

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

function sigla(nome) {
  return String(nome || "").trim().split(/\s+/).slice(0, 2).map((parte) => parte.slice(0, 1).toUpperCase()).join("") || "•";
}

function whatsappDe(numero) {
  const digitos = String(numero || "").replace(/\D/g, "");
  if (!digitos) return "";
  return `https://wa.me/${digitos.length <= 11 ? `55${digitos}` : digitos}`;
}

export default function Loja() {
  const [vitrine, setVitrine] = useState(null);
  const [falha, setFalha] = useState("");
  const [aviso, setAviso] = useState("");
  const [especie, setEspecie] = useState("Cachorro");
  const [painel, setPainel] = useState("");
  const [cliente, setCliente] = useState(null);
  const [novo, setNovo] = useState(false);
  const [telefone, setTelefone] = useState("");
  const [carrinho, setCarrinho] = useState([]);
  const [pets, setPets] = useState([]);
  const [agenda, setAgenda] = useState([]);
  const [horarios, setHorarios] = useState([]);
  const [petId, setPetId] = useState("");
  const [servicoId, setServicoId] = useState("");
  const [dia, setDia] = useState("");
  const [petNome, setPetNome] = useState("");
  const [petEspecie, setPetEspecie] = useState("Cachorro");
  const [porte, setPorte] = useState("M");

  useEffect(() => {
    chamar("/api/loja/vitrine").then((dados) => {
      setVitrine(dados);
      aplicarCor(dados.cor);
      document.title = dados.nome;
    }).catch((erro) => setFalha(erro.message));
    chamar("/api/loja/me").then(setCliente).catch(() => setCliente(null));
  }, []);

  useEffect(() => {
    if (!cliente) {
      setPets([]);
      setAgenda([]);
      return;
    }
    chamar("/api/loja/pets").then(setPets).catch((erro) => setAviso(erro.message));
    chamar("/api/loja/agendamentos").then(setAgenda).catch(() => setAgenda([]));
  }, [cliente]);

  const pet = pets.find((item) => String(item.id) === String(petId));
  const servicos = useMemo(() => {
    const lista = vitrine?.servicos || [];
    return pet ? lista.filter((item) => item.porte === pet.porte) : lista;
  }, [vitrine, pet]);

  useEffect(() => {
    if (!cliente || !petId || !servicoId || !dia) {
      setHorarios([]);
      return;
    }
    chamar(`/api/loja/horarios?pet_id=${petId}&servico_id=${servicoId}&dia=${dia}`)
      .then(setHorarios)
      .catch((erro) => {
        setHorarios([]);
        setAviso(erro.message);
      });
  }, [cliente, petId, servicoId, dia]);

  function somar(produto) {
    setCarrinho((atual) => {
      const existe = atual.find((item) => item.id === produto.id);
      if (existe) {
        if (existe.quantidade >= produto.estoque) return atual;
        return atual.map((item) => item.id === produto.id ? { ...item, quantidade: item.quantidade + 1 } : item);
      }
      return [...atual, { ...produto, quantidade: 1 }];
    });
    setPainel("sacola");
  }

  function quantidade(id, delta) {
    setCarrinho((atual) => atual.flatMap((item) => {
      if (item.id !== id) return [item];
      const proxima = item.quantidade + delta;
      return proxima < 1 ? [] : [{ ...item, quantidade: proxima }];
    }));
  }

  const total = carrinho.reduce((soma, item) => soma + item.preco * item.quantidade, 0);
  const video = ANIMAIS.find(([nome]) => nome === especie)?.[1] || ANIMAIS[0][1];
  const produtos = (vitrine?.produtos || []).filter((item) => item.especie === "Todos" || item.especie === especie);
  const contato = whatsappDe(vitrine?.whatsapp);

  async function entrar(evento) {
    evento.preventDefault();
    const dados = new FormData(evento.target);
    const caminho = novo ? "/api/loja/cadastro" : "/api/loja/login";
    const usuario = await chamar(caminho, { method: "POST", body: Object.fromEntries(dados.entries()) });
    setCliente(usuario);
    setPainel("");
    setAviso(`Olá, ${usuario.nome}.`);
  }

  async function reservar() {
    const pedido = await chamar("/api/loja/pedidos", {
      method: "POST",
      body: { entrega: "retirada", itens: carrinho.map((item) => ({ produto_id: item.id, quantidade: item.quantidade })) },
    });
    setCarrinho([]);
    setAviso(`Pedido ${pedido.id} reservado. O pagamento é na retirada, no caixa da loja.`);
    setVitrine(await chamar("/api/loja/vitrine"));
  }

  async function criarPet(evento) {
    evento.preventDefault();
    const criado = await chamar("/api/loja/pets", { method: "POST", body: { nome: petNome, especie: petEspecie, porte } });
    setPetNome("");
    setPets(await chamar("/api/loja/pets"));
    setPetId(String(criado.id));
  }

  async function marcar(hora) {
    const inicio = `${dia}T${hora}:00`;
    const marcado = await chamar("/api/loja/agendamentos", {
      method: "POST",
      body: { pet_id: Number(petId), servico_id: Number(servicoId), inicio },
    });
    setAviso(`${marcado.servico} de ${marcado.pet} marcado. O pagamento é na busca.`);
    setAgenda(await chamar("/api/loja/agendamentos"));
    setHorarios([]);
  }

  function escolherServico(servico) {
    setServicoId(String(servico.id));
    document.getElementById("agenda")?.scrollIntoView({ behavior: "smooth" });
  }

  if (falha) {
    return <main className="site"><p className="site-aviso">{falha}</p></main>;
  }
  if (!vitrine) {
    return <main className="site"><p className="site-aviso">Abrindo a loja...</p></main>;
  }

  return (
    <main className="site">
      <header className="site-topo">
        <div className="site-acoes">
          <button type="button" aria-label="Abrir menu" onClick={() => setPainel("menu")}><Menu {...ICONE} /></button>
          <button type="button" aria-label="Conta" onClick={() => setPainel("conta")}><User {...ICONE} /></button>
          <button type="button" aria-label="Sacola" onClick={() => setPainel("sacola")}>
            <ShoppingBag {...ICONE} />
            {carrinho.length ? <em>{carrinho.reduce((soma, item) => soma + item.quantidade, 0)}</em> : null}
          </button>
        </div>
        <a className="site-marca" href="#inicio">
          {vitrine.logo ? <img src={vitrine.logo} alt="" /> : <strong>{vitrine.nome}</strong>}
        </a>
        <a className="site-pill" href="#loja">Comprar</a>
      </header>

      <section className="site-hero" id="inicio">
        <video key={video} src={video} autoPlay muted loop playsInline />
        <div className="site-velo" />
        <div className="site-hero-texto">
          <h1>{vitrine.nome}</h1>
          <a className="site-pill clara" href="#agenda">Agendar um horário <ArrowRight {...ICONE} /></a>
        </div>
        <div className="site-especies">
          {ANIMAIS.map(([nome]) => (
            <button key={nome} type="button" className={especie === nome ? "ativa" : ""} aria-pressed={especie === nome} onClick={() => setEspecie(nome)}>{nome}</button>
          ))}
        </div>
      </section>

      <section className="site-faixa">
        <p>{vitrine.slogan}</p>
      </section>

      <section className="site-bloco" id="servicos">
        <h2>Serviços</h2>
        <div className="site-grade">
          {servicos.length ? servicos.map((servico) => (
            <article key={servico.id}>
              <h3>{servico.nome}</h3>
              <p>Porte {servico.porte} · {servico.duracao_min} min</p>
              <strong>{moeda(servico.preco)}</strong>
              <button type="button" onClick={() => escolherServico(servico)}>Agendar</button>
            </article>
          )) : <p className="site-mudo">Os horários aparecem quando a loja publica os serviços.</p>}
        </div>
      </section>

      <section className="site-bloco" id="loja">
        <h2>Loja · {especie}</h2>
        <div className="site-grade">
          {produtos.length ? produtos.map((produto) => (
            <article key={produto.id}>
              {produto.foto ? <img src={produto.foto} alt="" /> : <b className="site-sigla">{sigla(produto.nome)}</b>}
              <h3>{produto.nome}</h3>
              <strong>{moeda(produto.preco)}</strong>
              <button type="button" onClick={() => somar(produto)}>Adicionar</button>
            </article>
          )) : <p className="site-mudo">Nenhum produto de {especie} com estoque.</p>}
        </div>
      </section>

      <section className="site-bloco" id="agenda">
        <h2>Agendar</h2>
        <p className="site-mudo">O horário entra na agenda da loja. O pagamento do serviço é na busca.</p>
        {cliente ? (
          <>
            <form className="site-linha" onSubmit={(evento) => criarPet(evento).catch((erro) => setAviso(erro.message))}>
              <input required placeholder="Nome do pet" value={petNome} onChange={(evento) => setPetNome(evento.target.value)} />
              <select value={petEspecie} onChange={(evento) => setPetEspecie(evento.target.value)}>
                {ANIMAIS.map(([nome]) => <option key={nome}>{nome}</option>)}
              </select>
              <select value={porte} onChange={(evento) => setPorte(evento.target.value)}>
                <option value="P">Porte P</option>
                <option value="M">Porte M</option>
                <option value="G">Porte G</option>
              </select>
              <button className="site-pill" type="submit">Guardar pet</button>
            </form>
            <div className="site-linha">
              <select value={petId} onChange={(evento) => setPetId(evento.target.value)}>
                <option value="">Escolha o pet</option>
                {pets.map((item) => <option key={item.id} value={item.id}>{item.nome} · porte {item.porte}</option>)}
              </select>
              <select value={servicoId} onChange={(evento) => setServicoId(evento.target.value)}>
                <option value="">Escolha o serviço</option>
                {servicos.map((item) => <option key={item.id} value={item.id}>{item.nome} · {moeda(item.preco)}</option>)}
              </select>
              <input type="date" value={dia} min={new Date().toISOString().slice(0, 10)} onChange={(evento) => setDia(evento.target.value)} />
            </div>
            <div className="site-horas">
              {horarios.length ? horarios.map((hora) => (
                <button key={hora} type="button" onClick={() => marcar(hora).catch((erro) => setAviso(erro.message))}>{hora}</button>
              )) : <p className="site-mudo">{petId && servicoId && dia ? "Nenhum horário livre nesse dia." : "Escolha o pet, o serviço e o dia."}</p>}
            </div>
            {agenda.length ? (
              <ul className="site-lista">
                {agenda.map((item) => <li key={item.id}>{item.pet} · {item.servico} · {item.inicio?.replace("T", " ").slice(0, 16)} · {item.status}</li>)}
              </ul>
            ) : null}
          </>
        ) : <button className="site-pill" type="button" onClick={() => setPainel("conta")}>Entrar para agendar</button>}
      </section>

      <section className="site-bloco" id="contato">
        <h2>Contato</h2>
        {contato ? <a className="site-pill" href={contato} target="_blank" rel="noreferrer">WhatsApp da loja</a> : <p className="site-mudo">A loja ainda não publicou o WhatsApp.</p>}
      </section>

      <footer className="site-rodape">
        <strong>{vitrine.nome}</strong>
        <a href="/">Área da equipe</a>
      </footer>

      {aviso ? <p className="site-toast" role="status">{aviso}</p> : null}

      {painel ? (
        <div className="site-painel">
          <button className="site-fundo" type="button" aria-label="Fechar" onClick={() => setPainel("")} />
          <aside>
            <button className="site-fechar" type="button" aria-label="Fechar painel" onClick={() => setPainel("")}><X {...ICONE} /></button>
            {painel === "menu" ? (
              <nav>
                {[["#inicio", "Início"], ["#servicos", "Serviços"], ["#loja", "Loja"], ["#agenda", "Agendar"], ["#contato", "Contato"]].map(([href, nome]) => (
                  <a key={href} href={href} onClick={() => setPainel("")}>{nome}</a>
                ))}
              </nav>
            ) : null}
            {painel === "conta" ? (
              cliente ? (
                <div>
                  <h2>{cliente.nome}</h2>
                  <button className="site-pill" type="button" onClick={() => chamar("/api/loja/logout", { method: "POST" }).then(() => { setCliente(null); setPainel(""); })}>Sair</button>
                </div>
              ) : (
                <form onSubmit={(evento) => entrar(evento).catch((erro) => setAviso(erro.message))}>
                  <h2>{novo ? "Criar conta" : "Entrar"}</h2>
                  <label>E-mail<input name="email" type="email" required /></label>
                  <label>Senha<CampoSenha key={novo ? "nova" : "entrar"} name="senha" required minLength={6} autoComplete={novo ? "new-password" : "current-password"} /></label>
                  {novo ? (
                    <>
                      <label>Nome<input name="nome" required /></label>
                      <label>Telefone<input name="telefone" inputMode="tel" autoComplete="tel" required placeholder="(00) 00000-0000" value={telefone} onChange={(evento) => setTelefone(mascaraTelefone(evento.target.value))} /></label>
                    </>
                  ) : null}
                  <button className="site-pill" type="submit">{novo ? "Criar conta" : "Entrar"}</button>
                  <button className="site-texto" type="button" onClick={() => setNovo((valor) => !valor)}>{novo ? "Já tenho conta" : "Criar conta"}</button>
                </form>
              )
            ) : null}
            {painel === "sacola" ? (
              <div>
                <h2>Sacola</h2>
                {carrinho.length ? carrinho.map((item) => (
                  <p key={item.id}>
                    <span>{item.nome}</span>
                    <button type="button" onClick={() => quantidade(item.id, -1)}>-</button>
                    {item.quantidade}
                    <button type="button" onClick={() => quantidade(item.id, 1)}>+</button>
                    <strong>{moeda(item.preco * item.quantidade)}</strong>
                  </p>
                )) : <p className="site-mudo">A sacola está vazia.</p>}
                <p><strong>{moeda(total)}</strong></p>
                <p className="site-mudo">A reserva sai do estoque. O pagamento é na retirada, no caixa da loja.</p>
                {cliente ? (
                  <button className="site-pill" type="button" disabled={!carrinho.length} onClick={() => reservar().catch((erro) => setAviso(erro.message))}>Reservar retirada</button>
                ) : <button className="site-pill" type="button" onClick={() => setPainel("conta")}>Entrar para reservar</button>}
              </div>
            ) : null}
          </aside>
        </div>
      ) : null}
    </main>
  );
}

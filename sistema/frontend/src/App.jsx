import { useCallback, useEffect, useRef, useState } from "react";
import { Bell, Menu } from "lucide-react";
import { intervaloAgenda, isoDate, isoLocal, mensagemErro } from "./format.js";
import {
  AbrirCaixaModal,
  AgendamentoModal,
  BuscaModal,
  CheckoutModal,
  ClienteModal,
  FecharCaixaModal,
  PacoteModal,
  VendaModal,
} from "./modals.jsx";
import Loja from "./loja.jsx";
import Pagina from "./pages.jsx";
import { GRUPOS, ICONE, ROTULOS_PAPEL, pode, primeiraPagina } from "./ui.jsx";

function Sino({ api, ir }) {
  const [itens, setItens] = useState([]);
  const [aberto, setAberto] = useState(false);
  useEffect(() => {
    api("/api/notificacoes").then(setItens).catch(() => setItens([]));
  }, [api]);
  const novas = itens.filter((item) => !item.lida).length;
  return (
    <div className="sino">
      <button className="icon-btn" type="button" aria-label="Notificações" onClick={() => setAberto((valor) => !valor)}>
        <Bell {...ICONE} />
        {novas ? <span className="selo-num">{novas}</span> : null}
      </button>
      {aberto ? (
        <div className="sino-lista">
          {itens.length ? itens.map((item) => (
            <button key={item.chave} type="button" className={item.lida ? "lida" : ""} onClick={() => {
              api("/api/notificacoes/lida", { method: "POST", body: { chave: item.chave } }).catch(() => {});
              setItens((lista) => lista.map((atual) => atual.chave === item.chave ? { ...atual, lida: true } : atual));
              setAberto(false);
              if (item.acao === "mapa") ir("mapa");
              else if (item.acao) ir(item.acao);
            }}>
              <strong>{item.texto}</strong>
              <small>{item.prioridade} · {item.quando?.slice(11, 16)}</small>
            </button>
          )) : <p className="muted">Nada pendente.</p>}
        </div>
      ) : null}
    </div>
  );
}

async function buscarPagina(api, { page, modo, cursor }) {
  if (page === "painel") return { dados: await api("/api/painel") };
  if (page === "mapa") return { dados: await api("/api/mapa") };
  if (page === "agenda") {
    const [de, ate] = intervaloAgenda(modo, cursor);
    return { dados: await api(`/api/agenda?de=${isoDate(de)}&ate=${isoDate(ate)}`) };
  }
  if (page === "vendas") return { dados: await api("/api/vendas") };
  if (page === "pdv") {
    const produtos = await api("/api/pdv/produtos");
    let caixa = null;
    let suspensas = [];
    try { caixa = (await api("/api/caixas"))[0] || null; } catch { caixa = null; }
    try { suspensas = await api("/api/pdv/suspensas"); } catch { suspensas = []; }
    return { dados: { produtos, caixa, suspensas } };
  }
  if (page === "caixas") return { dados: await api("/api/caixas") };
  if (page === "pets") return { pessoas: await api("/api/pessoas") };
  return {};
}

export default function App() {
  const [sessao, setSessao] = useState("checando");
  const [me, setMe] = useState(null);
  const [page, setPage] = useState("painel");
  const [catalogo, setCatalogo] = useState(null);
  const [pessoas, setPessoas] = useState([]);
  const [vista, setVista] = useState(null);
  const [cursor, setCursor] = useState(() => new Date());
  const [modo, setModo] = useState("mes");
  const [profissional, setProfissional] = useState("");
  const [buscaVenda, setBuscaVenda] = useState("");
  const [sugestao, setSugestao] = useState(null);
  const [modal, setModal] = useState(null);
  const [menuAberto, setMenuAberto] = useState(false);
  const [toast, setToast] = useState("");
  const toastTimer = useRef();
  const pedido = useRef(0);

  const avisar = useCallback((texto) => {
    setToast(texto);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(""), 4600);
  }, []);

  const api = useCallback(async (path, options = {}) => {
    const resposta = await fetch(path, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      ...options,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
    const data = await resposta.json().catch(() => ({}));
    if (!resposta.ok) {
      const erro = new Error(mensagemErro(data));
      erro.status = resposta.status;
      if (resposta.status === 401) {
        setSessao("fora");
        setMe(null);
      }
      throw erro;
    }
    return data;
  }, []);

  const run = useCallback(async (fn) => {
    try {
      await fn();
    } catch (erro) {
      if (erro.status !== 401) avisar(erro.message);
    }
  }, [avisar]);

  const recarregar = useCallback(async (proxima = page) => {
    const ticket = ++pedido.current;
    const pacote = await buscarPagina(api, { page: proxima, modo, cursor });
    if (ticket !== pedido.current) return;
    setVista({ page: proxima, modo, cursor: cursor.getTime(), dados: pacote.dados ?? null });
    if (pacote.pessoas) setPessoas(pacote.pessoas);
  }, [api, page, modo, cursor]);

  useEffect(() => {
    let vivo = true;
    api("/api/me")
      .then(async (usuario) => {
        if (!vivo) return;
        const base = await api("/api/catalogo");
        const lista = await api("/api/pessoas");
        if (!vivo) return;
        setMe(usuario);
        setPage((atual) => (pode(usuario.papel, atual) ? atual : primeiraPagina(usuario.papel)));
        setCatalogo(base);
        setPessoas(lista);
        setSessao("dentro");
      })
      .catch(() => {
        if (vivo) setSessao("fora");
      });
    return () => { vivo = false; };
  }, [api]);

  useEffect(() => {
    if (sessao !== "dentro" || !catalogo) return undefined;
    const ticket = ++pedido.current;
    buscarPagina(api, { page, modo, cursor })
      .then((pacote) => {
        if (ticket !== pedido.current) return;
        setVista({ page, modo, cursor: cursor.getTime(), dados: pacote.dados ?? null });
        if (pacote.pessoas) setPessoas(pacote.pessoas);
      })
      .catch((erro) => {
        if (ticket === pedido.current && erro.status !== 401) avisar(erro.message);
      });
    return undefined;
  }, [sessao, catalogo, page, modo, cursor, api, avisar]);

  useEffect(() => {
    function tecla(evento) {
      if (evento.key === "Escape") {
        setModal(null);
        setMenuAberto(false);
      }
    }
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, []);

  async function entrar(evento) {
    evento.preventDefault();
    const dados = new FormData(evento.target);
    await run(async () => {
      const usuario = await api("/api/login", { method: "POST", body: { login: dados.get("login"), senha: dados.get("senha") } });
      setMe(usuario);
      setPage(primeiraPagina(usuario.papel));
      setCatalogo(await api("/api/catalogo"));
      setPessoas(await api("/api/pessoas"));
      setSessao("dentro");
    });
  }

  function encaixar() {
    if (!sugestao) return;
    const agora = new Date();
    let inicio = sugestao.janela_inicio;
    if (new Date(inicio) < agora) inicio = isoLocal(agora);
    setModal({
      nome: "agendamento",
      prefill: { pet_id: sugestao.pet_id, profissional_id: sugestao.profissional_id, inicio, busca: sugestao.janela_fim },
    });
  }

  function mover(delta) {
    if (modo === "mes") setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + delta, 1));
    else setCursor(new Date(cursor.getFullYear(), cursor.getMonth(), cursor.getDate() + delta * 7));
  }

  const acoes = {
    ir: setPage,
    abrirAgendamento: (prefill = {}) => setModal({ nome: "agendamento", prefill }),
    dispensar: () => setSugestao(null),
    encaixar,
    passo: (id, nome) => run(async () => {
      const data = await api(`/api/agendamentos/${id}/${nome}`, { method: "POST" });
      setSugestao(data.sugestao || null);
      if (nome === "faltou" || nome === "cancelar") avisar(data.sugestao ? "Baia liberada. Tem alguém na fila." : "Baia liberada.");
      await recarregar();
    }),
    abrirBusca: (agendamento) => setModal({ nome: "busca", agendamento }),
    abrirCheckout: (hospedagem) => setModal({ nome: "checkout", hospedagem }),
    modo: setModo,
    profissional: setProfissional,
    mover,
    hoje: () => setCursor(new Date()),
    buscaVenda: setBuscaVenda,
    abrirVenda: () => setModal({ nome: "venda" }),
    abrirCaixa: () => setModal({ nome: "abrir-caixa" }),
    fecharCaixa: (caixa) => setModal({ nome: "fechar-caixa", caixa }),
    abrirCliente: () => setModal({ nome: "cliente" }),
    abrirPacote: (pet) => setModal({ nome: "pacote", pet }),
    recarregar,
    limparBaia: (id) => run(async () => {
      await api(`/api/baias/${id}/limpar`, { method: "POST" });
      avisar("Baia liberada depois da limpeza.");
      await recarregar();
    }),
  };

  const dadosProntos = vista && vista.page === page && (page !== "agenda" || (vista.modo === modo && vista.cursor === cursor.getTime()));

  let dialogo = null;
  if (modal?.nome === "agendamento") {
    dialogo = (
      <AgendamentoModal
        prefill={modal.prefill}
        catalogo={catalogo}
        pessoas={pessoas}
        api={api}
        onClose={() => setModal(null)}
        onSalvo={(hotel, corpo) => run(async () => {
          if (hotel) await api("/api/hospedagens", { method: "POST", body: corpo });
          else await api("/api/agendamentos", { method: "POST", body: corpo });
          setSugestao(null);
          setModal(null);
          avisar("A rotina foi reservada na baia.");
          await recarregar();
        })}
        onFila={(corpo) => run(async () => {
          await api("/api/encaixes", { method: "POST", body: corpo });
          setModal(null);
          avisar("Entrou na fila de encaixe deste dia.");
          setPage("mapa");
        })}
      />
    );
  } else if (modal?.nome === "busca") {
    dialogo = (
      <BuscaModal
        agendamento={modal.agendamento}
        onClose={() => setModal(null)}
        onSalvo={(corpo) => run(async () => {
          await api(`/api/agendamentos/${modal.agendamento.id}/buscar`, { method: "POST", body: corpo });
          setModal(null);
          avisar("Busca recebida. A baia ficou livre.");
          setPessoas(await api("/api/pessoas"));
          await recarregar();
        })}
      />
    );
  } else if (modal?.nome === "checkout") {
    dialogo = (
      <CheckoutModal
        hospedagem={modal.hospedagem}
        onClose={() => setModal(null)}
        onSalvo={(corpo) => run(async () => {
          const venda = await api(`/api/hospedagens/${modal.hospedagem.id}/checkout`, { method: "POST", body: corpo });
          setModal(null);
          avisar(venda.checkout_atrasado ? "Checkout lançado com diária extra." : "Checkout lançado no caixa do turno.");
          await recarregar();
        })}
      />
    );
  } else if (modal?.nome === "abrir-caixa") {
    dialogo = (
      <AbrirCaixaModal
        operador={me?.nome}
        onClose={() => setModal(null)}
        onSalvo={(corpo) => run(async () => {
          await api("/api/caixas", { method: "POST", body: corpo });
          setModal(null);
          avisar(`Caixa aberto no nome de ${me.nome}.`);
          await recarregar();
        })}
      />
    );
  } else if (modal?.nome === "fechar-caixa") {
    dialogo = (
      <FecharCaixaModal
        caixa={modal.caixa}
        onClose={() => setModal(null)}
        onSalvo={async (corpo) => {
          try {
            return await api(`/api/caixas/${modal.caixa.id}/fechar`, { method: "POST", body: corpo });
          } catch (erro) {
            if (erro.status !== 401) avisar(erro.message);
            return null;
          }
        }}
        onSair={() => run(async () => {
          setModal(null);
          await api("/api/logout", { method: "POST" });
          setMe(null);
          setSessao("fora");
        })}
      />
    );
  } else if (modal?.nome === "venda") {
    dialogo = (
      <VendaModal
        pessoas={pessoas}
        api={api}
        onErro={avisar}
        onClose={() => setModal(null)}
        onSalvo={async (corpo) => {
          try {
            const venda = await api("/api/pdv", { method: "POST", body: corpo });
            avisar("Venda lançada no caixa e no estoque.");
            await recarregar();
            return venda;
          } catch (erro) {
            if (erro.status !== 401) avisar(erro.message);
            return null;
          }
        }}
      />
    );
  } else if (modal?.nome === "pacote") {
    dialogo = (
      <PacoteModal
        pet={modal.pet}
        onClose={() => setModal(null)}
        onSalvo={(corpo) => run(async () => {
          await api("/api/pacotes", { method: "POST", body: corpo });
          setModal(null);
          avisar("Pacote lançado no pet e no caixa.");
          await recarregar();
        })}
      />
    );
  } else if (modal?.nome === "cliente") {
    dialogo = (
      <ClienteModal
        api={api}
        onClose={() => setModal(null)}
        onErro={avisar}
        onSalvo={(corpo) => run(async () => {
          setPessoas(await api("/api/clientes", { method: "POST", body: corpo }));
          setModal(null);
          if (page === "pets") await recarregar();
        })}
      />
    );
  }

  if (window.location.pathname.startsWith("/loja")) return <Loja />;

  return (
    <>
      {sessao !== "dentro" || !me || !catalogo ? (
        <main className="login">
          {sessao === "checando" ? <p className="muted">Carregando a rotina...</p> : (
            <section className="login-card">
              <p className="kicker">Rotina em ordem</p>
              <h1>A rotina do pet shop, em ordem.</h1>
              <p className="sub">A vaga de verdade é a baia. O horário só entra se o porte couber até a hora da busca.</p>
              <form onSubmit={entrar}>
                <label className="field"><span>Login</span><input name="login" defaultValue="paulo" autoComplete="username" required /></label>
                <label className="field"><span>Senha</span><input name="senha" type="password" defaultValue="rotina" autoComplete="current-password" required /></label>
                <button className="btn" type="submit">Entrar</button>
              </form>
              <p className="hint">Demonstração da equipe: paulo / rotina</p>
            </section>
          )}
        </main>
      ) : (
        <div className={`shell${menuAberto ? " menu-aberto" : ""}`}>
          <header className="topo-movel">
            <button className="icon-btn" type="button" aria-label="Abrir menu" aria-expanded={menuAberto} onClick={() => setMenuAberto((aberto) => !aberto)}>
              <Menu {...ICONE} />
            </button>
            <strong>Rotina em ordem</strong>
          </header>
          <div className="menu-fundo" onClick={() => setMenuAberto(false)} />
          <aside className="sidebar">
            <div className="brand"><strong>Rotina em ordem</strong><small>Banho, tosa e hotel</small></div>
            <nav className="nav">
              {GRUPOS.map(([grupo, itens]) => {
                const visiveis = itens.filter(([id]) => pode(me.papel, id));
                if (!visiveis.length) return null;
                return (
                  <div key={grupo}>
                    <p className="menu-label">{grupo}</p>
                    {visiveis.map(([id, nome, Icone]) => (
                      <button type="button" key={id} className={page === id ? "active" : ""} onClick={() => { setPage(id); setMenuAberto(false); }}>
                        <Icone {...ICONE} /> {nome}
                      </button>
                    ))}
                  </div>
                );
              })}
            </nav>
            <div className="sidebar-foot">
              <span className="avatar">{(me.nome || "?").slice(0, 1).toUpperCase()}</span>
              <div className="who"><strong>{me.nome}</strong><small>{ROTULOS_PAPEL[me.papel] || "Equipe"}</small></div>
              <button className="sair" type="button" onClick={() => run(async () => {
                await api("/api/logout", { method: "POST" });
                setMe(null);
                setSessao("fora");
              })}>Sair</button>
            </div>
          </aside>
          <main className="main">
            <div className="barra-topo"><Sino api={api} ir={(id) => { if (pode(me.papel, id)) setPage(id); }} /></div>
            <Pagina
              page={page}
              dados={dadosProntos ? vista.dados : null}
              pessoas={pessoas}
              catalogo={catalogo}
              cursor={cursor}
              modo={modo}
              profissional={profissional}
              buscaVenda={buscaVenda}
              sugestao={sugestao}
              acoes={acoes}
              api={api}
              run={run}
              me={me}
            />
          </main>
        </div>
      )}
      {dialogo ? (
        <div className="modal">
          <div className="backdrop" onClick={() => setModal(null)} />
          <div className="dialog">{dialogo}</div>
        </div>
      ) : null}
      <div id="toast" className={toast ? "show" : ""} role="status">{toast}</div>
    </>
  );
}

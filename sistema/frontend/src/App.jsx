import { useCallback, useEffect, useRef, useState } from "react";
import { Bell, Menu } from "lucide-react";
import { aplicarCor, intervaloAgenda, isoDate, isoLocal, mascaraMoeda, mascaraTelefone, mensagemErro, moedaParaNumero, PALETA } from "./format.js";
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
import { CampoSenha, GRUPOS, ICONE, ROTULOS_PAPEL, pode, primeiraPagina } from "./ui.jsx";

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
  if (page === "caixas" || page === "pdv") {
    const caixas = await api("/api/caixas");
    const produtos = await api("/api/pdv/produtos");
    let suspensas = [];
    try { suspensas = await api("/api/pdv/suspensas"); } catch { suspensas = []; }
    return { dados: { caixas, produtos, suspensas } };
  }
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
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [erroLogin, setErroLogin] = useState("");
  const [modoAcesso, setModoAcesso] = useState("login");
  const [empresa, setEmpresa] = useState("");
  const [slogan, setSlogan] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [tolerancia, setTolerancia] = useState("15");
  const [taxa, setTaxa] = useState("20,00");
  const [responsavel, setResponsavel] = useState("");
  const [cor, setCor] = useState("#1f6b4a");
  const [logoArquivo, setLogoArquivo] = useState(null);
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
      .catch(async () => {
        if (!vivo) return;
        try {
          const estado = await api("/api/estado");
          if (!vivo) return;
          setModoAcesso(estado.pronta ? "login" : "cadastro");
        } catch {
          if (!vivo) return;
          setModoAcesso("login");
        }
        setSessao("fora");
      });
    return () => { vivo = false; };
  }, [api]);

  useEffect(() => {
    if (page === "pdv") setPage("caixas");
  }, [page]);

  useEffect(() => {
    aplicarCor(me?.cor);
  }, [me]);

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

  async function entrarNaLoja(usuario) {
    setSenha("");
    setMe(usuario);
    setPage(primeiraPagina(usuario.papel));
    setCatalogo(await api("/api/catalogo"));
    setPessoas(await api("/api/pessoas"));
    setSessao("dentro");
  }

  async function entrar(evento) {
    evento.preventDefault();
    setErroLogin("");
    try {
      await entrarNaLoja(await api("/api/login", { method: "POST", body: { login: login.trim(), senha } }));
    } catch (erro) {
      setErroLogin(erro.message || "Não foi possível entrar.");
    }
  }

  async function cadastrar(evento) {
    evento.preventDefault();
    setErroLogin("");
    const minutos = Number(tolerancia);
    try {
      const usuario = await api("/api/cadastro", {
        method: "POST",
        body: {
          empresa: empresa.trim(),
          slogan: slogan.trim(),
          whatsapp,
          tolerancia_busca_min: Number.isFinite(minutos) ? minutos : -1,
          valor_atraso: moedaParaNumero(taxa),
          responsavel: responsavel.trim(),
          login: login.trim(),
          senha,
          cor,
        },
      });
      let perfil = usuario;
      if (logoArquivo) {
        const corpo = new FormData();
        corpo.append("arquivo", logoArquivo);
        const resposta = await fetch("/api/marca/logo", { method: "POST", credentials: "same-origin", body: corpo });
        const json = await resposta.json().catch(() => ({}));
        if (resposta.ok) perfil = { ...usuario, logo: json.logo, cor: json.cor || cor };
        else avisar(json.detail || "A loja foi criada. A logo pode ser enviada depois, em Marca.");
      }
      await entrarNaLoja(perfil);
    } catch (erro) {
      setErroLogin(erro.message || "Não foi possível cadastrar a empresa.");
    }
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
            <section className={`login-card${modoAcesso === "cadastro" ? " largo" : ""}`}>
              <p className="kicker">Rotina em ordem</p>
              {modoAcesso === "cadastro" ? (
                <>
                  <h1>Cadastrar a empresa</h1>
                  <p className="sub">O nome aparece no menu, o WhatsApp recebe os avisos e a tolerância vale na hora da busca.</p>
                  <form onSubmit={cadastrar}>
                    <label className="field"><span>Nome da empresa</span><input value={empresa} onChange={(evento) => setEmpresa(evento.target.value)} autoComplete="organization" required /></label>
                    <div className="field"><span>Cor da marca</span><div className="paleta">{PALETA.map(([valor]) => <button key={valor} type="button" className={cor === valor ? "ativa" : ""} style={{ background: valor }} aria-label={valor} onClick={() => setCor(valor)} />)}</div></div>
                    <label className="field"><span>Logo</span><input type="file" accept="image/jpeg,image/png,image/webp,image/svg+xml" onChange={(evento) => setLogoArquivo(evento.target.files?.[0] || null)} /></label>
                    <label className="field"><span>Frase da loja</span><input value={slogan} onChange={(evento) => setSlogan(evento.target.value)} maxLength={120} /></label>
                    <label className="field"><span>WhatsApp com DDD</span><input inputMode="tel" value={whatsapp} onChange={(evento) => setWhatsapp(mascaraTelefone(evento.target.value))} placeholder="(00) 00000-0000" /></label>
                    <label className="field"><span>Tolerância da busca (minutos)</span><input inputMode="numeric" value={tolerancia} onChange={(evento) => setTolerancia(evento.target.value.replace(/\D/g, "").slice(0, 3))} required /></label>
                    <label className="field"><span>Taxa de atraso</span><input inputMode="numeric" value={taxa} onChange={(evento) => setTaxa(mascaraMoeda(evento.target.value))} required /></label>
                    <label className="field"><span>Seu nome</span><input value={responsavel} onChange={(evento) => setResponsavel(evento.target.value)} autoComplete="name" required /></label>
                    <label className="field"><span>Login</span><input value={login} onChange={(evento) => setLogin(evento.target.value)} autoComplete="username" required /></label>
                    <label className="field"><span>Senha</span><CampoSenha value={senha} onChange={(evento) => setSenha(evento.target.value)} autoComplete="new-password" required /></label>
                    {erroLogin ? <p className="alerta">{erroLogin}</p> : null}
                    <button className="btn" type="submit">Criar a loja</button>
                  </form>
                  <p className="troca-acesso"><button type="button" onClick={() => { setModoAcesso("login"); setErroLogin(""); }}>Já tenho login</button></p>
                </>
              ) : (
                <>
                  <h1>Entrar</h1>
                  <p className="sub">Use o login criado para a sua equipe.</p>
                  <form onSubmit={entrar}>
                    <label className="field"><span>Login</span><input name="login" value={login} onChange={(evento) => setLogin(evento.target.value)} autoComplete="username" required /></label>
                    <label className="field"><span>Senha</span><CampoSenha name="senha" value={senha} onChange={(evento) => setSenha(evento.target.value)} autoComplete="current-password" required /></label>
                    {erroLogin ? <p className="alerta">{erroLogin}</p> : null}
                    <button className="btn" type="submit">Entrar</button>
                  </form>
                  <p className="troca-acesso"><button type="button" onClick={() => { setModoAcesso("cadastro"); setErroLogin(""); }}>Cadastrar a empresa</button></p>
                </>
              )}
            </section>
          )}
        </main>
      ) : (
        <div className={`shell${menuAberto ? " menu-aberto" : ""}`}>
          <header className="topo-movel">
            <button className="icon-btn" type="button" aria-label="Abrir menu" aria-expanded={menuAberto} onClick={() => setMenuAberto((aberto) => !aberto)}>
              <Menu {...ICONE} />
            </button>
            <strong>{me.loja || "Rotina em ordem"}</strong>
          </header>
          <div className="menu-fundo" onClick={() => setMenuAberto(false)} />
          <aside className="sidebar">
            <div className="brand">{me.logo ? <img className="logo-loja" src={me.logo} alt="" /> : null}<div><strong>{me.loja || "Rotina em ordem"}</strong><small>{me.slogan || "Banho, tosa e hotel"}</small></div></div>
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
              onMarca={(perfil) => setMe((atual) => atual ? { ...atual, loja: perfil.nome, slogan: perfil.slogan, logo: perfil.logo, cor: perfil.cor } : atual)}
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

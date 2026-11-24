import { useCallback, useEffect, useState } from "react";
import { diaMes, horaDe, isoDate, mascaraTelefone, moeda } from "./format.js";
import { ROTULOS_FORMA } from "./format.js";
import { Bell, Calendar, Landmark, MessageCircle, NotebookPen, Package, PawPrint, ScrollText } from "lucide-react";
import { Cabecalho, Pill, ROTULOS_PAPEL, Vazio } from "./ui.jsx";

function useCarga(api, url) {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState("");
  const carregar = useCallback(async () => {
    const resposta = await api(url);
    setDados(resposta);
    setErro("");
    return resposta;
  }, [api, url]);
  useEffect(() => {
    let vivo = true;
    api(url)
      .then((resposta) => { if (vivo) setDados(resposta); })
      .catch((falha) => { if (vivo) setErro(falha.message); });
    return () => { vivo = false; };
  }, [api, url]);
  return { dados, erro, carregar, setDados };
}

function espera(erro, dados) {
  if (erro) return <p className="alerta">{erro}</p>;
  if (!dados) return <p className="muted">Carregando a rotina...</p>;
  return null;
}

function petsDaLoja(pessoas) {
  return pessoas.flatMap((cliente) => cliente.pets.map((pet) => ({ ...pet, cliente: cliente.nome })));
}

function Boletins({ api }) {
  const [dia, setDia] = useState(isoDate(new Date()));
  const { dados, erro } = useCarga(api, `/api/boletins?dia=${dia}`);
  const aviso = espera(erro, dados);
  return (
    <>
      <Cabecalho kicker="Passagem de turno" titulo="Boletins" sub="O que a equipe precisa saber deste dia: quem está na baia, quem segue no hotel e o que está acabando.">
        <input type="date" value={dia} onChange={(evento) => setDia(evento.target.value)} />
      </Cabecalho>
      {aviso || (
        <>
          <p className="prosa">{dados.texto}</p>
          <section className="secao lista">
            <h2>Salão</h2>
            {dados.atendimentos.length ? dados.atendimentos.map((item) => (
              <div className="item" key={item.id}>
                <span className="selo"><strong>{item.hora.slice(0, 2)}</strong><small>{item.hora.slice(3)}</small></span>
                <div><strong>{item.pet}</strong><small>{item.servico} · {item.baia} · busca {item.busca} · {item.profissional || "Sem profissional"}</small></div>
                <Pill status={item.status} />
              </div>
            )) : <Vazio icone={Calendar} titulo="Nenhum banho ou tosa neste dia" texto="Quando um horário for reservado, ele entra neste boletim." />}
          </section>
          <section className="secao lista">
            <h2>Hotel</h2>
            {dados.hotel.length ? dados.hotel.map((item) => (
              <div className="item" key={`${item.pet}-${item.entrada}`}>
                <div><strong>{item.pet}</strong><small>{item.cliente} · {diaMes(item.entrada)} até {diaMes(item.checkout)}</small></div>
                <Pill status={item.status} />
              </div>
            )) : <Vazio icone={PawPrint} titulo="Nenhuma hospedagem neste dia" texto="O hotel aparece aqui quando um pet dormir nesta data." />}
          </section>
          <section className="layout" style={{ marginTop: 14 }}>
            <div className="lista">
              <h2>Lembretes do dia</h2>
              {dados.lembretes.length ? dados.lembretes.map((item) => (
                <div className="item" key={item.id}><div><strong>{item.texto}</strong><small>{horaDe(item.quando)}</small></div></div>
              )) : <Vazio icone={Bell} titulo="Nenhum lembrete neste dia" texto="O que a equipe anotar para esta data aparece na passagem de turno." />}
            </div>
            <div className="lista">
              <h2>Estoque no limite</h2>
              {dados.estoque_baixo.length ? dados.estoque_baixo.map((item) => (
                <div className="item" key={item.id}><div><strong>{item.nome}</strong><small>{item.estoque} no estoque · mínimo {item.minimo}</small></div></div>
              )) : <Vazio icone={Package} titulo="Estoque em ordem" texto="Nenhum produto está no limite. Quando chegar no mínimo, o aviso entra aqui." />}
            </div>
          </section>
        </>
      )}
    </>
  );
}

function Prontuario({ api, run }) {
  const { dados, erro, carregar } = useCarga(api, "/api/prontuario");
  const [petId, setPetId] = useState("");
  const [texto, setTexto] = useState("");
  const aviso = espera(erro, dados);
  const escolhido = dados?.find((pet) => String(pet.id) === String(petId)) || dados?.[0];
  return (
    <>
      <Cabecalho kicker="Histórico do pet" titulo="Prontuário" sub="O que a equipe observou em cada visita. Não substitui o veterinário: é a memória do banho, da tosa e do hotel." />
      {aviso || (
        <section className="layout">
          <div className="lista">
            <label className="field">
              <span>Pet</span>
              <select value={escolhido ? String(escolhido.id) : ""} onChange={(evento) => setPetId(evento.target.value)}>
                {dados.map((pet) => <option key={pet.id} value={pet.id}>{pet.nome} · {pet.cliente}</option>)}
              </select>
            </label>
            {escolhido ? (
              <>
                <p className="prosa">{escolhido.cuidados || "Sem cuidado fixo anotado."} {escolhido.alimentacao}</p>
                <h2>Anotações</h2>
                {escolhido.notas.length ? escolhido.notas.map((nota) => (
                  <article className="nota" key={nota.id}>
                    <strong>{nota.autor}</strong>
                    <small className="muted"> {diaMes(nota.quando)} {horaDe(nota.quando)}</small>
                    <p>{nota.texto}</p>
                  </article>
                )) : <Vazio icone={NotebookPen} titulo="Prontuário ainda em branco" texto="A primeira observação fica aqui. Não substitui o veterinário: é a memória do banho, da tosa e do hotel." />}
                <form onSubmit={(evento) => {
                  evento.preventDefault();
                  run(async () => {
                    await api("/api/prontuario", { method: "POST", body: { pet_id: escolhido.id, texto } });
                    setTexto("");
                    await carregar();
                  });
                }}>
                  <label className="field"><span>Nova observação</span><textarea value={texto} onChange={(evento) => setTexto(evento.target.value)} /></label>
                  <button className="btn" type="submit">Guardar no prontuário</button>
                </form>
              </>
            ) : <Vazio icone={PawPrint} titulo="Nenhum pet no prontuário" texto="Cadastre o pet primeiro. As visitas e as observações passam a ficar com ele." />}
          </div>
          <div className="lista">
            <h2>Visitas</h2>
            {escolhido?.visitas.length ? escolhido.visitas.map((visita) => (
              <div className="item" key={visita.id}>
                <div><strong>{visita.servico}</strong><small>{diaMes(visita.quando)} {horaDe(visita.quando)} · {visita.profissional || "Sem profissional"}</small></div>
                <Pill status={visita.status} />
              </div>
            )) : <Vazio icone={Calendar} titulo="Nenhuma visita ainda" texto="Quando este pet tiver um horário, a visita aparece neste histórico." />}
          </div>
        </section>
      )}
    </>
  );
}

function Lembretes({ api, run, pessoas }) {
  const { dados, erro, carregar } = useCarga(api, "/api/lembretes");
  const [texto, setTexto] = useState("");
  const [quando, setQuando] = useState("");
  const [petId, setPetId] = useState("");
  const aviso = espera(erro, dados);
  const pets = petsDaLoja(pessoas);
  return (
    <>
      <Cabecalho kicker="Para não esquecer" titulo="Lembretes" sub="Vacina, ração, busca combinada ou qualquer coisa que a próxima pessoa da loja precisa ver." />
      {aviso || (
        <section className="layout">
          <div className="lista">
            {dados.length ? dados.map((item) => (
              <div className="item" key={item.id}>
                <div>
                  <strong>{item.texto}</strong>
                  <small>{diaMes(item.quando)} {horaDe(item.quando)}{item.pet ? ` · ${item.pet}` : ""}</small>
                </div>
                {item.feito ? <span className="pill fechado">Feito</span> : (
                  <button className="btn pequeno ghost" type="button" onClick={() => run(async () => {
                    await api(`/api/lembretes/${item.id}/concluir`, { method: "POST" });
                    await carregar();
                  })}>Concluir</button>
                )}
              </div>
            )) : <Vazio icone={Bell} titulo="Nenhum lembrete ainda" texto="Anote o que a próxima pessoa da loja precisa ver: ração, busca combinada ou vacina." />}
          </div>
          <form className="lista" onSubmit={(evento) => {
            evento.preventDefault();
            run(async () => {
              await api("/api/lembretes", { method: "POST", body: { texto, quando, pet_id: petId ? Number(petId) : null } });
              setTexto("");
              await carregar();
            });
          }}>
            <h2>Novo lembrete</h2>
            <label className="field"><span>O que lembrar</span><input required value={texto} onChange={(evento) => setTexto(evento.target.value)} /></label>
            <label className="field"><span>Quando</span><input required type="datetime-local" value={quando} onChange={(evento) => setQuando(evento.target.value)} /></label>
            <label className="field">
              <span>Pet, se for o caso</span>
              <select value={petId} onChange={(evento) => setPetId(evento.target.value)}>
                <option value="">Nenhum pet</option>
                {pets.map((pet) => <option key={pet.id} value={pet.id}>{pet.nome} · {pet.cliente}</option>)}
              </select>
            </label>
            <button className="btn" type="submit">Salvar lembrete</button>
          </form>
        </section>
      )}
    </>
  );
}

function Catalogo({ api, run }) {
  const { dados, erro, carregar } = useCarga(api, "/api/loja/catalogo");
  const [nome, setNome] = useState("");
  const [preco, setPreco] = useState("");
  const [estoqueInicial, setEstoqueInicial] = useState("0");
  const [minimo, setMinimo] = useState("1");
  const aviso = espera(erro, dados);
  return (
    <>
      <Cabecalho kicker="O que a loja oferece" titulo="Catálogo" sub="Serviços por porte e produtos de balcão. O preço do serviço é o que a busca usa quando ninguém combinou outro valor." />
      {aviso || (
        <>
          <section className="secao lista">
            <h2>Serviços</h2>
            {dados.servicos.map((servico) => (
              <form className="item" key={servico.id} onSubmit={(evento) => {
                evento.preventDefault();
                const campo = new FormData(evento.target);
                run(async () => {
                  await api(`/api/servicos/${servico.id}`, {
                    method: "PATCH",
                    body: { preco: Number(campo.get("preco")), preco_feriado: servico.preco_feriado },
                  });
                  await carregar();
                });
              }}>
                <div>
                  <strong>{servico.nome}</strong>
                  <small>Porte {servico.porte} · {servico.tipo === "hotel" ? "diária" : `${servico.duracao_min} min`}</small>
                </div>
                <label className="field" style={{ margin: 0, width: 120 }}>
                  <span>Preço</span>
                  <input name="preco" type="number" min="0" step="0.01" defaultValue={servico.preco} />
                </label>
                <button className="btn pequeno ghost" type="submit">Atualizar</button>
              </form>
            ))}
          </section>
          <section className="layout" style={{ marginTop: 14 }}>
            <div className="lista">
              <h2>Produtos</h2>
              {dados.produtos.length ? dados.produtos.map((produto) => (
                <div className="item" key={produto.id}>
                  <div><strong>{produto.nome}</strong><small>{produto.estoque} no estoque</small></div>
                  <strong>{moeda(produto.preco)}</strong>
                </div>
              )) : <Vazio icone={Package} titulo="Nenhum produto no balcão" texto="Os serviços já estão no catálogo. O shampoo e o restante entram aqui." />}
            </div>
            <form className="lista" onSubmit={(evento) => {
              evento.preventDefault();
              run(async () => {
                await api("/api/produtos", {
                  method: "POST",
                  body: { nome, preco: Number(preco), estoque: Number(estoqueInicial), minimo: Number(minimo) },
                });
                setNome("");
                setPreco("");
                await carregar();
              });
            }}>
              <h2>Novo produto</h2>
              <label className="field"><span>Nome</span><input required value={nome} onChange={(evento) => setNome(evento.target.value)} /></label>
              <label className="field"><span>Preço</span><input required type="number" min="0" step="0.01" value={preco} onChange={(evento) => setPreco(evento.target.value)} /></label>
              <label className="field"><span>Estoque inicial</span><input type="number" min="0" value={estoqueInicial} onChange={(evento) => setEstoqueInicial(evento.target.value)} /></label>
              <label className="field"><span>Mínimo</span><input type="number" min="0" value={minimo} onChange={(evento) => setMinimo(evento.target.value)} /></label>
              <button className="btn" type="submit">Incluir no catálogo</button>
            </form>
          </section>
        </>
      )}
    </>
  );
}

function Estoque({ api, run }) {
  const { dados, erro, carregar } = useCarga(api, "/api/estoque");
  const aviso = espera(erro, dados);
  return (
    <>
      <Cabecalho kicker="Balcão" titulo="Estoque" sub="O que entra e o que sai. Quando a quantidade chega no mínimo, o boletim do dia avisa a equipe." />
      {aviso || (dados.length ? dados.map((produto) => (
        <article className="lista estoque-item" key={produto.id}>
          <div>
            <strong>{produto.nome}</strong>
            <div className="muted">{moeda(produto.preco)} · mínimo {produto.minimo}</div>
            <div className={produto.baixo ? "credito" : "muted"}>{produto.estoque} unidade(s){produto.baixo ? " · abaixo do mínimo" : ""}</div>
            {produto.movimentos.map((mov, indice) => (
              <small className="muted" key={`${produto.id}-${indice}`}>{mov.quantidade > 0 ? "+" : ""}{mov.quantidade} · {mov.motivo}</small>
            ))}
          </div>
          <form onSubmit={(evento) => {
            evento.preventDefault();
            const campo = new FormData(evento.target);
            const sinal = campo.get("sentido") === "saida" ? -1 : 1;
            run(async () => {
              await api("/api/estoque", {
                method: "POST",
                body: { produto_id: produto.id, quantidade: sinal * Number(campo.get("quantidade")), motivo: campo.get("motivo") },
              });
              await carregar();
            });
          }}>
            <label className="field"><span>Quantidade</span><input name="quantidade" type="number" min="1" defaultValue="1" /></label>
            <label className="field"><span>Motivo</span><input name="motivo" placeholder="Compra ou uso no banho" /></label>
            <div className="acoes">
              <button className="btn pequeno" name="sentido" value="entrada" type="submit">Entrada</button>
              <button className="btn pequeno ghost" name="sentido" value="saida" type="submit">Saída</button>
            </div>
          </form>
        </article>
      )) : <Vazio icone={Package} titulo="Estoque ainda vazio" texto="Inclua um produto no catálogo. A quantidade e o mínimo passam a aparecer aqui." />)}
    </>
  );
}

function Financeiro({ api, run }) {
  const hoje = new Date();
  const { dados, erro, carregar } = useCarga(api, `/api/financeiro?ano=${hoje.getFullYear()}&mes=${hoje.getMonth() + 1}`);
  const [descricao, setDescricao] = useState("");
  const [valor, setValor] = useState("");
  const [quando, setQuando] = useState(isoDate(hoje));
  const aviso = espera(erro, dados);
  return (
    <>
      <Cabecalho kicker="O mês da loja" titulo="Financeiro" sub="O que entrou nas vendas e o que saiu em despesa. O dinheiro contado na gaveta continua na tela de caixas: Pix e cartão não ficam lá." />
      {aviso || (
        <>
          <section className="stats">
            <article className="stat"><span>Recebido no mês</span><b>{moeda(dados.recebido)}</b></article>
            <article className="stat"><span>Despesas</span><b>{moeda(dados.gasto)}</b></article>
            <article className="stat"><span>Resultado</span><b>{moeda(dados.resultado)}</b></article>
            <article className="stat"><span>Em dinheiro</span><b>{moeda(dados.dinheiro)}</b></article>
          </section>
          <section className="layout">
            <div className="lista">
              <h2>Por forma de pagamento</h2>
              {Object.keys(dados.por_forma).length ? Object.entries(dados.por_forma).map(([forma, total]) => (
                <div className="item" key={forma}><div>{ROTULOS_FORMA[forma] || forma}</div><strong>{moeda(total)}</strong></div>
              )) : <Vazio icone={Landmark} titulo="Nenhuma venda neste mês" texto="Quando uma busca, um checkout ou um pacote forem recebidos, o valor entra aqui." />}
              <h2>Despesas</h2>
              {dados.despesas.length ? dados.despesas.map((item) => (
                <div className="item" key={item.id}>
                  <div><strong>{item.descricao}</strong><small>{diaMes(item.data)} · {item.categoria}</small></div>
                  <strong>{moeda(item.valor)}</strong>
                </div>
              )) : <Vazio icone={Landmark} titulo="Nenhuma despesa neste mês" texto="Aluguel, compra de produto e o que sair do caixa da loja podem ser lançados ao lado." />}
            </div>
            <form className="lista" onSubmit={(evento) => {
              evento.preventDefault();
              run(async () => {
                await api("/api/despesas", { method: "POST", body: { descricao, valor: Number(valor), data: quando, categoria: "loja" } });
                setDescricao("");
                setValor("");
                await carregar();
              });
            }}>
              <h2>Lançar despesa</h2>
              <label className="field"><span>Descrição</span><input required value={descricao} onChange={(evento) => setDescricao(evento.target.value)} /></label>
              <label className="field"><span>Valor</span><input required type="number" min="0.01" step="0.01" value={valor} onChange={(evento) => setValor(evento.target.value)} /></label>
              <label className="field"><span>Data</span><input type="date" value={quando} onChange={(evento) => setQuando(evento.target.value)} /></label>
              <button className="btn" type="submit">Lançar</button>
            </form>
          </section>
        </>
      )}
    </>
  );
}

function Whatsapp({ api, run, me }) {
  const { dados, erro, setDados } = useCarga(api, "/api/whatsapp");
  const [numero, setNumero] = useState("");
  const aviso = espera(erro, dados);
  useEffect(() => {
    if (dados && numero === "" && dados.numero) setNumero(mascaraTelefone(dados.numero));
  }, [dados, numero]);
  return (
    <>
      <Cabecalho kicker="Mensagens da loja" titulo="WhatsApp" />
      {aviso || (
        <section className="layout">
          <div>
            {me.papel === "admin" ? (
              <form className="lista" onSubmit={(evento) => {
                evento.preventDefault();
                run(async () => {
                  const salvo = await api("/api/whatsapp", { method: "PUT", body: { numero: numero.replace(/\D/g, "") } });
                  setDados(salvo);
                  setNumero(mascaraTelefone(salvo.numero || ""));
                });
              }}>
                <h2>Número da loja</h2>
                <label className="field"><span>WhatsApp com DDD</span><input value={numero} onChange={(evento) => setNumero(mascaraTelefone(evento.target.value))} placeholder="(11) 98888-7777" inputMode="tel" /></label>
                <button className="btn" type="submit">Salvar número</button>
                {dados.token ? (
                  <p className="prosa">No WhatsApp Business, aponte o webhook para <span className="webhook">http://127.0.0.1:8765/api/whatsapp/webhook</span> e use o token <span className="webhook">{dados.token}</span>.</p>
                ) : <p className="muted">Salve o número para gerar o token do webhook.</p>}
              </form>
            ) : <p className="muted">O número da loja é definido por quem administra.</p>}
          </div>
          <div className="lista">
            <h2>Mensagens</h2>
            {dados.mensagens.length ? dados.mensagens.map((item) => (
              <article className="nota" key={item.id}>
                <strong>{item.telefone ? mascaraTelefone(item.telefone) : "Sem número"}</strong>
                <span className={`pill ${item.status === "criado" ? "pronto" : "agendado"}`}>{item.status === "criado" ? "Criado" : "Pendente"}</span>
                <p>{item.texto}</p>
                <p className="muted">{item.detalhe}</p>
              </article>
            )) : <Vazio icone={MessageCircle} titulo="Nenhuma mensagem ainda" texto="Quando um tutor pedir banho, tosa ou hotel pelo WhatsApp, a mensagem aparece aqui. Se a baia couber, o horário nasce sozinho." />}
          </div>
        </section>
      )}
    </>
  );
}

function Admin({ api, run }) {
  const { dados, erro, carregar } = useCarga(api, "/api/admin/resumo");
  const [nome, setNome] = useState("");
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [papel, setPapel] = useState("recepcao");
  const [filtro, setFiltro] = useState("");
  const aviso = espera(erro, dados);
  const atividades = (dados?.atividades || []).filter((item) => !filtro || String(item.usuario_id || "") === filtro);
  return (
    <>
      <Cabecalho kicker="Quem administra" titulo="Administração" sub="Cadastre quem entra no sistema e veja o que cada pessoa fez. Ana e Bruno aparecem pelo trabalho na baia, mesmo sem login." />
      {aviso || (
        <>
          <section className="stats">
            <article className="stat"><span>Funcionários</span><b>{dados.funcionarios.length}</b></article>
            <article className="stat"><span>Atendimentos no mês</span><b>{dados.agendamentos_mes}</b></article>
            <article className="stat"><span>Vendas no mês</span><b>{moeda(dados.vendas_mes)}</b></article>
            <article className="stat"><span>Pets</span><b>{dados.pets}</b></article>
          </section>
          <section className="layout">
            <div className="lista">
              <div className="row-between">
                <h2>O que foi feito no sistema</h2>
                <select value={filtro} onChange={(evento) => setFiltro(evento.target.value)}>
                  <option value="">Toda a equipe</option>
                  {dados.funcionarios.map((pessoa) => <option key={pessoa.id} value={pessoa.id}>{pessoa.nome}</option>)}
                </select>
              </div>
              {atividades.length ? atividades.map((item) => (
                <div className="item" key={item.id}>
                  <div><strong>{item.usuario}</strong><small>{item.acao}{item.detalhe ? ` · ${item.detalhe}` : ""}</small></div>
                  <small className="muted">{diaMes(item.quando)} {horaDe(item.quando)}</small>
                </div>
              )) : <Vazio icone={ScrollText} titulo="Nada registrado ainda" texto="Abrir o caixa, marcar um horário ou receber uma busca passa a aparecer nesta lista." />}
            </div>
            <div>
              <form className="lista" onSubmit={(evento) => {
                evento.preventDefault();
                run(async () => {
                  await api("/api/admin/funcionarios", { method: "POST", body: { nome, login, senha, papel } });
                  setNome("");
                  setLogin("");
                  setSenha("");
                  await carregar();
                });
              }}>
                <h2>Cadastrar funcionário</h2>
                <label className="field"><span>Nome</span><input required value={nome} onChange={(evento) => setNome(evento.target.value)} /></label>
                <label className="field"><span>Login</span><input required value={login} onChange={(evento) => setLogin(evento.target.value)} /></label>
                <label className="field"><span>Senha</span><input required type="password" value={senha} onChange={(evento) => setSenha(evento.target.value)} /></label>
                <label className="field">
                  <span>Papel</span>
                  <select value={papel} onChange={(evento) => setPapel(evento.target.value)}>
                    <option value="recepcao">Recepção / caixa</option>
                    <option value="tosador">Banho e tosa</option>
                    <option value="veterinario">Veterinário</option>
                    <option value="estoquista">Estoque</option>
                    <option value="gerente">Gerência</option>
                    <option value="admin">Dono</option>
                  </select>
                </label>
                <button className="btn" type="submit">Cadastrar</button>
              </form>
              <div className="lista" style={{ marginTop: 14 }}>
                <h2>Na baia neste mês</h2>
                {dados.por_profissional.map((pessoa) => (
                  <div className="item" key={pessoa.id}>
                    <div>
                      <strong>{pessoa.nome}</strong>
                      <small>{pessoa.atendimentos} atendimento(s) · {pessoa.concluidos} busca(s) · {pessoa.em_andamento} em aberto</small>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
          <section className="secao lista">
            <h2>Acessos</h2>
            {dados.funcionarios.map((pessoa) => (
              <div className="item" key={pessoa.id}>
                <div><strong>{pessoa.nome}</strong><small>{pessoa.login}</small></div>
                <span className="pill">{ROTULOS_PAPEL[pessoa.papel] || pessoa.papel}</span>
              </div>
            ))}
          </section>
        </>
      )}
    </>
  );
}

function Indicadores({ api }) {
  const hoje = new Date();
  const { dados, erro } = useCarga(api, `/api/indicadores?de=${isoDate(new Date(hoje.getFullYear(), hoje.getMonth(), 1))}&ate=${isoDate(hoje)}`);
  const aviso = espera(erro, dados);
  if (aviso) return aviso;
  return (
    <>
      <Cabecalho kicker="Gestão" titulo="Indicadores" sub="Números do período, lidos das vendas pagas, das despesas quitadas e da ocupação de hoje." />
      <section className="stats">
        <article className="stat"><span>Faturamento do dia</span><b>{moeda(dados.faturamento_dia)}</b></article>
        <article className="stat"><span>Faturamento do período</span><b>{moeda(dados.faturamento)}</b></article>
        <article className="stat"><span>Despesas</span><b>{moeda(dados.despesas)}</b></article>
        <article className="stat"><span>Resultado</span><b>{moeda(dados.resultado)}</b></article>
        <article className="stat"><span>Vendas</span><b>{dados.vendas}</b></article>
        <article className="stat"><span>Ticket médio</span><b>{moeda(dados.ticket_medio)}</b></article>
        <article className="stat"><span>Agendamentos hoje</span><b>{dados.agendamentos_hoje}</b></article>
        <article className="stat"><span>Hospedados</span><b>{dados.hospedados}</b></article>
        <article className="stat"><span>Ocupação das baias</span><b>{dados.ocupacao}%</b></article>
      </section>
      <section className="layout">
        <div className="lista"><h2>Estoque no limite</h2>
          {dados.estoque_baixo.length ? dados.estoque_baixo.map((item) => <div className="item" key={item.id}><div><strong>{item.nome}</strong><small>{item.estoque} no estoque</small></div></div>) : <p className="muted">Nenhum produto no limite.</p>}
        </div>
        <div className="lista"><h2>Contas</h2>
          <p className="muted">A pagar: {dados.contas_pagar.length}. A receber da loja: {dados.contas_receber.length}.</p>
        </div>
      </section>
    </>
  );
}

function Ponto({ api }) {
  const { dados, erro, carregar } = useCarga(api, "/api/ponto");
  const [arquivo, setArquivo] = useState("");
  const [falha, setFalha] = useState("");
  const aviso = espera(erro, dados);
  async function enviar(evento) {
    const escolhido = evento.target.files?.[0];
    evento.target.value = "";
    if (!escolhido) return;
    setArquivo(escolhido.name);
    setFalha("");
    const corpo = new FormData();
    corpo.append("arquivo", escolhido);
    const resposta = await fetch("/api/ponto/afd", { method: "POST", credentials: "same-origin", body: corpo });
    const json = await resposta.json().catch(() => ({}));
    if (!resposta.ok) {
      setFalha(json?.detail?.mensagem || "Não foi possível ler o arquivo do relógio.");
      return;
    }
    await carregar();
  }
  return (
    <>
      <Cabecalho kicker="Administração" titulo="Ponto" />
      <div className="importar">
        <label className="btn">
          Escolher arquivo do relógio
          <input type="file" accept=".txt,.afd,text/plain" hidden onChange={(evento) => enviar(evento)} />
        </label>
        <span className="muted">{arquivo || "Arquivo .txt ou .afd exportado pelo relógio"}</span>
      </div>
      {falha ? <p className="alerta">{falha}</p> : null}
      {aviso || (
        <section className="lista" style={{ marginTop: 16 }}>
          <h2>Marcações</h2>
          {dados.marcacoes.length ? dados.marcacoes.map((item) => (
            <div className="item" key={`${item.origem}-${item.nsr}`}><div><strong>{item.funcionario || `PIS ${item.pis}`}</strong><small>NSR {item.nsr} · {item.quando}</small></div></div>
          )) : <p className="muted">Nenhuma marcação importada.</p>}
        </section>
      )}
    </>
  );
}

const TELAS = {
  boletins: Boletins,
  prontuario: Prontuario,
  lembretes: Lembretes,
  catalogo: Catalogo,
  estoque: Estoque,
  financeiro: Financeiro,
  whatsapp: Whatsapp,
  indicadores: Indicadores,
  ponto: Ponto,
  admin: Admin,
};

export function eGestao(page) {
  return Object.prototype.hasOwnProperty.call(TELAS, page);
}

export default function Gestao({ page, api, run, me, pessoas }) {
  const Tela = TELAS[page];
  if (!Tela) return null;
  return <Tela api={api} run={run} me={me} pessoas={pessoas} />;
}

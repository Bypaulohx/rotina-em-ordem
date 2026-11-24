import { useEffect, useState } from "react";
import { Calendar, ChevronLeft, ChevronRight, PawPrint, Wallet } from "lucide-react";
import {
  MESES_CURTOS,
  ROTULOS_FORMA,
  diaMes,
  gradeMes,
  horaDe,
  inicioSemana,
  isoDate,
  moeda,
  mascaraMoeda,
  moedaParaNumero,
  parseData,
  tituloMes,
  cobreHotel,
} from "./format.js";
import Gestao, { eGestao } from "./gestao.jsx";
import Frente from "./pdv.jsx";
import { Alertas, Avatar, Cabecalho, ICONE, IconeStat, Pill, Sugestao, Vazio, pode } from "./ui.jsx";

function BotaoNovo({ onClick }) {
  return <button className="btn" type="button" onClick={onClick}>+ Novo agendamento</button>;
}

function AcoesBaia({ baia, onPasso, onBusca, onCheckout }) {
  const agora = baia.agora;
  if (!agora) return null;
  if (baia.tipo === "hotel") {
    return <button className="btn pequeno" type="button" onClick={() => onCheckout(agora)}>Fazer checkout</button>;
  }
  if (agora.status === "agendado") {
    return (
      <>
        <button className="btn pequeno" type="button" onClick={() => onPasso(agora.id, "chegou")}>Chegou</button>
        <button className="btn pequeno ghost" type="button" onClick={() => onPasso(agora.id, "faltou")}>Faltou</button>
      </>
    );
  }
  if (agora.status === "chegou") {
    return (
      <>
        <button className="btn pequeno" type="button" onClick={() => onPasso(agora.id, "iniciar")}>Iniciar</button>
        <button className="btn pequeno ghost" type="button" onClick={() => onPasso(agora.id, "cancelar")}>Cancelar</button>
      </>
    );
  }
  if (agora.status === "em_atendimento") {
    return (
      <>
        <button className="btn pequeno" type="button" onClick={() => onPasso(agora.id, "pronto")}>Pronto</button>
        <button className="btn pequeno ghost" type="button" onClick={() => onPasso(agora.id, "cancelar")}>Cancelar</button>
      </>
    );
  }
  if (agora.status === "pronto") {
    return <button className="btn pequeno salvia" type="button" onClick={() => onBusca(agora)}>Registrar busca</button>;
  }
  return null;
}

function CartaoBaia({ baia, onPasso, onBusca, onCheckout, onLimpar }) {
  const agora = baia.agora;
  const depois = (baia.proximos || []).slice(0, 2).map((item) => `${item.pet} às ${horaDe(item.inicio)}`).join(" · ");
  let corpo;
  if (baia.limpeza && !agora) {
    corpo = (
      <>
        <p><strong>Aguardando limpeza</strong></p>
        <p className="cuidados">O animal já saiu. A baia só volta a receber horário depois da limpeza.</p>
      </>
    );
  } else if (!agora) {
    corpo = (
      <>
        <p><strong>Livre agora</strong></p>
        <p className="cuidados">{depois ? `Depois: ${depois}` : "Ninguém reservou esta baia no restante do dia."}</p>
      </>
    );
  } else if (baia.tipo === "hotel") {
    const feriado = (agora.diarias || []).find((linha) => linha.feriado);
    corpo = (
      <>
        <Avatar nome={agora.pet} />
        <div>
          <strong>{agora.pet}</strong> <Pill status={agora.status} />
          <div className="muted">{agora.cliente} · até {diaMes(agora.checkout_previsto)}</div>
        </div>
        <p className="cuidados">{agora.cuidados || "Sem cuidado anotado."}</p>
        {feriado ? <p className="credito">Diária de feriado: {feriado.feriado} em {diaMes(feriado.data)}</p> : null}
      </>
    );
  } else {
    corpo = (
      <>
        <Avatar nome={agora.pet} />
        <div>
          <strong>{agora.pet}</strong> <Pill status={agora.status} />
          <div className="muted">{agora.servico} · busca {horaDe(agora.busca_prevista)} · {agora.profissional}</div>
        </div>
        <p className="cuidados">{agora.cuidados || "Sem cuidado anotado."}</p>
        {agora.atraso?.atrasou ? (
          <p className="credito">Busca atrasada {agora.atraso.minutos} min. A baia segue ocupada. Sugestão de atraso: {moeda(agora.atraso.valor)}.</p>
        ) : null}
        {baia.tambem?.length ? <p className="muted">Sem baixa também: {baia.tambem.join(", ")}.</p> : null}
        {depois ? <p className="muted">Depois: {depois}</p> : null}
      </>
    );
  }
  return (
    <article className={`baia ${agora ? "ocupada" : "livre"}`}>
      <header><strong>{baia.nome}</strong><span className="porte">{baia.porte}</span></header>
      {corpo}
      <div className="acoes">
        <AcoesBaia baia={baia} onPasso={onPasso} onBusca={onBusca} onCheckout={onCheckout} />
        {baia.limpeza && !agora ? <button className="btn pequeno" type="button" onClick={() => onLimpar(baia.id)}>Limpeza feita</button> : null}
      </div>
    </article>
  );
}

function Painel({ dados, sugestao, acoes, me }) {
  const recentes = dados.recentes || [];
  const operaCaixa = pode(me?.papel, "caixas");
  const lojaVazia = !dados.pets && !dados.clientes && !dados.agendamentos_hoje && !Number(dados.vendas_mes) && !dados.caixa && !recentes.length;
  if (lojaVazia) {
    return (
      <>
        <Cabecalho kicker="Painel" titulo="Visão geral" sub="A loja ainda não tem rotina. O primeiro cadastro abre o restante." />
        <section className="lista primeiro-acesso">
          <div className="vazio">
            <h2>Nada por aqui ainda</h2>
            <p>Cadastre um cliente e o pet. O horário só entra quando uma baia do porte estiver livre da chegada até a busca.</p>
          </div>
          <div className="primeiro-acoes">
            <button className="linkish" type="button" onClick={acoes.abrirCliente}><strong>Cadastrar pet</strong><small>Porte, cuidado e pacote</small></button>
            <button className="linkish" type="button" onClick={() => acoes.abrirAgendamento()}><strong>Novo agendamento</strong><small>Banho, tosa ou hotel</small></button>
            {operaCaixa ? <button className="linkish" type="button" onClick={() => acoes.ir("caixas")}><strong>Abrir caixa</strong><small>O dinheiro do seu turno</small></button> : null}
          </div>
        </section>
      </>
    );
  }
  return (
    <>
      <Cabecalho kicker="Painel" titulo="Visão geral" sub="O dia da loja: quem está na baia, o que a busca ainda segura e quanto o turno já recebeu.">
        <BotaoNovo onClick={() => acoes.abrirAgendamento()} />
      </Cabecalho>
      <Alertas itens={(dados.alertas || []).filter((item) => item.tipo !== "falta" && item.tipo !== "atraso")} />
      <Sugestao sugestao={sugestao} onDispensar={acoes.dispensar} onEncaixar={acoes.encaixar} />
      <section className="stats">
        <article className="stat"><IconeStat nome="agenda" /><span>Atendimentos hoje</span><b>{dados.agendamentos_hoje}</b></article>
        <article className="stat"><IconeStat nome="pets" /><span>Pets cadastrados</span><b>{dados.pets}</b></article>
        <article className="stat"><IconeStat nome="clientes" /><span>Clientes</span><b>{dados.clientes}</b></article>
        <article className="stat"><IconeStat nome="vendas" /><span>Vendas pagas no mês</span><b>{moeda(dados.vendas_mes)}</b></article>
      </section>
      <section className="layout">
        <div className="lista">
          <div className="row-between">
            <h2>Atendimentos de hoje</h2>
            <button className="btn pequeno ghost" type="button" onClick={() => acoes.ir("agenda")}>Ver agenda</button>
          </div>
          {recentes.length ? recentes.map((item) => (
            <div className="item" key={item.id}>
              <span className="selo">
                <strong>{parseData(item.inicio).getDate()}</strong>
                <small>{MESES_CURTOS[parseData(item.inicio).getMonth()]}</small>
              </span>
              <div><strong>{item.pet}</strong><small>{item.titulo} · {horaDe(item.inicio)}</small></div>
              <Pill status={item.status} />
            </div>
          )) : <Vazio icone={Calendar} titulo="Nenhum horário marcado para hoje" texto="Se uma baia ao lado tiver pet, o turno anterior não deu baixa. Ela segue ocupada." acao={() => acoes.abrirAgendamento()} rotulo="Novo agendamento" />}
        </div>
        <div>
          <div className="lista">
            <h2>Baias agora</h2>
            <div className="atalhos">
              {[...dados.salao, ...dados.hotel].map((baia) => (
                <button className="linkish" type="button" key={`${baia.tipo}-${baia.nome}`} onClick={() => acoes.ir("mapa")}>
                  <strong>{baia.nome}</strong>
                  <small>{baia.agora ? `${baia.agora.pet}${baia.tambem?.length ? ` · +${baia.tambem.length}` : ""}` : "Livre"}</small>
                </button>
              ))}
            </div>
          </div>
          {operaCaixa ? (
            <div className="lista" style={{ marginTop: 14 }}>
              <h2>Seu caixa</h2>
              {dados.caixa ? (
                <>
                  <p><strong>{dados.caixa.nome}</strong></p>
                  <p className="muted">Dinheiro esperado na gaveta: {moeda(dados.caixa.esperado_em_dinheiro)}. Pix e cartão não entram nessa conta.</p>
                  <button className="btn pequeno" type="button" style={{ marginTop: 10 }} onClick={() => acoes.ir("caixas")}>Fechar e conferir</button>
                </>
              ) : (
                <Vazio icone={Wallet} titulo="Nenhum caixa seu está aberto" texto="O caixa de outra pessoa não aparece aqui. Abra o seu para receber." acao={() => acoes.ir("caixas")} rotulo="Abrir caixa" />
              )}
            </div>
          ) : null}
        </div>
      </section>
    </>
  );
}

function Mapa({ dados, sugestao, acoes }) {
  function limpar(id) {
    acoes.limparBaia(id);
  }
  const fila = dados.fila || [];
  return (
    <>
      <Cabecalho kicker="A vaga de verdade" titulo="Mapa de baias" sub="O horário só confirma se a baia do porte cabe da chegada até a busca. No hotel, a baia fica ocupada por noite — e feriado muda a diária.">
        <BotaoNovo onClick={() => acoes.abrirAgendamento()} />
      </Cabecalho>
      {dados.feriado_hoje ? <div className="alerta feriado">Hoje é {dados.feriado_hoje}. Diária de hotel deste dia usa o valor de feriado.</div> : null}
      <Alertas itens={(dados.alertas || []).filter((item) => item.tipo !== "falta" && item.tipo !== "atraso")} />
      <Sugestao sugestao={sugestao} onDispensar={acoes.dispensar} onEncaixar={acoes.encaixar} />
      <section className="secao">
        <h2>Salão</h2>
        <div className="grade-baias">
          {dados.salao.map((baia) => (
            <CartaoBaia key={baia.nome} baia={baia} onPasso={acoes.passo} onBusca={acoes.abrirBusca} onCheckout={acoes.abrirCheckout} onLimpar={limpar} />
          ))}
        </div>
      </section>
      <section className="secao">
        <h2>Hotel</h2>
        <div className="grade-baias">
          {dados.hotel.map((baia) => (
            <CartaoBaia key={baia.nome} baia={baia} onPasso={acoes.passo} onBusca={acoes.abrirBusca} onCheckout={acoes.abrirCheckout} onLimpar={limpar} />
          ))}
        </div>
      </section>
      <section className="secao lista">
        <h2>Fila de encaixe</h2>
        {fila.length ? fila.map((item) => (
          <div className="item" key={item.id}>
            <Avatar nome={item.pet} />
            <div><strong>{item.pet}</strong><small>{item.cliente} · {item.servico} · porte {item.porte}</small></div>
            <Pill status={item.status} />
          </div>
        )) : <Vazio icone={PawPrint} titulo="Ninguém na fila" texto="Quando um horário não cabe na baia, o pet pode esperar um encaixe neste dia." />}
      </section>
    </>
  );
}

function eventosDoDia(dados, profissional, iso) {
  const banhos = (dados.agendamentos || []).filter((item) => item.inicio.slice(0, 10) === iso && (!profissional || String(item.profissional_id) === profissional));
  const hoteis = (dados.hospedagens || []).filter((item) => (item.diarias || []).some((linha) => linha.data === iso) || cobreHotel(item, iso));
  const feriado = (dados.feriados || []).find((item) => item.data === iso);
  return { banhos, hoteis, feriado };
}

function Agenda({ dados, catalogo, cursor, modo, profissional, acoes }) {
  const profissionais = catalogo.profissionais || [];
  const periodoVazio = !(dados.agendamentos || []).length && !(dados.hospedagens || []).length;
  let corpo;
  if (modo === "lista") {
    const itens = (dados.agendamentos || []).filter((item) => !profissional || String(item.profissional_id) === profissional);
    corpo = (
      <div className="lista">
        {itens.length ? itens.map((item) => (
          <div className="item" key={item.id}>
            <Avatar nome={item.pet} />
            <div><strong>{item.pet}</strong><small>{diaMes(item.inicio)} {horaDe(item.inicio)} · {item.baia} · busca {horaDe(item.busca_prevista)}</small></div>
            <Pill status={item.status} />
          </div>
        )) : <Vazio icone={Calendar} titulo="Nenhum atendimento no período" texto="A agenda deste intervalo ainda está livre." acao={() => acoes.abrirAgendamento()} rotulo="Novo agendamento" />}
      </div>
    );
  } else if (modo === "semana") {
    const inicio = inicioSemana(cursor);
    const dias = Array.from({ length: 7 }, (_, i) => new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate() + i));
    corpo = (
      <div className="rolagem"><div className="semana">
        {dias.map((dia) => {
          const iso = isoDate(dia);
          const ev = eventosDoDia(dados, profissional, iso);
          return (
            <article key={iso}>
              <strong>{dia.getDate()} {MESES_CURTOS[dia.getMonth()]}</strong>
              {ev.feriado ? <span className="feriado">{ev.feriado.nome}</span> : null}
              {ev.banhos.map((item) => <span className="evento" key={`b-${item.id}`}>{horaDe(item.inicio)} {item.pet}</span>)}
              {ev.hoteis.map((item) => <span className="evento hotel" key={`h-${item.id}`}>Hotel · {item.pet}</span>)}
            </article>
          );
        })}
      </div></div>
    );
  } else {
    const hoje = isoDate(new Date());
    corpo = (
      <div className="rolagem"><div className="cal">
        {["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"].map((nome) => <div className="dow" key={nome}>{nome}</div>)}
        {gradeMes(cursor).map((dia) => {
          const iso = isoDate(dia);
          const ev = eventosDoDia(dados, profissional, iso);
          const fora = dia.getMonth() !== cursor.getMonth() ? "fora" : "";
          const ehHoje = iso === hoje ? "hoje" : "";
          return (
            <div className={`dia ${fora} ${ehHoje}`} key={iso + fora}>
              <span className="num">{dia.getDate()}</span>
              {ev.feriado ? <span className="feriado">{ev.feriado.nome}</span> : null}
              {ev.banhos.slice(0, 3).map((item) => <span className="evento" key={item.id}>{item.pet}</span>)}
              {ev.hoteis.slice(0, 2).map((item) => <span className="evento hotel" key={`h-${item.id}`}>{`Hospedagem`}</span>)}
            </div>
          );
        })}
      </div></div>
    );
  }
  return (
    <>
      <Cabecalho kicker="Rotina em ordem" titulo="Agenda & hotel" sub="Banho, tosa e hospedagem no mesmo calendário. A confirmação continua dependendo da baia.">
        <BotaoNovo onClick={() => acoes.abrirAgendamento()} />
      </Cabecalho>
      <div className="controles">
        <div className="segmento">
          {[["mes", "Mês"], ["semana", "Semana"], ["lista", "Lista"]].map(([id, nome]) => (
            <button type="button" key={id} className={modo === id ? "active" : ""} onClick={() => acoes.modo(id)}>{nome}</button>
          ))}
        </div>
        <label className="field filtro">
          <span>Profissional</span>
          <select value={profissional} onChange={(evento) => acoes.profissional(evento.target.value)}>
            <option value="">Toda a equipe</option>
            {profissionais.map((pessoa) => <option key={pessoa.id} value={pessoa.id}>{pessoa.nome}</option>)}
          </select>
        </label>
        <div className="mes-nav">
          <button className="icon-btn" type="button" onClick={() => acoes.mover(-1)} aria-label="Período anterior"><ChevronLeft {...ICONE} /></button>
          <strong>{tituloMes(cursor)}</strong>
          <button className="icon-btn" type="button" onClick={() => acoes.mover(1)} aria-label="Próximo período"><ChevronRight {...ICONE} /></button>
          <button className="btn pequeno ghost" type="button" onClick={acoes.hoje}>Hoje</button>
        </div>
      </div>
      {periodoVazio && modo !== "lista" ? <Vazio icone={Calendar} titulo="Este período ainda está livre" texto="O calendário continua aqui. O horário entra quando a baia do porte couber até a busca." acao={() => acoes.abrirAgendamento()} rotulo="Novo agendamento" /> : null}
      {corpo}
    </>
  );
}

function Vendas({ dados, busca, acoes }) {
  const termo = busca.toLowerCase();
  const vendas = (dados || []).filter((venda) => {
    const texto = `${venda.numero} ${venda.cliente} ${venda.itens.map((item) => item.descricao).join(" ")}`.toLowerCase();
    return texto.includes(termo);
  });
  return (
    <>
      <Cabecalho kicker="Balcão" titulo="Vendas" sub="Cada recebimento nasce de uma busca, de um checkout ou de um pacote. E entra no caixa que está aberto.">
        <span className="acoes">
          <button className="btn ghost" type="button" onClick={() => acoes.ir("pdv")}>Frente de caixa</button>
          <button className="btn" type="button" onClick={acoes.abrirVenda}>+ Nova venda</button>
        </span>
      </Cabecalho>
      {(dados || []).length ? <input className="busca" placeholder="Buscar venda ou cliente..." value={busca} onChange={(evento) => acoes.buscaVenda(evento.target.value)} /> : null}
      {vendas.length ? vendas.map((venda) => (
        <article className="venda" key={venda.id}>
          <Avatar nome={venda.cliente} />
          <div>
            <strong>Venda #{venda.numero} — {venda.cliente}</strong>
            <small className="muted">{venda.itens.map((item) => item.descricao).join(" · ")} · {venda.forma_rotulo}</small>
          </div>
          <div className="valor">
            <strong>{moeda(venda.total)}</strong>
            <Pill status={venda.status} />
            <div className="muted">{diaMes(venda.criada_em)}</div>
          </div>
        </article>
      )) : <Vazio icone={Wallet} titulo={(dados || []).length ? "Nenhuma venda com esse termo" : "Nenhuma venda ainda"} texto={(dados || []).length ? "Tente outro nome, número ou o que foi vendido." : "A primeira venda nasce de uma busca, de um checkout ou de um pacote."} acao={(dados || []).length ? undefined : acoes.abrirVenda} rotulo="Nova venda" />}
    </>
  );
}

function CaixaAberto({ caixa, api, aoMudar, aoFechar }) {
  const [valor, setValor] = useState("0,00");
  const [motivo, setMotivo] = useState("");
  const [operadores, setOperadores] = useState([]);
  const [destino, setDestino] = useState("");
  useEffect(() => {
    api("/api/caixas/operadores").then(setOperadores).catch(() => {});
  }, [api]);
  async function mover(tipo) {
    await api(`/api/caixas/${caixa.id}/movimento`, { method: "POST", body: { tipo, valor: moedaParaNumero(valor), motivo } });
    setMotivo("");
    await aoMudar();
  }
  return (
    <div className="caixa-acoes">
      <div className="form-grid">
        <label className="field"><span>Valor</span><input inputMode="numeric" value={valor} onChange={(evento) => setValor(mascaraMoeda(evento.target.value))} /></label>
        <label className="field"><span>Motivo</span><input value={motivo} onChange={(evento) => setMotivo(evento.target.value)} /></label>
      </div>
      <div className="acoes">
        <button className="btn pequeno ghost" type="button" onClick={() => mover("suprimento")}>Suprimento</button>
        <button className="btn pequeno ghost" type="button" onClick={() => mover("sangria")}>Sangria</button>
        <button className="btn pequeno" type="button" onClick={aoFechar}>Fechar e conferir</button>
      </div>
      <div className="form-grid">
        <label className="field"><span>Passar o caixa</span>
          <select value={destino} onChange={(evento) => setDestino(evento.target.value)}>
            <option value="">Escolha quem recebe</option>
            {operadores.map((pessoa) => <option key={pessoa.id} value={pessoa.id}>{pessoa.nome}</option>)}
          </select>
        </label>
        <button className="btn pequeno ghost" type="button" onClick={async () => {
          if (!destino) return;
          await api(`/api/caixas/${caixa.id}/transferir`, { method: "POST", body: { usuario_id: Number(destino) } });
          await aoMudar();
        }}>Transferir</button>
      </div>
    </div>
  );
}

function Caixas({ dados, acoes, api }) {
  const caixas = dados || [];
  return (
    <>
      <Cabecalho kicker="Movimento de caixa" titulo="Caixas e turnos">
        {caixas.length ? null : <button className="btn" type="button" onClick={acoes.abrirCaixa}>+ Abrir caixa</button>}
      </Cabecalho>
      {caixas.length ? caixas.map((caixa) => (
        <article className="caixa" key={caixa.id}>
          <div className="icone-suave"><Wallet {...ICONE} /></div>
          <div>
            <strong>{caixa.nome}</strong>
            <div className="muted">
              Aberto em {diaMes(caixa.aberto_em)} {horaDe(caixa.aberto_em)}
              {caixa.operador ? ` por ${caixa.operador}` : ""} · inicial {moeda(caixa.saldo_inicial)}
            </div>
            <div className="muted">
              {Object.keys(caixa.por_forma || {}).length
                ? Object.entries(caixa.por_forma).map(([forma, total]) => <div key={forma}>{ROTULOS_FORMA[forma] || forma} · {moeda(total)}</div>)
                : "Sem vendas neste caixa."}
            </div>
            {caixa.status === "aberto" ? null : <div className="muted">Dinheiro esperado na gaveta: {moeda(caixa.esperado_em_dinheiro)}</div>}
            {caixa.saldo_informado != null ? <div>{caixa.fechado_por ? `Contado por ${caixa.fechado_por}` : "Contado"}: {moeda(caixa.saldo_informado)} · diferença {moeda(caixa.diferenca)}</div> : null}
            {(caixa.vendas || []).length ? (
              <div className="vendas-caixa">
                {caixa.vendas.map((venda) => (
                  <div className="item" key={venda.id}>
                    <div>
                      <strong>{horaDe(venda.criada_em)} · {venda.cliente}</strong>
                      <small>{(venda.itens || []).map((item) => `${item.quantidade && item.quantidade !== 1 ? `${item.quantidade}× ` : ""}${item.descricao}`).join(" · ")} · {ROTULOS_FORMA[venda.forma] || venda.forma}</small>
                    </div>
                    <strong>{moeda(venda.total)}</strong>
                  </div>
                ))}
              </div>
            ) : null}
            {(caixa.movimentos || []).length ? (
              <div className="muted">
                {caixa.movimentos.map((mov) => <div key={mov.id}>{mov.tipo} · {mov.motivo || "sem motivo"} · {moeda(mov.valor)}</div>)}
              </div>
            ) : null}
            {caixa.status === "aberto" ? (
              <CaixaAberto caixa={caixa} api={api} aoMudar={acoes.recarregar} aoFechar={() => acoes.fecharCaixa(caixa)} />
            ) : null}
          </div>
          <div className="lado"><Pill status={caixa.status} /></div>
        </article>
      )) : <Vazio icone={Wallet} titulo="Nenhum caixa seu está aberto" texto="O caixa de outra pessoa não aparece aqui. Abra o seu para receber." acao={acoes.abrirCaixa} rotulo="Abrir caixa" />}
    </>
  );
}

function Ficha({ ficha, tipo, onVoltar, onPacote }) {
  if (tipo === "cliente") {
    return (
      <>
        <Cabecalho kicker="Cliente" titulo={ficha.nome} sub={`${ficha.telefone} · ${[ficha.logradouro, ficha.numero, ficha.cidade].filter(Boolean).join(", ")}`}>
          <button className="btn ghost" type="button" onClick={onVoltar}>Voltar</button>
        </Cabecalho>
        {ficha.observacoes ? <p>{ficha.observacoes}</p> : null}
        <section className="lista"><h2>Animais</h2>
          {ficha.pets.map((pet) => (
            <div className="item" key={pet.id}><div><strong>{pet.nome}</strong><small>{(pet.pacotes || []).map((pacote) => `${pacote.nome}: ${pacote.restantes} restantes`).join(" · ") || "Sem pacote"}</small></div></div>
          ))}
        </section>
        <section className="lista"><h2>Compras</h2>
          {ficha.compras.length ? ficha.compras.map((venda) => <div className="item" key={venda.id}><div><strong>#{venda.numero}</strong><small>{venda.forma_rotulo}</small></div><strong>{moeda(venda.total)}</strong></div>) : <p className="muted">Nenhuma compra.</p>}
        </section>
      </>
    );
  }
  const pet = ficha.pet;
  return (
    <>
      <Cabecalho kicker="Animal" titulo={pet.nome} sub={`${ficha.cliente?.nome || ""} · ${pet.especie}${pet.raca ? ` · ${pet.raca}` : ""}`}>
        <button className="btn ghost" type="button" onClick={onVoltar}>Voltar</button>
      </Cabecalho>
      {pet.foto ? <img className="foto-pet" src={pet.foto} alt="" /> : null}
      <section className="lista"><h2>Pacotes</h2>
        {ficha.pacotes.length ? ficha.pacotes.map((pacote) => (
          <div className="item" key={pacote.id}><div><strong>{pacote.nome}</strong><small>Usadas {pacote.utilizadas} · restantes {pacote.restantes}</small></div></div>
        )) : <p className="muted">Nenhum pacote contratado.</p>}
        <button className="btn pequeno" type="button" onClick={() => onPacote(pet)}>Vender pacote</button>
      </section>
      <section className="lista"><h2>Atendimentos</h2>
        {ficha.atendimentos.length ? ficha.atendimentos.map((item) => <div className="item" key={item.id}><div><strong>{item.servico}</strong><small>{diaMes(item.inicio)} {horaDe(item.inicio)}</small></div><Pill status={item.status} /></div>) : <p className="muted">Sem atendimento.</p>}
      </section>
      <section className="lista"><h2>Hospedagens</h2>
        {ficha.hospedagens.length ? ficha.hospedagens.map((item) => <div className="item" key={item.id}><div><strong>Hotel</strong><small>até {diaMes(item.checkout_previsto)}</small></div><Pill status={item.status} /></div>) : <p className="muted">Sem hospedagem.</p>}
      </section>
      <section className="lista"><h2>Prontuário</h2>
        {ficha.prontuario.length ? ficha.prontuario.map((nota, indice) => <div className="nota" key={indice}><small>{nota.quando}</small><p>{nota.texto}</p></div>) : <p className="muted">Sem anotação.</p>}
      </section>
    </>
  );
}

function Pets({ pessoas, acoes, api }) {
  const [ficha, setFicha] = useState(null);
  const [tipo, setTipo] = useState("");
  async function abrir(url, qual) {
    setTipo(qual);
    setFicha(await api(url));
  }
  if (ficha) return <Ficha ficha={ficha} tipo={tipo} onVoltar={() => setFicha(null)} onPacote={acoes.abrirPacote} />;
  return (
    <>
      <Cabecalho kicker="Cadastro" titulo="Pets & clientes" sub="O serviço nasce do pet: porte, cuidado e o crédito do pacote já vêm com ele.">
        <button className="btn" type="button" onClick={acoes.abrirCliente}>+ Cadastrar</button>
      </Cabecalho>
      {pessoas.length ? pessoas.map((cliente) => (
        <article className="pessoa" key={cliente.id}>
          <button className="linkish" type="button" onClick={() => abrir(`/api/clientes/${cliente.id}`, "cliente")}><strong>{cliente.nome}</strong></button>
          <div className="muted">
            {cliente.telefone || "Sem telefone"} · {[cliente.logradouro, cliente.bairro, cliente.cidade, cliente.uf].filter(Boolean).join(", ") || "Sem endereço"}
          </div>
          <div className="pets" style={{ marginTop: 12 }}>
            {cliente.pets.map((pet) => (
              <div className="pet" key={pet.id}>
                <Avatar nome={pet.nome} />
                <div>
                  <strong>{pet.nome}</strong> <span className="porte">{pet.porte}</span>
                  <div className="muted">{pet.especie} · {pet.alimentacao || "Alimentação não anotada"}</div>
                  <div className="cuidados">{pet.cuidados || "Sem observação de cuidado."}</div>
                  <div className="credito">Pacote: {pet.creditos.banho} banho(s), {pet.creditos.tosa} tosa(s)</div>
                </div>
                <div className="acoes-pet">
                  <button className="btn pequeno ghost" type="button" onClick={() => abrir(`/api/pets/${pet.id}/ficha`, "pet")}>Ficha</button>
                  <button className="btn pequeno ghost" type="button" onClick={() => acoes.abrirPacote(pet)}>Vender pacote</button>
                </div>
              </div>
            ))}
          </div>
        </article>
      )) : <Vazio icone={PawPrint} titulo="Nenhum pet ainda" texto="O serviço nasce do pet. Porte, cuidado e o crédito do pacote passam a vir com ele." acao={acoes.abrirCliente} rotulo="Cadastrar" />}
    </>
  );
}

export default function Pagina(props) {
  const { page, dados, pessoas } = props;
  if (eGestao(page)) return <Gestao page={page} api={props.api} run={props.run} me={props.me} pessoas={pessoas} />;
  if (page === "pets") return <Pets pessoas={pessoas} acoes={props.acoes} api={props.api} />;
  if (!dados) return <p className="muted">Carregando a rotina...</p>;
  if (page === "painel") return <Painel {...props} />;
  if (page === "mapa") return <Mapa {...props} />;
  if (page === "agenda") return <Agenda {...props} />;
  if (page === "pdv") return <Frente dados={dados} pessoas={pessoas} me={props.me} api={props.api} acoes={props.acoes} />;
  if (page === "vendas") return <Vendas dados={dados} busca={props.buscaVenda} acoes={props.acoes} />;
  if (page === "caixas") return <Caixas dados={dados} acoes={props.acoes} api={props.api} />;
  return null;
}

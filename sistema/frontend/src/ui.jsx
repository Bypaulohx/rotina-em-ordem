import { BarChart3, Bell, BookOpen, Calendar, Clock, Landmark, LayoutGrid, Map, MessageCircle, NotebookPen, Package, PawPrint, ScrollText, Shield, ShoppingBag, Users, Wallet } from "lucide-react";
import { STATUS } from "./format.js";

export const GRUPOS = [
  ["Operação", [
    ["painel", "Visão geral", LayoutGrid],
    ["mapa", "Mapa de baias", Map],
    ["agenda", "Agenda & hotel", Calendar],
    ["vendas", "Vendas", ShoppingBag],
    ["pets", "Pets & clientes", PawPrint],
    ["caixas", "Caixas e turnos", Wallet],
  ]],
  ["Loja", [
    ["boletins", "Boletins", ScrollText],
    ["prontuario", "Prontuário", NotebookPen],
    ["lembretes", "Lembretes", Bell],
    ["catalogo", "Catálogo", BookOpen],
    ["estoque", "Estoque", Package],
    ["financeiro", "Financeiro", Landmark],
    ["indicadores", "Indicadores", BarChart3],
    ["whatsapp", "WhatsApp", MessageCircle],
  ]],
  ["Administração", [
    ["ponto", "Ponto", Clock],
    ["admin", "Administração", Shield],
  ]],
];

export const ACESSOS = {
  gerente: ["painel", "mapa", "agenda", "vendas", "pets", "boletins", "lembretes", "catalogo", "estoque", "financeiro", "indicadores", "whatsapp", "ponto"],
  recepcao: ["painel", "mapa", "agenda", "vendas", "pets", "caixas", "whatsapp"],
  equipe: ["painel", "mapa", "agenda", "vendas", "pets", "caixas", "whatsapp"],
  tosador: ["painel", "mapa", "agenda", "pets", "boletins", "lembretes"],
  veterinario: ["agenda", "pets", "boletins", "prontuario", "lembretes"],
  estoquista: ["vendas", "pets", "catalogo", "estoque"],
};

export const ROTULOS_PAPEL = {
  admin: "Dono",
  gerente: "Gerência",
  recepcao: "Recepção",
  equipe: "Recepção",
  tosador: "Banho e tosa",
  veterinario: "Veterinário",
  estoquista: "Estoque",
};

export function pode(papel, pagina) {
  if (papel === "admin") return true;
  return (ACESSOS[papel] || ACESSOS.recepcao).includes(pagina);
}

export function primeiraPagina(papel) {
  if (papel === "admin") return "painel";
  return (ACESSOS[papel] || ACESSOS.recepcao)[0];
}

export const ICONE = { size: 16, strokeWidth: 1.75 };

export function Pill({ status }) {
  return <span className={`pill ${status}`}>{STATUS[status] || status}</span>;
}

export function Avatar({ nome }) {
  return <span className="avatar">{(nome || "?").slice(0, 1).toUpperCase()}</span>;
}

export function Cabecalho({ kicker, titulo, sub, children }) {
  return (
    <header className="page-head">
      <div>
        <p className="kicker">{kicker}</p>
        <h1>{titulo}</h1>
      </div>
      {children}
    </header>
  );
}

export function Alertas({ itens = [] }) {
  if (!itens.length) return null;
  return (
    <div className="alertas">
      {itens.map((item) => (
        <div className={`alerta ${item.tipo || ""}`} key={item.texto}>{item.texto}</div>
      ))}
    </div>
  );
}

export function Sugestao({ sugestao, onDispensar, onEncaixar }) {
  if (!sugestao) return null;
  return (
    <div className="sugestao">
      <div>
        <strong>{sugestao.baia} ficou livre.</strong>
        <div className="muted">{sugestao.pet} está na fila, porte {sugestao.porte}. Dá para encaixar neste intervalo.</div>
      </div>
      <div className="acoes">
        <button className="btn pequeno ghost" type="button" onClick={onDispensar}>Agora não</button>
        <button className="btn pequeno" type="button" onClick={onEncaixar}>Encaixar {sugestao.pet}</button>
      </div>
    </div>
  );
}

export function Vazio({ titulo, texto, acao, rotulo }) {
  return (
    <div className="vazio">
      <strong>{titulo}</strong>
      <p>{texto}</p>
      {acao && rotulo ? <button className="btn pequeno" type="button" onClick={acao}>{rotulo}</button> : null}
    </div>
  );
}

export function IconeStat({ nome }) {
  const Icone = { agenda: Calendar, pets: PawPrint, clientes: Users, vendas: ShoppingBag, caixa: Wallet }[nome];
  return (
    <div className="icone">
      <Icone {...ICONE} />
    </div>
  );
}

export const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
export const MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

export const STATUS = {
  agendado: "Agendado",
  chegou: "Chegou",
  em_atendimento: "Em atendimento",
  pronto: "Pronto",
  buscado: "Buscado",
  cancelado: "Cancelado",
  faltou: "Faltou",
  hospedada: "No hotel",
  reservada: "Reservada",
  finalizada: "Checkout",
  paga: "Paga",
  aberto: "Aberto",
  fechado: "Fechado",
  aguardando: "Na fila",
};

export const FORMAS = [
  ["pix", "Pix"],
  ["dinheiro", "Dinheiro"],
  ["debito", "Débito"],
  ["credito", "Crédito"],
];

export const ROTULOS_FORMA = {
  pix: "Pix",
  dinheiro: "Dinheiro",
  debito: "Débito",
  credito: "Crédito",
  pacote: "Pacote",
  misto: "Misto",
};

export function moeda(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function pad(n) {
  return String(n).padStart(2, "0");
}

export function isoDate(data) {
  return `${data.getFullYear()}-${pad(data.getMonth() + 1)}-${pad(data.getDate())}`;
}

export function isoLocal(data) {
  return `${isoDate(data)}T${pad(data.getHours())}:${pad(data.getMinutes())}`;
}

export function parseData(iso) {
  const [ano, mes, dia] = iso.slice(0, 10).split("-").map(Number);
  return new Date(ano, mes - 1, dia);
}

export function diaMes(iso) {
  if (!iso) return "";
  const data = parseData(iso);
  return `${pad(data.getDate())}/${pad(data.getMonth() + 1)}`;
}

export function horaDe(iso) {
  return iso && iso.includes("T") ? iso.slice(11, 16) : "";
}

export function tituloMes(cursor) {
  const nome = MESES[cursor.getMonth()];
  return `${nome.charAt(0).toUpperCase()}${nome.slice(1)} de ${cursor.getFullYear()}`;
}

export function inicioSemana(data) {
  const copia = new Date(data.getFullYear(), data.getMonth(), data.getDate());
  const desloca = (copia.getDay() + 6) % 7;
  copia.setDate(copia.getDate() - desloca);
  return copia;
}

export function gradeMes(cursor) {
  const primeiro = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
  const inicio = inicioSemana(primeiro);
  return Array.from({ length: 42 }, (_, i) => new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate() + i));
}

export function intervaloAgenda(modo, cursor) {
  if (modo === "lista") {
    const de = new Date();
    const ate = new Date();
    ate.setDate(ate.getDate() + 45);
    return [de, ate];
  }
  if (modo === "semana") {
    const de = inicioSemana(cursor);
    return [de, new Date(de.getFullYear(), de.getMonth(), de.getDate() + 6)];
  }
  const grade = gradeMes(cursor);
  return [grade[0], grade[grade.length - 1]];
}

export function proximaHora() {
  const data = new Date();
  data.setMinutes(0, 0, 0);
  data.setHours(data.getHours() + 1);
  return data;
}

export function calcularBusca(inicioIso, duracaoMin) {
  const data = new Date(inicioIso);
  if (Number.isNaN(data.getTime())) return "";
  data.setMinutes(data.getMinutes() + Number(duracaoMin || 0) + 20);
  return isoLocal(data);
}

export function petPorId(pessoas, id) {
  for (const cliente of pessoas) {
    const pet = cliente.pets.find((item) => item.id === Number(id));
    if (pet) return { cliente, pet };
  }
  return null;
}

export function mensagemErro(data) {
  if (data?.detail?.mensagem) return data.detail.mensagem;
  if (typeof data?.detail === "string") return data.detail;
  return "Não foi possível concluir.";
}

export function mascaraTelefone(valor) {
  const digitos = String(valor || "").replace(/\D/g, "").slice(0, 11);
  if (digitos.length <= 10) {
    const parte = digitos.replace(/^(\d{2})(\d{0,4})(\d{0,4}).*/, (_, ddd, meio, fim) => {
      let texto = ddd ? `(${ddd}` : "";
      if (meio) texto += `) ${meio}`;
      if (fim) texto += `-${fim}`;
      return texto;
    });
    return digitos.length ? parte : "";
  }
  return digitos.replace(/^(\d{2})(\d{5})(\d{0,4}).*/, "($1) $2-$3");
}

export function mascaraCep(valor) {
  const digitos = String(valor || "").replace(/\D/g, "").slice(0, 8);
  return digitos.length > 5 ? `${digitos.slice(0, 5)}-${digitos.slice(5)}` : digitos;
}

export function mascaraMoeda(valor) {
  const digitos = String(valor ?? "").replace(/\D/g, "").slice(0, 12);
  const numero = Number(digitos || "0") / 100;
  return numero.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function moedaParaNumero(texto) {
  const limpo = String(texto || "").replace(/\./g, "").replace(",", ".");
  const numero = Number(limpo);
  return Number.isFinite(numero) ? numero : 0;
}

export function mascaraCpf(valor) {
  const digitos = String(valor || "").replace(/\D/g, "").slice(0, 11);
  return digitos
    .replace(/^(\d{3})(\d)/, "$1.$2")
    .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1-$2");
}

export const PALETA = [
  ["#1f6b4a", "Verde"],
  ["#1b4f6b", "Azul"],
  ["#6b3d45", "Vinho"],
  ["#6b4a1f", "Areia"],
];

export function aplicarCor(cor) {
  const accent = /^#[0-9a-fA-F]{6}$/.test(cor || "") ? cor : "#1f6b4a";
  const n = Number.parseInt(accent.slice(1), 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  const hex = (rv, gv, bv) => `#${[rv, gv, bv].map((valor) => Math.max(0, Math.min(255, valor)).toString(16).padStart(2, "0")).join("")}`;
  const raiz = document.documentElement.style;
  raiz.setProperty("--accent", accent);
  raiz.setProperty("--accent-2", hex(Math.round(r * 0.72), Math.round(g * 0.72), Math.round(b * 0.72)));
  raiz.setProperty("--accent-soft", hex(Math.round(r * 0.12 + 231), Math.round(g * 0.12 + 242), Math.round(b * 0.12 + 236)));
  raiz.setProperty("--accent-line", hex(Math.round(r * 0.45 + 140), Math.round(g * 0.45 + 170), Math.round(b * 0.45 + 160)));
}

export function documento(titulo, corpo, aviso) {
  const janela = window.open("", "_blank", "noopener,width=760,height=900");
  if (!janela) return;
  janela.document.write(`<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>${titulo}</title><style>body{font-family:"IBM Plex Sans",sans-serif;color:#1b2420;margin:32px}h1{font-size:22px;font-weight:600}table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #d9ddd8;text-align:left;padding:8px 0;font-weight:500}.aviso{color:#5c675f;font-size:12px}</style></head><body><h1>${titulo}</h1>${corpo}<p class="aviso">${aviso || ""}</p></body></html>`);
  janela.document.close();
  janela.focus();
  janela.print();
}

export function tabelaItens(itens, total) {
  const linhas = itens.map((item) => `<tr><td>${item.descricao}</td><td>${item.quantidade || 1}</td><td>${moeda(item.valor)}</td></tr>`).join("");
  return `<table><thead><tr><th>Item</th><th>Qtd</th><th>Valor</th></tr></thead><tbody>${linhas}</tbody></table><p><strong>Total ${moeda(total)}</strong></p>`;
}

export function cobreHotel(item, iso) {
  if ((item.diarias || []).length) return item.diarias.some((linha) => linha.data === iso);
  const fim = item.checkout_real || item.checkout_previsto;
  return item.entrada <= iso && iso < fim;
}

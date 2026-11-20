export const FALLBACK_MANDATOS: readonly string[] = [
  "2025-2028",
  "2021-2024",
  "2017-2020",
];

/**
 * Normaliza separadores (meia-risca, travessão, hífen) e espaços de um rótulo de Mandato Municipal.
 */
export function normalizarMandatoLabel(mandato: string): string {
  return mandato.replace(/[–—]/g, "-").replace(/\s*-\s*/g, "-").trim();
}

/**
 * Extrai os limites numéricos [anoInicio, anoFim] de um Mandato Municipal, ou nulo se inválido.
 */
export function parseMandatoBounds(mandato: string): [number, number] | null {
  const normalizado = normalizarMandatoLabel(mandato);
  const match = /^(\d{4})-(\d{4})$/.exec(normalizado);
  if (!match) return null;
  const inicio = Number(match[1]);
  const fim = Number(match[2]);
  return inicio <= fim ? [inicio, fim] : null;
}

/**
 * Normaliza hífens, remove duplicatas e ordena numericamente os mandatos por (anoInicio, anoFim) decrescente.
 */
export function ordenarMandatosDecrescente(mandatos?: string[]): string[] {
  const origem = mandatos && mandatos.length > 0 ? mandatos : FALLBACK_MANDATOS;
  const unicos = Array.from(
    new Set(origem.map(normalizarMandatoLabel).filter(Boolean))
  );
  if (unicos.length === 0) {
    return [...FALLBACK_MANDATOS];
  }
  return unicos.sort((a, b) => {
    const boundsA = parseMandatoBounds(a);
    const boundsB = parseMandatoBounds(b);
    const [iniA, fimA] = boundsA ?? [-Infinity, -Infinity];
    const [iniB, fimB] = boundsB ?? [-Infinity, -Infinity];
    if (iniB !== iniA) return iniB - iniA;
    if (fimB !== fimA) return fimB - fimA;
    return b.localeCompare(a);
  });
}

/**
 * Calcula dinamicamente o intervalo "anoMin–anoMax" para o rótulo de Todos os mandatos,
 * retornando "2017–2028" como fallback quando a lista estiver ausente, vazia ou sem intervalos válidos.
 */
export function resolverIntervaloTodosMandatos(mandatosDisponiveis?: string[]): string {
  if (!mandatosDisponiveis || mandatosDisponiveis.length === 0) {
    return "2017–2028";
  }
  let minInicio = Infinity;
  let maxFim = -Infinity;
  for (const item of mandatosDisponiveis) {
    const bounds = parseMandatoBounds(item);
    if (!bounds) continue;
    const [inicio, fim] = bounds;
    if (inicio < minInicio) minInicio = inicio;
    if (fim > maxFim) maxFim = fim;
  }
  if (!Number.isFinite(minInicio) || !Number.isFinite(maxFim)) {
    return "2017–2028";
  }
  return `${minInicio}–${maxFim}`;
}

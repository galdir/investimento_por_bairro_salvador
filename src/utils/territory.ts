import {
  BairroResumo,
  CotaListaFechada,
  FrenteMedicao,
  ObraCompacta,
  PrefeituraBairroResumo,
  TerritorySelection,
} from "../types";

export interface ObraTerritoryShare {
  isCotaParte: boolean;
  matched: boolean;
  peso: number;
  unidades?: number;
  totalUnidades?: number;
  fracao?: string;
  cotas: CotaListaFechada[];
}

/**
 * Extrai as cotas de Lista Fechada válidas de um contrato, respeitando a precedência
 * contábil de Frentes de Medição quando existirem (ADR-0006).
 */
export function getObraCotasListaFechada(obra: {
  cotasListaFechada?: CotaListaFechada[];
  frentesMedicao?: FrenteMedicao[];
  fontesOficiais?: { lastroTerritorial?: { cotasListaFechada?: CotaListaFechada[] } };
} | null | undefined): CotaListaFechada[] {
  if (!obra) return [];
  const temFrentes = (obra.frentesMedicao || []).some(
    (f) =>
      ((f.nivel === "Pontual" || f.nivel === "Bairro") && Boolean(f.bairro)) ||
      (f.nivel === "Regional (Prefeitura-Bairro)" && Boolean(f.prefeituraBairro))
  );
  if (temFrentes) return [];
  const rawCotas =
    obra.cotasListaFechada || obra.fontesOficiais?.lastroTerritorial?.cotasListaFechada || [];
  return rawCotas.filter(
    (c): c is CotaListaFechada => Boolean(c?.bairro) && Number(c?.peso ?? 0) > 0
  );
}

/**
 * Extrai a participação (peso, fração n/M e cotas) de um contrato no território selecionado.
 */
export function getObraTerritoryShare(
  obra: ObraCompacta,
  territorio: Pick<TerritorySelection, "tipo" | "nome"> | null | undefined
): ObraTerritoryShare {
  const cotas = getObraCotasListaFechada(obra);

  if (cotas.length > 0) {
    const totalUnidades =
      cotas[0].totalUnidades || cotas.reduce((acc, c) => acc + (c.unidades || 0), 0);

    if (!territorio) {
      return {
        isCotaParte: true,
        matched: true,
        peso: 1,
        unidades: totalUnidades,
        totalUnidades,
        cotas,
      };
    }

    const targetKey = normalizeName(territorio.nome);
    const matching = cotas.filter((c) => {
      if (territorio.tipo === "bairro") {
        return normalizeName(c.bairro) === targetKey;
      }
      return normalizeName(c.prefeituraBairro) === targetKey;
    });

    if (matching.length === 0) {
      return {
        isCotaParte: true,
        matched: false,
        peso: 0,
        totalUnidades,
        cotas: [],
      };
    }

    const peso = matching.reduce((acc, c) => acc + Number(c.peso ?? 0), 0);
    const unidades = matching.reduce((acc, c) => acc + Number(c.unidades ?? 0), 0);
    const fracao =
      matching.length === 1 && matching[0].fracao
        ? matching[0].fracao
        : `${unidades}/${totalUnidades}`;

    return {
      isCotaParte: true,
      matched: true,
      peso,
      unidades,
      totalUnidades,
      fracao,
      cotas: matching,
    };
  }

  if (!territorio) {
    return { isCotaParte: false, matched: true, peso: 1, cotas: [] };
  }

  const targetKey = normalizeName(territorio.nome);
  const matched =
    territorio.tipo === "bairro"
      ? Boolean(obra.bairro && normalizeName(obra.bairro) === targetKey)
      : Boolean(
        (obra.prefeituraBairro || obra.prefeitura_bairro) &&
        normalizeName(obra.prefeituraBairro || obra.prefeitura_bairro) === targetKey
      );

  return {
    isCotaParte: false,
    matched,
    peso: matched ? 1 : 0,
    cotas: [],
  };
}

/**
 * Verifica se um contrato pertence ao território selecionado (direto ou via Cota-Parte).
 */
export function obraMatchesTerritory(
  obra: ObraCompacta,
  territorio: Pick<TerritorySelection, "tipo" | "nome"> | null | undefined
): boolean {
  return getObraTerritoryShare(obra, territorio).matched;
}

/**
 * Normaliza um nome textual para correspondência insensível a acentuação e caixa.
 *
 * @summary Remove acentos e converte para maiúsculas padronizadas.
 * @param name - String contendo o topônimo ou nome do bairro/prefeitura.
 * @returns Nome normalizado em maiúsculas sem diacríticos.
 */
export function normalizeName(name?: string | null): string {
  if (!name) return "";
  return name
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toUpperCase();
}

/**
 * Verifica se um Bairro Oficial é uma Zona Especial Não-Residencial.
 *
 * @summary Identifica áreas com população residencial nula ou residual (Aeroporto, Porto Seco Pirajá e CAB).
 * @param bairro - Objeto de resumo do bairro.
 * @returns Verdadeiro caso o bairro seja uma Zona Especial Não-Residencial.
 */
export function isZonaEspecial(bairro: BairroResumo): boolean {
  if (bairro.is_zona_especial_nao_residencial || bairro.isZonaEspecialNaoResidencial) {
    return true;
  }
  const norm = normalizeName(bairro.nome);
  return (
    norm === "AEROPORTO" ||
    norm.includes("PORTO SECO PIRAJA") ||
    norm.includes("CENTRO ADMINISTRATIVO DA BAHIA") ||
    norm === "CAB" ||
    norm === "CENTRO ADMINISTRATIVO DA BAHIA - CAB"
  );
}

/**
 * Verifica se um Bairro Oficial é uma Centralidade Metropolitana de Baixa População Residente.
 *
 * @summary Identifica o bairro do Comércio (ZUE-3/ZCMe com < 1.000 hab. e < 1.000 hab/km²), isento per capita mas com vulnerabilidade preservada.
 */
export function isCentralidadeMetropolitana(
  bairro: Pick<BairroResumo, "nome" | "is_centralidade_metropolitana" | "isCentralidadeMetropolitana">
): boolean {
  if (bairro.is_centralidade_metropolitana || bairro.isCentralidadeMetropolitana) {
    return true;
  }
  return normalizeName(bairro.nome) === "COMERCIO";
}

interface WeightedObra {
  obra: ObraCompacta;
  peso: number;
}

interface ObrasAggregatedMetrics {
  valorTotal: number;
  valorPago: number;
  totalObras: number;
  obrasVerde: number;
  obrasAmarelo: number;
  obrasVermelho: number;
  obrasComValorPago: number;
  obrasSemValorPago: number;
}

export function hasNumericPayment(val: number | null | undefined): val is number {
  return typeof val === "number" && !Number.isNaN(val);
}

/**
 * Retorna a chave canônica do contrato (UG + contrato SIGEF) com fallback para id.
 */
function getObraCanonicalKey(obra: ObraCompacta): string {
  const ug = obra.unidadeGestora;
  const contrato = obra.numeroContrato;
  if (ug && contrato && ug.trim() && contrato.trim()) {
    return `canon:${ug.trim()}::${contrato.trim()}`;
  }
  return `id:${String(obra.id)}`;
}

/**
 * Conta obras únicas (deduplicadas pela chave canônica) e distribui os status do Semáforo da Obra.
 */
function countUniqueObrasSemaforos(obras: ObraCompacta[]): {
  totalObras: number;
  obrasVerde: number;
  obrasAmarelo: number;
  obrasVermelho: number;
  obrasComValorPago: number;
  obrasSemValorPago: number;
} {
  const unicas = new Map<string, ObraCompacta>();
  for (const obra of obras) {
    const key = getObraCanonicalKey(obra);
    if (!unicas.has(key)) {
      unicas.set(key, obra);
    }
  }

  let obrasVerde = 0;
  let obrasAmarelo = 0;
  let obrasVermelho = 0;
  let obrasComValorPago = 0;
  let obrasSemValorPago = 0;

  for (const obra of unicas.values()) {
    const status = obra.semaforo?.status;
    if (status === "VERDE") obrasVerde++;
    else if (status === "AMARELO") obrasAmarelo++;
    else if (status === "VERMELHO") obrasVermelho++;

    if (hasNumericPayment(obra.valorPago)) {
      obrasComValorPago++;
    } else {
      obrasSemValorPago++;
    }
  }

  return {
    totalObras: unicas.size,
    obrasVerde,
    obrasAmarelo,
    obrasVermelho,
    obrasComValorPago,
    obrasSemValorPago,
  };
}

/**
 * Agrega valores financeiros ponderados (ou integrais) e contagem deduplicada de obras.
 */
function aggregateWeightedObras(entries: WeightedObra[]): ObrasAggregatedMetrics {
  let valorTotal = 0;
  let valorPago = 0;

  for (const { obra, peso } of entries) {
    valorTotal += (obra.valorContratualVigente ?? 0) * peso;
    if (hasNumericPayment(obra.valorPago)) {
      valorPago += obra.valorPago * peso;
    }
  }

  const contagem = countUniqueObrasSemaforos(entries.map((entry) => entry.obra));
  return { valorTotal, valorPago, ...contagem };
}

/**
 * Agrega financeiramente e em contagens por semáforo uma lista de obras públicas.
 */
function aggregateObrasMetrics(obras: ObraCompacta[]): ObrasAggregatedMetrics {
  return aggregateWeightedObras(obras.map((obra) => ({ obra, peso: 1 })));
}

/**
 * Soma os valores liquidados e pagos de uma lista de Frentes de Medição.
 */
function sumFrentesMetrics(frentes: FrenteMedicao[]): { valorLiquidado: number; valorPago: number } {
  let valorLiquidado = 0;
  let valorPago = 0;
  for (const f of frentes) {
    valorLiquidado += f.valorLiquidado ?? 0;
    valorPago += f.valorPago ?? 0;
  }
  return { valorLiquidado, valorPago };
}

/**
 * Filtra as Frentes de Medição de um conjunto de obras que pertencem ao território selecionado.
 */
export function filterFrentesByTerritory(
  obras: ObraCompacta[],
  territorio: Pick<TerritorySelection, "tipo" | "nome">
): Array<{ obra: ObraCompacta; frente: FrenteMedicao }> {
  const territorioNorm = normalizeName(territorio.nome);
  const ehBairro = territorio.tipo === "bairro";
  const result: Array<{ obra: ObraCompacta; frente: FrenteMedicao }> = [];

  for (const obra of obras) {
    for (const frente of obra.frentesMedicao || []) {
      const match = ehBairro
        ? normalizeName(frente.bairro) === territorioNorm
        : normalizeName(frente.prefeituraBairro) === territorioNorm;
      if (match) {
        result.push({ obra, frente });
      }
    }
  }
  return result;
}

/**
 * Converte um Bairro cadastral em um objeto de seleção territorial unificado.
 *
 * @summary Encapsula a conversão de tipo para evitar repetição de parâmetros (Data Clump).
 * @param bairro - Objeto de BairroResumo.
 * @returns Objeto TerritorySelection configurado para o bairro.
 */
export function createBairroSelection(bairro: BairroResumo): TerritorySelection {
  return {
    tipo: "bairro",
    id: bairro.id,
    nome: bairro.nome,
    prefeitura_bairro: bairro.prefeitura_bairro,
    populacao: bairro.populacao,
    indice_vulnerabilidade: bairro.indice_vulnerabilidade,
    is_zona_especial_nao_residencial: bairro.is_zona_especial_nao_residencial,
    isZonaEspecialNaoResidencial: bairro.isZonaEspecialNaoResidencial ?? bairro.is_zona_especial_nao_residencial,
    is_centralidade_metropolitana: bairro.is_centralidade_metropolitana ?? isCentralidadeMetropolitana(bairro),
    isCentralidadeMetropolitana:
      bairro.isCentralidadeMetropolitana ??
      bairro.is_centralidade_metropolitana ??
      isCentralidadeMetropolitana(bairro),
    pct_esgoto_inadequado: bairro.pct_esgoto_inadequado,
    pct_agua_inadequada: bairro.pct_agua_inadequada,
    pct_analfabetismo_15mais: bairro.pct_analfabetismo_15mais,
    vulnerabilidade_estimada_contiguidade: bairro.vulnerabilidade_estimada_contiguidade,
    valorTotal: bairro.valorTotal,
    valorLiquidado: bairro.valorLiquidado,
    valorPago: bairro.valorPago,
    valorLiquidadoDireto: bairro.valorLiquidadoDireto,
    valorPagoDireto: bairro.valorPagoDireto,
    valorLiquidadoFrentes: bairro.valorLiquidadoFrentes,
    valorPagoFrentes: bairro.valorPagoFrentes,
    totalFrentesMedicao: bairro.totalFrentesMedicao,
    totalObras: bairro.totalObras,
    obrasVerde: bairro.obrasVerde,
    obrasAmarelo: bairro.obrasAmarelo,
    obrasVermelho: bairro.obrasVermelho,
    investimentoPorHabitante: bairro.investimentoPorHabitante,
    investimentoPorHabitantePago: bairro.investimentoPorHabitantePago,
    valorPagoDisponivel: bairro.valorPagoDisponivel,
    obrasSemValorPago: bairro.obrasSemValorPago,
  };
}

/**
 * Converte uma Prefeitura-Bairro cadastral em um objeto de seleção territorial unificado.
 *
 * @summary Encapsula a conversão de tipo para evitar repetição de parâmetros (Data Clump).
 * @param prefeitura - Objeto de PrefeituraBairroResumo.
 * @returns Objeto TerritorySelection configurado para a Prefeitura-Bairro.
 */
export function createPrefeituraSelection(prefeitura: PrefeituraBairroResumo): TerritorySelection {
  return {
    tipo: "prefeitura_bairro",
    id: prefeitura.id,
    nome: prefeitura.nome,
    populacao: prefeitura.populacao_total,
    indice_vulnerabilidade: prefeitura.indice_vulnerabilidade,
    pct_esgoto_inadequado: prefeitura.pct_esgoto_inadequado,
    pct_agua_inadequada: prefeitura.pct_agua_inadequada,
    pct_analfabetismo_15mais: prefeitura.pct_analfabetismo_15mais,
    vulnerabilidade_estimada_contiguidade: prefeitura.vulnerabilidade_estimada_contiguidade,
    bairros_vulnerabilidade_estimada: prefeitura.bairros_vulnerabilidade_estimada,
    valorTotal: prefeitura.valorTotal,
    valorLiquidado: prefeitura.valorLiquidado,
    valorPago: prefeitura.valorPago,
    valorLiquidadoDireto: prefeitura.valorLiquidadoDireto,
    valorPagoDireto: prefeitura.valorPagoDireto,
    valorLiquidadoFrentes: prefeitura.valorLiquidadoFrentes,
    valorPagoFrentes: prefeitura.valorPagoFrentes,
    totalFrentesMedicao: prefeitura.totalFrentesMedicao,
    totalObras: prefeitura.totalObras,
    obrasVerde: prefeitura.obrasVerde,
    obrasAmarelo: prefeitura.obrasAmarelo,
    obrasVermelho: prefeitura.obrasVermelho,
    investimentoPorHabitante: prefeitura.investimentoPorHabitante,
    investimentoPorHabitantePago: prefeitura.investimentoPorHabitantePago,
    valorPagoDisponivel: prefeitura.valorPagoDisponivel,
    obrasSemValorPago: prefeitura.obrasSemValorPago,
  };
}

/**
 * Verifica se uma seleção territorial é compatível com a camada ativa no mapa.
 *
 * @summary Evita que uma seleção de Bairro permaneça ativa ao visualizar Prefeituras-Bairro (e vice-versa).
 * @param territory - Objeto da seleção territorial atual ou null.
 * @param layer - Camada ativa no mapa ("bairros" ou "prefeituras").
 * @returns Verdadeiro caso a seleção seja nula ou compatível com a camada informada.
 */
export function isTerritoryCompatibleWithLayer(
  territory: TerritorySelection | null,
  layer: "bairros" | "prefeituras"
): boolean {
  if (!territory) return true;
  if (layer === "bairros") return territory.tipo === "bairro";
  if (layer === "prefeituras") return territory.tipo === "prefeitura_bairro";
  return false;
}

/**
 * Recalcula o rollup financeiro, quantitativo e de semáforo dos Bairros Oficiais e Prefeituras-Bairro
 * a partir de um conjunto filtrado de Obras Públicas.
 *
 * @summary Aplica regras de domínio territorial estritas sem rateio artificial de contratos regionais.
 * @param bairrosBase - Lista base de resumos dos 170 Bairros Oficiais com população e vulnerabilidade.
 * @param prefeiturasBase - Lista base de resumos das Prefeituras-Bairro com população total.
 * @param obrasFiltradas - Conjunto de obras públicas após aplicação dos filtros da barra superior.
 * @returns Objeto contendo os arrays de bairros e prefeituras-bairro recalculados.
 */
export function calculateTerritorialRollup(
  bairrosBase: BairroResumo[],
  prefeiturasBase: PrefeituraBairroResumo[],
  obrasFiltradas: ObraCompacta[]
): {
  bairros: BairroResumo[];
  prefeituras: PrefeituraBairroResumo[];
} {
  // 1. Agrupadores de obras e frentes de medição por bairro e por prefeitura-bairro
  const obrasPorBairro = new Map<string, WeightedObra[]>();
  const obrasRegionaisPorPrefeitura = new Map<string, ObraCompacta[]>();
  const frentesPorBairro = new Map<string, FrenteMedicao[]>();
  const frentesRegionaisPorPrefeitura = new Map<string, FrenteMedicao[]>();

  for (const obra of obrasFiltradas) {
    const nivel = obra.nivel || "Escopo Cidade (Não-Localizado)";
    const bairroNome = obra.bairro;
    const prefeituraNome = obra.prefeituraBairro || obra.prefeitura_bairro;
    const cotasValidas = getObraCotasListaFechada(obra);

    if (cotasValidas.length > 0) {
      for (const cota of cotasValidas) {
        const bairroKey = normalizeName(cota.bairro);
        const list = obrasPorBairro.get(bairroKey) || [];
        list.push({ obra, peso: Number(cota.peso) });
        obrasPorBairro.set(bairroKey, list);
      }
    } else if ((nivel === "Pontual" || nivel === "Bairro") && bairroNome) {
      const bairroKey = normalizeName(bairroNome);
      const list = obrasPorBairro.get(bairroKey) || [];
      list.push({ obra, peso: 1 });
      obrasPorBairro.set(bairroKey, list);
    } else if (nivel === "Regional (Prefeitura-Bairro)" && prefeituraNome) {
      const prefeituraKey = normalizeName(prefeituraNome);
      const list = obrasRegionaisPorPrefeitura.get(prefeituraKey) || [];
      list.push(obra);
      obrasRegionaisPorPrefeitura.set(prefeituraKey, list);
    }

    for (const frente of obra.frentesMedicao || []) {
      const fNivel = frente.nivel;
      if ((fNivel === "Pontual" || fNivel === "Bairro") && frente.bairro) {
        const bKey = normalizeName(frente.bairro);
        const list = frentesPorBairro.get(bKey) || [];
        list.push(frente);
        frentesPorBairro.set(bKey, list);
      } else if (fNivel === "Regional (Prefeitura-Bairro)" && frente.prefeituraBairro) {
        const pKey = normalizeName(frente.prefeituraBairro);
        const list = frentesRegionaisPorPrefeitura.get(pKey) || [];
        list.push(frente);
        frentesRegionaisPorPrefeitura.set(pKey, list);
      }
    }
  }

  // 2. Recálculo dos Bairros Oficiais
  const recalculatedBairros: BairroResumo[] = bairrosBase.map((bairro) => {
    const bairroKey = normalizeName(bairro.nome);
    const obrasDoBairro = obrasPorBairro.get(bairroKey) || [];
    const frentesDoBairro = frentesPorBairro.get(bairroKey) || [];
    const metrics = aggregateWeightedObras(obrasDoBairro);

    const { valorLiquidado: valorLiquidadoFrentes, valorPago: valorPagoFrentes } =
      sumFrentesMetrics(frentesDoBairro);
    const frentesComValorPago = frentesDoBairro.filter((f) => hasNumericPayment(f.valorPago)).length;

    const valorPagoDireto = metrics.valorPago;
    const valorPagoTotal = valorPagoDireto + valorPagoFrentes;
    const valorPagoDisponivel =
      (metrics.totalObras === 0 && frentesDoBairro.length === 0) ||
      metrics.obrasComValorPago > 0 ||
      frentesComValorPago > 0;

    const ehZonaEsp = isZonaEspecial(bairro);
    const ehCentralidade = !ehZonaEsp && isCentralidadeMetropolitana(bairro);
    const populacao = bairro.populacao || 0;

    let investimentoPorHabitante = 0.0;
    let investimentoPorHabitantePago: number | undefined = valorPagoDisponivel ? 0.0 : undefined;
    if (!ehZonaEsp && !ehCentralidade && populacao > 0) {
      investimentoPorHabitante = Math.round(((metrics.valorTotal / populacao) + Number.EPSILON) * 100) / 100;
      if (valorPagoDisponivel) {
        investimentoPorHabitantePago = Math.round(((valorPagoTotal / populacao) + Number.EPSILON) * 100) / 100;
      }
    }

    return {
      ...bairro,
      valorTotal: Math.round((metrics.valorTotal + Number.EPSILON) * 100) / 100,
      valorPago: valorPagoDisponivel
        ? Math.round((valorPagoTotal + Number.EPSILON) * 100) / 100
        : undefined,
      valorPagoDireto: valorPagoDisponivel
        ? Math.round((valorPagoDireto + Number.EPSILON) * 100) / 100
        : undefined,
      valorLiquidadoFrentes: Math.round((valorLiquidadoFrentes + Number.EPSILON) * 100) / 100,
      valorPagoFrentes: Math.round((valorPagoFrentes + Number.EPSILON) * 100) / 100,
      totalFrentesMedicao: frentesDoBairro.length,
      totalObras: metrics.totalObras,
      obrasVerde: metrics.obrasVerde,
      obrasAmarelo: metrics.obrasAmarelo,
      obrasVermelho: metrics.obrasVermelho,
      investimentoPorHabitante,
      investimentoPorHabitantePago,
      valorPagoDisponivel,
      obrasSemValorPago: metrics.obrasSemValorPago,
      is_zona_especial_nao_residencial: ehZonaEsp,
      isZonaEspecialNaoResidencial: ehZonaEsp,
      is_centralidade_metropolitana: ehCentralidade,
      isCentralidadeMetropolitana: ehCentralidade,
    };
  });

  // Mapeamento de prefeitura-bairro para bairros constituintes recalculados
  const bairrosPorPrefeitura = new Map<string, BairroResumo[]>();
  for (const bairro of recalculatedBairros) {
    if (bairro.prefeitura_bairro) {
      const prefeituraKey = normalizeName(bairro.prefeitura_bairro);
      const list = bairrosPorPrefeitura.get(prefeituraKey) || [];
      list.push(bairro);
      bairrosPorPrefeitura.set(prefeituraKey, list);
    }
  }

  // 3. Recálculo das Prefeituras-Bairro
  const recalculatedPrefeituras: PrefeituraBairroResumo[] = prefeiturasBase.map((prefeitura) => {
    const prefeituraKey = normalizeName(prefeitura.nome);
    const bairrosFilhos = bairrosPorPrefeitura.get(prefeituraKey) || [];
    const obrasRegionais = obrasRegionaisPorPrefeitura.get(prefeituraKey) || [];
    const frentesRegionais = frentesRegionaisPorPrefeitura.get(prefeituraKey) || [];

    let valorTotalBairros = 0;
    let valorPagoDiretoBairros = 0;
    let valorLiquidadoFrentesBairros = 0;
    let valorPagoFrentesBairros = 0;
    let totalFrentesBairros = 0;
    let frentesPagasBairros = 0;

    for (const bairro of bairrosFilhos) {
      valorTotalBairros += bairro.valorTotal ?? 0;
      valorPagoDiretoBairros += bairro.valorPagoDireto ?? (hasNumericPayment(bairro.valorPago) ? bairro.valorPago : 0);
      valorLiquidadoFrentesBairros += bairro.valorLiquidadoFrentes ?? 0;
      valorPagoFrentesBairros += bairro.valorPagoFrentes ?? 0;
      totalFrentesBairros += bairro.totalFrentesMedicao ?? 0;
      const fBairroCount = (frentesPorBairro.get(normalizeName(bairro.nome)) || []).filter((f) =>
        hasNumericPayment(f.valorPago)
      ).length;
      frentesPagasBairros += fBairroCount;
    }

    const obrasUnicasPrefeitura: ObraCompacta[] = [...obrasRegionais];
    for (const bairro of bairrosFilhos) {
      for (const item of obrasPorBairro.get(normalizeName(bairro.nome)) || []) {
        obrasUnicasPrefeitura.push(item.obra);
      }
    }
    const contagemUnica = countUniqueObrasSemaforos(obrasUnicasPrefeitura);

    const regionalMetrics = aggregateObrasMetrics(obrasRegionais);
    const { valorLiquidado: valorLiquidadoFrentesReg, valorPago: valorPagoFrentesReg } =
      sumFrentesMetrics(frentesRegionais);
    const frentesPagasReg = frentesRegionais.filter((f) => hasNumericPayment(f.valorPago)).length;

    const valorTotal = valorTotalBairros + regionalMetrics.valorTotal;
    const valorPagoDireto = valorPagoDiretoBairros + regionalMetrics.valorPago;
    const valorLiquidadoFrentes = valorLiquidadoFrentesBairros + valorLiquidadoFrentesReg;
    const valorPagoFrentes = valorPagoFrentesBairros + valorPagoFrentesReg;
    const valorPago = valorPagoDireto + valorPagoFrentes;
    const totalFrentesMedicao = totalFrentesBairros + frentesRegionais.length;
    const totalFrentesPagas = frentesPagasBairros + frentesPagasReg;
    const totalObras = contagemUnica.totalObras;
    const populacaoTotal = prefeitura.populacao_total || 0;

    const valorPagoDisponivel =
      (totalObras === 0 && totalFrentesMedicao === 0) ||
      contagemUnica.obrasComValorPago > 0 ||
      totalFrentesPagas > 0;

    const investimentoPorHabitante =
      populacaoTotal > 0 ? Math.round(((valorTotal / populacaoTotal) + Number.EPSILON) * 100) / 100 : 0.0;
    const investimentoPorHabitantePago = valorPagoDisponivel
      ? populacaoTotal > 0
        ? Math.round(((valorPago / populacaoTotal) + Number.EPSILON) * 100) / 100
        : 0.0
      : undefined;

    // Índice de vulnerabilidade e subindicadores da Prefeitura-Bairro: média ponderada pela população dos bairros residenciais
    const bairrosResidenciais = bairrosFilhos.filter(
      (b) => !(b.is_zona_especial_nao_residencial || b.isZonaEspecialNaoResidencial)
    );
    const bairrosEstimados = bairrosResidenciais
      .filter((b) => Boolean(b.vulnerabilidade_estimada_contiguidade))
      .map((b) => b.nome)
      .sort((a, b) => a.localeCompare(b, "pt-BR"));
    const temEstimativaContiguidade =
      bairrosEstimados.length > 0 || Boolean(prefeitura.vulnerabilidade_estimada_contiguidade);
    let popResidencial = 0;
    let somaVulnPonderada = 0;
    let somaEsgotoPonderada = 0;
    let somaAguaPonderada = 0;
    let somaAnalfPonderada = 0;

    for (const b of bairrosResidenciais) {
      const pop = b.populacao || 0;
      if (pop > 0) {
        popResidencial += pop;
        somaVulnPonderada += pop * (b.indice_vulnerabilidade ?? 0.0);
        somaEsgotoPonderada += pop * (b.pct_esgoto_inadequado ?? 0);
        somaAguaPonderada += pop * (b.pct_agua_inadequada ?? 0);
        somaAnalfPonderada += pop * (b.pct_analfabetismo_15mais ?? 0);
      }
    }

    let indiceVulnerabilidade = prefeitura.indice_vulnerabilidade ?? 0.0;
    let pctEsgoto = prefeitura.pct_esgoto_inadequado ?? 0.0;
    let pctAgua = prefeitura.pct_agua_inadequada ?? 0.0;
    let pctAnalf = prefeitura.pct_analfabetismo_15mais ?? 0.0;

    if (popResidencial > 0) {
      indiceVulnerabilidade = Math.round(((somaVulnPonderada / popResidencial) + Number.EPSILON) * 100) / 100;
      pctEsgoto = Math.round(((somaEsgotoPonderada / popResidencial) + Number.EPSILON) * 100) / 100;
      pctAgua = Math.round(((somaAguaPonderada / popResidencial) + Number.EPSILON) * 100) / 100;
      pctAnalf = Math.round(((somaAnalfPonderada / popResidencial) + Number.EPSILON) * 100) / 100;
    } else if (bairrosResidenciais.length > 0) {
      const somaSimples = bairrosResidenciais.reduce((acc, b) => acc + (b.indice_vulnerabilidade ?? 0.0), 0);
      indiceVulnerabilidade = Math.round(((somaSimples / bairrosResidenciais.length) + Number.EPSILON) * 100) / 100;
      pctEsgoto = Math.round(((bairrosResidenciais.reduce((acc, b) => acc + (b.pct_esgoto_inadequado ?? 0), 0) / bairrosResidenciais.length) + Number.EPSILON) * 100) / 100;
      pctAgua = Math.round(((bairrosResidenciais.reduce((acc, b) => acc + (b.pct_agua_inadequada ?? 0), 0) / bairrosResidenciais.length) + Number.EPSILON) * 100) / 100;
      pctAnalf = Math.round(((bairrosResidenciais.reduce((acc, b) => acc + (b.pct_analfabetismo_15mais ?? 0), 0) / bairrosResidenciais.length) + Number.EPSILON) * 100) / 100;
    }

    return {
      ...prefeitura,
      indice_vulnerabilidade: indiceVulnerabilidade,
      pct_esgoto_inadequado: pctEsgoto,
      pct_agua_inadequada: pctAgua,
      pct_analfabetismo_15mais: pctAnalf,
      vulnerabilidade_estimada_contiguidade: temEstimativaContiguidade,
      bairros_vulnerabilidade_estimada: bairrosEstimados,
      valorTotal: Math.round((valorTotal + Number.EPSILON) * 100) / 100,
      valorPago: valorPagoDisponivel
        ? Math.round((valorPago + Number.EPSILON) * 100) / 100
        : undefined,
      valorPagoDireto: valorPagoDisponivel
        ? Math.round((valorPagoDireto + Number.EPSILON) * 100) / 100
        : undefined,
      valorLiquidadoFrentes: Math.round((valorLiquidadoFrentes + Number.EPSILON) * 100) / 100,
      valorPagoFrentes: Math.round((valorPagoFrentes + Number.EPSILON) * 100) / 100,
      totalFrentesMedicao,
      totalObras,
      obrasVerde: contagemUnica.obrasVerde,
      obrasAmarelo: contagemUnica.obrasAmarelo,
      obrasVermelho: contagemUnica.obrasVermelho,
      investimentoPorHabitante,
      investimentoPorHabitantePago,
      valorPagoDisponivel,
      obrasSemValorPago: contagemUnica.obrasSemValorPago,
    };
  });

  return {
    bairros: recalculatedBairros,
    prefeituras: recalculatedPrefeituras,
  };
}

export type TerritoryInvestmentState =
  | { kind: "exempt"; reason: "zona_especial" | "centralidade" }
  | { kind: "unavailable" }
  | { kind: "value"; perCapita: number; total: number; obrasSemValorPago: number };

/**
 * Resolve o estado explícito do indicador financeiro de um território sem substituir pagamento ausente por contratado.
 */
export function getTerritoryInvestmentState(
  item: BairroResumo | PrefeituraBairroResumo | TerritorySelection,
  metricType: "vigente" | "executado",
  tipo?: "bairro" | "prefeitura_bairro"
): TerritoryInvestmentState {
  const isBairro =
    tipo === "bairro" ||
    ("prefeitura_bairro" in item && !("populacao_total" in item)) ||
    ("tipo" in item && item.tipo === "bairro");

  if (isBairro) {
    const b = item as BairroResumo;
    if (isZonaEspecial(b)) {
      return { kind: "exempt", reason: "zona_especial" };
    }
    if (isCentralidadeMetropolitana(b)) {
      return { kind: "exempt", reason: "centralidade" };
    }
  }

  if (metricType === "executado") {
    const pagoDisponivel = item.valorPagoDisponivel;
    const perCapitaPago = item.investimentoPorHabitantePago;
    const valorPago = item.valorPago;
    if (pagoDisponivel === false || (!hasNumericPayment(perCapitaPago) && !hasNumericPayment(valorPago))) {
      if ((item.totalObras ?? 0) === 0 && (item.totalFrentesMedicao ?? 0) === 0) {
        return { kind: "value", perCapita: 0, total: 0, obrasSemValorPago: 0 };
      }
      return { kind: "unavailable" };
    }
    return {
      kind: "value",
      perCapita: hasNumericPayment(perCapitaPago) ? perCapitaPago : 0,
      total: hasNumericPayment(valorPago) ? valorPago : 0,
      obrasSemValorPago: item.obrasSemValorPago ?? 0,
    };
  }

  return {
    kind: "value",
    perCapita: item.investimentoPorHabitante ?? 0,
    total: item.valorTotal ?? 0,
    obrasSemValorPago: 0,
  };
}

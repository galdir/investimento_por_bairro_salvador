import { BairroResumo, ObraCompacta, PrefeituraBairroResumo, TerritorySelection } from "../types";

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

interface ObrasAggregatedMetrics {
  valorTotal: number;
  valorPago: number;
  obrasVerde: number;
  obrasAmarelo: number;
  obrasVermelho: number;
}

/**
 * Agrega financeiramente e em contagens por semáforo uma lista de obras públicas.
 */
function aggregateObrasMetrics(obras: ObraCompacta[]): ObrasAggregatedMetrics {
  let valorTotal = 0;
  let valorPago = 0;
  let obrasVerde = 0;
  let obrasAmarelo = 0;
  let obrasVermelho = 0;

  for (const obra of obras) {
    valorTotal += obra.valorContratualVigente ?? 0;
    valorPago += obra.valorPago ?? 0;
    const status = obra.semaforo?.status;
    if (status === "VERDE") obrasVerde++;
    else if (status === "AMARELO") obrasAmarelo++;
    else if (status === "VERMELHO") obrasVermelho++;
  }

  return { valorTotal, valorPago, obrasVerde, obrasAmarelo, obrasVermelho };
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
    valorTotal: bairro.valorTotal,
    valorPago: bairro.valorPago,
    totalObras: bairro.totalObras,
    obrasVerde: bairro.obrasVerde,
    obrasAmarelo: bairro.obrasAmarelo,
    obrasVermelho: bairro.obrasVermelho,
    investimentoPorHabitante: bairro.investimentoPorHabitante,
    investimentoPorHabitantePago: bairro.investimentoPorHabitantePago,
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
    valorTotal: prefeitura.valorTotal,
    valorPago: prefeitura.valorPago,
    totalObras: prefeitura.totalObras,
    obrasVerde: prefeitura.obrasVerde,
    obrasAmarelo: prefeitura.obrasAmarelo,
    obrasVermelho: prefeitura.obrasVermelho,
    investimentoPorHabitante: prefeitura.investimentoPorHabitante,
    investimentoPorHabitantePago: prefeitura.investimentoPorHabitantePago,
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
  // 1. Agrupadores de obras por bairro e obras regionais por prefeitura-bairro
  const obrasPorBairro = new Map<string, ObraCompacta[]>();
  const obrasRegionaisPorPrefeitura = new Map<string, ObraCompacta[]>();

  for (const obra of obrasFiltradas) {
    const nivel = obra.nivel || "Escopo Cidade (Não-Localizado)";
    const bairroNome = obra.bairro;
    const prefeituraNome = obra.prefeituraBairro || obra.prefeitura_bairro;

    if ((nivel === "Pontual" || nivel === "Bairro") && bairroNome) {
      const bairroKey = normalizeName(bairroNome);
      const list = obrasPorBairro.get(bairroKey) || [];
      list.push(obra);
      obrasPorBairro.set(bairroKey, list);
    } else if (nivel === "Regional (Prefeitura-Bairro)" && prefeituraNome) {
      const prefeituraKey = normalizeName(prefeituraNome);
      const list = obrasRegionaisPorPrefeitura.get(prefeituraKey) || [];
      list.push(obra);
      obrasRegionaisPorPrefeitura.set(prefeituraKey, list);
    }
  }

  // 2. Recálculo dos Bairros Oficiais
  const recalculatedBairros: BairroResumo[] = bairrosBase.map((bairro) => {
    const bairroKey = normalizeName(bairro.nome);
    const obrasDoBairro = obrasPorBairro.get(bairroKey) || [];
    const metrics = aggregateObrasMetrics(obrasDoBairro);

    const ehZonaEsp = isZonaEspecial(bairro);
    const populacao = bairro.populacao || 0;

    let investimentoPorHabitante = 0.0;
    let investimentoPorHabitantePago = 0.0;
    if (!ehZonaEsp && populacao > 0) {
      investimentoPorHabitante = Math.round(((metrics.valorTotal / populacao) + Number.EPSILON) * 100) / 100;
      investimentoPorHabitantePago = Math.round(((metrics.valorPago / populacao) + Number.EPSILON) * 100) / 100;
    }

    return {
      ...bairro,
      valorTotal: Math.round((metrics.valorTotal + Number.EPSILON) * 100) / 100,
      valorPago: Math.round((metrics.valorPago + Number.EPSILON) * 100) / 100,
      totalObras: obrasDoBairro.length,
      obrasVerde: metrics.obrasVerde,
      obrasAmarelo: metrics.obrasAmarelo,
      obrasVermelho: metrics.obrasVermelho,
      investimentoPorHabitante,
      investimentoPorHabitantePago,
      is_zona_especial_nao_residencial: ehZonaEsp,
      isZonaEspecialNaoResidencial: ehZonaEsp,
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

    let valorTotalBairros = 0;
    let valorPagoBairros = 0;
    let totalObrasBairros = 0;
    let obrasVerdeBairros = 0;
    let obrasAmareloBairros = 0;
    let obrasVermelhoBairros = 0;

    for (const bairro of bairrosFilhos) {
      valorTotalBairros += bairro.valorTotal ?? 0;
      valorPagoBairros += bairro.valorPago ?? 0;
      totalObrasBairros += bairro.totalObras ?? 0;
      obrasVerdeBairros += bairro.obrasVerde ?? 0;
      obrasAmareloBairros += bairro.obrasAmarelo ?? 0;
      obrasVermelhoBairros += bairro.obrasVermelho ?? 0;
    }

    const regionalMetrics = aggregateObrasMetrics(obrasRegionais);

    const valorTotal = valorTotalBairros + regionalMetrics.valorTotal;
    const valorPago = valorPagoBairros + regionalMetrics.valorPago;
    const totalObras = totalObrasBairros + obrasRegionais.length;
    const populacaoTotal = prefeitura.populacao_total || 0;

    const investimentoPorHabitante =
      populacaoTotal > 0 ? Math.round(((valorTotal / populacaoTotal) + Number.EPSILON) * 100) / 100 : 0.0;
    const investimentoPorHabitantePago =
      populacaoTotal > 0 ? Math.round(((valorPago / populacaoTotal) + Number.EPSILON) * 100) / 100 : 0.0;

    // Índice de vulnerabilidade da Prefeitura-Bairro: média ponderada pela população dos bairros residenciais
    const bairrosResidenciais = bairrosFilhos.filter(
      (b) => !(b.is_zona_especial_nao_residencial || b.isZonaEspecialNaoResidencial)
    );
    let popResidencial = 0;
    let somaVulnPonderada = 0;
    for (const b of bairrosResidenciais) {
      const pop = b.populacao || 0;
      if (pop > 0) {
        popResidencial += pop;
        somaVulnPonderada += pop * (b.indice_vulnerabilidade ?? 0.5);
      }
    }

    let indiceVulnerabilidade = prefeitura.indice_vulnerabilidade ?? 0.5;
    if (popResidencial > 0) {
      indiceVulnerabilidade = Math.round(((somaVulnPonderada / popResidencial) + Number.EPSILON) * 100) / 100;
    } else if (bairrosResidenciais.length > 0) {
      const somaSimples = bairrosResidenciais.reduce((acc, b) => acc + (b.indice_vulnerabilidade ?? 0.5), 0);
      indiceVulnerabilidade = Math.round(((somaSimples / bairrosResidenciais.length) + Number.EPSILON) * 100) / 100;
    }

    return {
      ...prefeitura,
      indice_vulnerabilidade: indiceVulnerabilidade,
      valorTotal: Math.round((valorTotal + Number.EPSILON) * 100) / 100,
      valorPago: Math.round((valorPago + Number.EPSILON) * 100) / 100,
      totalObras,
      obrasVerde: obrasVerdeBairros + regionalMetrics.obrasVerde,
      obrasAmarelo: obrasAmareloBairros + regionalMetrics.obrasAmarelo,
      obrasVermelho: obrasVermelhoBairros + regionalMetrics.obrasVermelho,
      investimentoPorHabitante,
      investimentoPorHabitantePago,
    };
  });

  return {
    bairros: recalculatedBairros,
    prefeituras: recalculatedPrefeituras,
  };
}

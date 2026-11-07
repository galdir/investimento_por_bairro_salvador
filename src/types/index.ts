/**
 * Definições de tipos do Painel "Mapa das Obras e do Dinheiro por Bairro" de Salvador.
 */

export interface GlobalKpis {
  totalObras: number;
  valorTotal: number;
  totalAtivas: number;
  totalEmpenhado: number;
  totalLiquidado: number;
  totalPago: number;
  investimentoPorHabitanteCidade: number;
}

export interface BairroResumo {
  id: number | string;
  nome: string;
  prefeitura_bairro: string;
  populacao: number;
  indice_vulnerabilidade: number;
  is_zona_especial_nao_residencial: boolean;
  isZonaEspecialNaoResidencial?: boolean;
}

export interface PrefeituraBairroResumo {
  id: number | string;
  nome: string;
  populacao_total: number;
}

export interface ObraCompacta {
  id: number | string;
  unidadeGestora: string;
  numeroContrato: string;
  objeto: string;
  valorContratualVigente: number;
  percentualExecutado: number;
  situacao: string;
  credor: string;
}

export interface IndexData {
  metadata: {
    generatedAt: string;
    anoReferencia: number;
  };
  kpis_globais: GlobalKpis;
  prefeituras_bairro: PrefeituraBairroResumo[];
  bairros: BairroResumo[];
  obras: ObraCompacta[];
}

export interface TerritorySelection {
  tipo: "bairro" | "prefeitura_bairro";
  id: number | string;
  nome: string;
  prefeitura_bairro?: string;
  populacao: number;
  indice_vulnerabilidade?: number;
  is_zona_especial_nao_residencial?: boolean;
  isZonaEspecialNaoResidencial?: boolean;
}

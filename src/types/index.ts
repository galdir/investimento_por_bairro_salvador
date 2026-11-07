/**
 * Definições de tipos do Painel "Mapa das Obras e do Dinheiro por Bairro" de Salvador.
 */

export type SemaforoStatus = "VERDE" | "AMARELO" | "VERMELHO";

export interface SemaforoInfo {
  status: SemaforoStatus;
  rotulo: string;
  motivos: string[];
  deltaPercentualValor?: number;
}

export type TemaObra =
  | "Encostas e Contenção"
  | "Educação e Escolas"
  | "Saúde"
  | "Praças, Esporte e Lazer"
  | "Mobilidade, Pavimentação e Drenagem"
  | "Manutenção Urbana e Outros";

export type MetricType = "vigente" | "executado";

export interface GlobalKpis {
  totalObras: number;
  valorTotal: number;
  totalAtivas: number;
  totalCriticas?: number;
  percentualCriticas?: number;
  totalAditivosValor?: number;
  percentualMedioAditivos?: number;
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
  valorOriginal?: number;
  valorContratualVigente: number;
  valorAditivos?: number;
  deltaPercentualValor?: number;
  valorPago?: number;
  percentualExecutado: number;
  situacao: string;
  credor: string;
  tema?: TemaObra | string;
  semaforo?: SemaforoInfo;
  ano?: number;
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

export interface FilterState {
  ano: number | "todos";
  orgao: string | "todos";
  tema: string | "todos";
  semaforo: SemaforoStatus | "todos";
  busca: string;
  metricType: MetricType;
}

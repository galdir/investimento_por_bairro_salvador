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

export type ChoroplethMetric = "investimentoPorHabitante" | "vulnerabilidade";

export type NivelAlocacaoTerritorial =
  | "Pontual"
  | "Bairro"
  | "Regional (Prefeitura-Bairro)"
  | "Escopo Cidade (Não-Localizado)";

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
  totalNaoLocalizado?: number;
  valorNaoLocalizado?: number;
  valorPagoNaoLocalizado?: number;
  percentualNaoLocalizado?: number;
}

export interface BairroResumo {
  id: number | string;
  nome: string;
  prefeitura_bairro: string;
  populacao: number;
  indice_vulnerabilidade: number;
  is_zona_especial_nao_residencial: boolean;
  isZonaEspecialNaoResidencial?: boolean;
  valorTotal?: number;
  valorPago?: number;
  totalObras?: number;
  obrasVerde?: number;
  obrasAmarelo?: number;
  obrasVermelho?: number;
  investimentoPorHabitante?: number;
  investimentoPorHabitantePago?: number;
}

export interface PrefeituraBairroResumo {
  id: number | string;
  nome: string;
  populacao_total: number;
  indice_vulnerabilidade?: number;
  valorTotal?: number;
  valorPago?: number;
  totalObras?: number;
  obrasVerde?: number;
  obrasAmarelo?: number;
  obrasVermelho?: number;
  investimentoPorHabitante?: number;
  investimentoPorHabitantePago?: number;
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
  cnpj?: string;
  cnpjCredor?: string;
  tema?: TemaObra | string;
  semaforo?: SemaforoInfo;
  ano?: number;
  mandatos?: string[];
  dtInicioVigencia?: string;
  dtTerminoVigenciaAtualizado?: string;
  nivel?: NivelAlocacaoTerritorial | string;
  bairro?: string | null;
  prefeituraBairro?: string | null;
  prefeitura_bairro?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  estagioAlocacao?: string | null;
}

export interface EmpreiteiraResumo {
  cnpj: string;
  razaoSocial: string;
  totalObras: number;
  totalObrasAtivas: number;
  valorTotalContratado: number;
  obrasIds?: (number | string)[];
}

export interface FunilFinanceiro {
  valorOriginal: number;
  valorContratualVigente: number;
  valorEmpenhado: number;
  valorLiquidado: number;
  valorPago: number;
  percentualExecutado: number;
  valorAditivos?: number;
  deltaPercentualAditivos?: number;
}

export interface EmpreiteiraInfo {
  razaoSocial: string;
  cnpj: string;
  totalObras: number;
  totalObrasAtivas?: number;
  valorTotalContratado: number;
  outrasObrasCount?: number;
  outrasObrasIds?: (number | string)[];
}

export interface AditivoContratual {
  nuAditivo: string;
  dsTipoAlteracao: string;
  dsObjetoAditivo?: string;
  dtAssinatura?: string;
  dtTerminoVigencia?: string;
  dtPublicacao?: string;
  nuDom?: string;
  vlAditivo: number;
}

export interface DotacaoRecurso {
  subacao?: string;
  fonteRecurso: string;
  classificacao?: string;
}

export interface VigenciaInfo {
  dataInicio?: string;
  dataFimOriginal?: string;
  dataTerminoAtualizado?: string;
  prazoOriginal?: string;
  prazoAtualizado?: string;
}

export interface DomInfo {
  nuDom: string;
  dataPublicacao?: string;
}

export interface FichaLimpaObra {
  id: number | string;
  unidadeGestora: string;
  numeroContrato: string;
  numeroContratoOriginal?: string;
  nuProcesso?: string;
  objeto: string;
  situacao?: string;
  empreiteira: EmpreiteiraInfo;
  vigencia: VigenciaInfo;
  dom: DomInfo;
  funilFinanceiro: FunilFinanceiro;
  aditivos: AditivoContratual[];
  dotacao: DotacaoRecurso[];
  empenhos?: any[];
  liquidacoes?: any[];
  pagamentos?: any[];
  tema?: string;
  semaforo?: SemaforoInfo;
  nivel?: string;
  bairro?: string | null;
  prefeituraBairro?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  estagioAlocacao?: string | null;
}

export interface IndexData {
  metadata: {
    generatedAt: string;
    anoReferencia: number;
    mandatosDisponiveis?: string[];
  };
  kpis_globais: GlobalKpis;
  concentracao_empreiteiras?: EmpreiteiraResumo[];
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
  valorTotal?: number;
  valorPago?: number;
  totalObras?: number;
  obrasVerde?: number;
  obrasAmarelo?: number;
  obrasVermelho?: number;
  investimentoPorHabitante?: number;
  investimentoPorHabitantePago?: number;
}

export interface FilterState {
  mandato: string | "todos";
  ano?: number | "todos";
  orgao: string | "todos";
  tema: string | "todos";
  semaforo: SemaforoStatus | "todos";
  busca: string;
  metricType: MetricType;
}

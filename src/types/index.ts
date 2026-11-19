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

export type VocacaoObra =
  | "Vizinhança e Comunidade"
  | "Mobilidade Estrutural e Orlas"
  | "Equipamentos e Marcos da Cidade";

export const VOCACOES_PADRAO: VocacaoObra[] = [
  "Vizinhança e Comunidade",
  "Mobilidade Estrutural e Orlas",
  "Equipamentos e Marcos da Cidade",
];

export const VOCACAO_BADGE_CLASS: Record<VocacaoObra, string> = {
  "Vizinhança e Comunidade": "bg-emerald-50 text-emerald-800 border border-emerald-200",
  "Mobilidade Estrutural e Orlas": "bg-sky-50 text-sky-800 border border-sky-200",
  "Equipamentos e Marcos da Cidade": "bg-amber-50 text-amber-800 border border-amber-200",
};

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
  valorPagoNaoLocalizado?: number | null;
  percentualNaoLocalizado?: number;
  valorPagoDisponivel?: boolean;
  obrasSemValorPago?: number;
}

export interface BairroResumo {
  id: number | string;
  nome: string;
  prefeitura_bairro: string;
  populacao: number;
  indice_vulnerabilidade?: number | null;
  is_zona_especial_nao_residencial: boolean;
  isZonaEspecialNaoResidencial?: boolean;
  is_centralidade_metropolitana?: boolean;
  isCentralidadeMetropolitana?: boolean;
  pct_esgoto_inadequado?: number;
  pct_agua_inadequada?: number;
  pct_analfabetismo_15mais?: number;
  vulnerabilidade_estimada_contiguidade?: boolean;
  valorTotal?: number;
  valorLiquidado?: number;
  valorPago?: number | null;
  valorLiquidadoDireto?: number;
  valorPagoDireto?: number | null;
  valorLiquidadoFrentes?: number;
  valorPagoFrentes?: number | null;
  totalFrentesMedicao?: number;
  totalObras?: number;
  obrasVerde?: number;
  obrasAmarelo?: number;
  obrasVermelho?: number;
  investimentoPorHabitante?: number | null;
  investimentoPorHabitantePago?: number | null;
  valorPagoDisponivel?: boolean;
  obrasSemValorPago?: number;
}

export interface PrefeituraBairroResumo {
  id: number | string;
  nome: string;
  populacao_total: number;
  indice_vulnerabilidade?: number | null;
  pct_esgoto_inadequado?: number;
  pct_agua_inadequada?: number;
  pct_analfabetismo_15mais?: number;
  vulnerabilidade_estimada_contiguidade?: boolean;
  bairros_vulnerabilidade_estimada?: string[];
  valorTotal?: number;
  valorLiquidado?: number;
  valorPago?: number | null;
  valorLiquidadoDireto?: number;
  valorPagoDireto?: number | null;
  valorLiquidadoFrentes?: number;
  valorPagoFrentes?: number | null;
  totalFrentesMedicao?: number;
  totalObras?: number;
  obrasVerde?: number;
  obrasAmarelo?: number;
  obrasVermelho?: number;
  investimentoPorHabitante?: number | null;
  investimentoPorHabitantePago?: number | null;
  valorPagoDisponivel?: boolean;
  obrasSemValorPago?: number;
}

export interface FrenteMedicao {
  notaLiquidacao: string;
  nivel: NivelAlocacaoTerritorial | string;
  bairro?: string | null;
  prefeituraBairro?: string | null;
  valorLiquidado: number;
  valorPago: number | null;
  dataLiquidacao?: string | null;
  trechoComprobatorio?: string | null;
  documentoOrigem?: string | null;
  justificativa?: string | null;
}

export interface CotaListaFechada {
  bairro: string;
  prefeituraBairro?: string | null;
  unidades: number;
  totalUnidades: number;
  peso: number;
  fracao: string;
  latitude?: number | null;
  longitude?: number | null;
  descricaoUnidades?: string | null;
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
  valorPago?: number | null;
  percentualExecutado: number;
  situacao: string;
  credor: string;
  cnpj?: string;
  cnpjCredor?: string;
  tema?: TemaObra | string;
  vocacao?: VocacaoObra | string;
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
  frentesMedicao?: FrenteMedicao[];
  cotasListaFechada?: CotaListaFechada[];
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
  valorPago: number | null;
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

export interface FontesOficiaisInfo {
  portalTransparencia: {
    nome: string;
    url: string;
  };
  chaveCanonica: {
    cdUnidadeGestora: string | null;
    unidadeGestora: string | null;
    nuContratoSigef: string | null;
  };
  nuProcesso: string | null;
  domContrato: {
    nuDom: string | null;
    url: string | null;
  };
  domAditivos: Array<{
    nuAditivo?: string;
    nuDom: string;
    dtPublicacao?: string | null;
    url: string;
  }>;
  lastroTerritorial: {
    nivel: string | null;
    estagioAlocacao: string | null;
    bairro: string | null;
    prefeituraBairro: string | null;
    origem: string;
    trechoComprobatorio?: string | null;
    documentoOrigem?: string | null;
    justificativa?: string | null;
    cotasListaFechada?: CotaListaFechada[];
  };
}

export interface FichaLimpaObra {
  versaoDados?: string;
  id: number | string;
  cdUnidadeGestora?: string | number | null;
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
  apuracaoPagamentos?: {
    registrosSemValor: number;
    situacao: "sem_registros" | "indisponivel" | "saldo_registrado";
  };
  tema?: string;
  vocacao?: VocacaoObra | string;
  semaforo?: SemaforoInfo;
  nivel?: string;
  bairro?: string | null;
  prefeituraBairro?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  estagioAlocacao?: string | null;
  fontesOficiais?: FontesOficiaisInfo;
  frentesMedicao?: FrenteMedicao[];
  cotasListaFechada?: CotaListaFechada[];
}

export interface IndexData {
  metadata: {
    generatedAt: string;
    anoReferencia: number;
    mandatosDisponiveis?: string[];
    atualizacao?: {
      versaoDados: string;
      concluidaEm: string;
      dataReferenciaPagamentos: string;
      inicioConsultas: string;
      fimConsultas: string;
      consultas: string;
      validacoes: string;
      coberturaHistorica: string;
      limitacoesConhecidas: string[];
    };
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
  indice_vulnerabilidade?: number | null;
  is_zona_especial_nao_residencial?: boolean;
  isZonaEspecialNaoResidencial?: boolean;
  is_centralidade_metropolitana?: boolean;
  isCentralidadeMetropolitana?: boolean;
  pct_esgoto_inadequado?: number;
  pct_agua_inadequada?: number;
  pct_analfabetismo_15mais?: number;
  vulnerabilidade_estimada_contiguidade?: boolean;
  bairros_vulnerabilidade_estimada?: string[];
  valorTotal?: number;
  valorLiquidado?: number;
  valorPago?: number | null;
  valorLiquidadoDireto?: number;
  valorPagoDireto?: number | null;
  valorLiquidadoFrentes?: number;
  valorPagoFrentes?: number | null;
  totalFrentesMedicao?: number;
  totalObras?: number;
  obrasVerde?: number;
  obrasAmarelo?: number;
  obrasVermelho?: number;
  investimentoPorHabitante?: number | null;
  investimentoPorHabitantePago?: number | null;
  valorPagoDisponivel?: boolean;
  obrasSemValorPago?: number;
}

export interface FilterState {
  mandato: string | "todos";
  ano?: number | "todos";
  orgao: string | "todos";
  tema: string | "todos";
  vocacoes: VocacaoObra[];
  semaforo: SemaforoStatus | "todos";
  busca: string;
  metricType: MetricType;
}

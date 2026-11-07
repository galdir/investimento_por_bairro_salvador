import { BairroResumo, PrefeituraBairroResumo, TerritorySelection } from "../types";

/**
 * Converte um Bairro cadastral em um objeto de seleção territorial unificado.
 *
 * @summary Encapsula a conversão de tipo para evitar repetição de parâmetros (Data Clump).
 * @param b - Objeto de BairroResumo.
 * @returns Objeto TerritorySelection configurado para o bairro.
 */
export function createBairroSelection(b: BairroResumo): TerritorySelection {
  return {
    tipo: "bairro",
    id: b.id,
    nome: b.nome,
    prefeitura_bairro: b.prefeitura_bairro,
    populacao: b.populacao,
    indice_vulnerabilidade: b.indice_vulnerabilidade,
    is_zona_especial_nao_residencial: b.is_zona_especial_nao_residencial,
    isZonaEspecialNaoResidencial: b.isZonaEspecialNaoResidencial ?? b.is_zona_especial_nao_residencial,
    valorTotal: b.valorTotal,
    valorPago: b.valorPago,
    totalObras: b.totalObras,
    obrasVerde: b.obrasVerde,
    obrasAmarelo: b.obrasAmarelo,
    obrasVermelho: b.obrasVermelho,
    investimentoPorHabitante: b.investimentoPorHabitante,
    investimentoPorHabitantePago: b.investimentoPorHabitantePago,
  };
}

/**
 * Converte uma Prefeitura-Bairro cadastral em um objeto de seleção territorial unificado.
 *
 * @summary Encapsula a conversão de tipo para evitar repetição de parâmetros (Data Clump).
 * @param pb - Objeto de PrefeituraBairroResumo.
 * @returns Objeto TerritorySelection configurado para a Prefeitura-Bairro.
 */
export function createPrefeituraSelection(pb: PrefeituraBairroResumo): TerritorySelection {
  return {
    tipo: "prefeitura_bairro",
    id: pb.id,
    nome: pb.nome,
    populacao: pb.populacao_total,
    valorTotal: pb.valorTotal,
    valorPago: pb.valorPago,
    totalObras: pb.totalObras,
    obrasVerde: pb.obrasVerde,
    obrasAmarelo: pb.obrasAmarelo,
    obrasVermelho: pb.obrasVermelho,
    investimentoPorHabitante: pb.investimentoPorHabitante,
    investimentoPorHabitantePago: pb.investimentoPorHabitantePago,
  };
}

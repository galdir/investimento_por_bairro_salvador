import React from "react";
import { MetricType, ObraCompacta, TerritorySelection } from "../types";
import { formatCurrency, formatDecimal, formatNumber } from "../utils/formatters";
import {
  filterFrentesByTerritory,
  getObraTerritoryShare,
  getTerritoryAbsoluteTotal,
  getTerritoryInvestmentState,
  hasNumericValue,
  isCentralidadeMetropolitana,
} from "../utils/territory";
import { MonetaryValue } from "./MonetaryValue";

interface TerritorySidebarProps {
  /**
   * Território selecionado no mapa (Bairro Oficial ou Prefeitura-Bairro) ou null se nenhum.
   */
  territorio: TerritorySelection | null;
  /**
   * Callback para limpar a seleção e fechar o painel.
   */
  onClear: () => void;
  /**
   * Callback opcional para navegar diretamente para a visão de tabela com filtro do território.
   */
  onViewWorksInTable?: () => void;
  /**
   * Métrica financeira ativa na barra superior: "vigente" (Valor Contratual Vigente) ou "executado" (Valor Executado / Pago).
   */
  metricType?: MetricType;
  /**
   * Callback para abrir o modal de nota metodológica do Índice de Vulnerabilidade.
   */
  onOpenNotaMetodologica?: () => void;
  /**
   * Lista de obras filtradas para listar Frentes de Medição vinculadas ao território.
   */
  obras?: ObraCompacta[];
  /**
   * Callback para abrir a Ficha Limpa da Obra ao clicar em uma Frente de Medição.
   */
  onSelectObra?: (obra: ObraCompacta) => void;
  /**
   * Callback opcional para alternar a métrica financeira global diretamente para "executado" (Valor Executado / Pago).
   */
  onSwitchToExecutado?: () => void;
}

/**
 * Painel lateral "Raio-X do Bairro / Prefeitura-Bairro".
 *
 * @summary Apresenta o perfil demográfico, social e financeiro detalhado da área selecionada no mapa.
 * @description Exibe o nome do território, seu vínculo regional com a Prefeitura-Bairro,
 * a contagem de população residente oficial do Censo 2022 do IBGE, o montante total investido,
 * o Investimento por Habitante (R$/hab), o Índice de Vulnerabilidade do Bairro, a distribuição
 * de obras pelo Semáforo (Verde, Amarelo e Vermelho) e a indicação especial quando o bairro é
 * uma Zona Especial Não-Residencial (Aeroporto, Porto Seco Pirajá e CAB).
 *
 * @param props - Propriedades contendo o território ativo e funções de fechamento e navegação.
 * @returns Elemento JSX do painel lateral.
 * @throws Não lança exceções.
 */
export const TerritorySidebar: React.FC<TerritorySidebarProps> = ({
  territorio,
  onClear,
  onViewWorksInTable,
  metricType = "vigente",
  onOpenNotaMetodologica,
  obras = [],
  onSelectObra,
  onSwitchToExecutado,
}) => {
  if (!territorio) {
    return null;
  }

  const ehZonaEspecial = !!(
    territorio.is_zona_especial_nao_residencial || territorio.isZonaEspecialNaoResidencial
  );
  const ehBairro = territorio.tipo === "bairro";
  const ehCentralidade =
    ehBairro && !ehZonaEspecial && isCentralidadeMetropolitana(territorio);

  const isExecutado = metricType === "executado";
  const invState = getTerritoryInvestmentState(territorio, metricType, territorio.tipo);
  const totalInvestido =
    invState.kind === "value" ? invState.total : getTerritoryAbsoluteTotal(territorio, metricType);
  const totalInvestidoDisponivel = totalInvestido !== undefined;
  const totalObras = territorio.totalObras ?? 0;
  const obrasVerde = territorio.obrasVerde ?? 0;
  const obrasAmarelo = territorio.obrasAmarelo ?? 0;
  const obrasVermelho = territorio.obrasVermelho ?? 0;

  const frentesNoTerritorio = filterFrentesByTerritory(obras, territorio);
  const cotasNoTerritorio = obras
    .map((obra) => {
      const share = getObraTerritoryShare(obra, territorio);
      if (!share.isCotaParte || !share.matched) return null;
      const valorBase = isExecutado
        ? hasNumericValue(obra.valorPago)
          ? obra.valorPago
          : undefined
        : (obra.valorContratualVigente ?? 0);
      return {
        obra,
        share,
        valorProporcional: valorBase !== undefined ? valorBase * share.peso : undefined,
        valorIntegral: valorBase,
      };
    })
    .filter((item): item is NonNullable<typeof item> => item !== null);

  const totalFrentes = territorio.totalFrentesMedicao ?? frentesNoTerritorio.length;
  const valorPagoDireto = hasNumericValue(territorio.valorPagoDireto)
    ? territorio.valorPagoDireto
    : hasNumericValue(territorio.valorPago)
      ? territorio.valorPago
      : 0;
  const valorPagoFrentes = territorio.valorPagoFrentes;
  const valorLiquidadoFrentes = territorio.valorLiquidadoFrentes ?? 0;
  const temFrentes =
    totalFrentes > 0 || (valorPagoFrentes ?? 0) > 0 || valorLiquidadoFrentes > 0 || frentesNoTerritorio.length > 0;
  const bairrosEstimados = territorio.bairros_vulnerabilidade_estimada || [];

  return (
    <aside
      data-testid="raio-x-container"
      aria-label={`Resumo territorial de ${territorio.nome}`}
      className="w-full bg-white rounded-xl border border-slate-200 p-4 sm:p-5 flex flex-col shadow-sm"
    >
      {/* Cabeçalho do Raio-X */}
      <div className="flex items-start justify-between pb-4 border-b border-slate-100">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
            {ehBairro ? "Bairro Oficial" : "Prefeitura-Bairro"}
          </span>
          <h2
            data-testid="raio-x-nome"
            className="text-xl font-bold text-slate-900 mt-1 tracking-tight"
          >
            {territorio.nome}
          </h2>
          {territorio.prefeitura_bairro && (
            <p className="text-xs text-slate-500 mt-0.5">
              Prefeitura-Bairro:{" "}
              <span className="font-medium text-slate-700">{territorio.prefeitura_bairro}</span>
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onClear}
          aria-label="Fechar painel lateral"
          className="text-slate-400 hover:text-slate-600 p-1 rounded-md hover:bg-slate-100 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Alerta de Zona Especial Não-Residencial */}
      {ehZonaEspecial && (
        <div
          data-testid="badge-zona-especial"
          className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-xs"
        >
          <div className="font-semibold flex items-center gap-1.5 text-amber-900">
            <svg className="w-4 h-4 text-amber-600 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            Zona Especial Não-Residencial
          </div>
          <p className="mt-1 leading-relaxed text-amber-700">
            Área de ocupação institucional, aeroportuária ou logística com população residencial nula ou residual. Excluída dos rankings de Investimento por Habitante para evitar distorções estatísticas per capita.
          </p>
        </div>
      )}

      {/* Alerta de Centralidade Metropolitana de Baixa População Residente */}
      {ehCentralidade && (
        <div
          data-testid="badge-centralidade-metropolitana"
          className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-xs"
        >
          <div className="font-semibold flex items-center gap-1.5 text-amber-900">
            <svg className="w-4 h-4 text-amber-600 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            Centralidade Metropolitana de Baixa População Residente
          </div>
          <p className="mt-1 leading-relaxed text-amber-700">
            Área de vocação portuária, financeira e cultural metropolitana (ZUE-3/ZCMe) com menos de 1.000 habitantes. Isenta do cálculo de Investimento por Habitante para evitar distorções per capita, preservando integralmente seu Índice de Vulnerabilidade do Bairro.
          </p>
        </div>
      )}

      {/* Métricas Principais: Investimento Total, Per Capita, População e Vulnerabilidade */}
      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
        <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
            {isExecutado ? "Total Pago Alocado" : "Total Contratual Alocado"}
          </span>
          <div className="text-base font-bold text-slate-900 mt-0.5 block">
            {totalInvestidoDisponivel ? (
              <MonetaryValue value={totalInvestido!} compact testId="raio-x-total-investido" />
            ) : (
              <span
                data-testid="raio-x-total-investido"
                className="text-xs font-semibold text-amber-800"
              >
                Pagamento indisponível
              </span>
            )}
          </div>
          <span className="text-[10px] text-slate-500">{totalObras} contratos</span>
        </div>

        <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
            R$ / Habitante
          </span>
          <span
            data-testid="raio-x-investimento-per-capita"
            className="text-base font-bold text-emerald-700 mt-0.5 block tabular-nums"
          >
            {invState.kind === "exempt"
              ? "Isento"
              : invState.kind === "unavailable"
                ? invState.reason === "population"
                  ? "Per capita indisponível"
                  : "Pagamento indisponível"
                : formatCurrency(invState.perCapita)}
          </span>
          <span className="text-[10px] text-slate-500">
            {ehZonaEspecial
              ? "Zona Especial"
              : ehCentralidade
                ? "Centralidade Metropolitana"
                : invState.kind === "unavailable"
                  ? invState.reason === "population"
                    ? "População censitária indisponível"
                    : "Sem registro de pagamento"
                  : "por morador"}
          </span>
        </div>

        <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
            População (Censo 2022)
          </span>
          <span
            data-testid="raio-x-populacao"
            className="text-base font-bold text-slate-900 mt-0.5 block tabular-nums"
          >
            {formatNumber(territorio.populacao)}
          </span>
          <span className="text-[10px] text-slate-500">habitantes</span>
        </div>

        <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
            Vulnerabilidade
          </span>
          <span
            data-testid="raio-x-vulnerabilidade"
            className={`text-base font-bold mt-0.5 block tabular-nums ${ehZonaEspecial ? "text-slate-500" : "text-indigo-800"}`}
          >
            {ehZonaEspecial
              ? "Isento"
              : hasNumericValue(territorio.indice_vulnerabilidade)
                ? formatDecimal(territorio.indice_vulnerabilidade)
                : "Indisponível"}
          </span>
          <span className="text-[10px] text-slate-500">
            {ehZonaEspecial
              ? "Sem domicílios"
              : !hasNumericValue(territorio.indice_vulnerabilidade)
                ? "Dado indisponível"
                : territorio.vulnerabilidade_estimada_contiguidade
                  ? "Inclui estimativa"
                  : "Índice Censo 2022"}
          </span>
        </div>
      </div>

      {/* Distinção entre Contratos Diretos e Frentes de Medição (Guarda-Chuva) */}
      {temFrentes && (
        <div
          data-testid="secao-frentes-medicao"
          className="mt-4 bg-indigo-50/60 border border-indigo-200 rounded-xl p-3.5 space-y-2.5"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-indigo-950">
              Origem da Execução Territorial
            </span>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-800">
              {totalFrentes} {totalFrentes === 1 ? "frente" : "frentes"}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-white/90 border border-slate-200 rounded-lg p-2">
              <span className="text-[10px] font-medium text-slate-500 block">Contratos diretos</span>
              <span className="font-bold text-slate-900">{formatCurrency(valorPagoDireto)}</span>
              <span className="text-[10px] text-slate-400 block">pago ({totalObras} obras)</span>
            </div>
            <div className="bg-white/90 border border-indigo-200 rounded-lg p-2">
              <span className="text-[10px] font-medium text-indigo-700 block">Frentes de Medição</span>
              <span className="font-bold text-indigo-900">{valorPagoFrentes == null && totalFrentes > 0 ? "Indisponível" : formatCurrency(valorPagoFrentes ?? 0)}</span>
              <span className="text-[10px] text-indigo-600 block">
                liquidado: {formatCurrency(valorLiquidadoFrentes)}
              </span>
            </div>
          </div>

          <p className="text-[10px] text-indigo-800 leading-relaxed">
            Frentes de Medição somam apenas valores liquidados e pagos comprovados em notas de liquidação, sem inflar o Valor Contratual Vigente nem duplicar contratos.
          </p>

          {!isExecutado && (
            <div
              data-testid="aviso-metrica-vigente-frentes"
              className="bg-amber-50 border border-amber-200 rounded-lg p-2.5 text-[11px] text-amber-900 space-y-1.5"
            >
              <p className="leading-relaxed">
                Com a métrica <strong>Valor Contratual Vigente</strong> ativa, o Total Investido do território reflete apenas obras de alocação direta. As <strong>Frentes de Medição</strong> somam apenas em <strong>Valor Executado / Pago</strong>.
              </p>
              {onSwitchToExecutado && (
                <button
                  type="button"
                  data-testid="btn-atalho-metrica-executado"
                  onClick={onSwitchToExecutado}
                  className="w-full py-1.5 px-2.5 rounded-md bg-amber-600 hover:bg-amber-700 text-white text-[11px] font-semibold transition-colors shadow-sm"
                >
                  Alternar para Valor Executado / Pago
                </button>
              )}
            </div>
          )}

          {frentesNoTerritorio.length > 0 && (
            <div className="space-y-1.5 max-h-48 overflow-y-auto pr-0.5">
              {frentesNoTerritorio.map(({ obra, frente }) => (
                <div
                  key={`${obra.id}-${frente.notaLiquidacao}`}
                  className="bg-white border border-indigo-100 rounded-lg p-2 text-[11px]"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-slate-800">
                      {obra.unidadeGestora} · {obra.numeroContrato}
                    </span>
                    <span className="font-mono text-[10px] text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded">
                      {frente.notaLiquidacao}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-slate-600 mt-1">
                    <span>Liquidado: {formatCurrency(frente.valorLiquidado)}</span>
                    <span>Pago: {frente.valorPago == null ? "Indisponível" : formatCurrency(frente.valorPago)}</span>
                  </div>
                  {frente.trechoComprobatorio && (
                    <p className="text-[10px] text-slate-500 mt-1 line-clamp-2">
                      {frente.trechoComprobatorio}
                    </p>
                  )}
                  {onSelectObra && (
                    <button
                      type="button"
                      onClick={() => onSelectObra(obra)}
                      className="mt-1.5 text-[10px] font-semibold text-indigo-700 hover:text-indigo-900 underline"
                    >
                      Ver Ficha Limpa da Obra
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {cotasNoTerritorio.length > 0 && (
        <div
          data-testid="secao-cotas-lista-fechada"
          className="mt-4 bg-amber-50/70 p-3.5 rounded-xl border border-amber-200 space-y-2.5"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold text-amber-950">
              Rateio por Cota-Parte (Lista Fechada)
            </span>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-900">
              {cotasNoTerritorio.length} {cotasNoTerritorio.length === 1 ? "contrato" : "contratos"}
            </span>
          </div>

          <p className="text-[10px] text-amber-900 leading-relaxed">
            Contratos com lista fechada distribuídos proporcionalmente às unidades/equipamentos deste território (peso n/M), sem duplicação global.
          </p>

          <div className="space-y-2 max-h-60 overflow-y-auto pr-0.5">
            {cotasNoTerritorio.map(({ obra, share, valorProporcional, valorIntegral }) => (
              <div
                key={obra.id}
                data-testid={`raiox-cota-item-${obra.id}`}
                className="bg-white border border-amber-200/80 rounded-lg p-2.5 text-[11px] space-y-1.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-slate-800">
                    {obra.unidadeGestora} · {obra.numeroContrato || "S/N"}
                  </span>
                  <span
                    data-testid={`badge-cota-parte-${obra.id}`}
                    className="font-semibold text-[10px] text-amber-900 bg-amber-100 px-1.5 py-0.5 rounded border border-amber-300 shrink-0"
                  >
                    Cota-Parte ({share.fracao})
                  </span>
                </div>

                <p className="text-[11px] text-slate-700 line-clamp-2">{obra.objeto}</p>

                <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-600">
                  <span>
                    Cota territorial:{" "}
                    <strong className="text-slate-900">
                      {valorProporcional !== undefined
                        ? formatCurrency(valorProporcional)
                        : "Pagamento indisponível"}
                    </strong>
                  </span>
                  <span className="text-[10px] text-slate-500">
                    Total contrato:{" "}
                    <strong className="text-slate-700">
                      {valorIntegral !== undefined
                        ? formatCurrency(valorIntegral)
                        : "Pagamento indisponível"}
                    </strong>
                  </span>
                </div>

                <div className="space-y-1">
                  {share.cotas.map((cota) => (
                    <div
                      key={`${obra.id}-${cota.bairro}`}
                      className="text-[10px] text-slate-600 bg-amber-50/60 border border-amber-200/70 rounded px-2 py-1"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-slate-800">{cota.bairro}</span>
                        <span className="font-medium text-amber-900">
                          {cota.fracao} ·{" "}
                          {valorIntegral !== undefined
                            ? formatCurrency(valorIntegral * cota.peso)
                            : "Pagamento indisponível"}
                        </span>
                      </div>
                      {cota.descricaoUnidades && (
                        <p className="text-[10px] text-slate-500 mt-0.5">
                          {cota.descricaoUnidades}
                        </p>
                      )}
                    </div>
                  ))}
                </div>

                {onSelectObra && (
                  <button
                    type="button"
                    onClick={() => onSelectObra(obra)}
                    className="text-[10px] font-semibold text-amber-800 hover:text-amber-950 underline"
                  >
                    Ver Ficha Limpa da Obra
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Breakdown de Obras por Semáforo */}
      <div className="mt-4 bg-slate-50 p-3.5 rounded-xl border border-slate-100">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-slate-700">
            Obras por Semáforo de Risco:
          </span>
          <span className="text-xs text-slate-400 font-medium">{totalObras} total</span>
        </div>
        <div className="grid grid-cols-3 gap-1.5 text-center text-xs">
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-2 text-emerald-800">
            <span className="block font-bold text-sm" data-testid="raio-x-obras-verde">
              {obrasVerde}
            </span>
            <span className="text-[10px] text-emerald-700">No Prazo</span>
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-2 text-amber-800">
            <span className="block font-bold text-sm" data-testid="raio-x-obras-amarelo">
              {obrasAmarelo}
            </span>
            <span className="text-[10px] text-amber-700">Atenção</span>
          </div>
          <div className="bg-rose-50 border border-rose-200 rounded-lg p-2 text-rose-800">
            <span className="block font-bold text-sm" data-testid="raio-x-obras-vermelho">
              {obrasVermelho}
            </span>
            <span className="text-[10px] text-rose-700">Crítica</span>
          </div>
        </div>
      </div>

      {/* Composição social e estimativas por contiguidade */}
      <div className="mt-4 space-y-3">
        {(ehZonaEspecial || territorio.indice_vulnerabilidade !== undefined) && (
          <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-100">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">
                Índice de Vulnerabilidade e Composição (Censo 2022)
              </span>
              <div className="flex items-center gap-2">
                {onOpenNotaMetodologica && (
                  <button
                    type="button"
                    data-testid="btn-como-calculado-raiox"
                    onClick={onOpenNotaMetodologica}
                    title="Como é calculado o Índice de Vulnerabilidade?"
                    className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200/60 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                  >
                    <span className="font-bold">ⓘ</span>
                    <span>Como é calculado?</span>
                  </button>
                )}
                <span className={`text-xs font-bold ${ehZonaEspecial ? "text-slate-500" : "text-slate-900"}`}>
                  {ehZonaEspecial
                    ? "Isento"
                    : hasNumericValue(territorio.indice_vulnerabilidade)
                      ? formatDecimal(territorio.indice_vulnerabilidade)
                      : "Indisponível"}
                </span>
              </div>
            </div>

            {ehZonaEspecial ? (
              <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                Zona Especial Não-Residencial isenta de cálculo de vulnerabilidade social (sem domicílios permanentes no Censo 2022).
              </p>
            ) : !hasNumericValue(territorio.indice_vulnerabilidade) ? (
              <p className="text-[11px] text-slate-600 mt-1.5 leading-relaxed">
                Índice de Vulnerabilidade indisponível nos dados censitários deste território.
              </p>
            ) : (
              <>
                {/* Barra Visual de Intensidade */}
                <div className="w-full bg-slate-200 h-2 rounded-full mt-2 overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                    style={{
                      width: `${Math.min(100, Math.max(5, territorio.indice_vulnerabilidade * 100))}%`,
                    }}
                  ></div>
                </div>

                {/* Badge de Contiguidade Territorial para Bairros ausentes na malha SIDRA */}
                {ehBairro && territorio.vulnerabilidade_estimada_contiguidade && (
                  <div
                    data-testid="badge-contiguidade-territorial"
                    className="mt-2.5 flex items-center gap-1.5 px-2 py-1 bg-amber-50 border border-amber-200 rounded text-amber-800 text-[11px]"
                  >
                    <svg className="w-3.5 h-3.5 shrink-0 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span>Estimativa por contiguidade territorial (bairro sem linha individual na malha N102 do IBGE)</span>
                  </div>
                )}

                {/* Badge de Contiguidade na Composição Regional (Prefeitura-Bairro) */}
                {!ehBairro && territorio.vulnerabilidade_estimada_contiguidade && (
                  <div
                    data-testid="badge-contiguidade-regional"
                    className="mt-2.5 flex items-center gap-1.5 px-2 py-1.5 bg-amber-50 border border-amber-200 rounded text-amber-900 text-[11px]"
                  >
                    <svg className="w-3.5 h-3.5 shrink-0 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span>
                      Composição da Prefeitura-Bairro inclui vulnerabilidade estimada por contiguidade
                      {bairrosEstimados.length > 0 ? `: ${bairrosEstimados.join(", ")}` : "."}
                    </span>
                  </div>
                )}

                {/* Decomposição Multidimensional Censo 2022 */}
                {(territorio.pct_esgoto_inadequado !== undefined ||
                  territorio.pct_agua_inadequada !== undefined ||
                  territorio.pct_analfabetismo_15mais !== undefined) && (
                  <div className="mt-3 pt-3 border-t border-slate-200/60">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-semibold text-slate-600 uppercase tracking-wider">
                        Componentes (Censo 2022)
                      </span>
                      <span className="text-[10px] text-slate-400">IBGE</span>
                    </div>
                    <div className="space-y-1.5 text-xs">
                      <div className="flex justify-between items-center text-slate-600">
                        <span className="text-[11px]">Déficit de Esgoto:</span>
                        <span data-testid="raio-x-esgoto" className="font-semibold text-slate-900">
                          {territorio.pct_esgoto_inadequado !== undefined
                            ? `${formatDecimal(territorio.pct_esgoto_inadequado)}%`
                            : "-"}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-slate-600">
                        <span className="text-[11px]">Déficit de Água:</span>
                        <span data-testid="raio-x-agua" className="font-semibold text-slate-900">
                          {territorio.pct_agua_inadequada !== undefined
                            ? `${formatDecimal(territorio.pct_agua_inadequada)}%`
                            : "-"}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-slate-600">
                        <span className="text-[11px]">Analfabetismo (15+ anos):</span>
                        <span data-testid="raio-x-analfabetismo" className="font-semibold text-slate-900">
                          {territorio.pct_analfabetismo_15mais !== undefined
                            ? `${formatDecimal(territorio.pct_analfabetismo_15mais)}%`
                            : "-"}
                        </span>
                      </div>
                    </div>
                    {!ehBairro && (
                      <p className="text-[10px] text-slate-400 mt-2 leading-relaxed italic">
                        Média ponderada pela população dos bairros componentes (Censo 2022).
                      </p>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Botões de Ação na Base */}
      <div className="mt-auto pt-4 border-t border-slate-100 space-y-2">
        {onViewWorksInTable && (
          <button
            type="button"
            data-testid="btn-ver-obras-tabela"
            onClick={onViewWorksInTable}
            className="w-full py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
            Ver obras deste território na tabela (
            {totalFrentes > 0
              ? `${totalObras} ${totalObras === 1 ? "contrato" : "contratos"} · ${totalFrentes} ${totalFrentes === 1 ? "frente" : "frentes"}`
              : totalObras}
            )
          </button>
        )}
        <button
          type="button"
          data-testid="btn-limpar-selecao-territorio"
          onClick={onClear}
          className="w-full py-1.5 px-3 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
        >
          Limpar Seleção do Mapa
        </button>
      </div>
    </aside>
  );
};

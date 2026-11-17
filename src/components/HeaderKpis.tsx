import React from "react";
import { GlobalKpis, MetricType } from "../types";
import { formatCurrency, formatDate, formatNumber } from "../utils/formatters";
import { hasNumericPayment } from "../utils/territory";
import { MonetaryValue } from "./MonetaryValue";

interface HeaderKpisProps {
  /**
   * Indicadores financeiros e quantitativos da comparação municipal (invariantes à seleção territorial).
   */
  kpis: GlobalKpis;
  /**
   * Camada territorial ativa na comparação ('prefeituras' ou 'bairros').
   */
  activeLayer?: "bairros" | "prefeituras";
  /**
   * Quantidade de territórios na comparação ativa.
   */
  territorioCount?: number;
  /**
   * Valor territorialmente alocado na comparação ativa segundo a métrica selecionada.
   */
  valorAlocadoTerritorial?: number;
  /**
   * Indica se há dados disponíveis de pagamento para o valor alocado (false se todos ausentes).
   */
  valorAlocadoDisponivel?: boolean;
  /**
   * Quantidade de obras alocadas aos territórios comparados.
   */
  totalObrasAlocadas?: number;
  /**
   * Quantidade de contratos exclusivos de Prefeitura-Bairro não rateados entre Bairros Oficiais.
   */
  contratosPrefeituraBairroSemRateioCount?: number;
  /**
   * Indica se a contagem de obras em Bairros Oficiais foi apurada no nível exato do recorte.
   */
  isExactLayerWorkCount?: boolean;
  /**
   * Data ISO de atualização do acervo (metadata.generatedAt).
   */
  generatedAt?: string;
  /**
   * Métrica financeira ativa: 'vigente' (Valor Contratual Vigente) ou 'executado' (Valor Pago).
   */
  metricType?: MetricType;
  /**
   * Mandato Municipal selecionado nos filtros (ex: '2025-2028', '2021-2024' ou 'todos').
   */
  mandato?: string;
}

/**
 * Cabeçalho compacto da comparação municipal de Salvador.
 * Mantém escopo municipal constante mesmo quando um território específico está selecionado.
 */
export const HeaderKpis: React.FC<HeaderKpisProps> = ({
  kpis,
  activeLayer = "prefeituras",
  territorioCount = 0,
  valorAlocadoTerritorial,
  valorAlocadoDisponivel = true,
  totalObrasAlocadas,
  contratosPrefeituraBairroSemRateioCount = 0,
  isExactLayerWorkCount = true,
  generatedAt,
  metricType = "executado",
  mandato,
}) => {
  const isVigente = metricType === "vigente";
  const metricLabel = isVigente ? "Valor Contratual Vigente" : "Valor Pago";
  const totalNaoLocalizado = kpis.totalNaoLocalizado ?? 0;
  const valorNaoLocalizado = isVigente
    ? (kpis.valorNaoLocalizado ?? 0)
    : hasNumericPayment(kpis.valorPagoNaoLocalizado)
      ? kpis.valorPagoNaoLocalizado
      : undefined;
  const percentualNaoLocalizado = kpis.percentualNaoLocalizado ?? 0;

  const valorAlocadoExibido =
    valorAlocadoTerritorial !== undefined ? valorAlocadoTerritorial : kpis.valorTotal;

  const mandatoLabel =
    mandato && mandato !== "todos"
      ? `Mandato ${mandato.replace("-", "–")}`
      : "Todos os mandatos (2021–2028)";

  const dataAtualizacao = generatedAt ? formatDate(generatedAt) : null;

  return (
    <header
      data-testid="header-comparativo"
      className="bg-slate-900 text-white shadow-sm border-b border-slate-800 shrink-0"
    >
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-2.5">
        {/* Linha 1: Título, indicação de acumulados, data de atualização e fontes */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-1.5 pb-2 border-b border-slate-800">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
            <h1 className="text-base sm:text-lg font-bold tracking-tight text-white">
              Mapa das Obras e do Dinheiro por Bairro
            </h1>
            <span
              data-testid="header-subtitulo"
              className="text-xs text-slate-300"
            >
              Salvador • {mandatoLabel}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
            <span
              data-testid="header-valores-acumulados"
              className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-medium text-emerald-300"
            >
              {mandato && mandato !== "todos"
                ? "Valores acumulados dos contratos (não exclusivos do mandato)"
                : "Valores acumulados no acervo"}
            </span>
            {dataAtualizacao && (
              <span
                data-testid="header-atualizacao"
                className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700"
              >
                Atualizado em {dataAtualizacao}
              </span>
            )}
            <span className="hidden xl:inline text-slate-400">
              Fontes: Portal da Transparência • GeoSalvador • IBGE Censo 2022
            </span>
          </div>
        </div>

        {/* Linha 2: Resumo comparativo municipal compacto (invariante à seleção de território) */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 pt-2">
          {/* 1. Quantidade de territórios comparados */}
          <div className="bg-slate-800/90 rounded-lg px-3 py-2 border border-slate-700/80 flex flex-col justify-between">
            <span className="text-[11px] font-medium text-slate-400">
              Territórios na comparação
            </span>
            <div className="mt-0.5 flex items-baseline gap-1.5">
              <span
                data-testid="kpi-territorios-comparados"
                className="text-sm sm:text-base font-bold text-white tabular-nums"
              >
                {formatNumber(territorioCount)}{" "}
                {activeLayer === "prefeituras" ? "Prefeituras-Bairro" : "Bairros Oficiais"}
              </span>
            </div>
          </div>

          {/* 2. Valor territorialmente alocado da métrica ativa */}
          <div className="bg-slate-800/90 rounded-lg px-3 py-2 border border-slate-700/80 flex flex-col justify-between">
            <span className="text-[11px] font-medium text-slate-400">
              {metricLabel} alocado nos territórios
            </span>
            <div className="mt-0.5 flex flex-wrap items-baseline gap-x-2">
              {valorAlocadoDisponivel ? (
                <MonetaryValue
                  value={valorAlocadoExibido}
                  compact
                  tone="dark"
                  testId="kpi-valor-alocado"
                  className="text-sm sm:text-base font-extrabold text-emerald-400"
                />
              ) : (
                <span
                  data-testid="kpi-valor-alocado"
                  className="text-xs font-semibold text-amber-300"
                >
                  Pagamento indisponível
                </span>
              )}
              {totalObrasAlocadas !== undefined && (
                <span className="text-[11px] text-slate-400">
                  {activeLayer === "bairros" && isExactLayerWorkCount
                    ? `(${formatNumber(totalObrasAlocadas)} obras em bairros${
                        contratosPrefeituraBairroSemRateioCount > 0
                          ? ` • ${formatNumber(contratosPrefeituraBairroSemRateioCount)} de Prefeitura-Bairro sem rateio`
                          : ""
                      })`
                    : `(${formatNumber(totalObrasAlocadas)} obras localizadas)`}
                </span>
              )}
            </div>
          </div>

          {/* 3. Aviso sobre recursos sem localização (Escopo Cidade) */}
          <div
            data-testid="kpi-transparencia-opaca"
            className="bg-slate-800/90 rounded-lg px-3 py-2 border border-purple-500/30 flex flex-col justify-between"
          >
            <span className="text-[11px] font-medium text-purple-300">
              Sem localização • {metricLabel} (Escopo Cidade)
            </span>
            <div className="mt-0.5 flex flex-wrap items-baseline gap-x-2">
              {valorNaoLocalizado !== undefined ? (
                <MonetaryValue
                  value={valorNaoLocalizado}
                  compact
                  tone="dark"
                  testId="kpi-valor-nao-localizado"
                  className="text-sm sm:text-base font-extrabold text-purple-300"
                />
              ) : (
                <span
                  data-testid="kpi-valor-nao-localizado"
                  className="text-xs font-semibold text-amber-300"
                >
                  Pagamento indisponível
                </span>
              )}
              <span className="text-[11px] text-purple-200/90">
                {formatNumber(totalNaoLocalizado)} contratos ({percentualNaoLocalizado.toFixed(1).replace(".", ",")}%)
              </span>
            </div>
          </div>

          {/* 4. Referência municipal por habitante (escopo toda a cidade) */}
          <div className="bg-slate-800/90 rounded-lg px-3 py-2 border border-slate-700/80 flex flex-col justify-between">
            <span className="text-[11px] font-medium text-slate-400">
              Média alocada na cidade (Censo 2022)
            </span>
            <div className="mt-0.5 flex flex-wrap items-baseline gap-x-2">
              {valorAlocadoDisponivel ? (
                <span
                  data-testid="kpi-investimento-per-capita"
                  className="text-sm sm:text-base font-bold text-sky-300 tabular-nums"
                >
                  {formatCurrency(kpis.investimentoPorHabitanteCidade)} / hab
                </span>
              ) : (
                <span
                  data-testid="kpi-investimento-per-capita"
                  className="text-xs font-semibold text-amber-300"
                >
                  Pagamento indisponível
                </span>
              )}
              <span className="text-[11px] text-slate-400">{metricLabel} • Escopo municipal</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

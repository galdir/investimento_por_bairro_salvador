import React from "react";
import { GlobalKpis, MetricType } from "../types";
import { formatCurrency, formatNumber } from "../utils/formatters";

interface HeaderKpisProps {
  /**
   * Indicadores financeiros e quantitativos consolidados de Salvador.
   */
  kpis: GlobalKpis;
  /**
   * Ano de referência dos dados exibidos (ex: 2025).
   */
  ano: number;
  /**
   * Métrica financeira ativa: 'vigente' (Valor Contratual Vigente) ou 'executado' (Valor Executado/Pago).
   */
  metricType?: MetricType;
}

/**
 * Componente de cabeçalho com os 5 KPIs Superiores do Painel de Obras de Salvador.
 *
 * @summary Exibe os cartões superiores dinâmicos de auditoria social e execução orçamentária.
 * @description Apresenta em 5 blocos responsivos as métricas fundamentais de controle:
 * 1. Total Investido (recalculado conforme a métrica financeira ativa);
 * 2. Obras Ativas em relação ao total de contratos;
 * 3. Obras Críticas e Atrasadas (classificadas no Semáforo Vermelho);
 * 4. Aditivos de Preço (total financeiro em R$ e variação percentual média);
 * 5. Investimento Médio por Habitante de Salvador (base populacional Censo 2022).
 *
 * @param props - Propriedades contendo o objeto de KPIs, o ano de referência e a métrica ativa.
 * @returns Elemento JSX com a grade de cartões de indicadores.
 * @throws Não lança exceções.
 */
export const HeaderKpis: React.FC<HeaderKpisProps> = ({ kpis, ano, metricType = "vigente" }) => {
  const isVigente = metricType === "vigente";
  const totalCriticas = kpis.totalCriticas ?? 0;
  const percentualCriticas = kpis.percentualCriticas ?? 0;
  const totalAditivos = kpis.totalAditivosValor ?? 0;
  const percentualMedioAditivos = kpis.percentualMedioAditivos ?? 0;

  return (
    <header className="bg-slate-900 text-white shadow-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        {/* Título e Subtítulo Institucional */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between pb-3 border-b border-slate-800">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <span className="inline-block w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></span>
              Mapa das Obras e do Dinheiro por Bairro
            </h1>
            <p className="text-sm text-slate-400 mt-0.5">
              Controle social da execução orçamentária no território de Salvador • Exercício {ano}
            </p>
          </div>
          <div className="mt-3 md:mt-0 flex items-center gap-2 text-xs text-slate-400 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
            <span>Fontes: Portal da Transparência • GeoSalvador • IBGE Censo 2022</span>
          </div>
        </div>

        {/* Grade com os 5 KPIs Superiores do Painel */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 mt-4">
          {/* Card 1: Total Investido em Obras */}
          <div className="bg-slate-800/90 rounded-xl p-3.5 border border-slate-700/80 shadow-sm flex flex-col justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
              Total Investido em Obras
            </span>
            <div className="mt-1.5">
              <span
                data-testid="kpi-total-investido"
                className="text-xl sm:text-2xl font-extrabold text-white tracking-tight"
              >
                {formatCurrency(kpis.valorTotal)}
              </span>
              <p className="text-[11px] text-emerald-400 mt-0.5">
                {isVigente ? "Valor Contratual Vigente" : "Valor Executado / Pago"}
              </p>
            </div>
          </div>

          {/* Card 2: Obras Ativas / Totais */}
          <div className="bg-slate-800/90 rounded-xl p-3.5 border border-slate-700/80 shadow-sm flex flex-col justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
              Obras Ativas / Totais
            </span>
            <div className="mt-1.5">
              <span
                data-testid="kpi-obras-ativas"
                className="text-xl sm:text-2xl font-extrabold text-sky-400 tracking-tight"
              >
                {formatNumber(kpis.totalAtivas)} / {formatNumber(kpis.totalObras)}
              </span>
              <p className="text-[11px] text-slate-400 mt-0.5">Contratos vigentes no exercício</p>
            </div>
          </div>

          {/* Card 3: Obras Críticas / Atrasadas */}
          <div className="bg-slate-800/90 rounded-xl p-3.5 border border-slate-700/80 shadow-sm flex flex-col justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-rose-400 flex items-center justify-between">
              <span>Obras Críticas / Atrasadas</span>
              <span className="w-2 h-2 rounded-full bg-rose-500"></span>
            </span>
            <div className="mt-1.5">
              <div className="flex items-baseline gap-1.5">
                <span
                  data-testid="kpi-obras-criticas"
                  className="text-xl sm:text-2xl font-extrabold text-rose-400 tracking-tight"
                >
                  {formatNumber(totalCriticas)}
                </span>
                <span className="text-xs font-semibold text-rose-300">
                  ({percentualCriticas.toFixed(1).replace(".", ",")}%)
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">Semáforo Vermelho (Risco Alto)</p>
            </div>
          </div>

          {/* Card 4: Aditivos de Preço */}
          <div className="bg-slate-800/90 rounded-xl p-3.5 border border-slate-700/80 shadow-sm flex flex-col justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-amber-400">
              Aditivos de Preço
            </span>
            <div className="mt-1.5">
              <span
                data-testid="kpi-aditivos-preco"
                className="text-xl sm:text-2xl font-extrabold text-amber-300 tracking-tight"
              >
                {formatCurrency(totalAditivos)}
              </span>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Acréscimo médio de {percentualMedioAditivos.toFixed(1).replace(".", ",")}%
              </p>
            </div>
          </div>

          {/* Card 5: Investimento Médio por Habitante */}
          <div className="bg-slate-800/90 rounded-xl p-3.5 border border-slate-700/80 shadow-sm flex flex-col justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
              Investimento por Habitante
            </span>
            <div className="mt-1.5">
              <span
                data-testid="kpi-investimento-per-capita"
                className="text-xl sm:text-2xl font-extrabold text-emerald-400 tracking-tight"
              >
                {formatCurrency(kpis.investimentoPorHabitanteCidade)}
              </span>
              <p className="text-[11px] text-slate-400 mt-0.5">Média municipal (Censo 2022)</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

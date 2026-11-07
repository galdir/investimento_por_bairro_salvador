import React from "react";
import { GlobalKpis } from "../types";
import { formatCurrency, formatNumber } from "../utils/formatters";

interface HeaderKpisProps {
  /**
   * Indicadores financeiros e quantitativos globais consolidados de Salvador.
   */
  kpis: GlobalKpis;
  /**
   * Ano de referência dos dados exibidos (ex: 2025).
   */
  ano: number;
}

/**
 * Componente de cabeçalho com os KPIs Globais de Obras Públicas de Salvador.
 *
 * @summary Exibe os cartões superiores de controle financeiro e execução orçamentária.
 * @description Apresenta em destaque o Total Investido em Obras, a proporção de Obras Ativas
 * em relação ao total contratado, e o Investimento Médio por Habitante da capital baiana
 * (calculado a partir da soma do Censo 2022). Em um bloco secundário, exibe o Funil de
 * Execução Financeira resumido: Empenhado, Liquidado e Pago.
 *
 * @param props - Propriedades contendo o objeto de KPIs e o ano de referência.
 * @returns Elemento JSX com os blocos de métricas e títulos institucionais.
 * @throws Não lança exceções.
 */
export const HeaderKpis: React.FC<HeaderKpisProps> = ({ kpis, ano }) => {
  return (
    <header className="bg-slate-900 text-white shadow-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
        {/* Título e Subtítulo Institucional */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between pb-4 border-b border-slate-800">
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

        {/* Grade de Cartões de KPIs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-5">
          {/* Card 1: Total Investido em Obras */}
          <div className="bg-slate-800/90 rounded-xl p-4 border border-slate-700/80 shadow-sm flex flex-col justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
              Total Investido em Obras
            </span>
            <div className="mt-2">
              <span
                data-testid="kpi-total-investido"
                className="text-2xl font-extrabold text-white tracking-tight"
              >
                {formatCurrency(kpis.valorTotal)}
              </span>
              <p className="text-xs text-emerald-400 mt-1">Valor Contratual Vigente global</p>
            </div>
          </div>

          {/* Card 2: Obras Ativas / Totais */}
          <div className="bg-slate-800/90 rounded-xl p-4 border border-slate-700/80 shadow-sm flex flex-col justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
              Obras Ativas / Totais
            </span>
            <div className="mt-2">
              <span
                data-testid="kpi-obras-ativas"
                className="text-2xl font-extrabold text-sky-400 tracking-tight"
              >
                {formatNumber(kpis.totalAtivas)} / {formatNumber(kpis.totalObras)}
              </span>
              <p className="text-xs text-slate-400 mt-1">Contratos vigentes no exercício</p>
            </div>
          </div>

          {/* Card 3: Investimento Médio por Habitante */}
          <div className="bg-slate-800/90 rounded-xl p-4 border border-slate-700/80 shadow-sm flex flex-col justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
              Investimento por Habitante (Média Salvador)
            </span>
            <div className="mt-2">
              <span
                data-testid="kpi-investimento-per-capita"
                className="text-2xl font-extrabold text-amber-400 tracking-tight"
              >
                {formatCurrency(kpis.investimentoPorHabitanteCidade)}
              </span>
              <p className="text-xs text-slate-400 mt-1">Por morador residente (Censo 2022)</p>
            </div>
          </div>

          {/* Card 4: Funil de Execução Financeira */}
          <div className="bg-slate-800/90 rounded-xl p-4 border border-slate-700/80 shadow-sm flex flex-col justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
              Funil de Execução Financeira
            </span>
            <div className="mt-2 text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-400">Empenhado:</span>
                <span className="font-semibold text-slate-200">{formatCurrency(kpis.totalEmpenhado)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Liquidado:</span>
                <span className="font-semibold text-slate-200">{formatCurrency(kpis.totalLiquidado)}</span>
              </div>
              <div className="flex justify-between border-t border-slate-700 pt-1">
                <span className="text-emerald-400 font-medium">Pago:</span>
                <span className="font-bold text-emerald-400">{formatCurrency(kpis.totalPago)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

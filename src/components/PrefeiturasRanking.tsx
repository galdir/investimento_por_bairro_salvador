import React, { useMemo, useState } from "react";
import { BairroResumo, MetricType, PrefeituraBairroResumo } from "../types";
import { formatCurrency, formatDecimal, formatNumber } from "../utils/formatters";

interface PrefeiturasRankingProps {
  prefeituras: PrefeituraBairroResumo[];
  bairros?: BairroResumo[];
  metricType: MetricType;
  selectedNome?: string;
  onSelectPrefeitura: (pb: PrefeituraBairroResumo) => void;
  onSelectBairro?: (b: BairroResumo) => void;
}

/**
 * Componente de Ranking Territorial de Salvador (Prefeituras-Bairro e Bairros Oficiais).
 *
 * @summary Exibe a distribuição de recursos públicos em barras horizontais interativas por R$/hab ou Vulnerabilidade.
 * @description Apresenta as Prefeituras-Bairro ou os Bairros Oficiais ordenados de forma decrescente
 * pelo Investimento por Habitante (R$/hab) ou pelo Índice de Vulnerabilidade do Censo 2022.
 * Permite ao cidadão clicar em qualquer linha para selecionar o território correspondente no mapa e no Raio-X.
 *
 * @param props - Propriedades contendo listas territoriais, métrica ativa e callbacks de seleção.
 * @returns Elemento JSX com o ranking territorial horizontal.
 */
export const PrefeiturasRanking: React.FC<PrefeiturasRankingProps> = ({
  prefeituras,
  bairros = [],
  metricType,
  selectedNome,
  onSelectPrefeitura,
  onSelectBairro,
}) => {
  const [rankingLevel, setRankingLevel] = useState<"prefeituras" | "bairros">("prefeituras");
  const [rankingCriteria, setRankingCriteria] = useState<"investimento" | "vulnerabilidade">("investimento");

  // Ordenação de Prefeituras-Bairro
  const sortedPrefeituras = useMemo(() => {
    return [...prefeituras].sort((a, b) => {
      const valA =
        metricType === "vigente"
          ? (a.investimentoPorHabitante ?? 0)
          : (a.investimentoPorHabitantePago ?? a.investimentoPorHabitante ?? 0);
      const valB =
        metricType === "vigente"
          ? (b.investimentoPorHabitante ?? 0)
          : (b.investimentoPorHabitantePago ?? b.investimentoPorHabitante ?? 0);
      return valB - valA;
    });
  }, [prefeituras, metricType]);

  // Ordenação de Bairros Oficiais (excluindo zonas especiais para ranking per capita)
  const sortedBairros = useMemo(() => {
    const filtrados = bairros.filter(
      (b) => !b.is_zona_especial_nao_residencial && !b.isZonaEspecialNaoResidencial
    );

    return [...filtrados].sort((a, b) => {
      if (rankingCriteria === "vulnerabilidade") {
        return (b.indice_vulnerabilidade ?? 0) - (a.indice_vulnerabilidade ?? 0);
      }
      const valA =
        metricType === "vigente"
          ? (a.investimentoPorHabitante ?? 0)
          : (a.investimentoPorHabitantePago ?? a.investimentoPorHabitante ?? 0);
      const valB =
        metricType === "vigente"
          ? (b.investimentoPorHabitante ?? 0)
          : (b.investimentoPorHabitantePago ?? b.investimentoPorHabitante ?? 0);
      return valB - valA;
    });
  }, [bairros, metricType, rankingCriteria]);

  const maxVal = useMemo(() => {
    if (rankingLevel === "prefeituras") {
      let maxP = 0;
      for (const pb of sortedPrefeituras) {
        const v =
          metricType === "vigente"
            ? (pb.investimentoPorHabitante ?? 0)
            : (pb.investimentoPorHabitantePago ?? pb.investimentoPorHabitante ?? 0);
        if (v > maxP) maxP = v;
      }
      return maxP > 0 ? maxP : 1;
    } else {
      if (rankingCriteria === "vulnerabilidade") return 1.0;
      let maxB = 0;
      for (const b of sortedBairros) {
        const v =
          metricType === "vigente"
            ? (b.investimentoPorHabitante ?? 0)
            : (b.investimentoPorHabitantePago ?? b.investimentoPorHabitante ?? 0);
        if (v > maxB) maxB = v;
      }
      return maxB > 0 ? maxB : 1;
    }
  }, [rankingLevel, rankingCriteria, sortedPrefeituras, sortedBairros, metricType]);

  return (
    <section
      data-testid="ranking-prefeituras-container"
      aria-label="Ranking Territorial de Salvador por Justiça Per Capita"
      className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 mb-3 gap-2">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-indigo-600"></span>
            Ranking Territorial (Justiça Territorial Per Capita)
          </h3>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Compare o Investimento por Habitante (R$/hab) e o Índice de Vulnerabilidade do Censo 2022
          </p>
        </div>

        {/* Controles de Nível e Critério */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Seletor de Nível */}
          <div className="flex bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-semibold">
            <button
              type="button"
              data-testid="btn-ranking-prefeituras"
              onClick={() => setRankingLevel("prefeituras")}
              className={`px-2 py-1 rounded-md transition-all ${
                rankingLevel === "prefeituras"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Prefeituras-Bairro
            </button>
            <button
              type="button"
              data-testid="btn-ranking-bairros"
              onClick={() => setRankingLevel("bairros")}
              className={`px-2 py-1 rounded-md transition-all ${
                rankingLevel === "bairros"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Bairros Oficiais
            </button>
          </div>

          {/* Seletor de Critério */}
          {rankingLevel === "bairros" && (
            <div className="flex bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-semibold">
              <button
                type="button"
                data-testid="btn-criterio-investimento"
                onClick={() => setRankingCriteria("investimento")}
                className={`px-2 py-1 rounded-md transition-all ${
                  rankingCriteria === "investimento"
                    ? "bg-emerald-600 text-white shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                R$/Hab
              </button>
              <button
                type="button"
                data-testid="btn-criterio-vulnerabilidade"
                onClick={() => setRankingCriteria("vulnerabilidade")}
                className={`px-2 py-1 rounded-md transition-all ${
                  rankingCriteria === "vulnerabilidade"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Vulnerabilidade
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Lista de Prefeituras-Bairro */}
      {rankingLevel === "prefeituras" && (
        <div className="space-y-2.5">
          {sortedPrefeituras.map((pb, index) => {
            const perCapita =
              metricType === "vigente"
                ? (pb.investimentoPorHabitante ?? 0)
                : (pb.investimentoPorHabitantePago ?? pb.investimentoPorHabitante ?? 0);
            const percentualBarra = Math.min(100, Math.max(8, (perCapita / maxVal) * 100));
            const isSelected = selectedNome === pb.nome;

            return (
              <div
                key={pb.id}
                data-testid={`ranking-item-${index + 1}`}
                onClick={() => onSelectPrefeitura(pb)}
                className={`p-2 rounded-lg cursor-pointer transition-all border ${
                  isSelected
                    ? "bg-indigo-50/80 border-indigo-400 shadow-sm"
                    : "bg-slate-50/60 border-slate-100 hover:bg-slate-100/80"
                }`}
              >
                <div className="flex items-center justify-between text-xs mb-1">
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-slate-400 w-5 text-right">
                      #{index + 1}
                    </span>
                    <span className="font-bold text-slate-800 hover:text-indigo-600 transition-colors">
                      {pb.nome}
                    </span>
                  </div>
                  <div className="text-right">
                    <span
                      data-testid={`ranking-valor-${index + 1}`}
                      className="font-extrabold text-slate-900 text-xs sm:text-sm"
                    >
                      {formatCurrency(perCapita)}
                    </span>
                    <span className="text-[10px] text-slate-500 ml-1">/ hab</span>
                  </div>
                </div>

                <div className="w-full bg-slate-200/80 h-2 rounded-full overflow-hidden flex">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      isSelected ? "bg-indigo-600" : "bg-indigo-500"
                    }`}
                    style={{ width: `${percentualBarra}%` }}
                  ></div>
                </div>

                <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                  <span>{formatNumber(pb.populacao_total)} habitantes</span>
                  <span>
                    Total: {formatCurrency(pb.valorTotal ?? 0)} • {pb.totalObras ?? 0} obras
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Lista de Bairros Oficiais */}
      {rankingLevel === "bairros" && (
        <div className="space-y-2.5 max-h-[500px] overflow-y-auto pr-1">
          {sortedBairros.map((b, index) => {
            const perCapita =
              metricType === "vigente"
                ? (b.investimentoPorHabitante ?? 0)
                : (b.investimentoPorHabitantePago ?? b.investimentoPorHabitante ?? 0);
            const valExibido =
              rankingCriteria === "vulnerabilidade"
                ? formatDecimal(b.indice_vulnerabilidade ?? 0)
                : `${formatCurrency(perCapita)} / hab`;
            const percentualBarra =
              rankingCriteria === "vulnerabilidade"
                ? Math.min(100, Math.max(5, (b.indice_vulnerabilidade ?? 0) * 100))
                : Math.min(100, Math.max(5, (perCapita / maxVal) * 100));
            const isSelected = selectedNome === b.nome;

            return (
              <div
                key={b.id}
                data-testid={`ranking-bairro-${index + 1}`}
                onClick={() => onSelectBairro && onSelectBairro(b)}
                className={`p-2 rounded-lg cursor-pointer transition-all border ${
                  isSelected
                    ? "bg-emerald-50/80 border-emerald-400 shadow-sm"
                    : "bg-slate-50/60 border-slate-100 hover:bg-slate-100/80"
                }`}
              >
                <div className="flex items-center justify-between text-xs mb-1">
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-slate-400 w-5 text-right">
                      #{index + 1}
                    </span>
                    <span className="font-bold text-slate-800 hover:text-emerald-600 transition-colors">
                      {b.nome}
                    </span>
                    <span className="text-[10px] text-slate-400">({b.prefeitura_bairro})</span>
                  </div>
                  <div className="text-right">
                    <span className="font-extrabold text-slate-900 text-xs">
                      {valExibido}
                    </span>
                  </div>
                </div>

                <div className="w-full bg-slate-200/80 h-2 rounded-full overflow-hidden flex">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      rankingCriteria === "vulnerabilidade" ? "bg-indigo-600" : "bg-emerald-500"
                    }`}
                    style={{ width: `${percentualBarra}%` }}
                  ></div>
                </div>

                <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                  <span>{formatNumber(b.populacao)} habitantes</span>
                  <span>
                    Total: {formatCurrency(b.valorTotal ?? 0)} • {b.totalObras ?? 0} obras
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};

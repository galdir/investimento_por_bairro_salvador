import React, { useMemo, useState } from "react";
import { BairroResumo, MetricType, PrefeituraBairroResumo } from "../types";
import { formatCurrency, formatDecimal, formatNumber } from "../utils/formatters";

export type RankingLevel = "prefeituras" | "bairros";
export type RankingCriteria = "investimento" | "valorTotal" | "totalObras" | "vulnerabilidade";
export type RankingDirection = "desc" | "asc";

export interface PrefeiturasRankingProps {
  prefeituras: PrefeituraBairroResumo[];
  bairros?: BairroResumo[];
  metricType: MetricType;
  selectedNome?: string;
  activeLevel?: RankingLevel;
  onLevelChange?: (level: RankingLevel) => void;
  onSelectPrefeitura: (pb: PrefeituraBairroResumo) => void;
  onSelectBairro?: (b: BairroResumo) => void;
}

const isSpecialZone = (b: BairroResumo): boolean => {
  return Boolean(b.is_zona_especial_nao_residencial || b.isZonaEspecialNaoResidencial);
};

const getTerritoryMetric = (
  item: PrefeituraBairroResumo | BairroResumo,
  criterion: RankingCriteria,
  metric: MetricType
): number => {
  switch (criterion) {
    case "investimento":
      return metric === "vigente"
        ? (item.investimentoPorHabitante ?? 0)
        : (item.investimentoPorHabitantePago ?? 0);
    case "valorTotal":
      return metric === "vigente"
        ? (item.valorTotal ?? 0)
        : (item.valorPago ?? 0);
    case "totalObras":
      return item.totalObras ?? 0;
    case "vulnerabilidade":
      return item.indice_vulnerabilidade ?? 0;
  }
};

const sortTerritories = <T extends PrefeituraBairroResumo | BairroResumo>(
  items: T[],
  criterion: RankingCriteria,
  direction: RankingDirection,
  metric: MetricType
): T[] => {
  return [...items].sort((a, b) => {
    const valA = getTerritoryMetric(a, criterion, metric);
    const valB = getTerritoryMetric(b, criterion, metric);
    const vulnA = a.indice_vulnerabilidade ?? 0;
    const vulnB = b.indice_vulnerabilidade ?? 0;

    if (direction === "desc") {
      if (valB !== valA) return valB - valA;
      if (vulnB !== vulnA) return vulnB - vulnA;
      return a.nome.localeCompare(b.nome);
    } else {
      if (valA !== valB) return valA - valB;
      // na ordenação crescente por investimento ou número de obras, empates são desempatados pelo maior Índice de Vulnerabilidade do Bairro primeiro
      if (criterion !== "vulnerabilidade" && vulnB !== vulnA) {
        return vulnB - vulnA;
      }
      return a.nome.localeCompare(b.nome);
    }
  });
};

const formatCardPrimaryValue = (
  item: PrefeituraBairroResumo | BairroResumo,
  criterion: RankingCriteria,
  metric: MetricType,
  isSpecial: boolean = false
): { text: string; unit?: string } => {
  switch (criterion) {
    case "vulnerabilidade":
      return { text: isSpecial ? "Isento" : formatDecimal(item.indice_vulnerabilidade ?? 0) };
    case "valorTotal": {
      const val = metric === "vigente" ? (item.valorTotal ?? 0) : (item.valorPago ?? 0);
      return { text: formatCurrency(val) };
    }
    case "totalObras": {
      const obras = item.totalObras ?? 0;
      return { text: `${obras} ${obras === 1 ? "obra" : "obras"}` };
    }
    case "investimento": {
      if (isSpecial) {
        return { text: "Isento per capita" };
      }
      const val =
        metric === "vigente"
          ? (item.investimentoPorHabitante ?? 0)
          : (item.investimentoPorHabitantePago ?? 0);
      return { text: formatCurrency(val), unit: "/ hab" };
    }
  }
};

/**
 * Componente de Ranking Territorial de Salvador (Prefeituras-Bairro e Bairros Oficiais).
 *
 * @summary Exibe a distribuição de recursos públicos em barras horizontais interativas com 4 critérios e direção simétrica.
 * @description Apresenta as Prefeituras-Bairro ou os Bairros Oficiais ordenados de forma crescente ou decrescente
 * por R$/Hab, Valor Total, Nº de Obras ou Índice de Vulnerabilidade do Censo 2022.
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
  activeLevel,
  onLevelChange,
  onSelectPrefeitura,
  onSelectBairro,
}) => {
  const [internalLevel, setInternalLevel] = useState<RankingLevel>("bairros");
  const rankingLevel = activeLevel ?? internalLevel;

  const handleLevelChange = (newLevel: RankingLevel) => {
    if (onLevelChange) {
      onLevelChange(newLevel);
    }
    setInternalLevel(newLevel);
  };

  const [rankingCriteria, setRankingCriteria] = useState<RankingCriteria>("investimento");
  const [rankingDirection, setRankingDirection] = useState<RankingDirection>("desc");

  // Ordenação de Prefeituras-Bairro
  const sortedPrefeituras = useMemo(() => {
    return sortTerritories(prefeituras, rankingCriteria, rankingDirection, metricType);
  }, [prefeituras, metricType, rankingCriteria, rankingDirection]);

  // Ordenação de Bairros Oficiais (excluindo zonas especiais para ranking de bairros residenciais)
  const sortedBairros = useMemo(() => {
    const filtrados = bairros.filter((b) => !isSpecialZone(b));
    return sortTerritories(filtrados, rankingCriteria, rankingDirection, metricType);
  }, [bairros, metricType, rankingCriteria, rankingDirection]);

  const maxVal = useMemo(() => {
    if (rankingCriteria === "vulnerabilidade") return 1.0;
    const list = rankingLevel === "prefeituras" ? sortedPrefeituras : sortedBairros;
    let max = 0;
    for (const item of list) {
      const v = getTerritoryMetric(item, rankingCriteria, metricType);
      if (v > max) max = v;
    }
    return max > 0 ? max : 1;
  }, [rankingLevel, rankingCriteria, sortedPrefeituras, sortedBairros, metricType]);

  return (
    <section
      data-testid="ranking-prefeituras-container"
      aria-label="Ranking Territorial de Salvador por Justiça Per Capita"
      className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm"
    >
      <div className="flex flex-col lg:flex-row lg:items-center justify-between pb-3 border-b border-slate-100 mb-3 gap-3">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-indigo-600"></span>
            Ranking Territorial (Justiça Territorial Per Capita)
          </h3>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Compare o Investimento por Habitante (R$/hab), Valor Total, Obras e Índice de Vulnerabilidade
          </p>
        </div>

        {/* Controles de Nível, Critério e Direção */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Seletor de Nível */}
          <div className="flex bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-semibold">
            <button
              type="button"
              data-testid="btn-ranking-prefeituras"
              onClick={() => handleLevelChange("prefeituras")}
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
              onClick={() => handleLevelChange("bairros")}
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
              data-testid="btn-criterio-valortotal"
              onClick={() => setRankingCriteria("valorTotal")}
              className={`px-2 py-1 rounded-md transition-all ${
                rankingCriteria === "valorTotal"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Valor Total
            </button>
            <button
              type="button"
              data-testid="btn-criterio-totalobras"
              onClick={() => setRankingCriteria("totalObras")}
              className={`px-2 py-1 rounded-md transition-all ${
                rankingCriteria === "totalObras"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Nº de Obras
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

          {/* Seletor de Direção */}
          <div className="flex bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-semibold">
            <button
              type="button"
              data-testid="btn-direcao-desc"
              onClick={() => setRankingDirection("desc")}
              className={`px-2 py-1 rounded-md transition-all ${
                rankingDirection === "desc"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Maiores primeiro (↓)
            </button>
            <button
              type="button"
              data-testid="btn-direcao-asc"
              onClick={() => setRankingDirection("asc")}
              className={`px-2 py-1 rounded-md transition-all ${
                rankingDirection === "asc"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Menores / Desassistidos primeiro (↑)
            </button>
          </div>
        </div>
      </div>

      {/* Lista de Prefeituras-Bairro */}
      {rankingLevel === "prefeituras" && (
        <div className="space-y-2.5">
          {sortedPrefeituras.map((pb, index) => {
            const perCapita =
              metricType === "vigente"
                ? (pb.investimentoPorHabitante ?? 0)
                : (pb.investimentoPorHabitantePago ?? 0);
            const valorTotalExibido =
              metricType === "vigente"
                ? (pb.valorTotal ?? 0)
                : (pb.valorPago ?? 0);
            const vuln = pb.indice_vulnerabilidade ?? 0;
            const primaryVal = getTerritoryMetric(pb, rankingCriteria, metricType);
            const primaryFormatted = formatCardPrimaryValue(pb, rankingCriteria, metricType);
            const percentualBarra =
              rankingCriteria === "vulnerabilidade"
                ? Math.min(100, Math.max(8, vuln * 100))
                : Math.min(100, Math.max(8, (primaryVal / maxVal) * 100));
            const isSelected = selectedNome === pb.nome;

            return (
              <div
                key={pb.id}
                data-testid={`ranking-item-${index + 1}`}
                onClick={() => onSelectPrefeitura(pb)}
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
                      {pb.nome}
                    </span>
                  </div>
                  <div className="text-right">
                    <span
                      data-testid={`ranking-valor-${index + 1}`}
                      className="font-extrabold text-slate-900 text-xs sm:text-sm"
                    >
                      {primaryFormatted.text}
                    </span>
                    {primaryFormatted.unit && (
                      <span className="text-[10px] text-slate-500 ml-1">
                        {primaryFormatted.unit}
                      </span>
                    )}
                  </div>
                </div>

                <div className="w-full bg-slate-200/80 h-2 rounded-full overflow-hidden flex">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      rankingCriteria === "vulnerabilidade"
                        ? isSelected
                          ? "bg-indigo-600"
                          : "bg-indigo-500"
                        : isSelected
                        ? "bg-emerald-600"
                        : "bg-emerald-500"
                    }`}
                    style={{ width: `${percentualBarra}%` }}
                  ></div>
                </div>

                <div className="flex flex-wrap items-center justify-between text-[10px] text-slate-500 mt-1 gap-1">
                  <span>
                    {formatNumber(pb.populacao_total)} habitantes • Total: {formatCurrency(valorTotalExibido)} • {pb.totalObras ?? 0} {(pb.totalObras ?? 0) === 1 ? "obra" : "obras"}
                  </span>
                  <span>
                    {formatCurrency(perCapita)} / hab • Vulnerabilidade: {formatDecimal(vuln)}
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
            const isSpecial = isSpecialZone(b);
            const perCapita =
              metricType === "vigente"
                ? (b.investimentoPorHabitante ?? 0)
                : (b.investimentoPorHabitantePago ?? 0);
            const valorTotalExibido =
              metricType === "vigente"
                ? (b.valorTotal ?? 0)
                : (b.valorPago ?? 0);
            const vuln = b.indice_vulnerabilidade ?? 0;
            const primaryVal = getTerritoryMetric(b, rankingCriteria, metricType);
            const primaryFormatted = formatCardPrimaryValue(b, rankingCriteria, metricType, isSpecial);
            const percentualBarra =
              rankingCriteria === "vulnerabilidade"
                ? Math.min(100, Math.max(5, vuln * 100))
                : Math.min(100, Math.max(5, (primaryVal / maxVal) * 100));
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
                    {isSpecial && (
                      <span className="text-[10px] bg-amber-100 text-amber-800 font-semibold px-1.5 py-0.2 rounded">
                        Zona Especial
                      </span>
                    )}
                    <span className="text-[10px] text-slate-400">({b.prefeitura_bairro})</span>
                  </div>
                  <div className="text-right">
                    <span
                      data-testid={`ranking-bairro-valor-${index + 1}`}
                      className="font-extrabold text-slate-900 text-xs"
                    >
                      {primaryFormatted.text}
                    </span>
                    {primaryFormatted.unit && (
                      <span className="text-[10px] text-slate-500 ml-1">
                        {primaryFormatted.unit}
                      </span>
                    )}
                  </div>
                </div>

                <div className="w-full bg-slate-200/80 h-2 rounded-full overflow-hidden flex">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      rankingCriteria === "vulnerabilidade"
                        ? isSelected
                          ? "bg-indigo-600"
                          : "bg-indigo-500"
                        : isSelected
                        ? "bg-emerald-600"
                        : "bg-emerald-500"
                    }`}
                    style={{ width: `${percentualBarra}%` }}
                  ></div>
                </div>

                <div className="flex flex-wrap items-center justify-between text-[10px] text-slate-500 mt-1 gap-1">
                  <span>
                    {formatNumber(b.populacao)} habitantes • Total: {formatCurrency(valorTotalExibido)} • {b.totalObras ?? 0} {(b.totalObras ?? 0) === 1 ? "obra" : "obras"}
                  </span>
                  <span>
                    {isSpecial ? "Isento per capita" : `${formatCurrency(perCapita)} / hab`} • Vulnerabilidade: {isSpecial ? "Isento" : formatDecimal(vuln)}
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

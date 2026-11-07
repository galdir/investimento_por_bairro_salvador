import React, { useMemo, useState } from "react";
import { BairroResumo, MetricType, ObraCompacta, PrefeituraBairroResumo } from "../types";
import { formatCurrency, formatDecimal, formatNumber } from "../utils/formatters";
import { isZonaEspecial, normalizeName } from "../utils/territory";

export type RankingLevel = "prefeituras" | "bairros";
export type RankingCriteria = "investimento" | "valorTotal" | "totalObras" | "vulnerabilidade";
export type RankingDirection = "desc" | "asc";

export interface PrefeiturasRankingProps {
  prefeituras: PrefeituraBairroResumo[];
  bairros?: BairroResumo[];
  obras?: ObraCompacta[];
  metricType: MetricType;
  selectedNome?: string;
  activeLevel?: RankingLevel;
  onLevelChange?: (level: RankingLevel) => void;
  onSelectPrefeitura: (pb: PrefeituraBairroResumo) => void;
  onSelectBairro?: (b: BairroResumo) => void;
}

// Helper para filtrar itens pelo nome insensível a acentuação e caixa
function filterByName<T extends { nome: string }>(items: T[], term: string): T[] {
  if (!term.trim()) return items;
  const termoNorm = normalizeName(term);
  return items.filter((item) => normalizeName(item.nome).includes(termoNorm));
}

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
 * Permite ao cidadão buscar bairros por nome, filtrar por Prefeitura-Bairro, visualizar obras regionais e auditar Zonas Especiais.
 *
 * @param props - Propriedades contendo listas territoriais, obras, métrica ativa e callbacks de seleção.
 * @returns Elemento JSX com o ranking territorial horizontal.
 */
export const PrefeiturasRanking: React.FC<PrefeiturasRankingProps> = ({
  prefeituras,
  bairros = [],
  obras = [],
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
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [filtroPrefeitura, setFiltroPrefeitura] = useState<string>("todas");

  // Lista de Prefeituras-Bairro disponíveis para o seletor de filtro
  const prefeiturasDisponiveis = useMemo(() => {
    const nomes = new Set<string>();
    for (const pb of prefeituras) {
      if (pb.nome) nomes.add(pb.nome);
    }
    for (const b of bairros) {
      if (b.prefeitura_bairro) nomes.add(b.prefeitura_bairro);
    }
    return Array.from(nomes).sort((a, b) => a.localeCompare(b));
  }, [prefeituras, bairros]);

  // Contratos de nível Regional (Prefeitura-Bairro)
  const regionalObras = useMemo(() => {
    return (obras || []).filter((o) => {
      if (o.nivel !== "Regional (Prefeitura-Bairro)") return false;
      if (filtroPrefeitura !== "todas") {
        const pbObra = o.prefeituraBairro || o.prefeitura_bairro;
        return normalizeName(pbObra) === normalizeName(filtroPrefeitura);
      }
      return true;
    });
  }, [obras, filtroPrefeitura]);

  const regionalObrasCount = regionalObras.length;
  const valorRegionalTotal = useMemo(() => {
    return regionalObras.reduce((acc, o) => {
      const val =
        metricType === "vigente"
          ? (o.valorContratualVigente ?? 0)
          : (o.valorPago ?? 0);
      return acc + val;
    }, 0);
  }, [regionalObras, metricType]);

  // Ordenação de Prefeituras-Bairro
  const sortedPrefeituras = useMemo(() => {
    return sortTerritories(prefeituras, rankingCriteria, rankingDirection, metricType);
  }, [prefeituras, metricType, rankingCriteria, rankingDirection]);

  // Critério per capita ou vulnerabilidade: separa Zonas Especiais Não-Residenciais
  const ehCriterioPerCapitaOuVuln =
    rankingCriteria === "investimento" || rankingCriteria === "vulnerabilidade";

  // 1. Filtragem preliminar por Prefeitura-Bairro
  const bairrosFiltradosPorPrefeitura = useMemo(() => {
    if (filtroPrefeitura === "todas") return bairros;
    return bairros.filter(
      (b) => normalizeName(b.prefeitura_bairro) === normalizeName(filtroPrefeitura)
    );
  }, [bairros, filtroPrefeitura]);

  // 2. Separação condicional ou unificação de bairros para ranking
  const { bairrosParaOrdenar, zonasEspeciaisParaExibir } = useMemo(() => {
    if (ehCriterioPerCapitaOuVuln) {
      const residenciais = bairrosFiltradosPorPrefeitura.filter((b) => !isZonaEspecial(b));
      const especiais = bairrosFiltradosPorPrefeitura.filter((b) => isZonaEspecial(b));
      return {
        bairrosParaOrdenar: residenciais,
        zonasEspeciaisParaExibir: especiais,
      };
    } else {
      // Em valorTotal ou totalObras, zonas especiais participam diretamente do ranking numerado
      return {
        bairrosParaOrdenar: bairrosFiltradosPorPrefeitura,
        zonasEspeciaisParaExibir: [],
      };
    }
  }, [bairrosFiltradosPorPrefeitura, ehCriterioPerCapitaOuVuln]);

  // 3. Ordenação dos bairros e indexação de posição no ranking da visão
  const bairrosOrdenadosComPosicao = useMemo(() => {
    const sorted = sortTerritories(bairrosParaOrdenar, rankingCriteria, rankingDirection, metricType);
    return sorted.map((b, idx) => ({
      ...b,
      posicaoNoRanking: idx + 1,
    }));
  }, [bairrosParaOrdenar, rankingCriteria, rankingDirection, metricType]);

  // 4. Ordenação das zonas especiais (para quando estão na seção dedicada)
  const sortedZonasEspeciais = useMemo(() => {
    if (!ehCriterioPerCapitaOuVuln || zonasEspeciaisParaExibir.length === 0) return [];
    return [...zonasEspeciaisParaExibir].sort((a, b) => {
      const valA = metricType === "vigente" ? (a.valorTotal ?? 0) : (a.valorPago ?? 0);
      const valB = metricType === "vigente" ? (b.valorTotal ?? 0) : (b.valorPago ?? 0);
      if (valB !== valA) return valB - valA;
      return a.nome.localeCompare(b.nome);
    });
  }, [zonasEspeciaisParaExibir, ehCriterioPerCapitaOuVuln, metricType]);

  // 5. Aplicação da busca textual (filtra em tempo real sem perder a posição relativa do ranking)
  const finalBairros = useMemo(() => {
    return filterByName(bairrosOrdenadosComPosicao, searchTerm);
  }, [bairrosOrdenadosComPosicao, searchTerm]);

  const finalZonasEspeciais = useMemo(() => {
    return filterByName(sortedZonasEspeciais, searchTerm);
  }, [sortedZonasEspeciais, searchTerm]);

  const maxVal = useMemo(() => {
    if (rankingCriteria === "vulnerabilidade") return 1.0;
    const list = rankingLevel === "prefeituras" ? sortedPrefeituras : bairrosOrdenadosComPosicao;
    let max = 0;
    for (const item of list) {
      const v = getTerritoryMetric(item, rankingCriteria, metricType);
      if (v > max) max = v;
    }
    return max > 0 ? max : 1;
  }, [rankingLevel, rankingCriteria, sortedPrefeituras, bairrosOrdenadosComPosicao, metricType]);

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

      {/* Controles de Busca e Filtro por Prefeitura-Bairro dos Bairros Oficiais */}
      {rankingLevel === "bairros" && (
        <div className="space-y-3 mb-3">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            {/* Campo de busca textual por nome do bairro */}
            <div className="relative flex-1">
              <input
                type="text"
                data-testid="input-busca-bairro"
                aria-label="Buscar bairro oficial por nome"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Buscar bairro oficial..."
                className="w-full pl-8 pr-7 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:bg-white transition-all"
              />
              <svg
                className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              {searchTerm && (
                <button
                  type="button"
                  data-testid="btn-limpar-busca-bairro"
                  onClick={() => setSearchTerm("")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs px-1 font-bold"
                  aria-label="Limpar busca de bairro"
                >
                  ×
                </button>
              )}
            </div>

            {/* Seletor de Filtro por Prefeitura-Bairro */}
            <div className="sm:w-64">
              <select
                data-testid="select-filtro-prefeitura"
                aria-label="Filtrar por Prefeitura-Bairro"
                value={filtroPrefeitura}
                onChange={(e) => setFiltroPrefeitura(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:bg-white transition-all"
              >
                <option value="todas">Todas as Prefeituras-Bairro</option>
                {prefeiturasDisponiveis.map((pb) => (
                  <option key={pb} value={pb}>
                    {pb}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Banner Contextual de Obras Regionais */}
          <div
            data-testid="banner-obras-regionais"
            className="bg-indigo-50/70 border border-indigo-100 rounded-lg p-2.5 flex items-start gap-2.5 text-xs text-indigo-950"
          >
            <svg
              className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div className="flex-1">
              <div className="flex flex-wrap items-center justify-between gap-1">
                <span className="font-semibold text-indigo-900">
                  Contratos de nível Regional (Prefeitura-Bairro): {regionalObrasCount}{" "}
                  {regionalObrasCount === 1 ? "obra" : "obras"} ({formatCurrency(valorRegionalTotal)})
                </span>
                <span className="text-[10px] text-indigo-600 font-medium">
                  {filtroPrefeitura === "todas" ? "Salvador (Todas)" : filtroPrefeitura}
                </span>
              </div>
              <p className="text-[11px] text-indigo-800/80 mt-0.5 leading-snug">
                Obras públicas com alocação regional beneficiam a Prefeitura-Bairro como um todo e integram o total da
                Prefeitura-Bairro sem rateio artificial entre os bairros individuais.
              </p>
            </div>
          </div>
        </div>
      )}

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
          {finalBairros.length === 0 ? (
            <div className="p-4 text-center text-xs text-slate-500 bg-slate-50 rounded-lg border border-slate-200">
              Nenhum bairro oficial encontrado para os filtros selecionados.
            </div>
          ) : (
            finalBairros.map((b, index) => {
              const isSpecial = isZonaEspecial(b);
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
                        #{b.posicaoNoRanking}
                      </span>
                      <span className="font-bold text-slate-800 hover:text-emerald-600 transition-colors">
                        {b.nome}
                      </span>
                      {isSpecial && (
                        <span className="text-[10px] bg-amber-100 text-amber-800 font-semibold px-1.5 py-0.2 rounded">
                          Zona Especial Não-Residencial
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
            })
          )}

          {/* Seção dedicada de Zonas Especiais Não-Residenciais (quando em R$/Hab ou Vulnerabilidade) */}
          {ehCriterioPerCapitaOuVuln && finalZonasEspeciais.length > 0 && (
            <div data-testid="secao-zonas-especiais" className="mt-4 pt-3 border-t border-slate-200">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-2 gap-1">
                <h4 className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                  Zonas Especiais Não-Residenciais — isentas do cálculo per capita
                </h4>
                <span className="text-[10px] text-slate-400">
                  Áreas institucionais/logísticas com população residencial nula ou residual
                </span>
              </div>
              <div className="space-y-2">
                {finalZonasEspeciais.map((zona, idx) => {
                  const valorTotalExibido =
                    metricType === "vigente" ? (zona.valorTotal ?? 0) : (zona.valorPago ?? 0);
                  const isSelected = selectedNome === zona.nome;
                  return (
                    <div
                      key={zona.id}
                      data-testid={`ranking-zona-especial-${idx + 1}`}
                      onClick={() => onSelectBairro && onSelectBairro(zona)}
                      className={`p-2 rounded-lg cursor-pointer transition-all border ${
                        isSelected
                          ? "bg-amber-50/80 border-amber-400 shadow-sm"
                          : "bg-slate-50/60 border-slate-100 hover:bg-slate-100/80"
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs mb-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-800 hover:text-amber-700 transition-colors">
                            {zona.nome}
                          </span>
                          <span className="text-[10px] bg-amber-100 text-amber-800 font-semibold px-1.5 py-0.2 rounded">
                            Zona Especial Não-Residencial
                          </span>
                          <span className="text-[10px] text-slate-400">({zona.prefeitura_bairro})</span>
                        </div>
                        <div className="text-right">
                          <span className="font-extrabold text-slate-900 text-xs">
                            {formatCurrency(valorTotalExibido)}
                          </span>
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center justify-between text-[10px] text-slate-500 mt-1 gap-1">
                        <span>
                          Total: {formatCurrency(valorTotalExibido)} • {zona.totalObras ?? 0}{" "}
                          {(zona.totalObras ?? 0) === 1 ? "obra" : "obras"}
                        </span>
                        <span>Isento per capita • Vulnerabilidade: Isento</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
};

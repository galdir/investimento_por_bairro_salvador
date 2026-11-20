import React, { useEffect, useMemo, useRef } from "react";
import {
  BairroResumo,
  MetricType,
  PrefeituraBairroResumo,
  TerritorySelection,
} from "../types";
import { formatDecimal, formatNumber } from "../utils/formatters";
import {
  createBairroSelection,
  createPrefeituraSelection,
  getTerritoryAbsoluteTotal,
  getTerritoryInvestmentState,
  hasNumericValue,
  isCentralidadeMetropolitana,
  isZonaEspecial,
  normalizeName,
} from "../utils/territory";
import { normalizeTestId } from "./InteractiveMap";
import { MonetaryValue } from "./MonetaryValue";
import { SearchInput } from "./SearchInput";

function renderTotalSummary(
  totalTerritorial: number | undefined,
  testSlug: string,
  metricType: MetricType,
  obrasSemValorPago: number = 0,
  parcial: boolean = false
) {
  const totalPrefix = metricType === "executado" ? (parcial ? "Soma parcial:" : "Total pago:") : "Total contratual:";
  return (
    <div className="flex flex-wrap items-center justify-end gap-x-2 gap-y-1 ml-auto">
      {totalTerritorial !== undefined ? (
        <span className="tabular-nums">
          {totalPrefix}{" "}
          <MonetaryValue
            value={totalTerritorial}
            compact
            align="right"
            testId={`comparison-total-${testSlug}`}
            className="font-semibold text-slate-800"
          />
        </span>
      ) : (
        <span className="text-amber-800 font-medium">Pagamento indisponível</span>
      )}
      {obrasSemValorPago > 0 && (
        <span className="text-[10px] text-amber-800 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
          {obrasSemValorPago} obra(s) sem valor de pagamento
        </span>
      )}
    </div>
  );
}

export type VulnerabilitySortDirection = "asc" | "desc";

interface TerritoryComparisonListProps {
  activeLayer: "bairros" | "prefeituras";
  prefeituras: PrefeituraBairroResumo[];
  bairros: BairroResumo[];
  metricType: MetricType;
  sortDirection: VulnerabilitySortDirection;
  onToggleSortDirection: () => void;
  territorySearch?: string;
  onTerritorySearchChange?: (query: string) => void;
  hasEmptyContractFilter?: boolean;
  onClearContractFilters?: () => void;
  selectedTerritory: TerritorySelection | null;
  onSelectTerritory: (territorio: TerritorySelection) => void;
  onOpenNotaMetodologica?: () => void;
  isVisible?: boolean;
}

function sortByVulnerabilityAndName<
  T extends { nome: string; indice_vulnerabilidade?: number | null }
>(
  items: T[],
  direction: VulnerabilitySortDirection
): T[] {
  return [...items].sort((a, b) => {
    const vulnA = a.indice_vulnerabilidade;
    const vulnB = b.indice_vulnerabilidade;
    const hasA = hasNumericValue(vulnA);
    const hasB = hasNumericValue(vulnB);

    if (hasA && hasB && vulnA !== vulnB) {
      return direction === "asc" ? vulnA - vulnB : vulnB - vulnA;
    }
    if (hasA !== hasB) {
      return hasA ? -1 : 1;
    }
    return a.nome.localeCompare(b.nome, "pt-BR");
  });
}

interface ComparisonTerritoryRowProps {
  item: BairroResumo | PrefeituraBairroResumo;
  isPrefeitura: boolean;
  rankNumber?: number;
  metricType: MetricType;
  maxPerCapita: number;
  selectedTerritory: TerritorySelection | null;
  onSelectTerritory: (territorio: TerritorySelection) => void;
  rowRef?: (el: HTMLLIElement | null) => void;
}

const ComparisonTerritoryRow: React.FC<ComparisonTerritoryRowProps> = ({
  item,
  isPrefeitura,
  rankNumber,
  metricType,
  maxPerCapita,
  selectedTerritory,
  onSelectTerritory,
  rowRef,
}) => {
  const tipo = isPrefeitura ? "prefeitura_bairro" : "bairro";
  const normKey = normalizeName(item.nome);
  const isSelected =
    selectedTerritory !== null &&
    selectedTerritory.tipo === tipo &&
    normalizeName(selectedTerritory.nome) === normKey;

  const testSlug = normalizeTestId(item.nome);
  const invState = getTerritoryInvestmentState(item, metricType, tipo);
  const vuln = item.indice_vulnerabilidade;
  const hasVuln = hasNumericValue(vuln);
  const isContiguidade = Boolean(item.vulnerabilidade_estimada_contiguidade);
  const bairrosEstimados = isPrefeitura
    ? (item as PrefeituraBairroResumo).bairros_vulnerabilidade_estimada || []
    : [];
  const isCentralidade = !isPrefeitura && isCentralidadeMetropolitana(item as BairroResumo);

  const barWidthPct =
    invState.kind === "value" && invState.perCapita !== 0
      ? Math.max(2, Math.min(100, (Math.abs(invState.perCapita) / maxPerCapita) * 100))
      : 0;

  const populacao = isPrefeitura
    ? (item as PrefeituraBairroResumo).populacao_total
    : (item as BairroResumo).populacao;

  const totalTerritorial = getTerritoryAbsoluteTotal(item, metricType);
  const limitacoes = metricType === "executado" ? item.limitacoesConhecidas || [] : [];

  const handleSelect = () => {
    if (isPrefeitura) {
      onSelectTerritory(createPrefeituraSelection(item as PrefeituraBairroResumo));
    } else {
      onSelectTerritory(createBairroSelection(item as BairroResumo));
    }
  };

  return (
    <li
      ref={rowRef}
      data-testid={`comparison-row-${testSlug}`}
      data-index={rankNumber !== undefined ? rankNumber - 1 : undefined}
      data-selected={isSelected ? "true" : "false"}
      className={`rounded-xl border transition-all p-3 ${
        isSelected
          ? "bg-emerald-50/80 border-emerald-600 ring-2 ring-emerald-500/30 shadow-sm"
          : "bg-slate-50/70 border-slate-200 hover:bg-slate-100/80 hover:border-slate-300"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <button
          type="button"
          data-testid={`comparison-select-${testSlug}`}
          onClick={handleSelect}
          aria-pressed={isSelected}
          className="flex-1 min-w-0 text-left rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
        >
          <div className="flex flex-wrap items-center gap-1.5">
            {rankNumber !== undefined && (
              <span className="text-xs font-bold text-slate-400 tabular-nums">
                #{rankNumber}
              </span>
            )}
            <span className="text-sm font-bold text-slate-900 break-words">
              {item.nome}
            </span>
            {isSelected && (
              <span
                data-testid={`comparison-selected-badge-${testSlug}`}
                className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-700 text-white"
              >
                Selecionado
              </span>
            )}
            {isCentralidade && (
              <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
                Centralidade Metropolitana
              </span>
            )}
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
            <span
              data-testid={`comparison-vuln-${testSlug}`}
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border font-semibold tabular-nums ${
                hasVuln
                  ? "bg-indigo-50 text-indigo-900 border-indigo-200"
                  : "bg-slate-100 text-slate-700 border-slate-300"
              }`}
            >
              <span>Vulnerabilidade:</span>
              <span>{hasVuln ? formatDecimal(vuln) : "Indisponível"}</span>
            </span>

            {isContiguidade && (
              <span
                data-testid={`comparison-estimativa-${testSlug}`}
                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-200 text-[11px] font-medium"
              >
                {bairrosEstimados.length > 0
                  ? `Inclui estimativa (${bairrosEstimados.join(", ")})`
                  : "Estimativa por contiguidade"}
              </span>
            )}
          </div>
        </button>

        <div className="text-right shrink-0">
          {invState.kind === "value" && (
            <div data-testid={`comparison-valor-${testSlug}`} className="text-sm font-extrabold text-slate-900">
              <MonetaryValue value={invState.perCapita} compact={false} suffix=" / hab" />
            </div>
          )}
          {invState.kind === "unavailable" && (
            <div
              data-testid={`comparison-valor-${testSlug}`}
              className={`text-xs font-semibold px-2 py-0.5 rounded border ${
                invState.reason === "population"
                  ? "text-slate-700 bg-slate-100 border-slate-300"
                  : "text-amber-800 bg-amber-50 border-amber-200"
              }`}
            >
              {invState.reason === "population" ? "Per capita indisponível" : "Pagamento indisponível"}
            </div>
          )}
          {invState.kind === "exempt" && (
            <div
              data-testid={`comparison-valor-${testSlug}`}
              className="text-xs font-semibold text-amber-900 bg-amber-100 border border-amber-300 px-2 py-0.5 rounded"
            >
              Isento per capita
            </div>
          )}
        </div>
      </div>

      {/* Barra comparável em escala comum */}
      {invState.kind === "value" && (
        <div
          className="mt-2 w-full bg-slate-200 h-2.5 rounded-full overflow-hidden"
          aria-hidden="true"
        >
          <div
            data-testid={`comparison-bar-${testSlug}`}
            className={`h-2.5 rounded-full transition-all duration-300 ${
              invState.perCapita < 0 ? "bg-rose-600" : isSelected ? "bg-emerald-700" : "bg-emerald-600"
            }`}
            style={{ width: `${barWidthPct}%` }}
          />
        </div>
      )}

      {/* Metadados e total alocado com valor exato acessível */}
      {limitacoes.length > 0 && <div className="mt-2 text-xs text-amber-900">
        <strong>Soma Parcial de Pagamentos</strong>
        {limitacoes.map((limite) => <div key={limite}>{limite}</div>)}
      </div>}
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
        <span className="tabular-nums">
          {formatNumber(populacao)} hab • {item.totalObras ?? 0}{" "}
          {(item.totalObras ?? 0) === 1 ? "obra" : "obras"}
        </span>

        {renderTotalSummary(
          totalTerritorial,
          testSlug,
          metricType,
          item.obrasSemValorPago ?? 0,
          limitacoes.length > 0
        )}
      </div>
    </li>
  );
};

/**
 * Lista principal de Comparação Territorial ordenada pelo Índice de Vulnerabilidade do Bairro,
 * exibindo o Investimento por Habitante em barras comparáveis de escala comum.
 */
export const TerritoryComparisonList: React.FC<TerritoryComparisonListProps> = ({
  activeLayer,
  prefeituras,
  bairros,
  metricType,
  sortDirection,
  onToggleSortDirection,
  territorySearch = "",
  onTerritorySearchChange,
  hasEmptyContractFilter = false,
  onClearContractFilters,
  selectedTerritory,
  onSelectTerritory,
  onOpenNotaMetodologica,
  isVisible = true,
}) => {
  const rowRefs = useRef<Map<string, HTMLLIElement>>(new Map());
  const pendingSelectionScrollRef = useRef<boolean>(false);
  const prevSelectedKeyRef = useRef<string | null>(
    selectedTerritory ? `${selectedTerritory.tipo}:${normalizeName(selectedTerritory.nome)}` : null
  );
  const prevVisibleRef = useRef<boolean>(isVisible);
  const setRowRef = (nome: string) => (el: HTMLLIElement | null) => {
    const normKey = normalizeName(nome);
    if (el) rowRefs.current.set(normKey, el);
    else rowRefs.current.delete(normKey);
  };

  const { orderedItems, missingVulnItems, exemptItems } = useMemo(() => {
    if (activeLayer === "prefeituras") {
      const comIndice = prefeituras.filter((pb) => hasNumericValue(pb.indice_vulnerabilidade));
      const semIndice = prefeituras
        .filter((pb) => !hasNumericValue(pb.indice_vulnerabilidade))
        .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
      return {
        orderedItems: sortByVulnerabilityAndName(comIndice, sortDirection),
        missingVulnItems: semIndice,
        exemptItems: [] as BairroResumo[],
      };
    }

    const elegiveisComIndice = bairros.filter(
      (b) => !isZonaEspecial(b) && hasNumericValue(b.indice_vulnerabilidade)
    );
    const semIndice = bairros
      .filter((b) => !isZonaEspecial(b) && !hasNumericValue(b.indice_vulnerabilidade))
      .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
    const zonasEspeciais = bairros
      .filter((b) => isZonaEspecial(b))
      .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));

    return {
      orderedItems: sortByVulnerabilityAndName(elegiveisComIndice, sortDirection),
      missingVulnItems: semIndice,
      exemptItems: zonasEspeciais,
    };
  }, [activeLayer, prefeituras, bairros, sortDirection]);

  // Escala comum para todas as barras da comparação ativa (independe de ordenação, seleção ou busca)
  const maxPerCapita = useMemo(() => {
    let max = 0;
    const items = activeLayer === "prefeituras" ? prefeituras : bairros;
    const tipo = activeLayer === "prefeituras" ? "prefeitura_bairro" : "bairro";

    for (const item of items) {
      const state = getTerritoryInvestmentState(item, metricType, tipo);
      if (state.kind === "value" && Math.abs(state.perCapita) > max) {
        max = Math.abs(state.perCapita);
      }
    }
    return max > 0 ? max : 1;
  }, [activeLayer, prefeituras, bairros, metricType]);

  // Busca territorial preserva ranking original, valores e escala comum das barras
  const normalizedSearch = normalizeName(territorySearch);
  const hasTerritorySearch = normalizedSearch.length > 0;

  const { filteredOrderedItems, filteredMissingVulnItems, filteredExemptItems } = useMemo(() => {
    const withRank = orderedItems.map((item, idx) => ({ item, rankNumber: idx + 1 }));
    if (!hasTerritorySearch) {
      return {
        filteredOrderedItems: withRank,
        filteredMissingVulnItems: missingVulnItems,
        filteredExemptItems: exemptItems,
      };
    }
    const matchesSearch = (nome: string) => normalizeName(nome).includes(normalizedSearch);
    return {
      filteredOrderedItems: withRank.filter(({ item }) => matchesSearch(item.nome)),
      filteredMissingVulnItems: missingVulnItems.filter((item) => matchesSearch(item.nome)),
      filteredExemptItems: exemptItems.filter((item) => matchesSearch(item.nome)),
    };
  }, [orderedItems, missingVulnItems, exemptItems, hasTerritorySearch, normalizedSearch]);

  const totalMatchesCount =
    filteredOrderedItems.length + filteredMissingVulnItems.length + filteredExemptItems.length;

  // Localiza automaticamente a linha correspondente quando o território é selecionado no mapa
  // Se a lista estiver oculta no celular, adia o scroll até retornar para Lista (preservando posição quando não houve nova seleção no mapa)
  useEffect(() => {
    const currentKey = selectedTerritory
      ? `${selectedTerritory.tipo}:${normalizeName(selectedTerritory.nome)}`
      : null;
    const selectionChanged = currentKey !== prevSelectedKeyRef.current;
    prevSelectedKeyRef.current = currentKey;

    const becameVisible = isVisible && !prevVisibleRef.current;
    prevVisibleRef.current = isVisible;

    if (!selectedTerritory) {
      pendingSelectionScrollRef.current = false;
      return;
    }

    if (!isVisible) {
      if (selectionChanged) {
        pendingSelectionScrollRef.current = true;
      }
      return;
    }

    if (selectionChanged || (becameVisible && pendingSelectionScrollRef.current)) {
      pendingSelectionScrollRef.current = false;
      const key = normalizeName(selectedTerritory.nome);
      const el = rowRefs.current.get(key);
      if (el && typeof el.scrollIntoView === "function") {
        el.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    }
  }, [selectedTerritory, orderedItems, isVisible]);

  const metricLabel =
    metricType === "executado" ? "Valor Pago por habitante" : "Valor Contratual Vigente por habitante";

  return (
    <section
      data-testid="comparison-list-container"
      aria-label="Comparação Territorial por Vulnerabilidade e Investimento por Habitante"
      className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col h-full min-h-0 md:overflow-hidden"
    >
      {/* Cabeçalho da Lista de Comparação */}
      <div className="px-4 py-3 border-b border-slate-200 bg-slate-50/80 rounded-t-xl flex flex-col gap-2 shrink-0">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-slate-900">
              {activeLayer === "prefeituras"
                ? "Prefeituras-Bairro por vulnerabilidade"
                : "Bairros Oficiais por vulnerabilidade"}
            </h2>
            <p className="text-xs text-slate-600 mt-0.5">
              Ordenação pela vulnerabilidade; barras em escala comum ({metricLabel}).
            </p>
          </div>

          {onOpenNotaMetodologica && (
            <button
              type="button"
              data-testid="btn-como-calculado-lista"
              onClick={onOpenNotaMetodologica}
              className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium bg-indigo-50 text-indigo-800 hover:bg-indigo-100 border border-indigo-200 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              <span aria-hidden="true" className="font-bold">
                ⓘ
              </span>
              <span>Metodologia</span>
            </button>
          )}
        </div>

        {/* Busca territorial pelo nome (não altera valores nem escalas) */}
        <div className="flex flex-col gap-1">
          <SearchInput
            id="busca-territorio-input"
            label="Buscar território pelo nome"
            testId="busca-territorio"
            clearTestId="btn-limpar-busca-territorio"
            clearAriaLabel="Limpar busca territorial"
            value={territorySearch}
            onChange={(val) => onTerritorySearchChange?.(val)}
            placeholder={
              activeLayer === "prefeituras"
                ? "Buscar Prefeitura-Bairro pelo nome..."
                : "Buscar Bairro Oficial pelo nome..."
            }
          />
          <p className="text-[11px] text-slate-500 leading-tight">
            Localiza pelo nome sem alterar valores ou escalas; busca por objeto ou Empreiteira fica na Tabela de Obras.
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2">
          <button
            type="button"
            data-testid="btn-inverter-ordenacao"
            onClick={onToggleSortDirection}
            aria-pressed={sortDirection === "desc"}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-white text-slate-800 border border-slate-300 hover:bg-slate-100 transition-colors shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
          >
            <span aria-hidden="true">{sortDirection === "asc" ? "↑" : "↓"}</span>
            <span>
              {sortDirection === "asc"
                ? "Menor vulnerabilidade primeiro"
                : "Maior vulnerabilidade primeiro"}
            </span>
            <span className="text-[11px] font-normal text-slate-500">(Inverter)</span>
          </button>

          <span data-testid="comparison-list-count" className="text-[11px] font-medium text-slate-500">
            {(() => {
              const totalCount = activeLayer === "prefeituras" ? prefeituras.length : bairros.length;
              const label = activeLayer === "prefeituras" ? "Prefeituras-Bairro" : "Bairros Oficiais";
              if (hasTerritorySearch) {
                return `${totalMatchesCount} de ${totalCount} ${label}`;
              }
              const suffix =
                orderedItems.length < totalCount ? ` (${orderedItems.length} comparados)` : "";
              return `${totalCount} ${label}${suffix}`;
            })()}
          </span>
        </div>
      </div>

      {/* Lista rolável dos territórios */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {hasEmptyContractFilter && (
          <div
            data-testid="aviso-filtros-sem-contratos"
            className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-950 space-y-2"
          >
            <p className="leading-relaxed">
              <strong>Nenhum contrato corresponde aos filtros selecionados.</strong> Todos os territórios
              permanecem visíveis com alocação observada de <strong>R$ 0</strong> (zero obras no recorte),
              sem alterar população, vulnerabilidade censitária ou isenções.
            </p>
            {onClearContractFilters && (
              <button
                type="button"
                data-testid="btn-recuperar-filtros-vazios"
                onClick={onClearContractFilters}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-amber-900 text-white hover:bg-amber-950 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-700"
              >
                Limpar filtros de contratos
              </button>
            )}
          </div>
        )}

        {hasTerritorySearch && totalMatchesCount === 0 ? (
          <div
            data-testid="busca-territorio-vazia"
            className="rounded-xl border border-slate-200 bg-slate-50 p-5 text-center space-y-2"
          >
            <h3 className="text-sm font-bold text-slate-800">
              Nenhum território encontrado para &ldquo;{territorySearch.trim()}&rdquo;
            </h3>
            <p className="text-xs text-slate-600 max-w-sm mx-auto leading-relaxed">
              A busca territorial procura apenas nomes de{" "}
              {activeLayer === "prefeituras" ? "Prefeituras-Bairro" : "Bairros Oficiais"}. Para pesquisar
              por objeto do contrato ou Empreiteira, consulte a <strong>Tabela de Obras</strong>.
            </p>
            <button
              type="button"
              data-testid="btn-limpar-busca-territorio-vazia"
              onClick={() => onTerritorySearchChange?.("")}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
            >
              Limpar busca territorial
            </button>
          </div>
        ) : (
          <>
            <ul data-testid="comparison-list-items" className="space-y-2">
              {filteredOrderedItems.map(({ item, rankNumber }) => (
                <ComparisonTerritoryRow
                  key={item.id ?? item.nome}
                  item={item}
                  isPrefeitura={activeLayer === "prefeituras"}
                  rankNumber={rankNumber}
                  metricType={metricType}
                  maxPerCapita={maxPerCapita}
                  selectedTerritory={selectedTerritory}
                  onSelectTerritory={onSelectTerritory}
                  rowRef={setRowRef(item.nome)}
                />
              ))}
            </ul>

            {/* Territórios com Índice de Vulnerabilidade indisponível (fora do ordenamento numérico) */}
            {filteredMissingVulnItems.length > 0 && (
              <div
                data-testid="comparison-missing-vuln-section"
                className="pt-3 mt-3 border-t border-slate-200 space-y-2"
              >
                <h3 className="text-xs font-bold text-slate-700">
                  Dado de vulnerabilidade indisponível (fora do ordenamento numérico)
                </h3>
                <ul className="space-y-2">
                  {filteredMissingVulnItems.map((item) => (
                    <ComparisonTerritoryRow
                      key={item.id ?? item.nome}
                      item={item}
                      isPrefeitura={activeLayer === "prefeituras"}
                      metricType={metricType}
                      maxPerCapita={maxPerCapita}
                      selectedTerritory={selectedTerritory}
                      onSelectTerritory={onSelectTerritory}
                      rowRef={setRowRef(item.nome)}
                    />
                  ))}
                </ul>
              </div>
            )}

            {/* Zonas Especiais Não-Residenciais (fora do ranking numérico de vulnerabilidade/per capita) */}
            {activeLayer === "bairros" && filteredExemptItems.length > 0 && (
              <div
                data-testid="comparison-exempt-section"
                className="pt-3 mt-3 border-t border-slate-200 space-y-2"
              >
                <h3 className="text-xs font-bold text-slate-700">
                  Zonas Especiais Não-Residenciais (isentas de índice e cálculo per capita)
                </h3>
                <ul className="space-y-2">
                  {filteredExemptItems.map((b) => {
                const testSlug = normalizeTestId(b.nome);
                const isSelected =
                  selectedTerritory?.tipo === "bairro" &&
                  normalizeName(selectedTerritory.nome) === normalizeName(b.nome);
                const totalTerritorial = getTerritoryAbsoluteTotal(b, metricType);

                return (
                  <li
                    key={b.id ?? b.nome}
                    ref={setRowRef(b.nome)}
                    data-testid={`comparison-row-${testSlug}`}
                    data-selected={isSelected ? "true" : "false"}
                    className={`rounded-xl border p-3 ${
                      isSelected
                        ? "bg-amber-50 border-amber-600 ring-2 ring-amber-400/40"
                        : "bg-amber-50/40 border-amber-200"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <button
                        type="button"
                        data-testid={`comparison-select-${testSlug}`}
                        onClick={() => onSelectTerritory(createBairroSelection(b))}
                        aria-pressed={isSelected}
                        className="flex-1 min-w-0 text-left rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-600"
                      >
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-sm font-bold text-slate-900">{b.nome}</span>
                          {isSelected && (
                            <span
                              data-testid={`comparison-selected-badge-${testSlug}`}
                              className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-800 text-white"
                            >
                              Selecionado
                            </span>
                          )}
                          <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
                            Zona Especial Não-Residencial
                          </span>
                        </div>
                        <span
                          data-testid={`comparison-vuln-${testSlug}`}
                          className="inline-block mt-1 text-xs font-semibold text-amber-900"
                        >
                          Vulnerabilidade: Isento
                        </span>
                      </button>
                      <div
                        data-testid={`comparison-valor-${testSlug}`}
                        className="text-xs font-semibold text-amber-900 bg-amber-100 border border-amber-300 px-2 py-0.5 rounded shrink-0"
                      >
                        Isento per capita
                      </div>
                    </div>
                    {metricType === "executado" && !!b.limitacoesConhecidas?.length && <div className="mt-2 text-xs text-amber-900">
                      <strong>Soma Parcial de Pagamentos</strong>
                      {b.limitacoesConhecidas.map((limite) => <div key={limite}>{limite}</div>)}
                    </div>}
                    <div className="mt-1.5 flex items-center justify-between text-xs text-slate-600">
                      <span>
                        {b.totalObras ?? 0} {(b.totalObras ?? 0) === 1 ? "obra" : "obras"}
                      </span>
                      {renderTotalSummary(
                        totalTerritorial,
                        testSlug,
                        metricType,
                        metricType === "executado" ? (b.obrasSemValorPago ?? 0) : 0,
                        metricType === "executado" && !!b.limitacoesConhecidas?.length
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
          </>
        )}
      </div>
    </section>
  );
};

import React, { useEffect, useMemo, useState } from "react";
import {
  MetricType,
  ObraCompacta,
  SemaforoStatus,
  TerritorySelection,
  VOCACAO_BADGE_CLASS,
  VocacaoObra,
} from "../types";
import { formatCurrency, formatNumber, formatDate } from "../utils/formatters";
import {
  getObraTerritoryShare,
  getTerritoryAbsoluteTotal,
  hasNumericPayment,
  ObraTerritoryShare,
} from "../utils/territory";
import { SearchInput } from "./SearchInput";

interface WorksTableProps {
  /**
   * Lista de contratos de obras públicas a serem exibidos na tabela.
   */
  obras: ObraCompacta[];
  /**
   * Métrica financeira ativa: 'vigente' ou 'executado'.
   */
  metricType: MetricType;
  /**
   * Território selecionado para exibição proporcional de contratos em Cota-Parte.
   */
  selectedTerritory?: TerritorySelection | null;
  /**
   * Bairros pertencentes à Prefeitura-Bairro selecionada (quando aplicável).
   */
  childBairroKeys?: ReadonlySet<string>;
  /**
   * Quantidade total de contratos/frentes do território antes da busca textual na tabela.
   */
  totalTerritoryObrasCount?: number;
  /**
   * Callback opcional ao clicar em uma obra para inspecionar detalhes.
   */
  onSelectObra?: (obra: ObraCompacta) => void;
  /**
   * Termo de busca por objeto da obra, Empreiteira ou CNPJ.
   */
  busca?: string;
  /**
   * Callback para atualizar o termo de busca de obras.
   */
  onBuscaChange?: (busca: string) => void;
  /**
   * Indica se há filtros de contrato ativos além da busca, permitindo recuperação in-place quando vazio.
   */
  hasActiveContractFilters?: boolean;
  /**
   * Callback para limpar os filtros de contrato mantendo nível e métrica.
   */
  onClearContractFilters?: () => void;
  /**
   * Callback opcional para retornar à Comparação Territorial preservando contexto.
   */
  onBackToComparison?: () => void;
  /**
   * Callback opcional para limpar a seleção territorial e ver todas as obras da cidade.
   */
  onClearTerritory?: () => void;
}

type SortField =
  | "objeto"
  | "unidadeGestora"
  | "credor"
  | "tema"
  | "valorOriginal"
  | "valorContratualVigente"
  | "percentualExecutado"
  | "semaforo";

type SortDirection = "asc" | "desc";

function getMetricSortValue(
  obra: ObraCompacta,
  share: ObraTerritoryShare,
  selectedTerritory: TerritorySelection | null | undefined,
  metricType: MetricType
): number {
  if (selectedTerritory && share.isFrenteMedicao && !share.isDirectOrRegionalMatch) {
    return metricType === "executado" ? share.frentesValorPago : 0;
  }
  if (metricType === "vigente") {
    return (obra.valorContratualVigente ?? 0) * share.peso;
  }
  return hasNumericPayment(obra.valorPago) ? obra.valorPago * share.peso : -1;
}

/**
 * Renderiza o badge estilizado e acessível do Semáforo da Obra.
 *
 * @summary Cria o elemento visual da cor do Semáforo com indicador e texto legível.
 * @description Constrói um indicador visual em pílula com ponto pulsante para status Vermelho (Crítica),
 * ponto amarelo fixo para Atenção e ponto verde para No Prazo, garantindo contraste e acessibilidade.
 *
 * @param status - Status canônico ('VERDE', 'AMARELO' ou 'VERMELHO').
 * @param rotulo - Texto descritivo para exibição no badge.
 * @returns Elemento JSX com as cores e indicador do estado.
 * @throws Não lança exceções.
 */
function renderSemaforoBadge(status: SemaforoStatus, rotulo?: string) {
  switch (status) {
    case "VERMELHO":
      return (
        <span
          data-testid="badge-semaforo-vermelho"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200"
          title="Obra Crítica / Atrasada"
        >
          <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span>
          {rotulo || "Crítica"}
        </span>
      );
    case "AMARELO":
      return (
        <span
          data-testid="badge-semaforo-amarelo"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-300"
          title="Obra em Atenção / Prazo Prorrogado"
        >
          <span className="w-2 h-2 rounded-full bg-amber-500"></span>
          {rotulo || "Atenção"}
        </span>
      );
    case "VERDE":
    default:
      return (
        <span
          data-testid="badge-semaforo-verde"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200"
          title="Obra No Prazo"
        >
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          {rotulo || "No Prazo"}
        </span>
      );
  }
}

/**
 * Componente de Tabela Detalhada de Obras Públicas de Salvador.
 *
 * @summary Exibe a listagem tabular completa para auditoria cidadã, com ordenação por coluna e paginação.
 * @description Apresenta cada contrato público com seu objeto, órgão contratante, credor,
 * valor original, valor contratual vigente acompanhado do percentual de acréscimo de aditivos,
 * percentual físico executado com barra de progresso e badge do Semáforo da Obra.
 * Permite ordenação clicável em todas as colunas essenciais e paginação client-side.
 *
 * @param props - Propriedades de obras, métrica financeira ativa e manipulador de seleção.
 * @returns Elemento JSX da tabela ou estado vazio quando nenhum resultado for encontrado.
 * @throws Não lança exceções.
 */
function renderVocacaoBadge(obra: ObraCompacta, compact: boolean = false) {
  const vocacao = (obra.vocacao as VocacaoObra) || "Vizinhança e Comunidade";
  return (
    <span
      data-testid={`badge-vocacao-${obra.id}`}
      className={`${compact ? "px-1.5" : "px-2"} py-0.5 rounded-full text-[10px] font-semibold ${
        VOCACAO_BADGE_CLASS[vocacao] || VOCACAO_BADGE_CLASS["Vizinhança e Comunidade"]
      }`}
    >
      {vocacao}
    </span>
  );
}

export const WorksTable: React.FC<WorksTableProps> = ({
  obras,
  metricType,
  selectedTerritory = null,
  childBairroKeys,
  totalTerritoryObrasCount,
  onSelectObra,
  busca = "",
  onBuscaChange,
  hasActiveContractFilters = false,
  onClearContractFilters,
  onBackToComparison,
  onClearTerritory,
}) => {
  const [sortField, setSortField] = useState<SortField>("valorContratualVigente");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [showOptionalColumns, setShowOptionalColumns] = useState<boolean>(false);

  useEffect(() => {
    setCurrentPage(1);
  }, [selectedTerritory?.tipo, selectedTerritory?.id, selectedTerritory?.nome]);

  const territoryBreakdown = useMemo(() => {
    if (!selectedTerritory) return null;
    let allocatedFromRows = 0;
    let frentesFromRows = 0;

    for (const o of obras) {
      const share = getObraTerritoryShare(o, selectedTerritory, childBairroKeys);
      if (share.isCotaParte || share.isDirectOrRegionalMatch) {
        allocatedFromRows++;
      }
      if (share.isFrenteMedicao) {
        frentesFromRows += share.frentes.length;
      }
    }

    const totalTerritorial = getTerritoryAbsoluteTotal(selectedTerritory, metricType);
    return {
      allocatedContracts: selectedTerritory.totalObras ?? allocatedFromRows,
      frentesNotes: selectedTerritory.totalFrentesMedicao ?? frentesFromRows,
      totalTerritorial,
    };
  }, [obras, selectedTerritory, childBairroKeys, metricType]);

  // Manipulador de ordenação por cabeçalho clicável
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
    setCurrentPage(1);
  };

  // Ordenação determinística das obras
  const sortedObras = useMemo(() => {
    return [...obras].sort((a, b) => {
      let valA: any = "";
      let valB: any = "";
      const shareA = getObraTerritoryShare(a, selectedTerritory, childBairroKeys);
      const shareB = getObraTerritoryShare(b, selectedTerritory, childBairroKeys);
      const pesoA = shareA.peso;
      const pesoB = shareB.peso;

      switch (sortField) {
        case "objeto":
          valA = a.objeto || "";
          valB = b.objeto || "";
          break;
        case "unidadeGestora":
          valA = a.unidadeGestora || "";
          valB = b.unidadeGestora || "";
          break;
        case "credor":
          valA = a.credor || "";
          valB = b.credor || "";
          break;
        case "tema":
          valA = a.tema || "";
          valB = b.tema || "";
          break;
        case "valorOriginal":
          valA = (a.valorOriginal || 0) * pesoA;
          valB = (b.valorOriginal || 0) * pesoB;
          break;
        case "valorContratualVigente":
          valA = getMetricSortValue(a, shareA, selectedTerritory, metricType);
          valB = getMetricSortValue(b, shareB, selectedTerritory, metricType);
          break;
        case "percentualExecutado":
          valA = a.percentualExecutado || 0;
          valB = b.percentualExecutado || 0;
          break;
        case "semaforo": {
          // Peso hierárquico: Vermelho (3) > Amarelo (2) > Verde (1)
          const weight = (s?: SemaforoStatus) => (s === "VERMELHO" ? 3 : s === "AMARELO" ? 2 : 1);
          valA = weight(a.semaforo?.status);
          valB = weight(b.semaforo?.status);
          break;
        }
        default:
          valA = a.valorContratualVigente * pesoA;
          valB = b.valorContratualVigente * pesoB;
      }

      if (typeof valA === "string" && typeof valB === "string") {
        return sortDirection === "asc" ? valA.localeCompare(valB) : valB.localeCompare(valA);
      }
      return sortDirection === "asc" ? (valA > valB ? 1 : -1) : (valA < valB ? 1 : -1);
    });
  }, [obras, sortField, sortDirection, metricType, selectedTerritory]);

  // Paginação client-side
  const totalPages = Math.max(1, Math.ceil(sortedObras.length / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * pageSize;
  const paginatedObras = sortedObras.slice(startIndex, startIndex + pageSize);

  // Ícone visual de ordenação
  const renderSortIndicator = (field: SortField) => {
    if (sortField !== field) {
      return (
        <span className="opacity-30 ml-1 text-[10px]">▲▼</span>
      );
    }
    return (
      <span className="text-emerald-600 ml-1 font-bold text-xs">
        {sortDirection === "asc" ? "▲" : "▼"}
      </span>
    );
  };

  const renderBuscaObrasControl = () =>
    onBuscaChange ? (
      <SearchInput
        id="filtro-busca-obras-input"
        label="Buscar obra por objeto, Empreiteira ou CNPJ"
        testId="filtro-busca"
        clearTestId="btn-limpar-busca-obras"
        clearAriaLabel="Limpar busca de obras"
        value={busca}
        onChange={(val) => {
          onBuscaChange(val);
          setCurrentPage(1);
        }}
        onClear={() => {
          onBuscaChange("");
          setCurrentPage(1);
        }}
        placeholder="Buscar por objeto da obra, palavra-chave, Empreiteira ou CNPJ..."
        className="flex-1 min-w-[220px] max-w-md"
      />
    ) : null;

  if (obras.length === 0) {
    const isEmptyTerritoryWithoutFilter =
      Boolean(selectedTerritory) && busca.trim().length === 0 && !hasActiveContractFilters;

    return (
      <div
        data-testid="tabela-obras-vazia"
        className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8 text-center my-4 space-y-3"
      >
        {onBuscaChange && (
          <div className="flex justify-center text-left">{renderBuscaObrasControl()}</div>
        )}
        <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 mx-auto flex items-center justify-center">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h4 className="text-sm font-bold text-slate-800">
          {selectedTerritory
            ? `Nenhuma obra encontrada em ${selectedTerritory.nome}`
            : "Nenhuma obra encontrada"}
        </h4>
        <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
          {isEmptyTerritoryWithoutFilter && selectedTerritory
            ? selectedTerritory.tipo === "bairro"
              ? `O Bairro Oficial ${selectedTerritory.nome} não possui obras alocadas diretamente ou por Frentes de Medição neste recorte. Contratos de escopo regional ou de cidade inteira não são divididos artificialmente entre bairros.`
              : `A Prefeitura-Bairro ${selectedTerritory.nome} não possui obras alocadas neste recorte.`
            : "Nenhum contrato corresponde aos critérios e filtros selecionados. Tente alterar a busca de obras ou os filtros de contratos."}
        </p>
        <div className="flex flex-wrap items-center justify-center gap-2">
          {onBuscaChange && busca.trim().length > 0 && (
            <button
              type="button"
              data-testid="btn-recuperar-busca-obras-vazia"
              onClick={() => {
                onBuscaChange("");
                setCurrentPage(1);
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 transition-colors"
            >
              Limpar busca de obras
            </button>
          )}
          {hasActiveContractFilters && onClearContractFilters && (
            <button
              type="button"
              data-testid="btn-recuperar-filtros-tabela-vazia"
              onClick={() => {
                onClearContractFilters();
                setCurrentPage(1);
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-slate-300 text-slate-800 hover:bg-slate-100 transition-colors"
            >
              Limpar filtros de contratos
            </button>
          )}
          {onBackToComparison && (
            <button
              type="button"
              data-testid="btn-vazio-voltar-comparacao"
              onClick={onBackToComparison}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
            >
              Voltar à Comparação Territorial
            </button>
          )}
          {selectedTerritory && onClearTerritory && (
            <button
              type="button"
              data-testid="btn-vazio-limpar-territorio"
              onClick={onClearTerritory}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-slate-300 text-slate-700 hover:bg-slate-100 transition-colors"
            >
              Ver todas as obras da cidade
            </button>
          )}
        </div>
      </div>
    );
  }

  const activeMetricLabel = metricType === "vigente" ? "Valor Contratual Vigente" : "Valor Pago";

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
      {/* Contexto Explícito da Consulta Territorial de Obras */}
      {selectedTerritory && territoryBreakdown && (
        <div
          data-testid="consulta-territorial-contexto"
          className="px-4 py-3 bg-emerald-50/70 border-b border-emerald-200 flex flex-col gap-1.5 text-xs text-emerald-950"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-bold uppercase tracking-wider text-[10px] bg-emerald-200/80 text-emerald-950 px-2 py-0.5 rounded">
                Consulta Territorial • {selectedTerritory.tipo === "bairro" ? "Bairro Oficial" : "Prefeitura-Bairro"}
              </span>
              <strong className="text-sm text-slate-900">{selectedTerritory.nome}</strong>
              <span className="text-slate-600">
                Métrica ativa: <strong className="text-slate-900">{activeMetricLabel}</strong>
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="bg-white border border-emerald-200 px-2 py-0.5 rounded font-medium text-slate-800">
                {territoryBreakdown.allocatedContracts}{" "}
                {territoryBreakdown.allocatedContracts === 1 ? "contrato alocado" : "contratos alocados"}
                {territoryBreakdown.frentesNotes > 0 && (
                  <>
                    {" "}
                    + {territoryBreakdown.frentesNotes}{" "}
                    {territoryBreakdown.frentesNotes === 1 ? "frente de medição" : "frentes de medição"}
                  </>
                )}
              </span>
              <span className="bg-white border border-emerald-200 px-2 py-0.5 rounded font-bold text-emerald-900">
                Total territorial:{" "}
                {territoryBreakdown.totalTerritorial !== undefined
                  ? formatCurrency(territoryBreakdown.totalTerritorial)
                  : "Pagamento indisponível"}
              </span>
              {busca.trim().length > 0 && totalTerritoryObrasCount !== undefined && (
                <span className="bg-amber-50 border border-amber-200 px-2 py-0.5 rounded font-medium text-amber-900">
                  Exibindo {formatNumber(obras.length)} de {formatNumber(totalTerritoryObrasCount)} na busca
                </span>
              )}
            </div>
          </div>
          <p className="text-[11px] text-emerald-900/90 leading-relaxed">
            Os valores de <strong>Cota-Parte</strong> e <strong>Frente de Medição</strong> mostram a parcela atribuída a este território separadamente do total integral do contrato.
            {selectedTerritory.tipo === "bairro" && selectedTerritory.prefeitura_bairro
              ? ` Contratos regionais (${selectedTerritory.prefeitura_bairro}) e de Escopo Cidade sem frente comprovada não são divididos entre bairros.`
              : ""}
          </p>
        </div>
      )}

      {/* Cabeçalho de Controle da Tabela */}
      <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-2.5">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-bold text-slate-800">
            {selectedTerritory ? `Obras de ${selectedTerritory.nome}` : "Tabela Detalhada de Obras Públicas"}
          </h3>
          <span className="text-xs text-slate-500 bg-slate-200/80 px-2 py-0.5 rounded-full font-medium">
            {formatNumber(obras.length)} {obras.length === 1 ? "obra" : "obras"}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {renderBuscaObrasControl()}

          {/* Toggle de Colunas Opcionais */}
          <button
            type="button"
            data-testid="btn-colunas-opcionais"
            aria-expanded={showOptionalColumns}
            onClick={() => setShowOptionalColumns((prev) => !prev)}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 ${
              showOptionalColumns
                ? "bg-slate-900 text-white border-slate-900"
                : "bg-white text-slate-700 border-slate-300 hover:bg-slate-100"
            }`}
          >
            {showOptionalColumns ? "Ocultar colunas adicionais" : "Colunas adicionais"}
          </button>

          {/* Seletor de Itens por Página */}
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <span>Exibir:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="text-xs bg-white border border-slate-300 rounded px-2 py-1 font-medium text-slate-700 focus:outline-none"
            >
              <option value={5}>5 por página</option>
              <option value={10}>10 por página</option>
              <option value={25}>25 por página</option>
              <option value={50}>50 por página</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tabela Responsiva */}
      <div className="overflow-x-auto">
        <table
          data-testid="tabela-obras"
          className="w-full text-left border-collapse text-xs"
        >
          <thead>
            <tr className="bg-slate-100 text-slate-700 border-b border-slate-200 font-semibold uppercase tracking-wider text-[11px]">
              <th className="py-3 px-3">
                <button
                  type="button"
                  data-testid="sort-objeto"
                  onClick={() => handleSort("objeto")}
                  className="flex items-center hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 rounded"
                >
                  Identificação da Obra
                  {renderSortIndicator("objeto")}
                </button>
              </th>
              <th data-testid="col-territorio" className="py-3 px-3 whitespace-nowrap">
                Bairro / Território
              </th>
              {showOptionalColumns && (
                <>
                  <th className="py-3 px-3 whitespace-nowrap">
                    <button
                      type="button"
                      data-testid="sort-orgao"
                      onClick={() => handleSort("unidadeGestora")}
                      className="flex items-center hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 rounded"
                    >
                      Órgão
                      {renderSortIndicator("unidadeGestora")}
                    </button>
                  </th>
                  <th className="py-3 px-3 whitespace-nowrap">
                    <button
                      type="button"
                      data-testid="sort-credor"
                      onClick={() => handleSort("credor")}
                      className="flex items-center hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 rounded"
                    >
                      Empreiteira
                      {renderSortIndicator("credor")}
                    </button>
                  </th>
                  <th className="py-3 px-3 whitespace-nowrap">
                    <button
                      type="button"
                      data-testid="sort-tema"
                      onClick={() => handleSort("tema")}
                      className="flex items-center hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 rounded"
                    >
                      Tema da Obra
                      {renderSortIndicator("tema")}
                    </button>
                  </th>
                  <th className="py-3 px-3 text-right whitespace-nowrap">
                    <button
                      type="button"
                      data-testid="sort-valor-original"
                      onClick={() => handleSort("valorOriginal")}
                      className="flex items-center justify-end w-full hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 rounded"
                    >
                      Valor Original
                      {renderSortIndicator("valorOriginal")}
                    </button>
                  </th>
                </>
              )}
              <th className="py-3 px-3 text-right whitespace-nowrap">
                <button
                  type="button"
                  data-testid="sort-valor"
                  onClick={() => handleSort("valorContratualVigente")}
                  className="flex items-center justify-end w-full hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 rounded"
                >
                  {metricType === "vigente" ? "Valor Contratual Vigente" : "Valor Pago"}
                  {renderSortIndicator("valorContratualVigente")}
                </button>
              </th>
              <th className="py-3 px-3 text-center whitespace-nowrap">
                <button
                  type="button"
                  data-testid="sort-percentual"
                  onClick={() => handleSort("percentualExecutado")}
                  className="flex items-center justify-center w-full hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 rounded"
                >
                  Execução Física
                  {renderSortIndicator("percentualExecutado")}
                </button>
              </th>
              <th className="py-3 px-3 text-center whitespace-nowrap">
                <button
                  type="button"
                  data-testid="sort-semaforo"
                  onClick={() => handleSort("semaforo")}
                  className="flex items-center justify-center w-full hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 rounded"
                >
                  Risco (Semáforo)
                  {renderSortIndicator("semaforo")}
                </button>
              </th>
              <th data-testid="col-acoes" className="py-3 px-3 text-right whitespace-nowrap">
                Detalhes
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {paginatedObras.map((o) => {
              const deltaPerc = o.deltaPercentualValor ?? 0;
              const hasAditivo = deltaPerc > 0;
              const semaforoStatus = o.semaforo?.status || "VERDE";
              const semaforoRotulo = o.semaforo?.rotulo;
              const share = getObraTerritoryShare(o, selectedTerritory, childBairroKeys);
              const isCotaFiltrada = Boolean(selectedTerritory && share.isCotaParte && share.matched);
              const isFrenteFiltrada = Boolean(
                selectedTerritory && share.isFrenteMedicao && !share.isDirectOrRegionalMatch
              );
              const valorBase =
                metricType === "vigente"
                  ? o.valorContratualVigente
                  : hasNumericPayment(o.valorPago)
                    ? o.valorPago
                    : undefined;
              const valorOriginalExibido = (o.valorOriginal || o.valorContratualVigente) * share.peso;
              const valorPrincipalExibido = valorBase !== undefined ? valorBase * share.peso : undefined;
              const territorioPrincipalLabel = isCotaFiltrada
                ? share.cotas.map((c) => c.bairro).join(", ")
                : isFrenteFiltrada
                  ? share.frentes.map((f) => f.bairro || f.prefeituraBairro).filter(Boolean).join(", ")
                  : o.bairro ||
                    (o.prefeituraBairro ? `Prefeitura-Bairro: ${o.prefeituraBairro}` : "Escopo Cidade (Não-Localizado)");

              return (
                <tr
                  key={o.id}
                  data-testid={`linha-obra-${o.id}`}
                  onClick={() => onSelectObra && onSelectObra(o)}
                  className={`hover:bg-slate-50/80 transition-colors ${
                    onSelectObra ? "cursor-pointer" : ""
                  }`}
                >
                  {/* Identificação da Obra */}
                  <td className="py-3 px-3 max-w-md">
                    <p className="font-semibold text-slate-800 leading-snug" title={o.objeto}>
                      {o.objeto}
                    </p>
                    <div className="flex flex-wrap items-center gap-1.5 mt-1 text-[10px] text-slate-500">
                      <span>Contrato: {o.numeroContrato || "S/N"}</span>
                      {(o.dtInicioVigencia || o.ano) && (
                        <>
                          <span>•</span>
                          <span data-testid={`data-inicio-obra-${o.id}`}>
                            Início: {formatDate(o.dtInicioVigencia) || String(o.ano)}
                          </span>
                        </>
                      )}
                      <span>•</span>
                      <span>Situação: {o.situacao || "Não informada"}</span>
                      {!showOptionalColumns && (
                        <>
                          <span>•</span>
                          {renderVocacaoBadge(o, true)}
                        </>
                      )}
                    </div>
                  </td>

                  {/* Bairro / Território e Pertença */}
                  <td className="py-3 px-3 max-w-xs">
                    <div className="flex flex-col items-start gap-1">
                      <span className="font-semibold text-slate-800 text-xs">
                        {territorioPrincipalLabel}
                      </span>
                      {o.prefeituraBairro && o.bairro && (
                        <span className="text-[10px] text-slate-500">
                          {o.prefeituraBairro}
                        </span>
                      )}
                      <div className="flex flex-wrap items-center gap-1 text-[10px]">
                        {o.nivel && (
                          <span
                            data-testid={`badge-nivel-${o.id}`}
                            className={`font-medium px-1.5 py-0.5 rounded border ${
                              o.nivel === "Pontual"
                                ? "text-emerald-700 bg-emerald-50 border-emerald-200"
                                : o.nivel === "Bairro"
                                ? "text-sky-700 bg-sky-50 border-sky-200"
                                : o.nivel === "Regional (Prefeitura-Bairro)"
                                ? "text-indigo-700 bg-indigo-50 border-indigo-200"
                                : "text-purple-700 bg-purple-50 border-purple-200"
                            }`}
                          >
                            {share.isCotaParte
                              ? o.nivel
                              : `${o.nivel}${o.bairro ? `: ${o.bairro}` : o.prefeituraBairro ? `: ${o.prefeituraBairro}` : ""}`}
                          </span>
                        )}
                        {share.isCotaParte && (
                          <span
                            data-testid={`badge-cota-parte-${o.id}`}
                            className="font-semibold px-1.5 py-0.5 rounded border text-amber-800 bg-amber-50 border-amber-200"
                          >
                            {isCotaFiltrada
                              ? `Cota-Parte (${share.fracao})`
                              : `Cota-Parte (${share.totalUnidades}/${share.totalUnidades})`}
                          </span>
                        )}
                        {isFrenteFiltrada && (
                          <span
                            data-testid={`badge-frente-medicao-${o.id}`}
                            className="font-semibold px-1.5 py-0.5 rounded border text-indigo-800 bg-indigo-50 border-indigo-200"
                          >
                            Frente de Medição ({share.frentes.length})
                          </span>
                        )}
                      </div>
                      {share.isCotaParte && o.cotasListaFechada && o.cotasListaFechada.length > 0 && (
                        <div
                          data-testid={`cota-breakdown-${o.id}`}
                          className="flex flex-wrap items-center gap-1 mt-0.5 text-[10px]"
                        >
                          {o.cotasListaFechada.map((cota) => {
                            const isMatchedQuota =
                              Boolean(selectedTerritory) &&
                              share.cotas.some((mc) => mc.bairro === cota.bairro);
                            return (
                              <span
                                key={cota.bairro}
                                className={`px-1.5 py-0.5 rounded border ${
                                  isMatchedQuota
                                    ? "bg-amber-100 text-amber-900 border-amber-300 font-semibold"
                                    : "bg-slate-50 text-slate-600 border-slate-200"
                                }`}
                              >
                                {cota.bairro} ({cota.fracao})
                              </span>
                            );
                          })}
                        </div>
                      )}
                      {isFrenteFiltrada && share.frentes.length > 0 && (
                        <div
                          data-testid={`frente-breakdown-${o.id}`}
                          className="flex flex-wrap items-center gap-1 mt-0.5 text-[10px]"
                        >
                          {share.frentes.map((frente) => (
                            <span
                              key={frente.notaLiquidacao}
                              className="px-1.5 py-0.5 rounded border bg-indigo-50 text-indigo-900 border-indigo-200 font-medium"
                            >
                              {frente.notaLiquidacao}
                              {frente.bairro ? ` (${frente.bairro})` : ""}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </td>

                  {/* Colunas Secundárias Opcionais */}
                  {showOptionalColumns && (
                    <>
                      <td className="py-3 px-3 whitespace-nowrap">
                        <span className="inline-block bg-slate-100 text-slate-700 font-medium px-2 py-0.5 rounded text-[11px]">
                          {o.unidadeGestora}
                        </span>
                      </td>

                      <td className="py-3 px-3 max-w-xs">
                        <p className="text-slate-700 font-medium truncate" title={o.credor}>
                          {o.credor || "Não informado"}
                        </p>
                      </td>

                      <td className="py-3 px-3 whitespace-nowrap">
                        <div className="flex flex-col items-start gap-1">
                          <span className="text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full text-[11px] font-medium">
                            {o.tema || "Manutenção Urbana e Outros"}
                          </span>
                          {renderVocacaoBadge(o, false)}
                        </div>
                      </td>

                      <td className="py-3 px-3 text-right whitespace-nowrap text-slate-500 font-medium">
                        {isFrenteFiltrada ? (
                          <div>
                            <span className="text-[11px] text-slate-500">Sem rateio</span>
                            <div className="text-[10px] font-normal text-slate-400">
                              Total: {formatCurrency(o.valorOriginal || o.valorContratualVigente)}
                            </div>
                          </div>
                        ) : (
                          <>
                            <div>{formatCurrency(valorOriginalExibido)}</div>
                            {isCotaFiltrada && (
                              <div className="text-[10px] font-normal text-slate-400">
                                Total: {formatCurrency(o.valorOriginal || o.valorContratualVigente)}
                              </div>
                            )}
                          </>
                        )}
                      </td>
                    </>
                  )}

                  {/* Valor da Métrica Ativa (com distinção entre parcela territorial e contrato integral) */}
                  <td className="py-3 px-3 text-right whitespace-nowrap font-bold text-slate-900">
                    {isFrenteFiltrada ? (
                      metricType === "executado" ? (
                        <>
                          <div className="text-indigo-900">{formatCurrency(share.frentesValorPago)}</div>
                          <div className="text-[10px] font-medium text-indigo-700">
                            Parcela (Frentes • liq. {formatCurrency(share.frentesValorLiquidado)})
                          </div>
                          {valorBase !== undefined && (
                            <div className="text-[10px] font-normal text-slate-500">
                              Total contrato: {formatCurrency(valorBase)}
                            </div>
                          )}
                        </>
                      ) : (
                        <>
                          <div className="text-xs font-semibold text-indigo-800">
                            Sem rateio contratual
                          </div>
                          <div className="text-[10px] font-normal text-slate-500">
                            Soma apenas em Valor Pago
                          </div>
                          <div className="text-[10px] font-normal text-slate-500">
                            Total contrato: {formatCurrency(o.valorContratualVigente)}
                          </div>
                        </>
                      )
                    ) : valorPrincipalExibido !== undefined ? (
                      <>
                        <div>{formatCurrency(valorPrincipalExibido)}</div>
                        {isCotaFiltrada && valorBase !== undefined && (
                          <div className="text-[10px] font-normal text-slate-500">
                            Total contrato: {formatCurrency(valorBase)}
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="text-xs font-semibold text-amber-800">
                        Pagamento indisponível
                      </div>
                    )}
                    {hasAditivo && !isFrenteFiltrada && (
                      <span
                        className={`text-[10px] font-semibold ${
                          deltaPerc > 25
                            ? "text-rose-600"
                            : deltaPerc >= 10
                            ? "text-amber-600"
                            : "text-emerald-600"
                        }`}
                        title={`Acréscimo de ${formatCurrency((o.valorAditivos ?? 0) * share.peso)}`}
                      >
                        +{deltaPerc.toFixed(1).replace(".", ",")}%
                      </span>
                    )}
                  </td>

                  {/* Execução Física com Barra de Progresso */}
                  <td className="py-3 px-3 text-center whitespace-nowrap">
                    <div className="flex flex-col items-center gap-1">
                      <span className="font-semibold text-slate-700 text-xs">
                        {(o.percentualExecutado || 0).toFixed(1).replace(".", ",")}%
                      </span>
                      <div className="w-16 bg-slate-200 h-1.5 rounded-full overflow-hidden">
                        <div
                          className="bg-emerald-500 h-1.5 rounded-full"
                          style={{
                            width: `${Math.min(100, Math.max(0, o.percentualExecutado || 0))}%`,
                          }}
                        ></div>
                      </div>
                    </div>
                  </td>

                  {/* Risco (Semáforo) */}
                  <td className="py-3 px-3 text-center whitespace-nowrap">
                    {renderSemaforoBadge(semaforoStatus, semaforoRotulo)}
                  </td>

                  {/* Ação evidente: Ver detalhes */}
                  <td className="py-3 px-3 text-right whitespace-nowrap">
                    <button
                      type="button"
                      data-testid={`btn-ver-detalhes-${o.id}`}
                      aria-label={`Ver detalhes da obra ${o.objeto}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectObra?.(o);
                      }}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
                    >
                      Ver detalhes
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Controles de Paginação */}
      {totalPages > 1 && (
        <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <span className="text-xs text-slate-500">
            Página <strong className="text-slate-800">{safeCurrentPage}</strong> de{" "}
            <span className="text-slate-700">{totalPages}</span>
          </span>
          <div className="flex gap-1.5">
            <button
              type="button"
              data-testid="btn-pagina-anterior"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={safeCurrentPage === 1}
              className="px-2.5 py-1 text-xs font-medium rounded border border-slate-200 bg-white text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100"
            >
              Anterior
            </button>
            <button
              type="button"
              data-testid="btn-proxima-pagina"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={safeCurrentPage === totalPages}
              className="px-2.5 py-1 text-xs font-medium rounded border border-slate-200 bg-white text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-100"
            >
              Próxima
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

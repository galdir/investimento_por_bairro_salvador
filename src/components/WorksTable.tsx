import React, { useMemo, useState } from "react";
import { MetricType, ObraCompacta, SemaforoStatus } from "../types";
import { formatCurrency, formatNumber } from "../utils/formatters";

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
   * Callback opcional ao clicar em uma obra para inspecionar detalhes.
   */
  onSelectObra?: (obra: ObraCompacta) => void;
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
export const WorksTable: React.FC<WorksTableProps> = ({
  obras,
  metricType,
  onSelectObra,
}) => {
  const [sortField, setSortField] = useState<SortField>("valorContratualVigente");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

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
          valA = a.valorOriginal || 0;
          valB = b.valorOriginal || 0;
          break;
        case "valorContratualVigente":
          valA = metricType === "vigente" ? a.valorContratualVigente : (a.valorPago || 0);
          valB = metricType === "vigente" ? b.valorContratualVigente : (b.valorPago || 0);
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
          valA = a.valorContratualVigente;
          valB = b.valorContratualVigente;
      }

      if (typeof valA === "string" && typeof valB === "string") {
        return sortDirection === "asc" ? valA.localeCompare(valB) : valB.localeCompare(valA);
      }
      return sortDirection === "asc" ? (valA > valB ? 1 : -1) : (valA < valB ? 1 : -1);
    });
  }, [obras, sortField, sortDirection, metricType]);

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

  if (obras.length === 0) {
    return (
      <div
        data-testid="tabela-obras-vazia"
        className="bg-white rounded-xl border border-slate-200 p-8 text-center my-4"
      >
        <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 mx-auto flex items-center justify-center mb-3">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h4 className="text-sm font-bold text-slate-800">Nenhuma obra encontrada</h4>
        <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
          Nenhum contrato corresponde aos critérios e filtros selecionados. Tente alterar o órgão, tema, semáforo ou termo de busca.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
      {/* Cabeçalho de Controle da Tabela */}
      <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-bold text-slate-800">
            Tabela Detalhada de Obras Públicas
          </h3>
          <span className="text-xs text-slate-500 bg-slate-200/80 px-2 py-0.5 rounded-full font-medium">
            {formatNumber(obras.length)} {obras.length === 1 ? "obra" : "obras"}
          </span>
        </div>

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
                  className="flex items-center hover:text-slate-900 focus:outline-none"
                >
                  Objeto da Obra
                  {renderSortIndicator("objeto")}
                </button>
              </th>
              <th className="py-3 px-3 whitespace-nowrap">
                <button
                  type="button"
                  data-testid="sort-orgao"
                  onClick={() => handleSort("unidadeGestora")}
                  className="flex items-center hover:text-slate-900 focus:outline-none"
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
                  className="flex items-center hover:text-slate-900 focus:outline-none"
                >
                  Construtora (Credor)
                  {renderSortIndicator("credor")}
                </button>
              </th>
              <th className="py-3 px-3 whitespace-nowrap">
                <button
                  type="button"
                  data-testid="sort-tema"
                  onClick={() => handleSort("tema")}
                  className="flex items-center hover:text-slate-900 focus:outline-none"
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
                  className="flex items-center justify-end w-full hover:text-slate-900 focus:outline-none"
                >
                  Valor Original
                  {renderSortIndicator("valorOriginal")}
                </button>
              </th>
              <th className="py-3 px-3 text-right whitespace-nowrap">
                <button
                  type="button"
                  data-testid="sort-valor"
                  onClick={() => handleSort("valorContratualVigente")}
                  className="flex items-center justify-end w-full hover:text-slate-900 focus:outline-none"
                >
                  {metricType === "vigente" ? "Valor Vigente (+Aditivo)" : "Valor Pago / Executado"}
                  {renderSortIndicator("valorContratualVigente")}
                </button>
              </th>
              <th className="py-3 px-3 text-center whitespace-nowrap">
                <button
                  type="button"
                  data-testid="sort-percentual"
                  onClick={() => handleSort("percentualExecutado")}
                  className="flex items-center justify-center w-full hover:text-slate-900 focus:outline-none"
                >
                  % Executado
                  {renderSortIndicator("percentualExecutado")}
                </button>
              </th>
              <th className="py-3 px-3 text-center whitespace-nowrap">
                <button
                  type="button"
                  data-testid="sort-semaforo"
                  onClick={() => handleSort("semaforo")}
                  className="flex items-center justify-center w-full hover:text-slate-900 focus:outline-none"
                >
                  Semáforo
                  {renderSortIndicator("semaforo")}
                </button>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {paginatedObras.map((o) => {
              const deltaPerc = o.deltaPercentualValor ?? 0;
              const hasAditivo = deltaPerc > 0;
              const semaforoStatus = o.semaforo?.status || "VERDE";
              const semaforoRotulo = o.semaforo?.rotulo;

              return (
                <tr
                  key={o.id}
                  data-testid={`linha-obra-${o.id}`}
                  onClick={() => onSelectObra && onSelectObra(o)}
                  className={`hover:bg-slate-50/80 transition-colors ${
                    onSelectObra ? "cursor-pointer" : ""
                  }`}
                >
                  {/* Objeto e Contrato */}
                  <td className="py-3 px-3 max-w-md">
                    <p className="font-semibold text-slate-800 line-clamp-2" title={o.objeto}>
                      {o.objeto}
                    </p>
                    <span className="text-[10px] text-slate-400 mt-0.5 block">
                      Contrato: {o.numeroContrato || "S/N"} • Situação: {o.situacao || "Não informada"}
                    </span>
                  </td>

                  {/* Órgão */}
                  <td className="py-3 px-3 whitespace-nowrap">
                    <span className="inline-block bg-slate-100 text-slate-700 font-medium px-2 py-0.5 rounded text-[11px]">
                      {o.unidadeGestora}
                    </span>
                  </td>

                  {/* Construtora */}
                  <td className="py-3 px-3 max-w-xs">
                    <p className="text-slate-700 font-medium truncate" title={o.credor}>
                      {o.credor || "Não informado"}
                    </p>
                  </td>

                  {/* Tema da Obra */}
                  <td className="py-3 px-3 whitespace-nowrap">
                    <span className="text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full text-[11px] font-medium">
                      {o.tema || "Manutenção Urbana e Outros"}
                    </span>
                  </td>

                  {/* Valor Original */}
                  <td className="py-3 px-3 text-right whitespace-nowrap text-slate-500 font-medium">
                    {formatCurrency(o.valorOriginal || o.valorContratualVigente)}
                  </td>

                  {/* Valor Vigente com Delta de Aditivo */}
                  <td className="py-3 px-3 text-right whitespace-nowrap font-bold text-slate-900">
                    <div>
                      {formatCurrency(
                        metricType === "vigente"
                          ? o.valorContratualVigente
                          : (o.valorPago ?? o.valorContratualVigente)
                      )}
                    </div>
                    {hasAditivo && (
                      <span
                        className={`text-[10px] font-semibold ${
                          deltaPerc > 25
                            ? "text-rose-600"
                            : deltaPerc >= 10
                            ? "text-amber-600"
                            : "text-emerald-600"
                        }`}
                        title={`Acréscimo de ${formatCurrency(o.valorAditivos ?? 0)}`}
                      >
                        +{deltaPerc.toFixed(1).replace(".", ",")}%
                      </span>
                    )}
                  </td>

                  {/* % Executado com Barra de Progresso */}
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

                  {/* Badge do Semáforo */}
                  <td className="py-3 px-3 text-center whitespace-nowrap">
                    {renderSemaforoBadge(semaforoStatus, semaforoRotulo)}
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

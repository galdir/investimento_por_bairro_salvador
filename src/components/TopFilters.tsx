import React from "react";
import { FilterState, SemaforoStatus } from "../types";

interface TopFiltersProps {
  /**
   * Estado atual dos filtros aplicados.
   */
  filters: FilterState;
  /**
   * Callback invocado quando qualquer filtro for modificado pelo usuário.
   */
  onFilterChange: (updated: Partial<FilterState>) => void;
  /**
   * Callback para restaurar todos os filtros para o estado padrão inicial.
   */
  onResetFilters: () => void;
  /**
   * Lista de anos disponíveis nos dados.
   */
  availableYears: number[];
  /**
   * Lista de siglas ou nomes de órgãos municipais presentes nos contratos.
   */
  availableOrgaos: string[];
  /**
   * Lista dos 6 Temas Canônicos da Obra disponíveis.
   */
  availableTemas: string[];
  /**
   * Quantidade de obras que atendem aos filtros ativos no momento.
   */
  totalObrasFiltradas: number;
  /**
   * Quantidade total de obras registradas na base.
   */
  totalObrasGeral: number;
}

/**
 * Barra superior de controles e filtros combinados do Painel de Obras de Salvador.
 *
 * @summary Fornece filtros por Ano, Órgão, Tema da Obra, Semáforo, busca textual e alternância de métrica.
 * @description Permite ao cidadão cruzar múltiplos critérios de filtragem para refinar
 * a lista de obras e recalcular em tempo real os 5 KPIs do topo. Inclui controle acessível
 * de busca textual (objeto e construtora), alternância de métrica financeira entre
 * Valor Contratual Vigente e Valor Executado/Pago, além de botão para limpar filtros ativos.
 *
 * @param props - Propriedades de estado, listas de opções e manipuladores de evento.
 * @returns Elemento JSX com os controles de filtro.
 * @throws Não lança exceções.
 */
export const TopFilters: React.FC<TopFiltersProps> = ({
  filters,
  onFilterChange,
  onResetFilters,
  availableYears,
  availableOrgaos,
  availableTemas,
  totalObrasFiltradas,
  totalObrasGeral,
}) => {
  const hasActiveFilters =
    filters.ano !== "todos" ||
    filters.orgao !== "todos" ||
    filters.tema !== "todos" ||
    filters.semaforo !== "todos" ||
    filters.busca.trim().length > 0;

  return (
    <section
      aria-label="Filtros superiores de auditoria de obras"
      className="bg-white border-b border-slate-200 px-4 sm:px-6 lg:px-8 py-3.5 shadow-sm"
    >
      <div className="max-w-7xl mx-auto flex flex-col gap-3">
        {/* Linha 1: Busca Textual e Alternância de Métrica Financeira */}
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          {/* Campo de Busca Rápida */}
          <div className="relative flex-1 max-w-xl">
            <span className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-slate-400">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </span>
            <input
              type="text"
              data-testid="filtro-busca"
              value={filters.busca}
              onChange={(e) => onFilterChange({ busca: e.target.value })}
              placeholder="Buscar por objeto da obra, palavra-chave ou empreiteira..."
              className="w-full pl-9 pr-3 py-1.5 text-xs sm:text-sm bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition-all text-slate-800 placeholder-slate-400"
            />
            {filters.busca && (
              <button
                type="button"
                onClick={() => onFilterChange({ busca: "" })}
                className="absolute inset-y-0 right-0 flex items-center pr-2.5 text-slate-400 hover:text-slate-600"
                aria-label="Limpar texto de busca"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            )}
          </div>

          {/* Toggle de Métrica Financeira (Vigente vs Executado/Pago) */}
          <div className="flex items-center gap-2 self-start md:self-auto">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider hidden sm:inline">
              Métrica Financeira:
            </span>
            <div
              data-testid="toggle-metrica-financeira"
              className="inline-flex rounded-lg p-0.5 bg-slate-100 border border-slate-200"
            >
              <button
                type="button"
                data-testid="btn-metrica-vigente"
                onClick={() => onFilterChange({ metricType: "vigente" })}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  filters.metricType === "vigente"
                    ? "bg-emerald-600 text-white shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Valor Contratual Vigente
              </button>
              <button
                type="button"
                data-testid="btn-metrica-executado"
                onClick={() => onFilterChange({ metricType: "executado" })}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  filters.metricType === "executado"
                    ? "bg-emerald-600 text-white shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Valor Executado / Pago
              </button>
            </div>
          </div>
        </div>

        {/* Linha 2: Dropdowns de Filtro Combinado (Ano, Órgão, Tema, Semáforo) e Botão Limpar */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          {/* Filtro: Ano */}
          <div className="flex items-center gap-1.5">
            <label htmlFor="filtro-ano-select" className="text-xs font-medium text-slate-500">
              Ano:
            </label>
            <select
              id="filtro-ano-select"
              data-testid="filtro-ano"
              value={filters.ano}
              onChange={(e) =>
                onFilterChange({
                  ano: e.target.value === "todos" ? "todos" : Number(e.target.value),
                })
              }
              className="text-xs bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 font-medium text-slate-700 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              <option value="todos">Todos os Anos</option>
              {availableYears.map((ano) => (
                <option key={ano} value={ano}>
                  {ano}
                </option>
              ))}
            </select>
          </div>

          {/* Filtro: Órgão / Unidade Gestora */}
          <div className="flex items-center gap-1.5">
            <label htmlFor="filtro-orgao-select" className="text-xs font-medium text-slate-500">
              Órgão:
            </label>
            <select
              id="filtro-orgao-select"
              data-testid="filtro-orgao"
              value={filters.orgao}
              onChange={(e) => onFilterChange({ orgao: e.target.value })}
              className="text-xs bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 font-medium text-slate-700 focus:outline-none focus:ring-1 focus:ring-emerald-500 max-w-[160px] truncate"
            >
              <option value="todos">Todos os Órgãos</option>
              {availableOrgaos.map((org) => (
                <option key={org} value={org}>
                  {org}
                </option>
              ))}
            </select>
          </div>

          {/* Filtro: Tema da Obra */}
          <div className="flex items-center gap-1.5">
            <label htmlFor="filtro-tema-select" className="text-xs font-medium text-slate-500">
              Tema:
            </label>
            <select
              id="filtro-tema-select"
              data-testid="filtro-tema"
              value={filters.tema}
              onChange={(e) => onFilterChange({ tema: e.target.value })}
              className="text-xs bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 font-medium text-slate-700 focus:outline-none focus:ring-1 focus:ring-emerald-500 max-w-[200px] truncate"
            >
              <option value="todos">Todos os Temas</option>
              {availableTemas.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          {/* Filtro: Semáforo da Obra */}
          <div className="flex items-center gap-1.5">
            <label htmlFor="filtro-semaforo-select" className="text-xs font-medium text-slate-500">
              Semáforo:
            </label>
            <select
              id="filtro-semaforo-select"
              data-testid="filtro-semaforo"
              value={filters.semaforo}
              onChange={(e) =>
                onFilterChange({
                  semaforo: e.target.value as SemaforoStatus | "todos",
                })
              }
              className="text-xs bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 font-medium text-slate-700 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              <option value="todos">Todas as Cores</option>
              <option value="VERDE">Verde (No Prazo)</option>
              <option value="AMARELO">Amarelo (Atenção)</option>
              <option value="VERMELHO">Vermelho (Crítica)</option>
            </select>
          </div>

          {/* Botão de Limpar Filtros */}
          {hasActiveFilters && (
            <button
              type="button"
              data-testid="btn-limpar-filtros"
              onClick={onResetFilters}
              className="text-xs font-medium text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 px-2.5 py-1.5 rounded-lg transition-colors flex items-center gap-1 ml-auto"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Limpar Filtros
            </button>
          )}

          {/* Badge de Contagem de Obras Filtradas */}
          <div
            data-testid="contador-obras-filtradas"
            className="text-xs text-slate-500 font-medium ml-auto"
          >
            Exibindo <strong className="text-slate-800">{totalObrasFiltradas}</strong> de{" "}
            <span className="text-slate-600">{totalObrasGeral}</span> obras
          </div>
        </div>
      </div>
    </section>
  );
};

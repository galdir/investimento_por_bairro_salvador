import React from "react";
import { FilterState, SemaforoStatus, VocacaoObra } from "../types";

const VOCACOES_CONFIG: Array<{
  value: VocacaoObra;
  label: string;
  testId: string;
  activeClass: string;
}> = [
    {
      value: "Vizinhança e Comunidade",
      label: "Vizinhança e Comunidade",
      testId: "chip-vocacao-vizinhanca",
      activeClass: "bg-emerald-600 text-white border-emerald-600 shadow-sm",
    },
    {
      value: "Mobilidade Estrutural e Orlas",
      label: "Mobilidade Estrutural e Orlas",
      testId: "chip-vocacao-mobilidade",
      activeClass: "bg-sky-600 text-white border-sky-600 shadow-sm",
    },
    {
      value: "Equipamentos e Marcos da Cidade",
      label: "Equipamentos e Marcos da Cidade",
      testId: "chip-vocacao-equipamentos",
      activeClass: "bg-amber-600 text-white border-amber-600 shadow-sm",
    },
  ];

interface SegmentedToggleOption<T extends string> {
  value: T;
  label: string;
  testId: string;
}

interface SegmentedToggleProps<T extends string> {
  label: string;
  groupTestId: string;
  groupAriaLabel: string;
  value: T;
  options: readonly SegmentedToggleOption<T>[];
  activeClass: string;
  onChange: (value: T) => void;
}

function SegmentedToggle<T extends string>({
  label,
  groupTestId,
  groupAriaLabel,
  value,
  options,
  activeClass,
  onChange,
}: SegmentedToggleProps<T>) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider hidden sm:inline">
        {label}:
      </span>
      <div
        data-testid={groupTestId}
        role="group"
        aria-label={groupAriaLabel}
        className="inline-flex rounded-lg p-0.5 bg-slate-100 border border-slate-200"
      >
        {options.map((option) => {
          const isActive = value === option.value;
          return (
            <button
              key={option.value}
              type="button"
              data-testid={option.testId}
              aria-pressed={isActive}
              onClick={() => onChange(option.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 ${
                isActive ? activeClass : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

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
   * Lista de mandatos municipais disponíveis nos dados (ex: ["2025-2028", "2021-2024"]).
   */
  availableMandatos?: string[];
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
  /**
   * Recorte territorial ativo ("prefeituras" ou "bairros").
   */
  activeLayer?: "bairros" | "prefeituras";
  /**
   * Callback para alternar o recorte territorial entre Prefeituras-Bairro e Bairros Oficiais.
   */
  onToggleLayer?: (layer: "bairros" | "prefeituras") => void;
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
  availableMandatos,
  availableOrgaos,
  availableTemas,
  totalObrasFiltradas,
  totalObrasGeral,
  activeLayer,
  onToggleLayer,
}) => {
  const mandatosList =
    availableMandatos && availableMandatos.length > 0
      ? availableMandatos
      : ["2025-2028", "2021-2024"];

  const vocacoesAtivas = filters.vocacoes ?? VOCACOES_CONFIG.map((v) => v.value);

  const handleToggleVocacao = (vocacao: VocacaoObra) => {
    const isSelected = vocacoesAtivas.includes(vocacao);
    if (isSelected) {
      if (vocacoesAtivas.length <= 1) {
        return;
      }
      onFilterChange({
        vocacoes: vocacoesAtivas.filter((v) => v !== vocacao),
      });
    } else {
      onFilterChange({
        vocacoes: [...vocacoesAtivas, vocacao],
      });
    }
  };

  const hasActiveFilters =
    (filters.mandato && filters.mandato !== "todos") ||
    (filters.ano && filters.ano !== "todos") ||
    filters.orgao !== "todos" ||
    filters.tema !== "todos" ||
    vocacoesAtivas.length < VOCACOES_CONFIG.length ||
    filters.semaforo !== "todos" ||
    filters.busca.trim().length > 0;

  return (
    <section
      aria-label="Filtros superiores de auditoria de obras"
      className="bg-white border-b border-slate-200 px-4 sm:px-6 py-2.5 shadow-sm shrink-0"
    >
        <div className="max-w-[1440px] mx-auto flex flex-col gap-2">
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

            {/* Toggle de Recorte Territorial + Métrica Financeira */}
            <div className="flex flex-wrap items-center gap-3 self-start md:self-auto">
              {activeLayer && onToggleLayer && (
                <SegmentedToggle
                  label="Recorte"
                  groupTestId="controle-recorte-territorial"
                  groupAriaLabel="Recorte territorial"
                  value={activeLayer}
                  options={[
                    { value: "prefeituras", label: "Prefeituras-Bairro", testId: "btn-recorte-prefeituras" },
                    { value: "bairros", label: "Bairros Oficiais", testId: "btn-recorte-bairros" },
                  ]}
                  activeClass="bg-slate-900 text-white shadow-sm"
                  onChange={onToggleLayer}
                />
              )}

              <SegmentedToggle
                label="Métrica Financeira"
                groupTestId="toggle-metrica-financeira"
                groupAriaLabel="Métrica financeira"
                value={filters.metricType}
                options={[
                  { value: "executado", label: "Valor Pago", testId: "btn-metrica-executado" },
                  { value: "vigente", label: "Valor Contratual Vigente", testId: "btn-metrica-vigente" },
                ]}
                activeClass="bg-emerald-600 text-white shadow-sm"
                onChange={(metricType) => onFilterChange({ metricType })}
              />
            </div>
          </div>

          {/* Linha 2: Chips Multi-Seleção de Vocação da Obra */}
          <div
            data-testid="filtro-vocacao-chips"
            className="flex flex-wrap items-center gap-2 pt-0.5"
          >
            <span className="text-xs font-medium text-slate-500">Vocação da Obra:</span>
            {VOCACOES_CONFIG.map((item) => {
              const isSelected = vocacoesAtivas.includes(item.value);
              return (
                <button
                  key={item.value}
                  type="button"
                  data-testid={item.testId}
                  aria-pressed={isSelected}
                  onClick={() => handleToggleVocacao(item.value)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-full border transition-all flex items-center gap-1.5 ${isSelected
                      ? item.activeClass
                      : "bg-slate-50 text-slate-500 border-slate-300 hover:bg-slate-100 hover:text-slate-700"
                    }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${isSelected ? "bg-white" : "bg-slate-300"
                      }`}
                  />
                  {item.label}
                </button>
              );
            })}
          </div>

          {/* Linha 3: Dropdowns de Filtro Combinado (Mandato, Órgão, Tema, Semáforo) e Botão Limpar */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            {/* Filtro: Mandato Municipal */}
            <div className="flex items-center gap-1.5">
              <label htmlFor="filtro-mandato-select" className="text-xs font-medium text-slate-500">
                Mandato:
              </label>
              <select
                id="filtro-mandato-select"
                data-testid="filtro-mandato"
                value={filters.mandato || "todos"}
                onChange={(e) =>
                  onFilterChange({
                    mandato: e.target.value,
                  })
                }
                className="text-xs bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 font-medium text-slate-700 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              >
                <option value="todos">Todos os Mandatos</option>
                {mandatosList.map((m) => (
                  <option key={m} value={m}>
                    {m.replace("-", "–")}
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

          {/* Nota temporal explícita sobre Mandato Municipal */}
          <p
            data-testid="explicacao-mandato"
            className="text-[11px] text-slate-600 leading-snug"
          >
            <strong className="font-semibold text-slate-700">Mandato Municipal:</strong>{" "}
            seleciona contratos cuja vigência se sobrepõe ao período; os valores exibidos são{" "}
            <strong className="font-semibold text-slate-700">acumulados do contrato</strong>, não pagamentos exclusivos daquela administração.
          </p>
        </div>
    </section>
  );
};

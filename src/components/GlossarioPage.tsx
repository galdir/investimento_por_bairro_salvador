import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  filterGlossarioVerbetes,
  GLOSSARIO_CATEGORIAS,
  GLOSSARIO_VERBETES,
  GlossarioCategoria,
} from "../data/glossario";
import { SearchInput } from "./SearchInput";

export interface GlossarioPageProps {
  /**
   * Slug do verbete alvo quando acessado via `#glossario-<slug>`.
   */
  activeSlug?: string | null;
  /**
   * Callback para retornar ao painel principal preservando estado em memória.
   */
  onBackToPanel: () => void;
  /**
   * Callback para abrir o modal da Nota Metodológica do Índice de Vulnerabilidade.
   */
  onOpenNotaMetodologica: () => void;
}

const CATEGORIA_BADGE_CLASSES: Record<GlossarioCategoria, string> = {
  "Território": "bg-sky-50 text-sky-800 border-sky-200",
  "Obras e Localização": "bg-amber-50 text-amber-800 border-amber-200",
  "Dinheiro e Execução": "bg-emerald-50 text-emerald-800 border-emerald-200",
  "Mapa e Indicadores": "bg-violet-50 text-violet-800 border-violet-200",
};

/**
 * Página dedicada de Glossário Cidadão acessível via `#glossario`.
 *
 * @summary Explica em linguagem acessível os conceitos exibidos no painel, com busca instantânea,
 * filtro por 4 categorias, âncoras compartilháveis e acesso à Nota Metodológica.
 */
export const GlossarioPage: React.FC<GlossarioPageProps> = ({
  activeSlug = null,
  onBackToPanel,
  onOpenNotaMetodologica,
}) => {
  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<GlossarioCategoria | "todas">("todas");
  const cardRefs = useRef<Record<string, HTMLElement | null>>({});

  const activeVerbete = useMemo(
    () => (activeSlug ? GLOSSARIO_VERBETES.find((v) => v.slug === activeSlug) ?? null : null),
    [activeSlug]
  );

  const hasUnknownSlug = Boolean(activeSlug && !activeVerbete);

  useEffect(() => {
    if (!activeSlug) return;
    setQuery("");
    setSelectedCategory("todas");
  }, [activeSlug]);

  const filteredVerbetes = useMemo(
    () => filterGlossarioVerbetes(GLOSSARIO_VERBETES, query, selectedCategory),
    [query, selectedCategory]
  );

  const isTargetVisible = Boolean(
    activeVerbete && filteredVerbetes.some((v) => v.slug === activeVerbete.slug)
  );

  useEffect(() => {
    if (!activeVerbete || !isTargetVisible) return;
    const targetEl = cardRefs.current[activeVerbete.slug];
    if (!targetEl) return;

    if (typeof targetEl.focus === "function") {
      try {
        targetEl.focus({ preventScroll: true });
      } catch {
        targetEl.focus();
      }
    }

    if (typeof targetEl.scrollIntoView === "function") {
      try {
        targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
      } catch { }
    }
  }, [activeVerbete, isTargetVisible]);

  return (
    <div
      data-testid="pagina-glossario"
      className="min-h-screen flex flex-col bg-slate-50 text-slate-800 font-sans"
    >
      <header className="bg-slate-900 text-white border-b border-slate-800 shadow-sm">
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-emerald-300">
              Mapa das Obras e do Dinheiro por Bairro • Salvador
            </p>
            <h1 className="text-lg sm:text-2xl font-bold tracking-tight text-white mt-0.5">
              Glossário Cidadão
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 mt-1 max-w-2xl">
              Tradução direta dos termos usados no painel para acompanhar obras públicas,
              pagamentos e vulnerabilidade social em Salvador.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <button
              type="button"
              data-testid="btn-glossario-nota-metodologica"
              onClick={onOpenNotaMetodologica}
              className="px-3 py-2 rounded-lg text-xs font-semibold bg-slate-800 text-slate-100 border border-slate-700 hover:bg-slate-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
            >
              Nota Metodológica de Vulnerabilidade
            </button>
            <button
              type="button"
              data-testid="btn-voltar-painel"
              onClick={onBackToPanel}
              className="px-3.5 py-2 rounded-lg text-xs font-bold bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-white"
            >
              ← Voltar ao Painel
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-[1200px] w-full mx-auto px-4 sm:px-6 py-6 flex flex-col gap-5">
        {/* Barra de busca e filtros por categoria */}
        <section
          aria-label="Busca e filtros do Glossário Cidadão"
          className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex flex-col gap-3"
        >
          <div className="flex flex-col md:flex-row md:items-center gap-3">
            <SearchInput
              id="glossario-busca"
              label="Buscar termo ou dúvida no Glossário Cidadão"
              testId="input-glossario-busca"
              clearTestId="btn-limpar-glossario-busca"
              clearAriaLabel="Limpar busca do glossário"
              value={query}
              onChange={setQuery}
              placeholder='Busque por termo, explicação ou dúvida (ex: "R$ 0 no meu bairro", "Frente de Medição")'
              className="flex-1"
            />
            <span
              data-testid="glossario-contador"
              className="text-xs font-medium text-slate-500 shrink-0 tabular-nums"
            >
              {filteredVerbetes.length} de {GLOSSARIO_VERBETES.length} verbetes
            </span>
          </div>

          <div
            role="group"
            aria-label="Filtrar verbetes por categoria"
            className="flex flex-wrap items-center gap-1.5"
          >
            {([
              { value: "todas" as const, label: "Todas" },
              ...GLOSSARIO_CATEGORIAS.map((categoria) => ({
                value: categoria,
                label: categoria,
              })),
            ]).map(({ value, label }) => {
              const active = selectedCategory === value;
              return (
                <button
                  key={value}
                  type="button"
                  aria-pressed={active}
                  onClick={() => setSelectedCategory(value)}
                  className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 ${
                    active
                      ? "bg-slate-900 text-white border-slate-900"
                      : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </section>

        {hasUnknownSlug && (
          <div
            role="status"
            data-testid="glossario-slug-inexistente"
            className="bg-amber-50 border border-amber-200 text-amber-900 rounded-xl px-4 py-3 text-xs sm:text-sm flex items-center justify-between gap-3"
          >
            <span>
              O termo solicitado (<code className="font-mono font-semibold">{activeSlug}</code>) não
              foi encontrado no glossário. Todos os verbetes disponíveis seguem listados abaixo.
            </span>
          </div>
        )}

        {/* Lista de verbetes */}
        {filteredVerbetes.length === 0 ? (
          <div
            data-testid="glossario-vazio"
            className="bg-white rounded-xl border border-slate-200 p-8 text-center flex flex-col items-center gap-3"
          >
            <p className="text-sm font-semibold text-slate-700">
              Nenhum verbete encontrado para &ldquo;{query}&rdquo;.
            </p>
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setSelectedCategory("todas");
              }}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
            >
              Mostrar todos os verbetes
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredVerbetes.map((verbete) => {
              const isHighlighted = activeVerbete?.slug === verbete.slug;
              return (
                <article
                  key={verbete.slug}
                  id={`glossario-${verbete.slug}`}
                  ref={(el) => {
                    cardRefs.current[verbete.slug] = el;
                  }}
                  tabIndex={isHighlighted ? -1 : undefined}
                  aria-current={isHighlighted ? "true" : undefined}
                  data-testid={`glossario-card-${verbete.slug}`}
                  className={`bg-white rounded-xl border p-5 flex flex-col gap-3 transition-shadow focus:outline-none ${
                    isHighlighted
                      ? "border-emerald-500 ring-2 ring-emerald-500/40 shadow-md"
                      : "border-slate-200 shadow-sm hover:shadow"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
                        CATEGORIA_BADGE_CLASSES[verbete.categoria]
                      }`}
                    >
                      {verbete.categoria}
                    </span>
                    <a
                      href={`#glossario-${verbete.slug}`}
                      aria-label={`Link direto para ${verbete.titulo}`}
                      className="text-[11px] font-medium text-slate-500 hover:text-emerald-700 underline decoration-slate-300 underline-offset-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 rounded px-1"
                    >
                      #glossario-{verbete.slug}
                    </a>
                  </div>

                  <div>
                    <h2 className="text-base font-bold text-slate-900 leading-snug">
                      {verbete.titulo}
                    </h2>
                    <p className="text-xs sm:text-sm font-medium text-slate-700 mt-1">
                      {verbete.resumo}
                    </p>
                  </div>

                  <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                    {verbete.explicacao}
                  </p>

                  <div className="mt-auto pt-3 border-t border-slate-100 bg-slate-50/80 -mx-5 -mb-5 px-5 py-3 rounded-b-xl">
                    <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">
                      Na prática em Salvador
                    </p>
                    <p className="text-xs text-slate-700 mt-0.5 leading-relaxed">
                      {verbete.exemploSalvador}
                    </p>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
};

import React, { useEffect, useMemo, useState } from "react";
import { FichaLimpaModal } from "./components/FichaLimpaModal";
import { HeaderKpis } from "./components/HeaderKpis";
import { InteractiveMap } from "./components/InteractiveMap";
import { PrefeiturasRanking } from "./components/PrefeiturasRanking";
import { TerritorySidebar } from "./components/TerritorySidebar";
import { TopFilters } from "./components/TopFilters";
import { WorksTable } from "./components/WorksTable";
import {
  BairroResumo,
  FichaLimpaObra,
  FilterState,
  GlobalKpis,
  IndexData,
  ObraCompacta,
  PrefeituraBairroResumo,
  TemaObra,
  TerritorySelection,
} from "./types";
import { createBairroSelection, createPrefeituraSelection } from "./utils/territory";

const TEMAS_PADRAO: TemaObra[] = [
  "Encostas e Contenção",
  "Educação e Escolas",
  "Saúde",
  "Praças, Esporte e Lazer",
  "Mobilidade, Pavimentação e Drenagem",
  "Manutenção Urbana e Outros",
];

const INITIAL_FILTERS: FilterState = {
  ano: "todos",
  orgao: "todos",
  tema: "todos",
  semaforo: "todos",
  busca: "",
  metricType: "vigente",
};

/**
 * Componente principal do Painel de Obras Públicas de Salvador.
 *
 * @summary Integra os componentes de cabeçalho (KPIs), filtros superiores, mapa coroplético, ranking e tabela detalhada.
 * @description Carrega no início da aplicação os artefatos estáticos particionados gerados pelo
 * pipeline ETL (índice anual e malhas GeoJSON de Bairros e Prefeituras-Bairro). Gerencia o estado
 * de filtragem combinada, recálculo dinâmico dos KPIs superiores (incluindo transparência opaca),
 * alternância entre as visões de Mapa, Ranking de Prefeituras-Bairro e Tabela de Obras,
 * e filtragem da tabela ao selecionar um território no mapa ou ranking.
 *
 * @returns Elemento JSX com a estrutura completa da aplicação.
 * @throws Não lança exceções; captura falhas de rede de forma amigável.
 */
export const App: React.FC = () => {
  const [indexData, setIndexData] = useState<IndexData | null>(null);
  const [bairrosGeo, setBairrosGeo] = useState<any>(null);
  const [prefeiturasGeo, setPrefeiturasGeo] = useState<any>(null);
  const [activeLayer, setActiveLayer] = useState<"bairros" | "prefeituras">("bairros");
  const [selectedTerritory, setSelectedTerritory] = useState<TerritorySelection | null>(null);
  const [selectedObraFicha, setSelectedObraFicha] = useState<FichaLimpaObra | null>(null);
  const [loadingFicha, setLoadingFicha] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"mapa" | "ranking" | "tabela">("mapa");
  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadStaticArtifacts() {
      try {
        setLoading(true);
        const basePath = import.meta.env.BASE_URL.replace(/\/$/, "");

        const [resIndex, resBairros, resPb] = await Promise.all([
          fetch(`${basePath}/data/index_2025.json`),
          fetch(`${basePath}/data/geo/bairros.geojson`),
          fetch(`${basePath}/data/geo/prefeituras_bairro.geojson`),
        ]);

        if (!resIndex.ok) throw new Error(`Falha ao carregar index_2025.json (${resIndex.status})`);
        if (!resBairros.ok) throw new Error(`Falha ao carregar bairros.geojson (${resBairros.status})`);
        if (!resPb.ok) throw new Error(`Falha ao carregar prefeituras_bairro.geojson (${resPb.status})`);

        const [dataIndex, dataBairros, dataPb] = await Promise.all([
          resIndex.json(),
          resBairros.json(),
          resPb.json(),
        ]);

        if (isMounted) {
          setIndexData(dataIndex);
          setBairrosGeo(dataBairros);
          setPrefeiturasGeo(dataPb);
          setLoading(false);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || "Erro desconhecido ao carregar dados.");
          setLoading(false);
        }
      }
    }

    loadStaticArtifacts();

    return () => {
      isMounted = false;
    };
  }, []);

  // Lista de anos disponíveis extraída dos contratos
  const availableYears = useMemo(() => {
    if (!indexData) return [2025];
    const years = new Set<number>();
    indexData.obras.forEach((o) => {
      if (o.ano) years.add(o.ano);
    });
    if (years.size === 0) years.add(indexData.metadata.anoReferencia);
    return Array.from(years).sort((a, b) => b - a);
  }, [indexData]);

  // Lista de órgãos contratantes disponíveis
  const availableOrgaos = useMemo(() => {
    if (!indexData) return [];
    const orgs = new Set<string>();
    indexData.obras.forEach((o) => {
      if (o.unidadeGestora) orgs.add(o.unidadeGestora);
    });
    return Array.from(orgs).sort();
  }, [indexData]);

  // Filtragem combinada de Obras Públicas (incluindo filtro de território selecionado)
  const filteredObras = useMemo(() => {
    if (!indexData) return [];

    return indexData.obras.filter((obra) => {
      // 1. Filtro por Território Selecionado no Mapa ou Ranking
      if (selectedTerritory) {
        if (selectedTerritory.tipo === "bairro") {
          if (obra.bairro !== selectedTerritory.nome) {
            return false;
          }
        } else if (selectedTerritory.tipo === "prefeitura_bairro") {
          const pbObra = obra.prefeituraBairro || obra.prefeitura_bairro;
          if (pbObra !== selectedTerritory.nome) {
            return false;
          }
        }
      }

      // 2. Filtro por Ano
      if (filters.ano !== "todos" && obra.ano && obra.ano !== filters.ano) {
        return false;
      }
      // 3. Filtro por Órgão
      if (filters.orgao !== "todos" && obra.unidadeGestora !== filters.orgao) {
        return false;
      }
      // 4. Filtro por Tema da Obra
      if (filters.tema !== "todos" && obra.tema !== filters.tema) {
        return false;
      }
      // 5. Filtro por cor do Semáforo da Obra
      if (filters.semaforo !== "todos" && obra.semaforo?.status !== filters.semaforo) {
        return false;
      }
      // 6. Busca textual no Objeto, Razão Social da Construtora ou CNPJ
      if (filters.busca.trim()) {
        const query = filters.busca.toLowerCase();
        const objMatch = (obra.objeto || "").toLowerCase().includes(query);
        const credorMatch = (obra.credor || "").toLowerCase().includes(query);
        const cnpjMatch = (obra.cnpj || "").toLowerCase().includes(query);
        if (!objMatch && !credorMatch && !cnpjMatch) return false;
      }
      return true;
    });
  }, [indexData, filters, selectedTerritory]);

  // Recálculo dinâmico dos KPIs superiores sob filtros e métrica ativa
  const dynamicKpis: GlobalKpis = useMemo(() => {
    if (!indexData) {
      return {
        totalObras: 0,
        valorTotal: 0,
        totalAtivas: 0,
        totalCriticas: 0,
        percentualCriticas: 0,
        totalAditivosValor: 0,
        percentualMedioAditivos: 0,
        totalEmpenhado: 0,
        totalLiquidado: 0,
        totalPago: 0,
        investimentoPorHabitanteCidade: 0,
        totalNaoLocalizado: 0,
        valorNaoLocalizado: 0,
        percentualNaoLocalizado: 0,
      };
    }

    const isFiltered =
      filters.ano !== "todos" ||
      filters.orgao !== "todos" ||
      filters.tema !== "todos" ||
      filters.semaforo !== "todos" ||
      filters.busca.trim() !== "" ||
      filters.metricType === "executado" ||
      selectedTerritory !== null;

    // População de referência para per capita
    let populacaoReferencia = indexData.bairros.reduce((acc, b) => acc + (b.populacao || 0), 0);
    if (selectedTerritory) {
      populacaoReferencia = selectedTerritory.populacao || 1;
    }

    // Se nenhum filtro estiver ativo e a métrica for a padrão contratual, usa os KPIs originais
    if (!isFiltered) {
      return indexData.kpis_globais;
    }

    let valorTotalRecalc = 0;
    let ativasRecalc = 0;
    let criticasRecalc = 0;
    let aditivosValorRecalc = 0;
    let naoLocalizadoRecalc = 0;
    let valorNaoLocalizadoRecalc = 0;
    const deltasPercentuais: number[] = [];

    const situacoesInativas = new Set(["CONCLUÍDA", "CONCLUIDA", "CANCELADA", "RESCINDIDA"]);

    for (const o of filteredObras) {
      const vl =
        filters.metricType === "vigente"
          ? o.valorContratualVigente
          : (o.valorPago ?? o.valorContratualVigente);
      valorTotalRecalc += vl;

      const sit = (o.situacao || "").toUpperCase();
      if (!situacoesInativas.has(sit)) {
        ativasRecalc++;
      }

      if (o.semaforo?.status === "VERMELHO") {
        criticasRecalc++;
      }

      if (o.valorAditivos && o.valorAditivos > 0) {
        aditivosValorRecalc += o.valorAditivos;
      }
      if (o.deltaPercentualValor !== undefined) {
        deltasPercentuais.push(o.deltaPercentualValor);
      }

      if (o.nivel === "Escopo Cidade (Não-Localizado)") {
        naoLocalizadoRecalc++;
        valorNaoLocalizadoRecalc += vl;
      }
    }

    const totalObrasRecalc = filteredObras.length;
    const percCriticas = totalObrasRecalc > 0 ? (criticasRecalc / totalObrasRecalc) * 100.0 : 0.0;
    const percMedioAditivos =
      deltasPercentuais.length > 0
        ? deltasPercentuais.reduce((a, b) => a + b, 0) / deltasPercentuais.length
        : 0.0;
    const invPorHab = populacaoReferencia > 0 ? valorTotalRecalc / populacaoReferencia : 0.0;
    const percNaoLocalizado =
      valorTotalRecalc > 0 ? (valorNaoLocalizadoRecalc / valorTotalRecalc) * 100.0 : 0.0;

    return {
      totalObras: totalObrasRecalc,
      valorTotal: valorTotalRecalc,
      totalAtivas: ativasRecalc,
      totalCriticas: criticasRecalc,
      percentualCriticas: percCriticas,
      totalAditivosValor: aditivosValorRecalc,
      percentualMedioAditivos: percMedioAditivos,
      totalEmpenhado: indexData.kpis_globais.totalEmpenhado,
      totalLiquidado: indexData.kpis_globais.totalLiquidado,
      totalPago: indexData.kpis_globais.totalPago,
      investimentoPorHabitanteCidade: invPorHab,
      totalNaoLocalizado: naoLocalizadoRecalc,
      valorNaoLocalizado: valorNaoLocalizadoRecalc,
      percentualNaoLocalizado: percNaoLocalizado,
    };
  }, [indexData, filteredObras, filters, selectedTerritory]);

  const handleFilterChange = (updated: Partial<FilterState>) => {
    setFilters((prev) => ({ ...prev, ...updated }));
  };

  const handleResetFilters = () => {
    setFilters(INITIAL_FILTERS);
    setSelectedTerritory(null);
  };

  const handleSelectPrefeituraFromRanking = (pb: PrefeituraBairroResumo) => {
    setSelectedTerritory(createPrefeituraSelection(pb));
    setActiveLayer("prefeituras");
  };

  const handleSelectObra = async (obra: ObraCompacta) => {
    try {
      setLoadingFicha(true);
      const basePath = import.meta.env.BASE_URL.replace(/\/$/, "");
      const res = await fetch(`${basePath}/data/obras/${obra.id}.json`);
      if (res.ok) {
        const data: FichaLimpaObra = await res.json();
        setSelectedObraFicha(data);
      } else {
        throw new Error(`Falha ao carregar obra ${obra.id} (status ${res.status})`);
      }
    } catch (err) {
      console.error("Erro ao carregar Ficha Limpa da Obra sob demanda:", err);
    } finally {
      setLoadingFicha(false);
    }
  };

  const handleFilterByEmpreiteira = (credorOuCnpj: string) => {
    setFilters((prev) => ({
      ...prev,
      busca: credorOuCnpj,
    }));
    setSelectedObraFicha(null);
  };

  if (loading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-slate-900 text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm font-medium text-slate-300">Carregando dados territoriais de Salvador...</p>
        </div>
      </div>
    );
  }

  if (error || !indexData) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-slate-900 text-white p-6">
        <div className="max-w-md bg-slate-800 p-6 rounded-xl border border-rose-500/30 text-center">
          <div className="w-12 h-12 rounded-full bg-rose-500/20 text-rose-400 mx-auto flex items-center justify-center mb-3">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-lg font-bold text-white">Não foi possível carregar o mapa</h2>
          <p className="text-sm text-slate-400 mt-2">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-50 font-sans">
      {/* 1. Cabeçalho com KPIs Superiores e Transparência Opaca */}
      <HeaderKpis
        kpis={dynamicKpis}
        ano={indexData.metadata.anoReferencia}
        metricType={filters.metricType}
      />

      {/* 2. Barra de Filtros Superiores Combinados */}
      <TopFilters
        filters={filters}
        onFilterChange={handleFilterChange}
        onResetFilters={handleResetFilters}
        availableYears={availableYears}
        availableOrgaos={availableOrgaos}
        availableTemas={TEMAS_PADRAO}
        totalObrasFiltradas={filteredObras.length}
        totalObrasGeral={indexData.obras.length}
      />

      {/* Indicador de Filtro Territorial Ativo */}
      {selectedTerritory && (
        <div
          data-testid="banner-territorio-filtrado"
          className="bg-emerald-50 border-b border-emerald-200 px-4 sm:px-6 py-2 flex items-center justify-between text-xs text-emerald-900"
        >
          <div className="flex items-center gap-2">
            <span className="font-bold uppercase tracking-wider text-[10px] bg-emerald-200 text-emerald-900 px-1.5 py-0.5 rounded">
              Filtro Territorial Ativo
            </span>
            <span>
              Exibindo apenas obras de: <strong>{selectedTerritory.nome}</strong> (
              {selectedTerritory.tipo === "bairro" ? "Bairro Oficial" : "Prefeitura-Bairro"})
            </span>
          </div>
          <button
            type="button"
            data-testid="btn-limpar-filtro-territorial"
            onClick={() => setSelectedTerritory(null)}
            className="text-xs font-semibold text-emerald-700 hover:text-emerald-950 underline"
          >
            Limpar filtro territorial (mostrar toda a cidade)
          </button>
        </div>
      )}

      {/* 3. Seletor de Visão Principal: Mapa vs Ranking vs Tabela */}
      <div className="bg-slate-100 border-b border-slate-200 px-4 sm:px-6 lg:px-8 py-2 flex items-center justify-between">
        <div className="flex items-center gap-1 bg-white p-1 rounded-lg border border-slate-200 shadow-sm">
          <button
            type="button"
            data-testid="tab-mapa"
            onClick={() => setActiveTab("mapa")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 ${
              activeTab === "mapa"
                ? "bg-slate-900 text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
            Mapa Territorial (Camada A)
          </button>
          <button
            type="button"
            data-testid="tab-ranking"
            onClick={() => setActiveTab("ranking")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 ${
              activeTab === "ranking"
                ? "bg-slate-900 text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            Ranking Prefeituras-Bairro
          </button>
          <button
            type="button"
            data-testid="tab-tabela"
            onClick={() => setActiveTab("tabela")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 ${
              activeTab === "tabela"
                ? "bg-slate-900 text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            Tabela Detalhada de Obras
            <span
              className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                activeTab === "tabela" ? "bg-slate-700 text-white" : "bg-slate-200 text-slate-700"
              }`}
            >
              {filteredObras.length}
            </span>
          </button>
        </div>
      </div>

      {/* 4. Área Central de Visualização */}
      <main className="flex-1 overflow-hidden relative">
        {activeTab === "mapa" && (
          <div className="h-full flex flex-col md:flex-row overflow-hidden relative">
            <InteractiveMap
              activeLayer={activeLayer}
              onToggleLayer={setActiveLayer}
              bairros={indexData.bairros}
              prefeituras={indexData.prefeituras_bairro}
              bairrosGeoJson={bairrosGeo}
              prefeiturasGeoJson={prefeiturasGeo}
              obras={filteredObras}
              selectedTerritory={selectedTerritory}
              onSelectTerritory={setSelectedTerritory}
              onSelectObra={handleSelectObra}
            />

            <TerritorySidebar
              territorio={selectedTerritory}
              onClear={() => setSelectedTerritory(null)}
              onViewWorksInTable={() => setActiveTab("tabela")}
            />
          </div>
        )}

        {activeTab === "ranking" && (
          <div className="h-full flex flex-col md:flex-row overflow-hidden relative">
            <div className="flex-1 p-4 sm:p-6 overflow-y-auto">
              <div className="max-w-4xl mx-auto">
                <PrefeiturasRanking
                  prefeituras={indexData.prefeituras_bairro}
                  bairros={indexData.bairros}
                  metricType={filters.metricType}
                  selectedNome={selectedTerritory?.nome}
                  onSelectPrefeitura={handleSelectPrefeituraFromRanking}
                  onSelectBairro={(b: BairroResumo) => setSelectedTerritory(createBairroSelection(b))}
                />
              </div>
            </div>

            <TerritorySidebar
              territorio={selectedTerritory}
              onClear={() => setSelectedTerritory(null)}
              onViewWorksInTable={() => setActiveTab("tabela")}
            />
          </div>
        )}

        {activeTab === "tabela" && (
          <div className="h-full p-4 sm:p-6 overflow-y-auto">
            <div className="max-w-7xl mx-auto">
              <WorksTable
                obras={filteredObras}
                metricType={filters.metricType}
                onSelectObra={handleSelectObra}
              />
            </div>
          </div>
        )}
      </main>

      {/* 5. Ficha Limpa da Obra sob demanda (Camada C) */}
      <FichaLimpaModal
        obra={selectedObraFicha}
        loading={loadingFicha}
        onClose={() => setSelectedObraFicha(null)}
        onFilterByEmpreiteira={handleFilterByEmpreiteira}
      />
    </div>
  );
};

export default App;

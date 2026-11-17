import React, { useEffect, useMemo, useState } from "react";
import { FichaLimpaModal } from "./components/FichaLimpaModal";
import { HeaderKpis } from "./components/HeaderKpis";
import { InteractiveMap } from "./components/InteractiveMap";
import { NotaMetodologicaModal } from "./components/NotaMetodologicaModal";
import {
  TerritoryComparisonList,
  VulnerabilitySortDirection,
} from "./components/TerritoryComparisonList";
import { TerritorySidebar } from "./components/TerritorySidebar";
import { TopFilters } from "./components/TopFilters";
import { WorksTable } from "./components/WorksTable";
import {
  FichaLimpaObra,
  FilterState,
  GlobalKpis,
  IndexData,
  ObraCompacta,
  TemaObra,
  TerritorySelection,
  VOCACOES_PADRAO,
  VocacaoObra,
} from "./types";
import {
  calculateTerritorialRollup,
  createBairroSelection,
  createPrefeituraSelection,
  deduplicateObrasByCanonicalKey,
  getObraCotasListaFechada,
  hasNumericPayment,
  isTerritoryCompatibleWithLayer,
  normalizeName,
  obraMatchesTerritory,
  obraOverlapsMandato,
} from "./utils/territory";

const TEMAS_PADRAO: TemaObra[] = [
  "Encostas e Contenção",
  "Educação e Escolas",
  "Saúde",
  "Praças, Esporte e Lazer",
  "Mobilidade, Pavimentação e Drenagem",
  "Manutenção Urbana e Outros",
];

const INITIAL_FILTERS: FilterState = {
  mandato: "todos",
  ano: "todos",
  orgao: "todos",
  tema: "todos",
  vocacoes: VOCACOES_PADRAO,
  semaforo: "todos",
  busca: "",
  metricType: "executado",
};

/**
 * Constrói a URL completa para um artefato estático respeitando o subcaminho base do GitHub Pages.
 *
 * @summary Resolve o caminho de arquivos em `data/` combinando `BASE_URL` do Vite com o caminho relativo.
 * @description Garante que o carregamento de `index_<ano>.json`, `geo/*.geojson` e `obras/<id>.json`
 * funcione tanto na raiz em desenvolvimento quanto sob o subcaminho `/investimento_por_bairro_salvador/`
 * quando publicado no GitHub Pages, evitando barras duplicadas.
 *
 * @param relativePath - Caminho relativo dentro da pasta pública (ex: `'data/index_2025.json'`).
 * @param baseUrl - Caminho base configurado no build (padrão: `import.meta.env.BASE_URL`).
 * @returns String com a URL normalizada pronta para chamada `fetch`.
 * @throws Não lança exceções.
 */
export function buildDataUrl(
  relativePath: string,
  baseUrl: string = import.meta.env.BASE_URL
): string {
  const cleanBase = (baseUrl || "/").replace(/\/+$/, "");
  const cleanRelative = relativePath.replace(/^\/+/, "");
  return `${cleanBase}/${cleanRelative}`;
}

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
  const [activeLayer, setActiveLayer] = useState<"bairros" | "prefeituras">("prefeituras");
  const [selectedTerritory, setSelectedTerritory] = useState<TerritorySelection | null>(null);
  const [selectedObraFicha, setSelectedObraFicha] = useState<FichaLimpaObra | null>(null);
  const [loadingFicha, setLoadingFicha] = useState<boolean>(false);
  const [showNotaMetodologica, setShowNotaMetodologica] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"comparacao" | "tabela">("comparacao");
  const [sortDirection, setSortDirection] = useState<VulnerabilitySortDirection>("asc");
  const [territorySearch, setTerritorySearch] = useState<string>("");
  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadStaticArtifacts() {
      try {
        setLoading(true);

        const [resIndex, resBairros, resPb] = await Promise.all([
          fetch(buildDataUrl("data/index_2025.json")),
          fetch(buildDataUrl("data/geo/bairros.geojson")),
          fetch(buildDataUrl("data/geo/prefeituras_bairro.geojson")),
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

  // Lista de Mandatos Municipais disponíveis
  const availableMandatos = useMemo(() => {
    if (!indexData) return ["2025-2028", "2021-2024"];
    if (indexData.metadata.mandatosDisponiveis && indexData.metadata.mandatosDisponiveis.length > 0) {
      return indexData.metadata.mandatosDisponiveis;
    }
    const mandatosSet = new Set<string>();
    indexData.obras.forEach((o) => {
      (o.mandatos || []).forEach((m) => mandatosSet.add(m));
    });
    if (mandatosSet.size === 0) {
      return ["2025-2028", "2021-2024"];
    }
    return Array.from(mandatosSet).sort().reverse();
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

  // 1. Filtragem das Obras Públicas exclusivamente pelos filtros superiores da tela (Camada A / Top Filters)
  const topFilteredObras = useMemo(() => {
    if (!indexData) return [];

    return indexData.obras.filter((obra) => {
      // Filtro por Mandato Municipal (sobreposição de vigência)
      if (!obraOverlapsMandato(obra, filters.mandato)) {
        return false;
      }

      // Filtro por Ano (compatibilidade)
      if (filters.ano && filters.ano !== "todos" && obra.ano && obra.ano !== filters.ano) {
        return false;
      }
      // Filtro por Órgão
      if (filters.orgao !== "todos" && obra.unidadeGestora !== filters.orgao) {
        return false;
      }
      // Filtro por Tema da Obra
      if (filters.tema !== "todos" && obra.tema !== filters.tema) {
        return false;
      }
      // Filtro multi-seleção por Vocação da Obra (fallback conservador para Vizinhança e Comunidade)
      if (filters.vocacoes.length < VOCACOES_PADRAO.length) {
        const vocacaoObra = (obra.vocacao as VocacaoObra) || "Vizinhança e Comunidade";
        if (!filters.vocacoes.includes(vocacaoObra)) {
          return false;
        }
      }
      // Filtro por cor do Semáforo da Obra
      if (filters.semaforo !== "todos" && obra.semaforo?.status !== filters.semaforo) {
        return false;
      }
      // Busca textual no Objeto, Razão Social da Construtora ou CNPJ
      if (filters.busca.trim()) {
        const query = filters.busca.toLowerCase();
        const objMatch = (obra.objeto || "").toLowerCase().includes(query);
        const credorMatch = (obra.credor || "").toLowerCase().includes(query);
        const cnpjMatch = (obra.cnpj || "").toLowerCase().includes(query);
        if (!objMatch && !credorMatch && !cnpjMatch) return false;
      }
      return true;
    });
  }, [indexData, filters]);

  // 2. Recálculo dinâmico da Camada A (Bairros e Prefeituras-Bairro) a partir de topFilteredObras
  const isContractFiltered =
    (filters.mandato && filters.mandato !== "todos") ||
    (filters.ano && filters.ano !== "todos") ||
    filters.orgao !== "todos" ||
    filters.tema !== "todos" ||
    filters.vocacoes.length < VOCACOES_PADRAO.length ||
    filters.semaforo !== "todos" ||
    filters.busca.trim() !== "";

  const usesPrecomputedSummary = Boolean(
    indexData &&
      !isContractFiltered &&
      (indexData.kpis_globais?.totalObras ?? 0) > indexData.obras.length
  );

  const { bairros: recalculatedBairros, prefeituras: recalculatedPrefeituras } = useMemo(() => {
    if (!indexData) {
      return { bairros: [], prefeituras: [] };
    }
    const rollup = calculateTerritorialRollup(
      indexData.bairros,
      indexData.prefeituras_bairro,
      topFilteredObras
    );

    if (usesPrecomputedSummary) {
      const rollupPbByName = new Map(
        rollup.prefeituras.map((pb) => [normalizeName(pb.nome), pb])
      );
      const rollupBairroByName = new Map(
        rollup.bairros.map((b) => [normalizeName(b.nome), b])
      );
      const resolvePrecomputedPaymentDisponivel = (
        valorPago: number | null | undefined,
        totalObras: number | undefined,
        rollupEntry?: { valorPagoDisponivel?: boolean; totalObras?: number }
      ) => {
        if (valorPago === null) return false;
        if (hasNumericPayment(valorPago)) return true;
        if ((totalObras ?? 0) === 0) return true;
        return (rollupEntry?.totalObras ?? 0) > 0 ? rollupEntry?.valorPagoDisponivel : false;
      };
      return {
        bairros: indexData.bairros.map((b) => {
          const rb = rollupBairroByName.get(normalizeName(b.nome));
          return {
            ...b,
            valorPagoDisponivel: resolvePrecomputedPaymentDisponivel(
              b.valorPago,
              b.totalObras,
              rb
            ),
          };
        }),
        prefeituras: indexData.prefeituras_bairro.map((pb) => {
          const rpb = rollupPbByName.get(normalizeName(pb.nome));
          return {
            ...pb,
            indice_vulnerabilidade: pb.indice_vulnerabilidade ?? rpb?.indice_vulnerabilidade,
            vulnerabilidade_estimada_contiguidade:
              pb.vulnerabilidade_estimada_contiguidade ??
              rpb?.vulnerabilidade_estimada_contiguidade ??
              false,
            bairros_vulnerabilidade_estimada:
              pb.bairros_vulnerabilidade_estimada ??
              rpb?.bairros_vulnerabilidade_estimada ??
              [],
            valorPagoDisponivel: resolvePrecomputedPaymentDisponivel(
              pb.valorPago,
              pb.totalObras,
              rpb
            ),
          };
        }),
      };
    }

    return rollup;
  }, [indexData, topFilteredObras, usesPrecomputedSummary]);

  // 3. Sincronização reativa do território selecionado com o rollup recalculado sob os filtros ativos
  const activeSelectedTerritory = useMemo<TerritorySelection | null>(() => {
    if (!selectedTerritory) return null;
    if (selectedTerritory.tipo === "bairro") {
      const b = recalculatedBairros.find(
        (item) => item.nome === selectedTerritory.nome || item.id === selectedTerritory.id
      );
      if (b) {
        return createBairroSelection(b);
      }
    } else {
      const pb = recalculatedPrefeituras.find(
        (item) => item.nome === selectedTerritory.nome || item.id === selectedTerritory.id
      );
      if (pb) {
        return createPrefeituraSelection(pb);
      }
    }
    return selectedTerritory;
  }, [selectedTerritory, recalculatedBairros, recalculatedPrefeituras]);

  // 4. Filtragem combinada para pinos no mapa e linhas da tabela (aplicando filtro de território selecionado)
  const filteredObras = useMemo(() => {
    if (!activeSelectedTerritory) return topFilteredObras;

    return topFilteredObras.filter((obra) =>
      obraMatchesTerritory(obra, activeSelectedTerritory)
    );
  }, [topFilteredObras, activeSelectedTerritory]);

  // 5. Indicadores comparativos municipais do cabeçalho (NUNCA restringidos pelo território selecionado)
  const headerComparisonSummary = useMemo(() => {
    if (!indexData) {
      return {
        kpis: {
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
          valorPagoNaoLocalizado: 0,
          percentualNaoLocalizado: 0,
        } as GlobalKpis,
        territorioCount: 0,
        valorAlocadoTerritorial: 0,
        valorAlocadoDisponivel: true,
        totalObrasAlocadas: 0,
        contratosPrefeituraBairroSemRateioCount: 0,
        isExactLayerWorkCount: true,
      };
    }

    const isVigente = filters.metricType === "vigente";
    const territoriesScope =
      activeLayer === "prefeituras" ? recalculatedPrefeituras : recalculatedBairros;
    const territorioCount = territoriesScope.length;

    let valorAlocadoTerritorial = 0;
    let territoriesWithPaymentData = 0;
    let territoriesWithWorks = 0;

    for (const t of territoriesScope) {
      const hasWorks = (t.totalObras ?? 0) > 0 || (t.totalFrentesMedicao ?? 0) > 0;
      if (hasWorks) territoriesWithWorks++;
      if (isVigente) {
        valorAlocadoTerritorial += t.valorTotal ?? 0;
      } else if (t.valorPagoDisponivel !== false && hasNumericPayment(t.valorPago)) {
        valorAlocadoTerritorial += t.valorPago;
        if (hasWorks) territoriesWithPaymentData++;
      }
    }

    const valorAlocadoDisponivel =
      isVigente || territoriesWithWorks === 0 || territoriesWithPaymentData > 0;

    const populacaoCidade =
      recalculatedBairros.reduce((acc, b) => acc + (b.populacao || 0), 0) ||
      recalculatedPrefeituras.reduce((acc, pb) => acc + (pb.populacao_total || 0), 0);

    if (usesPrecomputedSummary) {
      const k = indexData.kpis_globais;
      const totalNaoLoc = k.totalNaoLocalizado ?? 0;
      const totalAlocadas = Math.max(0, (k.totalObras ?? 0) - totalNaoLoc);
      const naoLocalizadoAtivo = isVigente
        ? (k.valorNaoLocalizado ?? 0)
        : hasNumericPayment(k.valorPagoNaoLocalizado)
          ? k.valorPagoNaoLocalizado
          : 0;
      const basePercentual = valorAlocadoTerritorial + naoLocalizadoAtivo;
      const percNaoLoc = isVigente
        ? k.percentualNaoLocalizado
        : basePercentual > 0
          ? (naoLocalizadoAtivo / basePercentual) * 100.0
          : 0.0;
      return {
        kpis: {
          ...k,
          percentualNaoLocalizado: percNaoLoc,
          investimentoPorHabitanteCidade:
            populacaoCidade > 0 ? valorAlocadoTerritorial / populacaoCidade : 0,
        },
        territorioCount,
        valorAlocadoTerritorial,
        valorAlocadoDisponivel,
        totalObrasAlocadas: totalAlocadas,
        contratosPrefeituraBairroSemRateioCount: 0,
        isExactLayerWorkCount: false,
      };
    }

    let valorTotalCarteira = 0;
    let ativasRecalc = 0;
    let criticasRecalc = 0;
    let aditivosValorRecalc = 0;
    let naoLocalizadoRecalc = 0;
    let contratosPrefeituraBairroSemRateioCount = 0;
    let valorNaoLocalizadoVigente = 0;
    let valorNaoLocalizadoPago = 0;
    let naoLocalizadoComPago = 0;
    const deltasPercentuais: number[] = [];
    const situacoesInativas = new Set(["CONCLUÍDA", "CONCLUIDA", "CANCELADA", "RESCINDIDA"]);

    const uniqueFilteredObras = deduplicateObrasByCanonicalKey(topFilteredObras);

    for (const o of uniqueFilteredObras) {
      const vlBase = isVigente
        ? (o.valorContratualVigente ?? 0)
        : hasNumericPayment(o.valorPago)
          ? o.valorPago
          : 0;
      valorTotalCarteira += vlBase;

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
        valorNaoLocalizadoVigente += o.valorContratualVigente ?? 0;
        if (hasNumericPayment(o.valorPago)) {
          naoLocalizadoComPago++;
          const pagoFrentes = (o.frentesMedicao || []).reduce(
            (acc, f) => acc + (hasNumericPayment(f.valorPago) ? f.valorPago : 0),
            0
          );
          valorNaoLocalizadoPago += Math.max(0, o.valorPago - pagoFrentes);
        }
      } else if (
        getObraCotasListaFechada(o).length === 0 &&
        o.nivel === "Regional (Prefeitura-Bairro)" &&
        Boolean(o.prefeituraBairro || o.prefeitura_bairro)
      ) {
        contratosPrefeituraBairroSemRateioCount++;
      }
    }

    const totalObrasRecalc = uniqueFilteredObras.length;
    const totalObrasAlocadas =
      activeLayer === "bairros"
        ? Math.max(0, totalObrasRecalc - naoLocalizadoRecalc - contratosPrefeituraBairroSemRateioCount)
        : totalObrasRecalc - naoLocalizadoRecalc;
    const valorNaoLocalizadoAtivo = isVigente
      ? valorNaoLocalizadoVigente
      : valorNaoLocalizadoPago;
    const basePercentualNaoLocalizado = valorAlocadoTerritorial + valorNaoLocalizadoAtivo;
    const percNaoLocalizado =
      basePercentualNaoLocalizado > 0
        ? (valorNaoLocalizadoAtivo / basePercentualNaoLocalizado) * 100.0
        : 0.0;

    return {
      kpis: {
        totalObras: totalObrasRecalc,
        valorTotal: valorTotalCarteira,
        totalAtivas: ativasRecalc,
        totalCriticas: criticasRecalc,
        percentualCriticas:
          totalObrasRecalc > 0 ? (criticasRecalc / totalObrasRecalc) * 100.0 : 0.0,
        totalAditivosValor: aditivosValorRecalc,
        percentualMedioAditivos:
          deltasPercentuais.length > 0
            ? deltasPercentuais.reduce((a, b) => a + b, 0) / deltasPercentuais.length
            : 0.0,
        totalEmpenhado: indexData.kpis_globais.totalEmpenhado,
        totalLiquidado: indexData.kpis_globais.totalLiquidado,
        totalPago: indexData.kpis_globais.totalPago,
        investimentoPorHabitanteCidade:
          populacaoCidade > 0 ? valorAlocadoTerritorial / populacaoCidade : 0.0,
        totalNaoLocalizado: naoLocalizadoRecalc,
        valorNaoLocalizado: valorNaoLocalizadoVigente,
        valorPagoNaoLocalizado:
          naoLocalizadoRecalc === 0 || naoLocalizadoComPago > 0
            ? valorNaoLocalizadoPago
            : undefined,
        percentualNaoLocalizado: percNaoLocalizado,
      } as GlobalKpis,
      territorioCount,
      valorAlocadoTerritorial,
      valorAlocadoDisponivel,
      totalObrasAlocadas,
      contratosPrefeituraBairroSemRateioCount,
      isExactLayerWorkCount: true,
    };
  }, [
    indexData,
    topFilteredObras,
    recalculatedBairros,
    recalculatedPrefeituras,
    activeLayer,
    filters.metricType,
    usesPrecomputedSummary,
  ]);

  const handleFilterChange = (updated: Partial<FilterState>) => {
    setFilters((prev) => ({ ...prev, ...updated }));
  };

  const handleResetFilters = () => {
    setFilters(INITIAL_FILTERS);
    setSelectedTerritory(null);
  };

  const handleClearContractFilters = () => {
    setFilters((prev) => ({
      ...INITIAL_FILTERS,
      metricType: prev.metricType,
    }));
  };

  const handleToggleLayer = (layer: "bairros" | "prefeituras") => {
    if (layer !== activeLayer) {
      setActiveLayer(layer);
      // Ao alternar entre Bairros Oficiais e Prefeituras-Bairro,
      // qualquer seleção territorial incompatível com a nova camada é limpa
      if (!isTerritoryCompatibleWithLayer(selectedTerritory, layer)) {
        setSelectedTerritory(null);
      }
    }
  };

  const handleSelectObra = async (obra: ObraCompacta) => {
    try {
      setLoadingFicha(true);
      const res = await fetch(buildDataUrl(`data/obras/${obra.id}.json`));
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
    <div className="flex flex-col min-h-screen w-full bg-slate-50 font-sans">
      {/* 1. Cabeçalho compacto com escopo comparativo municipal */}
      <HeaderKpis
        kpis={headerComparisonSummary.kpis}
        activeLayer={activeLayer}
        territorioCount={headerComparisonSummary.territorioCount}
        valorAlocadoTerritorial={headerComparisonSummary.valorAlocadoTerritorial}
        valorAlocadoDisponivel={headerComparisonSummary.valorAlocadoDisponivel}
        totalObrasAlocadas={headerComparisonSummary.totalObrasAlocadas}
        contratosPrefeituraBairroSemRateioCount={
          headerComparisonSummary.contratosPrefeituraBairroSemRateioCount
        }
        isExactLayerWorkCount={headerComparisonSummary.isExactLayerWorkCount}
        generatedAt={indexData.metadata.generatedAt}
        metricType={filters.metricType}
        mandato={filters.mandato}
      />

      {/* 2. Barra de Filtros Superiores Combinados */}
      <TopFilters
        filters={filters}
        onFilterChange={handleFilterChange}
        onResetFilters={handleResetFilters}
        availableMandatos={availableMandatos}
        availableOrgaos={availableOrgaos}
        availableTemas={TEMAS_PADRAO}
        totalObrasFiltradas={filteredObras.length}
        totalObrasGeral={indexData.obras.length}
        activeLayer={activeLayer}
        onToggleLayer={handleToggleLayer}
      />

      {/* Indicador de Seleção Territorial Ativa para Consulta de Obras */}
      {activeSelectedTerritory && (
        <div
          data-testid="banner-territorio-filtrado"
          className="bg-emerald-50 border-b border-emerald-200 px-4 sm:px-6 py-1.5 flex flex-wrap items-center justify-between gap-2 text-xs text-emerald-900"
        >
          <div className="flex items-center gap-2">
            <span className="font-bold uppercase tracking-wider text-[10px] bg-emerald-200 text-emerald-900 px-1.5 py-0.5 rounded">
              Território selecionado
            </span>
            <span>
              <strong>{activeSelectedTerritory.nome}</strong> (
              {activeSelectedTerritory.tipo === "bairro" ? "Bairro Oficial" : "Prefeitura-Bairro"})
              {activeTab === "comparacao"
                ? " — comparação municipal preservada; resumo abaixo do mapa"
                : " — exibindo apenas obras deste território"}
            </span>
          </div>
          <button
            type="button"
            data-testid="btn-limpar-filtro-territorial"
            onClick={() => setSelectedTerritory(null)}
            className="text-xs font-semibold text-emerald-800 hover:text-emerald-950 underline"
          >
            Limpar seleção
          </button>
        </div>
      )}

      {/* 3. Seletor de Visão: Comparação Territorial vs Tabela de Obras */}
      <div className="bg-slate-100 border-b border-slate-200 px-4 sm:px-6 py-2 flex items-center justify-between">
        <div className="flex items-center gap-1 bg-white p-1 rounded-lg border border-slate-200 shadow-sm">
          <button
            type="button"
            data-testid="tab-comparacao"
            onClick={() => setActiveTab("comparacao")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 ${
              activeTab === "comparacao"
                ? "bg-slate-900 text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Comparação Territorial
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
            Tabela de Obras
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
      <main className="flex-1">
        {activeTab === "comparacao" && (
          <div className="max-w-[1440px] w-full mx-auto px-4 sm:px-6 py-4 flex flex-col md:flex-row items-start gap-4">
            {/* Esquerda (~45%): Lista de Comparação Territorial ordenada por vulnerabilidade */}
            <div className="w-full md:w-[45%] min-w-0 md:h-[calc(100vh-14rem)] md:min-h-[480px] md:max-h-[760px]">
              <TerritoryComparisonList
                activeLayer={activeLayer}
                prefeituras={recalculatedPrefeituras}
                bairros={recalculatedBairros}
                metricType={filters.metricType}
                sortDirection={sortDirection}
                onToggleSortDirection={() =>
                  setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"))
                }
                territorySearch={territorySearch}
                onTerritorySearchChange={setTerritorySearch}
                hasEmptyContractFilter={isContractFiltered && topFilteredObras.length === 0}
                onClearContractFilters={handleClearContractFilters}
                selectedTerritory={activeSelectedTerritory}
                onSelectTerritory={setSelectedTerritory}
                onOpenNotaMetodologica={() => setShowNotaMetodologica(true)}
              />
            </div>

            {/* Direita (~55%): Mapa ao lado e Resumo do selecionado abaixo do mapa */}
            <div className="w-full md:w-[55%] min-w-0 flex flex-col gap-3">
              <div className="h-[440px] sm:h-[480px] lg:h-[520px] min-w-0 overflow-hidden rounded-xl border border-slate-200 shadow-sm flex flex-col">
                <InteractiveMap
                  activeLayer={activeLayer}
                  onToggleLayer={handleToggleLayer}
                  bairros={recalculatedBairros}
                  prefeituras={recalculatedPrefeituras}
                  bairrosGeoJson={bairrosGeo}
                  prefeiturasGeoJson={prefeiturasGeo}
                  obras={filteredObras}
                  selectedTerritory={activeSelectedTerritory}
                  onSelectTerritory={setSelectedTerritory}
                  onSelectObra={handleSelectObra}
                  metricType={filters.metricType}
                  territorySearch={territorySearch}
                  onOpenNotaMetodologica={() => setShowNotaMetodologica(true)}
                />
              </div>

              {activeSelectedTerritory && (
                <TerritorySidebar
                  territorio={activeSelectedTerritory}
                  onClear={() => setSelectedTerritory(null)}
                  onViewWorksInTable={() => setActiveTab("tabela")}
                  metricType={filters.metricType}
                  onOpenNotaMetodologica={() => setShowNotaMetodologica(true)}
                  obras={topFilteredObras}
                  onSelectObra={handleSelectObra}
                  onSwitchToExecutado={() => handleFilterChange({ metricType: "executado" })}
                />
              )}
            </div>
          </div>
        )}

        {activeTab === "tabela" && (
          <div className="max-w-[1440px] mx-auto p-4 sm:p-6">
            <div className="mb-3">
              <button
                type="button"
                data-testid="btn-voltar-comparacao"
                onClick={() => setActiveTab("comparacao")}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-slate-300 text-slate-700 hover:bg-slate-100 transition-colors"
              >
                ← Voltar à Comparação Territorial
              </button>
            </div>
            <WorksTable
              obras={filteredObras}
              metricType={filters.metricType}
              selectedTerritory={activeSelectedTerritory}
              onSelectObra={handleSelectObra}
              busca={filters.busca}
              onBuscaChange={(busca) => handleFilterChange({ busca })}
              hasActiveContractFilters={isContractFiltered}
              onClearContractFilters={handleClearContractFilters}
            />
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

      {/* 6. Modal de Nota Metodológica — Índice de Vulnerabilidade */}
      <NotaMetodologicaModal
        isOpen={showNotaMetodologica}
        onClose={() => setShowNotaMetodologica(false)}
      />
    </div>
  );
};

export default App;

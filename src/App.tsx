import React, { useEffect, useMemo, useRef, useState } from "react";
import { FichaLimpaModal } from "./components/FichaLimpaModal";
import { HeaderKpis } from "./components/HeaderKpis";
import { InteractiveMap } from "./components/InteractiveMap";
import { NotaMetodologicaModal } from "./components/NotaMetodologicaModal";
import { FALLBACK_MANDATOS, ordenarMandatosDecrescente } from "./utils/mandatos";
import {
  ComparisonSortColumn,
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
  limitacoesDaObra,
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

const RECARREGAR_VERSAO_RETIRADA =
  "A versão do painel não está mais disponível. Recarregue a página para continuar com os dados atuais.";

async function versaoFoiRetirada(versao: string | undefined): Promise<boolean> {
  if (!versao || !/^[0-9a-f]{32}$/.test(versao)) return false;

  try {
    const resposta = await fetch(buildDataUrl("data/versoes-servidas.json"), {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!resposta.ok) return false;

    const lista = await resposta.json();
    if (!Array.isArray(lista?.versoesDados)
      || lista.versoesDados.some((item: unknown) => typeof item !== "string" || !/^[0-9a-f]{32}$/.test(item))) {
      return false;
    }
    return !lista.versoesDados.includes(versao);
  } catch {
    return false;
  }
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
const MOBILE_MEDIA_QUERY = "(max-width: 767px)";

function getMobileMediaQueryList(): MediaQueryList | null {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return null;
  }
  return window.matchMedia(MOBILE_MEDIA_QUERY);
}

function checkIsMobileViewport(): boolean {
  if (typeof window === "undefined") return false;
  const mql = getMobileMediaQueryList();
  if (mql && typeof mql.matches === "boolean") {
    return mql.matches;
  }
  return window.innerWidth < 768;
}

function safeWindowScrollTo(top: number): void {
  if (typeof window !== "undefined" && typeof window.scrollTo === "function") {
    try {
      window.scrollTo({ top, behavior: "auto" });
    } catch { }
  }
}

export const App: React.FC = () => {
  const [indexData, setIndexData] = useState<IndexData | null>(null);
  const [dataBase, setDataBase] = useState("data");
  const [bairrosGeo, setBairrosGeo] = useState<any>(null);
  const [prefeiturasGeo, setPrefeiturasGeo] = useState<any>(null);
  const [activeLayer, setActiveLayer] = useState<"bairros" | "prefeituras">("prefeituras");
  const [selectedTerritory, setSelectedTerritory] = useState<TerritorySelection | null>(null);
  const [isDrawerCollapsed, setIsDrawerCollapsed] = useState<boolean>(false);
  const [selectedObraFicha, setSelectedObraFicha] = useState<FichaLimpaObra | null>(null);
  const [loadingFicha, setLoadingFicha] = useState<boolean>(false);
  const [fichaError, setFichaError] = useState<string | null>(null);
  const [lastRequestedObra, setLastRequestedObra] = useState<ObraCompacta | null>(null);
  const [showNotaMetodologica, setShowNotaMetodologica] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"comparacao" | "tabela">("comparacao");
  const comparacaoScrollYRef = useRef<number>(0);
  const pendingRestoreComparacaoScrollRef = useRef<boolean>(false);
  const lastFichaTriggerRef = useRef<HTMLElement | null>(null);
  const fichaRequestRef = useRef(0);
  const [isMobileViewport, setIsMobileViewport] = useState<boolean>(() => checkIsMobileViewport());
  const [mobileView, setMobileView] = useState<"lista" | "mapa">("lista");
  const mobileToggleRef = useRef<HTMLDivElement>(null);
  const mobileListaScrollYRef = useRef<number>(0);
  const mobileSelectionChangedInMapRef = useRef<boolean>(false);
  const pendingRestoreMobileScrollRef = useRef<boolean>(false);
  const pendingFocusMobileMapRef = useRef<boolean>(false);
  const [sortColumn, setSortColumn] = useState<ComparisonSortColumn>("vulnerabilidade");
  const [sortDirection, setSortDirection] = useState<VulnerabilitySortDirection>("asc");
  const [territorySearch, setTerritorySearch] = useState<string>("");
  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const updateViewport = () => setIsMobileViewport(checkIsMobileViewport());
    updateViewport();

    const mql = getMobileMediaQueryList();
    if (mql && typeof mql.addEventListener === "function") {
      mql.addEventListener("change", updateViewport);
    }
    window.addEventListener("resize", updateViewport);

    return () => {
      if (mql && typeof mql.removeEventListener === "function") {
        mql.removeEventListener("change", updateViewport);
      }
      window.removeEventListener("resize", updateViewport);
    };
  }, []);

  useEffect(() => {
    if (!isMobileViewport) return;

    if (mobileView === "lista" && pendingRestoreMobileScrollRef.current) {
      pendingRestoreMobileScrollRef.current = false;
      if (!mobileSelectionChangedInMapRef.current) {
        safeWindowScrollTo(mobileListaScrollYRef.current);
      }
      mobileSelectionChangedInMapRef.current = false;
    } else if (mobileView === "mapa" && pendingFocusMobileMapRef.current) {
      pendingFocusMobileMapRef.current = false;
      const toggleEl = mobileToggleRef.current;
      if (toggleEl && typeof toggleEl.getBoundingClientRect === "function") {
        const rect = toggleEl.getBoundingClientRect();
        if (rect.top < 0 && typeof toggleEl.scrollIntoView === "function") {
          toggleEl.scrollIntoView({ block: "start", behavior: "auto" });
        }
      }
    }
  }, [isMobileViewport, mobileView]);

  useEffect(() => {
    if (activeTab === "comparacao" && pendingRestoreComparacaoScrollRef.current) {
      pendingRestoreComparacaoScrollRef.current = false;
      safeWindowScrollTo(comparacaoScrollYRef.current);
    }
  }, [activeTab]);

  const handleOpenTabela = () => {
    if (activeTab === "tabela") return;
    comparacaoScrollYRef.current = window.scrollY || 0;
    setActiveTab("tabela");
    safeWindowScrollTo(0);
  };

  const handleBackToComparacao = () => {
    if (activeTab === "comparacao") return;
    pendingRestoreComparacaoScrollRef.current = true;
    setActiveTab("comparacao");
  };

  const handleMobileViewChange = (nextView: "lista" | "mapa") => {
    if (nextView === mobileView) return;
    if (mobileView === "lista" && nextView === "mapa") {
      mobileListaScrollYRef.current = window.scrollY || 0;
      mobileSelectionChangedInMapRef.current = false;
      pendingFocusMobileMapRef.current = true;
    } else if (mobileView === "mapa" && nextView === "lista") {
      pendingRestoreMobileScrollRef.current = true;
    }
    setMobileView(nextView);
  };

  const handleSelectTerritory = (territorio: TerritorySelection | null) => {
    setSelectedTerritory(territorio);
    setIsDrawerCollapsed(false);
  };

  const handleSelectTerritoryFromMap = (territorio: TerritorySelection) => {
    if (isMobileViewport && mobileView === "mapa") {
      mobileSelectionChangedInMapRef.current = true;
    }
    handleSelectTerritory(territorio);
  };

  useEffect(() => {
    let isMounted = true;

    async function loadStaticArtifacts() {
      try {
        setLoading(true);

        const ponteiroResposta = await fetch(buildDataUrl("data/atual.json"), {
          cache: "no-store",
          headers: { Accept: "application/json" },
        });
        let base = "data";
        let versaoPublicada: string | undefined;
        if (ponteiroResposta.ok) {
          const ponteiro = await ponteiroResposta.json().catch(() => null);
          if (typeof ponteiro?.versaoDados !== "string" || !/^[0-9a-f]{32}$/.test(ponteiro.versaoDados)
            || ponteiro.caminho !== `versoes/${ponteiro.versaoDados}`) {
            throw new Error("Referência da versão publicada inválida.");
          }
          versaoPublicada = ponteiro.versaoDados;
          base = `data/${ponteiro.caminho}`;
        } else if (ponteiroResposta.status !== 404) {
          throw new Error(`Falha ao carregar a versão publicada (${ponteiroResposta.status})`);
        }

        const [resIndex, resBairros, resPb] = await Promise.all([
          fetch(buildDataUrl(`${base}/index_2025.json`)),
          fetch(buildDataUrl(`${base}/geo/bairros.geojson`)),
          fetch(buildDataUrl(`${base}/geo/prefeituras_bairro.geojson`)),
        ]);

        if (!resIndex.ok) throw new Error(`Falha ao carregar index_2025.json (${resIndex.status})`);
        if (!resBairros.ok) throw new Error(`Falha ao carregar bairros.geojson (${resBairros.status})`);
        if (!resPb.ok) throw new Error(`Falha ao carregar prefeituras_bairro.geojson (${resPb.status})`);

        const [dataIndex, dataBairros, dataPb] = await Promise.all([
          resIndex.json(),
          resBairros.json(),
          resPb.json(),
        ]);

        const versao = dataIndex.metadata?.atualizacao?.versaoDados;
        if (versaoPublicada && versao !== versaoPublicada) {
          throw new Error("A referência e os dados são de versões diferentes. Recarregue a página.");
        }
        if (versao ? dataBairros.versaoDados !== versao || dataPb.versaoDados !== versao
          : dataBairros.versaoDados || dataPb.versaoDados) {
          throw new Error("Os arquivos de dados são de versões diferentes. Recarregue a página.");
        }
        if (versao) {
          const atualizacao = dataIndex.metadata.atualizacao;
          if (atualizacao.consultas !== "concluidas" || atualizacao.validacoes !== "aprovadas"
            || !Array.isArray(atualizacao.limitacoesConhecidas)
            || !/^\d{4}-\d{2}-\d{2}$/.test(atualizacao.dataReferenciaPagamentos)
            || [atualizacao.inicioConsultas, atualizacao.fimConsultas, atualizacao.concluidaEm]
              .some((data: string) => typeof data !== "string" || Number.isNaN(Date.parse(data)))
            || Date.parse(atualizacao.inicioConsultas) > Date.parse(atualizacao.fimConsultas)
            || Date.parse(atualizacao.fimConsultas) > Date.parse(atualizacao.concluidaEm)) {
            throw new Error("Metadados da atualização inválidos.");
          }
        }

        if (isMounted) {
          setIndexData(dataIndex);
          setDataBase(base);
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
    if (!indexData) return [...FALLBACK_MANDATOS];
    if (indexData.metadata.mandatosDisponiveis && indexData.metadata.mandatosDisponiveis.length > 0) {
      return ordenarMandatosDecrescente(indexData.metadata.mandatosDisponiveis);
    }
    const mandatosSet = new Set<string>();
    indexData.obras.forEach((o) => {
      (o.mandatos || []).forEach((m) => mandatosSet.add(m));
    });
    if (mandatosSet.size === 0) {
      return [...FALLBACK_MANDATOS];
    }
    return ordenarMandatosDecrescente(Array.from(mandatosSet));
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
    filters.semaforo !== "todos";

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
        disponibilidadeInformada: boolean | undefined,
        rollupEntry?: { valorPagoDisponivel?: boolean; totalObras?: number }
      ) => {
        if (disponibilidadeInformada !== undefined) return disponibilidadeInformada;
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
              b.valorPagoDisponivel,
              rb
            ),
            obrasSemValorPago: b.obrasSemValorPago ?? rb?.obrasSemValorPago,
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
              pb.valorPagoDisponivel,
              rpb
            ),
            obrasSemValorPago: pb.obrasSemValorPago ?? rpb?.obrasSemValorPago,
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
  const selectedChildBairroKeys = useMemo(() => {
    if (!indexData || !activeSelectedTerritory || activeSelectedTerritory.tipo !== "prefeitura_bairro") {
      return undefined;
    }
    const targetKey = normalizeName(activeSelectedTerritory.nome);
    const keys = new Set<string>();
    for (const b of indexData.bairros) {
      if (b.prefeitura_bairro && normalizeName(b.prefeitura_bairro) === targetKey) {
        keys.add(normalizeName(b.nome));
      }
    }
    return keys;
  }, [indexData, activeSelectedTerritory]);

  const filteredObras = useMemo(() => {
    if (!activeSelectedTerritory) return topFilteredObras;

    return topFilteredObras.filter((obra) =>
      obraMatchesTerritory(obra, activeSelectedTerritory, selectedChildBairroKeys)
    );
  }, [topFilteredObras, activeSelectedTerritory, selectedChildBairroKeys]);

  // 4b. Busca textual por objeto, Empreiteira ou CNPJ pertence exclusivamente à consulta de obras
  const tableObras = useMemo(() => {
    const rawQuery = filters.busca.trim().toLowerCase();
    if (!rawQuery) return filteredObras;
    return filteredObras.filter((obra) => {
      const objMatch = (obra.objeto || "").toLowerCase().includes(rawQuery);
      const credorMatch = (obra.credor || "").toLowerCase().includes(rawQuery);
      const cnpjMatch = (obra.cnpj || obra.cnpjCredor || "").toLowerCase().includes(rawQuery);
      return objMatch || credorMatch || cnpjMatch;
    });
  }, [filteredObras, filters.busca]);

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
          valorNaoLocalizadoPago += o.valorPago - pagoFrentes;
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
    const requestId = ++fichaRequestRef.current;
    if (typeof document !== "undefined" && document.activeElement instanceof HTMLElement) {
      const fichaAberta = document.querySelector('[role="dialog"][aria-modal="true"]');
      if (!fichaAberta?.contains(document.activeElement)) {
        lastFichaTriggerRef.current = document.activeElement;
      }
    }
    setLastRequestedObra(obra);
    setFichaError(null);
    setSelectedObraFicha(null);
    let falhaDeCarregamento = false;
    try {
      setLoadingFicha(true);
      falhaDeCarregamento = true;
      const res = await fetch(buildDataUrl(`${dataBase}/obras/${obra.id}.json`));
      if (res.ok) {
        const data: FichaLimpaObra = await res.json();
        falhaDeCarregamento = false;
        const versao = indexData?.metadata.atualizacao?.versaoDados;
        if (versao ? data.versaoDados !== versao : data.versaoDados) {
          throw new Error("A ficha e o painel são de versões diferentes. Recarregue a página.");
        }
        if (requestId === fichaRequestRef.current) setSelectedObraFicha(data);
      } else {
        throw new Error(`Falha ao carregar obra ${obra.id} (status ${res.status})`);
      }
    } catch (err: any) {
      if (requestId !== fichaRequestRef.current) return;
      console.error("Erro ao carregar Ficha Limpa da Obra sob demanda:", err);
      const versao = indexData?.metadata.atualizacao?.versaoDados;
      const mensagem = falhaDeCarregamento && await versaoFoiRetirada(versao)
        ? RECARREGAR_VERSAO_RETIRADA
        : err?.message || "Não foi possível carregar os detalhes completos desta obra.";
      if (requestId !== fichaRequestRef.current) return;
      setFichaError(
        mensagem
      );
    } finally {
      if (requestId === fichaRequestRef.current) setLoadingFicha(false);
    }
  };

  const handleCloseFicha = () => {
    fichaRequestRef.current++;
    setSelectedObraFicha(null);
    setFichaError(null);
    setLoadingFicha(false);
    const trigger = lastFichaTriggerRef.current;
    lastFichaTriggerRef.current = null;
    if (trigger && trigger.isConnected && typeof trigger.focus === "function") {
      Promise.resolve().then(() => {
        try {
          trigger.focus();
        } catch { }
      });
    }
  };

  const handleRetryFicha = () => {
    if (lastRequestedObra) {
      void handleSelectObra(lastRequestedObra);
    }
  };

  const handleFilterByEmpreiteira = (credorOuCnpj: string) => {
    fichaRequestRef.current++;
    setFilters((prev) => ({
      ...prev,
      busca: credorOuCnpj,
    }));
    setSelectedObraFicha(null);
    setFichaError(null);
    setLoadingFicha(false);
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
        obrasSemPagamento={Math.max(
          deduplicateObrasByCanonicalKey(topFilteredObras).filter((obra) => !hasNumericPayment(obra.valorPago)).length,
          usesPrecomputedSummary ? (indexData.kpis_globais.obrasSemValorPago ?? 0) : 0,
          usesPrecomputedSummary ? Math.max(0, ...recalculatedPrefeituras.map((pb) => pb.obrasSemValorPago ?? 0)) : 0
        )}
        totalObrasAlocadas={headerComparisonSummary.totalObrasAlocadas}
        contratosPrefeituraBairroSemRateioCount={
          headerComparisonSummary.contratosPrefeituraBairroSemRateioCount
        }
        isExactLayerWorkCount={headerComparisonSummary.isExactLayerWorkCount}
        limitacoesConhecidas={Array.from(new Set(topFilteredObras.flatMap(limitacoesDaObra)))}
        limitacoesAlocadas={Array.from(new Set((activeLayer === "bairros" ? recalculatedBairros : recalculatedPrefeituras).flatMap((territorio) => territorio.limitacoesConhecidas || [])))}
        limitacoesNaoLocalizadas={Array.from(new Set(topFilteredObras.filter((obra) => obra.nivel === "Escopo Cidade (Não-Localizado)").flatMap(limitacoesDaObra)))}
        generatedAt={indexData.metadata.atualizacao ? undefined : indexData.metadata.generatedAt}
        atualizacao={indexData.metadata.atualizacao}
        metricType={filters.metricType}
        mandato={filters.mandato}
        mandatosDisponiveis={availableMandatos}
        activeTab={activeTab}
        onSelectComparacao={handleBackToComparacao}
        onSelectTabela={handleOpenTabela}
        tableObrasCount={tableObras.length}
      />

      {/* 2. Barra de Filtros Superiores Combinados */}
      <TopFilters
        filters={filters}
        onFilterChange={handleFilterChange}
        onResetFilters={handleResetFilters}
        availableMandatos={availableMandatos}
        availableOrgaos={availableOrgaos}
        availableTemas={TEMAS_PADRAO}
        totalObrasFiltradas={activeTab === "tabela" ? tableObras.length : filteredObras.length}
        totalObrasGeral={indexData.obras.length}
        activeLayer={activeLayer}
        onToggleLayer={handleToggleLayer}
        selectedTerritory={activeSelectedTerritory}
        territoryContextMessage={
          activeTab === "comparacao"
            ? isMobileViewport
              ? mobileView === "lista"
                ? " — comparação municipal preservada; resumo abaixo da lista"
                : " — comparação municipal preservada; resumo abaixo do mapa"
              : " — comparação municipal preservada; resumo no painel ao lado do mapa"
            : " — exibindo apenas obras deste território"
        }
        onClearTerritory={() => setSelectedTerritory(null)}
        onJumpToTerritorySummary={
          activeTab === "comparacao" && isMobileViewport && mobileView === "lista"
            ? () => {
              const el = document.querySelector('[data-testid="raio-x-container"]');
              if (el && typeof el.scrollIntoView === "function") {
                el.scrollIntoView({ behavior: "smooth", block: "start" });
              }
            }
            : undefined
        }
      />

      {/* 3. Área Central de Visualização */}
      <main className="flex-1">
        {activeTab === "comparacao" && (
          <div className="max-w-[1440px] w-full mx-auto px-4 sm:px-6 py-3 md:py-4 flex flex-col gap-3 md:gap-4">
            {/* Alternância evidente Lista/Mapa no celular */}
            {isMobileViewport && (
              <div
                ref={mobileToggleRef}
                data-testid="mobile-view-toggle"
                role="group"
                aria-label="Alternar visualização entre Lista e Mapa no celular"
                className="md:hidden grid grid-cols-2 gap-1.5 bg-slate-200/80 p-1 rounded-xl border border-slate-300 shadow-sm"
              >
                <button
                  type="button"
                  data-testid="btn-mobile-visao-lista"
                  aria-pressed={mobileView === "lista"}
                  onClick={() => handleMobileViewChange("lista")}
                  className={`min-h-[40px] px-3 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 ${mobileView === "lista"
                    ? "bg-slate-900 text-white shadow-sm ring-1 ring-slate-900"
                    : "bg-white/70 text-slate-700 hover:bg-white"
                    }`}
                >
                  <span aria-hidden="true">{mobileView === "lista" ? "✓" : "☰"}</span>
                  <span>Lista</span>
                </button>
                <button
                  type="button"
                  data-testid="btn-mobile-visao-mapa"
                  aria-pressed={mobileView === "mapa"}
                  onClick={() => handleMobileViewChange("mapa")}
                  className={`min-h-[40px] px-3 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 ${mobileView === "mapa"
                    ? "bg-slate-900 text-white shadow-sm ring-1 ring-slate-900"
                    : "bg-white/70 text-slate-700 hover:bg-white"
                    }`}
                >
                  <span aria-hidden="true">{mobileView === "mapa" ? "✓" : "🗺"}</span>
                  <span>Mapa</span>
                </button>
              </div>
            )}

            <div className="flex flex-col md:flex-row items-start gap-4">
              {/* Esquerda (~45%): Lista de Comparação Territorial ordenada por vulnerabilidade */}
              <div
                data-testid="mobile-lista-panel"
                hidden={isMobileViewport && mobileView !== "lista"}
                className={`w-full md:w-[45%] min-w-0 overflow-hidden md:h-[calc(100vh-12.5rem)] md:min-h-[520px] md:max-h-[780px] ${isMobileViewport && mobileView !== "lista" ? "hidden md:block" : ""
                  }`}
              >
                <TerritoryComparisonList
                  activeLayer={activeLayer}
                  prefeituras={recalculatedPrefeituras}
                  bairros={recalculatedBairros}
                  metricType={filters.metricType}
                  sortColumn={sortColumn}
                  onSelectSortColumn={(col, dir) => {
                    setSortColumn(col);
                    setSortDirection(dir);
                  }}
                  sortDirection={sortDirection}
                  onToggleSortDirection={() =>
                    setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"))
                  }
                  cityAveragePerCapita={headerComparisonSummary.kpis.investimentoPorHabitanteCidade}
                  cityAverageAvailable={headerComparisonSummary.valorAlocadoDisponivel}
                  territorySearch={territorySearch}
                  onTerritorySearchChange={setTerritorySearch}
                  hasEmptyContractFilter={isContractFiltered && topFilteredObras.length === 0}
                  onClearContractFilters={handleClearContractFilters}
                  selectedTerritory={activeSelectedTerritory}
                  onSelectTerritory={handleSelectTerritory}
                  onOpenNotaMetodologica={() => setShowNotaMetodologica(true)}
                  isVisible={!isMobileViewport || mobileView === "lista"}
                />
              </div>

              {/* Direita (~55%): Mapa com altura alinhada e Raio-X flutuante no desktop (ou empilhado no celular) */}
              <div className="w-full md:w-[55%] min-w-0 flex flex-col gap-3 md:relative md:overflow-hidden md:h-[calc(100vh-12.5rem)] md:min-h-[520px] md:max-h-[780px]">
                <div
                  data-testid="mobile-mapa-panel"
                  hidden={isMobileViewport && mobileView !== "mapa"}
                  className={`sm:min-h-[480px] lg:min-h-[520px] md:h-full min-w-0 overflow-hidden rounded-xl border border-slate-200 shadow-sm flex flex-col ${isMobileViewport && mobileView !== "mapa" ? "hidden md:flex" : ""
                    }`}
                >
                  <InteractiveMap
                    activeLayer={activeLayer}
                    bairros={recalculatedBairros}
                    prefeituras={recalculatedPrefeituras}
                    bairrosGeoJson={bairrosGeo}
                    prefeiturasGeoJson={prefeiturasGeo}
                    obras={filteredObras}
                    heatmapObras={topFilteredObras}
                    selectedTerritory={activeSelectedTerritory}
                    onSelectTerritory={handleSelectTerritoryFromMap}
                    onSelectObra={handleSelectObra}
                    metricType={filters.metricType}
                    territorySearch={territorySearch}
                    onOpenNotaMetodologica={() => setShowNotaMetodologica(true)}
                    isVisible={!isMobileViewport || mobileView === "mapa"}
                    isDesktopDrawerExpanded={
                      !isMobileViewport && Boolean(activeSelectedTerritory) && !isDrawerCollapsed
                    }
                  />
                </div>

                {activeSelectedTerritory && (
                  <TerritorySidebar
                    territorio={activeSelectedTerritory}
                    onClear={() => setSelectedTerritory(null)}
                    onViewWorksInTable={handleOpenTabela}
                    metricType={filters.metricType}
                    onOpenNotaMetodologica={() => setShowNotaMetodologica(true)}
                    obras={topFilteredObras}
                    onSelectObra={handleSelectObra}
                    onSwitchToExecutado={() => handleFilterChange({ metricType: "executado" })}
                    isCollapsed={isDrawerCollapsed}
                    onToggleCollapse={() => setIsDrawerCollapsed((prev) => !prev)}
                  />
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === "tabela" && (
          <div className="max-w-[1440px] mx-auto p-4 sm:p-6">
            <div className="mb-3">
              <button
                type="button"
                data-testid="btn-voltar-comparacao"
                onClick={handleBackToComparacao}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-slate-300 text-slate-700 hover:bg-slate-100 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
              >
                ← Voltar à Comparação Territorial
              </button>
            </div>
            <WorksTable
              obras={tableObras}
              metricType={filters.metricType}
              selectedTerritory={activeSelectedTerritory}
              childBairroKeys={selectedChildBairroKeys}
              totalTerritoryObrasCount={filteredObras.length}
              onSelectObra={handleSelectObra}
              busca={filters.busca}
              onBuscaChange={(busca) => handleFilterChange({ busca })}
              hasActiveContractFilters={isContractFiltered}
              onClearContractFilters={handleClearContractFilters}
              onBackToComparison={handleBackToComparacao}
              onClearTerritory={() => setSelectedTerritory(null)}
            />
          </div>
        )}
      </main>

      {/* 5. Ficha Limpa da Obra sob demanda (Camada C) */}
      <FichaLimpaModal
        obra={selectedObraFicha}
        loading={loadingFicha}
        error={fichaError}
        requestedObra={lastRequestedObra}
        onRetry={handleRetryFicha}
        onClose={handleCloseFicha}
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

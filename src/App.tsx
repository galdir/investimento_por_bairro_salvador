import React, { useEffect, useState } from "react";
import { HeaderKpis } from "./components/HeaderKpis";
import { InteractiveMap } from "./components/InteractiveMap";
import { TerritorySidebar } from "./components/TerritorySidebar";
import { IndexData, TerritorySelection } from "./types";

/**
 * Componente principal do Painel de Obras Públicas de Salvador.
 *
 * @summary Integra os componentes de cabeçalho (KPIs), mapa interativo e painel de Raio-X.
 * @description Carrega no início da aplicação os artefatos estáticos particionados gerados pelo
 * pipeline ETL (índice anual e malhas GeoJSON de Bairros e Prefeituras-Bairro). Gerencia o estado
 * de navegação espacial, alternância de camadas e seleção ativa de territórios para controle social.
 *
 * @returns Elemento JSX com a estrutura completa da aplicação.
 */
export const App: React.FC = () => {
  const [indexData, setIndexData] = useState<IndexData | null>(null);
  const [bairrosGeo, setBairrosGeo] = useState<any>(null);
  const [prefeiturasGeo, setPrefeiturasGeo] = useState<any>(null);
  const [activeLayer, setActiveLayer] = useState<"bairros" | "prefeituras">("bairros");
  const [selectedTerritory, setSelectedTerritory] = useState<TerritorySelection | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadStaticArtifacts() {
      try {
        setLoading(true);
        // O caminho base suporta execução em desenvolvimento e deploy no GitHub Pages
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
      {/* 1. Cabeçalho com KPIs Globais */}
      <HeaderKpis kpis={indexData.kpis_globais} ano={indexData.metadata.anoReferencia} />

      {/* 2. Área Central de Visualização (Mapa + Painel Lateral) */}
      <main className="flex-1 flex flex-col md:flex-row overflow-hidden relative">
        <InteractiveMap
          activeLayer={activeLayer}
          onToggleLayer={setActiveLayer}
          bairros={indexData.bairros}
          prefeituras={indexData.prefeituras_bairro}
          bairrosGeoJson={bairrosGeo}
          prefeiturasGeoJson={prefeiturasGeo}
          selectedTerritory={selectedTerritory}
          onSelectTerritory={setSelectedTerritory}
        />

        <TerritorySidebar
          territorio={selectedTerritory}
          onClear={() => setSelectedTerritory(null)}
        />
      </main>
    </div>
  );
};

export default App;

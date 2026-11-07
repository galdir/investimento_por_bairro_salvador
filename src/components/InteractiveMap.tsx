import React, { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  BairroResumo,
  ChoroplethMetric,
  ObraCompacta,
  PrefeituraBairroResumo,
  TerritorySelection,
} from "../types";
import { formatCurrency, formatNumber } from "../utils/formatters";
import { createBairroSelection, createPrefeituraSelection } from "../utils/territory";

export const SALVADOR_CENTER: L.LatLngTuple = [-12.9777, -38.48];
export const SALVADOR_DEFAULT_ZOOM = 12;

interface InteractiveMapProps {
  activeLayer: "bairros" | "prefeituras";
  onToggleLayer: (layer: "bairros" | "prefeituras") => void;
  bairros: BairroResumo[];
  prefeituras: PrefeituraBairroResumo[];
  bairrosGeoJson: any;
  prefeiturasGeoJson: any;
  obras: ObraCompacta[];
  selectedTerritory: TerritorySelection | null;
  onSelectTerritory: (territorio: TerritorySelection) => void;
  onSelectObra?: (obra: ObraCompacta) => void;
}

export function normalizeTestId(nome: string): string {
  if (!nome) return "";
  return nome
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

/**
 * Retorna a cor do mapa coroplético para o Investimento por Habitante (escala esmeralda).
 */
function getInvestimentoColor(valor: number, breaks: number[]): string {
  if (valor <= 0) return "#f1f5f9";
  if (valor < breaks[0]) return "#d1fae5";
  if (valor < breaks[1]) return "#6ee7b7";
  if (valor < breaks[2]) return "#10b981";
  if (valor < breaks[3]) return "#059669";
  return "#064e3b";
}

/**
 * Retorna a cor do mapa coroplético para o Índice de Vulnerabilidade (escala roxa).
 */
function getVulnerabilidadeColor(vuln: number): string {
  if (vuln < 0.2) return "#ede9fe";
  if (vuln < 0.4) return "#c4b5fd";
  if (vuln < 0.6) return "#8b5cf6";
  if (vuln < 0.8) return "#6d28d9";
  return "#4c1d95";
}

/**
 * Componente do Mapa Interativo com Camada A (Justiça Territorial Per Capita e Semáforo da Obra).
 *
 * @summary Renderiza o mapa coroplético de Salvador com pinos de obras e alternância de métricas.
 * @description Apresenta a visualização coroplética dos territórios (Bairros Oficiais ou Prefeituras-Bairro)
 * coloridos pelo Investimento por Habitante (R$/hab) ou pelo Índice de Vulnerabilidade social.
 * Exclui as 3 Zonas Especiais Não-Residenciais da escala per capita, plotando também os pinos
 * georreferenciados das Obras Públicas coloridos pelo Semáforo da Obra com dispersão geométrica anti-sobreposição.
 *
 * @param props - Propriedades de configuração do mapa, dados geográficos e obras filtradas.
 * @returns Elemento JSX com controles de camada, legenda coroplética e seletor rápido.
 */
export const InteractiveMap: React.FC<InteractiveMapProps> = ({
  activeLayer,
  onToggleLayer,
  bairros,
  prefeituras,
  bairrosGeoJson,
  prefeiturasGeoJson,
  obras,
  selectedTerritory,
  onSelectTerritory,
  onSelectObra,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const leafletMapRef = useRef<L.Map | null>(null);
  const geoJsonLayerRef = useRef<L.GeoJSON | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);

  const [choroplethMetric, setChoroplethMetric] = useState<ChoroplethMetric>("investimentoPorHabitante");
  const [showPins, setShowPins] = useState<boolean>(true);
  const [territorySearch, setTerritorySearch] = useState<string>("");

  // Inicialização do Leaflet centrada em Salvador
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (leafletMapRef.current) return;

    try {
      const map = L.map(mapContainerRef.current, {
        center: SALVADOR_CENTER,
        zoom: SALVADOR_DEFAULT_ZOOM,
        zoomControl: false,
      });

      L.control.zoom({ position: "bottomright" }).addTo(map);

      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      leafletMapRef.current = map;

      setTimeout(() => {
        try {
          map.invalidateSize();
          map.setView(SALVADOR_CENTER, SALVADOR_DEFAULT_ZOOM);
        } catch {}
      }, 50);
    } catch {}

    return () => {
      if (leafletMapRef.current) {
        try {
          leafletMapRef.current.remove();
        } catch {}
        leafletMapRef.current = null;
      }
    };
  }, []);

  // Observador de redimensionamento do container
  useEffect(() => {
    if (!mapContainerRef.current || typeof ResizeObserver === "undefined") return;

    const ro = new ResizeObserver(() => {
      if (leafletMapRef.current) {
        try {
          leafletMapRef.current.invalidateSize();
        } catch {}
      }
    });

    ro.observe(mapContainerRef.current);

    return () => {
      ro.disconnect();
    };
  }, []);

  // Calcula os limites de quantis para a escala coroplética de Investimento por Habitante
  const breaksInvestimento = useMemo(() => {
    const valores = bairros
      .filter((b) => !b.is_zona_especial_nao_residencial && !b.isZonaEspecialNaoResidencial && (b.investimentoPorHabitante ?? 0) > 0)
      .map((b) => b.investimentoPorHabitante ?? 0)
      .sort((a, b) => a - b);

    if (valores.length === 0) return [20, 50, 100, 200];

    const q = (p: number) => valores[Math.floor((valores.length - 1) * p)];
    return [q(0.2), q(0.4), q(0.6), q(0.8)];
  }, [bairros]);

  // Atualização dos polígonos GeoJSON no Leaflet
  useEffect(() => {
    const map = leafletMapRef.current;
    if (!map) return;

    if (geoJsonLayerRef.current) {
      try {
        map.removeLayer(geoJsonLayerRef.current);
      } catch {}
      geoJsonLayerRef.current = null;
    }

    const geoData = activeLayer === "bairros" ? bairrosGeoJson : prefeiturasGeoJson;
    if (!geoData || !geoData.features) return;

    try {
      const layer = L.geoJSON(geoData, {
        style: (feature) => {
          const props = feature?.properties || {};
          const nome = props.nome || props.NM_BAIRRO || props.NM_PREFEITURA_BAIRRO || "";
          const isSelected = selectedTerritory?.nome === nome;
          const isZonaEspecial = !!(props.is_zona_especial_nao_residencial || props.isZonaEspecialNaoResidencial);

          let fillColor = "#cbd5e1";

          if (isZonaEspecial) {
            fillColor = "#fef3c7";
          } else if (choroplethMetric === "investimentoPorHabitante") {
            const inv = props.investimentoPorHabitante ?? 0;
            fillColor = getInvestimentoColor(inv, breaksInvestimento);
          } else {
            const vuln = props.indice_vulnerabilidade ?? 0.5;
            fillColor = getVulnerabilidadeColor(vuln);
          }

          return {
            fillColor: isSelected ? "#10B981" : fillColor,
            weight: isSelected ? 3 : 1.2,
            opacity: 1,
            color: isSelected ? "#065f46" : isZonaEspecial ? "#d97706" : "#ffffff",
            fillOpacity: isSelected ? 0.75 : 0.6,
          };
        },
        onEachFeature: (feature, layerItem) => {
          const props = feature.properties || {};
          const nome = props.nome || props.NM_BAIRRO || props.NM_PREFEITURA_BAIRRO || "";

          layerItem.on({
            click: () => {
              if (activeLayer === "bairros") {
                const b = bairros.find((item) => item.nome === nome) || {
                  id: props.id || 0,
                  nome,
                  prefeitura_bairro: props.prefeitura_bairro || "",
                  populacao: props.populacao || 0,
                  indice_vulnerabilidade: props.indice_vulnerabilidade || 0.5,
                  is_zona_especial_nao_residencial: !!(props.is_zona_especial_nao_residencial || props.isZonaEspecialNaoResidencial),
                  valorTotal: props.valorTotal,
                  valorPago: props.valorPago,
                  totalObras: props.totalObras,
                  obrasVerde: props.obrasVerde,
                  obrasAmarelo: props.obrasAmarelo,
                  obrasVermelho: props.obrasVermelho,
                  investimentoPorHabitante: props.investimentoPorHabitante,
                  investimentoPorHabitantePago: props.investimentoPorHabitantePago,
                };
                onSelectTerritory(createBairroSelection(b));
              } else {
                const pb = prefeituras.find((item) => item.nome === nome) || {
                  id: props.id || 0,
                  nome,
                  populacao_total: props.populacao_total || 0,
                  valorTotal: props.valorTotal,
                  valorPago: props.valorPago,
                  totalObras: props.totalObras,
                  obrasVerde: props.obrasVerde,
                  obrasAmarelo: props.obrasAmarelo,
                  obrasVermelho: props.obrasVermelho,
                  investimentoPorHabitante: props.investimentoPorHabitante,
                  investimentoPorHabitantePago: props.investimentoPorHabitantePago,
                };
                onSelectTerritory(createPrefeituraSelection(pb));
              }
            },
          });
        },
      });

      layer.addTo(map);
      geoJsonLayerRef.current = layer;

      if (selectedTerritory) {
        let foundBounds: L.LatLngBounds | null = null;
        layer.eachLayer((l: any) => {
          const p = l.feature?.properties || {};
          const itemNome = p.nome || p.NM_BAIRRO || p.NM_PREFEITURA_BAIRRO;
          if (itemNome === selectedTerritory.nome && typeof l.getBounds === "function") {
            try {
              foundBounds = l.getBounds();
            } catch {}
          }
        });

        if (foundBounds && (foundBounds as L.LatLngBounds).isValid()) {
          try {
            map.fitBounds(foundBounds, { maxZoom: 14, padding: [40, 40] });
          } catch {}
        }
      }
    } catch {}
  }, [
    activeLayer,
    bairrosGeoJson,
    prefeiturasGeoJson,
    selectedTerritory,
    choroplethMetric,
    breaksInvestimento,
    bairros,
    prefeituras,
    onSelectTerritory,
  ]);

  // Renderização dos Pinos de Obras Públicas com dispersão determinística anti-sobreposição
  useEffect(() => {
    const map = leafletMapRef.current;
    if (!map) return;

    if (markersLayerRef.current) {
      try {
        map.removeLayer(markersLayerRef.current);
      } catch {}
      markersLayerRef.current = null;
    }

    if (!showPins) return;

    try {
      const markersGroup = L.layerGroup();

      // Agrupa obras com coordenadas idênticas para aplicar dispersão radial
      const obrasPorCoord: Record<string, ObraCompacta[]> = {};
      for (const obra of obras) {
        if (obra.latitude && obra.longitude) {
          const coordKey = `${obra.latitude.toFixed(4)}_${obra.longitude.toFixed(4)}`;
          if (!obrasPorCoord[coordKey]) obrasPorCoord[coordKey] = [];
          obrasPorCoord[coordKey].push(obra);
        }
      }

      for (const coordGroup of Object.values(obrasPorCoord)) {
        const total = coordGroup.length;
        coordGroup.forEach((obra, idx) => {
          let lat = obra.latitude!;
          let lon = obra.longitude!;

          // Se houver mais de uma obra no mesmo ponto exato/centróide, aplica dispersão circular
          if (total > 1) {
            const angulo = (idx * (2 * Math.PI)) / total;
            const raio = 0.0015; // Aproximadamente 150m de dispersão visual
            lat += Math.sin(angulo) * raio;
            lon += Math.cos(angulo) * raio;
          }

          const status = obra.semaforo?.status || "VERDE";
          const corPino = status === "VERMELHO" ? "#EF4444" : status === "AMARELO" ? "#F59E0B" : "#10B981";

          const marker = L.circleMarker([lat, lon], {
            radius: 6,
            fillColor: corPino,
            color: "#ffffff",
            weight: 1.5,
            opacity: 1,
            fillOpacity: 0.9,
          });

          const tooltipContent = `
            <div style="font-size: 11px; max-width: 220px;">
              <strong style="color: #0f172a;">${obra.objeto}</strong><br/>
              <span style="color: #64748b;">${obra.unidadeGestora} • ${formatCurrency(obra.valorContratualVigente)}</span><br/>
              <span style="font-weight: 600; color: ${corPino};">Semáforo: ${obra.semaforo?.rotulo || status}</span>
              ${obra.nivel ? `<br/><span style="color: #475569; font-size: 10px;">Nível: ${obra.nivel}</span>` : ""}
            </div>
          `;
          marker.bindTooltip(tooltipContent, { direction: "top", offset: [0, -5] });

          marker.on("click", () => {
            if (onSelectObra) onSelectObra(obra);
          });

          marker.addTo(markersGroup);
        });
      }

      markersGroup.addTo(map);
      markersLayerRef.current = markersGroup;
    } catch {}
  }, [obras, showPins, onSelectObra]);

  const handleRecenter = () => {
    if (leafletMapRef.current) {
      try {
        leafletMapRef.current.invalidateSize();
        leafletMapRef.current.setView(SALVADOR_CENTER, SALVADOR_DEFAULT_ZOOM);
      } catch {}
    }
  };

  // Filtragem dos botões do seletor rápido pelo campo de busca
  const filteredBairrosButtons = useMemo(() => {
    if (!territorySearch.trim()) return bairros;
    const q = territorySearch.toLowerCase();
    return bairros.filter((b) => b.nome.toLowerCase().includes(q));
  }, [bairros, territorySearch]);

  const filteredPrefeiturasButtons = useMemo(() => {
    if (!territorySearch.trim()) return prefeituras;
    const q = territorySearch.toLowerCase();
    return prefeituras.filter((pb) => pb.nome.toLowerCase().includes(q));
  }, [prefeituras, territorySearch]);

  return (
    <div className="relative flex-1 flex flex-col h-full bg-slate-100">
      {/* Controles Superiores do Mapa */}
      <div className="absolute top-4 left-4 z-10 bg-white/95 backdrop-blur-sm p-2 rounded-xl shadow-md border border-slate-200/80 flex flex-wrap items-center gap-2 max-w-full">
        {/* Divisão Territorial */}
        <div className="flex bg-slate-100 p-1 rounded-lg">
          <button
            type="button"
            onClick={() => onToggleLayer("bairros")}
            className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
              activeLayer === "bairros"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Bairros Oficiais
          </button>
          <button
            type="button"
            onClick={() => onToggleLayer("prefeituras")}
            className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
              activeLayer === "prefeituras"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Prefeituras-Bairro
          </button>
        </div>

        {/* Alternância de Métrica Coroplética */}
        <div
          data-testid="toggle-camada-metrica"
          className="flex bg-slate-100 p-1 rounded-lg border border-slate-200"
        >
          <button
            type="button"
            data-testid="btn-camada-per-capita"
            onClick={() => setChoroplethMetric("investimentoPorHabitante")}
            className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
              choroplethMetric === "investimentoPorHabitante"
                ? "bg-emerald-600 text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            R$ / Habitante
          </button>
          <button
            type="button"
            data-testid="btn-camada-vulnerabilidade"
            onClick={() => setChoroplethMetric("vulnerabilidade")}
            className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
              choroplethMetric === "vulnerabilidade"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Vulnerabilidade Social
          </button>
        </div>

        {/* Toggle de Pinos de Obras */}
        <button
          type="button"
          data-testid="btn-toggle-pinos-obras"
          onClick={() => setShowPins((prev) => !prev)}
          className={`px-2.5 py-1 text-xs font-semibold rounded-lg border transition-all flex items-center gap-1.5 ${
            showPins
              ? "bg-slate-900 text-white border-slate-900"
              : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          Pinos de Obras ({obras.filter((o) => o.latitude && o.longitude).length})
        </button>

        {/* Botão de Recentralizar */}
        <button
          type="button"
          data-testid="btn-centralizar-salvador"
          onClick={handleRecenter}
          title="Recentralizar visualização em Salvador"
          className="px-2.5 py-1 text-xs font-medium bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-slate-700 transition-colors flex items-center gap-1 shadow-sm"
        >
          <svg className="w-3.5 h-3.5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Centralizar
        </button>
      </div>

      {/* Legenda Coroplética Flutuante */}
      <div
        data-testid="legenda-coropletica"
        className="absolute bottom-20 left-4 z-10 bg-white/95 backdrop-blur-sm p-2.5 rounded-xl shadow-md border border-slate-200 text-xs"
      >
        <span className="font-bold text-slate-700 block mb-1">
          {choroplethMetric === "investimentoPorHabitante"
            ? "Investimento por Habitante (R$):"
            : "Índice de Vulnerabilidade:"}
        </span>
        <div className="flex items-center gap-1 text-[10px] text-slate-600">
          <span>Menor</span>
          <div className="flex gap-0.5">
            {choroplethMetric === "investimentoPorHabitante" ? (
              <>
                <span className="w-4 h-3 rounded-sm bg-[#d1fae5]"></span>
                <span className="w-4 h-3 rounded-sm bg-[#6ee7b7]"></span>
                <span className="w-4 h-3 rounded-sm bg-[#10b981]"></span>
                <span className="w-4 h-3 rounded-sm bg-[#059669]"></span>
                <span className="w-4 h-3 rounded-sm bg-[#064e3b]"></span>
              </>
            ) : (
              <>
                <span className="w-4 h-3 rounded-sm bg-[#ede9fe]"></span>
                <span className="w-4 h-3 rounded-sm bg-[#c4b5fd]"></span>
                <span className="w-4 h-3 rounded-sm bg-[#8b5cf6]"></span>
                <span className="w-4 h-3 rounded-sm bg-[#6d28d9]"></span>
                <span className="w-4 h-3 rounded-sm bg-[#4c1d95]"></span>
              </>
            )}
          </div>
          <span>Maior</span>
        </div>
        <div className="flex items-center gap-1.5 mt-1 pt-1 border-t border-slate-100 text-[10px] text-amber-800">
          <span className="w-3 h-3 rounded-sm bg-[#fef3c7] border border-amber-400"></span>
          <span>Zona Especial (Isenta)</span>
        </div>
      </div>

      {/* Container Leaflet do Mapa */}
      <div
        ref={mapContainerRef}
        data-testid="leaflet-map-container"
        className="w-full flex-1 min-h-[420px] z-0"
      />

      {/* Seletor Rápido de Territórios com Busca Textual para o Raio-X */}
      <div className="bg-white border-t border-slate-200 p-3 z-10">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              {activeLayer === "bairros" ? "Bairros no Mapa:" : "Prefeituras-Bairro:"}
            </span>
            <input
              type="text"
              data-testid="busca-bairro-mapa"
              value={territorySearch}
              onChange={(e) => setTerritorySearch(e.target.value)}
              placeholder="Buscar para abrir o Raio-X..."
              className="px-2 py-0.5 text-xs bg-slate-50 border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
          <span className="text-xs text-slate-400">
            {activeLayer === "bairros"
              ? `${filteredBairrosButtons.length} de ${bairros.length} bairros`
              : `${filteredPrefeiturasButtons.length} prefeituras`}
          </span>
        </div>
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
          {activeLayer === "bairros"
            ? filteredBairrosButtons.map((b) => {
                const isSelected = selectedTerritory?.id === b.id && selectedTerritory?.tipo === "bairro";
                const isZonaEspecial = b.is_zona_especial_nao_residencial || b.isZonaEspecialNaoResidencial;
                const testId = `territory-selector-${normalizeTestId(b.nome)}`;

                return (
                  <button
                    key={b.id}
                    data-testid={testId}
                    onClick={() => onSelectTerritory(createBairroSelection(b))}
                    className={`shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-all border flex items-center gap-1.5 ${
                      isSelected
                        ? "bg-emerald-600 text-white border-emerald-600 shadow-sm"
                        : isZonaEspecial
                        ? "bg-amber-50 text-amber-800 border-amber-300 hover:bg-amber-100"
                        : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                    }`}
                  >
                    <span>{b.nome}</span>
                    {isZonaEspecial && (
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500" title="Zona Especial Não-Residencial"></span>
                    )}
                    <span className="text-[10px] opacity-75">
                      ({formatNumber(b.populacao)} hab • {formatCurrency(b.investimentoPorHabitante ?? 0)}/hab)
                    </span>
                  </button>
                );
              })
            : filteredPrefeiturasButtons.map((pb) => {
                const isSelected = selectedTerritory?.id === pb.id && selectedTerritory?.tipo === "prefeitura_bairro";
                const testId = `territory-selector-${normalizeTestId(pb.nome)}`;

                return (
                  <button
                    key={pb.id}
                    data-testid={testId}
                    onClick={() => onSelectTerritory(createPrefeituraSelection(pb))}
                    className={`shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-all border flex items-center gap-1.5 ${
                      isSelected
                        ? "bg-indigo-600 text-white border-indigo-600 shadow-sm"
                        : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                    }`}
                  >
                    <span>{pb.nome}</span>
                    <span className="text-[10px] opacity-75">
                      ({formatNumber(pb.populacao_total)} hab • {formatCurrency(pb.investimentoPorHabitante ?? 0)}/hab)
                    </span>
                  </button>
                );
              })}
        </div>
      </div>
    </div>
  );
};

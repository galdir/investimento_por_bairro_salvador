import React, { useEffect, useRef } from "react";
import L from "leaflet";
import { BairroResumo, PrefeituraBairroResumo, TerritorySelection } from "../types";
import { formatNumber } from "../utils/formatters";

interface InteractiveMapProps {
  /**
   * Camada ativa atual no mapa: 'bairros' ou 'prefeituras'.
   */
  activeLayer: "bairros" | "prefeituras";
  /**
   * Callback disparado quando o usuário altera a camada territorial.
   */
  onToggleLayer: (layer: "bairros" | "prefeituras") => void;
  /**
   * Lista cadastral de Bairros Oficiais.
   */
  bairros: BairroResumo[];
  /**
   * Lista cadastral de Prefeituras-Bairro.
   */
  prefeituras: PrefeituraBairroResumo[];
  /**
   * GeoJSON FeatureCollection de Bairros Oficiais.
   */
  bairrosGeoJson: any;
  /**
   * GeoJSON FeatureCollection de Prefeituras-Bairro.
   */
  prefeiturasGeoJson: any;
  /**
   * Território selecionado no momento.
   */
  selectedTerritory: TerritorySelection | null;
  /**
   * Callback quando o usuário clica em um território.
   */
  onSelectTerritory: (territorio: TerritorySelection) => void;
}

/**
 * Normaliza uma string de nome para uso seguro em IDs de teste e seletores HTML.
 *
 * @summary Remove diacríticos, espaços e pontuação para formar um identificador web seguro.
 * @description Converte o texto para caixa baixa, aplica decomposição canônica NFKD para
 * descartar caracteres acentuados e substitui caracteres não alfanuméricos por hífens.
 *
 * @param nome - Nome original com ou sem acentos (ex: "Barra/Pituba").
 * @returns String simplificada contendo apenas caracteres alfanuméricos e hífens (ex: "barra-pituba").
 * @throws Não lança exceções; se o nome for vazio ou nulo retorna string vazia.
 */
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
 * Converte um Bairro cadastral em um objeto de seleção territorial unificado.
 *
 * @summary Encapsula a conversão de tipo para evitar repetição de parâmetros (Data Clump).
 * @param b - Objeto de BairroResumo.
 * @returns Objeto TerritorySelection configurado para o bairro.
 */
function createBairroSelection(b: BairroResumo): TerritorySelection {
  return {
    tipo: "bairro",
    id: b.id,
    nome: b.nome,
    prefeitura_bairro: b.prefeitura_bairro,
    populacao: b.populacao,
    indice_vulnerabilidade: b.indice_vulnerabilidade,
    is_zona_especial_nao_residencial: b.is_zona_especial_nao_residencial,
    isZonaEspecialNaoResidencial: b.isZonaEspecialNaoResidencial ?? b.is_zona_especial_nao_residencial,
  };
}

/**
 * Converte uma Prefeitura-Bairro cadastral em um objeto de seleção territorial unificado.
 *
 * @summary Encapsula a conversão de tipo para evitar repetição de parâmetros (Data Clump).
 * @param pb - Objeto de PrefeituraBairroResumo.
 * @returns Objeto TerritorySelection configurado para a Prefeitura-Bairro.
 */
function createPrefeituraSelection(pb: PrefeituraBairroResumo): TerritorySelection {
  return {
    tipo: "prefeitura_bairro",
    id: pb.id,
    nome: pb.nome,
    populacao: pb.populacao_total,
  };
}

/**
 * Componente do Mapa Interativo de Salvador com suporte a Leaflet e camada territorial interativa.
 *
 * @summary Renderiza o mapa geográfico de Salvador com alternância de camadas e clique nos territórios.
 * @description Permite ao usuário alternar entre a divisão administrativa por Prefeituras-Bairro
 * e a divisão por Bairros Oficiais (Decreto 32.791/2020). Utiliza Leaflet para visualização espacial
 * e uma barra de seleção territorial interativa com suporte a acessibilidade e testes automatizados.
 *
 * @param props - Propriedades de configuração do mapa, dados geográficos e callbacks de interação.
 * @returns Elemento JSX do mapa com controles de camada e seletor rápido.
 * @throws Não lança exceções; captura falhas de renderização em ambientes headless/JSDOM.
 */
export const InteractiveMap: React.FC<InteractiveMapProps> = ({
  activeLayer,
  onToggleLayer,
  bairros,
  prefeituras,
  bairrosGeoJson,
  prefeiturasGeoJson,
  selectedTerritory,
  onSelectTerritory,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const leafletMapRef = useRef<L.Map | null>(null);
  const geoJsonLayerRef = useRef<L.GeoJSON | null>(null);

  // Inicialização do mapa Leaflet centrado em Salvador
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (leafletMapRef.current) return;

    try {
      // Coordenadas aproximadas do centro de Salvador: -12.9777, -38.48
      const map = L.map(mapContainerRef.current, {
        center: [-12.9777, -38.48],
        zoom: 12,
        zoomControl: false,
      });

      L.control.zoom({ position: "bottomright" }).addTo(map);

      // Camada base CartoDB Positron sem ruído visual
      L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
        maxZoom: 19,
      }).addTo(map);

      leafletMapRef.current = map;
    } catch {
      // Em ambientes de teste jsdom onde Leaflet não consegue calcular dimensões de tela
    }

    return () => {
      if (leafletMapRef.current) {
        try {
          leafletMapRef.current.remove();
        } catch {
          // Tratamento para ambientes JSDOM / headless
        }
        leafletMapRef.current = null;
      }
    };
  }, []);

  // Atualização dos polígonos GeoJSON no Leaflet ao mudar camada ou dados
  useEffect(() => {
    const map = leafletMapRef.current;
    if (!map) return;

    if (geoJsonLayerRef.current) {
      try {
        map.removeLayer(geoJsonLayerRef.current);
      } catch {
        // Tratamento para ambientes JSDOM / headless
      }
      geoJsonLayerRef.current = null;
    }

    const geoData = activeLayer === "bairros" ? bairrosGeoJson : prefeiturasGeoJson;
    if (!geoData || !geoData.features) return;

    try {
      const layer = L.geoJSON(geoData, {
        style: (feature) => {
          const props = feature?.properties || {};
          const isSelected = selectedTerritory?.nome === (props.nome || props.NM_BAIRRO || props.NM_PREFEITURA_BAIRRO);
          const isZonaEspecial = !!(props.is_zona_especial_nao_residencial || props.isZonaEspecialNaoResidencial);

          return {
            fillColor: isSelected
              ? "#10B981"
              : isZonaEspecial
              ? "#F59E0B"
              : activeLayer === "bairros"
              ? "#3B82F6"
              : "#6366F1",
            weight: isSelected ? 3 : 1.5,
            opacity: 1,
            color: isSelected ? "#065F46" : "#ffffff",
            fillOpacity: isSelected ? 0.6 : 0.35,
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
                };
                onSelectTerritory(createBairroSelection(b));
              } else {
                const pb = prefeituras.find((item) => item.nome === nome) || {
                  id: props.id || 0,
                  nome,
                  populacao_total: props.populacao_total || 0,
                };
                onSelectTerritory(createPrefeituraSelection(pb));
              }
            },
          });
        },
      });

      layer.addTo(map);
      geoJsonLayerRef.current = layer;
    } catch {
      // Ignora falhas em testes headless sem renderização WebGL/Canvas
    }
  }, [activeLayer, bairrosGeoJson, prefeiturasGeoJson, selectedTerritory, bairros, prefeituras, onSelectTerritory]);

  return (
    <div className="relative flex-1 flex flex-col h-full bg-slate-100">
      {/* Barra de Controles Superiores do Mapa */}
      <div className="absolute top-4 left-4 z-10 bg-white/95 backdrop-blur-sm p-2 rounded-xl shadow-md border border-slate-200/80 flex items-center gap-3">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider pl-1">
          Divisão Territorial:
        </span>
        <div className="flex bg-slate-100 p-1 rounded-lg">
          <button
            type="button"
            onClick={() => onToggleLayer("bairros")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
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
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
              activeLayer === "prefeituras"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Prefeituras-Bairro
          </button>
        </div>
        <div data-testid="active-layer-indicator" className="text-xs text-slate-500 px-2 border-l border-slate-200">
          Camada ativa: <strong className="text-slate-800">{activeLayer === "bairros" ? "Bairros Oficiais" : "Prefeituras-Bairro"}</strong>
        </div>
      </div>

      {/* Container Leaflet do Mapa */}
      <div
        ref={mapContainerRef}
        data-testid="leaflet-map-container"
        className="w-full flex-1 min-h-[420px] z-0"
      />

      {/* Seletor Rápido de Territórios Acessível e Interativo */}
      <div className="bg-white border-t border-slate-200 p-3 z-10">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            {activeLayer === "bairros" ? "Bairros no Mapa (Clique para inspecionar):" : "Prefeituras-Bairro no Mapa:"}
          </span>
          <span className="text-xs text-slate-400">
            {activeLayer === "bairros" ? `${bairros.length} bairros` : `${prefeituras.length} prefeituras-bairro`}
          </span>
        </div>
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
          {activeLayer === "bairros"
            ? bairros.map((b) => {
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
                    {isZonaEspecial && <span className="w-1.5 h-1.5 rounded-full bg-amber-500" title="Zona Especial Não-Residencial"></span>}
                    <span className="text-[10px] opacity-75">({formatNumber(b.populacao)} hab)</span>
                  </button>
                );
              })
            : prefeituras.map((pb) => {
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
                    <span className="text-[10px] opacity-75">({formatNumber(pb.populacao_total)} hab)</span>
                  </button>
                );
              })}
        </div>
      </div>
    </div>
  );
};

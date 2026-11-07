import React, { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { BairroResumo, PrefeituraBairroResumo, TerritorySelection } from "../types";
import { formatNumber } from "../utils/formatters";

/**
 * Coordenadas geográficas centrais da malha urbana de Salvador (Bahia).
 *
 * @summary Coordenadas de referência central de Salvador (Latitude, Longitude).
 * @description Centraliza a visualização no coração urbano de Salvador (-12.9777, -38.48),
 * abrangendo de forma equilibrada o Centro Histórico, a Orla Atlântica, o Subúrbio e o Miolo.
 */
export const SALVADOR_CENTER: L.LatLngTuple = [-12.9777, -38.48];

/**
 * Nível de zoom inicial padrão para visualização do município de Salvador.
 */
export const SALVADOR_DEFAULT_ZOOM = 12;

/**
 * Limites geográficos (Bounding Box) da área urbana e continental de Salvador.
 *
 * @summary Delimita a mancha urbana principal de Salvador, evitando distorções provocadas por ilhas remotas na baía.
 * @description Define o retângulo envolvente de Salvador do Farol da Barra (-13.02, -38.54) até
 * a Praia do Flamengo/Itapuã e o Subúrbio (-12.83, -38.32).
 */
export const SALVADOR_URBAN_BOUNDS = L.latLngBounds(
  [-13.02, -38.54],
  [-12.83, -38.32]
);

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
 * @returns String simplificada contendo apenas caracteres alfanuméricos e hífens.
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
 * @summary Renderiza o mapa geográfico de Salvador centrado no município com alternância de camadas.
 * @description Garante a correta centralização em Salvador (-12.9777, -38.48) na inicialização,
 * adaptando o tamanho dinâmico do container Leaflet via ResizeObserver para evitar distorções de layout.
 * Permite alternar entre Bairros Oficiais e Prefeituras-Bairro, com destaque para Zonas Especiais
 * Não-Residenciais e zoom automático no território selecionado.
 *
 * @param props - Propriedades de configuração do mapa, dados geográficos e callbacks de interação.
 * @returns Elemento JSX do mapa com controles de camada, botão de recentralização e seletor rápido.
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

  // Inicialização do mapa Leaflet com centro canônico em Salvador
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (leafletMapRef.current) return;

    try {
      // Cria a instância do Leaflet diretamente centrada no município de Salvador
      const map = L.map(mapContainerRef.current, {
        center: SALVADOR_CENTER,
        zoom: SALVADOR_DEFAULT_ZOOM,
        zoomControl: false,
      });

      L.control.zoom({ position: "bottomright" }).addTo(map);

      // Camada base OpenStreetMap oficial (100% gratuita, sem marca d'água e sem API Key)
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      leafletMapRef.current = map;

      // Invalida o tamanho do container após primeiro ciclo de layout para garantir tiles alinhados
      setTimeout(() => {
        try {
          map.invalidateSize();
          map.setView(SALVADOR_CENTER, SALVADOR_DEFAULT_ZOOM);
        } catch {
          // Ignora em testes headless
        }
      }, 50);
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

  // Observa redimensionamento do container para atualizar o Leaflet (ex: abertura de sidebar ou abas)
  useEffect(() => {
    if (!mapContainerRef.current || typeof ResizeObserver === "undefined") return;

    const ro = new ResizeObserver(() => {
      if (leafletMapRef.current) {
        try {
          leafletMapRef.current.invalidateSize();
        } catch {
          // Ignora em testes headless
        }
      }
    });

    ro.observe(mapContainerRef.current);

    return () => {
      ro.disconnect();
    };
  }, []);

  // Atualização dos polígonos GeoJSON no Leaflet ao mudar camada, seleção ou dados
  useEffect(() => {
    const map = leafletMapRef.current;
    if (!map) return;

    // Remove camada anterior se já existente
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

      // Se houver um território selecionado, foca suavemente nele
      if (selectedTerritory) {
        let foundBounds: L.LatLngBounds | null = null;
        layer.eachLayer((l: any) => {
          const p = l.feature?.properties || {};
          const itemNome = p.nome || p.NM_BAIRRO || p.NM_PREFEITURA_BAIRRO;
          if (itemNome === selectedTerritory.nome && typeof l.getBounds === "function") {
            try {
              foundBounds = l.getBounds();
            } catch {
              // Ignora em testes headless
            }
          }
        });

        if (foundBounds && (foundBounds as L.LatLngBounds).isValid()) {
          try {
            map.fitBounds(foundBounds, { maxZoom: 14, padding: [40, 40] });
          } catch {
            // Ignora em testes headless
          }
        }
      } else {
        // Quando nenhum território estiver selecionado, centraliza rigorosamente em Salvador
        try {
          map.setView(SALVADOR_CENTER, SALVADOR_DEFAULT_ZOOM);
        } catch {
          // Ignora em testes headless
        }
      }
    } catch {
      // Ignora falhas em testes headless sem renderização WebGL/Canvas
    }
  }, [activeLayer, bairrosGeoJson, prefeiturasGeoJson, selectedTerritory, bairros, prefeituras, onSelectTerritory]);

  /**
   * Recentraliza a visão do mapa no centro urbano de Salvador com zoom padrão.
   */
  const handleRecenter = () => {
    if (leafletMapRef.current) {
      try {
        leafletMapRef.current.invalidateSize();
        leafletMapRef.current.setView(SALVADOR_CENTER, SALVADOR_DEFAULT_ZOOM);
      } catch {
        // Ignora em ambientes headless
      }
    }
  };

  return (
    <div className="relative flex-1 flex flex-col h-full bg-slate-100">
      {/* Barra de Controles Superiores do Mapa */}
      <div className="absolute top-4 left-4 z-10 bg-white/95 backdrop-blur-sm p-2 rounded-xl shadow-md border border-slate-200/80 flex flex-wrap items-center gap-3">
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

        {/* Botão de Recentralização Rápida em Salvador */}
        <button
          type="button"
          data-testid="btn-centralizar-salvador"
          onClick={handleRecenter}
          title="Recentralizar visualização em Salvador"
          className="px-2.5 py-1.5 text-xs font-medium bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-slate-700 transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <svg className="w-3.5 h-3.5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Centralizar Salvador
        </button>

        <div data-testid="active-layer-indicator" className="text-xs text-slate-500 px-2 border-l border-slate-200 hidden sm:block">
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

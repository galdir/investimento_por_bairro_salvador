import React, { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  BairroResumo,
  ChoroplethMetric,
  MetricType,
  ObraCompacta,
  PrefeituraBairroResumo,
  TerritorySelection,
} from "../types";
import { formatCompactCurrency, formatCurrency } from "../utils/formatters";
import {
  createBairroSelection,
  createPrefeituraSelection,
  getObraTerritoryShare,
  getTerritoryInvestmentState,
  hasNumericValue,
  isCentralidadeMetropolitana,
  isZonaEspecial,
  normalizeName,
} from "../utils/territory";

interface MapPinEntry {
  key: string;
  obra: ObraCompacta;
  latitude: number;
  longitude: number;
  isPrimaryPin: boolean;
  isApproximate: boolean;
  overlapCount: number;
  fracao?: string;
  bairroLabel?: string | null;
}

function isApproximatePinLocation(obra: ObraCompacta, isCotaPin: boolean): boolean {
  if (obra.nivel === "Pontual") return false;
  if (isCotaPin && (obra.estagioAlocacao || "").toLowerCase().includes("equipamento")) {
    return false;
  }
  return true;
}

/**
 * Converte contratos (incluindo múltiplas cotas de Lista Fechada) em entradas de pinos para o mapa,
 * identificando precisão aproximada e grupos sobrepostos na mesma coordenada.
 */
function buildMapPinEntries(
  obras: ObraCompacta[],
  selectedTerritory: TerritorySelection | null
): MapPinEntry[] {
  const rawEntries: Array<Omit<MapPinEntry, "overlapCount">> = [];
  for (const obra of obras) {
    const share = getObraTerritoryShare(obra, selectedTerritory);
    if (share.isCotaParte && share.cotas.length > 0) {
      const cotasComCoord = share.cotas.filter(
        (c) => Boolean(c.latitude) && Boolean(c.longitude)
      );
      if (cotasComCoord.length > 0) {
        cotasComCoord.forEach((cota, idx) => {
          rawEntries.push({
            key: `${obra.id}-cota-${idx}`,
            obra,
            latitude: cota.latitude!,
            longitude: cota.longitude!,
            isPrimaryPin: idx === 0,
            isApproximate: isApproximatePinLocation(obra, true),
            fracao: cota.fracao,
            bairroLabel: cota.bairro,
          });
        });
        continue;
      }
    }
    if (obra.latitude && obra.longitude) {
      rawEntries.push({
        key: String(obra.id),
        obra,
        latitude: obra.latitude,
        longitude: obra.longitude,
        isPrimaryPin: true,
        isApproximate: isApproximatePinLocation(obra, false),
        bairroLabel: obra.bairro,
      });
    }
  }

  const countsByCoord = new Map<string, number>();
  for (const entry of rawEntries) {
    const coordKey = getPinCoordKey(entry.latitude, entry.longitude);
    countsByCoord.set(coordKey, (countsByCoord.get(coordKey) || 0) + 1);
  }

  return rawEntries.map((entry) => {
    const coordKey = getPinCoordKey(entry.latitude, entry.longitude);
    return {
      ...entry,
      overlapCount: countsByCoord.get(coordKey) || 1,
    };
  });
}

function getPinCoordKey(latitude: number, longitude: number): string {
  return `${latitude.toFixed(4)}_${longitude.toFixed(4)}`;
}

function formatPinMetricLabel(obra: ObraCompacta, metricType: MetricType, isCotaPin: boolean): string {
  const prefix = isCotaPin ? "Total contrato — " : "";
  if (metricType === "executado") {
    const rotulo = obra.apuracaoPagamentos?.limitacoesConhecidas?.length ? "Soma parcial" : "Pago";
    return hasNumericValue(obra.valorPago)
      ? `${prefix}${rotulo}: ${formatCurrency(obra.valorPago)}`
      : `${prefix}Pagamento indisponível`;
  }
  return `${prefix}Contratual: ${formatCurrency(obra.valorContratualVigente)}`;
}

export const SALVADOR_CENTER: L.LatLngTuple = [-12.88, -38.48];
export const SALVADOR_DEFAULT_ZOOM = 11;

/**
 * Enquadra e recentraliza o mapa Leaflet na visão padrão de Salvador com invalidateSize.
 *
 * @summary Helper de recentralização garantida reutilizado na inicialização, alternância de camada e reset.
 * @param map - Instância do mapa Leaflet ou null/undefined.
 */
export function recenterMap(map: L.Map | null | undefined): void {
  if (!map) return;
  try {
    map.stop();
    map.invalidateSize({ pan: false });
    map.setView(SALVADOR_CENTER, SALVADOR_DEFAULT_ZOOM);
  } catch { }
}

interface InteractiveMapProps {
  activeLayer: "bairros" | "prefeituras";
  onToggleLayer?: (layer: "bairros" | "prefeituras") => void;
  bairros: BairroResumo[];
  prefeituras: PrefeituraBairroResumo[];
  bairrosGeoJson: any;
  prefeiturasGeoJson: any;
  obras: ObraCompacta[];
  selectedTerritory: TerritorySelection | null;
  onSelectTerritory: (territorio: TerritorySelection) => void;
  onSelectObra?: (obra: ObraCompacta) => void;
  metricType?: MetricType;
  territorySearch?: string;
  onOpenNotaMetodologica?: () => void;
  isVisible?: boolean;
  isDesktopDrawerExpanded?: boolean;
}

function focusSelectedLayerAndGetBounds(
  geoLayer: L.GeoJSON | null,
  selectedTerritory: TerritorySelection | null
): L.LatLngBounds | null {
  if (!geoLayer || !selectedTerritory) return null;
  const selectedKey = normalizeName(selectedTerritory.nome);
  let foundBounds: L.LatLngBounds | null = null;

  geoLayer.eachLayer((featureLayer: any) => {
    const featureProps = featureLayer.feature?.properties || {};
    const itemNome =
      featureProps.nome || featureProps.NM_BAIRRO || featureProps.NM_PREFEITURA_BAIRRO || "";
    if (normalizeName(itemNome) === selectedKey) {
      try {
        featureLayer.bringToFront?.();
      } catch { }
      if (typeof featureLayer.getBounds === "function") {
        try {
          const bounds = featureLayer.getBounds();
          if (bounds && (bounds as L.LatLngBounds).isValid()) {
            if (!foundBounds) {
              foundBounds = bounds;
            } else {
              foundBounds.extend(bounds);
            }
          }
        } catch { }
      }
    }
  });

  return foundBounds;
}

/**
 * Calcula as opções de enquadramento (`fitBounds`) do Leaflet considerando o drawer flutuante no desktop.
 */
export function getFitBoundsOptions(
  mapWidth: number,
  isDesktopDrawerExpanded: boolean
): L.FitBoundsOptions {
  if (isDesktopDrawerExpanded && mapWidth >= 640) {
    return {
      maxZoom: 14,
      paddingTopLeft: [24, 56],
      paddingBottomRight: [Math.min(380, Math.round(mapWidth * 0.48)), 24],
    };
  }
  return {
    maxZoom: 14,
    padding: [40, 40],
  };
}

function frameMapViewport(
  map: L.Map,
  geoLayer: L.GeoJSON | null,
  selectedTerritory: TerritorySelection | null,
  isDesktopDrawerExpanded: boolean,
  containerEl: HTMLDivElement | null
): void {
  if (selectedTerritory) {
    const foundBounds = focusSelectedLayerAndGetBounds(geoLayer, selectedTerritory);
    if (foundBounds && foundBounds.isValid()) {
      try {
        const sizeX = typeof map.getSize === "function" ? map.getSize()?.x : 0;
        const mapWidth = sizeX || containerEl?.clientWidth || 0;
        map.fitBounds(foundBounds, getFitBoundsOptions(mapWidth, isDesktopDrawerExpanded));
        return;
      } catch { }
    }
  }
  recenterMap(map);
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
  if (valor < 0) return "#be123c";
  if (valor === 0) return "#f1f5f9";
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
 * coloridos pelo Investimento por Habitante (R$/hab) ou pelo Índice de Vulnerabilidade social sobre
 * o basemap CartoDB Positron. Exclui as 3 Zonas Especiais Não-Residenciais da escala per capita,
 * plotando também os pinos georreferenciados das Obras Públicas coloridos pelo Semáforo da Obra.
 *
 * @param props - Propriedades de configuração do mapa, dados geográficos e obras filtradas.
 * @returns Elemento JSX com controles do mapa, legenda coroplética e painel de pinos.
 */
export const InteractiveMap: React.FC<InteractiveMapProps> = ({
  activeLayer,
  bairros = [],
  prefeituras = [],
  bairrosGeoJson,
  prefeiturasGeoJson,
  obras,
  selectedTerritory,
  onSelectTerritory,
  onSelectObra,
  metricType = "vigente",
  territorySearch = "",
  onOpenNotaMetodologica,
  isVisible = true,
  isDesktopDrawerExpanded = false,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const leafletMapRef = useRef<L.Map | null>(null);
  const geoJsonLayerRef = useRef<L.GeoJSON | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const selectedTerritoryRef = useRef<TerritorySelection | null>(selectedTerritory);
  selectedTerritoryRef.current = selectedTerritory;
  const prevLayerRef = useRef<"bairros" | "prefeituras" | null>(null);
  const prevSelectedRef = useRef<TerritorySelection | null>(null);
  const prevVisibleRef = useRef<boolean>(isVisible);
  const isVisibleRef = useRef<boolean>(isVisible);
  isVisibleRef.current = isVisible;
  const isDesktopDrawerExpandedRef = useRef<boolean>(isDesktopDrawerExpanded);
  isDesktopDrawerExpandedRef.current = isDesktopDrawerExpanded;
  const needsViewportSyncWhenVisibleRef = useRef<boolean>(!isVisible);

  const [choroplethMetric, setChoroplethMetric] = useState<ChoroplethMetric>("investimentoPorHabitante");
  const [showPins, setShowPins] = useState<boolean>(false);
  const normalizedSearch = normalizeName(territorySearch);
  const hasSearch = normalizedSearch.length > 0;

  const mapPinEntries = useMemo(
    () => buildMapPinEntries(obras, selectedTerritory),
    [obras, selectedTerritory]
  );

  // Inicialização do Leaflet centrada em Salvador
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (leafletMapRef.current) return;

    let t1: any;
    let t2: any;

    try {
      const map = L.map(mapContainerRef.current, {
        center: SALVADOR_CENTER,
        zoom: SALVADOR_DEFAULT_ZOOM,
        zoomControl: false,
      });

      L.control.zoom({ position: "bottomleft" }).addTo(map);

      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
        className: "map-tiles-monochrome",
      }).addTo(map);

      leafletMapRef.current = map;

      // Garante enquadramento preciso no layout inicial e após estabilização do container
      recenterMap(map);
      t1 = setTimeout(() => recenterMap(map), 100);
      t2 = setTimeout(() => recenterMap(map), 300);
    } catch { }

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      if (leafletMapRef.current) {
        try {
          leafletMapRef.current.remove();
        } catch { }
        leafletMapRef.current = null;
        geoJsonLayerRef.current = null;
        markersLayerRef.current = null;
      }
    };
  }, []);

  // Observador de redimensionamento do container
  useEffect(() => {
    if (!mapContainerRef.current || typeof ResizeObserver === "undefined") return;

    const ro = new ResizeObserver(() => {
      const map = leafletMapRef.current;
      if (!map) return;
      if (selectedTerritoryRef.current) {
        try {
          map.invalidateSize({ pan: false });
        } catch { }
      } else {
        recenterMap(map);
      }
    });

    ro.observe(mapContainerRef.current);

    return () => {
      ro.disconnect();
    };
  }, []);

  // Ao tornar o mapa visível (ex: alternância Lista -> Mapa no celular), recalcula tamanho
  // e só reenquadra se a seleção/camada ainda não tiver sido enquadrada visivelmente (preservando pan/zoom manual)
  useEffect(() => {
    const becameVisible = isVisible && !prevVisibleRef.current;
    prevVisibleRef.current = isVisible;
    if (!becameVisible) return;

    const map = leafletMapRef.current;
    if (!map) return;

    try {
      map.invalidateSize({ pan: false });
      if (needsViewportSyncWhenVisibleRef.current) {
        needsViewportSyncWhenVisibleRef.current = false;
        frameMapViewport(
          map,
          geoJsonLayerRef.current,
          selectedTerritoryRef.current,
          isDesktopDrawerExpandedRef.current,
          mapContainerRef.current
        );
      }
    } catch { }
  }, [isVisible]);

  // Mapas indexados por nome normalizado para lookup dinâmico do recálculo territorial
  const currentBairroMap = useMemo(() => {
    const m = new Map<string, BairroResumo>();
    bairros.forEach((bairro) => {
      m.set(normalizeName(bairro.nome), bairro);
    });
    return m;
  }, [bairros]);

  const currentPrefeituraMap = useMemo(() => {
    const m = new Map<string, PrefeituraBairroResumo>();
    prefeituras.forEach((prefeitura) => {
      m.set(normalizeName(prefeitura.nome), prefeitura);
    });
    return m;
  }, [prefeituras]);

  // Calcula os limites de quantis para a escala coroplética de Investimento por Habitante (vigente ou executado)
  const {
    breaksInvestimento,
    hasUnavailablePayment,
    hasUnavailablePopulation,
    hasUnavailableVulnerability,
  } = useMemo(() => {
    const list = activeLayer === "bairros" ? bairros : prefeituras;
    const tipo = activeLayer === "bairros" ? "bairro" : "prefeitura_bairro";
    let unavailablePayment = false;
    let unavailablePopulation = false;
    let unavailableVuln = false;
    const valores: number[] = [];

    for (const item of list) {
      const state = getTerritoryInvestmentState(item, metricType, tipo);
      if (state.kind === "unavailable") {
        if (state.reason === "population") unavailablePopulation = true;
        else unavailablePayment = true;
      } else if (state.kind === "value" && state.perCapita > 0) {
        valores.push(state.perCapita);
      }

      const isExemptVuln = activeLayer === "bairros" && isZonaEspecial(item as BairroResumo);
      if (!isExemptVuln && !hasNumericValue(item.indice_vulnerabilidade)) {
        unavailableVuln = true;
      }
    }

    valores.sort((a, b) => a - b);
    if (valores.length === 0) {
      return {
        breaksInvestimento: [20, 50, 100, 200],
        hasUnavailablePayment: unavailablePayment,
        hasUnavailablePopulation: unavailablePopulation,
        hasUnavailableVulnerability: unavailableVuln,
      };
    }

    const q = (p: number) => valores[Math.floor((valores.length - 1) * p)];
    return {
      breaksInvestimento: [q(0.2), q(0.4), q(0.6), q(0.8)],
      hasUnavailablePayment: unavailablePayment,
      hasUnavailablePopulation: unavailablePopulation,
      hasUnavailableVulnerability: unavailableVuln,
    };
  }, [activeLayer, bairros, prefeituras, metricType]);

  // Atualização dos polígonos GeoJSON no Leaflet
  useEffect(() => {
    const map = leafletMapRef.current;
    if (!map) return;

    if (geoJsonLayerRef.current) {
      try {
        map.removeLayer(geoJsonLayerRef.current);
      } catch { }
      geoJsonLayerRef.current = null;
    }

    const geoData = activeLayer === "bairros" ? bairrosGeoJson : prefeiturasGeoJson;
    if (!geoData || !geoData.features) return;

    const layerChanged = prevLayerRef.current !== activeLayer;
    const currentSelectedKey = selectedTerritory
      ? `${selectedTerritory.tipo}:${normalizeName(selectedTerritory.nome)}`
      : null;
    const prevSelectedKey = prevSelectedRef.current
      ? `${prevSelectedRef.current.tipo}:${normalizeName(prevSelectedRef.current.nome)}`
      : null;
    const selectionChanged = currentSelectedKey !== prevSelectedKey;
    const selectionCleared = prevSelectedRef.current !== null && selectedTerritory === null;
    prevLayerRef.current = activeLayer;
    prevSelectedRef.current = selectedTerritory;

    const isFeatureSearchMatch = (
      lookupKey: string,
      dynamicBairro?: BairroResumo,
      dynamicPrefeitura?: PrefeituraBairroResumo
    ): boolean => {
      if (!hasSearch) return false;
      return (
        lookupKey.includes(normalizedSearch) ||
        (dynamicBairro !== undefined && normalizeName(dynamicBairro.nome).includes(normalizedSearch)) ||
        (dynamicPrefeitura !== undefined &&
          normalizeName(dynamicPrefeitura.nome).includes(normalizedSearch))
      );
    };

    try {
      const layer = L.geoJSON(geoData, {
        style: (feature) => {
          const props = feature?.properties || {};
          const rawNome = (props.nome || props.NM_BAIRRO || props.NM_PREFEITURA_BAIRRO || "").trim();
          const lookupKey = normalizeName(rawNome);
          const dynamicBairro = activeLayer === "bairros" ? currentBairroMap.get(lookupKey) : undefined;
          const dynamicPrefeitura = activeLayer === "prefeituras" ? currentPrefeituraMap.get(lookupKey) : undefined;

          const isSelected =
            selectedTerritory !== null &&
            (normalizeName(selectedTerritory.nome) === lookupKey ||
              (dynamicBairro && normalizeName(selectedTerritory.nome) === normalizeName(dynamicBairro.nome)) ||
              (dynamicPrefeitura && normalizeName(selectedTerritory.nome) === normalizeName(dynamicPrefeitura.nome)));

          const isSearchMatch = isFeatureSearchMatch(lookupKey, dynamicBairro, dynamicPrefeitura);

          const isZonaEspecial = dynamicBairro
            ? !!(dynamicBairro.is_zona_especial_nao_residencial || dynamicBairro.isZonaEspecialNaoResidencial)
            : !!(props.is_zona_especial_nao_residencial || props.isZonaEspecialNaoResidencial);
          const isCentralidade =
            activeLayer === "bairros" &&
            !isZonaEspecial &&
            (dynamicBairro
              ? isCentralidadeMetropolitana(dynamicBairro)
              : isCentralidadeMetropolitana({
                  nome: rawNome,
                  is_centralidade_metropolitana: props.is_centralidade_metropolitana,
                  isCentralidadeMetropolitana: props.isCentralidadeMetropolitana,
                }));
          const isExemptInCurrentLayer =
            isZonaEspecial || (choroplethMetric === "investimentoPorHabitante" && isCentralidade);

          let fillColor = "#cbd5e1";
          let isUnavailable = false;

          if (isExemptInCurrentLayer) {
            fillColor = "#fef3c7";
          } else if (choroplethMetric === "investimentoPorHabitante") {
            const targetItem = activeLayer === "bairros" ? dynamicBairro : dynamicPrefeitura;
            if (targetItem) {
              const state = getTerritoryInvestmentState(
                targetItem,
                metricType,
                activeLayer === "bairros" ? "bairro" : "prefeitura_bairro"
              );
              if (state.kind === "unavailable") {
                fillColor = "#e2e8f0";
                isUnavailable = true;
              } else if (state.kind === "exempt") {
                fillColor = "#fef3c7";
              } else {
                fillColor = getInvestimentoColor(state.perCapita, breaksInvestimento);
              }
            } else {
              const fallbackProp =
                metricType === "executado"
                  ? props.investimentoPorHabitantePago
                  : props.investimentoPorHabitante;
              if (typeof fallbackProp === "number") {
                fillColor = getInvestimentoColor(fallbackProp, breaksInvestimento);
              } else {
                fillColor = "#e2e8f0";
                isUnavailable = true;
              }
            }
          } else {
            const vuln =
              dynamicBairro?.indice_vulnerabilidade ??
              dynamicPrefeitura?.indice_vulnerabilidade ??
              props.indice_vulnerabilidade;
            if (typeof vuln === "number" && !Number.isNaN(vuln)) {
              fillColor = getVulnerabilidadeColor(vuln);
            } else {
              fillColor = "#e2e8f0";
              isUnavailable = true;
            }
          }

          return {
            fillColor: isSelected ? "#10B981" : fillColor,
            weight: isSelected ? 3.5 : isSearchMatch ? 3.0 : 1.2,
            opacity: isSelected || !hasSearch || isSearchMatch ? 1 : 0.45,
            color: isSelected
              ? "#064e3b"
              : isSearchMatch
                ? "#0369a1"
                : isExemptInCurrentLayer
                  ? "#d97706"
                  : isUnavailable
                    ? "#64748b"
                    : "#ffffff",
            dashArray: !isSelected && isUnavailable ? "4 3" : undefined,
            fillOpacity: isSelected ? 0.8 : hasSearch ? (isSearchMatch ? 0.78 : 0.2) : 0.65,
          };
        },
        onEachFeature: (feature, layerItem) => {
          const props = feature.properties || {};
          const rawNome = (props.nome || props.NM_BAIRRO || props.NM_PREFEITURA_BAIRRO || "").trim();
          const lookupKey = normalizeName(rawNome);
          const dynamicBairro = activeLayer === "bairros" ? currentBairroMap.get(lookupKey) : undefined;
          const dynamicPrefeitura = activeLayer === "prefeituras" ? currentPrefeituraMap.get(lookupKey) : undefined;
          const isZonaEspecial = dynamicBairro
            ? !!(dynamicBairro.is_zona_especial_nao_residencial || dynamicBairro.isZonaEspecialNaoResidencial)
            : !!(props.is_zona_especial_nao_residencial || props.isZonaEspecialNaoResidencial);
          const isCentralidade =
            activeLayer === "bairros" &&
            !isZonaEspecial &&
            (dynamicBairro
              ? isCentralidadeMetropolitana(dynamicBairro)
              : isCentralidadeMetropolitana({
                  nome: rawNome,
                  is_centralidade_metropolitana: props.is_centralidade_metropolitana,
                  isCentralidadeMetropolitana: props.isCentralidadeMetropolitana,
                }));

          layerItem.on({
            click: () => {
              if (activeLayer === "bairros") {
                const b: BairroResumo = dynamicBairro || bairros.find((item) => item.nome === rawNome) || {
                  id: props.id || 0,
                  nome: rawNome,
                  prefeitura_bairro: props.prefeitura_bairro || "",
                  populacao: props.populacao || 0,
                  indice_vulnerabilidade: props.indice_vulnerabilidade,
                  is_zona_especial_nao_residencial: isZonaEspecial,
                  is_centralidade_metropolitana: isCentralidade,
                  valorTotal: props.valorTotal,
                  valorPago: props.valorPago,
                  valorPagoDisponivel: props.valorPagoDisponivel,
                  obrasSemValorPago: props.obrasSemValorPago,
                  limitacoesConhecidas: props.limitacoesConhecidas,
                  totalObras: props.totalObras,
                  obrasVerde: props.obrasVerde,
                  obrasAmarelo: props.obrasAmarelo,
                  obrasVermelho: props.obrasVermelho,
                  investimentoPorHabitante: props.investimentoPorHabitante,
                  investimentoPorHabitantePago: props.investimentoPorHabitantePago,
                };
                onSelectTerritory(createBairroSelection(b));
              } else {
                const pb: PrefeituraBairroResumo = dynamicPrefeitura || prefeituras.find((item) => item.nome === rawNome) || {
                  id: props.id || 0,
                  nome: rawNome,
                  populacao_total: props.populacao_total || 0,
                  indice_vulnerabilidade: props.indice_vulnerabilidade,
                  valorTotal: props.valorTotal,
                  valorPago: props.valorPago,
                  valorPagoDisponivel: props.valorPagoDisponivel,
                  obrasSemValorPago: props.obrasSemValorPago,
                  limitacoesConhecidas: props.limitacoesConhecidas,
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

      try {
        layer.addTo(map);
      } catch { }
      geoJsonLayerRef.current = layer;

      if (hasSearch || selectedTerritory) {
        if (hasSearch) {
          layer.eachLayer((featureLayer: any) => {
            const featureProps = featureLayer.feature?.properties || {};
            const itemNome =
              featureProps.nome || featureProps.NM_BAIRRO || featureProps.NM_PREFEITURA_BAIRRO || "";
            const lookupKey = normalizeName(itemNome);
            const dynamicBairro = activeLayer === "bairros" ? currentBairroMap.get(lookupKey) : undefined;
            const dynamicPrefeitura =
              activeLayer === "prefeituras" ? currentPrefeituraMap.get(lookupKey) : undefined;

            if (isFeatureSearchMatch(lookupKey, dynamicBairro, dynamicPrefeitura)) {
              try {
                featureLayer.bringToFront?.();
              } catch { }
            }
          });
        }

        if (selectedTerritory) {
          if (selectionChanged || layerChanged) {
            if (!isVisibleRef.current) {
              focusSelectedLayerAndGetBounds(layer, selectedTerritory);
              needsViewportSyncWhenVisibleRef.current = true;
            } else {
              frameMapViewport(
                map,
                layer,
                selectedTerritory,
                isDesktopDrawerExpandedRef.current,
                mapContainerRef.current
              );
            }
          } else {
            focusSelectedLayerAndGetBounds(layer, selectedTerritory);
          }
        }
      } else if (layerChanged || selectionCleared) {
        if (!isVisibleRef.current) {
          needsViewportSyncWhenVisibleRef.current = true;
        } else {
          recenterMap(map);
        }
      }
    } catch { }
  }, [
    activeLayer,
    bairrosGeoJson,
    prefeiturasGeoJson,
    selectedTerritory,
    choroplethMetric,
    metricType,
    breaksInvestimento,
    bairros,
    prefeituras,
    onSelectTerritory,
    currentBairroMap,
    currentPrefeituraMap,
    hasSearch,
    normalizedSearch,
  ]);

  // Renderização dos Pinos de Obras Públicas com dispersão determinística anti-sobreposição
  useEffect(() => {
    const map = leafletMapRef.current;
    if (!map) return;

    if (markersLayerRef.current) {
      try {
        map.removeLayer(markersLayerRef.current);
      } catch { }
      markersLayerRef.current = null;
    }

    if (!showPins) return;

    try {
      const markersGroup = L.layerGroup();

      // Agrupa pinos com coordenadas idênticas para aplicar dispersão radial
      const entriesPorCoord: Record<string, MapPinEntry[]> = {};
      for (const entry of mapPinEntries) {
        const coordKey = getPinCoordKey(entry.latitude, entry.longitude);
        if (!entriesPorCoord[coordKey]) entriesPorCoord[coordKey] = [];
        entriesPorCoord[coordKey].push(entry);
      }

      for (const coordGroup of Object.values(entriesPorCoord)) {
        const total = coordGroup.length;
        coordGroup.forEach((entry, idx) => {
          const { obra } = entry;
          let lat = entry.latitude;
          let lon = entry.longitude;

          // Se houver mais de um pino no mesmo ponto exato/centróide, aplica dispersão circular
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
            color: entry.isApproximate ? "#0f172a" : "#ffffff",
            weight: 1.5,
            dashArray: entry.isApproximate ? "3 2" : undefined,
            opacity: 1,
            fillOpacity: entry.isApproximate ? 0.8 : 0.92,
          });

          const valorPinText = formatPinMetricLabel(obra, metricType, Boolean(entry.fracao));

          const precisionText = entry.isApproximate
            ? "Local aproximado (centróide do bairro — não é endereço exato)"
            : "Ponto identificado (localização pontual/equipamento)";

          const overlapText =
            total > 1
              ? `<br/><span style="color: #0369a1; font-size: 10px; font-weight: 600;">Ponto compartilhado com outras ${total - 1} obra(s) — acesse todas na lista de pinos</span>`
              : "";

          const tooltipContent = `
            <div style="font-size: 11px; max-width: 240px;">
              <strong style="color: #0f172a;">${obra.objeto}</strong><br/>
              <span style="color: #64748b;">${obra.unidadeGestora} • ${valorPinText}</span><br/>
              <span style="font-weight: 600; color: ${corPino};">Semáforo: ${obra.semaforo?.rotulo || status}</span>
              ${entry.fracao ? `<br/><span style="color: #0f766e; font-size: 10px; font-weight: 600;">Cota-Parte (${entry.fracao})${entry.bairroLabel ? ` • ${entry.bairroLabel}` : ""}</span>` : ""}
              <br/><span style="color: ${entry.isApproximate ? "#b45309" : "#047857"}; font-size: 10px; font-weight: 600;">${precisionText}</span>
              ${overlapText}
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
    } catch { }
  }, [mapPinEntries, showPins, onSelectObra, metricType]);

  const handleRecenter = () => {
    recenterMap(leafletMapRef.current);
  };

  const searchMatches = useMemo(() => {
    if (!hasSearch) return [];
    const list = activeLayer === "bairros" ? bairros : prefeituras;
    return list.filter((item) => normalizeName(item.nome).includes(normalizedSearch));
  }, [activeLayer, bairros, prefeituras, hasSearch, normalizedSearch]);

  const [b0, b1, b2, b3] = breaksInvestimento;
  const formatLegendaBreak = (v: number) =>
    v >= 1000 ? formatCompactCurrency(Math.round(v)) : `R$ ${Math.round(v)}`;
  const metricSubtitle =
    metricType === "executado" ? "Valor Pago (R$/hab)" : "Valor Contratual Vigente (R$/hab)";

  return (
      <div className="relative flex-1 min-w-0 overflow-hidden flex flex-col h-full bg-slate-100">
        {/* Área do Mapa: no celular (<sm), controles acima e legenda abaixo evitam cobrir o mapa e os botões de zoom */}
        <div className="relative flex-1 min-w-0 overflow-hidden flex flex-col sm:block sm:h-full sm:min-h-[390px] w-full">
        {/* Controles Superiores do Mapa */}
        <div className="p-2 bg-slate-50 border-b border-slate-200 sm:p-0 sm:bg-transparent sm:border-b-0 sm:absolute sm:top-2.5 sm:left-2.5 sm:right-2.5 z-[400] sm:pointer-events-none flex flex-wrap items-center gap-1.5">
        <div className="pointer-events-auto sm:bg-white/95 sm:backdrop-blur-sm sm:p-1.5 sm:rounded-xl sm:shadow-md sm:border sm:border-slate-200/80 flex flex-wrap items-center gap-1.5 max-w-full">
          {/* Alternância de Métrica Coroplética */}
          <div
            data-testid="toggle-camada-metrica"
            role="group"
            aria-label="Métrica coroplética do mapa"
            className="flex flex-wrap bg-slate-100 p-1 rounded-lg border border-slate-200 max-w-full"
          >
            <button
              type="button"
              data-testid="btn-camada-per-capita"
              aria-pressed={choroplethMetric === "investimentoPorHabitante"}
              onClick={() => setChoroplethMetric("investimentoPorHabitante")}
              className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 ${choroplethMetric === "investimentoPorHabitante"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
                }`}
            >
              R$ / Habitante
            </button>
            <button
              type="button"
              data-testid="btn-camada-vulnerabilidade"
              aria-pressed={choroplethMetric === "vulnerabilidade"}
              onClick={() => setChoroplethMetric("vulnerabilidade")}
              className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 ${choroplethMetric === "vulnerabilidade"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
                }`}
            >
              Vulnerabilidade Social
            </button>
          </div>

          {/* Botão de Como é calculado? */}
          {onOpenNotaMetodologica && (
            <button
              type="button"
              data-testid="btn-como-calculado-mapa"
              onClick={onOpenNotaMetodologica}
              title="Como é calculado o Índice de Vulnerabilidade?"
              className="px-2.5 py-1 text-xs font-medium bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-lg text-indigo-700 hover:text-indigo-900 transition-colors flex items-center gap-1 shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
            >
              <span className="font-bold">ⓘ</span>
              <span>Como é calculado?</span>
            </button>
          )}

          {/* Toggle de Pinos de Obras */}
          <button
            type="button"
            data-testid="btn-toggle-pinos-obras"
            aria-pressed={showPins}
            onClick={() => setShowPins((prev) => !prev)}
            className={`px-2.5 py-1 text-xs font-semibold rounded-lg border transition-all flex items-center gap-1.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 ${showPins
                ? "bg-slate-900 text-white border-slate-900"
                : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
              }`}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            Pinos de Obras ({mapPinEntries.length})
          </button>

          {/* Botão de Recentralizar */}
          <button
            type="button"
            data-testid="btn-centralizar-salvador"
            onClick={handleRecenter}
            title="Recentralizar visualização em Salvador"
            className="px-2.5 py-1 text-xs font-medium bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-slate-700 transition-colors flex items-center gap-1 shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
          >
            <svg className="w-3.5 h-3.5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Centralizar
          </button>

          {hasSearch && (
            <span
              data-testid="mapa-destaque-busca"
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-sky-50 text-sky-900 border border-sky-200"
            >
              {searchMatches.length === 0
                ? `Nenhuma correspondência no mapa para "${territorySearch.trim()}"`
                : searchMatches.length === 1
                  ? `1 correspondência destacada: ${searchMatches[0].nome}`
                  : `${searchMatches.length} correspondências destacadas no mapa`}
            </span>
          )}
        </div>
        </div>

        {/* Container Leaflet do Mapa */}
        <div
          ref={mapContainerRef}
          data-testid="leaflet-map-container"
          className="w-full h-[300px] sm:h-[405px] md:h-full min-h-[280px] sm:min-h-[380px] z-0 relative"
        />

        {/* Legenda Coroplética com intervalos quantitativos e unidade */}
        <div
          data-testid="legenda-coropletica"
          className="sm:absolute sm:bottom-2.5 sm:left-14 z-[400] bg-white/95 backdrop-blur-sm p-2 sm:rounded-xl sm:shadow-md border-t sm:border border-slate-200 text-xs sm:max-w-[270px]"
        >
          <span className="font-bold text-slate-800 block mb-1.5 text-[11px] leading-tight">
            {choroplethMetric === "investimentoPorHabitante"
              ? `Investimento por Habitante — ${metricSubtitle}`
              : "Índice de Vulnerabilidade (0,00 a 1,00)"}
          </span>
          {choroplethMetric === "investimentoPorHabitante" ? (
            <div className="grid grid-cols-2 gap-x-2.5 gap-y-1 text-[10px] text-slate-700 tabular-nums">
              {metricType === "executado" && <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-[#be123c] shrink-0" />
                <span>Saldo negativo</span>
              </div>}
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-[#f1f5f9] border border-slate-300 shrink-0" />
                <span>R$ 0 / hab</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-[#d1fae5] border border-emerald-200 shrink-0" />
                <span>&lt; {formatLegendaBreak(b0)}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-[#6ee7b7] shrink-0" />
                <span>{formatLegendaBreak(b0)}–{formatLegendaBreak(b1)}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-[#10b981] shrink-0" />
                <span>{formatLegendaBreak(b1)}–{formatLegendaBreak(b2)}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-[#059669] shrink-0" />
                <span>{formatLegendaBreak(b2)}–{formatLegendaBreak(b3)}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-[#064e3b] shrink-0" />
                <span>≥ {formatLegendaBreak(b3)}</span>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-x-2.5 gap-y-1 text-[10px] text-slate-700 tabular-nums">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-[#ede9fe] border border-violet-200 shrink-0" />
                <span>0,00–0,19</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-[#c4b5fd] shrink-0" />
                <span>0,20–0,39</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-[#8b5cf6] shrink-0" />
                <span>0,40–0,59</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-[#6d28d9] shrink-0" />
                <span>0,60–0,79</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-[#4c1d95] shrink-0" />
                <span>0,80–1,00</span>
              </div>
            </div>
          )}
          {(activeLayer === "bairros" ||
            (choroplethMetric === "investimentoPorHabitante" &&
              (hasUnavailablePayment || hasUnavailablePopulation)) ||
            (choroplethMetric === "vulnerabilidade" && hasUnavailableVulnerability)) && (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 pt-1 border-t border-slate-100 text-[10px]">
              {activeLayer === "bairros" && (
                <div className="flex items-center gap-1 text-amber-800">
                  <span className="w-3 h-3 rounded-sm bg-[#fef3c7] border border-amber-400 shrink-0" />
                  <span>Isento</span>
                </div>
              )}
              {choroplethMetric === "investimentoPorHabitante" && hasUnavailablePayment && (
                <div className="flex items-center gap-1 text-slate-700">
                  <span className="w-3 h-3 rounded-sm bg-[#e2e8f0] border border-dashed border-slate-500 shrink-0" />
                  <span>Sem pagamento</span>
                </div>
              )}
              {((choroplethMetric === "investimentoPorHabitante" && hasUnavailablePopulation) ||
                (choroplethMetric === "vulnerabilidade" && hasUnavailableVulnerability)) && (
                <div className="flex items-center gap-1 text-slate-700">
                  <span className="w-3 h-3 rounded-sm bg-[#e2e8f0] border border-dashed border-slate-500 shrink-0" />
                  <span>Dado indisponível</span>
                </div>
              )}
            </div>
          )}
        </div>
        </div>

        {/* Painel acessível de pinos ativos: expõe obras sobrepostas e distingue locais aproximados */}
        {showPins && (
          <div
            data-testid="painel-pinos-obras"
            aria-label="Lista acessível de obras com pinos no mapa"
            className="w-full min-w-0 bg-slate-50 border-t border-slate-200 px-3 py-2.5 space-y-2 shrink-0"
          >
            <div
              data-testid="aviso-precisao-pinos"
              className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-700"
            >
              <span>
                <strong>Pinos ativos ({mapPinEntries.length}):</strong>{" "}
                <span className="text-amber-900 font-medium">
                  locais aproximados (nível Bairro/Prefeitura-Bairro) indicam o centróide do território e não são endereços exatos.
                </span>
                {mapPinEntries.some((entry) => entry.overlapCount > 1) && (
                  <span className="text-sky-900 font-medium">
                    {" "}
                    Obras sobrepostas no mesmo ponto estão listadas abaixo para acesso individual.
                  </span>
                )}
              </span>
            </div>

            {mapPinEntries.length === 0 ? (
              <p className="text-xs text-slate-500">
                Nenhuma obra deste recorte possui coordenada georreferenciada para exibir pino no mapa.
              </p>
            ) : (
              <div className="max-h-36 overflow-y-auto space-y-1.5 pr-0.5">
                {mapPinEntries.map((entry) => {
                  const valorText = formatPinMetricLabel(entry.obra, metricType, Boolean(entry.fracao));

                  return (
                    <button
                      key={entry.key}
                      type="button"
                      data-testid={
                        entry.isPrimaryPin
                          ? `map-pin-obra-${entry.obra.id}`
                          : `map-pin-obra-${entry.obra.id}-extra-${entry.key}`
                      }
                      onClick={() => onSelectObra && onSelectObra(entry.obra)}
                      className="w-full text-left bg-white hover:bg-emerald-50/70 border border-slate-200 hover:border-emerald-300 rounded-lg px-2.5 py-1.5 text-xs transition-colors flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
                    >
                      <div className="min-w-0">
                        <div className="font-semibold text-slate-900 truncate">
                          {entry.obra.objeto}
                        </div>
                        <div className="flex flex-wrap items-center gap-1.5 mt-0.5 text-[10px]">
                          <span
                            className={`px-1.5 py-0.5 rounded border font-semibold ${
                              entry.isApproximate
                                ? "bg-amber-50 text-amber-900 border-amber-200"
                                : "bg-emerald-50 text-emerald-800 border-emerald-200"
                            }`}
                          >
                            {entry.isApproximate
                              ? "Local aproximado (não é endereço exato)"
                              : "Ponto identificado (Pontual)"}
                          </span>
                          {entry.overlapCount > 1 && (
                            <span className="px-1.5 py-0.5 rounded border bg-sky-50 text-sky-900 border-sky-200 font-semibold">
                              Sobreposição: {entry.overlapCount} obras no mesmo ponto
                            </span>
                          )}
                          {entry.fracao && (
                            <span className="px-1.5 py-0.5 rounded border bg-amber-50 text-amber-900 border-amber-200 font-semibold">
                              Cota-Parte ({entry.fracao}){entry.bairroLabel ? ` • ${entry.bairroLabel}` : ""}
                            </span>
                          )}
                          {!entry.fracao && entry.bairroLabel && (
                            <span className="text-slate-600">{entry.bairroLabel}</span>
                          )}
                        </div>
                      </div>
                      <div className="shrink-0 flex items-center gap-2 text-[11px]">
                        <span className="font-semibold text-slate-800 tabular-nums">{valorText}</span>
                        <span className="text-emerald-700 font-semibold underline">Ver detalhes</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}
        </div>
        );
};

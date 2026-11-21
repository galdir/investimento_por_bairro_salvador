import { MetricType, ObraCompacta } from "../types";
import {
  deduplicateObrasByCanonicalKey,
  getObraCanonicalKey,
  getObraCotasListaFechada,
  hasNumericValue,
  normalizeName,
} from "./territory";

export interface LatLngPoint {
  lat: number;
  lng: number;
}

export interface HeatmapPoint {
  latitude: number;
  longitude: number;
  value: number;
  weight: number;
}

export interface HeatmapExtractionResult {
  points: HeatmapPoint[];
  localizedObraCount: number;
}

function isValidCoordinate(lat: unknown, lng: unknown): lat is number {
  return (
    typeof lat === "number" &&
    typeof lng === "number" &&
    Number.isFinite(lat) &&
    Number.isFinite(lng) &&
    lat >= -90 &&
    lat <= 90 &&
    lng >= -180 &&
    lng <= 180 &&
    (lat !== 0 || lng !== 0)
  );
}

/**
 * Calcula área absoluta e centróide geométrico 2D (fórmula de Gauss/shoelace) de um anel [lng, lat][].
 */
function computeRingAreaAndCentroid(ring: number[][]): { area: number; centroid: LatLngPoint } | null {
  if (!Array.isArray(ring) || ring.length < 3) return null;

  let signedArea2 = 0;
  let cx = 0;
  let cy = 0;
  let sumX = 0;
  let sumY = 0;
  let validCount = 0;

  for (let i = 0; i < ring.length; i++) {
    const p1 = ring[i];
    const p2 = ring[(i + 1) % ring.length];
    if (!Array.isArray(p1) || p1.length < 2 || !Array.isArray(p2) || p2.length < 2) continue;

    const x1 = Number(p1[0]);
    const y1 = Number(p1[1]);
    const x2 = Number(p2[0]);
    const y2 = Number(p2[1]);
    if (!Number.isFinite(x1) || !Number.isFinite(y1) || !Number.isFinite(x2) || !Number.isFinite(y2)) {
      continue;
    }

    sumX += x1;
    sumY += y1;
    validCount++;

    const cross = x1 * y2 - x2 * y1;
    signedArea2 += cross;
    cx += (x1 + x2) * cross;
    cy += (y1 + y2) * cross;
  }

  if (validCount === 0) return null;

  const absArea = Math.abs(signedArea2) / 2;
  if (absArea < 1e-12) {
    return {
      area: 0,
      centroid: { lat: sumY / validCount, lng: sumX / validCount },
    };
  }

  const factor = 3 * signedArea2;
  return {
    area: absArea,
    centroid: { lat: cy / factor, lng: cx / factor },
  };
}

/**
 * Deriva no cliente os centróides de Bairros Oficiais a partir do GeoJSON já carregado,
 * tratando tanto `Polygon` quanto `MultiPolygon` (anel externo do maior polígono).
 */
export function computeBairroCentroids(bairrosGeoJson: any): Map<string, LatLngPoint> {
  const centroids = new Map<string, LatLngPoint>();
  const features = bairrosGeoJson?.features;
  if (!Array.isArray(features)) return centroids;

  for (const feature of features) {
    const props = feature?.properties || {};
    const rawNome = (props.nome || props.NM_BAIRRO || "").trim();
    const key = normalizeName(rawNome);
    if (!key) continue;

    const geometry = feature?.geometry;
    if (!geometry) continue;

    let chosenCentroid: LatLngPoint | null = null;
    if (geometry.type === "Polygon" && Array.isArray(geometry.coordinates)) {
      const outerRing = geometry.coordinates[0];
      const computed = computeRingAreaAndCentroid(outerRing);
      if (computed) chosenCentroid = computed.centroid;
    } else if (geometry.type === "MultiPolygon" && Array.isArray(geometry.coordinates)) {
      let bestArea = -1;
      for (const polyCoords of geometry.coordinates) {
        if (!Array.isArray(polyCoords) || polyCoords.length === 0) continue;
        const computed = computeRingAreaAndCentroid(polyCoords[0]);
        if (computed && computed.area > bestArea) {
          bestArea = computed.area;
          chosenCentroid = computed.centroid;
        }
      }
    }

    if (chosenCentroid && isValidCoordinate(chosenCentroid.lat, chosenCentroid.lng)) {
      centroids.set(key, chosenCentroid);
    }
  }

  return centroids;
}

function getObraMetricValue(obra: ObraCompacta, metricType: MetricType): number | null {
  const raw = metricType === "executado" ? obra.valorPago : obra.valorContratualVigente;
  return hasNumericValue(raw) && raw > 0 ? raw : null;
}

function resolvePointCoordinate(
  lat: number | null | undefined,
  lng: number | null | undefined,
  bairroName: string | null | undefined,
  centroids: ReadonlyMap<string, LatLngPoint>
): LatLngPoint | null {
  if (typeof lat === "number" && typeof lng === "number" && isValidCoordinate(lat, lng)) {
    return { lat, lng };
  }
  if (bairroName) {
    const fallback = centroids.get(normalizeName(bairroName));
    if (fallback && isValidCoordinate(fallback.lat, fallback.lng)) {
      return fallback;
    }
  }
  return null;
}

/**
 * Extrai pontos ponderados em escala logarítmica para o Mapa de Calor de Obras Localizadas.
 *
 * @summary Aplica precedência de frentesMedicao sobre cotasListaFechada, agrega frentes por (obra, bairro)
 * apenas em Valor Pago, exclui contratos regionais e Escopo Cidade sem frentes de bairro e normaliza
 * pesos via `Math.log10(1 + valor)` no intervalo `[0, 1]`.
 */
export function extractHeatmapPoints(
  obras: ObraCompacta[],
  centroids: ReadonlyMap<string, LatLngPoint>,
  metricType: MetricType
): HeatmapExtractionResult {
  const uniqueObras = deduplicateObrasByCanonicalKey(obras);
  const rawPoints: Array<{ latitude: number; longitude: number; value: number }> = [];
  const countedCanonicalKeys = new Set<string>();

  for (const obra of uniqueObras) {
    const canonicalKey = getObraCanonicalKey(obra);
    const nivel = obra.nivel || "Escopo Cidade (Não-Localizado)";
    const cotasValidas = getObraCotasListaFechada(obra);

    if (cotasValidas.length > 0) {
      const baseValue = getObraMetricValue(obra, metricType);
      if (baseValue !== null) {
        for (const cota of cotasValidas) {
          const proportionalValue = baseValue * Number(cota.peso);
          if (!(proportionalValue > 0)) continue;

          const coord = resolvePointCoordinate(
            cota.latitude,
            cota.longitude,
            cota.bairro,
            centroids
          );
          if (coord) {
            rawPoints.push({ latitude: coord.lat, longitude: coord.lng, value: proportionalValue });
            countedCanonicalKeys.add(canonicalKey);
          }
        }
      }
    } else if (nivel === "Pontual" || nivel === "Bairro") {
      const directValue = getObraMetricValue(obra, metricType);
      if (directValue !== null) {
        const coord = resolvePointCoordinate(
          obra.latitude,
          obra.longitude,
          obra.bairro,
          centroids
        );
        if (coord) {
          rawPoints.push({ latitude: coord.lat, longitude: coord.lng, value: directValue });
          countedCanonicalKeys.add(canonicalKey);
        }
      }
    }

    // Frentes de Medição de nível Pontual/Bairro entram somente em Valor Pago, agregadas por (obra, bairro)
    if (metricType === "executado" && Array.isArray(obra.frentesMedicao) && obra.frentesMedicao.length > 0) {
      const aggregatedByBairro = new Map<string, number>();
      for (const frente of obra.frentesMedicao) {
        const fNivel = frente.nivel;
        if ((fNivel !== "Pontual" && fNivel !== "Bairro") || !frente.bairro) continue;
        if (!hasNumericValue(frente.valorPago) || frente.valorPago <= 0) continue;

        const bairroKey = normalizeName(frente.bairro);
        if (!bairroKey) continue;
        aggregatedByBairro.set(bairroKey, (aggregatedByBairro.get(bairroKey) || 0) + frente.valorPago);
      }

      for (const [bairroKey, totalPago] of aggregatedByBairro.entries()) {
        if (!(totalPago > 0)) continue;
        const coord = centroids.get(bairroKey);
        if (coord && isValidCoordinate(coord.lat, coord.lng)) {
          rawPoints.push({ latitude: coord.lat, longitude: coord.lng, value: totalPago });
          countedCanonicalKeys.add(canonicalKey);
        }
      }
    }
  }

  if (rawPoints.length === 0) {
    return { points: [], localizedObraCount: 0 };
  }

  const maxLog = rawPoints.reduce((max, pt) => {
    const logValue = Math.log10(1 + pt.value);
    return logValue > max ? logValue : max;
  }, 0);

  const points: HeatmapPoint[] = rawPoints.map((pt) => ({
    ...pt,
    weight: maxLog > 0 ? Math.log10(1 + pt.value) / maxLog : 0,
  }));

  return {
    points,
    localizedObraCount: countedCanonicalKeys.size,
  };
}

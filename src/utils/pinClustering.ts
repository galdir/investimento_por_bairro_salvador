export type SemaforoStatus = "VERDE" | "AMARELO" | "VERMELHO";

export interface PinPoint2D {
  x: number;
  y: number;
}

export type PinProjectionFn = (lat: number, lng: number, zoom: number) => PinPoint2D;

export interface ClusterablePinEntry<T = unknown> {
  key: string;
  latitude: number;
  longitude: number;
  isApproximate: boolean;
  semaforoStatus?: string | null;
  payload: T;
}

export interface SemaforoCounts {
  VERDE: number;
  AMARELO: number;
  VERMELHO: number;
}

export interface PinCluster<T = unknown> {
  id: string;
  latitude: number;
  longitude: number;
  entries: ClusterablePinEntry<T>[];
  semaforoCounts: SemaforoCounts;
  isAllApproximate: boolean;
  hasApproximate: boolean;
  sharesSameCoordKey: boolean;
  isIndivisible: boolean;
}

export interface ClusterPinsOptions {
  zoom: number;
  maxZoom?: number;
  radiusPx?: number;
  project?: PinProjectionFn;
}

export const DEFAULT_CLUSTER_RADIUS_PX = 40;
export const DEFAULT_FALLBACK_MAX_ZOOM = 19;

const MERCATOR_TILE_SIZE = 256;
const MERCATOR_MAX_LAT = 85.05112878;

/**
 * Retorna a chave de coordenada normalizada em 4 casas decimais para detectar sobreposições.
 */
export function getPinCoordKey(latitude: number, longitude: number): string {
  return `${latitude.toFixed(4)}_${longitude.toFixed(4)}`;
}

/**
 * Resolve o limite máximo de zoom finito para agrupamento e expansão de clusters.
 */
export function resolveFiniteMaxZoom(maxZoom?: number): number {
  if (typeof maxZoom === "number" && Number.isFinite(maxZoom) && maxZoom > 0) {
    return maxZoom;
  }
  return DEFAULT_FALLBACK_MAX_ZOOM;
}

/**
 * Projeção esférica Web Mercator pura em pixels para um nível de zoom, sem dependência de DOM.
 */
export function projectLatLngMercator(lat: number, lng: number, zoom: number): PinPoint2D {
  const scale = MERCATOR_TILE_SIZE * Math.pow(2, zoom);
  const clampedLat = Math.max(-MERCATOR_MAX_LAT, Math.min(MERCATOR_MAX_LAT, lat));
  const sinLat = Math.sin((clampedLat * Math.PI) / 180);
  const x = ((lng + 180) / 360) * scale;
  const y = (0.5 - Math.log((1 + sinLat) / (1 - sinLat)) / (4 * Math.PI)) * scale;
  return { x, y };
}

function normalizeSemaforoStatus(status?: string | null): SemaforoStatus {
  if (status === "VERMELHO" || status === "AMARELO" || status === "VERDE") {
    return status;
  }
  return "VERDE";
}

interface MutableCluster<T> {
  entries: ClusterablePinEntry<T>[];
  sumLat: number;
  sumLng: number;
  anchorPx: PinPoint2D;
}

/**
 * Agrupa entradas de pinos por proximidade em pixels no nível de zoom atual.
 */
export function clusterPinEntries<T>(
  entries: ClusterablePinEntry<T>[],
  options: ClusterPinsOptions
): PinCluster<T>[] {
  if (entries.length === 0) return [];

  const zoom = options.zoom;
  const maxZoom = resolveFiniteMaxZoom(options.maxZoom);
  const radiusPx = options.radiusPx ?? DEFAULT_CLUSTER_RADIUS_PX;
  const project = options.project ?? projectLatLngMercator;

  const groups: MutableCluster<T>[] = [];

  for (const entry of entries) {
    const px = project(entry.latitude, entry.longitude, zoom);
    let nearestGroup: MutableCluster<T> | null = null;
    let nearestDistSq = radiusPx * radiusPx;

    for (const group of groups) {
      const dx = px.x - group.anchorPx.x;
      const dy = px.y - group.anchorPx.y;
      const distSq = dx * dx + dy * dy;
      if (distSq <= nearestDistSq) {
        nearestDistSq = distSq;
        nearestGroup = group;
      }
    }

    if (nearestGroup) {
      nearestGroup.entries.push(entry);
      nearestGroup.sumLat += entry.latitude;
      nearestGroup.sumLng += entry.longitude;
      const count = nearestGroup.entries.length;
      nearestGroup.anchorPx = project(
        nearestGroup.sumLat / count,
        nearestGroup.sumLng / count,
        zoom
      );
    } else {
      groups.push({
        entries: [entry],
        sumLat: entry.latitude,
        sumLng: entry.longitude,
        anchorPx: px,
      });
    }
  }

  return groups.map((group, idx) => {
    const count = group.entries.length;
    const latitude = group.sumLat / count;
    const longitude = group.sumLng / count;

    const semaforoCounts: SemaforoCounts = {
      VERDE: 0,
      AMARELO: 0,
      VERMELHO: 0,
    };

    let isAllApproximate = true;
    let hasApproximate = false;
    const firstCoordKey = getPinCoordKey(group.entries[0].latitude, group.entries[0].longitude);
    let sharesSameCoordKey = true;

    for (const entry of group.entries) {
      const status = normalizeSemaforoStatus(entry.semaforoStatus);
      semaforoCounts[status] += 1;
      if (entry.isApproximate) {
        hasApproximate = true;
      } else {
        isAllApproximate = false;
      }
      if (getPinCoordKey(entry.latitude, entry.longitude) !== firstCoordKey) {
        sharesSameCoordKey = false;
      }
    }

    const isIndivisible = sharesSameCoordKey || zoom >= maxZoom;

    return {
      id: `cluster-${idx}-${firstCoordKey}`,
      latitude,
      longitude,
      entries: group.entries,
      semaforoCounts,
      isAllApproximate,
      hasApproximate,
      sharesSameCoordKey,
      isIndivisible,
    };
  });
}

import L from "leaflet";
import { HeatmapPoint } from "./heatmap";

const HEATMAP_PANE_NAME = "heatmapPane";

export const WARM_COLOR_STOPS: Array<{ pos: number; r: number; g: number; b: number; a: number }> = [
  { pos: 0.0, r: 254, g: 240, b: 138, a: 0 },
  { pos: 0.25, r: 251, g: 191, b: 36, a: 72 },
  { pos: 0.55, r: 249, g: 115, b: 22, a: 124 },
  { pos: 0.8, r: 239, g: 68, b: 68, a: 162 },
  { pos: 1.0, r: 185, g: 28, b: 28, a: 190 },
];

export const HEATMAP_WARM_GRADIENT_CSS = `linear-gradient(to right, ${WARM_COLOR_STOPS.map(
  (s) => `rgb(${s.r}, ${s.g}, ${s.b}) ${Math.round(s.pos * 100)}%`
).join(", ")})`;

/**
 * Gera uma tabela de lookup RGBA de 256 níveis na rampa quente
 * (âmbar suave -> laranja -> vermelho-coral) distinta do verde coroplético e do roxo.
 */
export function buildWarmColorPalette(): Uint8ClampedArray {
  const palette = new Uint8ClampedArray(256 * 4);
  const stops = WARM_COLOR_STOPS;

  for (let i = 0; i < 256; i++) {
    const t = i / 255;
    let lower = stops[0];
    let upper = stops[stops.length - 1];
    for (let s = 0; s < stops.length - 1; s++) {
      if (t >= stops[s].pos && t <= stops[s + 1].pos) {
        lower = stops[s];
        upper = stops[s + 1];
        break;
      }
    }
    const span = upper.pos - lower.pos || 1;
    const localT = (t - lower.pos) / span;
    const offset = i * 4;
    palette[offset] = Math.round(lower.r + (upper.r - lower.r) * localT);
    palette[offset + 1] = Math.round(lower.g + (upper.g - lower.g) * localT);
    palette[offset + 2] = Math.round(lower.b + (upper.b - lower.b) * localT);
    palette[offset + 3] = Math.round(lower.a + (upper.a - lower.a) * localT);
  }

  return palette;
}

const WARM_PALETTE = buildWarmColorPalette();

const HEATMAP_POINT_MIN_ALPHA = 0.06;
const HEATMAP_POINT_MAX_ALPHA = 0.38;

/**
 * Calcula a contribuição de opacidade individual de um ponto do Mapa de Calor a partir do seu peso global,
 * mantendo pontos isolados em âmbar/laranja e reservando vermelho-coral para acúmulo espacial.
 */
export function computeHeatmapPointAlpha(weight: number): number {
  const safeWeight = Number.isFinite(weight) ? Math.max(0, weight) : 0;
  return Math.max(
    HEATMAP_POINT_MIN_ALPHA,
    Math.min(HEATMAP_POINT_MAX_ALPHA, safeWeight * HEATMAP_POINT_MAX_ALPHA)
  );
}

/**
 * Camada `<canvas>` nativa sobre Leaflet para renderizar o Mapa de Calor sem dependências externas.
 *
 * @summary Posiciona o canvas em pane próprio acima dos polígonos GeoJSON com `pointer-events: none`.
 */
export class HeatmapCanvasLayer extends L.Layer {
  private points: HeatmapPoint[];
  private canvas: HTMLCanvasElement | null = null;
  private boundRedraw = () => this.redraw();

  constructor(points: HeatmapPoint[] = []) {
    super();
    this.points = points;
  }

  public setPoints(points: HeatmapPoint[]): void {
    this.points = points;
    this.redraw();
  }

  public onAdd(map: L.Map): this {
    this._map = map;

    let pane = map.getPane(HEATMAP_PANE_NAME);
    if (!pane) {
      pane = map.createPane(HEATMAP_PANE_NAME);
      pane.style.zIndex = "450";
      pane.style.pointerEvents = "none";
    }

    const canvas = document.createElement("canvas");
    canvas.className = "leaflet-heatmap-layer";
    canvas.style.position = "absolute";
    canvas.style.top = "0";
    canvas.style.left = "0";
    canvas.style.pointerEvents = "none";
    pane.appendChild(canvas);
    this.canvas = canvas;

    map.on("moveend zoomend resize", this.boundRedraw);
    this.redraw();
    return this;
  }

  public onRemove(map: L.Map): this {
    map.off("moveend zoomend resize", this.boundRedraw);
    if (this.canvas && this.canvas.parentNode) {
      this.canvas.parentNode.removeChild(this.canvas);
    }
    this.canvas = null;
    this._map = undefined as unknown as L.Map;
    return this;
  }

  public redraw(): void {
    const map = this._map;
    const canvas = this.canvas;
    if (!map || !canvas) return;

    let size: L.Point;
    try {
      size = map.getSize();
    } catch {
      return;
    }

    if (!size || size.x <= 0 || size.y <= 0) {
      canvas.width = 0;
      canvas.height = 0;
      return;
    }

    canvas.width = size.x;
    canvas.height = size.y;
    canvas.style.width = `${size.x}px`;
    canvas.style.height = `${size.y}px`;

    try {
      const topLeft = map.containerPointToLayerPoint([0, 0]);
      L.DomUtil.setPosition(canvas, topLeft);
    } catch { }

    let ctx: CanvasRenderingContext2D | null = null;
    try {
      ctx = canvas.getContext("2d", { willReadFrequently: true });
    } catch {
      return;
    }
    if (!ctx) return;

    ctx.clearRect(0, 0, size.x, size.y);
    if (this.points.length === 0) return;

    const zoom = typeof map.getZoom === "function" ? map.getZoom() : 11;
    const radius = Math.max(14, Math.min(44, Math.round(14 + (zoom - 10) * 5)));

    for (const pt of this.points) {
      let projected: L.Point;
      try {
        projected = map.latLngToContainerPoint([pt.latitude, pt.longitude]);
      } catch {
        continue;
      }

      if (
        projected.x < -radius ||
        projected.y < -radius ||
        projected.x > size.x + radius ||
        projected.y > size.y + radius
      ) {
        continue;
      }

      const alpha = computeHeatmapPointAlpha(pt.weight);
      const gradient = ctx.createRadialGradient(
        projected.x,
        projected.y,
        0,
        projected.x,
        projected.y,
        radius
      );
      gradient.addColorStop(0, `rgba(0, 0, 0, ${alpha})`);
      gradient.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(projected.x, projected.y, radius, 0, Math.PI * 2);
      ctx.fill();
    }

    try {
      const imageData = ctx.getImageData(0, 0, size.x, size.y);
      const data = imageData.data;
      for (let i = 0; i < data.length; i += 4) {
        const alpha = data[i + 3];
        if (alpha === 0) continue;
        const pIdx = alpha * 4;
        data[i] = WARM_PALETTE[pIdx];
        data[i + 1] = WARM_PALETTE[pIdx + 1];
        data[i + 2] = WARM_PALETTE[pIdx + 2];
        data[i + 3] = WARM_PALETTE[pIdx + 3];
      }
      ctx.putImageData(imageData, 0, 0);
    } catch {
      // Degrada silenciosamente caso o ambiente não suporte manipulação de pixels
    }
  }
}

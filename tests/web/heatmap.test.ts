import { describe, expect, it, vi } from "vitest";
import L from "leaflet";
import { computeBairroCentroids, extractHeatmapPoints } from "../../src/utils/heatmap";
import {
  buildWarmColorPalette,
  computeHeatmapPointAlpha,
  HeatmapCanvasLayer,
  WARM_COLOR_STOPS,
} from "../../src/utils/heatmapLayer";
import { ObraCompacta } from "../../src/types";

describe("Mapa de Calor — centróides de GeoJSON e extrator puro de pontos", () => {
  it("deriva centróides de Polygon e MultiPolygon (anel externo do maior polígono)", () => {
    const geojson = {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: { nome: "Pituba" },
          geometry: {
            type: "Polygon",
            coordinates: [
              [
                [-38.46, -13.0],
                [-38.44, -13.0],
                [-38.44, -12.98],
                [-38.46, -12.98],
                [-38.46, -13.0],
              ],
            ],
          },
        },
        {
          type: "Feature",
          properties: { NM_BAIRRO: "Itapuã" },
          geometry: {
            type: "MultiPolygon",
            coordinates: [
              // Polígono menor (ilha/fragmento)
              [
                [
                  [-38.30, -12.90],
                  [-38.299, -12.90],
                  [-38.299, -12.899],
                  [-38.30, -12.899],
                  [-38.30, -12.90],
                ],
              ],
              // Polígono maior
              [
                [
                  [-38.38, -12.96],
                  [-38.34, -12.96],
                  [-38.34, -12.92],
                  [-38.38, -12.92],
                  [-38.38, -12.96],
                ],
              ],
            ],
          },
        },
      ],
    };

    const centroids = computeBairroCentroids(geojson);
    expect(centroids.get("PITUBA")).toBeDefined();
    expect(centroids.get("PITUBA")!.lat).toBeCloseTo(-12.99, 4);
    expect(centroids.get("PITUBA")!.lng).toBeCloseTo(-38.45, 4);

    expect(centroids.get("ITAPUA")).toBeDefined();
    expect(centroids.get("ITAPUA")!.lat).toBeCloseTo(-12.94, 4);
    expect(centroids.get("ITAPUA")!.lng).toBeCloseTo(-38.36, 4);
  });

  it("inclui obras Pontual/Bairro, cotas de Lista Fechada proporcionais, exclui Regional/Escopo Cidade e aplica escala logarítmica", () => {
    const centroids = new Map([
      ["PITUBA", { lat: -12.99, lng: -38.45 }],
      ["PARIPE", { lat: -12.82, lng: -38.47 }],
      ["BROTAS", { lat: -12.98, lng: -38.49 }],
    ]);

    const obras: ObraCompacta[] = [
      // Pontual válida
      {
        id: 1,
        unidadeGestora: "SEINFRA",
        numeroContrato: "001/2025",
        objeto: "Drenagem Pontual",
        valorContratualVigente: 1_000_000,
        valorPago: 500_000,
        percentualExecutado: 50,
        situacao: "Em Execução",
        credor: "Construtora A",
        nivel: "Pontual",
        bairro: "Pituba",
        latitude: -12.991,
        longitude: -38.451,
      },
      // Megaobra de Bairro (sem lat/lng explícito -> usa centróide do bairro)
      {
        id: 2,
        unidadeGestora: "SEINFRA",
        numeroContrato: "002/2025",
        objeto: "Megaobra Bairro",
        valorContratualVigente: 100_000_000,
        valorPago: 80_000_000,
        percentualExecutado: 80,
        situacao: "Em Execução",
        credor: "Construtora B",
        nivel: "Bairro",
        bairro: "Paripe",
      },
      // Cota-Parte de Lista Fechada (2 cotas)
      {
        id: 3,
        unidadeGestora: "SMS",
        numeroContrato: "003/2025",
        objeto: "Reforma de UBS em Lista Fechada",
        valorContratualVigente: 2_000_000,
        valorPago: 1_000_000,
        percentualExecutado: 50,
        situacao: "Em Execução",
        credor: "Construtora C",
        nivel: "Regional (Prefeitura-Bairro)",
        cotasListaFechada: [
          {
            bairro: "Pituba",
            unidades: 1,
            totalUnidades: 4,
            peso: 0.25,
            fracao: "1/4",
            latitude: -12.995,
            longitude: -38.455,
          },
          {
            bairro: "Brotas",
            unidades: 3,
            totalUnidades: 4,
            peso: 0.75,
            fracao: "3/4",
            latitude: -12.982,
            longitude: -38.492,
          },
        ],
      },
      // Regional sem cotas -> excluído
      {
        id: 4,
        unidadeGestora: "SEINFRA",
        numeroContrato: "004/2025",
        objeto: "Manutenção Regional",
        valorContratualVigente: 5_000_000,
        valorPago: 3_000_000,
        percentualExecutado: 60,
        situacao: "Em Execução",
        credor: "Construtora D",
        nivel: "Regional (Prefeitura-Bairro)",
        prefeituraBairro: "Barra/Pituba",
      },
      // Escopo Cidade sem frentes -> excluído
      {
        id: 5,
        unidadeGestora: "SEINFRA",
        numeroContrato: "005/2025",
        objeto: "Contrato Cidade",
        valorContratualVigente: 10_000_000,
        valorPago: 4_000_000,
        percentualExecutado: 40,
        situacao: "Em Execução",
        credor: "Construtora E",
        nivel: "Escopo Cidade (Não-Localizado)",
      },
      // Valor zero -> excluído
      {
        id: 6,
        unidadeGestora: "SEINFRA",
        numeroContrato: "006/2025",
        objeto: "Obra Valor Zero",
        valorContratualVigente: 0,
        valorPago: 0,
        percentualExecutado: 0,
        situacao: "Paralisada",
        credor: "Construtora F",
        nivel: "Pontual",
        bairro: "Pituba",
        latitude: -12.99,
        longitude: -38.45,
      },
    ];

    const result = extractHeatmapPoints(obras, centroids, "vigente");
    // Obras 1, 2 e 3 (3 obras distintas), gerando 4 pontos (1 + 1 + 2 cotas)
    expect(result.localizedObraCount).toBe(3);
    expect(result.points).toHaveLength(4);

    const maxLog = Math.log10(1 + 100_000_000);
    const expectedWeight1 = Math.log10(1 + 1_000_000) / maxLog;
    const expectedWeightCota1 = Math.log10(1 + 2_000_000 * 0.25) / maxLog;

    expect(result.points[0].weight).toBeCloseTo(expectedWeight1, 6);
    expect(result.points[1].weight).toBeCloseTo(1, 6);
    expect(result.points[2].weight).toBeCloseTo(expectedWeightCota1, 6);
    // Obra menor (1M vs 100M) mantém peso relevante (> 0.7) graças à escala logarítmica
    expect(result.points[0].weight).toBeGreaterThan(0.7);
  });

  it("respeita precedência de frentesMedicao sobre cotas, entra só em Valor Pago e agrega por (obra, bairro)", () => {
    const centroids = new Map([
      ["CAJAZEIRAS", { lat: -12.89, lng: -38.41 }],
      ["PARIPE", { lat: -12.82, lng: -38.47 }],
    ]);

    const obras: ObraCompacta[] = [
      {
        id: 10,
        unidadeGestora: "SEINFRA",
        numeroContrato: "010/2025",
        objeto: "Contrato Cidade com Frentes",
        valorContratualVigente: 5_000_000,
        valorPago: 900_000,
        percentualExecutado: 18,
        situacao: "Em Execução",
        credor: "Construtora G",
        nivel: "Escopo Cidade (Não-Localizado)",
        // Cotas devem ser ignoradas pela precedência de frentesMedicao
        cotasListaFechada: [
          {
            bairro: "Paripe",
            unidades: 1,
            totalUnidades: 1,
            peso: 1,
            fracao: "1/1",
            latitude: -12.82,
            longitude: -38.47,
          },
        ],
        frentesMedicao: [
          {
            notaLiquidacao: "NL-1",
            nivel: "Bairro",
            bairro: "Cajazeiras",
            valorLiquidado: 300_000,
            valorPago: 200_000,
          },
          {
            notaLiquidacao: "NL-2",
            nivel: "Pontual",
            bairro: "Cajazeiras",
            valorLiquidado: 300_000,
            valorPago: 300_000,
          },
          // Frente regional -> deve ser excluída
          {
            notaLiquidacao: "NL-3",
            nivel: "Regional (Prefeitura-Bairro)",
            prefeituraBairro: "Cajazeiras",
            valorLiquidado: 400_000,
            valorPago: 400_000,
          },
        ],
      },
      // Duplicata canônica da mesma obra para testar deduplicação na contagem
      {
        id: 11,
        unidadeGestora: "SEINFRA",
        numeroContrato: "010/2025",
        objeto: "Contrato Cidade com Frentes (duplicata)",
        valorContratualVigente: 5_000_000,
        valorPago: 900_000,
        percentualExecutado: 18,
        situacao: "Em Execução",
        credor: "Construtora G",
        nivel: "Escopo Cidade (Não-Localizado)",
        frentesMedicao: [
          {
            notaLiquidacao: "NL-1",
            nivel: "Bairro",
            bairro: "Cajazeiras",
            valorLiquidado: 300_000,
            valorPago: 200_000,
          },
        ],
      },
    ];

    // Em Valor Contratual Vigente: frentes não entram e cotas são suprimidas pela precedência
    const resVigente = extractHeatmapPoints(obras, centroids, "vigente");
    expect(resVigente.points).toHaveLength(0);
    expect(resVigente.localizedObraCount).toBe(0);

    // Em Valor Pago: frentes Pontual/Bairro entram agregadas por (obra, bairro)
    const resPago = extractHeatmapPoints(obras, centroids, "executado");
    expect(resPago.localizedObraCount).toBe(1);
    expect(resPago.points).toHaveLength(1);
    expect(resPago.points[0].latitude).toBeCloseTo(-12.89, 4);
    expect(resPago.points[0].longitude).toBeCloseTo(-38.41, 4);
    expect(resPago.points[0].value).toBe(500_000);
  });

  it("HeatmapCanvasLayer usa pointer-events: none acima dos polígonos, recalcula em moveend/zoomend e degrada silenciosamente em 0x0 ou sem contexto 2D", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const map = L.map(container, { center: [-12.88, -38.48], zoom: 11 });

    const layer = new HeatmapCanvasLayer([
      { latitude: -12.9, longitude: -38.48, value: 1_000_000, weight: 0.8 },
    ]);

    expect(() => layer.addTo(map)).not.toThrow();

    const pane = map.getPane("heatmapPane");
    expect(pane).toBeDefined();
    expect(Number(pane!.style.zIndex)).toBeGreaterThan(400);
    expect(pane!.style.pointerEvents).toBe("none");

    const canvas = pane!.querySelector("canvas");
    expect(canvas).toBeInTheDocument();
    expect(canvas!.style.pointerEvents).toBe("none");

    const redrawSpy = vi.spyOn(layer, "redraw");
    map.fire("zoomend");
    map.fire("moveend");
    map.fire("resize");
    expect(redrawSpy).toHaveBeenCalledTimes(3);

    layer.setPoints([]);
    expect(redrawSpy).toHaveBeenCalledTimes(4);

    // Simula dimensões 0x0 e ausência de contexto 2D sem lançar exceções
    vi.spyOn(map, "getSize").mockReturnValue(L.point(0, 0));
    expect(() => layer.redraw()).not.toThrow();
    expect(canvas!.width).toBe(0);
    expect(canvas!.height).toBe(0);

    vi.spyOn(map, "getSize").mockReturnValue(L.point(400, 300));
    vi.spyOn(canvas!, "getContext").mockReturnValue(null);
    expect(() => layer.redraw()).not.toThrow();

    layer.remove();
    expect(pane!.querySelector("canvas")).toBeNull();
    redrawSpy.mockClear();
    map.fire("zoomend");
    expect(redrawSpy).not.toHaveBeenCalled();

    map.remove();
    container.remove();
  });

  it("rampa quente tem paradas de alfa estritamente crescentes de 0 até teto ~75% (~190/255)", () => {
    expect(WARM_COLOR_STOPS.length).toBeGreaterThanOrEqual(4);
    expect(WARM_COLOR_STOPS[0].a).toBe(0);

    for (let i = 1; i < WARM_COLOR_STOPS.length; i++) {
      expect(WARM_COLOR_STOPS[i].pos).toBeGreaterThan(WARM_COLOR_STOPS[i - 1].pos);
      expect(WARM_COLOR_STOPS[i].a).toBeGreaterThan(WARM_COLOR_STOPS[i - 1].a);
    }

    const maxAlphaStop = WARM_COLOR_STOPS[WARM_COLOR_STOPS.length - 1].a;
    expect(maxAlphaStop).toBeGreaterThanOrEqual(185);
    expect(maxAlphaStop).toBeLessThanOrEqual(195);

    const palette = buildWarmColorPalette();
    expect(palette).toHaveLength(256 * 4);
    expect(palette[3]).toBe(0);
    for (let i = 1; i < 256; i++) {
      expect(palette[i * 4 + 3]).toBeGreaterThanOrEqual(palette[(i - 1) * 4 + 3]);
    }
    expect(palette[255 * 4 + 3]).toBe(maxAlphaStop);
  });

  it("computeHeatmapPointAlpha respeita piso ~0,06 e teto individual ~0,35–0,42", () => {
    expect(computeHeatmapPointAlpha(0)).toBeCloseTo(0.06, 2);
    expect(computeHeatmapPointAlpha(-0.5)).toBeCloseTo(0.06, 2);
    expect(computeHeatmapPointAlpha(Number.NaN)).toBeCloseTo(0.06, 2);

    const maxAlpha = computeHeatmapPointAlpha(1);
    expect(maxAlpha).toBeGreaterThanOrEqual(0.35);
    expect(maxAlpha).toBeLessThanOrEqual(0.42);
    expect(computeHeatmapPointAlpha(2)).toBeCloseTo(maxAlpha, 5);

    const midAlpha = computeHeatmapPointAlpha(0.5);
    expect(midAlpha).toBeGreaterThan(0.06);
    expect(midAlpha).toBeLessThan(maxAlpha);
  });

  it("HeatmapCanvasLayer inicializa contexto 2D com willReadFrequently: true e mantém alfa invariante a pontos fora da viewport", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const map = L.map(container, { center: [-12.9, -38.48], zoom: 12 });
    vi.spyOn(map, "getSize").mockReturnValue(L.point(400, 300));
    vi.spyOn(map, "latLngToContainerPoint").mockImplementation((latlng: any) => {
      const lat = Array.isArray(latlng) ? latlng[0] : latlng.lat;
      if (lat < -15) {
        return L.point(2000, 2000); // fora da viewport
      }
      return L.point(200, 150); // visível no centro
    });

    const recordedStops: string[] = [];
    const mockCtx = {
      clearRect: vi.fn(),
      createRadialGradient: vi.fn(() => ({
        addColorStop: vi.fn((offset: number, color: string) => {
          if (offset === 0) recordedStops.push(color);
        }),
      })),
      beginPath: vi.fn(),
      arc: vi.fn(),
      fill: vi.fn(),
      getImageData: vi.fn(() => ({ data: new Uint8ClampedArray(400 * 300 * 4) })),
      putImageData: vi.fn(),
      fillStyle: "",
    } as unknown as CanvasRenderingContext2D;

    const getContextSpy = vi
      .spyOn(HTMLCanvasElement.prototype, "getContext")
      .mockReturnValue(mockCtx as any);

    const visiblePoint = { latitude: -12.9, longitude: -38.48, value: 1_000_000, weight: 0.75 };
    const offscreenPoint = { latitude: -20.0, longitude: -40.0, value: 50_000_000, weight: 1.0 };

    const layer = new HeatmapCanvasLayer([visiblePoint]);
    layer.addTo(map);

    expect(getContextSpy).toHaveBeenCalledWith("2d", { willReadFrequently: true });
    expect(recordedStops).toHaveLength(1);
    const alphaOnlyVisible = recordedStops[0];

    recordedStops.length = 0;
    layer.setPoints([visiblePoint, offscreenPoint]);
    expect(recordedStops).toHaveLength(1);
    expect(recordedStops[0]).toBe(alphaOnlyVisible);

    getContextSpy.mockRestore();
    layer.remove();
    map.remove();
    container.remove();
  });
});

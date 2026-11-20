import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import L from "leaflet";
import { describe, expect, it, vi } from "vitest";
import { InteractiveMap } from "../../src/components/InteractiveMap";
import { BairroResumo, PrefeituraBairroResumo } from "../../src/types";

const bairrosMock: BairroResumo[] = [
  {
    id: 1,
    nome: "Pituba",
    prefeitura_bairro: "Barra/Pituba",
    populacao: 65000,
    indice_vulnerabilidade: 0.12,
    is_zona_especial_nao_residencial: false,
    valorTotal: 12000000,
    valorPago: 10000000,
    valorPagoDisponivel: true,
    totalObras: 2,
    obrasVerde: 2,
    obrasAmarelo: 0,
    obrasVermelho: 0,
    investimentoPorHabitante: 184.62,
    investimentoPorHabitantePago: 153.85,
  },
];

const prefeiturasMock: PrefeituraBairroResumo[] = [
  {
    id: 10,
    nome: "Barra/Pituba",
    populacao_total: 65000,
    indice_vulnerabilidade: 0.12,
    valorTotal: 12000000,
    valorPago: 10000000,
    valorPagoDisponivel: true,
    totalObras: 2,
    obrasVerde: 2,
    obrasAmarelo: 0,
    obrasVermelho: 0,
    investimentoPorHabitante: 184.62,
    investimentoPorHabitantePago: 153.85,
  },
];

const bairrosGeoJsonMock = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { id: 1, nome: "Pituba", prefeitura_bairro: "Barra/Pituba" },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-38.46, -13.0],
            [-38.45, -13.0],
            [-38.45, -12.99],
            [-38.46, -12.99],
            [-38.46, -13.0],
          ],
        ],
      },
    },
  ],
};

describe("InteractiveMap — Positron, moldura limpa e padding assimétrico", () => {
  it("usa tiles CartoDB Positron, zoom à esquerda, sem seletor de camada/chips duplicados e exibe mapa-destaque-busca na barra superior", () => {
    const tileLayerSpy = vi.spyOn(L, "tileLayer");
    const zoomSpy = vi.spyOn(L.control, "zoom");

    render(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={[]}
        selectedTerritory={null}
        onSelectTerritory={vi.fn()}
        territorySearch="Pituba"
        onOpenNotaMetodologica={vi.fn()}
      />
    );

    expect(tileLayerSpy).toHaveBeenCalledWith(
      "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      expect.objectContaining({
        className: "map-tiles-monochrome",
        attribution: expect.stringContaining("OpenStreetMap"),
      })
    );
    expect(zoomSpy).toHaveBeenCalledWith(expect.objectContaining({ position: "bottomleft" }));

    expect(screen.queryByTestId("btn-camada-bairros")).not.toBeInTheDocument();
    expect(screen.queryByTestId("btn-camada-prefeituras")).not.toBeInTheDocument();
    expect(screen.queryByTestId(/^territory-selector-/)).not.toBeInTheDocument();

    expect(screen.getByTestId("btn-camada-per-capita")).toBeInTheDocument();
    expect(screen.getByTestId("btn-camada-vulnerabilidade")).toBeInTheDocument();
    expect(screen.getByTestId("btn-como-calculado-mapa")).toBeInTheDocument();
    expect(screen.getByTestId("btn-toggle-pinos-obras")).toBeInTheDocument();
    expect(screen.getByTestId("btn-centralizar-salvador")).toBeInTheDocument();
    expect(screen.getByTestId("mapa-destaque-busca")).toHaveTextContent("1 correspondência destacada: Pituba");

    tileLayerSpy.mockRestore();
    zoomSpy.mockRestore();
  });

  it("aplica padding assimétrico no fitBounds quando drawer desktop está expandido e largura >= 640px, e fallback simétrico nos demais casos", () => {
    const fitBoundsSpy = vi.spyOn(L.Map.prototype, "fitBounds").mockImplementation(function (this: L.Map) {
      return this;
    });
    let mockWidth = 700;
    const clientWidthSpy = vi
      .spyOn(HTMLElement.prototype, "clientWidth", "get")
      .mockImplementation(() => mockWidth);

    const selection = {
      tipo: "bairro" as const,
      ...bairrosMock[0],
    };

    const { rerender } = render(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={[]}
        selectedTerritory={selection}
        onSelectTerritory={vi.fn()}
        isDesktopDrawerExpanded={true}
      />
    );

    expect(fitBoundsSpy).toHaveBeenLastCalledWith(
      expect.anything(),
      expect.objectContaining({
        maxZoom: 14,
        paddingTopLeft: [24, 56],
        paddingBottomRight: [336, 24],
      })
    );

    // Largura >= 800 limita paddingBottomRight.x em 380
    mockWidth = 900;
    rerender(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={[]}
        selectedTerritory={null}
        onSelectTerritory={vi.fn()}
        isDesktopDrawerExpanded={true}
      />
    );
    fitBoundsSpy.mockClear();
    rerender(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={[]}
        selectedTerritory={selection}
        onSelectTerritory={vi.fn()}
        isDesktopDrawerExpanded={true}
      />
    );
    expect(fitBoundsSpy).toHaveBeenLastCalledWith(
      expect.anything(),
      expect.objectContaining({
        maxZoom: 14,
        paddingTopLeft: [24, 56],
        paddingBottomRight: [380, 24],
      })
    );

    // Drawer recolhido com largura >= 640px -> fallback simétrico [40, 40]
    mockWidth = 800;
    rerender(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={[]}
        selectedTerritory={null}
        onSelectTerritory={vi.fn()}
        isDesktopDrawerExpanded={false}
      />
    );
    fitBoundsSpy.mockClear();
    rerender(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={[]}
        selectedTerritory={selection}
        onSelectTerritory={vi.fn()}
        isDesktopDrawerExpanded={false}
      />
    );
    expect(fitBoundsSpy).toHaveBeenLastCalledWith(
      expect.anything(),
      expect.objectContaining({
        maxZoom: 14,
        padding: [40, 40],
      })
    );

    // Largura < 640px -> fallback simétrico [40, 40]
    mockWidth = 500;
    rerender(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={[]}
        selectedTerritory={null}
        onSelectTerritory={vi.fn()}
        isDesktopDrawerExpanded={true}
      />
    );
    fitBoundsSpy.mockClear();
    rerender(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={[]}
        selectedTerritory={selection}
        onSelectTerritory={vi.fn()}
        isDesktopDrawerExpanded={true}
      />
    );
    expect(fitBoundsSpy).toHaveBeenLastCalledWith(
      expect.anything(),
      expect.objectContaining({
        maxZoom: 14,
        padding: [40, 40],
      })
    );

    fitBoundsSpy.mockRestore();
    clientWidthSpy.mockRestore();
  });
});

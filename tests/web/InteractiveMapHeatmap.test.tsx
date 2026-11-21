import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import L from "leaflet";
import { describe, expect, it, vi } from "vitest";
import { InteractiveMap } from "../../src/components/InteractiveMap";
import { BairroResumo, ObraCompacta, PrefeituraBairroResumo, TerritorySelection } from "../../src/types";

const bairrosMock: BairroResumo[] = [
  {
    id: 1,
    nome: "Pituba",
    prefeitura_bairro: "Barra/Pituba",
    populacao: 65000,
    indice_vulnerabilidade: 0.12,
    is_zona_especial_nao_residencial: false,
    valorTotal: 1_000_000,
    valorPago: 500_000,
    valorPagoDisponivel: true,
    totalObras: 1,
  },
  {
    id: 2,
    nome: "Paripe",
    prefeitura_bairro: "Subúrbio/Ilhas",
    populacao: 50000,
    indice_vulnerabilidade: 0.85,
    is_zona_especial_nao_residencial: false,
    valorTotal: 2_000_000,
    valorPago: 1_000_000,
    valorPagoDisponivel: true,
    totalObras: 1,
  },
];

const prefeiturasMock: PrefeituraBairroResumo[] = [
  {
    id: 10,
    nome: "Barra/Pituba",
    populacao_total: 65000,
    indice_vulnerabilidade: 0.12,
    valorTotal: 1_000_000,
    valorPago: 500_000,
    valorPagoDisponivel: true,
    totalObras: 1,
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
    {
      type: "Feature",
      properties: { id: 2, nome: "Paripe", prefeitura_bairro: "Subúrbio/Ilhas" },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-38.48, -12.83],
            [-38.47, -12.83],
            [-38.47, -12.82],
            [-38.48, -12.82],
            [-38.48, -12.83],
          ],
        ],
      },
    },
  ],
};

const obrasMunicipais: ObraCompacta[] = [
  {
    id: 101,
    unidadeGestora: "SEINFRA",
    numeroContrato: "101/2025",
    objeto: "Praça na Pituba",
    valorContratualVigente: 1_000_000,
    valorPago: 500_000,
    percentualExecutado: 50,
    situacao: "Em Execução",
    credor: "Empresa A",
    nivel: "Pontual",
    bairro: "Pituba",
    latitude: -12.995,
    longitude: -38.455,
  },
  {
    id: 102,
    unidadeGestora: "SEINFRA",
    numeroContrato: "102/2025",
    objeto: "Drenagem em Paripe",
    valorContratualVigente: 2_000_000,
    valorPago: 1_000_000,
    percentualExecutado: 50,
    situacao: "Em Execução",
    credor: "Empresa B",
    nivel: "Bairro",
    bairro: "Paripe",
    latitude: -12.825,
    longitude: -38.475,
  },
  {
    id: 103,
    unidadeGestora: "SEINFRA",
    numeroContrato: "103/2025",
    objeto: "Contrato Escopo Cidade",
    valorContratualVigente: 5_000_000,
    valorPago: 2_000_000,
    percentualExecutado: 40,
    situacao: "Em Execução",
    credor: "Empresa C",
    nivel: "Escopo Cidade (Não-Localizado)",
  },
];

describe("InteractiveMap — 3ª camada Mapa de Calor", () => {
  it("exibe botão acessível Mapa de Calor, adapta legenda, preserva Pinos de Obras filtrados e mantém clique territorial", () => {
    const onSelectTerritory = vi.fn();
    const geoJsonSpy = vi.spyOn(L, "geoJSON");

    const selectedPituba: TerritorySelection = {
      tipo: "bairro",
      id: 1,
      nome: "Pituba",
      prefeitura_bairro: "Barra/Pituba",
      populacao: 65000,
      indice_vulnerabilidade: 0.12,
    };

    render(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={[obrasMunicipais[0]]}
        heatmapObras={obrasMunicipais}
        selectedTerritory={selectedPituba}
        onSelectTerritory={onSelectTerritory}
        metricType="executado"
        territorySearch="Paripe"
      />
    );

    const btnHeatmap = screen.getByTestId("btn-camada-mapa-calor");
    expect(btnHeatmap).toHaveTextContent("Mapa de Calor");
    expect(btnHeatmap).toHaveAttribute("aria-pressed", "false");

    // Pinos de Obras refletem a prop `obras` (apenas Pituba = 1 pino)
    expect(screen.getByTestId("btn-toggle-pinos-obras")).toHaveTextContent("Pinos de Obras (1)");

    // Alterna para Mapa de Calor
    fireEvent.click(btnHeatmap);
    expect(btnHeatmap).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("btn-camada-per-capita")).toHaveAttribute("aria-pressed", "false");

    // Legenda adaptada: título Valor Pago, barra contínua quente, contagem distinta de obras localizadas (2, excluindo Escopo Cidade), aviso e sem Isento
    const legenda = screen.getByTestId("legenda-coropletica");
    expect(legenda).toHaveTextContent(/Mapa de Calor — Valor Pago/i);
    expect(legenda).toHaveTextContent(/Menor/i);
    expect(legenda).toHaveTextContent(/Maior concentração/i);
    expect(legenda).toHaveTextContent(/2 obras localizadas/i);
    expect(legenda).toHaveTextContent(/Escopo Cidade \(Não-Localizado\)/i);
    expect(legenda).not.toHaveTextContent("Isento");

    // Pinos de Obras continua com 1 pino (filtrado pelo território selecionado)
    expect(screen.getByTestId("btn-toggle-pinos-obras")).toHaveTextContent("Pinos de Obras (1)");

    // Verifica que o canvas foi montado com pointer-events: none
    const mapContainer = screen.getByTestId("leaflet-map-container");
    const canvas = mapContainer.querySelector("canvas.leaflet-heatmap-layer") as HTMLCanvasElement | null;
    expect(canvas).toBeInTheDocument();
    expect(canvas!.style.pointerEvents).toBe("none");

    // Verifica estilo dos polígonos no modo Mapa de Calor (fillOpacity: 0, borda de seleção e busca)
    const lastGeoCall = geoJsonSpy.mock.calls[geoJsonSpy.mock.calls.length - 1];
    const geoOptions = lastGeoCall[1] as L.GeoJSONOptions;
    const styleSelected = (geoOptions.style as (f: any) => L.PathOptions)(bairrosGeoJsonMock.features[0]);
    const styleSearchMatch = (geoOptions.style as (f: any) => L.PathOptions)(bairrosGeoJsonMock.features[1]);
    expect(styleSelected.fillOpacity).toBe(0);
    expect(styleSelected.color).toBe("#0f172a");
    expect(styleSearchMatch.fillOpacity).toBe(0);
    expect(styleSearchMatch.color).toBe("#0369a1");
    expect(styleSelected.fill).not.toBe(false);
    expect(styleSearchMatch.fill).not.toBe(false);

    // Simula clique em um polígono (Paripe) no modo Mapa de Calor -> abre Raio-X
    const createdLayer = geoJsonSpy.mock.results[geoJsonSpy.mock.results.length - 1].value as L.GeoJSON;
    const layers = createdLayer.getLayers();
    const paripeLayer = layers[1] as any;
    paripeLayer.fire("click");
    expect(onSelectTerritory).toHaveBeenCalledWith(
      expect.objectContaining({ tipo: "bairro", nome: "Paripe" })
    );

    geoJsonSpy.mockRestore();
  });
});

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

const bairrosComExcecoesMock: BairroResumo[] = [
  ...bairrosMock,
  {
    id: 3,
    nome: "Polo Industrial",
    prefeitura_bairro: "Subúrbio/Ilhas",
    populacao: 0,
    indice_vulnerabilidade: null,
    is_zona_especial_nao_residencial: true,
    valorTotal: 0,
    valorPago: 0,
    valorPagoDisponivel: true,
    totalObras: 0,
  },
  {
    id: 4,
    nome: "Ilha Sem Dado",
    prefeitura_bairro: "Subúrbio/Ilhas",
    populacao: 1000,
    indice_vulnerabilidade: null,
    is_zona_especial_nao_residencial: false,
    valorTotal: 0,
    valorPago: 0,
    valorPagoDisponivel: true,
    totalObras: 0,
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

  it("exibe o toggle 'Vulnerabilidade ao fundo' somente no Mapa de Calor e preserva o estado ao alternar camadas", () => {
    render(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={obrasMunicipais}
        selectedTerritory={null}
        onSelectTerritory={vi.fn()}
      />
    );

    // Oculto na camada inicial (R$ / Habitante)
    expect(screen.queryByTestId("btn-toggle-vulnerabilidade-fundo")).not.toBeInTheDocument();

    // Oculto em Vulnerabilidade Social
    fireEvent.click(screen.getByTestId("btn-camada-vulnerabilidade"));
    expect(screen.queryByTestId("btn-toggle-vulnerabilidade-fundo")).not.toBeInTheDocument();

    // Visível e desligado por padrão em Mapa de Calor
    fireEvent.click(screen.getByTestId("btn-camada-mapa-calor"));
    const toggleUnderlay = screen.getByTestId("btn-toggle-vulnerabilidade-fundo");
    expect(toggleUnderlay).toHaveTextContent("Vulnerabilidade ao fundo");
    expect(toggleUnderlay).toHaveAttribute("aria-pressed", "false");

    // Liga o toggle
    fireEvent.click(toggleUnderlay);
    expect(toggleUnderlay).toHaveAttribute("aria-pressed", "true");

    // Alterna para outra camada (oculta) e volta para Mapa de Calor (preserva ligado)
    fireEvent.click(screen.getByTestId("btn-camada-per-capita"));
    expect(screen.queryByTestId("btn-toggle-vulnerabilidade-fundo")).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("btn-camada-mapa-calor"));
    expect(screen.getByTestId("btn-toggle-vulnerabilidade-fundo")).toHaveAttribute(
      "aria-pressed",
      "true"
    );
  });

  it("aplica preenchimento de vulnerabilidade com opacidade reduzida (0.30-0.45) em bairros, isentos, indisponíveis, selecionados, busca e prefeituras mantendo clique e canvas acima", () => {
    const onSelectTerritory = vi.fn();
    const geoJsonSpy = vi.spyOn(L, "geoJSON");

    const geoJsonComExcecoes = {
      type: "FeatureCollection",
      features: [
        ...bairrosGeoJsonMock.features,
        {
          type: "Feature",
          properties: { id: 3, nome: "Polo Industrial", is_zona_especial_nao_residencial: true },
          geometry: {
            type: "Polygon",
            coordinates: [
              [
                [-38.49, -12.81],
                [-38.48, -12.81],
                [-38.48, -12.8],
                [-38.49, -12.8],
                [-38.49, -12.81],
              ],
            ],
          },
        },
        {
          type: "Feature",
          properties: { id: 4, nome: "Ilha Sem Dado" },
          geometry: {
            type: "Polygon",
            coordinates: [
              [
                [-38.5, -12.81],
                [-38.49, -12.81],
                [-38.49, -12.8],
                [-38.5, -12.8],
                [-38.5, -12.81],
              ],
            ],
          },
        },
      ],
    };

    const prefeiturasGeoJsonMock = {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: { id: 10, nome: "Barra/Pituba" },
          geometry: bairrosGeoJsonMock.features[0].geometry,
        },
      ],
    };

    const selectedPituba: TerritorySelection = {
      tipo: "bairro",
      id: 1,
      nome: "Pituba",
      prefeitura_bairro: "Barra/Pituba",
      populacao: 65000,
      indice_vulnerabilidade: 0.12,
    };

    const { rerender } = render(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosComExcecoesMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={geoJsonComExcecoes}
        prefeiturasGeoJson={prefeiturasGeoJsonMock}
        obras={[obrasMunicipais[0]]}
        heatmapObras={obrasMunicipais}
        selectedTerritory={selectedPituba}
        onSelectTerritory={onSelectTerritory}
        territorySearch="Paripe"
      />
    );

    fireEvent.click(screen.getByTestId("btn-camada-mapa-calor"));
    fireEvent.click(screen.getByTestId("btn-toggle-vulnerabilidade-fundo"));

    // Canvas do Mapa de Calor continua montado com pointer-events: none e z-index acima do overlayPane (400)
    const mapContainer = screen.getByTestId("leaflet-map-container");
    const canvas = mapContainer.querySelector("canvas.leaflet-heatmap-layer") as HTMLCanvasElement | null;
    expect(canvas).toBeInTheDocument();
    expect(canvas!.style.pointerEvents).toBe("none");
    expect(Number((canvas!.parentElement as HTMLElement).style.zIndex)).toBeGreaterThan(400);

    const lastGeoCall = geoJsonSpy.mock.calls[geoJsonSpy.mock.calls.length - 1];
    const styleFn = (lastGeoCall[1] as L.GeoJSONOptions).style as (f: any) => L.PathOptions;

    // Pituba (selecionado, vuln 0.12 -> #ede9fe): preserva cor de vulnerabilidade com opacidade reduzida e borda de alto contraste (sem verde #10B981 nem fillOpacity 0.78/0.8)
    const styleSelected = styleFn(geoJsonComExcecoes.features[0]);
    expect(styleSelected.fillColor).toBe("#ede9fe");
    expect(styleSelected.fillColor).not.toBe("#10B981");
    expect(styleSelected.fillOpacity).toBeGreaterThanOrEqual(0.3);
    expect(styleSelected.fillOpacity).toBeLessThanOrEqual(0.45);
    expect(styleSelected.color).toBe("#0f172a");

    // Paripe (match de busca, vuln 0.85 -> #4c1d95): preserva cor de vulnerabilidade com opacidade reduzida e borda de busca
    const styleSearchMatch = styleFn(geoJsonComExcecoes.features[1]);
    expect(styleSearchMatch.fillColor).toBe("#4c1d95");
    expect(styleSearchMatch.fillOpacity).toBeGreaterThanOrEqual(0.3);
    expect(styleSearchMatch.fillOpacity).toBeLessThanOrEqual(0.45);
    expect(styleSearchMatch.color).toBe("#0369a1");

    // Polo Industrial (Zona Especial isenta): preenchimento âmbar suave com opacidade reduzida e borda âmbar
    const styleExempt = styleFn(geoJsonComExcecoes.features[2]);
    expect(styleExempt.fillColor).toBe("#fef3c7");
    expect(styleExempt.fillOpacity).toBeGreaterThanOrEqual(0.3);
    expect(styleExempt.fillOpacity).toBeLessThanOrEqual(0.45);
    expect(styleExempt.color).toBe("#d97706");

    // Ilha Sem Dado (indisponível): preenchimento cinza com opacidade reduzida e borda tracejada cinza
    const styleUnavailable = styleFn(geoJsonComExcecoes.features[3]);
    expect(styleUnavailable.fillColor).toBe("#e2e8f0");
    expect(styleUnavailable.fillOpacity).toBeGreaterThanOrEqual(0.3);
    expect(styleUnavailable.fillOpacity).toBeLessThanOrEqual(0.45);
    expect(styleUnavailable.color).toBe("#64748b");
    expect(styleUnavailable.dashArray).toBe("4 3");

    // Clique territorial continua funcional com a sobreposição ativa
    const createdLayer = geoJsonSpy.mock.results[geoJsonSpy.mock.results.length - 1].value as L.GeoJSON;
    (createdLayer.getLayers()[1] as any).fire("click");
    expect(onSelectTerritory).toHaveBeenCalledWith(
      expect.objectContaining({ tipo: "bairro", nome: "Paripe" })
    );

    // Recorte Prefeituras-Bairro também aplica preenchimento de vulnerabilidade em opacidade reduzida
    rerender(
      <InteractiveMap
        activeLayer="prefeituras"
        bairros={bairrosComExcecoesMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={geoJsonComExcecoes}
        prefeiturasGeoJson={prefeiturasGeoJsonMock}
        obras={obrasMunicipais}
        heatmapObras={obrasMunicipais}
        selectedTerritory={null}
        onSelectTerritory={onSelectTerritory}
      />
    );
    const prefGeoCall = geoJsonSpy.mock.calls[geoJsonSpy.mock.calls.length - 1];
    const prefStyleFn = (prefGeoCall[1] as L.GeoJSONOptions).style as (f: any) => L.PathOptions;
    const stylePref = prefStyleFn(prefeiturasGeoJsonMock.features[0]);
    expect(stylePref.fillColor).toBe("#ede9fe");
    expect(stylePref.fillOpacity).toBeGreaterThanOrEqual(0.3);
    expect(stylePref.fillOpacity).toBeLessThanOrEqual(0.45);

    geoJsonSpy.mockRestore();
  });

  it("atualiza a legenda do Mapa de Calor com barra contínua roxa (0,00 -> 1,00) e marcadores Isento / Dado indisponível apenas quando aplicáveis", () => {
    const { rerender } = render(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosComExcecoesMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={obrasMunicipais}
        selectedTerritory={null}
        onSelectTerritory={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId("btn-camada-mapa-calor"));
    const legenda = screen.getByTestId("legenda-coropletica");
    expect(screen.queryByTestId("legenda-vulnerabilidade-fundo")).not.toBeInTheDocument();

    // Ativa Vulnerabilidade ao fundo -> exibe barra roxa 0,00 -> 1,00 + Isento + Dado indisponível
    fireEvent.click(screen.getByTestId("btn-toggle-vulnerabilidade-fundo"));
    const legendaVuln = screen.getByTestId("legenda-vulnerabilidade-fundo");
    expect(legendaVuln).toBeInTheDocument();
    expect(legendaVuln).toHaveTextContent("0,00");
    expect(legendaVuln).toHaveTextContent("1,00");
    expect(legenda).toHaveTextContent("Isento");
    expect(legenda).toHaveTextContent("Dado indisponível");

    // Sem Zona Especial e sem dado indisponível -> mantém barra roxa, oculta Isento e Dado indisponível
    rerender(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={obrasMunicipais}
        selectedTerritory={null}
        onSelectTerritory={vi.fn()}
      />
    );
    expect(screen.getByTestId("legenda-vulnerabilidade-fundo")).toBeInTheDocument();
    expect(legenda).not.toHaveTextContent("Isento");
    expect(legenda).not.toHaveTextContent("Dado indisponível");

    // Em Prefeituras-Bairro, mesmo com bairros tendo Zona Especial, não exibe Isento
    rerender(
      <InteractiveMap
        activeLayer="prefeituras"
        bairros={bairrosComExcecoesMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={obrasMunicipais}
        selectedTerritory={null}
        onSelectTerritory={vi.fn()}
      />
    );
    expect(screen.getByTestId("legenda-vulnerabilidade-fundo")).toBeInTheDocument();
    expect(legenda).not.toHaveTextContent("Isento");
  });

  it("cria pinsPane (z-index 500) na inicialização, mantém hierarquia tooltipPane > pinsPane > heatmapPane > overlayPane e abre Ficha Limpa sem selecionar polígono", () => {
    const onSelectTerritory = vi.fn();
    const onSelectObra = vi.fn();
    const mapSpy = vi.spyOn(L, "map");
    const circleMarkerSpy = vi.spyOn(L, "circleMarker");
    const geoJsonSpy = vi.spyOn(L, "geoJSON");
    const stopPropagationSpy = vi.spyOn(L.DomEvent, "stopPropagation");

    render(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={obrasMunicipais}
        selectedTerritory={null}
        onSelectTerritory={onSelectTerritory}
        onSelectObra={onSelectObra}
      />
    );

    const mapInstance = mapSpy.mock.results[mapSpy.mock.results.length - 1].value as L.Map;

    // pinsPane já existe na inicialização mesmo com Pinos de Obras desligado
    const pinsPane = mapInstance.getPane("pinsPane");
    const overlayPane = mapInstance.getPane("overlayPane");
    const tooltipPane = mapInstance.getPane("tooltipPane");
    expect(pinsPane).toBeDefined();
    expect(overlayPane).toBeDefined();
    expect(tooltipPane).toBeDefined();
    expect(pinsPane!.style.zIndex).toBe("500");

    // Ativa Mapa de Calor e Pinos de Obras
    fireEvent.click(screen.getByTestId("btn-camada-mapa-calor"));
    fireEvent.click(screen.getByTestId("btn-toggle-pinos-obras"));

    const heatmapPane = mapInstance.getPane("heatmapPane");
    expect(heatmapPane).toBeDefined();

    const zTooltip = Number(getComputedStyle(tooltipPane!).zIndex || tooltipPane!.style.zIndex || 650);
    const zPins = Number(pinsPane!.style.zIndex);
    const zHeatmap = Number(heatmapPane!.style.zIndex);
    const zOverlay = Number(getComputedStyle(overlayPane!).zIndex || overlayPane!.style.zIndex || 400);

    expect(zTooltip).toBeGreaterThan(zPins);
    expect(zPins).toBeGreaterThan(zHeatmap);
    expect(zHeatmap).toBeGreaterThan(zOverlay);

    // Todos os circleMarkers dos pinos são criados no pinsPane
    expect(circleMarkerSpy).toHaveBeenCalled();
    for (const call of circleMarkerSpy.mock.calls) {
      expect(call[1]?.pane).toBe("pinsPane");
    }

    // Simula clique no primeiro pino com originalEvent -> abre Ficha Limpa e interrompe propagação
    const firstMarker = circleMarkerSpy.mock.results[0].value as L.CircleMarker;
    const domClickEvent = new MouseEvent("click", { bubbles: true, cancelable: true });
    firstMarker.fire("click", { originalEvent: domClickEvent });

    expect(stopPropagationSpy).toHaveBeenCalled();
    expect(onSelectObra).toHaveBeenCalledWith(expect.objectContaining({ id: 101 }));
    expect(onSelectTerritory).not.toHaveBeenCalled();

    // Clique em área sem pino continua selecionando o polígono mesmo com mapa de calor ativo
    const createdGeoJson = geoJsonSpy.mock.results[geoJsonSpy.mock.results.length - 1].value as L.GeoJSON;
    (createdGeoJson.getLayers()[1] as any).fire("click");
    expect(onSelectTerritory).toHaveBeenCalledWith(
      expect.objectContaining({ tipo: "bairro", nome: "Paripe" })
    );

    mapSpy.mockRestore();
    circleMarkerSpy.mockRestore();
    geoJsonSpy.mockRestore();
    stopPropagationSpy.mockRestore();
  });
});

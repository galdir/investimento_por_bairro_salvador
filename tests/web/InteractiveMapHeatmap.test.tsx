import "@testing-library/jest-dom";
import { act, fireEvent, render, screen } from "@testing-library/react";
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

  it("renderiza clusters neutros em pinsPane, reagrupa em zoomend, respeita borda tracejada/aria-label/teclado/tooltip e aproxima ao ativar", () => {
    const onSelectTerritory = vi.fn();
    const onSelectObra = vi.fn();
    const mapSpy = vi.spyOn(L, "map");
    const markerSpy = vi.spyOn(L, "marker");
    const circleMarkerSpy = vi.spyOn(L, "circleMarker");
    const stopPropagationSpy = vi.spyOn(L.DomEvent, "stopPropagation");

    const obrasClusterMock: ObraCompacta[] = [
      // Duas obras próximas na Pituba (coordenadas distintas -> cluster expansível, 1 pontual + 1 bairro)
      {
        ...(obrasMunicipais[0] as ObraCompacta),
        id: 701,
        objeto: "Drenagem Pituba Trecho A",
        nivel: "Pontual",
        latitude: -12.9960,
        longitude: -38.4550,
        semaforo: { status: "VERMELHO", rotulo: "Crítica", motivos: [] },
      },
      {
        ...(obrasMunicipais[0] as ObraCompacta),
        id: 702,
        objeto: "Pavimentação Pituba Trecho B",
        nivel: "Bairro",
        latitude: -12.9980,
        longitude: -38.4570,
        semaforo: { status: "AMARELO", rotulo: "Atenção", motivos: [] },
      },
      // Duas obras exatamente no mesmo ponto em Paripe (100% aproximadas -> cluster indivisível com borda tracejada)
      {
        ...(obrasMunicipais[1] as ObraCompacta),
        id: 703,
        objeto: "Reforma Escola Paripe 1",
        nivel: "Bairro",
        latitude: -12.8250,
        longitude: -38.4750,
        semaforo: { status: "VERDE", rotulo: "No Prazo", motivos: [] },
      },
      {
        ...(obrasMunicipais[1] as ObraCompacta),
        id: 704,
        objeto: "Reforma Escola Paripe 2",
        nivel: "Bairro",
        latitude: -12.8250,
        longitude: -38.4750,
        semaforo: undefined,
      },
    ];

    render(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={obrasClusterMock}
        selectedTerritory={null}
        onSelectTerritory={onSelectTerritory}
        onSelectObra={onSelectObra}
      />
    );

    const mapInstance = mapSpy.mock.results[mapSpy.mock.results.length - 1].value as L.Map;
    fireEvent.click(screen.getByTestId("btn-toggle-pinos-obras"));

    // No zoom 11, temos 2 clusters (2 obras cada) e nenhum circleMarker isolado
    expect(markerSpy).toHaveBeenCalledTimes(2);
    expect(circleMarkerSpy).not.toHaveBeenCalled();

    for (const call of markerSpy.mock.calls) {
      expect(call[1]?.pane).toBe("pinsPane");
    }

    const clusterPituba = markerSpy.mock.results[0].value as L.Marker;
    const clusterParipe = markerSpy.mock.results[1].value as L.Marker;

    const pitubaEl = clusterPituba.getElement()!;
    const paripeEl = clusterParipe.getElement()!;
    expect(pitubaEl).toBeTruthy();
    expect(paripeEl).toBeTruthy();

    // Estilo neutro escuro, diâmetro 28px (faixa 2-9) e borda sólida vs tracejada
    expect(pitubaEl.innerHTML).toContain("background-color:#0f172a");
    expect(pitubaEl.innerHTML).toContain("width:28px;height:28px");
    expect(pitubaEl.innerHTML).toContain("border:2px solid #ffffff");
    expect(pitubaEl.innerHTML).toContain(">2<");

    expect(paripeEl.innerHTML).toContain("border:2px dashed #ffffff");
    expect(paripeEl.innerHTML).toContain(">2<");

    // Acessibilidade (aria-label)
    expect(pitubaEl.getAttribute("aria-label")).toMatch(/2 obras/i);
    expect(pitubaEl.getAttribute("aria-label")).toMatch(/aproximar/i);
    expect(paripeEl.getAttribute("aria-label")).toMatch(/2 obras/i);

    // Tooltips estruturados
    const pitubaTooltip = String(clusterPituba.getTooltip()?.getContent() || "");
    expect(pitubaTooltip).toMatch(/2 obras agrupadas/i);
    expect(pitubaTooltip).toMatch(/Semáforo da Obra/i);
    expect(pitubaTooltip).toMatch(/Amarelo 1/i);
    expect(pitubaTooltip).toMatch(/Vermelho 1/i);
    expect(pitubaTooltip).toMatch(/parcial/i);
    expect(pitubaTooltip).not.toMatch(/Ponto compartilhado/i);

    const paripeTooltip = String(clusterParipe.getTooltip()?.getContent() || "");
    expect(paripeTooltip).toMatch(/Verde 2/i);
    expect(paripeTooltip).toMatch(/100% aproximados/i);
    expect(paripeTooltip).toMatch(/Ponto compartilhado/i);

    // Clique no cluster indivisível interrompe propagação e não seleciona território
    const domClick = new MouseEvent("click", { bubbles: true, cancelable: true });
    clusterParipe.fire("click", { originalEvent: domClick });
    expect(stopPropagationSpy).toHaveBeenCalled();
    expect(onSelectTerritory).not.toHaveBeenCalled();

    // Clique no cluster expansível interrompe propagação, não seleciona polígono e aproxima o mapa
    const zoomBeforeClick = mapInstance.getZoom();
    const expansibleClick = new MouseEvent("click", { bubbles: true, cancelable: true });
    act(() => {
      clusterPituba.fire("click", { originalEvent: expansibleClick });
    });
    expect(stopPropagationSpy).toHaveBeenCalled();
    expect(onSelectTerritory).not.toHaveBeenCalled();
    expect(mapInstance.getZoom()).toBeGreaterThanOrEqual(zoomBeforeClick + 1);

    // Restaura zoom 11 para testar ativação por teclado (Enter) no cluster expansível
    act(() => {
      mapInstance.setZoom(11);
      mapInstance.fire("zoomend");
    });
    const pitubaAfterReset = markerSpy.mock.results[markerSpy.mock.results.length - 2].value as L.Marker;
    const pitubaElAfterReset = pitubaAfterReset.getElement()!;

    // Ativação por teclado (Enter e Space) no cluster expansível aproxima o mapa
    const setViewSpy = vi.spyOn(mapInstance, "setView");
    const fitBoundsSpy = vi.spyOn(mapInstance, "fitBounds");
    const zoomBefore = mapInstance.getZoom();

    const enterEvent = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true });
    act(() => {
      pitubaElAfterReset.dispatchEvent(enterEvent);
    });
    expect(enterEvent.defaultPrevented).toBe(true);
    expect(fitBoundsSpy).toHaveBeenCalled();
    expect(mapInstance.getZoom()).toBeGreaterThanOrEqual(zoomBefore + 1);

    // Reagrupamento automático em zoomend: ao ir para zoom 17, Pituba desmembra em 2 circleMarkers e Paripe segue cluster indivisível
    markerSpy.mockClear();
    circleMarkerSpy.mockClear();
    act(() => {
      mapInstance.setZoom(17);
      mapInstance.fire("zoomend");
    });

    expect(circleMarkerSpy).toHaveBeenCalledTimes(2);
    expect(markerSpy).toHaveBeenCalledTimes(1);

    // Space também ativa sem erro e previne default no cluster restante se expansível; aqui testamos em zoom 11 novamente
    act(() => {
      mapInstance.setZoom(11);
      mapInstance.fire("zoomend");
    });
    const reclusteredPitubaEl = (markerSpy.mock.results[markerSpy.mock.results.length - 2].value as L.Marker).getElement()!;
    const spaceEvent = new KeyboardEvent("keydown", { key: " ", bubbles: true, cancelable: true });
    act(() => {
      reclusteredPitubaEl.dispatchEvent(spaceEvent);
    });
    expect(spaceEvent.defaultPrevented).toBe(true);

    setViewSpy.mockRestore();
    fitBoundsSpy.mockRestore();
    mapSpy.mockRestore();
    markerSpy.mockRestore();
    circleMarkerSpy.mockRestore();
    stopPropagationSpy.mockRestore();
  });

  it("filtra Pinos ativos ao ativar cluster indivisível por clique ou teclado e restaura com Mostrar todos", () => {
    const onSelectTerritory = vi.fn();
    const onSelectObra = vi.fn();
    const markerSpy = vi.spyOn(L, "marker");
    const stopPropagationSpy = vi.spyOn(L.DomEvent, "stopPropagation");

    const obrasClusterMock: ObraCompacta[] = [
      {
        ...(obrasMunicipais[0] as ObraCompacta),
        id: 801,
        objeto: "Drenagem Pituba Trecho A",
        nivel: "Pontual",
        latitude: -12.9960,
        longitude: -38.4550,
        semaforo: { status: "VERMELHO", rotulo: "Crítica", motivos: [] },
      },
      {
        ...(obrasMunicipais[0] as ObraCompacta),
        id: 802,
        objeto: "Pavimentação Pituba Trecho B",
        nivel: "Bairro",
        latitude: -12.9980,
        longitude: -38.4570,
        semaforo: { status: "AMARELO", rotulo: "Atenção", motivos: [] },
      },
      {
        ...(obrasMunicipais[1] as ObraCompacta),
        id: 803,
        objeto: "Reforma Escola Paripe 1",
        nivel: "Bairro",
        latitude: -12.8250,
        longitude: -38.4750,
        semaforo: { status: "VERDE", rotulo: "No Prazo", motivos: [] },
      },
      {
        ...(obrasMunicipais[1] as ObraCompacta),
        id: 804,
        objeto: "Reforma Escola Paripe 2",
        nivel: "Bairro",
        latitude: -12.8250,
        longitude: -38.4750,
        semaforo: { status: "VERDE", rotulo: "No Prazo", motivos: [] },
      },
    ];

    render(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={obrasClusterMock}
        selectedTerritory={null}
        onSelectTerritory={onSelectTerritory}
        onSelectObra={onSelectObra}
      />
    );

    const btnPinos = screen.getByTestId("btn-toggle-pinos-obras");
    fireEvent.click(btnPinos);

    expect(btnPinos).toHaveTextContent("Pinos de Obras (4)");
    expect(screen.getByTestId("painel-pinos-obras")).toHaveTextContent("Pinos ativos (4):");
    expect(screen.queryByTestId("btn-mostrar-todos-pinos")).not.toBeInTheDocument();

    const clusterParipe = markerSpy.mock.results[1].value as L.Marker;
    const domClick = new MouseEvent("click", { bubbles: true, cancelable: true });
    act(() => {
      clusterParipe.fire("click", { originalEvent: domClick });
    });

    expect(stopPropagationSpy).toHaveBeenCalled();
    expect(onSelectTerritory).not.toHaveBeenCalled();

    // Botão superior mantém contagem total, painel exibe contagem focada e botão Mostrar todos
    expect(btnPinos).toHaveTextContent("Pinos de Obras (4)");
    const painel = screen.getByTestId("painel-pinos-obras");
    expect(painel).toHaveTextContent("Pinos ativos (2 de 4 — grupo selecionado):");
    expect(screen.queryByTestId("map-pin-obra-801")).not.toBeInTheDocument();
    expect(screen.queryByTestId("map-pin-obra-802")).not.toBeInTheDocument();
    expect(screen.getByTestId("map-pin-obra-803")).toBeInTheDocument();
    expect(screen.getByTestId("map-pin-obra-804")).toBeInTheDocument();

    // Permite abrir a ficha da obra a partir da lista focada
    fireEvent.click(screen.getByTestId("map-pin-obra-803"));
    expect(onSelectObra).toHaveBeenCalledWith(expect.objectContaining({ id: 803 }));

    // Botão Mostrar todos restaura a lista completa
    fireEvent.click(screen.getByTestId("btn-mostrar-todos-pinos"));
    expect(painel).toHaveTextContent("Pinos ativos (4):");
    expect(screen.queryByTestId("btn-mostrar-todos-pinos")).not.toBeInTheDocument();
    expect(screen.getByTestId("map-pin-obra-801")).toBeInTheDocument();
    expect(screen.getByTestId("map-pin-obra-804")).toBeInTheDocument();

    // Ativação por teclado (Enter e Space) no cluster indivisível também filtra
    const paripeEl = clusterParipe.getElement()!;
    const enterEvent = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true });
    act(() => {
      paripeEl.dispatchEvent(enterEvent);
    });
    expect(enterEvent.defaultPrevented).toBe(true);
    expect(painel).toHaveTextContent("Pinos ativos (2 de 4 — grupo selecionado):");

    fireEvent.click(screen.getByTestId("btn-mostrar-todos-pinos"));
    expect(painel).toHaveTextContent("Pinos ativos (4):");

    const spaceEvent = new KeyboardEvent("keydown", { key: " ", bubbles: true, cancelable: true });
    act(() => {
      paripeEl.dispatchEvent(spaceEvent);
    });
    expect(spaceEvent.defaultPrevented).toBe(true);
    expect(painel).toHaveTextContent("Pinos ativos (2 de 4 — grupo selecionado):");

    markerSpy.mockRestore();
    stopPropagationSpy.mockRestore();
  });

  it("limpa o foco ao desligar pinos, alterar assinatura de pinos/território, trocar recorte, ocorrer zoomend ou ativar cluster expansível, mas preserva ao alternar métrica financeira", () => {
    const onSelectTerritory = vi.fn();
    const mapSpy = vi.spyOn(L, "map");
    const markerSpy = vi.spyOn(L, "marker");

    const buildObras = (valorPagoParipe: number): ObraCompacta[] => [
      {
        ...(obrasMunicipais[0] as ObraCompacta),
        id: 901,
        objeto: "Drenagem Pituba A",
        nivel: "Pontual",
        latitude: -12.9960,
        longitude: -38.4550,
        valorContratualVigente: 1000000,
        valorPago: 400000,
      },
      {
        ...(obrasMunicipais[0] as ObraCompacta),
        id: 902,
        objeto: "Pavimentação Pituba B",
        nivel: "Bairro",
        latitude: -12.9980,
        longitude: -38.4570,
        valorContratualVigente: 1000000,
        valorPago: 500000,
      },
      {
        ...(obrasMunicipais[1] as ObraCompacta),
        id: 903,
        objeto: "Reforma Escola Paripe 1",
        nivel: "Bairro",
        latitude: -12.8250,
        longitude: -38.4750,
        valorContratualVigente: 2000000,
        valorPago: valorPagoParipe,
      },
      {
        ...(obrasMunicipais[1] as ObraCompacta),
        id: 904,
        objeto: "Reforma Escola Paripe 2",
        nivel: "Bairro",
        latitude: -12.8250,
        longitude: -38.4750,
        valorContratualVigente: 2000000,
        valorPago: valorPagoParipe,
      },
    ];

    const territoryParipe = () => ({ id: "paripe", tipo: "bairro" as const, nome: "Paripe", populacao: 50000 });
    const territoryPituba = () => ({ id: "pituba", tipo: "bairro" as const, nome: "Pituba", populacao: 60000 });

    const { rerender } = render(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={buildObras(1500000)}
        selectedTerritory={territoryParipe()}
        onSelectTerritory={onSelectTerritory}
        metricType="vigente"
      />
    );

    const mapInstance = mapSpy.mock.results[mapSpy.mock.results.length - 1].value as L.Map;
    const btnPinos = screen.getByTestId("btn-toggle-pinos-obras");
    fireEvent.click(btnPinos);

    const focusParipeCluster = () => {
      const markers = markerSpy.mock.results
        .map((r) => r.value as L.Marker)
        .filter((m) => Boolean(m?.getElement()?.getAttribute("aria-label")?.includes("mesmo ponto")));
      const clusterParipe = markers[markers.length - 1];
      act(() => {
        clusterParipe.fire("click", { originalEvent: new MouseEvent("click", { bubbles: true, cancelable: true }) });
      });
    };

    // 1) Foca o cluster indivisível de Paripe
    focusParipeCluster();
    const painel = screen.getByTestId("painel-pinos-obras");
    expect(painel).toHaveTextContent("Pinos ativos (2 de 4 — grupo selecionado):");
    expect(screen.getByTestId("map-pin-obra-903")).toHaveTextContent(/Contratual: R\$ 2\.000\.000/);

    // 2) Alternar métrica financeira com NOVAS referências de obras e selectedTerritory (mesma identidade) PRESERVA o foco e atualiza valores
    rerender(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={buildObras(1500000)}
        selectedTerritory={territoryParipe()}
        onSelectTerritory={onSelectTerritory}
        metricType="executado"
      />
    );
    expect(painel).toHaveTextContent("Pinos ativos (2 de 4 — grupo selecionado):");
    expect(screen.getByTestId("map-pin-obra-903")).toHaveTextContent(/Pago: R\$ 1\.500\.000/);

    // 3) (a) Desligar e religar Pinos de Obras limpa o foco
    fireEvent.click(btnPinos);
    fireEvent.click(btnPinos);
    expect(screen.getByTestId("painel-pinos-obras")).toHaveTextContent("Pinos ativos (4):");

    // 4) (b.1) Alterar assinatura do conjunto de pinos limpa o foco
    focusParipeCluster();
    expect(screen.getByTestId("painel-pinos-obras")).toHaveTextContent("Pinos ativos (2 de 4 — grupo selecionado):");
    rerender(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={buildObras(1500000).slice(1)}
        selectedTerritory={territoryParipe()}
        onSelectTerritory={onSelectTerritory}
        metricType="executado"
      />
    );
    expect(screen.getByTestId("painel-pinos-obras")).toHaveTextContent("Pinos ativos (3):");

    // Restaura 4 obras e refoca
    rerender(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={buildObras(1500000)}
        selectedTerritory={territoryParipe()}
        onSelectTerritory={onSelectTerritory}
        metricType="executado"
      />
    );
    focusParipeCluster();
    expect(screen.getByTestId("painel-pinos-obras")).toHaveTextContent("Pinos ativos (2 de 4 — grupo selecionado):");

    // 5) (b.2) Alterar identidade do território selecionado limpa o foco
    rerender(
      <InteractiveMap
        activeLayer="bairros"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={buildObras(1500000)}
        selectedTerritory={territoryPituba()}
        onSelectTerritory={onSelectTerritory}
        metricType="executado"
      />
    );
    expect(screen.getByTestId("painel-pinos-obras")).toHaveTextContent("Pinos ativos (4):");

    // 6) (c) Trocar recorte territorial (bairros -> prefeituras) limpa o foco
    focusParipeCluster();
    expect(screen.getByTestId("painel-pinos-obras")).toHaveTextContent("Pinos ativos (2 de 4 — grupo selecionado):");
    rerender(
      <InteractiveMap
        activeLayer="prefeituras"
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJsonMock}
        prefeiturasGeoJson={null}
        obras={buildObras(1500000)}
        selectedTerritory={territoryPituba()}
        onSelectTerritory={onSelectTerritory}
        metricType="executado"
      />
    );
    expect(screen.getByTestId("painel-pinos-obras")).toHaveTextContent("Pinos ativos (4):");

    // 7) (d) Ocorrer zoomend limpa o foco
    focusParipeCluster();
    expect(screen.getByTestId("painel-pinos-obras")).toHaveTextContent("Pinos ativos (2 de 4 — grupo selecionado):");
    act(() => {
      mapInstance.setZoom(13);
      mapInstance.fire("zoomend");
    });
    expect(screen.getByTestId("painel-pinos-obras")).toHaveTextContent("Pinos ativos (4):");

    // Volta para zoom 11 para ter o cluster expansível da Pituba e testar (e)
    act(() => {
      mapInstance.setZoom(11);
      mapInstance.fire("zoomend");
    });
    focusParipeCluster();
    expect(screen.getByTestId("painel-pinos-obras")).toHaveTextContent("Pinos ativos (2 de 4 — grupo selecionado):");

    // 8) (e) Ativar cluster expansível limpa o foco
    const expansibleMarkers = markerSpy.mock.results
      .map((r) => r.value as L.Marker)
      .filter((m) => Boolean(m?.getElement()?.getAttribute("aria-label")?.includes("aproximar")));
    const clusterPituba = expansibleMarkers[expansibleMarkers.length - 1];
    act(() => {
      clusterPituba.fire("click", { originalEvent: new MouseEvent("click", { bubbles: true, cancelable: true }) });
    });
    expect(screen.getByTestId("painel-pinos-obras")).toHaveTextContent("Pinos ativos (4):");

    mapSpy.mockRestore();
    markerSpy.mockRestore();
  });
});

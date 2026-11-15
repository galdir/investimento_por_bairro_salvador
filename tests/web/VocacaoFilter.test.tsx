import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "../../src/App";

const mockIndexData = {
  metadata: {
    generatedAt: "2026-11-15T10:00:00Z",
    anoReferencia: 2025,
    mandatosDisponiveis: ["2025-2028", "2021-2024"],
  },
  kpis_globais: {
    totalObras: 3,
    valorTotal: 35000000.0,
    totalAtivas: 3,
    totalCriticas: 0,
    percentualCriticas: 0.0,
    totalAditivosValor: 0.0,
    percentualMedioAditivos: 0.0,
    totalEmpenhado: 35000000.0,
    totalLiquidado: 20000000.0,
    totalPago: 15000000.0,
    investimentoPorHabitanteCidade: 1000.0,
    totalNaoLocalizado: 0,
    valorNaoLocalizado: 0.0,
    valorPagoNaoLocalizado: 0.0,
    percentualNaoLocalizado: 0.0,
  },
  prefeituras_bairro: [
    {
      id: 1,
      nome: "Barra/Pituba",
      populacao_total: 10000,
      indice_vulnerabilidade: 0.15,
      valorTotal: 30000000.0,
      valorPago: 12000000.0,
      investimentoPorHabitante: 3000.0,
      investimentoPorHabitantePago: 1200.0,
      totalObras: 2,
      obrasVerde: 2,
      obrasAmarelo: 0,
      obrasVermelho: 0,
    },
    {
      id: 2,
      nome: "Liberdade/São Caetano",
      populacao_total: 25000,
      indice_vulnerabilidade: 0.65,
      valorTotal: 5000000.0,
      valorPago: 3000000.0,
      investimentoPorHabitante: 200.0,
      investimentoPorHabitantePago: 120.0,
      totalObras: 1,
      obrasVerde: 1,
      obrasAmarelo: 0,
      obrasVermelho: 0,
    },
  ],
  bairros: [
    {
      id: 101,
      nome: "Pituba",
      prefeitura_bairro: "Barra/Pituba",
      populacao: 10000,
      indice_vulnerabilidade: 0.15,
      is_zona_especial_nao_residencial: false,
      valorTotal: 30000000.0,
      valorPago: 12000000.0,
      investimentoPorHabitante: 3000.0,
      investimentoPorHabitantePago: 1200.0,
      totalObras: 2,
      obrasVerde: 2,
      obrasAmarelo: 0,
      obrasVermelho: 0,
    },
    {
      id: 102,
      nome: "Liberdade",
      prefeitura_bairro: "Liberdade/São Caetano",
      populacao: 25000,
      indice_vulnerabilidade: 0.65,
      is_zona_especial_nao_residencial: false,
      valorTotal: 5000000.0,
      valorPago: 3000000.0,
      investimentoPorHabitante: 200.0,
      investimentoPorHabitantePago: 120.0,
      totalObras: 1,
      obrasVerde: 1,
      obrasAmarelo: 0,
      obrasVermelho: 0,
    },
  ],
  obras: [
    {
      id: 101,
      unidadeGestora: "SMED",
      numeroContrato: "001/2025",
      objeto: "Reforma de Escola Municipal na Liberdade",
      valorOriginal: 5000000.0,
      valorContratualVigente: 5000000.0,
      valorPago: 3000000.0,
      percentualExecutado: 60.0,
      situacao: "Em Execução",
      credor: "CONSTRUTORA BAIRRO LTDA",
      tema: "Educação e Escolas",
      vocacao: "Vizinhança e Comunidade",
      semaforo: { status: "VERDE", rotulo: "Verde (No Prazo)", motivos: [] },
      ano: 2025,
      mandatos: ["2025-2028"],
      nivel: "Pontual",
      bairro: "Liberdade",
      prefeituraBairro: "Liberdade/São Caetano",
      latitude: -12.94,
      longitude: -38.49,
    },
    {
      id: 102,
      unidadeGestora: "SEINFRA",
      numeroContrato: "002/2025",
      objeto: "Requalificação da Orla da Pituba",
      valorOriginal: 10000000.0,
      valorContratualVigente: 10000000.0,
      valorPago: 4000000.0,
      percentualExecutado: 40.0,
      situacao: "Em Execução",
      credor: "CONSTRUTORA ORLA LTDA",
      tema: "Mobilidade, Pavimentação e Drenagem",
      vocacao: "Mobilidade Estrutural e Orlas",
      semaforo: { status: "VERDE", rotulo: "Verde (No Prazo)", motivos: [] },
      ano: 2025,
      mandatos: ["2025-2028"],
      nivel: "Pontual",
      bairro: "Pituba",
      prefeituraBairro: "Barra/Pituba",
      latitude: -13.0,
      longitude: -38.46,
    },
    {
      id: 103,
      unidadeGestora: "SEINFRA",
      numeroContrato: "003/2025",
      objeto: "Construção do Complexo Multiuso Arena Salvador",
      valorOriginal: 20000000.0,
      valorContratualVigente: 20000000.0,
      valorPago: 8000000.0,
      percentualExecutado: 40.0,
      situacao: "Em Execução",
      credor: "CONSÓRCIO ARENA",
      tema: "Praças, Esporte e Lazer",
      vocacao: "Equipamentos e Marcos da Cidade",
      semaforo: { status: "VERDE", rotulo: "Verde (No Prazo)", motivos: [] },
      ano: 2025,
      mandatos: ["2025-2028"],
      nivel: "Pontual",
      bairro: "Pituba",
      prefeituraBairro: "Barra/Pituba",
      latitude: -13.01,
      longitude: -38.45,
    },
  ],
};

const mockBairrosGeo = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { id: 101, nome: "Pituba", prefeitura_bairro: "Barra/Pituba", populacao: 10000, valorTotal: 30000000.0, investimentoPorHabitante: 3000.0 },
      geometry: { type: "Polygon", coordinates: [[[-38.47, -13.01], [-38.45, -13.01], [-38.45, -12.99], [-38.47, -13.01]]] },
    },
    {
      type: "Feature",
      properties: { id: 102, nome: "Liberdade", prefeitura_bairro: "Liberdade/São Caetano", populacao: 25000, valorTotal: 5000000.0, investimentoPorHabitante: 200.0 },
      geometry: { type: "Polygon", coordinates: [[[-38.50, -12.95], [-38.48, -12.95], [-38.48, -12.93], [-38.50, -12.95]]] },
    },
  ],
};

const mockPbGeo = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { id: 1, nome: "Barra/Pituba", populacao_total: 10000, valorTotal: 30000000.0, investimentoPorHabitante: 3000.0 },
      geometry: { type: "Polygon", coordinates: [[[-38.47, -13.01], [-38.45, -13.01], [-38.45, -12.99], [-38.47, -13.01]]] },
    },
  ],
};

const mockObra103Detalhe = {
  id: 103,
  unidadeGestora: "SEINFRA",
  numeroContrato: "003/2025",
  objeto: "Construção do Complexo Multiuso Arena Salvador",
  situacao: "Em Execução",
  empreiteira: { razaoSocial: "CONSÓRCIO ARENA", cnpj: "12.345.678/0001-90", totalObras: 1, valorTotalContratado: 20000000.0 },
  vigencia: { dataInicio: "2025-01-10", dataFimOriginal: "2026-12-31", dataTerminoAtualizado: "2026-12-31" },
  dom: { nuDom: "9.001" },
  funilFinanceiro: { valorOriginal: 20000000.0, valorContratualVigente: 20000000.0, valorEmpenhado: 20000000.0, valorLiquidado: 8000000.0, valorPago: 8000000.0, percentualExecutado: 40.0 },
  aditivos: [],
  dotacao: [],
  tema: "Praças, Esporte e Lazer",
  vocacao: "Equipamentos e Marcos da Cidade",
  semaforo: { status: "VERDE", rotulo: "Verde (No Prazo)", motivos: [] },
  nivel: "Pontual",
  bairro: "Pituba",
  prefeituraBairro: "Barra/Pituba",
};

describe("Filtro Multi-Seleção de Vocação da Obra", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("index_2025.json")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockIndexData) });
      }
      if (url.includes("bairros.geojson")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockBairrosGeo) });
      }
      if (url.includes("prefeituras_bairro.geojson")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockPbGeo) });
      }
      if (url.includes("obras/103.json")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockObra103Detalhe) });
      }
      return Promise.reject(new Error(`URL não mockada: ${url}`));
    }) as any;
  });

  it("inicia com os 3 chips de Vocação ativos por padrão, sem botão Limpar Filtros e preservando 100% dos totais", async () => {
    render(<App />);

    const chipViz = await screen.findByTestId("chip-vocacao-vizinhanca");
    const chipMob = screen.getByTestId("chip-vocacao-mobilidade");
    const chipEq = screen.getByTestId("chip-vocacao-equipamentos");

    expect(chipViz).toHaveAttribute("aria-pressed", "true");
    expect(chipMob).toHaveAttribute("aria-pressed", "true");
    expect(chipEq).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByTestId("btn-limpar-filtros")).not.toBeInTheDocument();

    expect(screen.getByTestId("contador-obras-filtradas")).toHaveTextContent("Exibindo 3 de 3 obras");
    expect(screen.getByTestId("kpi-obras-ativas")).toHaveTextContent("3 / 3");
    expect(screen.getByTestId("kpi-total-investido")).toHaveTextContent("R$ 35.000.000");
  });

  it("recalcula KPIs, Ranking Territorial, Raio-X e Tabela em tempo real ao desmarcar vocações e impede desmarcar a última ativa", async () => {
    render(<App />);

    const chipViz = await screen.findByTestId("chip-vocacao-vizinhanca");
    const chipMob = screen.getByTestId("chip-vocacao-mobilidade");
    const chipEq = screen.getByTestId("chip-vocacao-equipamentos");

    // Desmarca Equipamentos e Marcos da Cidade (fica Vizinhança + Mobilidade = R$ 15M, 2 obras)
    fireEvent.click(chipEq);
    expect(chipEq).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByTestId("btn-limpar-filtros")).toBeInTheDocument();
    expect(screen.getByTestId("contador-obras-filtradas")).toHaveTextContent("Exibindo 2 de 3 obras");
    expect(screen.getByTestId("kpi-obras-ativas")).toHaveTextContent("2 / 2");
    expect(screen.getByTestId("kpi-total-investido")).toHaveTextContent("R$ 15.000.000");

    // Desmarca Mobilidade Estrutural e Orlas (fica apenas Vizinhança = R$ 5M, 1 obra)
    fireEvent.click(chipMob);
    expect(chipMob).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByTestId("contador-obras-filtradas")).toHaveTextContent("Exibindo 1 de 3 obras");
    expect(screen.getByTestId("kpi-total-investido")).toHaveTextContent("R$ 5.000.000");

    // Tenta desmarcar a última categoria ativa (Vizinhança) -> deve permanecer ativa
    fireEvent.click(chipViz);
    expect(chipViz).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("contador-obras-filtradas")).toHaveTextContent("Exibindo 1 de 3 obras");

    // Verifica Ranking Territorial recalculado (Pituba cai para R$ 0,00 porque só tinha Mobilidade e Equipamentos)
    fireEvent.click(screen.getByTestId("tab-ranking"));
    const pitubaItem = (await screen.findByText("Pituba")).closest("[data-testid^='ranking-bairro-']") as HTMLElement;
    expect(pitubaItem).toHaveTextContent("0 obras");

    // Seleciona Pituba para verificar Raio-X recalculado e depois restaura via Limpar Filtros
    fireEvent.click(pitubaItem);
    expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Pituba");
    expect(screen.getByTestId("raio-x-total-investido")).toHaveTextContent("R$ 0");

    // Clica em Limpar Filtros -> restaura as 3 vocações
    fireEvent.click(screen.getByTestId("btn-limpar-filtros"));
    expect(chipViz).toHaveAttribute("aria-pressed", "true");
    expect(chipMob).toHaveAttribute("aria-pressed", "true");
    expect(chipEq).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByTestId("btn-limpar-filtros")).not.toBeInTheDocument();
  });

  it("exibe selo de Vocação na Tabela de Obras e na Ficha Limpa da Obra", async () => {
    render(<App />);

    await screen.findByTestId("chip-vocacao-vizinhanca");
    fireEvent.click(screen.getByTestId("tab-tabela"));

    const row103 = await screen.findByTestId("linha-obra-103");
    expect(row103).toHaveTextContent("Equipamentos e Marcos da Cidade");

    fireEvent.click(row103);
    await waitFor(() => {
      expect(screen.getByTestId("ficha-limpa-vocacao")).toHaveTextContent("Equipamentos e Marcos da Cidade");
    });
  });
});

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../../src/App";

const minimalIndexData = {
  metadata: {
    generatedAt: "2026-11-06T20:00:00Z",
    anoReferencia: 2025,
    mandatosDisponiveis: ["2025-2028", "2021-2024"],
  },
  kpis_globais: {
    totalObras: 1,
    valorTotal: 12000000.0,
    totalAtivas: 1,
    totalCriticas: 0,
    percentualCriticas: 0,
    totalAditivosValor: 0,
    percentualMedioAditivos: 0,
    totalEmpenhado: 10000000.0,
    totalLiquidado: 8000000.0,
    totalPago: 7860000.0,
    investimentoPorHabitanteCidade: 120.92,
    totalNaoLocalizado: 0,
    valorNaoLocalizado: 0,
    valorPagoNaoLocalizado: 0,
    percentualNaoLocalizado: 0,
  },
  prefeituras_bairro: [
    {
      id: 1,
      nome: "Barra/Pituba",
      populacao_total: 65000,
      indice_vulnerabilidade: 0.12,
      valorTotal: 12000000.0,
      valorPago: 7860000.0,
      investimentoPorHabitante: 184.62,
      investimentoPorHabitantePago: 120.92,
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
      populacao: 65000,
      indice_vulnerabilidade: 0.12,
      is_zona_especial_nao_residencial: false,
      valorTotal: 12000000.0,
      valorPago: 7860000.0,
      investimentoPorHabitante: 184.62,
      investimentoPorHabitantePago: 120.92,
      totalObras: 1,
      obrasVerde: 1,
      obrasAmarelo: 0,
      obrasVermelho: 0,
    },
  ],
  obras: [
    {
      id: 1001,
      unidadeGestora: "SUCOP",
      numeroContrato: "001/2024",
      objeto: "Requalificação da Orla da Pituba",
      valorOriginal: 12000000.0,
      valorContratualVigente: 12000000.0,
      valorAditivos: 0.0,
      deltaPercentualValor: 0.0,
      valorPago: 7860000.0,
      percentualExecutado: 65.5,
      situacao: "Em Execução",
      credor: "CONSTRUTORA SALVADOR LTDA",
      tema: "Mobilidade, Pavimentação e Drenagem",
      vocacao: "Mobilidade Estrutural e Orlas",
      semaforo: {
        status: "VERDE",
        rotulo: "Verde (No Prazo)",
        motivos: ["No prazo"],
        deltaPercentualValor: 0.0,
      },
      ano: 2024,
      mandatos: ["2021-2024", "2025-2028"],
      dtInicioVigencia: "2024-01-10T00:00:00.000Z",
      dtTerminoVigenciaAtualizado: "2027-12-31T00:00:00.000Z",
      nivel: "Bairro",
      bairro: "Pituba",
      prefeituraBairro: "Barra/Pituba",
      latitude: -12.9965,
      longitude: -38.4552,
    },
  ],
};

const emptyGeo = { type: "FeatureCollection", features: [] };

describe("Navegação e Integração do Glossário Cidadão via Hash", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    window.location.hash = "";
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    window.location.hash = "";
  });

  it("abre #glossario imediatamente antes do carregamento de dados e permite abrir a Nota Metodológica", () => {
    globalThis.fetch = vi.fn(() => new Promise<Response>(() => {})) as typeof fetch;
    window.location.hash = "#glossario";

    render(<App />);

    expect(screen.getByTestId("pagina-glossario")).toBeInTheDocument();
    expect(screen.queryByText(/Carregando dados territoriais de Salvador/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("btn-glossario-nota-metodologica"));
    expect(screen.getByTestId("modal-nota-metodologica")).toBeInTheDocument();
  });

  it("abre âncora direta #glossario-<slug> destacando e focando o verbete correspondente", () => {
    globalThis.fetch = vi.fn(() => new Promise<Response>(() => {})) as typeof fetch;
    window.location.hash = "#glossario-frente-de-medicao";

    render(<App />);

    const card = screen.getByTestId("glossario-card-frente-de-medicao");
    expect(card).toHaveAttribute("aria-current", "true");
    expect(document.activeElement).toBe(card);
  });

  it("abre pelo cabeçalho do painel, responde a hashchange e retorna preservando filtros e território", async () => {
    globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("atual.json")) {
        return Promise.resolve({ ok: false, status: 404 } as Response);
      }
      if (url.includes("index_2025.json")) {
        return Promise.resolve({
          ok: true,
          json: async () => minimalIndexData,
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        json: async () => emptyGeo,
      } as Response);
    }) as typeof fetch;

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("header-comparativo")).toBeInTheDocument();
    });

    // Aplica filtro de vocação e seleciona território
    const chipVizinhanca = screen.getByTestId("chip-vocacao-vizinhanca");
    expect(chipVizinhanca).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(chipVizinhanca);
    expect(chipVizinhanca).toHaveAttribute("aria-pressed", "false");

    const pbItem = await screen.findByText("Barra/Pituba");
    fireEvent.click(pbItem);

    await waitFor(() => {
      expect(screen.getByTestId("raio-x-container")).toBeInTheDocument();
    });

    // Clica no link discreto do cabeçalho para abrir o Glossário
    const headerLink = screen.getByTestId("link-header-glossario");
    expect(headerLink).toHaveAttribute("href", "#glossario");
    fireEvent.click(headerLink);

    await waitFor(() => {
      expect(screen.getByTestId("pagina-glossario")).toBeInTheDocument();
    });

    // Retorna ao painel pelo botão "Voltar ao Painel"
    fireEvent.click(screen.getByTestId("btn-voltar-painel"));

    await waitFor(() => {
      expect(screen.getByTestId("header-comparativo")).toBeInTheDocument();
    });

    expect(window.location.hash).toBe("");
    expect(screen.getByTestId("chip-vocacao-vizinhanca")).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByTestId("raio-x-container")).toBeInTheDocument();
  });
});

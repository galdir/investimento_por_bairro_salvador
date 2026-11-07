import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "../../src/App";

const mockIndexData = {
  metadata: {
    generatedAt: "2026-11-06T20:00:00Z",
    anoReferencia: 2025,
  },
  kpis_globais: {
    totalObras: 25,
    valorTotal: 150000000.0,
    totalAtivas: 18,
    totalEmpenhado: 120000000.0,
    totalLiquidado: 95000000.0,
    totalPago: 90000000.0,
    investimentoPorHabitanteCidade: 62.5,
  },
  prefeituras_bairro: [
    { id: 1, nome: "Barra/Pituba", populacao_total: 65000 },
    { id: 2, nome: "Liberdade/São Caetano", populacao_total: 48000 },
  ],
  bairros: [
    {
      id: 101,
      nome: "Pituba",
      prefeitura_bairro: "Barra/Pituba",
      populacao: 65000,
      indice_vulnerabilidade: 0.12,
      is_zona_especial_nao_residencial: false,
    },
    {
      id: 102,
      nome: "Aeroporto",
      prefeitura_bairro: "Itapuã/Ipitanga",
      populacao: 0,
      indice_vulnerabilidade: 0.05,
      is_zona_especial_nao_residencial: true,
    },
    {
      id: 104,
      nome: "Centro Administrativo da Bahia - CAB",
      prefeitura_bairro: "Cabula/Tancredo Neves",
      populacao: 5,
      indice_vulnerabilidade: 0.08,
      is_zona_especial_nao_residencial: true,
    },
  ],
  obras: [
    {
      id: 1001,
      unidadeGestora: "SUCOP",
      numeroContrato: "001/2024",
      objeto: "Requalificação da Orla da Pituba",
      valorContratualVigente: 12000000.0,
      percentualExecutado: 65.5,
      situacao: "Em Execução",
      credor: "CONSTRUTORA SALVADOR LTDA",
    },
  ],
};

const mockBairrosGeo = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: {
        id: 101,
        nome: "Pituba",
        prefeitura_bairro: "Barra/Pituba",
        populacao: 65000,
        indice_vulnerabilidade: 0.12,
        is_zona_especial_nao_residencial: false,
      },
      geometry: { type: "Polygon", coordinates: [[[-38.46, -13.0], [-38.45, -13.0], [-38.45, -12.99], [-38.46, -13.0]]] },
    },
    {
      type: "Feature",
      properties: {
        id: 102,
        nome: "Aeroporto",
        prefeitura_bairro: "Itapuã/Ipitanga",
        populacao: 0,
        indice_vulnerabilidade: 0.05,
        is_zona_especial_nao_residencial: true,
      },
      geometry: { type: "Polygon", coordinates: [[[-38.33, -12.91], [-38.32, -12.91], [-38.32, -12.9], [-38.33, -12.91]]] },
    },
  ],
};

const mockPbGeo = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: {
        id: 1,
        nome: "Barra/Pituba",
        populacao_total: 65000,
      },
      geometry: { type: "Polygon", coordinates: [[[-38.53, -13.01], [-38.44, -13.01], [-38.44, -12.98], [-38.53, -13.01]]] },
    },
  ],
};

describe("Seam 2: Painel Web do Mapa das Obras e Território de Salvador", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.includes("index_")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockIndexData),
          });
        }
        if (url.includes("bairros.geojson")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockBairrosGeo),
          });
        }
        if (url.includes("prefeituras_bairro.geojson")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockPbGeo),
          });
        }
        return Promise.reject(new Error("URL desconhecida"));
      })
    );
  });

  it("renderiza os KPIs globais de Salvador no cabeçalho", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("kpi-total-investido")).toBeInTheDocument();
    });

    expect(screen.getByTestId("kpi-total-investido")).toHaveTextContent("R$ 150.000.000");
    expect(screen.getByTestId("kpi-obras-ativas")).toHaveTextContent("18 / 25");
    expect(screen.getByTestId("kpi-investimento-per-capita")).toHaveTextContent("R$ 62,50");
  });

  it("permite alternar entre as camadas de Bairros Oficiais e Prefeituras-Bairro", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Bairros Oficiais/i })).toBeInTheDocument();
    });

    const btnPb = screen.getByRole("button", { name: /Prefeituras-Bairro/i });
    expect(btnPb).toBeInTheDocument();

    fireEvent.click(btnPb);
    expect(screen.getByTestId("active-layer-indicator")).toHaveTextContent(/Prefeituras-Bairro/i);
  });

  it("exibe o Raio-X do Bairro com dados do Censo 2022 e vulnerabilidade ao clicar no mapa", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("territory-selector-pituba")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("territory-selector-pituba"));

    expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Pituba");
    expect(screen.getByTestId("raio-x-populacao")).toHaveTextContent("65.000");
    expect(screen.getByTestId("raio-x-vulnerabilidade")).toHaveTextContent("0,12");
    expect(screen.queryByTestId("badge-zona-especial")).not.toBeInTheDocument();
  });

  it("sinaliza adequadamente a Zona Especial Não-Residencial no painel lateral", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("territory-selector-aeroporto")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("territory-selector-aeroporto"));

    expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Aeroporto");
    expect(screen.getByTestId("badge-zona-especial")).toBeInTheDocument();
    expect(screen.getByTestId("badge-zona-especial")).toHaveTextContent(/Zona Especial Não-Residencial/i);
  });
});

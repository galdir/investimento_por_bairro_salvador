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
    totalCriticas: 2,
    percentualCriticas: 8.0,
    totalAditivosValor: 1400000.0,
    percentualMedioAditivos: 17.7,
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
      valorOriginal: 12000000.0,
      valorContratualVigente: 12000000.0,
      valorAditivos: 0.0,
      deltaPercentualValor: 0.0,
      valorPago: 7860000.0,
      percentualExecutado: 65.5,
      situacao: "Em Execução",
      credor: "CONSTRUTORA SALVADOR LTDA",
      tema: "Mobilidade, Pavimentação e Drenagem",
      semaforo: {
        status: "VERDE",
        rotulo: "Verde (No Prazo)",
        motivos: ["No prazo"],
        deltaPercentualValor: 0.0,
      },
      ano: 2024,
    },
    {
      id: 1002,
      unidadeGestora: "CODESAL",
      numeroContrato: "002/2024",
      objeto: "Contenção de Encosta na Liberdade",
      valorOriginal: 2000000.0,
      valorContratualVigente: 2400000.0,
      valorAditivos: 400000.0,
      deltaPercentualValor: 20.0,
      valorPago: 1200000.0,
      percentualExecutado: 50.0,
      situacao: "Em Execução",
      credor: "BAHIA ENGENHARIA S/A",
      tema: "Encostas e Contenção",
      semaforo: {
        status: "AMARELO",
        rotulo: "Amarelo (Atenção)",
        motivos: ["Aditivo entre 10% e 25%"],
        deltaPercentualValor: 20.0,
      },
      ano: 2025,
    },
    {
      id: 1003,
      unidadeGestora: "FME",
      numeroContrato: "015/2024",
      objeto: "Construção de Escola Municipal no Subúrbio",
      valorOriginal: 3000000.0,
      valorContratualVigente: 4000000.0,
      valorAditivos: 1000000.0,
      deltaPercentualValor: 33.3,
      valorPago: 800000.0,
      percentualExecutado: 20.0,
      situacao: "Paralisada",
      credor: "NORDESTE OBRAS LTDA",
      tema: "Educação e Escolas",
      semaforo: {
        status: "VERMELHO",
        rotulo: "Vermelho (Crítica)",
        motivos: ["Paralisada", "Aditivo superior a 25%"],
        deltaPercentualValor: 33.3,
      },
      ano: 2025,
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

  it("renderiza os 5 KPIs superiores de Salvador no cabeçalho", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("kpi-total-investido")).toBeInTheDocument();
    });

    // 1. Total Investido
    expect(screen.getByTestId("kpi-total-investido")).toHaveTextContent("R$ 150.000.000");
    // 2. Obras Ativas / Totais
    expect(screen.getByTestId("kpi-obras-ativas")).toHaveTextContent("18 / 25");
    // 3. Obras Críticas
    expect(screen.getByTestId("kpi-obras-criticas")).toHaveTextContent("2");
    // 4. Aditivos de Preço
    expect(screen.getByTestId("kpi-aditivos-preco")).toHaveTextContent("R$ 1.400.000");
    // 5. Investimento por Habitante
    expect(screen.getByTestId("kpi-investimento-per-capita")).toHaveTextContent("R$ 62,50");
  });

  it("permite alternar a métrica financeira entre Valor Contratual Vigente e Valor Executado/Pago", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("btn-metrica-executado")).toBeInTheDocument();
    });

    // Clica no botão de alternar para 'Valor Executado / Pago'
    fireEvent.click(screen.getByTestId("btn-metrica-executado"));

    // Total recalculado com a soma de valorPago das obras filtradas:
    // 7.860.000 + 1.200.000 + 800.000 = 9.860.000
    await waitFor(() => {
      expect(screen.getByTestId("kpi-total-investido")).toHaveTextContent("R$ 9.860.000");
    });

    // Retorna para 'Valor Contratual Vigente'
    fireEvent.click(screen.getByTestId("btn-metrica-vigente"));
    await waitFor(() => {
      expect(screen.getByTestId("kpi-total-investido")).toHaveTextContent("R$ 150.000.000");
    });
  });

  it("filtra obras por busca textual, órgão, tema e semáforo recalculando os KPIs", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("filtro-busca")).toBeInTheDocument();
    });

    // 1. Filtrar por texto: 'Escola'
    fireEvent.change(screen.getByTestId("filtro-busca"), { target: { value: "Escola" } });

    await waitFor(() => {
      expect(screen.getByTestId("contador-obras-filtradas")).toHaveTextContent("Exibindo 1 de 3 obras");
      expect(screen.getByTestId("kpi-total-investido")).toHaveTextContent("R$ 4.000.000");
      expect(screen.getByTestId("kpi-obras-criticas")).toHaveTextContent("1");
    });

    // 2. Limpar filtros
    fireEvent.click(screen.getByTestId("btn-limpar-filtros"));
    await waitFor(() => {
      expect(screen.getByTestId("contador-obras-filtradas")).toHaveTextContent("Exibindo 3 de 3 obras");
    });

    // 3. Filtrar por Semáforo: Vermelho
    fireEvent.change(screen.getByTestId("filtro-semaforo"), { target: { value: "VERMELHO" } });
    await waitFor(() => {
      expect(screen.getByTestId("contador-obras-filtradas")).toHaveTextContent("Exibindo 1 de 3 obras");
      expect(screen.getByTestId("kpi-total-investido")).toHaveTextContent("R$ 4.000.000");
    });

    // 4. Filtrar por Tema da Obra: Encostas e Contenção
    fireEvent.change(screen.getByTestId("filtro-semaforo"), { target: { value: "todos" } });
    fireEvent.change(screen.getByTestId("filtro-tema"), { target: { value: "Encostas e Contenção" } });
    await waitFor(() => {
      expect(screen.getByTestId("contador-obras-filtradas")).toHaveTextContent("Exibindo 1 de 3 obras");
      expect(screen.getByTestId("kpi-total-investido")).toHaveTextContent("R$ 2.400.000");
    });
  });

  it("permite alternar para a Tabela Detalhada de Obras com ordenação por coluna e badges do Semáforo", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("tab-tabela")).toBeInTheDocument();
    });

    // Alterna para a visão de tabela
    fireEvent.click(screen.getByTestId("tab-tabela"));

    await waitFor(() => {
      expect(screen.getByTestId("tabela-obras")).toBeInTheDocument();
    });

    // As três obras devem estar presentes
    expect(screen.getByTestId("linha-obra-1001")).toBeInTheDocument();
    expect(screen.getByTestId("linha-obra-1002")).toBeInTheDocument();
    expect(screen.getByTestId("linha-obra-1003")).toBeInTheDocument();

    // Badges do Semáforo presentes
    expect(screen.getByTestId("badge-semaforo-verde")).toBeInTheDocument();
    expect(screen.getByTestId("badge-semaforo-amarelo")).toBeInTheDocument();
    expect(screen.getByTestId("badge-semaforo-vermelho")).toBeInTheDocument();

    // Ordenação clicável por coluna de Objeto
    fireEvent.click(screen.getByTestId("sort-objeto"));
    const linhas = screen.getAllByTestId(/^linha-obra-/);
    expect(linhas.length).toBe(3);
  });

  it("permite alternar entre as camadas de Bairros Oficiais e Prefeituras-Bairro no mapa", async () => {
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

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
    totalNaoLocalizado: 1,
    valorNaoLocalizado: 1500000.0,
    valorPagoNaoLocalizado: 1350000.0,
    percentualNaoLocalizado: 1.0,
  },
  prefeituras_bairro: [
    {
      id: 1,
      nome: "Barra/Pituba",
      populacao_total: 65000,
      valorTotal: 12000000.0,
      investimentoPorHabitante: 184.62,
      totalObras: 1,
      obrasVerde: 1,
      obrasAmarelo: 0,
      obrasVermelho: 0,
    },
    {
      id: 2,
      nome: "Liberdade/São Caetano",
      populacao_total: 48000,
      valorTotal: 2400000.0,
      investimentoPorHabitante: 50.0,
      totalObras: 1,
      obrasVerde: 0,
      obrasAmarelo: 1,
      obrasVermelho: 0,
    },
    {
      id: 3,
      nome: "Subúrbio/Ilhas",
      populacao_total: 80000,
      valorTotal: 4000000.0,
      investimentoPorHabitante: 50.0,
      totalObras: 1,
      obrasVerde: 0,
      obrasAmarelo: 0,
      obrasVermelho: 1,
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
      investimentoPorHabitante: 184.62,
      totalObras: 1,
      obrasVerde: 1,
      obrasAmarelo: 0,
      obrasVermelho: 0,
    },
    {
      id: 102,
      nome: "Aeroporto",
      prefeitura_bairro: "Itapuã/Ipitanga",
      populacao: 0,
      indice_vulnerabilidade: 0.05,
      is_zona_especial_nao_residencial: true,
      valorTotal: 10000000.0,
      investimentoPorHabitante: 0.0,
      totalObras: 1,
      obrasVerde: 1,
      obrasAmarelo: 0,
      obrasVermelho: 0,
    },
    {
      id: 104,
      nome: "Centro Administrativo da Bahia - CAB",
      prefeitura_bairro: "Cabula/Tancredo Neves",
      populacao: 5,
      indice_vulnerabilidade: 0.08,
      is_zona_especial_nao_residencial: true,
      valorTotal: 500000.0,
      investimentoPorHabitante: 0.0,
      totalObras: 1,
      obrasVerde: 1,
      obrasAmarelo: 0,
      obrasVermelho: 0,
    },
    {
      id: 105,
      nome: "Liberdade",
      prefeitura_bairro: "Liberdade/São Caetano",
      populacao: 48000,
      indice_vulnerabilidade: 0.78,
      is_zona_especial_nao_residencial: false,
      valorTotal: 2400000.0,
      investimentoPorHabitante: 50.0,
      totalObras: 1,
      obrasVerde: 0,
      obrasAmarelo: 1,
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
      semaforo: {
        status: "VERDE",
        rotulo: "Verde (No Prazo)",
        motivos: ["No prazo"],
        deltaPercentualValor: 0.0,
      },
      ano: 2024,
      nivel: "Bairro",
      bairro: "Pituba",
      prefeituraBairro: "Barra/Pituba",
      latitude: -12.9965,
      longitude: -38.4552,
      estagioAlocacao: "Stage 1 (Bairro)",
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
      nivel: "Pontual",
      bairro: "Liberdade",
      prefeituraBairro: "Liberdade/São Caetano",
      latitude: -12.955,
      longitude: -38.485,
      estagioAlocacao: "Stage 1 (Equipamento)",
    },
    {
      id: 1003,
      unidadeGestora: "FME",
      numeroContrato: "015/2024",
      objeto: "Construção de Escola Municipal no Lote Subúrbio",
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
      nivel: "Regional (Prefeitura-Bairro)",
      bairro: null,
      prefeituraBairro: "Subúrbio/Ilhas",
      latitude: null,
      longitude: null,
      estagioAlocacao: "Stage 1 (Lote Regional)",
    },
    {
      id: 1004,
      unidadeGestora: "DESAL",
      numeroContrato: "042/2024",
      objeto: "Requalificação e modernização de praça esportiva genérica",
      valorOriginal: 1500000.0,
      valorContratualVigente: 1500000.0,
      valorAditivos: 0.0,
      deltaPercentualValor: 0.0,
      valorPago: 1350000.0,
      percentualExecutado: 90.0,
      situacao: "Em Execução",
      credor: "SALVADOR PARQUES E OBRAS EIRELI",
      tema: "Praças, Esporte e Lazer",
      semaforo: {
        status: "VERDE",
        rotulo: "Verde (No Prazo)",
        motivos: ["No prazo"],
        deltaPercentualValor: 0.0,
      },
      ano: 2025,
      nivel: "Escopo Cidade (Não-Localizado)",
      bairro: null,
      prefeituraBairro: null,
      latitude: null,
      longitude: null,
      estagioAlocacao: "Não-Localizado (Transparência Opaca)",
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
        valorTotal: 12000000.0,
        investimentoPorHabitante: 184.62,
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
        valorTotal: 10000000.0,
        investimentoPorHabitante: 0.0,
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
        valorTotal: 12000000.0,
        investimentoPorHabitante: 184.62,
      },
      geometry: { type: "Polygon", coordinates: [[[-38.53, -13.01], [-38.44, -13.01], [-38.44, -12.98], [-38.53, -13.01]]] },
    },
  ],
};

describe("Seam 2: Painel Web do Mapa das Obras e Camada A (Justiça Territorial)", () => {
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

  it("renderiza os KPIs superiores de Salvador incluindo o indicador de Transparência Opaca", async () => {
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
    // 6. Transparência Opaca (Escopo Cidade)
    expect(screen.getByTestId("kpi-transparencia-opaca")).toBeInTheDocument();
    expect(screen.getByTestId("kpi-valor-nao-localizado")).toHaveTextContent("R$ 1.500.000");
  });

  it("permite alternar a camada coroplética entre R$/Habitante e Vulnerabilidade Social", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("btn-camada-vulnerabilidade")).toBeInTheDocument();
    });

    // Clica para ativar a camada de Vulnerabilidade Social
    fireEvent.click(screen.getByTestId("btn-camada-vulnerabilidade"));

    expect(screen.getByTestId("legenda-coropletica")).toHaveTextContent(/Índice de Vulnerabilidade/i);

    // Retorna para R$/Habitante
    fireEvent.click(screen.getByTestId("btn-camada-per-capita"));
    expect(screen.getByTestId("legenda-coropletica")).toHaveTextContent(/Investimento por Habitante/i);
  });

  it("exibe o Ranking horizontal de Prefeituras-Bairro e permite selecionar uma região", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("tab-ranking")).toBeInTheDocument();
    });

    // Clica na aba de Ranking de Prefeituras-Bairro
    fireEvent.click(screen.getByTestId("tab-ranking"));

    await waitFor(() => {
      expect(screen.getByTestId("ranking-prefeituras-container")).toBeInTheDocument();
    });

    // A Prefeitura #1 no ranking per capita deve ser Barra/Pituba (R$ 184,62)
    expect(screen.getByTestId("ranking-item-1")).toHaveTextContent("Barra/Pituba");
    expect(screen.getByTestId("ranking-valor-1")).toHaveTextContent("R$ 184,62");

    // Clica no item #1 do ranking para selecionar
    fireEvent.click(screen.getByTestId("ranking-item-1"));

    // O Raio-X deve ser atualizado para Barra/Pituba
    await waitFor(() => {
      expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Barra/Pituba");
    });
  });

  it("exibe o Raio-X do Bairro com investimento total, R$/hab e breakdown por Semáforo", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("territory-selector-pituba")).toBeInTheDocument();
    });

    // Clica no seletor de Pituba
    fireEvent.click(screen.getByTestId("territory-selector-pituba"));

    expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Pituba");
    expect(screen.getByTestId("raio-x-total-investido")).toHaveTextContent("R$ 12.000.000");
    expect(screen.getByTestId("raio-x-investimento-per-capita")).toHaveTextContent("R$ 184,62");
    expect(screen.getByTestId("raio-x-obras-verde")).toHaveTextContent("1");
    expect(screen.getByTestId("raio-x-populacao")).toHaveTextContent("65.000");
  });

  it("filtra a Tabela Detalhada de Obras ao selecionar um território", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("territory-selector-pituba")).toBeInTheDocument();
    });

    // 1. Seleciona o Bairro Pituba
    fireEvent.click(screen.getByTestId("territory-selector-pituba"));

    // O banner de filtro territorial ativo deve surgir
    await waitFor(() => {
      expect(screen.getByTestId("banner-territorio-filtrado")).toBeInTheDocument();
      expect(screen.getByTestId("banner-territorio-filtrado")).toHaveTextContent("Pituba");
    });

    // Alterna para a visão de Tabela
    fireEvent.click(screen.getByTestId("tab-tabela"));

    // Apenas a obra da Pituba (1001) deve aparecer na tabela filtrada
    await waitFor(() => {
      expect(screen.getByTestId("linha-obra-1001")).toBeInTheDocument();
      expect(screen.queryByTestId("linha-obra-1002")).not.toBeInTheDocument();
      expect(screen.queryByTestId("linha-obra-1003")).not.toBeInTheDocument();
    });

    // 2. Limpa o filtro territorial
    fireEvent.click(screen.getByTestId("btn-limpar-filtro-territorial"));

    // Todas as obras devem reaparecer
    await waitFor(() => {
      expect(screen.getByTestId("linha-obra-1001")).toBeInTheDocument();
      expect(screen.getByTestId("linha-obra-1002")).toBeInTheDocument();
      expect(screen.getByTestId("linha-obra-1003")).toBeInTheDocument();
    });
  });

  it("sinaliza adequadamente a Zona Especial Não-Residencial sem distorção per capita", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("territory-selector-aeroporto")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("territory-selector-aeroporto"));

    expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Aeroporto");
    expect(screen.getByTestId("badge-zona-especial")).toBeInTheDocument();
    // Investimento per capita deve ser indicado como Isento / 0 para não distorcer
    expect(screen.getByTestId("raio-x-investimento-per-capita")).toHaveTextContent("Isento");
    // Valor total bruto é preservado
    expect(screen.getByTestId("raio-x-total-investido")).toHaveTextContent("R$ 10.000.000");
  });
});

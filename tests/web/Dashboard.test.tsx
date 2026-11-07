import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import L from "leaflet";
import App, { buildDataUrl } from "../../src/App";
import { SALVADOR_CENTER, SALVADOR_DEFAULT_ZOOM } from "../../src/components/InteractiveMap";

const mockIndexData = {
  metadata: {
    generatedAt: "2026-11-06T20:00:00Z",
    anoReferencia: 2025,
    mandatosDisponiveis: ["2025-2028", "2021-2024"],
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
      valorPago: 7860000.0,
      investimentoPorHabitante: 184.62,
      investimentoPorHabitantePago: 120.92,
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
      valorPago: 1200000.0,
      investimentoPorHabitante: 50.0,
      investimentoPorHabitantePago: 25.0,
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
      valorPago: 800000.0,
      investimentoPorHabitante: 50.0,
      investimentoPorHabitantePago: 10.0,
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
      valorPago: 7860000.0,
      investimentoPorHabitante: 184.62,
      investimentoPorHabitantePago: 120.92,
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
      valorPago: 5000000.0,
      investimentoPorHabitante: 0.0,
      investimentoPorHabitantePago: 0.0,
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
      valorPago: 250000.0,
      investimentoPorHabitante: 0.0,
      investimentoPorHabitantePago: 0.0,
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
      valorPago: 1200000.0,
      investimentoPorHabitante: 50.0,
      investimentoPorHabitantePago: 25.0,
      totalObras: 1,
      obrasVerde: 0,
      obrasAmarelo: 1,
      obrasVermelho: 0,
    },
    {
      id: 106,
      nome: "São Caetano",
      prefeitura_bairro: "Liberdade/São Caetano",
      populacao: 30000,
      indice_vulnerabilidade: 0.78,
      is_zona_especial_nao_residencial: false,
      valorTotal: 0.0,
      valorPago: 0.0,
      investimentoPorHabitante: 0.0,
      investimentoPorHabitantePago: 0.0,
      totalObras: 0,
      obrasVerde: 0,
      obrasAmarelo: 0,
      obrasVermelho: 0,
    },
    {
      id: 107,
      nome: "Graça",
      prefeitura_bairro: "Barra/Pituba",
      populacao: 25000,
      indice_vulnerabilidade: 0.12,
      is_zona_especial_nao_residencial: false,
      valorTotal: 0.0,
      valorPago: 0.0,
      investimentoPorHabitante: 0.0,
      investimentoPorHabitantePago: 0.0,
      totalObras: 0,
      obrasVerde: 0,
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
      mandatos: ["2025-2028"],
      dtInicioVigencia: "2025-03-01T00:00:00.000Z",
      dtTerminoVigenciaAtualizado: "2027-12-31T00:00:00.000Z",
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
      ano: 2024,
      mandatos: ["2021-2024"],
      dtInicioVigencia: "2023-05-15T00:00:00.000Z",
      dtTerminoVigenciaAtualizado: "2024-12-31T00:00:00.000Z",
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
      mandatos: ["2025-2028"],
      dtInicioVigencia: "2025-01-20T00:00:00.000Z",
      dtTerminoVigenciaAtualizado: "2027-10-10T00:00:00.000Z",
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

const mockObra1001Detalhe = {
  id: 1001,
  unidadeGestora: "SUCOP",
  numeroContrato: "001/2024",
  numeroContratoOriginal: "001/2024",
  nuProcesso: "1234/2023",
  objeto: "Requalificação da Orla da Pituba com drenagem e nova ciclovia",
  situacao: "Em Execução",
  empreiteira: {
    razaoSocial: "CONSTRUTORA SALVADOR LTDA",
    cnpj: "12.345.678/0001-90",
    totalObras: 2,
    totalObrasAtivas: 2,
    valorTotalContratado: 16000000.0,
    outrasObrasCount: 1,
    outrasObrasIds: [1005],
  },
  vigencia: {
    dataInicio: "2024-01-10T00:00:00.000Z",
    dataFimOriginal: "2027-12-31T00:00:00.000Z",
    dataTerminoAtualizado: "2027-12-31T00:00:00.000Z",
    prazoOriginal: "1450 dias",
    prazoAtualizado: "1450 dias",
  },
  dom: {
    nuDom: "8.750",
    dataPublicacao: "2024-01-12T00:00:00.000Z",
  },
  funilFinanceiro: {
    valorOriginal: 12000000.0,
    valorContratualVigente: 12000000.0,
    valorEmpenhado: 12000000.0,
    valorLiquidado: 7860000.0,
    valorPago: 7860000.0,
    percentualExecutado: 65.5,
    valorAditivos: 0.0,
    deltaPercentualAditivos: 0.0,
  },
  aditivos: [],
  dotacao: [
    {
      subacao: "Requalificação da Orla Marítima e Projetos Estratégicos",
      fonteRecurso: "Tesouro Municipal (Recursos Ordinários)",
      classificacao: "4.4.90.51 - Obras e Instalações",
    },
  ],
  tema: "Mobilidade, Pavimentação e Drenagem",
  semaforo: {
    status: "VERDE",
    rotulo: "Verde (No Prazo)",
    motivos: ["No prazo"],
    deltaPercentualValor: 0.0,
  },
  nivel: "Bairro",
  bairro: "Pituba",
  prefeituraBairro: "Barra/Pituba",
};

const mockObra1002Detalhe = {
  id: 1002,
  unidadeGestora: "CODESAL",
  numeroContrato: "002/2024",
  numeroContratoOriginal: "002/2024",
  nuProcesso: "1235/2023",
  objeto: "Contenção de Encosta na Liberdade",
  situacao: "Em Execução",
  empreiteira: {
    razaoSocial: "BAHIA ENGENHARIA S/A",
    cnpj: "98.765.432/0001-10",
    totalObras: 1,
    totalObrasAtivas: 1,
    valorTotalContratado: 2400000.0,
    outrasObrasCount: 0,
    outrasObrasIds: [],
  },
  vigencia: {
    dataInicio: "2024-03-01T00:00:00.000Z",
    dataFimOriginal: "2027-06-30T00:00:00.000Z",
    dataTerminoAtualizado: "2027-12-31T00:00:00.000Z",
    prazoOriginal: "1200 dias",
    prazoAtualizado: "1384 dias",
  },
  dom: {
    nuDom: "8.712",
    dataPublicacao: "2024-02-25T00:00:00.000Z",
  },
  funilFinanceiro: {
    valorOriginal: 2000000.0,
    valorContratualVigente: 2400000.0,
    valorEmpenhado: 2400000.0,
    valorLiquidado: 1200000.0,
    valorPago: 1200000.0,
    percentualExecutado: 50.0,
    valorAditivos: 400000.0,
    deltaPercentualAditivos: 20.0,
  },
  aditivos: [
    {
      nuAditivo: "1º Termo Aditivo",
      dsTipoAlteracao: "Prazo e Valor",
      dsObjetoAditivo: "Acréscimo de contenção e prorrogação",
      dtAssinatura: "2024-11-15T00:00:00.000Z",
      dtTerminoVigencia: "2027-12-31T00:00:00.000Z",
      dtPublicacao: "2024-11-20T00:00:00.000Z",
      nuDom: "8.910",
      vlAditivo: 400000.0,
    },
  ],
  dotacao: [
    {
      subacao: "Proteção de Encostas",
      fonteRecurso: "Operação de Crédito Interna (FINISA)",
      classificacao: "4.4.90.51 - Obras e Instalações",
    },
  ],
  tema: "Encostas e Contenção",
  semaforo: {
    status: "AMARELO",
    rotulo: "Amarelo (Atenção)",
    motivos: ["Aditivo entre 10% e 25%"],
    deltaPercentualValor: 20.0,
  },
  nivel: "Pontual",
  bairro: "Liberdade",
  prefeituraBairro: "Liberdade/São Caetano",
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
        if (url.includes("obras/1001.json")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockObra1001Detalhe),
          });
        }
        if (url.includes("obras/1002.json")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockObra1002Detalhe),
          });
        }
        return Promise.reject(new Error("URL desconhecida: " + url));
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

    // Clica na aba de Ranking Territorial e alterna para Prefeituras-Bairro
    fireEvent.click(screen.getByTestId("tab-ranking"));
    fireEvent.click(screen.getByTestId("btn-ranking-prefeituras"));

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

  it("abre a Ficha Limpa da Obra sob demanda ao clicar na tabela, exibindo Funil, DOM, Dotação e Empreiteira", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("tab-tabela")).toBeInTheDocument();
    });

    // Alterna para a visualização tabular de Obras
    fireEvent.click(screen.getByTestId("tab-tabela"));

    await waitFor(() => {
      expect(screen.getByTestId("linha-obra-1001")).toBeInTheDocument();
    });

    // Clica na linha da obra 1001 (SUCOP - Orla da Pituba)
    fireEvent.click(screen.getByTestId("linha-obra-1001"));

    // O modal da Ficha Limpa deve ser renderizado após o carregamento sob demanda
    await waitFor(() => {
      expect(screen.getByTestId("ficha-limpa-modal")).toBeInTheDocument();
    });

    // 1. Dados cadastrais e objeto
    expect(screen.getByTestId("ficha-limpa-objeto")).toHaveTextContent("Requalificação da Orla da Pituba");
    expect(screen.getByTestId("ficha-limpa-contrato")).toHaveTextContent("001/2024");
    expect(screen.getByTestId("ficha-limpa-orgao")).toHaveTextContent("SUCOP");

    // 2. DOM (Diário Oficial do Município)
    expect(screen.getByTestId("ficha-limpa-dom")).toHaveTextContent("8.750");

    // 3. Funil de Execução Financeira
    expect(screen.getByTestId("funil-financeiro-container")).toBeInTheDocument();
    expect(screen.getByTestId("funil-valor-original")).toHaveTextContent("R$ 12.000.000");
    expect(screen.getByTestId("funil-valor-vigente")).toHaveTextContent("R$ 12.000.000");
    expect(screen.getByTestId("funil-percentual-executado")).toHaveTextContent("65,5%");

    // 4. Dotação Orçamentária / Fonte de Recurso
    expect(screen.getByTestId("ficha-limpa-dotacao")).toHaveTextContent("Tesouro Municipal (Recursos Ordinários)");

    // 5. Empreiteira e Concentração em Salvador
    expect(screen.getByTestId("ficha-limpa-empreiteira-nome")).toHaveTextContent("CONSTRUTORA SALVADOR LTDA");
    expect(screen.getByTestId("ficha-limpa-empreiteira-cnpj")).toHaveTextContent("12.345.678/0001-90");
    expect(screen.getByTestId("ficha-limpa-empreiteira-concentracao")).toHaveTextContent(/2 obra/i);
    expect(screen.getByTestId("ficha-limpa-empreiteira-concentracao")).toHaveTextContent("1 outra(s)");

    // 6. Botão de filtrar por empreiteira em 1 clique
    const btnFiltrarEmpreiteira = screen.getByTestId("btn-filtrar-por-empreiteira");
    expect(btnFiltrarEmpreiteira).toBeInTheDocument();
    fireEvent.click(btnFiltrarEmpreiteira);

    // O modal deve fechar e a tabela deve estar filtrada pela empreiteira
    await waitFor(() => {
      expect(screen.queryByTestId("ficha-limpa-modal")).not.toBeInTheDocument();
    });

    // Alterna para tabela para checar se apenas as obras da empreiteira aparecem
    fireEvent.click(screen.getByTestId("tab-tabela"));
    expect(screen.getByTestId("linha-obra-1001")).toBeInTheDocument();
    expect(screen.queryByTestId("linha-obra-1002")).not.toBeInTheDocument();
  });

  it("exibe a lista de Aditivos Contratuais detalhados na Ficha Limpa da Obra 1002", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("tab-tabela")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("tab-tabela"));

    await waitFor(() => {
      expect(screen.getByTestId("linha-obra-1002")).toBeInTheDocument();
    });

    // Clica na linha da obra 1002 (com aditivos de prazo e valor)
    fireEvent.click(screen.getByTestId("linha-obra-1002"));

    await waitFor(() => {
      expect(screen.getByTestId("ficha-limpa-modal")).toBeInTheDocument();
    });

    // Verifica presença da seção de Aditivos Contratuais
    expect(screen.getByTestId("secao-aditivos-obra")).toBeInTheDocument();
    expect(screen.getByTestId("aditivo-item-0")).toHaveTextContent("1º Termo Aditivo");
    expect(screen.getByTestId("aditivo-item-0")).toHaveTextContent("Prazo e Valor");
    expect(screen.getByTestId("aditivo-item-0")).toHaveTextContent("8.910");
    expect(screen.getByTestId("aditivo-item-0")).toHaveTextContent("20/11/2024");

    // Fecha a Ficha Limpa
    fireEvent.click(screen.getByTestId("btn-fechar-ficha-limpa"));

    await waitFor(() => {
      expect(screen.queryByTestId("ficha-limpa-modal")).not.toBeInTheDocument();
    });
  });

  it("abre a Ficha Limpa da Obra sob demanda ao clicar no pino da obra no mapa", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("map-pin-obra-1001")).toBeInTheDocument();
    });

    // Clica no pino da obra 1001 no mapa
    fireEvent.click(screen.getByTestId("map-pin-obra-1001"));

    await waitFor(() => {
      expect(screen.getByTestId("ficha-limpa-modal")).toBeInTheDocument();
    });

    expect(screen.getByTestId("ficha-limpa-objeto")).toHaveTextContent("Requalificação da Orla da Pituba");
    expect(screen.getByTestId("funil-financeiro-container")).toBeInTheDocument();
  });

  it("carrega todos os artefatos estáticos sob o subcaminho do repositório no GitHub Pages", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("map-pin-obra-1001")).toBeInTheDocument();
    });

    // Verifica chamadas iniciais para index_2025.json e geo/*.geojson com o base path do GitHub Pages
    expect(fetchMock).toHaveBeenCalledWith("/investimento_por_bairro_salvador/data/index_2025.json");
    expect(fetchMock).toHaveBeenCalledWith("/investimento_por_bairro_salvador/data/geo/bairros.geojson");
    expect(fetchMock).toHaveBeenCalledWith(
      "/investimento_por_bairro_salvador/data/geo/prefeituras_bairro.geojson"
    );

    // Clica para carregar a Ficha Limpa sob demanda
    fireEvent.click(screen.getByTestId("map-pin-obra-1001"));

    await waitFor(() => {
      expect(screen.getByTestId("ficha-limpa-modal")).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalledWith("/investimento_por_bairro_salvador/data/obras/1001.json");
    expect(buildDataUrl("data/index_2025.json", "/investimento_por_bairro_salvador/")).toBe(
      "/investimento_por_bairro_salvador/data/index_2025.json"
    );
    expect(buildDataUrl("/data/obras/1001.json", "/")).toBe("/data/obras/1001.json");
  });

  it("substitui o seletor de ano pelo seletor de Mandato Municipal e exibe as opções corretas", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("filtro-mandato")).toBeInTheDocument();
    });

    // Seletor de mandato deve estar presente e o de ano não deve mais existir
    expect(screen.queryByTestId("filtro-ano")).not.toBeInTheDocument();

    const selectMandato = screen.getByTestId("filtro-mandato") as HTMLSelectElement;
    expect(selectMandato.value).toBe("todos");

    const options = Array.from(selectMandato.querySelectorAll("option")).map((o) => o.textContent?.trim());
    expect(options).toContain("Todos os Mandatos");
    expect(options.some((o) => o?.includes("2025") && o?.includes("2028"))).toBe(true);
    expect(options.some((o) => o?.includes("2021") && o?.includes("2024"))).toBe(true);

    // Subtítulo do cabeçalho reflete Todos os Mandatos
    const headerSub = screen.getByTestId("header-subtitulo");
    expect(headerSub).toHaveTextContent(/Todos os Mandatos/i);
  });

  it("filtra por Mandato Municipal 2021-2024 exibindo obras vigentes naquele mandato incluindo plurianuais", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("filtro-mandato")).toBeInTheDocument();
    });

    // Seleciona 2021-2024
    fireEvent.change(screen.getByTestId("filtro-mandato"), { target: { value: "2021-2024" } });

    // Subtítulo do cabeçalho deve refletir o mandato 2021-2024
    await waitFor(() => {
      expect(screen.getByTestId("header-subtitulo")).toHaveTextContent(/2021.*2024/);
    });

    // Alterna para visão de tabela
    fireEvent.click(screen.getByTestId("tab-tabela"));

    await waitFor(() => {
      // Obra 1001 é plurianual (2021-2024 e 2025-2028): DEVE aparecer
      expect(screen.getByTestId("linha-obra-1001")).toBeInTheDocument();
      // Obra 1003 pertence a 2021-2024: DEVE aparecer
      expect(screen.getByTestId("linha-obra-1003")).toBeInTheDocument();
      // Obra 1002 e 1004 são exclusivas de 2025-2028: NÃO devem aparecer
      expect(screen.queryByTestId("linha-obra-1002")).not.toBeInTheDocument();
      expect(screen.queryByTestId("linha-obra-1004")).not.toBeInTheDocument();
    });
  });

  it("filtra por Mandato Municipal 2025-2028 exibindo obras vigentes naquele mandato incluindo plurianuais", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("filtro-mandato")).toBeInTheDocument();
    });

    // Seleciona 2025-2028
    fireEvent.change(screen.getByTestId("filtro-mandato"), { target: { value: "2025-2028" } });

    // Subtítulo do cabeçalho reflete 2025-2028
    await waitFor(() => {
      expect(screen.getByTestId("header-subtitulo")).toHaveTextContent(/2025.*2028/);
    });

    // Alterna para tabela
    fireEvent.click(screen.getByTestId("tab-tabela"));

    await waitFor(() => {
      // Obra 1001 é plurianual (vigente em 2025-2028 também): DEVE aparecer
      expect(screen.getByTestId("linha-obra-1001")).toBeInTheDocument();
      // Obra 1002 e 1004 pertencem a 2025-2028: DEVEM aparecer
      expect(screen.getByTestId("linha-obra-1002")).toBeInTheDocument();
      expect(screen.getByTestId("linha-obra-1004")).toBeInTheDocument();
      // Obra 1003 é exclusiva de 2021-2024: NÃO deve aparecer
      expect(screen.queryByTestId("linha-obra-1003")).not.toBeInTheDocument();
    });
  });

  it("não duplica obras plurianuais quando 'Todos os Mandatos' estiver selecionado", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("filtro-mandato")).toBeInTheDocument();
    });

    // Garante que 'todos' está ativo
    fireEvent.change(screen.getByTestId("filtro-mandato"), { target: { value: "todos" } });

    fireEvent.click(screen.getByTestId("tab-tabela"));

    await waitFor(() => {
      // Deve haver exatamente 4 obras (1001, 1002, 1003, 1004) sem duplicações
      expect(screen.getAllByTestId(/^linha-obra-/)).toHaveLength(4);
      expect(screen.getByTestId("linha-obra-1001")).toBeInTheDocument();
    });
  });

  it("exibe a data de início de vigência do contrato na Tabela Detalhada de Obras", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("tab-tabela")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("tab-tabela"));

    await waitFor(() => {
      expect(screen.getByTestId("linha-obra-1001")).toBeInTheDocument();
    });

    // Deve exibir a data formatada de início da vigência (10/01/2024)
    expect(screen.getByTestId("data-inicio-obra-1001")).toHaveTextContent("10/01/2024");
  });

  it("recalcula dinamicamente a Camada A (Ranking, Seletores e Raio-X) ao filtrar por Tema da Obra", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("filtro-tema")).toBeInTheDocument();
    });

    // Filtra por Tema: "Encostas e Contenção" (onde apenas a Obra 1002 em Liberdade existe)
    fireEvent.change(screen.getByTestId("filtro-tema"), {
      target: { value: "Encostas e Contenção" },
    });

    // 1. No seletor rápido de territórios do mapa:
    // Pituba (obra 1001) não pertence a este tema: deve ter R$ 0/hab
    await waitFor(() => {
      const seletorPituba = screen.getByTestId("territory-selector-pituba");
      expect(seletorPituba).toHaveTextContent(/R\$\s*0(\,00)?\/hab/);
    });

    // Liberdade (obra 1002) pertence ao tema: deve ter R$ 50/hab
    const seletorLiberdade = screen.getByTestId("territory-selector-liberdade");
    expect(seletorLiberdade).toHaveTextContent(/R\$\s*50(\,00)?\/hab/);

    // 2. No Ranking de Prefeituras-Bairro:
    fireEvent.click(screen.getByTestId("tab-ranking"));
    fireEvent.click(screen.getByTestId("btn-ranking-prefeituras"));
    await waitFor(() => {
      // Liberdade/São Caetano agora lidera o ranking com R$ 50
      expect(screen.getByTestId("ranking-item-1")).toHaveTextContent("Liberdade/São Caetano");
      expect(screen.getByTestId("ranking-valor-1")).toHaveTextContent(/R\$\s*50/);
    });

    // 3. No Raio-X do Bairro:
    fireEvent.click(screen.getByTestId("tab-mapa"));
    fireEvent.click(screen.getByTestId("btn-camada-bairros"));
    fireEvent.click(screen.getByTestId("territory-selector-pituba"));
    expect(screen.getByTestId("raio-x-total-investido")).toHaveTextContent("R$ 0");
    expect(screen.getByTestId("raio-x-investimento-per-capita")).toHaveTextContent(/R\$\s*0/);
    expect(screen.getByTestId("raio-x-obras-verde")).toHaveTextContent("0");
  });

  it("sincroniza reativamente o Raio-X aberto quando um filtro superior (mandato) é alterado", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("territory-selector-liberdade")).toBeInTheDocument();
    });

    // 1. Abre o Raio-X de Liberdade com todos os mandatos ativos
    fireEvent.click(screen.getByTestId("territory-selector-liberdade"));

    expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Liberdade");
    expect(screen.getByTestId("raio-x-total-investido")).toHaveTextContent("R$ 2.400.000");
    expect(screen.getByTestId("raio-x-investimento-per-capita")).toHaveTextContent(/R\$\s*50/);
    expect(screen.getByTestId("raio-x-obras-amarelo")).toHaveTextContent("1");

    // 2. Muda o Mandato para 2021-2024 (a Obra 1002 da Liberdade é de 2025-2028 e não existe em 2021-2024)
    fireEvent.change(screen.getByTestId("filtro-mandato"), {
      target: { value: "2021-2024" },
    });

    // O painel do Raio-X deve permanecer aberto em Liberdade, mas os valores devem zerar imediatamente
    await waitFor(() => {
      expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Liberdade");
      expect(screen.getByTestId("raio-x-total-investido")).toHaveTextContent("R$ 0");
      expect(screen.getByTestId("raio-x-investimento-per-capita")).toHaveTextContent(/R\$\s*0/);
      expect(screen.getByTestId("raio-x-obras-amarelo")).toHaveTextContent("0");
    });
  });

  it("recalcula dinamicamente a ordenação do Ranking de Prefeituras-Bairro e seletores ao alternar Mandatos Municipais", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("filtro-mandato")).toBeInTheDocument();
    });

    // 1. Filtra por 2021-2024
    fireEvent.change(screen.getByTestId("filtro-mandato"), {
      target: { value: "2021-2024" },
    });

    // No seletor rápido: Pituba tem obra (1001), Liberdade não tem (obra 1002 é exclusiva 2025-2028)
    await waitFor(() => {
      const seletorPituba = screen.getByTestId("territory-selector-pituba");
      expect(seletorPituba).toHaveTextContent(/R\$\s*184,62\/hab/);
    });
    const seletorLiberdade = screen.getByTestId("territory-selector-liberdade");
    expect(seletorLiberdade).toHaveTextContent(/R\$\s*0(\,00)?\/hab/);

    // No Ranking de Prefeituras-Bairro:
    fireEvent.click(screen.getByTestId("tab-ranking"));
    fireEvent.click(screen.getByTestId("btn-ranking-prefeituras"));
    await waitFor(() => {
      // 1º Barra/Pituba (R$ 184,62), 2º Subúrbio/Ilhas (R$ 50,00 via regional), 3º Liberdade/São Caetano (R$ 0)
      expect(screen.getByTestId("ranking-item-1")).toHaveTextContent("Barra/Pituba");
      expect(screen.getByTestId("ranking-valor-1")).toHaveTextContent("R$ 184,62");
      expect(screen.getByTestId("ranking-item-2")).toHaveTextContent("Subúrbio/Ilhas");
      expect(screen.getByTestId("ranking-valor-2")).toHaveTextContent(/R\$\s*50/);
      expect(screen.getByTestId("ranking-item-3")).toHaveTextContent("Liberdade/São Caetano");
      expect(screen.getByTestId("ranking-valor-3")).toHaveTextContent(/R\$\s*0/);
    });

    // 2. Alterna para 2025-2028
    fireEvent.change(screen.getByTestId("filtro-mandato"), {
      target: { value: "2025-2028" },
    });

    await waitFor(() => {
      // 1º Barra/Pituba (R$ 184,62), 2º Liberdade/São Caetano (R$ 50,00 via Liberdade), 3º Subúrbio/Ilhas (R$ 0)
      expect(screen.getByTestId("ranking-item-1")).toHaveTextContent("Barra/Pituba");
      expect(screen.getByTestId("ranking-valor-1")).toHaveTextContent("R$ 184,62");
      expect(screen.getByTestId("ranking-item-2")).toHaveTextContent("Liberdade/São Caetano");
      expect(screen.getByTestId("ranking-valor-2")).toHaveTextContent(/R\$\s*50/);
      expect(screen.getByTestId("ranking-item-3")).toHaveTextContent("Subúrbio/Ilhas");
      expect(screen.getByTestId("ranking-valor-3")).toHaveTextContent(/R\$\s*0/);
    });
  });

  it("recalcula dinamicamente a Camada A ao filtrar por Órgão contratante", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("filtro-orgao")).toBeInTheDocument();
    });

    // Filtra por SUCOP (apenas obra 1001 na Pituba)
    fireEvent.change(screen.getByTestId("filtro-orgao"), {
      target: { value: "SUCOP" },
    });

    await waitFor(() => {
      const seletorPituba = screen.getByTestId("territory-selector-pituba");
      expect(seletorPituba).toHaveTextContent(/R\$\s*184,62\/hab/);
    });
    const seletorLiberdade = screen.getByTestId("territory-selector-liberdade");
    expect(seletorLiberdade).toHaveTextContent(/R\$\s*0(\,00)?\/hab/);

    fireEvent.click(screen.getByTestId("tab-ranking"));
    fireEvent.click(screen.getByTestId("btn-ranking-prefeituras"));
    await waitFor(() => {
      expect(screen.getByTestId("ranking-item-1")).toHaveTextContent("Barra/Pituba");
      expect(screen.getByTestId("ranking-valor-1")).toHaveTextContent("R$ 184,62");
      // As demais prefeituras sem obras SUCOP devem exibir R$ 0
      expect(screen.getByTestId("ranking-valor-2")).toHaveTextContent(/R\$\s*0/);
      expect(screen.getByTestId("ranking-valor-3")).toHaveTextContent(/R\$\s*0/);
    });
  });

  it("recalcula dinamicamente a Camada A ao filtrar por Semáforo Crítico (VERMELHO)", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("filtro-semaforo")).toBeInTheDocument();
    });

    // Filtra por Semáforo VERMELHO (apenas obra 1003 regional de Subúrbio/Ilhas)
    fireEvent.change(screen.getByTestId("filtro-semaforo"), {
      target: { value: "VERMELHO" },
    });

    // Ambos os bairros Pituba e Liberdade devem estar zerados
    await waitFor(() => {
      expect(screen.getByTestId("territory-selector-pituba")).toHaveTextContent(/R\$\s*0(\,00)?\/hab/);
      expect(screen.getByTestId("territory-selector-liberdade")).toHaveTextContent(/R\$\s*0(\,00)?\/hab/);
    });

    // No ranking, Subúrbio/Ilhas lidera com R$ 50,00 e as outras estão zeradas
    fireEvent.click(screen.getByTestId("tab-ranking"));
    fireEvent.click(screen.getByTestId("btn-ranking-prefeituras"));
    await waitFor(() => {
      expect(screen.getByTestId("ranking-item-1")).toHaveTextContent("Subúrbio/Ilhas");
      expect(screen.getByTestId("ranking-valor-1")).toHaveTextContent(/R\$\s*50/);
      expect(screen.getByTestId("ranking-valor-2")).toHaveTextContent(/R\$\s*0/);
    });
  });

  it("recalcula dinamicamente a Camada A ao alternar a métrica financeira para Executado / Pago", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("btn-metrica-executado")).toBeInTheDocument();
    });

    // Alterna a métrica financeira para "Valor Executado / Pago"
    fireEvent.click(screen.getByTestId("btn-metrica-executado"));

    // No seletor rápido:
    // Pituba: 7.860.000 / 65.000 = R$ 120,92/hab
    // Liberdade: 1.200.000 / 48.000 = R$ 25,00/hab
    await waitFor(() => {
      const seletorPituba = screen.getByTestId("territory-selector-pituba");
      expect(seletorPituba).toHaveTextContent(/R\$\s*120,92\/hab/);
    });
    const seletorLiberdade = screen.getByTestId("territory-selector-liberdade");
    expect(seletorLiberdade).toHaveTextContent(/R\$\s*25(\,00)?\/hab/);

    // No Ranking de Prefeituras-Bairro:
    fireEvent.click(screen.getByTestId("tab-ranking"));
    fireEvent.click(screen.getByTestId("btn-ranking-prefeituras"));
    await waitFor(() => {
      // 1º Barra/Pituba (R$ 120,92)
      expect(screen.getByTestId("ranking-item-1")).toHaveTextContent("Barra/Pituba");
      expect(screen.getByTestId("ranking-valor-1")).toHaveTextContent("R$ 120,92");
      // 2º Liberdade/São Caetano (R$ 25,00)
      expect(screen.getByTestId("ranking-item-2")).toHaveTextContent("Liberdade/São Caetano");
      expect(screen.getByTestId("ranking-valor-2")).toHaveTextContent(/R\$\s*25/);
      // 3º Subúrbio/Ilhas (R$ 10,00)
      expect(screen.getByTestId("ranking-item-3")).toHaveTextContent("Subúrbio/Ilhas");
      expect(screen.getByTestId("ranking-valor-3")).toHaveTextContent(/R\$\s*10/);
    });
  });

  it("centraliza o mapa em Salvador (SALVADOR_CENTER, zoom 11) e chama invalidateSize ao carregar as malhas iniciais", async () => {
    const invalidateSizeSpy = vi.spyOn(L.Map.prototype, "invalidateSize");
    const setViewSpy = vi.spyOn(L.Map.prototype, "setView");

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("leaflet-map-container")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(invalidateSizeSpy).toHaveBeenCalled();
      expect(setViewSpy).toHaveBeenCalledWith(SALVADOR_CENTER, SALVADOR_DEFAULT_ZOOM);
    });

    invalidateSizeSpy.mockRestore();
    setViewSpy.mockRestore();
  });

  it("limpa seleção anterior incompatível e reenquadra o mapa em Salvador ao alternar entre Bairros e Prefeituras-Bairro", async () => {
    const invalidateSizeSpy = vi.spyOn(L.Map.prototype, "invalidateSize");
    const setViewSpy = vi.spyOn(L.Map.prototype, "setView");

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("territory-selector-pituba")).toBeInTheDocument();
    });

    // 1. Seleciona Pituba (Bairro Oficial)
    fireEvent.click(screen.getByTestId("territory-selector-pituba"));

    await waitFor(() => {
      expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Pituba");
      expect(screen.getByTestId("banner-territorio-filtrado")).toBeInTheDocument();
    });

    invalidateSizeSpy.mockClear();
    setViewSpy.mockClear();

    // 2. Alterna camada para Prefeituras-Bairro
    const btnPrefeituras = screen.getByRole("button", { name: /^Prefeituras-Bairro/i });
    fireEvent.click(btnPrefeituras);

    // 3. A seleção territorial anterior (Pituba) incompatível deve ser limpa
    await waitFor(() => {
      expect(screen.queryByTestId("banner-territorio-filtrado")).not.toBeInTheDocument();
      expect(screen.queryByTestId("raio-x-nome")).not.toBeInTheDocument();
    });

    // 4. O mapa deve ter executado invalidateSize() e recentralizado em Salvador
    expect(invalidateSizeSpy).toHaveBeenCalled();
    expect(setViewSpy).toHaveBeenCalledWith(SALVADOR_CENTER, SALVADOR_DEFAULT_ZOOM);

    invalidateSizeSpy.mockClear();
    setViewSpy.mockClear();

    // 5. Alterna de volta para Bairros Oficiais
    const btnBairros = screen.getByRole("button", { name: /^Bairros Oficiais/i });
    fireEvent.click(btnBairros);

    // 6. Deve recentralizar com segurança no centro e zoom de Salvador
    expect(invalidateSizeSpy).toHaveBeenCalled();
    expect(setViewSpy).toHaveBeenCalledWith(SALVADOR_CENTER, SALVADOR_DEFAULT_ZOOM);

    invalidateSizeSpy.mockRestore();
    setViewSpy.mockRestore();
  });

  it("atualiza dinamicamente o Total Investido e R$ / Habitante no Raio-X ao alternar para Executado / Pago e preserva Isento para Zonas Especiais", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("territory-selector-pituba")).toBeInTheDocument();
    });

    // 1. Seleciona Bairro Oficial Pituba
    fireEvent.click(screen.getByTestId("territory-selector-pituba"));

    await waitFor(() => {
      expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Pituba");
    });

    // Sob Valor Contratual Vigente:
    expect(screen.getByTestId("raio-x-total-investido")).toHaveTextContent("R$ 12.000.000");
    expect(screen.getByTestId("raio-x-investimento-per-capita")).toHaveTextContent("R$ 184,62");

    // 2. Alterna para Valor Executado / Pago
    fireEvent.click(screen.getByTestId("btn-metrica-executado"));

    // O Raio-X deve atualizar dinamicamente para valorPago (7.860.000) e investimentoPorHabitantePago (120,92)
    await waitFor(() => {
      expect(screen.getByTestId("raio-x-total-investido")).toHaveTextContent("R$ 7.860.000");
      expect(screen.getByTestId("raio-x-investimento-per-capita")).toHaveTextContent("R$ 120,92");
    });

    // 3. Retorna para Valor Contratual Vigente
    fireEvent.click(screen.getByTestId("btn-metrica-vigente"));
    await waitFor(() => {
      expect(screen.getByTestId("raio-x-total-investido")).toHaveTextContent("R$ 12.000.000");
      expect(screen.getByTestId("raio-x-investimento-per-capita")).toHaveTextContent("R$ 184,62");
    });

    // 4. Agora seleciona uma Zona Especial Não-Residencial (Aeroporto)
    fireEvent.click(screen.getByTestId("territory-selector-aeroporto"));

    await waitFor(() => {
      expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Aeroporto");
    });
    expect(screen.getByTestId("badge-zona-especial")).toBeInTheDocument();
    expect(screen.getByTestId("raio-x-investimento-per-capita")).toHaveTextContent("Isento");

    // Alterna para Executado / Pago: o per capita DEVE continuar "Isento"
    fireEvent.click(screen.getByTestId("btn-metrica-executado"));
    await waitFor(() => {
      expect(screen.getByTestId("raio-x-investimento-per-capita")).toHaveTextContent("Isento");
    });
  });

  it("restringe a largura do flex item do mapa (min-w-0 overflow-hidden) para que os 171 botões de bairros não expandam o mapa além da tela", async () => {
    render(<App />);

    const mapContainer = await screen.findByTestId("leaflet-map-container");
    const mapFlexColumn = mapContainer.parentElement;

    expect(mapFlexColumn).not.toBeNull();
    expect(mapFlexColumn).toHaveClass("min-w-0");
    expect(mapFlexColumn).toHaveClass("overflow-hidden");
  });

  it("aplica o Índice de Vulnerabilidade específico de cada Prefeitura-Bairro no mapa, no Raio-X e no Ranking", async () => {
    const geoJsonSpy = vi.spyOn(L, "geoJSON");

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("btn-camada-prefeituras")).toBeInTheDocument();
    });

    // 1. Alterna para a camada de Prefeituras-Bairro e métrica Vulnerabilidade Social
    fireEvent.click(screen.getByTestId("btn-camada-prefeituras"));
    fireEvent.click(screen.getByTestId("btn-camada-vulnerabilidade"));

    await waitFor(() => {
      expect(geoJsonSpy).toHaveBeenCalled();
    });

    // Verifica que a estilização GeoJSON para Barra/Pituba (vuln 0.12 < 0.2) usa #ede9fe e não o fallback 0.5 (#8b5cf6)
    const lastCall = geoJsonSpy.mock.calls[geoJsonSpy.mock.calls.length - 1];
    const options = lastCall[1] as L.GeoJSONOptions;
    const styleFn = options.style as (feature: any) => L.PathOptions;
    const barraStyle = styleFn(mockPbGeo.features[0]);
    expect(barraStyle.fillColor).toBe("#ede9fe");

    // 2. Seleciona a Prefeitura-Bairro Barra/Pituba e verifica o Índice de Vulnerabilidade no Raio-X
    fireEvent.click(screen.getByTestId("territory-selector-barra-pituba"));
    await waitFor(() => {
      expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Barra/Pituba");
      expect(screen.getByTestId("raio-x-vulnerabilidade")).toHaveTextContent("0,12");
    });

    // 3. No Ranking de Prefeituras-Bairro, permite ordenar por Vulnerabilidade
    fireEvent.click(screen.getByTestId("tab-ranking"));
    fireEvent.click(screen.getByTestId("btn-ranking-prefeituras"));
    await waitFor(() => {
      expect(screen.getByTestId("btn-criterio-vulnerabilidade")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("btn-criterio-vulnerabilidade"));

    await waitFor(() => {
      // Liberdade/São Caetano (0,78) deve vir antes de Barra/Pituba (0,12)
      expect(screen.getByTestId("ranking-item-1")).toHaveTextContent("Liberdade/São Caetano");
      expect(screen.getByTestId("ranking-valor-1")).toHaveTextContent("0,78");
    });

    geoJsonSpy.mockRestore();
  });

  it("sincroniza a aba Ranking Territorial com a camada ativa do painel e atualiza a camada ao alternar nível ou selecionar território", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("tab-ranking")).toBeInTheDocument();
    });

    // 1. Aba deve exibir o rótulo 'Ranking Territorial'
    expect(screen.getByTestId("tab-ranking")).toHaveTextContent("Ranking Territorial");

    // 2. Abre a aba Ranking Territorial: como a camada padrão é 'bairros', deve abrir em Bairros Oficiais
    fireEvent.click(screen.getByTestId("tab-ranking"));

    await waitFor(() => {
      expect(screen.getByTestId("ranking-prefeituras-container")).toBeInTheDocument();
    });

    // O botão de Bairros Oficiais deve estar ativo e a lista de bairros deve ser exibida
    expect(screen.getByTestId("btn-ranking-bairros")).toHaveClass("bg-white text-slate-900");
    expect(screen.getByTestId("ranking-bairro-1")).toBeInTheDocument();
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("Pituba");

    // 3. Alterna o nível para Prefeituras-Bairro no cabeçalho do Ranking
    fireEvent.click(screen.getByTestId("btn-ranking-prefeituras"));
    await waitFor(() => {
      expect(screen.getByTestId("ranking-item-1")).toBeInTheDocument();
    });
    expect(screen.getByTestId("btn-ranking-prefeituras")).toHaveClass("bg-white text-slate-900");
    expect(screen.getByTestId("ranking-item-1")).toHaveTextContent("Barra/Pituba");

    // Volta ao mapa para verificar que a camada ativa do painel foi sincronizada para Prefeituras-Bairro
    fireEvent.click(screen.getByTestId("tab-mapa"));
    await waitFor(() => {
      expect(screen.getByTestId("territory-selector-barra-pituba")).toBeInTheDocument();
    });

    // 4. Retorna ao Ranking Territorial: deve abrir diretamente em Prefeituras-Bairro (sincronizado com a camada ativa)
    fireEvent.click(screen.getByTestId("tab-ranking"));
    await waitFor(() => {
      expect(screen.getByTestId("ranking-item-1")).toBeInTheDocument();
    });

    // 5. Clica em Barra/Pituba no ranking: seleciona no Raio-X e preserva a camada de Prefeituras
    fireEvent.click(screen.getByTestId("ranking-item-1"));
    await waitFor(() => {
      expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Barra/Pituba");
    });

    // 6. Alterna de volta para Bairros Oficiais e clica em um bairro: seleciona no Raio-X e sincroniza a camada para Bairros
    fireEvent.click(screen.getByTestId("btn-ranking-bairros"));
    await waitFor(() => {
      expect(screen.getByTestId("ranking-bairro-1")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("ranking-bairro-1"));
    await waitFor(() => {
      expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Pituba");
    });

    // Volta ao mapa e confirma que o seletor rápido é de bairros
    fireEvent.click(screen.getByTestId("tab-mapa"));
    await waitFor(() => {
      expect(screen.getByTestId("territory-selector-pituba")).toBeInTheDocument();
    });
  });

  it("permite ordenar Bairros Oficiais e Prefeituras-Bairro pelos 4 critérios com simetria e reatividade financeira", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("tab-ranking")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("tab-ranking"));

    // 1. Verifica existência dos 4 critérios de ordenação
    expect(screen.getByTestId("btn-criterio-investimento")).toBeInTheDocument();
    expect(screen.getByTestId("btn-criterio-valortotal")).toBeInTheDocument();
    expect(screen.getByTestId("btn-criterio-totalobras")).toBeInTheDocument();
    expect(screen.getByTestId("btn-criterio-vulnerabilidade")).toBeInTheDocument();

    // 2. Critério padrão: R$/Hab em Bairros Oficiais (vigente)
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("Pituba");
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("R$ 184,62 / hab");
    expect(screen.getByTestId("ranking-bairro-2")).toHaveTextContent("Liberdade");
    expect(screen.getByTestId("ranking-bairro-2")).toHaveTextContent(/R\$\s*50(\,00)?\s*\/ hab/);

    // 3. Critério: Valor Total em Bairros Oficiais (vigente)
    fireEvent.click(screen.getByTestId("btn-criterio-valortotal"));
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("Pituba");
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("R$ 12.000.000");
    // Sob Valor Total, Zonas Especiais entram no ranking numerado (Aeroporto R$ 10M é #2, Liberdade R$ 2.4M é #3)
    expect(screen.getByTestId("ranking-bairro-2")).toHaveTextContent("Aeroporto");
    expect(screen.getByTestId("ranking-bairro-2")).toHaveTextContent("R$ 10.000.000");
    expect(screen.getByTestId("ranking-bairro-3")).toHaveTextContent("Liberdade");
    expect(screen.getByTestId("ranking-bairro-3")).toHaveTextContent("R$ 2.400.000");

    // 4. Critério: Vulnerabilidade em Bairros Oficiais
    fireEvent.click(screen.getByTestId("btn-criterio-vulnerabilidade"));
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("Liberdade");
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("0,78");

    // 5. Alterna a métrica superior para Executado / Pago
    fireEvent.click(screen.getByTestId("btn-metrica-executado"));

    // Valor Total sob Executado / Pago
    fireEvent.click(screen.getByTestId("btn-criterio-valortotal"));
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("Pituba");
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("R$ 7.860.000");
    expect(screen.getByTestId("ranking-bairro-2")).toHaveTextContent("Liberdade");
    expect(screen.getByTestId("ranking-bairro-2")).toHaveTextContent("R$ 1.200.000");

    // R$/Hab sob Executado / Pago
    fireEvent.click(screen.getByTestId("btn-criterio-investimento"));
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("Pituba");
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("R$ 120,92 / hab");
    expect(screen.getByTestId("ranking-bairro-2")).toHaveTextContent("Liberdade");
    expect(screen.getByTestId("ranking-bairro-2")).toHaveTextContent(/R\$\s*25(\,00)?\s*\/ hab/);

    // 6. Simetria nos 4 critérios em Prefeituras-Bairro
    fireEvent.click(screen.getByTestId("btn-ranking-prefeituras"));
    await waitFor(() => {
      expect(screen.getByTestId("ranking-item-1")).toBeInTheDocument();
    });

    // Em Prefeituras-Bairro sob Executado / Pago por Valor Total
    fireEvent.click(screen.getByTestId("btn-criterio-valortotal"));
    expect(screen.getByTestId("ranking-item-1")).toHaveTextContent("Barra/Pituba");
    expect(screen.getByTestId("ranking-valor-1")).toHaveTextContent("R$ 7.860.000");
    expect(screen.getByTestId("ranking-item-2")).toHaveTextContent("Liberdade/São Caetano");
    expect(screen.getByTestId("ranking-valor-2")).toHaveTextContent("R$ 1.200.000");

    // Em Prefeituras-Bairro por Vulnerabilidade
    fireEvent.click(screen.getByTestId("btn-criterio-vulnerabilidade"));
    expect(screen.getByTestId("ranking-item-1")).toHaveTextContent("Liberdade/São Caetano");
    expect(screen.getByTestId("ranking-valor-1")).toHaveTextContent("0,78");
  });

  it("alterna direção de ordenação (maiores vs menores/desassistidos primeiro) e desempata pelo maior índice de vulnerabilidade", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("tab-ranking")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("tab-ranking"));

    // 1. Controles de direção devem existir
    expect(screen.getByTestId("btn-direcao-desc")).toBeInTheDocument();
    expect(screen.getByTestId("btn-direcao-asc")).toBeInTheDocument();

    // 2. Ordenação crescente (menores / desassistidos primeiro) no critério R$/Hab
    fireEvent.click(screen.getByTestId("btn-direcao-asc"));

    // Bairros com R$ 0,00 / hab: São Caetano (vuln 0.78) e Graça (vuln 0.12)
    // Desempate: maior vulnerabilidade vem primeiro!
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("São Caetano");
    expect(screen.getByTestId("ranking-bairro-2")).toHaveTextContent("Graça");

    // 3. Ordenação crescente no critério Nº de Obras
    fireEvent.click(screen.getByTestId("btn-criterio-totalobras"));
    // Empate em 0 obras: São Caetano (vuln 0.78) antes de Graça (vuln 0.12)
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("São Caetano");
    expect(screen.getByTestId("ranking-bairro-2")).toHaveTextContent("Graça");

    // 4. Retorna a Maiores primeiro (desc)
    fireEvent.click(screen.getByTestId("btn-direcao-desc"));
    fireEvent.click(screen.getByTestId("btn-criterio-investimento"));
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("Pituba");
  });

  it("aplica semântica de cores unificada e exibe rodapé com metadados cruzados nos dois níveis", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("tab-ranking")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("tab-ranking"));

    // 1. Rodapé cruzado em Bairros Oficiais exibe os 5 indicadores simultaneamente
    const cardBairro1 = screen.getByTestId("ranking-bairro-1");
    expect(cardBairro1).toHaveTextContent("habitantes");
    expect(cardBairro1).toHaveTextContent("Total:");
    expect(cardBairro1).toHaveTextContent(/obras?/i);
    expect(cardBairro1).toHaveTextContent("/ hab");
    expect(cardBairro1).toHaveTextContent("Vulnerabilidade:");

    // 2. Cor da barra em Bairros Oficiais para critério financeiro (verde esmeralda)
    const barraBairroVerde = cardBairro1.querySelector(".bg-emerald-500, .bg-emerald-600");
    expect(barraBairroVerde).not.toBeNull();

    // 3. Cor da barra em Bairros Oficiais para vulnerabilidade (roxo índigo)
    fireEvent.click(screen.getByTestId("btn-criterio-vulnerabilidade"));
    const barraBairroRoxa = screen.getByTestId("ranking-bairro-1").querySelector(".bg-indigo-600, .bg-indigo-500");
    expect(barraBairroRoxa).not.toBeNull();

    // 4. Alterna para Prefeituras-Bairro e verifica simetria de cores e rodapé
    fireEvent.click(screen.getByTestId("btn-ranking-prefeituras"));
    await waitFor(() => {
      expect(screen.getByTestId("ranking-item-1")).toBeInTheDocument();
    });

    const cardPrefeitura1 = screen.getByTestId("ranking-item-1");
    expect(cardPrefeitura1).toHaveTextContent("habitantes");
    expect(cardPrefeitura1).toHaveTextContent("Total:");
    expect(cardPrefeitura1).toHaveTextContent(/obras?/i);
    expect(cardPrefeitura1).toHaveTextContent("Vulnerabilidade:");

    // Em vulnerabilidade, a barra da prefeitura usa índigo
    const barraPbRoxa = cardPrefeitura1.querySelector(".bg-indigo-600, .bg-indigo-500");
    expect(barraPbRoxa).not.toBeNull();

    // Em investimento, a barra da prefeitura DEVE usar verde esmeralda (unificação da semântica)
    fireEvent.click(screen.getByTestId("btn-criterio-investimento"));
    const barraPbVerde = screen.getByTestId("ranking-item-1").querySelector(".bg-emerald-500, .bg-emerald-600");
    expect(barraPbVerde).not.toBeNull();
  });

  it("permite busca textual por nome do bairro nos Bairros Oficiais (insensível a acentuação e maiúsculas/minúsculas)", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("tab-ranking")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("tab-ranking"));

    // O campo de busca por bairro oficial deve estar presente
    const searchInput = screen.getByTestId("input-busca-bairro");
    expect(searchInput).toBeInTheDocument();

    // 1. Busca por nome com minúsculas e sem acento: "graca" deve encontrar "Graça" preservando a posição relativa (#4)
    fireEvent.change(searchInput, { target: { value: "graca" } });

    const cardResultadoGraca = screen.getByTestId("ranking-bairro-1");
    expect(cardResultadoGraca).toHaveTextContent("Graça");
    expect(cardResultadoGraca).toHaveTextContent("#4");
    expect(screen.queryByText("Pituba")).not.toBeInTheDocument();
    expect(screen.queryByText("Liberdade")).not.toBeInTheDocument();

    // 2. Busca por nome em maiúsculas: "PITUBA" deve encontrar "Pituba" com sua posição (#1)
    fireEvent.change(searchInput, { target: { value: "PITUBA" } });
    const cardResultadoPituba = screen.getByTestId("ranking-bairro-1");
    expect(cardResultadoPituba).toHaveTextContent("Pituba");
    expect(cardResultadoPituba).toHaveTextContent("#1");
    expect(screen.queryByText("Graça")).not.toBeInTheDocument();

    // 3. Limpar a busca restaura a lista completa
    fireEvent.change(searchInput, { target: { value: "" } });
    expect(screen.getByText("Pituba")).toBeInTheDocument();
    expect(screen.getByText("Graça")).toBeInTheDocument();
  });

  it("permite filtrar Bairros Oficiais por Prefeitura-Bairro e restringe a lista à Prefeitura-Bairro selecionada", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("tab-ranking")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("tab-ranking"));

    const selectPb = screen.getByTestId("select-filtro-prefeitura");
    expect(selectPb).toBeInTheDocument();

    // 1. Filtra por Barra/Pituba
    fireEvent.change(selectPb, { target: { value: "Barra/Pituba" } });

    // Apenas bairros da Barra/Pituba devem aparecer (Pituba e Graça)
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("Pituba");
    expect(screen.getByTestId("ranking-bairro-2")).toHaveTextContent("Graça");
    expect(screen.queryByText("Liberdade")).not.toBeInTheDocument();
    expect(screen.queryByText("São Caetano")).not.toBeInTheDocument();

    // 2. Volta para Todas as Prefeituras-Bairro
    fireEvent.change(selectPb, { target: { value: "todas" } });
    expect(screen.getByText("Liberdade")).toBeInTheDocument();
    expect(screen.getByText("São Caetano")).toBeInTheDocument();
  });

  it("exibe banner contextual de Obras Regionais informando quantidade e valor financeiro de acordo com a métrica e a Prefeitura-Bairro filtrada", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("tab-ranking")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("tab-ranking"));

    // 1. Banner contextual deve estar presente em Bairros Oficiais
    const banner = screen.getByTestId("banner-obras-regionais");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent("Regional (Prefeitura-Bairro)");
    expect(banner).toHaveTextContent(/1 obra/i);
    expect(banner).toHaveTextContent("R$ 4.000.000");
    expect(banner).toHaveTextContent(/sem rateio artificial/i);

    // 2. Ao selecionar "Subúrbio/Ilhas" (onde a obra regional 1003 está alocada), mantém 1 obra e R$ 4.000.000
    const selectPb = screen.getByTestId("select-filtro-prefeitura");
    fireEvent.change(selectPb, { target: { value: "Subúrbio/Ilhas" } });
    expect(banner).toHaveTextContent(/1 obra/i);
    expect(banner).toHaveTextContent("R$ 4.000.000");

    // 3. Ao selecionar "Barra/Pituba" (sem obras regionais no mock), exibe 0 obras e R$ 0,00
    fireEvent.change(selectPb, { target: { value: "Barra/Pituba" } });
    expect(banner).toHaveTextContent(/0 obras?/i);
    expect(banner).toHaveTextContent(/R\$\s*0(\,00)?/);

    // 4. Retorna para todas e alterna métrica para "executado"
    fireEvent.change(selectPb, { target: { value: "todas" } });
    fireEvent.click(screen.getByTestId("btn-metrica-executado"));
    // Obra 1003 tem valorPago = 800.000
    expect(banner).toHaveTextContent("R$ 800.000");

    // 5. Clicar em um bairro individual (ex: Pituba) abre o Raio-X sem zerar o banner de obras regionais
    fireEvent.click(screen.getByTestId("ranking-bairro-1"));
    await waitFor(() => {
      expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Pituba");
    });
    // O banner de obras regionais permanece ativo e alimentado por topFilteredObras
    expect(screen.getByTestId("banner-obras-regionais")).toHaveTextContent("R$ 800.000");
  });

  it("trata Zonas Especiais Não-Residenciais condicionalmente: seção ao final em R$/Hab e Vulnerabilidade, e na lista numerada com badge em Valor Total e Nº de Obras", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("tab-ranking")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("tab-ranking"));

    // 1. Sob R$/Hab (padrão): Zonas especiais NÃO estão no ranking numerado #1..#N
    // Os bairros numerados devem ser os residenciais (Pituba, Liberdade, São Caetano, Graça)
    const cardBairro1 = screen.getByTestId("ranking-bairro-1");
    expect(cardBairro1).toHaveTextContent("Pituba");
    expect(screen.getByTestId("ranking-bairro-2")).toHaveTextContent("Liberdade");

    // Seção de Zonas Especiais deve existir ao final
    const secaoZonas = screen.getByTestId("secao-zonas-especiais");
    expect(secaoZonas).toBeInTheDocument();
    expect(secaoZonas).toHaveTextContent("Zonas Especiais Não-Residenciais — isentas do cálculo per capita");
    expect(secaoZonas).toHaveTextContent("Aeroporto");
    expect(secaoZonas).toHaveTextContent("Centro Administrativo da Bahia - CAB");
    expect(secaoZonas).toHaveTextContent("Isento per capita");

    // Clicar em Aeroporto na seção especial abre o Raio-X
    fireEvent.click(screen.getByTestId("ranking-zona-especial-1"));
    await waitFor(() => {
      expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Aeroporto");
    });
    expect(screen.getByTestId("badge-zona-especial")).toBeInTheDocument();

    // 2. Sob Vulnerabilidade: Zonas especiais permanecem na seção dedicada ao final
    fireEvent.click(screen.getByTestId("btn-criterio-vulnerabilidade"));
    expect(screen.getByTestId("secao-zonas-especiais")).toBeInTheDocument();

    // 3. Sob Valor Total: Zonas especiais ENTRAM nas posições numeradas #1..#N com badge
    fireEvent.click(screen.getByTestId("btn-criterio-valortotal"));
    expect(screen.queryByTestId("secao-zonas-especiais")).not.toBeInTheDocument();

    // Ranking por Valor Total desc:
    // 1: Pituba (R$ 12.000.000)
    // 2: Aeroporto (R$ 10.000.000) - Zona Especial
    // 3: Liberdade (R$ 2.400.000)
    // 4: Centro Administrativo da Bahia - CAB (R$ 500.000) - Zona Especial
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("Pituba");
    const itemAeroporto = screen.getByTestId("ranking-bairro-2");
    expect(itemAeroporto).toHaveTextContent("Aeroporto");
    expect(itemAeroporto).toHaveTextContent("Zona Especial Não-Residencial");
    expect(itemAeroporto).toHaveTextContent("R$ 10.000.000");
    expect(itemAeroporto).toHaveTextContent("Isento per capita");

    const itemCab = screen.getByTestId("ranking-bairro-4");
    expect(itemCab).toHaveTextContent("Centro Administrativo da Bahia - CAB");
    expect(itemCab).toHaveTextContent("Zona Especial Não-Residencial");
    expect(itemCab).toHaveTextContent("R$ 500.000");

    // 4. Sob Nº de Obras: Zonas especiais também participam do ranking numerado
    // Todas as 4 áreas com obras têm 1 obra; desempate por vulnerabilidade desc:
    // 1: Liberdade (0.78), 2: Pituba (0.12), 3: CAB (0.08), 4: Aeroporto (0.05)
    fireEvent.click(screen.getByTestId("btn-criterio-totalobras"));
    expect(screen.queryByTestId("secao-zonas-especiais")).not.toBeInTheDocument();
    const itemCabObras = screen.getByTestId("ranking-bairro-3");
    expect(itemCabObras).toHaveTextContent("Centro Administrativo da Bahia - CAB");
    expect(itemCabObras).toHaveTextContent("Zona Especial Não-Residencial");

    const itemAeroObras = screen.getByTestId("ranking-bairro-4");
    expect(itemAeroObras).toHaveTextContent("Aeroporto");
    expect(itemAeroObras).toHaveTextContent("Zona Especial Não-Residencial");
  });
});

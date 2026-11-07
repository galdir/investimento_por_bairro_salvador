import { describe, it, expect } from "vitest";
import { calculateTerritorialRollup } from "../../src/utils/territory";
import { BairroResumo, ObraCompacta, PrefeituraBairroResumo } from "../../src/types";

describe("Seam 1: Agregação e Rollup Territorial (calculateTerritorialRollup)", () => {
  const bairrosBase: BairroResumo[] = [
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
      nome: "Liberdade",
      prefeitura_bairro: "Liberdade/São Caetano",
      populacao: 48000,
      indice_vulnerabilidade: 0.78,
      is_zona_especial_nao_residencial: false,
    },
    {
      id: 103,
      nome: "Aeroporto",
      prefeitura_bairro: "Itapuã/Ipitanga",
      populacao: 0,
      indice_vulnerabilidade: 0.05,
      is_zona_especial_nao_residencial: true,
    },
  ];

  const prefeiturasBase: PrefeituraBairroResumo[] = [
    {
      id: 1,
      nome: "Barra/Pituba",
      populacao_total: 65000,
    },
    {
      id: 2,
      nome: "Liberdade/São Caetano",
      populacao_total: 48000,
    },
    {
      id: 3,
      nome: "Subúrbio/Ilhas",
      populacao_total: 80000,
    },
    {
      id: 4,
      nome: "Itapuã/Ipitanga",
      populacao_total: 30000,
    },
  ];

  const obrasExemplo: ObraCompacta[] = [
    {
      id: 1001,
      unidadeGestora: "SUCOP",
      numeroContrato: "001/2024",
      objeto: "Requalificação da Orla da Pituba",
      valorContratualVigente: 12000000.0,
      valorPago: 7860000.0,
      percentualExecutado: 65.5,
      situacao: "Em Execução",
      credor: "CONSTRUTORA SALVADOR LTDA",
      tema: "Mobilidade, Pavimentação e Drenagem",
      semaforo: {
        status: "VERDE",
        rotulo: "Verde (No Prazo)",
        motivos: ["No prazo"],
      },
      nivel: "Bairro",
      bairro: "Pituba",
      prefeituraBairro: "Barra/Pituba",
    },
    {
      id: 1002,
      unidadeGestora: "CODESAL",
      numeroContrato: "002/2024",
      objeto: "Contenção de Encosta na Liberdade",
      valorContratualVigente: 2400000.0,
      valorPago: 1200000.0,
      percentualExecutado: 50.0,
      situacao: "Em Execução",
      credor: "BAHIA ENGENHARIA S/A",
      tema: "Encostas e Contenção",
      semaforo: {
        status: "AMARELO",
        rotulo: "Amarelo (Atenção)",
        motivos: ["Aditivo"],
      },
      nivel: "Pontual",
      bairro: "Liberdade",
      prefeituraBairro: "Liberdade/São Caetano",
    },
    {
      id: 1003,
      unidadeGestora: "FME",
      numeroContrato: "015/2024",
      objeto: "Construção de Escola Municipal no Lote Subúrbio",
      valorContratualVigente: 4000000.0,
      valorPago: 800000.0,
      percentualExecutado: 20.0,
      situacao: "Paralisada",
      credor: "NORDESTE OBRAS LTDA",
      tema: "Educação e Escolas",
      semaforo: {
        status: "VERMELHO",
        rotulo: "Vermelho (Crítica)",
        motivos: ["Paralisada"],
      },
      nivel: "Regional (Prefeitura-Bairro)",
      bairro: null,
      prefeituraBairro: "Subúrbio/Ilhas",
    },
    {
      id: 1004,
      unidadeGestora: "DESAL",
      numeroContrato: "042/2024",
      objeto: "Praça esportiva genérica",
      valorContratualVigente: 1500000.0,
      valorPago: 1350000.0,
      percentualExecutado: 90.0,
      situacao: "Em Execução",
      credor: "SALVADOR PARQUES E OBRAS EIRELI",
      tema: "Praças, Esporte e Lazer",
      semaforo: {
        status: "VERDE",
        rotulo: "Verde (No Prazo)",
        motivos: ["No prazo"],
      },
      nivel: "Escopo Cidade (Não-Localizado)",
      bairro: null,
      prefeituraBairro: null,
    },
    {
      id: 1005,
      unidadeGestora: "SEINFRA",
      numeroContrato: "088/2024",
      objeto: "Obras no terminal de passageiros do aeroporto",
      valorContratualVigente: 10000000.0,
      valorPago: 5000000.0,
      percentualExecutado: 50.0,
      situacao: "Em Execução",
      credor: "INFRAERO SALVADOR",
      tema: "Mobilidade, Pavimentação e Drenagem",
      semaforo: {
        status: "VERDE",
        rotulo: "Verde (No Prazo)",
        motivos: ["No prazo"],
      },
      nivel: "Pontual",
      bairro: "Aeroporto",
      prefeituraBairro: "Itapuã/Ipitanga",
    },
  ];

  it("agrega corretamente contratos pontuais e de bairro nos seus respectivos bairros e prefeituras-bairro", () => {
    const { bairros, prefeituras } = calculateTerritorialRollup(bairrosBase, prefeiturasBase, obrasExemplo);

    // Pituba (Obra 1001)
    const pituba = bairros.find((b) => b.nome === "Pituba");
    expect(pituba).toBeDefined();
    expect(pituba?.valorTotal).toBe(12000000.0);
    expect(pituba?.valorPago).toBe(7860000.0);
    expect(pituba?.totalObras).toBe(1);
    expect(pituba?.obrasVerde).toBe(1);
    expect(pituba?.obrasAmarelo).toBe(0);
    expect(pituba?.obrasVermelho).toBe(0);
    // 12000000 / 65000 = 184.62
    expect(pituba?.investimentoPorHabitante).toBe(184.62);
    // 7860000 / 65000 = 120.92
    expect(pituba?.investimentoPorHabitantePago).toBe(120.92);

    // Barra/Pituba
    const pbBarra = prefeituras.find((pb) => pb.nome === "Barra/Pituba");
    expect(pbBarra).toBeDefined();
    expect(pbBarra?.valorTotal).toBe(12000000.0);
    expect(pbBarra?.investimentoPorHabitante).toBe(184.62);
    expect(pbBarra?.indice_vulnerabilidade).toBe(0.12);

    // Liberdade/São Caetano
    const pbLiberdade = prefeituras.find((pb) => pb.nome === "Liberdade/São Caetano");
    expect(pbLiberdade?.indice_vulnerabilidade).toBe(0.78);

    // Liberdade (Obra 1002)
    const liberdade = bairros.find((b) => b.nome === "Liberdade");
    expect(liberdade).toBeDefined();
    expect(liberdade?.valorTotal).toBe(2400000.0);
    expect(liberdade?.totalObras).toBe(1);
    expect(liberdade?.obrasAmarelo).toBe(1);
    // 2400000 / 48000 = 50.0
    expect(liberdade?.investimentoPorHabitante).toBe(50.0);
  });

  it("agrega contratos regionais exclusivamente na prefeitura-bairro sem ratear nos bairros", () => {
    const { bairros, prefeituras } = calculateTerritorialRollup(bairrosBase, prefeiturasBase, obrasExemplo);

    // Subúrbio/Ilhas tem a obra 1003 (Regional, R$ 4.000.000)
    const pbSuburbio = prefeituras.find((pb) => pb.nome === "Subúrbio/Ilhas");
    expect(pbSuburbio).toBeDefined();
    expect(pbSuburbio?.valorTotal).toBe(4000000.0);
    expect(pbSuburbio?.totalObras).toBe(1);
    expect(pbSuburbio?.obrasVermelho).toBe(1);
    // 4000000 / 80000 = 50.0
    expect(pbSuburbio?.investimentoPorHabitante).toBe(50.0);

    // Nenhum bairro constituinte deve receber a obra regional
    for (const b of bairros) {
      if (b.prefeitura_bairro === "Subúrbio/Ilhas") {
        expect(b.totalObras).toBe(0);
        expect(b.valorTotal).toBe(0);
      }
    }
  });

  it("fixa investimento per capita em 0.0 para Zonas Especiais Não-Residenciais mesmo com obras cadastradas", () => {
    const { bairros, prefeituras } = calculateTerritorialRollup(bairrosBase, prefeiturasBase, obrasExemplo);

    // Aeroporto (Obra 1005: R$ 10.000.000)
    const aeroporto = bairros.find((b) => b.nome === "Aeroporto");
    expect(aeroporto).toBeDefined();
    expect(aeroporto?.valorTotal).toBe(10000000.0);
    expect(aeroporto?.totalObras).toBe(1);
    // Regra inviolável: per capita deve ser 0.0 (isento)
    expect(aeroporto?.investimentoPorHabitante).toBe(0.0);
    expect(aeroporto?.investimentoPorHabitantePago).toBe(0.0);

    // Na Prefeitura-Bairro (Itapuã/Ipitanga), o valor bruto da obra do Aeroporto soma normalmente
    const pbItapua = prefeituras.find((pb) => pb.nome === "Itapuã/Ipitanga");
    expect(pbItapua).toBeDefined();
    expect(pbItapua?.valorTotal).toBe(10000000.0);
    // 10000000 / 30000 = 333.33
    expect(pbItapua?.investimentoPorHabitante).toBe(333.33);
  });

  it("ignora contratos de Escopo Cidade (Não-Localizado) no rollup territorial", () => {
    // Apenas a obra 1004 (Escopo Cidade)
    const { bairros, prefeituras } = calculateTerritorialRollup(bairrosBase, prefeiturasBase, [obrasExemplo[3]]);

    for (const b of bairros) {
      expect(b.totalObras).toBe(0);
      expect(b.valorTotal).toBe(0);
      expect(b.investimentoPorHabitante).toBe(0.0);
    }
    for (const pb of prefeituras) {
      expect(pb.totalObras).toBe(0);
      expect(pb.valorTotal).toBe(0);
      expect(pb.investimentoPorHabitante).toBe(0.0);
    }
  });

  it("retorna zeros quando a lista de obras filtradas está vazia", () => {
    const { bairros, prefeituras } = calculateTerritorialRollup(bairrosBase, prefeiturasBase, []);

    for (const b of bairros) {
      expect(b.totalObras).toBe(0);
      expect(b.valorTotal).toBe(0);
      expect(b.valorPago).toBe(0);
      expect(b.investimentoPorHabitante).toBe(0.0);
      expect(b.investimentoPorHabitantePago).toBe(0.0);
    }
    for (const pb of prefeituras) {
      expect(pb.totalObras).toBe(0);
      expect(pb.valorTotal).toBe(0);
      expect(pb.valorPago).toBe(0);
      expect(pb.investimentoPorHabitante).toBe(0.0);
      expect(pb.investimentoPorHabitantePago).toBe(0.0);
    }
  });
});


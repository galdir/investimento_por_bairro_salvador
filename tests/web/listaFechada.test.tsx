import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  calculateTerritorialRollup,
  getObraTerritoryShare,
  obraMatchesTerritory,
} from "../../src/utils/territory";
import { TerritorySidebar } from "../../src/components/TerritorySidebar";
import { WorksTable } from "../../src/components/WorksTable";
import { FichaLimpaModal } from "../../src/components/FichaLimpaModal";
import {
  BairroResumo,
  FichaLimpaObra,
  ObraCompacta,
  PrefeituraBairroResumo,
  TerritorySelection,
} from "../../src/types";

const BAIRROS_BASE: BairroResumo[] = [
  {
    id: 101,
    nome: "Pituba",
    prefeitura_bairro: "Barra/Pituba",
    populacao: 60000,
    indice_vulnerabilidade: 0.12,
    is_zona_especial_nao_residencial: false,
  },
  {
    id: 102,
    nome: "Amaralina",
    prefeitura_bairro: "Barra/Pituba",
    populacao: 20000,
    indice_vulnerabilidade: 0.25,
    is_zona_especial_nao_residencial: false,
  },
  {
    id: 201,
    nome: "Paripe",
    prefeitura_bairro: "Subúrbio/Ilhas",
    populacao: 50000,
    indice_vulnerabilidade: 0.65,
    is_zona_especial_nao_residencial: false,
  },
];

const PREFEITURAS_BASE: PrefeituraBairroResumo[] = [
  { id: 6, nome: "Barra/Pituba", populacao_total: 80000 },
  { id: 1, nome: "Subúrbio/Ilhas", populacao_total: 50000 },
];

const OBRA_LISTA_FECHADA: ObraCompacta = {
  id: "obra-lf-2025",
  unidadeGestora: "SEINFRA",
  numeroContrato: "099/2025",
  objeto: "Reforma de equipamentos comunitários em Pituba, Amaralina e Paripe",
  valorOriginal: 900000,
  valorContratualVigente: 900000,
  valorPago: 300000,
  percentualExecutado: 33.3,
  situacao: "Em Execução",
  credor: "CONSTRUTORA COTA LTDA",
  tema: "Praças, Esporte e Lazer",
  semaforo: { status: "AMARELO", rotulo: "Em Atraso", motivos: ["Atenção"] },
  nivel: "Bairro",
  bairro: "Pituba",
  prefeituraBairro: "Barra/Pituba",
  estagioAlocacao: "Curadoria Territorial Auditável (Lista Fechada)",
  cotasListaFechada: [
    {
      bairro: "Pituba",
      prefeituraBairro: "Barra/Pituba",
      unidades: 1,
      totalUnidades: 3,
      peso: 1 / 3,
      fracao: "1/3",
      latitude: -12.999,
      longitude: -38.458,
      descricaoUnidades: "Praça da Pituba",
    },
    {
      bairro: "Amaralina",
      prefeituraBairro: "Barra/Pituba",
      unidades: 1,
      totalUnidades: 3,
      peso: 1 / 3,
      fracao: "1/3",
      latitude: -13.008,
      longitude: -38.472,
      descricaoUnidades: "Praça de Amaralina",
    },
    {
      bairro: "Paripe",
      prefeituraBairro: "Subúrbio/Ilhas",
      unidades: 1,
      totalUnidades: 3,
      peso: 1 / 3,
      fracao: "1/3",
      latitude: -12.832,
      longitude: -38.469,
      descricaoUnidades: "Praça de Paripe",
    },
  ],
};

const OBRA_DIRETA_PITUBA: ObraCompacta = {
  id: "obra-direta-pituba",
  unidadeGestora: "SUCOP",
  numeroContrato: "100/2025",
  objeto: "Drenagem direta na Pituba",
  valorOriginal: 500000,
  valorContratualVigente: 500000,
  valorPago: 500000,
  percentualExecutado: 100,
  situacao: "Concluída",
  credor: "EMP B LTDA",
  semaforo: { status: "VERDE", rotulo: "Concluída", motivos: ["OK"] },
  nivel: "Bairro",
  bairro: "Pituba",
  prefeituraBairro: "Barra/Pituba",
};

describe("Seam 2: Cota-Parte de Lista Fechada no Rollup Dinâmico e Helpers Territoriais", () => {
  it("distribui valor proporcional por bairro, contabiliza +1 obra/semáforo e deduplica contrato na Prefeitura-Bairro", () => {
    const { bairros, prefeituras } = calculateTerritorialRollup(BAIRROS_BASE, PREFEITURAS_BASE, [
      OBRA_LISTA_FECHADA,
      OBRA_DIRETA_PITUBA,
    ]);

    const pituba = bairros.find((b) => b.nome === "Pituba")!;
    const amaralina = bairros.find((b) => b.nome === "Amaralina")!;
    const paripe = bairros.find((b) => b.nome === "Paripe")!;
    const barraPituba = prefeituras.find((p) => p.nome === "Barra/Pituba")!;
    const suburbio = prefeituras.find((p) => p.nome === "Subúrbio/Ilhas")!;

    expect(pituba.valorTotal).toBeCloseTo(800000, 2);
    expect(pituba.valorPago).toBeCloseTo(600000, 2);
    expect(pituba.totalObras).toBe(2);
    expect(pituba.obrasVerde).toBe(1);
    expect(pituba.obrasAmarelo).toBe(1);

    expect(amaralina.valorTotal).toBeCloseTo(300000, 2);
    expect(amaralina.valorPago).toBeCloseTo(100000, 2);
    expect(amaralina.totalObras).toBe(1);
    expect(amaralina.obrasAmarelo).toBe(1);

    expect(paripe.valorTotal).toBeCloseTo(300000, 2);
    expect(paripe.valorPago).toBeCloseTo(100000, 2);
    expect(paripe.totalObras).toBe(1);
    expect(paripe.obrasAmarelo).toBe(1);

    // Barra/Pituba soma R$ de Pituba (1/3) + Amaralina (1/3) + direta = 1.1M, mas deduplica obra-lf-2025 para totalObras = 2
    expect(barraPituba.valorTotal).toBeCloseTo(1100000, 2);
    expect(barraPituba.valorPago).toBeCloseTo(700000, 2);
    expect(barraPituba.totalObras).toBe(2);
    expect(barraPituba.obrasVerde).toBe(1);
    expect(barraPituba.obrasAmarelo).toBe(1);
    expect(barraPituba.obrasVermelho).toBe(0);

    expect(suburbio.valorTotal).toBeCloseTo(300000, 2);
    expect(suburbio.totalObras).toBe(1);
    expect(suburbio.obrasAmarelo).toBe(1);
  });

  it("filtra e extrai frações proporcionais corretamente tanto para Bairro Oficial quanto para Prefeitura-Bairro", () => {
    const selAmaralina: TerritorySelection = { tipo: "bairro", id: 102, nome: "Amaralina", populacao: 20000 };
    const selSuburbio: TerritorySelection = { tipo: "prefeitura_bairro", id: 1, nome: "Subúrbio/Ilhas", populacao: 50000 };
    const selBarra: TerritorySelection = { tipo: "prefeitura_bairro", id: 6, nome: "Barra/Pituba", populacao: 80000 };
    const selCentro: TerritorySelection = { tipo: "bairro", id: 999, nome: "Brotas", populacao: 70000 };

    expect(obraMatchesTerritory(OBRA_LISTA_FECHADA, selAmaralina)).toBe(true);
    expect(obraMatchesTerritory(OBRA_LISTA_FECHADA, selSuburbio)).toBe(true);
    expect(obraMatchesTerritory(OBRA_LISTA_FECHADA, selCentro)).toBe(false);

    const shareAmaralina = getObraTerritoryShare(OBRA_LISTA_FECHADA, selAmaralina);
    expect(shareAmaralina.isCotaParte).toBe(true);
    expect(shareAmaralina.matched).toBe(true);
    expect(shareAmaralina.fracao).toBe("1/3");
    expect(shareAmaralina.peso).toBeCloseTo(1 / 3, 6);

    // Em Barra/Pituba, Pituba (1/3) + Amaralina (1/3) somam 2/3 da lista
    const shareBarra = getObraTerritoryShare(OBRA_LISTA_FECHADA, selBarra);
    expect(shareBarra.isCotaParte).toBe(true);
    expect(shareBarra.matched).toBe(true);
    expect(shareBarra.fracao).toBe("2/3");
    expect(shareBarra.peso).toBeCloseTo(2 / 3, 6);
    expect(shareBarra.cotas).toHaveLength(2);
  });

  it("TerritorySidebar exibe selo Cota-Parte (n/M) e detalhamento das cotas para Bairro e Prefeitura-Bairro", () => {
    const selAmaralina: TerritorySelection = {
      tipo: "bairro",
      id: 102,
      nome: "Amaralina",
      prefeitura_bairro: "Barra/Pituba",
      populacao: 20000,
      valorTotal: 300000,
      valorPago: 100000,
      totalObras: 1,
    };

    const { rerender } = render(
      <TerritorySidebar
        territorio={selAmaralina}
        onClear={vi.fn()}
        metricType="vigente"
        obras={[OBRA_LISTA_FECHADA, OBRA_DIRETA_PITUBA]}
      />
    );

    const secaoCotas = screen.getByTestId("secao-cotas-lista-fechada");
    expect(secaoCotas).toBeInTheDocument();
    expect(screen.getByTestId("badge-cota-parte-obra-lf-2025")).toHaveTextContent("Cota-Parte (1/3)");
    expect(secaoCotas).toHaveTextContent(/300\.000/);
    expect(secaoCotas).toHaveTextContent(/900\.000/);
    expect(secaoCotas).toHaveTextContent("Praça de Amaralina");

    const selBarraPituba: TerritorySelection = {
      tipo: "prefeitura_bairro",
      id: 6,
      nome: "Barra/Pituba",
      populacao: 80000,
      valorTotal: 1100000,
      valorPago: 700000,
      totalObras: 2,
    };

    rerender(
      <TerritorySidebar
        territorio={selBarraPituba}
        onClear={vi.fn()}
        metricType="vigente"
        obras={[OBRA_LISTA_FECHADA, OBRA_DIRETA_PITUBA]}
      />
    );

    expect(screen.getByTestId("badge-cota-parte-obra-lf-2025")).toHaveTextContent("Cota-Parte (2/3)");
    expect(screen.getByTestId("secao-cotas-lista-fechada")).toHaveTextContent(/600\.000/);
    expect(screen.getByTestId("secao-cotas-lista-fechada")).toHaveTextContent(/900\.000/);
    expect(screen.getByTestId("secao-cotas-lista-fechada")).toHaveTextContent("Pituba");
    expect(screen.getByTestId("secao-cotas-lista-fechada")).toHaveTextContent("Amaralina");
  });

  it("WorksTable renderiza selo Cota-Parte (n/M), breakdown por território e fração monetária quando filtrado", () => {
    const selAmaralina: TerritorySelection = {
      tipo: "bairro",
      id: 102,
      nome: "Amaralina",
      populacao: 20000,
    };

    const { rerender } = render(
      <WorksTable
        obras={[OBRA_LISTA_FECHADA]}
        metricType="vigente"
        selectedTerritory={selAmaralina}
      />
    );

    expect(screen.getByTestId("badge-nivel-obra-lf-2025")).toHaveTextContent(/^Bairro$/);
    expect(screen.getByTestId("badge-cota-parte-obra-lf-2025")).toHaveTextContent("Cota-Parte (1/3)");
    expect(screen.getByTestId("linha-obra-obra-lf-2025")).toHaveTextContent(/300\.000/);
    expect(screen.getByTestId("linha-obra-obra-lf-2025")).toHaveTextContent(/900\.000/);
    expect(screen.getByTestId("cota-breakdown-obra-lf-2025")).toHaveTextContent("Pituba (1/3)");
    expect(screen.getByTestId("cota-breakdown-obra-lf-2025")).toHaveTextContent("Amaralina (1/3)");
    expect(screen.getByTestId("cota-breakdown-obra-lf-2025")).toHaveTextContent("Paripe (1/3)");

    rerender(
      <WorksTable
        obras={[OBRA_LISTA_FECHADA]}
        metricType="vigente"
        selectedTerritory={null}
      />
    );

    expect(screen.getByTestId("badge-cota-parte-obra-lf-2025")).toHaveTextContent("Cota-Parte (3/3)");
    expect(screen.getByTestId("linha-obra-obra-lf-2025")).toHaveTextContent(/900\.000/);
  });

  it("FichaLimpaModal exibe selo Cota-Parte e distribuição território a território em Fontes Oficiais & Lastro Territorial", () => {
    const obraFichaListaFechada: FichaLimpaObra = {
      id: "obra-lf-2025",
      cdUnidadeGestora: "567002",
      unidadeGestora: "SEINFRA",
      numeroContrato: "099/2025",
      numeroContratoOriginal: "099/2025",
      objeto: OBRA_LISTA_FECHADA.objeto,
      situacao: "Em Execução",
      empreiteira: {
        razaoSocial: "CONSTRUTORA COTA LTDA",
        cnpj: "11.222.333/0001-44",
        totalObras: 1,
        valorTotalContratado: 900000,
      },
      vigencia: {
        dataInicio: "2025-02-01T00:00:00.000Z",
        dataTerminoAtualizado: "2027-12-31T00:00:00.000Z",
      },
      dom: { nuDom: "9.100" },
      funilFinanceiro: {
        valorOriginal: 900000,
        valorContratualVigente: 900000,
        valorEmpenhado: 900000,
        valorLiquidado: 600000,
        valorPago: 300000,
        percentualExecutado: 33.3,
        valorAditivos: 0,
        deltaPercentualAditivos: 0,
      },
      aditivos: [],
      dotacao: [{ fonteRecurso: "Tesouro Municipal" }],
      nivel: "Bairro",
      bairro: "Pituba",
      prefeituraBairro: "Barra/Pituba",
      estagioAlocacao: "Curadoria Territorial Auditável (Lista Fechada)",
      cotasListaFechada: OBRA_LISTA_FECHADA.cotasListaFechada,
      fontesOficiais: {
        portalTransparencia: {
          nome: "Portal da Transparência de Salvador",
          url: "https://www.transparencia.salvador.ba.gov.br/",
        },
        chaveCanonica: {
          cdUnidadeGestora: "567002",
          unidadeGestora: "SEINFRA",
          nuContratoSigef: "099/2025",
        },
        nuProcesso: "00099/2025",
        domContrato: { nuDom: "9.100", url: "https://dom.salvador.ba.gov.br/" },
        domAditivos: [],
        lastroTerritorial: {
          nivel: "Bairro",
          estagioAlocacao: "Curadoria Territorial Auditável (Lista Fechada)",
          bairro: "Pituba",
          prefeituraBairro: "Barra/Pituba",
          origem: "Lista fechada contratual em 3 bairros oficiais",
          trechoComprobatorio: "Praça da Pituba, Praça de Amaralina e Praça de Paripe",
          documentoOrigem: "dsObjeto / Termo de Referência",
          justificativa: "Três equipamentos explicitados no contrato.",
          cotasListaFechada: OBRA_LISTA_FECHADA.cotasListaFechada,
        },
      },
    };

    render(<FichaLimpaModal obra={obraFichaListaFechada} onClose={vi.fn()} />);

    const secaoFontes = screen.getByTestId("secao-fontes-oficiais");
    const secaoCotas = screen.getByTestId("fontes-cotas-lista-fechada");
    expect(secaoFontes).toContainElement(secaoCotas);
    expect(screen.getByTestId("ficha-badge-cota-parte")).toHaveTextContent("Cota-Parte territorial");
    expect(screen.getByTestId("ficha-badge-cota-parte")).not.toHaveTextContent("3/3");
    expect(secaoCotas).toHaveTextContent(/900\.000/);

    expect(screen.getByTestId("fontes-cota-badge-0")).toHaveTextContent("Cota-Parte (1/3)");
    expect(screen.getByTestId("fontes-cota-item-0")).toHaveTextContent("Pituba");
    expect(screen.getByTestId("fontes-cota-item-0")).toHaveTextContent(/300\.000/);
    expect(screen.getByTestId("fontes-cota-item-0")).toHaveTextContent("Praça da Pituba");

    expect(screen.getByTestId("fontes-cota-badge-1")).toHaveTextContent("Cota-Parte (1/3)");
    expect(screen.getByTestId("fontes-cota-item-1")).toHaveTextContent("Amaralina");

    expect(screen.getByTestId("fontes-cota-badge-2")).toHaveTextContent("Cota-Parte (1/3)");
    expect(screen.getByTestId("fontes-cota-item-2")).toHaveTextContent("Paripe");
  });

  it("prioriza Frentes de Medição sobre cotasListaFechada no rollup e no compartilhamento territorial", () => {
    const obraComFrenteECotaStale: ObraCompacta = {
      ...OBRA_LISTA_FECHADA,
      id: "obra-frente-precedencia",
      nivel: "Escopo Cidade (Não-Localizado)",
      bairro: null,
      prefeituraBairro: null,
      frentesMedicao: [
        {
          notaLiquidacao: "2025NL900",
          nivel: "Bairro",
          bairro: "Pituba",
          prefeituraBairro: "Barra/Pituba",
          valorLiquidado: 200000,
          valorPago: 150000,
        },
      ],
    };

    const shareAmaralina = getObraTerritoryShare(obraComFrenteECotaStale, {
      tipo: "bairro",
      nome: "Amaralina",
    });
    expect(shareAmaralina.isCotaParte).toBe(false);
    expect(shareAmaralina.matched).toBe(false);

    const { bairros } = calculateTerritorialRollup(
      BAIRROS_BASE,
      PREFEITURAS_BASE,
      [obraComFrenteECotaStale]
    );
    const amaralina = bairros.find((b) => b.nome === "Amaralina")!;
    const pituba = bairros.find((b) => b.nome === "Pituba")!;

    expect(amaralina.valorTotal).toBe(0);
    expect(amaralina.totalObras).toBe(0);
    expect(pituba.valorPagoFrentes).toBe(150000);
    expect(pituba.valorTotal).toBe(0);
  });
});

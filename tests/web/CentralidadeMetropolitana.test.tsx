import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import L from "leaflet";
import { InteractiveMap } from "../../src/components/InteractiveMap";
import { PrefeiturasRanking } from "../../src/components/PrefeiturasRanking";
import { BairroResumo, PrefeituraBairroResumo } from "../../src/types";

const prefeiturasMock: PrefeituraBairroResumo[] = [
  {
    id: 1,
    nome: "Centro/Brotas",
    populacao_total: 60000,
    indice_vulnerabilidade: 0.3,
    valorTotal: 25000000,
    valorPago: 10000000,
    totalObras: 5,
    investimentoPorHabitante: 416.67,
    investimentoPorHabitantePago: 166.67,
  },
  {
    id: 2,
    nome: "Barra/Pituba",
    populacao_total: 65000,
    indice_vulnerabilidade: 0.12,
    valorTotal: 12000000,
    valorPago: 7860000,
    totalObras: 2,
    investimentoPorHabitante: 184.62,
    investimentoPorHabitantePago: 120.92,
  },
];

const bairrosMock: BairroResumo[] = [
  {
    id: 101,
    nome: "Pituba",
    prefeitura_bairro: "Barra/Pituba",
    populacao: 65000,
    indice_vulnerabilidade: 0.12,
    is_zona_especial_nao_residencial: false,
    is_centralidade_metropolitana: false,
    valorTotal: 12000000,
    valorPago: 7860000,
    totalObras: 2,
    investimentoPorHabitante: 184.62,
    investimentoPorHabitantePago: 120.92,
  },
  {
    id: 102,
    nome: "Comércio",
    prefeitura_bairro: "Centro/Brotas",
    populacao: 971,
    indice_vulnerabilidade: 0.48,
    is_zona_especial_nao_residencial: false,
    is_centralidade_metropolitana: true,
    valorTotal: 20000000,
    valorPago: 5000000,
    totalObras: 4,
    investimentoPorHabitante: 0,
    investimentoPorHabitantePago: 0,
  },
  {
    id: 103,
    nome: "Aeroporto",
    prefeitura_bairro: "Itapuã/Ipitanga",
    populacao: 0,
    indice_vulnerabilidade: 0.0,
    is_zona_especial_nao_residencial: true,
    is_centralidade_metropolitana: false,
    valorTotal: 10000000,
    valorPago: 5000000,
    totalObras: 1,
    investimentoPorHabitante: 0,
    investimentoPorHabitantePago: 0,
  },
];

describe("Centralidade Metropolitana (Comércio) no Ranking Territorial", () => {
  it("exibe Comércio na seção de rodapé em R$/Hab e na lista numerada em Vulnerabilidade, Valor Total e Nº de Obras", () => {
    render(
      <PrefeiturasRanking
        prefeituras={prefeiturasMock}
        bairros={bairrosMock}
        obras={[]}
        metricType="vigente"
        activeLevel="bairros"
        onSelectPrefeitura={vi.fn()}
        onSelectBairro={vi.fn()}
      />
    );

    // 1. Em R$/Hab (padrão): apenas Pituba está na lista numerada; Comércio e Aeroporto ficam na seção de rodapé
    expect(screen.getByTestId("ranking-bairro-1")).toHaveTextContent("Pituba");
    expect(screen.queryByTestId("ranking-bairro-2")).not.toBeInTheDocument();

    const secaoIsentos = screen.getByTestId("secao-zonas-especiais");
    expect(secaoIsentos).toHaveTextContent("Comércio");
    expect(secaoIsentos).toHaveTextContent("Centralidade Metropolitana");
    expect(secaoIsentos).toHaveTextContent("Isento per capita • Vulnerabilidade: 0,48");
    expect(secaoIsentos).toHaveTextContent("Aeroporto");
    expect(secaoIsentos).toHaveTextContent("Isento per capita • Vulnerabilidade: Isento");

    // 2. Em Vulnerabilidade: Comércio entra no ranking numerado (#1) com badge Centralidade Metropolitana; apenas Aeroporto fica no rodapé
    fireEvent.click(screen.getByTestId("btn-criterio-vulnerabilidade"));
    const itemComercioVuln = screen.getByTestId("ranking-bairro-1");
    expect(itemComercioVuln).toHaveTextContent("Comércio");
    expect(itemComercioVuln).toHaveTextContent("Centralidade Metropolitana");
    expect(itemComercioVuln).toHaveTextContent("0,48");
    expect(screen.getByTestId("ranking-bairro-2")).toHaveTextContent("Pituba");

    const secaoVuln = screen.getByTestId("secao-zonas-especiais");
    expect(secaoVuln).not.toHaveTextContent("Comércio");
    expect(secaoVuln).toHaveTextContent("Aeroporto");

    // 3. Em Valor Total: Comércio entra no ranking numerado (#1) com badge Centralidade Metropolitana
    fireEvent.click(screen.getByTestId("btn-criterio-valortotal"));
    expect(screen.queryByTestId("secao-zonas-especiais")).not.toBeInTheDocument();
    const itemComercioValor = screen.getByTestId("ranking-bairro-1");
    expect(itemComercioValor).toHaveTextContent("Comércio");
    expect(itemComercioValor).toHaveTextContent("Centralidade Metropolitana");

    // 4. Em Nº de Obras: Comércio entra no ranking numerado (#1) com badge Centralidade Metropolitana
    fireEvent.click(screen.getByTestId("btn-criterio-totalobras"));
    expect(screen.queryByTestId("secao-zonas-especiais")).not.toBeInTheDocument();
    const itemComercioObras = screen.getByTestId("ranking-bairro-1");
    expect(itemComercioObras).toHaveTextContent("Comércio");
    expect(itemComercioObras).toHaveTextContent("Centralidade Metropolitana");
    expect(itemComercioObras).toHaveTextContent("4 obras");
  });
});

describe("Centralidade Metropolitana (Comércio) no Mapa Coroplético", () => {
  it("exibe Comércio como Isento âmbar em R$/Hab e com escala roxa e Vuln: 0,48 em Vulnerabilidade Social", () => {
    const bairrosGeoJson = {
      type: "FeatureCollection",
      features: [
        { type: "Feature", properties: { id: 101, nome: "Pituba", prefeitura_bairro: "Barra/Pituba" }, geometry: null },
        { type: "Feature", properties: { id: 102, nome: "Comércio", prefeitura_bairro: "Centro/Brotas" }, geometry: null },
        { type: "Feature", properties: { id: 103, nome: "Aeroporto", prefeitura_bairro: "Itapuã/Ipitanga" }, geometry: null },
      ],
    };

    const geoJsonSpy = vi.spyOn(L, "geoJSON");

    render(
      <InteractiveMap
        activeLayer="bairros"
        onToggleLayer={vi.fn()}
        bairros={bairrosMock}
        prefeituras={prefeiturasMock}
        bairrosGeoJson={bairrosGeoJson}
        prefeiturasGeoJson={null}
        obras={[]}
        metricType="vigente"
        selectedTerritory={null}
        onSelectTerritory={vi.fn()}
        onSelectObra={vi.fn()}
      />
    );

    // 1. Camada R$ / Habitante: Comércio e Aeroporto recebem cor âmbar (#fef3c7) no mapa coroplético
    const lastCallPerCapita = geoJsonSpy.mock.calls[geoJsonSpy.mock.calls.length - 1];
    const styleFnPerCapita = (lastCallPerCapita?.[1] as any)?.style;
    expect(styleFnPerCapita({ properties: { nome: "Comércio" } }).fillColor).toBe("#fef3c7");
    expect(styleFnPerCapita({ properties: { nome: "Aeroporto" } }).fillColor).toBe("#fef3c7");

    // 2. Alternar para Vulnerabilidade Social: Comércio recebe escala roxa (não âmbar) e Aeroporto permanece âmbar
    fireEvent.click(screen.getByTestId("btn-camada-vulnerabilidade"));

    const lastCallVuln = geoJsonSpy.mock.calls[geoJsonSpy.mock.calls.length - 1];
    const styleFnVuln = (lastCallVuln?.[1] as any)?.style;
    expect(styleFnVuln({ properties: { nome: "Comércio" } }).fillColor).not.toBe("#fef3c7");
    expect(styleFnVuln({ properties: { nome: "Aeroporto" } }).fillColor).toBe("#fef3c7");
  });
});

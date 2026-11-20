import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TerritoryComparisonList } from "../../src/components/TerritoryComparisonList";
import { PrefeiturasRanking } from "../../src/components/PrefeiturasRanking";
import { BairroResumo, PrefeituraBairroResumo } from "../../src/types";

const bairrosFixture: BairroResumo[] = [
  {
    id: 1,
    nome: "Aquarius",
    prefeitura_bairro: "Barra/Pituba",
    populacao: 0,
    indice_vulnerabilidade: 0.05,
    pct_esgoto_inadequado: 0.19,
    pct_agua_inadequada: 0.35,
    pct_analfabetismo_15mais: 0.35,
    vulnerabilidade_estimada_contiguidade: true,
    is_zona_especial_nao_residencial: false,
    valorTotal: 500000,
    valorPago: 200000,
    valorPagoDisponivel: true,
    totalObras: 2,
    investimentoPorHabitante: null,
    investimentoPorHabitantePago: null,
  },
  {
    id: 2,
    nome: "Comércio",
    prefeitura_bairro: "Centro/Brotas",
    populacao: 971,
    indice_vulnerabilidade: 0.42,
    pct_esgoto_inadequado: 1.38,
    pct_agua_inadequada: 1.1,
    pct_analfabetismo_15mais: 5.95,
    vulnerabilidade_estimada_contiguidade: false,
    is_zona_especial_nao_residencial: false,
    is_centralidade_metropolitana: true,
    valorTotal: 1000000,
    valorPago: 800000,
    valorPagoDisponivel: true,
    totalObras: 3,
    investimentoPorHabitante: 0,
    investimentoPorHabitantePago: 0,
  },
  {
    id: 3,
    nome: "Aeroporto",
    prefeitura_bairro: "Itapuã/Ipitanga",
    populacao: 0,
    indice_vulnerabilidade: 0,
    vulnerabilidade_estimada_contiguidade: false,
    is_zona_especial_nao_residencial: true,
    valorTotal: 300000,
    valorPago: 150000,
    valorPagoDisponivel: true,
    totalObras: 1,
    investimentoPorHabitante: 0,
    investimentoPorHabitantePago: 0,
  },
];

const prefeiturasFixture: PrefeituraBairroResumo[] = [
  {
    id: 1,
    nome: "Barra/Pituba",
    populacao_total: 100000,
    indice_vulnerabilidade: 0.14,
    vulnerabilidade_estimada_contiguidade: true,
    bairros_vulnerabilidade_estimada: ["Aquarius"],
    valorTotal: 500000,
    valorPago: 200000,
    valorPagoDisponivel: true,
    totalObras: 2,
    investimentoPorHabitante: 5,
    investimentoPorHabitantePago: 2,
  },
];

describe("Consistência visual de Aquarius (população 0) em Comparação e Ranking Territorial", () => {
  it("exibe Aquarius com Per capita indisponível em estilo neutro (distinto do âmbar de Isento) na Comparação Territorial", () => {
    render(
      <TerritoryComparisonList
        activeLayer="bairros"
        prefeituras={prefeiturasFixture}
        bairros={bairrosFixture}
        metricType="vigente"
        sortDirection="asc"
        onToggleSortDirection={vi.fn()}
        selectedTerritory={null}
        onSelectTerritory={vi.fn()}
      />
    );

    const aquariusValor = screen.getByTestId("comparison-valor-aquarius");
    expect(aquariusValor).toHaveTextContent("Per capita indisponível");
    expect(aquariusValor.className).toContain("bg-slate-100");
    expect(aquariusValor.className).toContain("text-slate-700");
    expect(aquariusValor.className).not.toContain("amber");
    expect(aquariusValor).not.toHaveTextContent(/R\$\s*0,00/);

    expect(screen.getByTestId("comparison-vuln-aquarius")).toHaveTextContent("0,05");
    expect(screen.getByTestId("comparison-estimativa-aquarius")).toHaveTextContent(/Estimativa por contiguidade/i);
    expect(screen.getByTestId("comparison-row-aquarius")).toHaveTextContent("2 obras");
    expect(screen.getByTestId("comparison-total-aquarius")).toBeInTheDocument();

    const comercioValor = screen.getByTestId("comparison-valor-comercio");
    expect(comercioValor).toHaveTextContent("Isento per capita");
    expect(comercioValor.className).toContain("bg-amber-100");

    const aeroportoValor = screen.getByTestId("comparison-valor-aeroporto");
    expect(aeroportoValor).toHaveTextContent("Isento per capita");
    expect(aeroportoValor.className).toContain("bg-amber-100");
  });

  it("exibe Aquarius com Per capita indisponível em estilo neutro (nunca R$ 0,00 / hab) no Ranking Territorial de bairros", () => {
    render(
      <PrefeiturasRanking
        prefeituras={prefeiturasFixture}
        bairros={bairrosFixture}
        metricType="vigente"
        activeLevel="bairros"
        onSelectPrefeitura={vi.fn()}
        onSelectBairro={vi.fn()}
      />
    );

    const aquariusCard = screen.getByTestId("ranking-bairro-1");
    expect(aquariusCard).toHaveTextContent("Aquarius");
    expect(aquariusCard).toHaveTextContent("Per capita indisponível");
    expect(aquariusCard).toHaveTextContent("Vulnerabilidade: 0,05");
    expect(aquariusCard).toHaveTextContent("2 obras");
    expect(aquariusCard).not.toHaveTextContent(/R\$\s*0,00\s*\/\s*hab/);

    const aquariusValor = screen.getByTestId("ranking-bairro-valor-1");
    expect(aquariusValor).toHaveTextContent("Per capita indisponível");
    expect(aquariusValor.className).toContain("bg-slate-100");
    expect(aquariusValor.className).not.toContain("amber");
  });
});

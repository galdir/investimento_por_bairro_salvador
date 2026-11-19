import { expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TerritoryComparisonList } from "../../src/components/TerritoryComparisonList";
import { calculateTerritorialRollup } from "../../src/utils/territory";
import { ObraCompacta } from "../../src/types";

it("representa saldo negativo na escala de forma distinta de zero", () => {
  render(<TerritoryComparisonList activeLayer="bairros" prefeituras={[]} bairros={[
    { id: 1, nome: "Pituba", prefeitura_bairro: "Barra", populacao: 100, is_zona_especial_nao_residencial: false,
      indice_vulnerabilidade: 0.5, totalObras: 1, valorPago: -1000, investimentoPorHabitantePago: -10, valorPagoDisponivel: true },
  ]} metricType="executado" sortDirection="desc" onToggleSortDirection={vi.fn()}
    selectedTerritory={null} onSelectTerritory={vi.fn()} />);
  expect(screen.getByTestId("comparison-bar-pituba")).toHaveStyle({ width: "100%" });
  expect(screen.getByTestId("comparison-bar-pituba")).toHaveClass("bg-rose-600");
});

it("mostra limitação e conta uma obra sem valor vinculada por duas frentes", () => {
  const base = [{ id: 1, nome: "Pituba", prefeitura_bairro: "Barra", populacao: 100,
    is_zona_especial_nao_residencial: false, indice_vulnerabilidade: 0.5 }];
  const obra: ObraCompacta = { id: 1, unidadeGestora: "UG", numeroContrato: "1", objeto: "Obra",
    valorContratualVigente: 100, valorPago: null, percentualExecutado: 0, situacao: "", credor: "",
    apuracaoPagamentos: { situacao: "indisponivel", registrosSemValor: 2, limitacoesConhecidas: ["Histórico anterior a 2020 indisponível"] },
    frentesMedicao: ["1", "2"].map(notaLiquidacao => ({ notaLiquidacao, nivel: "Bairro", bairro: "Pituba", valorLiquidado: 0, valorPago: null })) };
  const { bairros } = calculateTerritorialRollup(base, [], [obra]);
  render(<TerritoryComparisonList activeLayer="bairros" prefeituras={[]} bairros={bairros}
    metricType="executado" sortDirection="desc" onToggleSortDirection={vi.fn()} selectedTerritory={null} onSelectTerritory={vi.fn()} />);
  const linha = screen.getByTestId("comparison-row-pituba");
  expect(linha).toHaveTextContent("Pagamento indisponível");
  expect(linha).toHaveTextContent("1 obra(s) sem valor de pagamento");
  expect(linha).toHaveTextContent("Histórico anterior a 2020 indisponível");
  const semObras = calculateTerritorialRollup(base, [], []).bairros;
  render(<TerritoryComparisonList activeLayer="bairros" prefeituras={[]} bairros={semObras}
    metricType="executado" sortDirection="desc" onToggleSortDirection={vi.fn()} selectedTerritory={null} onSelectTerritory={vi.fn()} />);
  const listaSemObras = screen.getAllByTestId("comparison-row-pituba")[1];
  expect(listaSemObras).not.toHaveTextContent("Histórico anterior a 2020 indisponível");
  expect(listaSemObras).not.toHaveTextContent("sem valor de pagamento");
});

it("identifica soma parcial também em zona especial isenta", () => {
  render(<TerritoryComparisonList activeLayer="bairros" prefeituras={[]} bairros={[
    { id: 2, nome: "Aeroporto", prefeitura_bairro: "Barra", populacao: 0, is_zona_especial_nao_residencial: true,
      valorPago: 0, valorPagoDisponivel: true, limitacoesConhecidas: ["Histórico anterior indisponível"] },
  ]} metricType="executado" sortDirection="desc" onToggleSortDirection={vi.fn()}
    selectedTerritory={null} onSelectTerritory={vi.fn()} />);
  expect(screen.getByTestId("comparison-row-aeroporto")).toHaveTextContent("Soma parcial:");
  expect(screen.getByTestId("comparison-row-aeroporto")).toHaveTextContent("Histórico anterior indisponível");
});

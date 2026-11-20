import { expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TerritoryComparisonList } from "../../src/components/TerritoryComparisonList";

it("posiciona território com saldo negativo no bloco comparável à frente de território com pagamento indisponível ao final", () => {
  render(
    <TerritoryComparisonList
      activeLayer="bairros"
      prefeituras={[]}
      metricType="executado"
      sortColumn="investimentoPorHabitante"
      sortDirection="desc"
      onToggleSortDirection={vi.fn()}
      selectedTerritory={null}
      onSelectTerritory={vi.fn()}
      bairros={[
        {
          id: 1,
          nome: "Paripe",
          prefeitura_bairro: "Subúrbio/Ilhas",
          populacao: 50000,
          indice_vulnerabilidade: 0.85,
          is_zona_especial_nao_residencial: false,
          totalObras: 1,
          valorPago: null,
          valorPagoDisponivel: false,
          investimentoPorHabitantePago: null,
        },
        {
          id: 2,
          nome: "Pituba",
          prefeitura_bairro: "Barra/Pituba",
          populacao: 65000,
          indice_vulnerabilidade: 0.12,
          is_zona_especial_nao_residencial: false,
          totalObras: 1,
          valorPago: -65000,
          valorPagoDisponivel: true,
          investimentoPorHabitantePago: -1,
        },
      ]}
    />
  );

  const rows = Array.from(screen.getByTestId("comparison-list-items").querySelectorAll("li"));
  expect(rows.map((li) => li.getAttribute("data-testid"))).toEqual([
    "comparison-row-pituba",
    "comparison-row-paripe",
  ]);
  expect(screen.getByTestId("comparison-row-pituba")).toHaveTextContent("#1");
  expect(screen.getByTestId("comparison-bar-pituba")).toHaveClass("bg-rose-600");
  expect(screen.getByTestId("comparison-row-paripe")).not.toHaveTextContent("#");
  expect(screen.getByTestId("comparison-valor-paripe")).toHaveTextContent("Pagamento indisponível");
});

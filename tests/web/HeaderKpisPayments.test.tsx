import { expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { HeaderKpis } from "../../src/components/HeaderKpis";

it("identifica a soma parcial nos totais afetados e explica a limitação", () => {
  render(<HeaderKpis metricType="executado" limitacoesConhecidas={["Histórico anterior a 2020 indisponível"]}
    limitacoesAlocadas={["Histórico anterior a 2020 indisponível"]} kpis={{ totalObras: 1, valorTotal: 1,
      totalAtivas: 1, totalEmpenhado: 0, totalLiquidado: 0, totalPago: 0, investimentoPorHabitanteCidade: 0 }} />);
  expect(screen.getAllByText(/Soma Parcial de Pagamentos/).length).toBeGreaterThan(0);
  expect(screen.getByText("Histórico anterior a 2020 indisponível")).toBeInTheDocument();
});

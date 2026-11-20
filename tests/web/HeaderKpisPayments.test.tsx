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

it("mantém a Data de Referência dos Pagamentos da rodada vigente no cabeçalho principal", () => {
  render(
    <HeaderKpis
      metricType="executado"
      atualizacao={{
        versaoDados: "abc123",
        dataReferenciaPagamentos: "2026-06-15",
        inicioConsultas: "2026-06-15T10:00:00Z",
        fimConsultas: "2026-06-15T10:05:00Z",
        concluidaEm: "2026-06-15T10:05:00Z",
        consultas: "concluidas",
        validacoes: "aprovadas",
        coberturaHistorica: "nao_verificada",
        limitacoesConhecidas: [],
      }}
      kpis={{
        totalObras: 10,
        valorTotal: 1000,
        totalAtivas: 2,
        totalEmpenhado: 800,
        totalLiquidado: 600,
        totalPago: 500,
        investimentoPorHabitanteCidade: 1,
      }}
    />
  );

  expect(screen.getByText(/Referência dos pagamentos: 15\/06\/2026/i)).toBeInTheDocument();
  expect(screen.queryByText(/Pagamentos consolidados em/i)).not.toBeInTheDocument();
});

it("calcula dinamicamente o rótulo de Todos os mandatos com fallback 2017–2028", () => {
  const kpisBase = {
    totalObras: 10,
    valorTotal: 1000,
    totalAtivas: 2,
    totalEmpenhado: 800,
    totalLiquidado: 600,
    totalPago: 500,
    investimentoPorHabitanteCidade: 1,
  };

  const { rerender } = render(
    <HeaderKpis metricType="executado" mandato="todos" kpis={kpisBase} />
  );
  expect(screen.getByTestId("header-subtitulo")).toHaveTextContent(
    "Salvador • Todos os mandatos (2017–2028)"
  );

  rerender(
    <HeaderKpis
      metricType="executado"
      mandato="todos"
      mandatosDisponiveis={[]}
      kpis={kpisBase}
    />
  );
  expect(screen.getByTestId("header-subtitulo")).toHaveTextContent(
    "Salvador • Todos os mandatos (2017–2028)"
  );

  rerender(
    <HeaderKpis
      metricType="executado"
      mandato="todos"
      mandatosDisponiveis={["invalido"]}
      kpis={kpisBase}
    />
  );
  expect(screen.getByTestId("header-subtitulo")).toHaveTextContent(
    "Salvador • Todos os mandatos (2017–2028)"
  );

  rerender(
    <HeaderKpis
      metricType="executado"
      mandato="todos"
      mandatosDisponiveis={["2017-2020", "2021–2024", "2025-2028"]}
      kpis={kpisBase}
    />
  );
  expect(screen.getByTestId("header-subtitulo")).toHaveTextContent(
    "Salvador • Todos os mandatos (2017–2028)"
  );

  rerender(
    <HeaderKpis
      metricType="executado"
      mandato="todos"
      mandatosDisponiveis={["2025-2028", "2021-2024", "2017-2020"]}
      kpis={kpisBase}
    />
  );
  expect(screen.getByTestId("header-subtitulo")).toHaveTextContent(
    "Salvador • Todos os mandatos (2017–2028)"
  );
});

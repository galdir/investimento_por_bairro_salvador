import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { WorksTable } from "../../src/components/WorksTable";
import { ObraCompacta } from "../../src/types";

const BASE_OBRA: Omit<ObraCompacta, "id" | "objeto" | "vocacao"> = {
  unidadeGestora: "SUCOP",
  numeroContrato: "001/2025",
  valorOriginal: 1000000,
  valorContratualVigente: 1000000,
  valorPago: 500000,
  percentualExecutado: 50,
  situacao: "Em Execução",
  credor: "CONSTRUTORA TESTE",
  tema: "Mobilidade, Pavimentação e Drenagem",
  nivel: "Bairro",
  bairro: "Liberdade",
  prefeituraBairro: "Liberdade/São Caetano",
};

describe("WorksTable — Selo de Vocação da Obra", () => {
  it("exibe o selo de Vocação da Obra para cada categoria e aplica fallback conservador quando ausente", () => {
    const obras: ObraCompacta[] = [
      {
        ...BASE_OBRA,
        id: "obra-1",
        objeto: "Reforma da Escola Municipal",
        valorContratualVigente: 4000000,
        vocacao: "Vizinhança e Comunidade",
      },
      {
        ...BASE_OBRA,
        id: "obra-2",
        objeto: "Viaduto do BRT",
        valorContratualVigente: 3000000,
        vocacao: "Mobilidade Estrutural e Orlas",
      },
      {
        ...BASE_OBRA,
        id: "obra-3",
        objeto: "Requalificação do Mercado Modelo",
        valorContratualVigente: 2000000,
        vocacao: "Equipamentos e Marcos da Cidade",
      },
      {
        ...BASE_OBRA,
        id: "obra-4",
        objeto: "Pavimentação local sem vocação explícita",
        valorContratualVigente: 1000000,
      },
    ];

    render(<WorksTable obras={obras} metricType="vigente" onSelectObra={vi.fn()} />);

    expect(screen.getByTestId("badge-vocacao-obra-1")).toHaveTextContent("Vizinhança e Comunidade");
    expect(screen.getByTestId("badge-vocacao-obra-2")).toHaveTextContent("Mobilidade Estrutural e Orlas");
    expect(screen.getByTestId("badge-vocacao-obra-3")).toHaveTextContent("Equipamentos e Marcos da Cidade");
    expect(screen.getByTestId("badge-vocacao-obra-4")).toHaveTextContent("Vizinhança e Comunidade");
  });
});

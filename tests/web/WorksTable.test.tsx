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
  it("exibe valor indisponível para frente sem pagamento apurável", () => {
    const obra: ObraCompacta = { ...BASE_OBRA, id: "frente", objeto: "Contrato por frentes",
      nivel: "Escopo Cidade (Não-Localizado)", bairro: null, prefeituraBairro: null, valorPago: null,
      frentesMedicao: [{ notaLiquidacao: "NL1", nivel: "Bairro", bairro: "Liberdade",
        prefeituraBairro: "Liberdade/São Caetano", valorLiquidado: 100, valorPago: null }] };
    render(<WorksTable obras={[obra]} metricType="executado" onSelectObra={vi.fn()}
      selectedTerritory={{ tipo: "bairro", id: 1, nome: "Liberdade", populacao: 48000 }} />);
    expect(screen.getByText("Indisponível")).toBeInTheDocument();
  });

  it("ordena valores negativos das frentes antes do valor indisponível", () => {
    const base: ObraCompacta = { ...BASE_OBRA, id: "x", objeto: "Frente", nivel: "Escopo Cidade (Não-Localizado)",
      bairro: null, prefeituraBairro: null };
    const obras = [
      { ...base, id: "ausente", frentesMedicao: [{ notaLiquidacao: "NL1", nivel: "Bairro", bairro: "Liberdade", valorLiquidado: 1, valorPago: null }] },
      { ...base, id: "menos2", frentesMedicao: [{ notaLiquidacao: "NL2", nivel: "Bairro", bairro: "Liberdade", valorLiquidado: 1, valorPago: -2 }] },
      { ...base, id: "menos05", frentesMedicao: [{ notaLiquidacao: "NL3", nivel: "Bairro", bairro: "Liberdade", valorLiquidado: 1, valorPago: -0.5 }] },
    ];
    render(<WorksTable obras={obras} metricType="executado" onSelectObra={vi.fn()}
      selectedTerritory={{ tipo: "bairro", id: 1, nome: "Liberdade", populacao: 48000 }} />);
    const linhas = screen.getAllByTestId(/^linha-obra-/).map((linha) => linha.getAttribute("data-testid"));
    expect(linhas).toEqual(["linha-obra-menos05", "linha-obra-menos2", "linha-obra-ausente"]);
  });
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

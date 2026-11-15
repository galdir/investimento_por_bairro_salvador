import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TerritorySidebar } from "../../src/components/TerritorySidebar";
import { ObraCompacta, TerritorySelection } from "../../src/types";

describe("Seam 3: Painel Lateral Raio-X (TerritorySidebar) com Decomposição Censo 2022", () => {
  const onClearMock = vi.fn();

  it("exibe índice composto e decomposição em 3 subindicadores para bairro residencial comum", () => {
    const bairroResidencial: TerritorySelection = {
      tipo: "bairro",
      id: 101,
      nome: "Pituba",
      prefeitura_bairro: "Barra/Pituba",
      populacao: 65000,
      indice_vulnerabilidade: 0.13,
      pct_esgoto_inadequado: 1.2,
      pct_agua_inadequada: 0.8,
      pct_analfabetismo_15mais: 1.5,
      is_zona_especial_nao_residencial: false,
      totalObras: 1,
      valorTotal: 12000000,
    };

    render(<TerritorySidebar territorio={bairroResidencial} onClear={onClearMock} />);

    expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Pituba");
    expect(screen.getByTestId("raio-x-vulnerabilidade")).toHaveTextContent("0,13");
    expect(screen.getByTestId("raio-x-esgoto")).toHaveTextContent("1,20%");
    expect(screen.getByTestId("raio-x-agua")).toHaveTextContent("0,80%");
    expect(screen.getByTestId("raio-x-analfabetismo")).toHaveTextContent("1,50%");
    expect(screen.queryByTestId("badge-contiguidade-territorial")).not.toBeInTheDocument();
  });

  it("exibe badge de contiguidade territorial quando vulnerabilidade_estimada_contiguidade é true", () => {
    const bairroContiguidade: TerritorySelection = {
      tipo: "bairro",
      id: 301,
      nome: "Ilha de Maré",
      prefeitura_bairro: "Subúrbio/Ilhas",
      populacao: 4236,
      indice_vulnerabilidade: 0.67,
      pct_esgoto_inadequado: 85.0,
      pct_agua_inadequada: 12.0,
      pct_analfabetismo_15mais: 9.5,
      vulnerabilidade_estimada_contiguidade: true,
      is_zona_especial_nao_residencial: false,
    };

    render(<TerritorySidebar territorio={bairroContiguidade} onClear={onClearMock} />);

    expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Ilha de Maré");
    expect(screen.getByTestId("raio-x-vulnerabilidade")).toHaveTextContent("0,67");
    expect(screen.getByTestId("badge-contiguidade-territorial")).toBeInTheDocument();
    expect(screen.getByTestId("badge-contiguidade-territorial")).toHaveTextContent(/contiguidade/i);
    expect(screen.getByTestId("raio-x-esgoto")).toHaveTextContent("85,00%");
  });

  it("exibe 'Isento' no indicador de vulnerabilidade para Zonas Especiais Não-Residenciais e omite subindicadores", () => {
    const zonaEspecial: TerritorySelection = {
      tipo: "bairro",
      id: 103,
      nome: "Aeroporto",
      prefeitura_bairro: "Itapuã/Ipitanga",
      populacao: 0,
      indice_vulnerabilidade: 0.0,
      pct_esgoto_inadequado: 0.0,
      pct_agua_inadequada: 0.0,
      pct_analfabetismo_15mais: 0.0,
      is_zona_especial_nao_residencial: true,
    };

    render(<TerritorySidebar territorio={zonaEspecial} onClear={onClearMock} />);

    expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Aeroporto");
    expect(screen.getByTestId("raio-x-vulnerabilidade")).toHaveTextContent("Isento");
    expect(screen.queryByTestId("raio-x-esgoto")).not.toBeInTheDocument();
    expect(screen.queryByTestId("raio-x-agua")).not.toBeInTheDocument();
    expect(screen.queryByTestId("raio-x-analfabetismo")).not.toBeInTheDocument();
  });

  it("exibe consolidação e nota de média ponderada para Prefeitura-Bairro", () => {
    const prefeitura: TerritorySelection = {
      tipo: "prefeitura_bairro",
      id: 2,
      nome: "Liberdade/São Caetano",
      populacao: 48000,
      indice_vulnerabilidade: 0.78,
      pct_esgoto_inadequado: 42.5,
      pct_agua_inadequada: 14.2,
      pct_analfabetismo_15mais: 8.1,
    };

    render(<TerritorySidebar territorio={prefeitura} onClear={onClearMock} />);

    expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Liberdade/São Caetano");
    expect(screen.getByTestId("raio-x-vulnerabilidade")).toHaveTextContent("0,78");
    expect(screen.getByTestId("raio-x-esgoto")).toHaveTextContent("42,50%");
    expect(screen.getByTestId("raio-x-agua")).toHaveTextContent("14,20%");
    expect(screen.getByTestId("raio-x-analfabetismo")).toHaveTextContent("8,10%");
    expect(screen.getByText(/Média ponderada pela população dos bairros componentes/i)).toBeInTheDocument();
  });

  it("renderiza o botão 'Como é calculado?' no card de vulnerabilidade e invoca o callback ao clicar", () => {
    const onOpenMock = vi.fn();
    const bairroResidencial: TerritorySelection = {
      tipo: "bairro",
      id: 101,
      nome: "Pituba",
      prefeitura_bairro: "Barra/Pituba",
      populacao: 65000,
      indice_vulnerabilidade: 0.13,
      pct_esgoto_inadequado: 1.2,
      pct_agua_inadequada: 0.8,
      pct_analfabetismo_15mais: 1.5,
    };

    render(
      <TerritorySidebar
        territorio={bairroResidencial}
        onClear={onClearMock}
        onOpenNotaMetodologica={onOpenMock}
      />
    );

    const btnComoCalculado = screen.getByTestId("btn-como-calculado-raiox");
    expect(btnComoCalculado).toBeInTheDocument();
    expect(btnComoCalculado).toHaveTextContent("Como é calculado?");

    fireEvent.click(btnComoCalculado);
    expect(onOpenMock).toHaveBeenCalledTimes(1);
  });

  it("distingue valores de contratos diretos e Frentes de Medição com acesso à Ficha Limpa da Obra", () => {
    const onSelectObraMock = vi.fn();
    const bairroComFrentes: TerritorySelection = {
      tipo: "bairro",
      id: 102,
      nome: "Boca do Rio",
      prefeitura_bairro: "Itapuã/Ipitanga",
      populacao: 45000,
      indice_vulnerabilidade: 0.35,
      valorTotal: 1000000,
      valorPago: 700000,
      valorPagoDireto: 500000,
      valorPagoFrentes: 200000,
      valorLiquidadoFrentes: 250000,
      totalObras: 2,
      totalFrentesMedicao: 1,
    };
    const obraGuardaChuva: ObraCompacta = {
      id: "obra-gc-1",
      unidadeGestora: "SEINFRA",
      numeroContrato: "2024CT007170",
      objeto: "Manutenção de Quadras e Campos - Lote 01",
      valorContratualVigente: 66000000,
      valorPago: 12000000,
      percentualExecutado: 18,
      situacao: "Em Execução",
      credor: "CONSTRUTORA BSM",
      nivel: "Escopo Cidade (Não-Localizado)",
      frentesMedicao: [
        {
          notaLiquidacao: "2025NL018688",
          nivel: "Bairro",
          bairro: "Boca do Rio",
          prefeituraBairro: "Itapuã/Ipitanga",
          valorLiquidado: 250000,
          valorPago: 200000,
          trechoComprobatorio: "REFORMA DOS CAMPOS E QUADRAS DA BOCA DO RIO",
        },
      ],
    };

    render(
      <TerritorySidebar
        territorio={bairroComFrentes}
        onClear={onClearMock}
        metricType="executado"
        obras={[obraGuardaChuva]}
        onSelectObra={onSelectObraMock}
      />
    );

    const secaoFrentes = screen.getByTestId("secao-frentes-medicao");
    expect(secaoFrentes).toBeInTheDocument();
    expect(secaoFrentes).toHaveTextContent("Contratos diretos");
    expect(secaoFrentes).toHaveTextContent("Frentes de Medição");
    expect(secaoFrentes).toHaveTextContent("2025NL018688");
    expect(secaoFrentes).toHaveTextContent("2024CT007170");

    const btnFicha = screen.getByRole("button", { name: /Ver Ficha Limpa/i });
    fireEvent.click(btnFicha);
    expect(onSelectObraMock).toHaveBeenCalledWith(obraGuardaChuva);
  });

  it("exibe aviso contextual na seção de Frentes de Medição quando metricType é 'vigente' e dispara onSwitchToExecutado ao clicar no atalho, ocultando o aviso quando metricType é 'executado'", () => {
    const onSwitchToExecutadoMock = vi.fn();
    const bairroComFrentes: TerritorySelection = {
      tipo: "bairro",
      id: 102,
      nome: "Boca do Rio",
      prefeitura_bairro: "Itapuã/Ipitanga",
      populacao: 45000,
      indice_vulnerabilidade: 0.35,
      valorTotal: 1000000,
      valorPago: 700000,
      valorPagoDireto: 500000,
      valorPagoFrentes: 200000,
      valorLiquidadoFrentes: 250000,
      totalObras: 2,
      totalFrentesMedicao: 1,
    };

    const { rerender } = render(
      <TerritorySidebar
        territorio={bairroComFrentes}
        onClear={onClearMock}
        metricType="vigente"
        onSwitchToExecutado={onSwitchToExecutadoMock}
      />
    );

    const aviso = screen.getByTestId("aviso-metrica-vigente-frentes");
    expect(aviso).toBeInTheDocument();
    expect(aviso).toHaveTextContent(/Valor Executado \/ Pago/i);

    const btnAtalho = screen.getByTestId("btn-atalho-metrica-executado");
    expect(btnAtalho).toBeInTheDocument();
    fireEvent.click(btnAtalho);
    expect(onSwitchToExecutadoMock).toHaveBeenCalledTimes(1);

    rerender(
      <TerritorySidebar
        territorio={bairroComFrentes}
        onClear={onClearMock}
        metricType="executado"
        onSwitchToExecutado={onSwitchToExecutadoMock}
      />
    );

    expect(screen.queryByTestId("aviso-metrica-vigente-frentes")).not.toBeInTheDocument();

    const bairroSemFrentes: TerritorySelection = {
      tipo: "bairro",
      id: 101,
      nome: "Pituba",
      prefeitura_bairro: "Barra/Pituba",
      populacao: 65000,
      valorTotal: 12000000,
      totalObras: 1,
      totalFrentesMedicao: 0,
      valorPagoFrentes: 0,
      valorLiquidadoFrentes: 0,
    };

    rerender(
      <TerritorySidebar
        territorio={bairroSemFrentes}
        onClear={onClearMock}
        metricType="vigente"
        onSwitchToExecutado={onSwitchToExecutadoMock}
      />
    );

    expect(screen.queryByTestId("aviso-metrica-vigente-frentes")).not.toBeInTheDocument();
  });
});

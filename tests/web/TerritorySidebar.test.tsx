import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TerritorySidebar } from "../../src/components/TerritorySidebar";
import { ObraCompacta, TerritorySelection } from "../../src/types";

describe("Seam 3: Painel Lateral Raio-X (TerritorySidebar) com Decomposição Censo 2022", () => {
  const onClearMock = vi.fn();

  it("informa a limitação e obras sem valor no território selecionado", () => {
    render(<TerritorySidebar territorio={{ tipo: "bairro", id: 1, nome: "Pituba", populacao: 100,
      valorPago: 0, valorPagoDisponivel: true, obrasSemValorPago: 1,
      limitacoesConhecidas: ["Histórico anterior a 2020 indisponível"] }} onClear={onClearMock} metricType="executado" />);
    expect(screen.getByTestId("raio-x-container")).toHaveTextContent("Soma Parcial de Pagamentos");
    expect(screen.getByTestId("raio-x-container")).toHaveTextContent("Histórico anterior a 2020 indisponível");
    expect(screen.getByTestId("raio-x-container")).toHaveTextContent("1 obra(s) sem valor de pagamento");
  });

  it("mostra pagamento das frentes como indisponível quando não há valor apurável", () => {
    const territorio: TerritorySelection = {
      tipo: "bairro", id: 101, nome: "Pituba", prefeitura_bairro: "Barra/Pituba",
      populacao: 65000, totalFrentesMedicao: 1, valorPagoFrentes: null,
      valorLiquidadoFrentes: 100, valorPagoDisponivel: false,
    };
    render(<TerritorySidebar territorio={territorio} onClear={onClearMock} metricType="executado" />);
    expect(screen.getByText("Frentes de Medição").parentElement).toHaveTextContent("Indisponível");
  });

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

  it("exibe badge de contiguidade territorial referenciando Agregados por Bairro do Censo 2022 para Aquarius e não exibe para Ilha de Maré", () => {
    const aquarius: TerritorySelection = {
      tipo: "bairro",
      id: 171,
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
      valorPago: 250000,
      valorPagoDisponivel: true,
      totalObras: 2,
      investimentoPorHabitante: null,
      investimentoPorHabitantePago: null,
    };

    const { rerender } = render(<TerritorySidebar territorio={aquarius} onClear={onClearMock} />);

    expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Aquarius");
    expect(screen.getByTestId("raio-x-vulnerabilidade")).toHaveTextContent("0,05");
    const badge = screen.getByTestId("badge-contiguidade-territorial");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent(/Agregados por Bairro do Censo 2022 do IBGE/i);
    expect(badge).not.toHaveTextContent(/N102/i);
    expect(screen.getByTestId("raio-x-esgoto")).toHaveTextContent("0,19%");

    // Per capita indisponível em estilo neutro (não R$ 0,00 / hab e não Isento)
    const perCapita = screen.getByTestId("raio-x-investimento-per-capita");
    expect(perCapita).toHaveTextContent("Per capita indisponível");
    expect(perCapita.className).toContain("text-slate-600");
    expect(perCapita).not.toHaveTextContent(/R\$\s*0,00/);

    // Ilha de Maré com dados reais do Censo 2022 não exibe badge de contiguidade
    const ilhaDeMare: TerritorySelection = {
      tipo: "bairro",
      id: 301,
      nome: "Ilha de Maré",
      prefeitura_bairro: "Subúrbio/Ilhas",
      populacao: 4036,
      indice_vulnerabilidade: 0.93,
      pct_esgoto_inadequado: 94.32,
      pct_agua_inadequada: 2.22,
      pct_analfabetismo_15mais: 14.42,
      vulnerabilidade_estimada_contiguidade: false,
      is_zona_especial_nao_residencial: false,
    };
    rerender(<TerritorySidebar territorio={ilhaDeMare} onClear={onClearMock} />);
    expect(screen.queryByTestId("badge-contiguidade-territorial")).not.toBeInTheDocument();

    // Chame-Chame com dados reais do Censo 2022 também não exibe badge de contiguidade
    const chameChame: TerritorySelection = {
      tipo: "bairro",
      id: 302,
      nome: "Chame-Chame",
      prefeitura_bairro: "Barra/Pituba",
      populacao: 2187,
      indice_vulnerabilidade: 0.04,
      pct_esgoto_inadequado: 0.1,
      pct_agua_inadequada: 0.21,
      pct_analfabetismo_15mais: 0.49,
      vulnerabilidade_estimada_contiguidade: false,
      is_zona_especial_nao_residencial: false,
    };
    rerender(<TerritorySidebar territorio={chameChame} onClear={onClearMock} />);
    expect(screen.queryByTestId("badge-contiguidade-territorial")).not.toBeInTheDocument();
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

  it("exibe alerta explicativo próprio, 'Isento' em R$ / Habitante e vulnerabilidade completa (0,48) para Centralidade Metropolitana (Comércio)", () => {
    const comercio: TerritorySelection = {
      tipo: "bairro",
      id: 102,
      nome: "Comércio",
      prefeitura_bairro: "Centro/Brotas",
      populacao: 971,
      indice_vulnerabilidade: 0.48,
      pct_esgoto_inadequado: 18.0,
      pct_agua_inadequada: 5.0,
      pct_analfabetismo_15mais: 4.5,
      is_zona_especial_nao_residencial: false,
      is_centralidade_metropolitana: true,
      valorTotal: 210690000,
      totalObras: 18,
      investimentoPorHabitante: 0,
      investimentoPorHabitantePago: 0,
    };

    render(<TerritorySidebar territorio={comercio} onClear={onClearMock} />);

    expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Comércio");
    expect(screen.queryByTestId("badge-zona-especial")).not.toBeInTheDocument();
    const badgeCentralidade = screen.getByTestId("badge-centralidade-metropolitana");
    expect(badgeCentralidade).toBeInTheDocument();
    expect(badgeCentralidade).toHaveTextContent("Centralidade Metropolitana de Baixa População Residente");

    expect(screen.getByTestId("raio-x-investimento-per-capita")).toHaveTextContent("Isento");
    expect(screen.getByTestId("raio-x-vulnerabilidade")).toHaveTextContent("0,48");
    expect(screen.getByTestId("raio-x-esgoto")).toHaveTextContent("18,00%");
    expect(screen.getByTestId("raio-x-agua")).toHaveTextContent("5,00%");
    expect(screen.getByTestId("raio-x-analfabetismo")).toHaveTextContent("4,50%");
  });

  it("renderiza como drawer flutuante no desktop com grade em 2 colunas e botão btn-recolher-raiox acessível", () => {
    const pituba: TerritorySelection = {
      tipo: "bairro",
      id: 101,
      nome: "Pituba",
      prefeitura_bairro: "Barra/Pituba",
      populacao: 65000,
      indice_vulnerabilidade: 0.12,
      valorTotal: 12000000,
      totalObras: 2,
    };

    const onToggleCollapse = vi.fn();
    const { rerender } = render(
      <TerritorySidebar
        territorio={pituba}
        onClear={onClearMock}
        isCollapsed={false}
        onToggleCollapse={onToggleCollapse}
      />
    );

    const container = screen.getByTestId("raio-x-container");
    expect(container.className).toContain("md:absolute");
    expect(container.className).toContain("md:top-14");
    expect(container.className).toContain("md:right-3");
    expect(container.className).toContain("md:bottom-3");
    expect(container.className).toContain("md:w-[340px]");
    expect(container.className).toContain("lg:w-[380px]");
    expect(container.className).toContain("md:z-[450]");
    expect(container.className).toContain("md:overflow-y-auto");

    const metricsGrid = screen.getByTestId("raio-x-metrics-grid");
    expect(metricsGrid.className).toContain("grid-cols-2");
    expect(metricsGrid.className).not.toContain("lg:grid-cols-4");

    const collapseBtn = screen.getByTestId("btn-recolher-raiox");
    expect(collapseBtn).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(collapseBtn);
    expect(onToggleCollapse).toHaveBeenCalledTimes(1);

    rerender(
      <TerritorySidebar
        territorio={pituba}
        onClear={onClearMock}
        isCollapsed={true}
        onToggleCollapse={onToggleCollapse}
      />
    );

    expect(screen.getByTestId("btn-recolher-raiox")).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByTestId("raio-x-container").className).toContain("md:bottom-auto");
    expect(screen.getByTestId("raio-x-body").className).toContain("md:hidden");
    expect(screen.getByTestId("raio-x-nome")).toHaveTextContent("Pituba");
  });
});

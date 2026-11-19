import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { FichaLimpaModal } from "../../src/components/FichaLimpaModal";
import { FichaLimpaObra } from "../../src/types";

const OBRA_COMPLETA: FichaLimpaObra = {
  id: 1002,
  cdUnidadeGestora: "2401",
  unidadeGestora: "SUCOP",
  numeroContrato: "002/2024",
  numeroContratoOriginal: "002/2024",
  nuProcesso: "2345/2023",
  objeto: "Contenção de encosta na Rua Direta da Liberdade",
  situacao: "Em Execução",
  empreiteira: {
    razaoSocial: "BAHIA ENGENHARIA S/A",
    cnpj: "98.765.432/0001-10",
    totalObras: 1,
    valorTotalContratado: 4200000,
  },
  vigencia: {
    dataInicio: "2024-03-01T00:00:00.000Z",
    dataFimOriginal: "2027-06-30T00:00:00.000Z",
    dataTerminoAtualizado: "2027-12-31T00:00:00.000Z",
  },
  dom: {
    nuDom: "8.780",
    dataPublicacao: "2024-03-01T00:00:00.000Z",
  },
  funilFinanceiro: {
    valorOriginal: 3500000,
    valorContratualVigente: 4200000,
    valorEmpenhado: 4200000,
    valorLiquidado: 1680000,
    valorPago: 1680000,
    percentualExecutado: 40,
    valorAditivos: 700000,
    deltaPercentualAditivos: 20,
  },
  aditivos: [
    {
      nuAditivo: "1º Termo Aditivo",
      dsTipoAlteracao: "Valor e Prazo",
      dsObjetoAditivo: "Reforço estrutural",
      nuDom: "8.910",
      vlAditivo: 700000,
    },
  ],
  dotacao: [
    {
      fonteRecurso: "Tesouro Municipal",
    },
  ],
  nivel: "Bairro",
  bairro: "Liberdade",
  prefeituraBairro: "Liberdade/São Caetano",
  estagioAlocacao: "Bairro",
  fontesOficiais: {
    portalTransparencia: {
      nome: "Portal da Transparência de Salvador",
      url: "https://www.transparencia.salvador.ba.gov.br/",
    },
    chaveCanonica: {
      cdUnidadeGestora: "2401",
      unidadeGestora: "SUCOP",
      nuContratoSigef: "002/2024",
    },
    nuProcesso: "2345/2023",
    domContrato: {
      nuDom: "8.780",
      url: "https://dom.salvador.ba.gov.br/",
    },
    domAditivos: [
      {
        nuAditivo: "1º Termo Aditivo",
        nuDom: "8.910",
        dtPublicacao: "2024-09-10T00:00:00.000Z",
        url: "https://dom.salvador.ba.gov.br/",
      },
    ],
    lastroTerritorial: {
      nivel: "Bairro",
      estagioAlocacao: "Bairro",
      bairro: "Liberdade",
      prefeituraBairro: "Liberdade/São Caetano",
      origem: "Alocação em Liberdade via Bairro",
    },
  },
};

const OBRA_SEM_DOM_SEM_PROCESSO: FichaLimpaObra = {
  ...OBRA_COMPLETA,
  id: 1099,
  cdUnidadeGestora: "616002",
  unidadeGestora: "SEINFRA",
  numeroContrato: "2020CT005461",
  nuProcesso: undefined,
  dom: {
    nuDom: "Não informado",
  },
  aditivos: [],
  nivel: "Escopo Cidade (Não-Localizado)",
  bairro: null,
  prefeituraBairro: null,
  estagioAlocacao: "Cache",
  fontesOficiais: {
    portalTransparencia: {
      nome: "Portal da Transparência de Salvador",
      url: "https://www.transparencia.salvador.ba.gov.br/",
    },
    chaveCanonica: {
      cdUnidadeGestora: "616002",
      unidadeGestora: "SEINFRA",
      nuContratoSigef: "2020CT005461",
    },
    nuProcesso: null,
    domContrato: {
      nuDom: null,
      url: null,
    },
    domAditivos: [],
    lastroTerritorial: {
      nivel: "Escopo Cidade (Não-Localizado)",
      estagioAlocacao: "Cache",
      bairro: null,
      prefeituraBairro: null,
      origem: "Contrato sem localização territorial específica (Cache)",
    },
  },
};

describe("Seam 2: FichaLimpaModal — Fontes Oficiais & Lastro Territorial", () => {
  it("explica valores ausentes e mantém os registros de pagamentos acessíveis", () => {
    render(<FichaLimpaModal obra={{ ...OBRA_COMPLETA, pagamentos: [
      { dataPagamento: "01/01/2025", ordemBancaria: "OB1", pago: "R$ 1.000,00" },
      { dataPagamento: "01/01/2025", pago: null },
    ], apuracaoPagamentos: { registrosSemValor: 1, situacao: "saldo_registrado" } }} onClose={vi.fn()} />);
    expect(screen.getByText(/1 registro sem valor informado/)).toBeInTheDocument();
    expect(screen.getByText(/OB1/)).toBeInTheDocument();
    expect(screen.getByText(/Valor não informado/)).toBeInTheDocument();
  });
  const writeTextMock = vi.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    writeTextMock.mockClear();
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: writeTextMock },
      configurable: true,
    });
  });

  it("exibe Fontes Oficiais & Lastro Territorial com links do Portal da Transparência, DOM do contrato e aditivos, e botões de cópia", async () => {
    render(<FichaLimpaModal obra={OBRA_COMPLETA} onClose={vi.fn()} />);

    const secao = screen.getByTestId("secao-fontes-oficiais");
    expect(secao).toBeInTheDocument();
    expect(secao).toHaveTextContent("Fontes Oficiais & Lastro Territorial");

    const portalLink = screen.getByTestId("link-portal-transparencia");
    expect(portalLink).toHaveAttribute("href", "https://www.transparencia.salvador.ba.gov.br/");
    expect(portalLink).toHaveAttribute("target", "_blank");

    const chave = screen.getByTestId("fontes-chave-canonica");
    expect(chave).toHaveTextContent("2401");
    expect(chave).toHaveTextContent("002/2024");

    const domContratoLink = screen.getByTestId("link-dom-contrato");
    expect(domContratoLink).toHaveAttribute("href", "https://dom.salvador.ba.gov.br/");
    expect(domContratoLink).toHaveTextContent("8.780");

    const domAditivoLink = screen.getByTestId("link-dom-aditivo-0");
    expect(domAditivoLink).toHaveAttribute("href", "https://dom.salvador.ba.gov.br/");
    expect(domAditivoLink).toHaveTextContent("8.910");

    expect(screen.getByTestId("fontes-lastro-territorial")).toHaveTextContent(
      "Alocação em Liberdade via Bairro"
    );

    fireEvent.click(screen.getByTestId("btn-copiar-contrato"));
    expect(writeTextMock).toHaveBeenCalledWith("002/2024");
    await waitFor(() => {
      expect(screen.getByTestId("btn-copiar-contrato")).toHaveTextContent("Copiado!");
    });

    fireEvent.click(screen.getByTestId("btn-copiar-processo"));
    expect(writeTextMock).toHaveBeenCalledWith("2345/2023");
    await waitFor(() => {
      expect(screen.getByTestId("btn-copiar-processo")).toHaveTextContent("Copiado!");
    });
  });

  it("degrada de forma limpa quando nuDom e nuProcesso estão ausentes, mantendo Chave Canônica e Portal da Transparência", () => {
    render(<FichaLimpaModal obra={OBRA_SEM_DOM_SEM_PROCESSO} onClose={vi.fn()} />);

    expect(screen.getByTestId("secao-fontes-oficiais")).toBeInTheDocument();
    expect(screen.getByTestId("link-portal-transparencia")).toHaveAttribute(
      "href",
      "https://www.transparencia.salvador.ba.gov.br/"
    );

    const chave = screen.getByTestId("fontes-chave-canonica");
    expect(chave).toHaveTextContent("616002");
    expect(chave).toHaveTextContent("2020CT005461");

    expect(screen.queryByTestId("link-dom-contrato")).not.toBeInTheDocument();
    expect(screen.queryByTestId("link-dom-aditivo-0")).not.toBeInTheDocument();
    expect(screen.queryByTestId("btn-copiar-processo")).not.toBeInTheDocument();

    expect(screen.getByTestId("fontes-nu-processo")).toHaveTextContent("Não informado");
    expect(screen.getByTestId("fontes-lastro-territorial")).toHaveTextContent(
      "Contrato sem localização territorial específica (Cache)"
    );
  });

  it("exibe justificativa, trecho comprobatório e documento de origem quando promovida por Curadoria Territorial Auditável", () => {
    const obraCurada: FichaLimpaObra = {
      ...OBRA_COMPLETA,
      id: 9100,
      nivel: "Bairro",
      bairro: "Fazenda Coutos",
      prefeituraBairro: "Subúrbio/Ilhas",
      estagioAlocacao: "Curadoria Territorial Auditável",
      fontesOficiais: {
        ...OBRA_COMPLETA.fontesOficiais!,
        lastroTerritorial: {
          nivel: "Bairro",
          estagioAlocacao: "Curadoria Territorial Auditável",
          bairro: "Fazenda Coutos",
          prefeituraBairro: "Subúrbio/Ilhas",
          origem: "Alocação em Fazenda Coutos via Curadoria Territorial Auditável",
          documentoOrigem: "dsObjetoAditivo (Aditivo Contratual)",
          trechoComprobatorio: "REFORMA DA USF FAZENDA COUTOS.II.",
          justificativa: "Aditivo contratual identifica univocamente a USF Fazenda Coutos II.",
        },
      },
    };

    render(<FichaLimpaModal obra={obraCurada} onClose={vi.fn()} />);

    expect(screen.getByTestId("fontes-lastro-documento")).toHaveTextContent(
      "dsObjetoAditivo (Aditivo Contratual)"
    );
    expect(screen.getByTestId("fontes-lastro-trecho")).toHaveTextContent(
      "REFORMA DA USF FAZENDA COUTOS.II."
    );
    expect(screen.getByTestId("fontes-lastro-justificativa")).toHaveTextContent(
      "Aditivo contratual identifica univocamente a USF Fazenda Coutos II."
    );
    expect(screen.queryByTestId("fontes-frentes-medicao")).not.toBeInTheDocument();
  });

  it("renderiza a lista auditável de Frentes de Medição no bloco Fontes Oficiais & Lastro Territorial quando frentesMedicao não está vazio", () => {
    const obraMultiFrente: FichaLimpaObra = {
      ...OBRA_SEM_DOM_SEM_PROCESSO,
      id: 9200,
      unidadeGestora: "SEINFRA",
      numeroContrato: "2024CT007170",
      objeto: "Manutenção de Quadras e Campos - Lote 01",
      estagioAlocacao: "Curadoria Territorial Auditável (Multi-Frente)",
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
        {
          notaLiquidacao: "2025NL019999",
          nivel: "Regional (Prefeitura-Bairro)",
          bairro: null,
          prefeituraBairro: "Subúrbio/Ilhas",
          valorLiquidado: 180000,
          valorPago: null,
          trechoComprobatorio: "RECUPERAÇÃO DE EQUIPAMENTOS ESPORTIVOS NO SUBÚRBIO",
        },
      ],
    };

    render(<FichaLimpaModal obra={obraMultiFrente} onClose={vi.fn()} />);

    const secaoFontes = screen.getByTestId("secao-fontes-oficiais");
    const listaFrentes = screen.getByTestId("fontes-frentes-medicao");
    expect(secaoFontes).toContainElement(listaFrentes);

    const frente0 = screen.getByTestId("fontes-frente-item-0");
    expect(frente0).toHaveTextContent("2025NL018688");
    expect(frente0).toHaveTextContent("Boca do Rio");
    expect(frente0).toHaveTextContent("250.000");
    expect(frente0).toHaveTextContent("200.000");
    expect(frente0).toHaveTextContent("REFORMA DOS CAMPOS E QUADRAS DA BOCA DO RIO");

    const frente1 = screen.getByTestId("fontes-frente-item-1");
    expect(frente1).toHaveTextContent("Pago: Indisponível");
    expect(frente1).toHaveTextContent("2025NL019999");
    expect(frente1).toHaveTextContent("Subúrbio/Ilhas");
    expect(frente1).toHaveTextContent("180.000");
    expect(frente1).toHaveTextContent("RECUPERAÇÃO DE EQUIPAMENTOS ESPORTIVOS NO SUBÚRBIO");
  });

  it("exibe o selo de Vocação da Obra explícito e com fallback conservador quando ausente", () => {
    const obraMobilidade: FichaLimpaObra = {
      ...OBRA_COMPLETA,
      vocacao: "Mobilidade Estrutural e Orlas",
    };

    const { rerender } = render(<FichaLimpaModal obra={obraMobilidade} onClose={vi.fn()} />);
    expect(screen.getByTestId("ficha-limpa-vocacao")).toHaveTextContent("Mobilidade Estrutural e Orlas");

    rerender(<FichaLimpaModal obra={OBRA_COMPLETA} onClose={vi.fn()} />);
    expect(screen.getByTestId("ficha-limpa-vocacao")).toHaveTextContent("Vizinhança e Comunidade");
  });
});

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
});

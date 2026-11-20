import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { NotaMetodologicaModal } from "../../src/components/NotaMetodologicaModal";

describe("Seam 1: Modal Nota Metodológica — Índice de Vulnerabilidade", () => {
  it("não renderiza nada quando isOpen é falso", () => {
    const onCloseMock = vi.fn();
    render(<NotaMetodologicaModal isOpen={false} onClose={onCloseMock} />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renderiza o modal completo com as 5 seções metodológicas e referências técnicas quando isOpen é true", () => {
    const onCloseMock = vi.fn();
    render(<NotaMetodologicaModal isOpen={true} onClose={onCloseMock} />);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute("aria-modal", "true");

    // Título e cabeçalho
    expect(screen.getByTestId("modal-nota-metodologica-titulo")).toHaveTextContent(
      "Nota Metodológica — Índice de Vulnerabilidade"
    );

    // 1. Referência científica: IDS (Cavallieri & Lopes / IPP) e IVS (IPEA)
    expect(screen.getByText(/Cavallieri & Lopes/i)).toBeInTheDocument();
    expect(screen.getByText(/Instituto Pereira Passos/i)).toBeInTheDocument();
    expect(screen.getAllByText(/IPEA/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Índice de Desenvolvimento Social/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Índice de Vulnerabilidade Social/i).length).toBeGreaterThanOrEqual(1);

    // 2. Variáveis dos Agregados por Bairro do Censo 2022 (IBGE) e população na Tabela SIDRA 9923
    expect(screen.getAllByText(/Agregados por Bairro/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/V00001/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/V00309–V00311/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/V00111/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/V00900–V00901/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/9923/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/PLANSAB/i).length).toBeGreaterThanOrEqual(1);

    // 3. Normalização min-max winsorizada no P95 e média simples (1/3 cada) sobre os 168 bairros residenciais
    expect(screen.getAllByText(/min-max/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/P95/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/min\(1,/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/168/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/1\/3/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/0,07/)).toBeInTheDocument();
    expect(screen.getByText(/0,08/)).toBeInTheDocument();
    expect(screen.getByText(/0,15/)).toBeInTheDocument();

    // 4. Média ponderada populacional para Prefeituras-Bairro
    expect(screen.getAllByText(/Prefeituras-Bairro/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/ponderada/i).length).toBeGreaterThanOrEqual(1);

    // 5. Exceções territoriais: Zonas Especiais (Isento) e Contiguidade exclusiva de Aquarius
    expect(screen.getAllByText(/Aeroporto/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Porto Seco Pirajá/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Centro Administrativo da Bahia/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Aquarius/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Pituba/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Itaigara/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Caminho das Árvores/i).length).toBeGreaterThanOrEqual(1);

    // Referências obsoletas do ADR-0003 não devem aparecer
    expect(screen.queryByText(/ADR-0003/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/6805/)).not.toBeInTheDocument();
    expect(screen.queryByText(/6803/)).not.toBeInTheDocument();
    expect(screen.queryByText(/9543/)).not.toBeInTheDocument();
    expect(screen.queryByText(/N102/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Colinas de Pituaçu/i)).not.toBeInTheDocument();
  });

  it("documenta Centralidade Metropolitana de Baixa População Residente (Comércio), as 3 categorias de Vocação da Obra e a referência ao ADR-0005", () => {
    render(<NotaMetodologicaModal isOpen={true} onClose={vi.fn()} />);

    expect(screen.getAllByText(/Zona Especial Não-Residencial/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Centralidade Metropolitana de Baixa População Residente/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Comércio/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/ZUE-3/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/ZCMe/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/1\.000 hab\./i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/1\.000 hab\/km²/i).length).toBeGreaterThanOrEqual(1);

    expect(screen.getAllByText(/Vocação da Obra/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Vizinhança e Comunidade/i)).toBeInTheDocument();
    expect(screen.getByText(/Mobilidade Estrutural e Orlas/i)).toBeInTheDocument();
    expect(screen.getByText(/Equipamentos e Marcos da Cidade/i)).toBeInTheDocument();

    expect(screen.getByText(/0,42/)).toBeInTheDocument();
    expect(screen.getByText(/ADR-0008/i)).toBeInTheDocument();
    expect(screen.getByText(/ADR-0005/i)).toBeInTheDocument();
  });

  it("fecha o modal ao clicar no botão fechar", () => {
    const onCloseMock = vi.fn();
    render(<NotaMetodologicaModal isOpen={true} onClose={onCloseMock} />);

    const btnFechar = screen.getByTestId("btn-fechar-nota-metodologica");
    fireEvent.click(btnFechar);

    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });

  it("fecha o modal ao pressionar a tecla Escape", () => {
    const onCloseMock = vi.fn();
    render(<NotaMetodologicaModal isOpen={true} onClose={onCloseMock} />);

    fireEvent.keyDown(window, { key: "Escape" });

    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });

  it("fecha o modal ao clicar no backdrop externo", () => {
    const onCloseMock = vi.fn();
    render(<NotaMetodologicaModal isOpen={true} onClose={onCloseMock} />);

    const dialogBackdrop = screen.getByRole("dialog");
    fireEvent.click(dialogBackdrop);

    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });
});

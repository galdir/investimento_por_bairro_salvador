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

    // 2. Variáveis do Universo Censo 2022 SIDRA nível N102 (Tabelas 6805, 6803 e 9543 com PLANSAB)
    expect(screen.getByText(/Tabela 6805/i)).toBeInTheDocument();
    expect(screen.getAllByText(/PLANSAB/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Tabela 6803/i)).toBeInTheDocument();
    expect(screen.getByText(/Tabela 9543/i)).toBeInTheDocument();
    expect(screen.getAllByText(/N102/i).length).toBeGreaterThanOrEqual(1);

    // 3. Normalização min-max e média simples (1/3 cada) sobre os 168 bairros residenciais
    expect(screen.getAllByText(/min-max/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/168/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/1\/3/i).length).toBeGreaterThanOrEqual(1);

    // 4. Média ponderada populacional para Prefeituras-Bairro
    expect(screen.getAllByText(/Prefeituras-Bairro/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/ponderada/i).length).toBeGreaterThanOrEqual(1);

    // 5. Exceções territoriais: Zonas Especiais (Isento) e Contiguidade (Chame-Chame, Colinas de Pituaçu, Ilha de Maré)
    expect(screen.getAllByText(/Aeroporto/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Porto Seco Pirajá/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Centro Administrativo da Bahia/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Chame-Chame/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Colinas de Pituaçu/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Ilha de Maré/i).length).toBeGreaterThanOrEqual(1);
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

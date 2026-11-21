import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GlossarioPage } from "../../src/components/GlossarioPage";

describe("GlossarioPage", () => {
  it("renderiza os 17 verbetes essenciais, busca por 'R$ 0' e filtra por categoria", () => {
    render(
      <GlossarioPage
        activeSlug={null}
        onBackToPanel={vi.fn()}
        onOpenNotaMetodologica={vi.fn()}
      />
    );

    expect(screen.getByRole("heading", { name: /Glossário Cidadão/i })).toBeInTheDocument();
    expect(screen.getByTestId("glossario-card-bairro-oficial")).toBeInTheDocument();
    expect(screen.getByTestId("glossario-card-mapa-de-calor-de-obras-localizadas")).toBeInTheDocument();

    // Busca por dúvida prática "R$ 0"
    const searchInput = screen.getByTestId("input-glossario-busca");
    fireEvent.change(searchInput, { target: { value: "R$ 0" } });

    expect(screen.getByTestId("glossario-card-escopo-cidade-nao-localizado")).toBeInTheDocument();
    expect(screen.queryByTestId("glossario-card-semaforo-da-obra")).not.toBeInTheDocument();

    // Limpa busca e filtra por categoria
    fireEvent.click(screen.getByTestId("btn-limpar-glossario-busca"));
    expect(screen.getByTestId("glossario-card-semaforo-da-obra")).toBeInTheDocument();

    const btnDinheiro = screen.getByRole("button", { name: "Dinheiro e Execução" });
    fireEvent.click(btnDinheiro);
    expect(btnDinheiro).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("glossario-card-funil-de-execucao-financeira")).toBeInTheDocument();
    expect(screen.queryByTestId("glossario-card-bairro-oficial")).not.toBeInTheDocument();
  });

  it("limpa filtros ativos, destaca com aria-current='true', foca e chama scrollIntoView ao receber activeSlug válido", () => {
    const scrollIntoViewMock = vi.fn();
    const originalScrollIntoView = HTMLElement.prototype.scrollIntoView;
    HTMLElement.prototype.scrollIntoView = scrollIntoViewMock;

    try {
      const { rerender } = render(
        <GlossarioPage
          activeSlug={null}
          onBackToPanel={vi.fn()}
          onOpenNotaMetodologica={vi.fn()}
        />
      );

      // Ativa busca e categoria que esconderiam "bairro-oficial"
      fireEvent.change(screen.getByTestId("input-glossario-busca"), {
        target: { value: "Funil" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Dinheiro e Execução" }));
      expect(screen.queryByTestId("glossario-card-bairro-oficial")).not.toBeInTheDocument();

      // Simula abertura via âncora #glossario-bairro-oficial
      rerender(
        <GlossarioPage
          activeSlug="bairro-oficial"
          onBackToPanel={vi.fn()}
          onOpenNotaMetodologica={vi.fn()}
        />
      );

      const targetCard = screen.getByTestId("glossario-card-bairro-oficial");
      expect(targetCard).toHaveAttribute("aria-current", "true");
      expect(targetCard).toHaveAttribute("tabindex", "-1");
      expect(document.activeElement).toBe(targetCard);
      expect(scrollIntoViewMock).toHaveBeenCalledTimes(1);
      expect(screen.getByTestId("input-glossario-busca")).toHaveValue("");
      expect(screen.getByRole("button", { name: "Todas" })).toHaveAttribute("aria-pressed", "true");
    } finally {
      HTMLElement.prototype.scrollIntoView = originalScrollIntoView;
    }
  });

  it("exibe aviso discreto para slug inexistente mantendo a lista completa acessível", () => {
    render(
      <GlossarioPage
        activeSlug="termo-que-nao-existe"
        onBackToPanel={vi.fn()}
        onOpenNotaMetodologica={vi.fn()}
      />
    );

    expect(screen.getByTestId("glossario-slug-inexistente")).toBeInTheDocument();
    expect(screen.getByTestId("glossario-card-bairro-oficial")).toBeInTheDocument();
    expect(screen.getByTestId("glossario-card-mapa-de-calor-de-obras-localizadas")).toBeInTheDocument();
  });

  it("aciona callbacks de Nota Metodológica e Voltar ao Painel", () => {
    const onBackToPanel = vi.fn();
    const onOpenNotaMetodologica = vi.fn();

    render(
      <GlossarioPage
        activeSlug={null}
        onBackToPanel={onBackToPanel}
        onOpenNotaMetodologica={onOpenNotaMetodologica}
      />
    );

    fireEvent.click(screen.getByTestId("btn-glossario-nota-metodologica"));
    expect(onOpenNotaMetodologica).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId("btn-voltar-painel"));
    expect(onBackToPanel).toHaveBeenCalledTimes(1);
  });
});

import { expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { InteractiveMap } from "../../src/components/InteractiveMap";

it("coloca território isento com saldo negativo antes do indisponível no seletor do mapa", () => {
  const geo = { type: "FeatureCollection", features: [] };
  render(<InteractiveMap activeLayer="bairros" onToggleLayer={vi.fn()} prefeituras={[]} obras={[]}
    bairrosGeoJson={geo} prefeiturasGeoJson={geo} selectedTerritory={null} onSelectTerritory={vi.fn()}
    metricType="executado" bairros={[
      { id: 1, nome: "Aeroporto", prefeitura_bairro: "", populacao: 0, is_zona_especial_nao_residencial: true, valorPago: null, valorPagoDisponivel: false },
      { id: 2, nome: "Porto Seco Pirajá", prefeitura_bairro: "", populacao: 0, is_zona_especial_nao_residencial: true, valorPago: -1, valorPagoDisponivel: true },
    ]} />);
  const negativo = screen.getByTestId("territory-selector-porto-seco-piraja");
  const indisponivel = screen.getByTestId("territory-selector-aeroporto");
  expect(negativo.compareDocumentPosition(indisponivel) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

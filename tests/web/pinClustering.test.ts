import { describe, expect, it } from "vitest";
import {
  clusterPinEntries,
  getPinCoordKey,
  projectLatLngMercator,
  type ClusterablePinEntry,
} from "../../src/utils/pinClustering";

function makeEntry(
  id: number,
  latitude: number,
  longitude: number,
  options: {
    status?: "VERDE" | "AMARELO" | "VERMELHO" | null;
    isApproximate?: boolean;
  } = {}
): ClusterablePinEntry<{ id: number; semaforo?: { status?: string } | null }> {
  return {
    key: String(id),
    latitude,
    longitude,
    isApproximate: options.isApproximate ?? false,
    semaforoStatus: options.status ?? undefined,
    payload: {
      id,
      semaforo: options.status ? { status: options.status } : null,
    },
  };
}

describe("pinClustering", () => {
  it("conserva a contagem total de entradas e agrupa pinos próximos em pixels sem depender de DOM", () => {
    // Duas obras muito próximas em Salvador (mesma quadra) e uma distante (~10km)
    const entries = [
      makeEntry(1, -12.9714, -38.5014, { status: "VERDE" }),
      makeEntry(2, -12.9715, -38.5015, { status: "VERMELHO" }),
      makeEntry(3, -12.8800, -38.4100, { status: "AMARELO" }),
    ];

    const clusters = clusterPinEntries(entries, { zoom: 12, maxZoom: 19 });

    const totalCount = clusters.reduce((sum, c) => sum + c.entries.length, 0);
    expect(totalCount).toBe(3);
    expect(clusters).toHaveLength(2);

    const grouped = clusters.find((c) => c.entries.length === 2)!;
    expect(grouped).toBeDefined();
    expect(grouped.latitude).toBeCloseTo((-12.9714 + -12.9715) / 2, 6);
    expect(grouped.longitude).toBeCloseTo((-38.5014 + -38.5015) / 2, 6);
    expect(grouped.isIndivisible).toBe(false);
    expect(grouped.sharesSameCoordKey).toBe(false);
  });

  it("aceita função de projeção injetável e separa pinos próximos quando o zoom aumenta", () => {
    const entries = [
      makeEntry(1, -12.9700, -38.5000),
      makeEntry(2, -12.9720, -38.5020),
    ];

    // Projeção linear simples escalada por 2^zoom para testar separação determinística
    const linearProject = (lat: number, lng: number, zoom: number) => ({
      x: lng * 1000 * Math.pow(2, zoom - 10),
      y: lat * 1000 * Math.pow(2, zoom - 10),
    });

    const lowZoom = clusterPinEntries(entries, {
      zoom: 10,
      maxZoom: 19,
      radiusPx: 40,
      project: linearProject,
    });
    expect(lowZoom).toHaveLength(1);
    expect(lowZoom[0].entries).toHaveLength(2);

    const highZoom = clusterPinEntries(entries, {
      zoom: 15,
      maxZoom: 19,
      radiusPx: 40,
      project: linearProject,
    });
    expect(highZoom).toHaveLength(2);
    expect(highZoom.every((c) => c.entries.length === 1)).toBe(true);
  });

  it("usa fallback finito maxZoom = 19 quando maxZoom for Infinity e marca isIndivisible em zoom >= maxZoom", () => {
    const entries = [
      makeEntry(1, -12.97000, -38.50000),
      makeEntry(2, -12.97006, -38.50006),
    ];

    const atZoom18 = clusterPinEntries(entries, { zoom: 18, maxZoom: Infinity });
    expect(atZoom18).toHaveLength(1);
    expect(atZoom18[0].isIndivisible).toBe(false);

    const atZoom19 = clusterPinEntries(entries, { zoom: 19, maxZoom: Infinity });
    expect(atZoom19).toHaveLength(1);
    expect(atZoom19[0].isIndivisible).toBe(true);
  });

  it("marca isIndivisible e sharesSameCoordKey quando todas as entradas compartilham chave de 4 casas decimais", () => {
    const entries = [
      makeEntry(1, -12.99651, -38.45521, { isApproximate: false }),
      makeEntry(2, -12.99654, -38.45524, { isApproximate: true }),
    ];

    expect(getPinCoordKey(entries[0].latitude, entries[0].longitude)).toBe(
      getPinCoordKey(entries[1].latitude, entries[1].longitude)
    );

    const clusters = clusterPinEntries(entries, { zoom: 11, maxZoom: 19 });
    expect(clusters).toHaveLength(1);
    expect(clusters[0].isIndivisible).toBe(true);
    expect(clusters[0].sharesSameCoordKey).toBe(true);
    expect(clusters[0].hasApproximate).toBe(true);
    expect(clusters[0].isAllApproximate).toBe(false);
  });

  it("calcula isAllApproximate, hasApproximate e contagem do Semáforo com fallback VERDE fechando o total", () => {
    const entries = [
      makeEntry(1, -12.9700, -38.5000, { status: "VERMELHO", isApproximate: true }),
      makeEntry(2, -12.9700, -38.5000, { status: "AMARELO", isApproximate: true }),
      makeEntry(3, -12.9700, -38.5000, { status: null, isApproximate: true }),
      makeEntry(4, -12.9700, -38.5000, { status: "VERDE", isApproximate: true }),
    ];

    const clusters = clusterPinEntries(entries, { zoom: 11, maxZoom: 19 });
    expect(clusters).toHaveLength(1);
    const cluster = clusters[0];
    expect(cluster.isAllApproximate).toBe(true);
    expect(cluster.hasApproximate).toBe(true);
    expect(cluster.semaforoCounts).toEqual({
      VERDE: 2,
      AMARELO: 1,
      VERMELHO: 1,
    });
    expect(
      cluster.semaforoCounts.VERDE +
        cluster.semaforoCounts.AMARELO +
        cluster.semaforoCounts.VERMELHO
    ).toBe(cluster.entries.length);
  });

  it("projeção Mercator padrão retorna coordenadas finitas crescentes em longitude", () => {
    const p1 = projectLatLngMercator(-12.97, -38.51, 12);
    const p2 = projectLatLngMercator(-12.97, -38.50, 12);
    expect(Number.isFinite(p1.x)).toBe(true);
    expect(Number.isFinite(p1.y)).toBe(true);
    expect(p2.x).toBeGreaterThan(p1.x);
  });
});

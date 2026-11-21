import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { GLOSSARIO_CATEGORIAS, GLOSSARIO_VERBETES } from "../../src/data/glossario";

const ESSENTIAL_TITLES = [
  "Bairro Oficial",
  "Prefeitura-Bairro",
  "Zona Especial Não-Residencial",
  "Centralidade Metropolitana de Baixa População Residente",
  "Nível de Alocação Territorial",
  "Escopo Cidade (Não-Localizado)",
  "Frente de Medição",
  "Cota-Parte de Lista Fechada Contratual",
  "Vocação da Obra",
  "Semáforo da Obra",
  "Funil de Execução Financeira",
  "Valor Contratual Vigente",
  "Valor Pago Acumulado do Contrato",
  "Soma Parcial de Pagamentos",
  "Investimento por Habitante",
  "Índice de Vulnerabilidade do Bairro",
  "Mapa de Calor de Obras Localizadas",
] as const;

function parseContextGlossary(markdown: string): {
  canonicalTerms: Set<string>;
  avoidTerms: Set<string>;
} {
  const canonicalTerms = new Set<string>();
  const avoidTerms = new Set<string>();

  for (const line of markdown.split(/\r?\n/)) {
    const canonicalMatch = line.match(/^\*\*([^*]+)\*\*:/);
    if (canonicalMatch) {
      canonicalTerms.add(canonicalMatch[1].trim());
    }

    const sublevelMatch = line.match(/^- \*\*([^*]+)\*\*:/);
    if (sublevelMatch) {
      canonicalTerms.add(sublevelMatch[1].trim());
    }

    const avoidMatch = line.match(/^_Avoid_:\s*(.+)$/);
    if (avoidMatch) {
      for (const term of avoidMatch[1].split(",")) {
        const cleaned = term.trim().toLowerCase();
        if (cleaned) {
          avoidTerms.add(cleaned);
        }
      }
    }
  }

  return { canonicalTerms, avoidTerms };
}

describe("Contrato do Glossário Cidadão com CONTEXT.md", () => {
  const contextPath = path.resolve(process.cwd(), "CONTEXT.md");
  const contextMarkdown = fs.readFileSync(contextPath, "utf-8");
  const { canonicalTerms, avoidTerms } = parseContextGlossary(contextMarkdown);

  it("cobre todos os 17 verbetes essenciais organizados nas 4 categorias esperadas", () => {
    expect(GLOSSARIO_CATEGORIAS).toEqual([
      "Território",
      "Obras e Localização",
      "Dinheiro e Execução",
      "Mapa e Indicadores",
    ]);

    const titles = GLOSSARIO_VERBETES.map((v) => v.titulo);
    for (const essential of ESSENTIAL_TITLES) {
      expect(titles).toContain(essential);
    }
  });

  it("garante que cada título de verbete corresponde a um termo canônico de CONTEXT.md", () => {
    for (const verbete of GLOSSARIO_VERBETES) {
      expect(canonicalTerms.has(verbete.titulo)).toBe(true);
    }
  });

  it("garante que nenhum título de verbete utiliza termos listados em _Avoid_ de CONTEXT.md", () => {
    for (const verbete of GLOSSARIO_VERBETES) {
      const normalizedTitle = verbete.titulo.trim().toLowerCase();
      expect(avoidTerms.has(normalizedTitle)).toBe(false);
    }
  });

  it("garante slugs únicos, campos obrigatórios preenchidos e palavras-chave práticas", () => {
    const slugs = new Set<string>();
    for (const verbete of GLOSSARIO_VERBETES) {
      expect(verbete.slug).toMatch(/^[a-z0-9-]+$/);
      expect(slugs.has(verbete.slug)).toBe(false);
      slugs.add(verbete.slug);

      expect(verbete.resumo.trim().length).toBeGreaterThan(10);
      expect(verbete.explicacao.trim().length).toBeGreaterThan(20);
      expect(verbete.exemploSalvador.trim().length).toBeGreaterThan(15);
      expect(verbete.palavrasChave.length).toBeGreaterThanOrEqual(2);
    }

    const hasZeroReaisKeyword = GLOSSARIO_VERBETES.some((v) =>
      v.palavrasChave.some((kw) => kw.toLowerCase().includes("r$ 0"))
    );
    expect(hasZeroReaisKeyword).toBe(true);
  });
});

# Backlog de Ideias

Registro versionado de ideias e evoluções futuras para o painel **Mapa das Obras e do Dinheiro por Bairro (Salvador)**.

Quando uma ideia deste backlog for priorizada para especificação e implementação, ela segue o fluxo local de especificação e tickets em `.scratch/<feature-slug>/` (conforme `docs/agents/issue-tracker.md` e `docs/agents/triage-labels.md`).

---

## Ideias registradas

### 1. Valor do m² imobiliário (Índice FipeZap e afins) e valor venal por Bairro Oficial

- **Status:** `needs-triage`
- **Resumo:** Incorporar indicadores de valor do m² por **Bairro Oficial** em duas dimensões complementares:
  1. **Valor de mercado / imobiliário (`R$/m²`):** referências como Índice FipeZap e fontes afins.
  2. **Valor venal (`R$/m²`):** base fiscal municipal (ex.: Planta Genérica de Valores — PGV / IPTU / ITIV da SEFAZ Salvador).
- **Motivação (controle social e Comparação Territorial):**
  - Cruzar o valor imobiliário e venal do m² com o **Investimento por Habitante** e o **Índice de Vulnerabilidade do Bairro** para investigar como os recursos públicos municipais se distribuem frente à valorização imobiliária da cidade.
  - Permitir leitura comparativa entre valor venal (base tributária) e valor de mercado por território.
- **Pontos em aberto para triagem e futura especificação:**
  - **Fontes e licenciamento:** mapear fontes abertas/reprodutíveis para o pipeline ETL estático (sem servidor), verificando termos de uso (especialmente no caso de índices privados como FipeZap vs. bases públicas como PGV/ITIV/SEFAZ).
  - **Cobertura e compatibilidade territorial:** índices de mercado frequentemente cobrem apenas um subconjunto de bairros ou usam nomes informais; definir como reconciliar com os 170 **Bairros Oficiais** (Decreto nº 32.791/2020) sem imputação opaca para bairros sem amostra.
  - **Recorte temporal e métrica:** definir ano/mês de referência, distinção entre preço de oferta, transação (ITIV) e valor venal (IPTU/PGV), além de eventual agregação ponderada para **Prefeitura-Bairro**.
  - **Uso no painel:** definir se entra como camada coroplética alternativa, coluna/indicador na **Comparação Territorial** ou atributo informativo no detalhamento do **Bairro Oficial**.

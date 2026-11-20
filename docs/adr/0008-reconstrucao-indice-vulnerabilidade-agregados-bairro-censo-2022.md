# Reconstrução do Índice de Vulnerabilidade a partir dos Agregados por Bairro do Censo 2022 (IBGE) e Normalização P95 Winsorizada

Status: aceita. Substitui [ADR-0003](./0003-indice-vulnerabilidade-composto-censo-2022.md).

O **Índice de Vulnerabilidade do Bairro** (`0,00` a `1,00`) passa a ser reconstruído integralmente a partir dos arquivos oficiais de **Agregados por Bairro do Universo do Censo Demográfico 2022 (IBGE — FTP `Agregados_por_Bairro_csv`)**, substituindo as referências às tabelas SIDRA `6805`, `6803` e `9543` (que na API SIDRA só existem até o nível `N6` — Município, não possuindo nível `N102` — Bairro).

Os três sub-indicadores oficiais por Bairro Oficial são apurados diretamente das variáveis do dicionário oficial do Censo 2022:
1. **Déficit de Esgotamento Sanitário Adequado (`pct_esgoto_inadequado`, critério PLANSAB):** $100\% \times \left(1 - \frac{\text{V00309} + \text{V00310} + \text{V00311}}{\text{V00001}}\right)$ (`caracteristicas_domicilio1` e `caracteristicas_domicilio2`).
2. **Déficit de Abastecimento de Água por Rede Geral (`pct_agua_inadequada`):** $100\% \times \left(1 - \frac{\text{V00111}}{\text{V00001}}\right)$ (`caracteristicas_domicilio1` e `caracteristicas_domicilio2`).
3. **Taxa de Analfabetismo de 15 anos ou mais (`pct_analfabetismo_15mais`):** $100\% \times \frac{\text{V00901}}{\text{V00900} + \text{V00901}}$ (`alfabetizacao`).

Para normalizar as três dimensões sobre os 168 **Bairros Oficiais** residenciais sem que *outliers* extremos reais (*Ilha de Maré* com `94,32%` de déficit de esgoto e `14,42%` de analfabetismo; *Cassange* com `37,45%` de déficit de água) comprimam mais de 95% dos bairros continentais abaixo de `0,25`, cada dimensão $k$ adota **normalização *min-max* winsorizada no percentil 95 (P95)** com teto em `1,00`:
$$I_{k,b} = \min\!\left(1,\; \frac{x_{k,b} - \min(x_k)}{P_{95}(x_k) - \min(x_k)}\right)$$
O índice composto permanece como a média aritmética simples (pesos iguais $\frac{1}{3}$) arredondada em 2 casas decimais, e a consolidação nas **Prefeituras-Bairro** permanece como a média ponderada populacional dos seus bairros residenciais constituintes.

A imputação espacial por contiguidade fica restrita **exclusivamente ao bairro `Aquarius`** (único dos 171 Bairros Oficiais ausente na malha de bairros do IBGE 2022), utilizando a média ponderada populacional dos seus vizinhos limítrofes (`Pituba`, `Itaigara` e `Caminho das Árvores`), sem inventar população residente (`populacao = 0`, mantendo `Investimento por Habitante` indisponível por ausência de recorte populacional próprio no Censo 2022). `Ilha de Maré`, `Chame-Chame` e `Colinas de Periperi` passam a utilizar seus dados reais do Censo 2022, e `IAPI` e `STIEP` passam a constar integralmente na base de referência.

## Opções Consideradas

- **Manter *min-max* linear puro sobre os dados reais (sem winsorização):** Rejeitado porque os dois *outliers* reais (*Ilha de Maré* e *Cassange*) esmagam quase toda a cidade abaixo de `0,25` no mapa coroplético e fazem bairros residenciais (*Horto Florestal* e *Itaigara*) arredondarem para `0,00`.
- ***Rank* percentil puro (`0,01` a `1,00`):** Rejeitado porque descarta a proporcionalidade entre taxas reais de carência e mede apenas posição ordinal.
- **Baixar os ZIPs nacionais (~18 MB) do FTP do IBGE em toda execução do ETL:** Rejeitado por latência e dependência de rede em CI sobre um censo decenal estático; optou-se por versionar `etl/reference/censo_2022_salvador_bairros.json` junto de um script reprodutível (`scripts/extrair_censo_2022_bairros.py`).

## Consequências

- **Blindagem contra lacunas silenciosas no ETL:** Qualquer Bairro Oficial residencial que não esteja na lista explícita de contiguidade (`Aquarius`) e esteja ausente ou com sub-indicador nulo na base de referência do Censo 2022 deve disparar `ValueError`, impedindo regressões como a ausência silenciosa de `IAPI` e `STIEP` convertida para `0,0`.
- **Reprodutibilidade e rastreabilidade:** O arquivo `etl/reference/censo_2022_salvador_bairros.json` passa a ser gerado por `scripts/extrair_censo_2022_bairros.py` diretamente dos CSVs oficiais do IBGE, e a `NotaMetodologicaModal` e o `README.md` refletem exatamente essas fontes, variáveis, a winsorização no P95 e a regra exclusiva de contiguidade de `Aquarius`.
- **Zonas Especiais Não-Residenciais preservadas:** `Aeroporto`, `Porto Seco Pirajá` e `Centro Administrativo da Bahia - CAB` continuam excluídas do domínio de normalização (e exibidas como `"Isento"` na interface).

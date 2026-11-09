# Índice de Vulnerabilidade Composto por Bairro a partir do Universo do Censo 2022 (IBGE/SIDRA)

O **Índice de Vulnerabilidade do Bairro** deixa de ser atribuído por um dicionário manual estático e passa a ser calculado de forma determinística e auditável na escala `0,00` a `1,00` pela combinação de três dimensões do Universo do Censo Demográfico 2022 do IBGE no nível territorial de Bairro (`N102` no SIDRA), fundamentada no Índice de Desenvolvimento Social (IDS — Cavallieri & Lopes / IPP) e nas dimensões de Infraestrutura Urbana e Capital Humano do Índice de Vulnerabilidade Social (IVS — IPEA): (1) déficit de esgotamento sanitário adequado (Tabela 6805), (2) déficit de abastecimento de água por rede geral (Tabela 6803) e (3) taxa de analfabetismo de pessoas de 15 anos ou mais (Tabela 9543), normalizadas via *min-max* entre os Bairros Oficiais residenciais de Salvador e consolidadas por média aritmética simples (e por média ponderada populacional nas Prefeituras-Bairro).

## Opções Consideradas

- **Dicionário manual por faixas socioeconômicas (`VULNERABILIDADE_BAIRROS` com fallback `0,50`)**: Rejeitado por carecer de lastro estatístico oficial auditável e colapsar dezenas de bairros não listados em `0,50`.
- **Microdados amostrais do Censo (renda domiciliar per capita)**: Rejeitado porque os resultados da Amostra por bairro oficial de Salvador possuem defasagem de liberação e restrições de sigilo estatístico em recortes pequenos, enquanto as variáveis de saneamento e alfabetização pertencem ao questionário básico do Universo (100% dos domicílios recenseados em 2022).
- **Indicador único isolado (apenas esgotamento sanitário)**: Rejeitado porque bairros de ocupação verticalizada antiga ou áreas litorâneas de alta renda com fossa séptica isolada distorceriam uma métrica unidimensional sem o contrapeso de abastecimento de água e capital humano (alfabetização).

## Consequências

- **Decomposição Transparente nos Artefatos (`public/data/`)**: Além do `indice_vulnerabilidade` consolidado (`0,00` a `1,00`), cada Bairro Oficial e Prefeitura-Bairro passa a expor os três sub-indicadores brutos (`pct_esgoto_inadequado`, `pct_agua_inadequada`, `pct_analfabetismo_15mais`) para auditoria cidadã no painel lateral (Raio-X).
- **Imputação Espacial Explícita para os 3 Bairros Ausentes no `N102` do SIDRA**: Os três Bairros Oficiais residenciais do Decreto nº 32.791/2020 que não possuem linha individual na malha `N102` do IBGE (`Chame-Chame`, `Colinas de Pituaçu` e `Ilha de Maré`) têm seus sub-indicadores calculados pela média ponderada populacional dos bairros limítrofes de sua mesma zona homogênea no Censo 2022, com regra documentada na Nota Metodológica.
- **Zonas Especiais Não-Residenciais**: `Aeroporto`, `Porto Seco Pirajá` e `Centro Administrativo da Bahia - CAB` permanecem isentos do cálculo e dos rankings de vulnerabilidade para não introduzir extremos artificiais na normalização *min-max*.


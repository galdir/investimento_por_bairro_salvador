# Relatório de Exploração Estatística Agnóstica (EDA) — Obras Públicas de Salvador

> Execução 100% offline e determinística sobre o acervo local reconciliado, separando variáveis brutas das fontes oficiais (Seções 1–4) da auditoria empírica das variáveis derivadas de domínio (Seção 5).

## Seção 1: Radiografia e Qualidade da Base

### 1.1 Volumetria nas Quatro Granularidades

| Granularidade | Entidade / Recorte | Quantidade |
|---|---|---:|
| Território | Bairros Oficiais no índice | 171 (168 residenciais + 3 Zonas Especiais Não-Residenciais) |
| Território | Prefeituras-Bairro | 10 |
| Território | Chaves no catálogo Censo 2022 | 338 |
| Contrato | Obras Públicas no índice / fichas individuais | 633 / 633 |
| Transação/Evento | Notas de Empenho | 4344 transações em 280 obras |
| Transação/Evento | Notas de Liquidação | 4735 transações em 269 obras |
| Transação/Evento | Ordens Bancárias / Pagamentos | 6202 transações em 268 obras |
| Transação/Evento | Aditivos Contratuais formais listados | 664 termos em 192 obras |
| Transação/Evento | Dotações Orçamentárias | 651 registros em 633 obras |
| Empreiteira | Empreiteiras unificadas | 244 (122 com CNPJ válido) |

### 1.2 Completude e Qualidade dos Campos

| Granularidade | Campo | Preenchidos | Nulos/Vazios | Zeros | % Preenchido | % Zeros |
|---|---|---:|---:|---:|---:|---:|
| Território (Bairro) | `populacao` | 171 | 0 | 2 | 100,00% | 1,17% |
| Território (Bairro) | `pct_esgoto_inadequado` | 171 | 0 | 5 | 100,00% | 2,92% |
| Território (Bairro) | `valorTotal` | 171 | 0 | 90 | 100,00% | 52,63% |
| Território (Bairro) | `totalObras` | 171 | 0 | 90 | 100,00% | 52,63% |
| Contrato (Obra) | `objeto` | 633 | 0 | 0 | 100,00% | 0,00% |
| Contrato (Obra) | `unidadeGestora` | 633 | 0 | 0 | 100,00% | 0,00% |
| Contrato (Obra) | `situacao` | 633 | 0 | 0 | 100,00% | 0,00% |
| Contrato (Obra) | `credor` | 633 | 0 | 0 | 100,00% | 0,00% |
| Contrato (Obra) | `cnpj` | 454 | 179 | 0 | 71,72% | 0,00% |
| Contrato (Obra) | `dtInicioVigencia` | 633 | 0 | 0 | 100,00% | 0,00% |
| Contrato (Obra) | `valorOriginal` | 633 | 0 | 0 | 100,00% | 0,00% |
| Contrato (Obra) | `valorAditivos` | 633 | 0 | 237 | 100,00% | 37,44% |
| Contrato (Obra) | `percentualExecutado` | 633 | 0 | 65 | 100,00% | 10,27% |
| Contrato (Obra) | `bairro` | 241 | 392 | 0 | 38,07% | 0,00% |
| Contrato (Obra) | `prefeituraBairro` | 287 | 346 | 0 | 45,34% | 0,00% |
| Contrato (Obra) | `latitude` | 241 | 392 | 0 | 38,07% | 0,00% |
| Transação (Empenho) | `dataEmpenho` | 4344 | 0 | 0 | 100,00% | 0,00% |
| Transação (Empenho) | `valEmpenhado` | 4344 | 0 | 36 | 100,00% | 0,83% |
| Transação (Empenho) | `fonteRecurso` | 4344 | 0 | 0 | 100,00% | 0,00% |
| Transação (Pagamento) | `dataPagamento` | 6202 | 0 | 0 | 100,00% | 0,00% |
| Transação (Pagamento) | `pago` | 6202 | 0 | 0 | 100,00% | 0,00% |
| Transação (Pagamento) | `ordBancaria` | 6202 | 0 | 0 | 100,00% | 0,00% |
| Transação (Aditivo) | `dtAssinatura` | 664 | 0 | 0 | 100,00% | 0,00% |
| Transação (Aditivo) | `vlAditivo` | 664 | 0 | 243 | 100,00% | 36,60% |
| Transação (Aditivo) | `dsTipoAlteracao` | 664 | 0 | 0 | 100,00% | 0,00% |
| Empreiteira | `cnpj` | 122 | 122 | 0 | 50,00% | 0,00% |
| Empreiteira | `razaoSocial` | 244 | 0 | 0 | 100,00% | 0,00% |
| Empreiteira | `totalObras` | 244 | 0 | 0 | 100,00% | 0,00% |
| Empreiteira | `valorTotalContratado` | 244 | 0 | 0 | 100,00% | 0,00% |
| Contrato (Ficha) | `dom.nuDom` | 233 | 400 | 0 | 36,81% | 0,00% |

- Contratos com CNPJ válido de 14 dígitos: **452/633** (71,41%).
- Lacuna de detalhamento contábil: **353** obras (55,77%) não possuem notas de empenho detalhadas na API; **365** obras (57,66%) não possuem ordens de pagamento reais (utilizando fallback por medição física apenas na visão do painel).

### 1.3 Auditoria Aritmética: Variação Contratual Acumulada vs. Aditivos Contratuais Formais

- Divergências aritméticas (`|valorOriginal + valorAditivos - valorContratualVigente| > R$ 1,00`): **9** contratos.
- **Variação Contratual Acumulada** total (`valorContratualVigente - valorOriginal`): **R$ 3.898.698.731,28**.
- Soma de **Aditivos Contratuais** formais listados (`sum(vlAditivo)`): **R$ 3.011.776.849,99**.
- Diferença (apostilamentos, reajustes de saldo ou aditivos não listados individualmente): **R$ 886.921.881,29**.
- Contratos com variação financeira positiva sem nenhum aditivo formal listado: **233**; contratos com diferença > R$ 1,00 entre variação acumulada e soma dos aditivos listados: **252**.

## Seção 2: Distribuições Univariadas das Variáveis Brutas

### 2.1 Variáveis Brutas do Censo 2022 (Bairros Oficiais Residenciais, N=168)

| Variável | N | Média | Desvio-Padrão | Mín | P10 | P25 | Mediana (P50) | P75 | P90 | P99 | Máx | IQR | Assimetria |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| População residente (Censo 2022) | 328 | 14.500,10 | 11.787,43 | 0,00 | 3.038,00 | 6.093,25 | 11.441,50 | 18.946,50 | 29.664,00 | 56.454,90 | 60.968,00 | 12.853,25 | 1,63 |
| % Esgoto inadequado | 328 | 25,17 | 9,82 | 2,95 | 11,87 | 22,12 | 22,12 | 34,93 | 38,65 | 43,10 | 43,74 | 12,81 | -0,01 |
| % Água inadequada | 328 | 3,35 | 1,43 | 0,37 | 1,43 | 2,85 | 2,85 | 4,78 | 5,37 | 6,08 | 6,18 | 1,93 | 0,18 |
| % Analfabetismo (15+ anos) | 328 | 4,97 | 1,47 | 1,16 | 2,96 | 4,60 | 4,60 | 6,40 | 6,90 | 7,47 | 7,55 | 1,80 | -0,34 |

### 2.2 Variáveis Brutas dos Contratos (N=633)

| Variável | N | Média | Desvio-Padrão | Mín | P10 | P25 | Mediana (P50) | P75 | P90 | P99 | Máx | IQR | Assimetria |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Valor Original Contratado | 633 | R$ 9.618.505,34 | R$ 21.770.381,43 | R$ 7.875,00 | R$ 98.014,97 | R$ 472.190,58 | R$ 2.783.070,46 | R$ 9.563.865,78 | R$ 21.605.983,55 | R$ 76.837.060,42 | R$ 212.781.070,50 | R$ 9.091.675,20 | 5,74 |
| Valor Contratual Vigente | 633 | R$ 15.768.249,22 | R$ 39.135.170,82 | R$ 7.875,00 | R$ 110.000,00 | R$ 542.841,40 | R$ 3.760.000,00 | R$ 12.419.649,04 | R$ 35.118.541,41 | R$ 245.618.160,61 | R$ 330.463.204,24 | R$ 11.876.807,64 | 5,12 |
| Variação Contratual Acumulada | 633 | R$ 6.159.081,72 | R$ 25.051.658,99 | R$ 0,00 | R$ 0,00 | R$ 0,00 | R$ 139.852,56 | R$ 1.547.316,14 | R$ 11.657.631,25 | R$ 128.499.211,06 | R$ 255.154.070,54 | R$ 1.547.316,14 | 7,15 |
| % Execução Física (fonte oficial) | 633 | 69,48 | 36,65 | 0,00 | 0,00 | 42,23 | 90,49 | 94,50 | 98,96 | 110,63 | 179,83 | 52,27 | -0,84 |
| Prazo Original (dias) | 233 | 369,85 | 139,86 | 59,00 | 179,00 | 359,00 | 364,00 | 366,00 | 549,00 | 729,68 | 789,00 | 7,00 | 0,64 |
| Prazo Atualizado (dias) | 233 | 973,72 | 2.206,83 | 89,00 | 359,00 | 419,00 | 731,00 | 1.095,00 | 1.486,40 | 2.007,40 | 33.719,00 | 676,00 | 14,20 |
| Qtd. Aditivos Formais por Contrato | 633 | 1,05 | 2,01 | 0,00 | 0,00 | 0,00 | 0,00 | 1,00 | 4,00 | 8,00 | 13,00 | 1,00 | 2,31 |

### 2.3 Funil de Execução Financeira (Subamostra Contábil Verificada — Sem Fallbacks Sintéticos)

- Obras com empenhos reais: **N = 280** (Total: **R$ 2.523.189.466,70**)
- Obras com liquidações reais: **N = 269** (Total: **R$ 1.949.817.856,37**)
- Obras com pagamentos reais: **N = 268** (Total: **R$ 746.324.479,49**)

| Variável | N | Média | Desvio-Padrão | Mín | P10 | P25 | Mediana (P50) | P75 | P90 | P99 | Máx | IQR | Assimetria |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Valor Empenhado Real (subamostra com notas) | 280 | R$ 9.011.390,95 | R$ 15.915.265,45 | -R$ 1.408,85 | R$ 59.985,77 | R$ 321.315,31 | R$ 3.900.563,01 | R$ 12.004.212,93 | R$ 20.833.041,09 | R$ 91.762.837,00 | R$ 138.772.529,49 | R$ 11.682.897,61 | 4,41 |
| Valor Liquidado Real (subamostra com notas) | 269 | R$ 7.248.393,52 | R$ 10.989.335,38 | R$ 3.000,00 | R$ 89.382,10 | R$ 448.908,64 | R$ 3.512.774,59 | R$ 9.657.590,98 | R$ 17.813.629,44 | R$ 55.975.251,13 | R$ 97.394.841,67 | R$ 9.208.682,34 | 3,81 |
| Valor Pago Real (subamostra com ordens) | 268 | R$ 2.784.792,83 | R$ 5.619.724,12 | R$ 3.000,00 | R$ 70.226,61 | R$ 242.439,57 | R$ 1.086.138,38 | R$ 3.529.409,59 | R$ 6.447.209,20 | R$ 18.395.843,74 | R$ 73.959.110,58 | R$ 3.286.970,02 | 8,27 |
| Transação Individual: Empenho | 4344 | R$ 580.844,72 | R$ 1.689.476,95 | -R$ 14.893.491,00 | -R$ 96.634,07 | R$ 0,00 | R$ 155.567,03 | R$ 660.000,00 | R$ 1.653.500,00 | R$ 8.229.032,19 | R$ 27.000.000,00 | R$ 660.000,00 | 4,03 |
| Transação Individual: Liquidação | 4735 | R$ 411.788,35 | R$ 869.922,68 | -R$ 4.802.067,68 | R$ 800,00 | R$ 24.694,32 | R$ 157.720,00 | R$ 491.286,26 | R$ 1.128.901,77 | R$ 4.195.760,52 | R$ 10.643.317,69 | R$ 466.591,93 | 4,19 |
| Transação Individual: Pagamento | 6202 | R$ 120.336,10 | R$ 444.947,03 | -R$ 199.357,58 | -R$ 2.516,39 | R$ 1.672,52 | R$ 10.819,58 | R$ 51.435,85 | R$ 262.080,28 | R$ 1.979.247,35 | R$ 10.643.317,69 | R$ 49.763,33 | 9,26 |
| Transação Individual: Aditivo Formal | 664 | R$ 4.535.808,51 | R$ 13.428.187,46 | R$ 0,00 | R$ 0,00 | R$ 0,00 | R$ 170.085,16 | R$ 2.316.822,17 | R$ 11.070.328,18 | R$ 80.511.410,86 | R$ 106.259.419,15 | R$ 2.316.822,17 | 4,61 |

### 2.4 Empreiteiras e Concentração de Mercado (N=244)

| Variável | N | Média | Desvio-Padrão | Mín | P10 | P25 | Mediana (P50) | P75 | P90 | P99 | Máx | IQR | Assimetria |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Valor Contratado por Empreiteira | 244 | R$ 40.906.974,41 | R$ 105.001.829,36 | R$ 7.875,00 | R$ 98.106,00 | R$ 341.436,24 | R$ 5.619.924,22 | R$ 32.312.770,17 | R$ 88.376.960,98 | R$ 426.684.563,14 | R$ 956.027.056,42 | R$ 31.971.333,93 | 5,24 |
| Qtd. de Obras por Empreiteira | 244 | 2,59 | 3,30 | 1,00 | 1,00 | 1,00 | 1,00 | 3,00 | 5,00 | 15,00 | 29,00 | 2,00 | 3,92 |

- **Índice de Gini**: `0,8115`
- **CR1 / CR5 / CR10 / CR20**: `9,58%` / `29,57%` / `44,78%` / `64,51%`
- **HHI (Herfindahl–Hirschman Index)**: `309,9`

### 2.5 Comparação Temporal por Coortes Mutuamente Exclusivas de Mandato e Datas de Transação

| Coorte Mutuamente Exclusiva | Contratos | % Contratos | Valor Contratual Vigente |
|---|---:|---:|---:|
| 2021-2024 exclusivo | 335 | 52,92% | R$ 2.970.327.112,76 |
| 2021-2024 ∩ 2025-2028 | 195 | 30,81% | R$ 5.862.477.846,56 |
| 2025-2028 exclusivo | 103 | 16,27% | R$ 1.148.496.797,55 |

| Ano da Transação | Empenhos | Liquidações | Pagamentos | Aditivos |
|---:|---:|---:|---:|---:|
| 2016 | 7 | 17 | 30 | 0 |
| 2017 | 18 | 13 | 0 | 0 |
| 2018 | 5 | 0 | 0 | 0 |
| 2019 | 0 | 8 | 30 | 0 |
| 2020 | 7 | 38 | 30 | 2 |
| 2021 | 25 | 42 | 141 | 2 |
| 2022 | 128 | 321 | 606 | 25 |
| 2023 | 549 | 797 | 1421 | 52 |
| 2024 | 1202 | 1505 | 1770 | 195 |
| 2025 | 1212 | 1002 | 903 | 232 |
| 2026 | 1191 | 992 | 1271 | 156 |

### 2.6 Frequências de Variáveis Categóricas Brutas

#### Unidade Gestora (`unidadeGestora`)

| Categoria | Contagem | % |
|---|---:|---:|
| SEINFRA | 248 | 39,18% |
| SMED | 119 | 18,80% |
| SEMAN | 111 | 17,54% |
| SEFAZ | 50 | 7,90% |
| SMS | 30 | 4,74% |
| SEMOP | 18 | 2,84% |
| SEDUR | 15 | 2,37% |
| SEMPRE | 12 | 1,90% |
| SECULT | 11 | 1,74% |
| SEMOB | 7 | 1,11% |
| SECIS | 4 | 0,63% |
| SEMDEC | 2 | 0,32% |
| *(demais 5 categorias)* | 6 | — |

#### Situação Contratual (`situacao`)

| Categoria | Contagem | % |
|---|---:|---:|
| Em Execução | 391 | 61,77% |
| Ajustar Cronograma | 211 | 33,33% |
| Cancelado | 22 | 3,48% |
| Rescindido | 9 | 1,42% |

#### Fonte de Recurso (`dotacao.fonteRecurso`)

| Categoria | Contagem | % |
|---|---:|---:|
| Tesouro Municipal (Recursos Ordinários) | 616 | 94,62% |
| Tesouro | 30 | 4,61% |
| Receita Própria de Entidades de Administração Indireta - Sem Detalhamento | 2 | 0,31% |
| COSIP - Contribuição p/ Custeio da Iluminação Pública | 1 | 0,15% |
| Rec. de Impostos e Transferências de Impostos - Saúde | 1 | 0,15% |
| Transferência de Recursos do Sistema Único de Saúde - SUS | 1 | 0,15% |

#### Subação Orçamentária (`dotacao.subacao`)

| Categoria | Contagem | % |
|---|---:|---:|
| Infraestrutura Urbana Municipal | 616 | 94,62% |
| Manutenção dos Serviços Técnicos e Administrativos - SEFAZ | 8 | 1,23% |
| Conservar Para Não Parar - Conservação da Malha Viária | 6 | 0,92% |
| Conservação da Malha Viária | 5 | 0,77% |
| Planejar Espaço Urbano - Projetos de Requalificação de Espaços Urbanos e Equipamentos Públicos | 4 | 0,61% |
| Poda de Árvores | 3 | 0,46% |
| Elaboração de Estudos, Planos e Projetos Urbanísticos e Arquitetônicos | 2 | 0,31% |
| Elaboração de Projetos Urbanísticos da Orla e de Áreas Estratégicas de Salvador | 2 | 0,31% |
| Construção e Implantação de Novas Unidades de Saúde da Família - USF | 2 | 0,31% |
| Elaboração de Planos Urbanísticos em ZEIS | 1 | 0,15% |
| Poda Revigora - Poda de Árvores nas Áreas Públicas | 1 | 0,15% |
| Manutenção dos Serviços Técnicos e Administrativos - SEDUR | 1 | 0,15% |

#### Classificação / Elemento (`dotacao.classificacao`)

| Categoria | Contagem | % |
|---|---:|---:|
| 4.4.90.51 - Obras e Instalações | 616 | 94,62% |
| Material de Consumo | 10 | 1,54% |
| Outros Serviços de Terceiros - Pessoa Jurídica | 10 | 1,54% |
| Obras e Instalações | 7 | 1,08% |
| Serviços de Consultoria | 2 | 0,31% |
| Despesas de Exercícios Anteriores | 2 | 0,31% |
| Outros Serviços de Terceiros - Pessoa Jurídica  | 2 | 0,31% |
|  Obras e Instalações | 2 | 0,31% |

#### Tipo de Alteração de Aditivo (`dsTipoAlteracao`)

| Categoria | Contagem | % |
|---|---:|---:|
| Prorrogação de prazo | 243 | 36,60% |
| Prorrogação de prazo com acréscimo de valor | 217 | 32,68% |
| Acréscimo de Valor | 179 | 26,96% |
| Reajuste ou Repactuação de Preço | 8 | 1,20% |
| Redução de Valor | 7 | 1,05% |
| Renovação (serviço continuado) | 6 | 0,90% |
| Prorrogação de prazo com redução de valor | 2 | 0,30% |
| Redução de prazo com redução de valor | 1 | 0,15% |
| Reequilibrio Econômico - Reajuste | 1 | 0,15% |

## Seção 3: Varredura Multivariada Agnóstica

### 3.1 Correlações Todos-contra-Todos — Nível Bairro Oficial (Residenciais)

#### Bairros Oficiais — Associações Relevantes (|r| ou |ρ| ≥ 0,20): 9 pares
| Variável 1 | Variável 2 | N | Pearson (r) | Spearman (ρ) |
|---|---|---:|---:|---:|
| `pct_esgoto_inadequado` | `pct_agua_inadequada` | 168 | 0,999 | 1,000 |
| `pct_esgoto_inadequado` | `pct_analfabetismo_15mais` | 168 | 0,994 | 1,000 |
| `pct_agua_inadequada` | `pct_analfabetismo_15mais` | 168 | 0,986 | 1,000 |
| `totalObras` | `valorTotal` | 168 | 0,789 | 0,956 |
| `valorTotal` | `valorPago` | 168 | 0,623 | 0,949 |
| `totalObras` | `valorPago` | 168 | 0,781 | 0,945 |
| `populacao` | `valorPago` | 168 | 0,443 | 0,332 |
| `populacao` | `totalObras` | 168 | 0,364 | 0,354 |
| `populacao` | `valorTotal` | 168 | 0,295 | 0,343 |

#### Bairros Oficiais — Ausências de Correlação (|r| e |ρ| < 0,10): 6 pares
| Variável 1 | Variável 2 | N | Pearson (r) | Spearman (ρ) |
|---|---|---:|---:|---:|
| `pct_esgoto_inadequado` | `totalObras` | 168 | -0,013 | 0,029 |
| `pct_agua_inadequada` | `totalObras` | 168 | -0,009 | 0,029 |
| `pct_analfabetismo_15mais` | `totalObras` | 168 | -0,017 | 0,029 |
| `pct_agua_inadequada` | `valorTotal` | 168 | 0,005 | -0,002 |
| `pct_esgoto_inadequado` | `valorTotal` | 168 | 0,003 | -0,002 |
| `pct_analfabetismo_15mais` | `valorTotal` | 168 | 0,001 | -0,002 |

### 3.2 Correlações Todos-contra-Todos — Nível Obra Pública

#### Obras Públicas — Associações Relevantes (|r| ou |ρ| ≥ 0,20): 40 pares
| Variável 1 | Variável 2 | N | Pearson (r) | Spearman (ρ) |
|---|---|---:|---:|---:|
| `valorOriginal` | `valorContratualVigente` | 633 | 0,809 | 0,974 |
| `valorEmpenhadoReal` | `valorLiquidadoReal` | 265 | 0,898 | 0,962 |
| `valorContratualVigente` | `valorLiquidadoReal` | 269 | 0,596 | 0,885 |
| `valorContratualVigente` | `valorEmpenhadoReal` | 280 | 0,681 | 0,868 |
| `valorContratualVigente` | `valorAditivos` | 633 | 0,860 | 0,612 |
| `valorOriginal` | `valorLiquidadoReal` | 269 | 0,608 | 0,855 |
| `valorAditivos` | `deltaPercentualValor` | 633 | 0,364 | 0,851 |
| `valorOriginal` | `valorEmpenhadoReal` | 280 | 0,654 | 0,844 |
| `valorLiquidadoReal` | `valorPagoReal` | 267 | 0,673 | 0,759 |
| `valorEmpenhadoReal` | `valorPagoReal` | 264 | 0,509 | 0,742 |
| `valorOriginal` | `valorPagoReal` | 268 | 0,306 | 0,726 |
| `valorContratualVigente` | `valorPagoReal` | 268 | 0,227 | 0,693 |
| `valorAditivos` | `valorEmpenhadoReal` | 280 | 0,512 | 0,666 |
| `prazoAtualizado` | `qtd_aditivos` | 233 | 0,054 | 0,665 |
| `valorAditivos` | `valorLiquidadoReal` | 269 | 0,433 | 0,656 |
| `deltaPercentualValor` | `prazoAtualizado` | 233 | 0,137 | 0,652 |
| `valorAditivos` | `prazoAtualizado` | 233 | 0,056 | 0,554 |
| `valorOriginal` | `valorAditivos` | 633 | 0,394 | 0,500 |
| `qtd_aditivos` | `valorLiquidadoReal` | 269 | 0,379 | 0,435 |
| `qtd_aditivos` | `valorEmpenhadoReal` | 280 | 0,351 | 0,431 |
| `valorAditivos` | `qtd_aditivos` | 633 | 0,252 | 0,414 |
| `valorOriginal` | `prazoOriginal` | 233 | 0,360 | 0,413 |
| `valorContratualVigente` | `prazoOriginal` | 233 | 0,211 | 0,407 |
| `prazoOriginal` | `prazoAtualizado` | 233 | 0,010 | 0,370 |
| `valorAditivos` | `valorPagoReal` | 268 | 0,117 | 0,367 |

#### Obras Públicas — Ausências de Correlação (|r| e |ρ| < 0,10): 6 pares
| Variável 1 | Variável 2 | N | Pearson (r) | Spearman (ρ) |
|---|---|---:|---:|---:|
| `percentualExecutado` | `qtd_aditivos` | 633 | 0,098 | -0,049 |
| `deltaPercentualValor` | `valorPagoReal` | 268 | -0,038 | 0,089 |
| `valorOriginal` | `percentualExecutado` | 633 | -0,075 | -0,050 |
| `valorContratualVigente` | `percentualExecutado` | 633 | -0,060 | -0,055 |
| `prazoAtualizado` | `valorPagoReal` | 214 | -0,039 | -0,019 |
| `percentualExecutado` | `valorPagoReal` | 268 | 0,029 | 0,005 |

### 3.3 Poder Explicativo de Variáveis Categóricas Brutas (η²)

| Variável Categórica | Métrica Numérica | Variância Explicada (η²) |
|---|---|---:|
| `fonteRecurso` | `prazoAtualizado` | 0,9697 |
| `unidadeGestora` | `percentualExecutado` | 0,2128 |
| `situacao` | `percentualExecutado` | 0,1680 |
| `unidadeGestora` | `valorContratualVigente` | 0,0730 |
| `coorte_mandato` | `percentualExecutado` | 0,0675 |
| `coorte_mandato` | `valorContratualVigente` | 0,0599 |
| `unidadeGestora` | `prazoAtualizado` | 0,0577 |
| `coorte_mandato` | `valorAditivos` | 0,0549 |
| `unidadeGestora` | `valorAditivos` | 0,0345 |
| `coorte_mandato` | `prazoAtualizado` | 0,0172 |
| `fonteRecurso` | `valorAditivos` | 0,0170 |
| `situacao` | `prazoAtualizado` | 0,0055 |
| `fonteRecurso` | `valorContratualVigente` | 0,0040 |
| `situacao` | `valorAditivos` | 0,0031 |
| `fonteRecurso` | `percentualExecutado` | 0,0026 |
| `situacao` | `valorContratualVigente` | 0,0017 |

## Seção 4: Outliers e Agrupamentos Naturais

### 4.1 Detecção Matemática de Outliers (|Z| > 3σ e > Q3 + 1,5×IQR)

#### Bairros Oficiais (Valor Total Alocado)
- Outliers `|Z| > 3σ`: **4** (limiar: R$ 173.147.847,49)
- Outliers `> Q3 + 1,5×IQR`: **24** (limiar: R$ 21.561.447,80)

**Top Outliers `|Z| > 3σ`:**

| Entidade | Valor | Z-score |
|---|---:|---:|
| Boca do Rio | R$ 421.047.191,46 | 7,76 |
| Rio Sena | R$ 349.831.643,15 | 6,39 |
| Itapuã | R$ 210.893.463,71 | 3,72 |
| Comércio | R$ 210.692.811,22 | 3,72 |

**Top Outliers `> Q3 + 1,5×IQR`:**

| Entidade | Valor | Z-score |
|---|---:|---:|
| Boca do Rio | R$ 421.047.191,46 | 7,76 |
| Rio Sena | R$ 349.831.643,15 | 6,39 |
| Itapuã | R$ 210.893.463,71 | 3,72 |
| Comércio | R$ 210.692.811,22 | 3,72 |
| Pituaçu | R$ 164.943.875,51 | 2,84 |

#### Obras Públicas (Valor Contratual Vigente)
- Outliers `|Z| > 3σ`: **15** (limiar: R$ 133.173.761,68)
- Outliers `> Q3 + 1,5×IQR`: **79** (limiar: R$ 30.234.860,50)

**Top Outliers `|Z| > 3σ`:**

| Entidade | Valor | Z-score |
|---|---:|---:|
| 2023CT001916 (SEINFRA) | R$ 330.463.204,24 | 8,04 |
| 2022CT007124 (SEINFRA) | R$ 309.696.523,27 | 7,51 |
| 2022CT006728 (SEINFRA) | R$ 299.586.120,12 | 7,25 |
| 2023CT000499 (SEINFRA) | R$ 292.122.786,20 | 7,06 |
| 2018CT001246 (SEINFRA) | R$ 268.942.700,51 | 6,47 |

**Top Outliers `> Q3 + 1,5×IQR`:**

| Entidade | Valor | Z-score |
|---|---:|---:|
| 2023CT001916 (SEINFRA) | R$ 330.463.204,24 | 8,04 |
| 2022CT007124 (SEINFRA) | R$ 309.696.523,27 | 7,51 |
| 2022CT006728 (SEINFRA) | R$ 299.586.120,12 | 7,25 |
| 2023CT000499 (SEINFRA) | R$ 292.122.786,20 | 7,06 |
| 2018CT001246 (SEINFRA) | R$ 268.942.700,51 | 6,47 |

#### Aditivos Contratuais Individuais
- Outliers `|Z| > 3σ`: **23** (limiar: R$ 44.820.370,88)
- Outliers `> Q3 + 1,5×IQR`: **104** (limiar: R$ 5.792.055,41)

**Top Outliers `|Z| > 3σ`:**

| Entidade | Valor | Z-score |
|---|---:|---:|
| 2024CT004935 Ad.2 | R$ 106.259.419,15 | 7,58 |
| 2023CT001916 Ad.4 | R$ 87.937.177,42 | 6,21 |
| 2023CT001916 Ad.2 | R$ 85.419.802,24 | 6,02 |
| 2022CT007124 Ad.3 | R$ 82.409.037,22 | 5,80 |
| 2023CT001916 Ad.1 | R$ 81.797.090,88 | 5,75 |

**Top Outliers `> Q3 + 1,5×IQR`:**

| Entidade | Valor | Z-score |
|---|---:|---:|
| 2024CT004935 Ad.2 | R$ 106.259.419,15 | 7,58 |
| 2023CT001916 Ad.4 | R$ 87.937.177,42 | 6,21 |
| 2023CT001916 Ad.2 | R$ 85.419.802,24 | 6,02 |
| 2022CT007124 Ad.3 | R$ 82.409.037,22 | 5,80 |
| 2023CT001916 Ad.1 | R$ 81.797.090,88 | 5,75 |

#### Pagamentos Individuais (Ordens Bancárias)
- Outliers `|Z| > 3σ`: **102** (limiar: R$ 1.455.177,19)
- Outliers `> Q3 + 1,5×IQR`: **956** (limiar: R$ 126.080,85)

**Top Outliers `|Z| > 3σ`:**

| Entidade | Valor | Z-score |
|---|---:|---:|
| 2023CT008965 2024OB065761 | R$ 10.643.317,69 | 23,65 |
| 2023CT008965 2024OB041567 | R$ 7.826.488,91 | 17,32 |
| 2023CT008965 2024OB049653 | R$ 7.183.410,23 | 15,87 |
| 2023CT008965 2024OB036561 | R$ 6.758.890,38 | 14,92 |
| 2023CT008965 2024OB027753 | R$ 6.694.104,78 | 14,77 |

**Top Outliers `> Q3 + 1,5×IQR`:**

| Entidade | Valor | Z-score |
|---|---:|---:|
| 2023CT008965 2024OB065761 | R$ 10.643.317,69 | 23,65 |
| 2023CT008965 2024OB041567 | R$ 7.826.488,91 | 17,32 |
| 2023CT008965 2024OB049653 | R$ 7.183.410,23 | 15,87 |
| 2023CT008965 2024OB036561 | R$ 6.758.890,38 | 14,92 |
| 2023CT008965 2024OB027753 | R$ 6.694.104,78 | 14,77 |

#### Empreiteiras (Valor Total Contratado)
- Outliers `|Z| > 3σ`: **4** (limiar: R$ 355.912.462,49)
- Outliers `> Q3 + 1,5×IQR`: **27** (limiar: R$ 80.269.771,07)

**Top Outliers `|Z| > 3σ`:**

| Entidade | Valor | Z-score |
|---|---:|---:|
| PEJOTA CONSTRUCOES LTDA | R$ 956.027.056,42 | 8,72 |
| CBS - CONSTRUTORA BAHIANA DE SANEAMENTO LTDA | R$ 788.383.859,89 | 7,12 |
| CONSTRUTORA BSM LTDA | R$ 434.804.716,50 | 3,75 |
| CBV CONSTRUTORA LTDA | R$ 415.920.638,91 | 3,57 |

**Top Outliers `> Q3 + 1,5×IQR`:**

| Entidade | Valor | Z-score |
|---|---:|---:|
| PEJOTA CONSTRUCOES LTDA | R$ 956.027.056,42 | 8,72 |
| CBS - CONSTRUTORA BAHIANA DE SANEAMENTO LTDA | R$ 788.383.859,89 | 7,12 |
| CONSTRUTORA BSM LTDA | R$ 434.804.716,50 | 3,75 |
| CBV CONSTRUTORA LTDA | R$ 415.920.638,91 | 3,57 |
| CAMPBEL CONSTRUCOES E TERRAPLANAGEM LTDA | R$ 355.865.780,50 | 3,00 |

### 4.2 Agrupamento Não-Supervisionado (K-means sobre Z-scores)

#### Perfis Naturais de Bairros Oficiais Residenciais (k=4, N=168)

| Cluster | N | % | Média `populacao` | Média `pct_esgoto_inadequado` | Média `pct_analfabetismo_15mais` | Média `valorTotal` |
|---|---:|---:|---:|---:|---:|---:|
| Cluster 4 | 91 | 54,17% | 10.143,53 | 21,94 | 4,57 | 6.209.398,46 |
| Cluster 1 | 50 | 29,76% | 19.397,30 | 37,33 | 6,72 | 7.317.670,35 |
| Cluster 2 | 21 | 12,50% | 17.122,29 | 6,59 | 1,87 | 20.923.998,54 |
| Cluster 3 | 6 | 3,57% | 27.493,83 | 26,41 | 5,19 | 245.388.987,72 |

#### Perfis Naturais de Obras Públicas (k=4, N=633)

| Cluster | N | % | Média `valorContratualVigente` | Média `valorAditivos` | Média `percentualExecutado` |
|---|---:|---:|---:|---:|---:|
| Cluster 1 | 426 | 67,30% | 7.341.361,09 | 1.968.962,24 | 91,64 |
| Cluster 4 | 168 | 26,54% | 9.206.837,83 | 975.901,74 | 15,39 |
| Cluster 2 | 32 | 5,06% | 106.558.330,67 | 44.816.030,55 | 61,23 |
| Cluster 3 | 7 | 1,11% | 271.038.085,34 | 208.836.620,76 | 56,36 |

## Seção 5: Auditoria Estatística das Variáveis de Domínio

### 5.1 Decomposição dos Gatilhos do Semáforo da Obra

| Classificação (Semáforo da Obra) | Qtd. Obras | % |
|---|---:|---:|
| VERMELHO | 518 | 81,83% |
| VERDE | 86 | 13,59% |
| AMARELO | 29 | 4,58% |

| Gatilho / Regra Crítica (Vermelho) | Obras Atingidas |
|---|---:|
| Aditivo de valor superior a 25% | 154 |
| Situação crítica (paralisada/suspensa/rescindida) | 9 |
| Vigência expirada em 03/11/2023 com execução física incompleta (0.0%) | 2 |
| Vigência expirada em 15/09/2022 com execução física incompleta (0.0%) | 2 |
| Vigência expirada em 16/02/2024 com execução física incompleta (0.0%) | 2 |
| Vigência expirada em 02/12/2022 com execução física incompleta (0.0%) | 2 |
| Vigência expirada em 29/09/2021 com execução física incompleta (0.0%) | 2 |
| Vigência expirada em 09/12/2025 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 01/11/2026 com execução física incompleta (89.95%) | 1 |
| Vigência expirada em 05/11/2025 com execução física incompleta (58.21%) | 1 |
| Vigência expirada em 30/10/2026 com execução física incompleta (29.89%) | 1 |
| Vigência expirada em 30/10/2026 com execução física incompleta (41.38%) | 1 |
| Vigência expirada em 30/10/2025 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 15/08/2026 com execução física incompleta (73.04%) | 1 |
| Vigência expirada em 14/04/2025 com execução física incompleta (93.4%) | 1 |
| Vigência expirada em 08/10/2025 com execução física incompleta (10.36%) | 1 |
| Vigência expirada em 08/11/2026 com execução física incompleta (91.8%) | 1 |
| Vigência expirada em 24/08/2026 com execução física incompleta (25.0%) | 1 |
| Vigência expirada em 23/12/2025 com execução física incompleta (25.01%) | 1 |
| Vigência expirada em 31/08/2025 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 07/03/2025 com execução física incompleta (96.46%) | 1 |
| Vigência expirada em 27/07/2026 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 08/09/2026 com execução física incompleta (12.37%) | 1 |
| Vigência expirada em 02/09/2025 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 28/02/2026 com execução física incompleta (43.13%) | 1 |
| Vigência expirada em 24/02/2025 com execução física incompleta (99.22%) | 1 |
| Vigência expirada em 11/08/2025 com execução física incompleta (89.62%) | 1 |
| Vigência expirada em 28/07/2026 com execução física incompleta (20.73%) | 1 |
| Vigência expirada em 28/07/2026 com execução física incompleta (6.53%) | 1 |
| Vigência expirada em 09/07/2025 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 06/03/2026 com execução física incompleta (95.34%) | 1 |
| Vigência expirada em 27/10/2025 com execução física incompleta (97.82%) | 1 |
| Vigência expirada em 01/12/2025 com execução física incompleta (92.8%) | 1 |
| Vigência expirada em 13/12/2024 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 12/10/2026 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 04/06/2025 com execução física incompleta (72.76%) | 1 |
| Vigência expirada em 12/05/2025 com execução física incompleta (94.34%) | 1 |
| Vigência expirada em 09/05/2025 com execução física incompleta (93.4%) | 1 |
| Vigência expirada em 07/07/2026 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 28/11/2024 com execução física incompleta (93.4%) | 1 |
| Vigência expirada em 02/05/2025 com execução física incompleta (93.4%) | 1 |
| Vigência expirada em 02/05/2025 com execução física incompleta (92.3%) | 1 |
| Vigência expirada em 22/04/2026 com execução física incompleta (68.76%) | 1 |
| Vigência expirada em 29/11/2024 com execução física incompleta (91.8%) | 1 |
| Vigência expirada em 08/02/2026 com execução física incompleta (93.45%) | 1 |
| Vigência expirada em 21/01/2026 com execução física incompleta (93.37%) | 1 |
| Vigência expirada em 14/03/2025 com execução física incompleta (96.15%) | 1 |
| Vigência expirada em 22/04/2025 com execução física incompleta (46.62%) | 1 |
| Vigência expirada em 06/11/2024 com execução física incompleta (95.13%) | 1 |
| Vigência expirada em 05/03/2025 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 08/07/2025 com execução física incompleta (95.63%) | 1 |
| Vigência expirada em 31/07/2024 com execução física incompleta (7.17%) | 1 |
| Vigência expirada em 29/04/2026 com execução física incompleta (89.32%) | 1 |
| Vigência expirada em 29/04/2026 com execução física incompleta (70.51%) | 1 |
| Vigência expirada em 29/04/2026 com execução física incompleta (81.54%) | 1 |
| Vigência expirada em 29/04/2026 com execução física incompleta (90.87%) | 1 |
| Vigência expirada em 28/02/2025 com execução física incompleta (96.15%) | 1 |
| Vigência expirada em 20/10/2024 com execução física incompleta (88.62%) | 1 |
| Vigência expirada em 08/10/2026 com execução física incompleta (94.34%) | 1 |
| Vigência expirada em 23/01/2026 com execução física incompleta (95.54%) | 1 |
| Vigência expirada em 22/01/2025 com execução física incompleta (94.5%) | 1 |
| Vigência expirada em 19/01/2025 com execução física incompleta (71.15%) | 1 |
| Vigência expirada em 16/04/2026 com execução física incompleta (94.66%) | 1 |
| Vigência expirada em 16/10/2025 com execução física incompleta (93.43%) | 1 |
| Vigência expirada em 12/05/2025 com execução física incompleta (87.82%) | 1 |
| Vigência expirada em 12/05/2025 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 25/01/2025 com execução física incompleta (94.5%) | 1 |
| Vigência expirada em 08/05/2024 com execução física incompleta (99.45%) | 1 |
| Vigência expirada em 14/05/2025 com execução física incompleta (95.85%) | 1 |
| Vigência expirada em 27/07/2025 com execução física incompleta (96.07%) | 1 |
| Vigência expirada em 19/06/2024 com execução física incompleta (93.61%) | 1 |
| Vigência expirada em 14/07/2024 com execução física incompleta (95.53%) | 1 |
| Vigência expirada em 06/03/2025 com execução física incompleta (94.4%) | 1 |
| Vigência expirada em 10/01/2025 com execução física incompleta (91.38%) | 1 |
| Vigência expirada em 05/04/2025 com execução física incompleta (95.76%) | 1 |
| Vigência expirada em 05/12/2024 com execução física incompleta (94.5%) | 1 |
| Vigência expirada em 06/10/2024 com execução física incompleta (91.32%) | 1 |
| Vigência expirada em 04/12/2024 com execução física incompleta (89.83%) | 1 |
| Vigência expirada em 05/01/2025 com execução física incompleta (94.5%) | 1 |
| Vigência expirada em 28/06/2026 com execução física incompleta (86.14%) | 1 |
| Vigência expirada em 22/04/2026 com execução física incompleta (99.92%) | 1 |
| Vigência expirada em 29/03/2026 com execução física incompleta (93.74%) | 1 |
| Vigência expirada em 22/05/2025 com execução física incompleta (93.08%) | 1 |
| Vigência expirada em 22/03/2025 com execução física incompleta (94.5%) | 1 |
| Vigência expirada em 22/05/2025 com execução física incompleta (94.32%) | 1 |
| Vigência expirada em 15/03/2025 com execução física incompleta (92.93%) | 1 |
| Vigência expirada em 19/03/2026 com execução física incompleta (75.69%) | 1 |
| Vigência expirada em 16/04/2024 com execução física incompleta (85.15%) | 1 |
| Vigência expirada em 08/11/2024 com execução física incompleta (25.33%) | 1 |
| Vigência expirada em 08/11/2026 com execução física incompleta (57.22%) | 1 |
| Vigência expirada em 08/11/2026 com execução física incompleta (80.32%) | 1 |
| Vigência expirada em 31/10/2026 com execução física incompleta (87.34%) | 1 |
| Vigência expirada em 30/09/2025 com execução física incompleta (93.16%) | 1 |
| Vigência expirada em 31/10/2025 com execução física incompleta (93.06%) | 1 |
| Vigência expirada em 28/02/2026 com execução física incompleta (10.4%) | 1 |
| Vigência expirada em 17/10/2024 com execução física incompleta (95.09%) | 1 |
| Vigência expirada em 06/07/2025 com execução física incompleta (94.46%) | 1 |
| Vigência expirada em 29/09/2024 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 10/06/2026 com execução física incompleta (99.97%) | 1 |
| Vigência expirada em 02/10/2024 com execução física incompleta (94.5%) | 1 |
| Vigência expirada em 02/10/2024 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 02/10/2024 com execução física incompleta (91.27%) | 1 |
| Vigência expirada em 22/02/2025 com execução física incompleta (94.57%) | 1 |
| Vigência expirada em 23/04/2025 com execução física incompleta (93.46%) | 1 |
| Vigência expirada em 26/10/2026 com execução física incompleta (91.49%) | 1 |
| Vigência expirada em 18/05/2025 com execução física incompleta (93.38%) | 1 |
| Vigência expirada em 12/09/2024 com execução física incompleta (51.23%) | 1 |
| Vigência expirada em 05/05/2025 com execução física incompleta (95.76%) | 1 |
| Vigência expirada em 24/03/2025 com execução física incompleta (94.48%) | 1 |
| Vigência expirada em 16/06/2025 com execução física incompleta (97.71%) | 1 |
| Vigência expirada em 30/09/2025 com execução física incompleta (93.36%) | 1 |
| Vigência expirada em 28/12/2025 com execução física incompleta (93.4%) | 1 |
| Vigência expirada em 23/08/2024 com execução física incompleta (95.6%) | 1 |
| Vigência expirada em 23/08/2024 com execução física incompleta (91.08%) | 1 |
| Vigência expirada em 22/08/2024 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 21/04/2025 com execução física incompleta (93.19%) | 1 |
| Vigência expirada em 24/01/2025 com execução física incompleta (80.04%) | 1 |
| Vigência expirada em 17/11/2024 com execução física incompleta (83.01%) | 1 |
| Vigência expirada em 17/11/2024 com execução física incompleta (85.47%) | 1 |
| Vigência expirada em 09/11/2025 com execução física incompleta (93.83%) | 1 |
| Vigência expirada em 02/09/2025 com execução física incompleta (88.58%) | 1 |
| Vigência expirada em 31/10/2025 com execução física incompleta (93.69%) | 1 |
| Vigência expirada em 05/11/2023 com execução física incompleta (93.4%) | 1 |
| Vigência expirada em 17/09/2023 com execução física incompleta (78.7%) | 1 |
| Vigência expirada em 14/07/2025 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 01/10/2023 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 31/03/2026 com execução física incompleta (94.64%) | 1 |
| Vigência expirada em 29/12/2023 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 25/07/2024 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 27/10/2025 com execução física incompleta (90.17%) | 1 |
| Vigência expirada em 27/06/2024 com execução física incompleta (93.39%) | 1 |
| Vigência expirada em 26/06/2024 com execução física incompleta (93.4%) | 1 |
| Vigência expirada em 22/12/2023 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 02/11/2025 com execução física incompleta (21.04%) | 1 |
| Vigência expirada em 16/08/2026 com execução física incompleta (88.56%) | 1 |
| Vigência expirada em 30/06/2026 com execução física incompleta (49.37%) | 1 |
| Vigência expirada em 07/03/2025 com execução física incompleta (98.24%) | 1 |
| Vigência expirada em 12/06/2025 com execução física incompleta (65.52%) | 1 |
| Vigência expirada em 12/06/2025 com execução física incompleta (80.15%) | 1 |
| Vigência expirada em 08/04/2026 com execução física incompleta (89.99%) | 1 |
| Vigência expirada em 30/11/2024 com execução física incompleta (99.5%) | 1 |
| Vigência expirada em 22/12/2024 com execução física incompleta (90.35%) | 1 |
| Vigência expirada em 21/03/2026 com execução física incompleta (93.59%) | 1 |
| Vigência expirada em 22/10/2025 com execução física incompleta (92.32%) | 1 |
| Vigência expirada em 17/04/2025 com execução física incompleta (94.06%) | 1 |
| Vigência expirada em 05/03/2024 com execução física incompleta (87.49%) | 1 |
| Vigência expirada em 26/04/2025 com execução física incompleta (85.45%) | 1 |
| Vigência expirada em 14/06/2024 com execução física incompleta (75.44%) | 1 |
| Vigência expirada em 10/10/2024 com execução física incompleta (95.97%) | 1 |
| Vigência expirada em 17/09/2024 com execução física incompleta (44.84%) | 1 |
| Vigência expirada em 10/03/2024 com execução física incompleta (95.12%) | 1 |
| Vigência expirada em 11/01/2025 com execução física incompleta (91.57%) | 1 |
| Vigência expirada em 18/08/2023 com execução física incompleta (99.96%) | 1 |
| Vigência expirada em 05/05/2024 com execução física incompleta (95.34%) | 1 |
| Vigência expirada em 05/06/2024 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 05/06/2024 com execução física incompleta (93.98%) | 1 |
| Vigência expirada em 09/01/2024 com execução física incompleta (95.36%) | 1 |
| Vigência expirada em 31/07/2024 com execução física incompleta (90.59%) | 1 |
| Vigência expirada em 28/11/2023 com execução física incompleta (87.35%) | 1 |
| Vigência expirada em 25/06/2024 com execução física incompleta (96.15%) | 1 |
| Vigência expirada em 23/03/2026 com execução física incompleta (91.81%) | 1 |
| Vigência expirada em 17/10/2023 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 01/10/2024 com execução física incompleta (94.99%) | 1 |
| Vigência expirada em 24/07/2023 com execução física incompleta (94.5%) | 1 |
| Vigência expirada em 11/01/2025 com execução física incompleta (92.81%) | 1 |
| Vigência expirada em 11/03/2024 com execução física incompleta (92.23%) | 1 |
| Vigência expirada em 11/03/2024 com execução física incompleta (88.94%) | 1 |
| Vigência expirada em 11/03/2024 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 05/09/2023 com execução física incompleta (16.22%) | 1 |
| Vigência expirada em 23/10/2023 com execução física incompleta (93.5%) | 1 |
| Vigência expirada em 29/10/2023 com execução física incompleta (95.6%) | 1 |
| Vigência expirada em 15/03/2023 com execução física incompleta (88.02%) | 1 |
| Vigência expirada em 12/02/2024 com execução física incompleta (85.67%) | 1 |
| Vigência expirada em 07/02/2024 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 02/03/2024 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 02/03/2024 com execução física incompleta (3.99%) | 1 |
| Vigência expirada em 14/08/2024 com execução física incompleta (95.55%) | 1 |
| Vigência expirada em 18/04/2025 com execução física incompleta (94.49%) | 1 |
| Vigência expirada em 21/03/2024 com execução física incompleta (39.59%) | 1 |
| Vigência expirada em 30/04/2024 com execução física incompleta (94.49%) | 1 |
| Vigência expirada em 21/02/2024 com execução física incompleta (94.1%) | 1 |
| Vigência expirada em 11/02/2024 com execução física incompleta (94.5%) | 1 |
| Vigência expirada em 02/11/2023 com execução física incompleta (94.17%) | 1 |
| Vigência expirada em 29/08/2024 com execução física incompleta (27.63%) | 1 |
| Vigência expirada em 18/11/2023 com execução física incompleta (98.79%) | 1 |
| Vigência expirada em 28/02/2024 com execução física incompleta (94.15%) | 1 |
| Vigência expirada em 25/10/2023 com execução física incompleta (72.16%) | 1 |
| Vigência expirada em 30/11/2023 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 02/11/2026 com execução física incompleta (74.43%) | 1 |
| Vigência expirada em 29/05/2023 com execução física incompleta (91.44%) | 1 |
| Vigência expirada em 16/09/2023 com execução física incompleta (99.48%) | 1 |
| Vigência expirada em 30/10/2024 com execução física incompleta (98.98%) | 1 |
| Vigência expirada em 06/12/2024 com execução física incompleta (96.09%) | 1 |
| Vigência expirada em 31/12/2023 com execução física incompleta (96.15%) | 1 |
| Vigência expirada em 21/09/2024 com execução física incompleta (91.75%) | 1 |
| Vigência expirada em 04/06/2023 com execução física incompleta (98.9%) | 1 |
| Vigência expirada em 12/11/2023 com execução física incompleta (96.14%) | 1 |
| Vigência expirada em 24/09/2024 com execução física incompleta (89.65%) | 1 |
| Vigência expirada em 25/10/2023 com execução física incompleta (93.75%) | 1 |
| Vigência expirada em 30/10/2026 com execução física incompleta (74.98%) | 1 |
| Vigência expirada em 10/10/2023 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 05/05/2025 com execução física incompleta (97.29%) | 1 |
| Vigência expirada em 02/04/2026 com execução física incompleta (78.45%) | 1 |
| Vigência expirada em 02/04/2026 com execução física incompleta (82.63%) | 1 |
| Vigência expirada em 02/04/2026 com execução física incompleta (53.99%) | 1 |
| Vigência expirada em 02/04/2026 com execução física incompleta (81.39%) | 1 |
| Vigência expirada em 03/09/2024 com execução física incompleta (88.51%) | 1 |
| Vigência expirada em 03/09/2024 com execução física incompleta (95.94%) | 1 |
| Vigência expirada em 21/09/2024 com execução física incompleta (95.93%) | 1 |
| Vigência expirada em 31/08/2024 com execução física incompleta (99.99%) | 1 |
| Vigência expirada em 31/12/2022 com execução física incompleta (99.84%) | 1 |
| Vigência expirada em 28/06/2023 com execução física incompleta (82.5%) | 1 |
| Vigência expirada em 12/07/2025 com execução física incompleta (54.72%) | 1 |
| Vigência expirada em 25/02/2023 com execução física incompleta (96.08%) | 1 |
| Vigência expirada em 26/12/2022 com execução física incompleta (95.6%) | 1 |
| Vigência expirada em 24/12/2022 com execução física incompleta (95.45%) | 1 |
| Vigência expirada em 19/10/2022 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 21/02/2024 com execução física incompleta (90.68%) | 1 |
| Vigência expirada em 02/10/2024 com execução física incompleta (96.69%) | 1 |
| Vigência expirada em 08/02/2024 com execução física incompleta (99.76%) | 1 |
| Vigência expirada em 01/03/2025 com execução física incompleta (92.44%) | 1 |
| Vigência expirada em 25/05/2023 com execução física incompleta (94.06%) | 1 |
| Vigência expirada em 25/05/2023 com execução física incompleta (95.5%) | 1 |
| Vigência expirada em 22/08/2022 com execução física incompleta (36.34%) | 1 |
| Vigência expirada em 20/08/2022 com execução física incompleta (96.5%) | 1 |
| Vigência expirada em 10/09/2022 com execução física incompleta (90.45%) | 1 |
| Vigência expirada em 22/11/2023 com execução física incompleta (97.42%) | 1 |
| Vigência expirada em 02/08/2022 com execução física incompleta (93.53%) | 1 |
| Vigência expirada em 11/03/2023 com execução física incompleta (96.64%) | 1 |
| Vigência expirada em 13/04/2025 com execução física incompleta (40.82%) | 1 |
| Vigência expirada em 27/03/2023 com execução física incompleta (62.52%) | 1 |
| Vigência expirada em 10/08/2022 com execução física incompleta (94.21%) | 1 |
| Vigência expirada em 05/01/2023 com execução física incompleta (82.9%) | 1 |
| Vigência expirada em 13/08/2022 com execução física incompleta (98.15%) | 1 |
| Vigência expirada em 20/10/2023 com execução física incompleta (94.26%) | 1 |
| Vigência expirada em 12/02/2024 com execução física incompleta (95.96%) | 1 |
| Vigência expirada em 22/01/2025 com execução física incompleta (93.28%) | 1 |
| Vigência expirada em 02/08/2022 com execução física incompleta (73.57%) | 1 |
| Vigência expirada em 23/03/2023 com execução física incompleta (48.5%) | 1 |
| Vigência expirada em 12/12/2022 com execução física incompleta (93.92%) | 1 |
| Vigência expirada em 12/03/2023 com execução física incompleta (93.91%) | 1 |
| Vigência expirada em 12/12/2022 com execução física incompleta (93.04%) | 1 |
| Vigência expirada em 12/12/2022 com execução física incompleta (94.5%) | 1 |
| Vigência expirada em 12/12/2022 com execução física incompleta (94.83%) | 1 |
| Vigência expirada em 12/12/2022 com execução física incompleta (91.97%) | 1 |
| Vigência expirada em 12/12/2022 com execução física incompleta (86.8%) | 1 |
| Vigência expirada em 12/12/2022 com execução física incompleta (93.75%) | 1 |
| Vigência expirada em 09/12/2022 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 06/12/2024 com execução física incompleta (72.63%) | 1 |
| Vigência expirada em 02/12/2023 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 30/11/2022 com execução física incompleta (99.81%) | 1 |
| Vigência expirada em 01/12/2022 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 29/11/2023 com execução física incompleta (91.83%) | 1 |
| Vigência expirada em 28/06/2023 com execução física incompleta (92.66%) | 1 |
| Vigência expirada em 28/07/2023 com execução física incompleta (94.5%) | 1 |
| Vigência expirada em 27/10/2023 com execução física incompleta (92.58%) | 1 |
| Vigência expirada em 28/09/2023 com execução física incompleta (93.88%) | 1 |
| Vigência expirada em 28/05/2023 com execução física incompleta (95.36%) | 1 |
| Vigência expirada em 10/03/2023 com execução física incompleta (94.44%) | 1 |
| Vigência expirada em 11/11/2022 com execução física incompleta (94.33%) | 1 |
| Vigência expirada em 11/11/2022 com execução física incompleta (92.3%) | 1 |
| Vigência expirada em 11/11/2022 com execução física incompleta (89.8%) | 1 |
| Vigência expirada em 25/10/2026 com execução física incompleta (69.5%) | 1 |
| Vigência expirada em 31/05/2022 com execução física incompleta (39.67%) | 1 |
| Vigência expirada em 12/12/2022 com execução física incompleta (87.71%) | 1 |
| Vigência expirada em 03/10/2022 com execução física incompleta (92.6%) | 1 |
| Vigência expirada em 03/10/2022 com execução física incompleta (94.5%) | 1 |
| Vigência expirada em 14/09/2026 com execução física incompleta (31.6%) | 1 |
| Vigência expirada em 28/12/2023 com execução física incompleta (91.05%) | 1 |
| Vigência expirada em 14/07/2022 com execução física incompleta (89.0%) | 1 |
| Vigência expirada em 02/08/2024 com execução física incompleta (15.6%) | 1 |
| Vigência expirada em 31/03/2022 com execução física incompleta (31.24%) | 1 |
| Vigência expirada em 02/08/2026 com execução física incompleta (40.0%) | 1 |
| Vigência expirada em 02/08/2026 com execução física incompleta (41.33%) | 1 |
| Vigência expirada em 20/07/2023 com execução física incompleta (3.02%) | 1 |
| Vigência expirada em 08/07/2022 com execução física incompleta (14.63%) | 1 |
| Vigência expirada em 07/07/2026 com execução física incompleta (32.5%) | 1 |
| Vigência expirada em 08/07/2022 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 07/11/2021 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 18/12/2021 com execução física incompleta (93.46%) | 1 |
| Vigência expirada em 02/04/2022 com execução física incompleta (51.37%) | 1 |
| Vigência expirada em 08/04/2026 com execução física incompleta (64.66%) | 1 |
| Vigência expirada em 17/01/2022 com execução física incompleta (92.14%) | 1 |
| Vigência expirada em 09/09/2021 com execução física incompleta (77.91%) | 1 |
| Vigência expirada em 03/12/2021 com execução física incompleta (95.2%) | 1 |
| Vigência expirada em 09/09/2021 com execução física incompleta (92.87%) | 1 |
| Vigência expirada em 09/09/2021 com execução física incompleta (95.51%) | 1 |
| Vigência expirada em 26/02/2022 com execução física incompleta (1.26%) | 1 |
| Vigência expirada em 24/02/2022 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 24/02/2026 com execução física incompleta (8.88%) | 1 |
| Vigência expirada em 19/03/2023 com execução física incompleta (84.62%) | 1 |
| Vigência expirada em 13/11/2021 com execução física incompleta (95.16%) | 1 |
| Vigência expirada em 08/09/2021 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 29/01/2023 com execução física incompleta (10.0%) | 1 |
| Vigência expirada em 18/01/2022 com execução física incompleta (98.24%) | 1 |
| Vigência expirada em 03/08/2022 com execução física incompleta (82.33%) | 1 |
| Vigência expirada em 10/03/2021 com execução física incompleta (98.5%) | 1 |
| Vigência expirada em 30/03/2021 com execução física incompleta (94.5%) | 1 |
| Vigência expirada em 08/07/2022 com execução física incompleta (93.71%) | 1 |
| Vigência expirada em 10/05/2021 com execução física incompleta (94.54%) | 1 |
| Vigência expirada em 09/11/2021 com execução física incompleta (93.19%) | 1 |
| Vigência expirada em 11/11/2023 com execução física incompleta (18.21%) | 1 |
| Vigência expirada em 01/11/2023 com execução física incompleta (69.99%) | 1 |
| Vigência expirada em 22/09/2021 com execução física incompleta (3.28%) | 1 |
| Vigência expirada em 17/09/2021 com execução física incompleta (92.6%) | 1 |
| Vigência expirada em 18/07/2021 com execução física incompleta (95.43%) | 1 |
| Vigência expirada em 10/05/2021 com execução física incompleta (90.49%) | 1 |
| Vigência expirada em 08/04/2021 com execução física incompleta (86.22%) | 1 |
| Vigência expirada em 31/01/2022 com execução física incompleta (94.15%) | 1 |
| Vigência expirada em 30/09/2023 com execução física incompleta (0.75%) | 1 |
| Vigência expirada em 10/01/2022 com execução física incompleta (93.55%) | 1 |
| Vigência expirada em 10/01/2022 com execução física incompleta (92.92%) | 1 |
| Vigência expirada em 10/01/2022 com execução física incompleta (92.33%) | 1 |
| Vigência expirada em 02/10/2024 com execução física incompleta (41.66%) | 1 |
| Vigência expirada em 30/01/2022 com execução física incompleta (95.56%) | 1 |
| Vigência expirada em 10/09/2022 com execução física incompleta (9.56%) | 1 |
| Vigência expirada em 16/01/2023 com execução física incompleta (92.03%) | 1 |
| Vigência expirada em 22/12/2021 com execução física incompleta (27.9%) | 1 |
| Vigência expirada em 15/03/2023 com execução física incompleta (80.83%) | 1 |
| Vigência expirada em 22/12/2021 com execução física incompleta (30.84%) | 1 |
| Vigência expirada em 03/09/2022 com execução física incompleta (93.03%) | 1 |
| Vigência expirada em 09/11/2021 com execução física incompleta (97.57%) | 1 |
| Vigência expirada em 29/04/2022 com execução física incompleta (99.24%) | 1 |
| Vigência expirada em 19/12/2021 com execução física incompleta (96.14%) | 1 |
| Vigência expirada em 24/04/2021 com execução física incompleta (94.62%) | 1 |
| Vigência expirada em 29/06/2021 com execução física incompleta (93.36%) | 1 |
| Vigência expirada em 05/11/2021 com execução física incompleta (93.4%) | 1 |
| Vigência expirada em 07/11/2021 com execução física incompleta (92.4%) | 1 |
| Vigência expirada em 30/10/2021 com execução física incompleta (94.5%) | 1 |
| Vigência expirada em 07/12/2021 com execução física incompleta (99.5%) | 1 |
| Vigência expirada em 22/07/2021 com execução física incompleta (91.57%) | 1 |
| Vigência expirada em 25/06/2022 com execução física incompleta (95.91%) | 1 |
| Vigência expirada em 29/02/2024 com execução física incompleta (89.42%) | 1 |
| Vigência expirada em 17/06/2021 com execução física incompleta (9.8%) | 1 |
| Vigência expirada em 29/10/2022 com execução física incompleta (93.84%) | 1 |
| Vigência expirada em 23/05/2024 com execução física incompleta (94.46%) | 1 |
| Vigência expirada em 31/07/2024 com execução física incompleta (64.73%) | 1 |
| Vigência expirada em 28/05/2021 com execução física incompleta (20.53%) | 1 |
| Vigência expirada em 12/02/2022 com execução física incompleta (91.82%) | 1 |
| Vigência expirada em 05/11/2025 com execução física incompleta (92.04%) | 1 |
| Vigência expirada em 27/09/2021 com execução física incompleta (92.71%) | 1 |
| Vigência expirada em 30/11/2022 com execução física incompleta (77.39%) | 1 |
| Vigência expirada em 30/04/2021 com execução física incompleta (27.71%) | 1 |
| Vigência expirada em 30/04/2023 com execução física incompleta (91.46%) | 1 |
| Vigência expirada em 23/04/2021 com execução física incompleta (23.5%) | 1 |
| Vigência expirada em 14/07/2022 com execução física incompleta (93.83%) | 1 |
| Vigência expirada em 14/01/2022 com execução física incompleta (93.2%) | 1 |
| Vigência expirada em 03/07/2021 com execução física incompleta (45.43%) | 1 |
| Vigência expirada em 01/01/2022 com execução física incompleta (93.4%) | 1 |
| Vigência expirada em 02/10/2021 com execução física incompleta (94.32%) | 1 |
| Vigência expirada em 01/11/2021 com execução física incompleta (93.14%) | 1 |
| Vigência expirada em 01/07/2021 com execução física incompleta (93.22%) | 1 |
| Vigência expirada em 04/04/2021 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 01/11/2021 com execução física incompleta (95.31%) | 1 |
| Vigência expirada em 26/09/2021 com execução física incompleta (93.22%) | 1 |
| Vigência expirada em 30/11/2021 com execução física incompleta (94.94%) | 1 |
| Vigência expirada em 20/06/2021 com execução física incompleta (90.47%) | 1 |
| Vigência expirada em 17/01/2021 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 05/05/2023 com execução física incompleta (69.27%) | 1 |
| Vigência expirada em 18/01/2022 com execução física incompleta (92.58%) | 1 |
| Vigência expirada em 05/12/2021 com execução física incompleta (93.87%) | 1 |
| Vigência expirada em 04/04/2022 com execução física incompleta (93.32%) | 1 |
| Vigência expirada em 10/12/2022 com execução física incompleta (31.09%) | 1 |
| Vigência expirada em 30/11/2022 com execução física incompleta (96.15%) | 1 |
| Vigência expirada em 31/05/2022 com execução física incompleta (93.08%) | 1 |
| Vigência expirada em 16/04/2021 com execução física incompleta (71.75%) | 1 |
| Vigência expirada em 27/07/2021 com execução física incompleta (95.49%) | 1 |
| Vigência expirada em 14/03/2021 com execução física incompleta (99.36%) | 1 |
| Vigência expirada em 30/03/2022 com execução física incompleta (44.42%) | 1 |
| Vigência expirada em 23/03/2021 com execução física incompleta (95.04%) | 1 |
| Vigência expirada em 30/11/2022 com execução física incompleta (93.76%) | 1 |
| Vigência expirada em 22/02/2022 com execução física incompleta (93.83%) | 1 |
| Vigência expirada em 19/03/2023 com execução física incompleta (63.67%) | 1 |
| Vigência expirada em 20/09/2024 com execução física incompleta (86.2%) | 1 |
| Vigência expirada em 17/02/2021 com execução física incompleta (91.33%) | 1 |
| Vigência expirada em 29/01/2021 com execução física incompleta (93.99%) | 1 |
| Vigência expirada em 23/01/2021 com execução física incompleta (90.07%) | 1 |
| Vigência expirada em 01/09/2021 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 02/09/2022 com execução física incompleta (16.33%) | 1 |
| Vigência expirada em 24/02/2021 com execução física incompleta (91.28%) | 1 |
| Vigência expirada em 29/07/2024 com execução física incompleta (17.86%) | 1 |
| Vigência expirada em 10/01/2021 com execução física incompleta (94.59%) | 1 |
| Vigência expirada em 21/07/2021 com execução física incompleta (80.36%) | 1 |
| Vigência expirada em 01/10/2021 com execução física incompleta (94.75%) | 1 |
| Vigência expirada em 31/10/2022 com execução física incompleta (91.09%) | 1 |
| Vigência expirada em 08/04/2025 com execução física incompleta (90.06%) | 1 |
| Vigência expirada em 07/09/2024 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 26/08/2021 com execução física incompleta (94.02%) | 1 |
| Vigência expirada em 31/05/2021 com execução física incompleta (17.76%) | 1 |
| Vigência expirada em 30/04/2024 com execução física incompleta (35.65%) | 1 |
| Vigência expirada em 13/02/2023 com execução física incompleta (88.9%) | 1 |
| Vigência expirada em 30/06/2021 com execução física incompleta (96.26%) | 1 |
| Vigência expirada em 19/12/2021 com execução física incompleta (22.42%) | 1 |
| Vigência expirada em 09/07/2021 com execução física incompleta (94.91%) | 1 |
| Vigência expirada em 14/04/2022 com execução física incompleta (86.15%) | 1 |
| Vigência expirada em 22/06/2021 com execução física incompleta (92.66%) | 1 |
| Vigência expirada em 27/06/2021 com execução física incompleta (90.66%) | 1 |
| Vigência expirada em 30/04/2022 com execução física incompleta (86.86%) | 1 |
| Vigência expirada em 31/07/2021 com execução física incompleta (91.09%) | 1 |
| Vigência expirada em 05/08/2021 com execução física incompleta (90.99%) | 1 |
| Vigência expirada em 11/12/2022 com execução física incompleta (93.54%) | 1 |
| Vigência expirada em 25/06/2021 com execução física incompleta (90.56%) | 1 |
| Vigência expirada em 25/06/2021 com execução física incompleta (89.86%) | 1 |
| Vigência expirada em 19/11/2023 com execução física incompleta (2.33%) | 1 |
| Vigência expirada em 27/07/2021 com execução física incompleta (93.69%) | 1 |
| Vigência expirada em 09/09/2021 com execução física incompleta (92.4%) | 1 |
| Vigência expirada em 19/06/2021 com execução física incompleta (91.02%) | 1 |
| Vigência expirada em 17/04/2022 com execução física incompleta (30.18%) | 1 |
| Vigência expirada em 17/03/2021 com execução física incompleta (92.87%) | 1 |
| Vigência expirada em 17/08/2023 com execução física incompleta (92.97%) | 1 |
| Vigência expirada em 20/05/2021 com execução física incompleta (67.28%) | 1 |
| Vigência expirada em 05/07/2023 com execução física incompleta (91.75%) | 1 |
| Vigência expirada em 02/05/2021 com execução física incompleta (34.14%) | 1 |
| Vigência expirada em 28/03/2021 com execução física incompleta (96.96%) | 1 |
| Vigência expirada em 30/12/2021 com execução física incompleta (97.55%) | 1 |
| Vigência expirada em 07/12/2022 com execução física incompleta (85.11%) | 1 |
| Vigência expirada em 21/06/2021 com execução física incompleta (94.0%) | 1 |
| Vigência expirada em 06/05/2021 com execução física incompleta (90.85%) | 1 |
| Vigência expirada em 25/04/2022 com execução física incompleta (91.8%) | 1 |
| Vigência expirada em 28/04/2021 com execução física incompleta (77.99%) | 1 |
| Vigência expirada em 29/11/2022 com execução física incompleta (68.42%) | 1 |
| Vigência expirada em 14/11/2022 com execução física incompleta (92.11%) | 1 |
| Vigência expirada em 27/04/2021 com execução física incompleta (0.52%) | 1 |
| Vigência expirada em 14/12/2025 com execução física incompleta (14.47%) | 1 |
| Vigência expirada em 05/10/2026 com execução física incompleta (95.6%) | 1 |
| Vigência expirada em 28/09/2026 com execução física incompleta (93.52%) | 1 |
| Vigência expirada em 23/09/2026 com execução física incompleta (94.48%) | 1 |
| Vigência expirada em 06/09/2026 com execução física incompleta (95.6%) | 1 |
| Vigência expirada em 31/08/2026 com execução física incompleta (95.6%) | 1 |
| Vigência expirada em 06/10/2026 com execução física incompleta (95.6%) | 1 |
| Vigência expirada em 02/10/2026 com execução física incompleta (89.44%) | 1 |
| Vigência expirada em 08/10/2026 com execução física incompleta (6.61%) | 1 |
| Vigência expirada em 07/10/2026 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 07/10/2026 com execução física incompleta (12.0%) | 1 |
| Vigência expirada em 07/08/2026 com execução física incompleta (95.6%) | 1 |
| Vigência expirada em 09/05/2026 com execução física incompleta (94.49%) | 1 |
| Vigência expirada em 19/04/2026 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 21/05/2026 com execução física incompleta (95.03%) | 1 |
| Vigência expirada em 14/03/2026 com execução física incompleta (95.6%) | 1 |
| Vigência expirada em 08/10/2026 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 28/03/2026 com execução física incompleta (95.6%) | 1 |
| Vigência expirada em 07/06/2026 com execução física incompleta (93.15%) | 1 |
| Vigência expirada em 02/04/2026 com execução física incompleta (53.53%) | 1 |
| Vigência expirada em 03/03/2026 com execução física incompleta (95.6%) | 1 |
| Vigência expirada em 31/07/2026 com execução física incompleta (94.5%) | 1 |
| Vigência expirada em 30/07/2026 com execução física incompleta (90.39%) | 1 |
| Vigência expirada em 20/10/2026 com execução física incompleta (53.9%) | 1 |
| Vigência expirada em 06/12/2025 com execução física incompleta (95.51%) | 1 |
| Vigência expirada em 29/03/2026 com execução física incompleta (93.07%) | 1 |
| Vigência expirada em 10/10/2026 com execução física incompleta (0.64%) | 1 |
| Vigência expirada em 01/08/2026 com execução física incompleta (96.13%) | 1 |
| Vigência expirada em 16/01/2026 com execução física incompleta (89.36%) | 1 |
| Vigência expirada em 30/06/2026 com execução física incompleta (93.4%) | 1 |
| Vigência expirada em 17/06/2026 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 16/06/2026 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 12/12/2025 com execução física incompleta (95.6%) | 1 |
| Vigência expirada em 14/03/2026 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 11/09/2025 com execução física incompleta (92.68%) | 1 |
| Vigência expirada em 28/02/2026 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 29/04/2026 com execução física incompleta (0.0%) | 1 |
| Vigência expirada em 04/11/2025 com execução física incompleta (91.07%) | 1 |
| Vigência expirada em 11/08/2025 com execução física incompleta (95.6%) | 1 |
| Vigência expirada em 07/04/2026 com execução física incompleta (96.32%) | 1 |
| Vigência expirada em 22/05/2025 com execução física incompleta (89.16%) | 1 |

### 5.2 Comparação: Obras Localizadas vs. Escopo Cidade (Não-Localizado)

| Recorte | Qtd. | Média Valor Vigente | Mediana Valor Vigente | Com Notas de Empenho |
|---|---:|---:|---:|---:|
| Localizadas (`Pontual` / `Bairro` / `Regional (Prefeitura-Bairro)`) | 287 | R$ 14.346.752,13 | R$ 4.151.329,73 | 105 |
| Escopo Cidade (Não-Localizado) | 346 | R$ 16.947.352,30 | R$ 3.111.138,00 | 175 |

### 5.3 Distribuição por Tema da Obra e Nível de Alocação Territorial

| Tema da Obra | Contratos | Valor Vigente Total |
|---|---:|---:|
| Manutenção Urbana e Outros | 265 | R$ 4.689.034.265,75 |
| Educação e Escolas | 122 | R$ 1.276.137.214,57 |
| Mobilidade, Pavimentação e Drenagem | 108 | R$ 1.482.043.966,89 |
| Praças, Esporte e Lazer | 77 | R$ 871.933.713,34 |
| Saúde | 35 | R$ 293.336.293,28 |
| Encostas e Contenção | 26 | R$ 1.368.816.303,04 |

| Nível de Alocação Territorial | Contratos | Valor Vigente Total |
|---|---:|---:|
| Escopo Cidade (Não-Localizado) | 346 | R$ 5.863.783.894,33 |
| Bairro | 241 | R$ 2.842.676.672,50 |
| Regional (Prefeitura-Bairro) | 46 | R$ 1.274.841.190,04 |

### 5.4 Índice de Vulnerabilidade do Bairro vs. Investimento por Habitante (Zonas Especiais Excluídas)

- Bairros Oficiais residenciais analisados: **N = 168** (Zonas Especiais Não-Residenciais excluídas do cálculo per capita).
- Correlação entre `indice_vulnerabilidade` e `investimentoPorHabitante`: Pearson `r = -0,016`, Spearman `ρ = -0,018`.

| Prefeitura-Bairro | População | Índice Vulnerabilidade | Obras | Valor Total | Invest./Hab |
|---|---:|---:|---:|---:|---:|
| Subúrbio/Ilhas | 261024 | 0,89 | 53 | R$ 769.636.608,05 | R$ 2.948,53 |
| Cajazeiras | 192680 | 0,74 | 21 | R$ 348.435.301,47 | R$ 1.808,36 |
| Valéria | 75740 | 0,73 | 3 | R$ 11.078.901,47 | R$ 146,28 |
| Liberdade/São Caetano | 297441 | 0,72 | 13 | R$ 329.484.409,23 | R$ 1.107,73 |
| Cabula/Tancredo Neves | 317923 | 0,71 | 33 | R$ 222.340.514,27 | R$ 699,35 |
| Pau da Lima | 173172 | 0,63 | 4 | R$ 20.271.359,76 | R$ 117,06 |
| Cidade Baixa | 148253 | 0,60 | 15 | R$ 135.463.338,81 | R$ 913,73 |
| Itapuã/Ipitanga | 388097 | 0,55 | 44 | R$ 1.174.406.379,44 | R$ 3.026,06 |
| Centro/Brotas | 239424 | 0,44 | 59 | R$ 501.704.674,21 | R$ 2.095,47 |
| Barra/Pituba | 323924 | 0,30 | 42 | R$ 604.696.375,83 | R$ 1.866,78 |

#### Cruzamento Prefeitura-Bairro × Bairros Oficiais Residenciais

| Prefeitura-Bairro | Bairros Residenciais | Bairros sem Obras | Mediana Invest./Hab (Bairros) | Máx Invest./Hab (Bairro) | Mediana Vulnerabilidade |
|---|---:|---:|---:|---:|---:|
| Barra/Pituba | 23 | 12 | R$ 0,00 | R$ 8.458,16 | 0,24 |
| Cabula/Tancredo Neves | 21 | 9 | R$ 23,20 | R$ 3.516,96 | 0,62 |
| Cajazeiras | 17 | 10 | R$ 0,00 | R$ 6.803,69 | 0,83 |
| Centro/Brotas | 22 | 11 | R$ 23,90 | R$ 14.420,19 | 0,49 |
| Cidade Baixa | 14 | 6 | R$ 202,82 | R$ 8.742,10 | 0,53 |
| Itapuã/Ipitanga | 16 | 6 | R$ 340,94 | R$ 10.850,61 | 0,53 |
| Liberdade/São Caetano | 19 | 12 | R$ 0,00 | R$ 701,48 | 0,78 |
| Pau da Lima | 12 | 10 | R$ 0,00 | R$ 750,04 | 0,53 |
| Subúrbio/Ilhas | 19 | 9 | R$ 26,53 | R$ 24.038,46 | 0,92 |
| Valéria | 4 | 2 | R$ 35,24 | R$ 319,54 | 0,73 |

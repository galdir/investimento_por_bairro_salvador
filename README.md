# Mapa das Obras e do Dinheiro por Bairro — Salvador

Painel interativo de controle social e justiça territorial que traduz a execução orçamentária de **Obras Públicas** e serviços de engenharia da Prefeitura de Salvador das rubricas contábeis (CNPJ e Unidade Gestora) para o território vivido pelo cidadão (**Equipamento Público**, Logradouro, **Bairro Oficial** e **Prefeitura-Bairro**).

Hospedado de forma 100% estática no **GitHub Pages** (`/investimento_por_bairro_salvador/`) e alimentado por um pipeline ETL incremental em Python que coleta, geocodifica e cruza três bases públicas oficiais sem custo de servidor.

---

## Sumário

1. [Arquitetura do Projeto (ADR-0001)](#arquitetura-do-projeto-adr-0001)
2. [Camadas de Informação do Painel](#camadas-de-informação-do-painel)
3. [Fontes de Dados Oficiais Utilizadas](#fontes-de-dados-oficiais-utilizadas)
4. [Regras de Domínio e Alocação Territorial](#regras-de-domínio-e-alocação-territorial)
5. [Metodologia do Índice de Vulnerabilidade do Bairro (Censo 2022 / ADR-0003)](#metodologia-do-índice-de-vulnerabilidade-do-bairro-censo-2022--adr-0003)
6. [Como Executar o ETL Manualmente na Máquina Local](#como-executar-o-etl-manualmente-na-máquina-local)
7. [Como Rodar o Painel Web Localmente](#como-rodar-o-painel-web-localmente)
8. [Como Executar os Testes Automatizados](#como-executar-os-testes-automatizados)
9. [Automação e Publicação via GitHub Actions](#automação-e-publicação-via-github-actions)

---

## Arquitetura do Projeto (ADR-0001)

O sistema adota uma **Arquitetura Estática Particionada** (documentada em `docs/adr/0001-arquitetura-estatica-github-pages.md`), dividida em dois subsistemas desacoplados que se comunicam exclusivamente por artefatos JSON e GeoJSON estáticos:

1. **Subsistema de Pipeline ETL (`etl/` — Python):**
   - Extrai dados da API do Portal da Transparência de Salvador, do servidor ArcGIS REST do GeoSalvador e da API SIDRA do Censo 2022 do IBGE.
   - Executa o **Funil de Alocação Territorial em 3 Estágios** apoiado pelo **Cache Incremental** persistido no repositório (`public/data/geocoding_cache.json`).
   - Classifica cada contrato pelo **Semáforo da Obra**, **Tema da Obra** e **Nível de Alocação Territorial**, calcula a concentração por construtora e emite os artefatos estáticos particionados.
2. **Subsistema do Painel Web (`src/` — React + TypeScript + Vite + Tailwind CSS + Leaflet):**
   - Single-Page Application (SPA) 100% estática compilada com caminho base `/investimento_por_bairro_salvador/` para o GitHub Pages.
   - Carrega na inicialização apenas o índice anual enxuto e as malhas cartográficas, buscando os prontuários individuais de cada contrato sob demanda (`fetch`) quando o cidadão abre a **Ficha Limpa da Obra**.

### Estrutura dos Artefatos Estáticos (`public/data/`)

```text
public/data/
├── geocoding_cache.json            # Cache Incremental de geocodificação (versionado no Git)
├── index_2025.json                 # KPIs globais, resumos territoriais e lista compacta de obras
├── geo/
│   ├── bairros.geojson             # Malha de Bairros Oficiais (EPSG:4326) enriquecida com R$/hab
│   └── prefeituras_bairro.geojson  # Malha de Prefeituras-Bairro (EPSG:4326) enriquecida
└── obras/
    └── <id>.json                   # Ficha Limpa da Obra carregada sob demanda (Funil, Aditivos, DOM, Dotação)
```

---

## Camadas de Informação do Painel

- **Camada A (Justiça Territorial Per Capita):**
  - Mapa coroplético interativo e ranking horizontal de **Prefeituras-Bairro** e **Bairros Oficiais** coloridos pelo **Investimento por Habitante** ou pelo **Índice de Vulnerabilidade do Bairro** (Censo 2022).
  - Painel lateral **"Raio-X do Território"** com população residente, investimento total alocado, investimento per capita e distribuição de obras por cor do semáforo.
  - Indicador de **Transparência Opaca** no topo do painel, destacando o volume financeiro retido em contratos de **Escopo Cidade (Não-Localizado)**.
- **Camada B (Semáforo da Obra e Temas):**
  - Pinos georreferenciados no mapa (com dispersão geométrica anti-sobreposição para obras no mesmo centróide) e tabela detalhada auditável.
  - Filtros combinados por Ano, Órgão/Unidade Gestora, **Tema da Obra**, **Semáforo da Obra**, busca textual (objeto, razão social ou CNPJ) e alternância de métrica financeira (**Valor Contratual Vigente** vs. **Valor Executado / Pago**).
- **Camada C (Ficha Limpa da Obra sob Demanda):**
  - Modal detalhado aberto ao clicar em qualquer pino no mapa ou linha na tabela, exibindo o objeto completo, número do contrato SIGEF, processo administrativo, edição do Diário Oficial do Município (`nuDom`), vigência original vs. atualizada, **Funil de Execução Financeira** (`Original -> Vigente -> Empenhado -> Liquidado -> Pago` comparado à execução física), histórico de **Aditivos Contratuais**, dotação orçamentária e resumo de concentração da empreiteira na cidade (com filtro em 1 clique).

---

## Fontes de Dados Oficiais Utilizadas

1. **Portal da Transparência Municipal de Salvador (`https://apitmptransparencia.salvador.ba.gov.br/api`):**
   - `POST /obraspublicas/totalizador` e `POST /obraspublicas/gridDetalhada?pagina=<N>`: totalizadores e contratos de engenharia ativos/concluídos no exercício.
   - `POST /obraspublicas/detalhamentoObrasPublicas`: CNPJ da construtora (`nuDocumentoCredor`), prazos originais e edição do Diário Oficial (`nuDom`).
   - `POST /obraspublicas/aditivo`, `/obraspublicas/dotacao`, `/obraspublicas/empenhoRelacionado`, `/obraspublicas/liquidacaoRelacionado` e `/obraspublicas/pagamentoRelacionado`: histórico de termos aditivos, fontes de recurso e estágios da execução orçamentária.
2. **GeoSalvador — Servidor ArcGIS REST (`https://geo.salvador.ba.gov.br/arcgis/rest/services/MAPA_BASE/MAPA_BASE_Consulta/MapServer`):**
   - `Layer 164`: Malha vigente dos 170 **Bairros Oficiais** de Salvador (Decreto nº 32.791/2020, que atualizou a Lei nº 9.278/2017), consultada em projeção `EPSG:4326` (`outSR=4326&f=geojson`).
   - `Layer 7`: Limites das **Prefeituras-Bairro**.
   - `Layer 9` e `Layer 11`: Cadastro oficial georreferenciado de **Equipamentos Públicos** municipais (118 Unidades de Saúde e 368 Escolas Municipais/CMEIs).
   - `Layer 2`: Malha oficial de logradouros.
3. **IBGE — API SIDRA do Censo Demográfico 2022 (`https://apisidra.ibge.gov.br`):**
   - Dados agregados do Universo (100% dos domicílios e moradores recenseados) no nível territorial `N102` (Bairros de Salvador — código municipal `2927408`):
     - `Tabela 9923`: População residente por bairro.
     - `Tabela 6805`: Domicílios particulares permanentes ocupados por tipo de esgotamento sanitário (definição PLANSAB de esgotamento adequado).
     - `Tabela 6803`: Domicílios particulares permanentes ocupados por forma principal de abastecimento de água (rede geral).
     - `Tabela 9543`: Alfabetização e taxa de analfabetismo de pessoas residentes com 15 anos ou mais de idade.

---

## Regras de Domínio e Alocação Territorial

### 1. Funil de Alocação Territorial em 3 Estágios

Cada **Obra Pública** recebe um dos quatro **Níveis de Alocação Territorial**:
- **Pontual**: Obra com logradouro ou **Equipamento Público** identificado; soma no **Bairro Oficial** e na **Prefeitura-Bairro**.
- **Bairro**: Obra cuja descrição identifica o **Bairro Oficial** (ou sublocalidade mapeada em `etl/reference/sublocalidades.json`); recebe a coordenada do centróide do bairro e soma no **Bairro Oficial** e na **Prefeitura-Bairro**.
- **Regional (Prefeitura-Bairro)**: Contrato guarda-chuva ou de lote regional mapeado em `etl/reference/lotes_regionais.json`; soma exclusivamente na **Prefeitura-Bairro** correspondente, sem rateio artificial entre bairros individuais.
- **Escopo Cidade (Não-Localizado)**: Contrato sem localização discriminada no objeto; alimenta os KPIs globais da cidade e o indicador de **Transparência Opaca**, sem inflar bairros ou Prefeituras-Bairro.

Os três estágios do funil executam em ordem:
1. **Estágio 1 (Catálogo Oficial Determinístico):** Casamento textual normalizado contra os 368 equipamentos de educação, 118 equipamentos de saúde, dicionários de lotes regionais e sublocalidades e os 170 **Bairros Oficiais**.
2. **Estágio 2 (Nominatim OpenStreetMap Fallback):** Quando habilitado (`ENABLE_NOMINATIM=1`), geocodifica logradouros remanescentes dentro da bounding box de Salvador com validação espacial *point-in-polygon* (`Shapely`) contra os polígonos oficiais.
3. **Estágio 3 (Extrator LLM Opcional):** Suporte opcional via variável de ambiente (`GEMINI_API_KEY`, `OPENAI_API_KEY` ou `ANTHROPIC_API_KEY`) para casos ambíguos.

### 2. Zonas Especiais Não-Residenciais

Os recortes `Aeroporto`, `Porto Seco Pirajá` e `Centro Administrativo da Bahia - CAB` possuem população residente nula ou residual no Censo 2022 e ocupação institucional/logística. Para evitar distorções milionárias de investimento por morador, são sinalizados com `isZonaEspecialNaoResidencial: true` e excluídos do ranking de **Investimento por Habitante**, mantendo visíveis seus valores brutos e contratos.

### 3. Máquina de Estados do Semáforo da Obra

Calculado a partir da variação percentual de aditivos `delta_percentual_valor = ((vlAtualizado - vlOriginal) / vlOriginal) * 100` em ordem estrita de prioridade:

- **Vermelho (Crítica):** Obra com situação `Paralisada`, `Suspensa` ou `Rescindida`; ou prazo de vigência atualizado vencido com execução física abaixo de 100%; ou `delta_percentual_valor > 25.0`; ou obra em execução sem liquidação/pagamento há mais de 90 dias.
- **Amarelo (Atenção):** Obra não crítica que sofreu prorrogação de prazo em relação ao término original ou possui `10.0 <= delta_percentual_valor <= 25.0`.
- **Verde (No Prazo):** Obra dentro do cronograma original (ou concluída) e com `delta_percentual_valor < 10.0`.

---

## Metodologia do Índice de Vulnerabilidade do Bairro (Censo 2022 / ADR-0003)

O **Índice de Vulnerabilidade do Bairro** do painel é uma métrica composta multidimensional contínua na escala `0,00` (menor vulnerabilidade relativa) a `1,00` (maior vulnerabilidade relativa), calculada de forma determinística e 100% auditável a partir de agregados do **Universo do Censo Demográfico 2022 do IBGE** (nível territorial `N102` — Bairros de Salvador `2927408`).

Esta metodologia foi homologada no repositório no **ADR-0003** (`docs/adr/0003-indice-vulnerabilidade-composto-censo-2022.md`), substituindo completamente dicionários manuais ou estimativas empíricas anteriores.

### 1. Referencial Científico: IDS (IPP) e IVS (IPEA)

O modelo combina duas referências consolidadas na literatura de indicadores urbanos no Brasil:
- **Índice de Desenvolvimento Social (IDS):** Criado por **Cavallieri & Lopes (2008)** no **Instituto Pereira Passos (IPP/Rio de Janeiro)** para mensurar desigualdades intraurbanas a partir de dimensões de acesso a saneamento básico e capital humano.
- **Índice de Vulnerabilidade Social (IVS):** Desenvolvido pelo **IPEA** (Instituto de Pesquisa Econômica Aplicada), em especial seus subíndices de *Infraestrutura Urbana* (saneamento básico e abastecimento de água) e de *Capital Humano* (escolaridade e alfabetização).

Ao contrário de índices que dependem de renda monetária per capita da amostra (sujeitos a restrições de sigilo estatístico e margens de erro amostrais em bairros de menor porte demográfico), os três componentes adotados provêm do **questionário básico do Universo do Censo 2022** (100% dos domicílios particulares permanentes ocupados e moradores recenseados).

---

### 2. As 3 Variáveis do Universo do Censo 2022 (IBGE / SIDRA nível N102)

Para cada **Bairro Oficial** residencial $b$ de Salvador, são extraídas as seguintes variáveis censitárias:

| Dimensão | Tabela SIDRA | Indicador de Domínio | Definição Oficial IBGE / PLANSAB |
| :--- | :---: | :--- | :--- |
| **Esgotamento Sanitário** | **Tabela 6805** | `pct_esgoto_inadequado` | Percentual de domicílios particulares permanentes ocupados sem rede geral/pluvial ou fossa séptica/filtro (critério oficial de adequação do **PLANSAB** — Plano Nacional de Saneamento Básico). |
| **Abastecimento de Água** | **Tabela 6803** | `pct_agua_inadequada` | Percentual de domicílios particulares permanentes ocupados sem ligação principal à rede geral de distribuição de água tratada. |
| **Alfabetização** | **Tabela 9543** | `pct_analfabetismo_15mais` | Percentual de moradores de 15 anos ou mais de idade que não sabem ler e escrever um bilhete simples (complemento de 100% da taxa de alfabetização). |

#### Equações dos Sub-indicadores Brutos:

1. **Déficit de Esgotamento Sanitário Adequado (critério PLANSAB):**
   $$x_{\text{esgoto}, b} = 100\% - \left(\frac{\text{Domicílios com rede geral} + \text{Domicílios com fossa séptica ou filtro}}{\text{Total de domicílios particulares permanentes ocupados}}\right) \times 100$$

2. **Déficit de Abastecimento de Água por Rede Geral:**
   $$x_{\text{agua}, b} = 100\% - \left(\frac{\text{Domicílios com rede geral de distribuição}}{\text{Total de domicílios particulares permanentes ocupados}}\right) \times 100$$

3. **Taxa de Analfabetismo (15 anos ou mais):**
   $$x_{\text{analf}, b} = 100\% - \text{Taxa de Alfabetização da População de 15 anos ou mais}$$

---

### 3. Fórmulas Matemáticas Passo a Passo

#### 3.1 Normalização Min-Max sobre os Bairros Residenciais
Para unificar as variáveis em uma escala comum sem distorcer as amplitudes naturais observadas em Salvador, cada sub-indicador $k \in \{\text{esgoto}, \text{agua}, \text{analf}\}$ é normalizado pelo método *min-max* sobre o conjunto dos **168 Bairros Oficiais residenciais**:

$$I_{k, b} = \frac{x_{k, b} - \min_{j \in \text{Residenciais}}(x_{k, j})}{\max_{j \in \text{Residenciais}}(x_{k, j}) - \min_{j \in \text{Residenciais}}(x_{k, j})}$$

Onde:
- $I_{k, b} \in [0,00;\; 1,00]$ é o sub-índice normalizado da dimensão $k$ no bairro $b$;
- $\min(x_k)$ e $\max(x_k)$ são os limites inferior e superior empíricos observados exclusivamente entre os 168 bairros residenciais de Salvador no Censo 2022.

#### 3.2 Composição por Média Aritmética Simples de Pesos Iguais
O **Índice de Vulnerabilidade do Bairro ($\text{IVB}_b$)** é obtido pela média aritmética simples das três dimensões normalizadas (peso de $\frac{1}{3}$ para esgoto, água e analfabetismo), arredondada em duas casas decimais:

$$\text{IVB}_b = \text{round}\left(\frac{I_{\text{esgoto}, b} + I_{\text{agua}, b} + I_{\text{analf}, b}}{3},\; 2\right)$$

Essa composição preserva a hierarquia socioeconômica observada pelo IBGE em Salvador (exemplo real: `Pituba (0,13) < Cabula (0,55) < Liberdade (0,78)`).

#### 3.3 Agregação Regional para as Prefeituras-Bairro
Para as 10 macrorregiões administrativas descentralizadas de Salvador (**Prefeituras-Bairro**), tanto o índice composto quanto os seus três sub-indicadores percentuais são consolidados pela **média ponderada populacional** dos seus Bairros Oficiais residenciais constituintes:

$$\text{IVB}_{\text{PB}} = \frac{\sum_{b \in \text{PB}} \left(\text{IVB}_b \times \text{População}_b\right)}{\sum_{b \in \text{PB}} \text{População}_b}$$

$$\bar{x}_{k, \text{PB}} = \frac{\sum_{b \in \text{PB}} \left(x_{k, b} \times \text{População}_b\right)}{\sum_{b \in \text{PB}} \text{População}_b}$$

Onde $\text{População}_b$ é a contagem de população residente oficial do Censo 2022 (Tabela 9923 do SIDRA).

---

### 4. Regras de Exceção Territorial e Imputação Espacial

#### 4.1 Zonas Especiais Não-Residenciais (Isenção Estatística)
Os recortes `Aeroporto`, `Porto Seco Pirajá` e `Centro Administrativo da Bahia - CAB` possuem ocupação logística, institucional ou aeroportuária, com população residente nula ou residual no Censo 2022.
- **Tratamento:** São expressamente **excluídos** do domínio de cálculo dos extremos $\min(x_k)$ e $\max(x_k)$.
- **Representação:** No pipeline ETL e no painel web, recebem `isZonaEspecialNaoResidencial: true`, `indice_vulnerabilidade: 0.0` e são apresentados com o status **`Isento`** no **Ranking Territorial**, no mapa coroplético e no card do painel lateral **Raio-X**.

#### 4.2 Imputação Espacial por Contiguidade Territorial
Três Bairros Oficiais residenciais delimitados pela malha legal vigente do município (Decreto nº 32.791/2020) não possuem linha própria de agregação individual no nível `N102` do SIDRA/IBGE. Para esses casos, os sub-indicadores brutos foram imputados de forma determinística pela **média ponderada populacional dos bairros limítrofes contíguos da mesma zona homogênea** no Censo 2022:

1. **Chame-Chame** (Prefeitura-Bairro Barra/Pituba):
   Imputado pela média ponderada populacional dos vizinhos contíguos `Graça`, `Barra` e `Vitória`.
2. **Colinas de Pituaçu** (Prefeitura-Bairro Pau da Lima):
   Imputado pela média ponderada populacional dos vizinhos contíguos `São Marcos` e `Pau da Lima`.
3. **Ilha de Maré** (Prefeitura-Bairro Subúrbio/Ilhas):
   Imputado pela média ponderada populacional das ilhas vizinhas do Censo 2022 (`Ilha de Bom Jesus dos Passos` e `Ilha dos Frades/Ilha de Santo Antônio`).

Estes três bairros recebem no modelo de dados a flag booleana `vulnerabilidade_estimada_contiguidade: true`, gerando automaticamente no painel lateral **Raio-X** um selo amarelo transparente que alerta o cidadão sobre a estimativa por contiguidade territorial.

---

---

## Como Executar o ETL Manualmente na Máquina Local

### Pré-requisitos

- **Python** 3.10 ou superior
- **pip** (gerenciador de pacotes Python)

### Passo a passo

1. Instale as dependências do subsistema ETL:

```bash
pip install -r requirements.txt
```

2. Execute o pipeline ETL para gerar ou atualizar os artefatos estáticos em `public/data/`:

```bash
python -m etl.main --output-dir public/data --year 2025
```

Você também pode especificar explicitamente o caminho do arquivo de **Cache Incremental** de geocodificação:

```bash
python -m etl.main --output-dir public/data --year 2025 --cache-file public/data/geocoding_cache.json
```

Para habilitar consultas externas ao Nominatim (Estágio 2) em contratos com logradouros inéditos:

```bash
# Linux / macOS
ENABLE_NOMINATIM=1 python -m etl.main --output-dir public/data --year 2025

# Windows (PowerShell)
$env:ENABLE_NOMINATIM="1"; python -m etl.main --output-dir public/data --year 2025
```

> **Nota sobre Resiliência Offline:** Caso a máquina local esteja sem acesso às APIs governamentais ou algum servidor externo apresente instabilidade, o pipeline recorre automaticamente às bases de referência consolidadas em `etl/reference/`, garantindo execução determinística.

---

## Como Rodar o Painel Web Localmente

### Pré-requisitos

- **Node.js** 20 ou superior e **npm**

### Passo a passo

1. Instale as dependências do front-end:

```bash
npm install
```

2. Inicie o servidor de desenvolvimento do Vite:

```bash
npm run dev
```

O painel ficará disponível em `http://localhost:5173/investimento_por_bairro_salvador/`.

3. Para compilar o build estático de produção (idêntico ao publicado no GitHub Pages) e inspecioná-lo localmente:

```bash
npm run build
npm run preview
```

---

## Como Executar os Testes Automatizados

O projeto conta com duas suítes de testes automatizados de ponta a ponta (ETL e Painel Web):

### 1. Testes do Pipeline ETL e Domínio (`pytest`)

```bash
python -m pytest
```

Valida a máquina de estados do **Semáforo da Obra**, o classificador de **Tema da Obra**, o **Funil de Alocação Territorial**, o **Cache Incremental**, as regras de rollup de **Bairros Oficiais**, **Prefeituras-Bairro** e **Zonas Especiais Não-Residenciais**, a construção da **Ficha Limpa da Obra** e a geração dos arquivos estáticos.

### 2. Testes do Painel Web (`vitest` + Testing Library)

```bash
npm test
```

Valida a renderização dos KPIs superiores (incluindo **Transparência Opaca**), alternância de camadas coropléticas (**Investimento por Habitante** vs. **Índice de Vulnerabilidade do Bairro**), ranking de **Prefeituras-Bairro**, painel **Raio-X**, filtragem da tabela detalhada, carregamento sob demanda da **Ficha Limpa da Obra** e resolução de caminhos sob o subcaminho do GitHub Pages (`/investimento_por_bairro_salvador/`).

---

## Automação e Publicação via GitHub Actions

O repositório possui dois workflows configurados em `.github/workflows/`:

1. **Publicar Painel no GitHub Pages (`.github/workflows/deploy-pages.yml`):**
   - Disparado automaticamente a cada `push` na branch `main` (ou manualmente via `workflow_dispatch`).
   - Executa toda a suíte `pytest` (ETL) e `vitest` (Painel Web), compila o pacote estático em `dist/` com `npm run build` e publica o artefato diretamente no GitHub Pages.
2. **Atualização de Dados do ETL (`.github/workflows/update-etl-data.yml`):**
   - Disparado por agendamento semanal (`cron: "0 6 * * 1"`, toda segunda-feira às 06:00 UTC) ou manualmente via botão **Run workflow** (`workflow_dispatch`) na aba Actions do GitHub, permitindo informar o ano de referência.
   - Reutiliza e atualiza o arquivo `public/data/geocoding_cache.json` no repositório, regenera `public/data/geo/*.geojson`, `public/data/index_<ano>.json` e `public/data/obras/<id>.json`, executa os testes de integridade com `pytest` e realiza o commit automático caso haja novos dados.

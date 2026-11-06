# Mapa das Obras e do Dinheiro por Bairro (Salvador)

Painel de controle social e justiça territorial que traduz a execução orçamentária de obras e serviços de engenharia da Prefeitura de Salvador das rubricas contábeis (CNPJ/Órgão) para o território vivido pelo cidadão (Logradouro, Bairro Oficial e Prefeitura-Bairro).

## Language

### Recortes Territoriais

**Bairro Oficial**:
Unidade territorial básica de Salvador delimitada pela malha vigente do município (Decreto nº 32.791/2020 no GeoSalvador, que atualizou a Lei nº 9.278/2017) e pareada com os agregados de bairro do Censo 2022 do IBGE.
_Avoid_: Distrito, subdistrito, zona, setor censitário

**Zona Especial Não-Residencial**:
Bairro Oficial cuja ocupação é predominantemente institucional, aeroportuária ou logística e que possui população residente nula ou residual no Censo 2022 (`Aeroporto`, `Porto Seco Pirajá` e `Centro Administrativo da Bahia - CAB`), sendo excluído do ranking de Investimento por Habitante para evitar distorções per capita.
_Avoid_: Bairro sem dados, bairro inválido, bairro deserto

**Prefeitura-Bairro**:
Macrorregião administrativa descentralizada da Prefeitura de Salvador que agrupa um conjunto de Bairros Oficiais para gestão e manutenção urbana.
_Avoid_: Regional, subprefeitura, macrozona

**Equipamento Público**:
Unidade física municipal de atendimento direto ao cidadão com coordenada e bairro conhecidos no cadastro oficial (como Escola Municipal, CMEI, UBS, USF ou UPA).
_Avoid_: Prédio público, repartição, instalação

### Classificação e Alocação de Obras

**Obra Pública**:
Contrato administrativo vigente ou concluído no período cujo objeto compreende obras ou serviços de engenharia gerenciados por Unidades Gestoras do município de Salvador.
_Avoid_: Despesa genérica, compra, licitação

**Tema da Obra**:
Categoria funcional atribuída a uma Obra Pública a partir da combinação de sua Unidade Gestora e das palavras-chave de seu objeto (`Encostas e Contenção`, `Educação e Escolas`, `Saúde`, `Praças, Esporte e Lazer`, `Mobilidade, Pavimentação e Drenagem` ou `Manutenção Urbana e Outros`).
_Avoid_: Tipo de licitação, natureza de despesa, rubrica

**Nível de Alocação Territorial**:
Grau de precisão geográfica com que uma Obra Pública é vinculada ao território de Salvador:
- **Pontual**: Obra com endereço, logradouro ou Equipamento Público identificado, alocada a uma coordenada geográfica, ao seu Bairro Oficial e à sua Prefeitura-Bairro.
- **Bairro**: Obra cuja descrição identifica o Bairro Oficial, mas não um ponto exato na rua; soma no Bairro Oficial e na Prefeitura-Bairro.
- **Regional (Prefeitura-Bairro)**: Contrato guarda-chuva ou de lote mapeado que abrange uma Prefeitura-Bairro inteira; soma na Prefeitura-Bairro sem ser rateado artificialmente entre seus bairros individuais.
- **Escopo Cidade (Não-Localizado)**: Contrato cujo objeto não especifica localização geográfica ou cita um lote ainda não mapeado; compõe os totais globais da cidade e o indicador de transparência opaca, sem inflar bairros ou Prefeituras-Bairro específicos.
_Avoid_: Precisão de GPS, tipo de endereço, categoria espacial

### Indicadores Financeiros e de Execução

**Valor Contratual Vigente**:
Valor global atualizado do contrato da Obra Pública (soma do Valor Original Contratado com os Termos Aditivos de valor acumulados).
_Avoid_: Valor bruto, orçamento total, custo final

**Aditivo Contratual**:
Alteração formal publicada no Diário Oficial do Município (DOM) que modifica o valor financeiro (Aditivo de Valor) ou a data de término da vigência (Aditivo de Prazo) de uma Obra Pública em relação ao contrato original.
_Avoid_: Reajuste informal, multa, extra

**Funil de Execução Financeira**:
Sequência de estágios orçamentários de uma Obra Pública: Valor Original Contratado -> Valor Contratual Vigente -> Valor Empenhado (reservado no orçamento) -> Valor Liquidado (obra efetivamente medida) -> Valor Pago (transferido à conta da empreiteira).
_Avoid_: Fluxo de caixa, etapas de pagamento

**Investimento por Habitante**:
Razão entre a soma financeira das Obras Públicas alocadas a um recorte territorial (Bairro Oficial residencial ou Prefeitura-Bairro) e a população residente daquele recorte segundo o Censo 2022 do IBGE.
_Avoid_: Gasto médio por pessoa, renda per capita, cota por morador

**Índice de Vulnerabilidade do Bairro**:
Métrica sociodemográfica e de déficit de infraestrutura de cada Bairro Oficial extraída dos agregados do Censo 2022 do IBGE, utilizada para confrontar o Investimento por Habitante com o grau de necessidade social do território.
_Avoid_: Índice de pobreza, nota social

**Semáforo da Obra**:
Classificação automática de risco e andamento de cada Obra Pública pela pior condição observada:
- **Vermelho (Crítica)**: Obra paralisada/suspensa/rescindida, com prazo atualizado vencido e execução inferior a 100%, com aditivo de valor superior a 25%, ou em execução sem liquidação/pagamento há mais de 90 dias.
- **Amarelo (Atenção)**: Obra não crítica que sofreu prorrogação de prazo em relação à vigência original ou aditivo de valor entre 10% e 25%.
- **Verde (No Prazo)**: Obra dentro da vigência original (ou concluída), sem prorrogação de prazo e com aditivo de valor inferior a 10%.
_Avoid_: Status do contrato, nota da obra, cor do pino

**Ficha Limpa da Obra**:
Visão detalhada de uma Obra Pública individual contendo objeto, empreiteira (nome e CNPJ), datas de vigência, número do DOM, Funil de Execução Financeira, histórico de Aditivos Contratuais e fonte de recurso (Dotação).
_Avoid_: Relatório contábil, extrato SIGEF

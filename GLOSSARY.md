# Mapa das Obras e do Dinheiro por Bairro (Salvador)

Painel de controle social e justiça territorial que traduz a execução orçamentária de obras e serviços de engenharia da Prefeitura de Salvador das rubricas contábeis (CNPJ/Órgão) para o território vivido pelo cidadão (Logradouro, Bairro Oficial e Prefeitura-Bairro).

## Language

### Recortes Territoriais

**Bairro Oficial**:
Unidade territorial básica de Salvador delimitada pela malha vigente do município (Decreto nº 32.791/2020 no GeoSalvador, que atualizou a Lei nº 9.278/2017) e pareada com os agregados de bairro do Censo 2022 do IBGE.
_Avoid_: Distrito, subdistrito, zona, setor censitário

**Zona Especial Não-Residencial**:
Bairro Oficial cuja ocupação é predominantemente institucional, aeroportuária ou logística e que possui população residente nula ou residual no Censo 2022 (`Aeroporto`, `Porto Seco Pirajá` e `Centro Administrativo da Bahia - CAB`), sendo isento do cálculo de Investimento por Habitante e de vulnerabilidade para evitar distorções estatísticas per capita, mas contabilizado normalmente em montante absoluto e quantidade de obras.
_Avoid_: Bairro sem dados, bairro inválido, bairro deserto

**Centralidade Metropolitana de Baixa População Residente**:
Bairro Oficial continental de vocação portuária, financeira, institucional e cultural metropolitana (`ZUE-3` / `ZCMe` na LOUOS) com população residente inferior a 1.000 habitantes e densidade demográfica inferior a 1.000 hab/km² no Censo 2022 (`Comércio`), que preserva seu Índice de Vulnerabilidade do Bairro (inclusive na média ponderada populacional da Prefeitura-Bairro `Centro/Brotas` e no mapa coroplético de vulnerabilidade), mas é isento do cálculo de Investimento por Habitante no nível de bairro para evitar distorções estatísticas per capita, sendo posicionado ao final dos bairros com comparação per capita ativa na lista bivariada de Bairros Oficiais em qualquer ordenação.
_Avoid_: Bairro comercial, zona mista, bairro semi-isento

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

**Chave Canônica da Obra**:
Identificador único e imutável de uma Obra Pública formado pelo par composto por sua Unidade Gestora e seu número de contrato no sistema contábil municipal, preservando a identidade do contrato independentemente de identificadores temporários de sessão gerados pelo portal da transparência.
_Avoid_: ID temporário da API, UUID volátil, chave primária de banco

**Empreiteira**:
Pessoa jurídica ou consórcio contratado pelo município para executar uma Obra Pública, identificada univocamente pelo seu CNPJ (ou unificada pela Razão Social canônica quando o CNPJ estiver omitido em parte dos registros oficiais da mesma empresa).
_Avoid_: Fornecedor genérico, prestador, parceiro

**Mandato Municipal**:
Ciclo quadrienal da administração municipal de Salvador (`2021–2024` ou `2025–2028`) utilizado como recorte temporal de controle social; uma Obra Pública integra todos os mandatos com os quais seu período de vigência (`dtInicioVigencia` a `dtTerminoVigenciaAtualizado`) se sobrepõe.
_Avoid_: Ano civil isolado, ano de assinatura, exercício contábil

**Tema da Obra**:
Categoria funcional atribuída a uma Obra Pública a partir da combinação de sua Unidade Gestora e das palavras-chave de seu objeto (`Encostas e Contenção`, `Educação e Escolas`, `Saúde`, `Praças, Esporte e Lazer`, `Mobilidade, Pavimentação e Drenagem` ou `Manutenção Urbana e Outros`).
_Avoid_: Tipo de licitação, natureza de despesa, rubrica

**Vocação da Obra**:
Classificação da abrangência de atendimento urbano de uma Obra Pública em três categorias selecionáveis pelo cidadão: `Vizinhança e Comunidade` (escolas básicas, USFs, contenção de encostas, praças, pavimentação/drenagem local e urbanização integrada de comunidades), `Mobilidade Estrutural e Orlas` (viadutos, túneis, BRT, grandes eixos viários e requalificação de orlas marítimas) ou `Equipamentos e Marcos da Cidade` (hospitais municipais, arenas multiuso, mercados históricos, teatros, museus, centros culturais e sedes administrativas de escopo municipal).
_Avoid_: Porte da obra, tamanho do contrato, relevância da obra

**Nível de Alocação Territorial**:
Grau de precisão geográfica com que uma Obra Pública é vinculada ao território de Salvador:
- **Pontual**: Obra com endereço, logradouro ou Equipamento Público identificado, alocada a uma coordenada geográfica, ao seu Bairro Oficial e à sua Prefeitura-Bairro.
- **Bairro**: Obra cuja descrição identifica o Bairro Oficial, mas não um ponto exato na rua; soma no Bairro Oficial e na Prefeitura-Bairro.
- **Regional (Prefeitura-Bairro)**: Contrato guarda-chuva ou de lote mapeado que abrange uma Prefeitura-Bairro inteira; soma na Prefeitura-Bairro sem ser rateado artificialmente entre seus bairros individuais.
- **Escopo Cidade (Não-Localizado)**: Contrato cujo objeto não especifica localização geográfica ou cita um lote ainda não mapeado; compõe os totais globais da cidade e o indicador de transparência opaca, sem inflar bairros ou Prefeituras-Bairro específicos.
_Avoid_: Precisão de GPS, tipo de endereço, categoria espacial

### Indicadores Financeiros e de Execução

**Valor Contratual Vigente**:
Valor global atualizado do contrato da Obra Pública registrado no cabeçalho contábil municipal (soma do Valor Original Contratado com a Variação Contratual Acumulada).
_Avoid_: Valor bruto, orçamento total, custo final

**Variação Contratual Acumulada**:
Diferença financeira positiva entre o Valor Contratual Vigente e o Valor Original Contratado de uma Obra Pública, abrangendo tanto Termos Aditivos de valor quanto apostilamentos e reajustes contratuais aplicados ao saldo global.
_Avoid_: Lucro, sobrepreço, custo extra

**Aditivo Contratual**:
Termo formal publicado no Diário Oficial do Município (DOM) e listado individualmente no histórico contratual que modifica o valor financeiro (Aditivo de Valor) ou a data de término da vigência (Aditivo de Prazo) de uma Obra Pública.
_Avoid_: Reajuste informal, multa, extra

**Funil de Execução Financeira**:
Sequência de estágios orçamentários de uma Obra Pública: Valor Original Contratado -> Valor Contratual Vigente -> Valor Empenhado (reservado no orçamento) -> Valor Liquidado (obra efetivamente medida) -> Valor Pago (transferido à conta da empreiteira).
_Avoid_: Fluxo de caixa, etapas de pagamento

**Valor Pago Acumulado do Contrato**:
Valor dos pagamentos registrados para a Obra Pública ao longo de todo o contrato até a data de referência, inclusive antes de 2021 quando aplicável. O Mandato Municipal seleciona contratos por sua vigência e não limita esses pagamentos ao período do mandato.
_Avoid_: Pagamento do mandato, valor estimado pela execução física

**Data da Última Atualização Concluída**:
Data de referência da última atualização dos dados do dashboard concluída sem falhas que impeçam sua publicação; permanece inalterada quando uma atualização posterior falha. A conclusão da atualização não implica cobertura integral do histórico de pagamentos de todos os contratos, que é informada separadamente.
_Avoid_: Data do pagamento, data da última tentativa

**Movimento de Pagamento**:
Registro individual de pagamento associado a uma Obra Pública, que pode ter valor positivo ou negativo e compartilhar uma ordem bancária com outros movimentos distintos. Registros informados pelo portal para contratos diferentes são contabilizados em seus respectivos contratos, mesmo quando semelhantes.
_Avoid_: Ordem bancária como pagamento único

**Conflito de Identidade de Pagamento**:
Incerteza sobre se registros de pagamento de um mesmo contrato representam o mesmo Movimento de Pagamento ou movimentos distintos. Enquanto não resolvido, apenas um representante de cada grupo ambíguo é contabilizado provisoriamente, os demais permanecem acessíveis e a cobertura do contrato é identificada como incompleta; o conflito é reavaliado automaticamente nas próximas atualizações.
_Avoid_: Duplicata presumida

**Registro de Pagamento Não Conciliável**:
Registro informado pela fonte sem os dados necessários para identificar com segurança a que grupo de pagamentos pertence. Permanece acessível e fora da soma até que novos dados permitam sua conciliação automática.
_Avoid_: Pagamento zerado, duplicata presumida

**Cobertura dos Pagamentos do Contrato**:
Grau em que os registros de pagamento disponíveis abrangem o histórico necessário para apurar o Valor Pago Acumulado do Contrato, considerando o período e a completude da consulta à fonte. Zero registrado representa uma consulta completa e confirmada sem registros para o período coberto, não uma prova independente de que nunca houve pagamento; quando a fonte cobre apenas parte do histórico, o zero é identificado como parcial.
_Avoid_: Comprovação de que não houve pagamento

**Limitação de Cobertura da Fonte**:
Lacuna no histórico necessário para apurar o Valor Pago Acumulado do Contrato causada por uma limitação comprovada das informações disponibilizadas pelo Portal da Transparência.
_Avoid_: Falha de coleta presumida como ausência de dados

**Cobertura de Pagamentos Não Verificada**:
Situação em que a consulta retorna registros, mas não há evidência suficiente para determinar qual período do histórico contratual está abrangido. Os registros permanecem acessíveis, mas não entram na escala comparativa territorial de Valor Pago por habitante até que a cobertura seja verificada.
_Avoid_: Cobertura completa presumida, limitação comprovada da fonte

**Soma Parcial de Pagamentos**:
Soma dos registros de pagamento apuráveis para uma Obra Pública ou território cuja Cobertura dos Pagamentos do Contrato não está completa. A soma territorial pode integrar a escala de Valor Pago por habitante identificada como parcial, sem incluir valores de contratos com Cobertura de Pagamentos Não Verificada; se não houver nenhum valor apurável, o território permanece visível como indisponível.
_Avoid_: Total pago, mínimo pago

**Investimento por Habitante**:
Razão entre a soma financeira das Obras Públicas alocadas a um recorte territorial (Bairro Oficial residencial ou Prefeitura-Bairro) e a população residente daquele recorte segundo o Censo 2022 do IBGE.
_Avoid_: Gasto médio por pessoa, renda per capita, cota por morador

**Índice de Vulnerabilidade do Bairro**:
Métrica composta multidimensional (`0,00` a `1,00`) de carência de infraestrutura urbana e capital humano de cada Bairro Oficial residencial (e consolidada por média ponderada populacional para cada Prefeitura-Bairro), fundamentada no Índice de Desenvolvimento Social (IDS/IPP) e no Índice de Vulnerabilidade Social (IVS/IPEA) a partir dos agregados do Universo do Censo 2022 do IBGE (déficit de esgotamento sanitário adequado, déficit de abastecimento de água por rede geral e taxa de analfabetismo de 15 anos ou mais).
_Avoid_: Índice de pobreza, nota social, estimativa manual

**Comparação Territorial**:
Leitura conjunta do Investimento por Habitante e do Índice de Vulnerabilidade do Bairro entre Bairros Oficiais ou entre Prefeituras-Bairro, com o Índice de Vulnerabilidade representado em escala fechada (`0,00` a `1,00`) e o Investimento por Habitante em barra comparativa referenciada pela média municipal, para investigar a distribuição territorial dos recursos municipais. A associação observada não estabelece, por si só, a população beneficiada nem a suficiência dos investimentos.
_Avoid_: Prova de abandono, índice de favorecimento

**Ranking Territorial**:
Ordenação comparativa de Bairros Oficiais ou de Prefeituras-Bairro segundo o Índice de Vulnerabilidade do Bairro ou o Investimento por Habitante (com desempate alfabético e preservação à parte dos territórios isentos ou sem dado disponível), permitindo investigar tanto a partir da carência social quanto da concentração per capita de recursos.
_Avoid_: Top bairros, placar de obras, lista de prefeituras

**Semáforo da Obra**:
Classificação automática de risco e andamento de cada Obra Pública pela pior condição observada:
- **Vermelho (Crítica)**: Obra paralisada/suspensa/rescindida, com prazo atualizado vencido e execução inferior a 100%, com aditivo de valor superior a 25%, ou em execução sem liquidação/pagamento há mais de 90 dias.
- **Amarelo (Atenção)**: Obra não crítica que sofreu prorrogação de prazo em relação à vigência original ou aditivo de valor entre 10% e 25%.
- **Verde (No Prazo)**: Obra dentro da vigência original (ou concluída), sem prorrogação de prazo e com aditivo de valor inferior a 10%.
_Avoid_: Status do contrato, nota da obra, cor do pino

**Ficha Limpa da Obra**:
Visão detalhada de uma Obra Pública individual contendo objeto, empreiteira (nome e CNPJ), datas de vigência, número do DOM, Funil de Execução Financeira, histórico de Aditivos Contratuais, fonte de recurso (Dotação) e referências às fontes oficiais comprobatórias (Chave Canônica da Obra, processo administrativo, DOM e lastro documental territorial).
_Avoid_: Relatório contábil, extrato SIGEF

**Frente de Medição**:
Parcela de uma Obra Pública guarda-chuva vinculada a um Bairro Oficial ou Prefeitura-Bairro específico mediante lastro documental em nota de liquidação, ordem de serviço ou curadoria semântica auditável, contabilizada estritamente nos valores liquidados e pagos comprovados sem rateio artificial do saldo contratual global.
_Avoid_: Rateio de contrato, estimativa por bairro, subcontrato informal

**Curadoria Territorial Auditável**:
Julgamento semântico explícito e versionado sobre textos livres de contratos, aditivos e liquidações, registrando a decisão e o trecho documental comprobatório para vincular uma Obra Pública ou Frente de Medição ao território sem heurísticas cegas por palavras-chave.
_Avoid_: Regex de bairro, geocodificação automática por palavra-chave

# Inclusão do Mandato Municipal 2017–2020 e Congelamento de Pagamentos Consolidados

Status: aceita. Emenda [ADR-0002](./0002-coleta-plurianual-incremental-por-mandato.md) e [ADR-0007](./0007-coleta-e-publicacao-de-pagamentos.md).

## Contexto

O painel passou a cobrir inicialmente dois ciclos quadrienais (`2021–2024` e `2025–2028`, 633 Obras Públicas). A consulta diagnóstica ao endpoint `/obraspublicas/gridDetalhada` para `2017–2020` identificou **558 contratos únicos** com o mesmo esquema de campos — sendo **140 já presentes** no portal (vigência estendida para 2021+) e **418 contratos novos** exclusivos até 2020 (+66% na base total, para ~1.051 contratos).

Dois achados empíricos condicionaram o desenho:
1. O Portal da Transparência de Salvador **não atualiza `dsSituacao` para `"Concluído"`** mesmo em contratos encerrados há anos (`0` ocorrências nos 418 novos de `2017–2020` e `0` nos 335 exclusivos de `2021–2024`, predominando `"Em Execução"` e `"Ajustar Cronograma"`), enquanto `dtTerminoVigenciaAtualizado` está preenchido em 100% da carteira.
2. O [ADR-0007](./0007-coleta-e-publicacao-de-pagamentos.md) (parágrafos 31 e 33) determinava a reconsulta obrigatória de pagamentos de 100% dos contratos em toda atualização semanal, sem mesclar datas de referência diferentes. Sem uma regra de consolidação para contratos antigos, expandir a série histórica degradaria o tempo e a confiabilidade das execuções semanais.

## Decisão

1. **Expansão para o Mandato Municipal `2017–2020` (série `2017–2028`):**
   - Adicionar `2017–2020` em `MANDATOS_MUNICIPAIS`, mantendo a classificação por sobreposição de vigência contratual e o padrão inicial do painel em `Todos os mandatos` com rótulo dinâmico (`2017–2028`).
   - Manter todos os valores em **reais nominais** (como publicados na fonte) e explicitar na Nota Metodológica a ausência de deflacionamento e o uso retroativo da malha oficial do Decreto nº 32.791/2020 e da demografia/vulnerabilidade do Censo 2022.
   - Antes de promover `2017–2020` para `public/data`, executar ensaio de conciliação de pagamentos em saída isolada comprovando que a nova janela não introduz divergência no `downloadDados` nem altera os valores apurados dos 140 contratos compartilhados com `2021–2024`.
   - Executar **Curadoria Territorial Auditável** em **100% dos contratos de `2017–2020` que caírem em `Escopo Cidade (Não-Localizado)`**, independentemente do `Valor Contratual Vigente`, alocando todos os que possuírem lastro documental e confirmando explicitamente os genuinamente sem localização.

2. **Emenda ao ADR-0007 — `Contrato com Pagamentos Consolidados`:**
   - Nas execuções semanais normais (sem `--full-refresh`), uma Obra Pública dispensa nova consulta à API de pagamentos e reaproveita sua última coleta válida e conciliada quando **todas** as condições abaixo forem satisfeitas:
     1. `dtTerminoVigenciaAtualizado` encerrada há mais de **12 meses** em relação à `Data de Referência dos Pagamentos` da rodada;
     2. Nenhuma alteração nos campos monitorados do grid (`vlAtualizado`, `percentualExecutado`, `dsSituacao`, `dtTerminoVigenciaAtualizado`);
     3. Coleta anterior de pagamentos concluída, conciliada e validada localmente;
     4. Menos de **180 dias** decorridos desde a `dataReferenciaPagamentos` registrada no contrato.
   - Qualquer alteração contratual no grid **descongela automaticamente** o contrato na próxima rodada.
   - Contratos cuja consolidação ultrapasse **180 dias** são revalidados automaticamente (capturando eventuais restos a pagar tardios), e `--full-refresh` continua reconsultando 100% da carteira.

3. **Transparência da `Data de Referência dos Pagamentos`:**
   - Persistir `dataReferenciaPagamentos` **por contrato** na ficha individual (`obras/<id>.json`).
   - Manter no cabeçalho principal do painel a `Data de Referência dos Pagamentos` da rodada vigente (aplicável aos contratos ativos), exibindo na **Ficha Limpa da Obra** dos contratos consolidados (*"Pagamentos consolidados em DD/MM/AAAA (vigência encerrada há mais de 12 meses)"*) e na **Nota Metodológica** o funcionamento da regra.

## Opções Consideradas

- **Manter ADR-0007 intacto (reconsultar 100% dos pagamentos toda semana):** Rejeitado porque aumentaria a carga e a exposição a falhas de rede em ~66% a cada semana para reconsultar centenas de contratos encerrados há anos.
- **Usar `dsSituacao == "Concluído"` como critério de congelamento:** Rejeitado porque a fonte oficial não atualiza esse campo (`0` casos em `2017–2024`).
- **Congelar indefinidamente sem revalidação automática (apenas `--full-refresh`):** Rejeitado para não perder pagamentos tardios de restos a pagar caso não haja disparo manual por longos períodos.
- **Limitar a curadoria de `2017–2020` a um piso mínimo em R\$:** Rejeitado em favor da auditoria de 100% dos contratos que caírem em `Escopo Cidade (Não-Localizado)`, preservando o mesmo rigor territorial já aplicado a `2021–2028`.
- **Aplicar deflacionamento (IPCA/INCC) nesta etapa:** Rejeitado para preservar conferência exata centavo a centavo com o Portal da Transparência e evitar acoplar séries econômicas externas à expansão de mandato.

## Consequências

- **Menor carga semanal mesmo com +66% de contratos:** Dos ~1.051 contratos previstos (`2017–2028`), ~834 tendem a operar como consolidados, reduzindo as consultas semanais de pagamentos de 633 para ~217 contratos.
- **Validação por contrato no ETL:** A validação de `data_referencia` em `etl/runner.py` passa a aceitar a data de consolidação salva para contratos elegíveis ao congelamento, preservando a exigência estrita da data da rodada vigente para todos os contratos ativos ou descongelados.
- **Revalidação semestral concentrada:** Contratos consolidados na mesma data expiram o prazo de 180 dias juntos (gerando uma rodada mais longa a cada semestre, já protegida pelo mecanismo de checkpoint e 3 dias de recuperação do ADR-0007).

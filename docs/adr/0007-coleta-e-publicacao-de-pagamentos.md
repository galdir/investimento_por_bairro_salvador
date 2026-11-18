# Coleta e publicação de pagamentos

Status: aceita.

A comparação usa os pagamentos registrados no Portal da Transparência, tomando a própria fonte como referência. Limitações conhecidas da fonte são informadas e os valores correspondentes integram a escala comparativa como parciais. A verificação da coleta se aplica às respostas da fonte para o período consultado.

A coleta usa a exportação JSON `downloadDados` de pagamentos relacionados ao contrato, entre duas consultas à primeira página com o mesmo filtro. Uma consulta é aceita quando as três respostas são válidas, os metadados de paginação e o totalizador `Valor Pago` são estáveis e a contagem e a soma decimal dos valores da exportação conferem com o total e o totalizador da página. A conciliação usa a lista bruta com todos os sinais e ocorrências, antes do corte pela Data de Referência dos Pagamentos. A enumeração paginada apresentou diferenças de conteúdo mesmo com contagem estável. A exportação evita fronteiras de página e, nos casos investigados, conciliou com os metadados e o totalizador.

Usar uma janela em que a unidade gestora e o contrato SIGEF tenham sido retornados pelo grid de Obras Públicas e registrar a janela escolhida. No ensaio, comparar as exportações por ocorrência, preservando multiplicidades, quando o mesmo contrato tiver sido encontrado em mais de uma janela. Definir a regra de escolha a partir desse ensaio. A Data de Referência dos Pagamentos é aplicada localmente, incluindo movimentos no próprio dia.

A ativação da rotina depende de um ensaio da carteira em saída isolada, com conciliação bem-sucedida para todos os contratos e sem divergência entre janelas aplicáveis. Contagem e soma iguais podem corresponder a conjuntos distintos, e as rotas podem compartilhar um limite. O projeto adota a conciliação como critério operacional de aceite após o ensaio, com esse risco residual. Divergência, resposta inválida, falha de coleta ou limite atingido antes da conclusão impedem a publicação.

Uma exportação vazia conciliada com as duas leituras válidas, ambas com total de registros e totalizador iguais a zero, produz zero identificado como ausência de registros encontrados na fonte. Se houver limitação conhecida de cobertura, o zero é apresentado como parcial e identificado pelo período disponível.

Zero por ausência de registros encontrados é distinguido de saldo registrado igual a zero com movimentos que se anulam. Os sinais dos movimentos são preservados na apuração; totais negativos permanecem na comparação e têm representação visual distinta de zero, mantendo as indicações de cobertura e parcialidade aplicáveis.

Os registros são contabilizados como fornecidos pela fonte, mesmo quando compartilham ordem bancária, data e valor ou têm identificadores diferentes. Semelhança não autoriza agrupamento com exclusão provisória da soma; apenas repetições comprovadamente introduzidas pela nossa coleta são removidas, com rastreabilidade da decisão.

A decisão preserva movimentos que a fonte disponibiliza e evita descartar pagamentos reais por semelhança, ao custo de também refletir eventuais duplicações existentes na própria fonte. Essa semelhança, isoladamente, não torna o histórico ou a soma parciais.

Registros informados pelo portal para contratos diferentes são contabilizados nos respectivos contratos, mesmo que sejam semelhantes. A semelhança entre contratos não autoriza sua exclusão automática; as regras territoriais existentes continuam impedindo a duplicação da mesma Obra Pública ou de suas cotas na agregação municipal.

Quando a fonte retornar validamente um registro sem valor, ele permanece acessível e não é convertido em zero: o painel soma os valores numéricos informados e apresenta a quantidade de registros sem valor, sem classificar automaticamente o histórico ou a soma como parciais por esse motivo; se nenhum valor numérico estiver disponível, o valor é informado como indisponível.

Registros que a fonte apresentar com identificação incompleta permanecem acessíveis e seus valores numéricos entram na soma. A ausência de campos de identidade não autoriza sua exclusão nem o agrupamento com outros registros por suposição.

Se não houver informação suficiente sobre a abrangência histórica da fonte, os valores registrados continuam acessíveis e integram a escala comparativa quando a coleta dos resultados disponibilizados foi concluída corretamente. A falta de comprovação independente não é tratada como limitação conhecida da fonte nem como falha de coleta.

Quando um território reunir obras com valores apuráveis e obras sem valor numérico disponível, apenas os valores apuráveis compõem a soma territorial mostrada na escala, acompanhada da indicação das obras sem valor. Se nenhuma obra tiver valor apurável, o território permanece visível como indisponível, sem posição numérica na escala; somas com limitações conhecidas da fonte são identificadas como parciais e não são apresentadas como mínimo pago.

A apuração usa o resultado da consulta válida mais recente, inclusive quando a fonte reduzir valores ou retirar registros; não há referência financeira especial ao último valor completo comprovado. Uma coleta nova não é substituída por listas antigas mais longas ou valores anteriores maiores; somente uma falha de coleta ou processamento conserva integralmente a versão anterior e sua data, sem mesclar pagamentos de atualizações diferentes.

Uma atualização semanal consulta pagamentos independentemente de alterações nos dados contratuais, alterando para esse fim a regra de reaproveitamento incremental do [ADR 0002](0002-coleta-plurianual-incremental-por-mandato.md). Se alguma consulta obrigatória não for concluída ou alguma fonte efetivamente consultada falhar, preservam-se a última versão publicada sem falhas e sua data; a atualização somente é publicada quando concluída sem falhas. A decisão mantém a referência da comparação coerente, ao custo de atrasar a publicação de novos dados quando houver falhas persistentes.

A regra abrange todas as fontes efetivamente consultadas pela rotina de atualização do dashboard, inclusive a malha territorial: falhas não podem ser apresentadas como sucesso por substituição por dados de exemplo. Uma base de referência validada pode ser reutilizada quando esse reuso fizer parte do procedimento planejado, e não como disfarce para uma consulta que falhou.

O escopo de publicação desta mudança é preparar, validar e substituir em conjunto os arquivos de dados e seus metadados, conservando a versão anterior diante de falhas. A atualização concluída se refere a essa versão validada dos dados; o deploy do site permanece no fluxo atual e sua automação não integra esta mudança.

O progresso da coleta é persistido entre execuções para reaproveitar os contratos já concluídos. Na retomada, descarta-se o resultado incompleto do contrato interrompido e reinicia-se a sequência de conciliação a partir da primeira consulta à página. São permitidas até três recuperações, uma por dia nos três dias seguintes à tentativa original. A publicação depende da resolução das falhas pendentes. A interface informa a Data da Última Atualização Concluída e o intervalo de realização das consultas.

A Data de Referência dos Pagamentos é fixada no início da tentativa semanal e mantida em suas recuperações. Movimentos datados depois desse limite ficam para a atualização seguinte; o intervalo real de realização das consultas é informado separadamente, inclusive quando atravessar vários dias, sem pressupor uma fotografia simultânea da fonte.

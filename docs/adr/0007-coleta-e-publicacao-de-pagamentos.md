# Coleta e publicação de pagamentos

Status: proposta, em refinamento.

A comparação usa pagamentos registrados no Portal da Transparência ao longo de todo o histórico do contrato. Quando a coleta terminar sem falhas, mas houver limitação comprovada de cobertura na fonte, os valores encontrados são apresentados como parciais e integram a escala comparativa de Valor Pago por habitante com identificação explícita; valores anteriores sem evidência de cobertura permanecem não verificados.

Uma resposta válida e vazia para um período de cobertura confirmado produz zero registrado nesse período. Se houver lacuna comprovada no restante do histórico contratual, o zero é apresentado como parcial e identificado pelo período coberto; uma resposta inválida ou de cobertura desconhecida não autoriza inferir zero.

Quando registros tiverem identidade ambígua, a atualização concluída poderá contabilizar provisoriamente um representante por grupo; os demais registros ficam disponíveis no detalhamento da obra sem integrar a soma. A cobertura e os valores afetados são identificados como parciais até a identidade ser resolvida; isso não transforma uma falha de coleta em consulta bem-sucedida.

Um grupo provisório exige a mesma Chave Canônica da Obra, ordem bancária, data e valor com o mesmo sinal; empenho e nota de liquidação devem coincidir quando presentes em ambos, ou estar em branco nos dois. Evidência confirmada da fonte de que os registros são movimentos distintos impede agrupá-los; números de ordem bancária iguais, isoladamente, não comprovam duplicidade. Os grupos são reavaliados automaticamente a cada atualização; enquanto não houver evidência suficiente para resolvê-los, a regra provisória e sua sinalização são mantidas, sem depender de análise humana.

Registros informados pelo portal para contratos diferentes são contabilizados nos respectivos contratos, mesmo que sejam semelhantes. A semelhança entre contratos não autoriza sua exclusão automática; as regras territoriais existentes continuam impedindo a duplicação da mesma Obra Pública ou de suas cotas na agregação municipal.

A repetição de identificadores diferentes em atualizações sucessivas, por si só, não comprova que os registros representem movimentos distintos. Quando a fonte retornar validamente um registro sem valor, ele permanece acessível e não é convertido em zero: a soma dos valores disponíveis é parcial, e, se nenhum valor numérico estiver disponível, o valor é informado como indisponível.

Registros que a fonte apresentar sem informações suficientes para formar um grupo de identidade com segurança permanecem acessíveis e fora da soma; a atualização pode ser publicada como parcial, e a conciliação é tentada automaticamente nas atualizações seguintes. Se não houver outros valores apuráveis, o valor é informado como indisponível, não zero.

Se uma consulta válida não permitir verificar o período efetivamente coberto pela fonte, os registros encontrados permanecem acessíveis com cobertura não verificada e não integram a escala comparativa; essa situação não é confundida com uma limitação de cobertura comprovada nem com uma resposta vazia confirmada.

Quando um território reunir obras com valores apuráveis e obras de cobertura não verificada, apenas os valores apuráveis compõem a soma territorial mostrada na escala, identificada como parcial e acompanhada da indicação das obras excluídas. Se nenhuma obra tiver valor apurável, o território permanece visível como indisponível, sem posição numérica na escala; a soma parcial não é apresentada como mínimo pago.

Se uma consulta posterior concluída revelar uma limitação da fonte e seus registros não puderem ser conciliados com segurança com a versão anterior, a comparação apresenta a soma parcial mais recente; o último valor anteriormente apurado com cobertura completa permanece consultável com sua data até ser substituído por outra apuração completa. A data da atualização concluída pode avançar quando as consultas terminarem sem falhas, acompanhada da quantidade de contratos com cobertura parcial.

Uma atualização semanal consulta pagamentos independentemente de alterações nos dados contratuais, alterando para esse fim a regra de reaproveitamento incremental do [ADR 0002](0002-coleta-plurianual-incremental-por-mandato.md). Se alguma consulta falhar, preservam-se a última versão publicada sem falhas e sua data; a atualização somente é publicada quando concluída sem falhas. A decisão mantém a referência da comparação coerente, ao custo de atrasar a publicação de novos dados quando houver falhas persistentes.

A regra abrange todas as fontes efetivamente consultadas pela rotina de atualização do dashboard, inclusive a malha territorial: falhas não podem ser apresentadas como sucesso por substituição por dados de exemplo. Uma base de referência validada pode ser reutilizada quando esse reuso fizer parte do procedimento planejado, e não como disfarce para uma consulta que falhou.

Na retomada, a coleta revalida as páginas do contrato afetado quando não houver garantia de paginação estável; se a consistência não puder ser verificada, sua cobertura permanece incompleta. A interface informa a conclusão da última atualização concluída e o intervalo de realização da consulta, sem apresentar essas datas como a data do pagamento ou uma fotografia simultânea da fonte.

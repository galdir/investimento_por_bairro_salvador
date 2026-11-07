"""Cálculo e agregação de KPIs globais de Obras Públicas de Salvador.

Consolida totalizadores financeiros, contagem de obras ativas e médias de
investimento por habitante em âmbito municipal.
"""

from typing import Any


def calcular_kpis_globais(
    totalizador_transparencia: dict[str, Any],
    obras_detalhadas: list[dict[str, Any]],
    populacao_total_cidade: int,
) -> dict[str, Any]:
    """Calcula os indicadores macroeconômicos e de transparência de Salvador.

    Sumário:
        Consolida o volume financeiro global, total de obras ativas e investimento per capita.

    Descrição Estendida:
        Combina os dados agregados do totalizador oficial da Transparência de Salvador
        com a listagem detalhada de contratos para extrair métricas de execução e calcular
        o Investimento por Habitante médio da cidade (Total Investido dividido pela População
        Residente Total do Censo 2022). Todas as fórmulas utilizam operações de divisão
        protegidas contra divisão por zero.

    Argumentos:
        totalizador_transparencia: Dicionário contendo os totais reportados pela API (/obraspublicas/totalizador).
        obras_detalhadas: Lista de dicionários contendo os contratos detalhados (/obraspublicas/gridDetalhada).
        populacao_total_cidade: Inteiro com a população residente total de Salvador segundo o Censo 2022.

    Retornos:
        Dicionário com a estrutura de KPIs globais contendo:
        - totalObras: Quantidade total de obras registradas.
        - valorTotal: Soma financeira atualizada ou contratada das obras (em Reais).
        - totalAtivas: Quantidade de contratos que estão em execução ou ativos.
        - totalEmpenhado: Valor total empenhado no orçamento municipal.
        - totalLiquidado: Valor total medido e liquidado.
        - totalPago: Valor total pago às empresas.
        - investimentoPorHabitanteCidade: Valor investido dividido pela população residente da cidade.

    Erros:
        Não lança exceções; utiliza valores padrão zero caso os campos estejam ausentes.
    """
    # Extrai totais financeiros fornecidos pelo totalizador
    total_obras = int(totalizador_transparencia.get("totalObras") or len(obras_detalhadas))
    valor_total = float(totalizador_transparencia.get("valorTotal") or 0.0)
    total_empenhado = float(totalizador_transparencia.get("totalEmpenhado") or 0.0)
    total_liquidado = float(totalizador_transparencia.get("totalLiquidado") or 0.0)
    total_pago = float(totalizador_transparencia.get("totalPago") or 0.0)

    # Se o totalizador não trouxe valor financeiro, soma a partir das obras detalhadas
    if valor_total == 0.0 and obras_detalhadas:
        valor_total = sum(float(obra.get("vlAtualizado") or obra.get("vlOriginal") or 0.0) for obra in obras_detalhadas)

    # Contabiliza obras ativas (situação diferente de Concluída, Cancelada ou Rescindida)
    situacoes_inativas = {"CONCLUÍDA", "CONCLUIDA", "CANCELADA", "RESCINDIDA"}
    obras_ativas_count = 0
    for obra in obras_detalhadas:
        situacao = str(obra.get("dsSituacao") or "").strip().upper()
        if situacao not in situacoes_inativas:
            obras_ativas_count += 1

    # Se a lista de obras for menor que o total geral, usa ao menos a contagem observada
    if obras_ativas_count == 0 and total_obras > 0:
        obras_ativas_count = total_obras

    # Fórmula: Investimento por Habitante = Valor Total / População Residente Total
    investimento_por_hab = 0.0
    if populacao_total_cidade > 0:
        investimento_por_hab = round(valor_total / populacao_total_cidade, 2)

    return {
        "totalObras": total_obras,
        "valorTotal": valor_total,
        "totalAtivas": obras_ativas_count,
        "totalEmpenhado": total_empenhado,
        "totalLiquidado": total_liquidado,
        "totalPago": total_pago,
        "investimentoPorHabitanteCidade": investimento_por_hab,
    }

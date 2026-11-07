"""Cálculo e agregação de KPIs globais de Obras Públicas de Salvador.

Consolida totalizadores financeiros, contagem de obras ativas, indicadores
do Semáforo da Obra (críticas e atrasadas), aditivos contratuais e médias de
investimento por habitante em âmbito municipal.
"""

from typing import Any
from etl.domain.semaforo import classificar_semaforo


def calcular_kpis_globais(
    totalizador_transparencia: dict[str, Any],
    obras_detalhadas: list[dict[str, Any]],
    populacao_total_cidade: int,
) -> dict[str, Any]:
    """Calcula os indicadores macroeconômicos e de transparência de Salvador.

    Sumário:
        Consolida volume financeiro, obras ativas, críticas, aditivos e investimento per capita.

    Descrição Estendida:
        Combina os dados agregados do totalizador oficial da Transparência de Salvador
        com a listagem detalhada de contratos para extrair métricas de execução e calcular:
        - Total Investido global e obras ativas;
        - Contagem e percentual de obras críticas/atrasadas (Semáforo Vermelho);
        - Volume financeiro total de aditivos de valor e acréscimo percentual médio;
        - Investimento por Habitante médio da cidade (Total Investido dividido pela População
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
        - totalCriticas: Quantidade de obras com classificação Vermelho (Crítica).
        - percentualCriticas: Percentual de obras críticas em relação ao total de obras.
        - totalAditivosValor: Soma financeira de acréscimos via aditivos contratuais de valor (em Reais).
        - percentualMedioAditivos: Variação percentual média de aditivos em relação ao valor original.
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
    obras_criticas_count = 0
    total_aditivos_reais = 0.0
    deltas_percentuais: list[float] = []

    for obra in obras_detalhadas:
        situacao = str(obra.get("dsSituacao") or obra.get("situacao") or "").strip().upper()
        if situacao not in situacoes_inativas:
            obras_ativas_count += 1

        # Classificação do Semáforo para aferir obras críticas
        semaforo = obra.get("semaforo")
        if not semaforo:
            semaforo = classificar_semaforo(obra)

        if semaforo.get("status") == "VERMELHO":
            obras_criticas_count += 1

        # Aditivos de valor
        vl_orig = float(obra.get("vlOriginal") or obra.get("valorOriginal") or 0.0)
        vl_atua = float(obra.get("vlAtualizado") or obra.get("valorContratualVigente") or vl_orig)
        if vl_atua > vl_orig:
            total_aditivos_reais += (vl_atua - vl_orig)

        if vl_orig > 0:
            delta_perc = ((vl_atua - vl_orig) / vl_orig) * 100.0
            deltas_percentuais.append(delta_perc)

    # Se a lista de obras for menor que o total geral, usa ao menos a contagem observada
    if obras_ativas_count == 0 and total_obras > 0:
        obras_ativas_count = total_obras

    percentual_criticas = 0.0
    total_para_percentual = len(obras_detalhadas) if obras_detalhadas else total_obras
    if total_para_percentual > 0:
        percentual_criticas = round((obras_criticas_count / total_para_percentual) * 100.0, 1)

    percentual_medio_aditivos = 0.0
    if deltas_percentuais:
        percentual_medio_aditivos = round(sum(deltas_percentuais) / len(deltas_percentuais), 1)

    # Fórmula: Investimento por Habitante = Valor Total / População Residente Total
    investimento_por_hab = 0.0
    if populacao_total_cidade > 0:
        investimento_por_hab = round(valor_total / populacao_total_cidade, 2)

    return {
        "totalObras": total_obras,
        "valorTotal": valor_total,
        "totalAtivas": obras_ativas_count,
        "totalCriticas": obras_criticas_count,
        "percentualCriticas": percentual_criticas,
        "totalAditivosValor": round(total_aditivos_reais, 2),
        "percentualMedioAditivos": percentual_medio_aditivos,
        "totalEmpenhado": total_empenhado,
        "totalLiquidado": total_liquidado,
        "totalPago": total_pago,
        "investimentoPorHabitanteCidade": investimento_por_hab,
    }

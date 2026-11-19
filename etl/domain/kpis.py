"""Cálculo e agregação de KPIs globais de Obras Públicas de Salvador.

Consolida totalizadores financeiros, contagem de obras ativas, indicadores
do Semáforo da Obra (críticas e atrasadas), aditivos contratuais, médias de
investimento por habitante em âmbito municipal e transparência opaca (Escopo Cidade).
"""

from typing import Any, Optional
from etl.domain.empreiteiras import SITUACOES_INATIVAS
from etl.domain.semaforo import classificar_semaforo
from etl.domain.territorio import extrair_status_semaforo, parse_float


def calcular_kpis_globais(
    totalizador_transparencia: dict[str, Any],
    obras_detalhadas: list[dict[str, Any]],
    populacao_total_cidade: int,
    indicador_opacidade: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Calcula os indicadores macroeconômicos e de transparência de Salvador.

    Sumário:
        Consolida volume financeiro, obras ativas, críticas, aditivos, investimento per capita e opacidade.

    Descrição Estendida:
        Combina os dados agregados do totalizador oficial da Transparência de Salvador
        com a listagem detalhada de contratos para extrair métricas de execução e calcular:
        - Total Investido global e obras ativas;
        - Contagem e percentual de obras críticas/atrasadas (Semáforo Vermelho);
        - Volume financeiro total de aditivos de valor e acréscimo percentual médio;
        - Investimento por Habitante médio da cidade (Total Investido dividido pela População
          Residente Total do Censo 2022);
        - Indicador de Transparência Opaca: volume financeiro e percentual de contratos classificados
          como Escopo Cidade (Não-Localizado) que não possuem endereço ou lote regional mapeado.

    Argumentos:
        totalizador_transparencia: Dicionário contendo os totais reportados pela API (/obraspublicas/totalizador).
        obras_detalhadas: Lista de dicionários contendo os contratos detalhados (/obraspublicas/gridDetalhada).
        populacao_total_cidade: Inteiro com a população residente total de Salvador segundo o Censo 2022.
        indicador_opacidade: Dicionário opcional contendo métricas calculadas de transparência opaca.

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
        - totalNaoLocalizado: Quantidade de obras em Escopo Cidade (Não-Localizado).
        - valorNaoLocalizado: Volume financeiro em contratos sem alocação territorial identificada.
        - percentualNaoLocalizado: Percentual do total financeiro que está em transparência opaca.

    Erros:
        Não lança exceções; utiliza valores padrão zero caso os campos estejam ausentes.
    """
    # Extrai totais financeiros fornecidos pelo totalizador
    total_obras = int(totalizador_transparencia.get("totalObras") or len(obras_detalhadas))
    valor_total = parse_float(
        totalizador_transparencia.get("valorTotal")
        or totalizador_transparencia.get("Valor Contratual (Atualizado)")
    )
    total_empenhado = parse_float(
        totalizador_transparencia.get("totalEmpenhado")
        or totalizador_transparencia.get("Empenhado no Período")
    )
    total_liquidado = parse_float(
        totalizador_transparencia.get("totalLiquidado")
        or totalizador_transparencia.get("Liquidado no período")
    )
    total_pago = parse_float(
        totalizador_transparencia.get("totalPago")
        or totalizador_transparencia.get("Pago no período")
    )

    # Somas reais apuradas na carteira de obras públicas
    soma_obras = sum(
        parse_float(obra.get("vlAtualizado") or obra.get("valorContratualVigente") or obra.get("vlOriginal") or 0.0)
        for obra in obras_detalhadas
    )
    soma_empenhado = round(
        sum(
            parse_float(obra.get("vlEmpenhado") or obra.get("valorEmpenhado") or 0.0)
            for obra in obras_detalhadas
        ),
        2,
    )
    soma_liquidado = round(
        sum(
            parse_float(obra.get("vlLiquidado") or obra.get("valorLiquidado") or 0.0)
            for obra in obras_detalhadas
        ),
        2,
    )
    soma_pago = round(
        sum(
            parse_float(obra["vlPagoReal"])
            if "vlPagoReal" in obra
            else parse_float(obra.get("vlPago") or obra.get("valorPago") or 0.0)
            for obra in obras_detalhadas
        ),
        2,
    )
    count_obras = len(obras_detalhadas)
    carteira_completa = count_obras > 0 and (
        total_obras == 0 or count_obras >= total_obras or soma_obras > valor_total
    )

    if valor_total == 0.0 and obras_detalhadas:
        valor_total = round(soma_obras, 2)
    elif carteira_completa:
        # Quando a carteira consolidada cobre o universo completo de obras, adota os totais apurados
        valor_total = round(soma_obras, 2)
        total_obras = count_obras

    if carteira_completa:
        total_empenhado = soma_empenhado
        total_liquidado = soma_liquidado
        total_pago = soma_pago
    else:
        if soma_empenhado > 0 and (total_empenhado == 0.0 or soma_empenhado > total_empenhado):
            total_empenhado = soma_empenhado
        if soma_liquidado > 0 and (total_liquidado == 0.0 or soma_liquidado > total_liquidado):
            total_liquidado = soma_liquidado
        if soma_pago > 0 and (total_pago == 0.0 or soma_pago > total_pago):
            total_pago = soma_pago

    # Consultas concluídas substituem o totalizador, inclusive com saldo zero ou negativo.
    if obras_detalhadas and all("vlPagoReal" in obra for obra in obras_detalhadas):
        total_pago = soma_pago

    # Contabiliza obras ativas (situação diferente de Concluída, Cancelada, Rescindida ou Paralisada)
    obras_ativas_count = 0
    obras_criticas_count = 0
    total_aditivos_reais = 0.0
    deltas_percentuais: list[float] = []

    for obra in obras_detalhadas:
        situacao = str(obra.get("dsSituacao") or obra.get("situacao") or "").strip().upper()
        if situacao not in SITUACOES_INATIVAS:
            obras_ativas_count += 1

        # Classificação do Semáforo para aferir obras críticas
        semaforo = obra.get("semaforo")
        if not semaforo:
            semaforo = classificar_semaforo(obra)

        if extrair_status_semaforo(semaforo) == "VERMELHO":
            obras_criticas_count += 1

        # Aditivos de valor
        vl_orig = parse_float(obra.get("vlOriginal") or obra.get("valorOriginal") or 0.0)
        vl_atua = parse_float(obra.get("vlAtualizado") or obra.get("valorContratualVigente") or vl_orig)
        if vl_atua > vl_orig:
            total_aditivos_reais += (vl_atua - vl_orig)

        if vl_orig > 0:
            delta_perc = ((vl_atua - vl_orig) / vl_orig) * 100.0
            deltas_percentuais.append(delta_perc)

    total_ativas_transp = totalizador_transparencia.get("totalAtivas")
    if total_ativas_transp is not None and not carteira_completa:
        obras_ativas_count = int(total_ativas_transp)
    elif obras_ativas_count == 0 and total_obras > 0 and not obras_detalhadas:
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

    # Indicador de Transparência Opaca (Escopo Cidade)
    total_nao_localizado = 0
    valor_nao_localizado = 0.0
    valor_pago_nao_localizado = 0.0
    percentual_nao_localizado = 0.0

    if indicador_opacidade:
        total_nao_localizado = int(indicador_opacidade.get("totalNaoLocalizado", 0))
        valor_nao_localizado = float(indicador_opacidade.get("valorNaoLocalizado", 0.0))
        valor_pago_nao_localizado = float(indicador_opacidade.get("valorPagoNaoLocalizado", 0.0))
        if valor_total > 0:
            percentual_nao_localizado = round((valor_nao_localizado / valor_total) * 100.0, 1)
        else:
            percentual_nao_localizado = float(indicador_opacidade.get("percentualNaoLocalizado", 0.0))

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
        "obrasSemValorPago": sum(
            1 for obra in obras_detalhadas
            if (obra.get("vlPagoReal") if "vlPagoReal" in obra else obra.get("vlPago", obra.get("valorPago"))) is None
        ),
        "investimentoPorHabitanteCidade": investimento_por_hab,
        "totalNaoLocalizado": total_nao_localizado,
        "valorNaoLocalizado": valor_nao_localizado,
        "valorPagoNaoLocalizado": round(valor_pago_nao_localizado, 2),
        "percentualNaoLocalizado": percentual_nao_localizado,
    }

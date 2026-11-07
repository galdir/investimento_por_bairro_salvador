"""Máquina de estados determinística do Semáforo da Obra de Salvador.

Classifica o nível de risco e conformidade contratual de cada Obra Pública
em três estados hierárquicos: Vermelho (Crítica), Amarelo (Atenção) ou Verde (No Prazo).
"""

from datetime import date, datetime
from typing import Any, Optional


def parse_iso_date(data_str: Any) -> Optional[date]:
    """Converte strings no padrão ISO ou datas parciais em objeto date.

    Sumário:
        Extrai um objeto date a partir de strings de data retornadas pela API da Transparência.

    Descrição Estendida:
        Lida com formatos como '2025-12-31T00:00:00.000Z', '2025-12-31' ou valores date já instanciados.
        Caso o valor seja nulo, vazio ou inválido, retorna None de maneira segura.

    Argumentos:
        data_str: String de data ou objeto date/datetime.

    Retornos:
        Objeto date ou None se a conversão não for possível.

    Erros:
        Não lança exceções; retorna None em caso de formato inválido.
    """
    if not data_str:
        return None
    if isinstance(data_str, date) and not isinstance(data_str, datetime):
        return data_str
    if isinstance(data_str, datetime):
        return data_str.date()

    limpo = str(data_str).strip()
    if not limpo:
        return None

    # Tenta extrair a parte 'YYYY-MM-DD'
    try:
        data_apenas = limpo.split("T")[0]
        return datetime.strptime(data_apenas, "%Y-%m-%d").date()
    except Exception:
        return None


def classificar_semaforo(
    obra: dict[str, Any],
    data_referencia: Optional[date] = None,
) -> dict[str, Any]:
    """Aplica a máquina de estados determinística do Semáforo da Obra.

    Sumário:
        Avalia as condições contratuais, temporais e financeiras para definir a cor do semáforo.

    Descrição Estendida:
        A classificação é avaliada em ordem estrita de prioridade (Vermelho > Amarelo > Verde):
        1. Vermelho (Crítica):
           - Situação cadastral paralisada, suspensa ou rescindida;
           - Data de término de vigência atualizada vencida em relação à data de referência com execução física < 100%;
           - Aditivo acumulado de valor superior a 25.0% em relação ao valor original contratado;
           - Contrato em execução sem qualquer medição/liquidação ou pagamento há mais de 90 dias.
        2. Amarelo (Atenção):
           - Data de término de vigência atualizada estendida para além do término de vigência original;
           - Registro de termo aditivo de prorrogação de prazo;
           - Aditivo acumulado de valor entre 10.0% e 25.0% (inclusive).
        3. Verde (No Prazo):
           - Todas as demais obras dentro do cronograma original e com aditivo de valor abaixo de 10.0%.

    Argumentos:
        obra: Dicionário contendo os atributos do contrato de obra pública.
        data_referencia: Data civil de corte para cálculo de atrasos (padrão: data de hoje).

    Retornos:
        Dicionário com o resultado da classificação contendo:
        - status: String canônica ('VERMELHO', 'AMARELO' ou 'VERDE').
        - rotulo: Descrição amigável para exibição em interface ('Vermelho (Crítica)', etc.).
        - motivos: Lista de strings explicando as regras disparadas.
        - deltaPercentualValor: Float com a variação percentual do valor atualizado sobre o original.

    Erros:
        Não lança exceções; trata valores ausentes com valores padrão seguros.
    """
    hoje = data_referencia or date.today()

    # 1. Extração e cálculo de valores financeiros
    vl_original = float(obra.get("vlOriginal") or obra.get("valorOriginal") or 0.0)
    vl_atualizado = float(obra.get("vlAtualizado") or obra.get("valorContratualVigente") or vl_original or 0.0)

    # Cálculo da variação percentual de aditivos: ((vlAtualizado - vlOriginal) / vlOriginal) * 100
    delta_percentual_valor = 0.0
    if vl_original > 0:
        delta_percentual_valor = round(((vl_atualizado - vl_original) / vl_original) * 100.0, 2)

    # 2. Extração de percentual executado e situação
    percentual_executado = float(obra.get("percentualExecutado") or 0.0)
    situacao = str(obra.get("dsSituacao") or obra.get("situacao") or "").strip().upper()

    # 3. Extração e conversão de datas de vigência
    dt_fim_original = parse_iso_date(obra.get("dtFimVigenciaOriginal"))
    dt_termino_atualizado = parse_iso_date(
        obra.get("dtTerminoVigenciaAtualizado") or obra.get("dtFimVigenciaAtualizado") or dt_fim_original
    )

    # 4. Inatividade financeira em dias
    dias_sem_pagamento = obra.get("dias_desde_ultima_liquidacao_ou_pagamento")
    if dias_sem_pagamento is None:
        dias_sem_pagamento = 0
    else:
        dias_sem_pagamento = int(dias_sem_pagamento)

    possui_aditivo_prazo = bool(obra.get("possui_aditivo_de_prazo") or obra.get("possuiAditivoPrazo"))

    motivos: list[str] = []

    # -------------------------------------------------------------
    # GATILHOS DA COR VERMELHO (CRÍTICA)
    # -------------------------------------------------------------
    # A. Situação cadastral problemática
    situacoes_criticas = {"PARALISADA", "PARALISADO", "SUSPENSA", "SUSPENSO", "RESCINDIDA", "RESCINDIDO"}
    if any(s in situacao for s in situacoes_criticas):
        motivos.append(f"Contrato com situação cadastral de alerta ({obra.get('dsSituacao') or obra.get('situacao')})")

    # B. Prazo de vigência atualizado vencido e obra com medição física incompleta (< 100%)
    if dt_termino_atualizado and hoje > dt_termino_atualizado and percentual_executado < 100.0:
        motivos.append(
            f"Vigência expirada em {dt_termino_atualizado.strftime('%d/%m/%Y')} com execução física incompleta ({percentual_executado}%)"
        )

    # C. Aditivo de valor acumulado superior a 25% do valor original
    if delta_percentual_valor > 25.0:
        motivos.append(
            f"Aditivo de valor superior a 25% (+{delta_percentual_valor}%) acumulado em relação ao contrato original"
        )

    # D. Obra ativa em execução sem liquidação ou pagamento há mais de 90 dias
    if ("EXECUCAO" in situacao or "EXECUÇÃO" in situacao) and dias_sem_pagamento > 90:
        motivos.append(
            f"Obra em execução sem movimentação de liquidação ou pagamento há mais de 90 dias ({dias_sem_pagamento} dias)"
        )

    if motivos:
        return {
            "status": "VERMELHO",
            "rotulo": "Vermelho (Crítica)",
            "motivos": motivos,
            "deltaPercentualValor": delta_percentual_valor,
        }

    # -------------------------------------------------------------
    # GATILHOS DA COR AMARELO (ATENÇÃO)
    # -------------------------------------------------------------
    # A. Vigência atualizada postergada em relação ao prazo original contratado
    if dt_termino_atualizado and dt_fim_original and dt_termino_atualizado > dt_fim_original:
        motivos.append(
            f"Prorrogação de prazo concedida: término estendido de {dt_fim_original.strftime('%d/%m/%Y')} para {dt_termino_atualizado.strftime('%d/%m/%Y')}"
        )

    # B. Registro de aditivo de prazo
    if possui_aditivo_prazo:
        motivos.append("Contrato possui termo aditivo de prorrogação de prazo formalizado")

    # C. Aditivo de valor expressivo entre 10% e 25%
    if 10.0 <= delta_percentual_valor <= 25.0:
        motivos.append(
            f"Aditivos de valor acumulados entre 10% e 25% (+{delta_percentual_valor}%) em relação ao contrato original"
        )

    if motivos:
        return {
            "status": "AMARELO",
            "rotulo": "Amarelo (Atenção)",
            "motivos": motivos,
            "deltaPercentualValor": delta_percentual_valor,
        }

    # -------------------------------------------------------------
    # GATILHO DA COR VERDE (NO PRAZO)
    # -------------------------------------------------------------
    return {
        "status": "VERDE",
        "rotulo": "Verde (No Prazo)",
        "motivos": ["Obra dentro do cronograma contratual vigente e com variação de aditivos inferior a 10%"],
        "deltaPercentualValor": delta_percentual_valor,
    }

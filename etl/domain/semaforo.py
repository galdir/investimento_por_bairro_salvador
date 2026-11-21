"""Máquina de estados determinística do Semáforo da Obra de Salvador.

Classifica o nível de risco e conformidade contratual de cada Obra Pública
em três estados hierárquicos: Vermelho (Crítica), Amarelo (Atenção) ou Verde (No Prazo).
"""

import copy
from datetime import date, datetime
import re
from typing import Any, Optional
import unicodedata

from etl.domain.territorio import parse_float

_LIMIAR_EXECUCAO_SUBSTANCIAL = 95.0
_SITUACOES_CRITICAS = {
    "PARALISADA",
    "PARALISADO",
    "SUSPENSA",
    "SUSPENSO",
    "RESCINDIDA",
    "RESCINDIDO",
    "CANCELADA",
    "CANCELADO",
}


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

    # Tenta extrair a parte 'YYYY-MM-DD' ou 'DD/MM/YYYY'
    try:
        if "/" in limpo:
            m_br = re.match(r"^(\d{2})/(\d{2})/(\d{4})", limpo)
            if m_br:
                return datetime.strptime(m_br.group(0), "%d/%m/%Y").date()
        data_apenas = limpo.split("T")[0]
        return datetime.strptime(data_apenas, "%Y-%m-%d").date()
    except Exception:
        return None


def _normalizar_texto(texto: Any) -> str:
    """Remove acentos e converte texto para minúsculas."""
    decomposto = unicodedata.normalize("NFKD", str(texto or ""))
    sem_acentos = "".join(c for c in decomposto if not unicodedata.combining(c))
    return sem_acentos.strip().lower()


def _aditivo_eh_prorrogacao_prazo(aditivo: dict[str, Any]) -> bool:
    """Identifica se o aditivo formaliza prorrogação de prazo."""
    tipo = _normalizar_texto(aditivo.get("dsTipoAlteracao") or aditivo.get("tipoAlteracao"))
    return "prorrogacao" in tipo and "prazo" in tipo


def _extrair_datas_movimentacao(ficha: dict[str, Any]) -> list[date]:
    """Coleta datas válidas de liquidações e pagamentos da Ficha Limpa consolidada."""
    datas: list[date] = []
    for liq in ficha.get("liquidacoes") or []:
        if isinstance(liq, dict):
            dt = parse_iso_date(liq.get("dataLiquidacao") or liq.get("dtLiquidacao"))
            if dt is not None:
                datas.append(dt)
    for pag in ficha.get("pagamentos") or []:
        if isinstance(pag, dict):
            dt = parse_iso_date(pag.get("dataPagamento") or pag.get("dtPagamento"))
            if dt is not None:
                datas.append(dt)
    return datas


def enriquecer_sinais_semaforo(
    obra: dict[str, Any],
    ficha: Optional[dict[str, Any]] = None,
    data_referencia: Optional[date | str] = None,
) -> dict[str, Any]:
    """Enriquece uma cópia da obra com sinais de prazo e inatividade da Ficha Limpa.

    Argumentos:
        obra: Dicionário base do contrato de obra pública.
        ficha: Ficha Limpa consolidada com vigência, aditivos, liquidações e pagamentos.
        data_referencia: Data civil de corte (objeto date ou string válida; padrão: hoje).

    Retornos:
        Nova cópia do dicionário da obra pronta para o classificador, sem mutar as entradas.
    """
    enriquecida = copy.deepcopy(obra)
    ficha_dict = ficha if isinstance(ficha, dict) else {}
    vigencia = ficha_dict.get("vigencia")
    vigencia_dict = vigencia if isinstance(vigencia, dict) else {}

    if not enriquecida.get("dtFimVigenciaOriginal") and vigencia_dict.get("dataFimOriginal"):
        enriquecida["dtFimVigenciaOriginal"] = vigencia_dict["dataFimOriginal"]

    if (
        not (enriquecida.get("dtTerminoVigenciaAtualizado") or enriquecida.get("dtFimVigenciaAtualizado"))
        and vigencia_dict.get("dataTerminoAtualizado")
    ):
        enriquecida["dtTerminoVigenciaAtualizado"] = vigencia_dict["dataTerminoAtualizado"]

    if not (enriquecida.get("dtInicioVigencia") or enriquecida.get("dataInicio")) and vigencia_dict.get("dataInicio"):
        enriquecida["dtInicioVigencia"] = vigencia_dict["dataInicio"]

    aditivos = ficha_dict.get("aditivos") or []
    possui_aditivo_prazo = bool(
        enriquecida.get("possui_aditivo_de_prazo") or enriquecida.get("possuiAditivoPrazo")
    )
    if any(isinstance(ad, dict) and _aditivo_eh_prorrogacao_prazo(ad) for ad in aditivos):
        possui_aditivo_prazo = True
    enriquecida["possui_aditivo_de_prazo"] = possui_aditivo_prazo

    ref_date = parse_iso_date(data_referencia) or date.today()
    datas_mov = _extrair_datas_movimentacao(ficha_dict)
    if datas_mov:
        dias_inatividade = max(0, (ref_date - max(datas_mov)).days)
    else:
        dt_inicio = parse_iso_date(
            enriquecida.get("dtInicioVigencia")
            or enriquecida.get("dataInicio")
            or vigencia_dict.get("dataInicio")
        )
        dias_inatividade = max(0, (ref_date - dt_inicio).days) if dt_inicio is not None else 0

    enriquecida["dias_desde_ultima_liquidacao_ou_pagamento"] = dias_inatividade
    return enriquecida


def classificar_semaforo(
    obra: dict[str, Any],
    data_referencia: Optional[date | str] = None,
) -> dict[str, Any]:
    """Aplica a máquina de estados determinística do Semáforo da Obra.

    Sumário:
        Avalia as condições contratuais, temporais e financeiras para definir a cor do semáforo.

    Descrição Estendida:
        A classificação é avaliada em ordem estrita de prioridade (Vermelho > Amarelo > Verde),
        preservando os motivos de atenção (Amarelo) após os motivos críticos em obras Vermelhas:
        1. Vermelho (Crítica):
           - Situação cadastral paralisada, suspensa, rescindida ou cancelada;
           - Data de término de vigência efetiva vencida em relação à data de referência com execução física < 95%;
           - Variação Contratual Acumulada superior a 25.0% em relação ao valor original contratado;
           - Contrato em execução dentro da vigência efetiva (execução < 95%) sem liquidação ou pagamento há mais de 90 dias.
        2. Amarelo (Atenção):
           - Data de término de vigência atualizada estendida para além do término de vigência original;
           - Registro de termo aditivo de prorrogação de prazo;
           - Variação Contratual Acumulada entre 10.0% e 25.0% (inclusive).
        3. Verde (No Prazo):
           - Todas as demais obras dentro do cronograma vigente (ou com execução >= 95% sem outros alertas)
             e com Variação Contratual Acumulada inferior a 10.0%.

    Argumentos:
        obra: Dicionário contendo os atributos do contrato de obra pública.
        data_referencia: Data civil de corte para cálculo de atrasos (objeto date ou string válida; padrão: hoje).

    Retornos:
        Dicionário com o resultado da classificação contendo:
        - status: String canônica ('VERMELHO', 'AMARELO' ou 'VERDE').
        - rotulo: Descrição amigável para exibição em interface ('Vermelho (Crítica)', etc.).
        - motivos: Lista de strings explicando as regras disparadas.
        - deltaPercentualValor: Float com a variação percentual do valor atualizado sobre o original.

    Erros:
        Não lança exceções; trata valores ausentes com valores padrão seguros.
    """
    hoje = parse_iso_date(data_referencia) or date.today()

    # 1. Extração e cálculo de valores financeiros (Variação Contratual Acumulada)
    vl_original = parse_float(obra.get("vlOriginal") or obra.get("valorOriginal") or 0.0)
    vl_atualizado = parse_float(obra.get("vlAtualizado") or obra.get("valorContratualVigente") or vl_original or 0.0)

    delta_percentual_valor = 0.0
    if vl_original > 0:
        delta_percentual_valor = round(((vl_atualizado - vl_original) / vl_original) * 100.0, 2)

    # 2. Extração de percentual executado e situação
    percentual_executado = parse_float(obra.get("percentualExecutado") or 0.0)
    situacao = str(obra.get("dsSituacao") or obra.get("situacao") or "").strip().upper()

    # 3. Extração e conversão de datas de vigência
    dt_fim_original = parse_iso_date(obra.get("dtFimVigenciaOriginal"))
    dt_termino_atualizado = parse_iso_date(
        obra.get("dtTerminoVigenciaAtualizado") or obra.get("dtFimVigenciaAtualizado") or dt_fim_original
    )

    # 4. Inatividade financeira em dias
    dias_sem_pagamento = obra.get("dias_desde_ultima_liquidacao_ou_pagamento")
    dias_sem_pagamento = 0 if dias_sem_pagamento is None else int(dias_sem_pagamento)

    possui_aditivo_prazo = bool(obra.get("possui_aditivo_de_prazo") or obra.get("possuiAditivoPrazo"))

    motivos_criticos: list[str] = []
    motivos_atencao: list[str] = []

    # -------------------------------------------------------------
    # GATILHOS DA COR VERMELHO (CRÍTICA)
    # -------------------------------------------------------------
    if any(s in situacao for s in _SITUACOES_CRITICAS):
        motivos_criticos.append(
            f"Contrato com situação cadastral de alerta ({obra.get('dsSituacao') or obra.get('situacao')})"
        )

    if dt_termino_atualizado and hoje > dt_termino_atualizado and percentual_executado < _LIMIAR_EXECUCAO_SUBSTANCIAL:
        motivos_criticos.append(
            f"Vigência expirada em {dt_termino_atualizado.strftime('%d/%m/%Y')} com execução física incompleta ({percentual_executado}%)"
        )

    if delta_percentual_valor > 25.0:
        motivos_criticos.append(
            f"Variação Contratual Acumulada superior a 25% (+{delta_percentual_valor}%) em relação ao contrato original"
        )

    em_execucao = "EXECUCAO" in situacao or "EXECUÇÃO" in situacao
    vigencia_ativa = dt_termino_atualizado is not None and hoje <= dt_termino_atualizado
    if em_execucao and vigencia_ativa and percentual_executado < _LIMIAR_EXECUCAO_SUBSTANCIAL and dias_sem_pagamento > 90:
        motivos_criticos.append(
            f"Obra em execução sem movimentação de liquidação ou pagamento há mais de 90 dias ({dias_sem_pagamento} dias)"
        )

    # -------------------------------------------------------------
    # GATILHOS DA COR AMARELO (ATENÇÃO)
    # -------------------------------------------------------------
    if dt_termino_atualizado and dt_fim_original and dt_termino_atualizado > dt_fim_original:
        motivos_atencao.append(
            f"Prorrogação de prazo concedida: término estendido de {dt_fim_original.strftime('%d/%m/%Y')} para {dt_termino_atualizado.strftime('%d/%m/%Y')}"
        )

    if possui_aditivo_prazo:
        motivos_atencao.append("Contrato possui termo aditivo de prorrogação de prazo formalizado")

    if 10.0 <= delta_percentual_valor <= 25.0:
        motivos_atencao.append(
            f"Variação Contratual Acumulada entre 10% e 25% (+{delta_percentual_valor}%) em relação ao contrato original"
        )

    if motivos_criticos:
        return {
            "status": "VERMELHO",
            "rotulo": "Vermelho (Crítica)",
            "motivos": motivos_criticos + motivos_atencao,
            "deltaPercentualValor": delta_percentual_valor,
        }

    if motivos_atencao:
        return {
            "status": "AMARELO",
            "rotulo": "Amarelo (Atenção)",
            "motivos": motivos_atencao,
            "deltaPercentualValor": delta_percentual_valor,
        }

    return {
        "status": "VERDE",
        "rotulo": "Verde (No Prazo)",
        "motivos": [
            "Obra dentro do cronograma contratual vigente e com Variação Contratual Acumulada inferior a 10%"
        ],
        "deltaPercentualValor": delta_percentual_valor,
    }

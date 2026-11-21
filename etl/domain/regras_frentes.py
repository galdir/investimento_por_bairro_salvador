"""Guardrails compartilhados e avaliação declarativa de Regras de Frente Auditada."""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

from etl.domain.pagamentos import valor_informado_pagamento
from etl.domain.territorio import normalizar_nome, normalizar_nome_prefeitura_bairro, parse_float

_REGEX_CODIGO_OBRA = re.compile(r"(?<![A-Z0-9])(?:[EDMP]\s*\d+|OBRA\s*\d+)(?![A-Z0-9])")
_REGEX_PONTO_VIRGULA_MULTI_OBRA = re.compile(
    r";\s*(?:"
    r"[EDMP]\s*\d+(?![A-Z0-9])"
    r"|OBRA\s*\d+(?![A-Z0-9])"
    r"|(?:RUA|AV|TRAV|LADEIRA|PRACA)(?![A-Z0-9])"
    r"|(?:SERV|DREN|REQUALIF|PAV)[A-Z0-9]*"
    r"|CONT(?!R)(?!\.?\s*\d)[A-Z0-9]*"
    r")"
)
_REGEX_MARCADOR_FECHAMENTO = re.compile(
    r"(?<![A-Z0-9])(?:CONT\.|(?:NFSE|NF-E|NFE|NF|CONTR|CT|PER|BM|CEI|CNO|PROC|SALVADOR/BA|SSA/BA)(?![A-Z0-9]))"
)
_REGEX_ESTORNO = re.compile(r"(?<![A-Z0-9])(?:ESTORN|ANUL|CANCEL)")
_PONTUACAO_PENDENTE = {",", ";", "-", "/", ":"}


def agrupar_pagamentos_por_nota(pagamentos: Optional[list[dict[str, Any]]]) -> dict[str, Optional[float]]:
    """Agrupa e soma valores informados de pagamento por número de nota de liquidação."""
    pagamentos_por_nl: dict[str, Optional[float]] = {}
    for pag in pagamentos or []:
        if not isinstance(pag, dict):
            continue
        nl_pag = str(pag.get("notaLiquidacao") or "").strip()
        if not nl_pag:
            continue
        valor = valor_informado_pagamento(pag)
        if valor in (None, ""):
            pagamentos_por_nl.setdefault(nl_pag, None)
        else:
            pagamentos_por_nl[nl_pag] = (pagamentos_por_nl.get(nl_pag) or 0.0) + parse_float(valor)
    return pagamentos_por_nl


def avaliar_guardrails_nota_liquidacao(
    nota: dict[str, Any],
    *,
    pagamentos: Optional[list[dict[str, Any]]] = None,
    pagamentos_por_nl: Optional[dict[str, Optional[float]]] = None,
) -> list[str]:
    """Avalia travas rígidas de integridade sobre uma nota de liquidação.

    Retorna uma lista ordenada de códigos de bloqueio (vazia quando a nota está liberada):
    - ``multi_obra``: 2+ códigos de obra ou ``;`` introduzindo nova frente/logradouro.
    - ``truncamento_ambiguo``: texto bruto >= 88 chars com pontuação pendente/parêntese aberto
      ou na faixa 88..91 chars sem marcador de fechamento nos últimos 30 caracteres.
    - ``estorno_ou_saldo_nao_positivo``: radical de estorno/anulação/cancelamento,
      ``valLiqLiquidacao <= 0`` ou soma de pagamentos vinculados ``<= 0``.
    """
    motivos: list[str] = []
    texto_bruto = str(nota.get("descObsLiquidacao") or "").strip()
    texto_norm = normalizar_nome(texto_bruto)

    # (a) Multi-obra
    codigos_obra = _REGEX_CODIGO_OBRA.findall(texto_norm)
    if len(codigos_obra) >= 2 or _REGEX_PONTO_VIRGULA_MULTI_OBRA.search(texto_norm):
        motivos.append("multi_obra")

    # (b) Truncamento ambíguo
    comp = len(texto_bruto)
    if comp >= 88:
        tem_pendencia = (
            texto_bruto[-1] in _PONTUACAO_PENDENTE
            or texto_bruto.endswith("(")
            or texto_bruto.count("(") > texto_bruto.count(")")
        )
        if tem_pendencia:
            motivos.append("truncamento_ambiguo")
        elif 88 <= comp <= 91:
            trecho_final = normalizar_nome(texto_bruto[-30:])
            if not _REGEX_MARCADOR_FECHAMENTO.search(trecho_final):
                motivos.append("truncamento_ambiguo")

    # (c) Estorno ou saldo não positivo
    val_liq = parse_float(nota.get("valLiqLiquidacao") or 0.0)
    estorno_texto = bool(_REGEX_ESTORNO.search(texto_norm))
    saldo_pag_nao_positivo = False
    if pagamentos_por_nl is not None or pagamentos is not None:
        nl = str(nota.get("notaLiquidacao") or "").strip()
        if nl:
            mapa_pag = (
                pagamentos_por_nl
                if pagamentos_por_nl is not None
                else agrupar_pagamentos_por_nota(pagamentos)
            )
            if nl in mapa_pag and mapa_pag[nl] is not None and mapa_pag[nl] <= 0.0:
                saldo_pag_nao_positivo = True

    if estorno_texto or val_liq <= 0.0 or saldo_pag_nao_positivo:
        motivos.append("estorno_ou_saldo_nao_positivo")

    return motivos


_CAMPOS_LASTRO_OBRIGATORIOS = ("trechoComprobatorio", "documentoOrigem", "justificativa")


def _normalizar_para_matching(texto: str) -> str:
    """Normaliza texto para matching alfanumérico tolerando pontuação de abreviações."""
    base = normalizar_nome(texto)
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", base).split())


def _contem_termo_com_fronteira(texto_matching: str, termo_matching: str) -> bool:
    """Verifica ocorrência de termo normalizado com fronteiras alfanuméricas."""
    if not texto_matching or not termo_matching:
        return False
    padrao = rf"(?<![A-Z0-9]){re.escape(termo_matching)}(?![A-Z0-9])"
    return bool(re.search(padrao, texto_matching))


def validar_e_preparar_regras_frentes(
    regras_raw: Any,
    *,
    bairros_nomes: list[str],
    sublocalidades_norm: dict[str, str],
    bairro_para_pb: dict[str, str],
    bairro_para_pb_norm: dict[str, str],
    reconciliar_bairro: Callable[[str, list[str], dict[str, str]], Optional[str]],
) -> list[dict[str, Any]]:
    """Valida em modo fail-fast e prepara as Regras de Frente Auditada de um contrato multi_frente."""
    if regras_raw is None:
        return []
    if not isinstance(regras_raw, list):
        raise ValueError("Campo 'regrasFrentes' deve ser uma lista.")

    ids_vistos: set[str] = set()
    regras_preparadas: list[dict[str, Any]] = []

    for idx, regra in enumerate(regras_raw):
        if not isinstance(regra, dict):
            raise ValueError(f"Regra em 'regrasFrentes[{idx}]' deve ser um objeto JSON.")

        regra_id = str(regra.get("id") or "").strip()
        if not regra_id:
            raise ValueError(f"Regra em 'regrasFrentes[{idx}]' sem 'id' obrigatório.")
        if regra_id in ids_vistos:
            raise ValueError(f"Identificador de regra duplicado no contrato: '{regra_id}'.")
        ids_vistos.add(regra_id)

        status = str(regra.get("status") or "").strip().lower()
        if not status:
            raise ValueError(f"Regra '{regra_id}' sem 'status' obrigatório.")

        for campo in _CAMPOS_LASTRO_OBRIGATORIOS:
            valor_campo = str(regra.get(campo) or "").strip()
            if not valor_campo:
                raise ValueError(f"Regra '{regra_id}' sem campo obrigatório de lastro '{campo}'.")

        contem_raw = regra.get("contemTodos")
        if not isinstance(contem_raw, list) or not contem_raw:
            raise ValueError(f"Regra '{regra_id}' exige 'contemTodos' como lista não vazia.")
        contem_norm: list[str] = []
        for termo in contem_raw:
            termo_norm = _normalizar_para_matching(str(termo or ""))
            if not termo_norm:
                raise ValueError(f"Regra '{regra_id}' contém termo vazio em 'contemTodos'.")
            contem_norm.append(termo_norm)

        excluir_raw = regra.get("excluirSeContiver")
        excluir_norm: list[str] = []
        if excluir_raw is not None:
            if not isinstance(excluir_raw, list):
                raise ValueError(f"Regra '{regra_id}' tem 'excluirSeContiver' inválido (esperada lista).")
            for termo in excluir_raw:
                termo_norm = _normalizar_para_matching(str(termo or ""))
                if termo_norm:
                    excluir_norm.append(termo_norm)

        nivel = str(regra.get("nivel") or "").strip()
        bairro_canonico: Optional[str] = None
        pb_final: Optional[str] = None
        if nivel == "Bairro":
            bairro_raw = str(regra.get("bairro") or "").strip()
            bairro_canonico = reconciliar_bairro(bairro_raw, bairros_nomes, sublocalidades_norm)
            if not bairro_canonico:
                raise ValueError(
                    f"Regra '{regra_id}' referencia bairro não reconciliável contra os Bairros Oficiais: '{bairro_raw}'."
                )
            pb_raw = (
                regra.get("prefeituraBairro")
                or bairro_para_pb.get(bairro_canonico)
                or bairro_para_pb_norm.get(normalizar_nome(bairro_canonico))
            )
            pb_final = normalizar_nome_prefeitura_bairro(str(pb_raw)) if pb_raw else None
        elif nivel == "Regional (Prefeitura-Bairro)":
            pb_raw = str(regra.get("prefeituraBairro") or "").strip()
            pb_final = normalizar_nome_prefeitura_bairro(pb_raw) if pb_raw else None
            if not pb_final:
                raise ValueError(
                    f"Regra '{regra_id}' de nível Regional exige 'prefeituraBairro' válido."
                )
        else:
            raise ValueError(
                f"Regra '{regra_id}' possui 'nivel' inválido: '{nivel}'."
            )

        if status != "promovido":
            continue

        regras_preparadas.append({
            "id": regra_id,
            "nivel": nivel,
            "bairro": bairro_canonico,
            "prefeituraBairro": pb_final,
            "contemTodosNorm": contem_norm,
            "excluirSeContiverNorm": excluir_norm,
            "trechoComprobatorio": regra.get("trechoComprobatorio"),
            "documentoOrigem": regra.get("documentoOrigem"),
            "justificativa": regra.get("justificativa"),
        })

    return regras_preparadas


def selecionar_regra_frente(
    nota: dict[str, Any],
    regras_preparadas: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Retorna a única Regra de Frente Auditada que casa a nota, ou None se 0 ou 2+ casarem."""
    if not regras_preparadas:
        return None
    texto_matching = _normalizar_para_matching(str(nota.get("descObsLiquidacao") or ""))
    if not texto_matching:
        return None

    casadas: list[dict[str, Any]] = []
    for regra in regras_preparadas:
        if not all(_contem_termo_com_fronteira(texto_matching, t) for t in regra["contemTodosNorm"]):
            continue
        if any(_contem_termo_com_fronteira(texto_matching, t) for t in regra["excluirSeContiverNorm"]):
            continue
        casadas.append(regra)
        if len(casadas) > 1:
            return None

    return casadas[0] if len(casadas) == 1 else None

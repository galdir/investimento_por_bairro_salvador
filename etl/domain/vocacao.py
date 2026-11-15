"""Classificação híbrida e auditável de Vocação da Obra Pública de Salvador.

Categoriza cada contrato de engenharia em uma das 3 vocações canônicas:
- Vizinhança e Comunidade
- Mobilidade Estrutural e Orlas
- Equipamentos e Marcos da Cidade
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from etl.domain.territorio import normalizar_nome

VOCACAO_VIZINHANCA = "Vizinhança e Comunidade"
VOCACAO_MOBILIDADE = "Mobilidade Estrutural e Orlas"
VOCACAO_EQUIPAMENTOS = "Equipamentos e Marcos da Cidade"

VOCACOES_CANONICAS: list[str] = [
    VOCACAO_VIZINHANCA,
    VOCACAO_MOBILIDADE,
    VOCACAO_EQUIPAMENTOS,
]

_CURADORIA_VOCACAO_PATH = Path(__file__).resolve().parent.parent / "reference" / "curadoria_vocacao.json"

_RE_EQUIPAMENTOS = re.compile(
    r"\b("
    r"HOSPITAL(?:ES|AR)?|"
    r"ARENA\s+(?:SALVADOR|MULTIUSO|AQUATICA)|"
    r"COMPLEXO\s+MULTIUSO|"
    r"CASA\s+DE\s+ESPETACULOS|"
    r"MERCADO\s+(?:MODELO|MUNICIPAL|POPULAR|DE\s+SAO\s+CRISTOVAO)|"
    r"TEATRO|"
    r"MUSEU|"
    r"CENTRO\s+CULTURAL|"
    r"CENTRO\s+DE\s+CONVENCOES|"
    r"ELEVADOR\s+LACERDA|"
    r"CASA\s+DA\s+MULHER\s+BRASILEIRA|"
    r"SEDE\s+ADMINISTRATIVA"
    r")\b"
)

_RE_MOBILIDADE = re.compile(
    r"\b("
    r"VIADUTO(?:S)?|"
    r"TUNEL|TUNEIS|"
    r"BRT|"
    r"VLT|"
    r"MONOTRILHO|"
    r"ORLA\s+(?:MARITIMA|DE|DA|DO)|"
    r"PROMENADE\s+CONTORNO|"
    r"EIXO\s+VIARIO|"
    r"CORREDOR\s+(?:VIARIO|EXCLUSIVO)|"
    r"ESTACAO\s+DE\s+TRANSBORDO|"
    r"TERMINAL\s+DE\s+INTEGRACAO"
    r")\b"
)


@lru_cache(maxsize=1)
def carregar_curadoria_vocacao() -> dict[str, dict[str, Any]]:
    """Carrega o catálogo versionado de Curadoria Semântica de Vocação da Obra."""
    if not _CURADORIA_VOCACAO_PATH.exists():
        return {}
    try:
        with open(_CURADORIA_VOCACAO_PATH, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(dados, dict):
        return {}
    registros = dados.get("registros")
    return registros if isinstance(registros, dict) else dados


def _chave_canonica_obra(obra: dict[str, Any]) -> str:
    cd_ug = str(obra.get("cdUnidadeGestora") or "").strip()
    nu_contrato = str(obra.get("nuContratoSigef") or obra.get("numeroContrato") or "").strip()
    if cd_ug and nu_contrato:
        return f"{cd_ug}:{nu_contrato}"
    return ""


def classificar_vocacao(
    obra: dict[str, Any],
    curadoria: Optional[dict[str, dict[str, Any]]] = None,
) -> str:
    """Classifica a Obra Pública em uma das 3 categorias canônicas de Vocação da Obra.

    Precedência:
        1. Curadoria semântica explícita por Chave Canônica da Obra (`cdUnidadeGestora:nuContratoSigef`).
        2. Regras determinísticas estritas sobre o objeto e a Unidade Gestora.
        3. Fallback conservador para `Vizinhança e Comunidade`.
    """
    catalogo = curadoria if curadoria is not None else carregar_curadoria_vocacao()
    chave = _chave_canonica_obra(obra)
    if chave and isinstance(catalogo.get(chave), dict):
        vocacao_curada = catalogo[chave].get("vocacao")
        if vocacao_curada in VOCACOES_CANONICAS:
            return vocacao_curada

    objeto_norm = normalizar_nome(str(obra.get("dsObjeto") or obra.get("objeto") or ""))
    orgao_norm = normalizar_nome(
        str(obra.get("sgOrgao") or obra.get("unidadeGestora") or obra.get("dsUnidadeGestora") or "")
    )

    if _RE_EQUIPAMENTOS.search(objeto_norm):
        return VOCACAO_EQUIPAMENTOS

    if "SMED" in orgao_norm or "FME" in orgao_norm or "CODESAL" in orgao_norm:
        return VOCACAO_VIZINHANCA

    if _RE_MOBILIDADE.search(objeto_norm):
        return VOCACAO_MOBILIDADE

    return VOCACAO_VIZINHANCA

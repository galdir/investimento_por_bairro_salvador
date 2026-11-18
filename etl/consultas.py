"""Contrato da coleta obrigatória de pagamentos para a publicação."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConsultaPagamentos:
    registros: list[dict[str, Any]]
    data_referencia: str
    concluida: bool
    validada: bool
    limitacoes_conhecidas: list[str] = field(default_factory=list)


def coletar_pagamentos(cd_unidade_gestora: Any, nu_contrato_sigef: Any, data_referencia: str) -> ConsultaPagamentos:
    """Impede publicação até a coleta histórica conciliada ser implementada e ensaiada."""
    raise RuntimeError("Coleta histórica conciliada de pagamentos ainda não está disponível")

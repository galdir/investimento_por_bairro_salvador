"""Regras comuns para valores informados em movimentos de pagamento."""

from typing import Any


def valor_informado_pagamento(registro: dict[str, Any]) -> Any:
    """Preserva zero e usa o nome alternativo apenas se o campo principal estiver vazio."""
    valor = registro.get("pago")
    return registro.get("valorPago") if valor in (None, "") else valor

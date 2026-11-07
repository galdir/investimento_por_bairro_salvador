"""Testes unitários para regras territoriais e classificação de Zonas Especiais Não-Residenciais."""

import pytest
from etl.domain.territorio import is_zona_especial_nao_residencial, normalizar_nome


@pytest.mark.parametrize(
    "nome_bairro,esperado",
    [
        ("Aeroporto", True),
        ("AEROPORTO", True),
        ("Porto Seco Pirajá", True),
        ("Porto Seco Piraja", True),
        ("Centro Administrativo da Bahia - CAB", True),
        ("Centro Administrativo da Bahia", True),
        ("CAB", True),
        # Testes de regressão: NÃO DEVEM ser marcados como Zona Especial
        ("Cabula", False),
        ("Cabula VI", False),
        ("Cabula 6", False),
        ("Pituba", False),
        ("Liberdade", False),
        ("Barra", False),
        ("Graça", False),
        ("Itapuã", False),
        ("", False),
    ],
)
def test_is_zona_especial_nao_residencial_regressao_cabula(nome_bairro: str, esperado: bool) -> None:
    """Garante que bairros residenciais (como Cabula) não sejam falsamente marcados como CAB.

    Sumário:
        Verifica a classificação booleana estrita para zonas especiais versus bairros comuns.

    Argumentos:
        nome_bairro: Nome do bairro de entrada.
        esperado: Valor booleano esperado da função.

    Retornos:
        None.
    """
    assert is_zona_especial_nao_residencial(nome_bairro) == esperado

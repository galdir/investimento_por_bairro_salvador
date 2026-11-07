"""Testes para o domínio de Mandato Municipal, paginação e deduplicação de obras.

Valida a classificação de mandatos por sobreposição de vigência,
a deduplicação canônica por (cdUnidadeGestora, nuContratoSigef) e a paginação completa do grid.
"""

from unittest.mock import patch
import pytest

from etl.domain.mandato import (
    MANDATOS_MUNICIPAIS,
    classificar_mandatos_obra,
    deduplicar_obras,
    obter_chave_canonica_obra,
)
from etl.sources.transparencia import fetch_grid_detalhada


def test_classificar_mandatos_obra_sobreposicao():
    """Valida a atribuição de mandatos municipais por sobreposição de vigência."""
    # Obra iniciada e encerrada no mandato 2021-2024
    obra_passada = {
        "dtInicioVigencia": "2022-03-01T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2024-06-30T00:00:00.000Z",
    }
    assert classificar_mandatos_obra(obra_passada) == ["2021-2024"]

    # Obra iniciada no mandato 2025-2028
    obra_recente = {
        "dtInicioVigencia": "2025-02-10T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
    }
    assert classificar_mandatos_obra(obra_recente) == ["2025-2028"]

    # Obra plurianual iniciada em 2023/2024 com término em 2026/2027 (atravessa dois mandatos)
    obra_plurianual = {
        "dtInicioVigencia": "2024-01-10T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2027-12-31T00:00:00.000Z",
    }
    assert classificar_mandatos_obra(obra_plurianual) == ["2021-2024", "2025-2028"]


def test_classificar_mandatos_obra_fallback_contrato_ou_ano():
    """Valida o fallback para extração de ano a partir do nuContratoSigef quando as datas estão ausentes."""
    obra_sem_datas = {
        "nuContratoSigef": "045/2023",
    }
    assert classificar_mandatos_obra(obra_sem_datas) == ["2021-2024"]

    obra_2025_sem_datas = {
        "nuContratoSigef": "002/2025",
    }
    assert classificar_mandatos_obra(obra_2025_sem_datas) == ["2025-2028"]


def test_deduplicar_obras_por_chave_canonica_preserva_estado_recente_e_mescla_mandatos():
    """Valida que contratos repetidos em múltiplos períodos são deduplicados pela chave canônica."""
    obras_brutas = [
        {
            "id": 1001,
            "cdUnidadeGestora": 2401,
            "nuContratoSigef": "001/2024",
            "vlAtualizado": 10000000.00,
            "percentualExecutado": 40.0,
            "dtInicioVigencia": "2024-01-10T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2027-12-31T00:00:00.000Z",
            "mandatos": ["2021-2024"],
        },
        {
            "id": 1001,
            "cdUnidadeGestora": 2401,
            "nuContratoSigef": "001/2024",
            "vlAtualizado": 12000000.00,
            "percentualExecutado": 65.5,
            "dtInicioVigencia": "2024-01-10T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2027-12-31T00:00:00.000Z",
            "mandatos": ["2025-2028"],
        },
        {
            "id": 1002,
            "cdUnidadeGestora": 2501,
            "nuContratoSigef": "002/2024",
            "vlAtualizado": 2400000.00,
            "percentualExecutado": 50.0,
            "mandatos": ["2021-2024"],
        },
    ]

    deduplicadas = deduplicar_obras(obras_brutas)
    assert len(deduplicadas) == 2

    obra_dedup = next(o for o in deduplicadas if o["nuContratoSigef"] == "001/2024")
    # Preserva o estado mais recente (vlAtualizado 12M e perc 65.5%)
    assert obra_dedup["vlAtualizado"] == 12000000.00
    assert obra_dedup["percentualExecutado"] == 65.5
    # Mescla mandatos sem duplicações
    assert set(obra_dedup["mandatos"]) == {"2021-2024", "2025-2028"}


def test_fetch_grid_detalhada_paginacao_completa():
    """Valida que fetch_grid_detalhada percorre todas as páginas até o encerramento da paginação."""
    pagina_1 = {
        "dados": [{"id": i, "cdUnidadeGestora": 2401, "nuContratoSigef": f"{i}/2024"} for i in range(1, 11)],
        "paginacao": {"paginaAtual": 1, "totalPaginas": 2, "totalRegistros": 15},
    }
    pagina_2 = {
        "dados": [{"id": i, "cdUnidadeGestora": 2401, "nuContratoSigef": f"{i}/2024"} for i in range(11, 16)],
        "paginacao": {"paginaAtual": 2, "totalPaginas": 2, "totalRegistros": 15},
    }

    respostas = [pagina_1, pagina_2]

    def fake_post(endpoint, payload, timeout=15):
        if "pagina=1" in endpoint:
            return respostas[0]
        if "pagina=2" in endpoint:
            return respostas[1]
        return {"dados": []}

    with patch("etl.sources.transparencia._post_transparencia", side_effect=fake_post):
        resultados = fetch_grid_detalhada(year=2024)

    assert len(resultados) == 15
    assert resultados[0]["id"] == 1
    assert resultados[-1]["id"] == 15

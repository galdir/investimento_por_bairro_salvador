"""Testes unitários para a máquina de estados determinística do Semáforo da Obra.

Cobre todos os gatilhos das cores Vermelho (Crítica), Amarelo (Atenção) e Verde (No Prazo).
"""

from datetime import date
import pytest

from etl.domain.semaforo import classificar_semaforo


def test_semaforo_vermelho_por_situacao_paralisada_ou_rescindida():
    """Gatilho Vermelho: obra com situação Paralisada, Suspensa ou Rescindida."""
    obra_paralisada = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1000000.0,
        "dsSituacao": "Paralisada",
        "percentualExecutado": 50.0,
    }
    resultado = classificar_semaforo(obra_paralisada)
    assert resultado["status"] == "VERMELHO"
    assert "Paralisada" in resultado["motivos"][0]

    obra_rescindida = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1000000.0,
        "dsSituacao": "Rescindida",
        "percentualExecutado": 20.0,
    }
    assert classificar_semaforo(obra_rescindida)["status"] == "VERMELHO"


def test_semaforo_vermelho_por_prazo_vencido_e_execucao_incompleta():
    """Gatilho Vermelho: data atual maior que término de vigência com percentual < 100%."""
    data_ref = date(2025, 6, 1)
    obra_atrasada = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1000000.0,
        "dtTerminoVigenciaAtualizado": "2025-05-01T00:00:00.000Z",
        "percentualExecutado": 85.0,
        "dsSituacao": "Em Execução",
    }
    resultado = classificar_semaforo(obra_atrasada, data_referencia=data_ref)
    assert resultado["status"] == "VERMELHO"
    assert any("vigência expirada" in m.lower() for m in resultado["motivos"])


def test_semaforo_vermelho_por_aditivo_valor_superior_a_25_porcento():
    """Gatilho Vermelho: delta percentual de aditivo contratual superior a 25%."""
    obra_aditivo_alto = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1260000.0,  # +26% de aditivo
        "dsSituacao": "Em Execução",
        "percentualExecutado": 30.0,
        "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
    }
    resultado = classificar_semaforo(obra_aditivo_alto, data_referencia=date(2025, 1, 1))
    assert resultado["status"] == "VERMELHO"
    assert any("aditivo de valor superior a 25%" in m.lower() for m in resultado["motivos"])


def test_semaforo_vermelho_por_inatividade_financeira_superior_a_90_dias():
    """Gatilho Vermelho: obra em execução sem liquidação ou pagamento há mais de 90 dias."""
    data_ref = date(2025, 5, 1)
    obra_sem_medicao = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1000000.0,
        "dsSituacao": "Em Execução",
        "percentualExecutado": 40.0,
        "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
        "dias_desde_ultima_liquidacao_ou_pagamento": 95,
    }
    resultado = classificar_semaforo(obra_sem_medicao, data_referencia=data_ref)
    assert resultado["status"] == "VERMELHO"
    assert any("90 dias" in m.lower() for m in resultado["motivos"])


def test_semaforo_amarelo_por_prorrogacao_de_prazo_ou_aditivo():
    """Gatilho Amarelo: término atualizado maior que fim original ou flag de aditivo de prazo."""
    obra_prorrogada = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1000000.0,
        "dtFimVigenciaOriginal": "2025-06-30T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2025-12-31T00:00:00.000Z",
        "dsSituacao": "Em Execução",
        "percentualExecutado": 50.0,
    }
    resultado = classificar_semaforo(obra_prorrogada, data_referencia=date(2025, 1, 1))
    assert resultado["status"] == "AMARELO"
    assert any("prorrogação de prazo" in m.lower() for m in resultado["motivos"])

    obra_com_aditivo_prazo = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1000000.0,
        "possui_aditivo_de_prazo": True,
        "dsSituacao": "Em Execução",
        "percentualExecutado": 50.0,
        "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
    }
    assert classificar_semaforo(obra_com_aditivo_prazo, data_referencia=date(2025, 1, 1))["status"] == "AMARELO"


def test_semaforo_amarelo_por_aditivo_valor_entre_10_e_25_porcento():
    """Gatilho Amarelo: aditivo de valor entre 10% e 25%."""
    obra_aditivo_medio = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1150000.0,  # +15%
        "dsSituacao": "Em Execução",
        "percentualExecutado": 50.0,
        "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
    }
    resultado = classificar_semaforo(obra_aditivo_medio, data_referencia=date(2025, 1, 1))
    assert resultado["status"] == "AMARELO"
    assert any("entre 10% e 25%" in m.lower() for m in resultado["motivos"])


def test_semaforo_verde_obra_no_prazo_e_aditivo_baixo():
    """Gatilho Verde: obra com vigência no prazo e aditivo de valor menor que 10%."""
    obra_verde = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1050000.0,  # +5% (menor que 10%)
        "dtFimVigenciaOriginal": "2026-12-31T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
        "dsSituacao": "Em Execução",
        "percentualExecutado": 40.0,
    }
    resultado = classificar_semaforo(obra_verde, data_referencia=date(2025, 1, 1))
    assert resultado["status"] == "VERDE"
    assert resultado["rotulo"] == "Verde (No Prazo)"

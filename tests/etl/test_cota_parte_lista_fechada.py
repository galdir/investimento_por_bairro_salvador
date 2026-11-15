"""Testes da Seam 1 para Cota-Parte de Lista Fechada Contratual (rollup, KPIs e reconciliação)."""

import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from etl.domain.kpis import calcular_kpis_globais
from etl.domain.territorio import calcular_rollup_territorial
from etl.reconcile import reconciliar_acervo_local
from tests.etl.fixtures.sample_data import (
    SAMPLE_GEOSALVADOR_BAIRROS,
    SAMPLE_GEOSALVADOR_PREFEITURAS,
)


def _bairros_fixture() -> list[dict]:
    return [
        {
            "id": 101,
            "nome": "Pituba",
            "prefeitura_bairro": "Barra/Pituba",
            "populacao": 60000,
            "indice_vulnerabilidade": 0.13,
            "is_zona_especial_nao_residencial": False,
            "isZonaEspecialNaoResidencial": False,
        },
        {
            "id": 102,
            "nome": "Amaralina",
            "prefeitura_bairro": "Barra/Pituba",
            "populacao": 20000,
            "indice_vulnerabilidade": 0.25,
            "is_zona_especial_nao_residencial": False,
            "isZonaEspecialNaoResidencial": False,
        },
        {
            "id": 201,
            "nome": "Paripe",
            "prefeitura_bairro": "Subúrbio/Ilhas",
            "populacao": 50000,
            "indice_vulnerabilidade": 0.65,
            "is_zona_especial_nao_residencial": False,
            "isZonaEspecialNaoResidencial": False,
        },
    ]


def _prefeituras_fixture() -> list[dict]:
    return [
        {
            "id": 6,
            "nome": "Barra/Pituba",
            "populacao_total": 80000,
        },
        {
            "id": 1,
            "nome": "Subúrbio/Ilhas",
            "populacao_total": 50000,
        },
    ]


def test_rollup_territorial_distribui_cotas_lista_fechada_e_deduplica_prefeitura_bairro() -> None:
    """Seam 1: cada bairro recebe peso n/M, +1 obra/semáforo, e Prefeitura-Bairro deduplica contrato."""
    obras = [
        {
            "id": "obra-lf-1",
            "nivel": "Bairro",
            "bairro": "Pituba",
            "prefeitura_bairro": "Barra/Pituba",
            "vlAtualizado": 900000.0,
            "vlLiquidado": 600000.0,
            "vlPago": 300000.0,
            "dsSituacao": "Em Execução",
            "semaforo": {"status": "AMARELO"},
            "cotasListaFechada": [
                {
                    "bairro": "Pituba",
                    "prefeituraBairro": "Barra/Pituba",
                    "unidades": 1,
                    "totalUnidades": 3,
                    "peso": 1 / 3,
                    "fracao": "1/3",
                    "latitude": -12.999,
                    "longitude": -38.458,
                },
                {
                    "bairro": "Amaralina",
                    "prefeituraBairro": "Barra/Pituba",
                    "unidades": 1,
                    "totalUnidades": 3,
                    "peso": 1 / 3,
                    "fracao": "1/3",
                    "latitude": -13.008,
                    "longitude": -38.472,
                },
                {
                    "bairro": "Paripe",
                    "prefeituraBairro": "Subúrbio/Ilhas",
                    "unidades": 1,
                    "totalUnidades": 3,
                    "peso": 1 / 3,
                    "fracao": "1/3",
                    "latitude": -12.832,
                    "longitude": -38.469,
                },
            ],
        },
        {
            "id": "obra-direta-pituba",
            "nivel": "Bairro",
            "bairro": "Pituba",
            "prefeitura_bairro": "Barra/Pituba",
            "vlAtualizado": 500000.0,
            "vlLiquidado": 500000.0,
            "vlPago": 500000.0,
            "dsSituacao": "Concluída",
            "semaforo": {"status": "VERDE"},
        },
    ]

    bairros_res, pbs_res, opacidade = calcular_rollup_territorial(
        bairros_resumo=_bairros_fixture(),
        prefeituras_resumo=_prefeituras_fixture(),
        obras_alocadas=obras,
    )
    por_bairro = {b["nome"]: b for b in bairros_res}
    por_pb = {p["nome"]: p for p in pbs_res}

    assert por_bairro["Pituba"]["valorTotal"] == pytest.approx(800000.0)
    assert por_bairro["Pituba"]["valorLiquidadoDireto"] == pytest.approx(700000.0)
    assert por_bairro["Pituba"]["valorPagoDireto"] == pytest.approx(600000.0)
    assert por_bairro["Pituba"]["valorPago"] == pytest.approx(600000.0)
    assert por_bairro["Pituba"]["totalObras"] == 2
    assert por_bairro["Pituba"]["obrasVerde"] == 1
    assert por_bairro["Pituba"]["obrasAmarelo"] == 1
    assert por_bairro["Pituba"]["obrasVermelho"] == 0

    assert por_bairro["Amaralina"]["valorTotal"] == pytest.approx(300000.0)
    assert por_bairro["Amaralina"]["valorLiquidadoDireto"] == pytest.approx(200000.0)
    assert por_bairro["Amaralina"]["valorPagoDireto"] == pytest.approx(100000.0)
    assert por_bairro["Amaralina"]["totalObras"] == 1
    assert por_bairro["Amaralina"]["obrasAmarelo"] == 1

    assert por_bairro["Paripe"]["valorTotal"] == pytest.approx(300000.0)
    assert por_bairro["Paripe"]["valorLiquidado"] == pytest.approx(200000.0)
    assert por_bairro["Paripe"]["valorPago"] == pytest.approx(100000.0)
    assert por_bairro["Paripe"]["totalObras"] == 1
    assert por_bairro["Paripe"]["obrasAmarelo"] == 1

    # Barra/Pituba soma os R$ de Pituba (800k) + Amaralina (300k), mas deduplica obra-lf-1 na contagem!
    assert por_pb["Barra/Pituba"]["valorTotal"] == pytest.approx(1100000.0)
    assert por_pb["Barra/Pituba"]["valorLiquidadoDireto"] == pytest.approx(900000.0)
    assert por_pb["Barra/Pituba"]["valorPagoDireto"] == pytest.approx(700000.0)
    assert por_pb["Barra/Pituba"]["totalObras"] == 2
    assert por_pb["Barra/Pituba"]["obrasVerde"] == 1
    assert por_pb["Barra/Pituba"]["obrasAmarelo"] == 1
    assert por_pb["Barra/Pituba"]["obrasVermelho"] == 0

    assert por_pb["Subúrbio/Ilhas"]["valorTotal"] == pytest.approx(300000.0)
    assert por_pb["Subúrbio/Ilhas"]["totalObras"] == 1
    assert por_pb["Subúrbio/Ilhas"]["obrasAmarelo"] == 1

    assert opacidade["totalNaoLocalizado"] == 0
    assert opacidade["valorNaoLocalizado"] == 0.0

    # KPIs globais contam cada contrato uma única vez em 100%
    kpis = calcular_kpis_globais(
        totalizador_transparencia={
            "totalObras": 2,
            "valorTotal": 1400000.0,
            "totalEmpenhado": 1400000.0,
            "totalLiquidado": 1100000.0,
            "totalPago": 800000.0,
        },
        obras_detalhadas=obras,
        populacao_total_cidade=2417678,
        indicador_opacidade=opacidade,
    )
    assert kpis["totalObras"] == 2
    assert kpis["valorTotal"] == pytest.approx(1400000.0)
    assert kpis["totalNaoLocalizado"] == 0


def test_reconciliar_acervo_local_propaga_cotas_lista_fechada_para_index_ficha_e_rollup(
    tmp_path: Path,
) -> None:
    """Seam 1 (ponta a ponta local): lista_fechada grava cotasListaFechada no índice, na Ficha Limpa e no rollup."""
    geo_dir = tmp_path / "geo"
    geo_dir.mkdir(parents=True, exist_ok=True)
    (geo_dir / "bairros.geojson").write_text(
        json.dumps(copy.deepcopy(SAMPLE_GEOSALVADOR_BAIRROS), ensure_ascii=False),
        encoding="utf-8",
    )
    (geo_dir / "prefeituras_bairro.geojson").write_text(
        json.dumps(copy.deepcopy(SAMPLE_GEOSALVADOR_PREFEITURAS), ensure_ascii=False),
        encoding="utf-8",
    )

    obra_id = "uuid-lf-reconcile"
    obras_dir = tmp_path / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)
    ficha_inicial = {
        "id": obra_id,
        "cdUnidadeGestora": "610002",
        "numeroContrato": "2025LF0099",
        "objeto": "Recuperação de três equipamentos públicos em Pituba (2) e Paripe (1)",
        "nivel": "Escopo Cidade (Não-Localizado)",
        "bairro": None,
        "prefeituraBairro": None,
        "latitude": None,
        "longitude": None,
        "estagioAlocacao": "Não-Localizado (Transparência Opaca)",
        "situacao": "Em Execução",
        "semaforo": {"status": "AMARELO", "label": "Em Atraso", "motivo": "Teste"},
        "funilFinanceiro": {
            "valorContratualVigente": 600000.0,
            "valorEmpenhado": 600000.0,
            "valorLiquidado": 300000.0,
            "valorPago": 150000.0,
        },
        "empenhos": [{"notaEmpenho": "2025NE0001", "valEmpenhado": "600.000,00"}],
        "liquidacoes": [{"notaLiquidacao": "2025NL0001", "valLiqLiquidacao": "300.000,00"}],
        "pagamentos": [{"ordemBancaria": "2025OB0001", "pago": "150.000,00"}],
        "fontesOficiais": {
            "escopo": "Portal da Transparência de Salvador",
            "contratoId": obra_id,
            "ultimaAtualizacaoEm": "2026-01-01T00:00:00+00:00",
        },
    }
    (obras_dir / f"{obra_id}.json").write_text(
        json.dumps(ficha_inicial, ensure_ascii=False),
        encoding="utf-8",
    )

    index_inicial = {
        "metadata": {
            "generatedAt": "2026-01-01T00:00:00+00:00",
            "anoReferencia": 2025,
            "mandatosDisponiveis": ["2025–2028"],
        },
        "kpis_globais": {
            "totalObras": 1,
            "valorTotal": 600000.0,
            "totalAtivas": 1,
            "totalCriticas": 0,
            "percentualCriticas": 0.0,
            "totalAditivosValor": 0.0,
            "percentualMedioAditivos": 0.0,
            "totalEmpenhado": 600000.0,
            "totalLiquidado": 300000.0,
            "totalPago": 150000.0,
            "investimentoPorHabitanteCidade": 0.25,
            "totalNaoLocalizado": 1,
            "valorNaoLocalizado": 600000.0,
            "percentualNaoLocalizado": 100.0,
        },
        "prefeituras_bairro": _prefeituras_fixture(),
        "bairros": _bairros_fixture(),
        "obras": [
            {
                "id": obra_id,
                "cdUnidadeGestora": "610002",
                "nuContratoSigef": "2025LF0099",
                "objeto": "Recuperação de três equipamentos públicos em Pituba (2) e Paripe (1)",
                "situacao": "Em Execução",
                "semaforo": {"status": "AMARELO", "label": "Em Atraso", "motivo": "Teste"},
                "nivel": "Escopo Cidade (Não-Localizado)",
                "bairro": None,
                "prefeituraBairro": None,
                "prefeitura_bairro": None,
                "latitude": None,
                "longitude": None,
                "estagioAlocacao": "Não-Localizado (Transparência Opaca)",
                "valorContratualVigente": 600000.0,
                "valorLiquidado": 300000.0,
                "valorPago": 150000.0,
                "ano": 2025,
                "mandatos": ["Bruno Reis (2025–2028)"],
            }
        ],
    }
    (tmp_path / "index_2025.json").write_text(
        json.dumps(index_inicial, ensure_ascii=False),
        encoding="utf-8",
    )

    curadoria = {
        "610002:2025LF0099": {
            "cdUnidadeGestora": "610002",
            "nuContratoSigef": "2025LF0099",
            "status": "lista_fechada",
            "cotas": [
                {
                    "bairro": "Paripe",
                    "unidades": 1,
                    "descricaoUnidades": "Praça Paripe",
                },
                {
                    "bairro": "Pituba",
                    "unidades": 2,
                    "descricaoUnidades": "Praça Pituba I e II",
                },
            ],
            "trechoComprobatorio": "2 equipamentos na Pituba e 1 em Paripe.",
            "documentoOrigem": "dsObjeto / Termo de Referência",
            "justificativa": "Lista fechada contratual com 3 unidades.",
        }
    }

    with patch("urllib.request.urlopen", side_effect=AssertionError("Não deve consultar Nominatim")):
        reconciliar_acervo_local(output_dir=tmp_path, year=2025, curadoria=curadoria)

    idx_final = json.loads((tmp_path / "index_2025.json").read_text(encoding="utf-8"))
    obra_idx = idx_final["obras"][0]
    assert obra_idx["nivel"] == "Bairro"
    assert obra_idx["bairro"] == "Pituba"  # maioria (2/3)
    assert obra_idx["prefeituraBairro"] == "Barra/Pituba"
    assert obra_idx["estagioAlocacao"] == "Curadoria Territorial Auditável (Lista Fechada)"
    assert len(obra_idx["cotasListaFechada"]) == 2
    assert obra_idx["cotasListaFechada"][0]["fracao"] == "1/3"
    assert obra_idx["cotasListaFechada"][1]["fracao"] == "2/3"

    ficha_final = json.loads((obras_dir / f"{obra_id}.json").read_text(encoding="utf-8"))
    assert ficha_final["nivel"] == "Bairro"
    assert ficha_final["bairro"] == "Pituba"
    assert ficha_final["estagioAlocacao"] == "Curadoria Territorial Auditável (Lista Fechada)"
    assert len(ficha_final["cotasListaFechada"]) == 2
    assert ficha_final["fontesOficiais"]["lastroTerritorial"]["cotasListaFechada"] == obra_idx["cotasListaFechada"]

    bairros_idx = {b["nome"]: b for b in idx_final["bairros"]}
    assert bairros_idx["Pituba"]["valorTotal"] == pytest.approx(400000.0)
    assert bairros_idx["Pituba"]["valorLiquidado"] == pytest.approx(200000.0)
    assert bairros_idx["Pituba"]["valorPago"] == pytest.approx(100000.0)
    assert bairros_idx["Pituba"]["totalObras"] == 1
    assert bairros_idx["Paripe"]["valorTotal"] == pytest.approx(200000.0)
    assert bairros_idx["Paripe"]["valorLiquidado"] == pytest.approx(100000.0)
    assert bairros_idx["Paripe"]["valorPago"] == pytest.approx(50000.0)
    assert bairros_idx["Paripe"]["totalObras"] == 1

    assert idx_final["kpis_globais"]["totalObras"] == 1
    assert idx_final["kpis_globais"]["valorTotal"] == pytest.approx(600000.0)
    assert idx_final["kpis_globais"]["totalNaoLocalizado"] == 0


def test_rollup_respeita_precedencia_frentes_e_deduplica_por_chave_canonica() -> None:
    """Seam 1: frentesMedicao prevalecem sobre cotasListaFechada e chave canônica deduplica obras regionais."""
    obras = [
        {
            "id": "uuid-frente-1",
            "cdUnidadeGestora": "567002",
            "nuContratoSigef": "2016CT001386",
            "nivel": "Escopo Cidade (Não-Localizado)",
            "vlAtualizado": 1000000.0,
            "vlLiquidado": 250000.0,
            "vlPago": 250000.0,
            "semaforo": {"status": "VERDE"},
            "frentesMedicao": [
                {
                    "nivel": "Bairro",
                    "bairro": "Pituba",
                    "prefeituraBairro": "Barra/Pituba",
                    "valorLiquidado": 150000.0,
                    "valorPago": 150000.0,
                }
            ],
            "cotasListaFechada": [
                {
                    "bairro": "Pituba",
                    "prefeituraBairro": "Barra/Pituba",
                    "unidades": 1,
                    "totalUnidades": 2,
                    "peso": 0.5,
                    "fracao": "1/2",
                },
                {
                    "bairro": "Amaralina",
                    "prefeituraBairro": "Barra/Pituba",
                    "unidades": 1,
                    "totalUnidades": 2,
                    "peso": 0.5,
                    "fracao": "1/2",
                },
            ],
        },
        {
            "id": "uuid-dup-a",
            "cdUnidadeGestora": "567002",
            "nuContratoSigef": "2025REG0001",
            "nivel": "Bairro",
            "bairro": "Pituba",
            "prefeitura_bairro": "Barra/Pituba",
            "vlAtualizado": 100000.0,
            "vlLiquidado": 0.0,
            "vlPago": 0.0,
            "semaforo": {"status": "VERDE"},
        },
        {
            "id": "uuid-dup-b",
            "cdUnidadeGestora": "567002",
            "nuContratoSigef": "2025REG0001",
            "nivel": "Regional (Prefeitura-Bairro)",
            "prefeitura_bairro": "Barra/Pituba",
            "vlAtualizado": 0.0,
            "vlLiquidado": 0.0,
            "vlPago": 0.0,
            "semaforo": {"status": "VERDE"},
        },
    ]

    bairros_res, pbs_res, _ = calcular_rollup_territorial(
        bairros_resumo=_bairros_fixture(),
        prefeituras_resumo=_prefeituras_fixture(),
        obras_alocadas=obras,
    )
    por_bairro = {b["nome"]: b for b in bairros_res}
    por_pb = {p["nome"]: p for p in pbs_res}

    # Amaralina não recebe cota teórica porque frentesMedicao prevalece; Pituba recebe apenas a frente + obra 100k
    assert por_bairro["Amaralina"]["valorTotal"] == pytest.approx(0.0)
    assert por_bairro["Amaralina"]["valorPago"] == pytest.approx(0.0)
    assert por_bairro["Amaralina"]["totalObras"] == 0
    assert por_bairro["Pituba"]["valorTotal"] == pytest.approx(100000.0)
    assert por_bairro["Pituba"]["valorPago"] == pytest.approx(150000.0)
    # Mesmo com ids distintos, (567002, 2025REG0001) deduplica na Prefeitura-Bairro
    assert por_pb["Barra/Pituba"]["totalObras"] == 1


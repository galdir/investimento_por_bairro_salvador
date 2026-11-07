"""Testes automatizados para execução incremental do ETL (--full-refresh), reuso de mandatos e catálogo completo.

Valida:
1. Fallback offline carregando o catálogo completo dos 170+ Bairros Oficiais, Prefeituras-Bairro e Censo 2022.
2. Modo incremental (full_refresh=False) preservando mandatos encerrados (2021-2024) sem chamadas de rede.
3. Modo incremental (full_refresh=False) reaproveitando Ficha Limpa local quando indicadores de estado não mudaram.
4. Flag --full-refresh forçando reconsulta de todos os mandatos e atualização completa de detalhes.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch
import pytest

from etl.sources import geosalvador, ibge_censo, transparencia
from tests.etl.fixtures.sample_data import (
    SAMPLE_GEOSALVADOR_BAIRROS,
    SAMPLE_GEOSALVADOR_PREFEITURAS,
    SAMPLE_IBGE_CENSO_2022,
    SAMPLE_TRANSPARENCIA_GRID,
    SAMPLE_TRANSPARENCIA_TOTALIZADOR,
)


def test_offline_fallback_loads_complete_170_catalogs():
    """Valida que o fallback offline carrega o catálogo completo de 170+ bairros, prefeituras e censo 2022."""
    with patch("urllib.request.urlopen", side_effect=RuntimeError("Sem rede externa")):
        bairros_geo = geosalvador.fetch_bairros_geojson()
        pb_geo = geosalvador.fetch_prefeituras_geojson()
        demografia = ibge_censo.fetch_demografia_censo_2022()

    # 1. Bairros Oficiais (170+ bairros vigentes)
    assert bairros_geo.get("type") == "FeatureCollection"
    features_bairros = bairros_geo.get("features", [])
    assert len(features_bairros) >= 170, f"Esperado ao menos 170 bairros oficiais, obtido {len(features_bairros)}"

    for feat in features_bairros:
        props = feat.get("properties", {})
        nome = props.get("NM_BAIRRO") or props.get("NOME_BAIRR")
        assert nome, "Todo bairro do catálogo deve ter nome identificado"
        assert "PREFEITURA_BAIRRO" in props, f"Bairro {nome} deve ter PREFEITURA_BAIRRO atribuída"

    # 2. Prefeituras-Bairro
    assert pb_geo.get("type") == "FeatureCollection"
    features_pb = pb_geo.get("features", [])
    assert len(features_pb) >= 10, f"Esperado ao menos 10 prefeituras-bairro, obtido {len(features_pb)}"

    # 3. Demografia Censo 2022
    assert len(demografia) >= 170, f"Esperado ao menos 170 bairros na demografia, obtido {len(demografia)}"
    assert "Pituba" in demografia
    assert demografia["Pituba"]["populacao"] > 0
    assert demografia["Pituba"]["indice_vulnerabilidade"] == 0.12

    assert "Aeroporto" in demografia
    assert demografia["Aeroporto"]["populacao"] <= 5
    assert demografia["Aeroporto"]["indice_vulnerabilidade"] == 0.05


def test_incremental_mode_reuses_closed_mandates_without_network_call(tmp_path: Path):
    """Valida que o modo incremental preserva mandatos passados (2021-2024) sem refazer chamadas de rede."""
    from etl.runner import run_pipeline

    # Cria um índice prévio contendo uma obra histórica consolidada do mandato 2021-2024
    obra_historica = {
        "id": 9999,
        "unidadeGestora": "SUCOP",
        "numeroContrato": "999/2021",
        "objeto": "Construção de Contenção de Encosta Histórica 2021-2024",
        "valorOriginal": 5000000.0,
        "valorContratualVigente": 5000000.0,
        "valorPago": 5000000.0,
        "percentualExecutado": 100.0,
        "situacao": "Concluído",
        "credor": "CONSTRUTORA HISTORICA LTDA",
        "cnpj": "00.111.222/0001-33",
        "ano": 2021,
        "mandatos": ["2021-2024"],
        "dtInicioVigencia": "2021-02-01T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2024-06-30T00:00:00.000Z",
        "nivel": "Bairro",
        "bairro": "Liberdade",
        "prefeituraBairro": "Liberdade/São Caetano",
        "prefeitura_bairro": "Liberdade/São Caetano",
    }

    index_previo = {
        "metadata": {
            "anoReferencia": 2025,
            "mandatosDisponiveis": ["2021-2024", "2025-2028"],
        },
        "kpis_globais": {},
        "obras": [obra_historica],
    }

    index_file = tmp_path / "index_2025.json"
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index_previo, f)

    # Obra do mandato ativo 2025-2028
    obra_vigente = {
        "id": 1001,
        "cdUnidadeGestora": 2401,
        "dsUnidadeGestora": "SUPERINTENDENCIA DE OBRAS PUBLICAS",
        "sgOrgao": "SUCOP",
        "nuContratoSigef": "001/2025",
        "dsObjeto": "Requalificação da Orla da Pituba",
        "vlOriginal": 12000000.0,
        "vlAtualizado": 12000000.0,
        "dtInicioVigencia": "2025-01-10T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2027-12-31T00:00:00.000Z",
        "percentualExecutado": 65.5,
        "dsSituacao": "Em Execução",
        "nmCredor": "CONSTRUTORA SALVADOR LTDA",
        "nuDocumentoCredor": "12.345.678/0001-90",
    }

    mock_grid = MagicMock(return_value=[obra_vigente])

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value=SAMPLE_IBGE_CENSO_2022),
        patch("etl.sources.transparencia.fetch_totalizador", return_value=SAMPLE_TRANSPARENCIA_TOTALIZADOR),
        patch("etl.sources.transparencia.fetch_grid_detalhada", mock_grid),
    ):
        result = run_pipeline(output_dir=tmp_path, year=2025, full_refresh=False)

    assert result["success"] is True

    # Verifica que fetch_grid_detalhada foi chamada APENAS para 2025-2028, e NÃO para 2021-2024
    assert mock_grid.call_count == 1
    call_args, call_kwargs = mock_grid.call_args
    payload = call_kwargs.get("payload_customizado", {})
    assert "2025" in payload.get("dataInicio", "")
    assert "2028" in payload.get("dataFim", "")

    # Verifica que o índice final contém tanto a obra histórica preservada quanto a nova obra vigente
    with open(tmp_path / "index_2025.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    obras_finais = data.get("obras", [])
    ids_finais = {o["id"] for o in obras_finais}
    assert 9999 in ids_finais, "A obra histórica 9999 de 2021-2024 deve ter sido preservada no índice"
    assert 1001 in ids_finais, "A obra vigente 1001 de 2025-2028 deve estar presente no índice"


def test_incremental_mode_diffs_contract_state_and_skips_detail_network_calls(tmp_path: Path):
    """Valida que o modo incremental reaproveita a Ficha Limpa local quando os indicadores de estado são idênticos."""
    from etl.runner import run_pipeline

    obra_base = dict(SAMPLE_TRANSPARENCIA_GRID[0])  # Obra 1001
    obra_id = obra_base["id"]

    # Cria em disco o arquivo obras/1001.json com os mesmos indicadores
    obras_dir = tmp_path / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)
    ficha_existente = {
        "id": obra_id,
        "unidadeGestora": "SUCOP",
        "numeroContrato": "001/2024",
        "situacao": "Em Execução",
        "empreiteira": {
            "razaoSocial": "CONSTRUTORA SALVADOR LTDA",
            "cnpj": "12.345.678/0001-90",
            "totalObras": 1,
            "totalObrasAtivas": 1,
            "valorTotalContratado": 12000000.0,
            "outrasObrasCount": 0,
            "outrasObrasIds": [],
        },
        "vigencia": {
            "dataInicio": "2024-01-10T00:00:00.000Z",
            "dataTerminoAtualizado": "2027-12-31T00:00:00.000Z",
        },
        "funilFinanceiro": {
            "valorOriginal": 12000000.0,
            "valorContratualVigente": 12000000.0,
            "valorEmpenhado": 12000000.0,
            "valorLiquidado": 0.0,
            "valorPago": 7860000.0,
            "percentualExecutado": 65.5,
        },
        "aditivos": [],
        "dotacao": [],
        "empenhos": [],
        "liquidacoes": [],
        "pagamentos": [],
    }

    with open(obras_dir / f"{obra_id}.json", "w", encoding="utf-8") as f:
        json.dump(ficha_existente, f)

    mock_detalhes = MagicMock(return_value={})
    mock_aditivos = MagicMock(return_value=[])
    mock_dotacao = MagicMock(return_value=[])
    mock_empenhos = MagicMock(return_value=[])
    mock_liquidacoes = MagicMock(return_value=[])
    mock_pagamentos = MagicMock(return_value=[])

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value=SAMPLE_IBGE_CENSO_2022),
        patch("etl.sources.transparencia.fetch_totalizador", return_value=SAMPLE_TRANSPARENCIA_TOTALIZADOR),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[obra_base]),
        patch("etl.sources.transparencia.fetch_detalhes_obra", mock_detalhes),
        patch("etl.sources.transparencia.fetch_aditivos_obra", mock_aditivos),
        patch("etl.sources.transparencia.fetch_dotacao_obra", mock_dotacao),
        patch("etl.sources.transparencia.fetch_empenhos_obra", mock_empenhos),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", mock_liquidacoes),
        patch("etl.sources.transparencia.fetch_pagamentos_obra", mock_pagamentos),
    ):
        result = run_pipeline(output_dir=tmp_path, year=2025, full_refresh=False)

    assert result["success"] is True
    assert result.get("detail_cache_hits", 0) >= 1

    # Como vlAtualizado, percentualExecutado, dsSituacao e dtTerminoVigenciaAtualizado foram idênticos,
    # NENHUMA requisição aos 6 endpoints de detalhe deve ter sido disparada
    mock_detalhes.assert_not_called()
    mock_aditivos.assert_not_called()
    mock_dotacao.assert_not_called()
    mock_empenhos.assert_not_called()
    mock_liquidacoes.assert_not_called()
    mock_pagamentos.assert_not_called()

    # Agora simula alteração em percentualExecutado (de 65.5 para 80.0)
    obra_modificada = dict(obra_base)
    obra_modificada["percentualExecutado"] = 80.0

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value=SAMPLE_IBGE_CENSO_2022),
        patch("etl.sources.transparencia.fetch_totalizador", return_value=SAMPLE_TRANSPARENCIA_TOTALIZADOR),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[obra_modificada]),
        patch("etl.sources.transparencia.fetch_detalhes_obra", mock_detalhes),
        patch("etl.sources.transparencia.fetch_aditivos_obra", mock_aditivos),
        patch("etl.sources.transparencia.fetch_dotacao_obra", mock_dotacao),
        patch("etl.sources.transparencia.fetch_empenhos_obra", mock_empenhos),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", mock_liquidacoes),
        patch("etl.sources.transparencia.fetch_pagamentos_obra", mock_pagamentos),
    ):
        result2 = run_pipeline(output_dir=tmp_path, year=2025, full_refresh=False)

    assert result2["success"] is True
    # Agora sim, deve ter consultado os endpoints de detalhe porque o estado mudou
    assert mock_detalhes.call_count == 1
    assert mock_aditivos.call_count == 1


def test_full_refresh_forces_requery_of_all_mandates_and_details(tmp_path: Path):
    """Valida que full_refresh=True força a reconsulta de todos os mandatos e de todas as fichas."""
    from etl.runner import run_pipeline

    obra_base = dict(SAMPLE_TRANSPARENCIA_GRID[0])
    obra_id = obra_base["id"]

    # Cria índice prévio e arquivo individual
    index_previo = {
        "metadata": {"anoReferencia": 2025, "mandatosDisponiveis": ["2021-2024", "2025-2028"]},
        "obras": [obra_base],
    }
    with open(tmp_path / "index_2025.json", "w", encoding="utf-8") as f:
        json.dump(index_previo, f)

    obras_dir = tmp_path / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)
    with open(obras_dir / f"{obra_id}.json", "w", encoding="utf-8") as f:
        json.dump({
            "id": obra_id,
            "vigencia": {"dataTerminoAtualizado": obra_base.get("dtTerminoVigenciaAtualizado")},
            "funilFinanceiro": {
                "valorContratualVigente": obra_base.get("vlAtualizado"),
                "percentualExecutado": obra_base.get("percentualExecutado"),
            },
            "situacao": obra_base.get("dsSituacao"),
        }, f)

    mock_grid = MagicMock(return_value=[obra_base])
    mock_detalhes = MagicMock(return_value={})

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value=SAMPLE_IBGE_CENSO_2022),
        patch("etl.sources.transparencia.fetch_totalizador", return_value=SAMPLE_TRANSPARENCIA_TOTALIZADOR),
        patch("etl.sources.transparencia.fetch_grid_detalhada", mock_grid),
        patch("etl.sources.transparencia.fetch_detalhes_obra", mock_detalhes),
    ):
        result = run_pipeline(output_dir=tmp_path, year=2025, full_refresh=True)

    assert result["success"] is True
    # full_refresh=True deve consultar AMBOS os mandatos (2021-2024 e 2025-2028)
    assert mock_grid.call_count == 2
    # e deve consultar os detalhes mesmo com o arquivo já existente e indicadores idênticos
    assert mock_detalhes.call_count >= 1


def test_cli_accepts_full_refresh_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Valida que o CLI de linha de comando aceita e propaga a flag --full-refresh."""
    from etl.main import main

    with (
        patch("etl.main.run_pipeline") as mock_pipeline,
    ):
        monkeypatch.setattr(
            "sys.argv",
            [
                "etl.main",
                "--output-dir",
                str(tmp_path),
                "--year",
                "2025",
                "--full-refresh",
            ],
        )
        main()

        assert mock_pipeline.call_count == 1
        _, kwargs = mock_pipeline.call_args
        assert kwargs.get("full_refresh") is True

"""Testes de ponta a ponta para a Seam 1: Pipeline ETL de Obras e Território de Salvador.

Verifica a geração dos artefatos estáticos (GeoJSON de Bairros Oficiais,
GeoJSON de Prefeituras-Bairro e índice anual index_2025.json) a partir do ponto
de entrada do pipeline com fixtures dos dados governamentais.
"""

import json
from pathlib import Path
from unittest.mock import patch

from tests.etl.fixtures.sample_data import (
    SAMPLE_GEOSALVADOR_BAIRROS,
    SAMPLE_GEOSALVADOR_PREFEITURAS,
    SAMPLE_IBGE_CENSO_2022,
    SAMPLE_TRANSPARENCIA_GRID,
    SAMPLE_TRANSPARENCIA_TOTALIZADOR,
)


def test_pipeline_runs_and_generates_valid_static_artifacts(tmp_path: Path) -> None:
    """Valida a execução completa do pipeline ETL e integridade dos artefatos estáticos gerados.

    Sumário:
        Executa o pipeline ETL direcionado para um diretório temporário, simulando as
        fontes externas (GeoSalvador, Censo IBGE e Transparência Salvador), e verifica
        se as malhas GeoJSON e o índice anual atendem a todos os critérios da Issue 01.

    Argumentos:
        tmp_path: Diretório temporário fornecido pelo pytest para isolar a saída dos artefatos.

    Retornos:
        None. Assegura via asserções a integridade dos dados gerados.

    Erros:
        Lança AssertionError caso algum arquivo esteja ausente, malformado ou com valores incorretos.
    """
    from etl.runner import run_pipeline

    # Mock das fontes externas para garantir teste determinístico sem rede
    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value=SAMPLE_IBGE_CENSO_2022),
        patch("etl.sources.transparencia.fetch_totalizador", return_value=SAMPLE_TRANSPARENCIA_TOTALIZADOR),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=SAMPLE_TRANSPARENCIA_GRID),
    ):
        result = run_pipeline(output_dir=tmp_path, year=2025)

    assert result["success"] is True, "O pipeline deve reportar sucesso ao finalizar a execução."

    # 1. Validação do arquivo geo/bairros.geojson
    bairros_file = tmp_path / "geo" / "bairros.geojson"
    assert bairros_file.exists(), "O arquivo bairros.geojson deve ser gerado no diretório geo/."

    with open(bairros_file, "r", encoding="utf-8") as f:
        bairros_geo = json.load(f)

    assert bairros_geo.get("type") == "FeatureCollection"
    features_bairros = bairros_geo.get("features", [])
    assert len(features_bairros) == len(SAMPLE_GEOSALVADOR_BAIRROS["features"]), (
        "Deve conter todos os bairros presentes no fixture."
    )

    # Indexa bairros pelo nome normalizado para conferência individual
    bairros_map = {feat["properties"]["nome"]: feat["properties"] for feat in features_bairros}

    # Validação de Bairros Residenciais Comuns (Pituba e Cabula)
    assert "Pituba" in bairros_map
    pituba = bairros_map["Pituba"]
    assert pituba["populacao"] == 65000
    assert pituba["indice_vulnerabilidade"] == 0.12
    assert pituba["is_zona_especial_nao_residencial"] is False
    assert pituba["isZonaEspecialNaoResidencial"] is False
    assert pituba["prefeitura_bairro"] == "Barra/Pituba"

    assert "Cabula" in bairros_map
    cabula = bairros_map["Cabula"]
    assert cabula["populacao"] == 32000
    assert cabula["is_zona_especial_nao_residencial"] is False
    assert cabula["isZonaEspecialNaoResidencial"] is False

    # Validação das 3 Zonas Especiais Não-Residenciais
    zonas_especiais = ["Aeroporto", "Porto Seco Pirajá", "Centro Administrativo da Bahia - CAB"]
    for nome_ze in zonas_especiais:
        assert nome_ze in bairros_map, f"{nome_ze} deve estar presente na malha de bairros."
        props = bairros_map[nome_ze]
        assert props["is_zona_especial_nao_residencial"] is True, (
            f"O bairro {nome_ze} deve ser marcado como Zona Especial Não-Residencial."
        )
        assert props["isZonaEspecialNaoResidencial"] is True

    # 2. Validação do arquivo geo/prefeituras_bairro.geojson
    pb_file = tmp_path / "geo" / "prefeituras_bairro.geojson"
    assert pb_file.exists(), "O arquivo prefeituras_bairro.geojson deve ser gerado no diretório geo/."

    with open(pb_file, "r", encoding="utf-8") as f:
        pb_geo = json.load(f)

    assert pb_geo.get("type") == "FeatureCollection"
    features_pb = pb_geo.get("features", [])
    assert len(features_pb) == len(SAMPLE_GEOSALVADOR_PREFEITURAS["features"]), (
        "Deve conter todas as prefeituras-bairro do fixture."
    )
    pb_map = {feat["properties"]["nome"]: feat["properties"] for feat in features_pb}
    assert "Barra/Pituba" in pb_map
    assert pb_map["Barra/Pituba"]["populacao_total"] >= 65000

    # 3. Validação do arquivo index_2025.json
    index_file = tmp_path / "index_2025.json"
    assert index_file.exists(), "O arquivo index_2025.json deve ser gerado na raiz de dados."

    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    # Verifica estrutura dos KPIs Globais
    kpis = index_data.get("kpis_globais", {})
    assert kpis["totalObras"] == 25
    assert kpis["valorTotal"] == 150000000.00
    assert kpis["totalAtivas"] >= 2
    assert "investimentoPorHabitanteCidade" in kpis

    # Verifica listas consolidadas
    assert len(index_data.get("bairros", [])) == len(SAMPLE_GEOSALVADOR_BAIRROS["features"])
    assert len(index_data.get("prefeituras_bairro", [])) == len(SAMPLE_GEOSALVADOR_PREFEITURAS["features"])
    assert len(index_data.get("obras", [])) == 2

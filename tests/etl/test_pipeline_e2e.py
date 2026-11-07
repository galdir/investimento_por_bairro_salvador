"""Testes de ponta a ponta para a Seam 1: Pipeline ETL de Obras e Território de Salvador.

Verifica a geração dos artefatos estáticos (GeoJSON de Bairros Oficiais com investimentos,
GeoJSON de Prefeituras-Bairro com agregação regional, cache incremental e índice anual index_2025.json)
a partir do ponto de entrada do pipeline com fixtures dos dados governamentais.
"""

import json
from pathlib import Path
from unittest.mock import patch
import pytest

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
        se as malhas GeoJSON, o cache incremental e o índice anual atendem a todos os critérios.

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

    # 1. Validação do arquivo de cache incremental em disco
    cache_file = tmp_path / "geocoding_cache.json"
    assert cache_file.exists(), "O cache incremental de geocodificação deve ser gerado no diretório de saída."

    with open(cache_file, "r", encoding="utf-8") as f:
        cache_data = json.load(f)
    assert len(cache_data) >= len(SAMPLE_TRANSPARENCIA_GRID), "Todas as obras devem ser cacheadas."

    # 2. Validação do arquivo geo/bairros.geojson
    bairros_file = tmp_path / "geo" / "bairros.geojson"
    assert bairros_file.exists(), "O arquivo bairros.geojson deve ser gerado no diretório geo/."

    with open(bairros_file, "r", encoding="utf-8") as f:
        bairros_geo = json.load(f)

    assert bairros_geo.get("type") == "FeatureCollection"
    features_bairros = bairros_geo.get("features", [])
    assert len(features_bairros) == len(SAMPLE_GEOSALVADOR_BAIRROS["features"])

    bairros_map = {feat["properties"]["nome"]: feat["properties"] for feat in features_bairros}

    # Bairro Residencial Pituba
    assert "Pituba" in bairros_map
    pituba = bairros_map["Pituba"]
    assert pituba["populacao"] == 57894
    assert pituba["indice_vulnerabilidade"] == 0.12
    assert pituba["is_zona_especial_nao_residencial"] is False
    assert pituba["isZonaEspecialNaoResidencial"] is False
    assert pituba["prefeitura_bairro"] == "Barra/Pituba"
    assert "valorTotal" in pituba
    assert "investimentoPorHabitante" in pituba
    assert pituba["totalObras"] >= 1

    # Zonas Especiais Não-Residenciais
    nome_cab = "Centro Administrativo da Bahia" if "Centro Administrativo da Bahia" in bairros_map else "Centro Administrativo da Bahia - CAB"
    zonas_especiais = ["Aeroporto", "Porto Seco Pirajá", nome_cab]
    for nome_ze in zonas_especiais:
        assert nome_ze in bairros_map, f"{nome_ze} deve estar presente na malha de bairros."
        props = bairros_map[nome_ze]
        assert props["is_zona_especial_nao_residencial"] is True
        assert props["isZonaEspecialNaoResidencial"] is True
        # Per capita deve ser 0 para evitar distorções
        assert props["investimentoPorHabitante"] == 0.0

    # 3. Validação do arquivo geo/prefeituras_bairro.geojson
    pb_file = tmp_path / "geo" / "prefeituras_bairro.geojson"
    assert pb_file.exists(), "O arquivo prefeituras_bairro.geojson deve ser gerado no diretório geo/."

    with open(pb_file, "r", encoding="utf-8") as f:
        pb_geo = json.load(f)

    assert pb_geo.get("type") == "FeatureCollection"
    features_pb = pb_geo.get("features", [])
    assert len(features_pb) == len(SAMPLE_GEOSALVADOR_PREFEITURAS["features"])

    pb_map = {feat["properties"]["nome"]: feat["properties"] for feat in features_pb}
    assert "Barra/Pituba" in pb_map
    assert pb_map["Barra/Pituba"]["populacao_total"] >= 65000
    assert "investimentoPorHabitante" in pb_map["Barra/Pituba"]
    assert "valorTotal" in pb_map["Barra/Pituba"]

    # 4. Validação do arquivo index_2025.json
    index_file = tmp_path / "index_2025.json"
    assert index_file.exists(), "O arquivo index_2025.json deve ser gerado na raiz de dados."

    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    # Verifica metadados de mandatos municipais
    metadata = index_data.get("metadata", {})
    assert "mandatosDisponiveis" in metadata
    assert metadata["mandatosDisponiveis"] == ["2021-2024", "2025-2028"]

    # Verifica estrutura dos KPIs Globais incluindo transparência opaca
    kpis = index_data.get("kpis_globais", {})
    assert kpis["totalObras"] == 25
    assert kpis["valorTotal"] == 150000000.00
    assert kpis["totalAtivas"] >= 2
    assert "investimentoPorHabitanteCidade" in kpis
    assert "totalCriticas" in kpis
    assert "percentualCriticas" in kpis
    assert "totalAditivosValor" in kpis
    assert "percentualMedioAditivos" in kpis
    assert "totalNaoLocalizado" in kpis
    assert "valorNaoLocalizado" in kpis
    assert "percentualNaoLocalizado" in kpis

    # Verifica lista de obras compactas com atributos territoriais e mandatos
    obras = index_data.get("obras", [])
    assert len(obras) == 5

    obras_por_id = {o["id"]: o for o in obras}

    # 1001: Mobilidade / Verde / Bairro Pituba (Plurianual: 2021-2024 e 2025-2028)
    o1001 = obras_por_id[1001]
    assert o1001["tema"] == "Mobilidade, Pavimentação e Drenagem"
    assert o1001["semaforo"]["status"] == "VERDE"
    assert o1001["nivel"] == "Bairro"
    assert o1001["bairro"] == "Pituba"
    assert o1001["latitude"] is not None
    assert o1001["longitude"] is not None
    assert o1001["mandatos"] == ["2021-2024", "2025-2028"]
    assert o1001.get("dtInicioVigencia") == "2024-01-10T00:00:00.000Z"
    assert o1001.get("dtTerminoVigenciaAtualizado") == "2027-12-31T00:00:00.000Z"

    # 1002: Encostas / Amarelo / Bairro Liberdade
    o1002 = obras_por_id[1002]
    assert o1002["tema"] == "Encostas e Contenção"
    assert o1002["semaforo"]["status"] == "AMARELO"
    assert o1002["bairro"] == "Liberdade"
    assert o1002["latitude"] is not None

    # 1003: Educação / Vermelho / Lote Subúrbio
    o1003 = obras_por_id[1003]
    assert o1003["tema"] == "Educação e Escolas"
    assert o1003["semaforo"]["status"] == "VERMELHO"
    assert o1003["nivel"] == "Regional (Prefeitura-Bairro)"

    # 1004: Praças / Verde / Escopo Cidade
    o1004 = obras_por_id[1004]
    assert o1004["tema"] == "Praças, Esporte e Lazer"
    assert o1004["semaforo"]["status"] == "VERDE"
    assert o1004["nivel"] == "Escopo Cidade (Não-Localizado)"

    # 1005: Saúde / Vermelho / Escopo Cidade (sem USF específica informada)
    o1005 = obras_por_id[1005]
    assert o1005["tema"] == "Saúde"
    assert o1005["semaforo"]["status"] == "VERMELHO"
    assert o1005["nivel"] == "Escopo Cidade (Não-Localizado)"


def test_pipeline_cli_reuses_and_updates_incremental_geocoding_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valida que a execução via CLI reutiliza e preserva o Cache Incremental de geocodificação.

    Sumário:
        Executa o pipeline duas vezes via ponto de entrada CLI (`etl.main.main`) e verifica
        que a segunda execução atinge 100% de cache hits no `geocoding_cache.json`.

    Argumentos:
        tmp_path: Diretório temporário para isolar os artefatos estáticos e o cache.
        monkeypatch: Utilitário do pytest para simular argumentos de linha de comando (`sys.argv`).

    Retornos:
        None.

    Erros:
        Lança AssertionError se o cache incremental não for reutilizado ou preservado.
    """
    from etl.main import main
    from etl.runner import run_pipeline

    custom_cache = tmp_path / "geocoding_cache.json"

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value=SAMPLE_IBGE_CENSO_2022),
        patch("etl.sources.transparencia.fetch_totalizador", return_value=SAMPLE_TRANSPARENCIA_TOTALIZADOR),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=SAMPLE_TRANSPARENCIA_GRID),
    ):
        monkeypatch.setattr(
            "sys.argv",
            [
                "etl.main",
                "--output-dir",
                str(tmp_path),
                "--year",
                "2025",
                "--cache-file",
                str(custom_cache),
            ],
        )
        main()

        assert custom_cache.exists(), "O arquivo de cache incremental deve ter sido criado pelo CLI."

        # Segunda execução deve reutilizar todas as entradas do cache incremental
        second_run = run_pipeline(output_dir=tmp_path, year=2025, cache_file=custom_cache)
        assert second_run["cache_hits"] == len(SAMPLE_TRANSPARENCIA_GRID)
        assert (tmp_path / "obras" / "1001.json").exists()


def test_pipeline_normalizes_raw_online_geosalvador_and_sidra_payloads_and_computes_semaforo_rollups(
    tmp_path: Path,
) -> None:
    """Valida que o pipeline normaliza malhas brutas do GeoSalvador e demografia do SIDRA e calcula o semáforo nos rollups.

    Sumário:
        Injeta payloads brutos idênticos ao retorno de rede do ArcGIS (sem NM_BAIRRO/PREFEITURA_BAIRRO e com
        prefixos romanos) e do SIDRA (com sufixo ' - Salvador - BA' e variável percentual), assegurando que o
        pipeline normalize os 10 nomes de Prefeituras-Bairro, vincule os 171 bairros e preencha semáforos e vulnerabilidades.
    """
    from etl.runner import run_pipeline

    ref_dir = Path("etl/reference")
    with open(ref_dir / "geosalvador_bairros_real.geojson", "r", encoding="utf-8") as f:
        raw_bairros_fresh = json.load(f)
    with open(ref_dir / "geosalvador_prefeituras_real.geojson", "r", encoding="utf-8") as f:
        raw_pbs_fresh = json.load(f)
    with open(ref_dir / "ibge_censo_salvador.json", "r", encoding="utf-8") as f:
        raw_censo_fresh = json.load(f)

    import io

    class MockHTTPResponse:
        def __init__(self, data: bytes):
            self._io = io.BytesIO(data)
        def read(self, *args, **kwargs):
            return self._io.read(*args, **kwargs)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    mock_resp = MockHTTPResponse(json.dumps(raw_censo_fresh).encode("utf-8"))

    # Simula retorno online do GeoSalvador e SIDRA pela camada HTTP
    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=raw_bairros_fresh),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=raw_pbs_fresh),
        patch("urllib.request.urlopen", return_value=mock_resp),
        patch("etl.sources.transparencia.fetch_totalizador", return_value=SAMPLE_TRANSPARENCIA_TOTALIZADOR),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=SAMPLE_TRANSPARENCIA_GRID),
    ):
        result = run_pipeline(output_dir=tmp_path, year=2025)

    assert result["success"] is True

    index_file = tmp_path / "index_2025.json"
    assert index_file.exists()
    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    prefeituras = index_data.get("prefeituras_bairro", [])
    bairros = index_data.get("bairros", [])
    obras = index_data.get("obras", [])
    kpis = index_data.get("kpis_globais", {})

    # 1. 10 Prefeituras-Bairro canônicas sem prefixos romanos
    expected_pbs = {
        "Centro/Brotas",
        "Subúrbio/Ilhas",
        "Cajazeiras",
        "Itapuã/Ipitanga",
        "Cidade Baixa",
        "Barra/Pituba",
        "Liberdade/São Caetano",
        "Cabula/Tancredo Neves",
        "Pau da Lima",
        "Valéria",
    }
    nomes_pbs = {pb["nome"] for pb in prefeituras}
    assert nomes_pbs == expected_pbs, f"Divergência nas Prefeituras-Bairro: {nomes_pbs ^ expected_pbs}"

    # 2. Todas as 10 Prefeituras-Bairro devem ter população > 0 coerente com seus bairros
    pop_por_pb: dict[str, int] = {}
    for b in bairros:
        pb_nome = b.get("prefeitura_bairro")
        assert pb_nome in expected_pbs, f"Bairro '{b.get('nome')}' tem prefeitura_bairro inválida: '{pb_nome}'"
        pop_por_pb[pb_nome] = pop_por_pb.get(pb_nome, 0) + int(b.get("populacao", 0))

    for pb in prefeituras:
        assert pb["populacao_total"] > 0, f"Prefeitura '{pb['nome']}' tem populacao_total zerada."
        assert pb["populacao_total"] == pop_por_pb[pb["nome"]]

    # 3. Nenhum dos 171 bairros tem prefeitura_bairro vazia
    assert len(bairros) == 171
    for b in bairros:
        assert b.get("prefeitura_bairro"), f"Bairro '{b.get('nome')}' está sem prefeitura_bairro."

    # 4. Rollup de semáforo: obrasVerde + obrasAmarelo + obrasVermelho == totalObras em todos os territórios
    for b in bairros:
        soma_semaforo = b.get("obrasVerde", 0) + b.get("obrasAmarelo", 0) + b.get("obrasVermelho", 0)
        assert soma_semaforo == b.get("totalObras", 0), f"Bairro '{b['nome']}' semáforos ({soma_semaforo}) != totalObras ({b.get('totalObras')})"

    for pb in prefeituras:
        soma_semaforo = pb.get("obrasVerde", 0) + pb.get("obrasAmarelo", 0) + pb.get("obrasVermelho", 0)
        assert soma_semaforo == pb.get("totalObras", 0), f"Prefeitura '{pb['nome']}' semáforos ({soma_semaforo}) != totalObras ({pb.get('totalObras')})"

    # 5. Índice de vulnerabilidade determinístico e diferenciado (> 10 valores distintos)
    vulns = {b.get("indice_vulnerabilidade") for b in bairros}
    assert len(vulns) > 10, f"Índices de vulnerabilidade colapsados: apenas {len(vulns)} valores distintos: {vulns}"

    bairros_by_name = {b["nome"]: b for b in bairros}
    assert bairros_by_name["Pituba"]["indice_vulnerabilidade"] == 0.12
    assert bairros_by_name["Liberdade"]["indice_vulnerabilidade"] == 0.78
    assert bairros_by_name["Cabula"]["indice_vulnerabilidade"] == 0.55
    assert bairros_by_name["Aeroporto"]["indice_vulnerabilidade"] == 0.05
    assert bairros_by_name["Porto Seco Pirajá"]["indice_vulnerabilidade"] == 0.20
    cab_bairro = bairros_by_name.get("Centro Administrativo da Bahia - CAB") or bairros_by_name.get("Centro Administrativo da Bahia")
    assert cab_bairro is not None
    assert cab_bairro["indice_vulnerabilidade"] == 0.08

    # 6. Obras de nível Bairro possuem latitude, longitude, bairro canônico e prefeitura_bairro
    obras_bairro = [o for o in obras if o.get("nivel") == "Bairro"]
    assert len(obras_bairro) > 0
    for o in obras_bairro:
        assert o.get("latitude") is not None, f"Obra {o.get('id')} de nível Bairro sem latitude."
        assert o.get("longitude") is not None, f"Obra {o.get('id')} de nível Bairro sem longitude."
        assert o.get("prefeitura_bairro") in expected_pbs, f"Obra {o.get('id')} com prefeitura_bairro inválida: {o.get('prefeitura_bairro')}"
        assert o.get("bairro") in bairros_by_name, f"Obra {o.get('id')} com bairro não oficial: {o.get('bairro')}"

    # 7. KPIs globais consistentes
    assert kpis.get("valorTotal", 0.0) >= kpis.get("valorNaoLocalizado", 0.0)
    assert 0 <= kpis.get("percentualNaoLocalizado", 0.0) <= 100



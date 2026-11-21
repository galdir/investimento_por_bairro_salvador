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


def test_pipeline_runs_and_generates_valid_static_artifacts(
    tmp_path: Path, portal_simulado, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    from etl.consultas import ConsultaPagamentos
    from etl.runner import run_pipeline

    # Obras vigentes Em Execução (1001, 1002, 1004) recebem movimentação recente para preservar cobertura
    # de VERDE e AMARELO, mantendo 1003 e 1005 sem movimentação para exercitar o disparo de VERMELHO.
    contratos_com_movimentacao_recente = {"001/2024", "002/2024", "042/2024"}
    monkeypatch.setattr(
        "etl.runner.coletar_pagamentos",
        lambda ug, contrato, referencia, janelas: ConsultaPagamentos(
            [{"ordemBancaria": f"OB-{contrato}", "dataPagamento": referencia, "pago": "R$ 10.000,00"}]
            if str(contrato) in contratos_com_movimentacao_recente
            else [],
            referencia,
            True,
            True,
        ),
    )

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
    tmp_path = Path(result["versao_dir"])

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
    assert 0.0 <= pituba["indice_vulnerabilidade"] <= 1.0
    assert "pct_esgoto_inadequado" in pituba
    assert "pct_agua_inadequada" in pituba
    assert "pct_analfabetismo_15mais" in pituba
    assert pituba["vulnerabilidade_estimada_contiguidade"] is False
    assert pituba["is_zona_especial_nao_residencial"] is False
    assert pituba["isZonaEspecialNaoResidencial"] is False
    assert pituba["prefeitura_bairro"] == "Barra/Pituba"
    assert "valorTotal" in pituba
    assert "investimentoPorHabitante" in pituba
    assert pituba["totalObras"] >= 1

    # Contiguidade exclusiva para Aquarius (população 0 e per capita indisponível/null)
    assert "Aquarius" in bairros_map
    aquarius = bairros_map["Aquarius"]
    assert aquarius["populacao"] == 0
    assert aquarius["vulnerabilidade_estimada_contiguidade"] is True
    assert aquarius["pct_esgoto_inadequado"] > 0
    assert aquarius["pct_agua_inadequada"] > 0
    assert aquarius["pct_analfabetismo_15mais"] > 0
    assert aquarius["investimentoPorHabitante"] is None
    assert aquarius["investimentoPorHabitantePago"] is None

    # Bairros com dados reais do Censo 2022 (sem marcação de contiguidade)
    for b_real in ["Chame-Chame", "Ilha de Maré", "Colinas de Periperi"]:
        assert b_real in bairros_map
        assert bairros_map[b_real]["vulnerabilidade_estimada_contiguidade"] is False
        assert bairros_map[b_real]["pct_esgoto_inadequado"] > 0

    # Zonas Especiais Não-Residenciais
    nome_cab = "Centro Administrativo da Bahia" if "Centro Administrativo da Bahia" in bairros_map else "Centro Administrativo da Bahia - CAB"
    zonas_especiais = ["Aeroporto", "Porto Seco Pirajá", nome_cab]
    for nome_ze in zonas_especiais:
        assert nome_ze in bairros_map, f"{nome_ze} deve estar presente na malha de bairros."
        props = bairros_map[nome_ze]
        assert props["is_zona_especial_nao_residencial"] is True
        assert props["isZonaEspecialNaoResidencial"] is True
        # Per capita e vulnerabilidade devem ser 0 para evitar distorções
        assert props["investimentoPorHabitante"] == 0.0
        assert props["indice_vulnerabilidade"] == 0.0
        assert props["pct_esgoto_inadequado"] == 0.0
        assert props["pct_agua_inadequada"] == 0.0
        assert props["pct_analfabetismo_15mais"] == 0.0
        assert props["vulnerabilidade_estimada_contiguidade"] is False

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
    assert pb_map["Barra/Pituba"]["vulnerabilidade_estimada_contiguidade"] is True
    assert pb_map["Barra/Pituba"]["bairros_vulnerabilidade_estimada"] == ["Aquarius"]
    assert "Subúrbio/Ilhas" in pb_map
    assert pb_map["Subúrbio/Ilhas"]["vulnerabilidade_estimada_contiguidade"] is False
    assert pb_map["Subúrbio/Ilhas"]["bairros_vulnerabilidade_estimada"] == []
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
    assert metadata["mandatosDisponiveis"] == ["2017-2020", "2021-2024", "2025-2028"]

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
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, portal_simulado
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

        versao_inicial = tmp_path / json.loads((tmp_path / "atual.json").read_text(encoding="utf-8"))["caminho"]
        assert (versao_inicial / "geocoding_cache.json").exists()

        # Segunda execução deve reutilizar todas as entradas do cache incremental
        second_run = run_pipeline(output_dir=tmp_path, year=2025, cache_file=custom_cache)
        assert second_run["cache_hits"] == len(SAMPLE_TRANSPARENCIA_GRID)
        assert (Path(second_run["versao_dir"]) / "obras" / "1001.json").exists()


def test_pipeline_normalizes_raw_online_geosalvador_and_sidra_payloads_and_computes_semaforo_rollups(
    tmp_path: Path, portal_simulado,
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

    tmp_path = Path(result["versao_dir"])

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
    # Invariante de ordenação socioeconômica do Censo 2022
    assert (
        bairros_by_name["Pituba"]["indice_vulnerabilidade"]
        < bairros_by_name["Cabula"]["indice_vulnerabilidade"]
        < bairros_by_name["Liberdade"]["indice_vulnerabilidade"]
    )
    # Zonas Especiais Não-Residenciais isentas (0.0)
    assert bairros_by_name["Aeroporto"]["indice_vulnerabilidade"] == 0.0
    assert bairros_by_name["Porto Seco Pirajá"]["indice_vulnerabilidade"] == 0.0
    cab_bairro = bairros_by_name.get("Centro Administrativo da Bahia - CAB") or bairros_by_name.get("Centro Administrativo da Bahia")
    assert cab_bairro is not None
    assert cab_bairro["indice_vulnerabilidade"] == 0.0

    # Sub-indicadores nas Prefeituras-Bairro
    for pb in prefeituras:
        assert "pct_esgoto_inadequado" in pb
        assert "pct_agua_inadequada" in pb
        assert "pct_analfabetismo_15mais" in pb
        assert pb["pct_esgoto_inadequado"] >= 0
        assert pb["pct_agua_inadequada"] >= 0
        assert pb["pct_analfabetismo_15mais"] >= 0

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


def test_pipeline_recalcula_semaforo_pos_ficha_com_data_referencia_e_pagamentos_consolidados(
    tmp_path: Path,
) -> None:
    """Valida na fronteira do orquestrador o recálculo determinístico pós-ficha do Semáforo."""
    from etl.consultas import ConsultaPagamentos
    from etl.runner import run_pipeline

    data_ref_r1 = "2025-06-01"
    data_ref_r2 = "2025-06-15"

    # Obras desenhadas para exercitar todos os critérios pós-ficha com data_referencia fixa:
    # 2001: Vigente, sem variação, mas com aditivo de prorrogação na ficha + pagamento recente -> AMARELO
    # 2002: Vigente Em Execução (<95%) com último pagamento > 90 dias antes de 2025-06-01 -> VERMELHO
    # 2003: Vigente Em Execução (<95%) iniciada > 90 dias sem nenhuma movimentação -> VERMELHO
    # 2004: Expirada > 90 dias com execução >= 95%, sem outros alertas -> VERDE
    # 2005: Expirada > 90 dias com execução >= 95% + prorrogação na ficha (elegível a consolidados!) -> AMARELO
    # 2006: Expirada > 90 dias com execução >= 95% + variação > 25% -> VERMELHO
    # 2007: Ajustar Cronograma > 90 dias sem pagamento, dentro da vigência -> VERDE
    grid_obras = [
        {
            "id": 2001,
            "cdUnidadeGestora": 2401,
            "sgOrgao": "SUCOP",
            "nuContratoSigef": "101/2025",
            "dsObjeto": "Drenagem na Pituba",
            "vlOriginal": 1000000.0,
            "vlAtualizado": 1000000.0,
            "dtInicioVigencia": "2025-01-10T00:00:00.000Z",
            "dtFimVigenciaOriginal": "2026-12-31T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
            "percentualExecutado": 50.0,
            "dsSituacao": "Em Execução",
            "nmCredor": "EMP A LTDA",
            "nuDocumentoCredor": "11.111.111/0001-11",
        },
        {
            "id": 2002,
            "cdUnidadeGestora": 2401,
            "sgOrgao": "SUCOP",
            "nuContratoSigef": "102/2025",
            "dsObjeto": "Pavimentação na Pituba",
            "vlOriginal": 1000000.0,
            "vlAtualizado": 1000000.0,
            "dtInicioVigencia": "2025-01-10T00:00:00.000Z",
            "dtFimVigenciaOriginal": "2026-12-31T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
            "percentualExecutado": 40.0,
            "dsSituacao": "Em Execução",
            "nmCredor": "EMP A LTDA",
            "nuDocumentoCredor": "11.111.111/0001-11",
        },
        {
            "id": 2003,
            "cdUnidadeGestora": 2401,
            "sgOrgao": "SUCOP",
            "nuContratoSigef": "103/2025",
            "dsObjeto": "Contenção na Liberdade",
            "vlOriginal": 1000000.0,
            "vlAtualizado": 1000000.0,
            "dtInicioVigencia": "2025-01-10T00:00:00.000Z",
            "dtFimVigenciaOriginal": "2026-12-31T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
            "percentualExecutado": 10.0,
            "dsSituacao": "Em Execução",
            "nmCredor": "EMP A LTDA",
            "nuDocumentoCredor": "11.111.111/0001-11",
        },
        {
            "id": 2004,
            "cdUnidadeGestora": 2401,
            "sgOrgao": "SUCOP",
            "nuContratoSigef": "104/2023",
            "dsObjeto": "Praça na Pituba",
            "vlOriginal": 1000000.0,
            "vlAtualizado": 1000000.0,
            "dtInicioVigencia": "2023-01-01T00:00:00.000Z",
            "dtFimVigenciaOriginal": "2024-01-01T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2024-01-01T00:00:00.000Z",
            "percentualExecutado": 96.0,
            "dsSituacao": "Em Execução",
            "nmCredor": "EMP A LTDA",
            "nuDocumentoCredor": "11.111.111/0001-11",
        },
        {
            "id": 2005,
            "cdUnidadeGestora": 2401,
            "sgOrgao": "SUCOP",
            "nuContratoSigef": "105/2023",
            "dsObjeto": "Escola na Liberdade",
            "vlOriginal": 1000000.0,
            "vlAtualizado": 1000000.0,
            "dtInicioVigencia": "2023-01-01T00:00:00.000Z",
            "dtFimVigenciaOriginal": "2024-01-01T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2024-01-01T00:00:00.000Z",
            "percentualExecutado": 95.0,
            "dsSituacao": "Em Execução",
            "nmCredor": "EMP A LTDA",
            "nuDocumentoCredor": "11.111.111/0001-11",
        },
        {
            "id": 2006,
            "cdUnidadeGestora": 2401,
            "sgOrgao": "SUCOP",
            "nuContratoSigef": "106/2023",
            "dsObjeto": "Creche na Pituba",
            "vlOriginal": 1000000.0,
            "vlAtualizado": 1300000.0,
            "dtInicioVigencia": "2023-01-01T00:00:00.000Z",
            "dtFimVigenciaOriginal": "2024-01-01T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2024-01-01T00:00:00.000Z",
            "percentualExecutado": 98.0,
            "dsSituacao": "Em Execução",
            "nmCredor": "EMP A LTDA",
            "nuDocumentoCredor": "11.111.111/0001-11",
        },
        {
            "id": 2007,
            "cdUnidadeGestora": 2401,
            "sgOrgao": "SUCOP",
            "nuContratoSigef": "107/2025",
            "dsObjeto": "Campo na Pituba",
            "vlOriginal": 1000000.0,
            "vlAtualizado": 1000000.0,
            "dtInicioVigencia": "2025-01-10T00:00:00.000Z",
            "dtFimVigenciaOriginal": "2026-12-31T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
            "percentualExecutado": 20.0,
            "dsSituacao": "Ajustar Cronograma",
            "nmCredor": "EMP A LTDA",
            "nuDocumentoCredor": "11.111.111/0001-11",
        },
    ]

    aditivos_por_contrato = {
        "101/2025": [{"nuAditivo": "1º TA", "dsTipoAlteracao": "Prorrogação de Prazo"}],
        "105/2023": [{"nuAditivo": "1º TA", "dsTipoAlteracao": "Prorrogação de Prazo"}],
    }
    pagamentos_por_contrato = {
        # 2001: pagamento recente em 2025-05-15 (17 dias antes de 2025-06-01)
        "101/2025": [{"ordemBancaria": "OB1", "dataPagamento": "15/05/2025", "pago": "R$ 100.000,00"}],
        # 2002: último pagamento em 2025-02-01 (120 dias antes de 2025-06-01 -> > 90 dias)
        "102/2025": [{"ordemBancaria": "OB2", "dataPagamento": "01/02/2025", "pago": "R$ 100.000,00"}],
    }

    def consulta_pagamentos(ug, contrato, referencia):
        return ConsultaPagamentos(
            registros=pagamentos_por_contrato.get(str(contrato), []),
            data_referencia=referencia,
            concluida=True,
            validada=True,
            limitacoes_conhecidas=[],
        )

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value=SAMPLE_IBGE_CENSO_2022),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={"totalObras": 7, "valorTotal": 7300000.0, "totalPago": 200000.0}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=grid_obras),
        patch("etl.sources.transparencia.fetch_detalhes_obra", return_value={}),
        patch("etl.sources.transparencia.fetch_aditivos_obra", side_effect=lambda ug, contrato, year=2025: aditivos_por_contrato.get(str(contrato), [])),
        patch("etl.sources.transparencia.fetch_dotacao_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_empenhos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", return_value=[]),
    ):
        r1 = run_pipeline(
            output_dir=tmp_path,
            year=2025,
            consulta_pagamentos=consulta_pagamentos,
            data_referencia_pagamentos=data_ref_r1,
        )
        # Segunda rodada para exercitar o caminho de Contrato com Pagamentos Consolidados (2004, 2005, 2006)
        r2 = run_pipeline(
            output_dir=tmp_path,
            year=2025,
            consulta_pagamentos=consulta_pagamentos,
            data_referencia_pagamentos=data_ref_r2,
        )

    for resultado in (r1, r2):
        versao_dir = Path(resultado["versao_dir"])
        indice = json.loads((versao_dir / "index_2025.json").read_text(encoding="utf-8"))
        obras_idx = {o["id"]: o for o in indice["obras"]}

        esperado = {
            2001: "AMARELO",
            2002: "VERMELHO",
            2003: "VERMELHO",
            2004: "VERDE",
            2005: "AMARELO",
            2006: "VERMELHO",
            2007: "VERDE",
        }
        for obra_id, status_esperado in esperado.items():
            ficha = json.loads((versao_dir / "obras" / f"{obra_id}.json").read_text(encoding="utf-8"))
            assert obras_idx[obra_id]["semaforo"]["status"] == status_esperado, f"Obra {obra_id} no índice"
            assert ficha["semaforo"] == obras_idx[obra_id]["semaforo"], f"Paridade ficha vs índice para obra {obra_id}"

        assert indice["kpis_globais"]["totalCriticas"] == 3  # 2002, 2003, 2006
        pituba_rollup = next(b for b in indice["bairros"] if b["nome"] == "Pituba")
        liberdade_rollup = next(b for b in indice["bairros"] if b["nome"] == "Liberdade")
        assert (pituba_rollup["obrasVerde"], pituba_rollup["obrasAmarelo"], pituba_rollup["obrasVermelho"]) == (2, 1, 2)
        assert (liberdade_rollup["obrasVerde"], liberdade_rollup["obrasAmarelo"], liberdade_rollup["obrasVermelho"]) == (0, 1, 1)

    # Garante que o caminho de pagamentos consolidados foi realmente exercitado na rodada 2
    ficha_2005_r2 = json.loads((Path(r2["versao_dir"]) / "obras" / "2005.json").read_text(encoding="utf-8"))
    assert ficha_2005_r2["apuracaoPagamentos"]["pagamentosConsolidados"] is True
    assert ficha_2005_r2["semaforo"]["status"] == "AMARELO"


def test_pipeline_expurga_cancelado_sem_gasto_e_blinda_kpis_e_limitacoes(tmp_path: Path) -> None:
    """Contrato Cancelado sem gasto é expurgado do índice, rollups, KPIs e limitações (inclusive consolidado)."""
    from etl.runner import ConsultaPagamentos, run_pipeline

    data_ref = "2025-06-01"
    grid_obras = [
        {
            "id": 3001,
            "cdUnidadeGestora": "2401",
            "sgOrgao": "SUCOP",
            "nuContratoSigef": "301/2025",
            "dsObjeto": "Drenagem na Pituba",
            "vlOriginal": 2000000.0,
            "vlAtualizado": 2000000.0,
            "vlEmpenhado": 1000000.0,
            "dtInicioVigencia": "2025-01-10T00:00:00.000Z",
            "dtFimVigenciaOriginal": "2026-12-31T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
            "percentualExecutado": 30.0,
            "dsSituacao": "Em Execução",
            "nmCredor": "EMP A LTDA",
            "nuDocumentoCredor": "11.111.111/0001-11",
        },
        {
            "id": 3002,
            "cdUnidadeGestora": "2401",
            "sgOrgao": "SUCOP",
            "nuContratoSigef": "302/2025",
            "dsObjeto": "Pavimentação na Pituba",
            "vlOriginal": 5000000.0,
            "vlAtualizado": 5000000.0,
            "vlEmpenhado": 3000000.0,
            "dtInicioVigencia": "2025-01-10T00:00:00.000Z",
            "dtFimVigenciaOriginal": "2026-12-31T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
            "percentualExecutado": 0.0,
            "dsSituacao": "Cancelado",
            "nmCredor": "EMP B LTDA",
            "nuDocumentoCredor": "22.222.222/0001-22",
        },
    ]

    def consulta_pagamentos(ug, contrato, referencia):
        if str(contrato) == "302/2025":
            return ConsultaPagamentos(
                registros=[],
                data_referencia=referencia,
                concluida=True,
                validada=True,
                limitacoes_conhecidas=["limitacao_exclusiva_expurgado"],
            )
        return ConsultaPagamentos(
            registros=[{"ordemBancaria": "OB1", "dataPagamento": "15/05/2025", "pago": 50000.0}],
            data_referencia=referencia,
            concluida=True,
            validada=True,
            limitacoes_conhecidas=["limitacao_contrato_ativo"],
        )

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value=SAMPLE_IBGE_CENSO_2022),
        patch(
            "etl.sources.transparencia.fetch_totalizador",
            return_value={
                "totalObras": 2,
                "valorTotal": 7000000.0,
                "totalEmpenhado": 4000000.0,
                "totalAtivas": 1,
                "totalPago": 50000.0,
            },
        ),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=grid_obras),
        patch("etl.sources.transparencia.fetch_detalhes_obra", return_value={}),
        patch("etl.sources.transparencia.fetch_aditivos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_dotacao_obra", return_value=[]),
        patch(
            "etl.sources.transparencia.fetch_empenhos_obra",
            side_effect=lambda ug, contrato, year=2025: (
                [{"valEmpenhado": 1000000.0}]
                if str(contrato) == "301/2025"
                else [{"valEmpenhado": 3000000.0}]
            ),
        ),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", return_value=[]),
    ):
        resultado = run_pipeline(
            output_dir=tmp_path,
            year=2025,
            consulta_pagamentos=consulta_pagamentos,
            data_referencia_pagamentos=data_ref,
        )

    versao_dir = Path(resultado["versao_dir"])
    indice = json.loads((versao_dir / "index_2025.json").read_text(encoding="utf-8"))

    assert resultado["total_obras"] == 1
    assert resultado["limitacoes_conhecidas"] == ["limitacao_contrato_ativo"]
    assert [o["id"] for o in indice["obras"]] == [3001]
    assert not (versao_dir / "obras" / "3002.json").exists()

    assert indice["kpis_globais"]["totalObras"] == 1
    assert indice["kpis_globais"]["valorTotal"] == 2000000.0
    assert indice["kpis_globais"]["totalEmpenhado"] == 1000000.0
    assert indice["kpis_globais"]["totalAtivas"] == 1
    assert indice["kpis_globais"]["totalCriticas"] == 0

    pituba_rollup = next(b for b in indice["bairros"] if b["nome"] == "Pituba")
    assert pituba_rollup["totalObras"] == 1
    assert pituba_rollup["valorTotal"] == 2000000.0


def test_pipeline_carteira_100_por_cento_expurgada_zera_kpis_e_limitacoes(tmp_path: Path) -> None:
    """Carteira com 100% dos contratos Cancelados sem gasto é tratada como completa e zerada."""
    from etl.runner import ConsultaPagamentos, run_pipeline

    grid_obras = [
        {
            "id": 3010,
            "cdUnidadeGestora": "2401",
            "sgOrgao": "SUCOP",
            "nuContratoSigef": "310/2025",
            "dsObjeto": "Contenção na Pituba",
            "vlOriginal": 4000000.0,
            "vlAtualizado": 4000000.0,
            "vlEmpenhado": 2000000.0,
            "dtInicioVigencia": "2025-01-10T00:00:00.000Z",
            "dtFimVigenciaOriginal": "2026-12-31T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
            "percentualExecutado": 0.0,
            "dsSituacao": "Cancelado",
            "nmCredor": "EMP C LTDA",
            "nuDocumentoCredor": "33.333.333/0001-33",
        },
    ]

    def consulta_pagamentos(ug, contrato, referencia):
        return ConsultaPagamentos(
            registros=[],
            data_referencia=referencia,
            concluida=True,
            validada=True,
            limitacoes_conhecidas=["limitacao_exclusiva_100_expurgada"],
        )

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value=SAMPLE_IBGE_CENSO_2022),
        patch(
            "etl.sources.transparencia.fetch_totalizador",
            return_value={
                "totalObras": 1,
                "valorTotal": 4000000.0,
                "totalEmpenhado": 2000000.0,
                "totalLiquidado": 0.0,
                "totalPago": 0.0,
                "totalAtivas": 0,
            },
        ),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=grid_obras),
        patch("etl.sources.transparencia.fetch_detalhes_obra", return_value={}),
        patch("etl.sources.transparencia.fetch_aditivos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_dotacao_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_empenhos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", return_value=[]),
    ):
        resultado = run_pipeline(
            output_dir=tmp_path,
            year=2025,
            consulta_pagamentos=consulta_pagamentos,
            data_referencia_pagamentos="2025-06-01",
        )

    versao_dir = Path(resultado["versao_dir"])
    indice = json.loads((versao_dir / "index_2025.json").read_text(encoding="utf-8"))

    assert resultado["total_obras"] == 0
    assert resultado["limitacoes_conhecidas"] == []
    assert indice["obras"] == []
    assert not (versao_dir / "obras" / "3010.json").exists()
    assert indice["kpis_globais"]["totalObras"] == 0
    assert indice["kpis_globais"]["valorTotal"] == 0.0
    assert indice["kpis_globais"]["totalEmpenhado"] == 0.0
    assert indice["kpis_globais"]["totalLiquidado"] == 0.0
    assert indice["kpis_globais"]["totalPago"] == 0.0
    assert indice["kpis_globais"]["totalAtivas"] == 0
    assert indice["kpis_globais"]["totalCriticas"] == 0


def test_pipeline_preserva_cancelado_com_gasto_ou_incerteza_em_vermelho(tmp_path: Path) -> None:
    """Casos conservadores de não-expurgo mantêm contratos Cancelados publicados em Vermelho (Crítica)."""
    from etl.runner import ConsultaPagamentos, run_pipeline

    def _obra_cancelada(obra_id: int, contrato: str) -> dict:
        return {
            "id": obra_id,
            "cdUnidadeGestora": "2401",
            "sgOrgao": "SUCOP",
            "nuContratoSigef": contrato,
            "dsObjeto": f"Obra Cancelada {obra_id} na Pituba",
            "vlOriginal": 1000000.0,
            "vlAtualizado": 1000000.0,
            "dtInicioVigencia": "2025-01-10T00:00:00.000Z",
            "dtFimVigenciaOriginal": "2026-12-31T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
            "percentualExecutado": 10.0,
            "dsSituacao": "Cancelado",
            "nmCredor": "EMP A LTDA",
            "nuDocumentoCredor": "11.111.111/0001-11",
        }

    grid_obras = [
        _obra_cancelada(4001, "401/2025"),  # pagamento registrado
        _obra_cancelada(4002, "402/2025"),  # liquidação positiva e pagamento zero
        _obra_cancelada(4003, "403/2025"),  # movimento positivo compensado por estorno
        _obra_cancelada(4004, "404/2025"),  # valor pago indisponível (registro sem valor)
    ]

    def consulta_pagamentos(ug, contrato, referencia):
        if str(contrato) == "401/2025":
            registros = [{"ordemBancaria": "OB1", "dataPagamento": "10/03/2025", "pago": 1000.0}]
        elif str(contrato) == "402/2025":
            registros = []
        elif str(contrato) == "403/2025":
            registros = [
                {"ordemBancaria": "OB3A", "dataPagamento": "10/03/2025", "pago": 500.0},
                {"ordemBancaria": "OB3B", "dataPagamento": "12/03/2025", "pago": -500.0},
            ]
        else:
            registros = [{"ordemBancaria": "OB4", "dataPagamento": "10/03/2025"}]
        return ConsultaPagamentos(
            registros=registros,
            data_referencia=referencia,
            concluida=True,
            validada=True,
            limitacoes_conhecidas=[],
        )

    def fetch_liquidacoes(ug, contrato, year=2025):
        if str(contrato) == "402/2025":
            return [{"notaLiquidacao": "NL-402", "valLiqLiquidacao": 500.0}]
        return []

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value=SAMPLE_IBGE_CENSO_2022),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={"totalObras": 4, "valorTotal": 4000000.0}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=grid_obras),
        patch("etl.sources.transparencia.fetch_detalhes_obra", return_value={}),
        patch("etl.sources.transparencia.fetch_aditivos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_dotacao_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_empenhos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", side_effect=fetch_liquidacoes),
    ):
        resultado = run_pipeline(
            output_dir=tmp_path,
            year=2025,
            consulta_pagamentos=consulta_pagamentos,
            data_referencia_pagamentos="2025-06-01",
        )

    versao_dir = Path(resultado["versao_dir"])
    indice = json.loads((versao_dir / "index_2025.json").read_text(encoding="utf-8"))
    obras_idx = {o["id"]: o for o in indice["obras"]}

    assert set(obras_idx.keys()) == {4001, 4002, 4003, 4004}
    for obra_id in (4001, 4002, 4003, 4004):
        assert obras_idx[obra_id]["semaforo"]["status"] == "VERMELHO"
        ficha = json.loads((versao_dir / "obras" / f"{obra_id}.json").read_text(encoding="utf-8"))
        assert ficha["semaforo"]["status"] == "VERMELHO"

    assert indice["kpis_globais"]["totalObras"] == 4
    assert indice["kpis_globais"]["totalCriticas"] == 4


def test_kpis_globais_desconta_expurgados_sem_quebrar_carteira_parcial() -> None:
    """Desconto de expurgados impede fallback indevido na completa e preserva carteira genuinamente parcial."""
    from etl.domain.kpis import calcular_kpis_globais

    expurgada = [{"id": 99, "vlAtualizado": 5000000.0, "vlEmpenhado": 3000000.0, "dsSituacao": "Cancelado"}]
    ativa = [{"id": 1, "vlAtualizado": 2000000.0, "vlEmpenhado": 1000000.0, "dsSituacao": "Em Execução", "vlPagoReal": 100000.0}]

    # Carteira genuinamente parcial: API reporta 5 obras (10M), detalhe tem 1 ativa (2M) + 1 expurgada (5M)
    # Após desconto da expurgada: restam 4 obras esperadas (5M) > 1 detalhada -> continua parcial!
    kpis_parcial = calcular_kpis_globais(
        totalizador_transparencia={"totalObras": 5, "valorTotal": 10000000.0, "totalEmpenhado": 6000000.0, "totalAtivas": 4},
        obras_detalhadas=ativa,
        populacao_total_cidade=100000,
        obras_expurgadas=expurgada,
    )
    assert kpis_parcial["totalObras"] == 4
    assert kpis_parcial["valorTotal"] == 5000000.0
    assert kpis_parcial["totalEmpenhado"] == 3000000.0
    assert kpis_parcial["totalAtivas"] == 4




"""Garantias de publicação observadas pela entrada do pipeline."""

from pathlib import Path
from io import BytesIO
from copy import deepcopy
import json
import os
from unittest.mock import patch

import pytest

from etl.runner import run_pipeline
from etl.consultas import ConsultaPagamentos
from tests.etl.fixtures.sample_data import (
    SAMPLE_GEOSALVADOR_BAIRROS,
    SAMPLE_GEOSALVADOR_PREFEITURAS,
    SAMPLE_TRANSPARENCIA_GRID,
)


def pagamentos_simulados(ug, contrato, referencia):
    return ConsultaPagamentos([], referencia, concluida=True, validada=True)


def test_falha_geografica_preserva_arquivos_publicados(tmp_path: Path) -> None:
    indice = tmp_path / "index_2025.json"
    indice.write_text('{"versao": "anterior"}', encoding="utf-8")
    anterior = indice.read_bytes()

    with (
        patch("urllib.request.urlopen", side_effect=OSError("GeoSalvador indisponível")),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[]),
        pytest.raises(OSError, match="GeoSalvador indisponível"),
    ):
        run_pipeline(tmp_path)

    assert indice.read_bytes() == anterior


def test_erro_de_geracao_tardia_preserva_todos_os_arquivos(tmp_path: Path) -> None:
    """Uma falha de serialização posterior às fichas não altera o acervo anterior."""
    (tmp_path / "obras").mkdir()
    (tmp_path / "obras" / "antiga.json").write_text('{"id":"antiga"}', encoding="utf-8")
    (tmp_path / "index_2025.json").write_text('{"metadata":{"data":"antiga"},"obras":[]}', encoding="utf-8")
    antes = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    bairros = deepcopy(SAMPLE_GEOSALVADOR_BAIRROS)
    bairros["features"][0]["geometry"]["nao_serializavel"] = {1}

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=bairros),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=SAMPLE_TRANSPARENCIA_GRID[:1]),
        patch("etl.sources.transparencia.fetch_detalhes_obra", return_value={}),
        patch("etl.sources.transparencia.fetch_aditivos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_dotacao_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_empenhos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_pagamentos_obra", return_value=[]),
        pytest.raises(TypeError),
    ):
        run_pipeline(tmp_path, full_refresh=True, consulta_pagamentos=pagamentos_simulados)

    depois = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert depois == antes

    log = tmp_path.parent / f".{tmp_path.name}-tentativas.jsonl"
    estados = [json.loads(linha)["estado"] for linha in log.read_text(encoding="utf-8").splitlines()]
    assert estados[-2:] == ["iniciada", "falhou"]


def test_resposta_geografica_invalida_nao_substitui_publicacao(tmp_path: Path) -> None:
    indice = tmp_path / "index_2025.json"
    indice.write_text('{"versao": "anterior"}', encoding="utf-8")
    anterior = indice.read_bytes()

    with (
        patch("urllib.request.urlopen", return_value=BytesIO(b'{}')),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[]),
        pytest.raises(ValueError, match="GeoJSON"),
    ):
        run_pipeline(tmp_path)

    assert indice.read_bytes() == anterior


def test_malha_truncada_nao_substitui_publicacao(tmp_path: Path) -> None:
    indice = tmp_path / "index_2025.json"
    indice.write_text('{"versao": "anterior"}', encoding="utf-8")
    anterior = indice.read_bytes()
    resposta = b'{"type":"FeatureCollection","features":[{}],"exceededTransferLimit":true}'

    with (
        patch("urllib.request.urlopen", side_effect=lambda *args, **kwargs: BytesIO(resposta)),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[]),
        pytest.raises(ValueError, match="GeoJSON"),
    ):
        run_pipeline(tmp_path)

    assert indice.read_bytes() == anterior


def test_malha_sem_geometria_ou_nome_nao_e_publicada(tmp_path: Path) -> None:
    resposta = b'{"type":"FeatureCollection","features":[{}]}'
    with (
        patch("urllib.request.urlopen", side_effect=lambda *args, **kwargs: BytesIO(resposta)),
        pytest.raises(ValueError, match="GeoJSON"),
    ):
        run_pipeline(tmp_path)
    assert not (tmp_path / "atual.json").exists()


def test_malha_com_poligono_invalido_nao_e_publicada(tmp_path: Path) -> None:
    resposta = json.dumps({"type": "FeatureCollection", "features": [{
        "type": "Feature", "properties": {"NOME_BAIRR": "Pituba", "NOMES": "Barra/Pituba"},
        "geometry": {"type": "Polygon", "coordinates": [[[-38.4, -13.0]]]},
    }]}).encode("utf-8")
    with (
        patch("urllib.request.urlopen", side_effect=lambda *args, **kwargs: BytesIO(resposta)),
        pytest.raises(ValueError, match="GeoJSON"),
    ):
        run_pipeline(tmp_path)
    assert not (tmp_path / "atual.json").exists()


def test_falha_totalizador_preserva_arquivos_publicados(tmp_path: Path) -> None:
    indice = tmp_path / "index_2025.json"
    indice.write_text('{"versao": "anterior"}', encoding="utf-8")
    anterior = indice.read_bytes()

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia._post_transparencia", side_effect=OSError("Portal indisponível")),
        pytest.raises(OSError, match="Portal indisponível"),
    ):
        run_pipeline(tmp_path)

    assert indice.read_bytes() == anterior


def test_falha_do_censo_preserva_arquivos_publicados(tmp_path: Path) -> None:
    indice = tmp_path / "index_2025.json"
    indice.write_text('{"versao": "anterior"}', encoding="utf-8")
    anterior = indice.read_bytes()

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("urllib.request.urlopen", side_effect=OSError("SIDRA indisponível")),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[]),
        pytest.raises(OSError, match="SIDRA indisponível"),
    ):
        run_pipeline(tmp_path)

    assert indice.read_bytes() == anterior


def test_resposta_sidra_sem_populacao_nao_e_publicada(tmp_path: Path) -> None:
    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("urllib.request.urlopen", return_value=BytesIO(b'[{},{ }]')),
        pytest.raises(ValueError, match="Censo 2022"),
    ):
        run_pipeline(tmp_path)
    assert not (tmp_path / "atual.json").exists()


def test_grid_interrompido_nao_publica_resultado_parcial(tmp_path: Path) -> None:
    indice = tmp_path / "index_2025.json"
    indice.write_text('{"versao": "anterior"}', encoding="utf-8")
    anterior = indice.read_bytes()

    def resposta_portal(endpoint, payload):
        if "totalizador" in endpoint:
            return {"totalObras": 0}
        if "pagina=1" in endpoint:
            return {"dados": [{"id": n} for n in range(10)],
                    "paginacao": {"paginaAtual": 1, "totalPagina": 10, "paginas": 2, "tamanho": 10, "total": 20}}
        raise OSError("Página interrompida")

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia._post_transparencia", side_effect=resposta_portal),
        pytest.raises(OSError, match="Página interrompida"),
    ):
        run_pipeline(tmp_path)

    assert indice.read_bytes() == anterior


def test_grid_com_contagem_incompleta_nao_e_publicado(tmp_path: Path) -> None:
    def resposta_portal(endpoint, payload):
        if "totalizador" in endpoint:
            return {"totalObras": 2}
        return {"dados": [{"id": 1}], "paginacao": {"paginaAtual": 1, "totalPagina": 1, "paginas": 1, "tamanho": 10, "total": 2}}

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia._post_transparencia", side_effect=resposta_portal),
        pytest.raises(ValueError, match="incomplet"),
    ):
        run_pipeline(tmp_path)

    assert not (tmp_path / "atual.json").exists()


def test_grid_com_pagina_inconsistente_nao_e_publicado(tmp_path: Path) -> None:
    def resposta_portal(endpoint, payload):
        if "totalizador" in endpoint:
            return {"totalObras": 11}
        if "pagina=1" in endpoint:
            return {"dados": [{"id": n} for n in range(10)], "paginacao": {"paginaAtual": 1, "paginas": 2, "total": 11, "totalPagina": 10}}
        return {"dados": [{"id": 11}], "paginacao": {"paginaAtual": 1, "paginas": 2, "total": 11, "totalPagina": 1}}

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia._post_transparencia", side_effect=resposta_portal),
        pytest.raises(ValueError, match="pagina"),
    ):
        run_pipeline(tmp_path)

    assert not (tmp_path / "atual.json").exists()


def test_falha_em_detalhes_nao_publica_dados_de_exemplo(tmp_path: Path) -> None:
    indice = tmp_path / "index_2025.json"
    indice.write_text('{"versao": "anterior"}', encoding="utf-8")
    anterior = indice.read_bytes()

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=SAMPLE_TRANSPARENCIA_GRID[:1]),
        patch("etl.sources.transparencia._post_transparencia", side_effect=OSError("Detalhes indisponíveis")),
        pytest.raises(OSError, match="Detalhes indisponíveis"),
    ):
        run_pipeline(tmp_path, full_refresh=True, consulta_pagamentos=pagamentos_simulados)

    assert indice.read_bytes() == anterior


def test_falha_em_lista_relacionada_preserva_conjunto(tmp_path: Path) -> None:
    indice = tmp_path / "index_2025.json"
    indice.write_text('{"versao": "anterior"}', encoding="utf-8")
    anterior = indice.read_bytes()

    def consulta(endpoint, payload):
        if "pagina=1" in endpoint:
            return {"dados": [{"id": n} for n in range(10)], "paginacao": {"paginaAtual": 1, "totalPagina": 10, "paginas": 2, "tamanho": 10, "total": 20}}
        raise OSError("Lista interrompida")

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=SAMPLE_TRANSPARENCIA_GRID[:1]),
        patch("etl.sources.transparencia.fetch_detalhes_obra", return_value={}),
        patch("etl.sources.transparencia._post_transparencia", side_effect=consulta),
        pytest.raises(OSError, match="Lista interrompida"),
    ):
        run_pipeline(tmp_path, full_refresh=True, consulta_pagamentos=pagamentos_simulados)

    assert indice.read_bytes() == anterior


def test_publicacao_concluida_identifica_versao_e_tempos(tmp_path: Path) -> None:
    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[]),
    ):
        run_pipeline(tmp_path, year=2025, full_refresh=True, data_referencia_pagamentos="2025-12-31")

    ponteiro = json.loads((tmp_path / "atual.json").read_text(encoding="utf-8"))
    versao_dir = tmp_path / ponteiro["caminho"]
    indice = json.loads((versao_dir / "index_2025.json").read_text(encoding="utf-8"))
    metadados = indice["metadata"]["atualizacao"]
    assert metadados["dataReferenciaPagamentos"] == "2025-12-31"
    assert metadados["inicioConsultas"] <= metadados["fimConsultas"] <= metadados["concluidaEm"]
    assert metadados["consultas"] == "concluidas"
    assert metadados["validacoes"] == "aprovadas"
    assert metadados["coberturaHistorica"] == "nao_verificada"
    for nome in ("bairros.geojson", "prefeituras_bairro.geojson"):
        malha = json.loads((versao_dir / "geo" / nome).read_text(encoding="utf-8"))
        assert malha["versaoDados"] == metadados["versaoDados"]


def test_consulta_obrigatoria_incompleta_preserva_versao_e_data(tmp_path: Path) -> None:
    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[]) as grid,
    ):
        run_pipeline(tmp_path, year=2025, full_refresh=True, data_referencia_pagamentos="2025-12-31")
        antes = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
        grid.return_value = SAMPLE_TRANSPARENCIA_GRID[:1]

        def incompleta(ug, contrato, referencia):
            return ConsultaPagamentos([], referencia, concluida=False, validada=False)

        with pytest.raises(ValueError, match="Consulta obrigatória"):
            run_pipeline(tmp_path, year=2025, full_refresh=True, consulta_pagamentos=incompleta)

    depois = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert depois == antes


@pytest.mark.parametrize("fonte", ["geosalvador", "ibge_censo", "transparencia"])
def test_falha_de_fonte_preserva_versao_validada_inteira(tmp_path: Path, fonte: str) -> None:
    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS) as geo,
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}) as censo,
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}) as portal,
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[]),
    ):
        run_pipeline(tmp_path, data_referencia_pagamentos="2025-12-31")
        antes = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
        {"geosalvador": geo, "ibge_censo": censo, "transparencia": portal}[fonte].side_effect = OSError("Falha da fonte")
        with pytest.raises(OSError, match="Falha da fonte"):
            run_pipeline(tmp_path, data_referencia_pagamentos="2026-01-01")

    depois = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert depois == antes


def test_valor_de_pagamento_invalido_impede_publicacao(tmp_path: Path) -> None:
    def consulta_invalida(ug, contrato, referencia):
        return ConsultaPagamentos([{"pago": "não é número"}], referencia, True, True)

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[]) as grid,
        patch("etl.sources.transparencia.fetch_detalhes_obra", return_value={}),
        patch("etl.sources.transparencia.fetch_aditivos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_dotacao_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_empenhos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", return_value=[]),
    ):
        run_pipeline(tmp_path, data_referencia_pagamentos="2025-12-31")
        antes = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
        grid.return_value = SAMPLE_TRANSPARENCIA_GRID[:1]
        with pytest.raises(ValueError, match="pagamento inválido"):
            run_pipeline(tmp_path, full_refresh=True, consulta_pagamentos=consulta_invalida)

    depois = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert depois == antes


@pytest.fixture
def fontes_com_frente_de_medicao():
    curadoria = {"2401:001/2024": {"status": "multi_frente", "frentesMedicao": {
        "NL1": {"status": "promovido", "nivel": "Bairro", "bairro": "Pituba", "prefeituraBairro": "Barra/Pituba"}
    }}}
    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}) as totalizador,
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=SAMPLE_TRANSPARENCIA_GRID[:1]),
        patch("etl.sources.transparencia.fetch_detalhes_obra", return_value={}),
        patch("etl.sources.transparencia.fetch_aditivos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_dotacao_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_empenhos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", return_value=[{"notaLiquidacao": "NL1", "valLiqLiquidacao": 20, "pago": 10}]) as liquidacoes,
        patch("etl.domain.geocoding._carregar_curadoria_territorial", return_value=curadoria),
    ):
        yield totalizador, liquidacoes


def test_reusa_referencia_validada_mas_reconsulta_pagamentos(tmp_path: Path, fontes_com_frente_de_medicao) -> None:
    valores = iter([10, 5])

    def fonte(ug, contrato, referencia):
        return ConsultaPagamentos([{"notaLiquidacao": "NL1", "valorPago": next(valores)}], referencia, True, True, ["Histórico anterior indisponível na fonte"])

    anterior = run_pipeline(tmp_path, consulta_pagamentos=fonte, data_referencia_pagamentos="2025-12-30")
    nova = run_pipeline(tmp_path, consulta_pagamentos=fonte, data_referencia_pagamentos="2025-12-31")

    assert nova["detail_cache_hits"] == 1
    antes = json.loads((Path(anterior["versao_dir"]) / "obras/1001.json").read_text(encoding="utf-8"))
    depois = json.loads((Path(nova["versao_dir"]) / "obras/1001.json").read_text(encoding="utf-8"))
    indice = json.loads((Path(nova["versao_dir"]) / "index_2025.json").read_text(encoding="utf-8"))
    assert antes["funilFinanceiro"]["valorPago"] == 10
    assert depois["funilFinanceiro"]["valorPago"] == 5
    assert depois["frentesMedicao"][0]["valorPago"] == 5
    assert indice["obras"][0]["valorPago"] == 5
    assert depois["versaoDados"] == indice["metadata"]["atualizacao"]["versaoDados"]
    assert indice["metadata"]["atualizacao"]["limitacoesConhecidas"] == ["Histórico anterior indisponível na fonte"]


def test_atualizacoes_sucessivas_publicam_somente_pagamentos_atuais(tmp_path: Path, fontes_com_frente_de_medicao) -> None:
    consultas = [
        ([{"notaLiquidacao": "NL1", "pago": 100}, {"notaLiquidacao": "NL1", "pago": 50}], 150, "saldo_registrado"),
        ([{"notaLiquidacao": "NL1", "pago": 40}], 40, "saldo_registrado"),
        ([{"notaLiquidacao": "NL1", "pago": 40}, {"notaLiquidacao": "NL1", "pago": -40}], 0, "saldo_registrado"),
        ([], 0, "sem_registros"),
        ([{"notaLiquidacao": "NL1"}], None, "indisponivel"),
    ]
    atual = []

    def fonte(ug, contrato, referencia):
        return ConsultaPagamentos(deepcopy(atual), referencia, True, True, ["Histórico anterior indisponível na fonte"])

    totalizador, liquidacoes = fontes_com_frente_de_medicao
    totalizador.return_value = {"totalObras": 20, "valorTotal": 999999999, "totalPago": 999}
    liquidacoes.return_value = [{"notaLiquidacao": "NL1", "valLiqLiquidacao": 200, "pago": 150}]

    for dia, (registros, esperado, situacao) in enumerate(consultas, 1):
        atual[:] = registros
        resultado = run_pipeline(tmp_path, consulta_pagamentos=fonte, data_referencia_pagamentos=f"2025-12-{dia:02}")
        versao = Path(resultado["versao_dir"])
        ficha = json.loads((versao / "obras/1001.json").read_text(encoding="utf-8"))
        indice = json.loads((versao / "index_2025.json").read_text(encoding="utf-8"))
        assert ficha["pagamentos"] == registros
        assert ficha["funilFinanceiro"]["valorPago"] == esperado
        assert ficha["apuracaoPagamentos"]["situacao"] == situacao
        assert ficha["frentesMedicao"][0]["valorPago"] == esperado
        assert indice["obras"][0]["valorPago"] == esperado
        assert indice["kpis_globais"]["totalPago"] == (esperado or 0)
        pituba = next(b for b in indice["bairros"] if b["nome"] == "Pituba")
        assert pituba["valorPago"] == esperado
        assert indice["metadata"]["atualizacao"]["limitacoesConhecidas"] == ["Histórico anterior indisponível na fonte"]

    antes = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    atual[:] = [{"pago": "inválido"}]
    with pytest.raises(ValueError, match="pagamento inválido"):
        run_pipeline(tmp_path, consulta_pagamentos=fonte, data_referencia_pagamentos="2025-12-06")
    assert {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == antes


def test_falha_na_ativacao_preserva_versoes_e_ponteiro(tmp_path: Path) -> None:
    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[]),
    ):
        run_pipeline(tmp_path, data_referencia_pagamentos="2025-12-31")
        antes = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
        substituir = os.replace

        def falhar_ponteiro(origem, destino):
            if Path(destino).name == "atual.json":
                raise OSError("Falha na ativação")
            substituir(origem, destino)

        with patch("os.replace", side_effect=falhar_ponteiro), pytest.raises(OSError, match="Falha na ativação"):
            run_pipeline(tmp_path, data_referencia_pagamentos="2025-12-31")

    depois = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert depois == antes



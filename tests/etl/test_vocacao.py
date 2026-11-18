"""Testes unitários para a classificação híbrida de Vocação da Obra Pública.

Valida a categorização nas 3 vocações canônicas de Salvador:
- Vizinhança e Comunidade
- Mobilidade Estrutural e Orlas
- Equipamentos e Marcos da Cidade
"""

import json
from pathlib import Path
from unittest.mock import patch

from etl.domain.vocacao import VOCACOES_CANONICAS, classificar_vocacao
from tests.etl.fixtures.sample_data import (
    SAMPLE_GEOSALVADOR_BAIRROS,
    SAMPLE_GEOSALVADOR_PREFEITURAS,
    SAMPLE_IBGE_CENSO_2022,
    SAMPLE_TRANSPARENCIA_GRID,
    SAMPLE_TRANSPARENCIA_TOTALIZADOR,
)


def test_lista_de_vocacoes_canonicas_contem_tres_categorias():
    """Garante que VOCACOES_CANONICAS possui exatamente as 3 categorias especificadas."""
    assert VOCACOES_CANONICAS == [
        "Vizinhança e Comunidade",
        "Mobilidade Estrutural e Orlas",
        "Equipamentos e Marcos da Cidade",
    ]


def test_curadoria_explicita_tem_precedencia_sobre_regras_heuristicas():
    """Curadoria explícita por Chave Canônica (cdUnidadeGestora:nuContratoSigef) vence regras de texto."""
    obra = {
        "cdUnidadeGestora": "616002",
        "nuContratoSigef": "2023CT005109",
        "sgOrgao": "SEINFRA",
        "dsObjeto": "Construção da Praça abaixo do Viaduto Juscelino Kubitschek",
    }
    curadoria = {
        "616002:2023CT005109": {
            "vocacao": "Vizinhança e Comunidade",
            "justificativa": "Praça de convivência local sob o viaduto.",
        }
    }
    assert classificar_vocacao(obra, curadoria=curadoria) == "Vizinhança e Comunidade"


def test_classificacao_mobilidade_estrutural_e_orlas():
    """Valida obras de viadutos, túneis, BRT, grandes eixos viários e requalificação de orlas."""
    assert (
        classificar_vocacao(
            {
                "sgOrgao": "SEINFRA",
                "dsObjeto": "Execução das obras de construção do Sistema Viário do BRT Trecho 2",
            }
        )
        == "Mobilidade Estrutural e Orlas"
    )
    assert (
        classificar_vocacao(
            {
                "sgOrgao": "SEINFRA",
                "dsObjeto": "IMPLANTAÇÃO DA INTERVENÇÃO 'C' - VIADUTO DIRECIONAL SENTIDO ACESSO NORTE",
            }
        )
        == "Mobilidade Estrutural e Orlas"
    )
    assert (
        classificar_vocacao(
            {
                "sgOrgao": "SEINFRA",
                "dsObjeto": "OBRAS DE REQUALIFICAÇÃO URBANA E AMBIENTAL DA ORLA DE PITUAÇU FASE 01 E 02",
            }
        )
        == "Mobilidade Estrutural e Orlas"
    )
    assert (
        classificar_vocacao(
            {
                "sgOrgao": "SEINFRA",
                "dsObjeto": "EXECUÇÃO DOS SERVIÇOS RECUPERAÇÃO ESTRUTURAL VIADUTOS DO TÚNEL AMÉRICO SIMAS",
            }
        )
        == "Mobilidade Estrutural e Orlas"
    )


def test_classificacao_equipamentos_e_marcos_da_cidade():
    """Valida hospitais municipais, arenas multiuso, mercados históricos, teatros, museus e marcos."""
    assert (
        classificar_vocacao(
            {
                "sgOrgao": "SMS",
                "dsObjeto": "Execução das obras de reforma e ampliação para implantação do Hospital Municipal da Criança",
            }
        )
        == "Equipamentos e Marcos da Cidade"
    )
    assert (
        classificar_vocacao(
            {
                "sgOrgao": "SEINFRA",
                "dsObjeto": "OBRAS DE CONSTRUÇÃO DO COMPLEXO MULTIUSO ARENA SALVADOR",
            }
        )
        == "Equipamentos e Marcos da Cidade"
    )
    assert (
        classificar_vocacao(
            {
                "sgOrgao": "SEINFRA",
                "dsObjeto": "OBRAS DE RESTAURAÇÃO E AMPLIAÇÃO DO MUSEU DA SANTA CASA DA MISERICÓRDIA - CENTRO",
            }
        )
        == "Equipamentos e Marcos da Cidade"
    )
    assert (
        classificar_vocacao(
            {
                "sgOrgao": "SEINFRA",
                "dsObjeto": "Execução das obras de Restauração e Requalificação do Elevador Lacerda",
            }
        )
        == "Equipamentos e Marcos da Cidade"
    )


def test_fallback_conservador_para_vizinhanca_e_comunidade():
    """Escolas, USFs, encostas, praças, pavimentação local e casos genéricos caem em Vizinhança e Comunidade."""
    assert (
        classificar_vocacao(
            {
                "sgOrgao": "SMED",
                "dsObjeto": "REFORMA DAS UNIDADES ESCOLARES NO MUNICÍPIO DE SALVADOR - LOTE 01 - GRE ORLA",
            }
        )
        == "Vizinhança e Comunidade"
    )
    assert (
        classificar_vocacao(
            {
                "sgOrgao": "CODESAL",
                "dsObjeto": "Execução de contenção de encosta com geomanta na Liberdade",
            }
        )
        == "Vizinhança e Comunidade"
    )
    assert (
        classificar_vocacao(
            {
                "sgOrgao": "SMS",
                "dsObjeto": "Reforma e ampliação da USF Fazenda Coutos II",
            }
        )
        == "Vizinhança e Comunidade"
    )
    assert (
        classificar_vocacao(
            {
                "sgOrgao": "SEINFRA",
                "dsObjeto": "Serviços de Requalificação de Vias urbanas em diversos logradouros da Cidade",
            }
        )
        == "Vizinhança e Comunidade"
    )


def test_pipeline_emite_vocacao_no_index_e_na_ficha_limpa(tmp_path: Path, portal_simulado) -> None:
    """Garante que o pipeline ETL propaga `vocacao` no index_2025.json e em obras/<id>.json."""
    from etl.runner import run_pipeline

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value=SAMPLE_IBGE_CENSO_2022),
        patch("etl.sources.transparencia.fetch_totalizador", return_value=SAMPLE_TRANSPARENCIA_TOTALIZADOR),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=SAMPLE_TRANSPARENCIA_GRID),
    ):
        result = run_pipeline(output_dir=tmp_path, year=2025)

    assert result["success"] is True
    tmp_path = Path(result["versao_dir"])

    with open(tmp_path / "index_2025.json", "r", encoding="utf-8") as f:
        index_data = json.load(f)

    obras_por_id = {o["id"]: o for o in index_data["obras"]}
    assert obras_por_id[1001]["vocacao"] == "Mobilidade Estrutural e Orlas"
    assert all(o.get("vocacao") in VOCACOES_CANONICAS for o in index_data["obras"])

    with open(tmp_path / "obras" / "1001.json", "r", encoding="utf-8") as f:
        ficha_1001 = json.load(f)

    assert ficha_1001["vocacao"] == "Mobilidade Estrutural e Orlas"

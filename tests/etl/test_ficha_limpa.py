"""Testes da Seam 1: Geração dos artefatos estáticos da Ficha Limpa da Obra sob demanda e concentração de empreiteiras."""

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


def test_indice_nao_transforma_execucao_fisica_em_pagamento(tmp_path: Path) -> None:
    """A ausência de registros de pagamento não autoriza estimar um pagamento."""
    from etl.domain.ficha_limpa import sincronizar_obra_com_ficha
    from etl.domain.kpis import calcular_kpis_globais
    from etl.generator import generate_index_json

    obra = {
        "id": "brt", "cdUnidadeGestora": "616002", "nuContratoSigef": "2018CT001246",
        "valorContratualVigente": 268942700.51, "percentualExecutado": 97.55,
    }
    ficha = {"funilFinanceiro": {"valorPago": 0}, "pagamentos": []}
    sincronizar_obra_com_ficha(obra, ficha)
    caminho = tmp_path / "index.json"
    generate_index_json({}, [], [], [obra], 2025, caminho)
    indice = json.loads(caminho.read_text(encoding="utf-8"))
    assert indice["obras"][0]["valorPago"] is None
    assert calcular_kpis_globais({}, [obra], 100)["obrasSemValorPago"] == 1


def test_ficha_nao_reaproveita_estimativa_antiga_como_pagamento() -> None:
    from etl.domain.ficha_limpa import construir_ficha_obra, sincronizar_obra_com_ficha

    obra = {"id": "brt", "vlAtualizado": 1000, "percentualExecutado": 50, "vlPago": 500}
    ficha = construir_ficha_obra(obra, {}, [], [], [], [], [])
    sincronizar_obra_com_ficha(obra, ficha)
    assert ficha["funilFinanceiro"]["valorPago"] is None
    assert obra["valorPago"] is None


def test_pipeline_generates_individual_obras_json_with_ficha_limpa(tmp_path: Path) -> None:
    """Valida a geração dos arquivos estáticos individuais em `obras/<id>.json` e o resumo de empreiteiras.

    Sumário:
        Executa o pipeline ETL e verifica se cada obra possui um JSON sob demanda com
        Funil Financeiro, Aditivos Contratuais, Dotação/Fonte de Recurso, edição do DOM,
        CNPJ da construtora e resumo de concentração de empreiteiras em Salvador.
    """
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

    # 1. Diretório obras/ com arquivos individuais
    obras_dir = tmp_path / "obras"
    assert obras_dir.exists() and obras_dir.is_dir(), "O diretório obras/ deve ser criado pelo pipeline."

    # Verifica se cada obra do grid gerou seu arquivo individual obras/<id>.json
    for item in SAMPLE_TRANSPARENCIA_GRID:
        obra_id = item["id"]
        obra_file = obras_dir / f"{obra_id}.json"
        assert obra_file.exists(), f"O artefato individual {obra_id}.json deve existir em obras/."

    # 2. Inspeciona a Ficha Limpa da Obra 1001 (SUCOP - Orla da Pituba)
    file_1001 = obras_dir / "1001.json"
    with open(file_1001, "r", encoding="utf-8") as f:
        data_1001 = json.load(f)

    assert data_1001["id"] == 1001
    assert data_1001["unidadeGestora"] == "SUCOP"
    assert data_1001["numeroContrato"] == "001/2024"
    assert "Requalificação da Orla da Pituba" in data_1001["objeto"]

    # Empreiteira e CNPJ
    assert "empreiteira" in data_1001
    emp_1001 = data_1001["empreiteira"]
    assert emp_1001["razaoSocial"] == "CONSTRUTORA SALVADOR LTDA"
    assert "cnpj" in emp_1001 and len(emp_1001["cnpj"]) >= 14
    assert "totalObras" in emp_1001
    assert "valorTotalContratado" in emp_1001

    # DOM (Diário Oficial do Município)
    assert "dom" in data_1001
    assert "nuDom" in data_1001["dom"]

    # Funil de Execução Financeira completo
    assert "funilFinanceiro" in data_1001
    funil = data_1001["funilFinanceiro"]
    assert "valorOriginal" in funil
    assert "valorContratualVigente" in funil
    assert "valorEmpenhado" in funil
    assert "valorLiquidado" in funil
    assert "valorPago" in funil
    assert "percentualExecutado" in funil
    assert funil["percentualExecutado"] == 65.5

    # Aditivos Contratuais
    assert "aditivos" in data_1001
    assert isinstance(data_1001["aditivos"], list)

    # Dotação orçamentária / Fonte de recurso
    assert "dotacao" in data_1001
    assert isinstance(data_1001["dotacao"], list)
    assert len(data_1001["dotacao"]) >= 1
    assert "fonteRecurso" in data_1001["dotacao"][0]

    # Inspeciona a Obra 1002 (com aditivo de valor e prorrogação de prazo)
    file_1002 = obras_dir / "1002.json"
    with open(file_1002, "r", encoding="utf-8") as f:
        data_1002 = json.load(f)

    assert len(data_1002["aditivos"]) >= 1
    adit_1 = data_1002["aditivos"][0]
    assert "nuAditivo" in adit_1 or "numero" in adit_1
    assert "tipoAlteracao" in adit_1 or "dsTipoAlteracao" in adit_1
    assert "nuDom" in adit_1

    # 3. Consolidação de Concentração de Empreiteiras no index_2025.json
    index_file = tmp_path / "index_2025.json"
    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    assert "concentracao_empreiteiras" in index_data
    conc = index_data["concentracao_empreiteiras"]
    assert len(conc) >= 1
    # Cada obra compacta no index também deve ter referência ao CNPJ da empreiteira
    for o in index_data["obras"]:
        assert "cnpj" in o or "cnpjCredor" in o


def test_pipeline_generates_fontes_oficiais_and_lastro_territorial(tmp_path: Path) -> None:
    """Valida a geração do bloco estruturado `fontesOficiais` com e sem `nuDom`/`nuProcesso`."""
    from etl.runner import run_pipeline

    grid_com_sem_dom = list(SAMPLE_TRANSPARENCIA_GRID) + [
        {
            "id": 1099,
            "cdUnidadeGestora": 616002,
            "dsUnidadeGestora": "SECRETARIA MUNICIPAL DE INFRAESTRUTURA E OBRAS PUBLICAS",
            "sgOrgao": "SEINFRA",
            "nuContratoSigef": "2020CT005461",
            "nuContratoOriginal": "2020CT005461",
            "nuProcesso": None,
            "dsObjeto": "Manutenção viária sem localização específica",
            "vlOriginal": 1000000.00,
            "vlAtualizado": 1000000.00,
            "dtInicioVigencia": "2024-01-10T00:00:00.000Z",
            "dtFimVigenciaOriginal": "2025-12-31T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2025-12-31T00:00:00.000Z",
            "dtAssinatura": "2024-01-05T00:00:00.000Z",
            "percentualExecutado": 50.0,
            "dsSituacao": "Em Execução",
            "nmCredor": "EG CONSTRUCOES LTDA",
            "nuDocumentoCredor": "15.198.195/0001-01",
            "nuDom": None,
        }
    ]

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value=SAMPLE_IBGE_CENSO_2022),
        patch("etl.sources.transparencia.fetch_totalizador", return_value=SAMPLE_TRANSPARENCIA_TOTALIZADOR),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=grid_com_sem_dom),
    ):
        result = run_pipeline(output_dir=tmp_path, year=2025)

    assert result["success"] is True

    # Obra 1001: com nuDom e nuProcesso
    with open(tmp_path / "obras" / "1001.json", "r", encoding="utf-8") as f:
        ficha_1001 = json.load(f)

    fontes_1001 = ficha_1001["fontesOficiais"]
    assert fontes_1001["portalTransparencia"]["url"] == "https://www.transparencia.salvador.ba.gov.br/"
    assert fontes_1001["chaveCanonica"] == {
        "cdUnidadeGestora": "2401",
        "unidadeGestora": "SUCOP",
        "nuContratoSigef": "001/2024",
    }
    assert fontes_1001["nuProcesso"] == "1234/2023"
    assert fontes_1001["domContrato"] == {
        "nuDom": "8.750",
        "url": "https://dom.salvador.ba.gov.br/",
    }
    assert isinstance(fontes_1001["domAditivos"], list)
    lastro_1001 = fontes_1001["lastroTerritorial"]
    assert lastro_1001["nivel"] == ficha_1001["nivel"]
    assert lastro_1001["estagioAlocacao"] == ficha_1001["estagioAlocacao"]
    assert lastro_1001["origem"]

    # Obra 1002: com aditivos e nuDom nos aditivos
    with open(tmp_path / "obras" / "1002.json", "r", encoding="utf-8") as f:
        ficha_1002 = json.load(f)

    dom_aditivos_1002 = ficha_1002["fontesOficiais"]["domAditivos"]
    assert len(dom_aditivos_1002) >= 1
    assert dom_aditivos_1002[0]["nuDom"]
    assert dom_aditivos_1002[0]["url"] == "https://dom.salvador.ba.gov.br/"

    # Obra 1099: sem nuDom e sem nuProcesso (degradação limpa)
    with open(tmp_path / "obras" / "1099.json", "r", encoding="utf-8") as f:
        ficha_1099 = json.load(f)

    fontes_1099 = ficha_1099["fontesOficiais"]
    assert fontes_1099["portalTransparencia"]["url"] == "https://www.transparencia.salvador.ba.gov.br/"
    assert fontes_1099["chaveCanonica"] == {
        "cdUnidadeGestora": "616002",
        "unidadeGestora": "SEINFRA",
        "nuContratoSigef": "2020CT005461",
    }
    assert fontes_1099["nuProcesso"] is None
    assert fontes_1099["domContrato"] == {"nuDom": None, "url": None}
    assert fontes_1099["domAditivos"] == []
    assert fontes_1099["lastroTerritorial"]["nivel"] == "Escopo Cidade (Não-Localizado)"
    assert fontes_1099["lastroTerritorial"]["origem"]


def test_pipeline_propagates_curadoria_lastro_to_ficha_limpa(tmp_path: Path) -> None:
    """Valida que o lastro documental da Curadoria Territorial é gravado em `fontesOficiais.lastroTerritorial`."""
    from etl.runner import run_pipeline

    obra_curada = {
        "id": 9100,
        "cdUnidadeGestora": 301110,
        "dsUnidadeGestora": "SECRETARIA MUNICIPAL DA SAUDE",
        "sgOrgao": "SMS",
        "nuContratoSigef": "2025CT005813",
        "nuContratoOriginal": "387/2025",
        "nuProcesso": "9999/2025",
        "dsObjeto": "Lançamento do Contrato Nº 387/2025",
        "vlOriginal": 500000.00,
        "vlAtualizado": 500000.00,
        "dtInicioVigencia": "2025-01-10T00:00:00.000Z",
        "dtFimVigenciaOriginal": "2025-12-31T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2025-12-31T00:00:00.000Z",
        "dtAssinatura": "2025-01-05T00:00:00.000Z",
        "percentualExecutado": 25.0,
        "dsSituacao": "Em Execução",
        "nmCredor": "CONSTRUTORA TESTE LTDA",
        "nuDocumentoCredor": "15.198.195/0001-01",
        "nuDom": None,
    }

    curadoria_mock = {
        "301110:2025CT005813": {
            "cdUnidadeGestora": "301110",
            "nuContratoSigef": "2025CT005813",
            "status": "promovido",
            "nivel": "Bairro",
            "bairro": "Pituba",
            "prefeituraBairro": "Barra/Pituba",
            "trechoComprobatorio": "REFORMA DA USF PITUBA II.",
            "documentoOrigem": "dsObjetoAditivo (Aditivo Contratual)",
            "justificativa": "Aditivo contratual identifica univocamente o bairro Pituba.",
        }
    }

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value=SAMPLE_IBGE_CENSO_2022),
        patch("etl.sources.transparencia.fetch_totalizador", return_value=SAMPLE_TRANSPARENCIA_TOTALIZADOR),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[obra_curada]),
        patch("etl.domain.geocoding._carregar_curadoria_territorial", return_value=curadoria_mock),
    ):
        result = run_pipeline(output_dir=tmp_path, year=2025)

    assert result["success"] is True

    with open(tmp_path / "obras" / "9100.json", "r", encoding="utf-8") as f:
        ficha = json.load(f)

    assert ficha["nivel"] == "Bairro"
    assert ficha["bairro"] == "Pituba"
    lastro = ficha["fontesOficiais"]["lastroTerritorial"]
    assert lastro["trechoComprobatorio"] == "REFORMA DA USF PITUBA II."
    assert lastro["documentoOrigem"] == "dsObjetoAditivo (Aditivo Contratual)"
    assert lastro["justificativa"] == "Aditivo contratual identifica univocamente o bairro Pituba."

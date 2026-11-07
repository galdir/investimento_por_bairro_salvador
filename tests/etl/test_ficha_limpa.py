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

"""Executa o primeiro runner e termina abruptamente no segundo contrato."""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from etl.runner import run_pipeline
from tests.etl.fixtures.sample_data import (
    SAMPLE_GEOSALVADOR_BAIRROS, SAMPLE_GEOSALVADOR_PREFEITURAS, SAMPLE_TRANSPARENCIA_GRID,
)


class Relogio(datetime):
    @classmethod
    def now(cls, tz=None):
        instante = datetime(2026, 1, 5, 12, tzinfo=timezone.utc)
        return instante.astimezone(tz) if tz else instante.replace(tzinfo=None)


def portal(endpoint, payload, **kwargs):
    contrato = payload["filtros"][1]["valor"]
    if contrato == "002/2024" and "downloadDados" in endpoint:
        os._exit(23)
    registros = [{"pago": "R$ 1,00", "dataPagamento": "01/01/2020"},
                 {"pago": "R$ 2,00", "dataPagamento": "06/01/2026"}]
    if "downloadDados" in endpoint:
        return registros
    return {"dados": registros, "paginacao": {"paginaAtual": 1, "totalPagina": 2,
            "paginas": 1, "tamanho": 10, "total": 2}, "totalizadores": {"Valor Pago": "R$ 3,00"}}


if __name__ == "__main__":
    repositorio = Path(sys.argv[1])
    primeiro = SAMPLE_TRANSPARENCIA_GRID[0]
    segundo = {**primeiro, "id": 1002, "nuContratoSigef": "002/2024"}
    with (
        patch("etl.runner.datetime", Relogio),
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[primeiro, segundo]),
        patch("etl.sources.transparencia.fetch_detalhes_obra", return_value={}),
        patch("etl.sources.transparencia.fetch_aditivos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_dotacao_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_empenhos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", return_value=[]),
        patch("etl.sources.transparencia._post_transparencia", side_effect=portal),
    ):
        run_pipeline(repositorio / "data", full_refresh=True, data_referencia_pagamentos="2026-01-05",
                     repositorio_progresso=repositorio)

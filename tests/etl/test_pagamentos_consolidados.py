from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from etl.consultas import ConsultaPagamentos
from etl.reference.sample_data import (
    SAMPLE_GEOSALVADOR_BAIRROS,
    SAMPLE_GEOSALVADOR_PREFEITURAS,
    SAMPLE_TRANSPARENCIA_GRID,
)
from etl.runner import run_pipeline


@pytest.fixture(autouse=True)
def fontes_basicas():
    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={"totalObras": 1, "valorTotal": 1000000, "totalPago": 500000}),
        patch("etl.sources.transparencia.fetch_detalhes_obra", return_value={}),
        patch("etl.sources.transparencia.fetch_aditivos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_dotacao_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_empenhos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", return_value=[]),
    ):
        yield


def test_contrato_consolidado_pula_consulta_e_preserva_dados_com_indicador(tmp_path: Path) -> None:
    obra_antiga = {
        **SAMPLE_TRANSPARENCIA_GRID[0],
        "id": 1001,
        "dtInicioVigencia": "2023-01-01T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2024-12-30T00:00:00.000Z",
    }
    chamadas: list[tuple[str, str, str]] = []

    def fonte(ug, contrato, referencia):
        chamadas.append((str(ug), str(contrato), str(referencia)))
        return ConsultaPagamentos(
            registros=[{"notaLiquidacao": "NL1", "pago": "R$ 125.000,00"}],
            data_referencia=referencia,
            concluida=True,
            validada=True,
            limitacoes_conhecidas=["Histórico anterior indisponível na fonte"],
            janela={"dataInicio": "2023-01-01T03:00:00.000Z", "dataFim": "2024-12-30T03:00:00.000Z"},
            periodo_disponivel={"inicio": "2023-01-01", "fim": "2025-12-01"},
        )

    with patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[obra_antiga]):
        r1 = run_pipeline(tmp_path, consulta_pagamentos=fonte, data_referencia_pagamentos="2025-12-01")
        assert len(chamadas) == 1

    ficha_r1 = json.loads((Path(r1["versao_dir"]) / "obras/1001.json").read_text(encoding="utf-8"))
    assert ficha_r1["apuracaoPagamentos"]["pagamentosConsolidados"] is False

    chamadas.clear()
    # 2025-12-31: 366 dias após 2024-12-30, 30 dias após 2025-12-01 (< 180)
    with patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[obra_antiga]):
        r2 = run_pipeline(tmp_path, consulta_pagamentos=fonte, data_referencia_pagamentos="2025-12-31")

    assert chamadas == []
    versao2 = Path(r2["versao_dir"])
    ficha_r2 = json.loads((versao2 / "obras/1001.json").read_text(encoding="utf-8"))
    indice_r2 = json.loads((versao2 / "index_2025.json").read_text(encoding="utf-8"))

    assert ficha_r2["apuracaoPagamentos"]["pagamentosConsolidados"] is True
    assert ficha_r2["apuracaoPagamentos"]["dataReferencia"] == "2025-12-01"
    assert ficha_r2["apuracaoPagamentos"]["limitacoesConhecidas"] == ["Histórico anterior indisponível na fonte"]
    assert ficha_r2["apuracaoPagamentos"]["periodoDisponivel"] == {"inicio": "2023-01-01", "fim": "2025-12-01"}
    assert ficha_r2["janelaPagamentos"] == {"dataInicio": "2023-01-01T03:00:00.000Z", "dataFim": "2024-12-30T03:00:00.000Z"}
    assert ficha_r2["funilFinanceiro"]["valorPago"] == 125000.0

    obra_idx = indice_r2["obras"][0]
    assert obra_idx["apuracaoPagamentos"] == ficha_r2["apuracaoPagamentos"]
    assert obra_idx["janelaPagamentos"] == ficha_r2["janelaPagamentos"]
    assert indice_r2["metadata"]["atualizacao"]["dataReferenciaPagamentos"] == "2025-12-31"
    assert indice_r2["metadata"]["atualizacao"]["limitacoesConhecidas"] == ["Histórico anterior indisponível na fonte"]


@pytest.mark.parametrize(
    ("dt_termino", "ref_r1", "ref_r2", "deve_consolidar"),
    [
        ("2024-12-31T00:00:00.000Z", "2025-12-01", "2025-12-31", False),  # exatos 365 dias -> não congela
        ("2024-12-30T00:00:00.000Z", "2025-12-01", "2025-12-31", True),   # 366 dias -> congela
        ("2024-01-01T00:00:00.000Z", "2025-07-05", "2025-12-31", True),   # 179 dias desde r1 -> congela
        ("2024-01-01T00:00:00.000Z", "2025-07-04", "2025-12-31", False),  # 180 dias desde r1 -> descongela
        ("2024-01-01T00:00:00.000Z", "2026-01-05", "2026-01-04", False),  # dias < 0 (retroativa) -> não congela
        (None, "2025-12-01", "2025-12-31", False),                        # dtTerminoVigenciaAtualizado ausente -> não congela
        ("2024-02-31", "2025-12-01", "2025-12-31", False),                # data calendário inválida -> não congela
    ],
)
def test_fronteiras_exatas_de_data_e_vigencia_na_consolidacao(
    tmp_path: Path,
    dt_termino: str | None,
    ref_r1: str,
    ref_r2: str,
    deve_consolidar: bool,
) -> None:
    obra = {
        **SAMPLE_TRANSPARENCIA_GRID[0],
        "id": 1001,
        "dtInicioVigencia": "2020-01-01T00:00:00.000Z",
        "dtFimVigenciaOriginal": "2021-01-01T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": dt_termino,
    }
    chamadas: list[str] = []

    def fonte(ug, contrato, referencia):
        chamadas.append(referencia)
        return ConsultaPagamentos(
            registros=[{"pago": "R$ 500,00"}],
            data_referencia=referencia,
            concluida=True,
            validada=True,
            limitacoes_conhecidas=[],
        )

    with patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[obra]):
        run_pipeline(tmp_path, consulta_pagamentos=fonte, data_referencia_pagamentos=ref_r1)
        assert len(chamadas) == 1
        chamadas.clear()

        r2 = run_pipeline(tmp_path, consulta_pagamentos=fonte, data_referencia_pagamentos=ref_r2)

    ficha = json.loads((Path(r2["versao_dir"]) / "obras/1001.json").read_text(encoding="utf-8"))
    indice = json.loads((Path(r2["versao_dir"]) / "index_2025.json").read_text(encoding="utf-8"))

    if deve_consolidar:
        assert chamadas == []
        assert ficha["apuracaoPagamentos"]["pagamentosConsolidados"] is True
        assert ficha["apuracaoPagamentos"]["dataReferencia"] == ref_r1
    else:
        assert chamadas == [ref_r2]
        assert ficha["apuracaoPagamentos"]["pagamentosConsolidados"] is False
        assert ficha["apuracaoPagamentos"]["dataReferencia"] == ref_r2
    assert indice["obras"][0]["apuracaoPagamentos"] == ficha["apuracaoPagamentos"]


@pytest.mark.parametrize(
    ("campo", "novo_valor"),
    [
        ("vlAtualizado", 9999999.0),
        ("percentualExecutado", 88.5),
        ("dsSituacao", "Paralisada"),
        ("dtTerminoVigenciaAtualizado", "2024-11-30T00:00:00.000Z"),
    ],
)
def test_descongela_quando_campo_monitorado_altera_e_sobrescreve_flag(
    tmp_path: Path,
    campo: str,
    novo_valor,
) -> None:
    obra_base = {
        **SAMPLE_TRANSPARENCIA_GRID[0],
        "id": 1001,
        "dtInicioVigencia": "2025-01-01T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2025-01-02T00:00:00.000Z",
    }
    chamadas: list[str] = []

    def fonte(ug, contrato, referencia):
        chamadas.append(referencia)
        return ConsultaPagamentos(
            registros=[{"pago": "R$ 100,00"}],
            data_referencia=referencia,
            concluida=True,
            validada=True,
            limitacoes_conhecidas=[],
        )

    with patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[obra_base]):
        run_pipeline(tmp_path, year=2026, consulta_pagamentos=fonte, data_referencia_pagamentos="2026-01-03")
        r2 = run_pipeline(tmp_path, year=2026, consulta_pagamentos=fonte, data_referencia_pagamentos="2026-01-10")
        assert json.loads((Path(r2["versao_dir"]) / "obras/1001.json").read_text(encoding="utf-8"))["apuracaoPagamentos"]["pagamentosConsolidados"] is True

    chamadas.clear()
    obra_alterada = {**obra_base, campo: novo_valor}
    with patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[obra_alterada]):
        r3 = run_pipeline(tmp_path, year=2026, consulta_pagamentos=fonte, data_referencia_pagamentos="2026-01-17")

    assert chamadas == ["2026-01-17"]
    ficha_r3 = json.loads((Path(r3["versao_dir"]) / "obras/1001.json").read_text(encoding="utf-8"))
    indice_r3 = json.loads((Path(r3["versao_dir"]) / "index_2025.json").read_text(encoding="utf-8"))
    assert ficha_r3["apuracaoPagamentos"]["pagamentosConsolidados"] is False
    assert ficha_r3["apuracaoPagamentos"]["dataReferencia"] == "2026-01-17"
    assert indice_r3["obras"][0]["apuracaoPagamentos"] == ficha_r3["apuracaoPagamentos"]


def test_full_refresh_descongela_e_reconsulta_contrato_consolidado(tmp_path: Path) -> None:
    obra = {
        **SAMPLE_TRANSPARENCIA_GRID[0],
        "id": 1001,
        "dtInicioVigencia": "2022-01-01T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2024-12-01T00:00:00.000Z",
    }
    chamadas: list[str] = []

    def fonte(ug, contrato, referencia):
        chamadas.append(referencia)
        return ConsultaPagamentos(
            registros=[{"pago": "R$ 200,00"}],
            data_referencia=referencia,
            concluida=True,
            validada=True,
            limitacoes_conhecidas=[],
        )

    with patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[obra]):
        run_pipeline(tmp_path, consulta_pagamentos=fonte, data_referencia_pagamentos="2025-12-10")
        run_pipeline(tmp_path, consulta_pagamentos=fonte, data_referencia_pagamentos="2025-12-20")
        chamadas.clear()
        r3 = run_pipeline(tmp_path, full_refresh=True, consulta_pagamentos=fonte, data_referencia_pagamentos="2025-12-31")

    assert chamadas == ["2025-12-31"]
    ficha_r3 = json.loads((Path(r3["versao_dir"]) / "obras/1001.json").read_text(encoding="utf-8"))
    assert ficha_r3["apuracaoPagamentos"]["pagamentosConsolidados"] is False
    assert ficha_r3["apuracaoPagamentos"]["dataReferencia"] == "2025-12-31"


@pytest.mark.parametrize("cenario", ["sem_registros", "indisponivel"])
def test_consolidacao_preserva_sem_registros_e_indisponivel_com_limitacoes(tmp_path: Path, cenario: str) -> None:
    obra = {
        **SAMPLE_TRANSPARENCIA_GRID[0],
        "id": 1001,
        "dtInicioVigencia": "2022-01-01T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2024-12-01T00:00:00.000Z",
    }
    registros = [] if cenario == "sem_registros" else [{"notaLiquidacao": "NL1"}]
    chamadas: list[str] = []

    def fonte(ug, contrato, referencia):
        chamadas.append(referencia)
        return ConsultaPagamentos(
            registros=registros,
            data_referencia=referencia,
            concluida=True,
            validada=True,
            limitacoes_conhecidas=["Histórico anterior a 2020 indisponível"],
            periodo_disponivel={"inicio": "2020-01-01", "fim": "2025-12-10"},
        )

    with patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[obra]):
        run_pipeline(tmp_path, consulta_pagamentos=fonte, data_referencia_pagamentos="2025-12-10")
        chamadas.clear()
        r2 = run_pipeline(tmp_path, consulta_pagamentos=fonte, data_referencia_pagamentos="2025-12-31")

    assert chamadas == []
    versao2 = Path(r2["versao_dir"])
    ficha = json.loads((versao2 / "obras/1001.json").read_text(encoding="utf-8"))
    indice = json.loads((versao2 / "index_2025.json").read_text(encoding="utf-8"))
    esperado_pago = 0.0 if cenario == "sem_registros" else None
    assert ficha["funilFinanceiro"]["valorPago"] == esperado_pago
    assert ficha["apuracaoPagamentos"]["situacao"] == cenario
    assert ficha["apuracaoPagamentos"]["pagamentosConsolidados"] is True
    assert ficha["apuracaoPagamentos"]["limitacoesConhecidas"] == ["Histórico anterior a 2020 indisponível"]
    assert ficha["apuracaoPagamentos"]["periodoDisponivel"] == {"inicio": "2020-01-01", "fim": "2025-12-10"}
    assert indice["obras"][0]["valorPago"] == esperado_pago
    assert indice["metadata"]["atualizacao"]["limitacoesConhecidas"] == ["Histórico anterior a 2020 indisponível"]


def test_recuperacao_automatica_nao_grava_checkpoint_para_consolidado_e_retoma_ativo(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    obra_consolidada = {
        **SAMPLE_TRANSPARENCIA_GRID[0],
        "id": 1001,
        "nuContratoSigef": "001/2024",
        "dtInicioVigencia": "2022-01-01T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2024-12-01T00:00:00.000Z",
    }
    obra_ativa = {
        **SAMPLE_TRANSPARENCIA_GRID[0],
        "id": 1002,
        "nuContratoSigef": "002/2025",
        "dtInicioVigencia": "2025-01-01T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2027-12-31T00:00:00.000Z",
    }
    chamadas: list[tuple[str, str]] = []
    falhar_ativo = [False]
    dia = [datetime(2025, 12, 10, 12, tzinfo=timezone.utc)]

    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):
            return dia[0].astimezone(tz) if tz else dia[0].replace(tzinfo=None)

    def fonte(ug, contrato, referencia):
        chamadas.append((str(contrato), str(referencia)))
        if str(contrato) == "002/2025" and falhar_ativo[0]:
            raise RuntimeError("Falha transitória no ativo")
        return ConsultaPagamentos(
            registros=[{"pago": "R$ 300,00"}],
            data_referencia=referencia,
            concluida=True,
            validada=True,
            limitacoes_conhecidas=[],
        )

    out_dir = tmp_path / "data"
    with (
        patch("etl.runner.datetime", Relogio),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[obra_consolidada, obra_ativa]),
    ):
        run_pipeline(out_dir, consulta_pagamentos=fonte, data_referencia_pagamentos="2025-12-10")
        chamadas.clear()
        falhar_ativo[0] = True
        dia[0] = datetime(2025, 12, 20, 12, tzinfo=timezone.utc)
        with pytest.raises(RuntimeError, match="Falha transitória"):
            run_pipeline(out_dir, consulta_pagamentos=fonte, data_referencia_pagamentos="2025-12-20")

        estado_file = out_dir.parent / f".{out_dir.name}-recuperacao.json"
        estado_salvo = json.loads(estado_file.read_text(encoding="utf-8"))
        assert estado_salvo["contratos"] == {}
        assert estado_salvo["contrato_em_andamento"] == ["2401", "002/2025"]
        assert chamadas == [("002/2025", "2025-12-20")]

        chamadas.clear()
        falhar_ativo[0] = False
        dia[0] = datetime(2025, 12, 21, 12, tzinfo=timezone.utc)
        r_rec = run_pipeline(out_dir, consulta_pagamentos=fonte, modo_recuperacao=True)

    assert chamadas == [("002/2025", "2025-12-20")]
    assert r_rec["success"] is True
    ficha_1001 = json.loads((Path(r_rec["versao_dir"]) / "obras/1001.json").read_text(encoding="utf-8"))
    ficha_1002 = json.loads((Path(r_rec["versao_dir"]) / "obras/1002.json").read_text(encoding="utf-8"))
    assert ficha_1001["apuracaoPagamentos"]["pagamentosConsolidados"] is True
    assert ficha_1001["apuracaoPagamentos"]["dataReferencia"] == "2025-12-10"
    assert ficha_1002["apuracaoPagamentos"]["pagamentosConsolidados"] is False
    assert ficha_1002["apuracaoPagamentos"]["dataReferencia"] == "2025-12-20"


def test_falha_ou_data_divergente_em_contrato_ativo_bloqueia_publicacao_preservando_anterior(tmp_path: Path) -> None:
    obra_consolidada = {
        **SAMPLE_TRANSPARENCIA_GRID[0],
        "id": 1001,
        "nuContratoSigef": "001/2024",
        "dtInicioVigencia": "2022-01-01T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2024-12-01T00:00:00.000Z",
    }
    obra_ativa = {
        **SAMPLE_TRANSPARENCIA_GRID[0],
        "id": 1002,
        "nuContratoSigef": "002/2025",
        "dtInicioVigencia": "2025-01-01T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2027-12-31T00:00:00.000Z",
    }

    def fonte_ok(ug, contrato, referencia):
        return ConsultaPagamentos(
            registros=[{"pago": "R$ 300,00"}],
            data_referencia=referencia,
            concluida=True,
            validada=True,
            limitacoes_conhecidas=[],
        )

    def fonte_divergente(ug, contrato, referencia):
        return ConsultaPagamentos(
            registros=[{"pago": "R$ 300,00"}],
            data_referencia="2025-12-10",  # divergente da rodada 2025-12-20
            concluida=True,
            validada=True,
            limitacoes_conhecidas=[],
        )

    with patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[obra_consolidada, obra_ativa]):
        r1 = run_pipeline(tmp_path, consulta_pagamentos=fonte_ok, data_referencia_pagamentos="2025-12-10")
        atual_antes = (tmp_path / "atual.json").read_bytes()

        with pytest.raises(ValueError, match="Consulta obrigatória de pagamentos incompleta"):
            run_pipeline(tmp_path, consulta_pagamentos=fonte_divergente, data_referencia_pagamentos="2025-12-20")

    assert (tmp_path / "atual.json").read_bytes() == atual_antes
    assert json.loads((tmp_path / "atual.json").read_text(encoding="utf-8"))["versaoDados"] == Path(r1["versao_dir"]).name

"""Tentativas de conciliação observadas pelo fluxo de atualização."""

import json
import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.error import HTTPError

import pytest
from etl.runner import run_pipeline
from etl.consultas import ConsultaPagamentos, conciliar_pagamentos
from etl.progresso import ProgressoGit, chave_contrato
from etl.sources import transparencia
from tests.etl.fixtures.sample_data import (
    SAMPLE_GEOSALVADOR_BAIRROS, SAMPLE_GEOSALVADOR_PREFEITURAS, SAMPLE_TRANSPARENCIA_GRID,
)


@pytest.mark.parametrize("codigo, espera_servidor", [(429, 17), (503, None), (None, None)])
def test_portal_aumenta_pausa_apos_falha_e_reduz_gradualmente(codigo, espera_servidor):
    relogio = 0.0
    tentativas = 0
    esperas = []

    def esperar(segundos):
        nonlocal relogio
        esperas.append(segundos)
        relogio += segundos

    def responder(req, **opcoes):
        nonlocal tentativas
        tentativas += 1
        if tentativas == 2:
            if codigo is None:
                raise TimeoutError("Tempo de consulta excedido")
            cabecalhos = {"Retry-After": str(espera_servidor)} if espera_servidor else {}
            raise HTTPError(req.full_url, codigo, "Indisponível", cabecalhos, BytesIO())
        return BytesIO(b'{"totalObras":1}')

    with (
        patch.object(transparencia, "_proxima_requisicao", 0.0),
        patch.object(transparencia, "_intervalo_requisicoes", 0.5),
        patch.object(transparencia, "_respostas_estaveis", 0),
        patch("urllib.request.urlopen", side_effect=responder),
        patch("time.monotonic", side_effect=lambda: relogio),
        patch("time.sleep", side_effect=esperar),
    ):
        assert transparencia.fetch_totalizador()["totalObras"] == 1
        assert transparencia.fetch_totalizador()["totalObras"] == 1
        for _ in range(40):
            assert transparencia.fetch_totalizador()["totalObras"] == 1

    assert esperas == [0.5, espera_servidor or 10.0] + [2.0] * 19 + [1.0] * 20 + [0.5]


def test_bloqueio_explicito_impede_nova_tentativa_de_conciliacao():
    erro = HTTPError("https://exemplo.invalid", 500, "Erro interno", {},
                     BytesIO(b"<title>Web Page Blocked!</title>"))
    with (
        patch.object(transparencia, "_proxima_requisicao", 0.0),
        patch("urllib.request.urlopen", side_effect=erro) as consulta,
        patch("time.sleep") as esperar,
        pytest.raises(RuntimeError, match="Bloqueio explícito do Portal"),
    ):
        conciliar_pagamentos(2401, "001/2024", "2025-12-31", "2025-01-01", "2025-12-31")

    consulta.assert_called_once()
    esperar.assert_not_called()


@pytest.mark.parametrize("codigo,limite", [(503, 1), (503, 2), (503, 3), (404, 1)])
def test_tentativas_de_requisicao_respeitam_tipo_de_erro(tmp_path: Path, codigo: int, limite: int) -> None:
    registro = {"pago": "R$ 1,00", "dataPagamento": "01/01/2020"}
    pagina = {"dados": [registro], "paginacao": {"paginaAtual": 1, "totalPagina": 1,
              "paginas": 1, "tamanho": 10, "total": 1}, "totalizadores": {"Valor Pago": "R$ 1,00"}}
    chamadas = []
    esperas = []

    def portal(req, **kwargs):
        chamadas.append(req.full_url)
        if "downloadDados" in req.full_url and sum("downloadDados" in url for url in chamadas) <= limite:
            raise HTTPError(req.full_url, codigo, "indisponível", {"Retry-After": "20"}, None)
        resposta = BytesIO(json.dumps([registro] if "downloadDados" in req.full_url else pagina).encode())
        resposta.headers = {}
        return resposta

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=SAMPLE_TRANSPARENCIA_GRID[:1]),
        patch("etl.sources.transparencia.fetch_detalhes_obra", return_value={}),
        patch("etl.sources.transparencia.fetch_aditivos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_dotacao_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_empenhos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", return_value=[]),
        patch("urllib.request.urlopen", side_effect=portal),
        patch("time.sleep", side_effect=esperas.append),
    ):
        if codigo == 404 or limite == 3:
            with pytest.raises(HTTPError):
                run_pipeline(tmp_path, full_refresh=True, data_referencia_pagamentos="2025-12-31")
            assert sum("downloadDados" in url for url in chamadas) == (1 if codigo == 404 else 3)
            assert (20 in esperas) == (codigo == 503)
            if codigo == 503:
                assert 30 in esperas
            return
        resultado = run_pipeline(tmp_path, full_refresh=True, data_referencia_pagamentos="2025-12-31")

    ficha = json.loads((Path(resultado["versao_dir"]) / "obras/1001.json").read_text(encoding="utf-8"))
    assert ficha["funilFinanceiro"]["valorPago"] == 1
    assert 20 in esperas
    if limite == 2:
        assert 30 in esperas


def test_recuperacao_reusa_contrato_concluido_e_reinicia_o_interrompido(tmp_path: Path) -> None:
    remoto = tmp_path / "remoto.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remoto)], check=True)
    repositorios = [tmp_path / "runner1", tmp_path / "runner2"]
    for repositorio in repositorios:
        repositorio.mkdir()
        subprocess.run(["git", "init", "-q", str(repositorio)], check=True)
        subprocess.run(["git", "-C", str(repositorio), "remote", "add", "origin", str(remoto)], check=True)
    primeiro = SAMPLE_TRANSPARENCIA_GRID[0]
    segundo = {**primeiro, "id": 1002, "nuContratoSigef": "002/2024"}
    chamadas = []
    dia = [datetime(2026, 1, 5, 12, tzinfo=timezone.utc)]

    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):
            return dia[0].astimezone(tz) if tz else dia[0].replace(tzinfo=None)

    registro = {"pago": "R$ 1,00", "dataPagamento": "01/01/2020"}
    posterior = {"pago": "R$ 2,00", "dataPagamento": "06/01/2026"}
    pagina = {"dados": [registro, posterior], "paginacao": {"paginaAtual": 1, "totalPagina": 2,
              "paginas": 1, "tamanho": 10, "total": 2}, "totalizadores": {"Valor Pago": "R$ 3,00"}}

    def portal(endpoint, payload, **kwargs):
        contrato = payload["filtros"][1]["valor"]
        chamadas.append((contrato, "downloadDados" in endpoint))
        if contrato == "002/2024" and "downloadDados" in endpoint and dia[0].day == 5:
            raise KeyboardInterrupt("runner perdido")
        return [registro, posterior] if "downloadDados" in endpoint else pagina

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
        processo = subprocess.run([sys.executable, "-m", "tests.etl.fixtures.interromper_pipeline", str(repositorios[0])])
        assert processo.returncode == 23
        arquivos_remotos = subprocess.run(
            ["git", "--git-dir", str(remoto), "ls-tree", "-r", "--name-only", "refs/heads/etl-progresso"],
            check=True, capture_output=True, text=True,
        ).stdout.splitlines()
        arquivos_contratos = [arquivo for arquivo in arquivos_remotos if arquivo.startswith("contratos/")]
        assert "metadados.json" in arquivos_remotos
        assert "estado.json" not in arquivos_remotos
        assert len(arquivos_contratos) == 1
        metadados = json.loads(subprocess.run(
            ["git", "--git-dir", str(remoto), "show", "refs/heads/etl-progresso:metadados.json"],
            check=True, capture_output=True, text=True,
        ).stdout)
        contrato_salvo = json.loads(subprocess.run(
            ["git", "--git-dir", str(remoto), "show", f"refs/heads/etl-progresso:{arquivos_contratos[0]}"],
            check=True, capture_output=True, text=True,
        ).stdout)
        assert metadados["tentativa_original"]
        assert metadados["estado"] == "pendente"
        assert metadados["referencia"] == "2026-01-05"
        assert "contratos" not in metadados
        assert contrato_salvo["identidade"] == ["2401", "001/2024"]
        assert contrato_salvo["tentativa_original"] == metadados["tentativa_original"]
        assert contrato_salvo["ficha"]["pagamentos"] == [registro]
        chamadas.clear()
        dia[0] += timedelta(days=1)
        resultado = run_pipeline(repositorios[1] / "data", full_refresh=True, modo_recuperacao=True,
                                 repositorio_progresso=repositorios[1], aguardar_publicacao=True)

        confirmar = [sys.executable, "-c", "from pathlib import Path; import sys; from etl.progresso import confirmar_publicacao; confirmar_publicacao(Path(sys.argv[1]), sys.argv[2])", str(repositorios[1])]
        assert subprocess.run([*confirmar, "outra-tentativa"], capture_output=True).returncode != 0
        subprocess.run([*confirmar, resultado["tentativa"]], check=True)
        dia[0] += timedelta(days=1)
        assert run_pipeline(repositorios[1] / "data", modo_recuperacao=True, repositorio_progresso=repositorios[1])["recuperacao"] == "sem tentativa pendente"

    assert chamadas == [("002/2024", False), ("002/2024", True), ("002/2024", False)]
    indice = json.loads((Path(resultado["versao_dir"]) / "index_2025.json").read_text(encoding="utf-8"))
    metadata = indice["metadata"]["atualizacao"]
    assert all(obra["valorPago"] == 1 for obra in indice["obras"])
    assert metadata["dataReferenciaPagamentos"] == "2026-01-05"
    assert metadata["inicioConsultas"].startswith("2026-01-05")
    assert metadata["fimConsultas"].startswith("2026-01-06")


def test_gravacoes_concorrentes_preservam_a_primeira_revisao(tmp_path: Path) -> None:
    remoto = tmp_path / "remoto.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remoto)], check=True)
    repositorios = [tmp_path / f"runner{indice}" for indice in range(3)]
    for repositorio in repositorios:
        repositorio.mkdir()
        subprocess.run(["git", "init", "-q", str(repositorio)], check=True)
        subprocess.run(["git", "-C", str(repositorio), "remote", "add", "origin", str(remoto)], check=True)

    inicial = ProgressoGit(repositorios[0])
    assert inicial.carregar() is None
    inicial.salvar({
        "dia_inicial": "2026-01-05", "ultima_recuperacao": None, "year": 2025,
        "mandatos": None, "full_refresh": True, "referencia": "2026-01-05",
        "inicio_consultas": None, "concluida": False, "estado": "pendente",
        "tentativa_original": "tentativa-original", "historico": [], "contratos": {},
    })

    primeira = ProgressoGit(repositorios[1])
    segunda = ProgressoGit(repositorios[2])
    estado_primeiro = primeira.carregar()
    estado_segundo = segunda.carregar()
    estado_primeiro["estado"] = "concluida"
    estado_primeiro["concluida"] = True
    estado_segundo["estado"] = "pendente"
    primeira.salvar(estado_primeiro)

    with pytest.raises(RuntimeError, match="conflito"):
        segunda.salvar(estado_segundo)

    vencedora = ProgressoGit(repositorios[0]).carregar()
    assert vencedora["estado"] == "concluida"
    assert vencedora["concluida"] is True


def test_chave_do_checkpoint_distingue_pares_de_contrato() -> None:
    primeiro = ["UG/1", "CT-2"]
    segundo = ["UG", "1/CT-2"]

    assert chave_contrato(*primeiro) != chave_contrato(*segundo)
    assert ProgressoGit.caminho_checkpoint(primeiro) != ProgressoGit.caminho_checkpoint(segundo)


def test_checkpoint_acima_do_limite_nao_e_enviado(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from etl import progresso as modulo_progresso

    remoto = tmp_path / "remoto.git"
    repositorio = tmp_path / "runner"
    repositorio.mkdir()
    subprocess.run(["git", "init", "--bare", "-q", str(remoto)], check=True)
    subprocess.run(["git", "init", "-q", str(repositorio)], check=True)
    subprocess.run(["git", "-C", str(repositorio), "remote", "add", "origin", str(remoto)], check=True)
    monkeypatch.setattr(modulo_progresso, "LIMITE_CHECKPOINT_BYTES", 128)
    progresso = ProgressoGit(repositorio)
    assert progresso.carregar() is None

    estado = {
        "dia_inicial": "2026-01-05", "ultima_recuperacao": None, "year": 2025,
        "mandatos": None, "full_refresh": True, "referencia": "2026-01-05",
        "inicio_consultas": None, "concluida": False, "estado": "pendente",
        "tentativa_original": "tentativa-original", "historico": [],
        "contratos": {
            chave_contrato("2401", "001/2024"): {
                "identidade": ["2401", "001/2024"], "tentativa_original": "tentativa-original",
                "consulta": {"registros": []}, "ficha": {"objeto": "x" * 256},
            },
        },
    }
    with pytest.raises(ValueError, match="excede o limite"):
        progresso.salvar(estado)
    assert ProgressoGit(repositorio).carregar() is None


def test_esgotamento_conserva_versao_e_proxima_semanal_recomeca(tmp_path: Path) -> None:
    dia = [datetime(2026, 1, 5, 12, tzinfo=timezone.utc)]
    falhar = [False]
    referencias = []

    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):
            return dia[0].astimezone(tz) if tz else dia[0].replace(tzinfo=None)

    def pagamentos(ug, contrato, referencia):
        referencias.append(referencia)
        if falhar[0]:
            raise OSError("indisponível")
        return ConsultaPagamentos([], referencia, True, True)

    with (
        patch("etl.runner.datetime", Relogio),
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=SAMPLE_TRANSPARENCIA_GRID[:1]),
        patch("etl.sources.transparencia.fetch_detalhes_obra", return_value={}),
        patch("etl.sources.transparencia.fetch_aditivos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_dotacao_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_empenhos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", return_value=[]),
    ):
        run_pipeline(tmp_path, full_refresh=True, consulta_pagamentos=pagamentos)
        anterior = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
        falhar[0] = True
        with pytest.raises(OSError):
            run_pipeline(tmp_path, full_refresh=True, consulta_pagamentos=pagamentos)
        for _ in range(3):
            dia[0] += timedelta(days=1)
            with pytest.raises(OSError):
                run_pipeline(tmp_path, consulta_pagamentos=pagamentos, modo_recuperacao=True)
            quantidade = len(referencias)
            run_pipeline(tmp_path, consulta_pagamentos=pagamentos, modo_recuperacao=True)
            assert len(referencias) == quantidade
        dia[0] += timedelta(days=1)
        run_pipeline(tmp_path, consulta_pagamentos=pagamentos, modo_recuperacao=True)
        assert len(referencias) == quantidade
        assert {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == anterior
        dia[0] += timedelta(days=3)
        falhar[0] = False
        nova = run_pipeline(tmp_path, full_refresh=True, consulta_pagamentos=pagamentos)

    assert referencias == ["2026-01-05"] * 5 + ["2026-01-12"]
    indice = json.loads((Path(nova["versao_dir"]) / "index_2025.json").read_text(encoding="utf-8"))
    assert indice["metadata"]["atualizacao"]["dataReferenciaPagamentos"] == "2026-01-12"


@pytest.mark.parametrize("etapa", ["checkpoint", "estado_final"])
def test_falha_ao_persistir_checkpoint_impede_publicacao(tmp_path: Path, etapa: str) -> None:
    remoto = tmp_path / "remoto.git"
    repositorio = tmp_path / "runner"
    repositorio.mkdir()
    subprocess.run(["git", "init", "--bare", "-q", str(remoto)], check=True)
    subprocess.run(["git", "init", "-q", str(repositorio)], check=True)
    subprocess.run(["git", "-C", str(repositorio), "remote", "add", "origin", str(remoto)], check=True)
    output = repositorio / "data"

    def pagamento(ug, contrato, referencia):
        if etapa == "checkpoint":
            subprocess.run(["git", "-C", str(repositorio), "remote", "set-url", "origin", str(tmp_path / "inexistente.git")], check=True)
        return ConsultaPagamentos([], referencia, True, True)

    substituir = os.replace

    def interromper_no_ponteiro(origem, destino):
        substituir(origem, destino)
        if etapa == "estado_final" and Path(destino).name == "atual.json":
            subprocess.run(["git", "-C", str(repositorio), "remote", "set-url", "origin", str(tmp_path / "inexistente.git")], check=True)

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
        run_pipeline(output, data_referencia_pagamentos="2025-12-30")
        anterior = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
        grid.return_value = SAMPLE_TRANSPARENCIA_GRID[:1]
        with patch("os.replace", side_effect=interromper_no_ponteiro), pytest.raises(RuntimeError, match="armazenamento remoto"):
            run_pipeline(output, full_refresh=True, data_referencia_pagamentos="2025-12-31",
                         consulta_pagamentos=pagamento, repositorio_progresso=repositorio)
        assert {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()} == anterior

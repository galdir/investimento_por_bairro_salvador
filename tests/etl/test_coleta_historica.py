"""Coleta conciliada observada pela atualização em saída isolada."""

import json
import hashlib
from io import BytesIO
import time
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from etl.consultas import ConsultaPagamentos, LotePagamentos, conciliar_pagamentos, conciliar_janelas_pagamentos
from etl.runner import run_pipeline
from tests.etl.fixtures.sample_data import (
    SAMPLE_GEOSALVADOR_BAIRROS,
    SAMPLE_GEOSALVADOR_PREFEITURAS,
    SAMPLE_TRANSPARENCIA_GRID,
)


@pytest.mark.parametrize("cenario", ["valida", "vazia", "sem_valor", "negativo", "negativo_sem_frente", "semelhantes", "saldo_zero", "reprocessada", "origens_distintas", "origem_conflitante", "janelas_iguais", "janelas_divergentes", "contagem", "soma", "mudanca", "mudanca_extra", "invalida", "falha"])
def test_conciliacao_controla_publicacao_e_corte_civil(tmp_path: Path, cenario: str) -> None:
    registros = [{"id": 1, "pago": "R$ 1,00", "dataPagamento": "01/01/2020", "notaLiquidacao": "NL1"} for _ in range(34)]
    registros += [{"id": 2, "pago": "R$ 1,00", "dataPagamento": "31/12/2025", "notaLiquidacao": "NL1"}]
    registros += [{"id": 35, "pago": "R$ -2,00", "dataPagamento": "01/01/2026"}]
    pagina = {"dados": registros[:10], "paginacao": {"paginaAtual": 1, "totalPagina": 10,
              "paginas": 4, "tamanho": 10, "total": 36}, "totalizadores": {"Valor Pago": "R$ 33,00"}}
    if cenario == "vazia":
        registros = []
        pagina = {"dados": [], "paginacao": {"paginaAtual": 1, "totalPagina": 0,
                  "paginas": 0, "tamanho": 10, "total": 0}, "totalizadores": {"Valor Pago": "R$ 0,00"}}
    if cenario in ("sem_valor", "negativo", "negativo_sem_frente"):
        registros = [{"dataPagamento": "31/12/2025", "notaLiquidacao": "NL1", "pago": None if cenario == "sem_valor" else "R$ -2,00"}]
        if cenario == "negativo_sem_frente":
            registros[0].pop("notaLiquidacao")
        pagina = {"dados": registros, "paginacao": {"paginaAtual": 1, "totalPagina": 1,
                  "paginas": 1, "tamanho": 10, "total": 1}, "totalizadores": {"Valor Pago": "R$ 0,00" if cenario == "sem_valor" else "R$ -2,00"}}
    if cenario in ("semelhantes", "saldo_zero"):
        registros = [
            {"id": 1, "ordemBancaria": "OB1", "dataPagamento": "01/01/2025", "notaLiquidacao": "NL1", "pago": "R$ 1.000,00"},
            {"id": 2, "ordemBancaria": "OB1", "dataPagamento": "01/01/2025", "notaLiquidacao": "NL1", "pago": "R$ -1.000,00" if cenario == "saldo_zero" else "R$ 1.000,00"},
            {"dataPagamento": "01/01/2025", "pago": None},
        ]
        if cenario == "semelhantes":
            registros.append({"dataPagamento": "01/01/2025", "pago": "", "valorPago": "R$ 3,00"})
        pagina = {"dados": registros, "paginacao": {"paginaAtual": 1, "totalPagina": len(registros), "paginas": 1, "tamanho": 10, "total": len(registros)},
                  "totalizadores": {"Valor Pago": "R$ 0,00" if cenario == "saldo_zero" else "R$ 2.003,00"}}
    if cenario == "contagem":
        registros = registros[:-1]
    if cenario == "soma":
        pagina["totalizadores"]["Valor Pago"] = "R$ 34,00"
    if cenario == "mudanca_extra":
        pagina["paginacao"]["ordenacao"] = "original"
    chamadas = 0

    def portal(endpoint, payload, **opcoes):
        nonlocal chamadas
        chamadas += 1
        if cenario == "falha" and chamadas == 2:
            raise OSError("Falha intermediária")
        if cenario == "invalida" and chamadas == 2:
            return {"erro": "exportação inválida"}
        if cenario == "mudanca" and chamadas == 3:
            return {**pagina, "totalizadores": {"Valor Pago": "R$ 34,00"}}
        if cenario == "mudanca_extra" and chamadas == 3:
            return {**pagina, "paginacao": {**pagina["paginacao"], "ordenacao": "outra"}}
        if cenario == "janelas_divergentes" and "downloadDados" in endpoint and payload["dataInicio"].startswith("2025"):
            return [*registros[:-1], {**registros[-1], "notaLiquidacao": "OUTRA"}]
        if cenario == "janelas_iguais" and "downloadDados" in endpoint and payload["dataInicio"].startswith("2025"):
            return [{**registro, "id": 999} for registro in registros]
        return registros if "downloadDados" in endpoint else pagina

    def consulta(ug, contrato, referencia):
        if cenario in ("reprocessada", "origens_distintas", "origem_conflitante"):
            movimentos = [{"id": 1, "dataPagamento": "01/01/2025", "notaLiquidacao": "NL1", "pago": "R$ 1.000,00"}] * 2
            lote = LotePagamentos("resposta-da-coleta-1", movimentos)
            outro = LotePagamentos("resposta-da-coleta-2" if cenario == "origens_distintas" else lote.origem,
                                   movimentos[:1] if cenario == "origem_conflitante" else movimentos)
            return ConsultaPagamentos(movimentos + outro.registros, referencia, True, True, lotes=[lote, outro])
        if cenario.startswith("janelas_"):
            return conciliar_janelas_pagamentos(ug, contrato, referencia, [
                {"dataInicio": "2021-01-01T03:00:00.000Z", "dataFim": "2024-12-31T03:00:00.000Z"},
                {"dataInicio": "2025-01-01T03:00:00.000Z", "dataFim": "2028-12-31T03:00:00.000Z"},
            ])
        return conciliar_pagamentos(ug, contrato, referencia, "2021-01-01T03:00:00.000Z", "2024-12-31T03:00:00.000Z")

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[{**SAMPLE_TRANSPARENCIA_GRID[0], "dtTerminoVigenciaAtualizado": "2024-12-31"}]) as grid,
        patch("etl.sources.transparencia.fetch_detalhes_obra", return_value={}),
        patch("etl.sources.transparencia.fetch_aditivos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_dotacao_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_empenhos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", return_value=[{"notaLiquidacao": "NL1", "valLiqLiquidacao": 40}]),
        patch("etl.domain.geocoding._carregar_curadoria_territorial", return_value={"2401:001/2024": {"status": "multi_frente", "frentesMedicao": {"NL1": {"status": "promovido", "nivel": "Bairro", "bairro": "Pituba", "prefeituraBairro": "Barra/Pituba"}}}}),
        patch("etl.sources.transparencia._post_transparencia", side_effect=portal),
    ):
        opcao = {"consulta_pagamentos": consulta} if cenario.startswith("janelas_") or cenario in ("reprocessada", "origens_distintas", "origem_conflitante") else {}
        if cenario not in ("valida", "vazia", "sem_valor", "negativo", "negativo_sem_frente", "semelhantes", "saldo_zero", "reprocessada", "origens_distintas", "janelas_iguais"):
            grid.return_value = []
            run_pipeline(tmp_path, full_refresh=True, data_referencia_pagamentos="2025-12-30", **opcao)
            anterior = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
            grid.return_value = SAMPLE_TRANSPARENCIA_GRID[:1]
            with pytest.raises((ValueError, OSError)):
                run_pipeline(tmp_path, full_refresh=True, data_referencia_pagamentos="2025-12-31", **opcao)
            assert {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == anterior
            return
        resultado = run_pipeline(tmp_path, full_refresh=True, data_referencia_pagamentos="2025-12-31", **opcao)

    ficha = json.loads((Path(resultado["versao_dir"]) / "obras/1001.json").read_text(encoding="utf-8"))
    if not cenario.startswith("janelas_") and cenario not in ("reprocessada", "origens_distintas"):
        indice = json.loads((Path(resultado["versao_dir"]) / "index_2025.json").read_text(encoding="utf-8"))
        janela = {"dataInicio": "2021-01-01T03:00:00.000Z", "dataFim": "2024-12-31T03:00:00.000Z"}
        assert ficha["janelaPagamentos"] == janela
        assert indice["obras"][0]["janelaPagamentos"] == janela
    if cenario in ("reprocessada", "origens_distintas"):
        assert len(ficha["pagamentos"]) == (2 if cenario == "reprocessada" else 4)
        assert ficha["funilFinanceiro"]["valorPago"] == (2000 if cenario == "reprocessada" else 4000)
        assert ficha["frentesMedicao"][0]["valorPago"] == (2000 if cenario == "reprocessada" else 4000)
        evidencias = ficha["repeticoesColeta"]
        assert len(evidencias) == (1 if cenario == "reprocessada" else 0)
        if evidencias:
            assert evidencias[0]["origem"] == "resposta-da-coleta-1"
            assert evidencias[0]["ocorrenciasRemovidas"] == 2
            inicio = evidencias[0]["inicioOriginal"]
            lote_original = ficha["pagamentos"][inicio:inicio + evidencias[0]["ocorrenciasRemovidas"]]
            canonico = json.dumps(lote_original, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            assert evidencias[0]["sha256"] == hashlib.sha256(canonico.encode("utf-8")).hexdigest()
    elif cenario == "vazia":
        assert ficha["pagamentos"] == []
        assert ficha["funilFinanceiro"]["valorPago"] == 0
        assert ficha["apuracaoPagamentos"] == {"registrosSemValor": 0, "situacao": "sem_registros", "limitacoesConhecidas": [], "dataReferencia": "2025-12-31", "pagamentosConsolidados": False}
    elif cenario == "negativo_sem_frente":
        assert ficha["funilFinanceiro"]["valorPago"] == -2
        assert indice["kpis_globais"]["valorPagoNaoLocalizado"] == -2
    elif cenario in ("sem_valor", "negativo"):
        assert len(ficha["pagamentos"]) == 1
        assert ficha["funilFinanceiro"]["valorPago"] == (None if cenario == "sem_valor" else -2)
        assert ficha["apuracaoPagamentos"] == {"registrosSemValor": 1 if cenario == "sem_valor" else 0, "situacao": "indisponivel" if cenario == "sem_valor" else "saldo_registrado", "limitacoesConhecidas": [], "dataReferencia": "2025-12-31", "pagamentosConsolidados": False}
        assert ficha["frentesMedicao"][0]["valorPago"] == (None if cenario == "sem_valor" else -2)
        if cenario == "sem_valor":
            pituba = next(b for b in indice["bairros"] if b["nome"] == "Pituba")
            assert pituba["valorPago"] is None
            assert pituba["valorPagoDisponivel"] is False
            assert pituba["valorPagoFrentes"] is None
    elif cenario in ("semelhantes", "saldo_zero"):
        assert ficha["pagamentos"] == registros
        assert ficha["funilFinanceiro"]["valorPago"] == (0 if cenario == "saldo_zero" else 2003)
        assert ficha["apuracaoPagamentos"] == {"registrosSemValor": 1, "situacao": "saldo_registrado", "limitacoesConhecidas": [], "dataReferencia": "2025-12-31", "pagamentosConsolidados": False}
        assert ficha["frentesMedicao"][0]["valorPago"] == (0 if cenario == "saldo_zero" else 2000)
    else:
        assert len(ficha["pagamentos"]) == 35
        assert ficha["funilFinanceiro"]["valorPago"] == 35
        assert ficha["pagamentos"][-1]["dataPagamento"] == "31/12/2025"
        assert ficha["frentesMedicao"][0]["valorPago"] == 35

    if cenario in ("sem_valor", "reprocessada"):
        from etl.reconcile import reconciliar_acervo_local

        versao = Path(resultado["versao_dir"])
        antiga = {**ficha, "id": "antiga", "consultaPagamentosConcluida": False,
                  "pagamentos": [{"notaLiquidacao": "NL1", "pago": "R$ 9.000,00"}] * 5}
        (versao / "obras/antiga.json").write_text(json.dumps(antiga), encoding="utf-8")
        curadoria = {"2401:001/2024": {"status": "multi_frente", "frentesMedicao": {"NL1": {
            "status": "promovido", "nivel": "Bairro", "bairro": "Pituba", "prefeituraBairro": "Barra/Pituba"}}}}
        reconciliar_acervo_local(versao, curadoria=curadoria)
        reconciliada = json.loads((versao / "obras/1001.json").read_text(encoding="utf-8"))
        assert reconciliada["pagamentos"] == ficha["pagamentos"]
        assert reconciliada["funilFinanceiro"]["valorPago"] == ficha["funilFinanceiro"]["valorPago"]
        assert reconciliada["apuracaoPagamentos"] == ficha["apuracaoPagamentos"]
        assert reconciliada["repeticoesColeta"] == ficha["repeticoesColeta"]
        assert reconciliada["frentesMedicao"][0]["valorPago"] == ficha["frentesMedicao"][0]["valorPago"]


def test_movimentos_iguais_de_contratos_diferentes_sao_preservados(tmp_path: Path) -> None:
    primeiro = {**SAMPLE_TRANSPARENCIA_GRID[0], "dtTerminoVigenciaAtualizado": "2024-12-31"}
    segundo = {**primeiro, "id": 1002, "nuContratoSigef": "002/2024"}
    movimento = {"id": 7, "ordemBancaria": "OB1", "dataPagamento": "01/01/2024", "pago": "R$ 1.000,00"}

    def consulta(ug, contrato, referencia):
        lote = LotePagamentos(f"resposta-{contrato}", [movimento])
        return ConsultaPagamentos([movimento], referencia, True, True, lotes=[lote])

    with (
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
    ):
        resultado = run_pipeline(tmp_path, full_refresh=True, data_referencia_pagamentos="2025-12-31", consulta_pagamentos=consulta)

    indice = json.loads((Path(resultado["versao_dir"]) / "index_2025.json").read_text(encoding="utf-8"))
    assert {obra["numeroContrato"]: obra["valorPago"] for obra in indice["obras"]} == {"001/2024": 1000, "002/2024": 1000}
    for obra_id in (1001, 1002):
        ficha = json.loads((Path(resultado["versao_dir"]) / f"obras/{obra_id}.json").read_text(encoding="utf-8"))
        assert ficha["pagamentos"] == [movimento]
        assert ficha["repeticoesColeta"] == []


@pytest.mark.parametrize("legado", [False, True])
def test_janelas_do_grid_sobrevivem_ao_reuso_incremental(tmp_path: Path, legado: bool) -> None:
    valor = [1]

    payloads = []
    def portal(endpoint, payload, **opcoes):
        payloads.append(payload)
        pagamento = {"dataPagamento": "01/01/2020", "pago": f"R$ {valor[0]},00"}
        if "downloadDados" in endpoint:
            return [pagamento]
        return {"dados": [pagamento], "paginacao": {"paginaAtual": 1, "totalPagina": 1, "paginas": 1, "tamanho": 10, "total": 1},
                "totalizadores": {"Valor Pago": f"R$ {valor[0]},00"}}

    encerrada = deepcopy(SAMPLE_TRANSPARENCIA_GRID[0])
    futura = {**deepcopy(encerrada), "id": "futura", "nuContratoSigef": "002/2025", "dtInicioVigencia": "2025-01-01", "dtTerminoVigenciaAtualizado": "2026-01-01", "mandatos": ["2025-2028"]}
    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value={}),
        patch("etl.sources.transparencia.fetch_totalizador", return_value={}),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=[encerrada, futura]) as grid,
        patch("etl.sources.transparencia.fetch_detalhes_obra", return_value={}),
        patch("etl.sources.transparencia.fetch_aditivos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_dotacao_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_empenhos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", return_value=[]),
        patch("etl.sources.transparencia._post_transparencia", side_effect=portal),
    ):
        primeira = run_pipeline(tmp_path, full_refresh=True)
        if legado:
            versao = Path(primeira["versao_dir"])
            manifesto_path = versao / "manifesto.json"
            manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))
            for nome in ("index.json", "index_2025.json"):
                caminho = versao / nome
                indice = json.loads(caminho.read_text(encoding="utf-8"))
                for obra in indice["obras"]:
                    obra.pop("janelasGrid")
                caminho.write_text(json.dumps(indice, ensure_ascii=False), encoding="utf-8")
                manifesto["arquivos"][nome] = hashlib.sha256(caminho.read_bytes()).hexdigest()
            manifesto_path.write_text(json.dumps(manifesto), encoding="utf-8")
        grid.reset_mock()
        payloads.clear()
        grid.return_value = [encerrada, futura] if legado else [futura]
        valor[0] = 2
        segunda = run_pipeline(tmp_path)
        assert grid.call_count == (2 if legado else 1)
        indice_novo = json.loads((Path(segunda["versao_dir"]) / "index_2025.json").read_text(encoding="utf-8"))
        assert {obra["numeroContrato"]: obra["valorPago"] for obra in indice_novo["obras"]} == {"001/2024": 2, "002/2025": 2}
        assert len(payloads) == 6
        assert all(payload["dataInicio"] == "2021-01-01T03:00:00.000Z" for payload in payloads)

    janelas = [{"dataInicio": "2021-01-01T03:00:00.000Z", "dataFim": "2024-12-31T03:00:00.000Z"},
               {"dataInicio": "2025-01-01T03:00:00.000Z", "dataFim": "2028-12-31T03:00:00.000Z"}]
    for resultado in ((segunda,) if legado else (primeira, segunda)):
        indice = json.loads((Path(resultado["versao_dir"]) / "index_2025.json").read_text(encoding="utf-8"))
        assert next(o for o in indice["obras"] if o["nuContratoSigef"] == "002/2025")["janelasGrid"] == janelas


def test_atualizacao_respeita_intervalo_entre_requisicoes_ao_portal(tmp_path: Path) -> None:
    esperas = []
    relogio = [time.monotonic() + 10]
    registros = [{"pago": "R$ 1,00", "dataPagamento": "01/01/2020"}]
    pagina = {"dados": registros, "paginacao": {"paginaAtual": 1, "totalPagina": 1, "paginas": 1, "tamanho": 10, "total": 1},
              "totalizadores": {"Valor Pago": "R$ 1,00"}}

    def urlopen(requisicao, **opcoes):
        resposta = BytesIO(json.dumps(registros if "downloadDados" in requisicao.full_url else pagina).encode())
        resposta.headers = {}
        return resposta

    def esperar(segundos):
        esperas.append(segundos)
        relogio[0] += segundos

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
        patch("urllib.request.urlopen", side_effect=urlopen),
        patch("etl.sources.transparencia._proxima_requisicao", 0.0),
        patch("etl.sources.transparencia._intervalo_requisicoes", 0.5),
        patch("time.monotonic", side_effect=lambda: relogio[0]),
        patch("time.sleep", side_effect=esperar),
    ):
        run_pipeline(tmp_path, full_refresh=True, data_referencia_pagamentos="2025-12-31")
    assert esperas == [0.5, 0.5]

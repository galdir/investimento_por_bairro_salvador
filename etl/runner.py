"""Ponto de entrada e orquestrador do pipeline ETL de Obras e Território de Salvador.

Coordena a extração das fontes governamentais, transformação dos dados territoriais,
execução do funil de alocação territorial com cache incremental em disco e gravação dos
artefatos estáticos particionados em conformidade com o ADR-0001.
"""

import copy
import json
import math
import os
import re
import shutil
import tempfile
import time
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any
import warnings
from dataclasses import asdict
from uuid import uuid4

if os.name == "nt":
    import msvcrt
else:
    import fcntl

from etl.domain import kpis
from etl.domain.pagamentos import valor_informado_pagamento
from etl.domain.ficha_limpa import (
    construir_ficha_obra,
    mesclar_fichas_obra,
    sincronizar_obra_com_ficha,
)
from etl.domain.geocoding import (
    GeocodingCache,
    calcular_centroides_bairros,
    classificar_alocacao_territorial,
    resolver_frentes_medicao,
)
from etl.domain.mandato import (
    MANDATOS_MUNICIPAIS,
    cds_ug_compativeis,
    deduplicar_obras,
    obter_chave_canonica_obra,
    normalizar_data_chave,
    obter_chaves_candidatas_obra,
    resolver_datas_vigencia,
)
from etl.domain.semaforo import classificar_semaforo, recalcular_semaforo_pos_ficha
from etl.domain.tema import classificar_tema
from etl.domain.vocacao import classificar_vocacao
from etl.domain.territorio import (
    calcular_rollup_territorial,
    is_centralidade_metropolitana,
    is_zona_especial_nao_residencial,
    normalizar_e_vincular_malhas_geosalvador,
    normalizar_nome,
    normalizar_nome_prefeitura_bairro,
    parse_float,
)
from etl.generator import (
    generate_bairros_geojson,
    generate_index_json,
    generate_prefeituras_geojson,
)
from etl.reconcile import (
    coletar_fichas_candidatas,
    escrever_indices_alias,
    finalizar_acervo_obras,
    indexar_fichas_locais,
    resolver_caminho_indice,
)
from etl.sources import geosalvador, ibge_censo, transparencia
from etl.publicacao import finalizar_versao, versao_anterior_valida, versao_publicada
from etl.consultas import ConsultaPagamentos, LotePagamentos, coletar_pagamentos, incorporar_lotes_pagamentos
from etl.progresso import ProgressoGit, chave_contrato


class InterrupcaoEnsaiada(RuntimeError):
    """Falha controlada para testar a retomada depois de checkpoints remotos."""


def _substituir_com_retentativa(origem: Path, destino: Path, tentativas: int = 10) -> None:
    """Executa `os.replace` com retentativa breve para contornar bloqueios transitórios no Windows."""
    for tentativa in range(tentativas):
        try:
            os.replace(origem, destino)
            return
        except PermissionError:
            if tentativa == tentativas - 1:
                if origem.is_dir() and not destino.exists():
                    shutil.copytree(origem, destino)
                    shutil.rmtree(origem, ignore_errors=True)
                    return
                raise
            time.sleep(0.1 * (tentativa + 1))


def _parse_data_calendario(valor: Any) -> date | None:
    """Converte string ISO/BR para `date` apenas quando representa data de calendário válida."""
    if not isinstance(valor, str) or not valor.strip():
        return None
    chave = normalizar_data_chave(valor)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", chave):
        return None
    try:
        return date.fromisoformat(chave)
    except ValueError:
        return None


def _validar_periodo_disponivel(periodo: Any) -> bool:
    """Valida se `periodoDisponivel` possui início e fim ISO válidos com início <= fim."""
    if (
        not isinstance(periodo, dict)
        or set(periodo) != {"inicio", "fim"}
        or any(
            not isinstance(periodo[campo], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", periodo[campo])
            for campo in ("inicio", "fim")
        )
        or periodo["inicio"] > periodo["fim"]
    ):
        return False
    return _parse_data_calendario(periodo["inicio"]) is not None and _parse_data_calendario(periodo["fim"]) is not None


def _primeiro_float_informado(registro: dict[str, Any], *chaves: str) -> float:
    for chave in chaves:
        val = registro.get(chave)
        if val is not None and val != "":
            return parse_float(val)
    return 0.0


def _campos_monitorados_inalterados(obra: dict[str, Any], ficha_disco: dict[str, Any]) -> bool:
    """Compara os quatro campos monitorados do grid com a ficha persistida localmente."""
    vl_atua = _primeiro_float_informado(obra, "vlAtualizado", "valorContratualVigente", "vlOriginal")
    perc_exec = _primeiro_float_informado(obra, "percentualExecutado")
    ds_situacao = str(obra.get("dsSituacao") or obra.get("situacao") or "").strip()
    dt_termino = normalizar_data_chave(obra.get("dtTerminoVigenciaAtualizado") or "")

    p_funil = ficha_disco.get("funilFinanceiro") or {}
    p_vigencia = ficha_disco.get("vigencia") or {}
    p_vl_atua = _primeiro_float_informado(p_funil, "valorContratualVigente")
    if p_vl_atua == 0.0 and p_funil.get("valorContratualVigente") is None:
        p_vl_atua = _primeiro_float_informado(ficha_disco, "vlAtualizado")
    p_perc_exec = _primeiro_float_informado(p_funil, "percentualExecutado")
    if p_perc_exec == 0.0 and p_funil.get("percentualExecutado") is None:
        p_perc_exec = _primeiro_float_informado(ficha_disco, "percentualExecutado")
    p_ds_situacao = str(ficha_disco.get("situacao") or ficha_disco.get("dsSituacao") or "").strip()
    p_dt_termino = normalizar_data_chave(
        p_vigencia.get("dataTerminoAtualizado") or ficha_disco.get("dtTerminoVigenciaAtualizado") or ""
    )

    return (
        vl_atua == p_vl_atua
        and perc_exec == p_perc_exec
        and ds_situacao == p_ds_situacao
        and dt_termino == p_dt_termino
    )


def _eh_ficha_pagamentos_integra(ficha: Any) -> bool:
    """Verifica se a ficha local comprova coleta de pagamentos concluída e estruturalmente íntegra."""
    if not isinstance(ficha, dict) or ficha.get("consultaPagamentosConcluida") is not True:
        return False
    pagamentos = ficha.get("pagamentos")
    if not isinstance(pagamentos, list) or not all(isinstance(item, dict) for item in pagamentos):
        return False
    funil = ficha.get("funilFinanceiro")
    if not isinstance(funil, dict) or "valorPago" not in funil:
        return False
    valor_pago = funil.get("valorPago")
    if valor_pago is not None and (
        not isinstance(valor_pago, (int, float)) or isinstance(valor_pago, bool) or not math.isfinite(valor_pago)
    ):
        return False
    apuracao = ficha.get("apuracaoPagamentos")
    if not isinstance(apuracao, dict):
        return False
    situacao = apuracao.get("situacao")
    if situacao not in {"sem_registros", "indisponivel", "saldo_registrado"}:
        return False
    if situacao == "sem_registros" and (pagamentos != [] or valor_pago not in (0, 0.0)):
        return False
    if situacao == "indisponivel" and valor_pago is not None:
        return False
    if situacao == "saldo_registrado" and valor_pago is None:
        return False
    reg_sem_valor = apuracao.get("registrosSemValor")
    if not isinstance(reg_sem_valor, int) or isinstance(reg_sem_valor, bool) or reg_sem_valor < 0:
        return False
    limitacoes = apuracao.get("limitacoesConhecidas")
    if not isinstance(limitacoes, list) or not all(isinstance(item, str) and item for item in limitacoes):
        return False
    if "periodoDisponivel" in apuracao and apuracao["periodoDisponivel"] is not None:
        if not _validar_periodo_disponivel(apuracao["periodoDisponivel"]):
            return False
    return _parse_data_calendario(apuracao.get("dataReferencia")) is not None


def _contrato_elegivel_pagamentos_consolidados(
    *,
    obra: dict[str, Any],
    ficha_disco: dict[str, Any] | None,
    referencia_pagamentos: str,
    full_refresh: bool,
    anterior_valida: bool,
) -> bool:
    """Avalia se o contrato é elegível ao reaproveitamento local como Contrato com Pagamentos Consolidados."""
    if full_refresh or not anterior_valida or ficha_disco is None:
        return False

    ref_date = _parse_data_calendario(referencia_pagamentos)
    dt_termino_date = _parse_data_calendario(obra.get("dtTerminoVigenciaAtualizado"))
    if ref_date is None or dt_termino_date is None or (ref_date - dt_termino_date).days <= 365:
        return False

    if not _campos_monitorados_inalterados(obra, ficha_disco):
        return False

    if not _eh_ficha_pagamentos_integra(ficha_disco):
        return False

    data_ref_salva = _parse_data_calendario((ficha_disco.get("apuracaoPagamentos") or {}).get("dataReferencia"))
    if data_ref_salva is None:
        return False
    dias_consolidacao = (ref_date - data_ref_salva).days
    return 0 <= dias_consolidacao < 180


def run_pipeline(
    output_dir: Path,
    year: int = 2025,
    cache_file: Path | None = None,
    mandatos: list[str] | None = None,
    full_refresh: bool = False,
    data_referencia_pagamentos: str | None = None,
    consulta_pagamentos=None,
    modo_recuperacao: bool = False,
    aguardar_publicacao: bool = False,
    repositorio_progresso: Path | None = None,
    ref_progresso: str | None = None,
    interromper_apos_checkpoints: int | None = None,
) -> dict[str, Any]:
    """Executa uma tentativa exclusiva e registra seu resultado fora do acervo publicado."""
    output_path = Path(output_dir).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = output_path.parent / f".{output_path.name}.lock"
    lock = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        if os.name == "nt":
            msvcrt.locking(lock, msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        os.close(lock)
        raise RuntimeError("Já existe uma atualização em andamento") from exc
    tentativa = uuid4().hex

    def registrar(estado: str, erro: str | None = None) -> None:
        registro = {"tentativa": tentativa, "instante": datetime.now(timezone.utc).isoformat(), "estado": estado}
        if erro:
            registro["erro"] = erro
        try:
            with (output_path.parent / f".{output_path.name}-tentativas.jsonl").open("a", encoding="utf-8") as arquivo:
                arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
        except OSError as exc:
            warnings.warn(f"Não foi possível registrar a tentativa: {exc}", RuntimeWarning, stacklevel=2)

    try:
        estado_path = output_path.parent / f".{output_path.name}-recuperacao.json"
        if interromper_apos_checkpoints is not None:
            if interromper_apos_checkpoints < 1 or repositorio_progresso is None or modo_recuperacao:
                raise ValueError("A interrupção ensaiada exige uma tentativa inicial e um ref remoto")
        progresso = ProgressoGit(repositorio_progresso, ref_progresso) if repositorio_progresso is not None else None
        remoto = progresso.carregar() if progresso is not None else None
        metricas_recuperacao = {"contratos_reaproveitados": [], "contratos_reiniciados": []}
        hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
        if modo_recuperacao:
            if progresso is not None:
                estado = remoto
            elif estado_path.exists():
                estado = json.loads(estado_path.read_text(encoding="utf-8"))
            else:
                estado = None
            if estado is None:
                return {"success": False, "recuperacao": "sem tentativa pendente"}
            if estado.get("concluida"):
                return {"success": False, "recuperacao": "sem tentativa pendente"}
            identidade_interrompida = estado.get("contrato_em_andamento")
            if (isinstance(identidade_interrompida, list) and len(identidade_interrompida) == 2
                    and all(isinstance(parte, str) for parte in identidade_interrompida)
                    and chave_contrato(*identidade_interrompida) not in estado.get("contratos", {})):
                metricas_recuperacao["contratos_reiniciados"].append(identidade_interrompida)
            dias = (hoje - date.fromisoformat(estado["dia_inicial"])).days
            if dias not in (1, 2, 3) or estado.get("ultima_recuperacao") == hoje.isoformat():
                return {"success": False, "recuperacao": "fora da janela diária"}
            estado["ultima_recuperacao"] = hoje.isoformat()
            year, mandatos, full_refresh = estado["year"], estado["mandatos"], estado["full_refresh"]
            data_referencia_pagamentos = estado["referencia"]
            if not estado.get("tentativa_original"):
                historico = estado.get("historico") or []
                estado["tentativa_original"] = historico[0]["tentativa"] if historico else tentativa
        else:
            estado = {"dia_inicial": hoje.isoformat(), "ultima_recuperacao": None,
                      "year": year, "mandatos": mandatos, "full_refresh": full_refresh,
                      "referencia": data_referencia_pagamentos or hoje.isoformat(),
                      "inicio_consultas": None, "contratos": {}, "historico": [],
                      "tentativa_original": tentativa, "concluida": False,
                      "contrato_em_andamento": None}
            data_referencia_pagamentos = estado["referencia"]

        estado.setdefault("contrato_em_andamento", None)

        def salvar_estado() -> None:
            if progresso is None:
                temporario = estado_path.with_suffix(".tmp")
                temporario.write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")
                _substituir_com_retentativa(temporario, estado_path)
            else:
                progresso.salvar(estado)

        estado["estado"] = "pendente"
        estado.setdefault("historico", []).append({"tentativa": tentativa, "dia": hoje.isoformat(), "estado": "iniciada"})
        salvar_estado()
        registrar("iniciada")

        def finalizar_estado() -> None:
            estado["historico"][-1]["estado"] = "preparada" if aguardar_publicacao else "concluida"
            estado["concluida"] = not aguardar_publicacao
            estado["estado"] = "preparada" if aguardar_publicacao else "concluida"
            salvar_estado()

        try:
            resultado = _preparar_e_publicar(
                output_path, year, cache_file, mandatos, full_refresh, data_referencia_pagamentos,
                consulta_pagamentos, estado, salvar_estado, finalizar_estado,
                metricas_recuperacao, interromper_apos_checkpoints,
            )
        except Exception as exc:
            registrar("falhou", str(exc))
            estado["concluida"] = False
            estado["estado"] = "pendente"
            estado["historico"][-1]["estado"] = "falhou"
            estado["historico"][-1]["erro"] = str(exc)
            salvar_estado()
            raise
        registrar("concluida")
        resultado["tentativa"] = tentativa
        resultado["ref_progresso"] = progresso.ref if progresso is not None else None
        resultado["revisao_progresso"] = progresso.versao if progresso is not None else None
        resultado["data_referencia_pagamentos"] = estado["referencia"]
        resultado.update(metricas_recuperacao)
        return resultado
    finally:
        os.close(lock)


def _preparar_e_publicar(
    output_dir: Path,
    year: int,
    cache_file: Path | None,
    mandatos: list[str] | None,
    full_refresh: bool,
    data_referencia_pagamentos: str | None,
    consulta_pagamentos,
    estado,
    salvar_estado,
    finalizar_estado,
    metricas_recuperacao,
    interromper_apos_checkpoints,
) -> dict[str, Any]:
    """Prepara e valida uma versão imutável antes de trocar o ponteiro."""
    output_path = Path(output_dir).resolve()
    referencia = data_referencia_pagamentos or datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()
    if datetime.strptime(referencia, "%Y-%m-%d").date().isoformat() != referencia:
        raise ValueError("Data de referência dos pagamentos inválida")
    if mandatos is not None and (not mandatos or any(m not in MANDATOS_MUNICIPAIS for m in mandatos)):
        raise ValueError("Plano de consultas contém mandato inválido ou vazio")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{output_path.name}-", dir=output_path.parent, ignore_cleanup_errors=True
    ) as temp:
        temp_path = Path(temp)
        stage = temp_path / "preparado"
        anterior = versao_publicada(output_path)
        if anterior is not None and not versao_anterior_valida(anterior):
            raise ValueError("A versão publicada não passou na verificação de integridade")
        if anterior is not None:
            shutil.copytree(anterior, stage)
        else:
            stage.mkdir()

        external_cache = None
        stage_cache = None
        if cache_file is not None:
            cache_path = Path(cache_file).resolve()
            try:
                relativo = cache_path.relative_to(output_path)
                if (not relativo.parts or relativo.parts[0] in {"geo", "obras", "versoes"}
                        or relativo.name in {"atual.json", "manifesto.json", "index.json"}
                        or relativo.name.startswith("index_")):
                    raise ValueError("O cache não pode substituir um artefato publicado")
                stage_cache = stage / relativo
            except ValueError:
                if cache_path.is_relative_to(output_path):
                    raise
                external_cache = cache_path
                stage_cache = stage / "geocoding_cache.json"

        anterior_valida = anterior is not None
        resultado = _executar_pipeline(
            stage, year, stage_cache, mandatos, full_refresh, anterior_valida, referencia,
            consulta_pagamentos, estado, salvar_estado, metricas_recuperacao,
            interromper_apos_checkpoints,
        )
        metadados = finalizar_versao(stage, year, resultado["inicio_consultas"], resultado["fim_consultas"], referencia, resultado["limitacoes_conhecidas"], resultado["total_obras"], stage_cache)
        versao = metadados["versaoDados"]
        ponteiro = temp_path / "atual.json"
        ponteiro.write_text(json.dumps({"versaoDados": versao, "caminho": f"versoes/{versao}"}), encoding="utf-8")
        destino = output_path / "versoes" / versao

        if external_cache is not None and stage_cache is not None and stage_cache.exists():
            external_cache.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(stage_cache, external_cache)

        output_path.mkdir(parents=True, exist_ok=True)
        destino.parent.mkdir(parents=True, exist_ok=True)
        caminho_atual = output_path / "atual.json"
        ponteiro_anterior = caminho_atual.read_bytes() if caminho_atual.exists() else None
        _substituir_com_retentativa(stage, destino)
        ativado = False
        try:
            _substituir_com_retentativa(ponteiro, caminho_atual)
            ativado = True
            finalizar_estado()
        except BaseException:
            if ativado:
                if ponteiro_anterior is None:
                    caminho_atual.unlink(missing_ok=True)
                else:
                    restauracao = temp_path / "anterior.json"
                    restauracao.write_bytes(ponteiro_anterior)
                    _substituir_com_retentativa(restauracao, caminho_atual)
            shutil.rmtree(destino)
            raise

        resultado["output_dir"] = str(output_path)
        resultado["versao_dir"] = str(destino)
        resultado["cache_file"] = str(external_cache if external_cache is not None else destino / (stage_cache.relative_to(stage) if stage_cache is not None else "geocoding_cache.json"))
        return resultado


def _executar_pipeline(
    output_dir: Path,
    year: int = 2025,
    cache_file: Path | None = None,
    mandatos: list[str] | None = None,
    full_refresh: bool = False,
    anterior_valida: bool = False,
    referencia_pagamentos: str = "",
    consulta_pagamentos=None,
    estado=None,
    salvar_estado=None,
    metricas_recuperacao=None,
    interromper_apos_checkpoints=None,
) -> dict[str, Any]:
    """Executa o pipeline completo de extração, geocodificação territorial, rollup e geração de artefatos.

    Sumário:
        Orquestra a coleta de malhas, censo, transparência, funil de alocação territorial e artefatos estáticos.

    Descrição Estendida:
        1. Extrai as malhas de Bairros Oficiais (Camada 164) e Prefeituras-Bairro (Camada 7) do GeoSalvador.
        2. Extrai dados demográficos e de vulnerabilidade do Censo 2022 do IBGE.
        3. Extrai totalizadores e contratos detalhados de Obras Públicas da Transparência de Salvador,
           com suporte a execução incremental inteligente (preservando mandatos encerrados e fichas
           inalteradas quando full_refresh=False) ou reconsulta forçada (full_refresh=True).
        4. Calcula os centróides geométricos dos Bairros Oficiais.
        5. Executa o Funil de Alocação Territorial em 3 estágios com cache incremental em disco.
        6. Aplica as regras de rollup financeiro (Camada A) por Bairro Oficial e por Prefeitura-Bairro.
        7. Gera `geo/bairros.geojson` e `geo/prefeituras_bairro.geojson` enriquecidos com métricas de investimento.
        8. Consolida os KPIs municipais de investimento (incluindo transparência opaca) e gera `index_<ano>.json`.

    Argumentos:
        output_dir: Diretório base onde a árvore de artefatos estáticos (`geo/`, `index_<ano>.json`) será gravada.
        year: Ano de referência da execução do pipeline (padrão: 2025).
        cache_file: Caminho opcional do arquivo de Cache Incremental de geocodificação
            (padrão: `<output_dir>/geocoding_cache.json`).
        mandatos: Lista opcional de mandatos municipais a considerar (padrão: todos de MANDATOS_MUNICIPAIS).
        full_refresh: Booleano que, se True, força a reconsulta de todos os mandatos e contratos de obras.

    Retornos:
        Dicionário com status da execução, contendo:
        - 'success': Booleano indicando se o pipeline foi concluído com êxito.
        - 'output_dir': Caminho em string do diretório de saída gerado.
        - 'cache_file': Caminho em string do arquivo de cache incremental utilizado.
        - 'cache_hits': Quantidade de obras resolvidas diretamente pelo cache incremental.
        - 'detail_cache_hits': Quantidade de fichas de obras reaproveitadas incrementalmente.
        - 'full_refresh': Booleano indicando o modo de execução.
        - 'ano': Ano processado.
        - 'total_bairros': Quantidade de bairros oficiais processados.
        - 'total_prefeituras': Quantidade de prefeituras-bairro processadas.
        - 'total_obras': Quantidade de obras listadas.

    Erros:
        Lança exceções caso ocorra erro irrecuperável durante a extração ou gravação dos arquivos.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    metricas_recuperacao = metricas_recuperacao if metricas_recuperacao is not None else {
        "contratos_reaproveitados": [], "contratos_reiniciados": [],
    }

    inicio_consultas = estado.get("inicio_consultas") if estado is not None else None
    fim_consultas = None

    def consultar(funcao, *args, **kwargs):
        nonlocal inicio_consultas, fim_consultas
        if inicio_consultas is None:
            inicio_consultas = datetime.now(timezone.utc).isoformat()
            if estado is not None:
                estado["inicio_consultas"] = inicio_consultas
                salvar_estado()
        try:
            return funcao(*args, **kwargs)
        finally:
            fim_consultas = datetime.now(timezone.utc).isoformat()

    # 1. Extração das fontes de dados externas e normalização das malhas
    raw_bairros = consultar(geosalvador.fetch_bairros_geojson)
    raw_prefeituras = consultar(geosalvador.fetch_prefeituras_geojson)
    raw_bairros, raw_prefeituras = normalizar_e_vincular_malhas_geosalvador(raw_bairros, raw_prefeituras)
    demografia_map = consultar(ibge_censo.fetch_demografia_censo_2022)
    totalizador = consultar(transparencia.fetch_totalizador, year=year)

    # Coleta de obras para todos os mandatos municipais especificados com suporte incremental
    mandatos_lista = mandatos or list(MANDATOS_MUNICIPAIS.keys())
    raw_grid: list[dict[str, Any]] = []
    mandatos_consultar = list(mandatos_lista)
    closed_mandates_reused: set[str] = set()

    # Reuso incremental de mandatos encerrados (ex: 2021-2024)
    index_candidate = resolver_caminho_indice(output_path, year) if anterior_valida else None

    def _hidratar_obra_existente(o: dict[str, Any]) -> dict[str, Any]:
        item_copy = dict(o)
        if "cdUnidadeGestora" not in item_copy and "unidadeGestora" in item_copy:
            item_copy["cdUnidadeGestora"] = item_copy["unidadeGestora"]
        if "sgOrgao" not in item_copy and "unidadeGestora" in item_copy:
            item_copy["sgOrgao"] = item_copy["unidadeGestora"]
        if "nuContratoSigef" not in item_copy and "numeroContrato" in item_copy:
            item_copy["nuContratoSigef"] = item_copy["numeroContrato"]
        if "dsObjeto" not in item_copy and "objeto" in item_copy:
            item_copy["dsObjeto"] = item_copy["objeto"]
        if "vlOriginal" not in item_copy and "valorOriginal" in item_copy:
            item_copy["vlOriginal"] = item_copy["valorOriginal"]
        if "vlAtualizado" not in item_copy and "valorContratualVigente" in item_copy:
            item_copy["vlAtualizado"] = item_copy["valorContratualVigente"]
        if "dsSituacao" not in item_copy and "situacao" in item_copy:
            item_copy["dsSituacao"] = item_copy["situacao"]
        if "nmCredor" not in item_copy and "credor" in item_copy:
            item_copy["nmCredor"] = item_copy["credor"]
        if "nuDocumentoCredor" not in item_copy and "cnpj" in item_copy:
            item_copy["nuDocumentoCredor"] = item_copy["cnpj"]
        if item_copy.get("nivel") == "Bairro":
            pb_val = item_copy.get("prefeitura_bairro") or item_copy.get("prefeituraBairro")
            if pb_val:
                pb_clean = normalizar_nome_prefeitura_bairro(pb_val)
                item_copy["prefeitura_bairro"] = pb_clean
                item_copy["prefeituraBairro"] = pb_clean
        ficha_local = fichas_por_id.get(str(o.get("id")))
        if ficha_local is None:
            cands_local = coletar_fichas_candidatas(o, fichas_por_chave, fichas_por_id)
            ficha_local = cands_local[0] if cands_local else None
        if ficha_local is not None:
            vigencia_local = ficha_local.get("vigencia") or {}
            item_copy["dtTerminoVigenciaAtualizado"] = vigencia_local.get("dataTerminoAtualizado")
            if "dtFimVigenciaOriginal" not in item_copy and vigencia_local.get("dataFimOriginal"):
                item_copy["dtFimVigenciaOriginal"] = vigencia_local.get("dataFimOriginal")
        else:
            item_copy.pop("dtTerminoVigenciaAtualizado", None)
        return item_copy

    obras_dir = output_path / "obras"
    fichas_por_chave, fichas_por_id = indexar_fichas_locais(obras_dir) if anterior_valida else ({}, {})
    persisted_refs_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}

    existing_obras: list[dict[str, Any]] = []
    if index_candidate is not None:
        try:
            with open(index_candidate, "r", encoding="utf-8") as f:
                existing_index = json.load(f)
            existing_obras = existing_index.get("obras", [])

            for o_exist in existing_obras:
                exist_id = o_exist.get("id")
                if exist_id in (None, ""):
                    continue
                for chave_cand in obter_chaves_candidatas_obra(o_exist):
                    persisted_refs_by_key.setdefault(chave_cand, []).append(o_exist)

            # Versões anteriores a esta coleta não registravam a procedência do grid.
            # Nesse caso, reconsultar os mandatos para recuperá-la antes do reuso.
            # Além disso, só reutiliza um mandato encerrado se ele já constar como
            # efetivamente consolidado nos metadados (mandatosDisponiveis) do índice anterior.
            existing_mandatos_meta = {
                str(m_meta).replace("–", "-").replace("—", "-").strip()
                for m_meta in ((existing_index.get("metadata") or {}).get("mandatosDisponiveis") or [])
                if str(m_meta).strip()
            }
            if not full_refresh and all(o.get("janelasGrid") for o in existing_obras):
                for m in mandatos_lista:
                    info = MANDATOS_MUNICIPAIS.get(m)
                    if info and info["fim"] < year and m in existing_mandatos_meta:
                        has_obras_mandato = any(m in o.get("mandatos", []) for o in existing_obras)
                        if has_obras_mandato:
                            closed_mandates_reused.add(m)

                if closed_mandates_reused:
                    mandatos_consultar = [m for m in mandatos_lista if m not in closed_mandates_reused]
                    reused_obras = [
                        _hidratar_obra_existente(o)
                        for o in existing_obras
                        if any(m in closed_mandates_reused for m in o.get("mandatos", []))
                    ]
                    raw_grid.extend(reused_obras)
        except (OSError, json.JSONDecodeError, TypeError, KeyError) as exc:
            warnings.warn(
                f"Falha ao ler índice incremental '{index_candidate}': {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            existing_obras = []
            persisted_refs_by_key.clear()
            raw_grid.clear()
            closed_mandates_reused.clear()
            mandatos_consultar = list(mandatos_lista)

    for chave_local, lista_fichas in fichas_por_chave.items():
        for ficha_local in lista_fichas:
            if ficha_local.get("id") not in (None, ""):
                persisted_refs_by_key.setdefault(chave_local, []).append(ficha_local)

    for m in mandatos_consultar:
        info = MANDATOS_MUNICIPAIS.get(m)
        if info:
            payload = {
                "dataInicio": info["data_inicio"],
                "dataFim": info["data_fim"],
                "filtros": [],
            }
            itens_mandato = consultar(transparencia.fetch_grid_detalhada,
                year=year,
                payload_customizado=payload,
            )
            janela = {"dataInicio": payload["dataInicio"], "dataFim": payload["dataFim"]}
            raw_grid.extend({**item, "janelasGrid": [janela]} for item in itens_mandato)
        else:
            raw_grid.extend(consultar(transparencia.fetch_grid_detalhada, year=year))

    if not raw_grid and not closed_mandates_reused:
        janela = {"dataInicio": f"{year}-01-01T03:00:00.000Z", "dataFim": f"{year}-12-31T03:00:00.000Z"}
        raw_grid = [{**item, "janelasGrid": [janela]} for item in consultar(transparencia.fetch_grid_detalhada, year=year)]

    # Deduplicação canônica por (cdUnidadeGestora, nuContratoSigef) e estabilização de IDs
    janelas_por_chave: dict[tuple[str, str], list[dict[str, str]]] = {}
    for item in ([*existing_obras, *raw_grid] if not full_refresh else raw_grid):
        janelas = janelas_por_chave.setdefault(obter_chave_canonica_obra(item), [])
        for janela in item.get("janelasGrid", []):
            if janela not in janelas:
                janelas.append(janela)
    grid_obras = deduplicar_obras(raw_grid)
    for obra in grid_obras:
        obra["janelasGrid"] = janelas_por_chave.get(obter_chave_canonica_obra(obra), [])
        id_estabilizado = False
        for chave_cand in obter_chaves_candidatas_obra(obra):
            for ref in persisted_refs_by_key.get(chave_cand, []):
                if cds_ug_compativeis(obra, ref):
                    obra["id"] = ref["id"]
                    id_estabilizado = True
                    break
            if id_estabilizado:
                break
        if obra.get("id") in (None, ""):
            ug_fb = str(obra.get("cdUnidadeGestora") or obra.get("sgOrgao") or "OBRA").strip()
            nu_fb = str(obra.get("nuContratoSigef") or obra.get("numeroContrato") or "SEM-NUM").strip()
            obra["id"] = f"{ug_fb}-{nu_fb}".replace("/", "-")

    # 2. Cálculo dos centróides dos Bairros Oficiais
    bairros_centroides = calcular_centroides_bairros(raw_bairros)

    # 3. Funil de Alocação Territorial com Cache Incremental
    cache_path = Path(cache_file) if cache_file is not None else (output_path / "geocoding_cache.json")
    if not anterior_valida and cache_path.exists():
        cache_path.unlink()
    cache = GeocodingCache(cache_file_path=cache_path)
    cache.reconciliar_entradas(raw_bairros, bairros_centroides)
    cache_hits = 0

    for obra in grid_obras:
        aloc = consultar(classificar_alocacao_territorial,
            obra=obra,
            bairros_geojson=raw_bairros,
            bairros_centroides=bairros_centroides,
            cache=cache,
        )
        if aloc.get("estagio") == "Cache":
            cache_hits += 1
        obra["nivel"] = aloc["nivel"]
        obra["bairro"] = aloc["bairro"]
        obra["prefeitura_bairro"] = aloc["prefeitura_bairro"]
        obra["latitude"] = aloc["latitude"]
        obra["longitude"] = aloc["longitude"]
        obra["estagioAlocacao"] = aloc["estagio"]
        obra["lastroCuradoria"] = aloc.get("lastro_curadoria")
        if aloc.get("cotas_lista_fechada"):
            obra["cotasListaFechada"] = aloc["cotas_lista_fechada"]
        else:
            obra.pop("cotasListaFechada", None)

    # 4. Estruturação base de Bairros Oficiais
    demografia_norm = {normalizar_nome(k): v for k, v in demografia_map.items()}
    bairros_base: list[dict[str, Any]] = []

    for feat in raw_bairros.get("features", []):
        props = feat.get("properties", {})
        nome = (props.get("NM_BAIRRO") or props.get("nome") or props.get("NOME_BAIRR") or "").strip()
        b_id = props.get("CD_BAIRRO") or props.get("OBJECTID") or props.get("id") or 0
        pb = (props.get("PREFEITURA_BAIRRO") or props.get("prefeitura_bairro") or "").strip()

        nome_norm = normalizar_nome(nome)
        demo = demografia_norm.get(nome_norm, {"populacao": 0, "indice_vulnerabilidade": 0.0})
        eh_zona_especial = is_zona_especial_nao_residencial(nome)
        eh_centralidade = not eh_zona_especial and is_centralidade_metropolitana(nome)

        bairros_base.append({
            "id": b_id,
            "nome": nome,
            "prefeitura_bairro": pb,
            "populacao": int(demo.get("populacao", 0)),
            "indice_vulnerabilidade": parse_float(demo.get("indice_vulnerabilidade", 0.0)),
            "is_zona_especial_nao_residencial": eh_zona_especial,
            "isZonaEspecialNaoResidencial": eh_zona_especial,
            "is_centralidade_metropolitana": eh_centralidade,
            "isCentralidadeMetropolitana": eh_centralidade,
            "pct_esgoto_inadequado": parse_float(demo.get("pct_esgoto_inadequado", 0.0)),
            "pct_agua_inadequada": parse_float(demo.get("pct_agua_inadequada", 0.0)),
            "pct_analfabetismo_15mais": parse_float(demo.get("pct_analfabetismo_15mais", 0.0)),
            "vulnerabilidade_estimada_contiguidade": bool(demo.get("vulnerabilidade_estimada_contiguidade", False)),
        })

    # 5. Estruturação base de Prefeituras-Bairro com agregação populacional
    pop_por_pb: dict[str, int] = {}
    for b in bairros_base:
        pb_norm = normalizar_nome(b.get("prefeitura_bairro", ""))
        pop_por_pb[pb_norm] = pop_por_pb.get(pb_norm, 0) + int(b.get("populacao", 0))

    prefeituras_base: list[dict[str, Any]] = []
    seen_pb: set[str] = set()
    for feat in raw_prefeituras.get("features", []):
        props = feat.get("properties", {})
        nome = (props.get("NM_PREFEITURA_BAIRRO") or props.get("nome") or props.get("NOMES") or "").strip()
        pb_id = props.get("CD_PREFEITURA_BAIRRO") or props.get("OBJECTID") or props.get("id") or 0
        norm = normalizar_nome(nome)
        if not norm or norm in seen_pb:
            continue
        seen_pb.add(norm)
        pop_total = pop_por_pb.get(norm, 0)

        prefeituras_base.append({
            "id": pb_id,
            "nome": nome,
            "populacao_total": pop_total,
        })

    # Classificação de Tema, Vocação e Semáforo da Obra antes da consolidação detalhada
    for obra in grid_obras:
        obra["tema"] = classificar_tema(obra)
        obra["vocacao"] = classificar_vocacao(obra)
        obra["semaforo"] = classificar_semaforo(obra, data_referencia=referencia_pagamentos)

    # 6. Detalhamento individual com reconciliação local e blindagem histórica
    obras_dir.mkdir(parents=True, exist_ok=True)
    detail_cache_hits = 0
    fichas_para_gravar: dict[str, dict[str, Any]] = {}
    limitacoes_conhecidas: set[str] = set()

    def _finalizar_ficha_obra(obra_atual: dict[str, Any], ficha_atual: dict[str, Any]) -> None:
        frentes = resolver_frentes_medicao(
            obra=obra_atual,
            bairros_geojson=raw_bairros,
            liquidacoes=ficha_atual.get("liquidacoes"),
            pagamentos=ficha_atual.get("pagamentos"),
        )
        if frentes:
            ficha_atual["frentesMedicao"] = frentes
        else:
            ficha_atual.pop("frentesMedicao", None)
        sincronizar_obra_com_ficha(obra_atual, ficha_atual)
        recalcular_semaforo_pos_ficha(
            obra_atual,
            ficha_atual,
            data_referencia=referencia_pagamentos,
        )
        fichas_para_gravar[str(obra_atual.get("id"))] = ficha_atual

    for obra in grid_obras:
        cd_ug = obra.get("cdUnidadeGestora") or obra.get("unidadeGestora") or obra.get("sgOrgao")
        nu_sigef = obra.get("nuContratoSigef") or obra.get("numeroContrato")
        obra_id = obra.get("id")

        candidatas_locais = coletar_fichas_candidatas(obra, fichas_por_chave, fichas_por_id)
        ficha_disco = fichas_por_id.get(str(obra_id)) or (candidatas_locais[0] if candidatas_locais else None)
        if _contrato_elegivel_pagamentos_consolidados(
            obra=obra,
            ficha_disco=ficha_disco,
            referencia_pagamentos=referencia_pagamentos,
            full_refresh=full_refresh,
            anterior_valida=anterior_valida,
        ):
            detail_cache_hits += 1
            cands_consolidacao = [ficha_disco, *(c for c in candidatas_locais if c is not ficha_disco)]
            ficha_obra = mesclar_fichas_obra(obra, cands_consolidacao)
            apuracao_consolidada = copy.deepcopy(ficha_obra["apuracaoPagamentos"])
            apuracao_consolidada["pagamentosConsolidados"] = True
            ficha_obra["apuracaoPagamentos"] = apuracao_consolidada
            limitacoes_conhecidas.update(apuracao_consolidada.get("limitacoesConhecidas") or [])
            _finalizar_ficha_obra(obra, ficha_obra)
            continue

        identidade_contrato = [str(cd_ug), str(nu_sigef)]
        chave_recuperacao = chave_contrato(*identidade_contrato)
        salvo = estado["contratos"].get(chave_recuperacao) if estado is not None else None
        if salvo is not None:
            if "identidade" not in salvo or "tentativa_original" not in salvo:
                # Checkpoints do formato local antigo não comprovam a identidade da tentativa.
                salvo = None
            elif (salvo["identidade"] != identidade_contrato
                    or salvo["tentativa_original"] != estado.get("tentativa_original")):
                raise ValueError(f"Checkpoint não corresponde ao contrato ou tentativa selecionada: {obra_id}")
        if salvo is None and estado is not None:
            estado["contrato_em_andamento"] = identidade_contrato
            salvar_estado()
        if salvo is not None:
            metricas_recuperacao["contratos_reaproveitados"].append(identidade_contrato)
            dados = dict(salvo["consulta"])
            if dados.get("lotes") is not None:
                dados["lotes"] = [LotePagamentos(**lote) for lote in dados["lotes"]]
            resultado_pagamentos = ConsultaPagamentos(**dados)
        elif consulta_pagamentos is None:
            resultado_pagamentos = consultar(coletar_pagamentos, cd_ug, nu_sigef, referencia_pagamentos, obra.get("janelasGrid"))
        else:
            resultado_pagamentos = consultar(consulta_pagamentos, cd_ug, nu_sigef, referencia_pagamentos)
        if (not isinstance(resultado_pagamentos, ConsultaPagamentos)
                or resultado_pagamentos.concluida is not True or resultado_pagamentos.validada is not True
                or resultado_pagamentos.data_referencia != referencia_pagamentos
                or not isinstance(resultado_pagamentos.registros, list)
                or not all(isinstance(item, dict) for item in resultado_pagamentos.registros)):
            raise ValueError(f"Consulta obrigatória de pagamentos incompleta: {obra_id}")
        if (interromper_apos_checkpoints is not None and estado is not None and salvo is None
                and len(estado["contratos"]) >= interromper_apos_checkpoints):
            raise InterrupcaoEnsaiada(
                f"Interrupção ensaiada após {len(estado['contratos'])} checkpoints concluídos; "
                f"contrato em andamento: {identidade_contrato}"
            )
        if not isinstance(resultado_pagamentos.limitacoes_conhecidas, list) or not all(
            isinstance(item, str) and item for item in resultado_pagamentos.limitacoes_conhecidas
        ):
            raise ValueError(f"Limitações de pagamentos inválidas: {obra_id}")
        limitacoes_conhecidas.update(resultado_pagamentos.limitacoes_conhecidas)
        pagamentos_raw, repeticoes_coleta = incorporar_lotes_pagamentos(resultado_pagamentos)
        obra["janelaPagamentos"] = resultado_pagamentos.janela

        reaproveitar_detalhes = False

        if not full_refresh and ficha_disco is not None:
            vl_atua = parse_float(obra.get("vlAtualizado") or obra.get("valorContratualVigente") or obra.get("vlOriginal") or 0.0)
            perc_exec = parse_float(obra.get("percentualExecutado") or 0.0)
            ds_situacao = str(obra.get("dsSituacao") or obra.get("situacao") or "").strip()
            dt_termino = normalizar_data_chave(
                obra.get("dtTerminoVigenciaAtualizado") or resolver_datas_vigencia(obra)[1] or ""
            )

            p_funil = ficha_disco.get("funilFinanceiro", {})
            p_vigencia = ficha_disco.get("vigencia", {})
            p_vl_atua = parse_float(p_funil.get("valorContratualVigente") or ficha_disco.get("vlAtualizado") or 0.0)
            p_perc_exec = parse_float(p_funil.get("percentualExecutado") or ficha_disco.get("percentualExecutado") or 0.0)
            p_ds_situacao = str(ficha_disco.get("situacao") or ficha_disco.get("dsSituacao") or "").strip()
            p_dt_termino = normalizar_data_chave(
                p_vigencia.get("dataTerminoAtualizado") or ficha_disco.get("dtTerminoVigenciaAtualizado") or ""
            )

            if (
                vl_atua == p_vl_atua
                and perc_exec == p_perc_exec
                and ds_situacao == p_ds_situacao
                and dt_termino == p_dt_termino
            ):
                reaproveitar_detalhes = True

        if salvo is not None:
            detail_cache_hits += 1
            ficha_obra = mesclar_fichas_obra(obra, [salvo["ficha"]])
        elif reaproveitar_detalhes and candidatas_locais:
            detail_cache_hits += 1
            ficha_obra = mesclar_fichas_obra(obra, candidatas_locais)
        else:
            detalhe = consultar(transparencia.fetch_detalhes_obra, cd_ug, nu_sigef, year=year, obra_base=obra)
            aditivos_raw = consultar(transparencia.fetch_aditivos_obra, cd_ug, nu_sigef, year=year)
            dotacoes_raw = consultar(transparencia.fetch_dotacao_obra, cd_ug, nu_sigef, year=year)
            empenhos_raw = consultar(transparencia.fetch_empenhos_obra, cd_ug, nu_sigef, year=year)
            liquidacoes_raw = consultar(transparencia.fetch_liquidacoes_obra, cd_ug, nu_sigef, year=year)

            ficha_nova = construir_ficha_obra(
                obra=obra,
                detalhe=detalhe,
                aditivos_raw=aditivos_raw,
                dotacoes_raw=dotacoes_raw,
                empenhos_raw=empenhos_raw,
                liquidacoes_raw=liquidacoes_raw,
                pagamentos_raw=pagamentos_raw,
                concentracao_map=None,
                year=year,
            )
            ficha_obra = (
                mesclar_fichas_obra(obra, [ficha_nova, *candidatas_locais])
                if candidatas_locais
                else ficha_nova
            )

        ficha_obra["pagamentos"] = pagamentos_raw
        ficha_obra["repeticoesColeta"] = repeticoes_coleta
        ficha_obra["janelaPagamentos"] = resultado_pagamentos.janela
        ficha_obra["consultaPagamentosConcluida"] = True
        valores = [valor_informado_pagamento(p) for p in pagamentos_raw]
        valores = [valor for valor in valores if valor is not None and valor != ""]
        valores_decimais = []
        for valor in valores:
            texto = str(valor).strip().removeprefix("R$ ").strip()
            if "," in texto:
                texto = texto.replace(".", "").replace(",", ".")
            try:
                numero = Decimal(texto)
            except InvalidOperation as exc:
                raise ValueError(f"Valor de pagamento inválido: {obra_id}") from exc
            if not numero.is_finite():
                raise ValueError(f"Valor de pagamento inválido: {obra_id}")
            valores_decimais.append(numero)
        ficha_obra.setdefault("funilFinanceiro", {})["valorPago"] = (
            float(sum(valores_decimais)) if valores_decimais else (0.0 if not pagamentos_raw else None)
        )
        ficha_obra["apuracaoPagamentos"] = {
            "registrosSemValor": len(pagamentos_raw) - len(valores_decimais),
            "limitacoesConhecidas": list(resultado_pagamentos.limitacoes_conhecidas),
            "dataReferencia": referencia_pagamentos,
            "pagamentosConsolidados": False,
            "situacao": "sem_registros" if not pagamentos_raw else (
                "saldo_registrado" if valores_decimais else "indisponivel"
            ),
        }
        if resultado_pagamentos.periodo_disponivel is not None:
            periodo = resultado_pagamentos.periodo_disponivel
            if not _validar_periodo_disponivel(periodo):
                raise ValueError(f"Período disponível inválido: {obra_id}")
            ficha_obra["apuracaoPagamentos"]["periodoDisponivel"] = copy.deepcopy(periodo)

        _finalizar_ficha_obra(obra, ficha_obra)
        if estado is not None and salvo is None:
            estado["contratos"][chave_recuperacao] = {
                "identidade": identidade_contrato,
                "tentativa_original": estado["tentativa_original"],
                "consulta": asdict(resultado_pagamentos),
                "ficha": ficha_obra,
            }
            estado["contrato_em_andamento"] = None
            salvar_estado()

    if estado is not None and estado.get("contrato_em_andamento") is not None:
        raise ValueError("O contrato interrompido não foi retomado na carteira atual")

    # 7. Unificação de Empreiteiras, gravação das fichas finais e expurgo de órfãos
    concentracao_map, _ = finalizar_acervo_obras(grid_obras, fichas_para_gravar, obras_dir)

    # 8. Agregações e Rollup Territorial (Camada A) com dados financeiros e cadastrais sincronizados
    bairros_rollup, prefeituras_rollup, opacidade = calcular_rollup_territorial(
        bairros_resumo=bairros_base,
        prefeituras_resumo=prefeituras_base,
        obras_alocadas=grid_obras,
    )

    # 9. Geração das malhas GeoJSON enriquecidas
    bairros_geo_path = output_path / "geo" / "bairros.geojson"
    generate_bairros_geojson(
        raw_bairros_geojson=raw_bairros,
        bairros_resumo=bairros_rollup,
        output_path=bairros_geo_path,
    )

    pb_geo_path = output_path / "geo" / "prefeituras_bairro.geojson"
    generate_prefeituras_geojson(
        raw_pb_geojson=raw_prefeituras,
        prefeituras_resumo=prefeituras_rollup,
        output_path=pb_geo_path,
    )

    # 10. Cálculo dos KPIs globais enriquecidos com carteira real e transparência opaca
    populacao_cidade = sum(int(b.get("populacao", 0)) for b in bairros_rollup)
    kpis_globais = kpis.calcular_kpis_globais(
        totalizador_transparencia=totalizador,
        obras_detalhadas=grid_obras,
        populacao_total_cidade=populacao_cidade,
        indicador_opacidade=opacidade,
    )

    # 11. Geração do índice anual estático com concentração de empreiteiras e mandatos
    index_file_path = output_path / f"index_{year}.json"
    generate_index_json(
        kpis_globais=kpis_globais,
        bairros_resumo=bairros_rollup,
        prefeituras_resumo=prefeituras_rollup,
        obras_detalhadas=grid_obras,
        year=year,
        output_path=index_file_path,
        concentracao_empreiteiras=concentracao_map,
        mandatos_disponiveis=mandatos_lista,
    )

    # Cria aliases index_2025.json e index.json sempre sincronizados
    escrever_indices_alias(index_file_path, output_path)

    return {
        "success": True,
        "output_dir": str(output_path),
        "cache_file": str(cache_path),
        "cache_hits": cache_hits,
        "detail_cache_hits": detail_cache_hits,
        "full_refresh": full_refresh,
        "ano": year,
        "total_bairros": len(bairros_rollup),
        "total_prefeituras": len(prefeituras_rollup),
        "total_obras": len(grid_obras),
        "inicio_consultas": inicio_consultas,
        "fim_consultas": fim_consultas,
        "limitacoes_conhecidas": sorted(limitacoes_conhecidas),
    }

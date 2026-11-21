"""Módulo de integração com a API da Transparência da Prefeitura de Salvador.

Responsável por consultar os endpoints de Obras Públicas vigentes no município,
incluindo totalizadores globais e a listagem detalhada de contratos.
"""

import json
import logging
import ssl
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPException
from typing import Any, Final

from etl.config import TRANSPARENCIA_API_BASE

PAGE_SIZE_TRANSPARENCIA: Final[int] = 10
_INTERVALO_MINIMO: Final[float] = 0.5
_INTERVALO_TRANSITORIO: Final[float] = 2.0
_RESPOSTAS_PARA_REDUZIR_INTERVALO: Final[int] = 20
_CODIGOS_TRANSITORIOS = (408, 429, 500, 502, 503, 504)
_lock_requisicoes = threading.Lock()
_proxima_requisicao = 0.0
_intervalo_requisicoes = _INTERVALO_MINIMO
_respostas_estaveis = 0
logger = logging.getLogger(__name__)


def _erro_transitorio(erro: Exception) -> bool:
    if isinstance(erro, urllib.error.HTTPError):
        return erro.code in _CODIGOS_TRANSITORIOS
    if isinstance(erro, ssl.SSLError):
        return "timed out" in str(erro).lower()
    return isinstance(erro, (urllib.error.URLError, TimeoutError, ConnectionError))


def _segundos_retry_after(erro: Exception) -> float:
    if not isinstance(erro, urllib.error.HTTPError) or not erro.headers:
        return 0.0
    valor = erro.headers.get("Retry-After")
    if not valor:
        return 0.0
    try:
        return max(0.0, float(int(valor)))
    except (ValueError, OverflowError):
        try:
            instante = parsedate_to_datetime(valor)
            return max(0.0, (instante - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return 0.0


def _bloqueio_explicito(erro: Exception) -> bool:
    if not isinstance(erro, urllib.error.HTTPError) or erro.code not in _CODIGOS_TRANSITORIOS:
        return False
    try:
        with erro:
            return b"web page blocked" in erro.read(4096).lower()
    except (OSError, HTTPException):
        return False


def _validar_paginacao(paginacao: Any, pagina: int, quantidade: int, anterior: tuple[int, int, int] | None, origem: str) -> tuple[int, int, int]:
    if not isinstance(paginacao, dict):
        raise ValueError(f"Metadados de paginacao ausentes de {origem}")
    total = paginacao.get("total", paginacao.get("totalRegistros"))
    paginas = paginacao.get("paginas", paginacao.get("totalPaginas"))
    atual = paginacao.get("paginaAtual")
    tamanho = paginacao.get("tamanho", paginacao.get("tamanhoPagina", PAGE_SIZE_TRANSPARENCIA))
    total_pagina = paginacao.get("totalPagina", quantidade)
    if (any(type(n) is not int for n in (total, paginas, atual, tamanho, total_pagina))
            or total < 0 or paginas < 0 or tamanho <= 0 or atual != pagina
            or total_pagina != quantidade or quantidade > tamanho
            or (paginas == 0 and (pagina != 1 or total != 0 or quantidade != 0))
            or (paginas > 0 and pagina > paginas)):
        raise ValueError(f"Metadados de paginacao inválidos de {origem}")
    estado = (total, paginas, tamanho)
    if anterior is not None and anterior != estado:
        raise ValueError(f"Metadados de paginacao inconsistentes de {origem}")
    return estado


def _criar_payload_filtro_ano(year: int) -> dict[str, Any]:
    """Constrói o payload padrão de filtro anual para as requisições à Transparência de Salvador.

    Sumário:
        Centraliza a montagem dos parâmetros de data de início e fim para evitar duplicação de código.

    Descrição Estendida:
        Formata o intervalo anual no padrão ISO 8601 UTC (de 01/01 a 31/12) esperado
        pela API do Portal da Transparência de Salvador.

    Argumentos:
        year: Ano civil de referência (ex: 2025).

    Retornos:
        Dicionário com chaves 'dataInicio', 'dataFim' e 'filtros'.

    Erros:
        Não lança exceções.
    """
    return {
        "dataInicio": f"{year}-01-01T03:00:00.000Z",
        "dataFim": f"{year}-12-31T03:00:00.000Z",
        "filtros": [],
    }


def _post_transparencia(endpoint: str, payload: dict[str, Any], timeout: int = 15, max_bytes: int | None = None) -> Any:
    """Envia uma requisição POST JSON para a API da Transparência de Salvador.

    Sumário:
        Executa chamada POST com SSL configurado e headers exigidos pelo portal.

    Descrição Estendida:
        O portal da Transparência de Salvador requer headers específicos de User-Agent,
        Origin e Referer para responder às chamadas JSON dos endpoints de obras.

    Argumentos:
        endpoint: Caminho relativo do endpoint (ex: '/obraspublicas/totalizador').
        payload: Dicionário contendo os filtros da consulta ('dataInicio', 'dataFim', 'filtros').
        timeout: Limite de tempo em segundos para resposta da API.

    Retornos:
        Dicionário com os dados JSON retornados pela API.

    Erros:
        Lança urllib.error.URLError ou RuntimeError em caso de falha de conexão.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    url = f"{TRANSPARENCIA_API_BASE}{endpoint}"
    data_bytes = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SalvadorObrasETL/1.0",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://www.transparencia.salvador.ba.gov.br",
            "Referer": "https://www.transparencia.salvador.ba.gov.br/",
        },
        method="POST",
    )

    global _proxima_requisicao, _intervalo_requisicoes, _respostas_estaveis
    with _lock_requisicoes:
        espera = _proxima_requisicao - time.monotonic()
        if espera > 0:
            time.sleep(espera)
        espera_servidor = 0.0
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                if max_bytes is None:
                    body_bytes = resp.read()
                else:
                    body_bytes = resp.read(max_bytes + 1)
                    if len(body_bytes) > max_bytes:
                        raise ValueError("Limite de tamanho da resposta atingido")
                    tamanho = resp.headers.get("Content-Length")
                    if tamanho is not None and tamanho != str(len(body_bytes)):
                        raise ValueError("Tamanho da resposta divergente")
            body = body_bytes.decode("utf-8")
            resposta = json.loads(body) if body else {}
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError) as erro:
            if _bloqueio_explicito(erro):
                raise RuntimeError(f"Bloqueio explícito do Portal da Transparência em {endpoint}") from erro
            if _erro_transitorio(erro):
                _intervalo_requisicoes = _INTERVALO_TRANSITORIO
                _respostas_estaveis = 0
                espera_servidor = _segundos_retry_after(erro)
                logger.info("Portal da Transparência: falha transitória em %s. Pausa de pelo menos %.1f s.",
                            endpoint, max(_intervalo_requisicoes, espera_servidor))
            raise
        else:
            if _intervalo_requisicoes > _INTERVALO_MINIMO:
                _respostas_estaveis += 1
                if _respostas_estaveis >= _RESPOSTAS_PARA_REDUZIR_INTERVALO:
                    _intervalo_requisicoes = max(_INTERVALO_MINIMO, _intervalo_requisicoes / 2)
                    _respostas_estaveis = 0
                    logger.info("Portal da Transparência: pausa reduzida para %.1f s.", _intervalo_requisicoes)
            return resposta
        finally:
            _proxima_requisicao = time.monotonic() + max(_intervalo_requisicoes, espera_servidor)


def consultar_com_tentativas(endpoint: str, payload: dict[str, Any], **opcoes: Any) -> Any:
    """Repete falhas transitórias de transporte com esperas de 10 e 30 segundos."""
    for tentativa in range(3):
        try:
            return _post_transparencia(endpoint, payload, **opcoes)
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError) as erro:
            if not _erro_transitorio(erro) or tentativa == 2:
                raise
            time.sleep(max((10, 30)[tentativa], _segundos_retry_after(erro)))
    raise AssertionError("Tentativas esgotadas")


def fetch_totalizador(year: int = 2025) -> dict[str, Any]:
    """Obtém o totalizador de obras públicas do município de Salvador para o ano de referência.

    Sumário:
        Consulta `/obraspublicas/totalizador` para o intervalo do ano informado.

    Descrição Estendida:
        Recupera os totais agregados de quantidade de obras, valor financeiro contratual,
        empenhos, liquidações e pagamentos acumulados no exercício.

    Argumentos:
        year: Ano de referência da pesquisa (ex: 2025).

    Retornos:
        Dicionário com os totais de obras, empenhado, liquidado e pago.

    Erros:
        Propaga falhas da consulta.
    """
    payload = _criar_payload_filtro_ano(year)
    resposta = consultar_com_tentativas("/obraspublicas/totalizador", payload)
    if not isinstance(resposta, dict) or not resposta or "error" in resposta:
        raise ValueError("Resposta inválida do totalizador de obras")
    return resposta


def fetch_grid_detalhada(
    year: int = 2025,
    payload_customizado: dict[str, Any] | None = None,
    max_paginas: int = 100,
) -> list[dict[str, Any]]:
    """Obtém os contratos detalhados de obras públicas vigentes para o período consultado com paginação completa.

    Sumário:
        Consulta `/obraspublicas/gridDetalhada?pagina=N` iterando por todas as páginas disponíveis.

    Descrição Estendida:
        Recupera a lista de contratos de engenharia com informações de número SIGEF, objeto,
        valores originais e atualizados, percentual de medição executado e razão social do credor.
        Itera pelas páginas de resultados até esgotar os dados ou atingir o total de páginas
        informado pelo portal. Falhas interrompem a atualização.

    Argumentos:
        year: Ano de referência da pesquisa (padrão: 2025).
        payload_customizado: Dicionário opcional com intervalo de datas personalizado.
        max_paginas: Limite de salvaguarda de páginas a consultar.

    Retornos:
        Lista de dicionários contendo os contratos de obras públicas.

    Erros:
        Propaga falhas da consulta ou erro quando a paginação não termina.
    """
    payload = payload_customizado or _criar_payload_filtro_ano(year)
    registros: list[dict[str, Any]] = []
    estado_paginacao: tuple[int, int, int] | None = None

    for pagina in range(1, max_paginas + 1):
        url = f"/obraspublicas/gridDetalhada?pagina={pagina}"
        resp = consultar_com_tentativas(url, payload)
        if not isinstance(resp, dict) or not isinstance(resp.get("dados"), list):
            raise ValueError("Resposta inválida do grid de obras")
        itens = resp["dados"]
        estado_paginacao = _validar_paginacao(resp.get("paginacao"), pagina, len(itens), estado_paginacao, "grid de obras")
        _, total_paginas, _ = estado_paginacao
        if not itens:
            if pagina < total_paginas:
                raise ValueError("Grid de obras terminou antes da última página")
            break

        registros.extend(itens)
        if pagina >= total_paginas:
            break
    else:
        raise RuntimeError("Limite de páginas do grid atingido antes da conclusão")

    if estado_paginacao is None or len(registros) != estado_paginacao[0]:
        raise ValueError("Grid de obras incompleto")
    return registros


def _criar_payload_contrato(cd_unidade_gestora: Any, nu_contrato_sigef: Any, year: int = 2025) -> dict[str, Any]:
    """Cria o payload padrão de filtro por contrato para a API da Transparência de Salvador.

    Sumário:
        Monta o dicionário com o intervalo do exercício e atributos de Unidade Gestora e Contrato SIGEF.

    Descrição Estendida:
        Constrói o payload JSON enviado aos endpoints detalhados (/detalhamentoObrasPublicas,
        /aditivo, /dotacao, /empenhoRelacionado, /liquidacaoRelacionado, /pagamentoRelacionado).

    Argumentos:
        cd_unidade_gestora: Código numérico da Unidade Gestora municipal (ex: 2401).
        nu_contrato_sigef: String com o número do contrato no SIGEF (ex: '001/2024').
        year: Ano de referência da consulta (padrão: 2025).

    Retornos:
        Dicionário formatado com chaves 'dataInicio', 'dataFim' e 'filtros'.

    Erros:
        Não lança exceções.
    """
    return {
        "dataInicio": f"{year}-01-01T03:00:00.000Z",
        "dataFim": f"{year}-12-31T03:00:00.000Z",
        "filtros": [
            {"atributo": "CDUNIDADEGESTORA", "valor": cd_unidade_gestora},
            {"atributo": "NUCONTRATOSIGEF", "valor": nu_contrato_sigef},
        ],
    }


def _fetch_lista_paginada(
    endpoint: str,
    cd_unidade_gestora: Any,
    nu_contrato_sigef: Any,
    year: int = 2025,
    max_paginas: int = 100,
) -> list[dict[str, Any]]:
    """Executa requisições paginadas para endpoints de listas relacionadas a uma obra.

    Sumário:
        Itera pelas páginas de um endpoint da Transparência acumulando os registros retornados.

    Descrição Estendida:
        Realiza chamadas POST com incremento de `pagina=1, 2, ...` até esgotar os registros
        ou atingir `max_paginas`, tratando respostas no formato de dicionário paginado (`dados`)
        ou lista direta.

    Argumentos:
        endpoint: Caminho base do endpoint (ex: '/obraspublicas/aditivo').
        cd_unidade_gestora: Código da unidade gestora da obra.
        nu_contrato_sigef: Número do contrato SIGEF.
        year: Ano de referência da consulta.
        max_paginas: Limite máximo de páginas a consultar por contrato.

    Retornos:
        Lista com todos os dicionários de registros acumulados.

    Erros:
        Propaga falhas e rejeita respostas inválidas ou incompletas.
    """
    payload = _criar_payload_contrato(cd_unidade_gestora, nu_contrato_sigef, year)
    registros: list[dict[str, Any]] = []
    estado_paginacao: tuple[int, int, int] | None = None

    for pagina in range(1, max_paginas + 1):
        url = f"{endpoint}?pagina={pagina}"
        resp = consultar_com_tentativas(url, payload)
        if not isinstance(resp, dict) or not isinstance(resp.get("dados"), list):
            raise ValueError(f"Resposta inválida de {endpoint}")
        itens = resp["dados"]
        estado_paginacao = _validar_paginacao(resp.get("paginacao"), pagina, len(itens), estado_paginacao, endpoint)
        _, total_paginas, _ = estado_paginacao
        registros.extend(itens)
        if not itens and pagina < total_paginas:
            raise ValueError(f"Paginação incompleta de {endpoint}")
        if pagina >= total_paginas:
            break
    else:
        raise RuntimeError(f"Limite de páginas atingido em {endpoint}")

    if estado_paginacao is None or len(registros) != estado_paginacao[0]:
        raise ValueError(f"Lista incompleta de {endpoint}")
    return registros


def fetch_detalhes_obra(
    cd_unidade_gestora: Any,
    nu_contrato_sigef: Any,
    year: int = 2025,
    obra_base: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Obtém os detalhes cadastrais do contrato da obra pública (/obraspublicas/detalhamentoObrasPublicas).

    Sumário:
        Consulta os dados contratuais aprofundados (CNPJ do credor, edição do DOM, prazos e vigência).

    Descrição Estendida:
        Recupera as informações detalhadas do contrato na API da Transparência de Salvador.

    Argumentos:
        cd_unidade_gestora: Código da unidade gestora municipal.
        nu_contrato_sigef: Número do contrato no SIGEF.
        year: Ano de referência da apuração.
        obra_base: Dicionário preliminar da obra oriundo do grid.

    Retornos:
        Dicionário com os atributos detalhados do contrato.

    Erros:
        Propaga falhas de consulta e rejeita respostas inválidas.
    """
    payload = _criar_payload_contrato(cd_unidade_gestora, nu_contrato_sigef, year)
    resp = consultar_com_tentativas("/obraspublicas/detalhamentoObrasPublicas", payload)
    if isinstance(resp, dict) and "dados" in resp and isinstance(resp["dados"], dict):
        return resp["dados"]
    if isinstance(resp, dict) and resp and "dados" not in resp:
        return resp
    raise ValueError("Resposta inválida do detalhamento de obra")


def fetch_aditivos_obra(
    cd_unidade_gestora: Any,
    nu_contrato_sigef: Any,
    year: int = 2025,
) -> list[dict[str, Any]]:
    """Obtém a lista de termos aditivos da obra pública (/obraspublicas/aditivo).

    Sumário:
        Consulta termos aditivos de prazo e valor vigentes para a obra informada.

    Descrição Estendida:
        Extrai o histórico de alterações contratuais publicadas no DOM.

    Argumentos:
        cd_unidade_gestora: Código da unidade gestora da obra.
        nu_contrato_sigef: Número do contrato SIGEF.
        year: Ano de referência da pesquisa.

    Retornos:
        Lista de termos aditivos contendo número, tipo, objeto, datas, DOM e valor.

    Erros:
        Propaga falhas de consulta e rejeita respostas inválidas.
    """
    return _fetch_lista_paginada("/obraspublicas/aditivo", cd_unidade_gestora, nu_contrato_sigef, year)


def fetch_dotacao_obra(
    cd_unidade_gestora: Any,
    nu_contrato_sigef: Any,
    year: int = 2025,
) -> list[dict[str, Any]]:
    """Obtém a dotação orçamentária e fontes de recurso da obra pública (/obraspublicas/dotacao).

    Sumário:
        Identifica as fontes de recursos e subações orçamentárias que financiam o contrato.

    Descrição Estendida:
        Consulta os dados de dotação orçamentária na API da Transparência de Salvador.

    Argumentos:
        cd_unidade_gestora: Código da unidade gestora da obra.
        nu_contrato_sigef: Número do contrato SIGEF.
        year: Ano de referência da pesquisa.

    Retornos:
        Lista de dicionários com subação, fonte de recurso e classificação contábil.

    Erros:
        Propaga falhas de consulta e rejeita respostas inválidas.
    """
    return _fetch_lista_paginada("/obraspublicas/dotacao", cd_unidade_gestora, nu_contrato_sigef, year)


def fetch_empenhos_obra(
    cd_unidade_gestora: Any,
    nu_contrato_sigef: Any,
    year: int = 2025,
) -> list[dict[str, Any]]:
    """Obtém os empenhos orçamentários relacionados à obra pública (/obraspublicas/empenhoRelacionado).

    Sumário:
        Consulta as notas de empenho emitidas para a obra no exercício.

    Descrição Estendida:
        Recupera as reservas orçamentárias registradas no sistema contábil municipal.

    Argumentos:
        cd_unidade_gestora: Código da unidade gestora da obra.
        nu_contrato_sigef: Número do contrato SIGEF.
        year: Ano de referência.

    Retornos:
        Lista de dicionários representando as notas de empenho.

    Erros:
        Não lança exceções.
    """
    return _fetch_lista_paginada("/obraspublicas/empenhoRelacionado", cd_unidade_gestora, nu_contrato_sigef, year)


def fetch_liquidacoes_obra(
    cd_unidade_gestora: Any,
    nu_contrato_sigef: Any,
    year: int = 2025,
) -> list[dict[str, Any]]:
    """Obtém as liquidações contábeis relacionadas à obra pública (/obraspublicas/liquidacaoRelacionado).

    Sumário:
        Consulta as notas de liquidação que atestam a medição de serviços da obra.

    Descrição Estendida:
        Recupera os registros de liquidação de despesa emitidos após medição técnica dos serviços executados.

    Argumentos:
        cd_unidade_gestora: Código da unidade gestora da obra.
        nu_contrato_sigef: Número do contrato SIGEF.
        year: Ano de referência.

    Retornos:
        Lista de dicionários representando as notas de liquidação.

    Erros:
        Não lança exceções.
    """
    return _fetch_lista_paginada("/obraspublicas/liquidacaoRelacionado", cd_unidade_gestora, nu_contrato_sigef, year)


def fetch_pagamentos_obra(
    cd_unidade_gestora: Any,
    nu_contrato_sigef: Any,
    year: int = 2025,
) -> list[dict[str, Any]]:
    """Obtém as ordens bancárias e pagamentos da obra pública (/obraspublicas/pagamentoRelacionado).

    Sumário:
        Consulta os repasses financeiros efetivamente transferidos à construtora.

    Descrição Estendida:
        Recupera o histórico de ordens bancárias pagas à empresa credora do contrato.

    Argumentos:
        cd_unidade_gestora: Código da unidade gestora da obra.
        nu_contrato_sigef: Número do contrato SIGEF.
        year: Ano de referência.

    Retornos:
        Lista de dicionários representando os pagamentos efetuados.

    Erros:
        Não lança exceções.
    """
    return _fetch_lista_paginada("/obraspublicas/pagamentoRelacionado", cd_unidade_gestora, nu_contrato_sigef, year)



"""Módulo de integração com a API da Transparência da Prefeitura de Salvador.

Responsável por consultar os endpoints de Obras Públicas vigentes no município,
incluindo totalizadores globais e a listagem detalhada de contratos, com suporte a fallback offline.
"""

import json
import ssl
import urllib.error
import urllib.request
from typing import Any

from etl.config import TRANSPARENCIA_API_BASE


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


def _post_transparencia(endpoint: str, payload: dict[str, Any], timeout: int = 15) -> dict[str, Any]:
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

    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return json.loads(body) if body else {}


def fetch_totalizador(year: int = 2025) -> dict[str, Any]:
    """Obtém o totalizador de obras públicas do município de Salvador para o ano de referência.

    Sumário:
        Consulta `/obraspublicas/totalizador` para o intervalo do ano informado.

    Descrição Estendida:
        Recupera os totais agregados de quantidade de obras, valor financeiro contratual,
        empenhos, liquidações e pagamentos acumulados no exercício. Caso ocorra indisponibilidade
        de rede externa, aciona a base de referência em `etl.reference`.

    Argumentos:
        year: Ano de referência da pesquisa (ex: 2025).

    Retornos:
        Dicionário com os totais de obras, empenhado, liquidado e pago.

    Erros:
        Retorna fixture de referência caso a rede externa esteja inacessível.
    """
    payload = _criar_payload_filtro_ano(year)
    try:
        return _post_transparencia("/obraspublicas/totalizador", payload)
    except Exception:
        from etl.reference.sample_data import SAMPLE_TRANSPARENCIA_TOTALIZADOR
        return SAMPLE_TRANSPARENCIA_TOTALIZADOR


def fetch_grid_detalhada(year: int = 2025) -> list[dict[str, Any]]:
    """Obtém os contratos detalhados de obras públicas vigentes para o ano de referência.

    Sumário:
        Consulta `/obraspublicas/gridDetalhada?pagina=1` para extrair a lista de contratos.

    Descrição Estendida:
        Recupera a lista de contratos de engenharia com informações de número SIGEF, objeto,
        valores originais e atualizados, percentual de medição executado e razão social do credor.
        Caso ocorra falha de rede, aciona a base de referência em `etl.reference`.

    Argumentos:
        year: Ano de referência da pesquisa (ex: 2025).

    Retornos:
        Lista de dicionários contendo os contratos de obras públicas.

    Erros:
        Retorna fixture de referência caso a rede externa esteja inacessível.
    """
    payload = _criar_payload_filtro_ano(year)
    try:
        resp = _post_transparencia("/obraspublicas/gridDetalhada?pagina=1", payload)
        if isinstance(resp, dict) and "dados" in resp:
            return resp["dados"]
        if isinstance(resp, list):
            return resp
        return []
    except Exception:
        from etl.reference.sample_data import SAMPLE_TRANSPARENCIA_GRID
        return SAMPLE_TRANSPARENCIA_GRID

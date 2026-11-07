"""Módulo de integração com a API da Transparência da Prefeitura de Salvador.

Responsável por consultar os endpoints de Obras Públicas vigentes no município,
incluindo totalizadores globais e a listagem detalhada de contratos, com suporte a fallback offline.
"""

import json
import ssl
import urllib.error
import urllib.request
from typing import Any, Final

from etl.config import TRANSPARENCIA_API_BASE

PAGE_SIZE_TRANSPARENCIA: Final[int] = 10


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
        informado pelo portal. Caso ocorra falha de rede na primeira página, aciona a base de
        referência em `etl.reference`.

    Argumentos:
        year: Ano de referência da pesquisa (padrão: 2025).
        payload_customizado: Dicionário opcional com intervalo de datas personalizado.
        max_paginas: Limite de salvaguarda de páginas a consultar.

    Retornos:
        Lista de dicionários contendo os contratos de obras públicas.

    Erros:
        Retorna fixture de referência caso a rede externa esteja inacessível na primeira página.
    """
    payload = payload_customizado or _criar_payload_filtro_ano(year)
    registros: list[dict[str, Any]] = []

    for pagina in range(1, max_paginas + 1):
        url = f"/obraspublicas/gridDetalhada?pagina={pagina}"
        try:
            resp = _post_transparencia(url, payload)
            itens: list[dict[str, Any]] = []
            total_paginas: int | None = None

            if isinstance(resp, dict):
                if "dados" in resp and isinstance(resp["dados"], list):
                    itens = resp["dados"]
                elif "dados" in resp and isinstance(resp["dados"], dict):
                    itens = [resp["dados"]]
                paginacao = resp.get("paginacao")
                if isinstance(paginacao, dict):
                    total_paginas = paginacao.get("totalPaginas") or paginacao.get("paginas")
            elif isinstance(resp, list):
                itens = resp

            if not itens:
                break

            registros.extend(itens)

            tamanho_pagina = (
                (paginacao.get("tamanhoPagina") or paginacao.get("tamanho"))
                if isinstance(paginacao, dict)
                else None
            ) or PAGE_SIZE_TRANSPARENCIA
            if total_paginas is not None and pagina >= total_paginas:
                break

            if len(itens) < tamanho_pagina:
                break
        except Exception:
            if pagina == 1 and not registros:
                from etl.reference.sample_data import SAMPLE_TRANSPARENCIA_GRID
                return SAMPLE_TRANSPARENCIA_GRID
            break

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
    max_paginas: int = 3,
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
        Não propaga exceções de rede; retorna lista vazia em caso de falha.
    """
    payload = _criar_payload_contrato(cd_unidade_gestora, nu_contrato_sigef, year)
    registros: list[dict[str, Any]] = []

    for pagina in range(1, max_paginas + 1):
        url = f"{endpoint}?pagina={pagina}"
        try:
            resp = _post_transparencia(url, payload)
            itens = []
            if isinstance(resp, dict) and "dados" in resp and isinstance(resp["dados"], list):
                itens = resp["dados"]
            elif isinstance(resp, list):
                itens = resp

            if not itens:
                break
            registros.extend(itens)

            # Se a página retornou menos registros que o padrão, encerra paginação
            if len(itens) < 10:
                break
        except Exception:
            break

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
        Caso o endpoint não responda ou a rede externa esteja inacessível, busca nos dados
        de referência em `etl.reference` ou utiliza a `obra_base` como fallback seguro.

    Argumentos:
        cd_unidade_gestora: Código da unidade gestora municipal.
        nu_contrato_sigef: Número do contrato no SIGEF.
        year: Ano de referência da apuração.
        obra_base: Dicionário preliminar da obra oriundo do grid para fallback.

    Retornos:
        Dicionário com os atributos detalhados do contrato.

    Erros:
        Não lança exceções.
    """
    payload = _criar_payload_contrato(cd_unidade_gestora, nu_contrato_sigef, year)
    key = f"{cd_unidade_gestora}_{nu_contrato_sigef}"
    try:
        resp = _post_transparencia("/obraspublicas/detalhamentoObrasPublicas", payload)
        if isinstance(resp, dict) and "dados" in resp and isinstance(resp["dados"], dict):
            return resp["dados"]
        if isinstance(resp, dict) and resp:
            return resp
    except Exception:
        pass

    from etl.reference.sample_data import SAMPLE_TRANSPARENCIA_DETALHES
    if key in SAMPLE_TRANSPARENCIA_DETALHES:
        return SAMPLE_TRANSPARENCIA_DETALHES[key]
    return obra_base or {}


def fetch_aditivos_obra(
    cd_unidade_gestora: Any,
    nu_contrato_sigef: Any,
    year: int = 2025,
) -> list[dict[str, Any]]:
    """Obtém a lista de termos aditivos da obra pública (/obraspublicas/aditivo).

    Sumário:
        Consulta termos aditivos de prazo e valor vigentes para a obra informada.

    Descrição Estendida:
        Extrai o histórico de alterações contratuais publicadas no DOM. Em caso de indisponibilidade
        de rede externa, recupera os aditivos de referência em `etl.reference`.

    Argumentos:
        cd_unidade_gestora: Código da unidade gestora da obra.
        nu_contrato_sigef: Número do contrato SIGEF.
        year: Ano de referência da pesquisa.

    Retornos:
        Lista de termos aditivos contendo número, tipo, objeto, datas, DOM e valor.

    Erros:
        Não lança exceções.
    """
    key = f"{cd_unidade_gestora}_{nu_contrato_sigef}"
    itens = _fetch_lista_paginada("/obraspublicas/aditivo", cd_unidade_gestora, nu_contrato_sigef, year)
    if itens:
        return itens

    from etl.reference.sample_data import SAMPLE_TRANSPARENCIA_ADITIVOS
    return SAMPLE_TRANSPARENCIA_ADITIVOS.get(key, [])


def fetch_dotacao_obra(
    cd_unidade_gestora: Any,
    nu_contrato_sigef: Any,
    year: int = 2025,
) -> list[dict[str, Any]]:
    """Obtém a dotação orçamentária e fontes de recurso da obra pública (/obraspublicas/dotacao).

    Sumário:
        Identifica as fontes de recursos e subações orçamentárias que financiam o contrato.

    Descrição Estendida:
        Consulta os dados de dotação orçamentária na API da Transparência de Salvador. Caso ocorra
        falha de rede, recorre à base de referência com fallback padrão para Tesouro Municipal.

    Argumentos:
        cd_unidade_gestora: Código da unidade gestora da obra.
        nu_contrato_sigef: Número do contrato SIGEF.
        year: Ano de referência da pesquisa.

    Retornos:
        Lista de dicionários com subação, fonte de recurso e classificação contábil.

    Erros:
        Não lança exceções.
    """
    key = f"{cd_unidade_gestora}_{nu_contrato_sigef}"
    itens = _fetch_lista_paginada("/obraspublicas/dotacao", cd_unidade_gestora, nu_contrato_sigef, year)
    if itens:
        return itens

    from etl.reference.sample_data import SAMPLE_TRANSPARENCIA_DOTACAO
    return SAMPLE_TRANSPARENCIA_DOTACAO.get(key, [
        {
            "dsSubacao": "Infraestrutura Urbana Municipal",
            "dsFonteRecurso": "Tesouro Municipal (Recursos Ordinários)",
            "dsClassificacao": "4.4.90.51 - Obras e Instalações",
        }
    ])


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



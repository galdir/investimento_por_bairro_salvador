"""Módulo de classificação de Mandatos Municipais e deduplicação canônica de obras.

Define os ciclos de mandatos municipais de Salvador (2021-2024 e 2025-2028),
calcula a sobreposição de vigência contratual e realiza a deduplicação de contratos
pela chave canônica (cdUnidadeGestora, nuContratoSigef) em conformidade com o ADR-0002.
"""

import re
from typing import Any, Final

from etl.domain.territorio import parse_float

MANDATOS_MUNICIPAIS: Final[dict[str, dict[str, Any]]] = {
    "2021-2024": {
        "inicio": 2021,
        "fim": 2024,
        "data_inicio": "2021-01-01T03:00:00.000Z",
        "data_fim": "2024-12-31T03:00:00.000Z",
    },
    "2025-2028": {
        "inicio": 2025,
        "fim": 2028,
        "data_inicio": "2025-01-01T03:00:00.000Z",
        "data_fim": "2028-12-31T03:00:00.000Z",
    },
}


def obter_chave_canonica_obra(obra: dict[str, Any]) -> tuple[str, str]:
    """Retorna a chave canônica única de um contrato de obra pública.

    Sumário:
        Utiliza a tupla (cdUnidadeGestora, nuContratoSigef) como chave primária composta.

    Descrição Estendida:
        Contratos municipais de Salvador são univocamente identificados pelo par
        composto por sua Unidade Gestora e número do contrato SIGEF. Caso algum
        deles esteja ausente, recorre ao identificador numérico da obra ou ao objeto.

    Argumentos:
        obra: Dicionário representando o contrato de obra pública.

    Retornos:
        Tupla de duas strings normalizadas identificando univocamente o contrato.

    Erros:
        Não lança exceções.
    """
    cd_ug = (
        obra.get("cdUnidadeGestora")
        or obra.get("dsUnidadeGestora")
        or obra.get("sgOrgao")
        or obra.get("unidadeGestora")
    )
    nu_sigef = obra.get("nuContratoSigef") or obra.get("numeroContrato")

    if cd_ug is not None and nu_sigef is not None:
        return (str(cd_ug).strip(), str(nu_sigef).strip())

    if obra.get("id") is not None:
        return ("ID", str(obra.get("id")).strip())

    obj = str(obra.get("dsObjeto") or obra.get("objeto") or "").strip()
    return ("OBJ", obj)


def _formatar_data_iso(data_val: Any) -> str | None:
    """Padroniza datas para formato string ISO ou preserva formato original."""
    if not data_val:
        return None
    s = str(data_val).strip()
    if not s:
        return None
    m_br = re.match(r"^(\d{2})/(\d{2})/(\d{4})", s)
    if m_br:
        dia, mes, ano = m_br.group(1), m_br.group(2), m_br.group(3)
        return f"{ano}-{mes}-{dia}T00:00:00.000Z"
    return s


def resolver_datas_vigencia(obra: dict[str, Any]) -> tuple[str | None, str | None]:
    """Determina as datas canônicas de início e término de vigência de uma obra pública.

    Sumário:
        Aplica as regras de precedência: dtInicioVigencia -> dtAssinatura e dtTerminoVigenciaAtualizado -> dtFimVigenciaOriginal.

    Argumentos:
        obra: Dicionário contendo os dados do contrato.

    Retornos:
        Tupla com (data_inicio, data_termino) em string ou None.
    """
    inicio = obra.get("dtInicioVigencia") or obra.get("dtAssinatura")
    fim = obra.get("dtTerminoVigenciaAtualizado") or obra.get("dtFimVigenciaOriginal") or inicio
    return (_formatar_data_iso(inicio), _formatar_data_iso(fim))


def extrair_ano_data(data_val: Any) -> int | None:
    """Extrai o ano numérico a partir de uma data em formato ISO, DD/MM/YYYY ou string.

    Sumário:
        Converte representações textuais de data em ano numérico.

    Argumentos:
        data_val: Objeto ou string contendo representação de data.

    Retornos:
        Ano inteiro ou None caso inválido.
    """
    if not data_val:
        return None
    s = str(data_val).strip()
    m_br = re.match(r"^\d{2}/\d{2}/(\d{4})", s)
    if m_br:
        try:
            return int(m_br.group(1))
        except ValueError:
            pass
    m_iso = re.match(r"^(\d{4})", s)
    if m_iso:
        try:
            return int(m_iso.group(1))
        except ValueError:
            pass
    m_any = re.search(r"\b(20\d{2})\b", s)
    if m_any:
        try:
            return int(m_any.group(1))
        except ValueError:
            pass
    return None


def classificar_mandatos_obra(
    obra: dict[str, Any],
    mandatos_map: dict[str, dict[str, Any]] | None = None,
    periodo_referencia_ano: int | None = None,
) -> list[str]:
    """Calcula os mandatos municipais aos quais a obra pública pertence por sobreposição de vigência.

    Sumário:
        Verifica se o intervalo de vigência do contrato se sobrepõe aos limites quadrienais dos mandatos.

    Descrição Estendida:
        Obtém a data de início (dtInicioVigencia ou dtAssinatura) e a data de término
        (dtTerminoVigenciaAtualizado, dtFimVigenciaOriginal ou início). Uma obra sobrepõe
        um mandato [mandato_inicio, mandato_fim] sempre que inicio_ano <= mandato_fim e
        fim_ano >= mandato_inicio. Caso não possua datas explícitas, recorre ao ano extraído
        do nuContratoSigef, ao atributo ano ou ao período de referência consultado.

    Argumentos:
        obra: Dicionário contendo os dados do contrato de obra pública.
        mandatos_map: Dicionário opcional com a definição dos mandatos e seus anos limites.
        periodo_referencia_ano: Ano inteiro de referência da consulta como fallback adicional.

    Retornos:
        Lista com os rótulos de mandato aos quais a obra pertence (ex: ['2021-2024', '2025-2028']).

    Erros:
        Não lança exceções.
    """
    mandatos_config = mandatos_map or MANDATOS_MUNICIPAIS

    inicio_raw, fim_raw = resolver_datas_vigencia(obra)

    inicio_ano = extrair_ano_data(inicio_raw)
    fim_ano = extrair_ano_data(fim_raw)

    if inicio_ano is None and fim_ano is not None:
        inicio_ano = fim_ano
    elif fim_ano is None and inicio_ano is not None:
        fim_ano = inicio_ano

    # Fallback caso não haja datas válidas de vigência
    if inicio_ano is None:
        nu_sigef = str(obra.get("nuContratoSigef") or obra.get("numeroContrato") or "")
        match_ano = re.search(r"/(\d{4})", nu_sigef)
        if match_ano:
            try:
                ano_contrato = int(match_ano.group(1))
                inicio_ano = fim_ano = ano_contrato
            except ValueError:
                pass

    if inicio_ano is None and obra.get("ano"):
        try:
            inicio_ano = fim_ano = int(obra["ano"])
        except (ValueError, TypeError):
            pass

    if inicio_ano is None and periodo_referencia_ano:
        inicio_ano = fim_ano = periodo_referencia_ano

    if inicio_ano is None or fim_ano is None:
        return []

    mandatos_pertencentes: list[str] = []
    for nome_mandato, bounds in mandatos_config.items():
        if inicio_ano <= bounds["fim"] and fim_ano >= bounds["inicio"]:
            mandatos_pertencentes.append(nome_mandato)

    return mandatos_pertencentes


def _recencia_score(obra: dict[str, Any]) -> tuple[str, float, float]:
    """Calcula tupla comparável de recência e atualização para desempate na deduplicação."""
    _, dt_fim = resolver_datas_vigencia(obra)
    fim_str = dt_fim or ""
    vl = parse_float(obra.get("vlAtualizado") or obra.get("valorContratualVigente") or 0.0)
    perc = parse_float(obra.get("percentualExecutado") or 0.0)
    return (fim_str, vl, perc)


def deduplicar_obras(obras: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplica contratos retornados em múltiplos períodos pela chave canônica.

    Sumário:
        Agrupa contratos por (cdUnidadeGestora, nuContratoSigef), preservando o estado mais recente e mesclando mandatos.

    Descrição Estendida:
        Quando um contrato plurianual é retornado em múltiplas consultas (por exemplo, na consulta de 2024
        e na de 2025), consolida em uma única entrada com o estado cadastral e financeiro mais atualizado,
        unificando a lista de mandatos municipais aos quais o contrato se sobrepõe.

    Argumentos:
        obras: Lista de dicionários brutos de contratos de obras públicas.

    Retornos:
        Lista deduplicada preservando a ordem original de inserção.

    Erros:
        Não lança exceções.
    """
    mapa_obras: dict[tuple[str, str], dict[str, Any]] = {}
    ordem_chaves: list[tuple[str, str]] = []

    for obra in obras:
        chave = obter_chave_canonica_obra(obra)
        obra_dict = dict(obra)

        # Garante que mandatos estejam atribuídos
        if "mandatos" not in obra_dict or not obra_dict["mandatos"]:
            obra_dict["mandatos"] = classificar_mandatos_obra(obra_dict)

        if chave not in mapa_obras:
            mapa_obras[chave] = obra_dict
            ordem_chaves.append(chave)
        else:
            existente = mapa_obras[chave]
            mandatos_unidos = set(existente.get("mandatos", [])) | set(obra_dict.get("mandatos", []))
            # Preserva ordem canônica dos mandatos
            mandatos_ordenados = [m for m in MANDATOS_MUNICIPAIS if m in mandatos_unidos]

            # Preserva o registro com score de recência maior ou igual
            if _recencia_score(obra_dict) >= _recencia_score(existente):
                for k, v in obra_dict.items():
                    if k != "mandatos" and v is not None:
                        existente[k] = v
            existente["mandatos"] = mandatos_ordenados

    return [mapa_obras[c] for c in ordem_chaves]

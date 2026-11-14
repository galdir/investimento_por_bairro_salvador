"""Módulo de cálculo e análise de concentração de empreiteiras em Salvador.

Agrupa os contratos de obras públicas por CNPJ / Razão Social da construtora
para identificar volume financeiro concentrado e quantidade de obras por empresa.
"""

from typing import Any

from etl.domain.territorio import normalizar_nome, parse_float


SITUACOES_INATIVAS = frozenset(
    {
        "CONCLUÍDA",
        "CONCLUIDA",
        "CONCLUÍDO",
        "CONCLUIDO",
        "CANCELADA",
        "CANCELADO",
        "RESCINDIDA",
        "RESCINDIDO",
        "PARALISADA",
        "PARALISADO",
    }
)


def eh_cnpj_valido(cnpj: Any) -> bool:
    """Verifica se um valor de CNPJ contém exatamente 14 dígitos numéricos."""
    return len("".join(filter(str.isdigit, str(cnpj or "")))) == 14


def formatar_cnpj(cnpj_raw: str) -> str:
    """Normaliza e formata string de CNPJ no padrão XX.XXX.XXX/XXXX-XX.

    Sumário:
        Remove caracteres não numéricos e formata como CNPJ se contiver 14 dígitos.

    Descrição Estendida:
        Higieniza o texto bruto de documento do credor, extraindo os dígitos decimais.
        Caso possua os 14 dígitos canônicos de um CNPJ brasileiro, insere a máscara
        oficial. Caso contrário, retorna o valor original sem espaços em branco nas pontas.

    Argumentos:
        cnpj_raw: String contendo o CNPJ bruto com ou sem pontuação.

    Retornos:
        String com o CNPJ formatado no padrão 00.000.000/0000-00 ou o valor original limpo.

    Erros:
        Não lança exceções.
    """
    if not cnpj_raw:
        return ""
    digits = "".join(filter(str.isdigit, str(cnpj_raw)))
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    return str(cnpj_raw).strip()


def obter_chave_empreiteira(cnpj: str, razao_social: str) -> str:
    """Retorna a chave única determinística para indexação de construtoras.

    Sumário:
        Define o CNPJ formatado como chave preferencial ou a Razão Social como fallback.

    Descrição Estendida:
        Verifica se o CNPJ fornecido contém 14 dígitos numéricos válidos. Em caso afirmativo,
        retorna o CNPJ formatado como identificador inequívoco da construtora. Caso contrário,
        utiliza o nome empresarial (Razão Social) normalizado.

    Argumentos:
        cnpj: String com o CNPJ do credor.
        razao_social: Razão social ou nome fantasia da construtora.

    Retornos:
        String identificadora única para a construtora.

    Erros:
        Não lança exceções.
    """
    cnpj_norm = formatar_cnpj(cnpj)
    if eh_cnpj_valido(cnpj_norm):
        return cnpj_norm
    razao_limpa = normalizar_nome(str(razao_social or ""))
    return razao_limpa or "NAO INFORMADO"


def calcular_concentracao_empreiteiras(obras: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Calcula a concentração de obras e volume financeiro por empreiteira em Salvador.

    Sumário:
        Agrupa contratos por CNPJ (propagando CNPJ único pela Razão Social aos itens sem CNPJ válido) e consolida totais.

    Descrição Estendida:
        Em primeira passagem, indexa cada Razão Social normalizada ao CNPJ de 14 dígitos quando
        informado em ao menos um contrato da mesma construtora sem ambiguidade. Em segunda passagem,
        propaga nos dicionários de `obras` o CNPJ canônico quando ausente ou inválido na fonte
        e consolida para cada empreiteira:
        - Quantidade total de obras vinculadas;
        - Quantidade de obras ativas (excluindo situações concluídas, canceladas, rescindidas e paralisadas);
        - Montante financeiro total contratado (soma do Valor Contratual Vigente);
        - Lista dos identificadores das obras pertencentes à mesma empresa.

    Argumentos:
        obras: Lista de dicionários representando as obras públicas (enriquecidos com `cnpj`, `cnpjCredor` e `nuDocumentoCredor` quando propagado).

    Retornos:
        Dicionário indexado pela chave única (CNPJ ou razão social) contendo os dados consolidados.

    Erros:
        Não lança exceções.
    """
    # 1ª Passagem: mapa de Razão Social normalizada -> CNPJ canônico único (14 dígitos)
    cnpjs_por_razao: dict[str, set[str]] = {}
    razao_preferencial: dict[str, str] = {}
    for o in obras:
        cnpj = formatar_cnpj(str(o.get("nuDocumentoCredor") or o.get("cnpj") or o.get("cnpjCredor") or ""))
        razao_raw = str(o.get("nmCredor") or o.get("credor") or "").strip()
        razao_norm = normalizar_nome(razao_raw)
        if not razao_norm or razao_norm == "NAO INFORMADO":
            continue
        if eh_cnpj_valido(cnpj):
            cnpjs_por_razao.setdefault(razao_norm, set()).add(cnpj)
            razao_preferencial.setdefault(razao_norm, razao_raw)

    cnpj_canonico_por_razao = {
        razao_norm: next(iter(cnpjs))
        for razao_norm, cnpjs in cnpjs_por_razao.items()
        if len(cnpjs) == 1
    }

    # 2ª Passagem: propagação de CNPJ canônico e consolidação dos grupos
    concentracao: dict[str, dict[str, Any]] = {}

    for o in obras:
        cnpj_raw = o.get("nuDocumentoCredor") or o.get("cnpj") or o.get("cnpjCredor") or ""
        cnpj = formatar_cnpj(str(cnpj_raw))
        razao_social = str(o.get("nmCredor") or o.get("credor") or "Não Informado").strip()
        razao_norm = normalizar_nome(razao_social)

        if not eh_cnpj_valido(cnpj) and razao_norm in cnpj_canonico_por_razao:
            cnpj = cnpj_canonico_por_razao[razao_norm]
            o["cnpj"] = cnpj
            o["cnpjCredor"] = cnpj
            if not eh_cnpj_valido(o.get("nuDocumentoCredor")):
                o["nuDocumentoCredor"] = cnpj

        if razao_norm in razao_preferencial:
            razao_exibicao = razao_preferencial[razao_norm]
        else:
            razao_exibicao = razao_social

        chave = obter_chave_empreiteira(cnpj, razao_exibicao)

        vl_orig = parse_float(o.get("vlOriginal") or o.get("valorOriginal") or 0.0)
        vl_atua = parse_float(o.get("vlAtualizado") or o.get("valorContratualVigente") or vl_orig)
        sit = str(o.get("dsSituacao") or o.get("situacao") or "").strip().upper()
        eh_ativa = sit not in SITUACOES_INATIVAS
        obra_id = o.get("id")

        if chave not in concentracao:
            concentracao[chave] = {
                "cnpj": cnpj if eh_cnpj_valido(cnpj) else "",
                "razaoSocial": razao_exibicao,
                "totalObras": 0,
                "totalObrasAtivas": 0,
                "valorTotalContratado": 0.0,
                "obrasIds": [],
            }

        item = concentracao[chave]
        item["totalObras"] += 1
        if eh_ativa:
            item["totalObrasAtivas"] += 1
        item["valorTotalContratado"] = round(item["valorTotalContratado"] + vl_atua, 2)
        if obra_id is not None and obra_id not in item["obrasIds"]:
            item["obrasIds"].append(obra_id)

    return concentracao

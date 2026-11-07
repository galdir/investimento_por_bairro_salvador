"""Módulo de cálculo e análise de concentração de empreiteiras em Salvador.

Agrupa os contratos de obras públicas por CNPJ / Razão Social da construtora
para identificar volume financeiro concentrado e quantidade de obras por empresa.
"""

from typing import Any


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
    digits = "".join(filter(str.isdigit, cnpj_norm))
    if len(digits) == 14:
        return cnpj_norm
    return str(razao_social or "Não Informado").strip()


def calcular_concentracao_empreiteiras(obras: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Calcula a concentração de obras e volume financeiro por empreiteira em Salvador.

    Sumário:
        Agrupa contratos por CNPJ e consolida total de obras e valor contratado.

    Descrição Estendida:
        Para cada construtora identificada nos contratos de obras públicas, calcula:
        - Quantidade total de obras vinculadas;
        - Quantidade de obras ativas (com situação em execução);
        - Montante financeiro total contratado (soma do Valor Contratual Vigente);
        - Lista dos identificadores das obras pertencentes à mesma empresa.

    Argumentos:
        obras: Lista de dicionários representando as obras públicas.

    Retornos:
        Dicionário indexado pela chave única (CNPJ ou razão social) contendo os dados consolidados.

    Erros:
        Não lança exceções.
    """
    situacoes_inativas = {"CONCLUÍDA", "CONCLUIDA", "CANCELADA", "RESCINDIDA"}
    concentracao: dict[str, dict[str, Any]] = {}

    for o in obras:
        cnpj_raw = o.get("nuDocumentoCredor") or o.get("cnpj") or o.get("cnpjCredor") or ""
        cnpj = formatar_cnpj(str(cnpj_raw))
        razao_social = str(o.get("nmCredor") or o.get("credor") or "Não Informado").strip()

        chave = obter_chave_empreiteira(cnpj, razao_social)

        vl_orig = float(o.get("vlOriginal") or o.get("valorOriginal") or 0.0)
        vl_atua = float(o.get("vlAtualizado") or o.get("valorContratualVigente") or vl_orig)
        sit = str(o.get("dsSituacao") or o.get("situacao") or "").strip().upper()
        eh_ativa = sit not in situacoes_inativas
        obra_id = o.get("id")

        if chave not in concentracao:
            concentracao[chave] = {
                "cnpj": cnpj,
                "razaoSocial": razao_social,
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

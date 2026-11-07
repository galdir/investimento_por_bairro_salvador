"""Módulo de montagem e consolidação da Ficha Limpa da Obra sob demanda (Camada C).

Estrutura o prontuário analítico de cada contrato de engenharia com Funil de Execução
Financeira, Aditivos Contratuais, Dotação Orçamentária e concentração da Empreiteira.
"""

from typing import Any

from etl.domain.empreiteiras import formatar_cnpj, obter_chave_empreiteira
from etl.domain.semaforo import classificar_semaforo
from etl.domain.tema import classificar_tema
from etl.domain.territorio import parse_float


def construir_ficha_obra(
    obra: dict[str, Any],
    detalhe: dict[str, Any],
    aditivos_raw: list[dict[str, Any]],
    dotacoes_raw: list[dict[str, Any]],
    empenhos_raw: list[dict[str, Any]],
    liquidacoes_raw: list[dict[str, Any]],
    pagamentos_raw: list[dict[str, Any]],
    concentracao_map: dict[str, dict[str, Any]],
    year: int = 2025,
) -> dict[str, Any]:
    """Constrói o payload JSON completo da Ficha Limpa da Obra para carregamento sob demanda.

    Sumário:
        Consolida cadastros, funil financeiro sem distorções, aditivos, dotações e empreiteira.

    Descrição Estendida:
        Recebe os dados brutos ou processados das diversas fontes e endpoints da Transparência
        de Salvador e produz o documento estruturado e padronizado da Ficha Limpa da Obra:
        - Objeto, órgãos, contratos, processos e situação;
        - Resumo da construtora com CNPJ formatado, total de obras e contagem de outras obras;
        - Prazos e datas de vigência original e atualizada;
        - Edição do Diário Oficial do Município (DOM);
        - Funil de Execução Financeira completo (Original, Vigente, Empenhado, Liquidado e Pago)
          preservando os valores reais medidos e pagos para confrontação com percentualExecutado;
        - Lista normalizada de aditivos contratuais com valor, justificativa, datas e DOM;
        - Lista de dotações orçamentárias e fontes de recurso do tesouro/transferências;
        - Classificações funcionais de Tema da Obra e Semáforo de Risco.

    Argumentos:
        obra: Dicionário base da obra com geocodificação e nível territorial.
        detalhe: Dicionário retornado por /obraspublicas/detalhamentoObrasPublicas.
        aditivos_raw: Lista de aditivos retornados por /obraspublicas/aditivo.
        dotacoes_raw: Lista de dotações retornadas por /obraspublicas/dotacao.
        empenhos_raw: Lista de empenhos relacionados.
        liquidacoes_raw: Lista de liquidações relacionadas.
        pagamentos_raw: Lista de pagamentos relacionados.
        concentracao_map: Dicionário com a concentração de mercado de cada construtora.
        year: Ano civil de referência da apuração.

    Retornos:
        Dicionário formatado no esquema canônico da Ficha Limpa da Obra.

    Erros:
        Não lança exceções; adota valores padrão seguros caso propriedades estejam ausentes.
    """
    obra_id = obra.get("id")
    cd_ug = obra.get("cdUnidadeGestora")
    nu_sigef = obra.get("nuContratoSigef")

    cnpj_credor = formatar_cnpj(str(detalhe.get("nuDocumentoCredor") or obra.get("nuDocumentoCredor") or ""))
    razao_social = str(detalhe.get("nmCredor") or obra.get("nmCredor") or "Não Informado").strip()
    chave_emp = obter_chave_empreiteira(cnpj_credor, razao_social)

    nu_dom = detalhe.get("nuDom") or obra.get("nuDom")

    emp_info = concentracao_map.get(chave_emp, {
        "cnpj": cnpj_credor,
        "razaoSocial": razao_social,
        "totalObras": 1,
        "totalObrasAtivas": 1,
        "valorTotalContratado": parse_float(obra.get("vlAtualizado") or obra.get("vlOriginal") or 0.0),
        "obrasIds": [obra_id],
    })

    vl_orig = parse_float(detalhe.get("vlOriginal") or obra.get("vlOriginal") or 0.0)
    vl_atua = parse_float(detalhe.get("vlAtualizado") or obra.get("vlAtualizado") or vl_orig)
    perc_exec = parse_float(detalhe.get("percentualExecutado") or obra.get("percentualExecutado") or 0.0)

    # Execução financeira real apurada a partir das listas contábeis
    vl_emp = sum(parse_float(e.get("valEmpenhado") or e.get("valEmpenho") or 0.0) for e in empenhos_raw)
    if vl_emp == 0.0:
        vl_emp = vl_atua

    vl_liq = sum(parse_float(l.get("valLiqLiquidacao") or l.get("valBrutLiquidacao") or 0.0) for l in liquidacoes_raw)
    if vl_liq == 0.0 and obra.get("vlLiquidado"):
        vl_liq = parse_float(obra.get("vlLiquidado"))

    vl_pago = sum(parse_float(p.get("pago") or p.get("valorPago") or 0.0) for p in pagamentos_raw)
    if vl_pago == 0.0:
        vl_pago = parse_float(obra.get("vlPago") or 0.0)

    delta_aditivos = round(max(0.0, vl_atua - vl_orig), 2)
    delta_perc_aditivos = round(((vl_atua - vl_orig) / vl_orig) * 100.0, 2) if vl_orig > 0 else 0.0

    # Normalização de aditivos contratuais
    aditivos_norm: list[dict[str, Any]] = []
    for ad in aditivos_raw:
        aditivos_norm.append({
            "nuAditivo": ad.get("nuAditivo") or ad.get("numero") or "Termo Aditivo",
            "dsTipoAlteracao": ad.get("dsTipoAlteracao") or ad.get("tipoAlteracao") or "Alteração Contratual",
            "dsObjetoAditivo": ad.get("dsObjetoAditivo") or ad.get("objeto") or "",
            "dtAssinatura": ad.get("dtAssinatura"),
            "dtTerminoVigencia": ad.get("dtTerminoVigencia"),
            "dtPublicacao": ad.get("dtPublicacao"),
            "nuDom": ad.get("nuDom") or nu_dom,
            "vlAditivo": parse_float(ad.get("vlAditivo") or ad.get("valor") or 0.0),
        })

    # Normalização de dotações orçamentárias
    dotacoes_norm: list[dict[str, Any]] = []
    for dt in dotacoes_raw:
        dotacoes_norm.append({
            "subacao": dt.get("dsSubacao") or "Infraestrutura Urbana Municipal",
            "fonteRecurso": dt.get("dsFonteRecurso") or "Tesouro Municipal (Recursos Ordinários)",
            "classificacao": dt.get("dsClassificacao") or "4.4.90.51 - Obras e Instalações",
        })

    tema = classificar_tema(obra)
    semaforo = obra.get("semaforo") or classificar_semaforo(obra)

    total_obras_emp = int(emp_info.get("totalObras", 1))
    outras_obras_count = max(0, total_obras_emp - 1)

    return {
        "id": obra_id,
        "unidadeGestora": obra.get("sgOrgao") or obra.get("dsUnidadeGestora"),
        "numeroContrato": nu_sigef,
        "numeroContratoOriginal": detalhe.get("nuContratoOriginal") or obra.get("nuContratoOriginal") or nu_sigef,
        "nuProcesso": detalhe.get("nuProcesso") or obra.get("nuProcesso"),
        "objeto": detalhe.get("dsObjeto") or obra.get("dsObjeto"),
        "situacao": detalhe.get("dsSituacao") or obra.get("dsSituacao"),
        "empreiteira": {
            "razaoSocial": emp_info.get("razaoSocial") or razao_social,
            "cnpj": cnpj_credor,
            "totalObras": total_obras_emp,
            "totalObrasAtivas": int(emp_info.get("totalObrasAtivas", 1)),
            "valorTotalContratado": parse_float(emp_info.get("valorTotalContratado", vl_atua)),
            "outrasObrasCount": outras_obras_count,
            "outrasObrasIds": [oid for oid in emp_info.get("obrasIds", []) if oid != obra_id],
        },
        "vigencia": {
            "dataInicio": detalhe.get("dtInicioVigencia") or obra.get("dtInicioVigencia"),
            "dataFimOriginal": detalhe.get("dtFimVigenciaOriginal") or obra.get("dtFimVigenciaOriginal"),
            "dataTerminoAtualizado": detalhe.get("dtTerminoVigenciaAtualizado") or obra.get("dtTerminoVigenciaAtualizado"),
            "prazoOriginal": detalhe.get("dsPrazoOriginal") or "Conforme Contrato",
            "prazoAtualizado": detalhe.get("dsPrazoAtualizado") or "Conforme Contrato",
        },
        "dom": {
            "nuDom": nu_dom or "Não informado",
            "dataPublicacao": detalhe.get("dtPublicacao") or detalhe.get("dtInicioVigencia"),
        },
        "funilFinanceiro": {
            "valorOriginal": vl_orig,
            "valorContratualVigente": vl_atua,
            "valorEmpenhado": vl_emp,
            "valorLiquidado": vl_liq,
            "valorPago": vl_pago,
            "percentualExecutado": perc_exec,
            "valorAditivos": delta_aditivos,
            "deltaPercentualAditivos": delta_perc_aditivos,
        },
        "aditivos": aditivos_norm,
        "dotacao": dotacoes_norm,
        "empenhos": empenhos_raw,
        "liquidacoes": liquidacoes_raw,
        "pagamentos": pagamentos_raw,
        "tema": tema,
        "semaforo": semaforo,
        "nivel": obra.get("nivel"),
        "bairro": obra.get("bairro"),
        "prefeituraBairro": obra.get("prefeitura_bairro") or obra.get("prefeituraBairro"),
        "latitude": obra.get("latitude"),
        "longitude": obra.get("longitude"),
        "estagioAlocacao": obra.get("estagioAlocacao"),
    }

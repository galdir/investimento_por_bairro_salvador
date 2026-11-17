"""Módulo de montagem e consolidação da Ficha Limpa da Obra sob demanda (Camada C).

Estrutura o prontuário analítico de cada contrato de engenharia com Funil de Execução
Financeira, Aditivos Contratuais, Dotação Orçamentária e concentração da Empreiteira.
"""

from typing import Any

from etl.domain.empreiteiras import eh_cnpj_valido, formatar_cnpj, obter_chave_empreiteira
from etl.domain.mandato import formatar_data_iso
from etl.domain.semaforo import classificar_semaforo
from etl.domain.tema import classificar_tema
from etl.domain.vocacao import classificar_vocacao
from etl.domain.territorio import parse_float

_DOM_INVALIDOS = {"", "nao informado", "não informado", "nao informada", "não informada", "none", "null"}
PORTAL_TRANSPARENCIA_URL = "https://www.transparencia.salvador.ba.gov.br/"
PORTAL_DOM_URL = "https://dom.salvador.ba.gov.br/"


def _texto_limpo(val: Any) -> str:
    """Converte valor opcional para string limpa, tratando sentinela nula."""
    if val is None:
        return ""
    s = str(val).strip()
    return "" if s.lower() in {"none", "null"} else s


def eh_dom_valido(val: Any) -> bool:
    """Indica se a edição do DOM informada é válida e não genérica."""
    return _texto_limpo(val).lower() not in _DOM_INVALIDOS


def _descrever_origem_alocacao(
    nivel: Any,
    estagio_alocacao: Any,
    bairro: Any,
    prefeitura_bairro: Any,
) -> str:
    """Descreve de forma legível a origem do lastro territorial da obra."""
    nivel_txt = _texto_limpo(nivel)
    estagio_txt = _texto_limpo(estagio_alocacao)
    bairro_txt = _texto_limpo(bairro)
    pb_txt = _texto_limpo(prefeitura_bairro)

    if nivel_txt == "Escopo Cidade (Não-Localizado)" or (not bairro_txt and not pb_txt):
        if estagio_txt:
            return f"Contrato sem localização territorial específica ({estagio_txt})"
        return "Contrato sem localização territorial específica identificada nas fontes oficiais"

    destino = bairro_txt or pb_txt
    if estagio_txt:
        return f"Alocação em {destino} via {estagio_txt}"
    return f"Alocação territorial registrada em {destino}"


def _construir_fontes_oficiais(
    *,
    cd_ug: Any,
    unidade_gestora: str | None,
    nu_contrato_sigef: str | None,
    nu_processo: str | None,
    nu_dom: str | None,
    aditivos: list[dict[str, Any]],
    nivel: Any,
    bairro: Any,
    prefeitura_bairro: Any,
    estagio_alocacao: Any,
    lastro_curadoria: dict[str, Any] | None = None,
    cotas_lista_fechada: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Constrói o bloco estruturado de Fontes Oficiais & Lastro Territorial da Ficha Limpa."""
    cd_ug_txt = _texto_limpo(cd_ug)
    ug_txt = _texto_limpo(unidade_gestora)
    nu_sigef_txt = _texto_limpo(nu_contrato_sigef)
    nu_proc_txt = _texto_limpo(nu_processo)
    nu_dom_txt = _texto_limpo(nu_dom)

    dom_contrato = (
        {"nuDom": nu_dom_txt, "url": PORTAL_DOM_URL}
        if eh_dom_valido(nu_dom_txt)
        else {"nuDom": None, "url": None}
    )

    dom_aditivos = [
        {
            "nuAditivo": ad.get("nuAditivo"),
            "nuDom": _texto_limpo(ad.get("nuDom")),
            "dtPublicacao": ad.get("dtPublicacao"),
            "url": PORTAL_DOM_URL,
        }
        for ad in aditivos
        if eh_dom_valido(ad.get("nuDom"))
    ]

    lastro_territorial: dict[str, Any] = {
        "nivel": _texto_limpo(nivel) or None,
        "estagioAlocacao": _texto_limpo(estagio_alocacao) or None,
        "bairro": _texto_limpo(bairro) or None,
        "prefeituraBairro": _texto_limpo(prefeitura_bairro) or None,
        "origem": _descrever_origem_alocacao(nivel, estagio_alocacao, bairro, prefeitura_bairro),
    }
    if isinstance(lastro_curadoria, dict):
        trecho = _texto_limpo(lastro_curadoria.get("trechoComprobatorio"))
        doc_origem = _texto_limpo(lastro_curadoria.get("documentoOrigem"))
        justificativa = _texto_limpo(lastro_curadoria.get("justificativa"))
        if trecho:
            lastro_territorial["trechoComprobatorio"] = trecho
        if doc_origem:
            lastro_territorial["documentoOrigem"] = doc_origem
        if justificativa:
            lastro_territorial["justificativa"] = justificativa
    if isinstance(cotas_lista_fechada, list) and cotas_lista_fechada:
        lastro_territorial["cotasListaFechada"] = cotas_lista_fechada

    return {
        "portalTransparencia": {
            "nome": "Portal da Transparência de Salvador",
            "url": PORTAL_TRANSPARENCIA_URL,
        },
        "chaveCanonica": {
            "cdUnidadeGestora": cd_ug_txt or None,
            "unidadeGestora": ug_txt or None,
            "nuContratoSigef": nu_sigef_txt or None,
        },
        "nuProcesso": nu_proc_txt or None,
        "domContrato": dom_contrato,
        "domAditivos": dom_aditivos,
        "lastroTerritorial": lastro_territorial,
    }


def _somar_listas_contabeis(
    empenhos: list[dict[str, Any]],
    liquidacoes: list[dict[str, Any]],
    pagamentos: list[dict[str, Any]],
) -> tuple[float, float, float]:
    """Soma os valores reais das listas de empenhos, liquidações e pagamentos."""
    vl_emp = round(
        sum(parse_float(e.get("valEmpenhado") or e.get("valEmpenho") or 0.0) for e in empenhos),
        2,
    )
    vl_liq = round(
        sum(
            parse_float(l.get("valLiqLiquidacao") or l.get("valBrutLiquidacao") or 0.0)
            for l in liquidacoes
        ),
        2,
    )
    vl_pago = round(
        sum(parse_float(p.get("pago") or p.get("valorPago") or 0.0) for p in pagamentos),
        2,
    )
    return vl_emp, vl_liq, vl_pago


def _calcular_deltas_aditivos(vl_orig: float, vl_atua: float) -> tuple[float, float]:
    """Calcula a variação contratual absoluta e percentual sobre o valor original."""
    delta_abs = round(max(0.0, vl_atua - vl_orig), 2)
    delta_perc = round(((vl_atua - vl_orig) / vl_orig) * 100.0, 2) if vl_orig > 0 else 0.0
    return delta_abs, delta_perc


def _montar_ficha_base(
    *,
    obra_id: Any,
    cd_ug: Any,
    unidade_gestora: str | None,
    numero_contrato: str | None,
    numero_contrato_original: str | None,
    nu_processo: str | None,
    objeto: str | None,
    situacao: str | None,
    razao_social: str,
    cnpj_credor: str,
    data_inicio: Any,
    data_fim_original: Any,
    data_termino_atualizado: Any,
    prazo_original: str,
    prazo_atualizado: str,
    nu_dom: str,
    dt_pub_dom: Any,
    funil_financeiro: dict[str, Any],
    aditivos: list[dict[str, Any]],
    dotacao: list[dict[str, Any]],
    empenhos: list[dict[str, Any]],
    liquidacoes: list[dict[str, Any]],
    pagamentos: list[dict[str, Any]],
    tema: Any,
    vocacao: Any,
    semaforo: Any,
    nivel: Any,
    bairro: Any,
    prefeitura_bairro: Any,
    latitude: Any,
    longitude: Any,
    estagio_alocacao: Any,
    concentracao_map: dict[str, dict[str, Any]] | None,
    lastro_curadoria: dict[str, Any] | None = None,
    cotas_lista_fechada: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Monta o dicionário estruturado da Ficha Limpa e aplica o resumo da empreiteira."""
    ficha: dict[str, Any] = {
        "id": obra_id,
        "unidadeGestora": unidade_gestora,
        "numeroContrato": numero_contrato,
        "numeroContratoOriginal": numero_contrato_original,
        "nuProcesso": nu_processo,
        "objeto": objeto,
        "situacao": situacao,
        "empreiteira": {"razaoSocial": razao_social, "cnpj": cnpj_credor},
        "vigencia": {
            "dataInicio": formatar_data_iso(data_inicio),
            "dataFimOriginal": formatar_data_iso(data_fim_original),
            "dataTerminoAtualizado": formatar_data_iso(data_termino_atualizado),
            "prazoOriginal": prazo_original,
            "prazoAtualizado": prazo_atualizado,
        },
        "dom": {
            "nuDom": nu_dom,
            "dataPublicacao": formatar_data_iso(dt_pub_dom),
        },
        "funilFinanceiro": funil_financeiro,
        "aditivos": aditivos,
        "dotacao": dotacao,
        "empenhos": empenhos,
        "liquidacoes": liquidacoes,
        "pagamentos": pagamentos,
        "tema": tema,
        "vocacao": vocacao,
        "semaforo": semaforo,
        "nivel": nivel,
        "bairro": bairro,
        "prefeituraBairro": prefeitura_bairro,
        "latitude": latitude,
        "longitude": longitude,
        "estagioAlocacao": estagio_alocacao,
        "fontesOficiais": _construir_fontes_oficiais(
            cd_ug=cd_ug,
            unidade_gestora=unidade_gestora,
            nu_contrato_sigef=numero_contrato,
            nu_processo=nu_processo,
            nu_dom=nu_dom,
            aditivos=aditivos,
            nivel=nivel,
            bairro=bairro,
            prefeitura_bairro=prefeitura_bairro,
            estagio_alocacao=estagio_alocacao,
            lastro_curadoria=lastro_curadoria,
            cotas_lista_fechada=cotas_lista_fechada,
        ),
    }
    if isinstance(cotas_lista_fechada, list) and cotas_lista_fechada:
        ficha["cotasListaFechada"] = cotas_lista_fechada
    if cd_ug is not None:
        ficha["cdUnidadeGestora"] = cd_ug

    return aplicar_resumo_empreiteira_ficha(
        ficha,
        concentracao_map=concentracao_map,
        cnpj_override=cnpj_credor,
        razao_override=razao_social,
    )


def aplicar_resumo_empreiteira_ficha(
    ficha: dict[str, Any],
    concentracao_map: dict[str, dict[str, Any]] | None = None,
    cnpj_override: str | None = None,
    razao_override: str | None = None,
) -> dict[str, Any]:
    """Atualiza o bloco `empreiteira` de uma Ficha Limpa com o resumo unificado da construtora."""
    emp_atual = ficha.get("empreiteira") or {}
    cnpj = formatar_cnpj(str(cnpj_override or emp_atual.get("cnpj") or ""))
    razao_social = str(razao_override or emp_atual.get("razaoSocial") or "Não Informado").strip()
    obra_id = ficha.get("id")
    vl_atua = parse_float((ficha.get("funilFinanceiro") or {}).get("valorContratualVigente") or 0.0)

    chave_emp = obter_chave_empreiteira(cnpj, razao_social)
    emp_info = (concentracao_map or {}).get(chave_emp)
    if emp_info is None:
        emp_info = {
            "cnpj": cnpj,
            "razaoSocial": razao_social,
            "totalObras": 1,
            "totalObrasAtivas": 1,
            "valorTotalContratado": vl_atua,
            "obrasIds": [obra_id] if obra_id is not None else [],
        }

    total_obras_emp = int(emp_info.get("totalObras", 1))
    obras_ids = emp_info.get("obrasIds", [])
    cnpj_final = formatar_cnpj(str(emp_info.get("cnpj") or cnpj))
    ficha["empreiteira"] = {
        "razaoSocial": emp_info.get("razaoSocial") or razao_social,
        "cnpj": cnpj_final,
        "totalObras": total_obras_emp,
        "totalObrasAtivas": int(emp_info.get("totalObrasAtivas", 1)),
        "valorTotalContratado": parse_float(emp_info.get("valorTotalContratado", vl_atua)),
        "outrasObrasCount": max(0, total_obras_emp - 1),
        "outrasObrasIds": [oid for oid in obras_ids if oid != obra_id],
    }
    return ficha


def construir_ficha_obra(
    obra: dict[str, Any],
    detalhe: dict[str, Any],
    aditivos_raw: list[dict[str, Any]],
    dotacoes_raw: list[dict[str, Any]],
    empenhos_raw: list[dict[str, Any]],
    liquidacoes_raw: list[dict[str, Any]],
    pagamentos_raw: list[dict[str, Any]],
    concentracao_map: dict[str, dict[str, Any]] | None = None,
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
        - Prazos e datas de vigência original e atualizada padronizados em ISO;
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
        concentracao_map: Dicionário opcional com a concentração de mercado de cada construtora.
        year: Ano civil de referência da apuração (mantido por compatibilidade de assinatura).

    Retornos:
        Dicionário formatado no esquema canônico da Ficha Limpa da Obra.

    Erros:
        Não lança exceções; adota valores padrão seguros caso propriedades estejam ausentes.
    """
    _ = year
    obra_id = obra.get("id")
    cd_ug = obra.get("cdUnidadeGestora")
    nu_sigef = obra.get("nuContratoSigef") or obra.get("numeroContrato")

    cnpj_credor = formatar_cnpj(
        str(
            detalhe.get("nuDocumentoCredor")
            or obra.get("nuDocumentoCredor")
            or obra.get("cnpj")
            or obra.get("cnpjCredor")
            or ""
        )
    )
    razao_social = str(
        detalhe.get("nmCredor") or obra.get("nmCredor") or obra.get("credor") or "Não Informado"
    ).strip()
    nu_dom = detalhe.get("nuDom") or obra.get("nuDom")

    vl_orig = parse_float(
        detalhe.get("vlOriginal") or obra.get("vlOriginal") or obra.get("valorOriginal") or 0.0
    )
    vl_atua = parse_float(
        detalhe.get("vlAtualizado")
        or obra.get("vlAtualizado")
        or obra.get("valorContratualVigente")
        or vl_orig
    )
    perc_exec = parse_float(
        detalhe.get("percentualExecutado")
        if detalhe.get("percentualExecutado") is not None
        else (obra.get("percentualExecutado") or 0.0)
    )

    vl_emp, vl_liq, vl_pago = _somar_listas_contabeis(empenhos_raw, liquidacoes_raw, pagamentos_raw)
    if vl_emp == 0.0:
        vl_emp = vl_atua
    if vl_liq == 0.0 and obra.get("vlLiquidado"):
        vl_liq = parse_float(obra.get("vlLiquidado"))
    if vl_pago == 0.0 and obra.get("vlPagoReal") is not None:
        vl_pago = parse_float(obra.get("vlPagoReal"))

    delta_aditivos, delta_perc_aditivos = _calcular_deltas_aditivos(vl_orig, vl_atua)

    aditivos_norm = [
        {
            "nuAditivo": ad.get("nuAditivo") or ad.get("numero") or "Termo Aditivo",
            "dsTipoAlteracao": ad.get("dsTipoAlteracao") or ad.get("tipoAlteracao") or "Alteração Contratual",
            "dsObjetoAditivo": ad.get("dsObjetoAditivo") or ad.get("objeto") or "",
            "dtAssinatura": ad.get("dtAssinatura"),
            "dtTerminoVigencia": ad.get("dtTerminoVigencia"),
            "dtPublicacao": ad.get("dtPublicacao"),
            "nuDom": ad.get("nuDom") or nu_dom,
            "vlAditivo": parse_float(ad.get("vlAditivo") or ad.get("valor") or 0.0),
        }
        for ad in aditivos_raw
    ]
    dotacoes_norm = [
        {
            "subacao": dt.get("dsSubacao") or "Infraestrutura Urbana Municipal",
            "fonteRecurso": dt.get("dsFonteRecurso") or "Tesouro Municipal (Recursos Ordinários)",
            "classificacao": dt.get("dsClassificacao") or "4.4.90.51 - Obras e Instalações",
        }
        for dt in dotacoes_raw
    ]

    data_inicio = detalhe.get("dtInicioVigencia") or obra.get("dtInicioVigencia")
    dt_pub_dom = detalhe.get("dtPublicacao") or data_inicio

    return _montar_ficha_base(
        obra_id=obra_id,
        cd_ug=cd_ug,
        unidade_gestora=obra.get("sgOrgao") or obra.get("unidadeGestora") or obra.get("dsUnidadeGestora"),
        numero_contrato=nu_sigef,
        numero_contrato_original=detalhe.get("nuContratoOriginal") or obra.get("nuContratoOriginal") or nu_sigef,
        nu_processo=detalhe.get("nuProcesso") or obra.get("nuProcesso"),
        objeto=detalhe.get("dsObjeto") or obra.get("dsObjeto") or obra.get("objeto"),
        situacao=detalhe.get("dsSituacao") or obra.get("dsSituacao") or obra.get("situacao"),
        razao_social=razao_social,
        cnpj_credor=cnpj_credor,
        data_inicio=data_inicio,
        data_fim_original=detalhe.get("dtFimVigenciaOriginal") or obra.get("dtFimVigenciaOriginal"),
        data_termino_atualizado=detalhe.get("dtTerminoVigenciaAtualizado") or obra.get("dtTerminoVigenciaAtualizado"),
        prazo_original=detalhe.get("dsPrazoOriginal") or "Conforme Contrato",
        prazo_atualizado=detalhe.get("dsPrazoAtualizado") or "Conforme Contrato",
        nu_dom=nu_dom or "Não informado",
        dt_pub_dom=dt_pub_dom,
        funil_financeiro={
            "valorOriginal": vl_orig,
            "valorContratualVigente": vl_atua,
            "valorEmpenhado": vl_emp,
            "valorLiquidado": vl_liq,
            "valorPago": vl_pago,
            "percentualExecutado": perc_exec,
            "valorAditivos": delta_aditivos,
            "deltaPercentualAditivos": delta_perc_aditivos,
        },
        aditivos=aditivos_norm,
        dotacao=dotacoes_norm,
        empenhos=empenhos_raw,
        liquidacoes=liquidacoes_raw,
        pagamentos=pagamentos_raw,
        tema=obra.get("tema") or classificar_tema(obra),
        vocacao=obra.get("vocacao") or classificar_vocacao(obra),
        semaforo=obra.get("semaforo") or classificar_semaforo(obra),
        nivel=obra.get("nivel"),
        bairro=obra.get("bairro"),
        prefeitura_bairro=obra.get("prefeitura_bairro") or obra.get("prefeituraBairro"),
        latitude=obra.get("latitude"),
        longitude=obra.get("longitude"),
        estagio_alocacao=obra.get("estagioAlocacao"),
        concentracao_map=concentracao_map,
        lastro_curadoria=obra.get("lastroCuradoria"),
        cotas_lista_fechada=obra.get("cotasListaFechada"),
    )


def _texto_limpo(val: Any) -> str:
    """Converte valor em texto sem espaços laterais, tratando None como string vazia."""
    if val is None:
        return ""
    s = str(val).strip()
    return "" if s.lower() in {"none", "null"} else s


def _eh_dotacao_padrao(dotacoes: list[dict[str, Any]]) -> bool:
    """Identifica o fallback genérico padrão de dotação orçamentária."""
    if not dotacoes:
        return True
    if len(dotacoes) != 1:
        return False
    d0 = dotacoes[0]
    return (
        d0.get("subacao") == "Infraestrutura Urbana Municipal"
        and d0.get("fonteRecurso") == "Tesouro Municipal (Recursos Ordinários)"
    )


def _selecionar_cnpj_mais_completo(
    obra: dict[str, Any],
    fichas_candidatas: list[dict[str, Any]],
) -> str:
    """Seleciona o primeiro CNPJ válido (14 dígitos) entre o registro base e as candidatas."""
    candidatos = [
        obra.get("nuDocumentoCredor"),
        obra.get("cnpj"),
        obra.get("cnpjCredor"),
    ]
    for f in fichas_candidatas:
        candidatos.append((f.get("empreiteira") or {}).get("cnpj"))
    for raw in candidatos:
        fmt = formatar_cnpj(str(raw or ""))
        if eh_cnpj_valido(fmt):
            return fmt
    return ""


def _resolver_vigencia_mesclada(
    obra: dict[str, Any],
    candidatas: list[dict[str, Any]],
) -> dict[str, Any]:
    """Consolida datas e prazos de vigência das fichas candidatas em formato ISO uniforme."""
    data_fim_orig = next(
        (_texto_limpo((f.get("vigencia") or {}).get("dataFimOriginal")) for f in candidatas if _texto_limpo((f.get("vigencia") or {}).get("dataFimOriginal"))),
        _texto_limpo(obra.get("dtFimVigenciaOriginal")) or None,
    )
    ficha_com_fim_orig = next(
        (f for f in candidatas if _texto_limpo((f.get("vigencia") or {}).get("dataFimOriginal"))),
        None,
    )
    data_inicio = (
        _texto_limpo(obra.get("dtInicioVigencia"))
        or (_texto_limpo((ficha_com_fim_orig.get("vigencia") or {}).get("dataInicio")) if ficha_com_fim_orig else "")
        or next(
            (_texto_limpo((f.get("vigencia") or {}).get("dataInicio")) for f in candidatas if _texto_limpo((f.get("vigencia") or {}).get("dataInicio"))),
            None,
        )
    )
    data_termino_atua = (
        _texto_limpo(obra.get("dtTerminoVigenciaAtualizado"))
        or next(
            (_texto_limpo((f.get("vigencia") or {}).get("dataTerminoAtualizado")) for f in candidatas if _texto_limpo((f.get("vigencia") or {}).get("dataTerminoAtualizado"))),
            None,
        )
    )
    prazo_orig = next(
        (
            _texto_limpo((f.get("vigencia") or {}).get("prazoOriginal"))
            for f in candidatas
            if _texto_limpo((f.get("vigencia") or {}).get("prazoOriginal")) not in {"", "Conforme Contrato"}
        ),
        "Conforme Contrato",
    )
    prazo_atua = next(
        (
            _texto_limpo((f.get("vigencia") or {}).get("prazoAtualizado"))
            for f in candidatas
            if _texto_limpo((f.get("vigencia") or {}).get("prazoAtualizado")) not in {"", "Conforme Contrato"}
        ),
        "Conforme Contrato",
    )
    return {
        "dataInicio": formatar_data_iso(data_inicio),
        "dataFimOriginal": formatar_data_iso(data_fim_orig),
        "dataTerminoAtualizado": formatar_data_iso(data_termino_atua),
        "prazoOriginal": prazo_orig,
        "prazoAtualizado": prazo_atua,
    }


def _resolver_funil_mesclado(
    obra: dict[str, Any],
    candidatas: list[dict[str, Any]],
    empenhos: list[dict[str, Any]],
    liquidacoes: list[dict[str, Any]],
    pagamentos: list[dict[str, Any]],
) -> dict[str, Any]:
    """Recalcula o Funil de Execução Financeira priorizando valores reais das listas resgatadas."""
    vl_orig = parse_float(
        obra.get("valorOriginal")
        or obra.get("vlOriginal")
        or next((f.get("funilFinanceiro", {}).get("valorOriginal") for f in candidatas if parse_float(f.get("funilFinanceiro", {}).get("valorOriginal")) > 0), 0.0)
    )
    vl_atua = parse_float(
        obra.get("valorContratualVigente")
        or obra.get("vlAtualizado")
        or next((f.get("funilFinanceiro", {}).get("valorContratualVigente") for f in candidatas if parse_float(f.get("funilFinanceiro", {}).get("valorContratualVigente")) > 0), vl_orig)
    )
    if obra.get("percentualExecutado") is not None:
        perc_exec = parse_float(obra.get("percentualExecutado"))
    else:
        perc_exec = next(
            (
                parse_float((f.get("funilFinanceiro") or {}).get("percentualExecutado"))
                for f in candidatas
                if (f.get("funilFinanceiro") or {}).get("percentualExecutado") is not None
            ),
            0.0,
        )

    delta_aditivos, delta_perc_aditivos = _calcular_deltas_aditivos(vl_orig, vl_atua)
    vl_emp, vl_liq, vl_pago = _somar_listas_contabeis(empenhos, liquidacoes, pagamentos)

    if vl_emp == 0.0:
        emp_com_lista = [
            parse_float((f.get("funilFinanceiro") or {}).get("valorEmpenhado"))
            for f in candidatas
            if f.get("empenhos") and parse_float((f.get("funilFinanceiro") or {}).get("valorEmpenhado")) > 0
        ]
        vl_emp = max(emp_com_lista) if emp_com_lista else vl_atua

    if vl_liq == 0.0:
        liq_com_lista = [
            parse_float((f.get("funilFinanceiro") or {}).get("valorLiquidado"))
            for f in candidatas
            if f.get("liquidacoes") and parse_float((f.get("funilFinanceiro") or {}).get("valorLiquidado")) > 0
        ]
        if liq_com_lista:
            vl_liq = max(liq_com_lista)

    if vl_pago == 0.0:
        pag_com_lista = [
            parse_float((f.get("funilFinanceiro") or {}).get("valorPago"))
            for f in candidatas
            if f.get("pagamentos") and parse_float((f.get("funilFinanceiro") or {}).get("valorPago")) > 0
        ]
        if pag_com_lista:
            vl_pago = max(pag_com_lista)

    return {
        "valorOriginal": vl_orig,
        "valorContratualVigente": vl_atua,
        "valorEmpenhado": vl_emp,
        "valorLiquidado": vl_liq,
        "valorPago": vl_pago,
        "percentualExecutado": perc_exec,
        "valorAditivos": delta_aditivos,
        "deltaPercentualAditivos": delta_perc_aditivos,
    }


def mesclar_fichas_obra(
    obra: dict[str, Any],
    fichas_candidatas: list[dict[str, Any]],
    concentracao_map: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Mescla múltiplas versões locais de uma Ficha Limpa aplicando máxima completude campo a campo.

    Sumário:
        Consolida listas contábeis, aditivos, dotações, DOM, vigência e CNPJ entre versões de um contrato.

    Descrição Estendida:
        Para contratos que possuem múltiplas versões em disco ou que passaram por reconsulta com
        endpoints secundários vazios, inspeciona todas as fichas candidatas da mesma Chave Canônica
        da Obra preservando a lista não vazia/mais longa de empenhos, liquidações, pagamentos,
        aditivos e dotações (preferindo dotações reais ao fallback padrão), além do CNPJ formatado,
        processo administrativo, número original do contrato, edição do DOM e datas de vigência
        normalizadas em ISO. Recalcula o Funil de Execução Financeira com os totais reais.
    """
    candidatas = [f for f in fichas_candidatas if isinstance(f, dict)]
    if not candidatas:
        return construir_ficha_obra(obra, {}, [], [], [], [], [], concentracao_map)

    obra_id = obra.get("id")
    if obra_id is None:
        obra_id = next((f.get("id") for f in candidatas if f.get("id") is not None), None)

    cd_ug = obra.get("cdUnidadeGestora")
    if cd_ug is None:
        cd_ug = next((f.get("cdUnidadeGestora") for f in candidatas if f.get("cdUnidadeGestora") is not None), None)

    unidade_gestora = (
        _texto_limpo(obra.get("unidadeGestora"))
        or _texto_limpo(obra.get("sgOrgao"))
        or _texto_limpo(obra.get("dsUnidadeGestora"))
        or next((_texto_limpo(f.get("unidadeGestora")) for f in candidatas if _texto_limpo(f.get("unidadeGestora"))), "")
    )
    numero_contrato = (
        _texto_limpo(obra.get("numeroContrato"))
        or _texto_limpo(obra.get("nuContratoSigef"))
        or next((_texto_limpo(f.get("numeroContrato")) for f in candidatas if _texto_limpo(f.get("numeroContrato"))), "")
    )

    orig_cands = [
        _texto_limpo(v)
        for v in ([obra.get("nuContratoOriginal")] + [f.get("numeroContratoOriginal") for f in candidatas])
        if _texto_limpo(v)
    ]
    numero_contrato_original = next(
        (v for v in orig_cands if v != numero_contrato),
        orig_cands[0] if orig_cands else numero_contrato,
    )

    proc_cands = [
        _texto_limpo(v)
        for v in ([obra.get("nuProcesso")] + [f.get("nuProcesso") for f in candidatas])
        if _texto_limpo(v)
    ]
    nu_processo = max(proc_cands, key=len) if proc_cands else None

    objeto = (
        _texto_limpo(obra.get("objeto"))
        or _texto_limpo(obra.get("dsObjeto"))
        or next((_texto_limpo(f.get("objeto")) for f in candidatas if _texto_limpo(f.get("objeto"))), "")
    )
    situacao = (
        _texto_limpo(obra.get("situacao"))
        or _texto_limpo(obra.get("dsSituacao"))
        or next((_texto_limpo(f.get("situacao")) for f in candidatas if _texto_limpo(f.get("situacao"))), "")
    )

    cnpj_credor = _selecionar_cnpj_mais_completo(obra, candidatas)
    razao_cands = [
        _texto_limpo(v)
        for v in (
            [obra.get("nmCredor"), obra.get("credor")]
            + [(f.get("empreiteira") or {}).get("razaoSocial") for f in candidatas]
        )
        if _texto_limpo(v) and _texto_limpo(v).lower() not in {"não informado", "nao informado"}
    ]
    razao_social = razao_cands[0] if razao_cands else "Não Informado"

    vigencia = _resolver_vigencia_mesclada(obra, candidatas)

    # DOM: prefere edição válida e sua data de publicação associada
    ficha_dom_valido = next(
        (f for f in candidatas if eh_dom_valido((f.get("dom") or {}).get("nuDom"))),
        None,
    )
    if ficha_dom_valido is not None:
        dom_info = ficha_dom_valido.get("dom") or {}
        nu_dom = _texto_limpo(dom_info.get("nuDom"))
        dt_pub_dom = _texto_limpo(dom_info.get("dataPublicacao")) or vigencia["dataInicio"]
    else:
        obra_dom = _texto_limpo(obra.get("nuDom"))
        nu_dom = obra_dom if eh_dom_valido(obra_dom) else "Não informado"
        dt_pub_dom = next(
            (_texto_limpo((f.get("dom") or {}).get("dataPublicacao")) for f in candidatas if _texto_limpo((f.get("dom") or {}).get("dataPublicacao"))),
            vigencia["dataInicio"],
        )

    # Listas: preserva a mais completa de cada endpoint
    empenhos = [dict(e) for e in max((f.get("empenhos") or [] for f in candidatas), key=len, default=[])]
    liquidacoes = [dict(l) for l in max((f.get("liquidacoes") or [] for f in candidatas), key=len, default=[])]
    pagamentos = [dict(p) for p in max((f.get("pagamentos") or [] for f in candidatas), key=len, default=[])]

    aditivos = [dict(ad) for ad in max((f.get("aditivos") or [] for f in candidatas), key=len, default=[])]
    if nu_dom != "Não informado":
        for ad in aditivos:
            if not eh_dom_valido(ad.get("nuDom")):
                ad["nuDom"] = nu_dom

    dotacoes_nao_padrao = [
        f.get("dotacao") or []
        for f in candidatas
        if not _eh_dotacao_padrao(f.get("dotacao") or [])
    ]
    if dotacoes_nao_padrao:
        dotacao = [dict(d) for d in max(dotacoes_nao_padrao, key=len)]
    else:
        dotacoes_existentes = [f.get("dotacao") or [] for f in candidatas if f.get("dotacao")]
        dotacao = [dict(d) for d in max(dotacoes_existentes, key=len, default=[])]

    funil = _resolver_funil_mesclado(obra, candidatas, empenhos, liquidacoes, pagamentos)
    tema = obra.get("tema") or next((f.get("tema") for f in candidatas if f.get("tema")), None) or classificar_tema(obra)
    vocacao = obra.get("vocacao") or next((f.get("vocacao") for f in candidatas if f.get("vocacao")), None) or classificar_vocacao(obra)
    semaforo = obra.get("semaforo") or next((f.get("semaforo") for f in candidatas if f.get("semaforo")), None) or classificar_semaforo(obra)

    tem_curadoria = isinstance(obra.get("lastroCuradoria"), dict)
    nivel_obra = obra.get("nivel")
    bairro_obra = obra.get("bairro")
    candidatas_compativeis = [
        f
        for f in candidatas
        if (not nivel_obra or f.get("nivel") == nivel_obra)
        and (bairro_obra is None or f.get("bairro") == bairro_obra)
    ]

    def _resolver_territorial(
        valor_obra: Any,
        chave_ficha: str,
        *,
        aceitar_none: bool = False,
    ) -> Any:
        if tem_curadoria or (aceitar_none and valor_obra is not None) or (not aceitar_none and valor_obra):
            return valor_obra
        if (
            nivel_obra in {"Regional (Prefeitura-Bairro)", "Escopo Cidade (Não-Localizado)"}
            and chave_ficha in {"bairro", "latitude", "longitude"}
        ):
            return None
        if nivel_obra == "Pontual" and chave_ficha == "bairro" and bool(obra.get("estagioAlocacao")):
            return None
        if nivel_obra == "Escopo Cidade (Não-Localizado)" and chave_ficha == "prefeituraBairro":
            return None
        return next(
            (
                f.get(chave_ficha)
                for f in candidatas_compativeis
                if (f.get(chave_ficha) is not None if aceitar_none else bool(f.get(chave_ficha)))
            ),
            None,
        )

    nivel_final = _resolver_territorial(obra.get("nivel"), "nivel")
    bairro_final = _resolver_territorial(obra.get("bairro"), "bairro", aceitar_none=True)
    prefeitura_bairro_final = _resolver_territorial(
        obra.get("prefeitura_bairro") or obra.get("prefeituraBairro"),
        "prefeituraBairro",
    )
    latitude_final = _resolver_territorial(obra.get("latitude"), "latitude", aceitar_none=True)
    longitude_final = _resolver_territorial(obra.get("longitude"), "longitude", aceitar_none=True)
    estagio_final = _resolver_territorial(obra.get("estagioAlocacao"), "estagioAlocacao")

    return _montar_ficha_base(
        obra_id=obra_id,
        cd_ug=cd_ug,
        unidade_gestora=unidade_gestora,
        numero_contrato=numero_contrato,
        numero_contrato_original=numero_contrato_original,
        nu_processo=nu_processo,
        objeto=objeto,
        situacao=situacao,
        razao_social=razao_social,
        cnpj_credor=cnpj_credor,
        data_inicio=vigencia["dataInicio"],
        data_fim_original=vigencia["dataFimOriginal"],
        data_termino_atualizado=vigencia["dataTerminoAtualizado"],
        prazo_original=vigencia["prazoOriginal"],
        prazo_atualizado=vigencia["prazoAtualizado"],
        nu_dom=nu_dom,
        dt_pub_dom=dt_pub_dom,
        funil_financeiro=funil,
        aditivos=aditivos,
        dotacao=dotacao,
        empenhos=empenhos,
        liquidacoes=liquidacoes,
        pagamentos=pagamentos,
        tema=tema,
        vocacao=vocacao,
        semaforo=semaforo,
        nivel=nivel_final,
        bairro=bairro_final,
        prefeitura_bairro=prefeitura_bairro_final,
        latitude=latitude_final,
        longitude=longitude_final,
        estagio_alocacao=estagio_final,
        concentracao_map=concentracao_map,
        lastro_curadoria=obra.get("lastroCuradoria"),
        cotas_lista_fechada=obra.get("cotasListaFechada"),
    )


def sincronizar_obra_com_ficha(obra: dict[str, Any], ficha: dict[str, Any]) -> None:
    """Propaga metadados e totais reais do Funil de Execução Financeira da ficha para a obra."""
    cnpj_credor = formatar_cnpj(str((ficha.get("empreiteira") or {}).get("cnpj") or ""))
    if eh_cnpj_valido(cnpj_credor):
        obra["cnpj"] = cnpj_credor
        obra["cnpjCredor"] = cnpj_credor
        obra["nuDocumentoCredor"] = cnpj_credor

    nu_dom = _texto_limpo((ficha.get("dom") or {}).get("nuDom"))
    if eh_dom_valido(nu_dom):
        obra["nuDom"] = nu_dom

    funil = ficha.get("funilFinanceiro") or {}
    vl_emp = parse_float(funil.get("valorEmpenhado") or 0.0)
    vl_liq = parse_float(funil.get("valorLiquidado") or 0.0)
    vl_pago_real = funil.get("valorPago")
    pagamento_indisponivel = vl_pago_real is None or (
        parse_float(vl_pago_real) == 0.0 and ficha.get("pagamentos") == []
    )
    valor_pago_indice = None if pagamento_indisponivel else round(parse_float(vl_pago_real), 2)
    if pagamento_indisponivel:
        funil["valorPago"] = None

    obra["vlEmpenhado"] = round(vl_emp, 2)
    obra["vlLiquidado"] = round(vl_liq, 2)
    obra["vlPagoReal"] = valor_pago_indice
    obra["valorPago"] = valor_pago_indice
    obra["vlPago"] = valor_pago_indice
    if ficha.get("frentesMedicao"):
        obra["frentesMedicao"] = ficha["frentesMedicao"]
    elif "frentesMedicao" in obra:
        obra["frentesMedicao"] = []
    if ficha.get("cotasListaFechada"):
        obra["cotasListaFechada"] = ficha["cotasListaFechada"]
    else:
        obra.pop("cotasListaFechada", None)

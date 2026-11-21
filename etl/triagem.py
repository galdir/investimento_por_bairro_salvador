"""CLI 100% offline de Triagem Territorial Assistida nas 3 trilhas revisáveis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Optional

from etl.domain.geocoding import (
    _ContextoTerritorialStage1,
    _buscar_equipamentos_no_objeto,
    _buscar_toponimos_blindados,
    _carregar_curadoria_territorial,
    _carregar_json_referencia,
    _deduplicar_bairros_canonicos,
    _executar_estagio_1_deterministico,
    _extrair_equipamentos_oficiais,
    _extrair_indices_territoriais,
    _normalizar_texto_equipamento,
    calcular_centroides_bairros,
    reconciliar_bairro_canonico,
)
from etl.domain.regras_frentes import (
    agrupar_pagamentos_por_nota,
    avaliar_guardrails_nota_liquidacao,
    selecionar_regra_frente,
    validar_e_preparar_regras_frentes,
)
from etl.domain.territorio import normalizar_nome, parse_float
from etl.publicacao import versao_publicada
from etl.reconcile import indexar_fichas_locais, resolver_caminho_indice

_NIVEIS_ALVO_VARREDURA = {
    "Escopo Cidade (Não-Localizado)",
    "Regional (Prefeitura-Bairro)",
}


def _resolver_diretorio_base(data_dir: Path) -> Path:
    """Resolve o ponteiro da versão publicada (`atual.json`) com fallback para `data_dir`."""
    versao_dir = versao_publicada(data_dir)
    if versao_dir is not None and versao_dir.exists():
        return versao_dir
    return data_dir


def _carregar_curadoria_somente_leitura(curadoria_path: Optional[Path]) -> dict[str, dict[str, Any]]:
    """Carrega o catálogo de curadoria sem nunca modificar o arquivo em disco."""
    if curadoria_path is None:
        return _carregar_curadoria_territorial()
    if not curadoria_path.exists():
        return {}
    dados = json.loads(curadoria_path.read_text(encoding="utf-8"))
    if not isinstance(dados, dict):
        return {}
    registros = dados.get("registros")
    if isinstance(registros, dict):
        return registros
    return dados


def _carregar_bairros_geojson(base_dir: Path, data_dir: Path) -> dict[str, Any]:
    """Carrega GeoJSON local de bairros com fallback para a malha oficial de referência."""
    for candidato in (base_dir / "geo" / "bairros.geojson", data_dir / "geo" / "bairros.geojson"):
        if candidato.exists():
            return json.loads(candidato.read_text(encoding="utf-8"))
    return _carregar_json_referencia("geosalvador_bairros_real.geojson") or {"features": []}


def _chave_contrato(registro: dict[str, Any]) -> str:
    """Retorna a chave canônica `cdUnidadeGestora:nuContratoSigef` do contrato."""
    cd_ug = str(registro.get("cdUnidadeGestora") or registro.get("unidadeGestora") or "").strip()
    nu_contrato = str(registro.get("nuContratoSigef") or registro.get("numeroContrato") or "").strip()
    if cd_ug or nu_contrato:
        return f"{cd_ug}:{nu_contrato}"
    return f"id:{registro.get('id', '')}"


def _construir_contexto_stage1(bairros_geojson: dict[str, Any]) -> tuple[
    _ContextoTerritorialStage1,
    list[dict[str, Any]],
    dict[str, str],
    dict[str, str],
]:
    """Prepara contexto territorial determinístico e dicionários auxiliares de referência."""
    bairros_nomes, sublocalidades_norm, bairro_para_pb, bairro_para_pb_norm = _extrair_indices_territoriais(
        bairros_geojson
    )
    bairros_centroides = calcular_centroides_bairros(bairros_geojson)
    bairros_centroides_norm = {normalizar_nome(k): v for k, v in bairros_centroides.items()}
    dicionario_lotes = _carregar_json_referencia("lotes_regionais.json") or {}
    dicionario_sublocalidades = _carregar_json_referencia("sublocalidades.json") or {}
    equipamentos = _extrair_equipamentos_oficiais()
    ctx = _ContextoTerritorialStage1(
        bairros_nomes=bairros_nomes,
        dicionario_lotes=dicionario_lotes,
        dicionario_sublocalidades=dicionario_sublocalidades,
        sublocalidades_norm=sublocalidades_norm,
        bairros_centroides=bairros_centroides,
        bairros_centroides_norm=bairros_centroides_norm,
        bairro_para_pb=bairro_para_pb,
        bairro_para_pb_norm=bairro_para_pb_norm,
    )
    return ctx, equipamentos, bairro_para_pb, bairro_para_pb_norm


def _carregar_contratos_e_fichas(base_dir: Path) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Carrega pares `(obra_indice, ficha)` para contratos em Escopo Cidade ou Regional."""
    obras_dir = base_dir / "obras"
    _, fichas_por_id = indexar_fichas_locais(obras_dir)

    index_path = resolver_caminho_indice(base_dir, 2025)
    if index_path is not None and index_path.exists():
        index_data = json.loads(index_path.read_text(encoding="utf-8"))
        obras_lista = index_data.get("obras") or []
    else:
        obras_lista = list(fichas_por_id.values())

    selecionados: list[tuple[dict[str, Any], dict[str, Any]]] = []
    vistos: set[str] = set()
    for obra in obras_lista:
        if not isinstance(obra, dict):
            continue
        obra_id = str(obra.get("id") or "").strip()
        if obra_id and obra_id in vistos:
            continue
        if obra_id:
            vistos.add(obra_id)
        ficha = fichas_por_id.get(obra_id) if obra_id else None
        if ficha is None:
            ficha = obra
        nivel = str(obra.get("nivel") or ficha.get("nivel") or "").strip()
        if nivel not in _NIVEIS_ALVO_VARREDURA:
            continue
        selecionados.append((obra, ficha))
    return selecionados


_REGEX_NF = re.compile(r"\bNF(?:-?E|S-?E)?\.?\s*(?:N[º°.]?\s*)?(\d+)\b")
_REGEX_COMPETENCIA = re.compile(r"\b(0[1-9]|1[0-2])/((?:19|20)\d{2})\b")
_REGEX_DATA_ISO = re.compile(r"^((?:19|20)\d{2})-(0[1-9]|1[0-2])-\d{2}")
_REGEX_DATA_BR = re.compile(r"^\d{2}/(0[1-9]|1[0-2])/((?:19|20)\d{2})")


def _adicionar_amostra_unica(lista: list[str], valor: str, limite: int = 5) -> None:
    """Adiciona `valor` à lista sem duplicatas até o limite especificado."""
    if valor and valor not in lista and len(lista) < limite:
        lista.append(valor)


def normalizar_assinatura_frente(texto: str) -> str:
    """Normaliza descrição de liquidação mascarando processo, competência, NF/NFSE, medição e datas."""
    t = normalizar_nome(texto)
    # Datas completas (DD/MM/AAAA, DD.MM.AAAA, AAAA-MM-DD)
    t = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "<DATA>", t)
    t = re.sub(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", "<DATA>", t)
    # Intervalos de dias no mesmo mês (ex: 01 A 15/06/2025)
    t = re.sub(r"\b\d{1,2}\s+A\s+<DATA>", "<DATA>", t)
    # Competência MM/AAAA
    t = _REGEX_COMPETENCIA.sub("<COMP>", t)
    # Número de processo (PROC. 1234/2025 ou 112721/2025)
    t = re.sub(r"\bPROC(?:ESSO)?\.?\s*(?:N[º°.]?\s*)?\d+(?:[./-]\d+)*\b", "<PROC>", t)
    t = re.sub(r"\b\d{4,}/\d{4}\b", "<PROC>", t)
    # Número de NF / NFSE / NFE
    t = _REGEX_NF.sub("<NF>", t)
    # Número de medição / boletim de medição
    t = re.sub(r"\b\d+[ªºA]?\s*(?:MEDICAO|MED\.?)\b", "<MED>", t)
    t = re.sub(r"\b(?:MEDICAO|MED\.?|BOLETIM DE MEDICAO|BM)\s*(?:N[º°.]?\s*)?\d+\b", "<MED>", t)
    return " ".join(t.split())


def _extrair_nf(texto_norm: str) -> Optional[str]:
    """Extrai o número normalizado de NF/NFSE/NFE do texto da liquidação."""
    m = _REGEX_NF.search(texto_norm)
    if not m:
        return None
    return m.group(1).lstrip("0") or "0"


def _extrair_competencia(texto_norm: str, data_liquidacao: Any) -> Optional[str]:
    """Extrai competência MM/AAAA do texto, com fallback para mês/ano de `dataLiquidacao`."""
    m = _REGEX_COMPETENCIA.search(texto_norm)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    data_str = str(data_liquidacao or "").strip()
    if not data_str:
        return None
    m_iso = _REGEX_DATA_ISO.match(data_str)
    if m_iso:
        return f"{m_iso.group(2)}/{m_iso.group(1)}"
    m_br = _REGEX_DATA_BR.match(data_str)
    if m_br:
        return f"{m_br.group(1)}/{m_br.group(2)}"
    return None


def _detectar_pares_estorno_substituicao(liquidacoes: list[dict[str, Any]]) -> dict[int, list[str]]:
    """Detecta pares potenciais de estorno/substituição entre notas do mesmo contrato."""
    motivos_por_idx: dict[int, list[str]] = {}
    metadados: list[tuple[int, str, Optional[str], Optional[str], float]] = []

    for idx, liq in enumerate(liquidacoes):
        if not isinstance(liq, dict):
            continue
        nl = str(liq.get("notaLiquidacao") or "").strip()
        texto_norm = normalizar_nome(str(liq.get("descObsLiquidacao") or ""))
        nf = _extrair_nf(texto_norm)
        comp = _extrair_competencia(texto_norm, liq.get("dataLiquidacao"))
        val = parse_float(liq.get("valLiqLiquidacao") or 0.0)
        metadados.append((idx, nl, nf, comp, val))

    def _marcar(i: int, motivo: str) -> None:
        lista = motivos_por_idx.setdefault(i, [])
        if motivo not in lista:
            lista.append(motivo)

    for pos_a in range(len(metadados)):
        idx_a, nl_a, nf_a, comp_a, val_a = metadados[pos_a]
        for pos_b in range(pos_a + 1, len(metadados)):
            idx_b, nl_b, nf_b, comp_b, val_b = metadados[pos_b]
            if nl_a and nl_b and nl_a == nl_b:
                continue
            if nf_a and nf_b and nf_a == nf_b:
                _marcar(idx_a, "possivel_substituicao_mesma_nf")
                _marcar(idx_b, "possivel_substituicao_mesma_nf")
            if abs(val_a) > 0.0 and abs(val_a + val_b) < 0.01:
                _marcar(idx_a, "possivel_estorno_valor_simetrico")
                _marcar(idx_b, "possivel_estorno_valor_simetrico")
            if val_a > 0.0 and abs(val_a - val_b) < 0.01 and comp_a and comp_a == comp_b:
                _marcar(idx_a, "possivel_substituicao_mesmo_valor_competencia")
                _marcar(idx_b, "possivel_substituicao_mesmo_valor_competencia")

    return motivos_por_idx


_ESTAGIOS_CONFLITO = (
    "Multi-Bairro",
    "Múltiplos Equipamentos",
    "Múltiplas Prefeituras-Bairro",
)


def _avaliar_trilha_1_contrato(
    *,
    chave: str,
    obra: dict[str, Any],
    ficha: dict[str, Any],
    status_cur: str,
    equipamentos: list[dict[str, Any]],
    ctx: _ContextoTerritorialStage1,
) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    """Avalia um contrato opaco para Trilha 1 (candidato a `promovido` ou `lista_fechada`)."""
    if status_cur in {"ambiguo", "multi_frente", "promovido", "lista_fechada"}:
        return None, None

    aditivos = ficha.get("aditivos") or []
    liquidacoes = ficha.get("liquidacoes") or []

    evidencias: list[dict[str, Any]] = []
    bairros_evidencias: set[str] = set()
    pbs_evidencias: set[str] = set()
    bairros_em_liquidacoes: set[str] = set()
    conflito = False

    def _processar_texto(origem: str, referencia: str, texto_bruto: str) -> None:
        nonlocal conflito
        texto_limpo = str(texto_bruto or "").strip()
        if not texto_limpo:
            return
        res = _executar_estagio_1_deterministico(
            objeto_norm=normalizar_nome(texto_limpo),
            equipamentos=equipamentos,
            ctx=ctx,
        )
        if res is None:
            return
        nivel = str(res.get("nivel") or "")
        estagio = str(res.get("estagio") or "")
        if nivel in {"Pontual", "Bairro"} and res.get("bairro"):
            bairro = str(res["bairro"])
            pb = res.get("prefeitura_bairro")
            bairros_evidencias.add(bairro)
            if pb:
                pbs_evidencias.add(str(pb))
            if origem == "liquidacao":
                bairros_em_liquidacoes.add(bairro)
            evidencias.append({
                "origem": origem,
                "referencia": referencia,
                "texto": texto_limpo,
                "bairro": bairro,
                "prefeituraBairro": pb,
            })
        elif nivel == "Regional (Prefeitura-Bairro)" or any(
            marcador in estagio for marcador in _ESTAGIOS_CONFLITO
        ):
            conflito = True

    for idx_ad, ad in enumerate(aditivos, start=1):
        if isinstance(ad, dict):
            ref = str(ad.get("nuAditivo") or idx_ad)
            _processar_texto("aditivo", ref, str(ad.get("dsObjetoAditivo") or ad.get("dsObjeto") or ""))

    for idx_liq, liq in enumerate(liquidacoes, start=1):
        if isinstance(liq, dict):
            ref = str(liq.get("notaLiquidacao") or idx_liq)
            _processar_texto("liquidacao", ref, str(liq.get("descObsLiquidacao") or ""))

    if not conflito and len(bairros_evidencias) == 1 and evidencias:
        bairro_unico = next(iter(bairros_evidencias))
        pb_unica = next(iter(pbs_evidencias)) if pbs_evidencias else None
        return {
            "contrato": chave,
            "idObra": obra.get("id"),
            "dsObjeto": obra.get("dsObjeto") or ficha.get("dsObjeto"),
            "tipoSugestao": "promovido",
            "bairroSugerido": bairro_unico,
            "prefeituraBairroSugerida": pb_unica,
            "evidencias": evidencias,
        }, None

    # Candidato a lista_fechada: 2 a 8 bairros ou Equipamentos Públicos distintos em objeto/aditivos,
    # sem medição individualizada por bairro nas liquidações.
    if len(bairros_em_liquidacoes) >= 2:
        return None, None

    textos_contratuais = [
        ("objeto", str(obra.get("dsObjeto") or ficha.get("dsObjeto") or "")),
        *[
            (f"aditivo:{ad.get('nuAditivo', idx)}", str(ad.get("dsObjetoAditivo") or ad.get("dsObjeto") or ""))
            for idx, ad in enumerate(aditivos, start=1)
            if isinstance(ad, dict)
        ],
    ]
    achados_por_texto: list[tuple[str, str, list[str], list[str]]] = []
    bairros_de_eqs: set[str] = set()

    for ref_origem, txt in textos_contratuais:
        txt_norm = normalizar_nome(txt)
        if not txt_norm:
            continue
        eqs = _buscar_equipamentos_no_objeto(txt_norm, equipamentos)
        toponimos = _buscar_toponimos_blindados(txt_norm, ctx.bairros_nomes, ctx.dicionario_sublocalidades)
        bairros_txt = _deduplicar_bairros_canonicos(toponimos, ctx)
        nomes_eq = [str(eq.get("nome") or "").strip() for eq in eqs if str(eq.get("nome") or "").strip()]
        for eq in eqs:
            if eq.get("bairro"):
                bairros_de_eqs.add(str(eq["bairro"]))
        if nomes_eq or bairros_txt:
            achados_por_texto.append((ref_origem, txt.strip(), nomes_eq, bairros_txt))

    itens_identificados: list[str] = []
    evidencias_lf: list[dict[str, Any]] = []
    for ref_origem, txt_limpo, nomes_eq, bairros_txt in achados_por_texto:
        achados_neste_texto: list[str] = []
        for nome_eq in nomes_eq:
            if nome_eq not in itens_identificados:
                itens_identificados.append(nome_eq)
                achados_neste_texto.append(nome_eq)
        for b in bairros_txt:
            if b not in bairros_de_eqs and b not in itens_identificados:
                itens_identificados.append(b)
                achados_neste_texto.append(b)
        if achados_neste_texto:
            evidencias_lf.append({
                "origem": ref_origem,
                "texto": txt_limpo,
                "itens": achados_neste_texto,
            })

    if 2 <= len(itens_identificados) <= 8:
        return None, {
            "contrato": chave,
            "idObra": obra.get("id"),
            "dsObjeto": obra.get("dsObjeto") or ficha.get("dsObjeto"),
            "tipoSugestao": "lista_fechada",
            "totalItens": len(itens_identificados),
            "itensIdentificados": itens_identificados,
            "evidencias": evidencias_lf,
        }

    return None, None


_DELIMITADOR_TRILHA_3 = (
    r"(?=(?:\s*(?:[,;\-/(]|NF(?:SE|E)?\b|PROC\b|CONTR\b|BM\b|PER\b|SALVADOR\b|\bE\s+NO\b|\bE\s+NA\b|\d{2}/\d{4}|$)))"
)
_REGEX_EQ_PREFIXO = re.compile(
    r"(?<![A-Z0-9])"
    r"(ESCOLA(?:\s+MUNICIPAL)?|E\.?\s*M\.?|CMEI|USF|UBS|UPA|CRAS|CREAS|CAPS|HOSPITAL|MERCADO|PARQUE|POLICLINICA)"
    r"\s+([A-Z0-9][A-Z0-9\s]{1,55}?)"
    + _DELIMITADOR_TRILHA_3
)
_REGEX_SUBLOC_CANDIDATO = re.compile(
    r"(?<![A-Z0-9])"
    r"(?:BAIRRO|LOTEAMENTO|CONJUNTO|VILA|LOCALIDADE|CONDOMINIO|ALTO|BAIXA|VALE|FAZENDA)\s+"
    r"([A-Z0-9][A-Z0-9\s]{2,40}?)"
    + _DELIMITADOR_TRILHA_3
)
_STOPWORDS_FINAIS_TRILHA_3 = {"DE", "DA", "DO", "DOS", "DAS", "E", "EM", "NA", "NO"}


def _limpar_candidato_trilha_3(texto: str) -> str:
    """Remove preposições e conectivos soltos ao final de um candidato extraído."""
    palavras = texto.split()
    while palavras and palavras[-1] in _STOPWORDS_FINAIS_TRILHA_3:
        palavras.pop()
    return " ".join(palavras)


def _coletar_candidatos_trilha_3(
    *,
    textos_nao_localizados: list[str],
    equipamentos: list[dict[str, Any]],
    ctx: _ContextoTerritorialStage1,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extrai equipamentos públicos e sublocalidades recorrentes (>= 2) ausentes dos catálogos."""
    bairros_norm_set = {normalizar_nome(b) for b in ctx.bairros_nomes}
    eq_contagem: dict[str, dict[str, Any]] = {}
    sub_contagem: dict[str, dict[str, Any]] = {}

    for texto_bruto in textos_nao_localizados:
        texto_norm = normalizar_nome(texto_bruto)
        if not texto_norm:
            continue

        # Equipamentos
        for m in _REGEX_EQ_PREFIXO.finditer(texto_norm):
            prefixo_raw = m.group(1).strip()
            sufixo = _limpar_candidato_trilha_3(m.group(2).strip())
            if len(sufixo) < 3:
                continue
            prefixo_unif = "ESCOLA" if prefixo_raw.startswith(("ESCOLA", "E.")) or prefixo_raw == "E M" else prefixo_raw
            cand_norm = _normalizar_texto_equipamento(f"{prefixo_unif} {sufixo}")
            if _buscar_equipamentos_no_objeto(cand_norm, equipamentos):
                continue
            chave_eq = re.sub(r"^ESCOLA\s+MUNICIPAL\s+", "ESCOLA ", cand_norm)
            reg = eq_contagem.setdefault(
                chave_eq,
                {"nome": chave_eq, "tipo": prefixo_unif, "contagem": 0, "amostras": []},
            )
            reg["contagem"] += 1
            _adicionar_amostra_unica(reg["amostras"], texto_bruto)

        # Sublocalidades
        for m in _REGEX_SUBLOC_CANDIDATO.finditer(texto_norm):
            termo_limpo = _limpar_candidato_trilha_3(m.group(1).strip())
            if len(termo_limpo) < 3:
                continue
            if termo_limpo in bairros_norm_set or termo_limpo in ctx.sublocalidades_norm:
                continue
            if _buscar_toponimos_blindados(termo_limpo, ctx.bairros_nomes, ctx.dicionario_sublocalidades):
                continue
            reg = sub_contagem.setdefault(
                termo_limpo,
                {"termo": termo_limpo, "contagem": 0, "amostras": []},
            )
            reg["contagem"] += 1
            _adicionar_amostra_unica(reg["amostras"], texto_bruto)

    eq_lista = sorted(
        (v for v in eq_contagem.values() if v["contagem"] >= 2),
        key=lambda x: (-x["contagem"], x["nome"]),
    )
    sub_lista = sorted(
        (v for v in sub_contagem.values() if v["contagem"] >= 2),
        key=lambda x: (-x["contagem"], x["termo"]),
    )
    return eq_lista, sub_lista


def _renderizar_markdown(relatorio: dict[str, Any]) -> str:
    """Gera resumo legível em Markdown para as 3 trilhas de triagem."""
    s = relatorio["sumario"]
    linhas = [
        "# Triagem Territorial Assistida",
        "",
        "## Sumário",
        f"- Contratos analisados: {s['contratos_analisados']}",
        f"- Notas analisadas (não cobertas): {s['notas_analisadas']}",
        f"- Notas omitidas (cobertas por curadoria/regras): {s['notas_omitidas_cobertas']}",
        f"- Notas sem match territorial: {s['notas_sem_match_territorial']}",
        f"- Trilha 1 (Contratos promovíveis/lista fechada): {s['trilha_1_total']}",
        f"- Trilha 2 (Alta confiança): {s['trilha_2_grupos_alta_confianca']}",
        f"- Trilha 2 (Revisão manual): {s['trilha_2_grupos_revisao_manual']}",
        f"- Trilha 2 (Regionais): {s['trilha_2_grupos_regionais']}",
        f"- Trilha 3 (Equipamentos candidatos): {s['trilha_3_equipamentos']}",
        f"- Trilha 3 (Sublocalidades candidatas): {s['trilha_3_sublocalidades']}",
        "",
    ]

    linhas.append("## Trilha 1 — Contratos Promovíveis ou Lista Fechada")
    for c in relatorio["trilha_1_contratos"]["promoviveis"]:
        linhas.append(
            f"- **{c['contrato']}** (`promovido` -> {c['bairroSugerido']}) | "
            f"{len(c['evidencias'])} evidência(s)"
        )
    for c in relatorio["trilha_1_contratos"]["lista_fechada"]:
        linhas.append(
            f"- **{c['contrato']}** (`lista_fechada`, {c['totalItens']} itens: "
            f"{', '.join(c['itensIdentificados'])})"
        )
    linhas.append("")

    linhas.append("## Trilha 2 — Frentes de Medição Unitárias (Alta Confiança)")
    for g in relatorio["trilha_2_frentes_unitarias"]["alta_confianca"]:
        linhas.append(
            f"- **{g['contrato']}** | {g['bairroSugerido']} | {g['quantidadeNotas']} nota(s) | "
            f"Liquidado: R$ {g['valorLiquidado']:.2f} | Pago: R$ {g['valorPago']:.2f} | "
            f"`{g['assinaturaNormalizada']}`"
        )
    linhas.append("")

    linhas.append("## Trilha 2 — Revisão Manual")
    for g in relatorio["trilha_2_frentes_unitarias"]["revisao_manual"]:
        linhas.append(
            f"- **{g['contrato']}** | {g['bairroSugerido']} | {g['quantidadeNotas']} nota(s) | "
            f"Bloqueios: {', '.join(g['motivosBloqueio'])} | `{g['assinaturaNormalizada']}`"
        )
    linhas.append("")

    linhas.append("### Subseção Regional (Prefeitura-Bairro)")
    for g in relatorio["trilha_2_frentes_unitarias"]["regionais"]:
        linhas.append(
            f"- **{g['contrato']}** | {g['prefeituraBairroSugerida']} | {g['quantidadeNotas']} nota(s) | "
            f"Liquidado: R$ {g['valorLiquidado']:.2f} | Pago: R$ {g['valorPago']:.2f} | "
            f"`{g['assinaturaNormalizada']}`"
        )
    linhas.append("")

    linhas.append("## Trilha 3 — Catálogos de Referência (Candidatos Recorrentes)")
    for eq in relatorio["trilha_3_catalogos"]["equipamentos"]:
        linhas.append(f"- Equipamento: **{eq['nome']}** ({eq['contagem']} ocorrências)")
    for sub in relatorio["trilha_3_catalogos"]["sublocalidades"]:
        linhas.append(f"- Sublocalidade: **{sub['termo']}** ({sub['contagem']} ocorrências)")
    linhas.append("")
    return "\n".join(linhas)


def executar_triagem_territorial(
    data_dir: Path,
    out_dir: Path,
    curadoria_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Executa a Triagem Territorial Assistida 100% offline e grava JSON e Markdown."""
    data_path = Path(data_dir)
    out_path = Path(out_dir)
    base_dir = _resolver_diretorio_base(data_path)
    curadoria = _carregar_curadoria_somente_leitura(curadoria_path)
    bairros_geojson = _carregar_bairros_geojson(base_dir, data_path)
    ctx, equipamentos, bairro_para_pb, bairro_para_pb_norm = _construir_contexto_stage1(bairros_geojson)

    contratos = _carregar_contratos_e_fichas(base_dir)
    notas_omitidas_cobertas = 0
    notas_analisadas = 0
    notas_sem_match = 0

    grupos_t2: dict[tuple[str, str, str], dict[str, Any]] = {}
    grupos_regionais: dict[tuple[str, str, str], dict[str, Any]] = {}
    t1_promoviveis: list[dict[str, Any]] = []
    t1_lista_fechada: list[dict[str, Any]] = []
    textos_nao_localizados: list[str] = []

    for obra, ficha in contratos:
        chave = _chave_contrato(obra)
        entrada = curadoria.get(chave) if isinstance(curadoria.get(chave), dict) else {}
        status_cur = str(entrada.get("status") or "").strip().lower()
        frentes_curadas = entrada.get("frentesMedicao") if isinstance(entrada.get("frentesMedicao"), dict) else {}

        cand_prom, cand_lf = _avaliar_trilha_1_contrato(
            chave=chave,
            obra=obra,
            ficha=ficha,
            status_cur=status_cur,
            equipamentos=equipamentos,
            ctx=ctx,
        )
        if cand_prom is not None:
            t1_promoviveis.append(cand_prom)
        if cand_lf is not None:
            t1_lista_fechada.append(cand_lf)

        ds_obj = str(obra.get("dsObjeto") or ficha.get("dsObjeto") or "").strip()
        if ds_obj:
            res_obj = _executar_estagio_1_deterministico(
                objeto_norm=normalizar_nome(ds_obj),
                equipamentos=equipamentos,
                ctx=ctx,
            )
            if res_obj is None or res_obj.get("nivel") not in {"Pontual", "Bairro"}:
                textos_nao_localizados.append(ds_obj)
        for ad in ficha.get("aditivos") or []:
            if isinstance(ad, dict):
                txt_ad = str(ad.get("dsObjetoAditivo") or ad.get("dsObjeto") or "").strip()
                if txt_ad:
                    res_ad = _executar_estagio_1_deterministico(
                        objeto_norm=normalizar_nome(txt_ad),
                        equipamentos=equipamentos,
                        ctx=ctx,
                    )
                    if res_ad is None or res_ad.get("nivel") not in {"Pontual", "Bairro"}:
                        textos_nao_localizados.append(txt_ad)

        regras_preparadas: list[dict[str, Any]] = []
        if status_cur == "multi_frente" and entrada.get("regrasFrentes") is not None:
            regras_preparadas = validar_e_preparar_regras_frentes(
                entrada.get("regrasFrentes"),
                bairros_nomes=ctx.bairros_nomes,
                sublocalidades_norm=ctx.sublocalidades_norm,
                bairro_para_pb=bairro_para_pb,
                bairro_para_pb_norm=bairro_para_pb_norm,
                reconciliar_bairro=reconciliar_bairro_canonico,
            )

        pagamentos = ficha.get("pagamentos")
        pagamentos_por_nl = agrupar_pagamentos_por_nota(pagamentos)
        liquidacoes = ficha.get("liquidacoes") or []
        pares_estorno = _detectar_pares_estorno_substituicao(liquidacoes)

        for idx_liq, liq in enumerate(liquidacoes):
            if not isinstance(liq, dict):
                continue
            nl = str(liq.get("notaLiquidacao") or "").strip()
            if nl and nl in frentes_curadas:
                notas_omitidas_cobertas += 1
                continue
            if (
                regras_preparadas
                and not avaliar_guardrails_nota_liquidacao(
                    liq,
                    pagamentos_por_nl=pagamentos_por_nl if pagamentos is not None else None,
                )
                and selecionar_regra_frente(liq, regras_preparadas) is not None
            ):
                notas_omitidas_cobertas += 1
                continue

            notas_analisadas += 1
            texto_bruto = str(liq.get("descObsLiquidacao") or "").strip()
            resultado = _executar_estagio_1_deterministico(
                objeto_norm=normalizar_nome(texto_bruto),
                equipamentos=equipamentos,
                ctx=ctx,
            )
            if resultado is None or resultado.get("nivel") == "Escopo Cidade (Não-Localizado)":
                notas_sem_match += 1
                if texto_bruto:
                    textos_nao_localizados.append(texto_bruto)
                continue

            nivel = str(resultado.get("nivel") or "")
            motivos = avaliar_guardrails_nota_liquidacao(
                liq,
                pagamentos_por_nl=pagamentos_por_nl if pagamentos is not None else None,
            )
            for motivo_par in pares_estorno.get(idx_liq, []):
                if motivo_par not in motivos:
                    motivos.append(motivo_par)
            classificacao = "revisao_manual" if motivos else "alta_confianca"
            assinatura = normalizar_assinatura_frente(texto_bruto)
            val_liq = parse_float(liq.get("valLiqLiquidacao") or 0.0)
            val_pago = (
                pagamentos_por_nl.pop(nl, 0.0)
                if pagamentos is not None and nl
                else parse_float(liq.get("pago") or 0.0)
            )
            if val_pago is None:
                val_pago = 0.0

            destino = grupos_regionais if nivel == "Regional (Prefeitura-Bairro)" else grupos_t2
            chave_grupo = (chave, assinatura, classificacao)
            grupo = destino.get(chave_grupo)
            if grupo is None:
                grupo = {
                    "contrato": chave,
                    "idObra": obra.get("id"),
                    "assinaturaNormalizada": assinatura,
                    "classificacao": classificacao,
                    "nivelSugerido": nivel,
                    "bairroSugerido": resultado.get("bairro"),
                    "prefeituraBairroSugerida": resultado.get("prefeitura_bairro"),
                    "quantidadeNotas": 0,
                    "valorLiquidado": 0.0,
                    "valorPago": 0.0,
                    "amostrasTexto": [],
                    "notas": [],
                    "motivosBloqueio": [],
                }
                destino[chave_grupo] = grupo

            grupo["quantidadeNotas"] += 1
            grupo["valorLiquidado"] = round(grupo["valorLiquidado"] + val_liq, 2)
            grupo["valorPago"] = round(grupo["valorPago"] + val_pago, 2)
            _adicionar_amostra_unica(grupo["amostrasTexto"], texto_bruto)
            if nl:
                grupo["notas"].append(nl)
            for m in motivos:
                if m not in grupo["motivosBloqueio"]:
                    grupo["motivosBloqueio"].append(m)

    alta_confianca = [g for g in grupos_t2.values() if g["classificacao"] == "alta_confianca"]
    revisao_manual = [g for g in grupos_t2.values() if g["classificacao"] == "revisao_manual"]
    regionais = list(grupos_regionais.values())
    t3_equipamentos, t3_sublocalidades = _coletar_candidatos_trilha_3(
        textos_nao_localizados=textos_nao_localizados,
        equipamentos=equipamentos,
        ctx=ctx,
    )

    relatorio: dict[str, Any] = {
        "sumario": {
            "contratos_analisados": len(contratos),
            "notas_analisadas": notas_analisadas,
            "notas_omitidas_cobertas": notas_omitidas_cobertas,
            "notas_sem_match_territorial": notas_sem_match,
            "trilha_1_total": len(t1_promoviveis) + len(t1_lista_fechada),
            "trilha_2_grupos_alta_confianca": len(alta_confianca),
            "trilha_2_grupos_revisao_manual": len(revisao_manual),
            "trilha_2_grupos_regionais": len(regionais),
            "trilha_3_equipamentos": len(t3_equipamentos),
            "trilha_3_sublocalidades": len(t3_sublocalidades),
        },
        "trilha_1_contratos": {
            "promoviveis": t1_promoviveis,
            "lista_fechada": t1_lista_fechada,
        },
        "trilha_2_frentes_unitarias": {
            "alta_confianca": alta_confianca,
            "revisao_manual": revisao_manual,
            "regionais": regionais,
        },
        "trilha_3_catalogos": {
            "equipamentos": t3_equipamentos,
            "sublocalidades": t3_sublocalidades,
        },
    }

    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "triagem_territorial.json").write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_path / "triagem_territorial.md").write_text(
        _renderizar_markdown(relatorio),
        encoding="utf-8",
    )
    return relatorio


def main() -> None:
    """Ponto de entrada CLI para a Triagem Territorial Assistida offline."""
    parser = argparse.ArgumentParser(description="Triagem Territorial Assistida (100% offline)")
    parser.add_argument("--data-dir", required=True, type=str, help="Diretório raiz dos dados locais")
    parser.add_argument("--out", required=True, type=str, help="Diretório de saída dos relatórios")
    parser.add_argument(
        "--curadoria",
        type=str,
        default=None,
        help="Caminho opcional para catálogo de curadoria isolado (somente leitura)",
    )
    args = parser.parse_args()

    try:
        relatorio = executar_triagem_territorial(
            data_dir=Path(args.data_dir),
            out_dir=Path(args.out),
            curadoria_path=Path(args.curadoria) if args.curadoria else None,
        )
        print(json.dumps(relatorio["sumario"], ensure_ascii=False))
    except Exception as exc:
        print(f"Erro na triagem territorial: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

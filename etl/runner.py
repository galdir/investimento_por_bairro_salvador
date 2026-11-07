"""Ponto de entrada e orquestrador do pipeline ETL de Obras e Território de Salvador.

Coordena a extração das fontes governamentais, transformação dos dados territoriais,
execução do funil de alocação territorial com cache incremental em disco e gravação dos
artefatos estáticos particionados em conformidade com o ADR-0001.
"""

import json
from pathlib import Path
import shutil
from typing import Any

from etl.domain import kpis
from etl.domain.empreiteiras import (
    calcular_concentracao_empreiteiras,
    formatar_cnpj,
    obter_chave_empreiteira,
)
from etl.domain.ficha_limpa import construir_ficha_obra
from etl.domain.geocoding import (
    GeocodingCache,
    calcular_centroides_bairros,
    classificar_alocacao_territorial,
)
from etl.domain.mandato import (
    MANDATOS_MUNICIPAIS,
    classificar_mandatos_obra,
    deduplicar_obras,
    resolver_datas_vigencia,
)
from etl.domain.semaforo import classificar_semaforo
from etl.domain.tema import classificar_tema
from etl.domain.territorio import (
    calcular_rollup_territorial,
    is_zona_especial_nao_residencial,
    normalizar_e_vincular_malhas_geosalvador,
    normalizar_nome,
    normalizar_nome_prefeitura_bairro,
    parse_float,
)
from etl.generator import (
    generate_bairros_geojson,
    generate_index_json,
    generate_obra_detalhe_json,
    generate_prefeituras_geojson,
)
from etl.sources import geosalvador, ibge_censo, transparencia


def run_pipeline(
    output_dir: Path,
    year: int = 2025,
    cache_file: Path | None = None,
    mandatos: list[str] | None = None,
    full_refresh: bool = False,
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

    # 1. Extração das fontes de dados externas e normalização das malhas
    raw_bairros = geosalvador.fetch_bairros_geojson()
    raw_prefeituras = geosalvador.fetch_prefeituras_geojson()
    raw_bairros, raw_prefeituras = normalizar_e_vincular_malhas_geosalvador(raw_bairros, raw_prefeituras)
    demografia_map = ibge_censo.fetch_demografia_censo_2022()
    totalizador = transparencia.fetch_totalizador(year=year)

    # Coleta de obras para todos os mandatos municipais especificados com suporte incremental
    mandatos_lista = mandatos or list(MANDATOS_MUNICIPAIS.keys())
    raw_grid: list[dict[str, Any]] = []
    mandatos_consultar = list(mandatos_lista)
    closed_mandates_reused: set[str] = set()

    # Reuso incremental de mandatos encerrados (ex: 2021-2024)
    index_candidate = output_path / f"index_{year}.json"
    if not index_candidate.exists() and (output_path / "index_2025.json").exists():
        index_candidate = output_path / "index_2025.json"

    if not full_refresh and index_candidate.exists():
        try:
            with open(index_candidate, "r", encoding="utf-8") as f:
                existing_index = json.load(f)
            existing_obras = existing_index.get("obras", [])

            for m in mandatos_lista:
                info = MANDATOS_MUNICIPAIS.get(m)
                if info and info["fim"] < year:
                    has_obras_mandato = any(m in o.get("mandatos", []) for o in existing_obras)
                    if has_obras_mandato:
                        closed_mandates_reused.add(m)

            if closed_mandates_reused:
                mandatos_consultar = [m for m in mandatos_lista if m not in closed_mandates_reused]
                reused_obras: list[dict[str, Any]] = []
                for o in existing_obras:
                    if any(m in closed_mandates_reused for m in o.get("mandatos", [])):
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
                        reused_obras.append(item_copy)
                raw_grid.extend(reused_obras)
        except Exception:
            closed_mandates_reused.clear()
            mandatos_consultar = list(mandatos_lista)

    for m in mandatos_consultar:
        info = MANDATOS_MUNICIPAIS.get(m)
        if info:
            payload = {
                "dataInicio": info["data_inicio"],
                "dataFim": info["data_fim"],
                "filtros": [],
            }
            itens_mandato = transparencia.fetch_grid_detalhada(
                year=year,
                payload_customizado=payload,
            )
            raw_grid.extend(itens_mandato)
        else:
            raw_grid.extend(transparencia.fetch_grid_detalhada(year=year))

    if not raw_grid and not closed_mandates_reused:
        raw_grid = transparencia.fetch_grid_detalhada(year=year)

    # Deduplicação canônica por (cdUnidadeGestora, nuContratoSigef) e classificação de mandatos
    grid_obras = deduplicar_obras(raw_grid)

    # 2. Cálculo dos centróides dos Bairros Oficiais
    bairros_centroides = calcular_centroides_bairros(raw_bairros)

    # 3. Funil de Alocação Territorial com Cache Incremental
    cache_path = Path(cache_file) if cache_file is not None else (output_path / "geocoding_cache.json")
    cache = GeocodingCache(cache_file_path=cache_path)
    cache.reconciliar_entradas(raw_bairros, bairros_centroides)
    cache_hits = 0

    for obra in grid_obras:
        aloc = classificar_alocacao_territorial(
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

    # 4. Estruturação base de Bairros Oficiais
    demografia_norm = {normalizar_nome(k): v for k, v in demografia_map.items()}
    bairros_base: list[dict[str, Any]] = []

    for feat in raw_bairros.get("features", []):
        props = feat.get("properties", {})
        nome = (props.get("NM_BAIRRO") or props.get("nome") or props.get("NOME_BAIRR") or "").strip()
        b_id = props.get("CD_BAIRRO") or props.get("OBJECTID") or props.get("id") or 0
        pb = (props.get("PREFEITURA_BAIRRO") or props.get("prefeitura_bairro") or "").strip()

        nome_norm = normalizar_nome(nome)
        demo = demografia_norm.get(nome_norm, {"populacao": 0, "indice_vulnerabilidade": 0.5})
        eh_ze = is_zona_especial_nao_residencial(nome)

        bairros_base.append({
            "id": b_id,
            "nome": nome,
            "prefeitura_bairro": pb,
            "populacao": int(demo.get("populacao", 0)),
            "indice_vulnerabilidade": parse_float(demo.get("indice_vulnerabilidade", 0.5)),
            "is_zona_especial_nao_residencial": eh_ze,
            "isZonaEspecialNaoResidencial": eh_ze,
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

    # Classificação de Tema e Semáforo da Obra antes do rollup territorial
    for obra in grid_obras:
        obra["tema"] = classificar_tema(obra)
        obra["semaforo"] = classificar_semaforo(obra)

    # 6. Agregações e Rollup Territorial (Camada A)
    bairros_rollup, prefeituras_rollup, opacidade = calcular_rollup_territorial(
        bairros_resumo=bairros_base,
        prefeituras_resumo=prefeituras_base,
        obras_alocadas=grid_obras,
    )

    # 7. Geração das malhas GeoJSON enriquecidas
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

    # 8. Detalhamento individual das Obras Públicas (Ficha Limpa sob demanda) e Concentração
    concentracao_map = calcular_concentracao_empreiteiras(grid_obras)
    obras_dir = output_path / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)
    detail_cache_hits = 0

    for obra in grid_obras:
        cd_ug = obra.get("cdUnidadeGestora") or obra.get("unidadeGestora") or obra.get("sgOrgao")
        nu_sigef = obra.get("nuContratoSigef") or obra.get("numeroContrato")
        obra_id = obra.get("id")

        obra_file_path = obras_dir / f"{obra_id}.json"
        reaproveitar_detalhes = False

        if not full_refresh and obra_file_path.exists():
            try:
                with open(obra_file_path, "r", encoding="utf-8") as f:
                    persisted_ficha = json.load(f)

                vl_atua = parse_float(obra.get("vlAtualizado") or obra.get("valorContratualVigente") or obra.get("vlOriginal") or 0.0)
                perc_exec = parse_float(obra.get("percentualExecutado") or 0.0)
                ds_situacao = str(obra.get("dsSituacao") or obra.get("situacao") or "").strip()
                dt_termino = str(obra.get("dtTerminoVigenciaAtualizado") or resolver_datas_vigencia(obra)[1] or "").strip()

                p_funil = persisted_ficha.get("funilFinanceiro", {})
                p_vigencia = persisted_ficha.get("vigencia", {})
                p_vl_atua = parse_float(p_funil.get("valorContratualVigente") or persisted_ficha.get("vlAtualizado") or 0.0)
                p_perc_exec = parse_float(p_funil.get("percentualExecutado") or persisted_ficha.get("percentualExecutado") or 0.0)
                p_ds_situacao = str(persisted_ficha.get("situacao") or persisted_ficha.get("dsSituacao") or "").strip()
                p_dt_termino = str(p_vigencia.get("dataTerminoAtualizado") or persisted_ficha.get("dtTerminoVigenciaAtualizado") or "").strip()

                if (
                    vl_atua == p_vl_atua
                    and perc_exec == p_perc_exec
                    and ds_situacao == p_ds_situacao
                    and dt_termino == p_dt_termino
                ):
                    reaproveitar_detalhes = True
            except Exception:
                reaproveitar_detalhes = False

        if reaproveitar_detalhes:
            detail_cache_hits += 1
            cnpj_credor = persisted_ficha.get("empreiteira", {}).get("cnpj") or formatar_cnpj(str(obra.get("nuDocumentoCredor") or obra.get("cnpj") or ""))
            obra["cnpjCredor"] = cnpj_credor
            obra["cnpj"] = cnpj_credor
            nu_dom = persisted_ficha.get("dom", {}).get("nuDom") or obra.get("nuDom")
            if nu_dom:
                obra["nuDom"] = nu_dom
            p_vl_pago = persisted_ficha.get("funilFinanceiro", {}).get("valorPago")
            if p_vl_pago is not None:
                obra["vlPago"] = parse_float(p_vl_pago)

            razao_social = str(persisted_ficha.get("empreiteira", {}).get("razaoSocial") or obra.get("nmCredor") or "").strip()
            chave_emp = obter_chave_empreiteira(cnpj_credor, razao_social)
            if chave_emp in concentracao_map:
                persisted_ficha["empreiteira"] = concentracao_map[chave_emp]
                generate_obra_detalhe_json(persisted_ficha, obra_file_path)
        else:
            detalhe = transparencia.fetch_detalhes_obra(cd_ug, nu_sigef, year=year, obra_base=obra)
            aditivos_raw = transparencia.fetch_aditivos_obra(cd_ug, nu_sigef, year=year)
            dotacoes_raw = transparencia.fetch_dotacao_obra(cd_ug, nu_sigef, year=year)
            empenhos_raw = transparencia.fetch_empenhos_obra(cd_ug, nu_sigef, year=year)
            liquidacoes_raw = transparencia.fetch_liquidacoes_obra(cd_ug, nu_sigef, year=year)
            pagamentos_raw = transparencia.fetch_pagamentos_obra(cd_ug, nu_sigef, year=year)

            cnpj_credor = formatar_cnpj(str(detalhe.get("nuDocumentoCredor") or obra.get("nuDocumentoCredor") or ""))
            obra["cnpjCredor"] = cnpj_credor
            obra["cnpj"] = cnpj_credor
            nu_dom = detalhe.get("nuDom") or obra.get("nuDom")
            if nu_dom:
                obra["nuDom"] = nu_dom

            ficha_obra = construir_ficha_obra(
                obra=obra,
                detalhe=detalhe,
                aditivos_raw=aditivos_raw,
                dotacoes_raw=dotacoes_raw,
                empenhos_raw=empenhos_raw,
                liquidacoes_raw=liquidacoes_raw,
                pagamentos_raw=pagamentos_raw,
                concentracao_map=concentracao_map,
                year=year,
            )

            obra_file_path = obras_dir / f"{obra_id}.json"
            generate_obra_detalhe_json(ficha_obra, obra_file_path)

    # 9. Cálculo dos KPIs globais enriquecidos com transparência opaca
    populacao_cidade = sum(int(b.get("populacao", 0)) for b in bairros_rollup)
    kpis_globais = kpis.calcular_kpis_globais(
        totalizador_transparencia=totalizador,
        obras_detalhadas=grid_obras,
        populacao_total_cidade=populacao_cidade,
        indicador_opacidade=opacidade,
    )

    # 10. Geração do índice anual estático com concentração de empreiteiras e mandatos
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

    # Cria alias index_2025.json e index.json quando aplicável
    for alias_name in ["index_2025.json", "index.json"]:
        alias_path = output_path / alias_name
        if alias_path.resolve() != index_file_path.resolve():
            try:
                shutil.copyfile(index_file_path, alias_path)
            except Exception:
                pass

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
    }

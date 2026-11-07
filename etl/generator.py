"""Gerador de artefatos estáticos (GeoJSON e JSON) do subsistema ETL.

Escreve os arquivos particionados no formato exigido pela arquitetura estática (ADR-0001)
e pelo painel web no GitHub Pages.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Optional

from etl.domain.empreiteiras import formatar_cnpj
from etl.domain.mandato import (
    MANDATOS_MUNICIPAIS,
    classificar_mandatos_obra,
    extrair_ano_data,
    resolver_datas_vigencia,
)
from etl.domain.semaforo import classificar_semaforo
from etl.domain.tema import classificar_tema
from etl.domain.territorio import is_zona_especial_nao_residencial, normalizar_nome, parse_float


def generate_bairros_geojson(
    raw_bairros_geojson: dict[str, Any],
    bairros_resumo: list[dict[str, Any]],
    output_path: Path,
) -> None:
    """Gera o arquivo `geo/bairros.geojson` com atributos sociodemográficos e financeiros integrados.

    Sumário:
        Combina a malha geográfica de bairros com os dados demográficos e financeiros calculados no rollup.

    Descrição Estendida:
        Percorre cada feature da malha oficial do GeoSalvador (Camada 164), pareia pelo nome normalizado
        com a lista de bairros processada pelo rollup territorial e salva as propriedades atualizadas
        (população, índice de vulnerabilidade, valorTotal, investimentoPorHabitante, totalObras e
        isZonaEspecialNaoResidencial) na FeatureCollection GeoJSON em EPSG:4326.

    Argumentos:
        raw_bairros_geojson: GeoJSON bruto extraído do GeoSalvador.
        bairros_resumo: Lista consolidada com dados de cada bairro oficial após o rollup territorial.
        output_path: Caminho completo do arquivo `bairros.geojson` a ser criado.

    Retornos:
        None.

    Erros:
        Lança IOError se o arquivo não puder ser gravado no diretório.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Índice de bairros normalizados para busca imediata O(1)
    bairros_map = {normalizar_nome(b.get("nome", "")): b for b in bairros_resumo}

    features_limpas: list[dict[str, Any]] = []

    for feat in raw_bairros_geojson.get("features", []):
        props = feat.get("properties", {})
        nome = (props.get("NM_BAIRRO") or props.get("nome") or props.get("NOME_BAIRR") or "").strip()
        bairro_id = props.get("CD_BAIRRO") or props.get("OBJECTID") or props.get("id") or 0
        pb_nome = (props.get("PREFEITURA_BAIRRO") or props.get("prefeitura_bairro") or "").strip()

        nome_norm = normalizar_nome(nome)
        dados_rollup = bairros_map.get(nome_norm, {})

        eh_zona_especial = is_zona_especial_nao_residencial(nome) or dados_rollup.get("isZonaEspecialNaoResidencial", False)

        propriedades_finais = {
            "id": bairro_id,
            "nome": nome,
            "prefeitura_bairro": pb_nome or dados_rollup.get("prefeitura_bairro", ""),
            "populacao": int(dados_rollup.get("populacao", 0)),
            "indice_vulnerabilidade": parse_float(dados_rollup.get("indice_vulnerabilidade", 0.5)),
            "is_zona_especial_nao_residencial": eh_zona_especial,
            "isZonaEspecialNaoResidencial": eh_zona_especial,
            "valorTotal": parse_float(dados_rollup.get("valorTotal", 0.0)),
            "valorPago": parse_float(dados_rollup.get("valorPago", 0.0)),
            "totalObras": int(dados_rollup.get("totalObras", 0)),
            "investimentoPorHabitante": parse_float(dados_rollup.get("investimentoPorHabitante", 0.0)),
            "investimentoPorHabitantePago": parse_float(dados_rollup.get("investimentoPorHabitantePago", 0.0)),
            "obrasVerde": int(dados_rollup.get("obrasVerde", 0)),
            "obrasAmarelo": int(dados_rollup.get("obrasAmarelo", 0)),
            "obrasVermelho": int(dados_rollup.get("obrasVermelho", 0)),
        }

        features_limpas.append({
            "type": "Feature",
            "properties": propriedades_finais,
            "geometry": feat.get("geometry"),
        })

    geojson_final = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": features_limpas,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson_final, f, ensure_ascii=False, indent=2)


def generate_prefeituras_geojson(
    raw_pb_geojson: dict[str, Any],
    prefeituras_resumo: list[dict[str, Any]],
    output_path: Path,
) -> None:
    """Gera o arquivo `geo/prefeituras_bairro.geojson` com agregação de população e investimentos.

    Sumário:
        Processa os polígonos das Prefeituras-Bairro e integra as métricas consolidadas de investimento.

    Descrição Estendida:
        Para cada Prefeitura-Bairro presente no GeoSalvador (Camada 7), associa as somas de população,
        valor total investido, investimento por habitante e contagem de obras agregadas pelo rollup territorial.

    Argumentos:
        raw_pb_geojson: GeoJSON bruto das Prefeituras-Bairro do GeoSalvador.
        prefeituras_resumo: Lista com os resumos de cada prefeitura-bairro pós-rollup territorial.
        output_path: Caminho completo do arquivo `prefeituras_bairro.geojson` a ser gravado.

    Retornos:
        None.

    Erros:
        Lança IOError se a escrita em disco falhar.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pb_map = {normalizar_nome(pb.get("nome", "")): pb for pb in prefeituras_resumo}
    features_limpas: list[dict[str, Any]] = []

    for feat in raw_pb_geojson.get("features", []):
        props = feat.get("properties", {})
        nome = (props.get("NM_PREFEITURA_BAIRRO") or props.get("nome") or props.get("NOMES") or "").strip()
        pb_id = props.get("CD_PREFEITURA_BAIRRO") or props.get("OBJECTID") or props.get("id") or 0

        nome_norm = normalizar_nome(nome)
        dados_rollup = pb_map.get(nome_norm, {})

        propriedades_finais = {
            "id": pb_id,
            "nome": nome,
            "populacao_total": int(dados_rollup.get("populacao_total", 0)),
            "valorTotal": parse_float(dados_rollup.get("valorTotal", 0.0)),
            "valorPago": parse_float(dados_rollup.get("valorPago", 0.0)),
            "totalObras": int(dados_rollup.get("totalObras", 0)),
            "investimentoPorHabitante": parse_float(dados_rollup.get("investimentoPorHabitante", 0.0)),
            "investimentoPorHabitantePago": parse_float(dados_rollup.get("investimentoPorHabitantePago", 0.0)),
            "obrasVerde": int(dados_rollup.get("obrasVerde", 0)),
            "obrasAmarelo": int(dados_rollup.get("obrasAmarelo", 0)),
            "obrasVermelho": int(dados_rollup.get("obrasVermelho", 0)),
        }

        features_limpas.append({
            "type": "Feature",
            "properties": propriedades_finais,
            "geometry": feat.get("geometry"),
        })

    geojson_final = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": features_limpas,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson_final, f, ensure_ascii=False, indent=2)


def generate_index_json(
    kpis_globais: dict[str, Any],
    bairros_resumo: list[dict[str, Any]],
    prefeituras_resumo: list[dict[str, Any]],
    obras_detalhadas: list[dict[str, Any]],
    year: int,
    output_path: Path,
    concentracao_empreiteiras: Optional[Any] = None,
    mandatos_disponiveis: Optional[list[str]] = None,
) -> None:
    """Gera o arquivo de índice anual estático `index_<ano>.json`.

    Sumário:
        Consolida metadados, KPIs globais, resumos territoriais, concentração de empreiteiras e obras em formato JSON compacto.

    Descrição Estendida:
        Gera o arquivo principal consumido pelo painel web no carregamento inicial, incluindo
        a lista compacta de obras com nível de alocação territorial, coordenadas geográficas,
        tema funcional, semáforo de risco e o sumário de concentração de empreiteiras da cidade.

    Argumentos:
        kpis_globais: Dicionário com os indicadores globais e métricas de opacidade.
        bairros_resumo: Lista consolidada com dados de cada bairro oficial.
        prefeituras_resumo: Lista consolidada com dados de cada prefeitura-bairro.
        obras_detalhadas: Lista com os contratos de obras públicas vigentes.
        year: Ano de referência da publicação (ex: 2025).
        output_path: Caminho completo de saída do arquivo `index_<ano>.json`.
        concentracao_empreiteiras: Dicionário ou lista com resumo consolidado de empreiteiras.

    Retornos:
        None.

    Erros:
        Lança IOError se houver falha de gravação no caminho de saída.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Formata a lista compacta de obras públicas para a visão inicial, mapa (pinos) e tabela
    obras_compactas = []
    for o in obras_detalhadas:
        vl_orig = parse_float(o.get("vlOriginal") or o.get("valorOriginal") or 0.0)
        vl_atua = parse_float(o.get("vlAtualizado") or o.get("valorContratualVigente") or vl_orig)
        valor_aditivos = round(max(0.0, vl_atua - vl_orig), 2)
        delta_percentual = round(((vl_atua - vl_orig) / vl_orig) * 100.0, 2) if vl_orig > 0 else 0.0

        # Percentual executado e estimativa do valor pago/liquidado
        perc_exec = parse_float(o.get("percentualExecutado") or 0.0)
        vl_pago = parse_float(o.get("vlPago") or o.get("valorPago") or round(vl_atua * (perc_exec / 100.0), 2))

        # Classificações determinísticas de Tema e Semáforo da Obra
        tema = classificar_tema(o)
        semaforo = o.get("semaforo") or classificar_semaforo(o)

        # Mandatos Municipais e vigência
        mandatos_obra = o.get("mandatos") or classificar_mandatos_obra(o)
        dt_inicio, dt_fim = resolver_datas_vigencia(o)

        # Extração de ano da obra
        ano_obra = (
            extrair_ano_data(dt_inicio)
            or extrair_ano_data(o.get("dtInicioVigencia"))
            or extrair_ano_data(o.get("ano"))
            or year
        )

        # Atributos de alocação territorial
        nivel = o.get("nivel") or "Escopo Cidade (Não-Localizado)"
        bairro = o.get("bairro")
        prefeitura_bairro = o.get("prefeitura_bairro")
        lat = o.get("latitude")
        lon = o.get("longitude")
        estagio = o.get("estagioAlocacao")
        cnpj_credor = formatar_cnpj(str(o.get("nuDocumentoCredor") or o.get("cnpj") or o.get("cnpjCredor") or ""))

        obras_compactas.append({
            "id": o.get("id"),
            "cdUnidadeGestora": o.get("cdUnidadeGestora"),
            "unidadeGestora": o.get("sgOrgao") or o.get("dsUnidadeGestora") or o.get("unidadeGestora"),
            "nuContratoSigef": o.get("nuContratoSigef") or o.get("numeroContrato"),
            "numeroContrato": o.get("nuContratoSigef") or o.get("numeroContrato"),
            "objeto": o.get("dsObjeto"),
            "valorOriginal": vl_orig,
            "valorContratualVigente": vl_atua,
            "valorAditivos": valor_aditivos,
            "deltaPercentualValor": delta_percentual,
            "valorPago": vl_pago,
            "percentualExecutado": perc_exec,
            "situacao": o.get("dsSituacao"),
            "credor": o.get("nmCredor"),
            "cnpj": cnpj_credor,
            "cnpjCredor": cnpj_credor,
            "tema": tema,
            "semaforo": semaforo,
            "ano": ano_obra,
            "mandatos": mandatos_obra,
            "dtInicioVigencia": dt_inicio,
            "dtTerminoVigenciaAtualizado": dt_fim,
            "nivel": nivel,
            "bairro": bairro,
            "prefeituraBairro": prefeitura_bairro,
            "prefeitura_bairro": prefeitura_bairro,
            "latitude": lat,
            "longitude": lon,
            "estagioAlocacao": estagio,
        })

    # Converte concentração de empreiteiras para lista/dicionário ordenado
    conc_payload: list[dict[str, Any]] = []
    if concentracao_empreiteiras:
        if isinstance(concentracao_empreiteiras, dict):
            conc_payload = sorted(
                list(concentracao_empreiteiras.values()),
                key=lambda x: x.get("valorTotalContratado", 0.0),
                reverse=True,
            )
        elif isinstance(concentracao_empreiteiras, list):
            conc_payload = concentracao_empreiteiras

    payload = {
        "metadata": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "anoReferencia": year,
            "mandatosDisponiveis": mandatos_disponiveis or list(MANDATOS_MUNICIPAIS.keys()),
        },
        "kpis_globais": kpis_globais,
        "concentracao_empreiteiras": conc_payload,
        "prefeituras_bairro": prefeituras_resumo,
        "bairros": bairros_resumo,
        "obras": obras_compactas,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def generate_obra_detalhe_json(
    obra_detalhe: dict[str, Any],
    output_path: Path,
) -> None:
    """Gera o arquivo JSON individual particionado da Ficha Limpa da Obra sob demanda (`obras/<id>.json`).

    Sumário:
        Escreve o JSON detalhado de uma obra pública com Funil Financeiro, Aditivos, Dotação e Empreiteira.

    Descrição Estendida:
        Serializa em arquivo JSON individual o prontuário completo da obra para viabilizar
        carregamento assíncrono (sob demanda) na web, sem onerar o tamanho do pacote inicial.

    Argumentos:
        obra_detalhe: Dicionário contendo a Ficha Limpa completa da obra.
        output_path: Caminho completo de saída do arquivo `obras/<id>.json`.

    Retornos:
        None.

    Erros:
        Lança IOError se o arquivo não puder ser criado no caminho especificado.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(obra_detalhe, f, ensure_ascii=False, indent=2)


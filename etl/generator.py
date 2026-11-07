"""Gerador de artefatos estáticos (GeoJSON e JSON) do subsistema ETL.

Escreve os arquivos particionados no formato exigido pela arquitetura estática (ADR-0001)
e pelo painel web no GitHub Pages.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from etl.domain.semaforo import classificar_semaforo
from etl.domain.tema import classificar_tema
from etl.domain.territorio import is_zona_especial_nao_residencial, normalizar_nome


def generate_bairros_geojson(
    raw_bairros_geojson: dict[str, Any],
    demografia_map: dict[str, dict[str, Any]],
    output_path: Path,
) -> list[dict[str, Any]]:
    """Gera o arquivo `geo/bairros.geojson` com atributos sociodemográficos integrados.

    Sumário:
        Combina a malha geográfica de bairros com os dados do Censo 2022 do IBGE.

    Descrição Estendida:
        Percorre cada feature da malha oficial do GeoSalvador (Camada 164), normaliza o nome
        do bairro para casar com a base do Censo 2022 e associa os valores de população residente,
        índice de vulnerabilidade e o indicador booleano `isZonaEspecialNaoResidencial`.
        Disponibiliza as chaves tanto em camelCase quanto em snake_case para compatibilidade.
        Salva o resultado formatado em JSON com codificação UTF-8 no caminho especificado.

    Argumentos:
        raw_bairros_geojson: GeoJSON bruto extraído do GeoSalvador.
        demografia_map: Dicionário mapeando nome do bairro para dados de população e vulnerabilidade.
        output_path: Caminho completo do arquivo `bairros.geojson` a ser criado.

    Retornos:
        Lista com o resumo cadastral de cada bairro processado para composição do índice anual.

    Erros:
        Lança IOError se o arquivo não puder ser gravado no diretório.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Cria índice auxiliar com chaves normalizadas para matching flexível
    demografia_norm = {normalizar_nome(k): v for k, v in demografia_map.items()}

    bairros_resumo: list[dict[str, Any]] = []
    features_limpas: list[dict[str, Any]] = []

    for feat in raw_bairros_geojson.get("features", []):
        props = feat.get("properties", {})
        nome = (props.get("NM_BAIRRO") or props.get("nome") or "").strip()
        bairro_id = props.get("CD_BAIRRO") or props.get("OBJECTID") or props.get("id") or 0
        pb_nome = (props.get("PREFEITURA_BAIRRO") or props.get("prefeitura_bairro") or "").strip()

        nome_norm = normalizar_nome(nome)
        demo = demografia_norm.get(nome_norm, {"populacao": 0, "indice_vulnerabilidade": 0.5})

        eh_zona_especial = is_zona_especial_nao_residencial(nome)

        propriedades_finais = {
            "id": bairro_id,
            "nome": nome,
            "prefeitura_bairro": pb_nome,
            "populacao": int(demo.get("populacao", 0)),
            "indice_vulnerabilidade": float(demo.get("indice_vulnerabilidade", 0.5)),
            "is_zona_especial_nao_residencial": eh_zona_especial,
            "isZonaEspecialNaoResidencial": eh_zona_especial,
        }

        bairros_resumo.append(propriedades_finais)

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

    return bairros_resumo


def generate_prefeituras_geojson(
    raw_pb_geojson: dict[str, Any],
    bairros_resumo: list[dict[str, Any]],
    output_path: Path,
) -> list[dict[str, Any]]:
    """Gera o arquivo `geo/prefeituras_bairro.geojson` com agregação de população.

    Sumário:
        Processa os polígonos das Prefeituras-Bairro e soma as populações dos seus bairros.

    Descrição Estendida:
        Para cada Prefeitura-Bairro presente na Camada 7 do GeoSalvador, agrega a população
        residente dos bairros oficiais que compõem sua circunscrição administrativa e salva
        a FeatureCollection GeoJSON em EPSG:4326.

    Argumentos:
        raw_pb_geojson: GeoJSON bruto das Prefeituras-Bairro do GeoSalvador.
        bairros_resumo: Lista com os resumos de bairros contendo nome e população.
        output_path: Caminho completo do arquivo `prefeituras_bairro.geojson` a ser gravado.

    Retornos:
        Lista com o resumo de cada prefeitura-bairro contendo id, nome e população total.

    Erros:
        Lança IOError se a escrita em disco falhar.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Agrupa população por prefeitura-bairro usando nomes normalizados
    pop_por_pb: dict[str, int] = {}
    for b in bairros_resumo:
        pb_norm = normalizar_nome(b.get("prefeitura_bairro", ""))
        pop_por_pb[pb_norm] = pop_por_pb.get(pb_norm, 0) + int(b.get("populacao", 0))

    prefeituras_resumo: list[dict[str, Any]] = []
    features_limpas: list[dict[str, Any]] = []

    for feat in raw_pb_geojson.get("features", []):
        props = feat.get("properties", {})
        nome = (props.get("NM_PREFEITURA_BAIRRO") or props.get("nome") or "").strip()
        pb_id = props.get("CD_PREFEITURA_BAIRRO") or props.get("OBJECTID") or props.get("id") or 0

        nome_norm = normalizar_nome(nome)
        pop_total = pop_por_pb.get(nome_norm, 0)

        propriedades_finais = {
            "id": pb_id,
            "nome": nome,
            "populacao_total": pop_total,
        }

        prefeituras_resumo.append(propriedades_finais)

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

    return prefeituras_resumo


def generate_index_json(
    kpis_globais: dict[str, Any],
    bairros_resumo: list[dict[str, Any]],
    prefeituras_resumo: list[dict[str, Any]],
    obras_detalhadas: list[dict[str, Any]],
    year: int,
    output_path: Path,
) -> None:
    """Gera o arquivo de índice anual estático `index_<ano>.json`.

    Sumário:
        Consolida metadados, KPIs globais, resumos territoriais e obras em formato JSON compacto.

    Descrição Estendida:
        Gera o arquivo principal consumido pelo painel web no carregamento inicial, evitando
        requisições pesadas adicionais para carregar os números gerais do município.

    Argumentos:
        kpis_globais: Dicionário com os indicadores globais calculados.
        bairros_resumo: Lista consolidada com dados de cada bairro oficial.
        prefeituras_resumo: Lista consolidada com dados de cada prefeitura-bairro.
        obras_detalhadas: Lista com os contratos de obras públicas vigentes.
        year: Ano de referência da publicação (ex: 2025).
        output_path: Caminho completo de saída do arquivo `index_<ano>.json`.

    Retornos:
        None.

    Erros:
        Lança IOError se houver falha de gravação no caminho de saída.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Formata a lista compacta de obras públicas para a visão inicial e tabela detalhada
    obras_compactas = []
    for o in obras_detalhadas:
        vl_orig = float(o.get("vlOriginal") or o.get("valorOriginal") or 0.0)
        vl_atua = float(o.get("vlAtualizado") or o.get("valorContratualVigente") or vl_orig)
        valor_aditivos = round(max(0.0, vl_atua - vl_orig), 2)
        delta_percentual = round(((vl_atua - vl_orig) / vl_orig) * 100.0, 2) if vl_orig > 0 else 0.0

        # Percentual executado e estimativa do valor pago/liquidado
        perc_exec = float(o.get("percentualExecutado") or 0.0)
        vl_pago = float(o.get("vlPago") or o.get("valorPago") or round(vl_atua * (perc_exec / 100.0), 2))

        # Classificações determinísticas de Tema e Semáforo da Obra
        tema = classificar_tema(o)
        semaforo = classificar_semaforo(o)

        # Extração de ano da obra
        ano_obra = year
        if o.get("dtInicioVigencia"):
            try:
                ano_obra = int(str(o["dtInicioVigencia"])[:4])
            except Exception:
                pass

        obras_compactas.append({
            "id": o.get("id"),
            "unidadeGestora": o.get("sgOrgao") or o.get("dsUnidadeGestora"),
            "numeroContrato": o.get("nuContratoSigef"),
            "objeto": o.get("dsObjeto"),
            "valorOriginal": vl_orig,
            "valorContratualVigente": vl_atua,
            "valorAditivos": valor_aditivos,
            "deltaPercentualValor": delta_percentual,
            "valorPago": vl_pago,
            "percentualExecutado": perc_exec,
            "situacao": o.get("dsSituacao"),
            "credor": o.get("nmCredor"),
            "tema": tema,
            "semaforo": semaforo,
            "ano": ano_obra,
        })

    payload = {
        "metadata": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "anoReferencia": year,
        },
        "kpis_globais": kpis_globais,
        "prefeituras_bairro": prefeituras_resumo,
        "bairros": bairros_resumo,
        "obras": obras_compactas,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

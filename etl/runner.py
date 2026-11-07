"""Ponto de entrada e orquestrador do pipeline ETL de Obras e Território de Salvador.

Coordena a extração das fontes governamentais, transformação dos dados territoriais,
execução do funil de alocação territorial com cache incremental em disco e gravação dos
artefatos estáticos particionados em conformidade com o ADR-0001.
"""

from pathlib import Path
from typing import Any

from etl.domain import kpis
from etl.domain.geocoding import (
    GeocodingCache,
    calcular_centroides_bairros,
    classificar_alocacao_territorial,
)
from etl.domain.territorio import (
    calcular_rollup_territorial,
    is_zona_especial_nao_residencial,
    normalizar_nome,
)
from etl.generator import (
    generate_bairros_geojson,
    generate_index_json,
    generate_prefeituras_geojson,
)
from etl.sources import geosalvador, ibge_censo, transparencia


def run_pipeline(output_dir: Path, year: int = 2025) -> dict[str, Any]:
    """Executa o pipeline completo de extração, geocodificação territorial, rollup e geração de artefatos.

    Sumário:
        Orquestra a coleta de malhas, censo, transparência, funil de alocação territorial e artefatos estáticos.

    Descrição Estendida:
        1. Extrai as malhas de Bairros Oficiais (Camada 164) e Prefeituras-Bairro (Camada 7) do GeoSalvador.
        2. Extrai dados demográficos e de vulnerabilidade do Censo 2022 do IBGE.
        3. Extrai totalizadores e contratos detalhados de Obras Públicas da Transparência de Salvador.
        4. Calcula os centróides geométricos dos Bairros Oficiais.
        5. Executa o Funil de Alocação Territorial em 3 estágios com cache incremental em disco.
        6. Aplica as regras de rollup financeiro (Camada A) por Bairro Oficial e por Prefeitura-Bairro.
        7. Gera `geo/bairros.geojson` e `geo/prefeituras_bairro.geojson` enriquecidos com métricas de investimento.
        8. Consolida os KPIs municipais de investimento (incluindo transparência opaca) e gera `index_<ano>.json`.

    Argumentos:
        output_dir: Diretório base onde a árvore de artefatos estáticos (`geo/`, `index_<ano>.json`) será gravada.
        year: Ano de referência da execução do pipeline (padrão: 2025).

    Retornos:
        Dicionário com status da execução, contendo:
        - 'success': Booleano indicando se o pipeline foi concluído com êxito.
        - 'output_dir': Caminho em string do diretório de saída gerado.
        - 'ano': Ano processado.
        - 'total_bairros': Quantidade de bairros oficiais processados.
        - 'total_prefeituras': Quantidade de prefeituras-bairro processadas.
        - 'total_obras': Quantidade de obras listadas.

    Erros:
        Lança exceções caso ocorra erro irrecuperável durante a extração ou gravação dos arquivos.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Extração das fontes de dados externas
    raw_bairros = geosalvador.fetch_bairros_geojson()
    raw_prefeituras = geosalvador.fetch_prefeituras_geojson()
    demografia_map = ibge_censo.fetch_demografia_censo_2022()
    totalizador = transparencia.fetch_totalizador(year=year)
    grid_obras = transparencia.fetch_grid_detalhada(year=year)

    # 2. Cálculo dos centróides dos Bairros Oficiais
    bairros_centroides = calcular_centroides_bairros(raw_bairros)

    # 3. Funil de Alocação Territorial com Cache Incremental
    cache_path = output_path / "geocoding_cache.json"
    cache = GeocodingCache(cache_file_path=cache_path)

    for obra in grid_obras:
        aloc = classificar_alocacao_territorial(
            obra=obra,
            bairros_geojson=raw_bairros,
            bairros_centroides=bairros_centroides,
            cache=cache,
        )
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
            "indice_vulnerabilidade": float(demo.get("indice_vulnerabilidade", 0.5)),
            "is_zona_especial_nao_residencial": eh_ze,
            "isZonaEspecialNaoResidencial": eh_ze,
        })

    # 5. Estruturação base de Prefeituras-Bairro com agregação populacional
    pop_por_pb: dict[str, int] = {}
    for b in bairros_base:
        pb_norm = normalizar_nome(b.get("prefeitura_bairro", ""))
        pop_por_pb[pb_norm] = pop_por_pb.get(pb_norm, 0) + int(b.get("populacao", 0))

    prefeituras_base: list[dict[str, Any]] = []
    for feat in raw_prefeituras.get("features", []):
        props = feat.get("properties", {})
        nome = (props.get("NM_PREFEITURA_BAIRRO") or props.get("nome") or props.get("NOMES") or "").strip()
        pb_id = props.get("CD_PREFEITURA_BAIRRO") or props.get("OBJECTID") or props.get("id") or 0
        pop_total = pop_por_pb.get(normalizar_nome(nome), 0)

        prefeituras_base.append({
            "id": pb_id,
            "nome": nome,
            "populacao_total": pop_total,
        })

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

    # 8. Cálculo dos KPIs globais enriquecidos com transparência opaca
    populacao_cidade = sum(int(b.get("populacao", 0)) for b in bairros_rollup)
    kpis_globais = kpis.calcular_kpis_globais(
        totalizador_transparencia=totalizador,
        obras_detalhadas=grid_obras,
        populacao_total_cidade=populacao_cidade,
        indicador_opacidade=opacidade,
    )

    # 9. Geração do índice anual estático
    index_file_path = output_path / f"index_{year}.json"
    generate_index_json(
        kpis_globais=kpis_globais,
        bairros_resumo=bairros_rollup,
        prefeituras_resumo=prefeituras_rollup,
        obras_detalhadas=grid_obras,
        year=year,
        output_path=index_file_path,
    )

    return {
        "success": True,
        "output_dir": str(output_path),
        "ano": year,
        "total_bairros": len(bairros_rollup),
        "total_prefeituras": len(prefeituras_rollup),
        "total_obras": len(grid_obras),
    }

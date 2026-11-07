"""Ponto de entrada e orquestrador do pipeline ETL de Obras e Território de Salvador.

Coordena a extração das fontes governamentais, transformação dos dados territoriais
e gravação dos artefatos estáticos particionados em conformidade com o ADR-0001.
"""

from pathlib import Path
from typing import Any

from etl.domain import kpis
from etl.generator import (
    generate_bairros_geojson,
    generate_index_json,
    generate_prefeituras_geojson,
)
from etl.sources import geosalvador, ibge_censo, transparencia


def run_pipeline(output_dir: Path, year: int = 2025) -> dict[str, Any]:
    """Executa o pipeline completo de extração, transformação e carga dos dados de Salvador.

    Sumário:
        Orquestra a coleta de malhas do GeoSalvador, Censo 2022 e Transparência, gerando os arquivos estáticos.

    Descrição Estendida:
        1. Obtém as malhas cartográficas oficiais de Bairros Oficiais (Camada 164) e Prefeituras-Bairro (Camada 7).
        2. Obtém os dados de população e índice de vulnerabilidade do Censo 2022 do IBGE.
        3. Obtém os totalizadores financeiros e contratos detalhados de Obras Públicas da Transparência de Salvador.
        4. Transforma e gera `geo/bairros.geojson` com atributos enriquecidos e sinalização de Zonas Especiais Não-Residenciais.
        5. Gera `geo/prefeituras_bairro.geojson` com agregações populacionais consistentes.
        6. Consolida os KPIs municipais de investimento e gera o arquivo de índice `index_<ano>.json`.

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

    # 2. Geração da malha enriquecida de Bairros Oficiais
    bairros_geo_path = output_path / "geo" / "bairros.geojson"
    bairros_resumo = generate_bairros_geojson(
        raw_bairros_geojson=raw_bairros,
        demografia_map=demografia_map,
        output_path=bairros_geo_path,
    )

    # 3. Geração da malha de Prefeituras-Bairro
    pb_geo_path = output_path / "geo" / "prefeituras_bairro.geojson"
    prefeituras_resumo = generate_prefeituras_geojson(
        raw_pb_geojson=raw_prefeituras,
        bairros_resumo=bairros_resumo,
        output_path=pb_geo_path,
    )

    # 4. Cálculo da população total residencial da cidade
    populacao_cidade = sum(int(b.get("populacao", 0)) for b in bairros_resumo)

    # 5. Cálculo dos KPIs globais
    kpis_globais = kpis.calcular_kpis_globais(
        totalizador_transparencia=totalizador,
        obras_detalhadas=grid_obras,
        populacao_total_cidade=populacao_cidade,
    )

    # 6. Geração do arquivo de índice anual estático
    index_file_path = output_path / f"index_{year}.json"
    generate_index_json(
        kpis_globais=kpis_globais,
        bairros_resumo=bairros_resumo,
        prefeituras_resumo=prefeituras_resumo,
        obras_detalhadas=grid_obras,
        year=year,
        output_path=index_file_path,
    )

    return {
        "success": True,
        "output_dir": str(output_path),
        "ano": year,
        "total_bairros": len(bairros_resumo),
        "total_prefeituras": len(prefeituras_resumo),
        "total_obras": len(grid_obras),
    }

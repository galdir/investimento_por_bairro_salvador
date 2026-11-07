"""Configurações e constantes do subsistema ETL de Salvador.

Define os endpoints das fontes de dados oficiais (GeoSalvador ArcGIS REST,
API da Transparência de Salvador e IBGE SIDRA) e os parâmetros de domínio
vigentes (Decreto 32.791/2020 e Censo 2022).
"""

from typing import Final

# Endpoints do GeoSalvador (ArcGIS REST)
GEOSALVADOR_MAPSERVER_BASE: Final[str] = (
    "https://geo.salvador.ba.gov.br/arcgis/rest/services/MAPA_BASE/MAPA_BASE_Consulta/MapServer"
)
LAYER_BAIRROS_OFICIAIS: Final[int] = 164  # Bairros Oficiais vigentes (Decreto 32.791/2020)
LAYER_PREFEITURAS_BAIRRO: Final[int] = 7  # Prefeituras-Bairro

# Endpoint da API da Transparência Municipal de Salvador
TRANSPARENCIA_API_BASE: Final[str] = "https://apitmptransparencia.salvador.ba.gov.br/api"

# Tabela do Censo 2022 do IBGE SIDRA (População residente por bairro em Salvador)
IBGE_SIDRA_POPULACAO_BAIRROS_SALVADOR: Final[str] = (
    "https://apisidra.ibge.gov.br/values/t/9923/n102/all/v/all/p/last%201?formato=json"
)

# Zonas Especiais Não-Residenciais definidas no domínio (CONTEXT.md)
# Bairros com ocupação institucional, logística ou aeroportuária com população nula/residual
ZONAS_ESPECIAIS_NAO_RESIDENCIAIS: Final[set[str]] = {
    "AEROPORTO",
    "PORTO SECO PIRAJÁ",
    "PORTO SECO PIRAJA",
    "CENTRO ADMINISTRATIVO DA BAHIA - CAB",
    "CENTRO ADMINISTRATIVO DA BAHIA",
    "CAB",
}

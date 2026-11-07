"""Dados de referência e fallback para o pipeline ETL de Obras de Salvador.

Fornece dados sintéticos representativos do GeoSalvador (Camadas 164 e 7),
do Censo 2022 do IBGE e da API da Transparência de Salvador para execução
offline sem dependência da rede externa.
"""

from typing import Any

# GeoJSON de referência de Bairros Oficiais (GeoSalvador Camada 164)
SAMPLE_GEOSALVADOR_BAIRROS: dict[str, Any] = {
    "type": "FeatureCollection",
    "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
    "features": [
        {
            "type": "Feature",
            "properties": {
                "OBJECTID": 1,
                "CD_BAIRRO": 101,
                "NM_BAIRRO": "Pituba",
                "PREFEITURA_BAIRRO": "Barra/Pituba",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-38.46, -13.00],
                        [-38.45, -13.00],
                        [-38.45, -12.99],
                        [-38.46, -12.99],
                        [-38.46, -13.00],
                    ]
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "OBJECTID": 2,
                "CD_BAIRRO": 102,
                "NM_BAIRRO": "Aeroporto",
                "PREFEITURA_BAIRRO": "Itapuã/Ipitanga",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-38.33, -12.91],
                        [-38.32, -12.91],
                        [-38.32, -12.90],
                        [-38.33, -12.90],
                        [-38.33, -12.91],
                    ]
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "OBJECTID": 3,
                "CD_BAIRRO": 103,
                "NM_BAIRRO": "Porto Seco Pirajá",
                "PREFEITURA_BAIRRO": "Cajazeiras",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-38.43, -12.90],
                        [-38.42, -12.90],
                        [-38.42, -12.89],
                        [-38.43, -12.89],
                        [-38.43, -12.90],
                    ]
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "OBJECTID": 4,
                "CD_BAIRRO": 104,
                "NM_BAIRRO": "Centro Administrativo da Bahia - CAB",
                "PREFEITURA_BAIRRO": "Cabula/Tancredo Neves",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-38.43, -12.95],
                        [-38.42, -12.95],
                        [-38.42, -12.94],
                        [-38.43, -12.94],
                        [-38.43, -12.95],
                    ]
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "OBJECTID": 5,
                "CD_BAIRRO": 105,
                "NM_BAIRRO": "Liberdade",
                "PREFEITURA_BAIRRO": "Liberdade/São Caetano",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-38.49, -12.96],
                        [-38.48, -12.96],
                        [-38.48, -12.95],
                        [-38.49, -12.95],
                        [-38.49, -12.96],
                    ]
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "OBJECTID": 6,
                "CD_BAIRRO": 106,
                "NM_BAIRRO": "Cabula",
                "PREFEITURA_BAIRRO": "Cabula/Tancredo Neves",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-38.47, -12.96],
                        [-38.46, -12.96],
                        [-38.46, -12.95],
                        [-38.47, -12.95],
                        [-38.47, -12.96],
                    ]
                ],
            },
        },
    ],
}

# GeoJSON de referência de Prefeituras-Bairro (GeoSalvador Camada 7)
SAMPLE_GEOSALVADOR_PREFEITURAS: dict[str, Any] = {
    "type": "FeatureCollection",
    "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
    "features": [
        {
            "type": "Feature",
            "properties": {
                "OBJECTID": 1,
                "CD_PREFEITURA_BAIRRO": 1,
                "NM_PREFEITURA_BAIRRO": "Barra/Pituba",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-38.53, -13.01],
                        [-38.44, -13.01],
                        [-38.44, -12.98],
                        [-38.53, -12.98],
                        [-38.53, -13.01],
                    ]
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "OBJECTID": 2,
                "CD_PREFEITURA_BAIRRO": 2,
                "NM_PREFEITURA_BAIRRO": "Liberdade/São Caetano",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-38.50, -12.97],
                        [-38.47, -12.97],
                        [-38.47, -12.93],
                        [-38.50, -12.93],
                        [-38.50, -12.97],
                    ]
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "OBJECTID": 3,
                "CD_PREFEITURA_BAIRRO": 3,
                "NM_PREFEITURA_BAIRRO": "Cabula/Tancredo Neves",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-38.47, -12.97],
                        [-38.42, -12.97],
                        [-38.42, -12.93],
                        [-38.47, -12.93],
                        [-38.47, -12.97],
                    ]
                ],
            },
        },
    ],
}

# Dados demográficos de referência do Censo 2022 (IBGE SIDRA)
SAMPLE_IBGE_CENSO_2022: dict[str, dict[str, Any]] = {
    "Pituba": {"populacao": 65000, "indice_vulnerabilidade": 0.12},
    "Aeroporto": {"populacao": 0, "indice_vulnerabilidade": 0.05},
    "Porto Seco Pirajá": {"populacao": 12, "indice_vulnerabilidade": 0.20},
    "Centro Administrativo da Bahia - CAB": {"populacao": 5, "indice_vulnerabilidade": 0.08},
    "Liberdade": {"populacao": 48000, "indice_vulnerabilidade": 0.78},
    "Cabula": {"populacao": 32000, "indice_vulnerabilidade": 0.55},
}

# Resposta de referência do totalizador da Transparência de Salvador
SAMPLE_TRANSPARENCIA_TOTALIZADOR: dict[str, Any] = {
    "totalObras": 25,
    "valorTotal": 150000000.00,
    "totalEmpenhado": 120000000.00,
    "totalLiquidado": 95000000.00,
    "totalPago": 90000000.00,
}

# Resposta de referência da gridDetalhada da Transparência de Salvador
SAMPLE_TRANSPARENCIA_GRID: list[dict[str, Any]] = [
    {
        "id": 1001,
        "cdUnidadeGestora": 2401,
        "dsUnidadeGestora": "SUPERINTENDENCIA DE OBRAS PUBLICAS DO SALVADOR",
        "sgOrgao": "SUCOP",
        "nuContratoSigef": "001/2024",
        "nuContratoOriginal": "001/2024",
        "nuProcesso": "1234/2023",
        "dsObjeto": "Requalificação da Orla da Pituba com drenagem e nova ciclovia",
        "vlOriginal": 12000000.00,
        "vlAtualizado": 12000000.00,
        "dtInicioVigencia": "2024-01-10T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2025-12-31T00:00:00.000Z",
        "dtAssinatura": "2024-01-05T00:00:00.000Z",
        "percentualExecutado": 65.5,
        "dsSituacao": "Em Execução",
        "nmCredor": "CONSTRUTORA SALVADOR LTDA",
    },
    {
        "id": 1002,
        "cdUnidadeGestora": 2401,
        "dsUnidadeGestora": "SUPERINTENDENCIA DE OBRAS PUBLICAS DO SALVADOR",
        "sgOrgao": "SUCOP",
        "nuContratoSigef": "002/2024",
        "nuContratoOriginal": "002/2024",
        "nuProcesso": "1235/2023",
        "dsObjeto": "Contenção de encosta na Rua Direta da Liberdade",
        "vlOriginal": 3500000.00,
        "vlAtualizado": 4200000.00,
        "dtInicioVigencia": "2024-03-01T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2025-08-30T00:00:00.000Z",
        "dtAssinatura": "2024-02-20T00:00:00.000Z",
        "percentualExecutado": 40.0,
        "dsSituacao": "Em Execução",
        "nmCredor": "BAHIA ENGENHARIA S/A",
    },
]

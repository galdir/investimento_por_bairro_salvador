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
        "dtFimVigenciaOriginal": "2027-12-31T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2027-12-31T00:00:00.000Z",
        "dtAssinatura": "2024-01-05T00:00:00.000Z",
        "percentualExecutado": 65.5,
        "dsSituacao": "Em Execução",
        "nmCredor": "CONSTRUTORA SALVADOR LTDA",
        "nuDocumentoCredor": "12.345.678/0001-90",
        "nuDom": "8.750",
    },
    {
        "id": 1002,
        "cdUnidadeGestora": 2401,
        "dsUnidadeGestora": "SUPERINTENDENCIA DE OBRAS PUBLICAS DO SALVADOR",
        "sgOrgao": "SUCOP",
        "nuContratoSigef": "002/2024",
        "nuContratoOriginal": "002/2024",
        "nuProcesso": "1235/2023",
        "dsObjeto": "Contenção de encosta na Rua Direta da Liberdade com aplicação de geomanta",
        "vlOriginal": 3500000.00,
        "vlAtualizado": 4200000.00,
        "dtInicioVigencia": "2024-03-01T00:00:00.000Z",
        "dtFimVigenciaOriginal": "2027-06-30T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2027-12-31T00:00:00.000Z",
        "dtAssinatura": "2024-02-20T00:00:00.000Z",
        "percentualExecutado": 40.0,
        "dsSituacao": "Em Execução",
        "nmCredor": "BAHIA ENGENHARIA S/A",
        "nuDocumentoCredor": "98.765.432/0001-10",
        "nuDom": "8.712",
    },
    {
        "id": 1003,
        "cdUnidadeGestora": 1501,
        "dsUnidadeGestora": "FUNDO MUNICIPAL DE EDUCACAO",
        "sgOrgao": "FME",
        "nuContratoSigef": "015/2024",
        "nuContratoOriginal": "015/2024",
        "nuProcesso": "4567/2023",
        "dsObjeto": "Construção de nova Escola Municipal e CMEI no Subúrbio Ferroviário",
        "vlOriginal": 5000000.00,
        "vlAtualizado": 6500000.00,
        "dtInicioVigencia": "2024-02-01T00:00:00.000Z",
        "dtFimVigenciaOriginal": "2025-02-01T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2025-02-01T00:00:00.000Z",
        "dtAssinatura": "2024-01-25T00:00:00.000Z",
        "percentualExecutado": 35.0,
        "dsSituacao": "Paralisada",
        "nmCredor": "NORDESTE CONSTRUCOES LTDA",
        "nuDocumentoCredor": "55.444.333/0001-22",
        "nuDom": "8.690",
    },
    {
        "id": 1004,
        "cdUnidadeGestora": 3101,
        "dsUnidadeGestora": "COMPANHIA DE DESENVOLVIMENTO URBANO DE SALVADOR",
        "sgOrgao": "DESAL",
        "nuContratoSigef": "042/2024",
        "nuContratoOriginal": "042/2024",
        "nuProcesso": "7890/2023",
        "dsObjeto": "Requalificação e modernização de praça esportiva com parque infantil e quadra poliesportiva",
        "vlOriginal": 1500000.00,
        "vlAtualizado": 1500000.00,
        "dtInicioVigencia": "2024-04-10T00:00:00.000Z",
        "dtFimVigenciaOriginal": "2027-10-10T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2027-10-10T00:00:00.000Z",
        "dtAssinatura": "2024-04-01T00:00:00.000Z",
        "percentualExecutado": 90.0,
        "dsSituacao": "Em Execução",
        "nmCredor": "SALVADOR PARQUES E OBRAS EIRELI",
        "nuDocumentoCredor": "11.222.333/0001-44",
        "nuDom": "8.780",
    },
    {
        "id": 1005,
        "cdUnidadeGestora": 1801,
        "dsUnidadeGestora": "FUNDO MUNICIPAL DE SAUDE",
        "sgOrgao": "FMS",
        "nuContratoSigef": "088/2024",
        "nuContratoOriginal": "088/2024",
        "nuProcesso": "9921/2023",
        "dsObjeto": "Reforma e ampliação da Unidade de Saúde da Família (USF)",
        "vlOriginal": 4000000.00,
        "vlAtualizado": 4000000.00,
        "dtInicioVigencia": "2024-01-15T00:00:00.000Z",
        "dtFimVigenciaOriginal": "2024-12-31T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2024-12-31T00:00:00.000Z",
        "dtAssinatura": "2024-01-10T00:00:00.000Z",
        "percentualExecutado": 70.0,
        "dsSituacao": "Em Execução",
        "nmCredor": "CONSTRUTORA SALVADOR LTDA",
        "nuDocumentoCredor": "12.345.678/0001-90",
        "nuDom": "8.705",
    },
]

# Detalhes complementares de contrato para /obraspublicas/detalhamentoObrasPublicas
SAMPLE_TRANSPARENCIA_DETALHES: dict[str, dict[str, Any]] = {
    "2401_001/2024": {
        "cdUnidadeGestora": 2401,
        "nuContratoSigef": "001/2024",
        "nuContratoOriginal": "001/2024",
        "nuProcesso": "1234/2023",
        "nuDocumentoCredor": "12.345.678/0001-90",
        "nmCredor": "CONSTRUTORA SALVADOR LTDA",
        "dsObjeto": "Requalificação da Orla da Pituba com drenagem e nova ciclovia",
        "vlOriginal": 12000000.00,
        "vlAtualizado": 12000000.00,
        "dtInicioVigencia": "2024-01-10T00:00:00.000Z",
        "dtFimVigenciaOriginal": "2027-12-31T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2027-12-31T00:00:00.000Z",
        "dsPrazoOriginal": "1450 dias",
        "dsPrazoAtualizado": "1450 dias",
        "nuDom": "8.750",
        "dtPublicacao": "2024-01-12T00:00:00.000Z",
        "dsSituacao": "Em Execução",
        "percentualExecutado": 65.5,
    },
    "2401_002/2024": {
        "cdUnidadeGestora": 2401,
        "nuContratoSigef": "002/2024",
        "nuContratoOriginal": "002/2024",
        "nuProcesso": "1235/2023",
        "nuDocumentoCredor": "98.765.432/0001-10",
        "nmCredor": "BAHIA ENGENHARIA S/A",
        "dsObjeto": "Contenção de encosta na Rua Direta da Liberdade com aplicação de geomanta",
        "vlOriginal": 3500000.00,
        "vlAtualizado": 4200000.00,
        "dtInicioVigencia": "2024-03-01T00:00:00.000Z",
        "dtFimVigenciaOriginal": "2027-06-30T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2027-12-31T00:00:00.000Z",
        "dsPrazoOriginal": "1200 dias",
        "dsPrazoAtualizado": "1384 dias",
        "nuDom": "8.712",
        "dtPublicacao": "2024-02-25T00:00:00.000Z",
        "dsSituacao": "Em Execução",
        "percentualExecutado": 40.0,
    },
    "1501_015/2024": {
        "cdUnidadeGestora": 1501,
        "nuContratoSigef": "015/2024",
        "nuContratoOriginal": "015/2024",
        "nuProcesso": "4567/2023",
        "nuDocumentoCredor": "55.444.333/0001-22",
        "nmCredor": "NORDESTE CONSTRUCOES LTDA",
        "dsObjeto": "Construção de nova Escola Municipal e CMEI no Subúrbio Ferroviário",
        "vlOriginal": 5000000.00,
        "vlAtualizado": 6500000.00,
        "dtInicioVigencia": "2024-02-01T00:00:00.000Z",
        "dtFimVigenciaOriginal": "2025-02-01T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2025-02-01T00:00:00.000Z",
        "dsPrazoOriginal": "365 dias",
        "dsPrazoAtualizado": "365 dias",
        "nuDom": "8.690",
        "dtPublicacao": "2024-01-30T00:00:00.000Z",
        "dsSituacao": "Paralisada",
        "percentualExecutado": 35.0,
    },
    "3101_042/2024": {
        "cdUnidadeGestora": 3101,
        "nuContratoSigef": "042/2024",
        "nuContratoOriginal": "042/2024",
        "nuProcesso": "7890/2023",
        "nuDocumentoCredor": "11.222.333/0001-44",
        "nmCredor": "SALVADOR PARQUES E OBRAS EIRELI",
        "dsObjeto": "Requalificação e modernização de praça esportiva com parque infantil e quadra poliesportiva",
        "vlOriginal": 1500000.00,
        "vlAtualizado": 1500000.00,
        "dtInicioVigencia": "2024-04-10T00:00:00.000Z",
        "dtFimVigenciaOriginal": "2027-10-10T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2027-10-10T00:00:00.000Z",
        "dsPrazoOriginal": "1280 dias",
        "dsPrazoAtualizado": "1280 dias",
        "nuDom": "8.780",
        "dtPublicacao": "2024-04-05T00:00:00.000Z",
        "dsSituacao": "Em Execução",
        "percentualExecutado": 90.0,
    },
    "1801_088/2024": {
        "cdUnidadeGestora": 1801,
        "nuContratoSigef": "088/2024",
        "nuContratoOriginal": "088/2024",
        "nuProcesso": "9921/2023",
        "nuDocumentoCredor": "12.345.678/0001-90",
        "nmCredor": "CONSTRUTORA SALVADOR LTDA",
        "dsObjeto": "Reforma e ampliação da Unidade de Saúde da Família (USF)",
        "vlOriginal": 4000000.00,
        "vlAtualizado": 4000000.00,
        "dtInicioVigencia": "2024-01-15T00:00:00.000Z",
        "dtFimVigenciaOriginal": "2024-12-31T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2024-12-31T00:00:00.000Z",
        "dsPrazoOriginal": "350 dias",
        "dsPrazoAtualizado": "350 dias",
        "nuDom": "8.705",
        "dtPublicacao": "2024-01-18T00:00:00.000Z",
        "dsSituacao": "Em Execução",
        "percentualExecutado": 70.0,
    },
}

# Aditivos contratuais por contrato
SAMPLE_TRANSPARENCIA_ADITIVOS: dict[str, list[dict[str, Any]]] = {
    "2401_001/2024": [],
    "2401_002/2024": [
        {
            "nuAditivo": "1º Termo Aditivo",
            "dsTipoAlteracao": "Prazo e Valor",
            "dsObjetoAditivo": "Acréscimo de serviços de drenagem profunda e prorrogação de 184 dias na vigência",
            "dtAssinatura": "2024-11-15T00:00:00.000Z",
            "dtTerminoVigencia": "2027-12-31T00:00:00.000Z",
            "dtPublicacao": "2024-11-20T00:00:00.000Z",
            "nuDom": "8.910",
            "vlAditivo": 700000.00,
        }
    ],
    "1501_015/2024": [
        {
            "nuAditivo": "1º Termo Aditivo",
            "dsTipoAlteracao": "Valor",
            "dsObjetoAditivo": "Readequação estrutural de fundações em solo argiloso e contenção",
            "dtAssinatura": "2024-08-10T00:00:00.000Z",
            "dtTerminoVigencia": "2025-02-01T00:00:00.000Z",
            "dtPublicacao": "2024-08-15T00:00:00.000Z",
            "nuDom": "8.845",
            "vlAditivo": 1500000.00,
        }
    ],
    "3101_042/2024": [],
    "1801_088/2024": [],
}

# Dotação e fontes de recurso por contrato
SAMPLE_TRANSPARENCIA_DOTACAO: dict[str, list[dict[str, Any]]] = {
    "2401_001/2024": [
        {
            "dsSubacao": "Requalificação da Orla Marítima e Projetos Estratégicos",
            "dsFonteRecurso": "Tesouro Municipal (Recursos Ordinários)",
            "dsClassificacao": "4.4.90.51 - Obras e Instalações",
        }
    ],
    "2401_002/2024": [
        {
            "dsSubacao": "Proteção e Contenção de Encostas em Áreas de Risco Geológico",
            "dsFonteRecurso": "Operação de Crédito Interna (FINISA)",
            "dsClassificacao": "4.4.90.51 - Obras e Instalações",
        }
    ],
    "1501_015/2024": [
        {
            "dsSubacao": "Construção e Ampliação de Unidades de Ensino Infantil e Fundamental",
            "dsFonteRecurso": "FUNDEB / Transferências de Recursos da Educação",
            "dsClassificacao": "4.4.90.51 - Obras e Instalações",
        }
    ],
    "3101_042/2024": [
        {
            "dsSubacao": "Manutenção e Criação de Espaços Públicos de Convivência e Lazer",
            "dsFonteRecurso": "Tesouro Municipal (Recursos Próprios)",
            "dsClassificacao": "4.4.90.51 - Obras e Instalações",
        }
    ],
    "1801_088/2024": [
        {
            "dsSubacao": "Reforma e Aparelhamento de Unidades Básicas de Saúde",
            "dsFonteRecurso": "SUS / Fundo Nacional de Saúde",
            "dsClassificacao": "4.4.90.51 - Obras e Instalações",
        }
    ],
}

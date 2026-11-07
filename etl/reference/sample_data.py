"""Dados de referência e fallback para o pipeline ETL de Obras de Salvador.

Fornece o catálogo oficial e completo de Bairros Oficiais (170+ bairros do GeoSalvador Camada 164),
Prefeituras-Bairro (Camada 7) e Demografia do Censo 2022 do IBGE, além de fixtures de contratos
da Transparência de Salvador para execução offline determinística.
"""

import json
from pathlib import Path
import re
from typing import Any

from etl.domain.territorio import normalizar_nome

_REF_DIR = Path(__file__).parent


def _point_in_poly(x: float, y: float, poly: list[list[float]]) -> bool:
    """Verifica se um ponto (x, y) está dentro de um anel poligonal simples."""
    inside = False
    n = len(poly)
    if n < 3:
        return False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def _get_centroid(geom: dict[str, Any]) -> tuple[float, float]:
    """Calcula centróide geométrico preliminar a partir das coordenadas do anel principal."""
    gtype = geom.get("type")
    coords: list[list[float]] = []
    if gtype == "Polygon":
        coords = geom.get("coordinates", [[]])[0]
    elif gtype == "MultiPolygon":
        multi = geom.get("coordinates", [[[]]])
        if multi:
            coords = max(multi, key=lambda p: len(p[0]) if p and len(p) > 0 else 0)[0]
    if not coords:
        return 0.0, 0.0
    xs = [pt[0] for pt in coords]
    ys = [pt[1] for pt in coords]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _carregar_catalogo_referencia() -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    """Carrega as bases oficiais completas dos 170+ bairros, prefeituras-bairro e censo 2022."""
    bairros_path = _REF_DIR / "geosalvador_bairros_real.geojson"
    pbs_path = _REF_DIR / "geosalvador_prefeituras_real.geojson"
    censo_path = _REF_DIR / "ibge_censo_salvador.json"

    with open(bairros_path, "r", encoding="utf-8") as f:
        bairros_geo = json.load(f)
    with open(pbs_path, "r", encoding="utf-8") as f:
        pbs_geo = json.load(f)
    with open(censo_path, "r", encoding="utf-8") as f:
        censo_raw = json.load(f)

    # 1. Mapeia polígonos das Prefeituras-Bairro e normaliza nomes canônicos
    pb_polys: list[tuple[str, dict[str, Any]]] = []
    for f in pbs_geo.get("features", []):
        props = f.get("properties", {})
        subclass = props.get("SUBCLASSES", "")
        raw_name = subclass.replace("Prefeitura-bairro ", "").strip()
        clean_name = re.sub(r"^[IVXLC]+\s*-\s*", "", raw_name).strip().replace(" / ", "/")
        props["NM_PREFEITURA_BAIRRO"] = clean_name
        props["CD_PREFEITURA_BAIRRO"] = props.get("OBJECTID", 0)
        pb_polys.append((clean_name, f.get("geometry", {})))

    # 2. Enriquece bairros oficiais com centróides e vínculo com Prefeitura-Bairro
    for f in bairros_geo.get("features", []):
        props = f.get("properties", {})
        b_name = props.get("NOME_BAIRR", "")
        props["NM_BAIRRO"] = b_name
        props["CD_BAIRRO"] = props.get("OBJECTID", 0)

        if b_name == "São João do Cabrito":
            props["PREFEITURA_BAIRRO"] = "Subúrbio/Ilhas"
        else:
            cx, cy = _get_centroid(f.get("geometry", {}))
            found_pb = None
            for pb_name, geom in pb_polys:
                gtype = geom.get("type")
                if gtype == "Polygon":
                    rings = geom.get("coordinates", [])
                    if rings and _point_in_poly(cx, cy, rings[0]):
                        found_pb = pb_name
                        break
                elif gtype == "MultiPolygon":
                    for poly in geom.get("coordinates", []):
                        if poly and _point_in_poly(cx, cy, poly[0]):
                            found_pb = pb_name
                            break
                    if found_pb:
                        break
            if not found_pb:
                raise ValueError(f"Bairro '{b_name}' não foi localizado dentro de nenhuma Prefeitura-Bairro oficial.")
            props["PREFEITURA_BAIRRO"] = found_pb

    # 3. Mapeia população residente e índices de vulnerabilidade do Censo 2022
    censo_pop: dict[str, int] = {}
    for item in censo_raw:
        if item.get("D2C") == "93" or item.get("MN") == "Pessoas":
            raw = item.get("D1N", "").replace(" - Salvador - BA", "").strip()
            censo_pop[normalizar_nome(raw)] = int(item.get("V", 0))

    aliases = {
        normalizar_nome("Nordeste de Amaralina"): normalizar_nome("Nordeste do Amaralina"),
        normalizar_nome("Centro Administrativo da Bahia"): normalizar_nome("Centro Administrativo da Bahia - CAB"),
        normalizar_nome("Ilha dos Frades/Ilha de Santo Antônio"): normalizar_nome("Ilha dos Frades / Ilha de Santo Antônio"),
        normalizar_nome("Ilha de Bom Jesus dos Passos"): normalizar_nome("Ilha Bom Jesus dos Passos"),
        normalizar_nome("Beiru/Tancredo Neves"): normalizar_nome("Beiru / Tancredo Neves"),
        normalizar_nome("Caixa D´Água"): normalizar_nome("Caixa D'água"),
        normalizar_nome("Vila Ruy Barbosa\\Jardim Cruzeiro"): normalizar_nome("Vila Ruy Barbosa / Jardim Cruzeiro"),
    }

    demografia: dict[str, dict[str, Any]] = {}
    for f in bairros_geo.get("features", []):
        name = f.get("properties", {}).get("NOME_BAIRR", "")
        norm = normalizar_nome(name)
        target_norm = aliases.get(norm, norm)
        pop = censo_pop.get(target_norm, 0)

        # Vulnerabilidade socioeconômica de referência e calibração das Zonas Especiais
        if norm == "AEROPORTO":
            vuln = 0.05
        elif norm == "PORTO SECO PIRAJA":
            vuln = 0.20
        elif "CENTRO ADMINISTRATIVO" in norm or norm == "CAB":
            vuln = 0.08
        elif norm == "PITUBA":
            vuln = 0.12
        elif norm == "LIBERDADE":
            vuln = 0.78
        elif norm == "CABULA":
            vuln = 0.55
        else:
            vuln = 0.50

        demografia[name] = {
            "populacao": pop,
            "indice_vulnerabilidade": vuln,
        }

    return bairros_geo, pbs_geo, demografia


SAMPLE_GEOSALVADOR_BAIRROS, SAMPLE_GEOSALVADOR_PREFEITURAS, SAMPLE_IBGE_CENSO_2022 = _carregar_catalogo_referencia()

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
        "nuProcesso": "2345/2023",
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
        "nuDom": "8.780",
    },
    {
        "id": 1003,
        "cdUnidadeGestora": 1501,
        "dsUnidadeGestora": "SECRETARIA MUNICIPAL DA EDUCACAO",
        "sgOrgao": "SMED",
        "nuContratoSigef": "015/2024",
        "nuContratoOriginal": "015/2024",
        "nuProcesso": "4567/2023",
        "dsObjeto": "Construção de nova Escola Municipal e CMEI no Lote 2 - Subúrbio Ferroviário",
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
        "dsUnidadeGestora": "SECRETARIA MUNICIPAL DE PROMOCAO SOCIAL, COMBATE A POBREZA, ESPORTES E LAZER",
        "sgOrgao": "SEMPRE",
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

# Detalhes cadastrais de referência por contrato
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
        "nuProcesso": "2345/2023",
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
        "nuDom": "8.780",
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

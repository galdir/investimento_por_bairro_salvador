"""Classificação temática determinística de Obras Públicas de Salvador.

Categoriza cada contrato de engenharia em um dos 6 temas funcionais canônicos:
- Encostas e Contenção
- Educação e Escolas
- Saúde
- Praças, Esporte e Lazer
- Mobilidade, Pavimentação e Drenagem
- Manutenção Urbana e Outros
"""

from typing import Any
from etl.domain.territorio import normalizar_nome

# Lista dos 6 Temas Canônicos da especificação
TEMAS_CANONICOS: list[str] = [
    "Encostas e Contenção",
    "Educação e Escolas",
    "Saúde",
    "Praças, Esporte e Lazer",
    "Mobilidade, Pavimentação e Drenagem",
    "Manutenção Urbana e Outros",
]


def classificar_tema(obra: dict[str, Any]) -> str:
    """Classifica determinística e hierarquicamente a Obra Pública em um Tema canônico.

    Sumário:
        Combina o órgão contratante (sigla ou descrição) e termos-chave do objeto da obra.

    Descrição Estendida:
        Avalia primeiro se o órgão contratante define unicamente o tema (ex: DESAL para Praças,
        CODESAL para Encostas, FME/SMED para Educação, FMS/SMS para Saúde, TRANSALVADOR para Trânsito).
        Em seguida, avalia o texto do objeto procurando palavras-chave na ordem de especificidade:
        Encostas > Educação > Saúde > Praças/Lazer > Mobilidade > Manutenção Urbana.

    Argumentos:
        obra: Dicionário contendo os dados do contrato de obra pública (ex: 'sgOrgao', 'dsObjeto').

    Retornos:
        String com o nome exato de um dos 6 temas canônicos.

    Erros:
        Não lança exceções; retorna sempre uma das 6 categorias válidas.
    """
    orgao_norm = normalizar_nome(str(obra.get("sgOrgao") or obra.get("unidadeGestora") or obra.get("dsUnidadeGestora") or ""))
    objeto_norm = normalizar_nome(str(obra.get("dsObjeto") or obra.get("objeto") or ""))

    # 1. Correspondência direta pelo órgão especialista (unidades setoriais)
    if "CODESAL" in orgao_norm:
        return "Encostas e Contenção"
    if "DESAL" in orgao_norm:
        return "Praças, Esporte e Lazer"
    if "FME" in orgao_norm or "SMED" in orgao_norm:
        return "Educação e Escolas"
    if "FMS" in orgao_norm or "SMS" in orgao_norm:
        return "Saúde"
    if "TRANSALVADOR" in orgao_norm:
        return "Mobilidade, Pavimentação e Drenagem"

    # 2. Encostas e Contenção (Prevenção de deslizamentos e contenção de encostas)
    termos_encostas = [
        "ENCOSTA",
        "ENCOSTAS",
        "GEOMANTA",
        "GEOMANTAS",
        "CONTENCAO",
        "CONTENCOES",
        "MURO DE ARRIMO",
        "TALUDE",
        "TALUDES",
        "ESTABILIZACAO",
        "DESLIZAMENTO",
        "RISCO GEOLOGICO",
    ]
    if any(termo in objeto_norm for termo in termos_encostas):
        return "Encostas e Contenção"

    # 3. Educação e Escolas (Creches, CMEIs, escolas municipais e ensino)
    termos_educacao = [
        "ESCOLA",
        "ESCOLAS",
        "CMEI",
        "CMEIS",
        "CRECHE",
        "CRECHES",
        "COLEGIO",
        "COLEGIOS",
        "EDUCACAO",
        "EDUCACIONAL",
        "ENSINO",
        "SALA DE AULA",
        "SALAS DE AULA",
    ]
    if any(termo in objeto_norm for termo in termos_educacao):
        return "Educação e Escolas"

    # 4. Praças, Esporte e Lazer (Campos de futebol, quadras, parques, academias ao ar livre, praças)
    termos_lazer = [
        "PRACA",
        "PRACAS",
        "CAMPO",
        "CAMPOS",
        "QUADRA",
        "QUADRAS",
        "ARENINHA",
        "ARENINHAS",
        "PARQUE",
        "PARQUES",
        "LAZER",
        "ESPORTE",
        "ESPORTIVA",
        "ESPORTIVO",
        "PISTA DE SKATE",
        "ACADEMIA DE SAUDE",
        "ACADEMIA AO AR LIVRE",
        "PARQUE INFANTIL",
    ]
    if any(termo in objeto_norm for termo in termos_lazer):
        return "Praças, Esporte e Lazer"

    # 5. Saúde (Postos de saúde, UBS, USF, UPA, hospitais municipais)
    termos_saude = [
        "POSTO DE SAUDE",
        "POSTO MEDICO",
        "UBS",
        "USF",
        "UPA",
        "HOSPITAL",
        "HOSPITALAR",
        "MULTICENTRO",
        "CLINICA",
        "AMBULATORIO",
        "UNIDADE DE SAUDE",
        "SAUDE",
    ]
    if any(termo in objeto_norm for termo in termos_saude):
        return "Saúde"

    # 6. Mobilidade, Pavimentação e Drenagem (Asfalto, requalificação viária, drenagem pluvial, ciclovias)
    termos_mobilidade = [
        "PAVIMENTACAO",
        "PAVIMENTACOES",
        "ASFALTO",
        "ASFALTICA",
        "ASFALTICO",
        "RECAPEAMENTO",
        "TAPA BURACO",
        "DRENAGEM",
        "AGUAS PLUVIAIS",
        "MACRODRENAGEM",
        "MICRODRENAGEM",
        "CANAL",
        "CANAIS",
        "CICLOVIA",
        "CICLORROTA",
        "VIARIO",
        "VIARIA",
        "ORLA",
        "AVENIDA",
        "RUA",
        "VIADUTO",
        "TUNEL",
        "PASSARELA",
        "SEINFRA",
        "ILUMINACAO PUBLICA",
        "SINALIZACAO",
    ]
    if any(termo in objeto_norm for termo in termos_mobilidade):
        return "Mobilidade, Pavimentação e Drenagem"

    # 7. Manutenção Urbana e Outros (Manutenção predial, reformas gerais e serviços de conservação)
    return "Manutenção Urbana e Outros"

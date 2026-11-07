"""Testes unitários para a classificação determinística de Tema da Obra.

Valida a categorização nos 6 temas canônicos de Salvador:
- Encostas e Contenção
- Educação e Escolas
- Saúde
- Praças, Esporte e Lazer
- Mobilidade, Pavimentação e Drenagem
- Manutenção Urbana e Outros
"""

import pytest
from etl.domain.tema import classificar_tema, TEMAS_CANONICOS


def test_lista_de_temas_canonicos_contem_seis_categorias():
    """Garante que a lista de temas canônicos possui exatamente as 6 categorias da especificação."""
    assert len(TEMAS_CANONICOS) == 6
    assert "Encostas e Contenção" in TEMAS_CANONICOS
    assert "Educação e Escolas" in TEMAS_CANONICOS
    assert "Saúde" in TEMAS_CANONICOS
    assert "Praças, Esporte e Lazer" in TEMAS_CANONICOS
    assert "Mobilidade, Pavimentação e Drenagem" in TEMAS_CANONICOS
    assert "Manutenção Urbana e Outros" in TEMAS_CANONICOS


def test_classificacao_encostas_e_contencao():
    """Valida obras classificadas como Encostas e Contenção por órgão CODESAL ou palavras-chave."""
    obra_encosta = {
        "sgOrgao": "SUCOP",
        "dsObjeto": "Obras de estabilização de encosta e aplicação de geomanta no bairro de Plataforma",
    }
    assert classificar_tema(obra_encosta) == "Encostas e Contenção"

    obra_codesal = {
        "sgOrgao": "CODESAL",
        "dsObjeto": "Muro de arrimo para prevenção de deslizamento na encosta",
    }
    assert classificar_tema(obra_codesal) == "Encostas e Contenção"


def test_classificacao_educacao_e_escolas():
    """Valida obras classificadas como Educação e Escolas por órgão FME/SMED ou palavras-chave."""
    obra_escola = {
        "sgOrgao": "SUCOP",
        "dsObjeto": "Construção de nova Escola Municipal e CMEI com quadra coberta",
    }
    assert classificar_tema(obra_escola) == "Educação e Escolas"

    obra_fme = {
        "sgOrgao": "FME",
        "dsObjeto": "Reforma geral e climatização de salas de aula do colégio municipal",
    }
    assert classificar_tema(obra_fme) == "Educação e Escolas"


def test_classificacao_saude():
    """Valida obras classificadas como Saúde por órgão FMS/SMS ou palavras-chave de unidades de saúde."""
    obra_ubs = {
        "sgOrgao": "SUCOP",
        "dsObjeto": "Implantação de Unidade de Saúde da Família - USF e ampliação de UBS",
    }
    assert classificar_tema(obra_ubs) == "Saúde"

    obra_upa = {
        "sgOrgao": "FMS",
        "dsObjeto": "Reforma do posto médico e instalação de leitos de observação na UPA",
    }
    assert classificar_tema(obra_upa) == "Saúde"


def test_classificacao_pracas_esporte_e_lazer():
    """Valida obras classificadas como Praças, Esporte e Lazer por órgão DESAL ou palavras-chave."""
    obra_praca = {
        "sgOrgao": "DESAL",
        "dsObjeto": "Requalificação da praça pública com parque infantil e academia de saúde",
    }
    assert classificar_tema(obra_praca) == "Praças, Esporte e Lazer"

    obra_campo = {
        "sgOrgao": "SUCOP",
        "dsObjeto": "Instalação de grama sintética em campo de futebol e areninha esportiva",
    }
    assert classificar_tema(obra_campo) == "Praças, Esporte e Lazer"


def test_classificacao_mobilidade_pavimentacao_e_drenagem():
    """Valida obras de drenagem, asfalto, ciclovias e requalificação viária."""
    obra_asfalto = {
        "sgOrgao": "SUCOP",
        "dsObjeto": "Recapeamento asfáltico e pavimentação de vias principais com drenagem de águas pluviais",
    }
    assert classificar_tema(obra_asfalto) == "Mobilidade, Pavimentação e Drenagem"

    obra_orla = {
        "sgOrgao": "SUCOP",
        "dsObjeto": "Requalificação urbanística da Orla da Pituba com nova ciclovia e iluminação viária",
    }
    assert classificar_tema(obra_orla) == "Mobilidade, Pavimentação e Drenagem"


def test_classificacao_manutencao_urbana_e_outros():
    """Valida obras genéricas, manutenções diversas ou sem correspondência específica."""
    obra_manutencao = {
        "sgOrgao": "SEMAN",
        "dsObjeto": "Serviços continuados de conservação predial e manutenção de instalações",
    }
    assert classificar_tema(obra_manutencao) == "Manutenção Urbana e Outros"

    obra_outro = {
        "sgOrgao": "SEFAZ",
        "dsObjeto": "Modernização das instalações de tecnologia da informação",
    }
    assert classificar_tema(obra_outro) == "Manutenção Urbana e Outros"

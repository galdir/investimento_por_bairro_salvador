"""Testes unitários para regras territoriais e classificação de Zonas Especiais Não-Residenciais."""

import pytest
from etl.domain.territorio import (
    calcular_rollup_territorial,
    is_zona_especial_nao_residencial,
    normalizar_nome,
)


@pytest.mark.parametrize(
    "nome_bairro,esperado",
    [
        ("Aeroporto", True),
        ("AEROPORTO", True),
        ("Porto Seco Pirajá", True),
        ("Porto Seco Piraja", True),
        ("Centro Administrativo da Bahia - CAB", True),
        ("Centro Administrativo da Bahia", True),
        ("CAB", True),
        # Testes de regressão: NÃO DEVEM ser marcados como Zona Especial
        ("Cabula", False),
        ("Cabula VI", False),
        ("Cabula 6", False),
        ("Pituba", False),
        ("Liberdade", False),
        ("Barra", False),
        ("Graça", False),
        ("Itapuã", False),
        ("", False),
    ],
)
def test_is_zona_especial_nao_residencial_regressao_cabula(nome_bairro: str, esperado: bool) -> None:
    """Garante que bairros residenciais (como Cabula) não sejam falsamente marcados como CAB.

    Sumário:
        Verifica a classificação booleana estrita para zonas especiais versus bairros comuns.

    Descrição Estendida:
        Testa casos verdadeiros (Aeroporto, Porto Seco Pirajá, CAB) e casos que não devem
        casar por falso positivo de substring (Cabula, Pituba, Barra, Liberdade).

    Argumentos:
        nome_bairro: Nome textual do bairro de entrada.
        esperado: Valor booleano esperado da função.

    Retornos:
        None.

    Erros:
        Lança AssertionError caso o retorno divirja do esperado.
    """
    assert is_zona_especial_nao_residencial(nome_bairro) == esperado


def test_rollup_territorial_regras_de_alocacao_e_zonas_especiais() -> None:
    """Valida as regras de agregação financeira por Bairro Oficial e por Prefeitura-Bairro.

    Sumário:
        Verifica se Bairros somam apenas Pontual e Bairro, se Prefeituras somam seus bairros + Regional,
        se Escopo Cidade compõe a transparência opaca e se Zonas Especiais são excluídas do per capita.

    Descrição Estendida:
        Cria um conjunto sintético contendo 3 bairros (sendo um residencial comum, um residencial
        vulnerável e uma zona especial aeroportuária), 3 prefeituras-bairro e 5 obras cobrindo
        cada nível de alocação territorial. Executa o rollup e valida cada asserção contábil.

    Argumentos:
        Nenhum.

    Retornos:
        None.

    Erros:
        Lança AssertionError caso algum valor financeiro, contagem ou per capita divirja do esperado.
    """
    bairros = [
        {
            "id": 101,
            "nome": "Pituba",
            "prefeitura_bairro": "Barra/Pituba",
            "populacao": 65000,
            "indice_vulnerabilidade": 0.12,
            "is_zona_especial_nao_residencial": False,
        },
        {
            "id": 102,
            "nome": "Aeroporto",
            "prefeitura_bairro": "Itapuã/Ipitanga",
            "populacao": 0,
            "indice_vulnerabilidade": 0.05,
            "is_zona_especial_nao_residencial": True,
        },
        {
            "id": 105,
            "nome": "Liberdade",
            "prefeitura_bairro": "Liberdade/São Caetano",
            "populacao": 48000,
            "indice_vulnerabilidade": 0.78,
            "is_zona_especial_nao_residencial": False,
        },
    ]

    prefeituras = [
        {"id": 1, "nome": "Barra/Pituba", "populacao_total": 65000},
        {"id": 2, "nome": "Liberdade/São Caetano", "populacao_total": 48000},
        {"id": 8, "nome": "Itapuã/Ipitanga", "populacao_total": 50000},
    ]

    obras = [
        # 1. Obra Pontual na Pituba
        {
            "id": 1,
            "vlAtualizado": 1000000.0,
            "vlPago": 800000.0,
            "nivel": "Pontual",
            "bairro": "Pituba",
            "prefeitura_bairro": "Barra/Pituba",
            "semaforo": {"status": "VERDE"},
        },
        # 2. Obra de Bairro na Pituba
        {
            "id": 2,
            "vlAtualizado": 500000.0,
            "vlPago": 400000.0,
            "nivel": "Bairro",
            "bairro": "Pituba",
            "prefeitura_bairro": "Barra/Pituba",
            "semaforo": {"status": "VERDE"},
        },
        # 3. Obra Regional na Barra/Pituba (NÃO deve somar na Pituba, mas DEVE somar na PB Barra/Pituba)
        {
            "id": 3,
            "vlAtualizado": 3000000.0,
            "vlPago": 1500000.0,
            "nivel": "Regional (Prefeitura-Bairro)",
            "bairro": None,
            "prefeitura_bairro": "Barra/Pituba",
            "semaforo": {"status": "AMARELO"},
        },
        # 4. Obra Pontual na Zona Especial (Aeroporto)
        {
            "id": 4,
            "vlAtualizado": 10000000.0,
            "vlPago": 5000000.0,
            "nivel": "Pontual",
            "bairro": "Aeroporto",
            "prefeitura_bairro": "Itapuã/Ipitanga",
            "semaforo": {"status": "VERMELHO"},
        },
        # 5. Obra Escopo Cidade (Não-Localizado)
        {
            "id": 5,
            "vlAtualizado": 2000000.0,
            "vlPago": 1000000.0,
            "nivel": "Escopo Cidade (Não-Localizado)",
            "bairro": None,
            "prefeitura_bairro": None,
            "semaforo": {"status": "VERDE"},
        },
    ]

    bairros_proc, pb_proc, opacidade = calcular_rollup_territorial(
        bairros_resumo=bairros,
        prefeituras_resumo=prefeituras,
        obras_alocadas=obras,
    )

    # 1. Verificação do Bairro Pituba
    pituba = next(b for b in bairros_proc if b["nome"] == "Pituba")
    # Soma apenas obra 1 (1.000.000) e obra 2 (500.000) = 1.500.000 (a obra regional 3 de 3M NÃO entra!)
    assert pituba["valorTotal"] == 1500000.0
    assert pituba["valorPago"] == 1200000.0
    assert pituba["totalObras"] == 2
    # Per capita = 1.500.000 / 65.000 = 23.08 R$/hab
    assert pituba["investimentoPorHabitante"] == pytest.approx(23.08, rel=1e-2)

    # 2. Verificação da Prefeitura-Bairro Barra/Pituba
    pb_barra_pituba = next(pb for pb in pb_proc if pb["nome"] == "Barra/Pituba")
    # Soma obras dos bairros (1.500.000) + obra regional (3.000.000) = 4.500.000
    assert pb_barra_pituba["valorTotal"] == 4500000.0
    assert pb_barra_pituba["valorPago"] == 2700000.0
    assert pb_barra_pituba["totalObras"] == 3
    # Per capita = 4.500.000 / 65.000 = 69.23 R$/hab
    assert pb_barra_pituba["investimentoPorHabitante"] == pytest.approx(69.23, rel=1e-2)
    assert pb_barra_pituba["indice_vulnerabilidade"] == pytest.approx(0.12, rel=1e-2)

    pb_liberdade = next(pb for pb in pb_proc if pb["nome"] == "Liberdade/São Caetano")
    assert pb_liberdade["indice_vulnerabilidade"] == pytest.approx(0.78, rel=1e-2)

    # 3. Verificação da Zona Especial (Aeroporto)
    aeroporto = next(b for b in bairros_proc if b["nome"] == "Aeroporto")
    assert aeroporto["valorTotal"] == 10000000.0  # Valor bruto preservado
    assert aeroporto["totalObras"] == 1
    # Per capita nulo/excluído para evitar distorção de população 0
    assert aeroporto["investimentoPorHabitante"] == 0.0
    assert aeroporto["isZonaEspecialNaoResidencial"] is True

    # 4. Verificação do Indicador de Transparência Opaca (Escopo Cidade)
    # Total de todas as obras: 1.5M + 3.0M + 10.0M + 2.0M = 16.5M
    # Não localizado: 2.0M
    assert opacidade["totalNaoLocalizado"] == 1
    assert opacidade["valorNaoLocalizado"] == 2000000.0
    assert opacidade["percentualNaoLocalizado"] == pytest.approx((2000000.0 / 16500000.0) * 100.0, rel=1e-2)


def test_calculo_multidimensional_vulnerabilidade_min_max_e_contiguidade() -> None:
    """Valida o cálculo composto multidimensional do Índice de Vulnerabilidade do Bairro.

    Sumário:
        Verifica a imputação por contiguidade para os 3 bairros ausentes no N102,
        a isenção das Zonas Especiais Não-Residenciais e a normalização min-max
        com pesos iguais (1/3 cada), preservando a ordenação Pituba < Cabula < Liberdade.
    """
    from etl.domain.territorio import calcular_indice_vulnerabilidade_bairros

    demografia_input = {
        # Bairros de referência para contiguidade da Ilha de Maré
        "Ilha de Bom Jesus dos Passos": {
            "populacao": 1635,
            "pct_esgoto_inadequado": 20.0,
            "pct_agua_inadequada": 10.0,
            "pct_analfabetismo_15mais": 4.0,
        },
        "Ilha dos Frades/Ilha de Santo Antônio": {
            "populacao": 894,
            "pct_esgoto_inadequado": 25.0,
            "pct_agua_inadequada": 15.0,
            "pct_analfabetismo_15mais": 6.0,
        },
        # Bairros limítrofes do Chame-Chame
        "Graça": {
            "populacao": 14996,
            "pct_esgoto_inadequado": 1.5,
            "pct_agua_inadequada": 0.3,
            "pct_analfabetismo_15mais": 0.6,
        },
        "Barra": {
            "populacao": 15094,
            "pct_esgoto_inadequado": 2.0,
            "pct_agua_inadequada": 0.4,
            "pct_analfabetismo_15mais": 0.8,
        },
        "Vitória": {
            "populacao": 4416,
            "pct_esgoto_inadequado": 1.0,
            "pct_agua_inadequada": 0.2,
            "pct_analfabetismo_15mais": 0.5,
        },
        # Bairros limítrofes de Colinas de Pituaçu
        "São Marcos": {
            "populacao": 22962,
            "pct_esgoto_inadequado": 22.0,
            "pct_agua_inadequada": 2.5,
            "pct_analfabetismo_15mais": 4.5,
        },
        "Pau da Lima": {
            "populacao": 20665,
            "pct_esgoto_inadequado": 24.0,
            "pct_agua_inadequada": 2.8,
            "pct_analfabetismo_15mais": 5.0,
        },
        # Âncoras do Censo 2022
        "Pituba": {
            "populacao": 57894,
            "pct_esgoto_inadequado": 1.8,
            "pct_agua_inadequada": 0.3,
            "pct_analfabetismo_15mais": 0.7,
        },
        "Cabula": {
            "populacao": 21825,
            "pct_esgoto_inadequado": 15.0,
            "pct_agua_inadequada": 1.5,
            "pct_analfabetismo_15mais": 3.0,
        },
        "Liberdade": {
            "populacao": 34451,
            "pct_esgoto_inadequado": 35.0,
            "pct_agua_inadequada": 3.5,
            "pct_analfabetismo_15mais": 6.5,
        },
        # 3 Bairros sem linha própria no SIDRA N102 (devem ser imputados)
        "Ilha de Maré": {
            "populacao": 4036,
        },
        "Chame-Chame": {
            "populacao": 2187,
        },
        "Colinas de Pituaçu": {
            "populacao": 3000,
        },
        # Zonas Especiais Não-Residenciais
        "Aeroporto": {
            "populacao": 0,
        },
        "Porto Seco Pirajá": {
            "populacao": 0,
        },
        "Centro Administrativo da Bahia - CAB": {
            "populacao": 173,
        },
    }

    resultado = calcular_indice_vulnerabilidade_bairros(demografia_input)

    # 1. Zonas Especiais Não-Residenciais: isentas (0.0) e sem contiguidade
    for ze in ["Aeroporto", "Porto Seco Pirajá", "Centro Administrativo da Bahia - CAB"]:
        assert resultado[ze]["indice_vulnerabilidade"] == 0.0
        assert resultado[ze]["pct_esgoto_inadequado"] == 0.0
        assert resultado[ze]["pct_agua_inadequada"] == 0.0
        assert resultado[ze]["pct_analfabetismo_15mais"] == 0.0
        assert resultado[ze]["vulnerabilidade_estimada_contiguidade"] is False

    # 2. Imputação por contiguidade para os 3 bairros ausentes no N102
    assert resultado["Ilha de Maré"]["vulnerabilidade_estimada_contiguidade"] is True
    # Ponderação Ilha de Maré: (1635*20 + 894*25)/(1635+894) = 55050 / 2529 = 21.77
    assert resultado["Ilha de Maré"]["pct_esgoto_inadequado"] == pytest.approx(21.77, abs=0.05)

    assert resultado["Chame-Chame"]["vulnerabilidade_estimada_contiguidade"] is True
    # Ponderação Chame-Chame: (14996*1.5 + 15094*2.0 + 4416*1.0) / 34506 = 57098 / 34506 = 1.65
    assert resultado["Chame-Chame"]["pct_esgoto_inadequado"] == pytest.approx(1.65, abs=0.05)

    assert resultado["Colinas de Pituaçu"]["vulnerabilidade_estimada_contiguidade"] is True
    # Ponderação Colinas de Pituaçu: (22962*22 + 20665*24) / 43627 = 1001124 / 43627 = 22.95
    assert resultado["Colinas de Pituaçu"]["pct_esgoto_inadequado"] == pytest.approx(22.95, abs=0.05)

    # Bairros comuns têm estimativa_contiguidade False
    assert resultado["Pituba"]["vulnerabilidade_estimada_contiguidade"] is False
    assert resultado["Liberdade"]["vulnerabilidade_estimada_contiguidade"] is False

    # 3. Invariante de ordenação socioeconômica do Censo 2022
    iv_pituba = resultado["Pituba"]["indice_vulnerabilidade"]
    iv_cabula = resultado["Cabula"]["indice_vulnerabilidade"]
    iv_liberdade = resultado["Liberdade"]["indice_vulnerabilidade"]
    assert 0.0 <= iv_pituba < iv_cabula < iv_liberdade <= 1.0


def test_rollup_territorial_consolida_subindicadores_prefeituras_bairro() -> None:
    """Valida que o rollup de Prefeituras-Bairro consolida os 3 sub-indicadores por média ponderada."""
    bairros = [
        {
            "id": 101,
            "nome": "Pituba",
            "prefeitura_bairro": "Barra/Pituba",
            "populacao": 60000,
            "indice_vulnerabilidade": 0.05,
            "pct_esgoto_inadequado": 2.0,
            "pct_agua_inadequada": 0.5,
            "pct_analfabetismo_15mais": 1.0,
            "vulnerabilidade_estimada_contiguidade": False,
            "is_zona_especial_nao_residencial": False,
        },
        {
            "id": 102,
            "nome": "Barra",
            "prefeitura_bairro": "Barra/Pituba",
            "populacao": 40000,
            "indice_vulnerabilidade": 0.15,
            "pct_esgoto_inadequado": 4.0,
            "pct_agua_inadequada": 1.0,
            "pct_analfabetismo_15mais": 1.5,
            "vulnerabilidade_estimada_contiguidade": False,
            "is_zona_especial_nao_residencial": False,
        },
        {
            "id": 103,
            "nome": "Aeroporto",
            "prefeitura_bairro": "Barra/Pituba",
            "populacao": 0,
            "indice_vulnerabilidade": 0.0,
            "pct_esgoto_inadequado": 0.0,
            "pct_agua_inadequada": 0.0,
            "pct_analfabetismo_15mais": 0.0,
            "vulnerabilidade_estimada_contiguidade": False,
            "is_zona_especial_nao_residencial": True,
        },
    ]

    prefeituras = [
        {"id": 1, "nome": "Barra/Pituba", "populacao_total": 100000},
    ]

    b_proc, pb_proc, _ = calcular_rollup_territorial(
        bairros_resumo=bairros,
        prefeituras_resumo=prefeituras,
        obras_alocadas=[],
    )

    pb = pb_proc[0]
    # Média ponderada residencial (60.000 Pituba + 40.000 Barra = 100.000):
    # Índice: (60k*0.05 + 40k*0.15)/100k = 0.09
    assert pb["indice_vulnerabilidade"] == 0.09
    # Esgoto: (60k*2.0 + 40k*4.0)/100k = 2.8
    assert pb["pct_esgoto_inadequado"] == 2.8
    # Água: (60k*0.5 + 40k*1.0)/100k = 0.7
    assert pb["pct_agua_inadequada"] == 0.7
    # Analfabetismo: (60k*1.0 + 40k*1.5)/100k = 1.2
    assert pb["pct_analfabetismo_15mais"] == 1.2

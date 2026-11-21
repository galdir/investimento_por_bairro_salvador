"""Testes unitários para regras territoriais e classificação de Zonas Especiais Não-Residenciais."""

import pytest
from etl.domain.territorio import (
    calcular_indice_vulnerabilidade_bairros,
    calcular_rollup_territorial,
    is_centralidade_metropolitana,
    is_zona_especial_nao_residencial,
    normalizar_nome,
)


def test_rollup_distingue_pagamento_ausente_zero_e_soma_parcial() -> None:
    bairros = [
        {"id": 1, "nome": "Pituba", "prefeitura_bairro": "Barra/Pituba", "populacao": 100},
        {"id": 2, "nome": "Graça", "prefeitura_bairro": "Barra/Pituba", "populacao": 100},
    ]
    prefeituras = [{"id": 1, "nome": "Barra/Pituba", "populacao_total": 200}]
    obras = [
        {"id": "ausente", "nivel": "Bairro", "bairro": "Pituba", "valorPago": None},
        {"id": "zero", "nivel": "Bairro", "bairro": "Graça", "valorPago": 0},
    ]
    bairros_rollup, pbs, _ = calcular_rollup_territorial(bairros, prefeituras, obras)
    pituba, graca = bairros_rollup
    assert pituba["valorPago"] is None
    assert pituba["investimentoPorHabitantePago"] is None
    assert pituba["valorPagoDisponivel"] is False
    assert pituba["obrasSemValorPago"] == 1
    assert graca["valorPago"] == 0
    assert graca["valorPagoDisponivel"] is True
    assert pbs[0]["valorPago"] == 0
    assert pbs[0]["valorPagoDisponivel"] is True
    assert pbs[0]["obrasSemValorPago"] == 1


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


def test_calculo_multidimensional_vulnerabilidade_p95_e_contiguidade_aquarius() -> None:
    """Valida o cálculo P95 winsorizado, a isenção de Zonas Especiais e a contiguidade exclusiva de Aquarius."""
    from etl.domain.territorio import CONTIGUIDADE_BAIRROS_AUSENTES, calcular_indice_vulnerabilidade_bairros

    assert list(CONTIGUIDADE_BAIRROS_AUSENTES.keys()) == ["AQUARIUS"]

    demografia_input = {
        # Vizinhos obrigatórios de Aquarius (soma pop = 100.000)
        "Pituba": {
            "populacao": 60000,
            "pct_esgoto_inadequado": 1.0,
            "pct_agua_inadequada": 0.2,
            "pct_analfabetismo_15mais": 0.5,
        },
        "Itaigara": {
            "populacao": 20000,
            "pct_esgoto_inadequado": 2.0,
            "pct_agua_inadequada": 0.4,
            "pct_analfabetismo_15mais": 1.0,
        },
        "Caminho das Árvores": {
            "populacao": 20000,
            "pct_esgoto_inadequado": 3.0,
            "pct_agua_inadequada": 0.6,
            "pct_analfabetismo_15mais": 1.5,
        },
        # Aquarius: população 0 e sem sub-indicadores próprios (deve ser imputado)
        "Aquarius": {
            "populacao": 0,
        },
        # Bairros antes imputados e agora com dados reais do Censo 2022
        "Ilha de Maré": {
            "populacao": 4036,
            "pct_esgoto_inadequado": 94.32,
            "pct_agua_inadequada": 1.2,
            "pct_analfabetismo_15mais": 14.42,
        },
        "Chame-Chame": {
            "populacao": 2187,
            "pct_esgoto_inadequado": 1.8,
            "pct_agua_inadequada": 0.4,
            "pct_analfabetismo_15mais": 0.9,
        },
        "Colinas de Periperi": {
            "populacao": 1500,
            "pct_esgoto_inadequado": 22.0,
            "pct_agua_inadequada": 2.5,
            "pct_analfabetismo_15mais": 4.5,
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
        # Zonas Especiais Não-Residenciais
        "Aeroporto": {"populacao": 0},
        "Porto Seco Pirajá": {"populacao": 0},
        "Centro Administrativo da Bahia - CAB": {"populacao": 173},
    }

    resultado = calcular_indice_vulnerabilidade_bairros(demografia_input)

    for ze in ["Aeroporto", "Porto Seco Pirajá", "Centro Administrativo da Bahia - CAB"]:
        assert resultado[ze]["indice_vulnerabilidade"] == 0.0
        assert resultado[ze]["pct_esgoto_inadequado"] == 0.0
        assert resultado[ze]["pct_agua_inadequada"] == 0.0
        assert resultado[ze]["pct_analfabetismo_15mais"] == 0.0
        assert resultado[ze]["vulnerabilidade_estimada_contiguidade"] is False

    # Aquarius recebe média ponderada de Pituba (60k), Itaigara (20k) e Caminho das Árvores (20k)
    assert resultado["Aquarius"]["vulnerabilidade_estimada_contiguidade"] is True
    assert resultado["Aquarius"]["pct_esgoto_inadequado"] == 1.6
    assert resultado["Aquarius"]["pct_agua_inadequada"] == 0.32
    assert resultado["Aquarius"]["pct_analfabetismo_15mais"] == 0.8

    # Ilha de Maré, Chame-Chame e Colinas de Periperi preservam dados reais sem contiguidade
    for b_real in ["Ilha de Maré", "Chame-Chame", "Colinas de Periperi", "Pituba", "Liberdade"]:
        assert resultado[b_real]["vulnerabilidade_estimada_contiguidade"] is False
    assert resultado["Ilha de Maré"]["pct_esgoto_inadequado"] == 94.32

    iv_pituba = resultado["Pituba"]["indice_vulnerabilidade"]
    iv_cabula = resultado["Cabula"]["indice_vulnerabilidade"]
    iv_liberdade = resultado["Liberdade"]["indice_vulnerabilidade"]
    assert 0.0 <= iv_pituba < iv_cabula < iv_liberdade <= 1.0


def test_normalizacao_p95_winsorizada_formula_exata_e_amplitude_zero() -> None:
    """Valida a interpolação linear inclusiva (N - 1) * 0.95, teto em 1.00 e amplitude zero."""
    demografia = {
        "Bairro A": {"populacao": 100, "pct_esgoto_inadequado": 1.0, "pct_agua_inadequada": 1.0, "pct_analfabetismo_15mais": 0.0},
        "Bairro B": {"populacao": 100, "pct_esgoto_inadequado": 2.0, "pct_agua_inadequada": 1.0, "pct_analfabetismo_15mais": 1.0},
        "Bairro C": {"populacao": 100, "pct_esgoto_inadequado": 3.0, "pct_agua_inadequada": 1.0, "pct_analfabetismo_15mais": 2.0},
        "Bairro D": {"populacao": 100, "pct_esgoto_inadequado": 4.0, "pct_agua_inadequada": 1.0, "pct_analfabetismo_15mais": 3.0},
        "Bairro E": {"populacao": 100, "pct_esgoto_inadequado": 100.0, "pct_agua_inadequada": 1.0, "pct_analfabetismo_15mais": 4.0},
    }
    resultado = calcular_indice_vulnerabilidade_bairros(demografia)
    # Bairro A: (0.0 + 0.0 + 0.0) / 3 = 0.0
    assert resultado["Bairro A"]["indice_vulnerabilidade"] == 0.0
    # Bairro E: (1.0 + 0.0 + 1.0) / 3 = 0.67 (clamped at 1.00 in esgoto and analf, 0.0 in zero-range agua)
    assert resultado["Bairro E"]["indice_vulnerabilidade"] == 0.67


def test_calculo_vulnerabilidade_falha_se_bairro_residencial_sem_subindicadores() -> None:
    """Bairro Oficial residencial fora da contiguidade sem os 3 sub-indicadores válidos deve falhar com ValueError."""
    demografia = {
        "Pituba": {"populacao": 60000, "pct_esgoto_inadequado": 1.0, "pct_agua_inadequada": 0.2, "pct_analfabetismo_15mais": 0.5},
        "IAPI": {"populacao": 19941, "pct_esgoto_inadequado": None, "pct_agua_inadequada": 0.3, "pct_analfabetismo_15mais": 3.8},
    }
    with pytest.raises(ValueError, match="IAPI"):
        calcular_indice_vulnerabilidade_bairros(demografia)


def test_calculo_vulnerabilidade_falha_se_vizinho_aquarius_ausente_ou_sem_populacao() -> None:
    """Aquarius deve falhar com ValueError se qualquer vizinho obrigatório estiver ausente ou com população <= 0."""
    demografia_sem_itaigara = {
        "Pituba": {"populacao": 60000, "pct_esgoto_inadequado": 1.0, "pct_agua_inadequada": 0.2, "pct_analfabetismo_15mais": 0.5},
        "Caminho das Árvores": {"populacao": 20000, "pct_esgoto_inadequado": 3.0, "pct_agua_inadequada": 0.6, "pct_analfabetismo_15mais": 1.5},
        "Aquarius": {"populacao": 0},
    }
    with pytest.raises(ValueError, match="ITAIGARA"):
        calcular_indice_vulnerabilidade_bairros(demografia_sem_itaigara)

    demografia_itaigara_zero = {
        **demografia_sem_itaigara,
        "Itaigara": {"populacao": 0, "pct_esgoto_inadequado": 2.0, "pct_agua_inadequada": 0.4, "pct_analfabetismo_15mais": 1.0},
    }
    with pytest.raises(ValueError, match="ITAIGARA"):
        calcular_indice_vulnerabilidade_bairros(demografia_itaigara_zero)


def test_normalizacao_p95_sobre_base_real_censo_2022() -> None:
    """Valida a normalização P95 winsorizada sobre a base real completa do Censo 2022 (modo offline)."""
    import json
    from pathlib import Path
    from etl.sources.ibge_censo import normalizar_registros_censo_2022

    geo_path = Path("etl/reference/geosalvador_bairros_real.geojson")
    bairros_geo = json.loads(geo_path.read_text(encoding="utf-8"))
    bairros_oficiais = [
        (f["properties"].get("NM_BAIRRO") or f["properties"].get("NOME_BAIRR") or "").strip()
        for f in bairros_geo["features"]
    ]

    resultado = normalizar_registros_censo_2022([])
    residenciais = [
        (nome, resultado[nome])
        for nome in bairros_oficiais
        if not is_zona_especial_nao_residencial(nome)
    ]
    assert len(residenciais) == 168

    valores = [entry["indice_vulnerabilidade"] for _, entry in residenciais]
    assert min(valores) == 0.01
    assert max(valores) == 0.93

    assert resultado["IAPI"]["indice_vulnerabilidade"] > 0.0
    assert resultado["STIEP"]["indice_vulnerabilidade"] > 0.0
    assert (
        resultado["Pituba"]["indice_vulnerabilidade"]
        < resultado["Cabula"]["indice_vulnerabilidade"]
        < resultado["Liberdade"]["indice_vulnerabilidade"]
    )
    assert resultado["Aquarius"]["populacao"] == 0
    assert resultado["Aquarius"]["vulnerabilidade_estimada_contiguidade"] is True
    for nome in bairros_oficiais:
        if nome != "Aquarius":
            assert resultado[nome]["vulnerabilidade_estimada_contiguidade"] is False


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


def test_rollup_frentes_de_medicao_conservadorismo_contabil() -> None:
    """Valida que Frentes de Medição somam apenas em valorLiquidado/valorPago sem inflar valorTotal ou totalObras."""
    bairros = [
        {
            "id": 101,
            "nome": "Pituba",
            "prefeitura_bairro": "Barra/Pituba",
            "populacao": 50000,
            "indice_vulnerabilidade": 0.10,
            "is_zona_especial_nao_residencial": False,
        },
        {
            "id": 102,
            "nome": "Aeroporto",
            "prefeitura_bairro": "Itapuã/Ipitanga",
            "populacao": 0,
            "indice_vulnerabilidade": 0.0,
            "is_zona_especial_nao_residencial": True,
        },
        {
            "id": 103,
            "nome": "Plataforma",
            "prefeitura_bairro": "Subúrbio/Ilhas",
            "populacao": 20000,
            "indice_vulnerabilidade": 0.60,
            "is_zona_especial_nao_residencial": False,
        },
    ]
    prefeituras = [
        {"id": 1, "nome": "Barra/Pituba", "populacao_total": 50000},
        {"id": 2, "nome": "Itapuã/Ipitanga", "populacao_total": 100000},
        {"id": 3, "nome": "Subúrbio/Ilhas", "populacao_total": 20000},
    ]
    obras = [
        {
            "id": "direta-1",
            "nivel": "Bairro",
            "bairro": "Pituba",
            "prefeitura_bairro": "Barra/Pituba",
            "vlAtualizado": 500000.0,
            "vlLiquidado": 300000.0,
            "vlPago": 250000.0,
            "semaforo": {"status": "VERDE"},
        },
        {
            "id": "guarda-chuva-1",
            "nivel": "Escopo Cidade (Não-Localizado)",
            "bairro": None,
            "prefeitura_bairro": None,
            "vlAtualizado": 1000000.0,
            "vlLiquidado": 600000.0,
            "vlPago": 500000.0,
            "semaforo": {"status": "AMARELO"},
            "frentesMedicao": [
                {
                    "notaLiquidacao": "2025NL0001",
                    "nivel": "Bairro",
                    "bairro": "Pituba",
                    "prefeituraBairro": "Barra/Pituba",
                    "valorLiquidado": 200000.0,
                    "valorPago": 180000.0,
                },
                {
                    "notaLiquidacao": "2025NL0002",
                    "nivel": "Bairro",
                    "bairro": "Aeroporto",
                    "prefeituraBairro": "Itapuã/Ipitanga",
                    "valorLiquidado": 100000.0,
                    "valorPago": 90000.0,
                },
                {
                    "notaLiquidacao": "2025NL0003",
                    "nivel": "Regional (Prefeitura-Bairro)",
                    "bairro": None,
                    "prefeituraBairro": "Subúrbio/Ilhas",
                    "valorLiquidado": 50000.0,
                    "valorPago": 40000.0,
                },
            ],
        },
    ]

    b_proc, pb_proc, opacidade = calcular_rollup_territorial(
        bairros_resumo=bairros,
        prefeituras_resumo=prefeituras,
        obras_alocadas=obras,
    )

    pituba = next(b for b in b_proc if b["nome"] == "Pituba")
    assert pituba["valorTotal"] == 500000.0
    assert pituba["totalObras"] == 1
    assert pituba["valorLiquidadoDireto"] == 300000.0
    assert pituba["valorPagoDireto"] == 250000.0
    assert pituba["valorLiquidadoFrentes"] == 200000.0
    assert pituba["valorPagoFrentes"] == 180000.0
    assert pituba["valorLiquidado"] == 500000.0
    assert pituba["valorPago"] == 430000.0
    assert pituba["totalFrentesMedicao"] == 1
    assert pituba["investimentoPorHabitante"] == 10.0
    assert pituba["investimentoPorHabitantePago"] == 8.6

    aeroporto = next(b for b in b_proc if b["nome"] == "Aeroporto")
    assert aeroporto["valorTotal"] == 0.0
    assert aeroporto["totalObras"] == 0
    assert aeroporto["valorLiquidado"] == 100000.0
    assert aeroporto["valorPago"] == 90000.0
    assert aeroporto["totalFrentesMedicao"] == 1
    assert aeroporto["investimentoPorHabitante"] == 0.0
    assert aeroporto["investimentoPorHabitantePago"] == 0.0

    plataforma = next(b for b in b_proc if b["nome"] == "Plataforma")
    assert plataforma["valorTotal"] == 0.0
    assert plataforma["valorPago"] == 0.0
    assert plataforma["totalFrentesMedicao"] == 0

    pb_suburbio = next(p for p in pb_proc if p["nome"] == "Subúrbio/Ilhas")
    assert pb_suburbio["valorTotal"] == 0.0
    assert pb_suburbio["totalObras"] == 0
    assert pb_suburbio["valorLiquidado"] == 50000.0
    assert pb_suburbio["valorPago"] == 40000.0
    assert pb_suburbio["valorPagoFrentes"] == 40000.0
    assert pb_suburbio["totalFrentesMedicao"] == 1

    assert opacidade["totalNaoLocalizado"] == 1
    assert opacidade["valorNaoLocalizado"] == 1000000.0
    assert opacidade["valorPagoNaoLocalizado"] == 190000.0


def test_centralidade_metropolitana_comercio_isencao_per_capita_preserva_vulnerabilidade() -> None:
    """Comércio é classificado como Centralidade Metropolitana: isento per capita, mas preserva vulnerabilidade e soma na PB."""
    assert is_centralidade_metropolitana("Comércio") is True
    assert is_centralidade_metropolitana("COMERCIO") is True
    assert is_centralidade_metropolitana("Pituba") is False
    assert is_centralidade_metropolitana("Aeroporto") is False
    assert is_zona_especial_nao_residencial("Comércio") is False

    demografia = {
        "Pituba": {
            "populacao": 65000,
            "pct_esgoto_inadequado": 1.0,
            "pct_agua_inadequada": 0.5,
            "pct_analfabetismo_15mais": 1.0,
        },
        "Comércio": {
            "populacao": 971,
            "pct_esgoto_inadequado": 18.0,
            "pct_agua_inadequada": 5.0,
            "pct_analfabetismo_15mais": 4.5,
        },
        "Brotas": {
            "populacao": 59029,
            "pct_esgoto_inadequado": 10.0,
            "pct_agua_inadequada": 2.0,
            "pct_analfabetismo_15mais": 3.0,
        },
        "Aeroporto": {
            "populacao": 0,
            "pct_esgoto_inadequado": 99.0,
            "pct_agua_inadequada": 99.0,
            "pct_analfabetismo_15mais": 99.0,
        },
    }

    vuln_calc = calcular_indice_vulnerabilidade_bairros(demografia)
    comercio_demo = vuln_calc["Comércio"]
    assert comercio_demo["is_centralidade_metropolitana"] is True
    assert comercio_demo["isCentralidadeMetropolitana"] is True
    assert comercio_demo["is_zona_especial_nao_residencial"] is False
    assert comercio_demo["indice_vulnerabilidade"] > 0.0
    assert comercio_demo["pct_esgoto_inadequado"] == 18.0
    assert comercio_demo["pct_agua_inadequada"] == 5.0
    assert comercio_demo["pct_analfabetismo_15mais"] == 4.5

    bairros = [
        {"id": 1, "nome": "Comércio", "prefeitura_bairro": "Centro/Brotas", **comercio_demo},
        {"id": 2, "nome": "Brotas", "prefeitura_bairro": "Centro/Brotas", **vuln_calc["Brotas"]},
    ]
    prefeituras = [
        {"id": 10, "nome": "Centro/Brotas", "populacao_total": 60000},
    ]
    obras = [
        {
            "id": 901,
            "vlAtualizado": 9710000.0,
            "vlPago": 971000.0,
            "nivel": "Pontual",
            "bairro": "Comércio",
            "prefeitura_bairro": "Centro/Brotas",
            "semaforo": {"status": "VERDE"},
        },
        {
            "id": 902,
            "vlAtualizado": 290000.0,
            "vlPago": 29000.0,
            "nivel": "Bairro",
            "bairro": "Brotas",
            "prefeitura_bairro": "Centro/Brotas",
            "semaforo": {"status": "VERDE"},
        },
    ]

    b_proc, pb_proc, _ = calcular_rollup_territorial(
        bairros_resumo=bairros,
        prefeituras_resumo=prefeituras,
        obras_alocadas=obras,
    )

    comercio = next(b for b in b_proc if b["nome"] == "Comércio")
    assert comercio["is_centralidade_metropolitana"] is True
    assert comercio["isCentralidadeMetropolitana"] is True
    assert comercio["is_zona_especial_nao_residencial"] is False
    assert comercio["valorTotal"] == 9710000.0
    assert comercio["valorPago"] == 971000.0
    assert comercio["totalObras"] == 1
    assert comercio["investimentoPorHabitante"] == 0.0
    assert comercio["investimentoPorHabitantePago"] == 0.0
    assert comercio["indice_vulnerabilidade"] == comercio_demo["indice_vulnerabilidade"]

    pb_centro = next(p for p in pb_proc if p["nome"] == "Centro/Brotas")
    assert pb_centro["valorTotal"] == 10000000.0
    assert pb_centro["totalObras"] == 2
    assert pb_centro["investimentoPorHabitante"] == round(10000000.0 / 60000, 2)
    vuln_esperada_pb = round(
        (971 * comercio_demo["indice_vulnerabilidade"] + 59029 * vuln_calc["Brotas"]["indice_vulnerabilidade"]) / 60000,
        2,
    )
    assert pb_centro["indice_vulnerabilidade"] == vuln_esperada_pb


def test_rollup_bairro_residencial_populacao_zero_serializa_per_capita_nulo_e_contiguidade_pb() -> None:
    """Bairro residencial com população <= 0 (Aquarius) serializa null per capita e propaga metadados para a PB."""
    bairros = [
        {
            "id": 1,
            "nome": "Pituba",
            "prefeitura_bairro": "Barra/Pituba",
            "populacao": 57894,
            "indice_vulnerabilidade": 0.04,
            "pct_esgoto_inadequado": 0.5,
            "pct_agua_inadequada": 0.2,
            "pct_analfabetismo_15mais": 0.6,
            "vulnerabilidade_estimada_contiguidade": False,
            "is_zona_especial_nao_residencial": False,
        },
        {
            "id": 2,
            "nome": "Aquarius",
            "prefeitura_bairro": "Barra/Pituba",
            "populacao": 0,
            "indice_vulnerabilidade": 0.05,
            "pct_esgoto_inadequado": 0.6,
            "pct_agua_inadequada": 0.25,
            "pct_analfabetismo_15mais": 0.7,
            "vulnerabilidade_estimada_contiguidade": True,
            "is_zona_especial_nao_residencial": False,
        },
        {
            "id": 3,
            "nome": "Ilha de Maré",
            "prefeitura_bairro": "Subúrbio/Ilhas",
            "populacao": 4036,
            "indice_vulnerabilidade": 0.85,
            "pct_esgoto_inadequado": 94.32,
            "pct_agua_inadequada": 1.2,
            "pct_analfabetismo_15mais": 14.42,
            "vulnerabilidade_estimada_contiguidade": False,
            "is_zona_especial_nao_residencial": False,
        },
    ]
    prefeituras = [
        {"id": 1, "nome": "Barra/Pituba", "populacao_total": 57894},
        {"id": 2, "nome": "Subúrbio/Ilhas", "populacao_total": 4036},
    ]
    obras = [
        {
            "id": "obra-aquarius",
            "nivel": "Pontual",
            "bairro": "Aquarius",
            "prefeitura_bairro": "Barra/Pituba",
            "vlAtualizado": 250000.0,
            "vlPago": 100000.0,
            "semaforo": {"status": "VERDE"},
        },
    ]

    b_proc, pb_proc, _ = calcular_rollup_territorial(bairros, prefeituras, obras)

    aquarius = next(b for b in b_proc if b["nome"] == "Aquarius")
    assert aquarius["populacao"] == 0
    assert aquarius["investimentoPorHabitante"] is None
    assert aquarius["investimentoPorHabitantePago"] is None
    assert aquarius["indice_vulnerabilidade"] == 0.05
    assert aquarius["valorTotal"] == 250000.0
    assert aquarius["valorPago"] == 100000.0
    assert aquarius["totalObras"] == 1

    pb_barra = next(p for p in pb_proc if p["nome"] == "Barra/Pituba")
    assert pb_barra["vulnerabilidade_estimada_contiguidade"] is True
    assert pb_barra["bairros_vulnerabilidade_estimada"] == ["Aquarius"]
    # Aquarius tem peso populacional 0 na média ponderada da PB
    assert pb_barra["indice_vulnerabilidade"] == 0.04

    pb_suburbio = next(p for p in pb_proc if p["nome"] == "Subúrbio/Ilhas")
    assert pb_suburbio["vulnerabilidade_estimada_contiguidade"] is False
    assert pb_suburbio["bairros_vulnerabilidade_estimada"] == []


def test_generator_geojson_preserva_per_capita_nulo_e_contiguidade_prefeitura(tmp_path) -> None:
    """GeoJSONs de bairros e Prefeituras-Bairro devem preservar null per capita e metadados de contiguidade."""
    import json
    from etl.generator import generate_bairros_geojson, generate_prefeituras_geojson

    raw_bairros = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"CD_BAIRRO": 1, "NM_BAIRRO": "Aquarius", "PREFEITURA_BAIRRO": "Barra/Pituba"},
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            }
        ],
    }
    raw_pbs = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"CD_PREFEITURA_BAIRRO": 1, "NM_PREFEITURA_BAIRRO": "Barra/Pituba"},
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            }
        ],
    }
    bairros_resumo = [
        {
            "nome": "Aquarius",
            "prefeitura_bairro": "Barra/Pituba",
            "populacao": 0,
            "indice_vulnerabilidade": 0.05,
            "vulnerabilidade_estimada_contiguidade": True,
            "valorTotal": 250000.0,
            "valorPago": 100000.0,
            "valorPagoDisponivel": True,
            "totalObras": 1,
            "investimentoPorHabitante": None,
            "investimentoPorHabitantePago": None,
        }
    ]
    pbs_resumo = [
        {
            "nome": "Barra/Pituba",
            "populacao_total": 57894,
            "indice_vulnerabilidade": 0.04,
            "vulnerabilidade_estimada_contiguidade": True,
            "bairros_vulnerabilidade_estimada": ["Aquarius"],
            "valorTotal": 250000.0,
            "valorPago": 100000.0,
            "valorPagoDisponivel": True,
            "totalObras": 1,
            "investimentoPorHabitante": 4.32,
            "investimentoPorHabitantePago": 1.73,
        }
    ]

    b_out = tmp_path / "bairros.geojson"
    pb_out = tmp_path / "prefeituras_bairro.geojson"
    generate_bairros_geojson(raw_bairros, bairros_resumo, b_out)
    generate_prefeituras_geojson(raw_pbs, pbs_resumo, pb_out)

    b_props = json.loads(b_out.read_text(encoding="utf-8"))["features"][0]["properties"]
    assert b_props["investimentoPorHabitante"] is None
    assert b_props["investimentoPorHabitantePago"] is None

    pb_props = json.loads(pb_out.read_text(encoding="utf-8"))["features"][0]["properties"]
    assert pb_props["vulnerabilidade_estimada_contiguidade"] is True
    assert pb_props["bairros_vulnerabilidade_estimada"] == ["Aquarius"]


def test_fetch_demografia_censo_2022_preserva_falha_bloqueante_sidra_9923() -> None:
    """Coleta online via SIDRA Tabela 9923 deve continuar bloqueante em falhas de rede ou payload inválido."""
    import io
    from unittest.mock import patch
    from etl.sources.ibge_censo import fetch_demografia_censo_2022

    with patch("urllib.request.urlopen", side_effect=OSError("SIDRA indisponível")):
        with pytest.raises(OSError, match="SIDRA indisponível"):
            fetch_demografia_censo_2022()

    payload_invalido = io.BytesIO(b'[{"D2C": "93", "D1C": "123", "D1N": "Pituba", "V": "abc"}]')
    with patch("urllib.request.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = payload_invalido
        with pytest.raises(ValueError, match="Resposta inválida do Censo 2022"):
            fetch_demografia_censo_2022()


def test_artefatos_publicados_regenerados_integros_e_validos() -> None:
    """Valida a integridade dos artefatos publicados regenerados na raiz e na versão ativa."""
    import json
    from pathlib import Path
    from etl.publicacao import versao_anterior_valida, versao_publicada
    from scripts.package_pages import _validate_version

    root = Path("public/data")
    active = versao_publicada(root)
    assert active is not None
    assert versao_anterior_valida(active) is True
    _validate_version(active, active.name, "local")

    for snap in (root, active):
        idx = json.loads((snap / "index.json").read_text(encoding="utf-8"))
        b_map = {b["nome"]: b for b in idx["bairros"]}
        pb_map = {p["nome"]: p for p in idx["prefeituras_bairro"]}

        assert b_map["Aquarius"]["populacao"] == 0
        assert b_map["Aquarius"]["vulnerabilidade_estimada_contiguidade"] is True
        assert b_map["Aquarius"]["investimentoPorHabitante"] is None
        assert b_map["Aquarius"]["investimentoPorHabitantePago"] is None
        assert b_map["Aquarius"]["indice_vulnerabilidade"] > 0.0

        assert b_map["IAPI"]["indice_vulnerabilidade"] > 0.0
        assert b_map["STIEP"]["indice_vulnerabilidade"] > 0.0
        for b_real in ("Ilha de Maré", "Chame-Chame", "Colinas de Periperi"):
            assert b_map[b_real]["vulnerabilidade_estimada_contiguidade"] is False

        assert pb_map["Barra/Pituba"]["vulnerabilidade_estimada_contiguidade"] is True
        assert pb_map["Barra/Pituba"]["bairros_vulnerabilidade_estimada"] == ["Aquarius"]
        assert pb_map["Subúrbio/Ilhas"]["vulnerabilidade_estimada_contiguidade"] is False
        assert pb_map["Subúrbio/Ilhas"]["bairros_vulnerabilidade_estimada"] == []

        b_geo = json.loads((snap / "geo" / "bairros.geojson").read_text(encoding="utf-8"))
        b_geo_map = {f["properties"]["nome"]: f["properties"] for f in b_geo["features"]}
        assert b_geo_map["Aquarius"]["investimentoPorHabitante"] is None
        assert b_geo_map["Aquarius"]["investimentoPorHabitantePago"] is None

        pb_geo = json.loads((snap / "geo" / "prefeituras_bairro.geojson").read_text(encoding="utf-8"))
        pb_geo_map = {f["properties"]["nome"]: f["properties"] for f in pb_geo["features"]}
        assert pb_geo_map["Barra/Pituba"]["vulnerabilidade_estimada_contiguidade"] is True
        assert pb_geo_map["Barra/Pituba"]["bairros_vulnerabilidade_estimada"] == ["Aquarius"]
        assert pb_geo_map["Subúrbio/Ilhas"]["vulnerabilidade_estimada_contiguidade"] is False
        assert pb_geo_map["Subúrbio/Ilhas"]["bairros_vulnerabilidade_estimada"] == []


def test_curadoria_100_porcento_escopo_cidade_2017_2020_na_versao_ativa() -> None:
    """Garante 100% de cobertura da Curadoria Territorial Auditável para Escopo Cidade em 2017-2020 na versão ativa."""
    import json
    from pathlib import Path
    from etl.domain.geocoding import _carregar_curadoria_territorial
    from etl.publicacao import versao_publicada

    active = versao_publicada(Path("public/data"))
    assert active is not None, "Ponteiro de publicação ativo não encontrado"

    idx = json.loads((active / "index.json").read_text(encoding="utf-8"))
    assert "2017-2020" in idx["metadata"]["mandatosDisponiveis"]

    curadoria = _carregar_curadoria_territorial()
    obras_2017_2020_nao_loc = [
        o for o in idx["obras"]
        if "2017-2020" in (o.get("mandatos") or [])
        and o.get("nivel") == "Escopo Cidade (Não-Localizado)"
    ]
    assert obras_2017_2020_nao_loc, "Esperado ao menos um contrato de 2017-2020 em Escopo Cidade"

    faltantes = []
    invalidos = []
    for o in obras_2017_2020_nao_loc:
        chave = f"{str(o.get('cdUnidadeGestora') or '').strip()}:{str(o.get('nuContratoSigef') or '').strip()}"
        entrada = curadoria.get(chave)
        if not isinstance(entrada, dict):
            faltantes.append(chave)
            continue
        status = str(entrada.get("status") or "").strip().lower()
        trecho = str(entrada.get("trechoComprobatorio") or "").strip()
        doc = str(entrada.get("documentoOrigem") or "").strip()
        just = str(entrada.get("justificativa") or "").strip()
        if status not in {"ambiguo", "multi_frente"} or not trecho or not doc or not just:
            invalidos.append((chave, status, bool(trecho), bool(doc), bool(just)))

    assert not faltantes, f"Contratos 2017-2020 em Escopo Cidade sem curadoria: {faltantes}"
    assert not invalidos, f"Entradas de curadoria inválidas ou sem lastro: {invalidos}"

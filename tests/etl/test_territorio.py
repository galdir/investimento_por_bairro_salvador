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

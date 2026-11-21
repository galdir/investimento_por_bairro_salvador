"""Testes unitários para a máquina de estados determinística do Semáforo da Obra.

Cobre todos os gatilhos das cores Vermelho (Crítica), Amarelo (Atenção) e Verde (No Prazo).
"""

from datetime import date
import pytest

from etl.domain.semaforo import (
    classificar_semaforo,
    contrato_cancelado_sem_gasto,
    enriquecer_sinais_semaforo,
)


def test_semaforo_vermelho_por_situacao_paralisada_rescindida_ou_cancelada():
    """Gatilho Vermelho: obra com situação Paralisada, Suspensa, Rescindida ou Cancelada/Cancelado."""
    for sit in ("Paralisada", "Suspensa", "Rescindida", "Cancelado", "Cancelada"):
        obra = {
            "vlOriginal": 1000000.0,
            "vlAtualizado": 1000000.0,
            "dsSituacao": sit,
            "percentualExecutado": 50.0,
        }
        resultado = classificar_semaforo(obra, data_referencia=date(2025, 1, 1))
        assert resultado["status"] == "VERMELHO"
        assert sit in resultado["motivos"][0]


def test_semaforo_ajustar_cronograma_nao_dispara_alerta_isoladamente():
    """Ajustar Cronograma não deve disparar alerta crítico nem inatividade isoladamente."""
    obra = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1000000.0,
        "dsSituacao": "Ajustar Cronograma",
        "dtFimVigenciaOriginal": "2026-12-31",
        "dtTerminoVigenciaAtualizado": "2026-12-31",
        "percentualExecutado": 40.0,
        "dias_desde_ultima_liquidacao_ou_pagamento": 150,
    }
    resultado = classificar_semaforo(obra, data_referencia="2025-06-01")
    assert resultado["status"] == "VERDE"


def test_semaforo_limiar_95_porcento_na_vigencia_expirada_e_fallback_original():
    """Vigência expirada dispara Vermelho para < 95% (94.99%) e não dispara para >= 95% (95.0%)."""
    data_ref = "2025-06-01"
    obra_94_99 = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1000000.0,
        "dtTerminoVigenciaAtualizado": "2025-05-01T00:00:00.000Z",
        "percentualExecutado": 94.99,
        "dsSituacao": "Em Execução",
    }
    res_critico = classificar_semaforo(obra_94_99, data_referencia=data_ref)
    assert res_critico["status"] == "VERMELHO"
    assert any("vigência expirada" in m.lower() for m in res_critico["motivos"])

    # Fallback para dtFimVigenciaOriginal quando dtTerminoVigenciaAtualizado ausente
    obra_fallback_orig = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1000000.0,
        "dtFimVigenciaOriginal": "2025-05-01",
        "percentualExecutado": 90.0,
        "dsSituacao": "Em Execução",
    }
    res_fallback = classificar_semaforo(obra_fallback_orig, data_referencia=data_ref)
    assert res_fallback["status"] == "VERMELHO"
    assert any("01/05/2025" in m for m in res_fallback["motivos"])

    # Execução >= 95.0% em contrato expirado não dispara alerta de prazo vencido
    obra_95_0 = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1000000.0,
        "dtFimVigenciaOriginal": "2025-05-01",
        "dtTerminoVigenciaAtualizado": "2025-05-01",
        "percentualExecutado": 95.0,
        "dsSituacao": "Em Execução",
        "dias_desde_ultima_liquidacao_ou_pagamento": 200,
    }
    res_encerrada = classificar_semaforo(obra_95_0, data_referencia=data_ref)
    assert res_encerrada["status"] == "VERDE"

    # Contrato expirado >= 95% ainda é avaliado normalmente para Amarelo/Vermelho por variação ou prorrogação
    obra_95_prorrogada = {
        **obra_95_0,
        "dtTerminoVigenciaAtualizado": "2025-05-15",
    }
    assert classificar_semaforo(obra_95_prorrogada, data_referencia=data_ref)["status"] == "AMARELO"


def test_semaforo_vermelho_por_variacao_contratual_superior_a_25_porcento():
    """Gatilho Vermelho: Variação Contratual Acumulada superior a 25%."""
    obra_aditivo_alto = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1260000.0,  # +26%
        "dsSituacao": "Em Execução",
        "percentualExecutado": 30.0,
        "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
    }
    resultado = classificar_semaforo(obra_aditivo_alto, data_referencia=date(2025, 1, 1))
    assert resultado["status"] == "VERMELHO"
    assert any("variação contratual acumulada superior a 25%" in m.lower() for m in resultado["motivos"])


def test_semaforo_inatividade_financeira_borda_90_vs_91_dias_e_restricoes():
    """Inatividade > 90 dias exige Em Execução, vigência ativa, execução < 95% e dias > 90."""
    data_ref = date(2025, 5, 1)
    base = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1000000.0,
        "dsSituacao": "Em Execução",
        "percentualExecutado": 94.99,
        "dtTerminoVigenciaAtualizado": "2025-05-01",  # data_ref == termino -> vigente
    }

    # 90 dias exatos -> não dispara Vermelho
    assert classificar_semaforo({**base, "dias_desde_ultima_liquidacao_ou_pagamento": 90}, data_referencia=data_ref)["status"] == "VERDE"

    # 91 dias -> dispara Vermelho
    res_91 = classificar_semaforo({**base, "dias_desde_ultima_liquidacao_ou_pagamento": 91}, data_referencia=data_ref)
    assert res_91["status"] == "VERMELHO"
    assert any("90 dias" in m.lower() for m in res_91["motivos"])

    # Execução >= 95% -> não dispara inatividade
    assert classificar_semaforo(
        {**base, "percentualExecutado": 95.0, "dias_desde_ultima_liquidacao_ou_pagamento": 120},
        data_referencia=data_ref,
    )["status"] == "VERDE"

    # Vigência expirada -> não dispara inatividade (>90d) mesmo que execução >= 95%
    # e se execução < 95% dispara apenas vigência expirada (não inatividade)
    res_expirada = classificar_semaforo(
        {**base, "dtTerminoVigenciaAtualizado": "2025-04-30", "dias_desde_ultima_liquidacao_ou_pagamento": 120},
        data_referencia=data_ref,
    )
    assert res_expirada["status"] == "VERMELHO"
    assert len(res_expirada["motivos"]) == 1
    assert "vigência expirada" in res_expirada["motivos"][0].lower()


def test_semaforo_amarelo_por_prorrogacao_de_prazo_ou_aditivo():
    """Gatilho Amarelo: término atualizado maior que fim original ou flag de aditivo de prazo."""
    obra_prorrogada = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1000000.0,
        "dtFimVigenciaOriginal": "2025-06-30T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2025-12-31T00:00:00.000Z",
        "dsSituacao": "Em Execução",
        "percentualExecutado": 50.0,
    }
    resultado = classificar_semaforo(obra_prorrogada, data_referencia=date(2025, 1, 1))
    assert resultado["status"] == "AMARELO"
    assert any("prorrogação de prazo" in m.lower() for m in resultado["motivos"])

    obra_com_aditivo_prazo = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1000000.0,
        "possui_aditivo_de_prazo": True,
        "dsSituacao": "Em Execução",
        "percentualExecutado": 50.0,
        "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
    }
    assert classificar_semaforo(obra_com_aditivo_prazo, data_referencia=date(2025, 1, 1))["status"] == "AMARELO"


def test_semaforo_amarelo_por_variacao_contratual_entre_10_e_25_porcento():
    """Gatilho Amarelo: Variação Contratual Acumulada entre 10% e 25%."""
    obra_aditivo_medio = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1150000.0,  # +15%
        "dsSituacao": "Em Execução",
        "percentualExecutado": 50.0,
        "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
    }
    resultado = classificar_semaforo(obra_aditivo_medio, data_referencia=date(2025, 1, 1))
    assert resultado["status"] == "AMARELO"
    assert any("variação contratual acumulada entre 10% e 25%" in m.lower() for m in resultado["motivos"])


def test_semaforo_verde_obra_no_prazo_e_variacao_baixa():
    """Gatilho Verde: obra com vigência no prazo e Variação Contratual Acumulada menor que 10%."""
    obra_verde = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1050000.0,  # +5% (menor que 10%)
        "dtFimVigenciaOriginal": "2026-12-31T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
        "dsSituacao": "Em Execução",
        "percentualExecutado": 40.0,
    }
    resultado = classificar_semaforo(obra_verde, data_referencia=date(2025, 1, 1))
    assert resultado["status"] == "VERDE"
    assert resultado["rotulo"] == "Verde (No Prazo)"
    assert "variação contratual acumulada inferior a 10%" in resultado["motivos"][0].lower()


def test_semaforo_vermelho_preserva_motivos_amarelos_apos_criticos():
    """Quando há gatilho Vermelho e Amarelo, mantém VERMELHO e lista motivos críticos antes dos de atenção."""
    obra = {
        "vlOriginal": 1000000.0,
        "vlAtualizado": 1150000.0,  # +15% -> Amarelo
        "dtFimVigenciaOriginal": "2025-06-30",
        "dtTerminoVigenciaAtualizado": "2025-12-31",  # Prorrogada -> Amarelo
        "possui_aditivo_de_prazo": True,  # -> Amarelo
        "dsSituacao": "Paralisada",  # -> Vermelho
        "percentualExecutado": 50.0,
    }
    resultado = classificar_semaforo(obra, data_referencia=date(2025, 1, 1))
    assert resultado["status"] == "VERMELHO"
    assert len(resultado["motivos"]) == 4
    assert "situação cadastral de alerta" in resultado["motivos"][0].lower()
    assert "prorrogação de prazo concedida" in resultado["motivos"][1].lower()
    assert "termo aditivo de prorrogação de prazo" in resultado["motivos"][2].lower()
    assert "variação contratual acumulada entre 10% e 25%" in resultado["motivos"][3].lower()


def test_enriquecer_sinais_semaforo_puro_e_extracao_completa():
    """Enriquecimento não muta entradas, propaga datas, filtra aditivos de prazo e calcula inatividade."""
    obra = {
        "id": "1",
        "dsSituacao": "Em Execução",
        "dtFimVigenciaAtualizado": "2025-12-31",  # alias existente não deve ser sobrescrito
    }
    ficha = {
        "vigencia": {
            "dataInicio": "2024-01-01",
            "dataFimOriginal": "2025-06-30",
            "dataTerminoAtualizado": "2025-10-15",
        },
        "aditivos": [
            {"dsTipoAlteracao": "Redução de Prazo"},
            {"dsTipoAlteracao": "Renovação de Serviço Continuado"},
            {"dsTipoAlteracao": "Prorrogação de Prazo"},
        ],
        "liquidacoes": [
            {"dataLiquidacao": "15/02/2025"},  # BR
        ],
        "pagamentos": [
            {"dataPagamento": "2025-03-01"},  # ISO mais recente
        ],
    }

    enriquecida = enriquecer_sinais_semaforo(obra, ficha, data_referencia="2025-06-01")

    # Pureza / não-mutação
    assert "dtFimVigenciaOriginal" not in obra
    assert "possui_aditivo_de_prazo" not in obra
    assert "dias_desde_ultima_liquidacao_ou_pagamento" not in obra

    # Datas propagadas respeitando aliases existentes
    assert enriquecida["dtInicioVigencia"] == "2024-01-01"
    assert enriquecida["dtFimVigenciaOriginal"] == "2025-06-30"
    assert enriquecida["dtFimVigenciaAtualizado"] == "2025-12-31"
    assert "dtTerminoVigenciaAtualizado" not in enriquecida

    # Aditivo de prorrogação de prazo
    assert enriquecida["possui_aditivo_de_prazo"] is True

    # Inatividade: 2025-06-01 - 2025-03-01 = 92 dias
    assert enriquecida["dias_desde_ultima_liquidacao_ou_pagamento"] == 92


def test_enriquecer_sinais_semaforo_filtros_aditivo_fallback_inicio_e_data_futura():
    """Exclui redução/renovação, preserva flag OR, usa dataInicio sem movimentações e limita a >= 0."""
    # Sem prorrogação real, mas com redução e renovação -> False
    obra_sem_flag = {"id": "2"}
    ficha_sem_mov = {
        "vigencia": {"dataInicio": "2025-01-01"},
        "aditivos": [
            {"tipoAlteracao": "Redução de Prazo"},
            {"tipoAlteracao": "Renovação de Serviço Continuado"},
        ],
        "liquidacoes": [],
        "pagamentos": [],
    }
    res = enriquecer_sinais_semaforo(obra_sem_flag, ficha_sem_mov, data_referencia=date(2025, 4, 2))
    assert res["possui_aditivo_de_prazo"] is False
    assert res["dias_desde_ultima_liquidacao_ou_pagamento"] == 91

    # Preserva flag já verdadeira via OR e limita dias futuros a 0
    obra_com_flag = {"id": "3", "possuiAditivoPrazo": True}
    ficha_futura = {
        "vigencia": {},
        "aditivos": [],
        "liquidacoes": [],
        "pagamentos": [{"dataPagamento": "20/05/2025"}],
    }
    res_futuro = enriquecer_sinais_semaforo(obra_com_flag, ficha_futura, data_referencia="2025-05-01")
    assert res_futuro["possui_aditivo_de_prazo"] is True
    assert res_futuro["dias_desde_ultima_liquidacao_ou_pagamento"] == 0

    # Sem movimentações e sem data de início -> 0 dias
    res_zero = enriquecer_sinais_semaforo({"id": "4"}, {"vigencia": {}}, data_referencia="2025-05-01")
    assert res_zero["dias_desde_ultima_liquidacao_ou_pagamento"] == 0


def test_contrato_cancelado_sem_gasto_elegivel_e_bordas_conservadoras():
    """Predicado puro de expurgo exige cancelamento, apuração concluída e ausência estrita de gasto."""
    obra_cancelada = {"id": "10", "dsSituacao": "Cancelado"}
    ficha_elegivel = {
        "situacao": "Cancelado",
        "consultaPagamentosConcluida": True,
        "funilFinanceiro": {"valorLiquidado": 0.0, "valorPago": 0.0},
        "liquidacoes": [],
        "pagamentos": [],
    }
    assert contrato_cancelado_sem_gasto(obra_cancelada, ficha_elegivel) is True

    # Aceita Cancelada, liquidado <= 0, movimentos zerados/negativos e liquidação com líquido 0 e bruto 0
    ficha_cancelada_estorno = {
        "situacao": "Cancelada",
        "consultaPagamentosConcluida": True,
        "funilFinanceiro": {"valorLiquidado": -50.0, "valorPago": 0.0},
        "liquidacoes": [{"valLiqLiquidacao": 0.0, "valBrutLiquidacao": 0.0}],
        "pagamentos": [{"pago": "R$ 0,00"}, {"pago": -10.0}],
    }
    assert contrato_cancelado_sem_gasto({"id": "11"}, ficha_cancelada_estorno) is True

    # 1. Apuração de pagamentos não concluída -> False
    assert contrato_cancelado_sem_gasto(
        obra_cancelada,
        {**ficha_elegivel, "consultaPagamentosConcluida": False},
    ) is False
    assert contrato_cancelado_sem_gasto(
        obra_cancelada,
        {k: v for k, v in ficha_elegivel.items() if k != "consultaPagamentosConcluida"},
    ) is False

    # 2. Valor liquidado consolidado nulo/indisponível -> False
    assert contrato_cancelado_sem_gasto(
        obra_cancelada,
        {**ficha_elegivel, "funilFinanceiro": {"valorLiquidado": None, "valorPago": 0.0}},
    ) is False
    assert contrato_cancelado_sem_gasto(
        obra_cancelada,
        {**ficha_elegivel, "funilFinanceiro": {"valorPago": 0.0}},
    ) is False

    # 3. Valor pago consolidado nulo ou diferente de zero -> False
    assert contrato_cancelado_sem_gasto(
        obra_cancelada,
        {**ficha_elegivel, "funilFinanceiro": {"valorLiquidado": 0.0, "valorPago": None}},
    ) is False
    assert contrato_cancelado_sem_gasto(
        obra_cancelada,
        {**ficha_elegivel, "funilFinanceiro": {"valorLiquidado": 0.0, "valorPago": -1.0}},
    ) is False

    # 4. Movimento de pagamento com valor textual inválido, ausente ou positivo -> False
    assert contrato_cancelado_sem_gasto(
        obra_cancelada,
        {**ficha_elegivel, "pagamentos": [{"pago": "indisponivel"}]},
    ) is False
    assert contrato_cancelado_sem_gasto(
        obra_cancelada,
        {**ficha_elegivel, "pagamentos": [{"ordemBancaria": "OB1"}]},
    ) is False
    assert contrato_cancelado_sem_gasto(
        obra_cancelada,
        {**ficha_elegivel, "pagamentos": [{"pago": 100.0}, {"pago": -100.0}]},
    ) is False

    # 5. Liquidação com valor bruto positivo quando o líquido é zero/ausente, ou ambos ausentes/inválidos -> False
    assert contrato_cancelado_sem_gasto(
        obra_cancelada,
        {**ficha_elegivel, "liquidacoes": [{"valLiqLiquidacao": 0.0, "valBrutLiquidacao": 500.0}]},
    ) is False
    assert contrato_cancelado_sem_gasto(
        obra_cancelada,
        {**ficha_elegivel, "liquidacoes": [{"valBrutLiquidacao": 250.0}]},
    ) is False
    assert contrato_cancelado_sem_gasto(
        obra_cancelada,
        {**ficha_elegivel, "liquidacoes": [{"notaLiquidacao": "NL1"}]},
    ) is False
    assert contrato_cancelado_sem_gasto(
        obra_cancelada,
        {**ficha_elegivel, "liquidacoes": [{"valLiqLiquidacao": "N/A", "valBrutLiquidacao": None}]},
    ) is False

    # 6. Situação divergente entre listagem inicial e ficha consolidada: prevalece a ficha (com fallback para obra)
    assert contrato_cancelado_sem_gasto(
        {"id": "12", "dsSituacao": "Cancelado"},
        {**ficha_elegivel, "situacao": "Em Execução"},
    ) is False
    assert contrato_cancelado_sem_gasto(
        {"id": "13", "dsSituacao": "Em Execução"},
        {**ficha_elegivel, "situacao": "Cancelado"},
    ) is True
    assert contrato_cancelado_sem_gasto(
        {"id": "14", "dsSituacao": "Cancelada"},
        {k: v for k, v in ficha_elegivel.items() if k != "situacao"},
    ) is True

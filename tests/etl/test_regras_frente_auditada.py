"""Testes para Regras de Frente Auditada e guardrails compartilhados."""

import json
from pathlib import Path
import pytest

from etl.domain.geocoding import (
    avaliar_guardrails_nota_liquidacao,
    resolver_frentes_medicao,
)
from tests.etl.fixtures.sample_data import SAMPLE_GEOSALVADOR_BAIRROS


@pytest.mark.parametrize(
    ("desc", "val_liq", "pagamentos", "motivos_esperados"),
    [
        # (a) Multi-obra: 2+ códigos de obra
        (
            "SERVICOS NAS OBRAS D001 E D002 NO BAIRRO PITUBA - NFSE 123",
            "10.000,00",
            None,
            {"multi_obra"},
        ),
        (
            "MEDICAO E 001 E E 002 CONTENCAO DE ENCOSTA - NF 45",
            "15.000,00",
            None,
            {"multi_obra"},
        ),
        (
            "OBRA 001 E OBRA 002 PAVIMENTACAO",
            "8.000,00",
            None,
            {"multi_obra"},
        ),
        # (a) Multi-obra: ';' seguido de novo código de obra ou prefixo de serviço/logradouro
        (
            "RUA DAS FLORES, PITUBA; RUA DO SOL, BROTAS - NFSE 10",
            "12.000,00",
            None,
            {"multi_obra"},
        ),
        (
            "CONTENCAO ENCOSTA PITUBA; SERV. DRENAGEM BROTAS",
            "12.000,00",
            None,
            {"multi_obra"},
        ),
        # (b) Truncamento ambíguo: >= 88 chars terminando em pontuação pendente ou parêntese aberto
        (
            "EXECUCAO DE SERVICOS DE CONTENCAO DE ENCOSTA NA RUA PRINCIPAL DO BAIRRO DA PITUBA, TRECHO 02,",
            "20.000,00",
            None,
            {"truncamento_ambiguo"},
        ),
        (
            "EXECUCAO DE SERVICOS DE CONTENCAO DE ENCOSTA NA RUA PRINCIPAL DO BAIRRO DA PITUBA (TRECHO 02",
            "20.000,00",
            None,
            {"truncamento_ambiguo"},
        ),
        # (b) Truncamento ambíguo: faixa 88..91 chars sem marcador de fechamento nos últimos 30 chars
        (
            "EXECUCAO DE SERVICOS DE PAVIMENTACAO ASFALTICA NA RUA PRINCIPAL DO BAIRRO DA PITUBA TRECHO",
            "20.000,00",
            None,
            {"truncamento_ambiguo"},
        ),
        # (c) Estorno ou saldo não positivo
        (
            "ESTORNO DA NOTA DE LIQUIDACAO 2025NL001000 REFERENTE A PITUBA",
            "10.000,00",
            None,
            {"estorno_ou_saldo_nao_positivo"},
        ),
        (
            "SERVICOS DE PAVIMENTACAO NA PITUBA - ANULACAO PARCIAL",
            "10.000,00",
            None,
            {"estorno_ou_saldo_nao_positivo"},
        ),
        (
            "CANCELAMENTO DE MEDICAO NA PITUBA REFERENTE AO MES 04/2025",
            "10.000,00",
            None,
            {"estorno_ou_saldo_nao_positivo"},
        ),
        (
            "SERVICOS DE PAVIMENTACAO NA PITUBA",
            "0,00",
            None,
            {"estorno_ou_saldo_nao_positivo"},
        ),
        (
            "SERVICOS DE PAVIMENTACAO NA PITUBA",
            "10.000,00",
            [{"notaLiquidacao": "2025NL0001", "pago": "10.000,00"}, {"notaLiquidacao": "2025NL0001", "pago": "-10.000,00"}],
            {"estorno_ou_saldo_nao_positivo"},
        ),
    ],
)
def test_guardrails_bloqueiam_notas_com_risco(
    desc: str,
    val_liq: str,
    pagamentos: list[dict] | None,
    motivos_esperados: set[str],
) -> None:
    """Garante que os 3 guardrails bloqueiam multi-obra, truncamento ambíguo e estorno/saldo <= 0."""
    nota = {
        "notaLiquidacao": "2025NL0001",
        "descObsLiquidacao": desc,
        "valLiqLiquidacao": val_liq,
    }
    motivos = set(avaliar_guardrails_nota_liquidacao(nota, pagamentos=pagamentos))
    assert motivos_esperados.issubset(motivos)


@pytest.mark.parametrize(
    ("desc", "val_liq", "pagamentos"),
    [
        # ';' separando apenas metadados administrativos
        (
            "112721/2025; Manutenção Terminal Maritimo Plataforma; 05/2025; 008/2024; nf 1490",
            "42.243,32",
            None,
        ),
        # ';' seguido de contrato administrativo (CONT. / CONTRATO) não é multi-obra
        (
            "OBRA D001 RUA DA PAZ, PITUBA; CONT. 008/2024; NFSE 1490",
            "25.000,00",
            None,
        ),
        # >= 88 chars (faixa 88..91) com marcador de fechamento nos últimos 30 chars e sem pontuação pendente
        (
            "EXECUCAO DE SERVICOS DE PAVIMENTACAO NA RUA PRINCIPAL DO BAIRRO DA PITUBA, SALVADOR/BA.",
            "30.000,00",
            None,
        ),
        (
            "EXECUCAO DE SERVICOS DE PAVIMENTACAO NA RUA PRINCIPAL DO BAIRRO DA PITUBA, CONT.008/2024.",
            "30.000,00",
            None,
        ),
        # Nota liquidada válida sem registro vinculado na lista de pagamentos
        (
            "EXECUCAO DE CONTENCAO DE ENCOSTA NA RUA DA PAZ, PITUBA - NFSE 200",
            "18.500,00",
            [{"notaLiquidacao": "2025NL9999", "pago": "5.000,00"}],
        ),
    ],
)
def test_guardrails_liberam_notas_validas(
    desc: str,
    val_liq: str,
    pagamentos: list[dict] | None,
) -> None:
    """Garante que notas limpas (metadados com ';', fechamento explícito, sem pagamento vinculado) passam."""
    nota = {
        "notaLiquidacao": "2025NL0001",
        "descObsLiquidacao": desc,
        "valLiqLiquidacao": val_liq,
    }
    assert avaliar_guardrails_nota_liquidacao(nota, pagamentos=pagamentos) == []



def _obra_multi_frente() -> dict:
    return {
        "id": 9100,
        "cdUnidadeGestora": "616002",
        "nuContratoSigef": "2024CT009999",
        "dsObjeto": "Contrato guarda-chuva de drenagem e pavimentacao",
    }


def _regra_base(**overrides: object) -> dict:
    regra = {
        "id": "regra-pituba-trav",
        "status": "promovido",
        "nivel": "Bairro",
        "bairro": "Pituba",
        "contemTodos": ["TRAV. SAO JOAO", "PITUBA"],
        "trechoComprobatorio": "SERVICOS NA TRAV. SAO JOAO - PITUBA",
        "documentoOrigem": "descObsLiquidacao (Contrato 999/2024)",
        "justificativa": "Frente unitaria verificada no bairro Pituba.",
    }
    regra.update(overrides)
    return regra


def test_precedencia_manual_sobre_regras_e_veto_estornado() -> None:
    """frentesMedicao manual tem precedência absoluta, inclusive quando veta com ambiguo/estornado."""
    curadoria = {
        "616002:2024CT009999": {
            "status": "multi_frente",
            "frentesMedicao": {
                "2025NL0001": {
                    "status": "promovido",
                    "nivel": "Bairro",
                    "bairro": "Brotas",
                    "trechoComprobatorio": "Manual Brotas",
                    "documentoOrigem": "NL 0001",
                    "justificativa": "Override manual para Brotas.",
                },
                "2025NL0002": {
                    "status": "estornado",
                    "nivel": "Escopo Cidade (Não-Localizado)",
                    "trechoComprobatorio": "Estornada manualmente",
                    "documentoOrigem": "NL 0002",
                    "justificativa": "Nota vetada manualmente.",
                },
            },
            "regrasFrentes": [_regra_base()],
        }
    }
    liquidacoes = [
        {
            "notaLiquidacao": "2025NL0001",
            "valLiqLiquidacao": "10.000,00",
            "descObsLiquidacao": "SERVICOS NA TRAV. SAO JOAO, PITUBA - NFSE 10",
        },
        {
            "notaLiquidacao": "2025NL0002",
            "valLiqLiquidacao": "12.000,00",
            "descObsLiquidacao": "SERVICOS NA TRAV. SAO JOAO, PITUBA - NFSE 11",
        },
        {
            "notaLiquidacao": "2025NL0003",
            "valLiqLiquidacao": "15.000,00",
            "descObsLiquidacao": "SERVICOS NA 2ª MEDICAO TRAV SAO JOAO, PITUBA - NFSE 12",
        },
    ]
    pagamentos = [
        {"notaLiquidacao": "2025NL0001", "pago": "10.000,00"},
        {"notaLiquidacao": "2025NL0002", "pago": "12.000,00"},
    ]

    frentes = resolver_frentes_medicao(
        obra=_obra_multi_frente(),
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        liquidacoes=liquidacoes,
        pagamentos=pagamentos,
        curadoria=curadoria,
    )

    assert [f["notaLiquidacao"] for f in frentes] == ["2025NL0001", "2025NL0003"]
    assert frentes[0]["bairro"] == "Brotas"
    assert "regraFrenteId" not in frentes[0]
    assert frentes[1]["bairro"] == "Pituba"
    assert frentes[1]["prefeituraBairro"] == "Barra/Pituba"
    assert frentes[1]["regraFrenteId"] == "regra-pituba-trav"
    assert frentes[1]["valorLiquidado"] == 15000.0
    assert frentes[1]["valorPago"] == 0.0


def test_regras_ignoradas_fora_de_multi_frente_ou_nao_promovidas() -> None:
    """Regras fora de contratos multi_frente ou com status != promovido são ignoradas sem erro."""
    curadoria_nao_mf = {
        "616002:2024CT009999": {
            "status": "ambiguo",
            "regrasFrentes": [_regra_base()],
        }
    }
    liquidacoes = [
        {
            "notaLiquidacao": "2025NL0010",
            "valLiqLiquidacao": "9.000,00",
            "descObsLiquidacao": "TRAV. SAO JOAO, PITUBA - NFSE 1",
        }
    ]
    assert resolver_frentes_medicao(
        obra=_obra_multi_frente(),
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        liquidacoes=liquidacoes,
        curadoria=curadoria_nao_mf,
    ) == []

    curadoria_regra_inativa = {
        "616002:2024CT009999": {
            "status": "multi_frente",
            "regrasFrentes": [_regra_base(status="rascunho")],
        }
    }
    assert resolver_frentes_medicao(
        obra=_obra_multi_frente(),
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        liquidacoes=liquidacoes,
        curadoria=curadoria_regra_inativa,
    ) == []


@pytest.mark.parametrize(
    "regras_invalidas",
    [
        # id duplicado no contrato
        [_regra_base(id="dup"), _regra_base(id="dup", bairro="Brotas", contemTodos=["BROTAS"])],
        # contemTodos vazio
        [_regra_base(contemTodos=[])],
        # bairro não reconciliável contra os 171 Bairros Oficiais
        [_regra_base(bairro="Bairro Inexistente XYZ")],
        # ausência de campos obrigatórios de lastro
        [_regra_base(justificativa="")],
        [_regra_base(documentoOrigem=None)],
        [_regra_base(trechoComprobatorio="  ")],
    ],
)
def test_regras_malformadas_falham_explicitamente(regras_invalidas: list[dict]) -> None:
    """Validação fail-fast de esquema para regrasFrentes em contratos multi_frente."""
    curadoria = {
        "616002:2024CT009999": {
            "status": "multi_frente",
            "regrasFrentes": regras_invalidas,
        }
    }
    with pytest.raises(ValueError):
        resolver_frentes_medicao(
            obra=_obra_multi_frente(),
            bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
            liquidacoes=[],
            curadoria=curadoria,
        )


def test_casamento_fronteira_alfanumerica_abreviacoes_e_excluir_se_contiver() -> None:
    """Casamento usa fronteira alfanumérica (nunca substring livre), tolera TRAV./JD./2ª e respeita excluirSeContiver."""
    curadoria = {
        "616002:2024CT009999": {
            "status": "multi_frente",
            "regrasFrentes": [
                _regra_base(
                    id="regra-barra-jd",
                    bairro="Barra",
                    contemTodos=["JD. BRASIL", "2ª TRAV.", "BARRA"],
                    excluirSeContiver=["ONDINA"],
                )
            ],
        }
    }
    liquidacoes = [
        # Deve casar: abreviações com/sem pontuação e 2ª
        {
            "notaLiquidacao": "2025NL0101",
            "valLiqLiquidacao": "5.000,00",
            "descObsLiquidacao": "OBRA JD BRASIL, 2ª TRAV DA BARRA - NF 1",
        },
        # Não deve casar: substring livre (BARRACA != BARRA)
        {
            "notaLiquidacao": "2025NL0102",
            "valLiqLiquidacao": "5.000,00",
            "descObsLiquidacao": "OBRA JD. BRASIL, 2ª TRAV. DA BARRACA - NF 2",
        },
        # Não deve casar: excluirSeContiver presente
        {
            "notaLiquidacao": "2025NL0103",
            "valLiqLiquidacao": "5.000,00",
            "descObsLiquidacao": "OBRA JD. BRASIL, 2ª TRAV. BARRA E ONDINA - NF 3",
        },
    ]
    frentes = resolver_frentes_medicao(
        obra=_obra_multi_frente(),
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        liquidacoes=liquidacoes,
        curadoria=curadoria,
    )
    assert [f["notaLiquidacao"] for f in frentes] == ["2025NL0101"]
    assert frentes[0]["regraFrenteId"] == "regra-barra-jd"


def test_abstencao_quando_duas_regras_casam_mesma_nota_e_bloqueio_guardrail() -> None:
    """Abstém se 2+ regras casam a mesma nota; bloqueia notas barradas pelos guardrails."""
    curadoria = {
        "616002:2024CT009999": {
            "status": "multi_frente",
            "regrasFrentes": [
                _regra_base(id="r1", bairro="Pituba", contemTodos=["RUA A"]),
                _regra_base(id="r2", bairro="Brotas", contemTodos=["RUA B"]),
            ],
        }
    }
    liquidacoes = [
        # Conflito entre r1 e r2 -> abstém
        {
            "notaLiquidacao": "2025NL0201",
            "valLiqLiquidacao": "10.000,00",
            "descObsLiquidacao": "SERVICOS NA RUA A E RUA B - NF 10",
        },
        # Guardrail multi_obra (D001 e E 001) -> bloqueia mesmo casando r1
        {
            "notaLiquidacao": "2025NL0202",
            "valLiqLiquidacao": "10.000,00",
            "descObsLiquidacao": "OBRA D001 RUA A E OBRA E 001 - NF 11",
        },
        # Nota limpa casando apenas r1 -> promove
        {
            "notaLiquidacao": "2025NL0203",
            "valLiqLiquidacao": "10.000,00",
            "descObsLiquidacao": "OBRA D001 NA RUA A - NF 12",
        },
    ]
    frentes = resolver_frentes_medicao(
        obra=_obra_multi_frente(),
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        liquidacoes=liquidacoes,
        curadoria=curadoria,
    )
    assert [f["notaLiquidacao"] for f in frentes] == ["2025NL0203"]
    assert frentes[0]["regraFrenteId"] == "r1"


def test_retrocompatibilidade_catalogo_curadoria_atual() -> None:
    """Todas as entradas existentes do catálogo curadoria_territorial.json seguem válidas e compatíveis."""
    catalogo_path = Path(__file__).resolve().parents[2] / "etl" / "reference" / "curadoria_territorial.json"
    dados = json.loads(catalogo_path.read_text(encoding="utf-8"))
    registros = dados.get("registros", {})
    assert isinstance(registros, dict) and len(registros) > 0

    for chave, entrada in registros.items():
        cd_ug, nu_contrato = chave.split(":", 1)
        obra = {"cdUnidadeGestora": cd_ug, "nuContratoSigef": nu_contrato}
        frentes = resolver_frentes_medicao(
            obra=obra,
            bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
            liquidacoes=[],
            curadoria=registros,
        )
        assert frentes == []



def test_reconciliacao_e_rollup_conservam_valor_total_e_somam_liquidado_e_pago(tmp_path: Path) -> None:
    """Seam 3: frentes promovidas por regra somam apenas em valorLiquidado/valorPago, sem alterar valorTotal/totalObras."""
    from etl.reconcile import reconciliar_acervo_local

    geo_dir = tmp_path / "geo"
    geo_dir.mkdir(parents=True, exist_ok=True)
    bairros_geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"NM_BAIRRO": "Pituba", "PREFEITURA_BAIRRO": "Barra/Pituba"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-38.46, -13.00], [-38.45, -13.00], [-38.45, -12.99], [-38.46, -12.99], [-38.46, -13.00]]],
                },
            }
        ],
    }
    pb_geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"NM_PREFEITURA_BAIRRO": "Barra/Pituba"},
                "geometry": bairros_geo["features"][0]["geometry"],
            }
        ],
    }
    (geo_dir / "bairros.geojson").write_text(json.dumps(bairros_geo), encoding="utf-8")
    (geo_dir / "prefeituras_bairro.geojson").write_text(json.dumps(pb_geo), encoding="utf-8")

    indice = {
        "kpis": {},
        "bairros": [
            {
                "nome": "Pituba",
                "prefeitura_bairro": "Barra/Pituba",
                "populacao": 10000,
                "valorTotal": 0.0,
                "totalObras": 0,
            }
        ],
        "prefeituras_bairro": [
            {
                "nome": "Barra/Pituba",
                "populacao": 10000,
                "valorTotal": 0.0,
                "totalObras": 0,
            }
        ],
        "obras": [
            {
                "id": "obra-mf-regra",
                "cdUnidadeGestora": "616002",
                "nuContratoSigef": "2024CT009999",
                "dsObjeto": "Contrato guarda-chuva de drenagem",
                "vlOriginal": 1000000.0,
                "vlAtualizado": 1000000.0,
                "vlEmpenhado": 500000.0,
                "vlLiquidado": 50000.0,
                "vlPago": 30000.0,
                "valorPago": 30000.0,
                "nivel": "Escopo Cidade (Não-Localizado)",
            }
        ],
    }
    (tmp_path / "index_2025.json").write_text(json.dumps(indice, ensure_ascii=False), encoding="utf-8")

    obras_dir = tmp_path / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)
    ficha = {
        "id": "obra-mf-regra",
        "cdUnidadeGestora": "616002",
        "nuContratoSigef": "2024CT009999",
        "liquidacoes": [
            {
                "notaLiquidacao": "2025NL0301",
                "valLiqLiquidacao": "50.000,00",
                "pago": "0,00",
                "descObsLiquidacao": "SERVICOS NA TRAV. SAO JOAO, PITUBA - NFSE 301",
            }
        ],
        "pagamentos": [
            {"notaLiquidacao": "2025NL0301", "pago": "30.000,00"},
        ],
    }
    (obras_dir / "obra-mf-regra.json").write_text(json.dumps(ficha, ensure_ascii=False), encoding="utf-8")

    curadoria = {
        "616002:2024CT009999": {
            "status": "multi_frente",
            "regrasFrentes": [_regra_base()],
        }
    }

    reconciliar_acervo_local(output_dir=tmp_path, year=2025, curadoria=curadoria)

    idx_atualizado = json.loads((tmp_path / "index_2025.json").read_text(encoding="utf-8"))
    ficha_atualizada = json.loads((obras_dir / "obra-mf-regra.json").read_text(encoding="utf-8"))

    assert len(ficha_atualizada["frentesMedicao"]) == 1
    assert ficha_atualizada["frentesMedicao"][0]["regraFrenteId"] == "regra-pituba-trav"

    pituba = idx_atualizado["bairros"][0]
    assert pituba["valorTotal"] == 0.0
    assert pituba["totalObras"] == 0
    assert pituba["valorLiquidado"] == 50000.0
    assert pituba["valorPago"] == 30000.0
    assert pituba["valorLiquidadoFrentes"] == 50000.0
    assert pituba["valorPagoFrentes"] == 30000.0
    assert pituba["totalFrentesMedicao"] == 1

    pb = idx_atualizado["prefeituras_bairro"][0]
    assert pb["valorTotal"] == 0.0
    assert pb["totalObras"] == 0
    assert pb["valorLiquidado"] == 50000.0
    assert pb["valorPago"] == 30000.0
    assert pb["totalFrentesMedicao"] == 1



def test_regra_regional_prefeitura_bairro_e_validacao_fail_fast() -> None:
    """Regras de nível Regional (Prefeitura-Bairro) promovem sem bairro e falham sem prefeituraBairro."""
    curadoria_valida = {
        "616002:2024CT009999": {
            "status": "multi_frente",
            "regrasFrentes": [
                {
                    "id": "regra-regional-barra-pituba",
                    "status": "promovido",
                    "nivel": "Regional (Prefeitura-Bairro)",
                    "prefeituraBairro": "VI - Barra / Pituba",
                    "contemTodos": ["MANUTENCAO", "BARRA PITUBA"],
                    "trechoComprobatorio": "MANUTENCAO REGIONAL BARRA PITUBA",
                    "documentoOrigem": "descObsLiquidacao",
                    "justificativa": "Frente regional comprovada.",
                }
            ],
        }
    }
    liquidacoes = [
        {
            "notaLiquidacao": "2025NL0401",
            "valLiqLiquidacao": "22.000,00",
            "descObsLiquidacao": "SERVICOS DE MANUTENCAO NA PREFEITURA BAIRRO BARRA/PITUBA - NF 40",
        }
    ]
    frentes = resolver_frentes_medicao(
        obra=_obra_multi_frente(),
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        liquidacoes=liquidacoes,
        curadoria=curadoria_valida,
    )
    assert len(frentes) == 1
    assert frentes[0]["nivel"] == "Regional (Prefeitura-Bairro)"
    assert frentes[0]["bairro"] is None
    assert frentes[0]["prefeituraBairro"] == "Barra/Pituba"
    assert frentes[0]["regraFrenteId"] == "regra-regional-barra-pituba"

    curadoria_invalida = {
        "616002:2024CT009999": {
            "status": "multi_frente",
            "regrasFrentes": [
                {
                    "id": "regra-regional-sem-pb",
                    "status": "promovido",
                    "nivel": "Regional (Prefeitura-Bairro)",
                    "contemTodos": ["MANUTENCAO"],
                    "trechoComprobatorio": "MANUTENCAO",
                    "documentoOrigem": "descObsLiquidacao",
                    "justificativa": "Falta prefeituraBairro.",
                }
            ],
        }
    }
    with pytest.raises(ValueError):
        resolver_frentes_medicao(
            obra=_obra_multi_frente(),
            bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
            liquidacoes=[],
            curadoria=curadoria_invalida,
        )

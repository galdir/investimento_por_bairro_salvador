"""Testes da Seam 1 para reconciliação canônica do acervo local, unificação de empreiteiras e blindagem incremental do ETL."""

import copy
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from etl.runner import run_pipeline

from tests.etl.fixtures.sample_data import (
    SAMPLE_GEOSALVADOR_BAIRROS,
    SAMPLE_GEOSALVADOR_PREFEITURAS,
    SAMPLE_IBGE_CENSO_2022,
    SAMPLE_TRANSPARENCIA_TOTALIZADOR,
)


def _criar_geo_minimo(tmp_path: Path) -> None:
    """Cria GeoJSONs mínimos compatíveis com o acervo local para validar atualização territorial."""
    geo_dir = tmp_path / "geo"
    geo_dir.mkdir(parents=True, exist_ok=True)
    bairros_geo = copy.deepcopy(SAMPLE_GEOSALVADOR_BAIRROS)
    pb_geo = copy.deepcopy(SAMPLE_GEOSALVADOR_PREFEITURAS)
    (geo_dir / "bairros.geojson").write_text(
        json.dumps(bairros_geo, ensure_ascii=False), encoding="utf-8"
    )
    (geo_dir / "prefeituras_bairro.geojson").write_text(
        json.dumps(pb_geo, ensure_ascii=False), encoding="utf-8"
    )


def test_reconciliar_acervo_local_resgata_versoes_unifica_empreiteiras_e_remove_orfaos(
    tmp_path: Path,
) -> None:
    """Valida na Seam 1 que reconciliar_acervo_local consolida 3 versões locais, unifica empreiteiras e expurga órfãos."""
    from etl.reconcile import reconciliar_acervo_local

    _criar_geo_minimo(tmp_path)
    obras_dir = tmp_path / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)

    # Obra A: ficha ativa esvaziada + 2 cópias órfãs complementares (total 3 versões locais)
    id_a_ativo = "uuid-a-ativo"
    id_a_orfao_contabil = "uuid-a-orfao-contabil"
    id_a_orfao_meta = "uuid-a-orfao-meta"

    # Obra B: mesma empreiteira (com variação de espaços/caixa e sem CNPJ), sem pagamentos
    id_b_ativo = "uuid-b-ativo"

    index_inicial = {
        "metadata": {
            "generatedAt": "2026-01-01T00:00:00+00:00",
            "anoReferencia": 2025,
            "mandatosDisponiveis": ["2021-2024", "2025-2028"],
        },
        "kpis_globais": {
            "totalObras": 2,
            "valorTotal": 3000000.0,
            "totalAtivas": 2,
            "totalCriticas": 0,
            "percentualCriticas": 0.0,
            "totalAditivosValor": 500000.0,
            "percentualMedioAditivos": 50.0,
            "totalEmpenhado": 120000000.0,
            "totalLiquidado": 95000000.0,
            "totalPago": 90000000.0,
            "investimentoPorHabitanteCidade": 1.0,
            "totalNaoLocalizado": 0,
            "valorNaoLocalizado": 0.0,
            "percentualNaoLocalizado": 0.0,
        },
        "concentracao_empreiteiras": [],
        "prefeituras_bairro": [
            {
                "id": 6,
                "nome": "Barra/Pituba",
                "populacao_total": 66417,
                "indice_vulnerabilidade": 0.13,
                "pct_esgoto_inadequado": 0.5,
                "pct_agua_inadequada": 0.1,
                "pct_analfabetismo_15mais": 0.6,
                "valorTotal": 3000000.0,
                "valorPago": 0.0,
                "totalObras": 2,
                "obrasVerde": 2,
                "obrasAmarelo": 0,
                "obrasVermelho": 0,
                "investimentoPorHabitante": 45.17,
                "investimentoPorHabitantePago": 0.0,
            }
        ],
        "bairros": [
            {
                "id": 101,
                "nome": "Pituba",
                "prefeitura_bairro": "Barra/Pituba",
                "populacao": 57894,
                "indice_vulnerabilidade": 0.13,
                "is_zona_especial_nao_residencial": False,
                "isZonaEspecialNaoResidencial": False,
                "pct_esgoto_inadequado": 0.5,
                "pct_agua_inadequada": 0.1,
                "pct_analfabetismo_15mais": 0.6,
                "vulnerabilidade_estimada_contiguidade": False,
                "valorTotal": 3000000.0,
                "valorPago": 0.0,
                "totalObras": 2,
                "obrasVerde": 2,
                "obrasAmarelo": 0,
                "obrasVermelho": 0,
                "investimentoPorHabitante": 51.82,
                "investimentoPorHabitantePago": 0.0,
            }
        ],
        "obras": [
            {
                "id": id_a_ativo,
                "cdUnidadeGestora": "616002",
                "unidadeGestora": "SUCOP",
                "nuContratoSigef": "2024CT000001",
                "numeroContrato": "2024CT000001",
                "objeto": "Drenagem na Pituba",
                "valorOriginal": 1000000.0,
                "valorContratualVigente": 1500000.0,
                "valorAditivos": 500000.0,
                "deltaPercentualValor": 50.0,
                "valorPago": 900000.0,  # estimativa por 60% antes do resgate
                "percentualExecutado": 60.0,
                "situacao": "Em Execução",
                "credor": "CONSTRUTORA UNIFICADA LTDA",
                "cnpj": "",
                "cnpjCredor": "",
                "tema": "Mobilidade, Pavimentação e Drenagem",
                "semaforo": {"status": "VERDE", "rotulo": "No Prazo", "motivos": []},
                "ano": 2024,
                "mandatos": ["2021-2024", "2025-2028"],
                "dtInicioVigencia": "2024-02-01T00:00:00.000Z",
                "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
                "nivel": "Bairro",
                "bairro": "Pituba",
                "prefeituraBairro": "Barra/Pituba",
                "prefeitura_bairro": "Barra/Pituba",
                "latitude": -12.999,
                "longitude": -38.458,
                "estagioAlocacao": "Bairro",
            },
            {
                "id": id_b_ativo,
                "cdUnidadeGestora": "567002",
                "unidadeGestora": "SEMAN",
                "nuContratoSigef": "2025CT000002",
                "numeroContrato": "2025CT000002",
                "objeto": "Reforma de praça na Pituba",
                "valorOriginal": 1500000.0,
                "valorContratualVigente": 1500000.0,
                "valorAditivos": 0.0,
                "deltaPercentualValor": 0.0,
                "valorPago": 750000.0,
                "percentualExecutado": 50.0,
                "situacao": "Em Execução",
                "credor": "Construtora  Unificada  Ltda",
                "cnpj": "",
                "cnpjCredor": "",
                "tema": "Praças, Esporte e Lazer",
                "semaforo": {"status": "VERDE", "rotulo": "No Prazo", "motivos": []},
                "ano": 2025,
                "mandatos": ["2025-2028"],
                "dtInicioVigencia": "2025-01-10T00:00:00.000Z",
                "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
                "nivel": "Bairro",
                "bairro": "Pituba",
                "prefeituraBairro": "Barra/Pituba",
                "prefeitura_bairro": "Barra/Pituba",
                "latitude": -12.998,
                "longitude": -38.457,
                "estagioAlocacao": "Bairro",
            },
        ],
    }
    (tmp_path / "index_2025.json").write_text(
        json.dumps(index_inicial, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "index.json").write_text(
        json.dumps(index_inicial, ensure_ascii=False), encoding="utf-8"
    )

    ficha_a_ativa_vazia = {
        "id": id_a_ativo,
        "unidadeGestora": "SUCOP",
        "numeroContrato": "2024CT000001",
        "numeroContratoOriginal": "2024CT000001",
        "nuProcesso": None,
        "objeto": "Drenagem na Pituba",
        "situacao": "Em Execução",
        "empreiteira": {
            "razaoSocial": "CONSTRUTORA UNIFICADA LTDA",
            "cnpj": "",
            "totalObras": 1,
            "totalObrasAtivas": 1,
            "valorTotalContratado": 1500000.0,
            "outrasObrasCount": 0,
            "outrasObrasIds": [],
        },
        "vigencia": {
            "dataInicio": "2024-02-01T00:00:00.000Z",
            "dataFimOriginal": None,
            "dataTerminoAtualizado": "2026-12-31T00:00:00.000Z",
            "prazoOriginal": "Conforme Contrato",
            "prazoAtualizado": "Conforme Contrato",
        },
        "dom": {"nuDom": "Não informado", "dataPublicacao": "2024-02-01T00:00:00.000Z"},
        "funilFinanceiro": {
            "valorOriginal": 1000000.0,
            "valorContratualVigente": 1500000.0,
            "valorEmpenhado": 1500000.0,
            "valorLiquidado": 0.0,
            "valorPago": 0.0,
            "percentualExecutado": 60.0,
            "valorAditivos": 500000.0,
            "deltaPercentualAditivos": 50.0,
        },
        "aditivos": [],
        "dotacao": [
            {
                "subacao": "Infraestrutura Urbana Municipal",
                "fonteRecurso": "Tesouro Municipal (Recursos Ordinários)",
                "classificacao": "4.4.90.51 - Obras e Instalações",
            }
        ],
        "empenhos": [],
        "liquidacoes": [],
        "pagamentos": [],
    }

    ficha_a_orfao_1 = copy.deepcopy(ficha_a_ativa_vazia)
    ficha_a_orfao_1["id"] = id_a_orfao_contabil
    ficha_a_orfao_1["empreiteira"]["cnpj"] = "12.345.678/0001-90"
    ficha_a_orfao_1["empenhos"] = [
        {"notaEmpenho": "2024NE0001", "valEmpenhado": "1.200.000,00"}
    ]
    ficha_a_orfao_1["liquidacoes"] = [
        {"notaLiquidacao": "2024NL0001", "valLiqLiquidacao": "800.000,00"}
    ]
    ficha_a_orfao_1["pagamentos"] = [
        {"ordemBancaria": "2024OB0001", "pago": "500.000,00"}
    ]
    ficha_a_orfao_1["aditivos"] = [
        {
            "nuAditivo": "1º Aditivo",
            "dsTipoAlteracao": "Valor",
            "dsObjetoAditivo": "Reforço de drenagem",
            "dtAssinatura": "2024-10-01",
            "dtTerminoVigencia": "2026-12-31",
            "dtPublicacao": "2024-10-05",
            "nuDom": "Não informado",
            "vlAditivo": 500000.0,
        }
    ]

    ficha_a_orfao_2 = copy.deepcopy(ficha_a_ativa_vazia)
    ficha_a_orfao_2["id"] = id_a_orfao_meta
    ficha_a_orfao_2["numeroContratoOriginal"] = "001/2024"
    ficha_a_orfao_2["nuProcesso"] = "123456/2023"
    ficha_a_orfao_2["vigencia"] = {
        "dataInicio": "01/02/2024",
        "dataFimOriginal": "01/02/2025",
        "dataTerminoAtualizado": "31/12/2026",
        "prazoOriginal": "365",
        "prazoAtualizado": "699",
    }
    ficha_a_orfao_2["dom"] = {"nuDom": "8899", "dataPublicacao": "05/02/2024"}
    ficha_a_orfao_2["dotacao"] = [
        {
            "subacao": "Drenagem Pluvial",
            "fonteRecurso": "FINISA",
            "classificacao": "4.4.90.51 - Obras e Instalações",
        }
    ]

    ficha_b_ativa = copy.deepcopy(ficha_a_ativa_vazia)
    ficha_b_ativa["id"] = id_b_ativo
    ficha_b_ativa["unidadeGestora"] = "SEMAN"
    ficha_b_ativa["numeroContrato"] = "2025CT000002"
    ficha_b_ativa["numeroContratoOriginal"] = "2025CT000002"
    ficha_b_ativa["objeto"] = "Reforma de praça na Pituba"
    ficha_b_ativa["empreiteira"]["razaoSocial"] = "Construtora  Unificada  Ltda"
    ficha_b_ativa["funilFinanceiro"]["valorOriginal"] = 1500000.0
    ficha_b_ativa["funilFinanceiro"]["valorContratualVigente"] = 1500000.0
    ficha_b_ativa["funilFinanceiro"]["valorEmpenhado"] = 1500000.0
    ficha_b_ativa["funilFinanceiro"]["percentualExecutado"] = 50.0
    ficha_b_ativa["funilFinanceiro"]["valorAditivos"] = 0.0
    ficha_b_ativa["funilFinanceiro"]["deltaPercentualAditivos"] = 0.0

    # Inclui arquivo de amostra sintético 1001.json como órfão extra
    ficha_amostra = copy.deepcopy(ficha_a_ativa_vazia)
    ficha_amostra["id"] = 1001
    ficha_amostra["numeroContrato"] = "001/2024"

    (obras_dir / f"{id_a_ativo}.json").write_text(
        json.dumps(ficha_a_ativa_vazia, ensure_ascii=False), encoding="utf-8"
    )
    (obras_dir / f"{id_a_orfao_contabil}.json").write_text(
        json.dumps(ficha_a_orfao_1, ensure_ascii=False), encoding="utf-8"
    )
    (obras_dir / f"{id_a_orfao_meta}.json").write_text(
        json.dumps(ficha_a_orfao_2, ensure_ascii=False), encoding="utf-8"
    )
    (obras_dir / f"{id_b_ativo}.json").write_text(
        json.dumps(ficha_b_ativa, ensure_ascii=False), encoding="utf-8"
    )
    (obras_dir / "1001.json").write_text(
        json.dumps(ficha_amostra, ensure_ascii=False), encoding="utf-8"
    )

    resultado = reconciliar_acervo_local(output_dir=tmp_path, year=2025)

    assert resultado["total_obras_ativas"] == 2
    assert resultado["arquivos_orfaos_removidos"] == 3
    assert resultado["arquivos_finais_obras"] == 2

    # Correspondência estrita 1:1 em obras/
    arquivos_restantes = sorted(p.name for p in obras_dir.glob("*.json"))
    assert arquivos_restantes == sorted([f"{id_a_ativo}.json", f"{id_b_ativo}.json"])

    # Obra A recebeu mesclagem máxima de todas as 3 cópias
    ficha_a_final = json.loads((obras_dir / f"{id_a_ativo}.json").read_text(encoding="utf-8"))
    assert len(ficha_a_final["empenhos"]) == 1
    assert len(ficha_a_final["liquidacoes"]) == 1
    assert len(ficha_a_final["pagamentos"]) == 1
    assert len(ficha_a_final["aditivos"]) == 1
    assert ficha_a_final["aditivos"][0]["nuDom"] == "8899"
    assert ficha_a_final["dotacao"][0]["subacao"] == "Drenagem Pluvial"
    assert ficha_a_final["dom"]["nuDom"] == "8899"
    assert ficha_a_final["nuProcesso"] == "123456/2023"
    assert ficha_a_final["numeroContratoOriginal"] == "001/2024"
    assert ficha_a_final["vigencia"]["dataInicio"] == "2024-02-01T00:00:00.000Z"
    assert ficha_a_final["vigencia"]["dataFimOriginal"] == "2025-02-01T00:00:00.000Z"
    assert ficha_a_final["vigencia"]["dataTerminoAtualizado"] == "2026-12-31T00:00:00.000Z"
    assert ficha_a_final["funilFinanceiro"]["valorEmpenhado"] == 1200000.0
    assert ficha_a_final["funilFinanceiro"]["valorLiquidado"] == 800000.0
    assert ficha_a_final["funilFinanceiro"]["valorPago"] == 500000.0

    # Unificação de empreiteira propagada para Obra B e para concentração
    assert ficha_a_final["empreiteira"]["cnpj"] == "12.345.678/0001-90"
    assert ficha_a_final["empreiteira"]["totalObras"] == 2
    assert ficha_a_final["empreiteira"]["outrasObrasCount"] == 1
    assert ficha_a_final["empreiteira"]["outrasObrasIds"] == [id_b_ativo]

    ficha_b_final = json.loads((obras_dir / f"{id_b_ativo}.json").read_text(encoding="utf-8"))
    assert ficha_b_final["empreiteira"]["cnpj"] == "12.345.678/0001-90"
    assert ficha_b_final["empreiteira"]["totalObras"] == 2
    assert ficha_b_final["empreiteira"]["valorTotalContratado"] == 3000000.0

    # Índice atualizado: ranking unificado, valorPago real onde existe e fallback na obra B, KPIs reais
    idx_final = json.loads((tmp_path / "index_2025.json").read_text(encoding="utf-8"))
    assert len(idx_final["concentracao_empreiteiras"]) == 1
    assert idx_final["concentracao_empreiteiras"][0]["cnpj"] == "12.345.678/0001-90"
    assert idx_final["concentracao_empreiteiras"][0]["totalObras"] == 2

    obras_idx = {o["id"]: o for o in idx_final["obras"]}
    assert obras_idx[id_a_ativo]["cnpj"] == "12.345.678/0001-90"
    assert obras_idx[id_b_ativo]["cnpj"] == "12.345.678/0001-90"
    assert obras_idx[id_a_ativo]["valorPago"] == 500000.0
    assert obras_idx[id_b_ativo]["valorPago"] == 750000.0

    # KPIs globais com somas reais do Funil Financeiro (1.2M + 1.5M = 2.7M empenhado, 800k liq, 500k pago)
    kpis = idx_final["kpis_globais"]
    assert kpis["totalEmpenhado"] == 2700000.0
    assert kpis["totalLiquidado"] == 800000.0
    assert kpis["totalPago"] == 500000.0

    # Rollup territorial atualizado com valorPago = 500k + 750k = 1.25M
    pituba = next(b for b in idx_final["bairros"] if b["nome"] == "Pituba")
    assert pituba["valorPago"] == 1250000.0
    pb = next(p for p in idx_final["prefeituras_bairro"] if p["nome"] == "Barra/Pituba")
    assert pb["valorPago"] == 1250000.0


def test_run_pipeline_estabiliza_uuid_volatil_preserva_historico_e_expurga_orfaos(
    tmp_path: Path,
) -> None:
    """Valida na Seam 1 a blindagem incremental contra UUID volátil, endpoints vazios e arquivos órfãos."""
    from etl.runner import run_pipeline

    obras_dir = tmp_path / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)

    id_persistido = "persisted-uuid-1"
    ficha_historica = {
        "id": id_persistido,
        "cdUnidadeGestora": 2401,
        "unidadeGestora": "SUCOP",
        "numeroContrato": "001/2024",
        "numeroContratoOriginal": "001/2024",
        "nuProcesso": "9988/2023",
        "objeto": "Drenagem na Pituba",
        "situacao": "Em Execução",
        "empreiteira": {
            "razaoSocial": "CONSTRUTORA BETA LTDA",
            "cnpj": "22.333.444/0001-55",
            "totalObras": 1,
            "totalObrasAtivas": 1,
            "valorTotalContratado": 1500000.0,
            "outrasObrasCount": 0,
            "outrasObrasIds": [],
        },
        "vigencia": {
            "dataInicio": "2024-02-01T00:00:00.000Z",
            "dataFimOriginal": "2025-12-31T00:00:00.000Z",
            "dataTerminoAtualizado": "2026-12-31T00:00:00.000Z",
            "prazoOriginal": "699",
            "prazoAtualizado": "1064",
        },
        "dom": {"nuDom": "8888", "dataPublicacao": "2024-02-05"},
        "funilFinanceiro": {
            "valorOriginal": 1500000.0,
            "valorContratualVigente": 1500000.0,
            "valorEmpenhado": 1200000.0,
            "valorLiquidado": 800000.0,
            "valorPago": 500000.0,
            "percentualExecutado": 60.0,
            "valorAditivos": 0.0,
            "deltaPercentualAditivos": 0.0,
        },
        "aditivos": [
            {
                "nuAditivo": "1º Aditivo",
                "dsTipoAlteracao": "Prazo",
                "dsObjetoAditivo": "Prorrogação",
                "dtAssinatura": "2025-11-01",
                "dtTerminoVigencia": "2026-12-31",
                "dtPublicacao": "2025-11-05",
                "nuDom": "8888",
                "vlAditivo": 0.0,
            }
        ],
        "dotacao": [
            {
                "subacao": "Drenagem Pluvial",
                "fonteRecurso": "FINISA",
                "classificacao": "4.4.90.51 - Obras e Instalações",
            }
        ],
        "empenhos": [{"notaEmpenho": "2024NE1", "valEmpenhado": "1.200.000,00"}],
        "liquidacoes": [{"notaLiquidacao": "2024NL1", "valLiqLiquidacao": "800.000,00"}],
        "pagamentos": [{"ordemBancaria": "2024OB1", "pago": "500.000,00"}],
    }
    (obras_dir / f"{id_persistido}.json").write_text(
        json.dumps(ficha_historica, ensure_ascii=False), encoding="utf-8"
    )
    (obras_dir / "orphan-stale.json").write_text(
        json.dumps({"id": "orphan-stale"}, ensure_ascii=False), encoding="utf-8"
    )

    index_previo = {
        "metadata": {
            "anoReferencia": 2025,
            "mandatosDisponiveis": ["2021-2024", "2025-2028"],
        },
        "kpis_globais": {},
        "obras": [
            {
                "id": id_persistido,
                "cdUnidadeGestora": 2401,
                "unidadeGestora": "SUCOP",
                "nuContratoSigef": "001/2024",
                "numeroContrato": "001/2024",
                "objeto": "Drenagem na Pituba",
                "valorOriginal": 1500000.0,
                "valorContratualVigente": 1500000.0,
                "percentualExecutado": 60.0,
                "situacao": "Em Execução",
                "credor": "CONSTRUTORA BETA LTDA",
                "cnpj": "22.333.444/0001-55",
                "mandatos": ["2021-2024", "2025-2028"],
                "dtInicioVigencia": "2024-02-01T00:00:00.000Z",
                "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
            }
        ],
    }
    (tmp_path / "index_2025.json").write_text(
        json.dumps(index_previo, ensure_ascii=False), encoding="utf-8"
    )

    # Portal retorna o mesmo contrato com UUID volátil novo e percentual alterado (dispara reconsulta)
    grid_simulado = [
        {
            "id": "volatile-uuid-999",
            "cdUnidadeGestora": 2401,
            "sgOrgao": "SUCOP",
            "nuContratoSigef": "001/2024",
            "dsObjeto": "Drenagem na Pituba",
            "vlOriginal": 1500000.0,
            "vlAtualizado": 1500000.0,
            "dtInicioVigencia": "2024-02-01T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
            "percentualExecutado": 65.0,
            "dsSituacao": "Em Execução",
            "nmCredor": "CONSTRUTORA BETA LTDA",
            "nuDocumentoCredor": "",
        },
        {
            "id": "volatile-uuid-222",
            "cdUnidadeGestora": 567002,
            "sgOrgao": "SEMAN",
            "nuContratoSigef": "002/2025",
            "dsObjeto": "Praça na Pituba",
            "vlOriginal": 2000000.0,
            "vlAtualizado": 2000000.0,
            "dtInicioVigencia": "2025-02-01T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
            "percentualExecutado": 50.0,
            "dsSituacao": "Em Execução",
            "nmCredor": "CONSTRUTORA  BETA  LTDA",
            "nuDocumentoCredor": "",
        },
    ]

    totalizador_simulado = {
        "totalObras": 2,
        "valorTotal": 3500000.0,
        "totalEmpenhado": 999999.0,
        "totalLiquidado": 999999.0,
        "totalPago": 999999.0,
    }

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value=SAMPLE_IBGE_CENSO_2022),
        patch("etl.sources.transparencia.fetch_totalizador", return_value=totalizador_simulado),
        patch("etl.sources.transparencia.fetch_grid_detalhada", return_value=grid_simulado),
        patch("etl.sources.transparencia.fetch_detalhes_obra", return_value={}),
        patch("etl.sources.transparencia.fetch_aditivos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_dotacao_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_empenhos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_pagamentos_obra", return_value=[]),
    ):
        result = run_pipeline(output_dir=tmp_path, year=2025, full_refresh=False)

    assert result["success"] is True

    # UUID persistido preservado, arquivo órfão removido e nenhum arquivo volátil duplicado criado
    arquivos = sorted(p.name for p in obras_dir.glob("*.json"))
    assert arquivos == sorted([f"{id_persistido}.json", "volatile-uuid-222.json"])

    # Histórico da ficha preservado mesmo com endpoints secundários retornando vazio
    ficha_1 = json.loads((obras_dir / f"{id_persistido}.json").read_text(encoding="utf-8"))
    assert ficha_1["funilFinanceiro"]["percentualExecutado"] == 65.0
    assert ficha_1["funilFinanceiro"]["valorEmpenhado"] == 1200000.0
    assert ficha_1["funilFinanceiro"]["valorLiquidado"] == 800000.0
    assert ficha_1["funilFinanceiro"]["valorPago"] == 500000.0
    assert len(ficha_1["empenhos"]) == 1
    assert len(ficha_1["liquidacoes"]) == 1
    assert len(ficha_1["pagamentos"]) == 1
    assert len(ficha_1["aditivos"]) == 1
    assert ficha_1["dotacao"][0]["subacao"] == "Drenagem Pluvial"
    assert ficha_1["dom"]["nuDom"] == "8888"
    assert ficha_1["empreiteira"]["cnpj"] == "22.333.444/0001-55"
    assert ficha_1["empreiteira"]["totalObras"] == 2

    # Unificação da empreiteira propagada para o segundo contrato
    ficha_2 = json.loads((obras_dir / "volatile-uuid-222.json").read_text(encoding="utf-8"))
    assert ficha_2["empreiteira"]["cnpj"] == "22.333.444/0001-55"
    assert ficha_2["empreiteira"]["totalObras"] == 2

    idx_final = json.loads((tmp_path / "index_2025.json").read_text(encoding="utf-8"))
    assert len(idx_final["concentracao_empreiteiras"]) == 1
    assert idx_final["concentracao_empreiteiras"][0]["totalObras"] == 2

    obras_map = {o["numeroContrato"]: o for o in idx_final["obras"]}
    assert obras_map["001/2024"]["id"] == id_persistido
    assert obras_map["001/2024"]["valorPago"] == 500000.0
    assert obras_map["002/2025"]["valorPago"] == 1000000.0
    assert obras_map["002/2025"]["cnpj"] == "22.333.444/0001-55"

    kpis = idx_final["kpis_globais"]
    assert kpis["totalEmpenhado"] == 3200000.0
    assert kpis["totalLiquidado"] == 800000.0
    assert kpis["totalPago"] == 500000.0


def test_run_pipeline_full_refresh_preserva_id_canonico_e_sincroniza_aliases(
    tmp_path: Path,
) -> None:
    """Em full_refresh=True, deduplica mandatos, preserva o ID estável prévio e sincroniza index.json."""
    obras_dir = tmp_path / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)
    id_estavel = "id-canonico-estavel"

    idx_previo = {
        "ano": 2025,
        "obras": [
            {
                "id": id_estavel,
                "unidadeGestora": "SUCOP",
                "cdUnidadeGestora": 123001,
                "numeroContrato": "007/2024",
                "mandatos": ["2021-2024", "2025-2028"],
            }
        ],
    }
    (tmp_path / "index_2025.json").write_text(
        json.dumps(idx_previo, ensure_ascii=False), encoding="utf-8"
    )

    ficha_estavel = {
        "id": id_estavel,
        "unidadeGestora": "SUCOP",
        "cdUnidadeGestora": 123001,
        "numeroContrato": "007/2024",
        "objeto": "Contenção de encosta na Pituba",
        "situacao": "Em Execução",
        "empreiteira": {"razaoSocial": "GEOTECNIA SUL LTDA", "cnpj": "33.444.555/0001-66"},
        "vigencia": {"dataInicio": "2024-03-01", "dataTerminoAtualizado": "2026-12-31"},
        "dom": {"nuDom": "Não informado", "dataPublicacao": "2024-03-05"},
        "funilFinanceiro": {
            "valorOriginal": 2000000.0,
            "valorContratualVigente": 2000000.0,
            "valorEmpenhado": 1800000.0,
            "valorLiquidado": 900000.0,
            "valorPago": 600000.0,
            "percentualExecutado": 30.0,
        },
        "aditivos": [],
        "dotacao": [],
        "empenhos": [{"notaEmpenho": "2024NE007", "valEmpenhado": 1800000.0}],
        "liquidacoes": [{"notaLiquidacao": "2024NL007", "valLiqLiquidacao": 900000.0}],
        "pagamentos": [{"ordemBancaria": "2024OB007", "pago": 600000.0}],
    }
    ficha_orfa_meta = copy.deepcopy(ficha_estavel)
    ficha_orfa_meta["id"] = "outro-orfao-historico"
    ficha_orfa_meta["nuProcesso"] = "98765/2024"
    ficha_orfa_meta["dom"] = {"nuDom": "9999", "dataPublicacao": "2024-03-10"}
    ficha_orfa_meta["empenhos"] = []
    ficha_orfa_meta["liquidacoes"] = []
    ficha_orfa_meta["pagamentos"] = []

    (obras_dir / f"{id_estavel}.json").write_text(
        json.dumps(ficha_estavel, ensure_ascii=False), encoding="utf-8"
    )
    (obras_dir / "outro-orfao-historico.json").write_text(
        json.dumps(ficha_orfa_meta, ensure_ascii=False), encoding="utf-8"
    )

    obra_m1 = {
        "id": "volatile-m1",
        "cdUnidadeGestora": 123001,
        "sgOrgao": "SUCOP",
        "nuContratoSigef": "007/2024",
        "dsObjeto": "Contenção de encosta na Pituba",
        "vlOriginal": 2000000.0,
        "vlAtualizado": 2000000.0,
        "dtInicioVigencia": "2024-03-01T00:00:00.000Z",
        "dtTerminoVigenciaAtualizado": "2026-12-31T00:00:00.000Z",
        "percentualExecutado": 30.0,
        "dsSituacao": "Em Execução",
        "nmCredor": "GEOTECNIA SUL LTDA",
        "nuDocumentoCredor": "",
    }
    obra_m2 = dict(obra_m1)
    obra_m2["id"] = "volatile-m2"
    obra_m2["percentualExecutado"] = 40.0

    mock_grid = MagicMock(side_effect=[[obra_m1], [obra_m2]])
    mock_detalhes = MagicMock(return_value={})

    totalizador_full_refresh = {
        "totalObras": 1,
        "valorTotal": 2000000.0,
        "totalEmpenhado": 0.0,
        "totalLiquidado": 0.0,
        "totalPago": 0.0,
    }

    with (
        patch("etl.sources.geosalvador.fetch_bairros_geojson", return_value=SAMPLE_GEOSALVADOR_BAIRROS),
        patch("etl.sources.geosalvador.fetch_prefeituras_geojson", return_value=SAMPLE_GEOSALVADOR_PREFEITURAS),
        patch("etl.sources.ibge_censo.fetch_demografia_censo_2022", return_value=SAMPLE_IBGE_CENSO_2022),
        patch("etl.sources.transparencia.fetch_totalizador", return_value=totalizador_full_refresh),
        patch("etl.sources.transparencia.fetch_grid_detalhada", mock_grid),
        patch("etl.sources.transparencia.fetch_detalhes_obra", mock_detalhes),
        patch("etl.sources.transparencia.fetch_aditivos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_dotacao_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_empenhos_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_liquidacoes_obra", return_value=[]),
        patch("etl.sources.transparencia.fetch_pagamentos_obra", return_value=[]),
    ):
        result = run_pipeline(output_dir=tmp_path, year=2025, full_refresh=True)

    assert result["success"] is True
    assert mock_grid.call_count == 2
    assert mock_detalhes.call_count == 1
    assert result["total_obras"] == 1

    assert [p.name for p in obras_dir.glob("*.json")] == [f"{id_estavel}.json"]
    ficha_final = json.loads((obras_dir / f"{id_estavel}.json").read_text(encoding="utf-8"))
    assert ficha_final["id"] == id_estavel
    assert ficha_final["nuProcesso"] == "98765/2024"
    assert ficha_final["dom"]["nuDom"] == "9999"
    assert ficha_final["empreiteira"]["cnpj"] == "33.444.555/0001-66"
    assert ficha_final["funilFinanceiro"]["valorPago"] == 600000.0
    assert len(ficha_final["empenhos"]) == 1

    assert (tmp_path / "index_2025.json").read_text(encoding="utf-8") == (
        tmp_path / "index.json"
    ).read_text(encoding="utf-8")
    idx_final = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert len(idx_final["obras"]) == 1
    assert idx_final["obras"][0]["id"] == id_estavel
    assert set(idx_final["obras"][0]["mandatos"]) == {"2021-2024", "2025-2028"}
    assert idx_final["obras"][0]["valorPago"] == 600000.0


def test_deduplicar_e_coletar_nao_colidem_ugs_distintas_com_mesma_sigla() -> None:
    """Contratos com mesma sigla de órgão e número mas cdUnidadeGestora distintos não se fundem."""
    from etl.domain.mandato import deduplicar_obras
    from etl.reconcile import coletar_fichas_candidatas

    obra_ug1 = {
        "id": "id-ug1",
        "cdUnidadeGestora": 1001,
        "sgOrgao": "SEINFRA",
        "nuContratoSigef": "001/2025",
        "dtInicioVigencia": "2025-01-10T00:00:00.000Z",
        "vlAtualizado": 500000.0,
    }
    obra_ug2 = {
        "id": "id-ug2",
        "cdUnidadeGestora": 1002,
        "sgOrgao": "SEINFRA",
        "nuContratoSigef": "001/2025",
        "dtInicioVigencia": "2025-02-10T00:00:00.000Z",
        "vlAtualizado": 900000.0,
    }

    dedup = deduplicar_obras([obra_ug1, obra_ug2])
    assert len(dedup) == 2
    assert {o["cdUnidadeGestora"] for o in dedup} == {1001, 1002}

    ficha_ug2 = {"id": "ficha-ug2", "cdUnidadeGestora": 1002, "unidadeGestora": "SEINFRA", "numeroContrato": "001/2025"}
    ficha_legado_sem_cd = {"id": "id-ug1", "unidadeGestora": "SEINFRA", "numeroContrato": "001/2025"}
    fichas_por_chave = {("SEINFRA", "001/2025"): [ficha_ug2, ficha_legado_sem_cd]}
    fichas_por_id = {"id-ug1": ficha_legado_sem_cd, "ficha-ug2": ficha_ug2}

    candidatas_ug1 = coletar_fichas_candidatas(obra_ug1, fichas_por_chave, fichas_por_id)
    assert [f["id"] for f in candidatas_ug1] == ["id-ug1"]


def test_concentracao_empreiteiras_nao_propaga_cnpj_quando_razao_social_eh_ambigua() -> None:
    """Razão social associada a dois CNPJs distintos não propaga CNPJ errado ao terceiro contrato."""
    from etl.domain.empreiteiras import calcular_concentracao_empreiteiras

    obras = [
        {
            "id": "o1",
            "nmCredor": "CONSTRUTORA HOMONIMA LTDA",
            "nuDocumentoCredor": "11111111000111",
            "vlAtualizado": 100000.0,
            "dsSituacao": "Em Execução",
        },
        {
            "id": "o2",
            "nmCredor": "CONSTRUTORA HOMONIMA LTDA",
            "nuDocumentoCredor": "22222222000122",
            "vlAtualizado": 200000.0,
            "dsSituacao": "Em Execução",
        },
        {
            "id": "o3",
            "nmCredor": "CONSTRUTORA HOMONIMA LTDA",
            "nuDocumentoCredor": "Não informado",
            "vlAtualizado": 300000.0,
            "dsSituacao": "Em Execução",
        },
    ]

    conc = calcular_concentracao_empreiteiras(obras)
    assert len(conc) == 3
    assert "cnpj" not in obras[2]
    assert obras[2]["nuDocumentoCredor"] == "Não informado"


def test_reconciliar_acervo_local_ignora_kpis_antigos_inflados_e_trata_json_corrompido(
    tmp_path: Path,
) -> None:
    """KPIs locais antigos inflados não poluem o recálculo e JSONs corrompidos geram aviso."""
    import pytest
    from etl.reconcile import reconciliar_acervo_local

    _criar_geo_minimo(tmp_path)
    obras_dir = tmp_path / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)

    (tmp_path / "index_2025.json").write_text(
        json.dumps(
            {
                "ano": 2025,
                "kpis_globais": {
                    "totalObras": 1,
                    "valorTotal": 999999999.0,
                    "totalEmpenhado": 888888888.0,
                    "totalLiquidado": 777777777.0,
                    "totalPago": 666666666.0,
                },
                "bairros": [
                    {"nome": "Pituba", "prefeitura_bairro": "Barra/Pituba", "populacao": 10000}
                ],
                "prefeituras_bairro": [{"nome": "Barra/Pituba", "populacao": 10000}],
                "obras": [
                    {
                        "id": "obra-limpa",
                        "cdUnidadeGestora": 123,
                        "unidadeGestora": "SUCOP",
                        "numeroContrato": "010/2025",
                        "objeto": "Obra",
                        "situacao": "Em Execução",
                        "valorOriginal": 1000000.0,
                        "valorContratualVigente": 1000000.0,
                        "percentualExecutado": 25.0,
                        "credor": "EMP TESTE LTDA",
                        "cnpj": "44.555.666/0001-77",
                        "nivel": "Bairro",
                        "bairro": "Pituba",
                        "prefeitura_bairro": "Barra/Pituba",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (obras_dir / "obra-limpa.json").write_text(
        json.dumps(
            {
                "id": "obra-limpa",
                "unidadeGestora": "SUCOP",
                "numeroContrato": "010/2025",
                "empreiteira": {"razaoSocial": "EMP TESTE LTDA", "cnpj": "44.555.666/0001-77"},
                "empenhos": [{"notaEmpenho": "NE1", "valEmpenhado": 400000.0}],
                "liquidacoes": [{"notaLiquidacao": "NL1", "valLiqLiquidacao": 200000.0}],
                "pagamentos": [{"ordemBancaria": "OB1", "pago": 100000.0}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (obras_dir / "corrompido.json").write_text("{json invalido", encoding="utf-8")

    with pytest.warns(RuntimeWarning, match="corrompido.json"):
        res = reconciliar_acervo_local(output_dir=tmp_path, year=2025)

    assert res["kpis_globais"]["valorTotal"] == 1000000.0
    assert res["kpis_globais"]["totalEmpenhado"] == 400000.0
    assert res["kpis_globais"]["totalLiquidado"] == 200000.0
    assert res["kpis_globais"]["totalPago"] == 100000.0
    assert not (obras_dir / "corrompido.json").exists()




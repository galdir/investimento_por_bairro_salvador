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


def test_reconciliar_acervo_local_desdobra_frentes_medicao_sem_inflar_valor_total(tmp_path: Path) -> None:
    """Seam 1 (E2E): reconciliar_acervo_local desdobra Frentes de Medição curadas preservando valorTotal e saldo opaco."""
    from etl.reconcile import reconciliar_acervo_local

    obras_dir = tmp_path / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "index_2025.json").write_text(
        json.dumps(
            {
                "metadata": {"anoReferencia": 2025},
                "bairros": [
                    {
                        "id": 1,
                        "nome": "Plataforma",
                        "prefeitura_bairro": "Subúrbio/Ilhas",
                        "populacao": 20000,
                        "indice_vulnerabilidade": 0.6,
                    }
                ],
                "prefeituras_bairro": [
                    {"id": 1, "nome": "Subúrbio/Ilhas", "populacao_total": 20000}
                ],
                "obras": [
                    {
                        "id": "gc-semob",
                        "cdUnidadeGestora": "530002",
                        "unidadeGestora": "SEMOB",
                        "numeroContrato": "2024CT006332",
                        "objeto": "Manutenção predial de equipamentos de mobilidade",
                        "valorContratualVigente": 2000000.0,
                        "valorPago": 172343.21,
                        "nivel": "Escopo Cidade (Não-Localizado)",
                        "bairro": None,
                        "prefeitura_bairro": None,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (obras_dir / "gc-semob.json").write_text(
        json.dumps(
            {
                "id": "gc-semob",
                "cdUnidadeGestora": "530002",
                "unidadeGestora": "SEMOB",
                "numeroContrato": "2024CT006332",
                "empreiteira": {"razaoSocial": "EMP MOB LTDA", "cnpj": "11.222.333/0001-44"},
                "liquidacoes": [
                    {
                        "notaLiquidacao": "2025NL004865",
                        "valLiqLiquidacao": "42.243,32",
                        "pago": "0,00",
                        "descObsLiquidacao": "Manutenção Terminal Maritimo Plataforma",
                    },
                    {
                        "notaLiquidacao": "2025NL002039",
                        "valLiqLiquidacao": "139.209,74",
                        "pago": "0,00",
                        "descObsLiquidacao": "Manutenção predial dos Ascensores",
                    },
                ],
                "pagamentos": [
                    {"notaLiquidacao": "2025NL004865", "pago": "40.000,00"},
                    {"notaLiquidacao": "2025NL002039", "pago": "132.343,21"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    res = reconciliar_acervo_local(output_dir=tmp_path, year=2025)
    idx_atualizado = json.loads((tmp_path / "index_2025.json").read_text(encoding="utf-8"))
    plataforma = idx_atualizado["bairros"][0]

    assert plataforma["valorTotal"] == 0.0
    assert plataforma["totalObras"] == 0
    assert plataforma["valorLiquidadoFrentes"] == 42243.32
    assert plataforma["valorPagoFrentes"] == 40000.0
    assert plataforma["totalFrentesMedicao"] == 1
    assert plataforma["investimentoPorHabitantePago"] == 2.0
    assert res["kpis_globais"]["valorNaoLocalizado"] == 2000000.0
    assert res["kpis_globais"]["valorPagoNaoLocalizado"] == 132343.21


def test_reconciliar_acervo_local_promove_curadoria_territorio_unico_e_propaga_lastro(
    tmp_path: Path,
) -> None:
    """Seam 1 (E2E): reconciliar_acervo_local aplica curadoria de território único (promovido e ambiguo)."""
    from etl.reconcile import reconciliar_acervo_local

    geo_dir = tmp_path / "geo"
    geo_dir.mkdir(parents=True, exist_ok=True)
    bairros_geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "CD_BAIRRO": 10,
                    "NM_BAIRRO": "Fazenda Coutos",
                    "PREFEITURA_BAIRRO": "Subúrbio/Ilhas",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-38.470, -12.840],
                            [-38.460, -12.840],
                            [-38.460, -12.830],
                            [-38.470, -12.830],
                            [-38.470, -12.840],
                        ]
                    ],
                },
            }
        ],
    }
    pb_geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"OBJECTID": 1, "PREFEITURA_BAIRRO": "Subúrbio/Ilhas"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-38.480, -12.850],
                            [-38.450, -12.850],
                            [-38.450, -12.820],
                            [-38.480, -12.820],
                            [-38.480, -12.850],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {"OBJECTID": 2, "PREFEITURA_BAIRRO": "Centro/Brotas"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-38.520, -12.990],
                            [-38.500, -12.990],
                            [-38.500, -12.970],
                            [-38.520, -12.970],
                            [-38.520, -12.990],
                        ]
                    ],
                },
            },
        ],
    }
    (geo_dir / "bairros.geojson").write_text(
        json.dumps(bairros_geo, ensure_ascii=False), encoding="utf-8"
    )
    (geo_dir / "prefeituras_bairro.geojson").write_text(
        json.dumps(pb_geo, ensure_ascii=False), encoding="utf-8"
    )

    obras_dir = tmp_path / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)

    id_promovido_bairro = "obra-curada-bairro"
    id_ambiguo = "obra-curada-ambigua"
    id_promovido_regional = "obra-curada-regional"

    (tmp_path / "index_2025.json").write_text(
        json.dumps(
            {
                "metadata": {"anoReferencia": 2025},
                "bairros": [
                    {
                        "id": 10,
                        "nome": "Fazenda Coutos",
                        "prefeitura_bairro": "Subúrbio/Ilhas",
                        "populacao": 30000,
                        "indice_vulnerabilidade": 0.55,
                    }
                ],
                "prefeituras_bairro": [
                    {"id": 1, "nome": "Subúrbio/Ilhas", "populacao_total": 30000},
                    {"id": 2, "nome": "Centro/Brotas", "populacao_total": 50000},
                ],
                "obras": [
                    {
                        "id": id_promovido_bairro,
                        "cdUnidadeGestora": "301110",
                        "unidadeGestora": "SMS",
                        "numeroContrato": "2025CT005813",
                        "objeto": "Reforma de unidade de saúde",
                        "valorContratualVigente": 500000.0,
                        "valorPago": 250000.0,
                        "nivel": "Escopo Cidade (Não-Localizado)",
                        "bairro": None,
                        "prefeitura_bairro": None,
                        "estagioAlocacao": "Não Localizado",
                    },
                    {
                        "id": id_ambiguo,
                        "cdUnidadeGestora": "616002",
                        "unidadeGestora": "SUCOP",
                        "numeroContrato": "2024CT006616",
                        "objeto": "Requalificação da Avenida Mário Leal Ferreira",
                        "valorContratualVigente": 1200000.0,
                        "valorPago": 300000.0,
                        "nivel": "Escopo Cidade (Não-Localizado)",
                        "bairro": None,
                        "prefeitura_bairro": None,
                        "estagioAlocacao": "Não Localizado",
                    },
                    {
                        "id": id_promovido_regional,
                        "cdUnidadeGestora": "567002",
                        "unidadeGestora": "SEMAN",
                        "numeroContrato": "2025CT999001",
                        "objeto": "Manutenção regional de vias",
                        "valorContratualVigente": 800000.0,
                        "valorPago": 400000.0,
                        "nivel": "Escopo Cidade (Não-Localizado)",
                        "bairro": None,
                        "prefeitura_bairro": None,
                        "estagioAlocacao": "Não Localizado",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    for oid, ug_cd, ug_sg, num, liq_val, pag_val in [
        (id_promovido_bairro, "301110", "SMS", "2025CT005813", "250.000,00", "250.000,00"),
        (id_ambiguo, "616002", "SUCOP", "2024CT006616", "300.000,00", "300.000,00"),
        (id_promovido_regional, "567002", "SEMAN", "2025CT999001", "400.000,00", "400.000,00"),
    ]:
        (obras_dir / f"{oid}.json").write_text(
            json.dumps(
                {
                    "id": oid,
                    "cdUnidadeGestora": ug_cd,
                    "unidadeGestora": ug_sg,
                    "numeroContrato": num,
                    "empreiteira": {"razaoSocial": "EMP TESTE LTDA", "cnpj": "11.222.333/0001-44"},
                    "liquidacoes": [{"notaLiquidacao": "NL1", "valLiqLiquidacao": liq_val}],
                    "pagamentos": [{"notaLiquidacao": "NL1", "pago": pag_val}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    curadoria_custom = {
        "301110:2025CT005813": {
            "status": "promovido",
            "nivel": "Bairro",
            "bairro": "Fazenda Coutos",
            "prefeituraBairro": "Subúrbio/Ilhas",
            "trechoComprobatorio": "REFORMA DA USF FAZENDA COUTOS.II.",
            "documentoOrigem": "dsObjetoAditivo (2º Termo Aditivo ao Contrato nº 387/2025)",
            "justificativa": "O aditivo contratual identifica univocamente o bairro Fazenda Coutos.",
        },
        "616002:2024CT006616": {
            "status": "ambiguo",
            "nivel": "Escopo Cidade (Não-Localizado)",
            "bairro": None,
            "prefeituraBairro": None,
            "trechoComprobatorio": "Requalificação Urbana do Canteiro Central da Avenida Mário Leal Ferreira",
            "documentoOrigem": "dsObjeto / dsObjetoAditivo (Contrato 012/2024)",
            "justificativa": "A Avenida Mário Leal Ferreira atravessa múltiplos bairros.",
        },
        "567002:2025CT999001": {
            "status": "promovido",
            "nivel": "Regional (Prefeitura-Bairro)",
            "bairro": None,
            "prefeituraBairro": "Centro/Brotas",
            "trechoComprobatorio": "LOTE 01 - PREFEITURA-BAIRRO CENTRO/BROTAS",
            "documentoOrigem": "dsObjetoAditivo (Contrato Regional)",
            "justificativa": "Contrato de lote regional vinculado à Prefeitura-Bairro Centro/Brotas.",
        },
    }

    res = reconciliar_acervo_local(output_dir=tmp_path, year=2025, curadoria=curadoria_custom)
    idx_atualizado = json.loads((tmp_path / "index_2025.json").read_text(encoding="utf-8"))
    obras_por_id = {o["id"]: o for o in idx_atualizado["obras"]}

    # 1. Contrato promovido para Bairro Oficial
    obra_bairro = obras_por_id[id_promovido_bairro]
    assert obra_bairro["nivel"] == "Bairro"
    assert obra_bairro["bairro"] == "Fazenda Coutos"
    assert obra_bairro["prefeituraBairro"] == "Subúrbio/Ilhas"
    assert obra_bairro["latitude"] is not None
    assert obra_bairro["longitude"] is not None
    assert obra_bairro["estagioAlocacao"] == "Curadoria Territorial Auditável"
    assert obra_bairro["lastroCuradoria"]["trechoComprobatorio"] == "REFORMA DA USF FAZENDA COUTOS.II."

    ficha_bairro = json.loads((obras_dir / f"{id_promovido_bairro}.json").read_text(encoding="utf-8"))
    assert ficha_bairro["nivel"] == "Bairro"
    assert ficha_bairro["bairro"] == "Fazenda Coutos"
    assert ficha_bairro["prefeituraBairro"] == "Subúrbio/Ilhas"
    assert ficha_bairro["estagioAlocacao"] == "Curadoria Territorial Auditável"
    assert ficha_bairro["fontesOficiais"]["lastroTerritorial"]["trechoComprobatorio"] == "REFORMA DA USF FAZENDA COUTOS.II."
    assert ficha_bairro["fontesOficiais"]["lastroTerritorial"]["documentoOrigem"] == "dsObjetoAditivo (2º Termo Aditivo ao Contrato nº 387/2025)"

    # 2. Contrato promovido para Regional (Prefeitura-Bairro)
    obra_reg = obras_por_id[id_promovido_regional]
    assert obra_reg["nivel"] == "Regional (Prefeitura-Bairro)"
    assert obra_reg["bairro"] is None
    assert obra_reg["prefeituraBairro"] == "Centro/Brotas"
    assert obra_reg["estagioAlocacao"] == "Curadoria Territorial Auditável"
    assert obra_reg["lastroCuradoria"]["trechoComprobatorio"] == "LOTE 01 - PREFEITURA-BAIRRO CENTRO/BROTAS"

    # 3. Contrato ambíguo mantém Escopo Cidade mas propaga estágio e lastro
    obra_amb = obras_por_id[id_ambiguo]
    assert obra_amb["nivel"] == "Escopo Cidade (Não-Localizado)"
    assert obra_amb["bairro"] is None
    assert obra_amb["estagioAlocacao"] == "Curadoria Territorial Auditável (Ambíguo)"
    assert obra_amb["lastroCuradoria"]["trechoComprobatorio"] == "Requalificação Urbana do Canteiro Central da Avenida Mário Leal Ferreira"

    ficha_amb = json.loads((obras_dir / f"{id_ambiguo}.json").read_text(encoding="utf-8"))
    assert ficha_amb["nivel"] == "Escopo Cidade (Não-Localizado)"
    assert ficha_amb["estagioAlocacao"] == "Curadoria Territorial Auditável (Ambíguo)"
    assert ficha_amb["fontesOficiais"]["lastroTerritorial"]["justificativa"] == "A Avenida Mário Leal Ferreira atravessa múltiplos bairros."

    # 4. Agregados territoriais e não-localizados
    fazenda_coutos = idx_atualizado["bairros"][0]
    assert fazenda_coutos["totalObras"] == 1
    assert fazenda_coutos["valorTotal"] == 500000.0
    assert fazenda_coutos["valorPago"] == 250000.0

    pbs_por_nome = {pb["nome"]: pb for pb in idx_atualizado["prefeituras_bairro"]}
    assert pbs_por_nome["Subúrbio/Ilhas"]["totalObras"] == 1
    assert pbs_por_nome["Subúrbio/Ilhas"]["valorTotal"] == 500000.0
    assert pbs_por_nome["Subúrbio/Ilhas"]["valorPago"] == 250000.0
    assert pbs_por_nome["Centro/Brotas"]["totalObras"] == 1
    assert pbs_por_nome["Centro/Brotas"]["valorTotal"] == 800000.0
    assert pbs_por_nome["Centro/Brotas"]["valorPago"] == 400000.0

    assert res["kpis_globais"]["totalNaoLocalizado"] == 1
    assert res["kpis_globais"]["valorNaoLocalizado"] == 1200000.0
    assert res["kpis_globais"]["valorPagoNaoLocalizado"] == 300000.0


def test_reconciliar_acervo_local_propaga_vocacao_e_centralidade_metropolitana(
    tmp_path: Path,
) -> None:
    """Garante que a reconciliação local preenche vocacao em 100% das obras/fichas e aplica isenção per capita no Comércio."""
    geo_dir = tmp_path / "geo"
    geo_dir.mkdir(parents=True, exist_ok=True)

    bairros_geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "id": 1,
                    "nome": "Comércio",
                    "prefeitura_bairro": "Centro/Brotas",
                    "populacao": 971,
                    "indice_vulnerabilidade": 0.48,
                    "is_zona_especial_nao_residencial": False,
                    "is_centralidade_metropolitana": True,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-38.520, -12.980],
                            [-38.510, -12.980],
                            [-38.510, -12.970],
                            [-38.520, -12.970],
                            [-38.520, -12.980],
                        ]
                    ],
                },
            }
        ],
    }
    pb_geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"OBJECTID": 2, "PREFEITURA_BAIRRO": "Centro/Brotas"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-38.530, -12.990],
                            [-38.500, -12.990],
                            [-38.500, -12.960],
                            [-38.530, -12.960],
                            [-38.530, -12.990],
                        ]
                    ],
                },
            }
        ],
    }
    (geo_dir / "bairros.geojson").write_text(
        json.dumps(bairros_geo, ensure_ascii=False), encoding="utf-8"
    )
    (geo_dir / "prefeituras_bairro.geojson").write_text(
        json.dumps(pb_geo, ensure_ascii=False), encoding="utf-8"
    )

    obras_dir = tmp_path / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)

    obra_mercado = {
        "id": "obra-comercio-mercado",
        "cdUnidadeGestora": "616002",
        "unidadeGestora": "SEINFRA",
        "numeroContrato": "010/2025",
        "objeto": "Requalificação do Mercado Modelo no Comércio",
        "valorOriginal": 10000000.0,
        "valorContratualVigente": 10000000.0,
        "valorEmpenhado": 10000000.0,
        "valorLiquidado": 5000000.0,
        "valorPago": 5000000.0,
        "percentualExecutado": 50.0,
        "situacao": "Em Execução",
        "credor": "CONSTRUTORA TESTE LTDA",
        "cnpj": "11.111.111/0001-11",
        "nivel": "Bairro",
        "bairro": "Comércio",
        "prefeitura_bairro": "Centro/Brotas",
        "prefeituraBairro": "Centro/Brotas",
        "mandatos": ["2025-2028"],
    }
    obra_viaduto = {
        "id": "obra-viaduto-brt",
        "cdUnidadeGestora": "2401",
        "unidadeGestora": "SUCOP",
        "numeroContrato": "011/2025",
        "objeto": "Construção de viaduto de integração do corredor BRT",
        "valorOriginal": 20000000.0,
        "valorContratualVigente": 20000000.0,
        "valorEmpenhado": 20000000.0,
        "valorLiquidado": 4000000.0,
        "valorPago": 4000000.0,
        "percentualExecutado": 20.0,
        "situacao": "Em Execução",
        "credor": "CONSTRUTORA TESTE LTDA",
        "cnpj": "11.111.111/0001-11",
        "nivel": "Escopo Cidade (Não-Localizado)",
        "bairro": None,
        "prefeitura_bairro": None,
        "prefeituraBairro": None,
        "mandatos": ["2025-2028"],
    }

    for obra in (obra_mercado, obra_viaduto):
        (obras_dir / f"{obra['id']}.json").write_text(
            json.dumps(obra, ensure_ascii=False), encoding="utf-8"
        )

    indice_inicial = {
        "ano": 2025,
        "kpis": {},
        "bairros": [bairros_geo["features"][0]["properties"]],
        "prefeituras_bairro": [
            {
                "id": 2,
                "nome": "Centro/Brotas",
                "populacao_total": 971,
                "indice_vulnerabilidade": 0.48,
            }
        ],
        "obras": [obra_mercado, obra_viaduto],
    }
    (tmp_path / "index_2025.json").write_text(
        json.dumps(indice_inicial, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "index.json").write_text(
        json.dumps(indice_inicial, ensure_ascii=False), encoding="utf-8"
    )

    from etl.reconcile import reconciliar_acervo_local

    reconciliar_acervo_local(output_dir=tmp_path, year=2025)

    idx_final = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    obras_final = {o["id"]: o for o in idx_final["obras"]}
    assert obras_final["obra-comercio-mercado"]["vocacao"] == "Equipamentos e Marcos da Cidade"
    assert obras_final["obra-viaduto-brt"]["vocacao"] == "Mobilidade Estrutural e Orlas"

    for oid, esperado in (
        ("obra-comercio-mercado", "Equipamentos e Marcos da Cidade"),
        ("obra-viaduto-brt", "Mobilidade Estrutural e Orlas"),
    ):
        ficha = json.loads((obras_dir / f"{oid}.json").read_text(encoding="utf-8"))
        assert ficha["vocacao"] == esperado

    comercio = idx_final["bairros"][0]
    assert comercio["nome"] == "Comércio"
    assert comercio["is_centralidade_metropolitana"] is True
    assert comercio["is_zona_especial_nao_residencial"] is False
    assert comercio["indice_vulnerabilidade"] == 0.48
    assert comercio["investimentoPorHabitante"] == 0.0
    assert comercio["investimentoPorHabitantePago"] == 0.0
    assert comercio["valorTotal"] == 10000000.0

    bairros_geo_final = json.loads((geo_dir / "bairros.geojson").read_text(encoding="utf-8"))
    comercio_geo = bairros_geo_final["features"][0]["properties"]
    assert comercio_geo["is_centralidade_metropolitana"] is True
    assert comercio_geo["investimentoPorHabitante"] == 0.0


def test_reconciliar_acervo_local_reexecuta_funil_integral_e_atualiza_cache_indice_geo_e_fichas(
    tmp_path: Path,
) -> None:
    """reconciliar_acervo_local deve reexecutar todo o funil determinístico offline e sobrescrever legados."""
    from etl.domain.geocoding import GeocodingCache
    from etl.reconcile import reconciliar_acervo_local

    def _poly(lon: float, lat: float) -> dict:
        d = 0.005
        return {
            "type": "Polygon",
            "coordinates": [[[lon - d, lat - d], [lon + d, lat - d], [lon + d, lat + d], [lon - d, lat + d], [lon - d, lat - d]]],
        }

    bairros_specs = [
        ("Pituba", "Barra/Pituba", -38.46, -13.00, 60000),
        ("Itaigara", "Barra/Pituba", -38.465, -12.995, 25000),
        ("Beiru/Tancredo Neves", "Cabula/Tancredo Neves", -38.445, -12.94, 45000),
        ("Boca do Rio", "Itapuã/Ipitanga", -38.42, -12.98, 50000),
        ("Imbuí", "Itapuã/Ipitanga", -38.43, -12.97, 30000),
        ("Brotas", "Centro/Brotas", -38.49, -12.99, 70000),
        ("Paripe", "Subúrbio/Ilhas", -38.47, -12.83, 60000),
        ("São Cristóvão", "Itapuã/Ipitanga", -38.34, -12.91, 40000),
    ]
    pbs_specs = [
        ("Barra/Pituba", 200000),
        ("Cabula/Tancredo Neves", 300000),
        ("Itapuã/Ipitanga", 250000),
        ("Centro/Brotas", 350000),
        ("Subúrbio/Ilhas", 280000),
    ]

    geo_dir = tmp_path / "geo"
    geo_dir.mkdir(parents=True, exist_ok=True)
    bairros_fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "OBJECTID": idx,
                    "NM_BAIRRO": nome,
                    "nome": nome,
                    "PREFEITURA_BAIRRO": pb,
                    "prefeitura_bairro": pb,
                    "populacao": pop,
                    "indice_vulnerabilidade": 0.4,
                },
                "geometry": _poly(lon, lat),
            }
            for idx, (nome, pb, lon, lat, pop) in enumerate(bairros_specs, start=1)
        ],
    }
    pbs_fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"OBJECTID": idx, "nome": pb, "NM_PREFEITURA_BAIRRO": pb},
                "geometry": _poly(-38.45, -12.95),
            }
            for idx, (pb, _) in enumerate(pbs_specs, start=1)
        ],
    }
    (geo_dir / "bairros.geojson").write_text(json.dumps(bairros_fc, ensure_ascii=False), encoding="utf-8")
    (geo_dir / "prefeituras_bairro.geojson").write_text(json.dumps(pbs_fc, ensure_ascii=False), encoding="utf-8")

    # Casos legados com classificações erradas que estavam congeladas no cache, índice e ficha limpa
    obras_iniciais = [
        {
            "id": "obra-lote-cego",
            "cdUnidadeGestora": "567002",
            "nuContratoSigef": "2024CT010011",
            "objeto": "Manutenção preventiva em escolas do Lote 02",
            "nivel": "Regional (Prefeitura-Bairro)",
            "bairro": None,
            "prefeituraBairro": "Subúrbio/Ilhas",
            "prefeitura_bairro": "Subúrbio/Ilhas",
            "estagioAlocacao": "Stage 1 (Lote Regional)",
            "valorContratualVigente": 100000.0,
            "valorPago": 50000.0,
            "ano": 2025,
            "mandatos": ["Bruno Reis (2025–2028)"],
        },
        {
            "id": "obra-av-tancredo",
            "cdUnidadeGestora": "610002",
            "nuContratoSigef": "2022CT000100",
            "objeto": "Recuperação Estrutural da Ponte situada na Av. Tancredo Neves",
            "nivel": "Bairro",
            "bairro": "Beiru/Tancredo Neves",
            "prefeituraBairro": "Cabula/Tancredo Neves",
            "prefeitura_bairro": "Cabula/Tancredo Neves",
            "latitude": -12.94,
            "longitude": -38.445,
            "estagioAlocacao": "Stage 1 (Bairro / Sublocalidade)",
            "valorContratualVigente": 200000.0,
            "valorPago": 100000.0,
            "ano": 2025,
            "mandatos": ["Bruno Reis (2025–2028)"],
        },
        {
            "id": "obra-pb-barra-pituba",
            "cdUnidadeGestora": "616002",
            "nuContratoSigef": "2019CT000200",
            "objeto": "PROG MORAR MELHOR MELHORIAS HABITACIONAIS PREFEITURA BAIRRO VI BARRA/ PITUBA",
            "nivel": "Bairro",
            "bairro": "Pituba",
            "prefeituraBairro": "Barra/Pituba",
            "prefeitura_bairro": "Barra/Pituba",
            "latitude": -13.0,
            "longitude": -38.46,
            "estagioAlocacao": "Stage 1 (Bairro / Sublocalidade)",
            "valorContratualVigente": 300000.0,
            "valorPago": 150000.0,
            "ano": 2025,
            "mandatos": ["Bruno Reis (2025–2028)"],
        },
        {
            "id": "obra-curralinho-imbui",
            "cdUnidadeGestora": "610002",
            "nuContratoSigef": "2024CT000300",
            "objeto": "Construção dos Lava-Jatos 01 e 02, Curralinho, Imbui, Salvador/BA",
            "nivel": "Bairro",
            "bairro": "Boca do Rio",
            "prefeituraBairro": "Itapuã/Ipitanga",
            "prefeitura_bairro": "Itapuã/Ipitanga",
            "latitude": -12.98,
            "longitude": -38.42,
            "estagioAlocacao": "Stage 1 (Bairro / Sublocalidade)",
            "valorContratualVigente": 400000.0,
            "valorPago": 200000.0,
            "ano": 2025,
            "mandatos": ["Bruno Reis (2025–2028)"],
        },
        {
            "id": "obra-multi-bairro-distintas",
            "cdUnidadeGestora": "616002",
            "nuContratoSigef": "2025CT002882",
            "objeto": "Centro de Referência Especializado (CREAS): em Brotas, Paripe e São Cristóvão",
            "nivel": "Bairro",
            "bairro": "Brotas",
            "prefeituraBairro": "Centro/Brotas",
            "prefeitura_bairro": "Centro/Brotas",
            "latitude": -12.99,
            "longitude": -38.49,
            "estagioAlocacao": "Stage 1 (Bairro / Sublocalidade)",
            "valorContratualVigente": 500000.0,
            "valorPago": 250000.0,
            "ano": 2025,
            "mandatos": ["Bruno Reis (2025–2028)"],
        },
        {
            "id": "obra-multi-bairro-mesma-pb",
            "cdUnidadeGestora": "610002",
            "nuContratoSigef": "2025CT009999",
            "objeto": "Requalificação de vias na Pituba e Itaigara, Salvador/BA",
            "nivel": "Bairro",
            "bairro": "Pituba",
            "prefeituraBairro": "Barra/Pituba",
            "prefeitura_bairro": "Barra/Pituba",
            "latitude": -13.0,
            "longitude": -38.46,
            "estagioAlocacao": "Stage 1 (Bairro / Sublocalidade)",
            "valorContratualVigente": 600000.0,
            "valorPago": 300000.0,
            "ano": 2025,
            "mandatos": ["Bruno Reis (2025–2028)"],
        },
        {
            "id": "obra-curada",
            "cdUnidadeGestora": "530002",
            "nuContratoSigef": "2024CT888001",
            "objeto": "Execução de serviços de conservação predial",
            "nivel": "Escopo Cidade (Não-Localizado)",
            "bairro": None,
            "prefeituraBairro": None,
            "prefeitura_bairro": None,
            "estagioAlocacao": "Não-Localizado (Transparência Opaca)",
            "valorContratualVigente": 700000.0,
            "valorPago": 350000.0,
            "ano": 2025,
            "mandatos": ["Bruno Reis (2025–2028)"],
        },
    ]

    cache_path = tmp_path / "geocoding_cache.json"
    cache = GeocodingCache(cache_path)
    obras_dir = tmp_path / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)
    for o in obras_iniciais:
        cache.set(
            o["cdUnidadeGestora"],
            o["nuContratoSigef"],
            o["objeto"],
            {
                "nivel": o["nivel"],
                "bairro": o["bairro"],
                "prefeitura_bairro": o.get("prefeituraBairro"),
                "latitude": o.get("latitude"),
                "longitude": o.get("longitude"),
                "estagio": "Cache",
            },
        )
        ficha = {
            "id": o["id"],
            "cdUnidadeGestora": o["cdUnidadeGestora"],
            "numeroContrato": o["nuContratoSigef"],
            "objeto": o["objeto"],
            "nivel": o["nivel"],
            "bairro": o["bairro"],
            "prefeituraBairro": o.get("prefeituraBairro"),
            "latitude": o.get("latitude"),
            "longitude": o.get("longitude"),
            "estagioAlocacao": o["estagioAlocacao"],
            "funilFinanceiro": {
                "valorContratualVigente": o["valorContratualVigente"],
                "valorPago": o["valorPago"],
            },
        }
        (obras_dir / f"{o['id']}.json").write_text(json.dumps(ficha, ensure_ascii=False), encoding="utf-8")

    indice_inicial = {
        "ano": 2025,
        "obras": obras_iniciais,
        "bairros": [
            {"id": idx, "nome": nome, "prefeitura_bairro": pb, "populacao": pop, "indice_vulnerabilidade": 0.4}
            for idx, (nome, pb, _, _, pop) in enumerate(bairros_specs, start=1)
        ],
        "prefeituras_bairro": [
            {"id": idx, "nome": pb, "populacao_total": pop}
            for idx, (pb, pop) in enumerate(pbs_specs, start=1)
        ],
    }
    (tmp_path / "index_2025.json").write_text(json.dumps(indice_inicial, ensure_ascii=False), encoding="utf-8")

    curadoria_teste = {
        "530002:2024CT888001": {
            "cdUnidadeGestora": "530002",
            "nuContratoSigef": "2024CT888001",
            "status": "promovido",
            "nivel": "Bairro",
            "bairro": "Pituba",
            "prefeituraBairro": "Barra/Pituba",
            "trechoComprobatorio": "Ordem de Serviço nº 12 - Unidade Pituba",
            "documentoOrigem": "Diário Oficial do Município",
            "justificativa": "Localização auditada documentalmente.",
        }
    }

    with patch("urllib.request.urlopen", side_effect=AssertionError("Não deve chamar rede na reconciliação!")):
        reconciliar_acervo_local(output_dir=tmp_path, year=2025, curadoria=curadoria_teste)

    idx_final = json.loads((tmp_path / "index_2025.json").read_text(encoding="utf-8"))
    idx_alias = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert len(idx_final["obras"]) == len(idx_alias["obras"]) == 7

    obras_final = {o["id"]: o for o in idx_final["obras"]}
    esperado = {
        "obra-lote-cego": ("Escopo Cidade (Não-Localizado)", None, None),
        "obra-av-tancredo": ("Escopo Cidade (Não-Localizado)", None, None),
        "obra-pb-barra-pituba": ("Regional (Prefeitura-Bairro)", None, "Barra/Pituba"),
        "obra-curralinho-imbui": ("Bairro", "Imbuí", "Itapuã/Ipitanga"),
        "obra-multi-bairro-distintas": ("Escopo Cidade (Não-Localizado)", None, None),
        "obra-multi-bairro-mesma-pb": ("Regional (Prefeitura-Bairro)", None, "Barra/Pituba"),
        "obra-curada": ("Bairro", "Pituba", "Barra/Pituba"),
    }

    cache_reloaded = GeocodingCache(cache_path)
    for oid, (nivel_esp, bairro_esp, pb_esp) in esperado.items():
        obra = obras_final[oid]
        assert obra["nivel"] == nivel_esp, oid
        assert obra["bairro"] == bairro_esp, oid
        assert obra["prefeituraBairro"] == pb_esp, oid
        if nivel_esp != "Bairro":
            assert obra["latitude"] is None, oid
            assert obra["longitude"] is None, oid

        ficha = json.loads((obras_dir / f"{oid}.json").read_text(encoding="utf-8"))
        assert ficha["nivel"] == nivel_esp, oid
        assert ficha["bairro"] == bairro_esp, oid
        assert ficha["prefeituraBairro"] == pb_esp, oid
        if nivel_esp != "Bairro":
            assert ficha["latitude"] is None, oid
            assert ficha["longitude"] is None, oid

        entrada_cache = cache_reloaded.get(obra["cdUnidadeGestora"], obra["nuContratoSigef"], obra["objeto"])
        assert entrada_cache is not None, oid
        assert entrada_cache["nivel"] == nivel_esp, oid
        assert entrada_cache["bairro"] == bairro_esp, oid
        assert entrada_cache["prefeitura_bairro"] == pb_esp, oid

    assert obras_final["obra-curada"]["lastroCuradoria"]["documentoOrigem"] == "Diário Oficial do Município"
    assert obras_final["obra-lote-cego"].get("lastroCuradoria") is None

    # GeoJSONs atualizados sem inflação legada
    bairros_geo_final = {
        f["properties"]["nome"]: f["properties"]
        for f in json.loads((geo_dir / "bairros.geojson").read_text(encoding="utf-8"))["features"]
    }
    pbs_geo_final = {
        f["properties"]["nome"]: f["properties"]
        for f in json.loads((geo_dir / "prefeituras_bairro.geojson").read_text(encoding="utf-8"))["features"]
    }
    assert bairros_geo_final["Imbuí"]["valorTotal"] == 400000.0
    assert bairros_geo_final["Pituba"]["valorTotal"] == 700000.0
    assert bairros_geo_final["Beiru/Tancredo Neves"]["valorTotal"] == 0.0
    assert bairros_geo_final["Boca do Rio"]["valorTotal"] == 0.0
    assert bairros_geo_final["Brotas"]["valorTotal"] == 0.0
    assert pbs_geo_final["Subúrbio/Ilhas"]["valorTotal"] == 0.0
    assert pbs_geo_final["Barra/Pituba"]["valorTotal"] == 1600000.0  # 700k curada + 300k PB VI + 600k multi-bairro Barra/Pituba


def test_reconciliar_acervo_local_bloqueia_nominatim_preserva_stage2_e_nao_herda_bairro_stale(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Reconciliação força modo offline com ENABLE_NOMINATIM=1, preserva Stage 2 e limpa bairro stale de Pontual."""
    from etl.domain.geocoding import GeocodingCache
    from etl.reconcile import reconciliar_acervo_local

    monkeypatch.setenv("ENABLE_NOMINATIM", "1")
    _criar_geo_minimo(tmp_path)

    obras_iniciais = [
        {
            "id": "obra-stage2-sem-bairro",
            "cdUnidadeGestora": "610002",
            "nuContratoSigef": "2024STG2001",
            "objeto": "Recuperação de trecho na Avenida Sete de Setembro, s/n",
            "nivel": "Pontual",
            "bairro": "Brotas",
            "prefeituraBairro": "Centro/Brotas",
            "prefeitura_bairro": "Centro/Brotas",
            "latitude": -12.981,
            "longitude": -38.515,
            "estagioAlocacao": "Stage 2 (Nominatim OSM)",
            "valorContratualVigente": 250000.0,
            "valorPago": 100000.0,
            "ano": 2025,
            "mandatos": ["Bruno Reis (2025–2028)"],
        },
        {
            "id": "obra-rua-sem-stage1",
            "cdUnidadeGestora": "610002",
            "nuContratoSigef": "2024NORED002",
            "objeto": "Pavimentação na Rua das Palmeiras, s/n",
            "nivel": "Escopo Cidade (Não-Localizado)",
            "bairro": None,
            "prefeituraBairro": None,
            "prefeitura_bairro": None,
            "estagioAlocacao": "Não-Localizado (Transparência Opaca)",
            "valorContratualVigente": 150000.0,
            "valorPago": 0.0,
            "ano": 2025,
            "mandatos": ["Bruno Reis (2025–2028)"],
        },
    ]

    cache_path = tmp_path / "geocoding_cache.json"
    cache = GeocodingCache(cache_path)
    cache.set(
        "610002",
        "2024STG2001",
        "Recuperação de trecho na Avenida Sete de Setembro, s/n",
        {
            "nivel": "Pontual",
            "bairro": None,
            "prefeitura_bairro": "Centro/Brotas",
            "latitude": -12.981,
            "longitude": -38.515,
            "estagio": "Stage 2 (Nominatim OSM)",
        },
    )

    obras_dir = tmp_path / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)
    for o in obras_iniciais:
        ficha = {
            "id": o["id"],
            "cdUnidadeGestora": o["cdUnidadeGestora"],
            "numeroContrato": o["nuContratoSigef"],
            "objeto": o["objeto"],
            "nivel": o["nivel"],
            "bairro": o["bairro"],
            "prefeituraBairro": o["prefeituraBairro"],
            "latitude": o.get("latitude"),
            "longitude": o.get("longitude"),
            "estagioAlocacao": o["estagioAlocacao"],
            "funilFinanceiro": {
                "valorContratualVigente": o["valorContratualVigente"],
                "valorPago": o["valorPago"],
            },
        }
        (obras_dir / f"{o['id']}.json").write_text(json.dumps(ficha, ensure_ascii=False), encoding="utf-8")

    (tmp_path / "index_2025.json").write_text(
        json.dumps({"ano": 2025, "obras": obras_iniciais, "bairros": [], "prefeituras_bairro": []}, ensure_ascii=False),
        encoding="utf-8",
    )

    with patch("urllib.request.urlopen", side_effect=AssertionError("Não deve consultar Nominatim na reconciliação!")):
        reconciliar_acervo_local(output_dir=tmp_path, year=2025, curadoria={})

    idx_final = json.loads((tmp_path / "index_2025.json").read_text(encoding="utf-8"))
    obras_final = {o["id"]: o for o in idx_final["obras"]}

    assert obras_final["obra-stage2-sem-bairro"]["nivel"] == "Pontual"
    assert obras_final["obra-stage2-sem-bairro"]["bairro"] is None
    assert obras_final["obra-stage2-sem-bairro"]["latitude"] == -12.981
    assert obras_final["obra-stage2-sem-bairro"]["longitude"] == -38.515
    assert obras_final["obra-rua-sem-stage1"]["nivel"] == "Escopo Cidade (Não-Localizado)"

    ficha_pontual = json.loads((obras_dir / "obra-stage2-sem-bairro.json").read_text(encoding="utf-8"))
    assert ficha_pontual["nivel"] == "Pontual"
    assert ficha_pontual["bairro"] is None
    assert ficha_pontual["latitude"] == -12.981
    assert ficha_pontual["longitude"] == -38.515


def test_reconciliar_acervo_local_promove_equipamento_unico_a_pontual_e_abstem_multiplos(
    tmp_path: Path,
) -> None:
    """Seam 1: reconciliação offline promove equipamento único para Pontual, expande logradouro e abstém múltiplos."""
    import shutil
    from shapely.geometry import Point, shape
    from etl.domain.geocoding import GeocodingCache
    from etl.reconcile import reconciliar_acervo_local

    raiz_repo = Path(__file__).resolve().parents[2]
    geo_dir = tmp_path / "geo"
    geo_dir.mkdir(parents=True, exist_ok=True)
    bairros_src = raiz_repo / "public" / "data" / "geo" / "bairros.geojson"
    pb_src = raiz_repo / "public" / "data" / "geo" / "prefeituras_bairro.geojson"
    shutil.copy2(bairros_src, geo_dir / "bairros.geojson")
    shutil.copy2(pb_src, geo_dir / "prefeituras_bairro.geojson")

    bairros_fc = json.loads(bairros_src.read_text(encoding="utf-8"))
    poligonos = {
        f["properties"]["nome"]: shape(f["geometry"])
        for f in bairros_fc["features"]
    }

    obras_iniciais = [
        {
            "id": "obra-eq-em-jesus",
            "cdUnidadeGestora": "610002",
            "nuContratoSigef": "2024EQ001",
            "objeto": "Execução da obra da E.M. Jesus de Nazaré",
            "nivel": "Bairro",
            "bairro": "Nazaré",
            "prefeituraBairro": "Centro/Brotas",
            "prefeitura_bairro": "Centro/Brotas",
            "latitude": -12.976,
            "longitude": -38.510,
            "estagioAlocacao": "Stage 1 (Bairro / Sublocalidade)",
            "valorContratualVigente": 500000.0,
            "valorPago": 250000.0,
            "ano": 2025,
            "mandatos": ["Bruno Reis (2025–2028)"],
        },
        {
            "id": "obra-eq-multiplos",
            "cdUnidadeGestora": "610002",
            "nuContratoSigef": "2024EQ002",
            "objeto": "Reforma do Mercado Modelo e do CRAS Boca do Rio",
            "nivel": "Escopo Cidade (Não-Localizado)",
            "bairro": None,
            "prefeituraBairro": None,
            "prefeitura_bairro": None,
            "latitude": None,
            "longitude": None,
            "estagioAlocacao": "Não-Localizado (Transparência Opaca)",
            "valorContratualVigente": 300000.0,
            "valorPago": 0.0,
            "ano": 2025,
            "mandatos": ["Bruno Reis (2025–2028)"],
        },
        {
            "id": "obra-logradouro-brotas",
            "cdUnidadeGestora": "610002",
            "nuContratoSigef": "2024LOG003",
            "objeto": "Requalificação da Rua Odilon Dórea e Avenida Dom João VI",
            "nivel": "Escopo Cidade (Não-Localizado)",
            "bairro": None,
            "prefeituraBairro": None,
            "prefeitura_bairro": None,
            "latitude": None,
            "longitude": None,
            "estagioAlocacao": "Não-Localizado (Transparência Opaca)",
            "valorContratualVigente": 200000.0,
            "valorPago": 100000.0,
            "ano": 2025,
            "mandatos": ["Bruno Reis (2025–2028)"],
        },
    ]

    cache = GeocodingCache(tmp_path / "geocoding_cache.json")
    cache.set(
        "610002",
        "2024EQ001",
        "Execução da obra da E.M. Jesus de Nazaré",
        {
            "nivel": "Bairro",
            "bairro": "Nazaré",
            "prefeitura_bairro": "Centro/Brotas",
            "latitude": -12.976,
            "longitude": -38.510,
            "estagio": "Stage 1 (Bairro / Sublocalidade)",
        },
    )

    obras_dir = tmp_path / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)
    for o in obras_iniciais:
        ficha = {
            "id": o["id"],
            "cdUnidadeGestora": o["cdUnidadeGestora"],
            "numeroContrato": o["nuContratoSigef"],
            "objeto": o["objeto"],
            "nivel": o["nivel"],
            "bairro": o["bairro"],
            "prefeituraBairro": o["prefeituraBairro"],
            "latitude": o["latitude"],
            "longitude": o["longitude"],
            "estagioAlocacao": o["estagioAlocacao"],
            "funilFinanceiro": {
                "valorContratualVigente": o["valorContratualVigente"],
                "valorPago": o["valorPago"],
            },
        }
        (obras_dir / f"{o['id']}.json").write_text(json.dumps(ficha, ensure_ascii=False), encoding="utf-8")

    (tmp_path / "index_2025.json").write_text(
        json.dumps({"ano": 2025, "obras": obras_iniciais, "bairros": [], "prefeituras_bairro": []}, ensure_ascii=False),
        encoding="utf-8",
    )

    with patch("urllib.request.urlopen", side_effect=AssertionError("Não deve consultar Nominatim na reconciliação!")):
        reconciliar_acervo_local(output_dir=tmp_path, year=2025, curadoria={})

    idx_final = json.loads((tmp_path / "index_2025.json").read_text(encoding="utf-8"))
    obras_final = {o["id"]: o for o in idx_final["obras"]}

    eq_unica = obras_final["obra-eq-em-jesus"]
    assert eq_unica["nivel"] == "Pontual"
    assert eq_unica["bairro"] == "Nova Sussuarana"
    assert eq_unica["prefeituraBairro"] == "Cabula/Tancredo Neves"
    assert eq_unica["estagioAlocacao"] == "Stage 1 (Equipamento Oficial)"
    assert poligonos["Nova Sussuarana"].contains(Point(eq_unica["longitude"], eq_unica["latitude"]))

    ficha_unica = json.loads((obras_dir / "obra-eq-em-jesus.json").read_text(encoding="utf-8"))
    assert ficha_unica["nivel"] == "Pontual"
    assert ficha_unica["bairro"] == "Nova Sussuarana"
    assert ficha_unica["latitude"] == eq_unica["latitude"]
    assert ficha_unica["longitude"] == eq_unica["longitude"]

    assert obras_final["obra-eq-multiplos"]["nivel"] == "Escopo Cidade (Não-Localizado)"
    assert obras_final["obra-eq-multiplos"]["bairro"] is None
    assert obras_final["obra-eq-multiplos"]["latitude"] is None

    assert obras_final["obra-logradouro-brotas"]["nivel"] == "Bairro"
    assert obras_final["obra-logradouro-brotas"]["bairro"] == "Brotas"
    assert obras_final["obra-logradouro-brotas"]["prefeituraBairro"] == "Centro/Brotas"



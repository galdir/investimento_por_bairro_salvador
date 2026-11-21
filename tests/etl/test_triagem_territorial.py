"""Testes para a CLI offline de Triagem Territorial Assistida (3 trilhas)."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from etl.triagem import executar_triagem_territorial


def _criar_acervo_minimo(
    base_dir: Path,
    *,
    obras: list[dict],
    fichas: dict[str, dict],
    com_ponteiro: bool = False,
) -> Path:
    """Cria um acervo local mínimo para testes de triagem (com ou sem atual.json)."""
    base_dir.mkdir(parents=True, exist_ok=True)
    if com_ponteiro:
        versao = "0123456789abcdef0123456789abcdef"
        alvo = base_dir / "versoes" / versao
        (base_dir / "atual.json").write_text(
            json.dumps({"versaoDados": versao, "caminho": f"versoes/{versao}"}),
            encoding="utf-8",
        )
    else:
        alvo = base_dir

    (alvo / "obras").mkdir(parents=True, exist_ok=True)
    index_payload = {
        "metadata": {"ano": 2025},
        "obras": obras,
        "bairros": [],
        "prefeituras_bairro": [],
        "kpis_globais": {},
    }
    (alvo / "index.json").write_text(json.dumps(index_payload, ensure_ascii=False), encoding="utf-8")
    for obra_id, ficha in fichas.items():
        (alvo / "obras" / f"{obra_id}.json").write_text(
            json.dumps(ficha, ensure_ascii=False),
            encoding="utf-8",
        )
    return base_dir


def test_cli_resolve_ponteiro_omite_cobertas_e_preserva_curadoria(tmp_path: Path) -> None:
    """CLI resolve atual.json, usa malha de referência, omite notas cobertas e não altera curadoria."""
    data_dir = _criar_acervo_minimo(
        tmp_path / "data",
        com_ponteiro=True,
        obras=[
            {
                "id": 1001,
                "cdUnidadeGestora": "530002",
                "nuContratoSigef": "2024CT006332",
                "dsObjeto": "Manutencao de equipamentos de transporte",
                "nivel": "Escopo Cidade (Não-Localizado)",
            }
        ],
        fichas={
            "1001": {
                "id": 1001,
                "cdUnidadeGestora": "530002",
                "nuContratoSigef": "2024CT006332",
                "dsObjeto": "Manutencao de equipamentos de transporte",
                "nivel": "Escopo Cidade (Não-Localizado)",
                "liquidacoes": [
                    {
                        "notaLiquidacao": "2025NL0001",
                        "valLiqLiquidacao": "10.000,00",
                        "descObsLiquidacao": "SERVICOS NA TRAV. SAO JOAO, PITUBA - NFSE 10",
                    },
                    {
                        "notaLiquidacao": "2025NL0002",
                        "valLiqLiquidacao": "11.000,00",
                        "descObsLiquidacao": "SERVICOS NA TRAV. SAO JOAO, PITUBA - NFSE 11",
                    },
                    {
                        "notaLiquidacao": "2025NL0003",
                        "valLiqLiquidacao": "12.000,00",
                        "descObsLiquidacao": "SERVICOS NA TRAV. SAO JOAO, PITUBA - NFSE 12",
                    },
                    {
                        "notaLiquidacao": "2025NL0004",
                        "valLiqLiquidacao": "13.000,00",
                        "descObsLiquidacao": "112721/2025; Manutencao Terminal Maritimo Plataforma; 05/2025; nf 1490",
                    },
                    {
                        "notaLiquidacao": "2025NL0005",
                        "valLiqLiquidacao": "14.000,00",
                        "descObsLiquidacao": "163836/2025; Manutencao Terminal Maritimo Plataforma; 07/2025; nf 1584",
                    },
                    {
                        "notaLiquidacao": "2025NL0006",
                        "valLiqLiquidacao": "15.000,00",
                        "descObsLiquidacao": "CONTENCAO NA RUA DAS FLORES, BROTAS - NFSE 99",
                    },
                ],
                "pagamentos": [
                    {"notaLiquidacao": "2025NL0006", "pago": "15.000,00"},
                ],
            }
        },
    )

    curadoria_payload = {
        "versao": 1,
        "registros": {
            "530002:2024CT006332": {
                "status": "multi_frente",
                "frentesMedicao": {
                    "2025NL0001": {
                        "status": "promovido",
                        "nivel": "Bairro",
                        "bairro": "Pituba",
                        "trechoComprobatorio": "Manual",
                        "documentoOrigem": "NL 1",
                        "justificativa": "Manual.",
                    },
                    "2025NL0002": {
                        "status": "ambiguo",
                        "nivel": "Escopo Cidade (Não-Localizado)",
                        "trechoComprobatorio": "Ambiguo",
                        "documentoOrigem": "NL 2",
                        "justificativa": "Ambiguo.",
                    },
                    "2025NL0003": {
                        "status": "estornado",
                        "nivel": "Escopo Cidade (Não-Localizado)",
                        "trechoComprobatorio": "Estornado",
                        "documentoOrigem": "NL 3",
                        "justificativa": "Estornado.",
                    },
                },
                "regrasFrentes": [
                    {
                        "id": "regra-plataforma",
                        "status": "promovido",
                        "nivel": "Bairro",
                        "bairro": "Plataforma",
                        "contemTodos": ["TERMINAL MARITIMO PLATAFORMA"],
                        "trechoComprobatorio": "Terminal Maritimo Plataforma",
                        "documentoOrigem": "descObsLiquidacao",
                        "justificativa": "Frente validada.",
                    }
                ],
            }
        },
    }
    curadoria_path = tmp_path / "curadoria_isolada.json"
    curadoria_texto_original = json.dumps(curadoria_payload, ensure_ascii=False, indent=2)
    curadoria_path.write_text(curadoria_texto_original, encoding="utf-8")

    out_dir = tmp_path / "saida"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "etl.triagem",
            "--data-dir",
            str(data_dir),
            "--out",
            str(out_dir),
            "--curadoria",
            str(curadoria_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr

    json_path = out_dir / "triagem_territorial.json"
    md_path = out_dir / "triagem_territorial.md"
    assert json_path.exists()
    assert md_path.exists()

    # Catálogo de curadoria nunca é modificado
    assert curadoria_path.read_text(encoding="utf-8") == curadoria_texto_original

    relatorio = json.loads(json_path.read_text(encoding="utf-8"))
    alta = relatorio["trilha_2_frentes_unitarias"]["alta_confianca"]
    notas_reportadas = [n for g in alta for n in g["notas"]]
    assert notas_reportadas == ["2025NL0006"]
    assert alta[0]["bairroSugerido"] == "Brotas"
    assert alta[0]["valorLiquidado"] == 15000.0
    assert alta[0]["valorPago"] == 15000.0
    assert relatorio["sumario"]["notas_omitidas_cobertas"] == 5

    md_texto = md_path.read_text(encoding="utf-8")
    assert "# Triagem Territorial Assistida" in md_texto
    assert "## Trilha 2 — Frentes de Medição Unitárias (Alta Confiança)" in md_texto
    assert "Brotas" in md_texto


def test_trilha_2_agrupamento_particionamento_e_pares_estorno_substituicao(tmp_path: Path) -> None:
    """Agrupa por assinatura mascarada, isola alta_confianca vs revisao_manual e detecta pares estorno/substituicao."""
    data_dir = _criar_acervo_minimo(
        tmp_path / "data_t2",
        com_ponteiro=False,
        obras=[
            {
                "id": 2001,
                "cdUnidadeGestora": "616002",
                "nuContratoSigef": "2025CT001001",
                "dsObjeto": "Contrato guarda-chuva de drenagem",
                "nivel": "Escopo Cidade (Não-Localizado)",
            }
        ],
        fichas={
            "2001": {
                "id": 2001,
                "cdUnidadeGestora": "616002",
                "nuContratoSigef": "2025CT001001",
                "dsObjeto": "Contrato guarda-chuva de drenagem",
                "nivel": "Escopo Cidade (Não-Localizado)",
                "liquidacoes": [
                    # Duas notas limpas da mesma frente (processo, competencia, NF, medicao, datas diferentes)
                    {
                        "notaLiquidacao": "2025NL0101",
                        "valLiqLiquidacao": "10.000,00",
                        "dataLiquidacao": "2025-03-10",
                        "descObsLiquidacao": "100100/2025; 1ª MEDICAO DRENAGEM RUA DA PAZ, PITUBA; 02/2025; 01/02/2025; NFSE 501",
                    },
                    {
                        "notaLiquidacao": "2025NL0102",
                        "valLiqLiquidacao": "20.000,00",
                        "dataLiquidacao": "2025-04-10",
                        "descObsLiquidacao": "100200/2025; 2ª MEDICAO DRENAGEM RUA DA PAZ, PITUBA; 03/2025; 01/03/2025; NFSE 502",
                    },
                    # Nota truncada da mesma frente -> deve ir para revisao_manual sem contaminar as limpas
                    {
                        "notaLiquidacao": "2025NL0103",
                        "valLiqLiquidacao": "5.000,00",
                        "dataLiquidacao": "2025-05-10",
                        "descObsLiquidacao": "EXECUCAO DE SERVICOS DE DRENAGEM NA RUA DA PAZ, NO BAIRRO DA PITUBA, TRECHO ADICIONAL 02,",
                    },
                    # Par por mesma NFSE (777) em notas distintas -> ambas rebaixadas para revisao_manual
                    {
                        "notaLiquidacao": "2025NL0104",
                        "valLiqLiquidacao": "8.000,00",
                        "dataLiquidacao": "2025-06-01",
                        "descObsLiquidacao": "PAVIMENTACAO RUA A, BROTAS - NFSE 777",
                    },
                    {
                        "notaLiquidacao": "2025NL0105",
                        "valLiqLiquidacao": "8.500,00",
                        "dataLiquidacao": "2025-06-05",
                        "descObsLiquidacao": "PAVIMENTACAO RUA A, BROTAS - NFSE 777",
                    },
                    # Par por valores simetricos (+X / -X) -> rebaixadas para revisao_manual
                    {
                        "notaLiquidacao": "2025NL0106",
                        "valLiqLiquidacao": "12.000,00",
                        "dataLiquidacao": "2025-07-01",
                        "descObsLiquidacao": "REFORMA PRACA CENTRAL, PARIPE - NFSE 801",
                    },
                    {
                        "notaLiquidacao": "2025NL0107",
                        "valLiqLiquidacao": "-12.000,00",
                        "dataLiquidacao": "2025-07-02",
                        "descObsLiquidacao": "REFORMA PRACA CENTRAL, PARIPE - NFSE 802",
                    },
                    # Par por valor identico na mesma competencia (fallback para dataLiquidacao 08/2025)
                    {
                        "notaLiquidacao": "2025NL0108",
                        "valLiqLiquidacao": "9.500,00",
                        "dataLiquidacao": "2025-08-10",
                        "descObsLiquidacao": "DRENAGEM TRAVESSA B, PERIPERI - NFSE 901",
                    },
                    {
                        "notaLiquidacao": "2025NL0109",
                        "valLiqLiquidacao": "9.500,00",
                        "dataLiquidacao": "2025-08-22",
                        "descObsLiquidacao": "DRENAGEM TRAVESSA B, PERIPERI - NFSE 902",
                    },
                    # Nota apenas regional (Prefeitura-Bairro)
                    {
                        "notaLiquidacao": "2025NL0110",
                        "valLiqLiquidacao": "4.000,00",
                        "dataLiquidacao": "2025-09-01",
                        "descObsLiquidacao": "MANUTENCAO VIARIA PREFEITURA-BAIRRO SUBURBIO/ILHAS - NFSE 950",
                    },
                    # Nota sem match territorial
                    {
                        "notaLiquidacao": "2025NL0111",
                        "valLiqLiquidacao": "3.000,00",
                        "dataLiquidacao": "2025-09-02",
                        "descObsLiquidacao": "SERVICOS ADMINISTRATIVOS GERAIS - NFSE 951",
                    },
                ],
                "pagamentos": [
                    {"notaLiquidacao": "2025NL0101", "pago": "10.000,00"},
                    {"notaLiquidacao": "2025NL0102", "pago": "15.000,00"},
                ],
            }
        },
    )

    out_dir = tmp_path / "out_t2"
    curadoria_vazia = tmp_path / "curadoria_vazia.json"
    curadoria_vazia.write_text('{"versao": 1, "registros": {}}', encoding="utf-8")

    relatorio = executar_triagem_territorial(data_dir, out_dir, curadoria_path=curadoria_vazia)
    t2 = relatorio["trilha_2_frentes_unitarias"]

    # Apenas as duas notas limpas de Pituba ficam em alta_confianca, agrupadas em 1 grupo
    assert len(t2["alta_confianca"]) == 1
    grupo_pituba = t2["alta_confianca"][0]
    assert grupo_pituba["bairroSugerido"] == "Pituba"
    assert grupo_pituba["quantidadeNotas"] == 2
    assert grupo_pituba["valorLiquidado"] == 30000.0
    assert grupo_pituba["valorPago"] == 25000.0
    assert grupo_pituba["notas"] == ["2025NL0101", "2025NL0102"]
    assert grupo_pituba["motivosBloqueio"] == []

    # Notas truncadas e pares suspeitos vao para revisao_manual com motivos explicitos
    notas_revisao = {n for g in t2["revisao_manual"] for n in g["notas"]}
    assert {"2025NL0103", "2025NL0104", "2025NL0105", "2025NL0106", "2025NL0107", "2025NL0108", "2025NL0109"}.issubset(
        notas_revisao
    )
    motivos_por_nota = {
        n: set(g["motivosBloqueio"])
        for g in t2["revisao_manual"]
        for n in g["notas"]
    }
    assert "truncamento_ambiguo" in motivos_por_nota["2025NL0103"]
    assert any("nf" in m for m in motivos_por_nota["2025NL0104"])
    assert any("simetrico" in m for m in motivos_por_nota["2025NL0106"])
    assert any("competencia" in m for m in motivos_por_nota["2025NL0108"])

    # Subsecao regional separada e contagem sem match no sumario
    assert len(t2["regionais"]) == 1
    assert t2["regionais"][0]["notas"] == ["2025NL0110"]
    assert relatorio["sumario"]["notas_sem_match_territorial"] == 1
    md_t2 = (out_dir / "triagem_territorial.md").read_text(encoding="utf-8")
    assert "### Subseção Regional (Prefeitura-Bairro)" in md_t2
    assert "Subúrbio/Ilhas" in md_t2


def test_trilha_1_promoviveis_lista_fechada_e_exclusoes(tmp_path: Path) -> None:
    """Trilha 1 identifica promovivel unico, lista_fechada (2..8), exclui ambiguo/multi_frente e rejeita conflitos."""
    data_dir = _criar_acervo_minimo(
        tmp_path / "data_t1",
        com_ponteiro=False,
        obras=[
            {
                "id": 3001,
                "cdUnidadeGestora": "301110",
                "nuContratoSigef": "2025CT000101",
                "dsObjeto": "Reforma de unidade de saude municipal",
                "nivel": "Escopo Cidade (Não-Localizado)",
            },
            {
                "id": 3002,
                "cdUnidadeGestora": "616002",
                "nuContratoSigef": "2025CT000102",
                "dsObjeto": "Requalificacao de escolas nos bairros Pituba, Brotas e Paripe",
                "nivel": "Escopo Cidade (Não-Localizado)",
            },
            {
                "id": 3003,
                "cdUnidadeGestora": "616002",
                "nuContratoSigef": "2025CT000103",
                "dsObjeto": "Obra ja curada como ambigua",
                "nivel": "Escopo Cidade (Não-Localizado)",
            },
            {
                "id": 3004,
                "cdUnidadeGestora": "616002",
                "nuContratoSigef": "2025CT000104",
                "dsObjeto": "Contrato com bairros conflitantes nas medicoes",
                "nivel": "Escopo Cidade (Não-Localizado)",
            },
            {
                "id": 3005,
                "cdUnidadeGestora": "616002",
                "nuContratoSigef": "2025CT000105",
                "dsObjeto": "Contrato ja curado como multi_frente",
                "nivel": "Escopo Cidade (Não-Localizado)",
            },
        ],
        fichas={
            "3001": {
                "id": 3001,
                "cdUnidadeGestora": "301110",
                "nuContratoSigef": "2025CT000101",
                "dsObjeto": "Reforma de unidade de saude municipal",
                "nivel": "Escopo Cidade (Não-Localizado)",
                "aditivos": [
                    {"nuAditivo": "1", "dsObjetoAditivo": "REFORMA DA UNIDADE NA PITUBA"}
                ],
                "liquidacoes": [
                    {
                        "notaLiquidacao": "2025NL0301",
                        "valLiqLiquidacao": "50.000,00",
                        "descObsLiquidacao": "1ª MEDICAO REFORMA PITUBA - NFSE 10",
                    }
                ],
            },
            "3002": {
                "id": 3002,
                "cdUnidadeGestora": "616002",
                "nuContratoSigef": "2025CT000102",
                "dsObjeto": "Requalificacao de escolas nos bairros Pituba, Brotas e Paripe",
                "nivel": "Escopo Cidade (Não-Localizado)",
                "aditivos": [],
                "liquidacoes": [
                    {
                        "notaLiquidacao": "2025NL0302",
                        "valLiqLiquidacao": "40.000,00",
                        "descObsLiquidacao": "MEDICAO GLOBAL DE REQUALIFICACAO ESCOLAR - NFSE 20",
                    }
                ],
            },
            "3003": {
                "id": 3003,
                "cdUnidadeGestora": "616002",
                "nuContratoSigef": "2025CT000103",
                "dsObjeto": "Obra ja curada como ambigua",
                "nivel": "Escopo Cidade (Não-Localizado)",
                "aditivos": [
                    {"nuAditivo": "1", "dsObjetoAditivo": "SERVICO EM BROTAS"}
                ],
                "liquidacoes": [],
            },
            "3004": {
                "id": 3004,
                "cdUnidadeGestora": "616002",
                "nuContratoSigef": "2025CT000104",
                "dsObjeto": "Contrato com bairros conflitantes nas medicoes",
                "nivel": "Escopo Cidade (Não-Localizado)",
                "aditivos": [],
                "liquidacoes": [
                    {
                        "notaLiquidacao": "2025NL0304",
                        "valLiqLiquidacao": "10.000,00",
                        "descObsLiquidacao": "SERVICOS EM PITUBA - NFSE 31",
                    },
                    {
                        "notaLiquidacao": "2025NL0305",
                        "valLiqLiquidacao": "10.000,00",
                        "descObsLiquidacao": "SERVICOS EM BROTAS - NFSE 32",
                    },
                ],
            },
            "3005": {
                "id": 3005,
                "cdUnidadeGestora": "616002",
                "nuContratoSigef": "2025CT000105",
                "dsObjeto": "Contrato ja curado como multi_frente",
                "nivel": "Escopo Cidade (Não-Localizado)",
                "aditivos": [
                    {"nuAditivo": "1", "dsObjetoAditivo": "SERVICO EM PARIPE"}
                ],
                "liquidacoes": [],
            },
        },
    )

    curadoria_path = tmp_path / "curadoria_t1.json"
    curadoria_path.write_text(
        json.dumps(
            {
                "versao": 1,
                "registros": {
                    "616002:2025CT000103": {
                        "status": "ambiguo",
                        "nivel": "Escopo Cidade (Não-Localizado)",
                    },
                    "616002:2025CT000105": {
                        "status": "multi_frente",
                        "nivel": "Escopo Cidade (Não-Localizado)",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    relatorio = executar_triagem_territorial(data_dir, tmp_path / "out_t1", curadoria_path=curadoria_path)
    t1 = relatorio["trilha_1_contratos"]

    assert [c["contrato"] for c in t1["promoviveis"]] == ["301110:2025CT000101"]
    assert t1["promoviveis"][0]["bairroSugerido"] == "Pituba"
    assert len(t1["promoviveis"][0]["evidencias"]) == 2

    assert [c["contrato"] for c in t1["lista_fechada"]] == ["616002:2025CT000102"]
    assert set(t1["lista_fechada"][0]["itensIdentificados"]) == {"Pituba", "Brotas", "Paripe"}
    assert relatorio["sumario"]["trilha_1_total"] == 2


def test_trilha_3_equipamentos_e_sublocalidades_recorrentes(tmp_path: Path) -> None:
    """Trilha 3 extrai equipamentos e sublocalidades recorrentes (>= 2) ausentes dos catalogos."""
    data_dir = _criar_acervo_minimo(
        tmp_path / "data_t3",
        com_ponteiro=False,
        obras=[
            {
                "id": 4001,
                "cdUnidadeGestora": "616002",
                "nuContratoSigef": "2025CT000401",
                "dsObjeto": "Manutencao na E.M. ESTRELA DOURADA e no LOTEAMENTO NOVA AURORA",
                "nivel": "Escopo Cidade (Não-Localizado)",
            },
            {
                "id": 4002,
                "cdUnidadeGestora": "616002",
                "nuContratoSigef": "2025CT000402",
                "dsObjeto": "Reforma da USF JARDIM INEXISTENTE",
                "nivel": "Escopo Cidade (Não-Localizado)",
            },
        ],
        fichas={
            "4001": {
                "id": 4001,
                "cdUnidadeGestora": "616002",
                "nuContratoSigef": "2025CT000401",
                "dsObjeto": "Manutencao na E.M. ESTRELA DOURADA e no LOTEAMENTO NOVA AURORA",
                "nivel": "Escopo Cidade (Não-Localizado)",
                "aditivos": [
                    {
                        "nuAditivo": "1",
                        "dsObjetoAditivo": "AMPLIACAO DA ESCOLA ESTRELA DOURADA - LOTEAMENTO NOVA AURORA",
                    }
                ],
                "liquidacoes": [
                    {
                        "notaLiquidacao": "2025NL0401",
                        "valLiqLiquidacao": "5.000,00",
                        "descObsLiquidacao": "SERVICOS NA USF JARDIM INEXISTENTE - NFSE 11",
                    },
                    {
                        "notaLiquidacao": "2025NL0402",
                        "valLiqLiquidacao": "3.000,00",
                        "descObsLiquidacao": "SERVICOS NA UPA UNICA ISOLADA - NFSE 12",
                    },
                ],
            },
            "4002": {
                "id": 4002,
                "cdUnidadeGestora": "616002",
                "nuContratoSigef": "2025CT000402",
                "dsObjeto": "Reforma da USF JARDIM INEXISTENTE",
                "nivel": "Escopo Cidade (Não-Localizado)",
                "aditivos": [],
                "liquidacoes": [],
            },
        },
    )

    curadoria_vazia = tmp_path / "curadoria_t3.json"
    curadoria_vazia.write_text('{"versao": 1, "registros": {}}', encoding="utf-8")

    relatorio = executar_triagem_territorial(data_dir, tmp_path / "out_t3", curadoria_path=curadoria_vazia)
    t3 = relatorio["trilha_3_catalogos"]

    nomes_eq = {e["nome"]: e["contagem"] for e in t3["equipamentos"]}
    assert any("JARDIM INEXISTENTE" in k and v >= 2 for k, v in nomes_eq.items())
    assert any("ESTRELA DOURADA" in k and v >= 2 for k, v in nomes_eq.items())
    assert not any("UNICA ISOLADA" in k for k in nomes_eq)

    nomes_sub = {s["termo"]: s["contagem"] for s in t3["sublocalidades"]}
    assert any("NOVA AURORA" in k and v >= 2 for k, v in nomes_sub.items())
    assert relatorio["sumario"]["trilha_3_equipamentos"] == len(t3["equipamentos"])
    assert relatorio["sumario"]["trilha_3_sublocalidades"] == len(t3["sublocalidades"])


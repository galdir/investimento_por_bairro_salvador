"""Testes da Seam 2 para o motor e relatório de Exploração Estatística Agnóstica (EDA)."""

import json
from pathlib import Path


def _criar_fixture_eda_minima(base_dir: Path) -> tuple[Path, Path]:
    """Cria um acervo local mínimo reconciliado e catálogo censitário em diretório temporário."""
    data_dir = base_dir / "data"
    obras_dir = data_dir / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)

    censo_path = base_dir / "censo_2022.json"
    censo = {
        "BAIRRO ALFA": {
            "populacao": 10000,
            "pct_esgoto_inadequado": 25.0,
            "pct_agua_inadequada": 4.0,
            "pct_analfabetismo_15mais": 5.0,
            "is_zona_especial_nao_residencial": False,
            "indice_vulnerabilidade": 0.65,
        },
        "BAIRRO BETA": {
            "populacao": 20000,
            "pct_esgoto_inadequado": 2.0,
            "pct_agua_inadequada": 0.5,
            "pct_analfabetismo_15mais": 1.0,
            "is_zona_especial_nao_residencial": False,
            "indice_vulnerabilidade": 0.12,
        },
        "AEROPORTO": {
            "populacao": 0,
            "pct_esgoto_inadequado": 0.0,
            "pct_agua_inadequada": 0.0,
            "pct_analfabetismo_15mais": 0.0,
            "is_zona_especial_nao_residencial": True,
            "indice_vulnerabilidade": 0.0,
        },
    }
    censo_path.write_text(json.dumps(censo, ensure_ascii=False), encoding="utf-8")

    obras_index = [
        {
            "id": "obra-1",
            "cdUnidadeGestora": "101",
            "unidadeGestora": "SUCOP",
            "nuContratoSigef": "2022CT0001",
            "numeroContrato": "2022CT0001",
            "objeto": "Contenção de encosta no Bairro Alfa",
            "valorOriginal": 1000000.0,
            "valorContratualVigente": 1300000.0,
            "valorAditivos": 300000.0,
            "deltaPercentualValor": 30.0,
            "valorPago": 500000.0,
            "percentualExecutado": 50.0,
            "situacao": "Em Execução",
            "credor": "CONSTRUTORA A LTDA",
            "cnpj": "11.111.111/0001-11",
            "tema": "Encostas e Contenção",
            "semaforo": {
                "status": "VERMELHO",
                "rotulo": "Vermelho (Crítica)",
                "motivos": ["Aditivo de valor superior a 25%"],
            },
            "mandatos": ["2021-2024"],
            "dtInicioVigencia": "2022-01-10T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2023-06-10T00:00:00.000Z",
            "nivel": "Bairro",
            "bairro": "Bairro Alfa",
            "prefeituraBairro": "PB Centro",
            "estagioAlocacao": "Texto",
        },
        {
            "id": "obra-2",
            "cdUnidadeGestora": "102",
            "unidadeGestora": "SEMED",
            "nuContratoSigef": "2024CT0002",
            "numeroContrato": "2024CT0002",
            "objeto": "Reforma de escola no Bairro Beta",
            "valorOriginal": 2000000.0,
            "valorContratualVigente": 2000000.0,
            "valorAditivos": 0.0,
            "deltaPercentualValor": 0.0,
            "valorPago": 1000000.0,  # Fallback sintético (50% de 2M, sem notas reais)
            "percentualExecutado": 50.0,
            "situacao": "Em Execução",
            "credor": "CONSTRUTORA B LTDA",
            "cnpj": "22.222.222/0001-22",
            "tema": "Educação e Escolas",
            "semaforo": {
                "status": "VERDE",
                "rotulo": "Verde (No Prazo)",
                "motivos": ["Obra dentro do cronograma contratual vigente"],
            },
            "mandatos": ["2021-2024", "2025-2028"],
            "dtInicioVigencia": "2024-06-01T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2025-06-01T00:00:00.000Z",
            "nivel": "Pontual",
            "bairro": "Bairro Beta",
            "prefeituraBairro": "PB Orla",
            "estagioAlocacao": "Equipamento",
        },
        {
            "id": "obra-3",
            "cdUnidadeGestora": "101",
            "unidadeGestora": "SUCOP",
            "nuContratoSigef": "2025CT0003",
            "numeroContrato": "2025CT0003",
            "objeto": "Manutenção viária em diversas vias da cidade",
            "valorOriginal": 500000.0,
            "valorContratualVigente": 575000.0,
            "valorAditivos": 75000.0,
            "deltaPercentualValor": 15.0,
            "valorPago": 0.0,
            "percentualExecutado": 0.0,
            "situacao": "Em Execução",
            "credor": "CONSTRUTORA A LTDA",
            "cnpj": "11.111.111/0001-11",
            "tema": "Mobilidade, Pavimentação e Drenagem",
            "semaforo": {
                "status": "AMARELO",
                "rotulo": "Amarelo (Atenção)",
                "motivos": ["Aditivo de valor entre 10% e 25%"],
            },
            "mandatos": ["2025-2028"],
            "dtInicioVigencia": "2025-02-01T00:00:00.000Z",
            "dtTerminoVigenciaAtualizado": "2026-02-01T00:00:00.000Z",
            "nivel": "Escopo Cidade (Não-Localizado)",
            "bairro": None,
            "prefeituraBairro": None,
            "estagioAlocacao": "Não-Localizado",
        },
    ]

    fichas = {
        "obra-1": {
            "id": "obra-1",
            "unidadeGestora": "SUCOP",
            "cdUnidadeGestora": "101",
            "numeroContrato": "2022CT0001",
            "objeto": "Contenção de encosta no Bairro Alfa",
            "situacao": "Em Execução",
            "empreiteira": {"razaoSocial": "CONSTRUTORA A LTDA", "cnpj": "11.111.111/0001-11"},
            "vigencia": {
                "dataInicio": "2022-01-10T00:00:00.000Z",
                "dataFimOriginal": "2023-01-10T00:00:00.000Z",
                "dataTerminoAtualizado": "2023-06-10T00:00:00.000Z",
                "prazoOriginal": "365",
                "prazoAtualizado": "516",
            },
            "dom": {"nuDom": "8100", "dataPublicacao": "2022-01-15T00:00:00.000Z"},
            "funilFinanceiro": {
                "valorOriginal": 1000000.0,
                "valorContratualVigente": 1300000.0,
                "valorEmpenhado": 900000.0,
                "valorLiquidado": 600000.0,
                "valorPago": 500000.0,
                "percentualExecutado": 50.0,
                "valorAditivos": 300000.0,
                "deltaPercentualAditivos": 30.0,
            },
            "aditivos": [
                {
                    "nuAditivo": "1",
                    "dsTipoAlteracao": "Acréscimo de valor",
                    "dtAssinatura": "10/11/2022",
                    "vlAditivo": 200000.0,
                }
            ],
            "dotacao": [
                {
                    "subacao": "Contenção de Encostas",
                    "fonteRecurso": "Tesouro",
                    "classificacao": "Obras e Instalações",
                }
            ],
            "empenhos": [
                {"dataEmpenho": "20/01/2022", "valEmpenhado": "900.000,00"}
            ],
            "liquidacoes": [
                {"dataLiquidacao": "15/08/2022", "valLiqLiquidacao": "600.000,00"}
            ],
            "pagamentos": [
                {"dataPagamento": "25/08/2022", "pago": "500.000,00"}
            ],
            "tema": "Encostas e Contenção",
            "semaforo": obras_index[0]["semaforo"],
            "nivel": "Bairro",
            "bairro": "Bairro Alfa",
            "prefeituraBairro": "PB Centro",
        },
        "obra-2": {
            "id": "obra-2",
            "unidadeGestora": "SEMED",
            "cdUnidadeGestora": "102",
            "numeroContrato": "2024CT0002",
            "objeto": "Reforma de escola no Bairro Beta",
            "situacao": "Em Execução",
            "empreiteira": {"razaoSocial": "CONSTRUTORA B LTDA", "cnpj": "22.222.222/0001-22"},
            "vigencia": {
                "dataInicio": "2024-06-01T00:00:00.000Z",
                "dataFimOriginal": "2025-06-01T00:00:00.000Z",
                "dataTerminoAtualizado": "2025-06-01T00:00:00.000Z",
                "prazoOriginal": "365",
                "prazoAtualizado": "365",
            },
            "dom": {"nuDom": None, "dataPublicacao": None},
            "funilFinanceiro": {
                "valorOriginal": 2000000.0,
                "valorContratualVigente": 2000000.0,
                "valorEmpenhado": 2000000.0,  # Fallback sintético!
                "valorLiquidado": 0.0,
                "valorPago": 1000000.0,  # Fallback sintético!
                "percentualExecutado": 50.0,
                "valorAditivos": 0.0,
                "deltaPercentualAditivos": 0.0,
            },
            "aditivos": [],
            "dotacao": [
                {
                    "subacao": "Infraestrutura Escolar",
                    "fonteRecurso": "FUNDEB",
                    "classificacao": "Obras e Instalações",
                }
            ],
            "empenhos": [],
            "liquidacoes": [],
            "pagamentos": [],
            "tema": "Educação e Escolas",
            "semaforo": obras_index[1]["semaforo"],
            "nivel": "Pontual",
            "bairro": "Bairro Beta",
            "prefeituraBairro": "PB Orla",
        },
        "obra-3": {
            "id": "obra-3",
            "unidadeGestora": "SUCOP",
            "cdUnidadeGestora": "101",
            "numeroContrato": "2025CT0003",
            "objeto": "Manutenção viária em diversas vias da cidade",
            "situacao": "Em Execução",
            "empreiteira": {"razaoSocial": "CONSTRUTORA A LTDA", "cnpj": "11.111.111/0001-11"},
            "vigencia": {
                "dataInicio": "2025-02-01T00:00:00.000Z",
                "dataFimOriginal": "2026-02-01T00:00:00.000Z",
                "dataTerminoAtualizado": "2026-02-01T00:00:00.000Z",
                "prazoOriginal": "365",
                "prazoAtualizado": "365",
            },
            "dom": {"nuDom": "9001", "dataPublicacao": "2025-02-05T00:00:00.000Z"},
            "funilFinanceiro": {
                "valorOriginal": 500000.0,
                "valorContratualVigente": 575000.0,
                "valorEmpenhado": 575000.0,  # Fallback sintético!
                "valorLiquidado": 0.0,
                "valorPago": 0.0,
                "percentualExecutado": 0.0,
                "valorAditivos": 75000.0,
                "deltaPercentualAditivos": 15.0,
            },
            "aditivos": [],
            "dotacao": [
                {
                    "subacao": "Pavimentação Urbana",
                    "fonteRecurso": "Tesouro",
                    "classificacao": "Obras e Instalações",
                }
            ],
            "empenhos": [],
            "liquidacoes": [],
            "pagamentos": [],
            "tema": "Mobilidade, Pavimentação e Drenagem",
            "semaforo": obras_index[2]["semaforo"],
            "nivel": "Escopo Cidade (Não-Localizado)",
            "bairro": None,
            "prefeituraBairro": None,
        },
    }

    for oid, ficha in fichas.items():
        (obras_dir / f"{oid}.json").write_text(
            json.dumps(ficha, ensure_ascii=False), encoding="utf-8"
        )

    index_data = {
        "metadata": {"anoReferencia": 2025},
        "kpis_globais": {
            "totalObras": 3,
            "valorTotal": 3875000.0,
            "totalEmpenhado": 900000.0,
            "totalLiquidado": 600000.0,
            "totalPago": 500000.0,
        },
        "concentracao_empreiteiras": [
            {
                "cnpj": "11.111.111/0001-11",
                "razaoSocial": "CONSTRUTORA A LTDA",
                "totalObras": 2,
                "totalObrasAtivas": 2,
                "valorTotalContratado": 1875000.0,
                "obrasIds": ["obra-1", "obra-3"],
            },
            {
                "cnpj": "22.222.222/0001-22",
                "razaoSocial": "CONSTRUTORA B LTDA",
                "totalObras": 1,
                "totalObrasAtivas": 1,
                "valorTotalContratado": 2000000.0,
                "obrasIds": ["obra-2"],
            },
        ],
        "prefeituras_bairro": [
            {
                "id": 1,
                "nome": "PB Centro",
                "populacao_total": 10000,
                "indice_vulnerabilidade": 0.65,
                "valorTotal": 1300000.0,
                "valorPago": 500000.0,
                "totalObras": 1,
                "investimentoPorHabitante": 130.0,
                "investimentoPorHabitantePago": 50.0,
            },
            {
                "id": 2,
                "nome": "PB Orla",
                "populacao_total": 20000,
                "indice_vulnerabilidade": 0.12,
                "valorTotal": 2000000.0,
                "valorPago": 1000000.0,
                "totalObras": 1,
                "investimentoPorHabitante": 100.0,
                "investimentoPorHabitantePago": 50.0,
            },
        ],
        "bairros": [
            {
                "id": 1,
                "nome": "Bairro Alfa",
                "prefeitura_bairro": "PB Centro",
                "populacao": 10000,
                "indice_vulnerabilidade": 0.65,
                "is_zona_especial_nao_residencial": False,
                "pct_esgoto_inadequado": 25.0,
                "pct_agua_inadequada": 4.0,
                "pct_analfabetismo_15mais": 5.0,
                "valorTotal": 1300000.0,
                "valorPago": 500000.0,
                "totalObras": 1,
                "investimentoPorHabitante": 130.0,
                "investimentoPorHabitantePago": 50.0,
            },
            {
                "id": 2,
                "nome": "Bairro Beta",
                "prefeitura_bairro": "PB Orla",
                "populacao": 20000,
                "indice_vulnerabilidade": 0.12,
                "is_zona_especial_nao_residencial": False,
                "pct_esgoto_inadequado": 2.0,
                "pct_agua_inadequada": 0.5,
                "pct_analfabetismo_15mais": 1.0,
                "valorTotal": 2000000.0,
                "valorPago": 1000000.0,
                "totalObras": 1,
                "investimentoPorHabitante": 100.0,
                "investimentoPorHabitantePago": 50.0,
            },
            {
                "id": 3,
                "nome": "Aeroporto",
                "prefeitura_bairro": "PB Orla",
                "populacao": 0,
                "indice_vulnerabilidade": 0.0,
                "is_zona_especial_nao_residencial": True,
                "pct_esgoto_inadequado": 0.0,
                "pct_agua_inadequada": 0.0,
                "pct_analfabetismo_15mais": 0.0,
                "valorTotal": 0.0,
                "valorPago": 0.0,
                "totalObras": 0,
                "investimentoPorHabitante": 0.0,
                "investimentoPorHabitantePago": 0.0,
            },
        ],
        "obras": obras_index,
    }
    (data_dir / "index.json").write_text(
        json.dumps(index_data, ensure_ascii=False), encoding="utf-8"
    )
    return data_dir, censo_path


def test_eda_agnostica_gera_cinco_secoes_coortes_exclusivas_e_isola_fallbacks(
    tmp_path: Path,
) -> None:
    """Valida na Seam 2 a geração completa do relatório EDA, coortes sem dupla contagem e isolamento de fallbacks."""
    from etl.eda import executar_eda_agnostica

    data_dir, censo_path = _criar_fixture_eda_minima(tmp_path)
    output_md = tmp_path / "relatorio_eda.md"

    resultado = executar_eda_agnostica(
        data_dir=data_dir,
        censo_path=censo_path,
        output_path=output_md,
    )

    assert output_md.exists()
    md = resultado["report_markdown"]
    assert output_md.read_text(encoding="utf-8") == md

    # Presença obrigatória das 5 seções
    for secao in [
        "## Seção 1:",
        "## Seção 2:",
        "## Seção 3:",
        "## Seção 4:",
        "## Seção 5:",
    ]:
        assert secao in md

    # Volumetria exata nas 4 granularidades
    vol = resultado["volumetria"]
    assert vol["bairros"] == 3
    assert vol["prefeituras_bairro"] == 2
    assert vol["obras"] == 3
    assert vol["empreiteiras"] == 2
    assert vol["obras_com_empenhos"] == 1
    assert vol["obras_com_liquidacoes"] == 1
    assert vol["obras_com_pagamentos"] == 1

    # Coortes mutuamente exclusivas de Mandato Municipal sem dupla contagem
    coortes = resultado["coortes_mandato"]
    assert coortes["2021-2024 exclusivo"] == 1
    assert coortes["2021-2024 ∩ 2025-2028"] == 1
    assert coortes["2025-2028 exclusivo"] == 1
    assert sum(coortes.values()) == 3

    # Isolamento dos fallbacks sintéticos na subamostra contábil verificada
    sub = resultado["subamostra_contabil"]
    assert sub["n_empenhos"] == 1
    assert sub["total_empenhado_real"] == 900000.0
    assert sub["n_pagamentos"] == 1
    assert sub["total_pago_real"] == 500000.0

    # Comparação Variação Contratual Acumulada vs Aditivos Contratuais formais
    # obra-1 tem 300k de variação e 200k em aditivos listados; obra-3 tem 75k e 0 listados
    comp = resultado["comparacao_aditivos"]
    assert comp["variacao_contratual_acumulada_total"] == 375000.0
    assert comp["aditivos_formais_listados_total"] == 200000.0
    assert comp["contratos_variacao_sem_aditivos_listados"] == 1

    # Presença de métricas de concentração, correlações, eta², outliers, clustering e auditoria
    for marcador in [
        "Índice de Gini",
        "CR1 / CR5 / CR10 / CR20",
        "HHI",
        "Pearson (r)",
        "Spearman (ρ)",
        "Variância Explicada (η²)",
        "|Z| > 3σ",
        "Q3 + 1,5×IQR",
        "Agrupamento Não-Supervisionado",
        "Decomposição dos Gatilhos do Semáforo da Obra",
        "Escopo Cidade (Não-Localizado)",
        "Zonas Especiais Não-Residenciais excluídas",
    ]:
        assert marcador in md


def test_eda_agnostica_acervo_real_deterministico_e_consistente(tmp_path: Path) -> None:
    """Valida na Seam 2 a consistência estrutural, isolamento contábil e determinismo sobre public/data."""
    from etl.eda import executar_eda_agnostica

    data_dir = Path("public/data")
    if not (data_dir / "index.json").exists():
        return

    index_data = json.loads((data_dir / "index.json").read_text(encoding="utf-8"))
    obras_index = index_data.get("obras", [])
    kpis_globais = index_data.get("kpis_globais", {})

    out_1 = tmp_path / "eda_1.md"
    out_2 = tmp_path / "eda_2.md"

    res_1 = executar_eda_agnostica(data_dir=data_dir, output_path=out_1)
    res_2 = executar_eda_agnostica(data_dir=data_dir, output_path=out_2)

    # Reprodutibilidade determinística
    assert res_1["report_markdown"] == res_2["report_markdown"]

    vol = res_1["volumetria"]
    assert vol["bairros"] == 171
    assert vol["bairros_residenciais"] == 168
    assert vol["bairros_especiais"] == 3
    assert vol["prefeituras_bairro"] == 10
    assert vol["obras"] == len(obras_index) > 0
    assert vol["fichas"] == vol["obras"]
    assert vol["empreiteiras"] == len(index_data.get("concentracao_empreiteiras", [])) > 0
    assert vol["obras_com_empenhos"] > 0
    assert vol["obras_com_liquidacoes"] > 0
    assert vol["obras_com_pagamentos"] > 0
    assert vol["obras_com_aditivos"] > 0

    # Coortes mutuamente exclusivas somam exatamente o total de obras sem dupla contagem
    coortes = res_1["coortes_mandato"]
    assert sum(coortes.values()) == vol["obras"]
    assert coortes["2021-2024 exclusivo"] > 0
    assert coortes["2021-2024 ∩ 2025-2028"] > 0
    assert coortes["2025-2028 exclusivo"] > 0
    assert coortes.get("Sem mandato definido", 0) == 0

    # Subamostra contábil real isolada de fallbacks sintéticos do índice
    sub = res_1["subamostra_contabil"]
    assert sub["n_empenhos"] == vol["obras_com_empenhos"]
    assert sub["n_liquidacoes"] == vol["obras_com_liquidacoes"]
    assert sub["n_pagamentos"] == vol["obras_com_pagamentos"]
    assert sub["total_empenhado_real"] > 0
    assert round(sub["total_liquidado_real"], 2) == round(float(kpis_globais["totalLiquidado"]), 2)
    assert round(sub["total_pago_real"], 2) == round(float(kpis_globais["totalPago"]), 2)
    soma_valor_pago_indice = sum(float(o.get("valorPago") or 0.0) for o in obras_index)
    assert sub["total_pago_real"] < soma_valor_pago_indice

    # Presença de tabelas não vazias nas Seções 3, 4 e 5
    assert res_1["correlacoes_bairros_count"] > 0
    assert res_1["correlacoes_obras_count"] > 0
    assert res_1["eta2_count"] > 0
    assert res_1["clusters_bairros"] == 4
    assert res_1["clusters_obras"] == 4


"""Motor offline, determinístico e reprodutível de Exploração Estatística Agnóstica (EDA).

Analisa o acervo local reconciliado nas quatro granularidades (Território, Contrato,
Transação/Evento e Credor) sem disparar requisições de rede e sem modificar os dados
de produção, emitindo um relatório técnico em Markdown dividido em cinco seções.
"""

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd

from etl.domain.empreiteiras import eh_cnpj_valido
from etl.domain.ficha_limpa import eh_dom_valido
from etl.domain.territorio import parse_float


DEFAULT_CENSO_PATH = Path(__file__).resolve().parent / "reference" / "censo_2022_salvador_bairros.json"
DEFAULT_DATA_DIR = Path("public/data")
DEFAULT_OUTPUT_PATH = Path("docs/relatorio_eda_agnostica.md")


def _fmt_brl(valor: float) -> str:
    """Formata um valor numérico em Real brasileiro."""
    sinal = "-" if valor < 0 else ""
    abs_val = abs(valor)
    inteiro, frac = f"{abs_val:,.2f}".split(".")
    inteiro_pt = inteiro.replace(",", ".")
    return f"{sinal}R$ {inteiro_pt},{frac}"


def _fmt_num(valor: float | None, casas: int = 2) -> str:
    """Formata um número decimal com separador brasileiro ou retorna N/A."""
    if valor is None or (isinstance(valor, float) and (math.isnan(valor) or math.isinf(valor))):
        return "N/A"
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _parse_int_seguro(valor: Any) -> float | None:
    """Converte um campo inteiro/string (como prazo em dias) para float ou None."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if not texto:
        return None
    try:
        return float(texto.replace(",", "."))
    except ValueError:
        return None


def _extrair_ano_mes(data_str: Any) -> tuple[int, int] | None:
    """Extrai (ano, mes) de datas DD/MM/YYYY ou ISO YYYY-MM-DD."""
    if not data_str or not isinstance(data_str, str):
        return None
    s = data_str.strip()
    m_br = re.match(r"^(\d{2})/(\d{2})/(\d{4})", s)
    if m_br:
        return int(m_br.group(3)), int(m_br.group(2))
    m_iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m_iso:
        return int(m_iso.group(1)), int(m_iso.group(2))
    return None


def _eh_zero(valor: Any) -> bool:
    """Verifica se um valor numérico ou string formatada equivale a zero."""
    if valor is None or valor == "":
        return False
    if isinstance(valor, (int, float)):
        return float(valor) == 0.0
    texto = str(valor).strip()
    if not re.match(r"^-?[\d.,]+$", texto):
        return False
    return parse_float(texto) == 0.0


def _classificar_coorte_mandato(mandatos: Any) -> str:
    """Classifica uma Obra Pública em uma das três coortes mutuamente exclusivas."""
    conjunto = set(mandatos or [])
    tem_21 = "2021-2024" in conjunto
    tem_25 = "2025-2028" in conjunto
    if tem_21 and not tem_25:
        return "2021-2024 exclusivo"
    if tem_21 and tem_25:
        return "2021-2024 ∩ 2025-2028"
    if tem_25 and not tem_21:
        return "2025-2028 exclusivo"
    return "Sem mandato definido"


def _resumo_univariado(valores: list[float]) -> dict[str, float | int | None]:
    """Calcula estatísticas paramétricas e não-paramétricas sobre uma lista numérica."""
    limpos = [float(v) for v in valores if v is not None and not math.isnan(float(v))]
    n = len(limpos)
    if n == 0:
        return {
            "n": 0,
            "mean": None,
            "std": None,
            "min": None,
            "p10": None,
            "p25": None,
            "p50": None,
            "p75": None,
            "p90": None,
            "p99": None,
            "max": None,
            "iqr": None,
            "skew": None,
        }
    arr = np.asarray(limpos, dtype=float)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    p10, p25, p50, p75, p90, p99 = [
        float(x) for x in np.percentile(arr, [10, 25, 50, 75, 90, 99])
    ]
    skew = float(pd.Series(arr).skew()) if n > 2 and std > 0 else 0.0
    if math.isnan(skew):
        skew = 0.0
    return {
        "n": n,
        "mean": mean,
        "std": std,
        "min": float(np.min(arr)),
        "p10": p10,
        "p25": p25,
        "p50": p50,
        "p75": p75,
        "p90": p90,
        "p99": p99,
        "max": float(np.max(arr)),
        "iqr": p75 - p25,
        "skew": skew,
    }


def _tabela_univariada_md(linhas: list[tuple[str, dict[str, Any], bool]]) -> str:
    """Formata uma lista de resumos univariados em tabela Markdown."""
    cabecalho = (
        "| Variável | N | Média | Desvio-Padrão | Mín | P10 | P25 | Mediana (P50) | "
        "P75 | P90 | P99 | Máx | IQR | Assimetria |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    )
    rows = [cabecalho]
    for nome, stats, eh_moeda in linhas:
        fmt = _fmt_brl if eh_moeda else _fmt_num
        rows.append(
            f"| {nome} | {stats['n']} | {fmt(stats['mean'])} | {fmt(stats['std'])} | "
            f"{fmt(stats['min'])} | {fmt(stats['p10'])} | {fmt(stats['p25'])} | "
            f"{fmt(stats['p50'])} | {fmt(stats['p75'])} | {fmt(stats['p90'])} | "
            f"{fmt(stats['p99'])} | {fmt(stats['max'])} | {fmt(stats['iqr'])} | "
            f"{_fmt_num(stats['skew'])} |"
        )
    return "\n".join(rows)


def _calcular_concentracao_mercado(valores: list[float]) -> dict[str, float]:
    """Calcula Gini, CR1, CR5, CR10, CR20 e HHI sobre os valores contratados por credor."""
    pos = sorted([float(v) for v in valores if v > 0])
    n = len(pos)
    total = sum(pos)
    if n == 0 or total <= 0:
        return {"gini": 0.0, "cr1": 0.0, "cr5": 0.0, "cr10": 0.0, "cr20": 0.0, "hhi": 0.0}

    # Gini ordenado ascendente: (2 * sum(i * x_i)) / (n * sum(x_i)) - (n + 1)/n
    soma_ponderada = sum((idx + 1) * val for idx, val in enumerate(pos))
    gini = (2.0 * soma_ponderada) / (n * total) - (n + 1.0) / n

    desc = list(reversed(pos))
    shares = [v / total for v in desc]
    cr1 = sum(shares[:1]) * 100.0
    cr5 = sum(shares[:5]) * 100.0
    cr10 = sum(shares[:10]) * 100.0
    cr20 = sum(shares[:20]) * 100.0
    hhi = sum((s * 100.0) ** 2 for s in shares)
    return {
        "gini": gini,
        "cr1": cr1,
        "cr5": cr5,
        "cr10": cr10,
        "cr20": cr20,
        "hhi": hhi,
    }


def _correlacoes_pares(
    df: pd.DataFrame, colunas: list[str]
) -> list[dict[str, Any]]:
    """Computa correlações de Pearson (r) e Spearman (rho) para todos os pares distintos."""
    resultados: list[dict[str, Any]] = []
    for i in range(len(colunas)):
        for j in range(i + 1, len(colunas)):
            c1, c2 = colunas[i], colunas[j]
            sub = df[[c1, c2]].dropna()
            if len(sub) < 3 or sub[c1].nunique() < 2 or sub[c2].nunique() < 2:
                continue
            r = float(sub[c1].corr(sub[c2], method="pearson"))
            rho = float(sub[c1].corr(sub[c2], method="spearman"))
            if math.isnan(r) or math.isnan(rho):
                continue
            resultados.append(
                {"var1": c1, "var2": c2, "n": len(sub), "pearson": r, "spearman": rho}
            )
    resultados.sort(key=lambda item: max(abs(item["pearson"]), abs(item["spearman"])), reverse=True)
    return resultados


def _eta_quadrado(grupos: pd.Series, valores: pd.Series) -> float | None:
    """Calcula a variância explicada eta² = SS_between / SS_total."""
    df = pd.DataFrame({"g": grupos, "v": valores}).dropna()
    if len(df) < 3 or df["g"].nunique() < 2:
        return None
    media_global = df["v"].mean()
    ss_total = float(((df["v"] - media_global) ** 2).sum())
    if ss_total <= 0:
        return None
    ss_between = float(
        sum(len(sub) * ((sub["v"].mean() - media_global) ** 2) for _, sub in df.groupby("g"))
    )
    return ss_between / ss_total


def _detectar_outliers_metrica(
    itens: list[tuple[str, float]],
) -> dict[str, Any]:
    """Identifica outliers matemáticos por |Z| > 3σ e > Q3 + 1.5×IQR."""
    if len(itens) < 4:
        return {"limiar_z3": None, "limiar_iqr": None, "outliers_z": [], "outliers_iqr": []}
    arr = np.asarray([v for _, v in itens], dtype=float)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    q1, q3 = [float(x) for x in np.percentile(arr, [25, 75])]
    iqr = q3 - q1
    limiar_iqr = q3 + 1.5 * iqr
    limiar_z3 = mean + 3.0 * std if std > 0 else None

    outliers_z = []
    outliers_iqr = []
    for rotulo, val in itens:
        z = (val - mean) / std if std > 0 else 0.0
        if std > 0 and abs(z) > 3.0:
            outliers_z.append({"rotulo": rotulo, "valor": val, "z": z})
        if val > limiar_iqr:
            outliers_iqr.append({"rotulo": rotulo, "valor": val, "z": z})

    outliers_z.sort(key=lambda x: abs(x["valor"]), reverse=True)
    outliers_iqr.sort(key=lambda x: x["valor"], reverse=True)
    return {
        "limiar_z3": limiar_z3,
        "limiar_iqr": limiar_iqr,
        "outliers_z": outliers_z,
        "outliers_iqr": outliers_iqr,
    }


def _kmeans_padronizado(
    df: pd.DataFrame, features: list[str], k: int = 4, seed: int = 42
) -> dict[str, Any]:
    """Executa K-means determinístico sobre variáveis padronizadas (Z-score)."""
    sub = df[features].dropna()
    n = len(sub)
    if n < 2:
        return {"n": n, "k": 0, "perfis": []}
    k_eff = min(k, n)
    raw = sub.to_numpy(dtype=float)
    means = raw.mean(axis=0)
    stds = raw.std(axis=0, ddof=0)
    stds[stds == 0] = 1.0
    z = (raw - means) / stds

    rng = np.random.default_rng(seed)
    indices = rng.choice(n, size=k_eff, replace=False)
    centroides = z[indices].copy()
    labels = np.zeros(n, dtype=int)

    for _ in range(100):
        dists = np.linalg.norm(z[:, None, :] - centroides[None, :, :], axis=2)
        novos_labels = np.argmin(dists, axis=1)
        if np.array_equal(novos_labels, labels):
            break
        labels = novos_labels
        for c in range(k_eff):
            membros = z[labels == c]
            if len(membros) > 0:
                centroides[c] = membros.mean(axis=0)

    perfis = []
    for c in range(k_eff):
        mascara = labels == c
        count = int(np.sum(mascara))
        if count == 0:
            continue
        medias_orig = raw[mascara].mean(axis=0)
        perfis.append(
            {
                "cluster": c + 1,
                "n": count,
                "pct": count / n * 100.0,
                "medias": {feat: float(medias_orig[idx]) for idx, feat in enumerate(features)},
            }
        )
    perfis.sort(key=lambda p: p["n"], reverse=True)
    return {"n": n, "k": len(perfis), "perfis": perfis}


def _carregar_acervo(
    data_dir: Path, censo_path: Path
) -> dict[str, Any]:
    """Carrega offline o índice, as fichas individuais e o catálogo do Censo 2022."""
    index_path = data_dir / "index.json"
    with open(index_path, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    censo_data: dict[str, Any] = {}
    if censo_path.exists():
        with open(censo_path, "r", encoding="utf-8") as f:
            censo_data = json.load(f)

    obras_dir = data_dir / "obras"
    fichas_por_id: dict[str, dict[str, Any]] = {}
    for obra in index_data.get("obras", []):
        oid = str(obra.get("id", ""))
        ficha_path = obras_dir / f"{oid}.json"
        if ficha_path.exists():
            with open(ficha_path, "r", encoding="utf-8") as f:
                fichas_por_id[oid] = json.load(f)

    return {
        "index": index_data,
        "censo": censo_data,
        "fichas": fichas_por_id,
    }


def _construir_secao_1(
    index_data: dict[str, Any],
    fichas: dict[str, dict[str, Any]],
    censo: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Constrói a Seção 1: Radiografia e Qualidade da Base."""
    bairros = index_data.get("bairros", [])
    prefeituras = index_data.get("prefeituras_bairro", [])
    obras = index_data.get("obras", [])
    empreiteiras = index_data.get("concentracao_empreiteiras", [])

    bairros_especiais = [b for b in bairros if b.get("is_zona_especial_nao_residencial")]
    bairros_residenciais = [b for b in bairros if not b.get("is_zona_especial_nao_residencial")]

    n_emp_obras = sum(1 for oid, f in fichas.items() if f.get("empenhos"))
    n_liq_obras = sum(1 for oid, f in fichas.items() if f.get("liquidacoes"))
    n_pag_obras = sum(1 for oid, f in fichas.items() if f.get("pagamentos"))
    n_adi_obras = sum(1 for oid, f in fichas.items() if f.get("aditivos"))
    n_dot_obras = sum(1 for oid, f in fichas.items() if f.get("dotacao"))

    tx_emp = sum(len(f.get("empenhos") or []) for f in fichas.values())
    tx_liq = sum(len(f.get("liquidacoes") or []) for f in fichas.values())
    tx_pag = sum(len(f.get("pagamentos") or []) for f in fichas.values())
    tx_adi = sum(len(f.get("aditivos") or []) for f in fichas.values())
    tx_dot = sum(len(f.get("dotacao") or []) for f in fichas.values())

    cnpjs_validos_obras = sum(1 for o in obras if eh_cnpj_valido(o.get("cnpj")))
    cnpjs_validos_emp = sum(1 for e in empreiteiras if eh_cnpj_valido(e.get("cnpj")))

    def _linhas_perfil(registros: list[dict[str, Any]], granularidade: str, campos: list[str]) -> list[str]:
        linhas: list[str] = []
        total = len(registros)
        for campo in campos:
            preenchidos = sum(1 for r in registros if r.get(campo) not in (None, "", []))
            nulos = total - preenchidos
            zeros = sum(1 for r in registros if _eh_zero(r.get(campo)))
            taxa_p = (preenchidos / total * 100.0) if total else 0.0
            taxa_z = (zeros / total * 100.0) if total else 0.0
            linhas.append(
                f"| {granularidade} | `{campo}` | {preenchidos} | {nulos} | {zeros} | {_fmt_num(taxa_p)}% | {_fmt_num(taxa_z)}% |"
            )
        return linhas

    todas_tx_emp = [x for f in fichas.values() for x in (f.get("empenhos") or [])]
    todas_tx_pag = [x for f in fichas.values() for x in (f.get("pagamentos") or [])]
    todas_tx_adi = [x for f in fichas.values() for x in (f.get("aditivos") or [])]

    linhas_completude = [
        "| Granularidade | Campo | Preenchidos | Nulos/Vazios | Zeros | % Preenchido | % Zeros |",
        "|---|---|---:|---:|---:|---:|---:|",
        *_linhas_perfil(bairros, "Território (Bairro)", ["populacao", "pct_esgoto_inadequado", "valorTotal", "totalObras"]),
        *_linhas_perfil(
            obras,
            "Contrato (Obra)",
            ["objeto", "unidadeGestora", "situacao", "credor", "cnpj", "dtInicioVigencia", "valorOriginal", "valorAditivos", "percentualExecutado", "bairro", "prefeituraBairro", "latitude"],
        ),
        *_linhas_perfil(todas_tx_emp, "Transação (Empenho)", ["dataEmpenho", "valEmpenhado", "fonteRecurso"]),
        *_linhas_perfil(todas_tx_pag, "Transação (Pagamento)", ["dataPagamento", "pago", "ordBancaria"]),
        *_linhas_perfil(todas_tx_adi, "Transação (Aditivo)", ["dtAssinatura", "vlAditivo", "dsTipoAlteracao"]),
        *_linhas_perfil(empreiteiras, "Empreiteira", ["cnpj", "razaoSocial", "totalObras", "valorTotalContratado"]),
    ]
    n_obras = len(obras)
    n_dom_valido = sum(
        1 for f in fichas.values() if eh_dom_valido((f.get("dom") or {}).get("nuDom"))
    )
    linhas_completude.append(
        f"| Contrato (Ficha) | `dom.nuDom` | {n_dom_valido} | {len(fichas) - n_dom_valido} | 0 | "
        f"{_fmt_num(n_dom_valido / len(fichas) * 100.0 if fichas else 0.0)}% | 0,00% |"
    )

    # Auditoria aritmética interna & Variação Contratual Acumulada vs Aditivos Contratuais formais
    inconsistencias_arit = 0
    variacao_total = 0.0
    aditivos_listados_total = 0.0
    contratos_variacao_sem_aditivos = 0
    contratos_diferenca_aditivos = 0

    for o in obras:
        oid = str(o.get("id", ""))
        ficha = fichas.get(oid, {})
        v_orig = parse_float(o.get("valorOriginal"))
        v_vig = parse_float(o.get("valorContratualVigente"))
        v_var = parse_float(o.get("valorAditivos"))
        if abs((v_orig + v_var) - v_vig) > 1.0:
            inconsistencias_arit += 1

        variacao_total += v_var
        aditivos_lista = ficha.get("aditivos") or []
        soma_aditivos_formais = sum(parse_float(a.get("vlAditivo")) for a in aditivos_lista)
        aditivos_listados_total += soma_aditivos_formais

        if v_var > 1.0 and len(aditivos_lista) == 0:
            contratos_variacao_sem_aditivos += 1
        if abs(v_var - soma_aditivos_formais) > 1.0:
            contratos_diferenca_aditivos += 1

    lacuna_emp = n_obras - n_emp_obras
    lacuna_pag = n_obras - n_pag_obras
    diferenca_var_adi = variacao_total - aditivos_listados_total

    texto = f"""## Seção 1: Radiografia e Qualidade da Base

### 1.1 Volumetria nas Quatro Granularidades

| Granularidade | Entidade / Recorte | Quantidade |
|---|---|---:|
| Território | Bairros Oficiais no índice | {len(bairros)} ({len(bairros_residenciais)} residenciais + {len(bairros_especiais)} Zonas Especiais Não-Residenciais) |
| Território | Prefeituras-Bairro | {len(prefeituras)} |
| Território | Chaves no catálogo Censo 2022 | {len(censo)} |
| Contrato | Obras Públicas no índice / fichas individuais | {n_obras} / {len(fichas)} |
| Transação/Evento | Notas de Empenho | {tx_emp} transações em {n_emp_obras} obras |
| Transação/Evento | Notas de Liquidação | {tx_liq} transações em {n_liq_obras} obras |
| Transação/Evento | Ordens Bancárias / Pagamentos | {tx_pag} transações em {n_pag_obras} obras |
| Transação/Evento | Aditivos Contratuais formais listados | {tx_adi} termos em {n_adi_obras} obras |
| Transação/Evento | Dotações Orçamentárias | {tx_dot} registros em {n_dot_obras} obras |
| Empreiteira | Empreiteiras unificadas | {len(empreiteiras)} ({cnpjs_validos_emp} com CNPJ válido) |

### 1.2 Completude e Qualidade dos Campos

{chr(10).join(linhas_completude)}

- Contratos com CNPJ válido de 14 dígitos: **{cnpjs_validos_obras}/{n_obras}** ({_fmt_num(cnpjs_validos_obras / n_obras * 100.0 if n_obras else 0.0)}%).
- Lacuna de detalhamento contábil: **{lacuna_emp}** obras ({_fmt_num(lacuna_emp / n_obras * 100.0 if n_obras else 0.0)}%) não possuem notas de empenho detalhadas na API; **{lacuna_pag}** obras ({_fmt_num(lacuna_pag / n_obras * 100.0 if n_obras else 0.0)}%) não possuem ordens de pagamento reais (utilizando fallback por medição física apenas na visão do painel).

### 1.3 Auditoria Aritmética: Variação Contratual Acumulada vs. Aditivos Contratuais Formais

- Divergências aritméticas (`|valorOriginal + valorAditivos - valorContratualVigente| > R$ 1,00`): **{inconsistencias_arit}** contratos.
- **Variação Contratual Acumulada** total (`valorContratualVigente - valorOriginal`): **{_fmt_brl(variacao_total)}**.
- Soma de **Aditivos Contratuais** formais listados (`sum(vlAditivo)`): **{_fmt_brl(aditivos_listados_total)}**.
- Diferença (apostilamentos, reajustes de saldo ou aditivos não listados individualmente): **{_fmt_brl(diferenca_var_adi)}**.
- Contratos com variação financeira positiva sem nenhum aditivo formal listado: **{contratos_variacao_sem_aditivos}**; contratos com diferença > R$ 1,00 entre variação acumulada e soma dos aditivos listados: **{contratos_diferenca_aditivos}**.
"""
    volumetria = {
        "bairros": len(bairros),
        "bairros_residenciais": len(bairros_residenciais),
        "bairros_especiais": len(bairros_especiais),
        "prefeituras_bairro": len(prefeituras),
        "obras": n_obras,
        "fichas": len(fichas),
        "empreiteiras": len(empreiteiras),
        "obras_com_empenhos": n_emp_obras,
        "obras_com_liquidacoes": n_liq_obras,
        "obras_com_pagamentos": n_pag_obras,
        "obras_com_aditivos": n_adi_obras,
        "tx_empenhos": tx_emp,
        "tx_liquidacoes": tx_liq,
        "tx_pagamentos": tx_pag,
        "tx_aditivos": tx_adi,
    }
    comparacao_aditivos = {
        "variacao_contratual_acumulada_total": variacao_total,
        "aditivos_formais_listados_total": aditivos_listados_total,
        "diferenca_total": diferenca_var_adi,
        "contratos_variacao_sem_aditivos_listados": contratos_variacao_sem_aditivos,
        "contratos_diferenca_aditivos": contratos_diferenca_aditivos,
    }
    return texto, {"volumetria": volumetria, "comparacao_aditivos": comparacao_aditivos}


def _construir_secao_2(
    index_data: dict[str, Any],
    fichas: dict[str, dict[str, Any]],
    censo: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Constrói a Seção 2: Distribuições Univariadas das Variáveis Brutas."""
    bairros_res = [
        b for b in index_data.get("bairros", []) if not b.get("is_zona_especial_nao_residencial")
    ]
    obras = index_data.get("obras", [])
    empreiteiras = index_data.get("concentracao_empreiteiras", [])

    # 2.1 Censo 2022 (variáveis brutas diretamente do catálogo IBGE quando disponível, sem imputação por contiguidade)
    censo_bruto = [
        v
        for v in censo.values()
        if isinstance(v, dict)
        and not v.get("is_zona_especial_nao_residencial")
        and not v.get("vulnerabilidade_estimada_contiguidade")
    ]
    fonte_censo = censo_bruto if censo_bruto else bairros_res
    censo_stats = [
        ("População residente (Censo 2022)", _resumo_univariado([parse_float(b.get("populacao")) for b in fonte_censo]), False),
        ("% Esgoto inadequado", _resumo_univariado([parse_float(b.get("pct_esgoto_inadequado")) for b in fonte_censo]), False),
        ("% Água inadequada", _resumo_univariado([parse_float(b.get("pct_agua_inadequada")) for b in fonte_censo]), False),
        ("% Analfabetismo (15+ anos)", _resumo_univariado([parse_float(b.get("pct_analfabetismo_15mais")) for b in fonte_censo]), False),
    ]

    # 2.2 Contratos (variáveis brutas)
    prazos_orig = []
    prazos_atual = []
    qtd_aditivos = []
    for o in obras:
        f = fichas.get(str(o.get("id", "")), {})
        vig = f.get("vigencia") or {}
        po = _parse_int_seguro(vig.get("prazoOriginal"))
        pa = _parse_int_seguro(vig.get("prazoAtualizado"))
        if po is not None:
            prazos_orig.append(po)
        if pa is not None:
            prazos_atual.append(pa)
        qtd_aditivos.append(float(len(f.get("aditivos") or [])))

    contratos_stats = [
        ("Valor Original Contratado", _resumo_univariado([parse_float(o.get("valorOriginal")) for o in obras]), True),
        ("Valor Contratual Vigente", _resumo_univariado([parse_float(o.get("valorContratualVigente")) for o in obras]), True),
        ("Variação Contratual Acumulada", _resumo_univariado([parse_float(o.get("valorAditivos")) for o in obras]), True),
        ("% Execução Física (fonte oficial)", _resumo_univariado([parse_float(o.get("percentualExecutado")) for o in obras]), False),
        ("Prazo Original (dias)", _resumo_univariado(prazos_orig), False),
        ("Prazo Atualizado (dias)", _resumo_univariado(prazos_atual), False),
        ("Qtd. Aditivos Formais por Contrato", _resumo_univariado(qtd_aditivos), False),
    ]

    # 2.3 Funil de Execução Financeira estritamente sobre subamostra contábil verificada (sem fallback)
    vals_emp_obra: list[float] = []
    vals_liq_obra: list[float] = []
    vals_pag_obra: list[float] = []
    vals_emp_tx: list[float] = []
    vals_liq_tx: list[float] = []
    vals_pag_tx: list[float] = []
    vals_adi_tx: list[float] = []

    emp_por_ano: Counter[int] = Counter()
    liq_por_ano: Counter[int] = Counter()
    pag_por_ano: Counter[int] = Counter()
    adi_por_ano: Counter[int] = Counter()

    for o in obras:
        f = fichas.get(str(o.get("id", "")), {})
        emps = f.get("empenhos") or []
        liqs = f.get("liquidacoes") or []
        pags = f.get("pagamentos") or []
        adis = f.get("aditivos") or []

        if emps:
            soma_e = sum(parse_float(x.get("valEmpenhado")) for x in emps)
            vals_emp_obra.append(soma_e)
            for x in emps:
                vals_emp_tx.append(parse_float(x.get("valEmpenhado")))
                ym = _extrair_ano_mes(x.get("dataEmpenho"))
                if ym:
                    emp_por_ano[ym[0]] += 1
        if liqs:
            soma_l = sum(parse_float(x.get("valLiqLiquidacao")) for x in liqs)
            vals_liq_obra.append(soma_l)
            for x in liqs:
                vals_liq_tx.append(parse_float(x.get("valLiqLiquidacao")))
                ym = _extrair_ano_mes(x.get("dataLiquidacao"))
                if ym:
                    liq_por_ano[ym[0]] += 1
        if pags:
            soma_p = sum(parse_float(x.get("pago")) for x in pags)
            vals_pag_obra.append(soma_p)
            for x in pags:
                vals_pag_tx.append(parse_float(x.get("pago")))
                ym = _extrair_ano_mes(x.get("dataPagamento"))
                if ym:
                    pag_por_ano[ym[0]] += 1
        for a in adis:
            vals_adi_tx.append(parse_float(a.get("vlAditivo")))
            ym = _extrair_ano_mes(a.get("dtAssinatura"))
            if ym:
                adi_por_ano[ym[0]] += 1

    funil_stats = [
        ("Valor Empenhado Real (subamostra com notas)", _resumo_univariado(vals_emp_obra), True),
        ("Valor Liquidado Real (subamostra com notas)", _resumo_univariado(vals_liq_obra), True),
        ("Valor Pago Real (subamostra com ordens)", _resumo_univariado(vals_pag_obra), True),
        ("Transação Individual: Empenho", _resumo_univariado(vals_emp_tx), True),
        ("Transação Individual: Liquidação", _resumo_univariado(vals_liq_tx), True),
        ("Transação Individual: Pagamento", _resumo_univariado(vals_pag_tx), True),
        ("Transação Individual: Aditivo Formal", _resumo_univariado(vals_adi_tx), True),
    ]

    # 2.4 Empreiteiras & Concentração de Mercado
    vals_emp_credor = [parse_float(e.get("valorTotalContratado")) for e in empreiteiras]
    obras_emp_credor = [float(e.get("totalObras") or 0) for e in empreiteiras]
    conc = _calcular_concentracao_mercado(vals_emp_credor)
    credores_stats = [
        ("Valor Contratado por Empreiteira", _resumo_univariado(vals_emp_credor), True),
        ("Qtd. de Obras por Empreiteira", _resumo_univariado(obras_emp_credor), False),
    ]

    # 2.5 Coortes mutuamente exclusivas de Mandato Municipal + Datas exatas
    coortes_ordem = [
        "2021-2024 exclusivo",
        "2021-2024 ∩ 2025-2028",
        "2025-2028 exclusivo",
        "Sem mandato definido",
    ]
    coortes_count: dict[str, int] = {k: 0 for k in coortes_ordem}
    coortes_valor: dict[str, float] = {k: 0.0 for k in coortes_ordem}
    for o in obras:
        coorte = _classificar_coorte_mandato(o.get("mandatos"))
        coortes_count[coorte] += 1
        coortes_valor[coorte] += parse_float(o.get("valorContratualVigente"))

    linhas_coortes = [
        "| Coorte Mutuamente Exclusiva | Contratos | % Contratos | Valor Contratual Vigente |",
        "|---|---:|---:|---:|",
    ]
    for c in coortes_ordem:
        cnt = coortes_count[c]
        if cnt == 0 and c == "Sem mandato definido":
            continue
        pct = cnt / len(obras) * 100.0 if obras else 0.0
        linhas_coortes.append(f"| {c} | {cnt} | {_fmt_num(pct)}% | {_fmt_brl(coortes_valor[c])} |")

    anos_todos = sorted(set(emp_por_ano) | set(liq_por_ano) | set(pag_por_ano) | set(adi_por_ano))
    linhas_anos = [
        "| Ano da Transação | Empenhos | Liquidações | Pagamentos | Aditivos |",
        "|---:|---:|---:|---:|---:|",
    ]
    for ano in anos_todos:
        linhas_anos.append(
            f"| {ano} | {emp_por_ano[ano]} | {liq_por_ano[ano]} | {pag_por_ano[ano]} | {adi_por_ano[ano]} |"
        )

    # 2.6 Frequências categóricas brutas
    def _tabela_freq(titulo: str, contador: Counter[str], limite: int = 12) -> str:
        total = sum(contador.values())
        linhas = [f"#### {titulo}", "", "| Categoria | Contagem | % |", "|---|---:|---:|"]
        for cat, cnt in contador.most_common(limite):
            linhas.append(f"| {cat} | {cnt} | {_fmt_num(cnt / total * 100.0 if total else 0.0)}% |")
        if len(contador) > limite:
            linhas.append(f"| *(demais {len(contador) - limite} categorias)* | {sum(v for _, v in contador.most_common()[limite:])} | — |")
        return "\n".join(linhas)

    ug_cnt = Counter(str(o.get("unidadeGestora") or "N/I") for o in obras)
    sit_cnt = Counter(str(o.get("situacao") or "N/I") for o in obras)
    fonte_cnt: Counter[str] = Counter()
    subacao_cnt: Counter[str] = Counter()
    classif_cnt: Counter[str] = Counter()
    tipo_adi_cnt: Counter[str] = Counter()
    for f in fichas.values():
        for dot in f.get("dotacao") or []:
            fonte_cnt[str(dot.get("fonteRecurso") or "N/I")] += 1
            subacao_cnt[str(dot.get("subacao") or "N/I")] += 1
            classif_cnt[str(dot.get("classificacao") or "N/I")] += 1
        for adi in f.get("aditivos") or []:
            tipo_adi_cnt[str(adi.get("dsTipoAlteracao") or "N/I")] += 1

    freq_blocos = "\n\n".join(
        [
            _tabela_freq("Unidade Gestora (`unidadeGestora`)", ug_cnt),
            _tabela_freq("Situação Contratual (`situacao`)", sit_cnt),
            _tabela_freq("Fonte de Recurso (`dotacao.fonteRecurso`)", fonte_cnt),
            _tabela_freq("Subação Orçamentária (`dotacao.subacao`)", subacao_cnt),
            _tabela_freq("Classificação / Elemento (`dotacao.classificacao`)", classif_cnt),
            _tabela_freq("Tipo de Alteração de Aditivo (`dsTipoAlteracao`)", tipo_adi_cnt),
        ]
    )

    total_emp_real = sum(vals_emp_obra)
    total_liq_real = sum(vals_liq_obra)
    total_pag_real = sum(vals_pag_obra)

    texto = f"""## Seção 2: Distribuições Univariadas das Variáveis Brutas

### 2.1 Variáveis Brutas do Censo 2022 (Bairros Oficiais Residenciais, N={len(bairros_res)})

{_tabela_univariada_md(censo_stats)}

### 2.2 Variáveis Brutas dos Contratos (N={len(obras)})

{_tabela_univariada_md(contratos_stats)}

### 2.3 Funil de Execução Financeira (Subamostra Contábil Verificada — Sem Fallbacks Sintéticos)

- Obras com empenhos reais: **N = {len(vals_emp_obra)}** (Total: **{_fmt_brl(total_emp_real)}**)
- Obras com liquidações reais: **N = {len(vals_liq_obra)}** (Total: **{_fmt_brl(total_liq_real)}**)
- Obras com pagamentos reais: **N = {len(vals_pag_obra)}** (Total: **{_fmt_brl(total_pag_real)}**)

{_tabela_univariada_md(funil_stats)}

### 2.4 Empreiteiras e Concentração de Mercado (N={len(empreiteiras)})

{_tabela_univariada_md(credores_stats)}

- **Índice de Gini**: `{_fmt_num(conc['gini'], 4)}`
- **CR1 / CR5 / CR10 / CR20**: `{_fmt_num(conc['cr1'])}%` / `{_fmt_num(conc['cr5'])}%` / `{_fmt_num(conc['cr10'])}%` / `{_fmt_num(conc['cr20'])}%`
- **HHI (Herfindahl–Hirschman Index)**: `{_fmt_num(conc['hhi'], 1)}`

### 2.5 Comparação Temporal por Coortes Mutuamente Exclusivas de Mandato e Datas de Transação

{chr(10).join(linhas_coortes)}

{chr(10).join(linhas_anos)}

### 2.6 Frequências de Variáveis Categóricas Brutas

{freq_blocos}
"""
    coortes_ret = {k: v for k, v in coortes_count.items() if v > 0 or k != "Sem mandato definido"}
    subamostra_ret = {
        "n_empenhos": len(vals_emp_obra),
        "total_empenhado_real": total_emp_real,
        "n_liquidacoes": len(vals_liq_obra),
        "total_liquidado_real": total_liq_real,
        "n_pagamentos": len(vals_pag_obra),
        "total_pago_real": total_pag_real,
    }
    return texto, {
        "coortes_mandato": coortes_ret,
        "subamostra_contabil": subamostra_ret,
        "concentracao_mercado": conc,
    }


def _construir_secao_3(
    index_data: dict[str, Any],
    fichas: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    """Constrói a Seção 3: Varredura Multivariada Agnóstica (Pearson, Spearman e eta²)."""
    bairros_res = [
        b for b in index_data.get("bairros", []) if not b.get("is_zona_especial_nao_residencial")
    ]
    df_bairros = pd.DataFrame(
        [
            {
                "populacao": parse_float(b.get("populacao")),
                "pct_esgoto_inadequado": parse_float(b.get("pct_esgoto_inadequado")),
                "pct_agua_inadequada": parse_float(b.get("pct_agua_inadequada")),
                "pct_analfabetismo_15mais": parse_float(b.get("pct_analfabetismo_15mais")),
                "totalObras": parse_float(b.get("totalObras")),
                "valorTotal": parse_float(b.get("valorTotal")),
                "valorPago": parse_float(b.get("valorPago")),
            }
            for b in bairros_res
        ]
    )
    cols_bairros = list(df_bairros.columns) if not df_bairros.empty else []
    corrs_bairros = _correlacoes_pares(df_bairros, cols_bairros)

    linhas_obras = []
    for o in index_data.get("obras", []):
        oid = str(o.get("id", ""))
        f = fichas.get(oid, {})
        vig = f.get("vigencia") or {}
        emps = f.get("empenhos") or []
        liqs = f.get("liquidacoes") or []
        pags = f.get("pagamentos") or []
        linhas_obras.append(
            {
                "valorOriginal": parse_float(o.get("valorOriginal")),
                "valorContratualVigente": parse_float(o.get("valorContratualVigente")),
                "valorAditivos": parse_float(o.get("valorAditivos")),
                "deltaPercentualValor": parse_float(o.get("deltaPercentualValor")),
                "percentualExecutado": parse_float(o.get("percentualExecutado")),
                "prazoOriginal": _parse_int_seguro(vig.get("prazoOriginal")),
                "prazoAtualizado": _parse_int_seguro(vig.get("prazoAtualizado")),
                "qtd_aditivos": float(len(f.get("aditivos") or [])),
                "valorEmpenhadoReal": sum(parse_float(x.get("valEmpenhado")) for x in emps) if emps else np.nan,
                "valorLiquidadoReal": sum(parse_float(x.get("valLiqLiquidacao")) for x in liqs) if liqs else np.nan,
                "valorPagoReal": sum(parse_float(x.get("pago")) for x in pags) if pags else np.nan,
                "unidadeGestora": str(o.get("unidadeGestora") or "N/I"),
                "situacao": str(o.get("situacao") or "N/I"),
                "coorte_mandato": _classificar_coorte_mandato(o.get("mandatos")),
                "fonteRecurso": str(((f.get("dotacao") or [{}])[0]).get("fonteRecurso") or "N/I"),
            }
        )
    df_obras = pd.DataFrame(linhas_obras)
    cols_obras_num = [
        "valorOriginal",
        "valorContratualVigente",
        "valorAditivos",
        "deltaPercentualValor",
        "percentualExecutado",
        "prazoOriginal",
        "prazoAtualizado",
        "qtd_aditivos",
        "valorEmpenhadoReal",
        "valorLiquidadoReal",
        "valorPagoReal",
    ]
    corrs_obras = _correlacoes_pares(df_obras, cols_obras_num) if not df_obras.empty else []

    def _formatar_corrs(corrs: list[dict[str, Any]], titulo: str) -> str:
        fortes = [c for c in corrs if abs(c["pearson"]) >= 0.20 or abs(c["spearman"]) >= 0.20]
        nulas = [c for c in corrs if abs(c["pearson"]) < 0.10 and abs(c["spearman"]) < 0.10]
        blocos = [f"#### {titulo} — Associações Relevantes (|r| ou |ρ| ≥ 0,20): {len(fortes)} pares"]
        if fortes:
            blocos.append("| Variável 1 | Variável 2 | N | Pearson (r) | Spearman (ρ) |")
            blocos.append("|---|---|---:|---:|---:|")
            for c in fortes[:25]:
                blocos.append(
                    f"| `{c['var1']}` | `{c['var2']}` | {c['n']} | {_fmt_num(c['pearson'], 3)} | {_fmt_num(c['spearman'], 3)} |"
                )
        blocos.append(f"\n#### {titulo} — Ausências de Correlação (|r| e |ρ| < 0,10): {len(nulas)} pares")
        if nulas:
            blocos.append("| Variável 1 | Variável 2 | N | Pearson (r) | Spearman (ρ) |")
            blocos.append("|---|---|---:|---:|---:|")
            for c in nulas[:15]:
                blocos.append(
                    f"| `{c['var1']}` | `{c['var2']}` | {c['n']} | {_fmt_num(c['pearson'], 3)} | {_fmt_num(c['spearman'], 3)} |"
                )
        return "\n".join(blocos)

    # Poder explicativo eta²
    cats = ["unidadeGestora", "situacao", "coorte_mandato", "fonteRecurso"]
    nums_eta = ["valorContratualVigente", "valorAditivos", "percentualExecutado", "prazoAtualizado"]
    eta_rows: list[dict[str, Any]] = []
    if not df_obras.empty:
        for cat in cats:
            for num in nums_eta:
                eta = _eta_quadrado(df_obras[cat], df_obras[num])
                if eta is not None:
                    eta_rows.append({"categorica": cat, "numerica": num, "eta2": eta})
    eta_rows.sort(key=lambda x: x["eta2"], reverse=True)

    linhas_eta = [
        "| Variável Categórica | Métrica Numérica | Variância Explicada (η²) |",
        "|---|---|---:|",
    ]
    for item in eta_rows:
        linhas_eta.append(
            f"| `{item['categorica']}` | `{item['numerica']}` | {_fmt_num(item['eta2'], 4)} |"
        )

    texto = f"""## Seção 3: Varredura Multivariada Agnóstica

### 3.1 Correlações Todos-contra-Todos — Nível Bairro Oficial (Residenciais)

{_formatar_corrs(corrs_bairros, "Bairros Oficiais")}

### 3.2 Correlações Todos-contra-Todos — Nível Obra Pública

{_formatar_corrs(corrs_obras, "Obras Públicas")}

### 3.3 Poder Explicativo de Variáveis Categóricas Brutas (η²)

{chr(10).join(linhas_eta)}
"""
    return texto, {
        "correlacoes_bairros_count": len(corrs_bairros),
        "correlacoes_obras_count": len(corrs_obras),
        "eta2_count": len(eta_rows),
    }


def _construir_secao_4(
    index_data: dict[str, Any],
    fichas: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    """Constrói a Seção 4: Outliers Matemáticos e Agrupamentos Naturais (Clustering)."""
    bairros_res = [
        b for b in index_data.get("bairros", []) if not b.get("is_zona_especial_nao_residencial")
    ]
    obras = index_data.get("obras", [])
    empreiteiras = index_data.get("concentracao_empreiteiras", [])

    # Outliers nas 5 dimensões solicitadas
    out_bairros = _detectar_outliers_metrica(
        [(str(b.get("nome")), parse_float(b.get("valorTotal"))) for b in bairros_res]
    )
    out_obras = _detectar_outliers_metrica(
        [(f"{o.get('nuContratoSigef')} ({o.get('unidadeGestora')})", parse_float(o.get("valorContratualVigente"))) for o in obras]
    )
    aditivos_itens = []
    pagamentos_itens = []
    for o in obras:
        f = fichas.get(str(o.get("id", "")), {})
        contrato = str(o.get("nuContratoSigef") or o.get("id"))
        for a in f.get("aditivos") or []:
            aditivos_itens.append((f"{contrato} Ad.{a.get('nuAditivo')}", parse_float(a.get("vlAditivo"))))
        for p in f.get("pagamentos") or []:
            pagamentos_itens.append((f"{contrato} {p.get('ordBancaria') or ''}".strip(), parse_float(p.get("pago"))))

    out_aditivos = _detectar_outliers_metrica(aditivos_itens)
    out_pagamentos = _detectar_outliers_metrica(pagamentos_itens)
    out_empreiteiras = _detectar_outliers_metrica(
        [(str(e.get("razaoSocial")), parse_float(e.get("valorTotalContratado"))) for e in empreiteiras]
    )

    def _bloco_outlier(titulo: str, res: dict[str, Any]) -> str:
        z_cnt = len(res["outliers_z"])
        iqr_cnt = len(res["outliers_iqr"])
        linhas = [
            f"#### {titulo}",
            f"- Outliers `|Z| > 3σ`: **{z_cnt}** (limiar: {_fmt_brl(res['limiar_z3']) if res['limiar_z3'] is not None else 'N/A'})",
            f"- Outliers `> Q3 + 1,5×IQR`: **{iqr_cnt}** (limiar: {_fmt_brl(res['limiar_iqr']) if res['limiar_iqr'] is not None else 'N/A'})",
        ]
        if res["outliers_z"]:
            linhas.extend(["", "**Top Outliers `|Z| > 3σ`:**", "", "| Entidade | Valor | Z-score |", "|---|---:|---:|"])
            for item in res["outliers_z"][:5]:
                linhas.append(f"| {item['rotulo']} | {_fmt_brl(item['valor'])} | {_fmt_num(item['z'])} |")
        if res["outliers_iqr"]:
            linhas.extend(["", "**Top Outliers `> Q3 + 1,5×IQR`:**", "", "| Entidade | Valor | Z-score |", "|---|---:|---:|"])
            for item in res["outliers_iqr"][:5]:
                linhas.append(f"| {item['rotulo']} | {_fmt_brl(item['valor'])} | {_fmt_num(item['z'])} |")
        return "\n".join(linhas)

    # Clustering K-means não-supervisionado
    df_b = pd.DataFrame(
        [
            {
                "populacao": parse_float(b.get("populacao")),
                "pct_esgoto_inadequado": parse_float(b.get("pct_esgoto_inadequado")),
                "pct_analfabetismo_15mais": parse_float(b.get("pct_analfabetismo_15mais")),
                "valorTotal": parse_float(b.get("valorTotal")),
            }
            for b in bairros_res
        ]
    )
    feats_b = ["populacao", "pct_esgoto_inadequado", "pct_analfabetismo_15mais", "valorTotal"]
    cl_bairros = _kmeans_padronizado(df_b, feats_b, k=4) if not df_b.empty else {"n": 0, "k": 0, "perfis": []}

    df_o = pd.DataFrame(
        [
            {
                "valorContratualVigente": parse_float(o.get("valorContratualVigente")),
                "valorAditivos": parse_float(o.get("valorAditivos")),
                "percentualExecutado": parse_float(o.get("percentualExecutado")),
            }
            for o in obras
        ]
    )
    feats_o = ["valorContratualVigente", "valorAditivos", "percentualExecutado"]
    cl_obras = _kmeans_padronizado(df_o, feats_o, k=4) if not df_o.empty else {"n": 0, "k": 0, "perfis": []}

    def _tabela_clusters(titulo: str, cl: dict[str, Any], feats: list[str]) -> str:
        if not cl["perfis"]:
            return f"#### {titulo}\n\nDados insuficientes para agrupamento."
        header = "| Cluster | N | % | " + " | ".join(f"Média `{f}`" for f in feats) + " |"
        sep = "|---|---:|---:|" + "|".join("---:" for _ in feats) + "|"
        rows = [f"#### {titulo} (k={cl['k']}, N={cl['n']})", "", header, sep]
        for p in cl["perfis"]:
            vals_str = " | ".join(_fmt_num(p["medias"][f]) for f in feats)
            rows.append(f"| Cluster {p['cluster']} | {p['n']} | {_fmt_num(p['pct'])}% | {vals_str} |")
        return "\n".join(rows)

    texto = f"""## Seção 4: Outliers e Agrupamentos Naturais

### 4.1 Detecção Matemática de Outliers (|Z| > 3σ e > Q3 + 1,5×IQR)

{_bloco_outlier("Bairros Oficiais (Valor Total Alocado)", out_bairros)}

{_bloco_outlier("Obras Públicas (Valor Contratual Vigente)", out_obras)}

{_bloco_outlier("Aditivos Contratuais Individuais", out_aditivos)}

{_bloco_outlier("Pagamentos Individuais (Ordens Bancárias)", out_pagamentos)}

{_bloco_outlier("Empreiteiras (Valor Total Contratado)", out_empreiteiras)}

### 4.2 Agrupamento Não-Supervisionado (K-means sobre Z-scores)

{_tabela_clusters("Perfis Naturais de Bairros Oficiais Residenciais", cl_bairros, feats_b)}

{_tabela_clusters("Perfis Naturais de Obras Públicas", cl_obras, feats_o)}
"""
    return texto, {
        "outliers_z3_obras": len(out_obras["outliers_z"]),
        "clusters_bairros": cl_bairros["k"],
        "clusters_obras": cl_obras["k"],
    }


def _construir_secao_5(
    index_data: dict[str, Any],
    fichas: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    """Constrói a Seção 5: Auditoria Estatística das Variáveis de Domínio."""
    obras = index_data.get("obras", [])
    bairros_res = [
        b for b in index_data.get("bairros", []) if not b.get("is_zona_especial_nao_residencial")
    ]
    prefeituras = index_data.get("prefeituras_bairro", [])

    # 5.1 Semáforo da Obra e decomposição de gatilhos normalizados por regra
    def _normalizar_gatilho_semaforo(motivo: str) -> str:
        m = motivo.lower()
        if "paralisad" in m or "suspens" in m or "rescind" in m:
            return "Situação crítica (paralisada/suspensa/rescindida)"
        if "prazo" in m or "vencid" in m:
            return "Prazo atualizado vencido sem 100% de execução"
        if "aditivo" in m or "25%" in m:
            return "Aditivo de valor superior a 25%"
        if "90 dias" in m or "sem liquidação" in m or "sem pagamento" in m:
            return "Sem liquidação/pagamento há mais de 90 dias"
        return motivo

    sem_status_cnt: Counter[str] = Counter()
    motivos_vermelho_cnt: Counter[str] = Counter()
    for o in obras:
        sem = o.get("semaforo") or {}
        st = str(sem.get("status") or "N/I")
        sem_status_cnt[st] += 1
        if st == "VERMELHO":
            gatilhos_obra = {_normalizar_gatilho_semaforo(str(m)) for m in (sem.get("motivos") or [])}
            for g in gatilhos_obra:
                motivos_vermelho_cnt[g] += 1

    linhas_sem = [
        "| Classificação (Semáforo da Obra) | Qtd. Obras | % |",
        "|---|---:|---:|",
    ]
    for st, cnt in sem_status_cnt.most_common():
        linhas_sem.append(f"| {st} | {cnt} | {_fmt_num(cnt / len(obras) * 100.0 if obras else 0.0)}% |")

    linhas_motivos = [
        "| Gatilho / Regra Crítica (Vermelho) | Obras Atingidas |",
        "|---|---:|",
    ]
    for mot, cnt in motivos_vermelho_cnt.most_common():
        linhas_motivos.append(f"| {mot} | {cnt} |")

    # 5.2 Localizadas vs Escopo Cidade (Não-Localizado)
    loc = [o for o in obras if o.get("nivel") != "Escopo Cidade (Não-Localizado)"]
    nao_loc = [o for o in obras if o.get("nivel") == "Escopo Cidade (Não-Localizado)"]
    loc_emp = sum(1 for o in loc if fichas.get(str(o.get("id", "")), {}).get("empenhos"))
    nloc_emp = sum(1 for o in nao_loc if fichas.get(str(o.get("id", "")), {}).get("empenhos"))

    val_loc = [parse_float(o.get("valorContratualVigente")) for o in loc]
    val_nloc = [parse_float(o.get("valorContratualVigente")) for o in nao_loc]
    st_loc = _resumo_univariado(val_loc)
    st_nloc = _resumo_univariado(val_nloc)

    # 5.3 Tema da Obra e Nível de Alocação Territorial
    tema_cnt: Counter[str] = Counter(str(o.get("tema") or "N/I") for o in obras)
    tema_val: defaultdict[str, float] = defaultdict(float)
    nivel_cnt: Counter[str] = Counter(str(o.get("nivel") or "N/I") for o in obras)
    nivel_val: defaultdict[str, float] = defaultdict(float)
    for o in obras:
        v = parse_float(o.get("valorContratualVigente"))
        tema_val[str(o.get("tema") or "N/I")] += v
        nivel_val[str(o.get("nivel") or "N/I")] += v

    linhas_tema = ["| Tema da Obra | Contratos | Valor Vigente Total |", "|---|---:|---:|"]
    for t, cnt in tema_cnt.most_common():
        linhas_tema.append(f"| {t} | {cnt} | {_fmt_brl(tema_val[t])} |")

    linhas_nivel = ["| Nível de Alocação Territorial | Contratos | Valor Vigente Total |", "|---|---:|---:|"]
    for nv, cnt in nivel_cnt.most_common():
        linhas_nivel.append(f"| {nv} | {cnt} | {_fmt_brl(nivel_val[nv])} |")

    # 5.4 Índice de Vulnerabilidade do Bairro vs Investimento por Habitante (excluindo Zonas Especiais)
    df_vuln = pd.DataFrame(
        [
            {
                "ivs": parse_float(b.get("indice_vulnerabilidade")),
                "inv_hab": parse_float(b.get("investimentoPorHabitante")),
                "inv_hab_pago": parse_float(b.get("investimentoPorHabitantePago")),
            }
            for b in bairros_res
        ]
    )
    r_ivs = rho_ivs = None
    if len(df_vuln) >= 3 and df_vuln["ivs"].nunique() > 1 and df_vuln["inv_hab"].nunique() > 1:
        r_ivs = float(df_vuln["ivs"].corr(df_vuln["inv_hab"], method="pearson"))
        rho_ivs = float(df_vuln["ivs"].corr(df_vuln["inv_hab"], method="spearman"))

    linhas_pb = [
        "| Prefeitura-Bairro | População | Índice Vulnerabilidade | Obras | Valor Total | Invest./Hab |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for pb in sorted(prefeituras, key=lambda x: parse_float(x.get("indice_vulnerabilidade")), reverse=True):
        linhas_pb.append(
            f"| {pb.get('nome')} | {int(parse_float(pb.get('populacao_total')))} | "
            f"{_fmt_num(parse_float(pb.get('indice_vulnerabilidade')))} | {pb.get('totalObras', 0)} | "
            f"{_fmt_brl(parse_float(pb.get('valorTotal')))} | {_fmt_brl(parse_float(pb.get('investimentoPorHabitante')))} |"
        )

    # Cruzamento Prefeitura-Bairro vs. Bairro Oficial (bairros residenciais agrupados por PB)
    bairros_por_pb: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for b in bairros_res:
        bairros_por_pb[str(b.get("prefeitura_bairro") or "N/I")].append(b)

    linhas_cruzamento = [
        "| Prefeitura-Bairro | Bairros Residenciais | Bairros sem Obras | Mediana Invest./Hab (Bairros) | Máx Invest./Hab (Bairro) | Mediana Vulnerabilidade |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for pb_nome in sorted(bairros_por_pb):
        grupo = bairros_por_pb[pb_nome]
        sem_obras = sum(1 for b in grupo if int(parse_float(b.get("totalObras"))) == 0)
        invs = [parse_float(b.get("investimentoPorHabitante")) for b in grupo]
        ivss = [parse_float(b.get("indice_vulnerabilidade")) for b in grupo]
        linhas_cruzamento.append(
            f"| {pb_nome} | {len(grupo)} | {sem_obras} | "
            f"{_fmt_brl(float(np.median(invs)))} | {_fmt_brl(float(np.max(invs)))} | "
            f"{_fmt_num(float(np.median(ivss)))} |"
        )

    texto = f"""## Seção 5: Auditoria Estatística das Variáveis de Domínio

### 5.1 Decomposição dos Gatilhos do Semáforo da Obra

{chr(10).join(linhas_sem)}

{chr(10).join(linhas_motivos)}

### 5.2 Comparação: Obras Localizadas vs. Escopo Cidade (Não-Localizado)

| Recorte | Qtd. | Média Valor Vigente | Mediana Valor Vigente | Com Notas de Empenho |
|---|---:|---:|---:|---:|
| Localizadas (`Pontual` / `Bairro` / `Regional (Prefeitura-Bairro)`) | {len(loc)} | {_fmt_brl(st_loc['mean'] or 0.0)} | {_fmt_brl(st_loc['p50'] or 0.0)} | {loc_emp} |
| Escopo Cidade (Não-Localizado) | {len(nao_loc)} | {_fmt_brl(st_nloc['mean'] or 0.0)} | {_fmt_brl(st_nloc['p50'] or 0.0)} | {nloc_emp} |

### 5.3 Distribuição por Tema da Obra e Nível de Alocação Territorial

{chr(10).join(linhas_tema)}

{chr(10).join(linhas_nivel)}

### 5.4 Índice de Vulnerabilidade do Bairro vs. Investimento por Habitante (Zonas Especiais Excluídas)

- Bairros Oficiais residenciais analisados: **N = {len(bairros_res)}** (Zonas Especiais Não-Residenciais excluídas do cálculo per capita).
- Correlação entre `indice_vulnerabilidade` e `investimentoPorHabitante`: Pearson `r = {_fmt_num(r_ivs, 3)}`, Spearman `ρ = {_fmt_num(rho_ivs, 3)}`.

{chr(10).join(linhas_pb)}

#### Cruzamento Prefeitura-Bairro × Bairros Oficiais Residenciais

{chr(10).join(linhas_cruzamento)}
"""
    return texto, {
        "semaforo": dict(sem_status_cnt),
        "localizadas": len(loc),
        "nao_localizadas": len(nao_loc),
        "bairros_residenciais_ivs": len(bairros_res),
    }


def executar_eda_agnostica(
    data_dir: Path = DEFAULT_DATA_DIR,
    censo_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Executa a Análise Exploratória de Dados Agnóstica offline sobre o acervo reconciliado.

    Sumário:
        Lê os artefatos estáticos locais e gera o relatório completo em Markdown em cinco seções.

    Descrição Estendida:
        Opera 100% offline sobre `index.json`, `obras/*.json` e o catálogo censitário do IBGE
        sem realizar chamadas de rede ou alterar arquivos de produção.

    Argumentos:
        data_dir: Diretório raiz dos dados estáticos (`public/data`).
        censo_path: Caminho opcional para `censo_2022_salvador_bairros.json`.
        output_path: Caminho opcional onde salvar o relatório Markdown gerado.

    Retornos:
        Dicionário contendo `report_markdown` e métricas resumidas para auditoria.

    Erros:
        Lança `FileNotFoundError` se `index.json` não existir em `data_dir`.
    """
    censo_efetivo = censo_path or DEFAULT_CENSO_PATH
    acervo = _carregar_acervo(data_dir, censo_efetivo)
    index_data = acervo["index"]
    fichas = acervo["fichas"]
    censo = acervo["censo"]

    sec1, meta1 = _construir_secao_1(index_data, fichas, censo)
    sec2, meta2 = _construir_secao_2(index_data, fichas, censo)
    sec3, meta3 = _construir_secao_3(index_data, fichas)
    sec4, meta4 = _construir_secao_4(index_data, fichas)
    sec5, meta5 = _construir_secao_5(index_data, fichas)

    cabecalho = (
        "# Relatório de Exploração Estatística Agnóstica (EDA) — Obras Públicas de Salvador\n\n"
        "> Execução 100% offline e determinística sobre o acervo local reconciliado, "
        "separando variáveis brutas das fontes oficiais (Seções 1–4) da auditoria empírica "
        "das variáveis derivadas de domínio (Seção 5).\n\n"
    )
    report_markdown = cabecalho + "\n".join([sec1, sec2, sec3, sec4, sec5])

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_markdown, encoding="utf-8")

    return {
        "report_markdown": report_markdown,
        "output_path": str(output_path) if output_path is not None else None,
        **meta1,
        **meta2,
        **meta3,
        **meta4,
        **meta5,
    }


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada CLI para gerar o relatório de EDA Agnóstica offline."""
    parser = argparse.ArgumentParser(
        description="Gera relatório técnico offline de Exploração Estatística Agnóstica (EDA)."
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--censo-path", type=Path, default=DEFAULT_CENSO_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)

    res = executar_eda_agnostica(
        data_dir=args.data_dir,
        censo_path=args.censo_path,
        output_path=args.output,
    )
    print(
        f"Relatório EDA gerado em '{args.output}' "
        f"({res['volumetria']['obras']} obras, {res['volumetria']['bairros']} bairros, "
        f"{res['volumetria']['empreiteiras']} empreiteiras)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

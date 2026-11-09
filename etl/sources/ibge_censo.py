"""Módulo de integração com os dados demográficos do Censo 2022 (IBGE).

Recupera os dados agregados por bairro de Salvador a partir da API SIDRA do IBGE
ou de arquivos locais consolidados para mapear população residente e vulnerabilidade.
"""

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

from etl.config import IBGE_SIDRA_POPULACAO_BAIRROS_SALVADOR
from etl.domain.territorio import (
    calcular_indice_vulnerabilidade_bairros,
    is_zona_especial_nao_residencial,
    normalizar_nome,
)

_REF_DIR = Path(__file__).resolve().parent.parent / "reference"

# Aliases ortográficos entre nomenclaturas do SIDRA IBGE e GeoSalvador
CENSO_ALIASES: dict[str, str] = {
    normalizar_nome("Nordeste de Amaralina"): normalizar_nome("Nordeste do Amaralina"),
    normalizar_nome("Centro Administrativo da Bahia"): normalizar_nome("Centro Administrativo da Bahia - CAB"),
    normalizar_nome("CAB"): normalizar_nome("Centro Administrativo da Bahia - CAB"),
    normalizar_nome("Ilha dos Frades"): normalizar_nome("Ilha dos Frades/Ilha de Santo Antônio"),
    normalizar_nome("Ilha dos Frades / Ilha de Santo Antônio"): normalizar_nome("Ilha dos Frades/Ilha de Santo Antônio"),
    normalizar_nome("Bom Jesus dos Passos"): normalizar_nome("Ilha de Bom Jesus dos Passos"),
    normalizar_nome("Ilha Bom Jesus dos Passos"): normalizar_nome("Ilha de Bom Jesus dos Passos"),
    normalizar_nome("Beiru / Tancredo Neves"): normalizar_nome("Beiru/Tancredo Neves"),
    normalizar_nome("Caixa D'Água"): normalizar_nome("Caixa D´Água"),
    normalizar_nome("Caixa D'água"): normalizar_nome("Caixa D´Água"),
    normalizar_nome("Vila Ruy Barbosa / Jardim Cruzeiro"): normalizar_nome("Vila Ruy Barbosa\\Jardim Cruzeiro"),
    normalizar_nome("Vila Ruy Barbosa \\ Jardim Cruzeiro"): normalizar_nome("Vila Ruy Barbosa\\Jardim Cruzeiro"),
}


def normalizar_registros_censo_2022(
    raw_sidra_rows: list[dict[str, Any]],
    bairros_nomes: Optional[list[str]] = None,
) -> dict[str, dict[str, Any]]:
    """Normaliza os registros do Censo 2022 do IBGE e calcula o índice de vulnerabilidade multidimensional.

    Sumário:
        Filtra a contagem populacional (D2C == '93' / MN == 'Pessoas'), aplica aliases oficiais,
        integra os sub-indicadores do Censo 2022 (esgotamento, água e analfabetismo) e executa
        o cálculo composto multidimensional por min-max (eliminando dicionários manuais).
    """
    censo_pop: dict[str, int] = {}
    censo_raw_names: dict[str, str] = {}
    for item in raw_sidra_rows:
        if not isinstance(item, dict):
            continue
        d2c = str(item.get("D2C") or "")
        mn = str(item.get("MN") or "")
        if d2c == "93" or mn == "Pessoas":
            raw_nome = str(item.get("D1N") or item.get("D2N") or "").strip()
            clean_nome = raw_nome.replace(" - Salvador - BA", "").strip()
            valor_str = str(item.get("V") or "0")
            try:
                pop = int(float(valor_str))
            except (ValueError, TypeError):
                pop = 0
            if clean_nome:
                norm = normalizar_nome(clean_nome)
                target_norm = CENSO_ALIASES.get(norm, norm)
                censo_pop[target_norm] = pop
                censo_pop[norm] = pop
                censo_raw_names[norm] = clean_nome
                censo_raw_names[target_norm] = clean_nome

    # Carrega a base de referência de sub-indicadores do Censo 2022
    ref_indicadores_path = _REF_DIR / "censo_2022_salvador_bairros.json"
    ref_indicadores: dict[str, dict[str, Any]] = {}
    if ref_indicadores_path.exists():
        try:
            with open(ref_indicadores_path, "r", encoding="utf-8") as f:
                raw_ref = json.load(f)
                ref_indicadores = {normalizar_nome(k): v for k, v in raw_ref.items()}
        except Exception:
            ref_indicadores = {}

    # Carrega a lista dos 171 Bairros Oficiais caso não seja fornecida
    if bairros_nomes is None:
        bairros_path = _REF_DIR / "geosalvador_bairros_real.geojson"
        if bairros_path.exists():
            try:
                with open(bairros_path, "r", encoding="utf-8") as f:
                    b_geo = json.load(f)
                    bairros_nomes = [
                        (feat.get("properties", {}).get("NM_BAIRRO") or feat.get("properties", {}).get("NOME_BAIRR") or "").strip()
                        for feat in b_geo.get("features", [])
                    ]
            except Exception:
                bairros_nomes = []
        else:
            bairros_nomes = []

    demografia_preliminar: dict[str, dict[str, Any]] = {}

    # Popula para cada bairro oficial
    for b_name in (bairros_nomes or []):
        if not b_name:
            continue
        norm = normalizar_nome(b_name)
        target_norm = CENSO_ALIASES.get(norm, norm)
        pop = censo_pop.get(target_norm, censo_pop.get(norm, 0))

        ref_entry = ref_indicadores.get(target_norm, ref_indicadores.get(norm, {}))

        demografia_preliminar[b_name] = {
            "populacao": pop if pop > 0 else int(ref_entry.get("populacao", 0)),
            "pct_esgoto_inadequado": ref_entry.get("pct_esgoto_inadequado"),
            "pct_agua_inadequada": ref_entry.get("pct_agua_inadequada"),
            "pct_analfabetismo_15mais": ref_entry.get("pct_analfabetismo_15mais"),
        }

    # Executa o cálculo multidimensional determinístico com min-max e contiguidade
    resultado = calcular_indice_vulnerabilidade_bairros(demografia_preliminar)

    # Garante que os nomes originais do SIDRA e aliases estejam no resultado
    for alias_orig, alias_canonico in CENSO_ALIASES.items():
        if alias_canonico in resultado and alias_orig not in resultado:
            resultado[alias_orig] = dict(resultado[alias_canonico])

    return resultado


def fetch_demografia_censo_2022() -> dict[str, dict[str, Any]]:
    """Recupera os dados de população e índice de vulnerabilidade dos bairros no Censo 2022.

    Sumário:
        Extrai população residente e indicadores socioeconômicos dos bairros de Salvador.

    Descrição Estendida:
        Consulta a API SIDRA do IBGE para obter a contagem populacional por bairro do município
        de Salvador (código IBGE 2927408) e normaliza os nomes para indexação unificada.
        Caso a conexão externa não esteja acessível, recorre à base consolidada do Censo 2022
        armazenada no módulo de referência de produção (`etl.reference.sample_data`).

    Argumentos:
        Nenhum.

    Retornos:
        Dicionário onde as chaves são os nomes dos bairros e os valores são dicionários com:
        - 'populacao': População residente do bairro no Censo 2022 (inteiro).
        - 'indice_vulnerabilidade': Métrica de 0.00 a 1.00 de vulnerabilidade socioeconômica (float).

    Erros:
        Não interrompe o fluxo caso ocorra erro de rede; retorna base de fallback de referência.
    """
    req = urllib.request.Request(
        IBGE_SIDRA_POPULACAO_BAIRROS_SALVADOR,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SalvadorObrasETL/1.0",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            if isinstance(data, list) and len(data) > 1:
                normalizados = normalizar_registros_censo_2022(data)
                if normalizados:
                    return normalizados
    except Exception:
        pass

    # Fallback determinístico consolidado com dados de referência em etl.reference
    from etl.reference.sample_data import SAMPLE_IBGE_CENSO_2022
    return SAMPLE_IBGE_CENSO_2022


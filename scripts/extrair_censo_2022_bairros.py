"""Extração reprodutível dos Agregados por Bairro do Censo 2022 (IBGE) para Salvador.

Lê os 4 pacotes oficiais de Agregados por Bairro do Censo Demográfico 2022
(`basico`, `caracteristicas_domicilio1`, `caracteristicas_domicilio2`, `alfabetizacao`)
em modo offline (diretório local com ZIPs/CSVs) ou por download direto do FTP do IBGE,
calcula os sub-indicadores oficiais por Bairro Oficial e grava a base plana de
referência separada dos metadados de auditoria.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT_DIR = Path(__file__).resolve().parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from etl.domain.territorio import is_zona_especial_nao_residencial, normalizar_nome

IBGE_AGREGADOS_BAIRRO_URL = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
    "Agregados_por_Setores_Censitarios/Agregados_por_Bairro_csv/"
)
SALVADOR_CD_MUNICIPIO = "2927408"
ESPERADO_BAIRROS_IBGE = 170
CELULAS_MASCARADAS = {"", ".", "..", "-", "X", "x"}

DEFAULT_OUTPUT_PATH = _ROOT_DIR / "etl" / "reference" / "censo_2022_salvador_bairros.json"
DEFAULT_METADATA_PATH = (
    _ROOT_DIR / "etl" / "reference" / "censo_2022_salvador_bairros_metadata.json"
)
DEFAULT_GEOSALVADOR_PATH = _ROOT_DIR / "etl" / "reference" / "geosalvador_bairros_real.geojson"

PACOTES_OFICIAIS = (
    "basico",
    "caracteristicas_domicilio1",
    "caracteristicas_domicilio2",
    "alfabetizacao",
)

# Direção IBGE -> nome normalizado canônico da malha GeoSalvador
IBGE_PARA_GEOSALVADOR_ALIASES: dict[str, str] = {
    normalizar_nome("Centro Administrativo da Bahia - CAB"): normalizar_nome(
        "Centro Administrativo da Bahia"
    ),
    normalizar_nome("CAB"): normalizar_nome("Centro Administrativo da Bahia"),
    normalizar_nome("Nordeste do Amaralina"): normalizar_nome("Nordeste de Amaralina"),
    normalizar_nome("Ilha dos Frades"): normalizar_nome(
        "Ilha dos Frades/Ilha de Santo Antônio"
    ),
    normalizar_nome("Ilha dos Frades / Ilha de Santo Antônio"): normalizar_nome(
        "Ilha dos Frades/Ilha de Santo Antônio"
    ),
    normalizar_nome("Bom Jesus dos Passos"): normalizar_nome(
        "Ilha de Bom Jesus dos Passos"
    ),
    normalizar_nome("Ilha Bom Jesus dos Passos"): normalizar_nome(
        "Ilha de Bom Jesus dos Passos"
    ),
    normalizar_nome("Beiru / Tancredo Neves"): normalizar_nome("Beiru/Tancredo Neves"),
    normalizar_nome("Caixa D'Água"): normalizar_nome("Caixa D´Água"),
    normalizar_nome("Caixa D'água"): normalizar_nome("Caixa D´Água"),
    normalizar_nome("Vila Ruy Barbosa / Jardim Cruzeiro"): normalizar_nome(
        "Vila Ruy Barbosa\\Jardim Cruzeiro"
    ),
    normalizar_nome("Vila Ruy Barbosa \\ Jardim Cruzeiro"): normalizar_nome(
        "Vila Ruy Barbosa\\Jardim Cruzeiro"
    ),
}

VARIAVEIS_DOCUMENTACAO = {
    "populacao": "basico.v0001",
    "domicilios_particulares_permanentes_ocupados": "caracteristicas_domicilio1.V00001",
    "pct_esgoto_inadequado": (
        "100 * (1 - (caracteristicas_domicilio2.V00309 + V00310 + V00311) "
        "/ caracteristicas_domicilio1.V00001) [PLANSAB]"
    ),
    "pct_agua_inadequada": (
        "100 * (1 - caracteristicas_domicilio2.V00111 "
        "/ caracteristicas_domicilio1.V00001)"
    ),
    "pct_analfabetismo_15mais": (
        "100 * alfabetizacao.V00901 / (alfabetizacao.V00900 + alfabetizacao.V00901)"
    ),
}


def _carregar_mapa_canonico_geosalvador(geosalvador_path: Path) -> dict[str, str]:
    """Carrega o mapeamento nome_normalizado -> nome_canonico da malha GeoSalvador."""
    with geosalvador_path.open("r", encoding="utf-8") as f:
        geo = json.load(f)
    mapa: dict[str, str] = {}
    for feat in geo.get("features", []):
        props = feat.get("properties", {})
        nome = (props.get("NM_BAIRRO") or props.get("NOME_BAIRR") or "").strip()
        if nome:
            mapa[normalizar_nome(nome)] = nome
    return mapa


def _resolver_nome_canonico(
    nome_ibge: str, mapa_canonico: dict[str, str]
) -> str:
    """Resolve um nome retornado pelo IBGE para o nome canônico no GeoSalvador."""
    norm = normalizar_nome(nome_ibge)
    alvo_norm = IBGE_PARA_GEOSALVADOR_ALIASES.get(norm, norm)
    if alvo_norm in mapa_canonico:
        return mapa_canonico[alvo_norm]
    raise ValueError(
        f"Bairro retornado pelo IBGE sem correspondência na malha GeoSalvador: {nome_ibge!r}"
    )


def _padrao_pacote(pacote: str) -> re.Pattern[str]:
    return re.compile(rf"(?:^|[_\-]){re.escape(pacote)}(?:[_\-.]|$)", re.IGNORECASE)


def _registro_zona_especial_zerado() -> dict[str, Any]:
    return {
        "populacao": 0,
        "pct_esgoto_inadequado": 0.0,
        "pct_agua_inadequada": 0.0,
        "pct_analfabetismo_15mais": 0.0,
        "is_zona_especial_nao_residencial": True,
        "isZonaEspecialNaoResidencial": True,
    }


def _localizar_arquivo_pacote(input_dir: Path, pacote: str) -> Path:
    """Localiza o CSV ou ZIP correspondente a um dos 4 pacotes do IBGE."""
    padrao = _padrao_pacote(pacote)
    candidatos_csv = sorted(
        p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() == ".csv" and padrao.search(p.stem)
    )
    if candidatos_csv:
        return candidatos_csv[0]
    candidatos_zip = sorted(
        p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() == ".zip" and padrao.search(p.stem)
    )
    if candidatos_zip:
        return candidatos_zip[0]
    raise FileNotFoundError(
        f"Pacote oficial '{pacote}' (.csv ou .zip) não encontrado em {input_dir}"
    )


def _ler_linhas_salvador(arquivo: Path, mapa_canonico: dict[str, str]) -> dict[str, dict[str, str]]:
    """Lê um CSV (ou ZIP contendo CSV) em Latin-1 delimitado por ';' filtrando Salvador."""
    if arquivo.suffix.lower() == ".zip":
        with zipfile.ZipFile(arquivo, "r") as zf:
            csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                raise ValueError(f"Arquivo ZIP sem CSV interno: {arquivo}")
            raw_bytes = zf.read(csv_names[0])
            text_stream = io.StringIO(raw_bytes.decode("latin-1"))
            return _parsear_csv_salvador(text_stream, arquivo.name, mapa_canonico)

    with arquivo.open("r", encoding="latin-1", newline="") as f:
        return _parsear_csv_salvador(f, arquivo.name, mapa_canonico)


def _parsear_csv_salvador(
    stream: io.TextIOBase,
    origem: str,
    mapa_canonico: dict[str, str],
) -> dict[str, dict[str, str]]:
    reader = csv.DictReader(stream, delimiter=";")
    if not reader.fieldnames:
        raise ValueError(f"CSV vazio ou sem cabeçalho: {origem}")

    # Normaliza cabeçalhos removendo BOM/espaços eventuais
    col_map = {col.strip().lstrip("\ufeff"): col for col in reader.fieldnames}
    if "CD_BAIRRO" not in col_map or "NM_BAIRRO" not in col_map:
        raise ValueError(f"Colunas CD_BAIRRO/NM_BAIRRO ausentes em {origem}")

    registros: dict[str, dict[str, str]] = {}
    for row in reader:
        cd_bairro = (row.get(col_map["CD_BAIRRO"]) or "").strip()
        if not cd_bairro.startswith(SALVADOR_CD_MUNICIPIO):
            continue
        nm_ibge = (row.get(col_map["NM_BAIRRO"]) or "").strip()
        nome_canonico = _resolver_nome_canonico(nm_ibge, mapa_canonico)
        limpo = {
            k.strip().lstrip("\ufeff"): (v or "").strip()
            for k, v in row.items()
            if k is not None
        }
        registros[nome_canonico] = limpo
    return registros


def _parse_numero(
    valor_raw: str | None,
    bairro: str,
    variavel: str,
    is_zona_especial: bool,
) -> float | None:
    """Converte célula IBGE para float ou retorna None se mascarada em Zona Especial."""
    texto = (valor_raw or "").strip()
    if texto in CELULAS_MASCARADAS:
        if is_zona_especial:
            return None
        raise ValueError(
            f"Célula mascarada ou vazia para bairro residencial {bairro!r} na variável {variavel}: {texto!r}"
        )
    try:
        return float(texto.replace(",", "."))
    except ValueError as exc:
        if is_zona_especial:
            return None
        raise ValueError(
            f"Valor não numérico para bairro residencial {bairro!r} na variável {variavel}: {texto!r}"
        ) from exc


def _baixar_pacotes_ibge(destino_dir: Path, base_url: str = IBGE_AGREGADOS_BAIRRO_URL) -> None:
    """Baixa os 4 ZIPs oficiais de Agregados por Bairro do FTP do IBGE."""
    req = urllib.request.Request(
        base_url,
        headers={"User-Agent": "SalvadorObrasAuditoria/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    links = re.findall(r'href=["\']([^"\']+\.zip)["\']', html, flags=re.IGNORECASE)
    for pacote in PACOTES_OFICIAIS:
        padrao = _padrao_pacote(pacote)
        correspondencias = [lnk for lnk in links if padrao.search(Path(lnk).stem)]
        if not correspondencias:
            raise RuntimeError(
                f"Arquivo ZIP para pacote '{pacote}' não encontrado na listagem de {base_url}"
            )
        nome_arquivo = Path(correspondencias[0]).name
        url_arquivo = base_url.rstrip("/") + "/" + nome_arquivo
        destino_arquivo = destino_dir / nome_arquivo
        req_zip = urllib.request.Request(
            url_arquivo,
            headers={"User-Agent": "SalvadorObrasAuditoria/1.0"},
        )
        with urllib.request.urlopen(req_zip, timeout=120) as resp_zip:
            destino_arquivo.write_bytes(resp_zip.read())


def extrair_censo_2022_bairros(
    input_dir: Path | None = None,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    metadata_path: Path = DEFAULT_METADATA_PATH,
    geosalvador_path: Path = DEFAULT_GEOSALVADOR_PATH,
    download: bool = False,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Extrai os sub-indicadores do Censo 2022 para os 170 bairros de Salvador no IBGE."""
    if input_dir is None and not download:
        raise ValueError("Informe input_dir para modo offline ou download=True para baixar do IBGE.")

    mapa_canonico = _carregar_mapa_canonico_geosalvador(geosalvador_path)

    if download:
        with tempfile.TemporaryDirectory(prefix="ibge_censo_2022_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            _baixar_pacotes_ibge(tmp_path)
            return _processar_diretorio(
                tmp_path,
                output_path=output_path,
                metadata_path=metadata_path,
                mapa_canonico=mapa_canonico,
            )

    assert input_dir is not None
    return _processar_diretorio(
        input_dir,
        output_path=output_path,
        metadata_path=metadata_path,
        mapa_canonico=mapa_canonico,
    )


def _processar_diretorio(
    source_dir: Path,
    *,
    output_path: Path,
    metadata_path: Path,
    mapa_canonico: dict[str, str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    arquivos_pacotes: dict[str, Path] = {
        pacote: _localizar_arquivo_pacote(source_dir, pacote)
        for pacote in PACOTES_OFICIAIS
    }
    tabelas: dict[str, dict[str, dict[str, str]]] = {
        pacote: _ler_linhas_salvador(caminho, mapa_canonico)
        for pacote, caminho in arquivos_pacotes.items()
    }

    chaves_por_pacote = {p: set(rows.keys()) for p, rows in tabelas.items()}
    uniao_chaves = set().union(*chaves_por_pacote.values())
    intersecao_chaves = set.intersection(*chaves_por_pacote.values())

    if uniao_chaves != intersecao_chaves:
        faltantes = {
            p: sorted(uniao_chaves - chaves)
            for p, chaves in chaves_por_pacote.items()
            if uniao_chaves - chaves
        }
        raise ValueError(f"Junção incompleta entre os 4 pacotes do IBGE: {faltantes}")

    if len(intersecao_chaves) != ESPERADO_BAIRROS_IBGE:
        raise ValueError(
            f"Contagem inesperada de bairros após junção: esperado {ESPERADO_BAIRROS_IBGE}, "
            f"obtido {len(intersecao_chaves)}"
        )

    resultado: dict[str, dict[str, Any]] = {}
    for bairro in sorted(intersecao_chaves):
        zona_especial = is_zona_especial_nao_residencial(bairro)
        r_basico = tabelas["basico"][bairro]
        r_dom1 = tabelas["caracteristicas_domicilio1"][bairro]
        r_dom2 = tabelas["caracteristicas_domicilio2"][bairro]
        r_alfab = tabelas["alfabetizacao"][bairro]

        v0001 = _parse_numero(r_basico.get("v0001") or r_basico.get("V0001"), bairro, "v0001", zona_especial)
        v00001 = _parse_numero(r_dom1.get("V00001"), bairro, "V00001", zona_especial)
        v00111 = _parse_numero(r_dom2.get("V00111"), bairro, "V00111", zona_especial)
        v00309 = _parse_numero(r_dom2.get("V00309"), bairro, "V00309", zona_especial)
        v00310 = _parse_numero(r_dom2.get("V00310"), bairro, "V00310", zona_especial)
        v00311 = _parse_numero(r_dom2.get("V00311"), bairro, "V00311", zona_especial)
        v00900 = _parse_numero(r_alfab.get("V00900"), bairro, "V00900", zona_especial)
        v00901 = _parse_numero(r_alfab.get("V00901"), bairro, "V00901", zona_especial)

        if zona_especial and any(
            val is None for val in (v0001, v00001, v00111, v00309, v00310, v00311, v00900, v00901)
        ):
            resultado[bairro] = _registro_zona_especial_zerado()
            continue

        assert v0001 is not None and v00001 is not None
        assert v00111 is not None and v00309 is not None and v00310 is not None and v00311 is not None
        assert v00900 is not None and v00901 is not None

        denom_alfab = v00900 + v00901
        if v00001 <= 0 or denom_alfab <= 0:
            if zona_especial:
                resultado[bairro] = _registro_zona_especial_zerado()
                continue
            raise ValueError(
                f"Denominador zero para bairro residencial {bairro!r}: "
                f"V00001={v00001}, V00900+V00901={denom_alfab}"
            )

        pct_esgoto = round((1.0 - (v00309 + v00310 + v00311) / v00001) * 100.0, 2)
        pct_agua = round((1.0 - v00111 / v00001) * 100.0, 2)
        pct_analf = round((v00901 / denom_alfab) * 100.0, 2)

        resultado[bairro] = {
            "populacao": int(round(v0001)),
            "pct_esgoto_inadequado": pct_esgoto,
            "pct_agua_inadequada": pct_agua,
            "pct_analfabetismo_15mais": pct_analf,
            "is_zona_especial_nao_residencial": zona_especial,
            "isZonaEspecialNaoResidencial": zona_especial,
        }

    metadados: dict[str, Any] = {
        "fonte": "IBGE Censo Demográfico 2022 — Agregados por Bairro (Universo)",
        "url_base": IBGE_AGREGADOS_BAIRRO_URL,
        "municipio_codigo": SALVADOR_CD_MUNICIPIO,
        "total_bairros": len(resultado),
        "extraido_em": datetime.now(timezone.utc).isoformat(),
        "pacotes": {p: path.name for p, path in arquivos_pacotes.items()},
        "variaveis": VARIAVEIS_DOCUMENTACAO,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(metadados, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return resultado, metadados


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extrai os Agregados por Bairro do Censo 2022 (IBGE) para Salvador."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help="Diretório local contendo os 4 pacotes (.zip ou .csv) do IBGE para modo offline.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Baixa os 4 pacotes oficiais diretamente do FTP do IBGE.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Caminho de saída do JSON plano de referência.",
    )
    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=DEFAULT_METADATA_PATH,
        help="Caminho de saída do arquivo companheiro de metadados de auditoria.",
    )
    args = parser.parse_args(argv)

    extrair_censo_2022_bairros(
        input_dir=args.input_dir,
        output_path=args.output,
        metadata_path=args.metadata_output,
        download=args.download,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

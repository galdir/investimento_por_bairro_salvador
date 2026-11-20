"""Testes de extração reprodutível dos Agregados por Bairro do Censo 2022 (IBGE)."""

import json
import zipfile
from pathlib import Path

import pytest

from scripts.extrair_censo_2022_bairros import extrair_censo_2022_bairros, main

_ROOT = Path(__file__).resolve().parents[2]
_GEOSALVADOR_PATH = _ROOT / "etl" / "reference" / "geosalvador_bairros_real.geojson"


def _carregar_bairros_ibge_esperados() -> list[str]:
    with _GEOSALVADOR_PATH.open("r", encoding="utf-8") as f:
        geo = json.load(f)
    nomes = [
        (feat["properties"].get("NM_BAIRRO") or feat["properties"].get("NOME_BAIRR")).strip()
        for feat in geo["features"]
    ]
    return [n for n in nomes if n != "Aquarius"]


def _escrever_fixtures_ibge(
    target_dir: Path,
    *,
    overrides: dict[str, dict[str, str]] | None = None,
    omitir_em_domicilio2: set[str] | None = None,
    extras_fora_salvador: bool = True,
) -> None:
    """Gera os 4 CSVs oficiais do IBGE em Latin-1 delimitados por ';' para 170 bairros."""
    bairros = _carregar_bairros_ibge_esperados()
    overrides = overrides or {}
    omitir_em_domicilio2 = omitir_em_domicilio2 or set()

    # Mapeia nomes canônicos para exemplos de nomes que o IBGE retorna
    ibge_aliases_inversos = {
        "Centro Administrativo da Bahia": "Centro Administrativo da Bahia - CAB",
        "Nordeste de Amaralina": "Nordeste do Amaralina",
        "Ilha dos Frades/Ilha de Santo Antônio": "Ilha dos Frades",
        "Ilha de Bom Jesus dos Passos": "Bom Jesus dos Passos",
        "Beiru/Tancredo Neves": "Beiru / Tancredo Neves",
        "Caixa D´Água": "Caixa D'Água",
        "Vila Ruy Barbosa\\Jardim Cruzeiro": "Vila Ruy Barbosa / Jardim Cruzeiro",
    }

    basico_rows = ["CD_BAIRRO;NM_BAIRRO;v0001"]
    dom1_rows = ["CD_BAIRRO;NM_BAIRRO;V00001"]
    dom2_rows = ["CD_BAIRRO;NM_BAIRRO;V00111;V00309;V00310;V00311"]
    alfab_rows = ["CD_BAIRRO;NM_BAIRRO;V00900;V00901"]

    if extras_fora_salvador:
        # Município diferente (2910800 = Feira de Santana) deve ser ignorado
        basico_rows.append("2910800001;Centro;99999")
        dom1_rows.append("2910800001;Centro;30000")
        dom2_rows.append("2910800001;Centro;25000;20000;1000;1000")
        alfab_rows.append("2910800001;Centro;50000;5000")

    for idx, nome_canonico in enumerate(bairros, start=1):
        cd_bairro = f"2927408{idx:03d}"
        nm_ibge = ibge_aliases_inversos.get(nome_canonico, nome_canonico)
        ov = overrides.get(nome_canonico, {})

        if nome_canonico == "Aeroporto" and "Aeroporto" not in overrides:
            v0001 = "."
            v00001 = "."
            v00111, v00309, v00310, v00311 = ".", ".", ".", "."
            v00900, v00901 = ".", "."
        else:
            v0001 = ov.get("v0001", "1000")
            v00001 = ov.get("V00001", "400")
            v00111 = ov.get("V00111", "380")
            v00309 = ov.get("V00309", "300")
            v00310 = ov.get("V00310", "40")
            v00311 = ov.get("V00311", "20")
            v00900 = ov.get("V00900", "760")
            v00901 = ov.get("V00901", "40")

        basico_rows.append(f"{cd_bairro};{nm_ibge};{v0001}")
        dom1_rows.append(f"{cd_bairro};{nm_ibge};{v00001}")
        if nome_canonico not in omitir_em_domicilio2:
            dom2_rows.append(f"{cd_bairro};{nm_ibge};{v00111};{v00309};{v00310};{v00311}")
        alfab_rows.append(f"{cd_bairro};{nm_ibge};{v00900};{v00901}")

    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "Agregados_por_bairros_basico_BR.csv").write_text(
        "\n".join(basico_rows) + "\n", encoding="latin-1"
    )
    (target_dir / "Agregados_por_bairros_caracteristicas_domicilio1_BR.csv").write_text(
        "\n".join(dom1_rows) + "\n", encoding="latin-1"
    )
    (target_dir / "Agregados_por_bairros_caracteristicas_domicilio2_BR.csv").write_text(
        "\n".join(dom2_rows) + "\n", encoding="latin-1"
    )
    (target_dir / "Agregados_por_bairros_alfabetizacao_BR.csv").write_text(
        "\n".join(alfab_rows) + "\n", encoding="latin-1"
    )


def test_extrair_censo_2022_bairros_calcula_formulas_aliases_e_metadados(tmp_path: Path) -> None:
    """Extração offline lê CSVs Latin-1, calcula PLANSAB/água/analfabetismo, resolve aliases e separa metadados."""
    input_dir = tmp_path / "ibge"
    output_path = tmp_path / "censo_2022_salvador_bairros.json"
    metadata_path = tmp_path / "censo_2022_salvador_bairros_metadata.json"

    _escrever_fixtures_ibge(
        input_dir,
        overrides={
            "Pituba": {
                "v0001": "65432",
                "V00001": "1000",
                "V00111": "995",      # déficit água: (1 - 995/1000)*100 = 0.5
                "V00309": "900",
                "V00310": "50",
                "V00311": "25",       # déficit esgoto: (1 - 975/1000)*100 = 2.5
                "V00900": "50000",
                "V00901": "500",      # analfabetismo: 500/50500*100 = 0.990099 -> 0.99
            },
            "Nordeste de Amaralina": {
                "v0001": "22111",
                "V00001": "800",
                "V00111": "760",      # 5.0
                "V00309": "600",
                "V00310": "20",
                "V00311": "20",       # 20.0
                "V00900": "15000",
                "V00901": "750",      # 750/15750*100 = 4.7619 -> 4.76
            },
        },
    )

    dados, metadados = extrair_censo_2022_bairros(
        input_dir=input_dir,
        output_path=output_path,
        metadata_path=metadata_path,
        geosalvador_path=_GEOSALVADOR_PATH,
    )

    assert len(dados) == 170
    assert "Aquarius" not in dados
    assert "PITUBA" not in dados
    assert "_metadata" not in dados

    # Verifica fórmulas exatas em Pituba
    pituba = dados["Pituba"]
    assert pituba["populacao"] == 65432
    assert pituba["pct_esgoto_inadequado"] == 2.5
    assert pituba["pct_agua_inadequada"] == 0.5
    assert pituba["pct_analfabetismo_15mais"] == 0.99
    assert pituba["is_zona_especial_nao_residencial"] is False
    assert pituba["isZonaEspecialNaoResidencial"] is False

    # Verifica resolução de aliases IBGE -> GeoSalvador
    assert "Nordeste de Amaralina" in dados
    assert "Nordeste do Amaralina" not in dados
    assert dados["Nordeste de Amaralina"]["pct_analfabetismo_15mais"] == 4.76

    assert "Centro Administrativo da Bahia" in dados
    assert "Centro Administrativo da Bahia - CAB" not in dados
    assert dados["Centro Administrativo da Bahia"]["is_zona_especial_nao_residencial"] is True
    assert dados["Centro Administrativo da Bahia"]["isZonaEspecialNaoResidencial"] is True

    # Verifica Aeroporto com células "." tratado como Zona Especial Não-Residencial
    assert dados["Aeroporto"] == {
        "populacao": 0,
        "pct_esgoto_inadequado": 0.0,
        "pct_agua_inadequada": 0.0,
        "pct_analfabetismo_15mais": 0.0,
        "is_zona_especial_nao_residencial": True,
        "isZonaEspecialNaoResidencial": True,
    }

    # Verifica presença de IAPI, STIEP, Ilha de Maré, Chame-Chame e Colinas de Periperi
    for obrigatorio in ("IAPI", "STIEP", "Ilha de Maré", "Chame-Chame", "Colinas de Periperi"):
        assert obrigatorio in dados

    # Verifica arquivos gravados e metadados separados
    assert json.loads(output_path.read_text(encoding="utf-8")) == dados
    meta_disk = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert meta_disk == metadados
    assert "url_base" in meta_disk
    assert "pacotes" in meta_disk
    assert "extraido_em" in meta_disk
    assert "variaveis" in meta_disk


@pytest.mark.parametrize("celula_mascarada", [".", "..", "-", "X", ""])
def test_extrair_censo_2022_bairros_rejeita_celula_mascarada_em_bairro_residencial(
    tmp_path: Path, celula_mascarada: str
) -> None:
    """Bairro residencial com célula mascarada ou vazia deve interromper com erro explícito."""
    input_dir = tmp_path / "ibge"
    _escrever_fixtures_ibge(input_dir, overrides={"IAPI": {"V00111": celula_mascarada}})

    with pytest.raises(ValueError, match="IAPI"):
        extrair_censo_2022_bairros(
            input_dir=input_dir,
            output_path=tmp_path / "out.json",
            metadata_path=tmp_path / "meta.json",
            geosalvador_path=_GEOSALVADOR_PATH,
        )


def test_extrair_censo_2022_bairros_rejeita_denominador_zero_em_bairro_residencial(
    tmp_path: Path,
) -> None:
    """Bairro residencial com denominador zero deve interromper com erro explícito."""
    input_dir = tmp_path / "ibge"
    _escrever_fixtures_ibge(input_dir, overrides={"STIEP": {"V00001": "0"}})

    with pytest.raises(ValueError, match="STIEP"):
        extrair_censo_2022_bairros(
            input_dir=input_dir,
            output_path=tmp_path / "out.json",
            metadata_path=tmp_path / "meta.json",
            geosalvador_path=_GEOSALVADOR_PATH,
        )


def test_extrair_censo_2022_bairros_rejeita_juncao_incompleta(tmp_path: Path) -> None:
    """Junção incompleta entre os 4 pacotes deve interromper com erro bloqueante."""
    input_dir = tmp_path / "ibge"
    _escrever_fixtures_ibge(input_dir, omitir_em_domicilio2={"Chame-Chame"})

    with pytest.raises(ValueError, match="Junção incompleta"):
        extrair_censo_2022_bairros(
            input_dir=input_dir,
            output_path=tmp_path / "out.json",
            metadata_path=tmp_path / "meta.json",
            geosalvador_path=_GEOSALVADOR_PATH,
        )


def test_extrair_censo_2022_bairros_le_zips_oficiais_em_modo_offline(tmp_path: Path) -> None:
    """Modo offline também aceita os 4 pacotes compactados em .zip."""
    csv_dir = tmp_path / "csvs"
    zip_dir = tmp_path / "zips"
    zip_dir.mkdir(parents=True, exist_ok=True)
    _escrever_fixtures_ibge(csv_dir)

    for csv_file in csv_dir.glob("*.csv"):
        zip_path = zip_dir / f"{csv_file.stem}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(csv_file, arcname=csv_file.name)

    dados, _ = extrair_censo_2022_bairros(
        input_dir=zip_dir,
        output_path=tmp_path / "out.json",
        metadata_path=tmp_path / "meta.json",
        geosalvador_path=_GEOSALVADOR_PATH,
    )
    assert len(dados) == 170


def test_extrair_censo_2022_bairros_rejeita_denominador_zero_alfabetizacao(
    tmp_path: Path,
) -> None:
    """Bairro residencial com denominador zero de alfabetização (V00900+V00901=0) gera erro explícito."""
    input_dir = tmp_path / "ibge"
    _escrever_fixtures_ibge(
        input_dir, overrides={"IAPI": {"V00900": "0", "V00901": "0"}}
    )

    with pytest.raises(ValueError, match="IAPI"):
        extrair_censo_2022_bairros(
            input_dir=input_dir,
            output_path=tmp_path / "out.json",
            metadata_path=tmp_path / "meta.json",
            geosalvador_path=_GEOSALVADOR_PATH,
        )


def test_extrair_censo_2022_bairros_rejeita_contagem_diferente_de_170(
    tmp_path: Path,
) -> None:
    """Junção completa nos 4 pacotes porém com contagem diferente de 170 deve falhar."""
    input_dir = tmp_path / "ibge"
    _escrever_fixtures_ibge(input_dir)
    # Remove o último bairro dos 4 CSVs (mantém junção completa, mas com 169 bairros)
    for csv_file in input_dir.glob("*.csv"):
        linhas = csv_file.read_text(encoding="latin-1").splitlines()
        csv_file.write_text("\n".join(linhas[:-1]) + "\n", encoding="latin-1")

    with pytest.raises(ValueError, match="esperado 170"):
        extrair_censo_2022_bairros(
            input_dir=input_dir,
            output_path=tmp_path / "out.json",
            metadata_path=tmp_path / "meta.json",
            geosalvador_path=_GEOSALVADOR_PATH,
        )


def test_cli_main_modo_offline_executa_extracao(tmp_path: Path) -> None:
    """CLI main(--input-dir) executa a extração offline e grava saída e metadados."""
    input_dir = tmp_path / "ibge"
    out_path = tmp_path / "out.json"
    meta_path = tmp_path / "meta.json"
    _escrever_fixtures_ibge(input_dir)

    rc = main(
        [
            "--input-dir",
            str(input_dir),
            "--output",
            str(out_path),
            "--metadata-output",
            str(meta_path),
        ]
    )
    assert rc == 0
    assert len(json.loads(out_path.read_text(encoding="utf-8"))) == 170
    assert json.loads(meta_path.read_text(encoding="utf-8"))["total_bairros"] == 170


def test_base_versionada_regenerada_cobre_170_bairros_canonicos_sem_duplicacao() -> None:
    """Base versionada regenerada tem exatamente 170 chaves únicas canônicas e metadados separados."""
    ref_path = _ROOT / "etl" / "reference" / "censo_2022_salvador_bairros.json"
    meta_path = _ROOT / "etl" / "reference" / "censo_2022_salvador_bairros_metadata.json"

    dados = json.loads(ref_path.read_text(encoding="utf-8"))
    esperados = set(_carregar_bairros_ibge_esperados())

    assert len(dados) == 170
    assert set(dados.keys()) == esperados
    assert "Aquarius" not in dados

    campos_esperados = {
        "populacao",
        "pct_esgoto_inadequado",
        "pct_agua_inadequada",
        "pct_analfabetismo_15mais",
        "is_zona_especial_nao_residencial",
        "isZonaEspecialNaoResidencial",
    }
    for bairro, entry in dados.items():
        assert campos_esperados.issubset(entry.keys()), f"Campos ausentes em {bairro}"

    for obrigatorio in ("IAPI", "STIEP", "Ilha de Maré", "Chame-Chame", "Colinas de Periperi"):
        assert dados[obrigatorio]["populacao"] > 0
        assert dados[obrigatorio]["is_zona_especial_nao_residencial"] is False

    assert dados["Aeroporto"]["populacao"] == 0
    assert dados["Aeroporto"]["is_zona_especial_nao_residencial"] is True

    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["total_bairros"] == 170
    assert len(meta["pacotes"]) == 4
    assert "extraido_em" in meta
    assert "url_base" in meta
    assert "variaveis" in meta

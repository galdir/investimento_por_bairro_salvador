"""Módulo de reconciliação canônica do acervo local de Obras Públicas de Salvador.

Consolida múltiplas versões locais de fichas (`obras/<id>.json`) pela Chave Canônica
da Obra, unifica a identidade das Empreiteiras por Razão Social canônica, recalcula os
KPIs reais do Funil de Execução Financeira e os rollups territoriais e remove arquivos
órfãos e amostras sintéticas garantindo correspondência estrita 1:1 com o índice.
"""

import argparse
import json
from pathlib import Path
import shutil
import sys
from typing import Any
import warnings

from etl.domain.empreiteiras import calcular_concentracao_empreiteiras, eh_cnpj_valido
from etl.domain.ficha_limpa import (
    aplicar_resumo_empreiteira_ficha,
    eh_dom_valido,
    mesclar_fichas_obra,
    sincronizar_obra_com_ficha,
)
from etl.domain.geocoding import (
    _carregar_curadoria_territorial,
    _extrair_indices_territoriais,
    aplicar_curadoria_obra,
    calcular_centroides_bairros,
    resolver_frentes_medicao,
)
from etl.domain.kpis import calcular_kpis_globais
from etl.domain.mandato import cds_ug_compativeis, obter_chaves_candidatas_obra
from etl.domain.territorio import calcular_rollup_territorial
from etl.generator import (
    generate_bairros_geojson,
    generate_index_json,
    generate_obra_detalhe_json,
    generate_prefeituras_geojson,
)


def indexar_fichas_locais(
    obras_dir: Path,
) -> tuple[dict[tuple[str, str], list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    """Carrega e indexa as fichas locais em `obras/*.json` por chave canônica e ID.

    Sumário:
        Varre o diretório de fichas individuais para consulta O(1) por chave ou identificador.

    Descrição Estendida:
        Lê todos os arquivos JSON presentes em `obras_dir` e os indexa simultaneamente pelo
        identificador (`id` / nome do arquivo) e pelas tuplas `(unidadeGestora, numeroContrato)`.
        Arquivos corrompidos ou inválidos emitem aviso via `warnings` sem interromper a carga.

    Argumentos:
        obras_dir: Caminho do subdiretório `obras/`.

    Retornos:
        Tupla `(fichas_por_chave, fichas_por_id)`.

    Erros:
        Não lança exceções; arquivos ilegíveis geram `RuntimeWarning`.
    """
    fichas_por_chave: dict[tuple[str, str], list[dict[str, Any]]] = {}
    fichas_por_id: dict[str, dict[str, Any]] = {}

    if not obras_dir.exists():
        return fichas_por_chave, fichas_por_id

    for arquivo in sorted(obras_dir.glob("*.json")):
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                ficha = json.load(f)
            if not isinstance(ficha, dict):
                continue
        except (OSError, json.JSONDecodeError) as exc:
            warnings.warn(
                f"Ignorando ficha local ilegível '{arquivo}': {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            continue

        ficha_id = str(ficha.get("id") if ficha.get("id") is not None else arquivo.stem)
        fichas_por_id[ficha_id] = ficha
        fichas_por_id.setdefault(arquivo.stem, ficha)

        for chave in obter_chaves_candidatas_obra(ficha):
            fichas_por_chave.setdefault(chave, []).append(ficha)

    return fichas_por_chave, fichas_por_id


def coletar_fichas_candidatas(
    obra: dict[str, Any],
    fichas_por_chave: dict[tuple[str, str], list[dict[str, Any]]],
    fichas_por_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Reúne todas as fichas locais compatíveis com a Chave Canônica da Obra.

    Sumário:
        Coleta versões candidatas em disco evitando colisões entre códigos `cdUnidadeGestora` distintos.

    Descrição Estendida:
        Busca primeiro pelo identificador direto (`id`) e depois pelas chaves candidatas
        `(ug, numeroContrato)`, filtrando pares incompatíveis quando ambos possuem
        `cdUnidadeGestora` explícito diferente (em conformidade com o ADR-0002).

    Argumentos:
        obra: Dicionário do contrato ativo.
        fichas_por_chave: Índice retornado por `indexar_fichas_locais`.
        fichas_por_id: Mapa de fichas por ID retornado por `indexar_fichas_locais`.

    Retornos:
        Lista ordenada e deduplicada de fichas candidatas compatíveis.

    Erros:
        Não lança exceções.
    """
    candidatas: list[dict[str, Any]] = []
    vistos: set[int] = set()

    obra_id = obra.get("id")
    if obra_id not in (None, ""):
        direta = fichas_por_id.get(str(obra_id))
        if direta is not None and cds_ug_compativeis(obra, direta):
            vistos.add(id(direta))
            candidatas.append(direta)

    for chave in obter_chaves_candidatas_obra(obra):
        for ficha in fichas_por_chave.get(chave, []):
            if id(ficha) not in vistos and cds_ug_compativeis(obra, ficha):
                vistos.add(id(ficha))
                candidatas.append(ficha)

    return candidatas


def expurgar_arquivos_orfaos(obras_dir: Path, ids_ativos: set[str]) -> int:
    """Remove arquivos JSON em `obras/` cujo nome-base não pertence ao conjunto ativo.

    Sumário:
        Exclui versões históricas órfãs e amostras residuais mantendo correspondência 1:1 com o índice.

    Argumentos:
        obras_dir: Subdiretório `obras/` a higienizar.
        ids_ativos: Conjunto de identificadores em string pertencentes à carteira consolidada.

    Retornos:
        Quantidade de arquivos removidos do disco.

    Erros:
        Propaga `OSError` apenas se o sistema de arquivos impedir a remoção.
    """
    if not obras_dir.exists():
        return 0

    removidos = 0
    for arquivo in list(obras_dir.glob("*.json")):
        if arquivo.stem not in ids_ativos:
            arquivo.unlink(missing_ok=True)
            removidos += 1
    return removidos


def escrever_indices_alias(index_file_path: Path, output_path: Path) -> None:
    """Mantém os aliases `index_2025.json` e `index.json` sincronizados com o índice principal.

    Sumário:
        Replica atomicamente o índice anual gerado para os caminhos canônicos consumidos pelo frontend.

    Argumentos:
        index_file_path: Caminho do arquivo `index_<ano>.json` recém-gerado.
        output_path: Diretório raiz dos artefatos estáticos.

    Retornos:
        Nenhum valor (efeito colateral em disco).

    Erros:
        Emite `RuntimeWarning` caso a cópia de algum alias falhe.
    """
    for alias_name in ("index_2025.json", "index.json"):
        alias_path = output_path / alias_name
        if alias_path.resolve() != index_file_path.resolve():
            try:
                shutil.copyfile(index_file_path, alias_path)
            except OSError as exc:
                warnings.warn(
                    f"Falha ao sincronizar alias '{alias_path}': {exc}",
                    RuntimeWarning,
                    stacklevel=2,
                )


def resolver_caminho_indice(output_path: Path, year: int) -> Path | None:
    """Localiza o arquivo de índice existente no diretório de dados estáticos.

    Sumário:
        Prioriza `index_<ano>.json`, recorrendo a `index_2025.json` e `index.json`.

    Argumentos:
        output_path: Diretório raiz dos artefatos estáticos.
        year: Ano de referência desejado.

    Retornos:
        `Path` do índice encontrado ou `None` caso nenhum exista.

    Erros:
        Não lança exceções.
    """
    for nome in (f"index_{year}.json", "index_2025.json", "index.json"):
        candidato = output_path / nome
        if candidato.exists():
            return candidato
    return None


def finalizar_acervo_obras(
    obras: list[dict[str, Any]],
    fichas_por_id_obra: dict[str, dict[str, Any]],
    obras_dir: Path,
) -> tuple[dict[str, dict[str, Any]], int]:
    """Unifica empreiteiras, grava fichas individuais sincronizadas e expurga arquivos órfãos.

    Sumário:
        Executa a consolidação final das empreiteiras antes da escrita em disco e dos rollups.

    Descrição Estendida:
        Preenche razões sociais ausentes a partir das fichas, calcula `concentracao_map` com
        propagação de CNPJ canônico sem ambiguidade, atualiza cada ficha com o resumo completo da
        construtora, mantém o registro resumido sincronizado e remove arquivos em `obras/` sem
        correspondência ativa no catálogo.

    Argumentos:
        obras: Lista deduplicada de contratos ativos no índice.
        fichas_por_id_obra: Mapa `{str(obra_id): ficha}` contendo as fichas já mescladas.
        obras_dir: Diretório `obras/` onde os JSONs individuais são persistidos.

    Retornos:
        Tupla `(concentracao_map, quantidade_orfaos_removidos)`.

    Erros:
        Lança `ValueError` caso alguma obra consolidada não possua identificador válido ou ficha correspondente.
    """
    obras_dir.mkdir(parents=True, exist_ok=True)

    for obra in obras:
        obra_id = obra.get("id")
        if obra_id in (None, ""):
            raise ValueError("Contrato consolidado sem identificador válido ('id') para persistência.")
        obra_id_str = str(obra_id)
        ficha = fichas_por_id_obra.get(obra_id_str)
        if ficha is None:
            raise ValueError(f"Ficha consolidada ausente para o contrato '{obra_id_str}'.")

        if not str(obra.get("nmCredor") or obra.get("credor") or "").strip():
            razao_ficha = str((ficha.get("empreiteira") or {}).get("razaoSocial") or "").strip()
            if razao_ficha:
                obra["nmCredor"] = razao_ficha

    concentracao_map = calcular_concentracao_empreiteiras(obras)
    ids_ativos: set[str] = set()

    for obra in obras:
        obra_id_str = str(obra["id"])
        ids_ativos.add(obra_id_str)
        ficha = fichas_por_id_obra[obra_id_str]
        cnpj_obra = str(obra.get("cnpjCredor") or obra.get("cnpj") or "").strip() or None
        razao_obra = str(obra.get("nmCredor") or obra.get("credor") or "").strip() or None

        aplicar_resumo_empreiteira_ficha(
            ficha,
            concentracao_map=concentracao_map,
            cnpj_override=cnpj_obra,
            razao_override=razao_obra,
        )
        sincronizar_obra_com_ficha(obra, ficha)
        generate_obra_detalhe_json(ficha, obras_dir / f"{obra_id_str}.json")

    orfaos_removidos = expurgar_arquivos_orfaos(obras_dir, ids_ativos)
    return concentracao_map, orfaos_removidos


def reconciliar_acervo_local(
    output_dir: Path,
    year: int = 2025,
    curadoria: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Executa a reconciliação canônica completa do acervo estático local de obras.

    Sumário:
        Mescla múltiplas versões locais pela Chave Canônica da Obra, unifica empreiteiras,
        recalcula KPIs e rollups territoriais e remove arquivos órfãos.

    Descrição Estendida:
        Lê o índice local vigente e todas as fichas em `obras/*.json`, resgata históricos e
        metadados dispersos entre versões do mesmo contrato, consolida a identidade das
        empreiteiras, atualiza GeoJSONs/rollups, apura `kpis_globais` exclusivamente sobre a
        carteira reconciliada e expurga arquivos órfãos para manter relação estrita 1:1.

    Argumentos:
        output_dir: Diretório raiz dos artefatos estáticos (ex: `public/data`).
        year: Ano de referência do índice principal (padrão: 2025).

    Retornos:
        Dicionário com contadores de reconciliação (onde `total_obras_ativas` representa o
        total de contratos vigentes listados no catálogo reconciliado) e `kpis_globais`.

    Erros:
        Lança `FileNotFoundError` se nenhum índice existir em `output_dir`, ou `ValueError` se
        algum contrato no catálogo não possuir identificador válido.
    """
    output_path = Path(output_dir)
    index_source = resolver_caminho_indice(output_path, year)
    if index_source is None:
        raise FileNotFoundError(
            f"Nenhum arquivo de índice encontrado em '{output_path}' para reconciliação."
        )

    with open(index_source, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    obras_catalogo: list[dict[str, Any]] = [dict(o) for o in index_data.get("obras", [])]
    bairros_base: list[dict[str, Any]] = index_data.get("bairros", [])
    prefeituras_base: list[dict[str, Any]] = index_data.get("prefeituras_bairro", [])
    mandatos_disponiveis = (index_data.get("metadata") or {}).get("mandatosDisponiveis")

    obras_dir = output_path / "obras"
    obras_dir.mkdir(parents=True, exist_ok=True)
    fichas_por_chave, fichas_por_id = indexar_fichas_locais(obras_dir)

    bairros_geo_path = output_path / "geo" / "bairros.geojson"
    raw_bairros_geo: dict[str, Any] | None = None
    if bairros_geo_path.exists():
        with open(bairros_geo_path, "r", encoding="utf-8") as f:
            raw_bairros_geo = json.load(f)
    bairros_geo_para_frentes = raw_bairros_geo or {
        "features": [{"properties": b} for b in bairros_base]
    }
    bairros_centroides = calcular_centroides_bairros(bairros_geo_para_frentes)
    catalogo_curadoria = curadoria if curadoria is not None else _carregar_curadoria_territorial()
    indices_territoriais = _extrair_indices_territoriais(bairros_geo_para_frentes)

    fichas_consolidadas: dict[str, dict[str, Any]] = {}
    obras_mescladas = 0

    for obra in obras_catalogo:
        obra_id = obra.get("id")
        if obra_id in (None, ""):
            raise ValueError("Entrada no índice sem identificador válido ('id').")
        resultado_curadoria = aplicar_curadoria_obra(
            obra=obra,
            bairros_geojson=bairros_geo_para_frentes,
            bairros_centroides=bairros_centroides,
            curadoria=catalogo_curadoria,
            indices_territoriais=indices_territoriais,
        )
        if resultado_curadoria is not None:
            obra["nivel"] = resultado_curadoria["nivel"]
            obra["bairro"] = resultado_curadoria["bairro"]
            obra["prefeitura_bairro"] = resultado_curadoria["prefeitura_bairro"]
            obra["prefeituraBairro"] = resultado_curadoria["prefeitura_bairro"]
            obra["latitude"] = resultado_curadoria["latitude"]
            obra["longitude"] = resultado_curadoria["longitude"]
            obra["estagioAlocacao"] = resultado_curadoria["estagio"]
            obra["lastroCuradoria"] = resultado_curadoria.get("lastro_curadoria")
        candidatas = coletar_fichas_candidatas(obra, fichas_por_chave, fichas_por_id)
        if len(candidatas) > 1:
            obras_mescladas += 1
        ficha = mesclar_fichas_obra(obra, candidatas)
        frentes = resolver_frentes_medicao(
            obra=obra,
            bairros_geojson=bairros_geo_para_frentes,
            liquidacoes=ficha.get("liquidacoes"),
            pagamentos=ficha.get("pagamentos"),
            curadoria=catalogo_curadoria,
        )
        if frentes:
            ficha["frentesMedicao"] = frentes
        else:
            ficha.pop("frentesMedicao", None)
        sincronizar_obra_com_ficha(obra, ficha)
        fichas_consolidadas[str(obra_id)] = ficha

    concentracao_map, orfaos_removidos = finalizar_acervo_obras(
        obras_catalogo,
        fichas_consolidadas,
        obras_dir,
    )

    # Recalcula rollups territoriais e atualiza GeoJSONs se presentes
    bairros_rollup, prefeituras_rollup, opacidade = calcular_rollup_territorial(
        bairros_resumo=bairros_base,
        prefeituras_resumo=prefeituras_base,
        obras_alocadas=obras_catalogo,
    )

    if raw_bairros_geo is not None:
        generate_bairros_geojson(raw_bairros_geo, bairros_rollup, bairros_geo_path)

    pb_geo_path = output_path / "geo" / "prefeituras_bairro.geojson"
    if pb_geo_path.exists():
        with open(pb_geo_path, "r", encoding="utf-8") as f:
            raw_pb_geo = json.load(f)
        generate_prefeituras_geojson(raw_pb_geo, prefeituras_rollup, pb_geo_path)

    populacao_cidade = sum(int(b.get("populacao", 0)) for b in bairros_rollup)
    kpis_globais = calcular_kpis_globais(
        totalizador_transparencia={},
        obras_detalhadas=obras_catalogo,
        populacao_total_cidade=populacao_cidade,
        indicador_opacidade=opacidade,
    )

    index_file_path = output_path / f"index_{year}.json"
    generate_index_json(
        kpis_globais=kpis_globais,
        bairros_resumo=bairros_rollup,
        prefeituras_resumo=prefeituras_rollup,
        obras_detalhadas=obras_catalogo,
        year=year,
        output_path=index_file_path,
        concentracao_empreiteiras=concentracao_map,
        mandatos_disponiveis=mandatos_disponiveis,
    )
    escrever_indices_alias(index_file_path, output_path)

    arquivos_finais = len(list(obras_dir.glob("*.json")))
    fichas_finais = list(fichas_consolidadas.values())
    obras_com_cnpj = sum(1 for o in obras_catalogo if eh_cnpj_valido(o.get("cnpj")))

    return {
        "success": True,
        "output_dir": str(output_path),
        "ano": year,
        "total_obras_ativas": len(obras_catalogo),
        "obras_mescladas": obras_mescladas,
        "obras_com_empenhos": sum(1 for f in fichas_finais if f.get("empenhos")),
        "obras_com_liquidacoes": sum(1 for f in fichas_finais if f.get("liquidacoes")),
        "obras_com_pagamentos": sum(1 for f in fichas_finais if f.get("pagamentos")),
        "obras_com_aditivos": sum(1 for f in fichas_finais if f.get("aditivos")),
        "obras_com_dom": sum(
            1 for f in fichas_finais if eh_dom_valido((f.get("dom") or {}).get("nuDom"))
        ),
        "obras_com_cnpj": obras_com_cnpj,
        "total_empreiteiras": len(concentracao_map),
        "arquivos_orfaos_removidos": orfaos_removidos,
        "arquivos_finais_obras": arquivos_finais,
        "kpis_globais": kpis_globais,
    }


def main() -> None:
    """Ponto de entrada CLI para reconciliação canônica do acervo local."""
    parser = argparse.ArgumentParser(description="Reconciliação Canônica do Acervo Local de Obras")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="public/data",
        help="Diretório base dos artefatos estáticos (padrão: public/data)",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2025,
        help="Ano de referência do índice (padrão: 2025)",
    )
    args = parser.parse_args()

    try:
        resumo = reconciliar_acervo_local(output_dir=Path(args.output_dir), year=args.year)
        print(f"Reconciliação concluída com sucesso: {json.dumps(resumo, ensure_ascii=False)}")
    except Exception as exc:
        print(f"Erro na reconciliação canônica: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

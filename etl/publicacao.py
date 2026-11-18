"""Identificação e validação dos artefatos preparados pelo pipeline."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from uuid import uuid4
from etl.sources.geosalvador import geometria_valida


def _ler(path: Path):
    with path.open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _gravar(path: Path, conteudo) -> None:
    with path.open("w", encoding="utf-8") as arquivo:
        json.dump(conteudo, arquivo, ensure_ascii=False, indent=2, allow_nan=False)


def versao_publicada(diretorio: Path) -> Path | None:
    ponteiro = diretorio / "atual.json"
    if not ponteiro.exists():
        return None
    dados = _ler(ponteiro)
    versao = dados["versaoDados"]
    if not isinstance(versao, str) or len(versao) != 32 or any(c not in "0123456789abcdef" for c in versao):
        raise ValueError("Ponteiro de publicação inválido")
    if dados.get("caminho") != f"versoes/{versao}":
        raise ValueError("Caminho da versão publicada inválido")
    return diretorio / "versoes" / versao


def versao_anterior_valida(diretorio: Path) -> bool:
    """Somente um conjunto anterior íntegro e validado pode alimentar o incremento."""
    try:
        manifesto = _ler(diretorio / "manifesto.json")
        indice = _ler(diretorio / "index.json")
        atualizacao = indice["metadata"]["atualizacao"]
        arquivos = manifesto["arquivos"]
        if (
            not isinstance(arquivos, dict)
            or manifesto["versaoDados"] != atualizacao["versaoDados"]
            or manifesto["validacoes"] != "aprovadas"
            or manifesto["consultas"] != "concluidas"
            or atualizacao["validacoes"] != "aprovadas"
            or atualizacao["consultas"] != "concluidas"
        ):
            return False
        obrigatorios = {"index.json", "index_2025.json", "geo/bairros.geojson", "geo/prefeituras_bairro.geojson"}
        obrigatorios.update(f"obras/{obra['id']}.json" for obra in indice["obras"])
        if not obrigatorios.issubset(arquivos):
            return False
        for nome, digest in arquivos.items():
            caminho = Path(nome)
            if caminho.is_absolute() or ".." in caminho.parts:
                return False
            if hashlib.sha256((diretorio / caminho).read_bytes()).hexdigest() != digest:
                return False
        fichas = {p.relative_to(diretorio).as_posix() for p in (diretorio / "obras").glob("*.json")}
        if fichas != {nome for nome in arquivos if nome.startswith("obras/")}:
            return False
        return True
    except (OSError, ValueError, TypeError, KeyError):
        return False


def finalizar_versao(diretorio: Path, year: int, inicio: str, fim: str, referencia: str, limitacoes: list[str], total_obras: int, cache_path: Path | None = None) -> dict:
    """Associa todos os artefatos à mesma versão e verifica o conjunto preparado."""
    if not inicio or not fim or inicio > fim:
        raise ValueError("Intervalo de consultas inválido")
    versao = uuid4().hex
    indice = _ler(diretorio / f"index_{year}.json")
    if (not isinstance(indice, dict) or not isinstance(indice.get("obras"), list)
            or not isinstance(indice.get("metadata"), dict)
            or not isinstance(indice.get("bairros"), list)
            or not isinstance(indice.get("prefeituras_bairro"), list)
            or not isinstance(indice.get("kpis_globais"), dict)):
        raise ValueError("Índice de obras inválido")
    if len(indice["obras"]) != total_obras:
        raise ValueError("Consultas obrigatórias e obras não correspondem")
    metadados = {
        "versaoDados": versao,
        "dataReferenciaPagamentos": referencia,
        "inicioConsultas": inicio,
        "fimConsultas": fim,
        "consultas": "concluidas",
        "validacoes": "aprovadas",
        "consultasPagamentosPrevistas": total_obras,
        "consultasPagamentosConcluidas": total_obras,
        "coberturaHistorica": "nao_verificada",
        "limitacoesConhecidas": limitacoes,
    }

    arquivos = []
    for nome in ("bairros.geojson", "prefeituras_bairro.geojson"):
        caminho = diretorio / "geo" / nome
        malha = _ler(caminho)
        if malha.get("type") != "FeatureCollection" or not isinstance(malha.get("features"), list) or not malha["features"]:
            raise ValueError(f"Malha inválida: {nome}")
        for feature in malha["features"]:
            if (not isinstance(feature, dict) or not isinstance(feature.get("properties"), dict)
                    or not feature["properties"].get("nome") or not geometria_valida(feature.get("geometry"))):
                raise ValueError(f"Malha inválida: {nome}")
        malha["versaoDados"] = versao
        _gravar(caminho, malha)
        arquivos.append(caminho)

    ids = set()
    for obra in indice["obras"]:
        obra_id = str(obra["id"])
        if obra_id in ids or Path(obra_id).name != obra_id:
            raise ValueError("Identificador de obra inválido ou duplicado")
        ids.add(obra_id)
        caminho = diretorio / "obras" / f"{obra_id}.json"
        ficha = _ler(caminho)
        if str(ficha.get("id")) != obra_id:
            raise ValueError(f"Ficha incompatível com o índice: {obra_id}")
        if obra.get("valorPago") != (ficha.get("funilFinanceiro") or {}).get("valorPago"):
            raise ValueError(f"Pagamento da ficha diverge do índice: {obra_id}")
        ficha["versaoDados"] = versao
        _gravar(caminho, ficha)
        arquivos.append(caminho)
    fichas = {p.stem for p in (diretorio / "obras").glob("*.json")}
    if fichas != ids:
        raise ValueError("Fichas e índice não correspondem")

    # A data definitiva só é fixada depois da verificação integral do conjunto.
    metadados["concluidaEm"] = fim
    indice.setdefault("metadata", {})["atualizacao"] = metadados
    for antigo in diretorio.glob("index_*.json"):
        if antigo.name not in {f"index_{year}.json", "index_2025.json"}:
            antigo.unlink()
    for nome in {f"index_{year}.json", "index_2025.json", "index.json"}:
        caminho = diretorio / nome
        _gravar(caminho, indice)
        arquivos.append(caminho)
    cache = cache_path or diretorio / "geocoding_cache.json"
    if cache.is_file():
        arquivos.append(cache)
    manifesto = {
        "versaoDados": versao,
        "atualizacao": metadados,
        "arquivos": {
            caminho.relative_to(diretorio).as_posix(): hashlib.sha256(caminho.read_bytes()).hexdigest()
            for caminho in arquivos
        },
        "consultas": metadados["consultas"],
        "validacoes": metadados["validacoes"],
        "consultasPagamentosPrevistas": total_obras,
        "consultasPagamentosConcluidas": total_obras,
        "coberturaHistorica": metadados["coberturaHistorica"],
        "limitacoesConhecidas": metadados["limitacoesConhecidas"],
    }
    _gravar(diretorio / "manifesto.json", manifesto)
    if not versao_anterior_valida(diretorio):
        raise ValueError("Validação do manifesto da versão falhou")
    metadados["concluidaEm"] = datetime.now(timezone.utc).isoformat()
    for nome in {f"index_{year}.json", "index_2025.json", "index.json"}:
        caminho = diretorio / nome
        _gravar(caminho, indice)
        manifesto["arquivos"][nome] = hashlib.sha256(caminho.read_bytes()).hexdigest()
    _gravar(diretorio / "manifesto.json", manifesto)
    return metadados

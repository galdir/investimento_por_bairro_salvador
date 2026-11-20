from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


PAGES_SITE_LIMIT_BYTES = 1_000_000_000
MAX_PREVIOUS_VERSIONS = 2
VERSION_PATTERN = re.compile(r"^[0-9a-f]{32}$")
REQUIRED_FILES = (
    "index.json",
    "index_2025.json",
    "geo/bairros.geojson",
    "geo/prefeituras_bairro.geojson",
)


class PackageError(Exception):
    """A data package cannot be safely published."""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PackageError(f"JSON inválido ou ausente: {path}") from error


def _version_from_pointer(pointer_path: Path) -> str:
    pointer = _read_json(pointer_path)
    version = pointer.get("versaoDados") if isinstance(pointer, dict) else None
    if not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version):
        raise PackageError(f"Ponteiro de versão inválido: {pointer_path}")
    if pointer.get("caminho") != f"versoes/{version}":
        raise PackageError(f"Caminho do ponteiro não corresponde à versão {version}.")
    return version


def _deployment_time(deployment: dict[str, Any]) -> datetime:
    value = deployment.get("created_at")
    if not isinstance(value, str):
        raise PackageError(f"Deploy sem data de criação: {deployment.get('sha', 'SHA desconhecido')}")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise PackageError(f"Data de deploy inválida: {value}") from error


def _previous_successful_versions(
    current_version: str, deployments: list[dict[str, Any]]
) -> list[tuple[str, str]]:
    try:
        ordered = sorted(deployments, key=_deployment_time, reverse=True)
    except TypeError as error:
        raise PackageError("Histórico de deploys contém datas incompatíveis.") from error

    previous: list[tuple[str, str]] = []
    seen = {current_version}
    for deployment in ordered:
        sha = str(deployment.get("sha") or "SHA desconhecido")
        states = deployment.get("states")
        if not isinstance(states, list) or "success" not in states:
            continue

        version = deployment.get("versaoDados")
        if version is None:
            continue
        if not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version):
            raise PackageError(f"Deploy bem-sucedido {sha} aponta para versão inválida.")
        if version in seen:
            continue

        previous.append((version, sha))
        seen.add(version)
        if len(previous) == MAX_PREVIOUS_VERSIONS:
            break
    return previous


def _validate_version(version_directory: Path, version: str, deployment_sha: str) -> None:
    prefix = f"Versão {version} do deploy {deployment_sha}"
    if not version_directory.is_dir():
        raise PackageError(f"{prefix} não está completa no pacote fonte.")

    manifest_path = version_directory / "manifesto.json"
    manifest = _read_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("versaoDados") != version:
        raise PackageError(f"{prefix} tem um manifesto de outra versão.")

    hashes = manifest.get("arquivos")
    if not isinstance(hashes, dict):
        raise PackageError(f"{prefix} não tem hashes de arquivos no manifesto.")

    for relative_path, expected_hash in hashes.items():
        if not isinstance(relative_path, str) or not isinstance(expected_hash, str):
            raise PackageError(f"{prefix} contém um hash inválido no manifesto.")
        manifest_path_part = PurePosixPath(relative_path)
        if (
            manifest_path_part.is_absolute()
            or ".." in manifest_path_part.parts
            or "\\" in relative_path
            or any(":" in part for part in manifest_path_part.parts)
        ):
            raise PackageError(f"{prefix} contém um caminho inseguro: {relative_path}")
        file_path = version_directory.joinpath(*manifest_path_part.parts)
        if not file_path.is_file():
            raise PackageError(f"{prefix} não contém {relative_path}.")
        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise PackageError(f"{prefix} tem hash inválido em {relative_path}.")

    for required_file in REQUIRED_FILES:
        if required_file not in hashes:
            raise PackageError(f"{prefix} não lista {required_file} no manifesto.")

    indexes = []
    for relative_path in ("index.json", "index_2025.json"):
        index = _read_json(version_directory / relative_path)
        index_version = index.get("metadata", {}).get("atualizacao", {}).get("versaoDados")
        if index_version != version:
            raise PackageError(f"{prefix} tem {relative_path} de outra versão.")
        indexes.append(index)

    for relative_path in REQUIRED_FILES[2:]:
        layer = _read_json(version_directory / relative_path)
        if layer.get("versaoDados") != version:
            raise PackageError(f"{prefix} tem {relative_path} de outra versão.")

    obras = indexes[1].get("obras")
    if not isinstance(obras, list):
        raise PackageError(f"{prefix} não tem fichas listadas em index_2025.json.")
    expected_fichas: set[str] = set()
    for obra in obras:
        obra_id = str(obra.get("id")) if isinstance(obra, dict) else ""
        if not obra_id or Path(obra_id).name != obra_id:
            raise PackageError(f"{prefix} contém uma obra sem identificador válido.")
        ficha_path = f"obras/{obra_id}.json"
        expected_fichas.add(ficha_path)
        if ficha_path not in hashes:
            raise PackageError(f"{prefix} não lista a ficha {ficha_path} no manifesto.")
        ficha = _read_json(version_directory / ficha_path)
        if ficha.get("versaoDados") != version:
            raise PackageError(f"{prefix} tem a ficha {ficha_path} de outra versão.")

    actual_fichas = {
        path.relative_to(version_directory).as_posix()
        for path in (version_directory / "obras").glob("*.json")
    }
    if actual_fichas != expected_fichas:
        raise PackageError(f"{prefix} não contém exatamente as fichas do índice.")


def _remove_legacy_data(data_directory: Path) -> None:
    for name in ("geo", "obras", "geocoding_cache.json", "index.json", "index_2025.json"):
        path = data_directory / name
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def _site_size(directory: Path) -> int:
    return sum(path.stat().st_size for path in directory.rglob("*") if path.is_file())


def package_pages(dist_directory: Path, deployments_file: Path) -> list[str]:
    dist_directory = dist_directory.resolve()
    data_directory = dist_directory / "data"
    if not dist_directory.is_dir() or not data_directory.is_dir():
        raise PackageError(f"Diretório do build Pages ausente: {dist_directory}")

    current_version = _version_from_pointer(data_directory / "atual.json")
    history = _read_json(deployments_file)
    if not isinstance(history, list) or any(not isinstance(item, dict) for item in history):
        raise PackageError("Histórico de deploys do Pages inválido.")

    previous = _previous_successful_versions(current_version, history)
    retained = [current_version, *(version for version, _ in previous)]
    versions_directory = data_directory / "versoes"

    for version in retained:
        deployment_sha = "versão ativa" if version == current_version else next(
            sha for prior_version, sha in previous if prior_version == version
        )
        _validate_version(versions_directory / version, version, deployment_sha)

    for entry in versions_directory.iterdir():
        if entry.name not in retained:
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()

    _remove_legacy_data(data_directory)
    (data_directory / "versoes-servidas.json").write_text(
        json.dumps({"versoesDados": retained}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    package_versions = sorted(path.name for path in versions_directory.iterdir() if path.is_dir())
    if set(package_versions) != set(retained):
        raise PackageError("A lista de versões servidas diverge das pastas do pacote.")

    size_bytes = _site_size(dist_directory)
    if size_bytes > PAGES_SITE_LIMIT_BYTES:
        raise PackageError(
            f"Build do Pages tem {size_bytes} bytes; o limite documentado é {PAGES_SITE_LIMIT_BYTES}."
        )
    return retained


def main() -> int:
    parser = argparse.ArgumentParser(description="Retém as versões servidas no pacote do GitHub Pages.")
    parser.add_argument("--dist-dir", type=Path, required=True)
    parser.add_argument("--deployments-file", type=Path, required=True)
    arguments = parser.parse_args()

    try:
        retained = package_pages(arguments.dist_dir, arguments.deployments_file)
    except (PackageError, OSError) as error:
        print(f"Erro ao empacotar o Pages: {error}", file=sys.stderr)
        return 1

    print(f"Versões completas incluídas no Pages: {', '.join(retained)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

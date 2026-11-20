import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_SCRIPT = REPO_ROOT / "scripts" / "package_pages.py"


def _write_version(directory: Path, version: str) -> None:
    files = {
        "index.json": {"metadata": {"atualizacao": {"versaoDados": version}}, "obras": [{"id": 1001}]},
        "index_2025.json": {"metadata": {"atualizacao": {"versaoDados": version}}, "obras": [{"id": 1001}]},
        "geo/bairros.geojson": {"versaoDados": version, "features": []},
        "geo/prefeituras_bairro.geojson": {"versaoDados": version, "features": []},
        "obras/1001.json": {"versaoDados": version, "id": 1001},
    }
    hashes = {}
    for relative_path, payload in files.items():
        path = directory / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(payload, sort_keys=True).encode("utf-8")
        path.write_bytes(content)
        hashes[relative_path] = hashlib.sha256(content).hexdigest()

    (directory / "manifesto.json").write_text(
        json.dumps({"versaoDados": version, "arquivos": hashes}), encoding="utf-8"
    )


def _package_fixture(tmp_path: Path, versions: list[str], history: list[dict]) -> Path:
    dist = tmp_path / "dist"
    data = dist / "data"
    versions_directory = data / "versoes"
    versions_directory.mkdir(parents=True)
    for version in versions:
        _write_version(versions_directory / version, version)

    (data / "atual.json").write_text(
        json.dumps({"versaoDados": versions[0], "caminho": f"versoes/{versions[0]}"}),
        encoding="utf-8",
    )
    (tmp_path / "deployments.json").write_text(json.dumps(history), encoding="utf-8")
    return dist


def test_pages_package_keeps_active_and_two_most_recent_successful_versions(tmp_path: Path) -> None:
    current, recent, previous, older, failed, generated = [f"{number:032x}" for number in range(1, 7)]
    history = [
        {"sha": "failed-deploy", "created_at": "2026-11-19T12:00:00Z", "states": ["failure"], "versaoDados": failed},
        {"sha": "oldest-success", "created_at": "2026-11-15T12:00:00Z", "states": ["success"], "versaoDados": older},
        {"sha": "previous-success", "created_at": "2026-11-17T12:00:00Z", "states": ["inactive", "success"], "versaoDados": previous},
        {"sha": "same-version-again", "created_at": "2026-11-18T12:00:00Z", "states": ["success"], "versaoDados": current},
        {"sha": "recent-success", "created_at": "2026-11-18T18:00:00Z", "states": ["success"], "versaoDados": recent},
    ]
    dist = _package_fixture(tmp_path, [current, recent, previous, older, failed, generated], history)

    result = subprocess.run(
        [
            sys.executable,
            str(PACKAGE_SCRIPT),
            "--dist-dir",
            str(dist),
            "--deployments-file",
            str(tmp_path / "deployments.json"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    served_versions = [current, recent, previous]
    packaged_versions = sorted(path.name for path in (dist / "data" / "versoes").iterdir())
    public_list = json.loads((dist / "data" / "versoes-servidas.json").read_text(encoding="utf-8"))
    assert packaged_versions == sorted(served_versions)
    assert public_list == {"versoesDados": served_versions}
    assert set(public_list["versoesDados"]) == set(packaged_versions)


def test_pages_package_fails_when_a_successful_deployment_version_is_incomplete(tmp_path: Path) -> None:
    current, missing = [f"{number:032x}" for number in range(1, 3)]
    history = [
        {"sha": "successful-deploy", "created_at": "2026-11-18T12:00:00Z", "states": ["success"], "versaoDados": missing},
    ]
    dist = _package_fixture(tmp_path, [current], history)

    result = subprocess.run(
        [
            sys.executable,
            str(PACKAGE_SCRIPT),
            "--dist-dir",
            str(dist),
            "--deployments-file",
            str(tmp_path / "deployments.json"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "successful-deploy" in result.stderr

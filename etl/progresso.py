"""Persistência do progresso em um ref Git independente do conjunto publicado."""

import json
import subprocess
from pathlib import Path
from typing import Any


class ProgressoGit:
    """Atualiza um único snapshot remoto com comparação da versão anterior."""

    REF = "refs/heads/etl-progresso"

    def __init__(self, repositorio: Path):
        self.repositorio = Path(repositorio)
        self.versao = ""

    def _git(self, *args: str, entrada: bytes | None = None) -> bytes:
        resultado = subprocess.run(
            ["git", "-C", str(self.repositorio), *args], input=entrada,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if resultado.returncode:
            raise RuntimeError(f"Falha no armazenamento remoto de progresso: {resultado.stderr.decode('utf-8', errors='replace').strip()}")
        return resultado.stdout

    def carregar(self) -> dict[str, Any] | None:
        linhas = self._git("ls-remote", "--heads", "origin", self.REF).decode().splitlines()
        if not linhas:
            self.versao = ""
            return None
        self.versao = linhas[0].split()[0]
        self._git("fetch", "--no-tags", "origin", self.REF)
        recebido = self._git("rev-parse", "FETCH_HEAD").decode().strip()
        if recebido != self.versao:
            raise RuntimeError("O progresso remoto foi alterado durante a leitura")
        estado = json.loads(self._git("show", f"{self.versao}:estado.json"))
        if not isinstance(estado, dict):
            raise ValueError("Estado remoto de recuperação inválido")
        return estado

    def salvar(self, estado: dict[str, Any]) -> None:
        conteudo = json.dumps(estado, ensure_ascii=False).encode("utf-8")
        blob = self._git("hash-object", "-w", "--stdin", entrada=conteudo).decode().strip()
        arvore = self._git("mktree", entrada=f"100644 blob {blob}\testado.json\n".encode()).decode().strip()
        commit = self._git("-c", "user.name=ETL progress", "-c", "user.email=etl-progress@users.noreply.github.com",
                           "commit-tree", arvore, "-m", "Progresso da atualização ETL").decode().strip()
        self._git("push", f"--force-with-lease={self.REF}:{self.versao}", "origin", f"{commit}:{self.REF}")
        self.versao = commit


def confirmar_publicacao(repositorio: Path, tentativa: str) -> None:
    progresso = ProgressoGit(repositorio)
    estado = progresso.carregar()
    if estado is None:
        raise RuntimeError("Nenhuma tentativa para confirmar")
    historico = estado.get("historico") or []
    if not historico or historico[-1].get("tentativa") != tentativa or historico[-1].get("estado") != "preparada":
        raise RuntimeError("Tentativa preparada não corresponde à publicação")
    estado["concluida"] = True
    historico[-1]["estado"] = "concluida"
    progresso.salvar(estado)

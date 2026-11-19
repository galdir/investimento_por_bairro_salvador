"""Persistência por contrato em um ref Git independente do conjunto publicado."""

import base64
import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Any


LIMITE_CHECKPOINT_BYTES = 100 * 1024 * 1024
LIMITE_METADADOS_BYTES = 1024 * 1024
VERSAO_ESQUEMA = 1


def chave_contrato(unidade_gestora: Any, contrato_sigef: Any) -> str:
    """Retorna uma chave canônica e sem colisões estruturais para o par contratual."""
    identidade = [str(unidade_gestora), str(contrato_sigef)]
    return json.dumps(identidade, ensure_ascii=False, separators=(",", ":"))


class ProgressoGit:
    """Carrega e atualiza um snapshot remoto com comparação da revisão anterior."""

    REF = "refs/heads/etl-progresso"
    ARQUIVO_METADADOS = "metadados.json"
    DIRETORIO_CONTRATOS = "contratos"

    def __init__(self, repositorio: Path, ref: str | None = None):
        self.repositorio = Path(repositorio)
        self.ref = self.REF if ref is None else ref
        validacao_ref = subprocess.run(
            ["git", "check-ref-format", self.ref], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False,
        )
        if not self.ref.startswith("refs/heads/") or validacao_ref.returncode:
            raise ValueError("Ref de progresso deve ser um nome válido em refs/heads")
        self.versao = ""

    def _git(self, *args: str, entrada: bytes | None = None) -> bytes:
        resultado = subprocess.run(
            ["git", "-C", str(self.repositorio), *args], input=entrada,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if resultado.returncode:
            detalhe = resultado.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Falha no armazenamento remoto de progresso: {detalhe}")
        return resultado.stdout

    @classmethod
    def caminho_checkpoint(cls, identidade: list[str]) -> str:
        chave = chave_contrato(*identidade).encode("utf-8")
        nome = base64.urlsafe_b64encode(chave).decode("ascii").rstrip("=")
        return f"{cls.DIRETORIO_CONTRATOS}/{nome}.json"

    @staticmethod
    def _json(conteudo: Any) -> bytes:
        return json.dumps(
            conteudo, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")

    def carregar(self) -> dict[str, Any] | None:
        linhas = self._git("ls-remote", "--heads", "origin", self.ref).decode().splitlines()
        if not linhas:
            self.versao = ""
            return None
        self.versao = linhas[0].split()[0]
        self._git("fetch", "--no-tags", "origin", self.ref)
        recebido = self._git("rev-parse", "FETCH_HEAD").decode().strip()
        if recebido != self.versao:
            raise RuntimeError("O progresso remoto foi alterado durante a leitura")

        arquivos = self._git("ls-tree", "-r", "--name-only", self.versao).decode().splitlines()
        if self.ARQUIVO_METADADOS not in arquivos:
            return self._carregar_legado(arquivos)

        metadados = json.loads(self._git("show", f"{self.versao}:{self.ARQUIVO_METADADOS}"))
        if not isinstance(metadados, dict) or metadados.get("versao_esquema") != VERSAO_ESQUEMA:
            raise ValueError("Metadados remotos de recuperação inválidos")
        tentativa_original = metadados.get("tentativa_original")
        if not isinstance(tentativa_original, str) or not tentativa_original:
            raise ValueError("Identidade da tentativa remota inválida")
        if metadados.get("estado") not in {"pendente", "preparada", "concluida"}:
            raise ValueError("Estado remoto de recuperação inválido")
        referencia = metadados.get("referencia")
        if not self._data_iso_valida(referencia):
            raise ValueError("Data de referência remota inválida")
        if bool(metadados.get("concluida")) != (metadados["estado"] == "concluida"):
            raise ValueError("Estado concluído não corresponde aos metadados remotos")

        estado = {chave: valor for chave, valor in metadados.items() if chave != "versao_esquema"}
        estado["contratos"] = {}
        for caminho in arquivos:
            if caminho == self.ARQUIVO_METADADOS:
                continue
            if not caminho.startswith(f"{self.DIRETORIO_CONTRATOS}/") or not caminho.endswith(".json"):
                raise ValueError(f"Arquivo inesperado no progresso remoto: {caminho}")
            nome = caminho.removeprefix(f"{self.DIRETORIO_CONTRATOS}/")
            if "/" in nome:
                raise ValueError("Caminho de checkpoint remoto inválido")
            checkpoint = json.loads(self._git("show", f"{self.versao}:{caminho}"))
            if not isinstance(checkpoint, dict):
                raise ValueError("Checkpoint remoto inválido")
            identidade = checkpoint.get("identidade")
            if (not isinstance(identidade, list) or len(identidade) != 2
                    or not all(isinstance(parte, str) for parte in identidade)
                    or caminho != self.caminho_checkpoint(identidade)):
                raise ValueError("Identidade do contrato no checkpoint remoto inválida")
            if checkpoint.get("tentativa_original") != tentativa_original:
                raise ValueError("Checkpoint pertence a outra tentativa")
            if not isinstance(checkpoint.get("consulta"), dict) or not isinstance(checkpoint.get("ficha"), dict):
                raise ValueError("Dados do checkpoint remoto inválidos")
            estado["contratos"][chave_contrato(*identidade)] = checkpoint
        return estado

    def _carregar_legado(self, arquivos: list[str]) -> dict[str, Any]:
        """Migra o estado anterior sem reutilizar checkpoints sem identidade comprovável."""
        if "estado.json" not in arquivos:
            raise ValueError("Metadados remotos de recuperação ausentes")
        estado = json.loads(self._git("show", f"{self.versao}:estado.json"))
        if not isinstance(estado, dict):
            raise ValueError("Estado remoto de recuperação inválido")
        historico = estado.get("historico") or []
        tentativa_original = estado.get("tentativa_original")
        if not tentativa_original and historico:
            tentativa_original = historico[0].get("tentativa")
        if not isinstance(tentativa_original, str) or not tentativa_original:
            raise ValueError("Estado remoto não identifica a tentativa original")
        estado["tentativa_original"] = tentativa_original
        estado["estado"] = "concluida" if estado.get("concluida") else "pendente"
        estado["concluida"] = bool(estado.get("concluida"))
        estado["contratos"] = {}
        return estado

    def salvar(self, estado: dict[str, Any]) -> None:
        tentativa_original = estado.get("tentativa_original")
        if not isinstance(tentativa_original, str) or not tentativa_original:
            raise ValueError("Não é possível salvar progresso sem identificar a tentativa original")
        if estado.get("estado") not in {"pendente", "preparada", "concluida"}:
            raise ValueError("Estado de recuperação inválido")
        referencia = estado.get("referencia")
        if not self._data_iso_valida(referencia):
            raise ValueError("Data de referência inválida")
        if bool(estado.get("concluida")) != (estado["estado"] == "concluida"):
            raise ValueError("Estado concluído não corresponde aos metadados da tentativa")

        checkpoints: list[tuple[str, bytes]] = []
        for chave, valor in estado.get("contratos", {}).items():
            if not isinstance(valor, dict):
                raise ValueError("Checkpoint de contrato inválido")
            identidade = valor.get("identidade")
            if (not isinstance(identidade, list) or len(identidade) != 2
                    or not all(isinstance(parte, str) for parte in identidade)
                    or chave != chave_contrato(*identidade)):
                raise ValueError("Identidade do contrato não corresponde à chave do checkpoint")
            if valor.get("tentativa_original") != tentativa_original:
                raise ValueError("Checkpoint pertence a outra tentativa")
            if not isinstance(valor.get("consulta"), dict) or not isinstance(valor.get("ficha"), dict):
                raise ValueError("Dados do checkpoint de contrato inválidos")
            caminho = self.caminho_checkpoint(identidade)
            conteudo = self._json(valor)
            if len(conteudo) >= LIMITE_CHECKPOINT_BYTES:
                raise ValueError(f"Checkpoint excede o limite de {LIMITE_CHECKPOINT_BYTES} bytes: {caminho}")
            checkpoints.append((caminho, conteudo))

        metadados = {chave: valor for chave, valor in estado.items() if chave != "contratos"}
        metadados["versao_esquema"] = VERSAO_ESQUEMA
        conteudo_metadados = self._json(metadados)
        if len(conteudo_metadados) >= LIMITE_METADADOS_BYTES:
            raise ValueError("Metadados remotos de recuperação excedem 1 MiB")

        blobs = [(caminho, self._gravar_blob(conteudo)) for caminho, conteudo in checkpoints]
        blob_metadados = self._gravar_blob(conteudo_metadados)
        entradas_contratos = [
            f"100644 blob {blob}\t{caminho.removeprefix(f'{self.DIRETORIO_CONTRATOS}/')}\n"
            for caminho, blob in sorted(blobs)
        ]
        entradas = [f"100644 blob {blob_metadados}\t{self.ARQUIVO_METADADOS}\n"]
        if entradas_contratos:
            arvore_contratos = self._git(
                "mktree", entrada="".join(entradas_contratos).encode("utf-8"),
            ).decode().strip()
            entradas.append(f"040000 tree {arvore_contratos}\t{self.DIRETORIO_CONTRATOS}\n")
        arvore = self._git("mktree", entrada="".join(entradas).encode("utf-8")).decode().strip()
        commit = self._git(
            "-c", "user.name=ETL progress", "-c", "user.email=etl-progress@users.noreply.github.com",
            "commit-tree", arvore, "-m", "Progresso ETL por contrato",
        ).decode().strip()
        try:
            self._git("push", f"--force-with-lease={self.ref}:{self.versao}", "origin", f"{commit}:{self.ref}")
        except RuntimeError as exc:
            raise RuntimeError(
                f"Falha no armazenamento remoto de progresso (conflito de gravação concorrente ou erro de transporte): {exc}"
            ) from exc
        self.versao = commit

    def _gravar_blob(self, conteudo: bytes) -> str:
        return self._git("hash-object", "-w", "--stdin", entrada=conteudo).decode().strip()

    @staticmethod
    def _data_iso_valida(valor: Any) -> bool:
        if not isinstance(valor, str):
            return False
        try:
            return date.fromisoformat(valor).isoformat() == valor
        except ValueError:
            return False


def confirmar_publicacao(repositorio: Path, tentativa: str) -> None:
    progresso = ProgressoGit(repositorio)
    estado = progresso.carregar()
    if estado is None:
        raise RuntimeError("Nenhuma tentativa para confirmar")
    historico = estado.get("historico") or []
    if not historico or historico[-1].get("tentativa") != tentativa or historico[-1].get("estado") != "preparada":
        raise RuntimeError("Tentativa preparada não corresponde à publicação")
    estado["concluida"] = True
    estado["estado"] = "concluida"
    historico[-1]["estado"] = "concluida"
    progresso.salvar(estado)

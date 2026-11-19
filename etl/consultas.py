"""Contrato da coleta obrigatória de pagamentos para a publicação."""

from dataclasses import dataclass, field, replace
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any
from uuid import uuid4

from etl.domain.pagamentos import valor_informado_pagamento
from etl.sources import transparencia


@dataclass(frozen=True)
class LotePagamentos:
    """Ocorrências de uma resposta, identificada pela própria coleta, não pelo portal."""

    origem: str
    registros: list[dict[str, Any]]


@dataclass(frozen=True)
class ConsultaPagamentos:
    registros: list[dict[str, Any]]
    data_referencia: str
    concluida: bool
    validada: bool
    limitacoes_conhecidas: list[str] = field(default_factory=list)
    janela: dict[str, str] | None = None
    lotes: list[LotePagamentos] | None = None
    periodo_disponivel: dict[str, str] | None = None


def incorporar_lotes_pagamentos(resultado: ConsultaPagamentos) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Remove apenas a reaplicação exata de uma resposta da mesma coleta.

    A origem é criada para cada resposta recebida; IDs e semelhanças do portal
    não identificam lotes. Reutilizar uma origem com conteúdo diferente falha.
    """
    if resultado.lotes is None:
        return resultado.registros, []
    if not isinstance(resultado.lotes, list):
        raise ValueError("Lotes de pagamentos inválidos")
    recebidos: list[dict[str, Any]] = []
    incluidos: list[dict[str, Any]] = []
    origens: dict[str, tuple[str, int, int]] = {}
    repeticoes: list[dict[str, Any]] = []
    for indice, lote in enumerate(resultado.lotes):
        if (not isinstance(lote, LotePagamentos) or not isinstance(lote.origem, str) or not lote.origem.strip()
                or not isinstance(lote.registros, list) or not all(isinstance(p, dict) for p in lote.registros)):
            raise ValueError("Lote de pagamentos inválido")
        conteudo = json.dumps(lote.registros, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        recebidos.extend(lote.registros)
        if lote.origem in origens:
            conteudo_original, indice_original, inicio_original = origens[lote.origem]
            if conteudo_original != conteudo:
                raise ValueError("Origem de coleta reutilizada com conteúdo diferente")
            repeticoes.append({"origem": lote.origem, "sha256": hashlib.sha256(conteudo.encode("utf-8")).hexdigest(),
                               "ocorrenciasRemovidas": len(lote.registros), "loteOriginal": indice_original,
                               "inicioOriginal": inicio_original, "loteReprocessado": indice,
                               "evidencia": "mesma origem da coleta e conteúdo canônico idêntico"})
        else:
            origens[lote.origem] = (conteudo, indice, len(incluidos))
            incluidos.extend(lote.registros)
    if recebidos != resultado.registros:
        raise ValueError("Lotes não correspondem aos registros da consulta")
    return incluidos, repeticoes


def _valor_monetario(valor: Any) -> Decimal:
    if not isinstance(valor, str):
        raise ValueError("Valor monetário inválido na fonte")
    texto = valor.removeprefix("R$ ").strip()
    if not re.fullmatch(r"-?(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+),[0-9]{2}", texto):
        raise ValueError("Valor monetário inválido na fonte")
    try:
        return Decimal(texto.replace(".", "").replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError("Valor monetário inválido na fonte") from exc


def _metadados_pagina(resposta: Any) -> tuple[int, str, Decimal]:
    if not isinstance(resposta, dict) or not isinstance(resposta.get("dados"), list):
        raise ValueError("Resposta de pagamentos inválida")
    dados = resposta["dados"]
    paginacao = resposta.get("paginacao")
    totalizadores = resposta.get("totalizadores")
    if not isinstance(paginacao, dict) or not isinstance(totalizadores, dict):
        raise ValueError("Metadados de pagamentos ausentes")
    campos = [paginacao.get(campo) for campo in ("total", "tamanho", "paginas", "paginaAtual", "totalPagina")]
    if any(type(campo) is not int for campo in campos):
        raise ValueError("Metadados de pagamentos inválidos")
    total, tamanho, paginas, atual, total_pagina = campos
    if (total < 0 or tamanho <= 0 or paginas != (total + tamanho - 1) // tamanho
            or atual != 1 or total_pagina != len(dados) or len(dados) != min(total, tamanho)
            or not all(isinstance(item, dict) for item in dados)):
        raise ValueError("Metadados de pagamentos inconsistentes")
    return total, json.dumps(paginacao, sort_keys=True, ensure_ascii=False), _valor_monetario(totalizadores.get("Valor Pago"))


def conciliar_pagamentos(cd_unidade_gestora: Any, nu_contrato_sigef: Any, data_referencia: str,
                         data_inicio: str, data_fim: str) -> ConsultaPagamentos:
    """Consulta uma janela observada no grid; não habilita a rotina de produção."""
    referencia = date.fromisoformat(data_referencia)
    payload = {"dataInicio": data_inicio, "dataFim": data_fim, "filtros": [
        {"atributo": "CDUNIDADEGESTORA", "valor": cd_unidade_gestora},
        {"atributo": "NUCONTRATOSIGEF", "valor": nu_contrato_sigef},
    ]}
    pagina = "/obraspublicas/pagamentoRelacionado?pagina=1"
    limite_bytes = 8 * 1024 * 1024
    antes = _metadados_pagina(transparencia.consultar_com_tentativas(pagina, payload, max_bytes=limite_bytes))
    registros = transparencia.consultar_com_tentativas(
        "/obrasPublicas/pagamentoRelacionado/downloadDados", payload, max_bytes=limite_bytes,
    )
    depois = _metadados_pagina(transparencia.consultar_com_tentativas(pagina, payload, max_bytes=limite_bytes))
    if not isinstance(registros, list) or not all(isinstance(item, dict) for item in registros):
        raise ValueError("Exportação de pagamentos inválida")
    valores = [valor_informado_pagamento(item) for item in registros]
    soma = sum((_valor_monetario(valor) for valor in valores if valor not in (None, "")), Decimal(0))
    if antes != depois or len(registros) != antes[0] or soma != antes[-1]:
        raise ValueError("Conciliação de pagamentos divergente")
    incluidos = []
    for item in registros:
        try:
            data = datetime.strptime(item["dataPagamento"], "%d/%m/%Y").date()
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("Data de pagamento inválida") from exc
        if data <= referencia:
            incluidos.append(item)
    return ConsultaPagamentos(incluidos, data_referencia, True, True,
                              lotes=[LotePagamentos(str(uuid4()), incluidos)])


def multiconjunto_pagamentos(registros: list[dict[str, Any]]) -> Counter:
    """Representa cada ocorrência ignorando apenas o identificador volátil do portal."""
    return Counter(json.dumps({k: v for k, v in item.items() if k != "id"},
                              ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                   for item in registros)


def conciliar_janelas_pagamentos(cd_unidade_gestora: Any, nu_contrato_sigef: Any, data_referencia: str,
                                janelas: list[dict[str, str]]) -> ConsultaPagamentos:
    """Compara exportações brutas por ocorrência antes de aplicar o corte civil."""
    if not janelas:
        raise ValueError("Contrato sem janela observada no grid")
    primeira = None
    ocorrencias_anteriores = None
    for janela in janelas:
        resultado = conciliar_pagamentos(cd_unidade_gestora, nu_contrato_sigef, "9999-12-31",
                                         janela["dataInicio"], janela["dataFim"])
        ocorrencias = multiconjunto_pagamentos(resultado.registros)
        if ocorrencias_anteriores is not None and ocorrencias != ocorrencias_anteriores:
            raise ValueError("Exportações de pagamentos divergem entre janelas")
        if primeira is None:
            primeira = resultado.registros
            ocorrencias_anteriores = ocorrencias
    referencia = date.fromisoformat(data_referencia)
    incluidos = [item for item in primeira if datetime.strptime(item["dataPagamento"], "%d/%m/%Y").date() <= referencia]
    return ConsultaPagamentos(incluidos, data_referencia, True, True)


def coletar_pagamentos(cd_unidade_gestora: Any, nu_contrato_sigef: Any, data_referencia: str,
                       janelas: list[dict[str, str]] | None = None) -> ConsultaPagamentos:
    """Usa a janela observada mais antiga, após a equivalência no ensaio da carteira."""
    if (not str(cd_unidade_gestora or "").strip().isdigit()
            or not str(nu_contrato_sigef or "").strip() or not isinstance(janelas, list) or not janelas):
        raise ValueError("Contrato sem unidade, número ou janela válida do grid")
    periodos = []
    for janela in janelas:
        if not isinstance(janela, dict) or not isinstance(janela.get("dataInicio"), str) or not isinstance(janela.get("dataFim"), str):
            raise ValueError("Janela do grid inválida")
        inicio, fim = janela["dataInicio"], janela["dataFim"]
        try:
            inicio_data = datetime.fromisoformat(inicio.replace("Z", "+00:00"))
            fim_data = datetime.fromisoformat(fim.replace("Z", "+00:00"))
            if inicio_data.tzinfo is None or fim_data.tzinfo is None or inicio_data > fim_data:
                raise ValueError
        except ValueError as exc:
            raise ValueError("Janela do grid inválida") from exc
        periodos.append((inicio_data, fim_data, inicio, fim))
    _, _, inicio, fim = min(periodos)
    resultado = conciliar_pagamentos(cd_unidade_gestora, nu_contrato_sigef, data_referencia, inicio, fim)
    return replace(resultado, janela={"dataInicio": inicio, "dataFim": fim})

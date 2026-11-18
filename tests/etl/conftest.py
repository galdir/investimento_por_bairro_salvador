"""Fontes simuladas para os testes de integração do ETL."""

import pytest
from etl.consultas import ConsultaPagamentos

from etl.reference.sample_data import (
    SAMPLE_TRANSPARENCIA_ADITIVOS,
    SAMPLE_TRANSPARENCIA_DETALHES,
    SAMPLE_TRANSPARENCIA_DOTACAO,
)


@pytest.fixture
def portal_simulado(monkeypatch):
    def consultar(endpoint, payload, **kwargs):
        filtros = {item["atributo"]: item["valor"] for item in payload.get("filtros", [])}
        chave = f"{filtros.get('CDUNIDADEGESTORA')}_{filtros.get('NUCONTRATOSIGEF')}"
        if "detalhamentoObrasPublicas" in endpoint:
            return {"dados": SAMPLE_TRANSPARENCIA_DETALHES.get(chave, {})}
        if "/aditivo?" in endpoint:
            dados = SAMPLE_TRANSPARENCIA_ADITIVOS.get(chave, [])
        elif "/dotacao?" in endpoint:
            dados = SAMPLE_TRANSPARENCIA_DOTACAO.get(chave, [])
        else:
            dados = []
        return {"dados": dados, "paginacao": {"paginaAtual": 1, "paginas": 1, "total": len(dados), "totalPagina": len(dados), "tamanho": 10}}

    monkeypatch.setattr("etl.sources.transparencia._post_transparencia", consultar)
    monkeypatch.setattr("etl.runner.coletar_pagamentos", lambda ug, contrato, referencia, janelas: ConsultaPagamentos([], referencia, True, True))

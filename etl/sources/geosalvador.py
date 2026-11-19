"""Módulo de extração de dados geográficos do GeoSalvador (ArcGIS REST).

Responsável por consultar o MapServer oficial da Prefeitura de Salvador e
retornar as malhas cartográficas em formato GeoJSON e projeção EPSG:4326.
"""

import json
import logging
import ssl
import time
import urllib.error
import urllib.request
from http.client import HTTPException
from typing import Any
from shapely.geometry import shape

from etl.config import (
    GEOSALVADOR_MAPSERVER_BASE,
    LAYER_BAIRROS_OFICIAIS,
    LAYER_PREFEITURAS_BAIRRO,
)
from etl.domain.territorio import normalizar_nome_prefeitura_bairro


logger = logging.getLogger(__name__)


def geometria_valida(geometria: Any) -> bool:
    if not isinstance(geometria, dict) or geometria.get("type") not in {"Polygon", "MultiPolygon"}:
        return False
    try:
        poligono = shape(geometria)
        return not poligono.is_empty and poligono.is_valid
    except (TypeError, ValueError, KeyError):
        return False


def _camada_nao_encontrada(erro: urllib.error.HTTPError) -> bool:
    if erro.code != 404:
        return False
    try:
        with erro:
            return b"layer not found" in erro.read(2048).lower()
    except (OSError, HTTPException):
        return False


def _query_arcgis_geojson(layer_id: int, where_clause: str = "1=1", timeout: int = 15) -> dict[str, Any]:
    """Executa uma consulta ao endpoint ArcGIS REST do GeoSalvador solicitando GeoJSON em EPSG:4326.

    Sumário:
        Realiza requisição GET com parâmetros formatados para retorno de GeoJSON oficial.

    Descrição Estendida:
        Constrói a URL da consulta com os parâmetros `f=geojson`, `outSR=4326`, `outFields=*`
        e executa a chamada HTTP com tratamento de contexto SSL e timeouts configuráveis.
        Falhas de consulta são propagadas para impedir a publicação de dados incompletos.

    Argumentos:
        layer_id: Número identificador da camada no MapServer do GeoSalvador.
        where_clause: Expressão SQL para filtrar registros (padrão '1=1' para todos).
        timeout: Tempo limite da requisição em segundos.

    Retornos:
        Dicionário com a estrutura GeoJSON FeatureCollection.

    Erros:
        Lança RuntimeError caso a resposta remota contenha mensagem de erro do ArcGIS.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    query_params = (
        f"where={urllib.request.quote(where_clause)}"
        f"&outFields=*"
        f"&outSR=4326"
        f"&f=geojson"
        f"&returnGeometry=true"
    )
    url = f"{GEOSALVADOR_MAPSERVER_BASE}/{layer_id}/query?{query_params}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SalvadorObrasETL/1.0",
            "Accept": "application/json, application/geo+json, */*",
        },
    )
    for tentativa, espera in enumerate((10, 30, None), start=1):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                content = response.read().decode("utf-8", errors="replace")
            break
        except urllib.error.HTTPError as erro:
            if espera is None or not _camada_nao_encontrada(erro):
                logger.error("GeoSalvador camada %d: HTTP %d na tentativa %d.", layer_id, erro.code, tentativa)
                raise
            logger.warning(
                "GeoSalvador camada %d: HTTP 404 (Layer not found) na tentativa %d. Nova tentativa em %d s.",
                layer_id, tentativa, espera,
            )
            time.sleep(espera)

    data = json.loads(content)
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(f"Erro retornado pelo GeoSalvador Layer {layer_id}: {data['error']}")
    if (
        not isinstance(data, dict)
        or data.get("type") != "FeatureCollection"
        or not isinstance(data.get("features"), list)
        or not data["features"]
        or data.get("exceededTransferLimit") is True
    ):
        raise ValueError(f"GeoJSON inválido retornado pelo GeoSalvador Layer {layer_id}")
    nomes = ("NM_BAIRRO", "NOME_BAIRR", "nome") if layer_id == LAYER_BAIRROS_OFICIAIS else ("NM_PREFEITURA_BAIRRO", "SUBCLASSES", "NOMES", "nome")
    for feature in data["features"]:
        if not isinstance(feature, dict):
            raise ValueError(f"GeoJSON inválido retornado pelo GeoSalvador Layer {layer_id}")
        props = feature.get("properties")
        geometria = feature.get("geometry")
        if (not isinstance(props, dict) or not any(str(props.get(nome) or "").strip() for nome in nomes)
                or not geometria_valida(geometria)):
            raise ValueError(f"GeoJSON inválido retornado pelo GeoSalvador Layer {layer_id}")
    return data


def fetch_bairros_geojson() -> dict[str, Any]:
    """Obtém a malha de Bairros Oficiais de Salvador (Decreto nº 32.791/2020).

    Sumário:
        Consulta a Camada 164 do GeoSalvador e retorna a FeatureCollection em EPSG:4326.

    Descrição Estendida:
        Recupera os limites geográficos oficiais de todos os bairros municipais de Salvador
        conforme o Decreto nº 32.791/2020.

    Argumentos:
        Nenhum.

    Retornos:
        Dicionário contendo GeoJSON FeatureCollection de Bairros Oficiais.

    Erros:
        Propaga erros de rede e respostas inválidas.
    """
    return _query_arcgis_geojson(LAYER_BAIRROS_OFICIAIS)


def fetch_prefeituras_geojson() -> dict[str, Any]:
    """Obtém a malha de Prefeituras-Bairro de Salvador.

    Sumário:
        Consulta a Camada 7 do GeoSalvador e retorna a FeatureCollection em EPSG:4326.

    Descrição Estendida:
        Recupera os polígonos das divisões administrativas descentralizadas de Salvador (Prefeituras-Bairro).

    Argumentos:
        Nenhum.

    Retornos:
        Dicionário contendo GeoJSON FeatureCollection das Prefeituras-Bairro.

    Erros:
        Propaga erros de rede e respostas inválidas.
    """
    data = _query_arcgis_geojson(LAYER_PREFEITURAS_BAIRRO)
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        raw_name = (
            props.get("NM_PREFEITURA_BAIRRO")
            or props.get("SUBCLASSES")
            or props.get("NOMES")
            or props.get("nome")
            or ""
        )
        clean = normalizar_nome_prefeitura_bairro(raw_name)
        if clean:
            props["NM_PREFEITURA_BAIRRO"] = clean
            props["NOMES"] = clean
            props["nome"] = clean
    return data

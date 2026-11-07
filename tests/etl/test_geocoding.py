"""Testes unitários e de integração para o Funil de Alocação Territorial e Cache Incremental."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from etl.domain.geocoding import (
    GeocodingCache,
    calcular_centroides_bairros,
    classificar_alocacao_territorial,
)
from tests.etl.fixtures.sample_data import (
    SAMPLE_GEOSALVADOR_BAIRROS,
    SAMPLE_GEOSALVADOR_PREFEITURAS,
)


@pytest.fixture
def sample_centroides() -> dict[str, tuple[float, float]]:
    """Gera centróides para os bairros de teste a partir do GeoJSON de referência."""
    return calcular_centroides_bairros(SAMPLE_GEOSALVADOR_BAIRROS)


@pytest.fixture
def sample_cache(tmp_path: Path) -> GeocodingCache:
    """Cria uma instância isolada do cache em disco no diretório temporário."""
    cache_file = tmp_path / "geocoding_cache.json"
    return GeocodingCache(cache_file_path=cache_file)


def test_estagio_1_vincula_equipamento_de_saude_automaticamente(sample_centroides, sample_cache) -> None:
    """Verifica se obras que citam unidades de saúde recebem alocação Pontual exata sem API externa.

    Sumário:
        Testa o casamento de equipamentos públicos de saúde municipais no Estágio 1.

    Descrição Estendida:
        Fornece um contrato que cita expressamente a USF Pituba e valida que a função
        devolve o nível 'Pontual', as coordenadas geográficas exatas e o bairro correto.

    Argumentos:
        sample_centroides: Dicionário com centróides dos bairros oficiais.
        sample_cache: Instância de cache incremental em disco temporário.

    Retornos:
        None.

    Erros:
        Lança AssertionError caso o nível ou coordenadas divirjam do esperado.
    """
    obra = {
        "id": 1005,
        "cdUnidadeGestora": 1801,
        "nuContratoSigef": "088/2024",
        "dsObjeto": "Reforma e ampliação da Unidade de Saúde da Família - USF Pituba",
    }
    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        bairros_centroides=sample_centroides,
        cache=sample_cache,
    )

    assert resultado["nivel"] == "Pontual"
    assert resultado["bairro"] == "Pituba"
    assert resultado["prefeitura_bairro"] == "Barra/Pituba"
    assert resultado["latitude"] is not None
    assert resultado["longitude"] is not None
    assert "Equipamento" in resultado["estagio"]


def test_estagio_1_vincula_escola_municipal_automaticamente(sample_centroides, sample_cache) -> None:
    """Verifica se obras que citam escolas municipais recebem alocação Pontual exata.

    Sumário:
        Testa o casamento de equipamentos educacionais municipais no Estágio 1.

    Descrição Estendida:
        Fornece um contrato citando a Escola Municipal Maria Quitéria e valida o nível 'Pontual'.

    Argumentos:
        sample_centroides: Dicionário com centróides dos bairros oficiais.
        sample_cache: Instância de cache incremental em disco temporário.

    Retornos:
        None.

    Erros:
        Lança AssertionError caso a escola não seja pareada corretamente.
    """
    obra = {
        "id": 2001,
        "cdUnidadeGestora": 1501,
        "nuContratoSigef": "099/2024",
        "dsObjeto": "Reforma da Escola Municipal Professora Maria Quitéria",
    }
    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        bairros_centroides=sample_centroides,
        cache=sample_cache,
    )

    assert resultado["nivel"] == "Pontual"
    assert resultado["bairro"] == "Pituba"
    assert resultado["prefeitura_bairro"] == "Barra/Pituba"
    assert resultado["latitude"] == pytest.approx(-12.9965, rel=1e-3)
    assert resultado["longitude"] == pytest.approx(-38.4552, rel=1e-3)


def test_estagio_1_vincula_bairro_e_atribui_centroide(sample_centroides, sample_cache) -> None:
    """Verifica se obras citando apenas o Bairro recebem nível Bairro com as coordenadas do centróide.

    Sumário:
        Valida a alocação de nível Bairro e posicionamento no centróide do polígono oficial.

    Descrição Estendida:
        Passa um contrato cujo objeto cita o bairro Pituba e valida que as coordenadas atribuídas
        são rigorosamente as coordenadas de centróide do bairro.

    Argumentos:
        sample_centroides: Dicionário com centróides dos bairros oficiais.
        sample_cache: Instância de cache incremental em disco temporário.

    Retornos:
        None.

    Erros:
        Lança AssertionError caso o centróide não corresponda ao valor calculado.
    """
    obra = {
        "id": 1001,
        "cdUnidadeGestora": 2401,
        "nuContratoSigef": "001/2024",
        "dsObjeto": "Requalificação da Orla da Pituba com drenagem e nova ciclovia",
    }
    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        bairros_centroides=sample_centroides,
        cache=sample_cache,
    )

    assert resultado["nivel"] == "Bairro"
    assert resultado["bairro"] == "Pituba"
    assert resultado["prefeitura_bairro"] == "Barra/Pituba"
    assert resultado["latitude"] == sample_centroides["Pituba"][0]
    assert resultado["longitude"] == sample_centroides["Pituba"][1]


def test_estagio_1_vincula_lote_regional_a_prefeitura_bairro(sample_centroides, sample_cache) -> None:
    """Verifica se contratos de lote regional recebem nível Regional sem inflar bairros individuais.

    Sumário:
        Testa a atribuição de nível Regional (Prefeitura-Bairro) a contratos de manutenção e lotes.

    Descrição Estendida:
        Fornece um contrato que cita 'Lote 2 - Subúrbio Ferroviário' e garante que a prefeitura-bairro
        é associada, enquanto o bairro e as coordenadas permanecem nulos para evitar rateio arbitrário.

    Argumentos:
        sample_centroides: Dicionário com centróides dos bairros oficiais.
        sample_cache: Instância de cache incremental em disco temporário.

    Retornos:
        None.

    Erros:
        Lança AssertionError caso o nível ou a prefeitura-bairro estejam incorretos.
    """
    obra = {
        "id": 1003,
        "cdUnidadeGestora": 1501,
        "nuContratoSigef": "015/2024",
        "dsObjeto": "Manutenção preventiva em escolas do Lote 2 - Subúrbio Ferroviário",
    }
    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        bairros_centroides=sample_centroides,
        cache=sample_cache,
    )

    assert resultado["nivel"] == "Regional (Prefeitura-Bairro)"
    assert resultado["bairro"] is None
    assert resultado["prefeitura_bairro"] == "Subúrbio/Ilhas"
    assert resultado["latitude"] is None
    assert resultado["longitude"] is None


def test_contrato_sem_localizacao_vira_escopo_cidade(sample_centroides, sample_cache) -> None:
    """Verifica se obras genéricas sem logradouro/bairro são classificadas como Escopo Cidade.

    Sumário:
        Garante que contratos sem referência espacial componham o Escopo Cidade (Não-Localizado).

    Descrição Estendida:
        Um contrato com objeto genérico não pode inflar nenhum território ou prefeitura-bairro,
        devendo ser marcado para o indicador de transparência opaca.

    Argumentos:
        sample_centroides: Dicionário com centróides dos bairros oficiais.
        sample_cache: Instância de cache incremental em disco temporário.

    Retornos:
        None.

    Erros:
        Lança AssertionError caso o contrato seja atribuído indevidamente a um bairro.
    """
    obra = {
        "id": 1004,
        "cdUnidadeGestora": 3101,
        "nuContratoSigef": "042/2024",
        "dsObjeto": "Requalificação e modernização de praça esportiva com parque infantil e quadra poliesportiva",
    }
    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        bairros_centroides=sample_centroides,
        cache=sample_cache,
    )

    assert resultado["nivel"] == "Escopo Cidade (Não-Localizado)"
    assert resultado["bairro"] is None
    assert resultado["prefeitura_bairro"] is None
    assert resultado["latitude"] is None
    assert resultado["longitude"] is None


def test_cache_incremental_persiste_e_reaproveita_resultados(tmp_path: Path, sample_centroides) -> None:
    """Valida o funcionamento do cache incremental em disco em chamadas repetidas.

    Sumário:
        Assegura a persistência em disco do cache e o reuso em execuções subsequentes.

    Descrição Estendida:
        Executa a alocação em um cache inicial gravando no disco temporário e, em seguida,
        abre uma nova instância de cache lendo o arquivo gerado para verificar o hit de cache.

    Argumentos:
        tmp_path: Diretório temporário isolado do pytest.
        sample_centroides: Centróides dos bairros.

    Retornos:
        None.

    Erros:
        Lança AssertionError caso o arquivo não seja gravado ou o estágio não seja 'Cache'.
    """
    cache_path = tmp_path / "cache_persistente.json"
    cache1 = GeocodingCache(cache_file_path=cache_path)

    obra = {
        "id": 9999,
        "cdUnidadeGestora": 2401,
        "nuContratoSigef": "999/2024",
        "dsObjeto": "Reforma e ampliação da Unidade Básica de Saúde - UBS Liberdade",
    }

    # Primeira execução: preenche o cache
    res1 = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        bairros_centroides=sample_centroides,
        cache=cache1,
    )
    assert res1["nivel"] == "Pontual"
    assert res1["bairro"] == "Liberdade"
    assert cache_path.exists(), "O arquivo de cache deve ser gravado em disco."

    # Segunda execução com uma nova instância do cache lendo do mesmo arquivo
    cache2 = GeocodingCache(cache_file_path=cache_path)
    res2 = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        bairros_centroides=sample_centroides,
        cache=cache2,
    )

    assert res2["nivel"] == "Pontual"
    assert res2["estagio"] == "Cache"
    assert res2["bairro"] == "Liberdade"


def test_estagio_2_nominatim_com_mock_validando_ponto_em_salvador(sample_centroides, sample_cache) -> None:
    """Valida o Estágio 2 com chamada simulada ao Nominatim caindo dentro do polígono de Salvador.

    Sumário:
        Testa o fallback de geocodificação via OSM com verificação point-in-polygon.

    Descrição Estendida:
        Simula resposta do Nominatim com coordenadas que recaem no polígono da Pituba
        e garante que a alocação atribui nível 'Pontual' e identifica o Bairro Oficial.

    Argumentos:
        sample_centroides: Dicionário com centróides dos bairros oficiais.
        sample_cache: Instância de cache incremental em disco temporário.

    Retornos:
        None.

    Erros:
        Lança AssertionError caso o retorno do Nominatim não resulte em alocação Pontual.
    """
    obra = {
        "id": 8888,
        "cdUnidadeGestora": 2401,
        "nuContratoSigef": "888/2024",
        "dsObjeto": "Pavimentação asfáltica na Rua das Rosas sem bairro informado",
    }

    mock_nominatim_retorno = {
        "latitude": -12.995,
        "longitude": -38.455,
        "bairro": "Pituba",
        "prefeitura_bairro": "Barra/Pituba",
    }

    with patch("etl.domain.geocoding._fallback_nominatim", return_value=mock_nominatim_retorno):
        resultado = classificar_alocacao_territorial(
            obra=obra,
            bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
            bairros_centroides=sample_centroides,
            cache=sample_cache,
            habilitar_rede=True,
        )

    assert resultado["nivel"] == "Pontual"
    assert resultado["bairro"] == "Pituba"
    assert resultado["latitude"] == -12.995
    assert resultado["longitude"] == -38.455
    assert "Nominatim" in resultado["estagio"]


def test_cache_reavalia_entrada_nao_localizada_contra_malha_oficial(sample_centroides, sample_cache) -> None:
    """Verifica se uma obra previamente salva no cache como Não-Localizado é reconciliada para Bairro quando a malha oficial contém o topônimo."""
    obra = {
        "id": 7777,
        "cdUnidadeGestora": 2401,
        "nuContratoSigef": "777/2024",
        "dsObjeto": "Requalificação viária e drenagem na Pituba",
    }
    # Simula entrada obsoleta gravada no cache antes da normalização da malha
    sample_cache.set(
        2401,
        "777/2024",
        obra["dsObjeto"],
        {
            "nivel": "Escopo Cidade (Não-Localizado)",
            "bairro": None,
            "prefeitura_bairro": None,
            "latitude": None,
            "longitude": None,
            "estagio": "Não-Localizado (Transparência Opaca)",
        },
    )

    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        bairros_centroides=sample_centroides,
        cache=sample_cache,
    )

    assert resultado["nivel"] == "Bairro"
    assert resultado["bairro"] == "Pituba"
    assert resultado["prefeitura_bairro"] == "Barra/Pituba"
    assert resultado["latitude"] == sample_centroides["Pituba"][0]
    assert resultado["longitude"] == sample_centroides["Pituba"][1]
    assert resultado["estagio"] == "Cache"


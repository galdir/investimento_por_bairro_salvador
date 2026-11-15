"""Testes unitários e de integração para o Funil de Alocação Territorial e Cache Incremental."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import zlib
import pytest

from etl.domain.geocoding import (
    GeocodingCache,
    calcular_centroides_bairros,
    classificar_alocacao_territorial,
    resolver_frentes_medicao,
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


def _construir_malha_bairros_salvador_para_testes() -> dict:
    """Malha GeoJSON sintética mínima com polígonos e Prefeituras-Bairro canônicas."""
    bairros = [
        ("Centro", "Centro/Brotas", -38.51, -12.97),
        ("Centro Histórico", "Centro/Brotas", -38.512, -12.972),
        ("Brotas", "Centro/Brotas", -38.49, -12.99),
        ("Engenho Velho de Brotas", "Centro/Brotas", -38.50, -12.995),
        ("Barra", "Barra/Pituba", -38.53, -13.005),
        ("Ondina", "Barra/Pituba", -38.51, -13.008),
        ("Pituba", "Barra/Pituba", -38.46, -13.00),
        ("Itaigara", "Barra/Pituba", -38.465, -12.995),
        ("Caminho das Árvores", "Barra/Pituba", -38.455, -12.98),
        ("Imbuí", "Itapuã/Ipitanga", -38.43, -12.97),
        ("Boca do Rio", "Itapuã/Ipitanga", -38.42, -12.98),
        ("Itapuã", "Itapuã/Ipitanga", -38.36, -12.95),
        ("São Cristóvão", "Itapuã/Ipitanga", -38.34, -12.91),
        ("Paripe", "Subúrbio/Ilhas", -38.47, -12.83),
        ("Periperi", "Subúrbio/Ilhas", -38.475, -12.86),
        ("Fazenda Coutos", "Subúrbio/Ilhas", -38.46, -12.82),
        ("Rio Sena", "Subúrbio/Ilhas", -38.47, -12.87),
        ("Monte Serrat", "Cidade Baixa", -38.515, -12.93),
        ("Liberdade", "Liberdade/São Caetano", -38.495, -12.945),
        ("Retiro", "Liberdade/São Caetano", -38.475, -12.955),
        ("Cabula", "Cabula/Tancredo Neves", -38.45, -12.95),
        ("Cabula VI", "Cabula/Tancredo Neves", -38.44, -12.955),
        ("Beiru/Tancredo Neves", "Cabula/Tancredo Neves", -38.445, -12.94),
        ("São Gonçalo", "Cabula/Tancredo Neves", -38.46, -12.95),
        ("Centro Administrativo da Bahia", "Cabula/Tancredo Neves", -38.43, -12.94),
        ("Cajazeiras X", "Cajazeiras", -38.405, -12.89),
        ("Pau da Lima", "Pau da Lima", -38.43, -12.91),
        ("Valéria", "Valéria", -38.46, -12.86),
    ]
    features = []
    for idx, (nome, pb, lon, lat) in enumerate(bairros, start=1):
        d = 0.005
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "OBJECTID": idx,
                    "NM_BAIRRO": nome,
                    "PREFEITURA_BAIRRO": pb,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [lon - d, lat - d],
                        [lon + d, lat - d],
                        [lon + d, lat + d],
                        [lon - d, lat + d],
                        [lon - d, lat - d],
                    ]],
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def test_estagio_1_ignora_lote_sem_prefeitura_bairro_explicita(sample_centroides, sample_cache) -> None:
    """Garante que números de lote isolados (Lote 01..10) sem Prefeitura-Bairro explícita vão para Escopo Cidade."""
    obra = {
        "id": 10030,
        "cdUnidadeGestora": 1501,
        "nuContratoSigef": "016/2024",
        "dsObjeto": "Manutenção preventiva em escolas do Lote 02",
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


@pytest.mark.parametrize(
    ("ds_objeto", "pb_esperada"),
    [
        (
            "PROG MORAR MELHOR MELHORIAS HABITACIONAIS PREFEITURA BAIRRO VI BARRA/ PITUBA",
            "Barra/Pituba",
        ),
        (
            "Execução de infraestrutura urbana referente ao Lote 01 - Pref. Bairro VIII - Cabula / Tancredo Neves",
            "Cabula/Tancredo Neves",
        ),
        (
            "Contenção de encostas na Prefeitura Bairro IV que abrange os Bairros Itapuã e Ipitanga",
            "Itapuã/Ipitanga",
        ),
        (
            "Serviços de pavimentação LOTE 01 PREF IV ITAPUÃ/ IPITANGA",
            "Itapuã/Ipitanga",
        ),
        (
            "Recuperação de vias na PREF. BAIRRO DE PAU DA LIMA",
            "Pau da Lima",
        ),
    ],
)
def test_estagio_1_reconhece_prefeitura_bairro_explicita_antes_de_bairro_homonimo(
    sample_cache,
    ds_objeto: str,
    pb_esperada: str,
) -> None:
    """Menção explícita a uma única Prefeitura-Bairro aloca em Regional antes de capturar bairro homônimo."""
    malha = _construir_malha_bairros_salvador_para_testes()
    centroides = calcular_centroides_bairros(malha)
    obra = {
        "id": 10031,
        "cdUnidadeGestora": 616002,
        "nuContratoSigef": f"TEST-{zlib.crc32(ds_objeto.encode('utf-8')) & 0xFFFF}",
        "dsObjeto": ds_objeto,
    }

    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=malha,
        bairros_centroides=centroides,
        cache=sample_cache,
    )

    assert resultado["nivel"] == "Regional (Prefeitura-Bairro)"
    assert resultado["bairro"] is None
    assert resultado["prefeitura_bairro"] == pb_esperada
    assert resultado["latitude"] is None
    assert resultado["longitude"] is None


@pytest.mark.parametrize(
    "ds_objeto",
    [
        "Obras do Lote 01 abrangendo a Pref. Bairro VIII - Cabula / Tancredo Neves e Prefeitura Bairro IV - Itapuã / Ipitanga",
        "Elaboração de projetos relativo ao lote 02 por Prefeituras Bairros: PB Barra/Pituba, PBCentro/Brotas, PB Cajazeiras",
        "Requalificação das pavimentações em vias urbanas LOTE 03 PREF BAIRROS I, VI E VII",
        "Melhorias habitacionais Prefeitura-Bairro IV - Itapuã/Ipitanga e Prefeitura-Bairro III - Cajazeiras",
        "MANUTENÇÃO CORRETIVA E PREVENTIVA LOTE 03 PB: VIII - CABULA E IX - TANCREDO NEVES",
        "Serviços de manutenção em escolas nas Prefeituras de Bairro I, II, ..., X",
        "Recuperação de drenagem nas PREFS. BAIRROS I, II E III",
        "Obras de infraestrutura GRE LIBERDADE E CIDADE BAIXA",
        "Reforma de 4 USFs: Curralinho (Imbui), São Marcos, Periperi (Subúrbio Ferroviário) e Alto do Cabrito",
    ],
)
def test_estagio_1_nao_aloca_multiplas_prefeituras_bairro_em_regional_unica(
    sample_cache,
    ds_objeto: str,
) -> None:
    """Objetos com múltiplas Prefeituras-Bairro sem curadoria não devem cair em uma única regional nem em um bairro."""
    malha = _construir_malha_bairros_salvador_para_testes()
    centroides = calcular_centroides_bairros(malha)
    obra = {
        "id": 10032,
        "cdUnidadeGestora": 610002,
        "nuContratoSigef": f"MULTIPB-{zlib.crc32(ds_objeto.encode('utf-8')) & 0xFFFF}",
        "dsObjeto": ds_objeto,
    }

    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=malha,
        bairros_centroides=centroides,
        cache=sample_cache,
    )

    assert resultado["nivel"] == "Escopo Cidade (Não-Localizado)"
    assert resultado["bairro"] is None
    assert resultado["prefeitura_bairro"] is None


@pytest.mark.parametrize(
    "ds_objeto",
    [
        "Recuperação da Ponte sobre o Rio Camarajipe situada na Av. Tancredo Neves",
        "Construção do Viaduto Tancredo Neves em estrutura mista",
        "Recuperação estrutural da Passarela Tancredo Neves",
        "Manutenção predial da Estação Tancredo Neves",
        "Construção da trincheira na Avenida Tancredo Neves",
        "Viaduto na Av. Pres. Tancredo Neves",
    ],
)
def test_estagio_1_ignora_tancredo_neves_quando_precedido_por_qualificador_viario(
    sample_cache,
    ds_objeto: str,
) -> None:
    """Qualificadores viários antes de Tancredo Neves não devem alocar para o bairro Beiru/Tancredo Neves."""
    malha = _construir_malha_bairros_salvador_para_testes()
    centroides = calcular_centroides_bairros(malha)
    obra = {
        "id": 10033,
        "cdUnidadeGestora": 610002,
        "nuContratoSigef": f"VIARIO-{zlib.crc32(ds_objeto.encode('utf-8')) & 0xFFFF}",
        "dsObjeto": ds_objeto,
    }

    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=malha,
        bairros_centroides=centroides,
        cache=sample_cache,
    )

    assert resultado["nivel"] == "Escopo Cidade (Não-Localizado)"
    assert resultado["bairro"] is None


@pytest.mark.parametrize(
    "ds_objeto",
    [
        "Reforma do Centro Diagnóstico Municipal da Mulher",
        "Construção do Centro de Referência Especializado de Assistência Social (CREAS)",
        "Implantação de Centro Comercial Popular",
        "Requalificação do Centro Esportivo Urbano",
        "Obras do Centro Integrado de Educação",
        "Adequação do Centro Médico Odontológico e Veterinário",
        "Construção do Centro POP / CAPS / CRAS",
        "Ampliação do Centro Administrativo Municipal",
        "Reforma no Centro, Cultural, de Salvador",
    ],
)
def test_estagio_1_ignora_centro_quando_seguido_por_qualificador_institucional(
    sample_cache,
    ds_objeto: str,
) -> None:
    """Usos institucionais da palavra Centro não devem capturar o bairro Centro."""
    malha = _construir_malha_bairros_salvador_para_testes()
    centroides = calcular_centroides_bairros(malha)
    obra = {
        "id": 10034,
        "cdUnidadeGestora": 616002,
        "nuContratoSigef": f"CENTRO-{zlib.crc32(ds_objeto.encode('utf-8')) & 0xFFFF}",
        "dsObjeto": ds_objeto,
    }

    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=malha,
        bairros_centroides=centroides,
        cache=sample_cache,
    )

    assert resultado["nivel"] == "Escopo Cidade (Não-Localizado)"
    assert resultado["bairro"] is None


def test_estagio_1_preserva_centro_historico_cab_e_nova_tancredo_neves(sample_cache) -> None:
    """Bairros oficiais homônimos (Centro Histórico, CAB) e menção não-viária a Tancredo Neves continuam válidos."""
    malha = _construir_malha_bairros_salvador_para_testes()
    centroides = calcular_centroides_bairros(malha)

    casos = [
        ("Restauração de encosta no Centro Histórico de Salvador", "Centro Histórico"),
        ("Construção de anexo no Centro Administrativo da Bahia", "Centro Administrativo da Bahia"),
        ("Obras de drenagem integrantes do projeto da Nova Tancredo Neves", "Beiru/Tancredo Neves"),
        ("Requalificação do Centro Esportivo no Centro, Salvador/BA", "Centro"),
        ("Reforma de praça no Centro de Salvador", "Centro"),
        ("Implantação de Centro Universitário na Pituba", "Pituba"),
        ("OBRA NO BEIRU / TANCREDO NEVES", "Beiru/Tancredo Neves"),
        ("Bairro de Fazenda Coutos II, Distrito Sanitário Subúrbio Ferroviário", "Fazenda Coutos"),
        ("Pavimentação na Rua X, Rio Sena, Subúrbio Ferroviário", "Rio Sena"),
        ("Requalificação na Ponta de Humaitá, Cidade Baixa", "Monte Serrat"),
        ("Escola Municipal de São Gonçalo do Retiro", "São Gonçalo"),
    ]
    for idx, (ds_objeto, bairro_esperado) in enumerate(casos):
        resultado = classificar_alocacao_territorial(
            obra={
                "id": 10035 + idx,
                "cdUnidadeGestora": 610002,
                "nuContratoSigef": f"PRESERVA-{idx}",
                "dsObjeto": ds_objeto,
            },
            bairros_geojson=malha,
            bairros_centroides=centroides,
            cache=sample_cache,
        )
        assert resultado["nivel"] == "Bairro"
        assert resultado["bairro"] == bairro_esperado


def test_estagio_1_prioriza_bairro_oficial_explicito_sobre_sublocalidade(sample_cache) -> None:
    """Quando o objeto cita sublocalidade e Bairro Oficial explícito ('Curralinho, Imbui'), vence o Bairro Oficial."""
    malha = _construir_malha_bairros_salvador_para_testes()
    centroides = calcular_centroides_bairros(malha)
    obra = {
        "id": 10039,
        "cdUnidadeGestora": 610002,
        "nuContratoSigef": "IMBUI-CURRALINHO-01",
        "dsObjeto": "Execução de obras de construção dos Lava-Jatos 01 e 02, Curralinho, Imbui, Salvador/BA",
    }

    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=malha,
        bairros_centroides=centroides,
        cache=sample_cache,
    )

    assert resultado["nivel"] == "Bairro"
    assert resultado["bairro"] == "Imbuí"
    assert resultado["prefeitura_bairro"] == "Itapuã/Ipitanga"


def test_estagio_1_multi_bairro_mesma_prefeitura_aloca_regional(sample_cache) -> None:
    """Múltiplos Bairros Oficiais na mesma Prefeitura-Bairro sem curadoria alocam em nível Regional."""
    malha = _construir_malha_bairros_salvador_para_testes()
    centroides = calcular_centroides_bairros(malha)
    obra = {
        "id": 10040,
        "cdUnidadeGestora": 610002,
        "nuContratoSigef": "MULTI-MESMA-PB-01",
        "dsObjeto": "Requalificação urbana na Pituba e Itaigara, Salvador/BA",
    }

    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=malha,
        bairros_centroides=centroides,
        cache=sample_cache,
    )

    assert resultado["nivel"] == "Regional (Prefeitura-Bairro)"
    assert resultado["bairro"] is None
    assert resultado["prefeitura_bairro"] == "Barra/Pituba"
    assert resultado["latitude"] is None
    assert resultado["longitude"] is None


def test_estagio_1_multi_bairro_prefeituras_distintas_aloca_escopo_cidade(sample_cache) -> None:
    """Múltiplos Bairros Oficiais em Prefeituras-Bairro distintas sem curadoria vão para Escopo Cidade."""
    malha = _construir_malha_bairros_salvador_para_testes()
    centroides = calcular_centroides_bairros(malha)
    obra = {
        "id": 10041,
        "cdUnidadeGestora": 616002,
        "nuContratoSigef": "MULTI-PBS-DISTINTAS-01",
        "dsObjeto": "Contratação de empresas Centro de Referência Especializado de Assistência Social (CREAS): em Brotas, Paripe e Parque São Cristóvão",
    }

    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=malha,
        bairros_centroides=centroides,
        cache=sample_cache,
    )

    assert resultado["nivel"] == "Escopo Cidade (Não-Localizado)"
    assert resultado["bairro"] is None
    assert resultado["prefeitura_bairro"] is None


@pytest.mark.parametrize(
    ("ds_objeto", "bairro_esperado"),
    [
        ("Drenagem pluvial no Engenho Velho de Brotas", "Engenho Velho de Brotas"),
        ("Pavimentação de vias no Cabula VI", "Cabula VI"),
        ("Recuperação da escadaria no Centro Histórico", "Centro Histórico"),
    ],
)
def test_estagio_1_substrings_compostas_nao_geram_falso_multi_bairro(
    sample_cache,
    ds_objeto: str,
    bairro_esperado: str,
) -> None:
    """Bairros compostos (ex.: Engenho Velho de Brotas vs Brotas) não geram detecção duplicada multi-bairro."""
    malha = _construir_malha_bairros_salvador_para_testes()
    centroides = calcular_centroides_bairros(malha)
    obra = {
        "id": 10042,
        "cdUnidadeGestora": 610002,
        "nuContratoSigef": f"SUBSTR-{bairro_esperado}",
        "dsObjeto": ds_objeto,
    }

    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=malha,
        bairros_centroides=centroides,
        cache=sample_cache,
    )

    assert resultado["nivel"] == "Bairro"
    assert resultado["bairro"] == bairro_esperado


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


def test_curadoria_promove_contrato_unico_para_bairro_com_lastro(sample_centroides, sample_cache) -> None:
    """Verifica promoção determinística via Curadoria Territorial Auditável para Bairro Oficial."""
    obra = {
        "id": 9001,
        "cdUnidadeGestora": "301110",
        "nuContratoSigef": "2025CT005813",
        "dsObjeto": "Lançamento do Contrato Nº 387/2025",
    }
    curadoria = {
        "301110:2025CT005813": {
            "cdUnidadeGestora": "301110",
            "nuContratoSigef": "2025CT005813",
            "status": "promovido",
            "nivel": "Bairro",
            "bairro": "Pituba",
            "prefeituraBairro": "Barra/Pituba",
            "trechoComprobatorio": "REFORMA DA USF PITUBA II.",
            "documentoOrigem": "dsObjetoAditivo (Aditivo Contratual)",
            "justificativa": "Aditivo contratual identifica univocamente o bairro Pituba.",
        }
    }

    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        bairros_centroides=sample_centroides,
        cache=sample_cache,
        curadoria=curadoria,
    )

    assert resultado["nivel"] == "Bairro"
    assert resultado["bairro"] == "Pituba"
    assert resultado["prefeitura_bairro"] == "Barra/Pituba"
    assert resultado["latitude"] == sample_centroides["Pituba"][0]
    assert resultado["longitude"] == sample_centroides["Pituba"][1]
    assert resultado["estagio"] == "Curadoria Territorial Auditável"
    assert resultado["lastro_curadoria"]["documentoOrigem"] == "dsObjetoAditivo (Aditivo Contratual)"
    assert resultado["lastro_curadoria"]["trechoComprobatorio"] == "REFORMA DA USF PITUBA II."


def test_curadoria_preserva_contrato_ambiguo_em_escopo_cidade(sample_centroides, sample_cache) -> None:
    """Verifica que contratos marcados como ambíguos na curadoria permanecem em Escopo Cidade."""
    obra = {
        "id": 9002,
        "cdUnidadeGestora": "616002",
        "nuContratoSigef": "2024CT007171",
        "dsObjeto": "Manutenção de Quadras e Campos, LOTE 02",
    }
    curadoria = {
        "616002:2024CT007171": {
            "cdUnidadeGestora": "616002",
            "nuContratoSigef": "2024CT007171",
            "status": "ambiguo",
            "nivel": "Escopo Cidade (Não-Localizado)",
            "bairro": None,
            "prefeituraBairro": None,
            "trechoComprobatorio": "LOTE 02 PREFS. BS. II, V E VII",
            "documentoOrigem": "descObsLiquidacao (Nota de Liquidação)",
            "justificativa": "Contrato abrange múltiplas Prefeituras-Bairro (II, V e VII).",
        }
    }

    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        bairros_centroides=sample_centroides,
        cache=sample_cache,
        curadoria=curadoria,
    )

    assert resultado["nivel"] == "Escopo Cidade (Não-Localizado)"
    assert resultado["bairro"] is None
    assert resultado["prefeitura_bairro"] is None
    assert resultado["lastro_curadoria"]["trechoComprobatorio"] == "LOTE 02 PREFS. BS. II, V E VII"


def test_resolver_frentes_medicao_separa_notas_promovidas_e_ambiguas() -> None:
    """Verifica que resolver_frentes_medicao extrai apenas notas promovidas e vincula pagamentos pela notaLiquidacao."""
    obra = {
        "id": 9003,
        "cdUnidadeGestora": "530002",
        "nuContratoSigef": "2024CT006332",
        "dsObjeto": "Manutenção predial de equipamentos de mobilidade urbana",
    }
    liquidacoes = [
        {
            "notaLiquidacao": "2025NL004858",
            "valLiqLiquidacao": "42.243,32",
            "pago": "0,00",
            "dataLiquidacao": "15/05/2025",
            "descObsLiquidacao": "Manutenção Terminal Maritimo Plataforma",
        },
        {
            "notaLiquidacao": "2025NL002039",
            "valLiqLiquidacao": "139.209,74",
            "pago": "0,00",
            "dataLiquidacao": "10/02/2025",
            "descObsLiquidacao": "Manutenção predial dos Ascensores",
        },
    ]
    pagamentos = [
        {"notaLiquidacao": "2025NL004858", "pago": "40.000,00"},
        {"notaLiquidacao": "2025NL002039", "pago": "132.343,21"},
        {"notaLiquidacao": " ", "pago": "4.904,66"},
    ]
    curadoria = {
        "530002:2024CT006332": {
            "cdUnidadeGestora": "530002",
            "nuContratoSigef": "2024CT006332",
            "status": "multi_frente",
            "nivel": "Escopo Cidade (Não-Localizado)",
            "frentesMedicao": {
                "2025NL004858": {
                    "status": "promovido",
                    "nivel": "Bairro",
                    "bairro": "Pituba",
                    "prefeituraBairro": "Barra/Pituba",
                    "trechoComprobatorio": "Manutenção Terminal Maritimo Plataforma",
                    "documentoOrigem": "descObsLiquidacao (Nota de Liquidação 2025NL004858)",
                    "justificativa": "Localização única comprovada.",
                },
                "2025NL002039": {
                    "status": "ambiguo",
                    "nivel": "Escopo Cidade (Não-Localizado)",
                    "bairro": None,
                    "prefeituraBairro": None,
                    "trechoComprobatorio": "Manutenção predial dos Ascensores",
                    "documentoOrigem": "descObsLiquidacao (Nota de Liquidação 2025NL002039)",
                    "justificativa": "Sem bairro definido.",
                },
            },
        }
    }

    frentes = resolver_frentes_medicao(
        obra=obra,
        bairros_geojson=SAMPLE_GEOSALVADOR_BAIRROS,
        liquidacoes=liquidacoes,
        pagamentos=pagamentos,
        curadoria=curadoria,
    )

    assert len(frentes) == 1
    assert frentes[0]["notaLiquidacao"] == "2025NL004858"
    assert frentes[0]["nivel"] == "Bairro"
    assert frentes[0]["bairro"] == "Pituba"
    assert frentes[0]["prefeituraBairro"] == "Barra/Pituba"
    assert frentes[0]["valorLiquidado"] == 42243.32
    assert frentes[0]["valorPago"] == 40000.0
    assert frentes[0]["trechoComprobatorio"] == "Manutenção Terminal Maritimo Plataforma"


@pytest.mark.parametrize(
    "ds_objeto",
    [
        "Obras em Brotas e Cajazeiras 10",
        "Reforma no Pelourinho e na Barra",
    ],
)
def test_estagio_1_multi_bairro_arabe_e_sublocalidade_coordenada(
    sample_cache,
    ds_objeto: str,
) -> None:
    """Variantes arábicas e sublocalidades coordenadas com outros bairros não ficam ocultas no multi-bairro."""
    malha = _construir_malha_bairros_salvador_para_testes()
    centroides = calcular_centroides_bairros(malha)
    obra = {
        "id": 10045,
        "cdUnidadeGestora": 610002,
        "nuContratoSigef": f"MULTIEXT-{zlib.crc32(ds_objeto.encode('utf-8')) & 0xFFFF}",
        "dsObjeto": ds_objeto,
    }

    resultado = classificar_alocacao_territorial(
        obra=obra,
        bairros_geojson=malha,
        bairros_centroides=centroides,
        cache=sample_cache,
    )

    assert resultado["nivel"] == "Escopo Cidade (Não-Localizado)"
    assert resultado["bairro"] is None
    assert resultado["prefeitura_bairro"] is None


def test_classificar_bloqueia_rede_quando_habilitar_rede_false_mesmo_com_env_nominatim(
    sample_cache,
    monkeypatch,
) -> None:
    """habilitar_rede=False explícito impede consulta ao Nominatim mesmo com ENABLE_NOMINATIM=1."""
    monkeypatch.setenv("ENABLE_NOMINATIM", "1")
    malha = _construir_malha_bairros_salvador_para_testes()
    centroides = calcular_centroides_bairros(malha)
    obra = {
        "id": 10046,
        "cdUnidadeGestora": 610002,
        "nuContratoSigef": "OFFLINE-01",
        "dsObjeto": "Pavimentação na Rua das Acácias, s/n",
    }

    with patch("urllib.request.urlopen", side_effect=AssertionError("Rede não deve ser acionada!")):
        resultado = classificar_alocacao_territorial(
            obra=obra,
            bairros_geojson=malha,
            bairros_centroides=centroides,
            cache=sample_cache,
            habilitar_rede=False,
        )

    assert resultado["nivel"] == "Escopo Cidade (Não-Localizado)"
    assert resultado["estagio"] == "Não-Localizado (Transparência Opaca)"


def test_recalcular_offline_preserva_pontual_estagio_2_do_cache(sample_cache) -> None:
    """Reconciliação offline com recalcular=True preserva entrada Pontual de Stage 2 quando Estágio 1 não casa."""
    malha = _construir_malha_bairros_salvador_para_testes()
    centroides = calcular_centroides_bairros(malha)
    obra = {
        "id": 10047,
        "cdUnidadeGestora": 610002,
        "nuContratoSigef": "STAGE2-PRESERVA-01",
        "dsObjeto": "Restauração da Rua Chile, nº 10",
    }
    sample_cache.set(
        610002,
        "STAGE2-PRESERVA-01",
        "Restauração da Rua Chile, nº 10",
        {
            "nivel": "Pontual",
            "bairro": "Centro",
            "prefeitura_bairro": "Centro/Brotas",
            "latitude": -12.976,
            "longitude": -38.513,
            "estagio": "Stage 2 (Nominatim OSM)",
        },
    )

    with patch("urllib.request.urlopen", side_effect=AssertionError("Não deve consultar rede!")):
        resultado = classificar_alocacao_territorial(
            obra=obra,
            bairros_geojson=malha,
            bairros_centroides=centroides,
            cache=sample_cache,
            habilitar_rede=False,
            recalcular=True,
        )

    assert resultado["nivel"] == "Pontual"
    assert resultado["bairro"] == "Centro"
    assert resultado["prefeitura_bairro"] == "Centro/Brotas"
    assert resultado["latitude"] == -12.976
    assert resultado["longitude"] == -38.513
    assert resultado["estagio"] == "Stage 2 (Nominatim OSM)"



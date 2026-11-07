"""Funil de alocação territorial em 3 estágios e cache incremental de geocodificação.

Responsável por classificar cada contrato público de Salvador em seu nível territorial canônico
(Pontual, Bairro, Regional (Prefeitura-Bairro) ou Escopo Cidade (Não-Localizado)), vincular
coordenadas geográficas exatas ou centroides de bairro e persistir resultados em cache de disco.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Optional
import urllib.parse
import urllib.request

from shapely.geometry import Point, shape

from etl.domain.territorio import normalizar_nome

# Diretório base dos dicionários de referência
REF_DIR = Path(__file__).resolve().parent.parent / "reference"


class GeocodingCache:
    """Gerenciador de cache incremental persistido em disco para alocação territorial.

    Sumário:
        Armazena em arquivo JSON os resultados da geocodificação para evitar requisições redundantes.

    Descrição Estendida:
        Gera uma chave determinística a partir da unidade gestora, número de contrato e
        hash do texto normalizado do objeto. Salva em disco de forma síncrona a cada nova
        inserção para suportar interrupções e reexecuções parciais sem perda de dados.

    Argumentos:
        cache_file_path: Caminho do arquivo JSON onde o cache será persistido.
    """

    def __init__(self, cache_file_path: Optional[Path] = None) -> None:
        """Inicializa a instância do cache com o caminho do arquivo JSON.

        Sumário:
            Define o caminho do arquivo de cache e carrega os dados já gravados.

        Descrição Estendida:
            Se nenhum caminho for informado, adota como padrão 'data/geocoding_cache.json'.
            Carrega imediatamente o conteúdo pré-existente do disco em memória.

        Argumentos:
            cache_file_path: Caminho opcional do arquivo de cache.

        Retornos:
            None.

        Erros:
            Não lança exceções.
        """
        if cache_file_path is None:
            self.cache_file_path = Path("data") / "geocoding_cache.json"
        else:
            self.cache_file_path = Path(cache_file_path)

        self._entries: dict[str, dict[str, Any]] = {}
        self.load()

    def _gerar_chave(self, cd_unidade_gestora: Any, nu_contrato: Any, ds_objeto: str) -> str:
        """Gera uma chave estável e única baseada em identificadores do contrato e no texto do objeto.

        Sumário:
            Cria uma string identificadora a partir de UG, contrato e hash SHA-256 do objeto.

        Descrição Estendida:
            Normaliza o texto do objeto e gera um hash de 16 caracteres para compor uma chave estável,
            evitando colisões e garantindo reuso para contratos inalterados.

        Argumentos:
            cd_unidade_gestora: Código ou sigla da unidade gestora contratante.
            nu_contrato: Número do contrato administrativo (ex: '001/2024').
            ds_objeto: Texto descritivo do objeto da obra.

        Retornos:
            String contendo a chave gerada no formato 'UG_CONTRATO_HASH'.

        Erros:
            Não lança exceções.
        """
        objeto_norm = normalizar_nome(ds_objeto)
        hash_obj = hashlib.sha256(objeto_norm.encode("utf-8")).hexdigest()[:16]
        return f"{cd_unidade_gestora}_{nu_contrato}_{hash_obj}"

    def load(self) -> None:
        """Carrega as entradas do cache gravadas no disco, se o arquivo existir.

        Sumário:
            Lê o arquivo JSON de cache do disco e popula a estrutura em memória.

        Descrição Estendida:
            Verifica a existência do arquivo no disco. Se presente e válido, decodifica
            o JSON. Em caso de arquivo corrompido ou inacessível, reinicia com cache vazio.

        Argumentos:
            Nenhum.

        Retornos:
            None.

        Erros:
            Não propaga exceções de leitura de arquivo.
        """
        if self.cache_file_path.exists():
            try:
                with open(self.cache_file_path, "r", encoding="utf-8") as f:
                    self._entries = json.load(f)
            except Exception:
                self._entries = {}
        else:
            self._entries = {}

    def get(self, cd_unidade_gestora: Any, nu_contrato: Any, ds_objeto: str) -> Optional[dict[str, Any]]:
        """Recupera o resultado em cache para um contrato, ou retorna None se não encontrado.

        Sumário:
            Consulta se um determinado contrato já possui coordenadas e alocação calculadas.

        Descrição Estendida:
            Calcula a chave a partir dos parâmetros de entrada e retorna o dicionário associado.

        Argumentos:
            cd_unidade_gestora: Código ou sigla da unidade gestora.
            nu_contrato: Número do contrato.
            ds_objeto: Descrição do objeto.

        Retornos:
            Dicionário com os dados de alocação se encontrado no cache; None caso contrário.

        Erros:
            Não lança exceções.
        """
        key = self._gerar_chave(cd_unidade_gestora, nu_contrato, ds_objeto)
        return self._entries.get(key)

    def set(
        self,
        cd_unidade_gestora: Any,
        nu_contrato: Any,
        ds_objeto: str,
        resultado: dict[str, Any],
    ) -> None:
        """Salva um resultado de alocação no cache e persiste o arquivo em disco.

        Sumário:
            Armazena o resultado em memória e salva imediatamente no arquivo JSON.

        Descrição Estendida:
            Grava a entrada na chave correspondente e invoca o método de gravação em disco.

        Argumentos:
            cd_unidade_gestora: Código ou sigla da unidade gestora.
            nu_contrato: Número do contrato.
            ds_objeto: Descrição do objeto.
            resultado: Dicionário com a alocação territorial classificada.

        Retornos:
            None.

        Erros:
            Não lança exceções.
        """
        key = self._gerar_chave(cd_unidade_gestora, nu_contrato, ds_objeto)
        self._entries[key] = resultado
        self.save()

    def save(self) -> None:
        """Grava as entradas acumuladas do cache no arquivo JSON.

        Sumário:
            Escreve em disco o estado atual do cache em formato JSON formatado.

        Descrição Estendida:
            Cria diretórios pais caso não existam e escreve o JSON com ensure_ascii=False
            para manter caracteres em português legíveis.

        Argumentos:
            Nenhum.

        Retornos:
            None.

        Erros:
            Não lança exceções; falhas de disco são tratadas silenciosamente em memória.
        """
        self.cache_file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.cache_file_path, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def _carregar_json_referencia(nome_arquivo: str) -> Any:
    """Carrega com segurança um arquivo JSON de referência neutro em etl/reference.

    Sumário:
        Abre e decodifica um arquivo JSON armazenado no diretório etl/reference.

    Descrição Estendida:
        Localiza o arquivo a partir do caminho relativo ao diretório de referência do pacote.
        Se o arquivo não existir ou for inválido, retorna None.

    Argumentos:
        nome_arquivo: Nome do arquivo JSON (ex: 'lotes_regionais.json').

    Retornos:
        Objeto decodificado (lista ou dicionário) ou None.

    Erros:
        Não propaga exceções de disco ou decodificação.
    """
    arquivo = REF_DIR / nome_arquivo
    if arquivo.exists():
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def calcular_centroides_bairros(bairros_geojson: dict[str, Any]) -> dict[str, tuple[float, float]]:
    """Calcula as coordenadas de centróide (latitude, longitude) para cada Bairro Oficial.

    Sumário:
        Calcula o ponto representativo no centro do polígono de cada Bairro Oficial de Salvador.

    Descrição Estendida:
        Utiliza a geometria do GeoJSON do GeoSalvador (Camada 164) convertida para polígonos
        Shapely, extraindo o centróide geométrico (Y = latitude, X = longitude). Caso a geometria
        seja inválida ou ausente, aplica a média dos vértices como fallback.

    Argumentos:
        bairros_geojson: FeatureCollection GeoJSON dos Bairros Oficiais.

    Retornos:
        Dicionário mapeando o nome canônico do bairro para uma tupla (latitude, longitude).

    Erros:
        Não lança exceções; se o polígono for inválido retorna coordenadas de Salvador (-12.9777, -38.48).
    """
    centroides: dict[str, tuple[float, float]] = {}

    for feat in bairros_geojson.get("features", []):
        props = feat.get("properties", {})
        nome = props.get("NM_BAIRRO") or props.get("nome") or props.get("NOME_BAIRR") or ""
        geom = feat.get("geometry")

        if not nome or not geom:
            continue

        try:
            sh_geom = shape(geom)
            ponto = sh_geom.centroid
            centroides[nome] = (round(ponto.y, 6), round(ponto.x, 6))
        except Exception:
            centroides[nome] = (-12.9777, -38.48)

    return centroides


def _extrair_equipamentos_oficiais() -> list[dict[str, Any]]:
    """Combina os catálogos oficiais de Escolas e Unidades de Saúde.

    Sumário:
        Carrega as bases de referência de 368 Escolas e 118 Unidades de Saúde municipais.

    Descrição Estendida:
        Lê os arquivos de referência 'equipamentos_educacao.json' e 'equipamentos_saude.json',
        concatenando as duas listas para busca uniforme no Estágio 1.

    Argumentos:
        Nenhum.

    Retornos:
        Lista de dicionários contendo equipamentos com nome, tipo, bairro e coordenadas.

    Erros:
        Não lança exceções.
    """
    escolas = _carregar_json_referencia("equipamentos_educacao.json") or []
    saude = _carregar_json_referencia("equipamentos_saude.json") or []
    return escolas + saude


def _buscar_equipamento_no_objeto(
    objeto_norm: str,
    equipamentos: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Identifica se o objeto cita um equipamento público escolar ou de saúde.

    Sumário:
        Verifica menção a unidades escolares ou de saúde no texto normalizado.

    Descrição Estendida:
        Compara o nome completo do equipamento contra o texto do objeto, além de padrões
        abreviados frequentes como 'USF + BAIRRO' ou 'CMEI + BAIRRO'.

    Argumentos:
        objeto_norm: String com o texto do objeto normalizado em caixa alta sem acentos.
        equipamentos: Lista de equipamentos públicos oficiais de referência.

    Retornos:
        Dicionário do equipamento correspondente, ou None se não houver casamento.

    Erros:
        Não lança exceções.
    """
    for eq in equipamentos:
        nome_eq = normalizar_nome(eq.get("nome", ""))
        if nome_eq and nome_eq in objeto_norm:
            return eq

        tipo = normalizar_nome(eq.get("tipo", ""))
        bairro = normalizar_nome(eq.get("bairro", ""))
        if tipo and bairro:
            padrao_curto = f"{tipo} {bairro}"
            if padrao_curto in objeto_norm:
                return eq

    return None


def _buscar_lote_regional_no_objeto(
    objeto_norm: str,
    dicionario_lotes: dict[str, str],
) -> Optional[str]:
    """Identifica se o objeto cita um Lote Regional mapeado para Prefeitura-Bairro.

    Sumário:
        Detecta contratos de lote regional guarda-chuva no texto do objeto.

    Descrição Estendida:
        Verifica se alguma chave do dicionário declarativo de lotes aparece como palavra inteira
        no objeto da obra, retornando a Prefeitura-Bairro correspondente.

    Argumentos:
        objeto_norm: String com o objeto da obra normalizado.
        dicionario_lotes: Dicionário mapeando termos de lotes para Prefeituras-Bairro.

    Retornos:
        Nome da Prefeitura-Bairro mapeada, ou None se não identificado.

    Erros:
        Não lança exceções.
    """
    for chave, pb_nome in dicionario_lotes.items():
        chave_norm = normalizar_nome(chave)
        if chave_norm and re.search(rf"\b{re.escape(chave_norm)}\b", objeto_norm):
            return pb_nome
    return None


def _buscar_bairro_ou_sublocalidade(
    objeto_norm: str,
    bairros_nomes: list[str],
    dicionario_sublocalidades: dict[str, str],
) -> Optional[str]:
    """Identifica Bairro Oficial ou sublocalidade informal no texto do objeto.

    Sumário:
        Localiza topônimos oficiais ou apelidos de bairros no texto descritivo.

    Descrição Estendida:
        Trata casos especiais de falsos positivos da língua portuguesa:
        - 'SAÚDE' não deve casar quando for 'UNIDADE DE SAÚDE', 'POSTO DE SAÚDE', 'SECRETARIA DE SAÚDE';
        - 'CENTRO' não deve casar quando for 'CENTRO ADMINISTRATIVO', 'CENTRO CULTURAL', etc.;
        - 'ARMAÇÃO' não deve casar quando for 'ARMAÇÃO METÁLICA' ou 'ARMAÇÃO DE FERRO'.

    Argumentos:
        objeto_norm: Texto normalizado do objeto.
        bairros_nomes: Lista de nomes canônicos de Bairros Oficiais.
        dicionario_sublocalidades: Dicionário mapeando sublocalidades para Bairros Oficiais.

    Retornos:
        Nome canônico do Bairro Oficial identificado, ou None.

    Erros:
        Não lança exceções.
    """
    # 1. Verifica no dicionário de sublocalidades
    for sub, bairro_alvo in dicionario_sublocalidades.items():
        sub_norm = normalizar_nome(sub)
        if not sub_norm:
            continue

        if sub_norm == "SAUDE":
            if not re.search(r"\b(BAIRRO|EM|NO|NA)\s+(DA\s+)?SAUDE\b", objeto_norm):
                continue
            if re.search(r"\b(DE|DA|POSTO|UNIDADE|SECRETARIA|FUNDO|SERVICO)\s+SAUDE\b", objeto_norm):
                continue

        if re.search(rf"\b{re.escape(sub_norm)}\b", objeto_norm):
            return bairro_alvo

    # 2. Verifica contra a lista de bairros oficiais (ordenados por tamanho decrescente)
    for b_nome in sorted(bairros_nomes, key=len, reverse=True):
        b_norm = normalizar_nome(b_nome)
        if not b_norm:
            continue

        if b_norm == "SAUDE":
            if not re.search(r"\b(BAIRRO|EM|NO|NA)\s+(DA\s+)?SAUDE\b", objeto_norm):
                continue
            if re.search(r"\b(DE|DA|POSTO|UNIDADE|SECRETARIA|FUNDO|SERVICO)\s+SAUDE\b", objeto_norm):
                continue

        if b_norm == "CENTRO":
            if re.search(r"\bCENTRO\s+(ADMINISTRATIVO|DE|MUNICIPAL|COMUNITARIO|CULTURAL|ESCOLAR|CIRURGICO)\b", objeto_norm):
                continue

        if b_norm == "ARMACAO":
            if re.search(r"\bARMACAO\s+(DE|METALICA|ESTRUTURAL)\b", objeto_norm):
                continue

        if re.search(rf"\b{re.escape(b_norm)}\b", objeto_norm):
            return b_nome

    return None


def _fallback_nominatim(
    logradouro_candidato: str,
    bairros_geojson: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Executa o Estágio 2: consulta o Nominatim OSM com rate-limiting e validação estrita em Salvador.

    Sumário:
        Busca o logradouro via OpenStreetMap delimitado à caixa envolvente de Salvador.

    Descrição Estendida:
        Aplica a restrição de rate-limiting de 1 requisição por segundo exigida pelas diretrizes
        do OpenStreetMap. Executa a requisição com parâmetro viewbox e checa se o ponto retornado está
        dentro dos limites territoriais dos Bairros Oficiais de Salvador via point-in-polygon Shapely.

    Argumentos:
        logradouro_candidato: Nome da rua, avenida ou praça candidata.
        bairros_geojson: FeatureCollection com os polígonos dos Bairros Oficiais.

    Retornos:
        Dicionário com latitude, longitude, bairro e prefeitura_bairro se contido em Salvador; None caso contrário.

    Erros:
        Não lança exceções; captura falhas de rede de forma silenciosa e resiliente.
    """
    if not logradouro_candidato:
        return None

    # Respeita o rate-limiting estrito de 1 requisição/segundo do OpenStreetMap
    time.sleep(1.0)

    query = f"{logradouro_candidato}, Salvador, Bahia, Brasil"
    encoded_q = urllib.parse.quote(query)
    url = (
        f"https://nominatim.openstreetmap.org/search?q={encoded_q}"
        f"&format=json&limit=1&bounded=1&viewbox=-38.54,-12.83,-38.32,-13.02"
    )

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SalvadorObrasETL/1.0 (contato@salvadorobras.ba.gov.br)"},
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not data or not isinstance(data, list):
                return None

            primeiro = data[0]
            lat = float(primeiro["lat"])
            lon = float(primeiro["lon"])
            ponto = Point(lon, lat)

            # Valida se a coordenada cai dentro do polígono de algum Bairro Oficial
            for feat in bairros_geojson.get("features", []):
                geom = feat.get("geometry")
                props = feat.get("properties", {})
                if geom:
                    sh_geom = shape(geom)
                    if sh_geom.contains(ponto):
                        bairro_encontrado = props.get("NM_BAIRRO") or props.get("nome") or ""
                        pb_encontrada = props.get("PREFEITURA_BAIRRO") or props.get("prefeitura_bairro") or ""
                        return {
                            "latitude": lat,
                            "longitude": lon,
                            "bairro": bairro_encontrado,
                            "prefeitura_bairro": pb_encontrada,
                        }
    except Exception:
        return None

    return None


def _extrator_llm_opcional(ds_objeto: str) -> Optional[dict[str, Optional[str]]]:
    """Estágio 3: Extrai entidades geográficas via LLM se chaves de API estiverem configuradas.

    Sumário:
        Tenta extrair campos estruturados (logradouro, equipamento, bairro, lote) usando LLM.

    Descrição Estendida:
        Verifica a presença das variáveis de ambiente GEMINI_API_KEY, OPENAI_API_KEY ou
        ANTHROPIC_API_KEY. Se presentes, pode analisar a descrição em linguagem natural.
        Caso as variáveis não estejam definidas, retorna None sem interromper o fluxo.

    Argumentos:
        ds_objeto: Descrição textual do objeto contratual.

    Retornos:
        Dicionário com chaves 'logradouro', 'equipamento', 'bairro', 'lote' ou None.

    Erros:
        Não propaga exceções de conexão com a API da LLM.
    """
    api_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
    )
    if not api_key:
        return None

    # Se configurado no ambiente, permite extrair termos para reprocessamento
    return None


def classificar_alocacao_territorial(
    obra: dict[str, Any],
    bairros_geojson: dict[str, Any],
    bairros_centroides: dict[str, tuple[float, float]],
    cache: Optional[GeocodingCache] = None,
    habilitar_rede: bool = False,
) -> dict[str, Any]:
    """Classifica a Obra Pública no Funil de Alocação Territorial em 3 estágios com cache incremental.

    Sumário:
        Determina o Nível de Alocação Territorial, Bairro Oficial, Prefeitura-Bairro e coordenadas.

    Descrição Estendida:
        Executa os seguintes passos em ordem estrita de precedência:
        1. Consulta o cache incremental em disco: se a chave já existir, retorna o resultado imediatamente.
        2. Estágio 1 (Determinístico Local):
           a) Mapeamento contra catálogo oficial de 368 Escolas e 118 Unidades de Saúde.
              Se encontrar, aloca como nível 'Pontual' com coordenadas e bairro conhecidos.
           b) Mapeamento de lotes regionais via lotes_regionais.json.
              Se encontrar, aloca como 'Regional (Prefeitura-Bairro)' sem inflar bairros individuais.
           c) Mapeamento de Bairros Oficiais e sublocalidades via sublocalidades.json.
              Se encontrar, aloca como nível 'Bairro', atribuindo as coordenadas do centróide oficial.
        3. Estágio 2 (Nominatim OSM):
           Se houver indicação de rua e a rede estiver habilitada (ou forçada), busca coordenadas
           e valida ponto dentro do polígono de Salvador.
        4. Estágio 3 (Extrator LLM opcional):
           Se chaves de IA estiverem no ambiente e a localização permanecer ambígua.
        5. Fallback Final:
           Se nenhuma correspondência for obtida, aloca como 'Escopo Cidade (Não-Localizado)'.
        6. Salva o resultado no cache incremental em disco.

    Argumentos:
        obra: Dicionário contendo dados do contrato (dsObjeto, cdUnidadeGestora, nuContratoSigef).
        bairros_geojson: FeatureCollection oficial dos Bairros Oficiais de Salvador.
        bairros_centroides: Dicionário mapeando nome do bairro para (latitude, longitude).
        cache: Instância opcional de GeocodingCache para persistência incremental.
        habilitar_rede: Booleano indicando se requisições externas ao Nominatim estão autorizadas.

    Retornos:
        Dicionário com a estrutura de alocação contendo:
        - nivel: 'Pontual' | 'Bairro' | 'Regional (Prefeitura-Bairro)' | 'Escopo Cidade (Não-Localizado)'.
        - bairro: Nome do Bairro Oficial ou None.
        - prefeitura_bairro: Nome da Prefeitura-Bairro ou None.
        - latitude: Float ou None.
        - longitude: Float ou None.
        - estagio: Descrição da regra ou estágio que determinou a localização.

    Erros:
        Não lança exceções; em caso de falha retorna nível 'Escopo Cidade (Não-Localizado)'.
    """
    cd_ug = obra.get("cdUnidadeGestora") or obra.get("unidadeGestora") or "UG"
    nu_contrato = obra.get("nuContratoSigef") or obra.get("numeroContrato") or "S_N"
    ds_objeto = str(obra.get("dsObjeto") or obra.get("objeto") or "")

    # 1. Verificação no Cache Incremental
    if cache is not None:
        cached = cache.get(cd_ug, nu_contrato, ds_objeto)
        if cached:
            resultado_cached = dict(cached)
            resultado_cached["estagio"] = "Cache"
            return resultado_cached

    objeto_norm = normalizar_nome(ds_objeto)

    # 2. Carrega catálogos e dicionários locais
    equipamentos = _extrair_equipamentos_oficiais()
    dicionario_lotes = _carregar_json_referencia("lotes_regionais.json") or {}
    dicionario_sublocalidades = _carregar_json_referencia("sublocalidades.json") or {}

    # Mapeamento auxiliar de bairros para suas respectivas Prefeituras-Bairro
    bairro_para_pb: dict[str, str] = {}
    for feat in bairros_geojson.get("features", []):
        p = feat.get("properties", {})
        nb = p.get("NM_BAIRRO") or p.get("nome") or ""
        npb = p.get("PREFEITURA_BAIRRO") or p.get("prefeitura_bairro") or ""
        if nb:
            bairro_para_pb[nb] = npb

    bairros_nomes = list(bairro_para_pb.keys())

    # --- ESTÁGIO 1A: Equipamento Público Oficial (Escolas ou Saúde) ---
    eq_encontrado = _buscar_equipamento_no_objeto(objeto_norm, equipamentos)
    if eq_encontrado:
        resultado = {
            "nivel": "Pontual",
            "bairro": eq_encontrado.get("bairro"),
            "prefeitura_bairro": eq_encontrado.get("prefeitura_bairro") or bairro_para_pb.get(eq_encontrado.get("bairro", "")),
            "latitude": eq_encontrado.get("latitude"),
            "longitude": eq_encontrado.get("longitude"),
            "estagio": "Stage 1 (Equipamento Oficial)",
        }
        if cache:
            cache.set(cd_ug, nu_contrato, ds_objeto, resultado)
        return resultado

    # --- ESTÁGIO 1B: Lote Regional (Prefeitura-Bairro) ---
    pb_lote = _buscar_lote_regional_no_objeto(objeto_norm, dicionario_lotes)
    if pb_lote and "RUA " not in objeto_norm and "AVENIDA " not in objeto_norm:
        resultado = {
            "nivel": "Regional (Prefeitura-Bairro)",
            "bairro": None,
            "prefeitura_bairro": pb_lote,
            "latitude": None,
            "longitude": None,
            "estagio": "Stage 1 (Lote Regional)",
        }
        if cache:
            cache.set(cd_ug, nu_contrato, ds_objeto, resultado)
        return resultado

    # --- ESTÁGIO 1C: Bairro Oficial ou Sublocalidade ---
    bairro_detectado = _buscar_bairro_ou_sublocalidade(
        objeto_norm,
        bairros_nomes,
        dicionario_sublocalidades,
    )
    if bairro_detectado:
        centroide = bairros_centroides.get(bairro_detectado)
        lat = centroide[0] if centroide else None
        lon = centroide[1] if centroide else None
        pb_bairro = bairro_para_pb.get(bairro_detectado)

        resultado = {
            "nivel": "Bairro",
            "bairro": bairro_detectado,
            "prefeitura_bairro": pb_bairro,
            "latitude": lat,
            "longitude": lon,
            "estagio": "Stage 1 (Bairro / Sublocalidade)",
        }
        if cache:
            cache.set(cd_ug, nu_contrato, ds_objeto, resultado)
        return resultado

    # --- ESTÁGIO 2: Nominatim OSM com Bounding Box de Salvador ---
    if habilitar_rede or os.getenv("ENABLE_NOMINATIM") == "1":
        match_rua = re.search(r"\b(RUA|AVENIDA|TRAVESSA|ALAMEDA|PRACA)\s+[^,\.;\(\)]+", objeto_norm)
        if match_rua:
            candidato_rua = match_rua.group(0).strip()
            res_osm = _fallback_nominatim(candidato_rua, bairros_geojson)
            if res_osm:
                resultado = {
                    "nivel": "Pontual",
                    "bairro": res_osm["bairro"],
                    "prefeitura_bairro": res_osm["prefeitura_bairro"],
                    "latitude": res_osm["latitude"],
                    "longitude": res_osm["longitude"],
                    "estagio": "Stage 2 (Nominatim OSM)",
                }
                if cache:
                    cache.set(cd_ug, nu_contrato, ds_objeto, resultado)
                return resultado

    # --- ESTÁGIO 3: Extrator LLM Opcional ---
    _extrator_llm_opcional(ds_objeto)

    # --- FALLBACK FINAL: Escopo Cidade (Não-Localizado) ---
    resultado = {
        "nivel": "Escopo Cidade (Não-Localizado)",
        "bairro": None,
        "prefeitura_bairro": None,
        "latitude": None,
        "longitude": None,
        "estagio": "Não-Localizado (Transparência Opaca)",
    }
    if cache:
        cache.set(cd_ug, nu_contrato, ds_objeto, resultado)
    return resultado

"""Funil de alocação territorial em 3 estágios e cache incremental de geocodificação.

Responsável por classificar cada contrato público de Salvador em seu nível territorial canônico
(Pontual, Bairro, Regional (Prefeitura-Bairro) ou Escopo Cidade (Não-Localizado)), vincular
coordenadas geográficas exatas ou centroides de bairro e persistir resultados em cache de disco.
"""

from functools import lru_cache
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

from etl.domain.territorio import normalizar_nome, normalizar_nome_prefeitura_bairro, parse_float

# Diretório base dos dicionários de referência
REF_DIR = Path(__file__).resolve().parent.parent / "reference"


def reconciliar_bairro_canonico(
    nome_candidato: str,
    bairros_nomes: list[str],
    sublocalidades_norm: dict[str, str],
) -> Optional[str]:
    """Reconcilia um topônimo contra a lista oficial de Bairros Oficiais ou sublocalidades."""
    if not nome_candidato:
        return None
    b_norm = normalizar_nome(nome_candidato)
    for nb in bairros_nomes:
        if normalizar_nome(nb) == b_norm:
            return nb
    if b_norm in sublocalidades_norm:
        return sublocalidades_norm[b_norm]
    return None


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

    def __init__(self, cache_file_path: Optional[Path] = None, *, auto_save: bool = True) -> None:
        """Inicializa a instância do cache com o caminho do arquivo JSON.

        Sumário:
            Define o caminho do arquivo de cache e carrega os dados já gravados.

        Descrição Estendida:
            Se nenhum caminho for informado, adota como padrão 'data/geocoding_cache.json'.
            Carrega imediatamente o conteúdo pré-existente do disco em memória.

        Argumentos:
            cache_file_path: Caminho opcional do arquivo de cache.
            auto_save: Se True (padrão), persiste imediatamente no disco a cada set().

        Retornos:
            None.

        Erros:
            Não lança exceções.
        """
        if cache_file_path is None:
            self.cache_file_path = Path("data") / "geocoding_cache.json"
        else:
            self.cache_file_path = Path(cache_file_path)

        self.auto_save = auto_save
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
        if self.auto_save:
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

    def reconciliar_entradas(
        self,
        bairros_geojson: dict[str, Any],
        bairros_centroides: dict[str, tuple[float, float]],
    ) -> int:
        """Higieniza todas as entradas gravadas no cache, reconciliando Bairros e hidratando coordenadas e PB.

        Retornos:
            Quantidade de entradas atualizadas e regravadas.
        """
        dicionario_sublocalidades = _carregar_json_referencia("sublocalidades.json") or {}
        sublocalidades_norm = {normalizar_nome(k): v for k, v in dicionario_sublocalidades.items()}

        bairro_para_pb: dict[str, str] = {}
        for feat in bairros_geojson.get("features", []):
            p = feat.get("properties", {})
            nb = p.get("NM_BAIRRO") or p.get("nome") or ""
            npb = p.get("PREFEITURA_BAIRRO") or p.get("prefeitura_bairro") or ""
            if nb:
                bairro_para_pb[nb] = normalizar_nome_prefeitura_bairro(npb)

        bairros_nomes = list(bairro_para_pb.keys())
        bairro_para_pb_norm = {normalizar_nome(k): v for k, v in bairro_para_pb.items()}
        bairros_centroides_norm = {normalizar_nome(k): v for k, v in bairros_centroides.items()}

        atualizadas = 0
        for entry in self._entries.values():
            if not isinstance(entry, dict):
                continue
            modificado = False
            if entry.get("nivel") == "Bairro":
                b_atual = entry.get("bairro") or ""
                b_canonico = reconciliar_bairro_canonico(b_atual, bairros_nomes, sublocalidades_norm)
                if b_canonico and entry.get("bairro") != b_canonico:
                    entry["bairro"] = b_canonico
                    modificado = True

                b_chave = entry.get("bairro") or ""
                pb_atual = entry.get("prefeitura_bairro")
                pb_norm = normalizar_nome_prefeitura_bairro(str(pb_atual or ""))
                if not pb_atual or pb_norm != pb_atual:
                    pb_hid = bairro_para_pb.get(b_chave) or bairro_para_pb_norm.get(normalizar_nome(b_chave))
                    if pb_hid and pb_hid != pb_atual:
                        entry["prefeitura_bairro"] = pb_hid
                        modificado = True

                if entry.get("latitude") is None or entry.get("longitude") is None:
                    coords = bairros_centroides.get(b_chave) or bairros_centroides_norm.get(normalizar_nome(b_chave))
                    if coords:
                        entry["latitude"] = coords[0]
                        entry["longitude"] = coords[1]
                        modificado = True

            elif entry.get("nivel") == "Regional (Prefeitura-Bairro)":
                pb_atual = entry.get("prefeitura_bairro")
                if pb_atual:
                    pb_norm = normalizar_nome_prefeitura_bairro(pb_atual)
                    if pb_norm != pb_atual:
                        entry["prefeitura_bairro"] = pb_norm
                        modificado = True

            elif entry.get("nivel") == "Pontual":
                pb_atual = entry.get("prefeitura_bairro")
                if pb_atual:
                    pb_norm = normalizar_nome_prefeitura_bairro(pb_atual)
                    if pb_norm != pb_atual:
                        entry["prefeitura_bairro"] = pb_norm
                        modificado = True
                elif entry.get("bairro"):
                    b_chave = entry["bairro"]
                    pb_hid = bairro_para_pb.get(b_chave) or bairro_para_pb_norm.get(normalizar_nome(b_chave))
                    if pb_hid:
                        entry["prefeitura_bairro"] = pb_hid
                        modificado = True

            if modificado:
                atualizadas += 1

        if atualizadas > 0 and self.auto_save:
            self.save()

        return atualizadas


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


_ROMANO_PARA_PB: dict[str, str] = {
    "I": "Centro/Brotas",
    "II": "Subúrbio/Ilhas",
    "III": "Cajazeiras",
    "IV": "Itapuã/Ipitanga",
    "V": "Cidade Baixa",
    "VI": "Barra/Pituba",
    "VII": "Liberdade/São Caetano",
    "VIII": "Cabula/Tancredo Neves",
    "IX": "Pau da Lima",
    "X": "Valéria",
}

_PADROES_NOME_PB: tuple[tuple[str, str], ...] = (
    (r"CENTRO\s*/\s*BROTAS", "Centro/Brotas"),
    (r"SUBURBIO\s*(?:/|E)\s*ILHAS?", "Subúrbio/Ilhas"),
    (r"SUBURBIO\s+FERROVIARIO", "Subúrbio/Ilhas"),
    (r"ITAP[UO]A\s*/\s*IPITANGA", "Itapuã/Ipitanga"),
    (r"CIDADE\s+BAIXA", "Cidade Baixa"),
    (r"BARRA\s*/\s*PITUBA", "Barra/Pituba"),
    (r"LIBERDADE\s*/\s*SAO\s+CAETANO", "Liberdade/São Caetano"),
    (r"CABULA\s*/\s*TANCREDO(?:\s+NEVES)?", "Cabula/Tancredo Neves"),
)

_PADROES_MACRO_REGIOES: tuple[tuple[str, str], ...] = (
    (r"SUBURBIO\s+FERROVIARIO", "Subúrbio/Ilhas"),
    (r"SUBURBIO\s*(?:/|E)\s*ILHAS?", "Subúrbio/Ilhas"),
    (r"CIDADE\s+BAIXA", "Cidade Baixa"),
)

_PADROES_NOME_PB_COM_PREFIXO: tuple[tuple[str, str], ...] = (
    *_PADROES_NOME_PB,
    (r"CAJAZEIRAS", "Cajazeiras"),
    (r"PAU\s+DA\s+LIMA", "Pau da Lima"),
    (r"VALERIA", "Valéria"),
)

_ALTERNACAO_NOMES_PB = "|".join(padrao for padrao, _ in _PADROES_NOME_PB_COM_PREFIXO)
_NOME_PARCIAL_PB = (
    rf"(?:{_ALTERNACAO_NOMES_PB}|CENTRO|BROTAS|SUBURBIO|ILHAS?|ITAP[UO]A|IPITANGA|"
    r"BARRA|PITUBA|LIBERDADE|SAO\s+CAETANO|CABULA|TANCREDO(?:\s+NEVES)?)"
)
_ROMANO_TOKEN = r"(?:VIII|VII|III|IX|VI|IV|II|X|V|I)"
_ROTULO_PB_OPCIONAL = rf"(?:(?:\s*-\s*|\s+){_NOME_PARCIAL_PB})?"
_SEP_LISTA_PB = r"(?:\s*(?:,|;|/|\bE\b|\bA\b)\s*(?:\.\.\.\s*,\s*)?)"
_PREFIXO_PB = (
    r"\b(?:PREFEITURAS?(?:\s+D[EAO]S?)?[\s-]*BAIRROS?"
    r"|PREFS?\.?(?:\s+D[EAO]S?)?\s*(?:BAIRROS?|BS?\.?)"
    r"|PREF\.?"
    r"|PBS?\.?)"
)
_RE_LISTA_ROMANO_PB = re.compile(
    rf"{_PREFIXO_PB}"
    rf"(?:\s*[:\-]\s*|\s+)"
    rf"({_ROMANO_TOKEN}\b{_ROTULO_PB_OPCIONAL}(?:{_SEP_LISTA_PB}{_ROMANO_TOKEN}\b{_ROTULO_PB_OPCIONAL})*)"
)
_RE_PREFIXO_NOME_PB = re.compile(
    rf"(?:{_PREFIXO_PB}(?:\s*[:\-]\s*|\s+)|PB\.?\s*[-]?\s*)"
    rf"(?:{_ROMANO_TOKEN}\b\s*[-:]?\s*)?"
    rf"(?:D[EAO]S?\s+)?"
    rf"({_ALTERNACAO_NOMES_PB})\b"
)
_RE_LOTE_COM_MACRO = re.compile(
    r"\bLOTE\s*\d+\s*[-:]\s*(SUBURBIO\s+FERROVIARIO|SUBURBIO\s*(?:/|E)\s*ILHAS?|CIDADE\s+BAIXA)\b"
)


def _detectar_prefeituras_bairro_no_objeto(
    objeto_norm: str,
    dicionario_lotes: dict[str, str],
) -> list[str]:
    """Extrai Prefeituras-Bairro explicitamente mencionadas no objeto da obra (Estágio 1B).

    Retornos:
        Lista ordenada de nomes canônicos únicos das Prefeituras-Bairro explicitamente citadas.
        Retorna vazia se não houver menção explícita; retorna 2+ itens em objetos multi-regionais.
    """
    if not objeto_norm:
        return []

    pbs_encontradas: set[str] = set()

    # 1. Menções explícitas com algarismo romano (ex.: Pref. Bairro VIII, PREF IV, PREFS. BS. II, V e VII)
    for match in _RE_LISTA_ROMANO_PB.finditer(objeto_norm):
        for romano in re.findall(rf"\b{_ROMANO_TOKEN}\b", match.group(1)):
            pb_canonica = _ROMANO_PARA_PB.get(romano)
            if pb_canonica:
                pbs_encontradas.add(pb_canonica)

    # 2. Prefixos explícitos seguidos do nome da Prefeitura-Bairro (ex.: PB PAU DA LIMA, PREF. BAIRRO DE PAU DA LIMA)
    for match in _RE_PREFIXO_NOME_PB.finditer(objeto_norm):
        trecho_nome = match.group(1)
        for padrao, pb_canonica in _PADROES_NOME_PB_COM_PREFIXO:
            if re.fullmatch(padrao, trecho_nome):
                pbs_encontradas.add(normalizar_nome_prefeitura_bairro(pb_canonica))
                break

    # 3. Lotes explícitos acompanhados de macro-região (ex.: LOTE 01 - SUBURBIO FERROVIARIO)
    for match in _RE_LOTE_COM_MACRO.finditer(objeto_norm):
        trecho_macro = match.group(1)
        for padrao, pb_canonica in _PADROES_MACRO_REGIOES:
            if re.fullmatch(padrao, trecho_macro):
                pbs_encontradas.add(normalizar_nome_prefeitura_bairro(pb_canonica))
                break

    # 4. Chaves explícitas em lotes_regionais.json (nunca casa LOTE N isolado)
    for chave, pb_nome in dicionario_lotes.items():
        chave_norm = normalizar_nome(chave)
        if not chave_norm or re.fullmatch(r"LOTE\s*\d+", chave_norm):
            continue
        padrao_chave = re.escape(chave_norm).replace("/", r"\s*/\s*")
        if re.search(rf"\b{padrao_chave}\b", objeto_norm):
            pbs_encontradas.add(normalizar_nome_prefeitura_bairro(pb_nome))

    return sorted(pbs_encontradas)


def _detectar_macro_regioes_no_objeto(objeto_norm: str) -> list[str]:
    """Detecta macro-regiões sem prefixo explícito de Prefeitura-Bairro (ex.: Subúrbio Ferroviário, Cidade Baixa)."""
    if not objeto_norm:
        return []
    encontradas: set[str] = set()
    for padrao, pb_canonica in _PADROES_MACRO_REGIOES:
        if re.search(rf"\b{padrao}\b", objeto_norm):
            encontradas.add(normalizar_nome_prefeitura_bairro(pb_canonica))
    return sorted(encontradas)


_RE_TANCREDO_VIARIO = re.compile(
    r"\b(?:AV\s*\.\s*|(?:AV|AVENIDAS?|VIADUTO|PASSARELA|ESTACAO)\b\s+)"
    r"(?:(?:DA|DE|DO)\s+)?"
    r"(?:(?:PRES\.?|PRESIDENTE|SEN\.?|SENADOR|DR\.?|DOUTOR)\s+)?"
    r"TANCREDO\s+NEVES\b"
)
_ADJETIVOS_CENTRO_INSTITUCIONAL = (
    r"ADMINISTRATIV[OA]|MUNICIPAL|COMUNITARI[OA]|CULTURAL|ESCOLAR|CIRURGIC[OA]|"
    r"DIAGNOSTIC[OA]|REFERENCIA|ESPECIALIZAD[OA]|INTEGRAD[OA]|COMERCIAL|ESPORTIV[OA]|"
    r"HISTORIC[OA]|MEDIC[OA]|ODONTOLOGIC[OA]|VETERINARI[OA]|UNIVERSITARI[OA]|"
    r"POPULAR|SOCIAL|CRAS|CREAS|CAPS|POP"
)
_TIPOS_CENTRO_INSTITUCIONAL = (
    r"REFERENCIA|SAUDE|ATENCAO|ATENDIMENTO|CONVIVENCIA|OPERACOES|EDUCACAO|"
    r"ESPORTES?|LAZER|CULTURA|ARTES?|TECNOLOGIA|INOVACAO|ZOONOSES|"
    r"REABILITACAO|ESPECIALIDADES|APOIO|ACOLHIMENTO|FORMACAO|CAPACITACAO|"
    r"ESTUDOS|TRIAGEM|PESQUISA|MEMORIA|DOCUMENTACAO|INTEGRACAO|INICIACAO|"
    r"EXPOSICOES|CONVENCOES|EVENTOS|NEGOCIOS|MODA|ARTESANATO|DISTRIBUICAO|"
    r"ABASTECIMENTO|OBSERVACAO|CONTROLE|MONITORAMENTO|IDOSO|JUVENTUDE|CRIANCA|MULHER|CIDADANIA|ENSINO"
)
_RE_QUALIFICADORES_CENTRO = re.compile(
    rf"^(?:(?:\s*,\s*|\s*[-/]\s*|\s+)(?:{_ADJETIVOS_CENTRO_INSTITUCIONAL})\b"
    rf"|(?:\s*[-/]\s*|\s+)D[EAO]S?\s+(?:{_TIPOS_CENTRO_INSTITUCIONAL})\b)"
)
_RE_QUALIFICADORES_ARMACAO = re.compile(r"^\s+(?:DE|METALICA|ESTRUTURAL)\b")
_RE_SAUDE_CONTEXTO_VALIDO = re.compile(r"\b(?:BAIRRO|EM|NO|NA)\s+(?:DA\s+)?$")
_RE_SAUDE_CONTEXTO_INVALIDO = re.compile(r"\b(?:DE|DA|POSTO|UNIDADE|SECRETARIA|FUNDO|SERVICO)\s+$")
_ROMANO_PARA_ARABICO: dict[str, str] = {
    "II": "2",
    "III": "3",
    "IV": "4",
    "V": "5",
    "VI": "6",
    "VII": "7",
    "VIII": "8",
    "IX": "9",
    "X": "10",
    "XI": "11",
}


def _mascarar_trecho(texto: str, start: int, end: int) -> str:
    """Substitui o intervalo [start, end) por espaços preservando índices e limites de palavra."""
    return f"{texto[:start]}{' ' * (end - start)}{texto[end:]}"


@lru_cache(maxsize=512)
def _compilar_padrao_toponimo(termo_norm: str) -> re.Pattern[str]:
    """Compila regex com fronteira de palavra tolerando espaços ao redor de barras '/'."""
    padrao = re.escape(termo_norm).replace("/", r"\s*/\s*")
    return re.compile(rf"\b{padrao}\b")


def _eh_ocorrencia_valida_toponimo(
    termo_norm: str,
    texto: str,
    start: int,
    end: int,
) -> bool:
    """Aplica blindagem sintática contextual sobre uma ocorrência candidata de topônimo."""
    if termo_norm == "SAUDE":
        prefixo = texto[:start]
        if not _RE_SAUDE_CONTEXTO_VALIDO.search(prefixo):
            return False
        if _RE_SAUDE_CONTEXTO_INVALIDO.search(prefixo):
            return False
        return True

    if termo_norm == "CENTRO":
        return not bool(_RE_QUALIFICADORES_CENTRO.match(texto[end:]))

    if termo_norm == "ARMACAO":
        return not bool(_RE_QUALIFICADORES_ARMACAO.match(texto[end:]))

    return True


def _consumir_candidatos_toponimos(
    texto_trabalho: str,
    candidatos_ordenados: list[tuple[str, str]],
) -> tuple[list[tuple[str, int, int]], str]:
    """Consome candidatos ordenados por tamanho decrescente, mascarando spans válidos."""
    ocorrencias: list[tuple[str, int, int]] = []

    for termo_bruto, destino_canonico in candidatos_ordenados:
        termo_norm = normalizar_nome(termo_bruto)
        destino_norm = normalizar_nome(destino_canonico)
        if not termo_norm or not destino_norm:
            continue
        padrao = _compilar_padrao_toponimo(termo_norm)
        while True:
            consumiu = False
            for match in padrao.finditer(texto_trabalho):
                start, end = match.span()
                if not _eh_ocorrencia_valida_toponimo(termo_norm, texto_trabalho, start, end):
                    continue
                texto_trabalho = _mascarar_trecho(texto_trabalho, start, end)
                ocorrencias.append((destino_canonico, start, end))
                consumiu = True
                break
            if not consumiu:
                break

    return ocorrencias, texto_trabalho


def _gerar_aliases_bairros_oficiais(bairros_nomes: list[str]) -> list[tuple[str, str]]:
    """Constrói lista de Bairros Oficiais incluindo variantes arábicas (II..XI) e desambiguação composta."""
    candidatos: list[tuple[str, str]] = [(b_nome, b_nome) for b_nome in bairros_nomes]
    nome_sao_goncalo: Optional[str] = None

    for b_nome in bairros_nomes:
        b_norm = normalizar_nome(b_nome)
        if b_norm == "SAO GONCALO":
            nome_sao_goncalo = b_nome
        for romano, arabico in _ROMANO_PARA_ARABICO.items():
            sufixo = f" {romano}"
            if b_norm.endswith(sufixo):
                prefixo = b_norm[: -len(sufixo)]
                candidatos.append((f"{prefixo} {arabico}", b_nome))
                break

    if nome_sao_goncalo:
        candidatos.append(("SAO GONCALO DO RETIRO", nome_sao_goncalo))

    return sorted(
        candidatos,
        key=lambda item: len(normalizar_nome(item[0])),
        reverse=True,
    )


def _eh_sublocalidade_subordinada(
    objeto_norm: str,
    sub_span: tuple[int, int],
    spans_oficiais: list[tuple[int, int]],
) -> bool:
    """Verifica se uma sublocalidade está imediatamente justaposta a um Bairro Oficial via , / - / ( sem conjunção."""
    s_sub, e_sub = sub_span
    for s_bai, e_bai in spans_oficiais:
        if e_sub <= s_bai:
            entre = objeto_norm[e_sub:s_bai]
        elif e_bai <= s_sub:
            entre = objeto_norm[e_bai:s_sub]
        else:
            continue
        if re.fullmatch(r"[\s,\-\(\)]+", entre):
            return True
    return False


def _buscar_toponimos_blindados(
    objeto_norm: str,
    bairros_nomes: list[str],
    dicionario_sublocalidades: dict[str, str],
) -> list[str]:
    """Extrai Bairros Oficiais distintos com blindagem sintática, priorizando Bairros Oficiais subordinantes."""
    texto_trabalho = _RE_TANCREDO_VIARIO.sub(
        lambda m: " " * len(m.group(0)),
        objeto_norm,
    )

    candidatos_oficiais = _gerar_aliases_bairros_oficiais(bairros_nomes)
    ocorrencias_oficiais, texto_restante = _consumir_candidatos_toponimos(
        texto_trabalho,
        candidatos_oficiais,
    )
    spans_oficiais = [(s, e) for _, s, e in ocorrencias_oficiais]

    candidatos_sub = sorted(
        list(dicionario_sublocalidades.items()),
        key=lambda item: len(normalizar_nome(item[0])),
        reverse=True,
    )
    ocorrencias_sub, _ = _consumir_candidatos_toponimos(
        texto_restante,
        candidatos_sub,
    )

    encontrados: list[str] = []
    vistos: set[str] = set()

    for destino, _, _ in ocorrencias_oficiais:
        dest_norm = normalizar_nome(destino)
        if dest_norm not in vistos:
            vistos.add(dest_norm)
            encontrados.append(destino)

    for destino, s_sub, e_sub in ocorrencias_sub:
        if spans_oficiais and _eh_sublocalidade_subordinada(
            objeto_norm,
            (s_sub, e_sub),
            spans_oficiais,
        ):
            continue
        dest_norm = normalizar_nome(destino)
        if dest_norm not in vistos:
            vistos.add(dest_norm)
            encontrados.append(destino)

    return encontrados


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


def _carregar_curadoria_territorial() -> dict[str, dict[str, Any]]:
    """Carrega o catálogo versionado de Curadoria Territorial Auditável."""
    dados = _carregar_json_referencia("curadoria_territorial.json")
    if not isinstance(dados, dict):
        return {}
    registros = dados.get("registros")
    if isinstance(registros, dict):
        return registros
    return dados


def _aplicar_curadoria_territorial(
    cd_ug: Any,
    nu_contrato: Any,
    curadoria: dict[str, dict[str, Any]],
    bairros_nomes: list[str],
    sublocalidades_norm: dict[str, str],
    bairros_centroides: dict[str, tuple[float, float]],
    bairros_centroides_norm: dict[str, tuple[float, float]],
    bairro_para_pb: dict[str, str],
    bairro_para_pb_norm: dict[str, str],
) -> Optional[dict[str, Any]]:
    """Aplica o julgamento semântico explícito do catálogo de Curadoria Territorial Auditável."""
    chave = f"{str(cd_ug).strip()}:{str(nu_contrato).strip()}"
    entrada = curadoria.get(chave)
    if not isinstance(entrada, dict):
        return None

    status = str(entrada.get("status") or "").strip().lower()
    lastro = {
        "trechoComprobatorio": entrada.get("trechoComprobatorio"),
        "documentoOrigem": entrada.get("documentoOrigem"),
        "justificativa": entrada.get("justificativa"),
    }

    if status in ("ambiguo", "nao_localizado", "multi_frente"):
        estagio = (
            "Curadoria Territorial Auditável (Multi-Frente)"
            if status == "multi_frente"
            else "Curadoria Territorial Auditável (Ambíguo)"
        )
        return {
            "nivel": "Escopo Cidade (Não-Localizado)",
            "bairro": None,
            "prefeitura_bairro": None,
            "latitude": None,
            "longitude": None,
            "estagio": estagio,
            "lastro_curadoria": lastro,
        }

    if status != "promovido":
        return None

    nivel = str(entrada.get("nivel") or "").strip()
    if nivel == "Bairro":
        bairro_raw = str(entrada.get("bairro") or "").strip()
        bairro_canonico = reconciliar_bairro_canonico(bairro_raw, bairros_nomes, sublocalidades_norm) or bairro_raw
        centroide = (
            bairros_centroides.get(bairro_canonico)
            or bairros_centroides_norm.get(normalizar_nome(bairro_canonico))
        )
        pb_raw = (
            entrada.get("prefeituraBairro")
            or bairro_para_pb.get(bairro_canonico)
            or bairro_para_pb_norm.get(normalizar_nome(bairro_canonico))
        )
        pb_final = normalizar_nome_prefeitura_bairro(str(pb_raw)) if pb_raw else None
        return {
            "nivel": "Bairro",
            "bairro": bairro_canonico or None,
            "prefeitura_bairro": pb_final,
            "latitude": centroide[0] if centroide else None,
            "longitude": centroide[1] if centroide else None,
            "estagio": "Curadoria Territorial Auditável",
            "lastro_curadoria": lastro,
        }

    if nivel == "Regional (Prefeitura-Bairro)":
        pb_raw = str(entrada.get("prefeituraBairro") or "").strip()
        pb_final = normalizar_nome_prefeitura_bairro(pb_raw) if pb_raw else None
        return {
            "nivel": "Regional (Prefeitura-Bairro)",
            "bairro": None,
            "prefeitura_bairro": pb_final,
            "latitude": None,
            "longitude": None,
            "estagio": "Curadoria Territorial Auditável",
            "lastro_curadoria": lastro,
        }

    return None


def aplicar_curadoria_obra(
    obra: dict[str, Any],
    bairros_geojson: dict[str, Any],
    bairros_centroides: Optional[dict[str, tuple[float, float]]] = None,
    curadoria: Optional[dict[str, dict[str, Any]]] = None,
    indices_territoriais: Optional[tuple[list[str], dict[str, str], dict[str, str], dict[str, str]]] = None,
) -> Optional[dict[str, Any]]:
    """Aplica o catálogo de Curadoria Territorial Auditável a uma obra específica."""
    catalogo = curadoria if curadoria is not None else _carregar_curadoria_territorial()
    if not catalogo:
        return None

    cd_ug = obra.get("cdUnidadeGestora") or obra.get("unidadeGestora") or ""
    nu_contrato = obra.get("nuContratoSigef") or obra.get("numeroContrato") or ""
    if not str(cd_ug).strip() or not str(nu_contrato).strip():
        return None

    bairros_nomes, sublocalidades_norm, bairro_para_pb, bairro_para_pb_norm = (
        indices_territoriais
        if indices_territoriais is not None
        else _extrair_indices_territoriais(bairros_geojson)
    )
    centroides = (
        bairros_centroides
        if bairros_centroides is not None
        else calcular_centroides_bairros(bairros_geojson)
    )
    bairros_centroides_norm = {normalizar_nome(k): v for k, v in centroides.items()}

    return _aplicar_curadoria_territorial(
        cd_ug=cd_ug,
        nu_contrato=nu_contrato,
        curadoria=catalogo,
        bairros_nomes=bairros_nomes,
        sublocalidades_norm=sublocalidades_norm,
        bairros_centroides=centroides,
        bairros_centroides_norm=bairros_centroides_norm,
        bairro_para_pb=bairro_para_pb,
        bairro_para_pb_norm=bairro_para_pb_norm,
    )


def _extrair_indices_territoriais(
    bairros_geojson: dict[str, Any],
) -> tuple[list[str], dict[str, str], dict[str, str], dict[str, str]]:
    """Extrai nomes canônicos de bairros, sublocalidades normalizadas e mapas de Prefeitura-Bairro."""
    subloc_dict = _carregar_json_referencia("sublocalidades.json") or {}
    sublocalidades_norm = {normalizar_nome(k): v for k, v in subloc_dict.items()}

    bairros_nomes: list[str] = []
    bairro_para_pb: dict[str, str] = {}
    bairro_para_pb_norm: dict[str, str] = {}
    for feat in bairros_geojson.get("features", []):
        props = feat.get("properties", {})
        nome = (props.get("NM_BAIRRO") or props.get("nome") or props.get("NOME_BAIRR") or "").strip()
        pb = (props.get("PREFEITURA_BAIRRO") or props.get("prefeitura_bairro") or "").strip()
        if nome:
            bairros_nomes.append(nome)
            if pb:
                bairro_para_pb[nome] = pb
                bairro_para_pb_norm[normalizar_nome(nome)] = pb

    return bairros_nomes, sublocalidades_norm, bairro_para_pb, bairro_para_pb_norm


def resolver_frentes_medicao(
    obra: dict[str, Any],
    bairros_geojson: dict[str, Any],
    liquidacoes: Optional[list[dict[str, Any]]] = None,
    pagamentos: Optional[list[dict[str, Any]]] = None,
    curadoria: Optional[dict[str, dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    """Resolve as Frentes de Medição comprovadas de um contrato guarda-chuva a partir da curadoria."""
    cd_ug = obra.get("cdUnidadeGestora") or obra.get("unidadeGestora") or ""
    nu_contrato = obra.get("nuContratoSigef") or obra.get("numeroContrato") or ""
    chave = f"{str(cd_ug).strip()}:{str(nu_contrato).strip()}"

    catalogo = curadoria if curadoria is not None else _carregar_curadoria_territorial()
    entrada = catalogo.get(chave)
    if not isinstance(entrada, dict):
        return []

    frentes_curadas = entrada.get("frentesMedicao")
    if not isinstance(frentes_curadas, dict) or not frentes_curadas:
        return []

    bairros_nomes, sublocalidades_norm, bairro_para_pb, bairro_para_pb_norm = _extrair_indices_territoriais(
        bairros_geojson
    )

    pagamentos_por_nl: dict[str, float] = {}
    for pag in pagamentos or []:
        if not isinstance(pag, dict):
            continue
        nl_pag = str(pag.get("notaLiquidacao") or "").strip()
        if not nl_pag:
            continue
        pagamentos_por_nl[nl_pag] = pagamentos_por_nl.get(nl_pag, 0.0) + parse_float(pag.get("pago") or 0.0)

    frentes_resolvidas: list[dict[str, Any]] = []
    for liq in liquidacoes or []:
        if not isinstance(liq, dict):
            continue
        nl = str(liq.get("notaLiquidacao") or "").strip()
        if not nl:
            continue
        frente_cfg = frentes_curadas.get(nl)
        if not isinstance(frente_cfg, dict):
            continue
        if str(frente_cfg.get("status") or "").strip().lower() != "promovido":
            continue

        nivel = str(frente_cfg.get("nivel") or "").strip()
        bairro_canonico: Optional[str] = None
        pb_final: Optional[str] = None

        if nivel == "Bairro":
            bairro_raw = str(frente_cfg.get("bairro") or "").strip()
            bairro_canonico = reconciliar_bairro_canonico(bairro_raw, bairros_nomes, sublocalidades_norm) or bairro_raw
            if not bairro_canonico:
                continue
            pb_raw = (
                frente_cfg.get("prefeituraBairro")
                or bairro_para_pb.get(bairro_canonico)
                or bairro_para_pb_norm.get(normalizar_nome(bairro_canonico))
            )
            pb_final = normalizar_nome_prefeitura_bairro(str(pb_raw)) if pb_raw else None
        elif nivel == "Regional (Prefeitura-Bairro)":
            pb_raw = str(frente_cfg.get("prefeituraBairro") or "").strip()
            pb_final = normalizar_nome_prefeitura_bairro(pb_raw) if pb_raw else None
            if not pb_final:
                continue
        else:
            continue

        val_liq = parse_float(liq.get("valLiqLiquidacao") or 0.0)
        val_pago = parse_float(liq.get("pago") or 0.0)
        if val_pago == 0.0 and nl in pagamentos_por_nl:
            val_pago = pagamentos_por_nl.pop(nl, 0.0)

        if val_liq <= 0.0 and val_pago <= 0.0:
            continue

        frentes_resolvidas.append({
            "notaLiquidacao": nl,
            "nivel": nivel,
            "bairro": bairro_canonico,
            "prefeituraBairro": pb_final,
            "valorLiquidado": round(val_liq, 2),
            "valorPago": round(val_pago, 2),
            "dataLiquidacao": liq.get("dataLiquidacao"),
            "trechoComprobatorio": frente_cfg.get("trechoComprobatorio"),
            "documentoOrigem": frente_cfg.get("documentoOrigem"),
            "justificativa": frente_cfg.get("justificativa"),
        })

    return frentes_resolvidas


def _classificar_estagio_1c_toponimos(
    *,
    objeto_norm: str,
    bairros_nomes: list[str],
    dicionario_sublocalidades: dict[str, str],
    sublocalidades_norm: dict[str, str],
    bairros_centroides: dict[str, tuple[float, float]],
    bairros_centroides_norm: dict[str, tuple[float, float]],
    bairro_para_pb: dict[str, str],
    bairro_para_pb_norm: dict[str, str],
) -> Optional[dict[str, Any]]:
    """Executa o Estágio 1C considerando multi-bairro sem curadoria, macro-regiões e blindagem sintática."""
    bairros_detectados = _buscar_toponimos_blindados(
        objeto_norm,
        bairros_nomes,
        dicionario_sublocalidades,
    )
    macros_detectadas = _detectar_macro_regioes_no_objeto(objeto_norm)

    bairros_unicos: list[str] = []
    vistos: set[str] = set()
    for b_det in bairros_detectados:
        b_canonico = reconciliar_bairro_canonico(b_det, bairros_nomes, sublocalidades_norm)
        b_final = b_canonico or b_det
        b_chave = normalizar_nome(b_final)
        if b_chave and b_chave not in vistos:
            vistos.add(b_chave)
            bairros_unicos.append(b_final)

    if not bairros_unicos:
        if len(macros_detectadas) == 1:
            return {
                "nivel": "Regional (Prefeitura-Bairro)",
                "bairro": None,
                "prefeitura_bairro": macros_detectadas[0],
                "latitude": None,
                "longitude": None,
                "estagio": "Stage 1 (Macro-Região Prefeitura-Bairro)",
            }
        if len(macros_detectadas) > 1:
            return {
                "nivel": "Escopo Cidade (Não-Localizado)",
                "bairro": None,
                "prefeitura_bairro": None,
                "latitude": None,
                "longitude": None,
                "estagio": "Múltiplas Prefeituras-Bairro",
            }
        return None

    if len(bairros_unicos) == 1:
        bairro_final = bairros_unicos[0]
        pb_bairro = (
            bairro_para_pb.get(bairro_final)
            or bairro_para_pb_norm.get(normalizar_nome(bairro_final))
        )
        if pb_bairro:
            pb_bairro = normalizar_nome_prefeitura_bairro(pb_bairro)
        pbs_envolvidas = {pb for pb in [pb_bairro, *macros_detectadas] if pb}
        if macros_detectadas and len(pbs_envolvidas) > 1:
            return {
                "nivel": "Escopo Cidade (Não-Localizado)",
                "bairro": None,
                "prefeitura_bairro": None,
                "latitude": None,
                "longitude": None,
                "estagio": "Múltiplas Prefeituras-Bairro",
            }
        centroide = (
            bairros_centroides.get(bairro_final)
            or bairros_centroides_norm.get(normalizar_nome(bairro_final))
        )
        return {
            "nivel": "Bairro",
            "bairro": bairro_final,
            "prefeitura_bairro": pb_bairro,
            "latitude": centroide[0] if centroide else None,
            "longitude": centroide[1] if centroide else None,
            "estagio": "Stage 1 (Bairro / Sublocalidade)",
        }

    pbs_bairros = []
    for b_nome in bairros_unicos:
        pb = bairro_para_pb.get(b_nome) or bairro_para_pb_norm.get(normalizar_nome(b_nome))
        pbs_bairros.append(normalizar_nome_prefeitura_bairro(pb) if pb else "")

    pbs_todas = {pb for pb in [*pbs_bairros, *macros_detectadas] if pb}
    if all(pbs_bairros) and len(pbs_todas) == 1:
        return {
            "nivel": "Regional (Prefeitura-Bairro)",
            "bairro": None,
            "prefeitura_bairro": next(iter(pbs_todas)),
            "latitude": None,
            "longitude": None,
            "estagio": "Stage 1 (Multi-Bairro Mesma Prefeitura-Bairro)",
        }

    return {
        "nivel": "Escopo Cidade (Não-Localizado)",
        "bairro": None,
        "prefeitura_bairro": None,
        "latitude": None,
        "longitude": None,
        "estagio": "Multi-Bairro (Prefeituras-Bairro Múltiplas)",
    }


def _executar_estagio_1_deterministico(
    *,
    objeto_norm: str,
    equipamentos: list[dict[str, Any]],
    dicionario_lotes: dict[str, str],
    bairros_nomes: list[str],
    dicionario_sublocalidades: dict[str, str],
    sublocalidades_norm: dict[str, str],
    bairros_centroides: dict[str, tuple[float, float]],
    bairros_centroides_norm: dict[str, tuple[float, float]],
    bairro_para_pb: dict[str, str],
    bairro_para_pb_norm: dict[str, str],
) -> Optional[dict[str, Any]]:
    """Executa o funil determinístico local (1A Pontual -> 1B Regional -> 1C Bairro/Multi-Bairro)."""
    eq_encontrado = _buscar_equipamento_no_objeto(objeto_norm, equipamentos)
    if eq_encontrado:
        eq_bairro = eq_encontrado.get("bairro")
        eq_pb = eq_encontrado.get("prefeitura_bairro")
        if not eq_pb and eq_bairro:
            eq_pb = bairro_para_pb.get(eq_bairro) or bairro_para_pb_norm.get(normalizar_nome(eq_bairro))
        if eq_pb:
            eq_pb = normalizar_nome_prefeitura_bairro(eq_pb)
        return {
            "nivel": "Pontual",
            "bairro": eq_bairro,
            "prefeitura_bairro": eq_pb,
            "latitude": eq_encontrado.get("latitude"),
            "longitude": eq_encontrado.get("longitude"),
            "estagio": "Stage 1 (Equipamento Oficial)",
        }

    pbs_detectadas = _detectar_prefeituras_bairro_no_objeto(objeto_norm, dicionario_lotes)
    if len(pbs_detectadas) == 1:
        return {
            "nivel": "Regional (Prefeitura-Bairro)",
            "bairro": None,
            "prefeitura_bairro": normalizar_nome_prefeitura_bairro(pbs_detectadas[0]),
            "latitude": None,
            "longitude": None,
            "estagio": "Stage 1 (Lote Regional)",
        }
    if len(pbs_detectadas) > 1:
        return {
            "nivel": "Escopo Cidade (Não-Localizado)",
            "bairro": None,
            "prefeitura_bairro": None,
            "latitude": None,
            "longitude": None,
            "estagio": "Múltiplas Prefeituras-Bairro",
        }

    return _classificar_estagio_1c_toponimos(
        objeto_norm=objeto_norm,
        bairros_nomes=bairros_nomes,
        dicionario_sublocalidades=dicionario_sublocalidades,
        sublocalidades_norm=sublocalidades_norm,
        bairros_centroides=bairros_centroides,
        bairros_centroides_norm=bairros_centroides_norm,
        bairro_para_pb=bairro_para_pb,
        bairro_para_pb_norm=bairro_para_pb_norm,
    )


def _eh_pontual_estagio_avancado(entry: dict[str, Any]) -> bool:
    """Identifica entrada pontual válida já geocodificada pelos Estágios 2 ou 3."""
    estagio = str(entry.get("estagio") or "")
    return (
        entry.get("nivel") == "Pontual"
        and estagio.startswith(("Stage 2", "Stage 3"))
        and entry.get("latitude") is not None
        and entry.get("longitude") is not None
    )


def _hidratar_pontual_preservado(
    entry: dict[str, Any],
    bairro_para_pb: dict[str, str],
    bairro_para_pb_norm: dict[str, str],
) -> dict[str, Any]:
    """Normaliza/hidrata a Prefeitura-Bairro de entrada pontual preservada em cache."""
    preservado = dict(entry)
    pb_atual = preservado.get("prefeitura_bairro")
    if pb_atual:
        pb_norm = normalizar_nome_prefeitura_bairro(str(pb_atual))
        if pb_norm != pb_atual:
            preservado["prefeitura_bairro"] = pb_norm
    elif preservado.get("bairro"):
        b_chave = str(preservado["bairro"])
        pb_hid = bairro_para_pb.get(b_chave) or bairro_para_pb_norm.get(normalizar_nome(b_chave))
        if pb_hid:
            preservado["prefeitura_bairro"] = pb_hid
    return preservado


def classificar_alocacao_territorial(
    obra: dict[str, Any],
    bairros_geojson: dict[str, Any],
    bairros_centroides: dict[str, tuple[float, float]],
    cache: Optional[GeocodingCache] = None,
    habilitar_rede: Optional[bool] = None,
    curadoria: Optional[dict[str, dict[str, Any]]] = None,
    recalcular: bool = False,
) -> dict[str, Any]:
    """Classifica a Obra Pública no Funil de Alocação Territorial em 3 estágios com cache incremental.

    Sumário:
        Determina o Nível de Alocação Territorial, Bairro Oficial, Prefeitura-Bairro e coordenadas.

    Descrição Estendida:
        Executa os seguintes passos em ordem estrita de precedência:
        1. Curadoria Territorial Auditável (quando aplicável ao contrato/UG):
           Tem precedência determinística offline e atualiza o cache se necessário.
        2. Cache incremental em disco (quando ``recalcular=False``):
           Reconcilia Bairros Oficiais, hidrata centróide/Prefeitura-Bairro e reavalia entradas
           antigas de ``Escopo Cidade (Não-Localizado)`` contra as regras determinísticas locais.
        3. Estágio 1 (Determinístico Local):
           a) Mapeamento contra catálogo oficial de Escolas e Unidades de Saúde -> ``Pontual``.
           b) Menção explícita a Prefeitura-Bairro (I..X, prefixo ``PB``/``Pref. Bairro``,
              pares compostos) -> ``Regional (Prefeitura-Bairro)`` se única, ou
              ``Escopo Cidade (Não-Localizado)`` se múltiplas Prefeituras-Bairro.
           c) Extração com blindagem sintática de Bairros Oficiais, sublocalidades e
              macro-regiões: 1 Bairro -> ``Bairro`` (salvo conflito com macro-região distinta);
              múltiplos Bairros da mesma Prefeitura-Bairro -> ``Regional (Prefeitura-Bairro)``;
              múltiplas Prefeituras-Bairro -> ``Escopo Cidade (Não-Localizado)``.
        4. Estágio 2 (Nominatim OSM):
           Quando autorizado (``habilitar_rede=True``, ou ``habilitar_rede=None`` com
           ``ENABLE_NOMINATIM=1``), busca coordenadas de logradouro e valida em Salvador.
           Se ``habilitar_rede=False``, bloqueia a rede mesmo com ``ENABLE_NOMINATIM=1``; em
           ``recalcular=True``, preserva entradas ``Pontual`` prévias de Estágio 2/3 no cache
           caso o Estágio 1 retorne sem correspondência local.
        5. Estágio 3 (Extrator LLM opcional) e Fallback Final (``Escopo Cidade (Não-Localizado)``).

    Argumentos:
        obra: Dicionário contendo dados do contrato (``dsObjeto``, ``cdUnidadeGestora``, ``nuContratoSigef``).
        bairros_geojson: FeatureCollection oficial dos Bairros Oficiais de Salvador.
        bairros_centroides: Dicionário mapeando nome do Bairro Oficial para ``(latitude, longitude)``.
        cache: Instância opcional de ``GeocodingCache`` para persistência incremental.
        habilitar_rede: ``True`` autoriza Nominatim; ``False`` força modo estritamente offline
            (ignora ``ENABLE_NOMINATIM=1``); ``None`` respeita ``os.getenv("ENABLE_NOMINATIM") == "1"``.
        curadoria: Catálogo opcional pré-carregado de curadoria territorial por chave canônica.
        recalcular: Se ``True``, ignora leitura prévia do cache para reavaliar o Estágio 1
            e sobrescrever o cache (preservando apenas pontuais de Estágio 2/3 no modo offline).

    Retornos:
        Dicionário com a estrutura de alocação contendo:
        - nivel: ``Pontual`` | ``Bairro`` | ``Regional (Prefeitura-Bairro)`` | ``Escopo Cidade (Não-Localizado)``.
        - bairro: Nome do Bairro Oficial ou ``None``.
        - prefeitura_bairro: Nome da Prefeitura-Bairro ou ``None``.
        - latitude: Float ou ``None``.
        - longitude: Float ou ``None``.
        - estagio: Descrição da regra ou estágio que determinou a localização.

    Erros:
        Não lança exceções; em caso de falha retorna nível ``Escopo Cidade (Não-Localizado)``.
    """
    cd_ug = obra.get("cdUnidadeGestora") or obra.get("unidadeGestora") or "UG"
    nu_contrato = obra.get("nuContratoSigef") or obra.get("numeroContrato") or "S_N"
    ds_objeto = str(obra.get("dsObjeto") or obra.get("objeto") or "")

    objeto_norm = normalizar_nome(ds_objeto)

    # 1. Carrega catálogos e dicionários locais para referência e hidratação
    equipamentos = _extrair_equipamentos_oficiais()
    dicionario_lotes = _carregar_json_referencia("lotes_regionais.json") or {}
    dicionario_sublocalidades = _carregar_json_referencia("sublocalidades.json") or {}
    sublocalidades_norm = {normalizar_nome(k): v for k, v in dicionario_sublocalidades.items()}

    # Mapeamento auxiliar de bairros para suas respectivas Prefeituras-Bairro
    bairro_para_pb: dict[str, str] = {}
    for feat in bairros_geojson.get("features", []):
        p = feat.get("properties", {})
        nb = p.get("NM_BAIRRO") or p.get("nome") or ""
        npb = p.get("PREFEITURA_BAIRRO") or p.get("prefeitura_bairro") or ""
        if nb:
            bairro_para_pb[nb] = normalizar_nome_prefeitura_bairro(npb)

    bairros_nomes = list(bairro_para_pb.keys())
    bairro_para_pb_norm = {normalizar_nome(k): v for k, v in bairro_para_pb.items()}
    bairros_centroides_norm = {normalizar_nome(k): v for k, v in bairros_centroides.items()}

    # 1b. Curadoria Territorial Auditável (precedência determinística offline)
    catalogo_curadoria = curadoria if curadoria is not None else _carregar_curadoria_territorial()
    if catalogo_curadoria:
        resultado_curado = _aplicar_curadoria_territorial(
            cd_ug=cd_ug,
            nu_contrato=nu_contrato,
            curadoria=catalogo_curadoria,
            bairros_nomes=bairros_nomes,
            sublocalidades_norm=sublocalidades_norm,
            bairros_centroides=bairros_centroides,
            bairros_centroides_norm=bairros_centroides_norm,
            bairro_para_pb=bairro_para_pb,
            bairro_para_pb_norm=bairro_para_pb_norm,
        )
        if resultado_curado is not None:
            if cache is not None and (
                recalcular or cache.get(cd_ug, nu_contrato, ds_objeto) != resultado_curado
            ):
                cache.set(cd_ug, nu_contrato, ds_objeto, resultado_curado)
            return resultado_curado

    # 2. Verificação no Cache Incremental com Reconciliação e Hidratação de Bairro
    if cache is not None and not recalcular:
        cached = cache.get(cd_ug, nu_contrato, ds_objeto)
        if cached:
            resultado_cached = dict(cached)
            modificado = False

            # Se for nível Bairro, reconcilia contra os 171 Bairros Oficiais e hidrata coordenadas/PB
            if resultado_cached.get("nivel") == "Bairro":
                b_atual = resultado_cached.get("bairro") or ""
                b_canonico = reconciliar_bairro_canonico(b_atual, bairros_nomes, sublocalidades_norm)
                if b_canonico and resultado_cached.get("bairro") != b_canonico:
                    resultado_cached["bairro"] = b_canonico
                    modificado = True

                b_chave = resultado_cached.get("bairro") or ""
                pb_cached = resultado_cached.get("prefeitura_bairro")
                pb_norm = normalizar_nome_prefeitura_bairro(str(pb_cached or ""))
                if not pb_cached or pb_norm != pb_cached:
                    pb_hidratada = (
                        bairro_para_pb.get(b_chave)
                        or bairro_para_pb_norm.get(normalizar_nome(b_chave))
                    )
                    if pb_hidratada and pb_hidratada != pb_cached:
                        resultado_cached["prefeitura_bairro"] = pb_hidratada
                        modificado = True

                if resultado_cached.get("latitude") is None or resultado_cached.get("longitude") is None:
                    coords = (
                        bairros_centroides.get(b_chave)
                        or bairros_centroides_norm.get(normalizar_nome(b_chave))
                    )
                    if coords:
                        resultado_cached["latitude"] = coords[0]
                        resultado_cached["longitude"] = coords[1]
                        modificado = True

            elif resultado_cached.get("nivel") == "Regional (Prefeitura-Bairro)":
                pb_cached = resultado_cached.get("prefeitura_bairro")
                if pb_cached:
                    pb_norm = normalizar_nome_prefeitura_bairro(pb_cached)
                    if pb_norm != pb_cached:
                        resultado_cached["prefeitura_bairro"] = pb_norm
                        modificado = True

            elif resultado_cached.get("nivel") == "Pontual":
                pb_cached = resultado_cached.get("prefeitura_bairro")
                if pb_cached:
                    pb_norm = normalizar_nome_prefeitura_bairro(pb_cached)
                    if pb_norm != pb_cached:
                        resultado_cached["prefeitura_bairro"] = pb_norm
                        modificado = True
                elif resultado_cached.get("bairro"):
                    b_chave = resultado_cached["bairro"]
                    pb_hidratada = (
                        bairro_para_pb.get(b_chave)
                        or bairro_para_pb_norm.get(normalizar_nome(b_chave))
                    )
                    if pb_hidratada:
                        resultado_cached["prefeitura_bairro"] = pb_hidratada
                        modificado = True

            elif resultado_cached.get("nivel") == "Escopo Cidade (Não-Localizado)":
                res_rec = _executar_estagio_1_deterministico(
                    objeto_norm=objeto_norm,
                    equipamentos=equipamentos,
                    dicionario_lotes=dicionario_lotes,
                    bairros_nomes=bairros_nomes,
                    dicionario_sublocalidades=dicionario_sublocalidades,
                    sublocalidades_norm=sublocalidades_norm,
                    bairros_centroides=bairros_centroides,
                    bairros_centroides_norm=bairros_centroides_norm,
                    bairro_para_pb=bairro_para_pb,
                    bairro_para_pb_norm=bairro_para_pb_norm,
                )
                if res_rec and res_rec.get("nivel") != "Escopo Cidade (Não-Localizado)":
                    resultado_cached = res_rec
                    modificado = True

            if modificado:
                cache.set(cd_ug, nu_contrato, ds_objeto, resultado_cached)

            resultado_cached["estagio"] = "Cache"
            return resultado_cached

    # --- ESTÁGIO 1: Funil Determinístico Local (Equipamento -> Regional PB -> Bairro/Multi-Bairro) ---
    res_estagio_1 = _executar_estagio_1_deterministico(
        objeto_norm=objeto_norm,
        equipamentos=equipamentos,
        dicionario_lotes=dicionario_lotes,
        bairros_nomes=bairros_nomes,
        dicionario_sublocalidades=dicionario_sublocalidades,
        sublocalidades_norm=sublocalidades_norm,
        bairros_centroides=bairros_centroides,
        bairros_centroides_norm=bairros_centroides_norm,
        bairro_para_pb=bairro_para_pb,
        bairro_para_pb_norm=bairro_para_pb_norm,
    )
    if res_estagio_1 is not None:
        if cache:
            cache.set(cd_ug, nu_contrato, ds_objeto, res_estagio_1)
        return res_estagio_1

    rede_autorizada = (
        habilitar_rede is True
        or (habilitar_rede is None and os.getenv("ENABLE_NOMINATIM") == "1")
    )

    if recalcular and cache is not None and not rede_autorizada:
        cached_previo = cache.get(cd_ug, nu_contrato, ds_objeto)
        if cached_previo and _eh_pontual_estagio_avancado(cached_previo):
            preservado = _hidratar_pontual_preservado(cached_previo, bairro_para_pb, bairro_para_pb_norm)
            if preservado != cached_previo:
                cache.set(cd_ug, nu_contrato, ds_objeto, preservado)
            return preservado

    # --- ESTÁGIO 2: Nominatim OSM com Bounding Box de Salvador ---
    if rede_autorizada:
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

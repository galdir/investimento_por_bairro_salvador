"""Regras e classificações do domínio territorial de Salvador.

Gerencia o pareamento de Bairros Oficiais com Prefeituras-Bairro e a identificação
estrita de Zonas Especiais Não-Residenciais para prevenção de distorções per capita.
"""

import re
import unicodedata
from etl.config import ZONAS_ESPECIAIS_NAO_RESIDENCIAIS


def normalizar_nome(nome: str) -> str:
    """Normaliza um nome textual removendo acentos e convertendo para maiúsculas.

    Sumário:
        Remove diacríticos e caracteres especiais para comparação uniforme de topônimos.

    Descrição Estendida:
        Aplica a decomposição canônica NFKD da biblioteca unicodedata para separar os acentos
        das letras base e descarta os códigos de combinação não espaçados. Também padroniza
        espaços múltiplos e remove espaços nas pontas.

    Argumentos:
        nome: String contendo o nome ou termo original a ser normalizado.

    Retornos:
        String contendo o texto em caixa alta sem acentuação.

    Erros:
        Não lança exceções; converte valores nulos ou vazios para string vazia.
    """
    if not nome:
        return ""
    # Decompõe caracteres acentuados em caractere base + modificador
    nfkd = unicodedata.normalize("NFKD", str(nome))
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Remove espaços excedentes
    return " ".join(sem_acento.strip().upper().split())


def is_zona_especial_nao_residencial(nome_bairro: str) -> bool:
    """Verifica se um Bairro Oficial é uma Zona Especial Não-Residencial.

    Sumário:
        Classifica estritamente se o bairro pertence ao grupo de áreas institucionais/logísticas/aeroportuárias.

    Descrição Estendida:
        As três Zonas Especiais Não-Residenciais de Salvador (Aeroporto, Porto Seco Pirajá
        e Centro Administrativo da Bahia - CAB) possuem população residente nula ou residual
        no Censo 2022. Esta função compara o nome normalizado garantindo que siglas curtas
        como 'CAB' não casem por substring com bairros residenciais (como 'Cabula' ou 'Cabula VI').

    Argumentos:
        nome_bairro: Nome do Bairro Oficial a ser verificado.

    Retornos:
        Booleano: True se for Zona Especial Não-Residencial; False caso contrário.

    Erros:
        Não lança exceções.
    """
    nome_norm = normalizar_nome(nome_bairro)
    if not nome_norm:
        return False

    # 1. Correspondência exata contra a lista de nomes canônicos e variações
    nomes_exatos_normalizados = {normalizar_nome(z) for z in ZONAS_ESPECIAIS_NAO_RESIDENCIAIS}
    if nome_norm in nomes_exatos_normalizados:
        return True

    # 2. Caso de Porto Seco Pirajá (ex: "PORTO SECO PIRAJÁ - SETOR X")
    if "PORTO SECO PIRAJA" in nome_norm:
        return True

    # 3. Caso de Centro Administrativo da Bahia (com ou sem hífen/sigla)
    if "CENTRO ADMINISTRATIVO DA BAHIA" in nome_norm:
        return True

    # 4. Caso estrito de sigla isolada CAB (utiliza limite de palavra para não casar Cabula/Cabula VI)
    # Exige que seja a palavra CAB isolada (ex: "BAIRRO CAB" ou "SETOR CAB"), nunca "CABULA"
    if re.search(r"\bCAB\b", nome_norm) and "CABULA" not in nome_norm:
        # Se for apenas CAB ou associado a Centro Administrativo
        if nome_norm == "CAB" or "ADMINISTRATIVO" in nome_norm:
            return True

    # 5. Caso de Aeroporto
    if nome_norm == "AEROPORTO":
        return True

    return False

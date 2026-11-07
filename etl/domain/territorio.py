"""Regras e classificações do domínio territorial de Salvador.

Gerencia o pareamento de Bairros Oficiais com Prefeituras-Bairro, a identificação
estrita de Zonas Especiais Não-Residenciais para prevenção de distorções per capita,
e o cálculo das agregações financeiras e per capita em múltiplos níveis territoriais.
"""

import re
from typing import Any
import unicodedata

from etl.config import ZONAS_ESPECIAIS_NAO_RESIDENCIAIS


def parse_float(val: Any) -> float:
    """Converte valores numéricos ou strings monetárias (incluindo formato brasileiro 1.234,56) para float.

    Sumário:
        Trata números inteiros, floats, None e strings monetárias brasileiras ou internacionais.
    """
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s:
        return 0.0
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def normalizar_nome_prefeitura_bairro(raw_nome: str) -> str:
    """Extrai o nome canônico de uma Prefeitura-Bairro removendo prefixos romanos e padronizando barras."""
    if not raw_nome:
        return ""
    nome = str(raw_nome).strip()
    nome = re.sub(r"^Prefeitura-bairro\s*", "", nome, flags=re.IGNORECASE).strip()
    nome = re.sub(r"^[IVXLC]+\s*-\s*", "", nome).strip()
    return nome.replace(" / ", "/").strip()


def _point_in_poly(x: float, y: float, poly: list[list[float]]) -> bool:
    """Verifica se um ponto (x, y) está dentro de um anel poligonal simples."""
    inside = False
    n = len(poly)
    if n < 3:
        return False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def _get_centroid_geom(geom: dict[str, Any]) -> tuple[float, float]:
    """Calcula centróide geométrico preliminar a partir das coordenadas do anel principal."""
    gtype = geom.get("type")
    coords: list[list[float]] = []
    if gtype == "Polygon":
        coords = geom.get("coordinates", [[]])[0]
    elif gtype == "MultiPolygon":
        multi = geom.get("coordinates", [[[]]])
        if multi:
            coords = max(multi, key=lambda p: len(p[0]) if p and len(p) > 0 else 0)[0]
    if not coords:
        return 0.0, 0.0
    xs = [pt[0] for pt in coords]
    ys = [pt[1] for pt in coords]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def normalizar_e_vincular_malhas_geosalvador(
    bairros_fc: dict[str, Any],
    prefeituras_fc: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Normaliza as propriedades das Prefeituras-Bairro e vincula Bairros Oficiais espacialmente.

    Garante que:
    1. Todas as features de prefeituras_fc tenham NM_PREFEITURA_BAIRRO e NOMES padronizados para o
       nome canônico (sem algarismos romanos nem prefixo 'Prefeitura-bairro') e CD_PREFEITURA_BAIRRO preenchido.
    2. Todas as features de bairros_fc tenham NM_BAIRRO, CD_BAIRRO e PREFEITURA_BAIRRO preenchidos.
       Se PREFEITURA_BAIRRO estiver ausente, vazio ou com prefixo romano, determina a Prefeitura-Bairro
       canônica por ponto-no-polígono do centróide (com fallback para São João do Cabrito -> Subúrbio/Ilhas
       e centróide mais próximo).
    """
    # 1. Normaliza as Prefeituras-Bairro
    pb_polys: list[tuple[str, dict[str, Any], tuple[float, float]]] = []
    for f in prefeituras_fc.get("features", []):
        props = f.get("properties", {})
        raw_name = (
            props.get("NM_PREFEITURA_BAIRRO")
            or props.get("SUBCLASSES")
            or props.get("NOMES")
            or props.get("nome")
            or ""
        )
        clean_name = normalizar_nome_prefeitura_bairro(raw_name)
        props["NM_PREFEITURA_BAIRRO"] = clean_name
        props["NOMES"] = clean_name
        props["nome"] = clean_name
        props["CD_PREFEITURA_BAIRRO"] = props.get("CD_PREFEITURA_BAIRRO") or props.get("OBJECTID", 0)
        geom = f.get("geometry", {})
        cx, cy = _get_centroid_geom(geom)
        pb_polys.append((clean_name, geom, (cx, cy)))

    # 2. Normaliza os Bairros Oficiais e vincula à Prefeitura-Bairro
    for idx, f in enumerate(bairros_fc.get("features", []), start=1):
        props = f.get("properties", {})
        b_name = (props.get("NM_BAIRRO") or props.get("NOME_BAIRR") or props.get("nome") or "").strip()
        props["NM_BAIRRO"] = b_name
        props["nome"] = b_name
        props["CD_BAIRRO"] = props.get("CD_BAIRRO") or props.get("OBJECTID") or idx

        pb_atual = props.get("PREFEITURA_BAIRRO") or props.get("prefeitura_bairro") or ""
        pb_limpa = normalizar_nome_prefeitura_bairro(pb_atual)

        if pb_limpa:
            props["PREFEITURA_BAIRRO"] = pb_limpa
            props["prefeitura_bairro"] = pb_limpa
        elif b_name == "São João do Cabrito":
            props["PREFEITURA_BAIRRO"] = "Subúrbio/Ilhas"
            props["prefeitura_bairro"] = "Subúrbio/Ilhas"
        else:
            cx, cy = _get_centroid_geom(f.get("geometry", {}))
            found_pb = None
            for pb_name, geom, _ in pb_polys:
                gtype = geom.get("type")
                if gtype == "Polygon":
                    rings = geom.get("coordinates", [])
                    if rings and _point_in_poly(cx, cy, rings[0]):
                        found_pb = pb_name
                        break
                elif gtype == "MultiPolygon":
                    for poly in geom.get("coordinates", []):
                        if poly and _point_in_poly(cx, cy, poly[0]):
                            found_pb = pb_name
                            break
                    if found_pb:
                        break

            if not found_pb and pb_polys:
                def dist_sq(p: tuple[str, dict[str, Any], tuple[float, float]]) -> float:
                    return (cx - p[2][0]) ** 2 + (cy - p[2][1]) ** 2
                found_pb = min(pb_polys, key=dist_sq)[0]

            props["PREFEITURA_BAIRRO"] = found_pb or "Centro/Brotas"
            props["prefeitura_bairro"] = props["PREFEITURA_BAIRRO"]

    return bairros_fc, prefeituras_fc


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
    if re.search(r"\bCAB\b", nome_norm) and "CABULA" not in nome_norm:
        if nome_norm == "CAB" or "ADMINISTRATIVO" in nome_norm:
            return True

    # 5. Caso de Aeroporto
    if nome_norm == "AEROPORTO":
        return True

    return False


def calcular_rollup_territorial(
    bairros_resumo: list[dict[str, Any]],
    prefeituras_resumo: list[dict[str, Any]],
    obras_alocadas: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Calcula as agregações financeiras e per capita por Bairro Oficial e Prefeitura-Bairro.

    Sumário:
        Aplica as regras de rollup territorial (Camada A) sem rateio artificial de contratos guarda-chuva.

    Descrição Estendida:
        Regras aplicadas rigorosamente:
        1. Bairro Oficial: soma apenas obras com Nível de Alocação Territorial 'Pontual' e 'Bairro'
           alocadas especificamente para aquele bairro.
        2. Prefeitura-Bairro: soma todas as obras de seus bairros constituintes mais as obras de nível
           'Regional (Prefeitura-Bairro)' atribuídas a ela, sem rateio artificial para os bairros.
        3. Escopo Cidade (Não-Localizado): contratos não alocados a nenhum bairro ou lote regional não
           inflam nenhum território e são consolidados no indicador de transparência opaca.
        4. Zonas Especiais Não-Residenciais: mantêm seus valores brutos e contagem de obras, mas seu
           Investimento por Habitante é zerado/excluído do ranking para prevenir distorções per capita.

    Argumentos:
        bairros_resumo: Lista de resumos de Bairros Oficiais com população e vulnerabilidade.
        prefeituras_resumo: Lista de resumos de Prefeituras-Bairro com população total.
        obras_alocadas: Lista de obras classificadas com nível de alocação, valores e semáforo.

    Retornos:
        Tupla de 3 elementos:
        - Lista atualizada de Bairros Oficiais com atributos financeiros e per capita.
        - Lista atualizada de Prefeituras-Bairro com atributos financeiros e per capita.
        - Dicionário do indicador de transparência opaca (Escopo Cidade).

    Erros:
        Não lança exceções; utiliza valores padrão zero caso os campos estejam ausentes.
    """
    # 1. Total geral de investimentos de todas as obras (para cálculo percentual de opacidade)
    valor_total_todas_obras = 0.0

    # 2. Agrupadores auxiliares
    obras_por_bairro: dict[str, list[dict[str, Any]]] = {}
    obras_regionais_por_pb: dict[str, list[dict[str, Any]]] = {}
    obras_escopo_cidade: list[dict[str, Any]] = []

    for obra in obras_alocadas:
        vl_atua = parse_float(obra.get("vlAtualizado") or obra.get("valorContratualVigente") or obra.get("vlOriginal") or 0.0)
        valor_total_todas_obras += vl_atua

        nivel = obra.get("nivel") or "Escopo Cidade (Não-Localizado)"
        bairro_nome = obra.get("bairro")
        pb_nome = obra.get("prefeitura_bairro")

        if nivel in {"Pontual", "Bairro"} and bairro_nome:
            b_norm = normalizar_nome(bairro_nome)
            obras_por_bairro.setdefault(b_norm, []).append(obra)

        elif nivel == "Regional (Prefeitura-Bairro)" and pb_nome:
            pb_norm = normalizar_nome(pb_nome)
            obras_regionais_por_pb.setdefault(pb_norm, []).append(obra)

        else:
            obras_escopo_cidade.append(obra)

    # 3. Consolidação de Bairros Oficiais
    bairros_atualizados: list[dict[str, Any]] = []
    # Mapeamento de prefeitura_bairro para bairros filhos
    bairros_por_pb: dict[str, list[str]] = {}

    for b in bairros_resumo:
        nome_bairro = b.get("nome", "")
        b_norm = normalizar_nome(nome_bairro)
        pb_nome = b.get("prefeitura_bairro", "")
        pb_norm = normalizar_nome(pb_nome)
        if pb_norm:
            bairros_por_pb.setdefault(pb_norm, []).append(b_norm)

        obras_do_bairro = obras_por_bairro.get(b_norm, [])

        vl_total_bairro = sum(
            parse_float(o.get("vlAtualizado") or o.get("valorContratualVigente") or o.get("vlOriginal") or 0.0)
            for o in obras_do_bairro
        )
        vl_pago_bairro = sum(
            parse_float(o.get("vlPago") or o.get("valorPago") or 0.0)
            for o in obras_do_bairro
        )

        verde_count = sum(1 for o in obras_do_bairro if (o.get("semaforo") or {}).get("status") == "VERDE")
        amarelo_count = sum(1 for o in obras_do_bairro if (o.get("semaforo") or {}).get("status") == "AMARELO")
        vermelho_count = sum(1 for o in obras_do_bairro if (o.get("semaforo") or {}).get("status") == "VERMELHO")

        populacao = int(b.get("populacao", 0))
        eh_zona_especial = is_zona_especial_nao_residencial(nome_bairro) or b.get("is_zona_especial_nao_residencial", False)

        # Regra: Zonas Especiais Não-Residenciais têm per capita zerado para evitar distorção
        inv_per_capita = 0.0
        inv_per_capita_pago = 0.0
        if not eh_zona_especial and populacao > 0:
            inv_per_capita = round(vl_total_bairro / populacao, 2)
            inv_per_capita_pago = round(vl_pago_bairro / populacao, 2)

        bairro_dict = dict(b)
        bairro_dict.update({
            "valorTotal": round(vl_total_bairro, 2),
            "valorPago": round(vl_pago_bairro, 2),
            "totalObras": len(obras_do_bairro),
            "obrasVerde": verde_count,
            "obrasAmarelo": amarelo_count,
            "obrasVermelho": vermelho_count,
            "investimentoPorHabitante": inv_per_capita,
            "investimentoPorHabitantePago": inv_per_capita_pago,
            "is_zona_especial_nao_residencial": eh_zona_especial,
            "isZonaEspecialNaoResidencial": eh_zona_especial,
        })
        bairros_atualizados.append(bairro_dict)

    # 4. Consolidação de Prefeituras-Bairro
    prefeituras_atualizadas: list[dict[str, Any]] = []

    # Cria índice rápido de bairros atualizados
    bairros_index = {normalizar_nome(b["nome"]): b for b in bairros_atualizados}

    for pb in prefeituras_resumo:
        nome_pb = pb.get("nome", "")
        pb_norm = normalizar_nome(nome_pb)

        # Bairros que compõem esta prefeitura-bairro
        bairros_filhos_nomes = bairros_por_pb.get(pb_norm, [])
        bairros_filhos = [bairros_index[bn] for bn in bairros_filhos_nomes if bn in bairros_index]

        # Soma os totais dos bairros
        vl_bairros = sum(b.get("valorTotal", 0.0) for b in bairros_filhos)
        vl_pago_bairros = sum(b.get("valorPago", 0.0) for b in bairros_filhos)
        obras_bairros_count = sum(b.get("totalObras", 0) for b in bairros_filhos)
        verde_pb = sum(b.get("obrasVerde", 0) for b in bairros_filhos)
        amarelo_pb = sum(b.get("obrasAmarelo", 0) for b in bairros_filhos)
        vermelho_pb = sum(b.get("obrasVermelho", 0) for b in bairros_filhos)

        # Soma as obras regionais mapeadas diretamente para a prefeitura-bairro
        obras_regionais = obras_regionais_por_pb.get(pb_norm, [])
        vl_regionais = sum(
            parse_float(o.get("vlAtualizado") or o.get("valorContratualVigente") or o.get("vlOriginal") or 0.0)
            for o in obras_regionais
        )
        vl_pago_regionais = sum(
            parse_float(o.get("vlPago") or o.get("valorPago") or 0.0)
            for o in obras_regionais
        )

        verde_pb += sum(1 for o in obras_regionais if (o.get("semaforo") or {}).get("status") == "VERDE")
        amarelo_pb += sum(1 for o in obras_regionais if (o.get("semaforo") or {}).get("status") == "AMARELO")
        vermelho_pb += sum(1 for o in obras_regionais if (o.get("semaforo") or {}).get("status") == "VERMELHO")

        vl_total_pb = vl_bairros + vl_regionais
        vl_pago_pb = vl_pago_bairros + vl_pago_regionais
        total_obras_pb = obras_bairros_count + len(obras_regionais)

        pop_total = int(pb.get("populacao_total", 0))
        inv_per_capita_pb = round(vl_total_pb / pop_total, 2) if pop_total > 0 else 0.0
        inv_per_capita_pago_pb = round(vl_pago_pb / pop_total, 2) if pop_total > 0 else 0.0

        pb_dict = dict(pb)
        pb_dict.update({
            "valorTotal": round(vl_total_pb, 2),
            "valorPago": round(vl_pago_pb, 2),
            "totalObras": total_obras_pb,
            "obrasVerde": verde_pb,
            "obrasAmarelo": amarelo_pb,
            "obrasVermelho": vermelho_pb,
            "investimentoPorHabitante": inv_per_capita_pb,
            "investimentoPorHabitantePago": inv_per_capita_pago_pb,
        })
        prefeituras_atualizadas.append(pb_dict)

    # 5. Indicador de Transparência Opaca (Escopo Cidade)
    vl_nao_localizado = sum(
        parse_float(o.get("vlAtualizado") or o.get("valorContratualVigente") or o.get("vlOriginal") or 0.0)
        for o in obras_escopo_cidade
    )
    vl_pago_nao_localizado = sum(
        parse_float(o.get("vlPago") or o.get("valorPago") or 0.0)
        for o in obras_escopo_cidade
    )

    percentual_opaco = 0.0
    if valor_total_todas_obras > 0:
        percentual_opaco = round((vl_nao_localizado / valor_total_todas_obras) * 100.0, 1)

    indicador_opacidade = {
        "totalNaoLocalizado": len(obras_escopo_cidade),
        "valorNaoLocalizado": round(vl_nao_localizado, 2),
        "valorPagoNaoLocalizado": round(vl_pago_nao_localizado, 2),
        "percentualNaoLocalizado": percentual_opaco,
    }

    return bairros_atualizados, prefeituras_atualizadas, indicador_opacidade

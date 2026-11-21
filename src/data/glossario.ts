export const GLOSSARIO_CATEGORIAS = [
  "Território",
  "Obras e Localização",
  "Dinheiro e Execução",
  "Mapa e Indicadores",
] as const;

export type GlossarioCategoria = (typeof GLOSSARIO_CATEGORIAS)[number];

export interface GlossarioVerbete {
  slug: string;
  titulo: string;
  categoria: GlossarioCategoria;
  resumo: string;
  explicacao: string;
  exemploSalvador: string;
  palavrasChave: string[];
}

export const GLOSSARIO_VERBETES: GlossarioVerbete[] = [
  {
    slug: "bairro-oficial",
    titulo: "Bairro Oficial",
    categoria: "Território",
    resumo:
      "Divisão territorial oficial de Salvador usada para somar população, vulnerabilidade e obras localizadas.",
    explicacao:
      "É cada um dos bairros reconhecidos oficialmente pela Prefeitura de Salvador (Decreto nº 32.791/2020 no GeoSalvador) e compatibilizados com o Censo 2022 do IBGE. Localidades populares sem limite oficial próprio aparecem agrupadas dentro do Bairro Oficial correspondente.",
    exemploSalvador:
      "Pituba, Cajazeiras X e Plataforma são Bairros Oficiais distintos, cada um com seu próprio contorno no mapa e população medida pelo IBGE.",
    palavrasChave: [
      "bairro",
      "delimitação oficial",
      "censo 2022",
      "geosavlador",
      "171 bairros",
      "meu bairro",
    ],
  },
  {
    slug: "prefeitura-bairro",
    titulo: "Prefeitura-Bairro",
    categoria: "Território",
    resumo:
      "Macrorregião administrativa da Prefeitura que reúne vários Bairros Oficiais vizinhos.",
    explicacao:
      "Salvador organiza a gestão e a manutenção urbana em Prefeituras-Bairro. Muitos contratos de engenharia cobrem uma Prefeitura-Bairro inteira — por isso aparecem somados nessa visão, sem serem divididos artificialmente entre bairros individuais.",
    exemploSalvador:
      "Um contrato de manutenção de drenagem válido para toda a Prefeitura-Bairro Subúrbio/Ilhas é contabilizado na macrorregião, sem inventar quanto foi gasto em cada rua.",
    palavrasChave: [
      "macrorregião",
      "subúrbio/ilhas",
      "barra/pituba",
      "centro/brotas",
      "contratos regionais",
      "r$ 0 no meu bairro",
    ],
  },
  {
    slug: "zona-especial-nao-residencial",
    titulo: "Zona Especial Não-Residencial",
    categoria: "Território",
    resumo:
      "Bairro Oficial quase sem moradores fixos, isento do cálculo por habitante para não distorcer a comparação.",
    explicacao:
      "São territórios de uso institucional, aeroportuário ou logístico onde quase ninguém reside segundo o Censo 2022. Se dividíssemos o valor de uma grande obra por 0 ou 5 moradores, o valor por habitante pareceria artificialmente gigantesco. Por isso eles são marcados como isentos nos indicadores per capita e de vulnerabilidade, mas mantêm o valor total e a contagem de obras.",
    exemploSalvador:
      "Aeroporto, Porto Seco Pirajá e Centro Administrativo da Bahia - CAB são as três Zonas Especiais Não-Residenciais de Salvador.",
    palavrasChave: [
      "isento",
      "aeroporto",
      "porto seco pirajá",
      "cab",
      "sem moradores",
      "população zero",
    ],
  },
  {
    slug: "centralidade-metropolitana-baixa-populacao",
    titulo: "Centralidade Metropolitana de Baixa População Residente",
    categoria: "Território",
    resumo:
      "Bairro histórico e econômico de uso metropolitano com poucos moradores, isento apenas do cálculo por habitante.",
    explicacao:
      "Refere-se a áreas centrais que recebem centenas de milhares de trabalhadores e visitantes por dia, mas têm menos de 1.000 moradores e baixa densidade residencial no Censo 2022. Para evitar distorção estatística, o Investimento por Habitante fica isento nesse bairro, embora seu Índice de Vulnerabilidade e seus valores absolutos continuem preservados.",
    exemploSalvador:
      "O Comércio é classificado nessa regra: mantém seu índice de vulnerabilidade e o total de obras, mas aparece ao final da lista quando se compara R$ por morador.",
    palavrasChave: [
      "comércio",
      "baixa população",
      "isento per capita",
      "centro/brotas",
      "distorção estatística",
    ],
  },
  {
    slug: "nivel-de-alocacao-territorial",
    titulo: "Nível de Alocação Territorial",
    categoria: "Obras e Localização",
    resumo:
      "Indica com que precisão geográfica o contrato permite saber onde a obra acontece.",
    explicacao:
      "Nem todo contrato da Prefeitura informa o endereço exato da obra. O painel classifica cada contrato em quatro níveis para nunca chutar localizações: Pontual (endereço ou equipamento público exato), Bairro (cita o Bairro Oficial), Regional (Prefeitura-Bairro inteira) e Escopo Cidade (Não-Localizado).",
    exemploSalvador:
      "A reforma de uma escola municipal com endereço cadastrado entra no nível Pontual; já um contrato de tapa-buraco para toda a cidade fica em Escopo Cidade (Não-Localizado).",
    palavrasChave: [
      "pontual",
      "bairro",
      "regional",
      "precisão geográfica",
      "endereço da obra",
      "onde fica a obra",
    ],
  },
  {
    slug: "escopo-cidade-nao-localizado",
    titulo: "Escopo Cidade (Não-Localizado)",
    categoria: "Obras e Localização",
    resumo:
      "Contrato sem endereço ou bairro definido no objeto, que entra no total de Salvador sem inflar nenhum bairro.",
    explicacao:
      "Quando o contrato é genérico para todo o município ou cita lotes sem detalhar onde cada serviço foi feito, ele é classificado como Escopo Cidade (Não-Localizado). Esses valores compõem o total geral da Prefeitura e o indicador de transparência opaca, explicando por que bairros específicos podem exibir R$ 0 mesmo quando há obras acontecendo na rua.",
    exemploSalvador:
      "Um contrato amplo de manutenção de vias em diversos pontos de Salvador sem lista de endereços ou notas liquidadas por bairro aparece em Escopo Cidade (Não-Localizado).",
    palavrasChave: [
      "r$ 0 no meu bairro",
      "por que meu bairro aparece com r$ 0",
      "não localizado",
      "transparência opaca",
      "contrato genérico",
    ],
  },
  {
    slug: "frente-de-medicao",
    titulo: "Frente de Medição",
    categoria: "Obras e Localização",
    resumo:
      "Parcela de um contrato guarda-chuva comprovadamente executada e paga em um bairro ou região específica.",
    explicacao:
      "Mesmo quando um contrato grande nasce genérico ou regional, as notas de liquidação e medições mensais podem registrar exatamente em qual rua, escola ou bairro o serviço foi feito. O painel reconhece essas Frentes de Medição comprovadas apenas nos valores liquidados e pagos, sem inventar divisão do saldo total do contrato.",
    exemploSalvador:
      "Se um contrato guarda-chuva de contenção de encostas registra uma medição paga para a Rua X em Pau da Lima, essa parcela paga passa a aparecer em Pau da Lima como Frente de Medição.",
    palavrasChave: [
      "contrato guarda-chuva",
      "nota de liquidação",
      "medição comprovada",
      "valor pago por bairro",
      "r$ 0 no meu bairro",
    ],
  },
  {
    slug: "cota-parte-lista-fechada-contratual",
    titulo: "Cota-Parte de Lista Fechada Contratual",
    categoria: "Obras e Localização",
    resumo:
      "Divisão proporcional de um contrato que lista nominalmente de 2 a 8 locais ou equipamentos definidos.",
    explicacao:
      "Quando um contrato ou aditivo nomeia exatamente uma lista fechada de 2 a 8 obras ou equipamentos públicos em bairros diferentes, sem medição separada por local, o painel atribui a fração proporcional correspondente a cada localidade contemplada. Assim, todos os bairros da lista aparecem sem duplicar o valor total da cidade.",
    exemploSalvador:
      "Um contrato de R$ 4 milhões para reformar 4 praças nomeadas em 4 bairros diferentes atribui R$ 1 milhão de Cota-Parte para cada bairro, mantendo R$ 4 milhões no total de Salvador.",
    palavrasChave: [
      "lista fechada",
      "rateio proporcional",
      "múltiplos bairros",
      "cota-parte",
      "equipamentos",
    ],
  },
  {
    slug: "vocacao-da-obra",
    titulo: "Vocação da Obra",
    categoria: "Obras e Localização",
    resumo:
      "Separa obras locais de bairro daquelas que atendem grandes corredores ou marcos da cidade inteira.",
    explicacao:
      "Permite filtrar os contratos conforme quem eles atendem no dia a dia: Vizinhança e Comunidade (escolas, postos de saúde, encostas, praças e drenagem local), Mobilidade Estrutural e Orlas (viadutos, BRT, grandes avenidas e orlas) e Equipamentos e Marcos da Cidade (hospitais, arenas, mercados históricos e prédios centrais).",
    exemploSalvador:
      "Uma obra do BRT na Av. Antônio Carlos Magalhães tem vocação de Mobilidade Estrutural e Orlas; já a contenção de uma encosta residencial em São Caetano é de Vizinhança e Comunidade.",
    palavrasChave: [
      "vizinhança e comunidade",
      "mobilidade estrutural e orlas",
      "equipamentos e marcos da cidade",
      "filtro de vocação",
      "tipo de atendimento",
    ],
  },
  {
    slug: "semaforo-da-obra",
    titulo: "Semáforo da Obra",
    categoria: "Obras e Localização",
    resumo:
      "Sinalização automática (Verde, Amarelo ou Vermelho) que resume o risco e o andamento do contrato.",
    explicacao:
      "Classifica cada Obra Pública pela pior condição observada nos dados oficiais: Verde (no prazo, dentro da vigência original e aditivo abaixo de 10%), Amarelo (sofreu prorrogação de prazo ou aditivo de valor entre 10% e 25%) e Vermelho (paralisada/rescindida, prazo vencido sem conclusão, aditivo acima de 25% ou mais de 90 dias sem pagamento em execução).",
    exemploSalvador:
      "Uma obra com prazo atualizado vencido há meses e execução abaixo de 100% recebe sinal Vermelho na tabela e no mapa.",
    palavrasChave: [
      "verde",
      "amarelo",
      "vermelho",
      "obra crítica",
      "obra atrasada",
      "aditivo acima de 25%",
    ],
  },
  {
    slug: "funil-de-execucao-financeira",
    titulo: "Funil de Execução Financeira",
    categoria: "Dinheiro e Execução",
    resumo:
      "Caminho do dinheiro público desde o contrato assinado até o pagamento efetivo à empresa.",
    explicacao:
      "Mostra os cinco estágios orçamentários de uma obra na contabilidade pública: Valor Original Contratado (preço inicial), Valor Contratual Vigente (com aditivos e reajustes), Valor Empenhado (reservado no orçamento), Valor Liquidado (serviço medido e atestado) e Valor Pago (dinheiro efetivamente transferido).",
    exemploSalvador:
      "Na Ficha Limpa de uma obra, você pode ver um contrato de R$ 10 milhões vigentes com R$ 7 milhões liquidados e R$ 6,5 milhões já pagos.",
    palavrasChave: [
      "empenhado",
      "liquidado",
      "pago",
      "valor original",
      "etapas do dinheiro",
      "orçamento",
    ],
  },
  {
    slug: "valor-contratual-vigente",
    titulo: "Valor Contratual Vigente",
    categoria: "Dinheiro e Execução",
    resumo:
      "Valor global atualizado do contrato somando o preço inicial e todos os aditivos ou reajustes.",
    explicacao:
      "Representa quanto o contrato passou a valer oficialmente após somar o Valor Original Contratado e a Variação Contratual Acumulada. Não significa que todo esse dinheiro já foi gasto: ele mostra o teto comprometido no contrato atual.",
    exemploSalvador:
      "Se uma obra foi contratada por R$ 2 milhões e recebeu um aditivo de R$ 400 mil, seu Valor Contratual Vigente passa a ser R$ 2,4 milhões.",
    palavrasChave: [
      "valor vigente",
      "valor atualizado",
      "aditivo",
      "reajuste",
      "contrato total",
    ],
  },
  {
    slug: "valor-pago-acumulado-do-contrato",
    titulo: "Valor Pago Acumulado do Contrato",
    categoria: "Dinheiro e Execução",
    resumo:
      "Total de pagamentos registrados ao longo de toda a duração do contrato até a data de referência.",
    explicacao:
      "Soma todos os movimentos de pagamento oficiais registrados para aquele contrato até a data de referência aplicável. Mesmo quando você filtra por um Mandato Municipal específico (como 2021–2024), o filtro seleciona os contratos vigentes naquele mandato e exibe o valor acumulado do contrato inteiro.",
    exemploSalvador:
      "Um contrato assinado em 2020 e vigente até 2023 aparece no filtro de 2021–2024 com todos os pagamentos acumulados do contrato desde o início.",
    palavrasChave: [
      "valor pago",
      "pagamentos acumulados",
      "mandato municipal",
      "quanto foi pago",
      "executado",
    ],
  },
  {
    slug: "soma-parcial-de-pagamentos",
    titulo: "Soma Parcial de Pagamentos",
    categoria: "Dinheiro e Execução",
    resumo:
      "Aviso exibido quando o Portal da Transparência disponibiliza apenas parte do histórico de pagamentos.",
    explicacao:
      "Quando há uma limitação conhecida e comprovada na série histórica de pagamentos fornecida pela fonte oficial, o painel não oculta os registros disponíveis, mas sinaliza claramente que a soma exibida é parcial — evitando que o cidadão tome um recorte incompleto como o total definitivo pago.",
    exemploSalvador:
      "Se o portal oficial limitar a consulta de pagamentos de um contrato antigo a determinado período, o cartão do território ou da obra exibe o alerta de Soma Parcial.",
    palavrasChave: [
      "parcial",
      "histórico incompleto",
      "limitação da fonte",
      "portal da transparência",
      "pagamentos ausentes",
    ],
  },
  {
    slug: "investimento-por-habitante",
    titulo: "Investimento por Habitante",
    categoria: "Mapa e Indicadores",
    resumo:
      "Divide o total de obras localizadas no bairro ou Prefeitura-Bairro pelo número de moradores no Censo 2022.",
    explicacao:
      "Calcula quantos reais em obras localizadas correspondem a cada morador residente segundo o Censo 2022 do IBGE. Ajuda a comparar se bairros populosos estão recebendo proporcionalmente menos investimento do que áreas de menor população, sempre observando que contratos em Escopo Cidade não entram nessa divisão.",
    exemploSalvador:
      "Se um bairro tem 50 mil moradores e R$ 5 milhões em obras pagas localizadas, seu Investimento por Habitante é de R$ 100/hab.",
    palavrasChave: [
      "r$ por habitante",
      "per capita",
      "população ibge",
      "comparação entre bairros",
      "média municipal",
    ],
  },
  {
    slug: "indice-de-vulnerabilidade-do-bairro",
    titulo: "Índice de Vulnerabilidade do Bairro",
    categoria: "Mapa e Indicadores",
    resumo:
      "Nota de 0,00 a 1,00 baseada no Censo 2022 que mede carência de saneamento, água e escolaridade.",
    explicacao:
      "Indicador composto construído com dados do Censo 2022 do IBGE (déficit de esgotamento sanitário adequado, déficit de abastecimento de água por rede geral e taxa de analfabetismo a partir dos 15 anos), inspirado no IDS (IPP) e no IVS (IPEA). Quanto mais próximo de 1,00, maior a carência estrutural do bairro; nas Prefeituras-Bairro, o valor é a média ponderada pela população dos bairros.",
    exemploSalvador:
      "Permite comparar se bairros com maior vulnerabilidade social na lista lateral estão recebendo mais ou menos R$ por habitante em relação à média de Salvador.",
    palavrasChave: [
      "vulnerabilidade social",
      "censo 2022",
      "saneamento",
      "água",
      "analfabetismo",
      "nota metodológica",
    ],
  },
  {
    slug: "mapa-de-calor-de-obras-localizadas",
    titulo: "Mapa de Calor de Obras Localizadas",
    categoria: "Mapa e Indicadores",
    resumo:
      "Manchas visuais que mostram onde as obras localizadas se concentram ou faltam em Salvador.",
    explicacao:
      "Terceira camada do mapa que projeta manchas contínuas de intensidade sobre as obras com localização identificada (Pontual, Bairro, Cota-Parte de Lista Fechada Contratual e, no modo Valor Pago, Frentes de Medição). Usa escala logarítmica para que poucas megaobras não apaguem as obras menores de bairro, e nunca rateia contratos de Escopo Cidade nem transfere dinheiro entre bairros.",
    exemploSalvador:
      "Ao ativar 'Mapa de Calor' com 'Vulnerabilidade ao fundo', o cidadão pode enxergar áreas de alta vulnerabilidade em roxo que permanecem sem manchas quentes de obras localizadas.",
    palavrasChave: [
      "heatmap",
      "mancha de calor",
      "concentração de obras",
      "escala logarítmica",
      "vulnerabilidade ao fundo",
      "r$ 0 no meu bairro",
    ],
  },
];

export function parseGlossarioHash(hash: string): {
  isGlossario: boolean;
  slug: string | null;
} {
  const trimmed = (hash || "").trim();
  if (trimmed === "#glossario" || trimmed === "#glossario/") {
    return { isGlossario: true, slug: null };
  }
  if (trimmed.startsWith("#glossario-")) {
    const rawSlug = trimmed.slice("#glossario-".length).trim();
    return {
      isGlossario: true,
      slug: rawSlug.length > 0 ? decodeURIComponent(rawSlug) : null,
    };
  }
  return { isGlossario: false, slug: null };
}

function normalizeSearchText(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

export function filterGlossarioVerbetes(
  verbetes: GlossarioVerbete[],
  query: string,
  categoria: GlossarioCategoria | "todas"
): GlossarioVerbete[] {
  const normalizedQuery = normalizeSearchText(query);

  return verbetes.filter((verbete) => {
    if (categoria !== "todas" && verbete.categoria !== categoria) {
      return false;
    }
    if (!normalizedQuery) {
      return true;
    }

    const searchableFields = [
      verbete.titulo,
      verbete.resumo,
      verbete.explicacao,
      verbete.exemploSalvador,
      ...verbete.palavrasChave,
    ];

    return searchableFields.some((field) =>
      normalizeSearchText(field).includes(normalizedQuery)
    );
  });
}

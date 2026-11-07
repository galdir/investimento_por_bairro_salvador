/**
 * Utilitários de formatação de números, moedas e porcentagens para o Painel de Obras de Salvador.
 */

/**
 * Formata um valor numérico em Reais (BRL) no formato padrão brasileiro.
 *
 * @summary Converte número float em string monetária "R$ 1.234.567,89" ou sem centavos se redondo.
 * @description Utiliza Intl.NumberFormat configurado para pt-BR e moeda BRL, omitindo centavos quando o valor for inteiro exato.
 * @param valor - Número financeiro em ponto flutuante.
 * @returns String formatada contendo o símbolo da moeda e separadores de milhar.
 * @throws Não lança exceções; retorna "R$ 0,00" caso o valor seja NaN ou inválido.
 */
export function formatCurrency(valor: number): string {
  if (isNaN(valor)) return "R$ 0,00";
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: valor % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(valor);
}

/**
 * Formata um número inteiro com separadores de milhar (ponto no Brasil).
 *
 * @summary Formata contagem de pessoas ou itens em formato legível.
 * @description Converte números inteiros em formato com pontos decimais, ex: 65000 -> "65.000".
 * @param valor - Número inteiro a ser formatado.
 * @returns String formatada com pontos de milhar.
 * @throws Não lança exceções; retorna "0" caso o valor seja NaN ou inválido.
 */
export function formatNumber(valor: number): string {
  if (isNaN(valor)) return "0";
  return new Intl.NumberFormat("pt-BR").format(valor);
}

/**
 * Formata um número decimal como índice de duas casas decimais com vírgula.
 *
 * @summary Converte índices socioeconômicos para formato decimal brasileiro com vírgula.
 * @description Converte valores numéricos em ponto flutuante (como o Índice de Vulnerabilidade do Bairro de 0 a 1) para representação textual com duas casas decimais fixas (ex: 0.12 -> "0,12").
 * @param valor - Número decimal entre 0 e 1 ou índice arbitrário.
 * @returns String formatada com duas casas decimais separadas por vírgula.
 * @throws Não lança exceções; retorna "0,00" caso o valor seja NaN ou inválido.
 */
export function formatDecimal(valor: number): string {
  if (isNaN(valor)) return "0,00";
  return valor.toFixed(2).replace(".", ",");
}

/**
 * Formata uma string de data (ISO 8601 ou AAAA-MM-DD) para o formato brasileiro DD/MM/AAAA.
 *
 * @summary Converte data ISO em formato legível DD/MM/AAAA utilizando componentes UTC.
 * @description Evita distorções de fuso horário local convertendo diretamente ano, mês e dia UTC.
 * @param dataStr - String de data em formato ISO ou similar.
 * @returns String formatada no padrão brasileiro "DD/MM/AAAA" ou string original em caso de falha.
 * @throws Não lança exceções.
 */
export function formatDate(dataStr?: string | null): string {
  if (!dataStr) return "";
  try {
    const d = new Date(dataStr);
    if (isNaN(d.getTime())) {
      const parts = dataStr.slice(0, 10).split("-");
      if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
      return dataStr;
    }
    const ano = d.getUTCFullYear();
    const mes = String(d.getUTCMonth() + 1).padStart(2, "0");
    const dia = String(d.getUTCDate()).padStart(2, "0");
    return `${dia}/${mes}/${ano}`;
  } catch {
    return dataStr;
  }
}

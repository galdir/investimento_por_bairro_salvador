import React from "react";
import { GlobalKpis, IndexData, MetricType } from "../types";
import { formatCurrency, formatDate, formatNumber } from "../utils/formatters";
import { hasNumericPayment } from "../utils/territory";
import { resolverIntervaloTodosMandatos } from "../utils/mandatos";
import { MonetaryValue } from "./MonetaryValue";

function formatarInstanteSalvador(valor: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Bahia",
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(valor));
}

interface HeaderKpisProps {
  /**
   * Indicadores financeiros e quantitativos da comparação municipal (invariantes à seleção territorial).
   */
  kpis: GlobalKpis;
  /**
   * Camada territorial ativa na comparação ('prefeituras' ou 'bairros').
   */
  activeLayer?: "bairros" | "prefeituras";
  /**
   * Quantidade de territórios na comparação ativa.
   */
  territorioCount?: number;
  /**
   * Valor territorialmente alocado na comparação ativa segundo a métrica selecionada.
   */
  valorAlocadoTerritorial?: number;
  /**
   * Indica se há dados disponíveis de pagamento para o valor alocado (false se todos ausentes).
   */
  valorAlocadoDisponivel?: boolean;
  obrasSemPagamento?: number;
  limitacoesConhecidas?: string[];
  limitacoesAlocadas?: string[];
  limitacoesNaoLocalizadas?: string[];
  /**
   * Quantidade de obras alocadas aos territórios comparados.
   */
  totalObrasAlocadas?: number;
  /**
   * Quantidade de contratos exclusivos de Prefeitura-Bairro não rateados entre Bairros Oficiais.
   */
  contratosPrefeituraBairroSemRateioCount?: number;
  /**
   * Indica se a contagem de obras em Bairros Oficiais foi apurada no nível exato do recorte.
   */
  isExactLayerWorkCount?: boolean;
  /**
   * Data ISO de atualização do acervo (metadata.generatedAt) usada como fallback.
   */
  generatedAt?: string;
  /**
   * Metadados completos da atualização concluída do acervo (metadata.atualizacao).
   */
  atualizacao?: IndexData["metadata"]["atualizacao"];
  /**
   * Métrica financeira ativa: 'vigente' (Valor Contratual Vigente) ou 'executado' (Valor Pago).
   */
  metricType?: MetricType;
  /**
   * Mandato Municipal selecionado nos filtros (ex: '2025-2028', '2021-2024', '2017-2020' ou 'todos').
   */
  mandato?: string;
  /**
   * Lista de Mandatos Municipais disponíveis nos dados para compor o intervalo dinâmico de Todos os mandatos.
   */
  mandatosDisponiveis?: string[];
  /**
   * Aba principal ativa ('comparacao' ou 'tabela').
   */
  activeTab?: "comparacao" | "tabela";
  /**
   * Callback para ativar a aba de Comparação Territorial.
   */
  onSelectComparacao?: () => void;
  /**
   * Callback para ativar a aba de Tabela de Obras.
   */
  onSelectTabela?: () => void;
  /**
   * Quantidade de obras filtradas exibida no contador da aba Tabela de Obras.
   */
  tableObrasCount?: number;
}

/**
 * Cabeçalho compacto da comparação municipal de Salvador.
 * Mantém escopo municipal constante mesmo quando um território específico está selecionado.
 */
export const HeaderKpis: React.FC<HeaderKpisProps> = ({
  kpis,
  activeLayer = "prefeituras",
  territorioCount = 0,
  valorAlocadoTerritorial,
  valorAlocadoDisponivel = true,
  obrasSemPagamento = 0,
  limitacoesConhecidas = [],
  limitacoesAlocadas = [],
  limitacoesNaoLocalizadas = [],
  totalObrasAlocadas,
  contratosPrefeituraBairroSemRateioCount = 0,
  isExactLayerWorkCount = true,
  generatedAt,
  atualizacao,
  metricType = "executado",
  mandato,
  mandatosDisponiveis,
  activeTab = "comparacao",
  onSelectComparacao,
  onSelectTabela,
  tableObrasCount = 0,
}) => {
  const isVigente = metricType === "vigente";
  const metricLabel = isVigente ? "Valor Contratual Vigente" : "Valor Pago";
  const totalNaoLocalizado = kpis.totalNaoLocalizado ?? 0;
  const valorNaoLocalizado = isVigente
    ? (kpis.valorNaoLocalizado ?? 0)
    : hasNumericPayment(kpis.valorPagoNaoLocalizado)
      ? kpis.valorPagoNaoLocalizado
      : undefined;
  const percentualNaoLocalizado = kpis.percentualNaoLocalizado ?? 0;

  const valorAlocadoExibido =
    valorAlocadoTerritorial !== undefined ? valorAlocadoTerritorial : kpis.valorTotal;

  const intervaloTodosMandatos = resolverIntervaloTodosMandatos(mandatosDisponiveis);
  const mandatoLabel =
    mandato && mandato !== "todos"
      ? `Mandato ${mandato.replace("-", "–")}`
      : `Todos os mandatos (${intervaloTodosMandatos})`;

  const dataAtualizacao = !atualizacao && generatedAt ? formatDate(generatedAt) : null;

  return (
    <header
      data-testid="header-comparativo"
      className="bg-slate-900 text-white shadow-sm border-b border-slate-800 shrink-0"
    >
      <div className="max-w-[1440px] mx-auto px-3 sm:px-6 py-2 sm:py-2.5">
        {/* Linha 1: Título, indicação de acumulados, data de atualização, fontes e abas principais */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-2 pb-1.5 sm:pb-2 border-b border-slate-800">
          <div className="flex flex-col gap-1 min-w-0">
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
              <h1 className="text-sm sm:text-lg font-bold tracking-tight text-white">
                Mapa das Obras e do Dinheiro por Bairro
              </h1>
              <span
                data-testid="header-subtitulo"
                className="text-[11px] sm:text-xs text-slate-300"
              >
                Salvador • {mandatoLabel}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 text-[10px] sm:text-[11px] text-slate-300">
              <span
                data-testid="header-valores-acumulados"
                className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-medium text-emerald-300"
              >
                {mandato && mandato !== "todos"
                  ? "Valores acumulados dos contratos (não exclusivos do mandato)"
                  : "Valores acumulados no acervo"}
              </span>
              {dataAtualizacao && (
                <span
                  data-testid="header-atualizacao"
                  className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700"
                >
                  Dados gerados em {dataAtualizacao}
                </span>
              )}
              <span className="hidden xl:inline text-slate-400">
                Fontes: Portal da Transparência • GeoSalvador • IBGE Censo 2022
              </span>
            </div>
          </div>

          {onSelectComparacao && onSelectTabela && (
            <div
              role="tablist"
              aria-label="Visões principais do painel"
              className="inline-flex items-center gap-1 bg-slate-800/90 p-1 rounded-lg border border-slate-700 shadow-sm self-start lg:self-center shrink-0"
            >
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "comparacao"}
                data-testid="tab-comparacao"
                onClick={onSelectComparacao}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 ${
                  activeTab === "comparacao"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-300 hover:text-white hover:bg-slate-700/60"
                }`}
              >
                Comparação Territorial
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "tabela"}
                data-testid="tab-tabela"
                onClick={onSelectTabela}
                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 ${
                  activeTab === "tabela"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-300 hover:text-white hover:bg-slate-700/60"
                }`}
              >
                Tabela de Obras
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full tabular-nums ${
                    activeTab === "tabela" ? "bg-slate-200 text-slate-900" : "bg-slate-700 text-slate-200"
                  }`}
                >
                  {tableObrasCount}
                </span>
              </button>
            </div>
          )}
        </div>

        {/* Linha 2: Resumo comparativo municipal compacto (invariante à seleção de território) */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-1.5 sm:gap-2 pt-1.5 sm:pt-2">
          {/* 1. Quantidade de territórios comparados */}
          <div className="bg-slate-800/90 rounded-lg px-2.5 py-1.5 sm:px-3 sm:py-2 border border-slate-700/80 flex flex-col justify-between min-w-0">
            <span className="text-[10px] sm:text-[11px] font-medium text-slate-400 leading-tight">
              Territórios na comparação
            </span>
            <div className="mt-0.5 flex items-baseline gap-1.5">
              <span
                data-testid="kpi-territorios-comparados"
                className="text-xs sm:text-base font-bold text-white tabular-nums"
              >
                {formatNumber(territorioCount)}{" "}
                {activeLayer === "prefeituras" ? "Prefeituras-Bairro" : "Bairros Oficiais"}
              </span>
            </div>
          </div>

          {/* 2. Valor territorialmente alocado da métrica ativa */}
          <div className="bg-slate-800/90 rounded-lg px-2.5 py-1.5 sm:px-3 sm:py-2 border border-slate-700/80 flex flex-col justify-between min-w-0">
            <span className="text-[10px] sm:text-[11px] font-medium text-slate-400 leading-tight">
              {!isVigente && limitacoesAlocadas.length ? "Soma Parcial de Pagamentos" : metricLabel} alocado nos territórios
            </span>
            <div className="mt-0.5 flex flex-wrap items-baseline gap-x-2">
              {valorAlocadoDisponivel ? (
                <MonetaryValue
                  value={valorAlocadoExibido}
                  compact
                  tone="dark"
                  align="right"
                  testId="kpi-valor-alocado"
                  className="text-xs sm:text-base font-extrabold text-emerald-400"
                />
              ) : (
                <span
                  data-testid="kpi-valor-alocado"
                  className="text-xs font-semibold text-amber-300"
                >
                  Pagamento indisponível
                </span>
              )}
              {totalObrasAlocadas !== undefined && (
                <span className="text-[10px] sm:text-[11px] text-slate-400 leading-tight">
                  {activeLayer === "bairros" && isExactLayerWorkCount
                    ? `(${formatNumber(totalObrasAlocadas)} obras em bairros${
                        contratosPrefeituraBairroSemRateioCount > 0
                          ? ` • ${formatNumber(contratosPrefeituraBairroSemRateioCount)} de Prefeitura-Bairro sem rateio`
                          : ""
                      })`
                    : `(${formatNumber(totalObrasAlocadas)} obras localizadas)`}
                </span>
              )}
            </div>
          </div>

          {/* 3. Aviso sobre recursos sem localização (Escopo Cidade) */}
          <div
            data-testid="kpi-transparencia-opaca"
            className="bg-slate-800/90 rounded-lg px-2.5 py-1.5 sm:px-3 sm:py-2 border border-purple-500/30 flex flex-col justify-between min-w-0"
          >
            <span className="text-[10px] sm:text-[11px] font-medium text-purple-300 leading-tight">
              Sem localização • {!isVigente && limitacoesNaoLocalizadas.length ? "Soma Parcial de Pagamentos" : metricLabel} (Escopo Cidade)
            </span>
            <div className="mt-0.5 flex flex-wrap items-baseline gap-x-2">
              {valorNaoLocalizado !== undefined ? (
                <MonetaryValue
                  value={valorNaoLocalizado}
                  compact
                  tone="dark"
                  testId="kpi-valor-nao-localizado"
                  className="text-xs sm:text-base font-extrabold text-purple-300"
                />
              ) : (
                <span
                  data-testid="kpi-valor-nao-localizado"
                  className="text-xs font-semibold text-amber-300"
                >
                  Pagamento indisponível
                </span>
              )}
              <span className="text-[10px] sm:text-[11px] text-purple-200/90 leading-tight">
                {formatNumber(totalNaoLocalizado)} contratos ({percentualNaoLocalizado.toFixed(1).replace(".", ",")}%)
              </span>
            </div>
          </div>

          {/* 4. Referência municipal por habitante (escopo toda a cidade) */}
          <div className="bg-slate-800/90 rounded-lg px-2.5 py-1.5 sm:px-3 sm:py-2 border border-slate-700/80 flex flex-col justify-between min-w-0">
            <span className="text-[10px] sm:text-[11px] font-medium text-slate-400 leading-tight">
              Média alocada na cidade (Censo 2022)
            </span>
            <div className="mt-0.5 flex flex-wrap items-baseline gap-x-2">
              {valorAlocadoDisponivel ? (
                <span
                  data-testid="kpi-investimento-per-capita"
                  className="text-xs sm:text-base font-bold text-sky-300 tabular-nums"
                >
                  {formatCurrency(kpis.investimentoPorHabitanteCidade)} / hab
                </span>
              ) : (
                <span
                  data-testid="kpi-investimento-per-capita"
                  className="text-xs font-semibold text-amber-300"
                >
                  Pagamento indisponível
                </span>
              )}
              <span className="text-[10px] sm:text-[11px] text-slate-400 leading-tight">{!isVigente && limitacoesAlocadas.length ? "Soma Parcial de Pagamentos" : metricLabel} • Escopo municipal</span>
            </div>
          </div>
        </div>
        {atualizacao && (
          <div
            data-testid="header-atualizacao-detalhes"
            className="mt-2 pt-2 border-t border-slate-800/80 text-[11px] text-slate-300 flex flex-wrap gap-x-4 gap-y-1"
          >
            <span>Última atualização concluída em {formatarInstanteSalvador(atualizacao.concluidaEm)}</span>
            <span>Referência dos pagamentos: {formatDate(atualizacao.dataReferenciaPagamentos)}</span>
            <span>
              Consultas realizadas entre {formatarInstanteSalvador(atualizacao.inicioConsultas)} e{" "}
              {formatarInstanteSalvador(atualizacao.fimConsultas)} (horário de Salvador)
            </span>
            <span>As consultas ocorreram em momentos diferentes.</span>
            {atualizacao.coberturaHistorica === "nao_verificada" && (
              <span className="text-amber-200">
                A abrangência histórica da fonte não foi verificada de forma independente.
              </span>
            )}
            {atualizacao.limitacoesConhecidas.map((limitacao) => (
              <span key={limitacao} className="text-amber-200">
                {limitacao}
              </span>
            ))}
          </div>
        )}
        {!isVigente && obrasSemPagamento > 0 && (
          <p className="mt-2 text-xs text-amber-200" role="status">
            {formatNumber(obrasSemPagamento)} contrato(s) com pagamento indisponível no acervo selecionado; a soma usa os valores disponíveis.
          </p>
        )}
        {!isVigente && limitacoesConhecidas.length > 0 && <div className="mt-2 text-xs text-amber-200">
          {limitacoesConhecidas.map((limite) => <p key={limite}>{limite}</p>)}
        </div>}
      </div>
    </header>
  );
};

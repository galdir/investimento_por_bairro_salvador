import React, { useEffect } from "react";
import { FichaLimpaObra } from "../types";
import { formatCurrency } from "../utils/formatters";

interface FichaLimpaModalProps {
  /**
   * Dados detalhados da obra pública ou nulo se fechado.
   */
  obra: FichaLimpaObra | null;
  /**
   * Indicador se a requisição sob demanda está em andamento.
   */
  loading?: boolean;
  /**
   * Callback para fechar a ficha detalhada.
   */
  onClose: () => void;
  /**
   * Callback para aplicar filtro do painel pela construtora em um clique.
   */
  onFilterByEmpreiteira?: (credor: string) => void;
}

/**
 * Componente modal/drawer da Ficha Limpa da Obra sob demanda (Camada C).
 *
 * @summary Apresenta o prontuário completo do contrato de engenharia com Funil Financeiro, DOM, Aditivos e Empreiteira.
 * @description Exibe a visão analítica sob demanda da obra pública clicada no mapa ou na tabela,
 * detalhando:
 * 1. Objeto limpo, processo administrativo, datas originais e prorrogadas de vigência;
 * 2. Construtora/empreiteira (razão social, CNPJ e resumo de concentração de obras na cidade com botão de filtro direto);
 * 3. Referência ao Diário Oficial do Município (DOM);
 * 4. Funil de Execução Financeira completo comparado com a medição física realizada;
 * 5. Tabela detalhada de Aditivos Contratuais (prazo, valor e DOM de publicação);
 * 6. Fontes de recurso e dotação orçamentária do município.
 *
 * @param props - Propriedades de controle e dados da obra sob demanda.
 * @returns Elemento JSX do modal ou nulo se não houver obra selecionada.
 */
export const FichaLimpaModal: React.FC<FichaLimpaModalProps> = ({
  obra,
  loading = false,
  onClose,
  onFilterByEmpreiteira,
}) => {
  // Fecha modal com a tecla ESC
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!obra && !loading) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4 md:p-6 animate-fadeIn"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        data-testid="ficha-limpa-modal"
        className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden text-slate-800"
      >
        {/* Cabeçalho do Modal */}
        <div className="bg-slate-900 text-white px-5 py-4 flex items-start justify-between gap-4 border-b border-slate-800 shrink-0">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              <span
                data-testid="ficha-limpa-orgao"
                className="bg-slate-800 text-emerald-400 font-bold text-[11px] px-2.5 py-0.5 rounded-full border border-emerald-500/30"
              >
                {obra?.unidadeGestora || "Carregando..."}
              </span>
              {obra?.tema && (
                <span className="bg-slate-800 text-slate-300 text-[11px] px-2.5 py-0.5 rounded-full border border-slate-700">
                  {obra.tema}
                </span>
              )}
              {obra?.semaforo && (
                <span
                  className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border flex items-center gap-1.5 ${
                    obra.semaforo.status === "VERMELHO"
                      ? "bg-rose-950/60 text-rose-300 border-rose-600/40"
                      : obra.semaforo.status === "AMARELO"
                      ? "bg-amber-950/60 text-amber-300 border-amber-600/40"
                      : "bg-emerald-950/60 text-emerald-300 border-emerald-600/40"
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      obra.semaforo.status === "VERMELHO"
                        ? "bg-rose-500 animate-pulse"
                        : obra.semaforo.status === "AMARELO"
                        ? "bg-amber-400"
                        : "bg-emerald-400"
                    }`}
                  ></span>
                  {obra.semaforo.rotulo}
                </span>
              )}
              {obra?.nivel && (
                <span className="bg-slate-800 text-sky-300 text-[11px] px-2.5 py-0.5 rounded-full border border-sky-500/30">
                  {obra.nivel}
                  {obra.bairro ? `: ${obra.bairro}` : obra.prefeituraBairro ? `: ${obra.prefeituraBairro}` : ""}
                </span>
              )}
            </div>

            <h2
              data-testid="ficha-limpa-objeto"
              className="text-base sm:text-lg font-extrabold text-white leading-snug"
            >
              {obra?.objeto || "Carregando Ficha Limpa da Obra..."}
            </h2>

            <div className="flex flex-wrap items-center gap-3 mt-1.5 text-xs text-slate-400">
              <span>
                Contrato SIGEF:{" "}
                <strong data-testid="ficha-limpa-contrato" className="text-white">
                  {obra?.numeroContrato || "—"}
                </strong>
              </span>
              {obra?.nuProcesso && (
                <>
                  <span>•</span>
                  <span>Processo Administrativo: <strong className="text-white">{obra.nuProcesso}</strong></span>
                </>
              )}
              {obra?.situacao && (
                <>
                  <span>•</span>
                  <span>Situação: <strong className="text-white">{obra.situacao}</strong></span>
                </>
              )}
            </div>
          </div>

          <button
            type="button"
            data-testid="btn-fechar-ficha-limpa"
            onClick={onClose}
            className="text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 p-2 rounded-xl transition-colors focus:outline-none shrink-0"
            title="Fechar Ficha Limpa (ESC)"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Conteúdo com Rolagem */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-6">
          {loading && !obra ? (
            <div className="py-16 text-center">
              <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
              <p className="text-sm text-slate-500 font-medium">
                Carregando histórico e prontuário completo da obra...
              </p>
            </div>
          ) : obra ? (
            <>
              {/* 1. Card da Empreiteira e Concentração em Salvador */}
              <div className="bg-slate-50 rounded-xl p-4 border border-slate-200">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      Construtora Responsável
                    </span>
                    <h3
                      data-testid="ficha-limpa-empreiteira-nome"
                      className="text-sm sm:text-base font-extrabold text-slate-900 mt-0.5"
                    >
                      {obra.empreiteira?.razaoSocial || "Não informada"}
                    </h3>
                    <p className="text-xs text-slate-600 mt-0.5">
                      CNPJ:{" "}
                      <strong
                        data-testid="ficha-limpa-empreiteira-cnpj"
                        className="text-slate-800 font-mono"
                      >
                        {obra.empreiteira?.cnpj || "Não informado"}
                      </strong>
                    </p>
                    <p
                      data-testid="ficha-limpa-empreiteira-concentracao"
                      className="text-xs text-emerald-800 font-medium mt-1"
                    >
                      Esta construtora detém <strong>{obra.empreiteira?.totalObras || 1} obra(s)</strong> contratadas em Salvador (<strong>{obra.empreiteira?.outrasObrasCount || 0} outra(s)</strong> no município), totalizando <strong>{formatCurrency(obra.empreiteira?.valorTotalContratado || obra.funilFinanceiro.valorContratualVigente)}</strong> em recursos municipais.
                    </p>
                  </div>

                  {onFilterByEmpreiteira && (
                    <button
                      type="button"
                      data-testid="btn-filtrar-por-empreiteira"
                      onClick={() => onFilterByEmpreiteira(obra.empreiteira?.razaoSocial || "")}
                      className="shrink-0 px-3.5 py-2 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg shadow-sm transition-colors flex items-center justify-center gap-1.5"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                      </svg>
                      Filtrar painel por esta empreiteira
                    </button>
                  )}
                </div>
              </div>

              {/* 2. Diário Oficial do Município (DOM) e Vigência */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-0.5">
                    Diário Oficial (DOM)
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
                    <strong data-testid="ficha-limpa-dom" className="text-slate-900 text-sm">
                      Edição nº {obra.dom?.nuDom || "Não informada"}
                    </strong>
                  </div>
                </div>

                <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-0.5">
                    Início de Vigência
                  </span>
                  <strong className="text-slate-800 text-sm">
                    {obra.vigencia?.dataInicio ? obra.vigencia.dataInicio.slice(0, 10).split("-").reverse().join("/") : "—"}
                  </strong>
                </div>

                <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-0.5">
                    Término Original
                  </span>
                  <strong className="text-slate-800 text-sm">
                    {obra.vigencia?.dataFimOriginal ? obra.vigencia.dataFimOriginal.slice(0, 10).split("-").reverse().join("/") : "—"}
                  </strong>
                </div>

                <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-0.5">
                    Término Atualizado
                  </span>
                  <strong className={`text-sm ${obra.vigencia?.dataTerminoAtualizado !== obra.vigencia?.dataFimOriginal ? "text-amber-700 font-bold" : "text-slate-800"}`}>
                    {obra.vigencia?.dataTerminoAtualizado ? obra.vigencia.dataTerminoAtualizado.slice(0, 10).split("-").reverse().join("/") : "—"}
                  </strong>
                </div>
              </div>

              {/* 3. Funil de Execução Financeira completo */}
              <div
                data-testid="funil-financeiro-container"
                className="bg-slate-50/80 rounded-xl p-4 sm:p-5 border border-slate-200"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
                  <div>
                    <h4 className="text-sm font-extrabold text-slate-900 flex items-center gap-2">
                      <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Funil de Execução Financeira da Obra
                    </h4>
                    <p className="text-xs text-slate-500">
                      Do compromisso contratual original ao valor efetivamente pago e medido
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-600 font-medium">Execução Física:</span>
                    <span
                      data-testid="funil-percentual-executado"
                      className="px-2.5 py-1 rounded-full text-xs font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-300"
                    >
                      {(obra.funilFinanceiro?.percentualExecutado || 0).toFixed(1).replace(".", ",")}%
                    </span>
                  </div>
                </div>

                {/* Blocos de Estágios do Funil */}
                <div className="grid grid-cols-1 sm:grid-cols-5 gap-2.5 mb-4">
                  {/* Estágio 1: Valor Original */}
                  <div className="bg-white p-3 rounded-lg border border-slate-200">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                      1. Original
                    </span>
                    <div
                      data-testid="funil-valor-original"
                      className="text-xs sm:text-sm font-bold text-slate-800 mt-1"
                    >
                      {formatCurrency(obra.funilFinanceiro?.valorOriginal || 0)}
                    </div>
                    <span className="text-[10px] text-slate-500">Contrato inicial</span>
                  </div>

                  {/* Estágio 2: Valor Vigente */}
                  <div className="bg-white p-3 rounded-lg border border-slate-200">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                      2. Vigente (+Aditivo)
                    </span>
                    <div
                      data-testid="funil-valor-vigente"
                      className="text-xs sm:text-sm font-bold text-slate-900 mt-1"
                    >
                      {formatCurrency(obra.funilFinanceiro?.valorContratualVigente || 0)}
                    </div>
                    {obra.funilFinanceiro?.valorAditivos && obra.funilFinanceiro.valorAditivos > 0 ? (
                      <span className="text-[10px] font-bold text-amber-700">
                        +{obra.funilFinanceiro.deltaPercentualAditivos?.toFixed(1).replace(".", ",")}% aditivos
                      </span>
                    ) : (
                      <span className="text-[10px] text-emerald-600 font-medium">Sem acréscimo</span>
                    )}
                  </div>

                  {/* Estágio 3: Valor Empenhado */}
                  <div className="bg-white p-3 rounded-lg border border-slate-200">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                      3. Empenhado
                    </span>
                    <div
                      data-testid="funil-valor-empenhado"
                      className="text-xs sm:text-sm font-bold text-slate-800 mt-1"
                    >
                      {formatCurrency(obra.funilFinanceiro?.valorEmpenhado || 0)}
                    </div>
                    <span className="text-[10px] text-slate-500">Reserva orçamentária</span>
                  </div>

                  {/* Estágio 4: Valor Liquidado */}
                  <div className="bg-white p-3 rounded-lg border border-slate-200">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                      4. Liquidado
                    </span>
                    <div
                      data-testid="funil-valor-liquidado"
                      className="text-xs sm:text-sm font-bold text-slate-800 mt-1"
                    >
                      {formatCurrency(obra.funilFinanceiro?.valorLiquidado || 0)}
                    </div>
                    <span className="text-[10px] text-slate-500">Medição atestada</span>
                  </div>

                  {/* Estágio 5: Valor Pago */}
                  <div className="bg-white p-3 rounded-lg border border-slate-200">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                      5. Pago
                    </span>
                    <div
                      data-testid="funil-valor-pago"
                      className="text-xs sm:text-sm font-bold text-emerald-700 mt-1"
                    >
                      {formatCurrency(obra.funilFinanceiro?.valorPago || 0)}
                    </div>
                    <span className="text-[10px] text-slate-500">Repasse à empresa</span>
                  </div>
                </div>

                {/* Barra Comparativa: Avanço Financeiro vs Avanço Físico */}
                <div className="space-y-2 pt-2 border-t border-slate-200 text-xs">
                  <div>
                    <div className="flex justify-between text-slate-600 mb-1">
                      <span>Execução Financeira (Pago / Vigente):</span>
                      <strong className="text-slate-800">
                        {obra.funilFinanceiro?.valorContratualVigente > 0
                          ? `${((obra.funilFinanceiro.valorPago / obra.funilFinanceiro.valorContratualVigente) * 100).toFixed(1).replace(".", ",")}%`
                          : "0%"}
                      </strong>
                    </div>
                    <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-indigo-600 h-2 rounded-full"
                        style={{
                          width: `${Math.min(
                            100,
                            obra.funilFinanceiro?.valorContratualVigente > 0
                              ? (obra.funilFinanceiro.valorPago / obra.funilFinanceiro.valorContratualVigente) * 100
                              : 0
                          )}%`,
                        }}
                      ></div>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-slate-600 mb-1">
                      <span>Execução Física Medida (percentualExecutado):</span>
                      <strong className="text-emerald-700">
                        {(obra.funilFinanceiro?.percentualExecutado || 0).toFixed(1).replace(".", ",")}%
                      </strong>
                    </div>
                    <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-emerald-500 h-2 rounded-full"
                        style={{
                          width: `${Math.min(100, obra.funilFinanceiro?.percentualExecutado || 0)}%`,
                        }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>

              {/* 4. Aditivos Contratuais */}
              <div
                data-testid="secao-aditivos-obra"
                className="bg-white rounded-xl border border-slate-200 p-4"
              >
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                    <svg className="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Histórico de Aditivos Contratuais
                  </h4>
                  <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full font-medium">
                    {obra.aditivos?.length || 0} {obra.aditivos?.length === 1 ? "aditivo" : "aditivos"}
                  </span>
                </div>

                {obra.aditivos && obra.aditivos.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[10px]">
                          <th className="py-2 px-2.5">Nº Aditivo</th>
                          <th className="py-2 px-2.5">Tipo de Alteração</th>
                          <th className="py-2 px-2.5">Justificativa / Objeto</th>
                          <th className="py-2 px-2.5">Assinatura</th>
                          <th className="py-2 px-2.5">Publicação</th>
                          <th className="py-2 px-2.5">Novo Término</th>
                          <th className="py-2 px-2.5">DOM</th>
                          <th className="py-2 px-2.5 text-right">Valor Adicionado</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {obra.aditivos.map((ad, idx) => (
                          <tr
                            key={idx}
                            data-testid={`aditivo-item-${idx}`}
                            className="hover:bg-slate-50"
                          >
                            <td className="py-2.5 px-2.5 font-bold text-slate-800 whitespace-nowrap">
                              {ad.nuAditivo}
                            </td>
                            <td className="py-2.5 px-2.5 whitespace-nowrap">
                              <span className="bg-amber-50 text-amber-800 border border-amber-200 px-2 py-0.5 rounded text-[11px] font-semibold">
                                {ad.dsTipoAlteracao}
                              </span>
                            </td>
                            <td className="py-2.5 px-2.5 text-slate-600 max-w-xs">
                              {ad.dsObjetoAditivo || "—"}
                            </td>
                            <td className="py-2.5 px-2.5 text-slate-600 whitespace-nowrap">
                              {ad.dtAssinatura ? ad.dtAssinatura.slice(0, 10).split("-").reverse().join("/") : "—"}
                            </td>
                            <td className="py-2.5 px-2.5 text-slate-600 whitespace-nowrap">
                              {ad.dtPublicacao ? ad.dtPublicacao.slice(0, 10).split("-").reverse().join("/") : "—"}
                            </td>
                            <td className="py-2.5 px-2.5 text-slate-700 whitespace-nowrap font-medium">
                              {ad.dtTerminoVigencia ? ad.dtTerminoVigencia.slice(0, 10).split("-").reverse().join("/") : "—"}
                            </td>
                            <td className="py-2.5 px-2.5 text-indigo-700 whitespace-nowrap font-semibold">
                              {ad.nuDom ? `Ed. ${ad.nuDom}` : "—"}
                            </td>
                            <td className="py-2.5 px-2.5 text-right font-bold text-slate-900 whitespace-nowrap">
                              {ad.vlAditivo > 0 ? `+${formatCurrency(ad.vlAditivo)}` : "R$ 0,00"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="bg-slate-50 p-4 rounded-lg text-center text-xs text-slate-500">
                    Nenhum termo aditivo registrado para este contrato (valores e prazos mantidos nos termos originais).
                  </div>
                )}
              </div>

              {/* 5. Dotação Orçamentária e Fonte de Recurso */}
              <div className="bg-white rounded-xl border border-slate-200 p-4">
                <h4 className="text-sm font-bold text-slate-900 mb-2 flex items-center gap-1.5">
                  <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                  Dotação Orçamentária e Origem dos Recursos
                </h4>

                <div data-testid="ficha-limpa-dotacao" className="space-y-2">
                  {obra.dotacao && obra.dotacao.length > 0 ? (
                    obra.dotacao.map((dt, idx) => (
                      <div
                        key={idx}
                        className="bg-slate-50 p-3 rounded-lg border border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs"
                      >
                        <div>
                          <span className="font-semibold text-slate-800">
                            {dt.fonteRecurso}
                          </span>
                          {dt.subacao && (
                            <p className="text-[11px] text-slate-500 mt-0.5">
                              Subação: {dt.subacao}
                            </p>
                          )}
                        </div>
                        {dt.classificacao && (
                          <span className="font-mono text-[10px] text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200 shrink-0">
                            {dt.classificacao}
                          </span>
                        )}
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-slate-500">
                      Fonte de recurso não discriminada no extrato de dotação.
                    </p>
                  )}
                </div>
              </div>
            </>
          ) : null}
        </div>

        {/* Rodapé com botão Fechar */}
        <div className="bg-slate-100 px-5 py-3 border-t border-slate-200 flex justify-end shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-semibold bg-white hover:bg-slate-50 border border-slate-300 rounded-lg text-slate-700 shadow-xs transition-colors"
          >
            Fechar Ficha Limpa
          </button>
        </div>
      </div>
    </div>
  );
};

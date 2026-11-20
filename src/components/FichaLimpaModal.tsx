import React, { useEffect, useRef, useState } from "react";
import { FichaLimpaObra, ObraCompacta } from "../types";
import { formatCurrency, formatDate } from "../utils/formatters";
import { getObraCotasListaFechada } from "../utils/territory";

const PORTAL_TRANSPARENCIA_URL = "https://www.transparencia.salvador.ba.gov.br/";
const PORTAL_DOM_URL = "https://dom.salvador.ba.gov.br/";
const DOM_INVALIDOS = new Set(["", "nao informado", "não informado", "nao informada", "não informada", "none", "null"]);
const MAX_OBJECT_TITLE_WORDS = 8;
const MAX_OBJECT_TITLE_LENGTH = 72;
const TRAILING_TITLE_CONNECTORS = new Set([
  "de", "da", "do", "das", "dos", "e", "com", "para", "por", "em", "a", "o", "as", "os", "no", "na", "nos", "nas", "ao", "aos", "à", "às",
]);

function formatarDataCalendarioValida(dataStr?: string | null): string | null {
  if (!dataStr) return null;
  const match = dataStr.trim().match(/^(\d{4})-(\d{2})-(\d{2})(?:$|T)/);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const d = new Date(Date.UTC(year, month - 1, day));
  if (
    d.getUTCFullYear() !== year ||
    d.getUTCMonth() !== month - 1 ||
    d.getUTCDate() !== day
  ) {
    return null;
  }
  return `${String(day).padStart(2, "0")}/${String(month).padStart(2, "0")}/${year}`;
}

function normalizeObjectText(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}

function summarizeObject(value: string): string {
  const normalized = normalizeObjectText(value);
  const subject = normalized
    .replace(/^contrata[çc][ãa]o de empresa para (?:execu[çc][ãa]o de )?servi[çc]os? comu(?:m|ns) de engenharia para (?:o |a )?/i, "")
    .replace(/^contrata[çc][ãa]o de empresa para execu[çc][ãa]o de servi[çc]os de engenharia para\s+/i, "")
    .replace(/^contrata[çc][ãa]o de empresas? (?:capacitada|especializada)s? para execu[çc][ãa]o d(?:as obras|a obra|os servi[çc]os|e servi[çc]os|e obras) de\s+/i, "")
    .replace(/^contrata[çc][ãa]o de empresa para execu[çc][ãa]o d(?:as obras|a obra|os servi[çc]os|e servi[çc]os|e obras) de\s+/i, "")
    .replace(/^contrata[çc][ãa]o de empresa especializada em servi[çc]o de arquitetura para (?=elabora[çc][ãa]o\b)/i, "")
    .replace(/^contrata[çc][ãa]o de empresa de engenharia civil especializada em manuten[çc][ãa]o predial para (?=presta[çc][ãa]o de servi[çc]os\b)/i, "")
    .replace(/^contrata[çc][ãa]o de empresas?(?: (?:especializadas?|capacitadas?|de engenharia(?: civil)?))? para (?=\S)/i, "")
    .replace(/^contrata[çc][ãa]o de empresa especializada na (?=presta[çc][ãa]o\b)/i, "");
  if (subject === normalized && /^contrata[çc][ãa]o de empresas?\b/i.test(normalized)) {
    return normalized;
  }
  const words = subject.split(" ");
  const exceedsWordLimit = words.length > MAX_OBJECT_TITLE_WORDS;
  const limitedWords = words.slice(0, MAX_OBJECT_TITLE_WORDS);
  if (exceedsWordLimit) {
    while (limitedWords.length > 1 && TRAILING_TITLE_CONNECTORS.has(limitedWords[limitedWords.length - 1].toLowerCase())) {
      limitedWords.pop();
    }
  }
  const wordLimited = limitedWords.join(" ");
  if (wordLimited.length <= MAX_OBJECT_TITLE_LENGTH) {
    return exceedsWordLimit ? `${wordLimited}…` : wordLimited;
  }

  const characters = Array.from(wordLimited).slice(0, MAX_OBJECT_TITLE_LENGTH).join("");
  const wordBoundary = characters.lastIndexOf(" ");
  const shortened = wordBoundary > MAX_OBJECT_TITLE_LENGTH / 2
    ? characters.slice(0, wordBoundary)
    : characters;
  return `${shortened.trimEnd()}…`;
}

function isDomValido(val?: string | null): boolean {
  if (!val) return false;
  return !DOM_INVALIDOS.has(val.trim().toLowerCase());
}

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
   * Mensagem de erro ao tentar carregar os detalhes da obra.
   */
  error?: string | null;
  /**
   * Obra compacta solicitada (para identificar contrato/objeto em carregamento ou erro).
   */
  requestedObra?: ObraCompacta | null;
  /**
   * Callback para tentar novamente o carregamento da Ficha Limpa.
   */
  onRetry?: () => void;
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
  error = null,
  requestedObra = null,
  onRetry,
  onClose,
  onFilterByEmpreiteira,
}) => {
  const [copiadoCampo, setCopiadoCampo] = useState<"contrato" | "processo" | null>(null);
  const isOpen = Boolean(obra || loading || error);
  const dialogRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const objetoOriginal = obra?.objeto || requestedObra?.objeto || "";
  const tituloResumo = objetoOriginal ? summarizeObject(objetoOriginal) : "";
  const objetoOriginalNormalizado = normalizeObjectText(objetoOriginal);
  const exibeObjetoOriginal = Boolean(objetoOriginal && tituloResumo !== objetoOriginalNormalizado);
  const percentualExecucaoFisica = obra?.funilFinanceiro?.percentualExecutado ?? 0;
  const valorContratualVigente = obra?.funilFinanceiro?.valorContratualVigente ?? 0;
  const valorPago = obra?.funilFinanceiro?.valorPago;
  const percentualPagoSobreVigente =
    valorPago != null && valorContratualVigente > 0
      ? (valorPago / valorContratualVigente) * 100
      : null;

  const handleCopiar = async (valor: string, campo: "contrato" | "processo") => {
    try {
      await navigator.clipboard?.writeText(valor);
      setCopiadoCampo(campo);
      setTimeout(() => setCopiadoCampo((prev) => (prev === campo ? null : prev)), 2000);
    } catch {
      // Ignora erro de clipboard em ambientes sem permissão
    }
  };

  // Mantém o foco dentro da ficha e fecha com ESC.
  useEffect(() => {
    if (!isOpen) return;
    dialogRef.current?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onCloseRef.current();
        return;
      }

      if (e.key !== "Tab") return;

      const focusableElements = dialogRef.current?.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary:not([tabindex="-1"]), [tabindex]:not([tabindex="-1"])'
      );
      const focusable = Array.from(focusableElements || []).filter(
        (element) => element.getAttribute("aria-hidden") !== "true"
      );
      if (focusable.length === 0) {
        e.preventDefault();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (active === dialogRef.current) {
        e.preventDefault();
        (e.shiftKey ? last : first).focus();
      } else if (e.shiftKey && (active === first || !dialogRef.current?.contains(active))) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && (active === last || !dialogRef.current?.contains(active))) {
        e.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  const cotasListaFechada = getObraCotasListaFechada(obra);
  const totalCotasUnidades =
    cotasListaFechada[0]?.totalUnidades ||
    cotasListaFechada.reduce((acc, c) => acc + (c.unidades || 0), 0);
  const percentualExecucaoFisicaFormatado = percentualExecucaoFisica.toFixed(1).replace(".", ",");

  return (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby="ficha-limpa-titulo"
      tabIndex={-1}
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4 md:p-6 animate-fadeIn"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        data-testid="ficha-limpa-modal"
        className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[92vh] overflow-y-auto text-slate-800"
      >
        {/* Cabeçalho do Modal */}
        <div className="bg-slate-900 text-white px-5 py-4 flex items-start justify-between gap-4 border-b border-slate-800 shrink-0">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              <span
                data-testid="ficha-limpa-orgao"
                className="bg-slate-800 text-emerald-400 font-bold text-[11px] px-2.5 py-0.5 rounded-full border border-emerald-500/30"
              >
                {obra?.unidadeGestora || requestedObra?.unidadeGestora || (error ? "Detalhe indisponível" : "Carregando...")}
              </span>
              {obra?.tema && (
                <span className="bg-slate-800 text-slate-300 text-[11px] px-2.5 py-0.5 rounded-full border border-slate-700">
                  {obra.tema}
                </span>
              )}
              {obra && (
                <span
                  data-testid="ficha-limpa-vocacao"
                  className="bg-sky-950/60 text-sky-200 text-[11px] font-medium px-2.5 py-0.5 rounded-full border border-sky-600/40"
                >
                  {obra.vocacao || "Vizinhança e Comunidade"}
                </span>
              )}
              {obra?.semaforo && (
                <span
                  className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border flex items-center gap-1.5 ${obra.semaforo.status === "VERMELHO"
                    ? "bg-rose-950/60 text-rose-300 border-rose-600/40"
                    : obra.semaforo.status === "AMARELO"
                      ? "bg-amber-950/60 text-amber-300 border-amber-600/40"
                      : "bg-emerald-950/60 text-emerald-300 border-emerald-600/40"
                    }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${obra.semaforo.status === "VERMELHO"
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
                  {cotasListaFechada.length > 0
                    ? obra.nivel
                    : `${obra.nivel}${obra.bairro ? `: ${obra.bairro}` : obra.prefeituraBairro ? `: ${obra.prefeituraBairro}` : ""}`}
                </span>
              )}
              {cotasListaFechada.length > 0 && (
                <span
                  data-testid="ficha-badge-cota-parte"
                  className="bg-amber-950/80 text-amber-200 text-[11px] font-semibold px-2.5 py-0.5 rounded-full border border-amber-400/40"
                >
                  Cota-Parte territorial
                </span>
              )}
            </div>

            <h2
              id="ficha-limpa-titulo"
              data-testid="ficha-limpa-objeto"
              className="text-base sm:text-lg font-extrabold text-white leading-snug break-words"
            >
              <span data-testid="ficha-limpa-titulo-resumido">
                {tituloResumo ||
                  (error ? "Não foi possível carregar os detalhes da obra" : "Carregando Ficha Limpa da Obra...")}
              </span>
            </h2>
            {exibeObjetoOriginal && (
              <details className="mt-2 max-w-3xl text-xs text-slate-200">
                <summary
                  data-testid="ficha-limpa-toggle-objeto-original"
                  className="w-fit cursor-pointer font-semibold underline underline-offset-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 rounded"
                >
                  Ver objeto original completo
                </summary>
                <p
                  data-testid="ficha-limpa-objeto-original"
                  className="mt-2 text-slate-300 leading-relaxed break-words"
                >
                  {objetoOriginal}
                </p>
              </details>
            )}

            <div className="flex flex-wrap items-center gap-3 mt-1.5 text-xs text-slate-400">
              <span>
                Contrato SIGEF:{" "}
                <strong data-testid="ficha-limpa-contrato" className="text-white">
                  {obra?.numeroContrato || requestedObra?.numeroContrato || "—"}
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
            aria-label="Fechar Ficha Limpa da Obra"
            className="text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 p-2 rounded-xl transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 shrink-0"
            title="Fechar Ficha Limpa (ESC)"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Conteúdo com Rolagem */}
        <div className="p-5 sm:p-6 space-y-6">
          {loading && !obra ? (
            <div className="py-16 text-center">
              <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
              <p className="text-sm text-slate-500 font-medium">
                Carregando histórico e prontuário completo da obra...
              </p>
            </div>
          ) : error && !obra ? (
            <div
              data-testid="ficha-limpa-erro"
              role="alert"
              className="py-8 px-4 bg-rose-50 border border-rose-200 rounded-xl text-center space-y-3"
            >
              <div className="w-11 h-11 rounded-full bg-rose-100 text-rose-700 mx-auto flex items-center justify-center">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="text-sm font-bold text-rose-950">
                Não foi possível carregar os detalhes desta obra
              </h3>
              <p className="text-xs text-rose-900 max-w-md mx-auto leading-relaxed">
                {error}
                {requestedObra?.numeroContrato
                  ? ` (Contrato ${requestedObra.numeroContrato}).`
                  : "."}{" "}
                Seus filtros, seleção territorial e consulta continuam preservados.
              </p>
              <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
                {onRetry && (
                  <button
                    type="button"
                    data-testid="btn-tentar-novamente-ficha"
                    onClick={onRetry}
                    className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
                  >
                    Tentar novamente
                  </button>
                )}
                <button
                  type="button"
                  data-testid="btn-fechar-ficha-erro"
                  onClick={onClose}
                  className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-white border border-slate-300 text-slate-800 hover:bg-slate-100 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
                >
                  Voltar à consulta
                </button>
              </div>
            </div>
          ) : obra ? (
            <>
              {obra.semaforo && (
                <section
                  data-testid="ficha-limpa-motivos-risco"
                  aria-label="Motivos da classificação do Semáforo da Obra"
                  className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-2"
                >
                  <h3 className="text-sm font-bold text-slate-900">Por que esta classificação?</h3>
                  {obra.semaforo.motivos.length > 0 ? (
                    <ul className="list-disc pl-5 text-xs text-slate-700 space-y-1">
                      {obra.semaforo.motivos.map((motivo, index) => (
                        <li key={`${motivo}-${index}`} className="break-words">{motivo}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-slate-700">A origem não detalha os motivos desta classificação.</p>
                  )}
                  <p className="text-xs text-slate-600">
                    O Semáforo resume critérios de risco e andamento; esta classificação, por si só, não comprova irregularidade.
                  </p>
                </section>
              )}

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
                      {percentualExecucaoFisicaFormatado}%
                    </span>
                  </div>
                </div>

                {/* Blocos de Estágios do Funil */}
                <div
                  data-testid="funil-estagios-grid"
                  className="grid grid-cols-1 md:grid-cols-5 gap-2 mb-4"
                >
                  {[
                    {
                      titulo: "1. Valor Original",
                      testId: "funil-valor-original",
                      valor: formatCurrency(obra.funilFinanceiro?.valorOriginal || 0),
                      valorClassName: "text-slate-800",
                      subtitulo: <span className="text-[10px] text-slate-500">Contrato inicial</span>,
                      destaque: false,
                      conector: true,
                    },
                    {
                      titulo: "2. Valor Contratual Vigente",
                      testId: "funil-valor-vigente",
                      valor: formatCurrency(obra.funilFinanceiro?.valorContratualVigente || 0),
                      valorClassName: "text-slate-900",
                      subtitulo:
                        obra.funilFinanceiro?.valorAditivos && obra.funilFinanceiro.valorAditivos > 0 ? (
                          <span className="text-[10px] font-bold text-amber-700">
                            +{obra.funilFinanceiro.deltaPercentualAditivos?.toFixed(1).replace(".", ",")}% aditivos
                          </span>
                        ) : (
                          <span className="text-[10px] text-emerald-600 font-medium">Sem acréscimo</span>
                        ),
                      destaque: false,
                      conector: true,
                    },
                    {
                      titulo: "3. Valor Empenhado",
                      testId: "funil-valor-empenhado",
                      valor: formatCurrency(obra.funilFinanceiro?.valorEmpenhado || 0),
                      valorClassName: "text-slate-800",
                      subtitulo: <span className="text-[10px] text-slate-500">Reserva orçamentária</span>,
                      destaque: false,
                      conector: true,
                    },
                    {
                      titulo: "4. Valor Liquidado",
                      testId: "funil-valor-liquidado",
                      valor: formatCurrency(obra.funilFinanceiro?.valorLiquidado || 0),
                      valorClassName: "text-slate-800",
                      subtitulo: <span className="text-[10px] text-slate-500">Medição atestada</span>,
                      destaque: false,
                      conector: true,
                    },
                    {
                      titulo: "5. Valor Pago",
                      testId: "funil-valor-pago",
                      valor: valorPago == null ? "Indisponível" : formatCurrency(valorPago),
                      valorClassName: "text-emerald-700",
                      subtitulo: <span className="text-[10px] text-slate-500">Repasse à empresa</span>,
                      destaque: true,
                      conector: false,
                    },
                  ].map((estagio) => (
                    <div
                      key={estagio.testId}
                      className={`relative p-3 rounded-lg border flex flex-col justify-between ${
                        estagio.destaque
                          ? "bg-emerald-50/70 border-emerald-300"
                          : "bg-white border-slate-200"
                      }`}
                    >
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                          {estagio.titulo}
                        </span>
                        <div
                          data-testid={estagio.testId}
                          className={`text-xs sm:text-sm font-bold tabular-nums mt-1 break-words ${estagio.valorClassName}`}
                        >
                          {estagio.valor}
                        </div>
                      </div>
                      <div className="mt-1">{estagio.subtitulo}</div>
                      {estagio.conector && (
                        <span
                          aria-hidden="true"
                          className="hidden md:inline-flex items-center justify-center absolute -right-1 translate-x-1/2 top-1/2 -translate-y-1/2 z-10 bg-slate-50 px-0.5 rounded text-[11px] font-semibold text-slate-400 leading-none pointer-events-none select-none"
                        >
                          →
                        </span>
                      )}
                    </div>
                  ))}
                </div>

                {obra.apuracaoPagamentos && (() => {
                  const dataConsolidacao =
                    obra.apuracaoPagamentos.pagamentosConsolidados === true
                      ? formatarDataCalendarioValida(obra.apuracaoPagamentos.dataReferencia)
                      : null;
                  return (
                    <div className="text-xs text-slate-600 space-y-2">
                      {dataConsolidacao ? (
                        <p>
                          Pagamentos consolidados em {dataConsolidacao} (vigência encerrada há mais de 12 meses)
                        </p>
                      ) : (
                        obra.apuracaoPagamentos.dataReferencia && (
                          <p>Referência dos pagamentos: {formatDate(obra.apuracaoPagamentos.dataReferencia)}</p>
                        )
                      )}
                      {obra.apuracaoPagamentos.periodoDisponivel && <p>Período disponível: {formatDate(obra.apuracaoPagamentos.periodoDisponivel.inicio)} a {formatDate(obra.apuracaoPagamentos.periodoDisponivel.fim)}</p>}
                      {!!obra.apuracaoPagamentos.limitacoesConhecidas?.length && !obra.apuracaoPagamentos.periodoDisponivel && <p>Período disponível não informado.</p>}
                      {!!obra.apuracaoPagamentos.limitacoesConhecidas?.length && <div>
                        <strong>Soma Parcial de Pagamentos</strong>
                        {obra.apuracaoPagamentos.limitacoesConhecidas.map((limite) => <p key={limite}>{limite}</p>)}
                      </div>}
                      {obra.apuracaoPagamentos.situacao === "sem_registros" && <p>Nenhum registro de pagamento encontrado na fonte.</p>}
                      {obra.apuracaoPagamentos.situacao === "saldo_registrado" && valorPago === 0 && <p>Saldo registrado igual a zero.</p>}
                      {obra.apuracaoPagamentos.registrosSemValor > 0 && <p>
                        {obra.apuracaoPagamentos.registrosSemValor} registro{obra.apuracaoPagamentos.registrosSemValor !== 1 ? "s" : ""} sem valor informado. Esses registros permanecem disponíveis e não tornam a soma parcial por si só.
                      </p>}
                      {!!obra.pagamentos?.length && <p>Valores informados são somados mesmo quando faltam campos de identificação; registros semelhantes são preservados.</p>}
                      {!!obra.pagamentos?.length && <details>
                        <summary className="cursor-pointer font-medium">Registros de pagamentos ({obra.pagamentos.length})</summary>
                        <ul className="space-y-2 mt-2">
                          {obra.pagamentos.map((pagamento, index) => <li key={index} className="border border-slate-200 rounded p-2 break-words">
                            {Object.entries(pagamento).map(([campo, valor]) => <div key={campo}>{campo}: {valor == null || valor === "" ? "Não informado" : typeof valor === "object" ? JSON.stringify(valor) : String(valor)}</div>)}
                            {(pagamento.pago == null || pagamento.pago === "") && (pagamento.valorPago == null || pagamento.valorPago === "") && <div>Valor não informado</div>}
                          </li>)}
                        </ul>
                      </details>}
                    </div>
                  );
                })()}

                {/* Barra Comparativa: Avanço Financeiro vs Avanço Físico */}
                <div className="space-y-2 pt-2 border-t border-slate-200 text-xs">
                  <div>
                    <div className="flex justify-between text-slate-600 mb-1">
                      <span>Execução Financeira (Pago / Vigente):</span>
                      <strong data-testid="funil-percentual-pago-vigente" className="text-slate-800">
                        {percentualPagoSobreVigente == null ? "Indisponível" : `${percentualPagoSobreVigente.toFixed(1).replace(".", ",")}%`}
                      </strong>
                    </div>
                    {percentualPagoSobreVigente != null && <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                      <div
                        role="progressbar"
                        aria-label="Execução financeira, valor pago sobre valor vigente"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={Math.max(0, Math.min(100, percentualPagoSobreVigente))}
                        aria-valuetext={`${percentualPagoSobreVigente.toFixed(1).replace(".", ",")}% do valor vigente pago`}
                        className="bg-indigo-600 h-2 rounded-full"
                        style={{
                          width: `${Math.max(0, Math.min(100, percentualPagoSobreVigente))}%`,
                        }}
                      ></div>
                    </div>}
                  </div>

                  <div>
                    <div className="flex justify-between text-slate-600 mb-1">
                      <span>Execução Física Medida (percentualExecutado):</span>
                      <strong className="text-emerald-700">
                        {percentualExecucaoFisicaFormatado}%
                      </strong>
                    </div>
                    <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                      <div
                        role="progressbar"
                        aria-label="Execução física informada pela fonte"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={Math.max(0, Math.min(100, percentualExecucaoFisica))}
                        aria-valuetext={`${percentualExecucaoFisicaFormatado}% informado pela fonte${percentualExecucaoFisica > 100 ? "; barra visual limitada a 100%" : ""}`}
                        className="bg-emerald-500 h-2 rounded-full"
                        style={{
                          width: `${Math.max(0, Math.min(100, percentualExecucaoFisica))}%`,
                        }}
                      ></div>
                    </div>
                    {percentualExecucaoFisica > 100 && (
                      <p data-testid="ficha-execucao-fisica-acima-100" className="text-[11px] text-amber-800">
                        Valor de origem mantido em {percentualExecucaoFisicaFormatado}%. A barra visual é limitada a 100% por escala e não representa pagamentos.
                      </p>
                    )}
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

              {/* 6. Fontes Oficiais & Lastro Territorial */}
              {(() => {
                const fontesOficiais = obra.fontesOficiais;
                const portalUrl = fontesOficiais?.portalTransparencia?.url || PORTAL_TRANSPARENCIA_URL;
                const cdUg =
                  fontesOficiais?.chaveCanonica?.cdUnidadeGestora ??
                  (obra.cdUnidadeGestora != null ? String(obra.cdUnidadeGestora) : null);
                const nuContratoSigef = fontesOficiais?.chaveCanonica?.nuContratoSigef || obra.numeroContrato;
                const nuProcesso = fontesOficiais?.nuProcesso ?? obra.nuProcesso ?? null;
                const domContratoNu =
                  fontesOficiais?.domContrato?.nuDom ?? (isDomValido(obra.dom?.nuDom) ? obra.dom?.nuDom : null);
                const domContratoUrl =
                  fontesOficiais?.domContrato?.url || (domContratoNu ? PORTAL_DOM_URL : null);
                const domAditivos =
                  fontesOficiais?.domAditivos ??
                  (obra.aditivos || [])
                    .filter((ad) => isDomValido(ad.nuDom))
                    .map((ad) => ({
                      nuAditivo: ad.nuAditivo,
                      nuDom: ad.nuDom as string,
                      dtPublicacao: ad.dtPublicacao,
                      url: PORTAL_DOM_URL,
                    }));
                const origemLastro =
                  fontesOficiais?.lastroTerritorial?.origem ||
                  (obra.estagioAlocacao
                    ? `Alocação territorial via ${obra.estagioAlocacao}`
                    : obra.nivel || "Origem territorial não informada");
                const lastroDocOrigem = fontesOficiais?.lastroTerritorial?.documentoOrigem || null;
                const lastroTrecho = fontesOficiais?.lastroTerritorial?.trechoComprobatorio || null;
                const lastroJustificativa = fontesOficiais?.lastroTerritorial?.justificativa || null;
                const baseVigente = obra.funilFinanceiro?.valorContratualVigente || 0;
                const basePago = obra.funilFinanceiro?.valorPago;
                const frentesMedicao = obra.frentesMedicao || [];

                const renderBotaoCopiar = (valor: string, campo: "contrato" | "processo", label: string, testId: string) => (
                  <button
                    type="button"
                    data-testid={testId}
                    onClick={() => handleCopiar(valor, campo)}
                    className="px-2 py-1 text-[11px] font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded border border-slate-300 transition-colors shrink-0"
                  >
                    {copiadoCampo === campo ? "Copiado!" : label}
                  </button>
                );

                return (
                  <div
                    data-testid="secao-fontes-oficiais"
                    className="bg-slate-50 rounded-xl border border-slate-200 p-4 space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <h4 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                        <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                        Fontes Oficiais &amp; Lastro Territorial
                      </h4>

                      <a
                        data-testid="link-portal-transparencia"
                        href={portalUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-700 hover:text-indigo-900 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 px-3 py-1.5 rounded-lg transition-colors"
                      >
                        Consultar no Portal da Transparência de Salvador
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                      </a>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      <div className="bg-white p-3 rounded-lg border border-slate-200">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                          Chave Canônica da Obra
                        </span>
                        <div className="flex items-center justify-between gap-2">
                          <div data-testid="fontes-chave-canonica" className="font-mono text-slate-800">
                            <span>UG {cdUg || "—"}</span>
                            <span className="mx-1.5 text-slate-400">•</span>
                            <strong>{nuContratoSigef || "—"}</strong>
                          </div>
                          {nuContratoSigef &&
                            renderBotaoCopiar(nuContratoSigef, "contrato", "Copiar contrato", "btn-copiar-contrato")}
                        </div>
                      </div>

                      <div className="bg-white p-3 rounded-lg border border-slate-200">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                          Processo Administrativo
                        </span>
                        <div className="flex items-center justify-between gap-2">
                          <span data-testid="fontes-nu-processo" className="font-mono text-slate-800 font-semibold">
                            {nuProcesso || "Não informado"}
                          </span>
                          {nuProcesso &&
                            renderBotaoCopiar(nuProcesso, "processo", "Copiar processo", "btn-copiar-processo")}
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      <div className="bg-white p-3 rounded-lg border border-slate-200">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                          Publicações no Diário Oficial (DOM)
                        </span>
                        <div className="space-y-1">
                          <div className="flex items-center gap-1.5">
                            <span className="text-slate-500">Contrato:</span>
                            {domContratoNu && domContratoUrl ? (
                              <a
                                data-testid="link-dom-contrato"
                                href={domContratoUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-semibold text-indigo-700 hover:underline"
                              >
                                Edição nº {domContratoNu}
                              </a>
                            ) : (
                              <span className="text-slate-500">Não informado</span>
                            )}
                          </div>
                          {domAditivos.length > 0 && (
                            <div className="flex flex-wrap items-center gap-1.5">
                              <span className="text-slate-500">Aditivos:</span>
                              {domAditivos.map((ad, idx) => (
                                <a
                                  key={`${ad.nuDom}-${idx}`}
                                  data-testid={`link-dom-aditivo-${idx}`}
                                  href={ad.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="font-semibold text-indigo-700 hover:underline bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-200"
                                >
                                  {ad.nuAditivo ? `${ad.nuAditivo}: ` : ""}Ed. {ad.nuDom}
                                </a>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-1.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                          Lastro Territorial
                        </span>
                        <p data-testid="fontes-lastro-territorial" className="text-slate-700 font-medium">
                          {origemLastro}
                        </p>
                        {lastroDocOrigem && (
                          <p data-testid="fontes-lastro-documento" className="text-[11px] text-slate-600">
                            <span className="font-semibold text-slate-700">Documento:</span> {lastroDocOrigem}
                          </p>
                        )}
                        {lastroTrecho && (
                          <blockquote
                            data-testid="fontes-lastro-trecho"
                            className="text-[11px] text-slate-700 bg-slate-50 border-l-2 border-indigo-400 pl-2 py-1 italic"
                          >
                            “{lastroTrecho}”
                          </blockquote>
                        )}
                        {lastroJustificativa && (
                          <p data-testid="fontes-lastro-justificativa" className="text-[11px] text-slate-500">
                            {lastroJustificativa}
                          </p>
                        )}
                      </div>
                    </div>

                    {cotasListaFechada.length > 0 && (
                      <div
                        data-testid="fontes-cotas-lista-fechada"
                        className="bg-white p-3 rounded-lg border border-amber-200 space-y-2 text-xs"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800">
                            Cota-Parte Territorial (Lista Fechada Contratual)
                          </span>
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-900 border border-amber-200">
                            {cotasListaFechada.length} {cotasListaFechada.length === 1 ? "bairro" : "bairros"} · {totalCotasUnidades} un.
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-600">
                          Total integral do contrato:{" "}
                          <strong className="text-slate-800">{formatCurrency(baseVigente)}</strong>{" "}
                          vigente ·{" "}
                          <strong className="text-emerald-700">{basePago == null ? "Indisponível" : formatCurrency(basePago)}</strong>{" "}
                          pago
                        </p>

                        <div className="space-y-2">
                          {cotasListaFechada.map((cota, idx) => {
                            const territorioLabel = cota.prefeituraBairro
                              ? `${cota.bairro} (${cota.prefeituraBairro})`
                              : cota.bairro;

                            return (
                              <div
                                key={`${cota.bairro}-${idx}`}
                                data-testid={`fontes-cota-item-${idx}`}
                                className="bg-amber-50/40 border border-amber-200/80 rounded-lg p-2.5 space-y-1"
                              >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <span className="font-semibold text-slate-800">
                                    {territorioLabel}
                                  </span>
                                  <span
                                    data-testid={`fontes-cota-badge-${idx}`}
                                    className="font-semibold text-[11px] text-amber-900 bg-amber-100 px-2 py-0.5 rounded border border-amber-300"
                                  >
                                    Cota-Parte ({cota.fracao})
                                  </span>
                                </div>
                                <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-600">
                                  <span>
                                    Unidades:{" "}
                                    <strong className="text-slate-800">
                                      {cota.unidades}/{cota.totalUnidades}
                                    </strong>
                                  </span>
                                  <span>
                                    Valor Vigente ({(cota.peso * 100).toFixed(1).replace(".", ",")}%):{" "}
                                    <strong className="text-slate-800">
                                      {formatCurrency(baseVigente * cota.peso)}
                                    </strong>
                                  </span>
                                  <span>
                                    Pago:{" "}
                                    <strong className="text-emerald-700">
                                      {basePago == null ? "Indisponível" : formatCurrency(basePago * cota.peso)}
                                    </strong>
                                  </span>
                                </div>
                                {cota.descricaoUnidades && (
                                  <p className="text-[11px] text-slate-600">
                                    {cota.descricaoUnidades}
                                  </p>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {frentesMedicao.length > 0 && (
                      <div
                        data-testid="fontes-frentes-medicao"
                        className="bg-white p-3 rounded-lg border border-indigo-200 space-y-2 text-xs"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700">
                            Frentes de Medição por Território
                          </span>
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-800 border border-indigo-200">
                            {frentesMedicao.length} {frentesMedicao.length === 1 ? "frente" : "frentes"}
                          </span>
                        </div>

                        <div className="space-y-2">
                          {frentesMedicao.map((frente, idx) => {
                            const territorioDestino =
                              frente.bairro && frente.prefeituraBairro
                                ? `${frente.bairro} (${frente.prefeituraBairro})`
                                : frente.bairro || frente.prefeituraBairro || frente.nivel;

                            return (
                              <div
                                key={`${frente.notaLiquidacao}-${idx}`}
                                data-testid={`fontes-frente-item-${idx}`}
                                className="bg-slate-50 border border-slate-200 rounded-lg p-2.5 space-y-1"
                              >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <span className="font-semibold text-slate-800">
                                    {territorioDestino}
                                  </span>
                                  <span className="font-mono text-[11px] font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                                    {frente.notaLiquidacao}
                                  </span>
                                </div>
                                <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-600">
                                  <span>
                                    Liquidado: <strong className="text-slate-800">{formatCurrency(frente.valorLiquidado)}</strong>
                                  </span>
                                  <span>
                                    Pago: <strong className="text-emerald-700">{frente.valorPago == null ? "Indisponível" : formatCurrency(frente.valorPago)}</strong>
                                  </span>
                                </div>
                                {frente.trechoComprobatorio && (
                                  <blockquote className="text-[11px] text-slate-600 border-l-2 border-indigo-300 pl-2 italic">
                                    “{frente.trechoComprobatorio}”
                                  </blockquote>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}
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

import React from "react";
import { TerritorySelection } from "../types";
import { formatDecimal, formatNumber } from "../utils/formatters";

interface TerritorySidebarProps {
  /**
   * Território selecionado no mapa (Bairro Oficial ou Prefeitura-Bairro) ou null se nenhum.
   */
  territorio: TerritorySelection | null;
  /**
   * Callback para limpar a seleção e fechar o painel.
   */
  onClear: () => void;
}

/**
 * Painel lateral "Raio-X do Bairro / Prefeitura-Bairro".
 *
 * @summary Apresenta o perfil demográfico e social detalhado da área selecionada no mapa.
 * @description Exibe o nome do território, seu vínculo regional com a Prefeitura-Bairro,
 * a contagem de população residente oficial do Censo 2022 do IBGE, o Índice de Vulnerabilidade
 * do Bairro e a indicação especial quando o bairro é uma Zona Especial Não-Residencial
 * (Aeroporto, Porto Seco Pirajá e CAB), explicando o motivo de ser excluído do ranking per capita.
 *
 * @param props - Propriedades contendo o território ativo e função de fechamento.
 * @returns Elemento JSX do painel lateral.
 * @throws Não lança exceções.
 */
export const TerritorySidebar: React.FC<TerritorySidebarProps> = ({ territorio, onClear }) => {
  if (!territorio) {
    return (
      <aside className="w-full md:w-96 bg-white border-l border-slate-200 p-6 flex flex-col justify-center items-center text-center shadow-sm">
        <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mb-4">
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <h3 className="text-base font-semibold text-slate-700">Nenhum território selecionado</h3>
        <p className="text-sm text-slate-500 mt-2 max-w-xs">
          Clique em qualquer Bairro Oficial ou Prefeitura-Bairro no mapa ou na lista ao lado para inspecionar os indicadores demográficos e de vulnerabilidade social.
        </p>
      </aside>
    );
  }

  const ehZonaEspecial = !!(territorio.is_zona_especial_nao_residencial || territorio.isZonaEspecialNaoResidencial);
  const ehBairro = territorio.tipo === "bairro";

  return (
    <aside className="w-full md:w-96 bg-white border-l border-slate-200 p-6 flex flex-col shadow-lg overflow-y-auto">
      {/* Cabeçalho do Raio-X */}
      <div className="flex items-start justify-between pb-4 border-b border-slate-100">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
            {ehBairro ? "Bairro Oficial" : "Prefeitura-Bairro"}
          </span>
          <h2
            data-testid="raio-x-nome"
            className="text-xl font-bold text-slate-900 mt-1 tracking-tight"
          >
            {territorio.nome}
          </h2>
          {territorio.prefeitura_bairro && (
            <p className="text-xs text-slate-500 mt-0.5">
              Prefeitura-Bairro: <span className="font-medium text-slate-700">{territorio.prefeitura_bairro}</span>
            </p>
          )}
        </div>
        <button
          onClick={onClear}
          aria-label="Fechar painel lateral"
          className="text-slate-400 hover:text-slate-600 p-1 rounded-md hover:bg-slate-100 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Alerta de Zona Especial Não-Residencial */}
      {ehZonaEspecial && (
        <div
          data-testid="badge-zona-especial"
          className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-xs"
        >
          <div className="font-semibold flex items-center gap-1.5 text-amber-900">
            <svg className="w-4 h-4 text-amber-600 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            Zona Especial Não-Residencial
          </div>
          <p className="mt-1 leading-relaxed text-amber-700">
            Área de ocupação institucional, aeroportuária ou logística com população residencial nula ou residual. Excluída dos rankings de Investimento por Habitante para evitar distorções estatísticas per capita.
          </p>
        </div>
      )}

      {/* Métricas Demográficas */}
      <div className="mt-5 space-y-4">
        {/* População Residente */}
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
            População Residente (Censo 2022)
          </span>
          <div className="mt-1 flex items-baseline gap-2">
            <span
              data-testid="raio-x-populacao"
              className="text-2xl font-bold text-slate-900"
            >
              {formatNumber(territorio.populacao)}
            </span>
            <span className="text-xs text-slate-500">habitantes</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Fonte: IBGE, Agregados por Setores Censitários e Bairros
          </p>
        </div>

        {/* Índice de Vulnerabilidade do Bairro */}
        {ehBairro && territorio.indice_vulnerabilidade !== undefined && (
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                Índice de Vulnerabilidade
              </span>
              <span
                data-testid="raio-x-vulnerabilidade"
                className="text-sm font-bold text-slate-900"
              >
                {formatDecimal(territorio.indice_vulnerabilidade)}
              </span>
            </div>
            {/* Barra Visual de Intensidade */}
            <div className="w-full bg-slate-200 h-2.5 rounded-full mt-2 overflow-hidden">
              <div
                className="bg-indigo-600 h-2.5 rounded-full transition-all duration-300"
                style={{
                  width: `${Math.min(100, Math.max(5, (territorio.indice_vulnerabilidade || 0) * 100))}%`,
                }}
              ></div>
            </div>
            <p className="text-xs text-slate-400 mt-2">
              Escala de 0,00 (menor carência) a 1,00 (maior carência socioeconômica e infraestrutura).
            </p>
          </div>
        )}
      </div>

      <div className="mt-auto pt-6 border-t border-slate-100">
        <button
          onClick={onClear}
          className="w-full py-2 px-4 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition-colors"
        >
          Limpar Seleção do Mapa
        </button>
      </div>
    </aside>
  );
};

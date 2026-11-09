import React, { useEffect } from "react";

export interface NotaMetodologicaModalProps {
  /**
   * Indicador se o modal metodológico está aberto.
   */
  isOpen: boolean;
  /**
   * Callback invocado para fechar o modal.
   */
  onClose: () => void;
}

/**
 * Modal explicativo da metodologia de cálculo do Índice de Vulnerabilidade do Bairro.
 *
 * @summary Apresenta a fundamentação técnica (IDS/IPP e IVS/IPEA), fontes do Censo 2022 (IBGE/SIDRA),
 * fórmulas matemáticas passo a passo (min-max e pesos iguais) e regras de exceção territorial.
 *
 * @param props - Propriedades de visibilidade e fechamento do modal.
 * @returns Elemento JSX do modal acessível ou nulo quando fechado.
 */
export const NotaMetodologicaModal: React.FC<NotaMetodologicaModalProps> = ({
  isOpen,
  onClose,
}) => {
  // Fecha modal com a tecla ESC
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-nota-metodologica-titulo"
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4 md:p-6 animate-fadeIn"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        data-testid="modal-nota-metodologica"
        className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden text-slate-800"
      >
        {/* Cabeçalho do Modal */}
        <div className="bg-slate-900 text-white px-5 py-4 flex items-start justify-between gap-4 border-b border-slate-800 shrink-0">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              <span className="bg-indigo-900/80 text-indigo-300 font-bold text-[11px] px-2.5 py-0.5 rounded-full border border-indigo-500/30">
                Metodologia Multidimensional
              </span>
              <span className="text-slate-400 text-xs">
                Censo Demográfico 2022 (IBGE) • Nível N102
              </span>
            </div>
            <h2
              id="modal-nota-metodologica-titulo"
              data-testid="modal-nota-metodologica-titulo"
              className="text-lg sm:text-xl font-bold text-white tracking-tight"
            >
              Nota Metodológica — Índice de Vulnerabilidade
            </h2>
            <p className="text-xs text-slate-300 mt-0.5">
              Como é calculado o Índice de Vulnerabilidade do Bairro e da Prefeitura-Bairro
            </p>
          </div>

          <button
            type="button"
            data-testid="btn-fechar-nota-metodologica"
            onClick={onClose}
            aria-label="Fechar nota metodológica"
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Corpo com Rolagem e Conteúdo Metodológico */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-6 text-sm text-slate-700 leading-relaxed">
          {/* Seção 1: Referência Conceitual e Científica */}
          <section className="bg-indigo-50/60 border border-indigo-100 rounded-xl p-4 sm:p-5">
            <div className="flex items-center gap-2 text-indigo-950 font-bold text-base mb-2">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-indigo-600 text-white text-xs font-bold shrink-0">
                1
              </span>
              <h3>Referência Técnica e Científica: IDS (IPP) e IVS (IPEA)</h3>
            </div>
            <p className="text-xs sm:text-sm text-indigo-950/90 leading-relaxed">
              O <strong>Índice de Vulnerabilidade do Bairro</strong> adota a metodologia científica do{" "}
              <strong>Índice de Desenvolvimento Social (IDS)</strong>, concebido por <strong>Cavallieri & Lopes</strong> no{" "}
              <strong>Instituto Pereira Passos (IPP)</strong>, combinada com as dimensões de <em>Infraestrutura Urbana</em> e{" "}
              <em>Capital Humano</em> do <strong>Índice de Vulnerabilidade Social (IVS)</strong> desenvolvido pelo{" "}
              <strong>IPEA</strong> (Instituto de Pesquisa Econômica Aplicada). O objetivo é mensurar, em escala relativa de{" "}
              <code>0,00</code> (menor carência) a <code>1,00</code> (maior carência), as privações estruturais de saneamento básico e
              escolaridade do território para confrontá-las com a destinação per capita de recursos municipais em obras públicas.
            </p>
          </section>

          {/* Seção 2: As 3 Variáveis do Universo do Censo 2022 (IBGE/SIDRA) */}
          <section className="space-y-3">
            <div className="flex items-center gap-2 text-slate-900 font-bold text-base">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-slate-900 text-white text-xs font-bold shrink-0">
                2
              </span>
              <h3>As 3 Variáveis do Universo do Censo 2022 (IBGE/SIDRA nível N102)</h3>
            </div>
            <p className="text-xs sm:text-sm text-slate-600">
              O cálculo utiliza dados do Universo do Censo Demográfico 2022 do IBGE (100% dos domicílios e moradores recenseados, sem
              erros amostrais) extraídos via API SIDRA no nível territorial <code>N102</code> (Bairros de Salvador — código{" "}
              <code>2927408</code>):
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
              {/* Dimensão 1: Esgoto */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded-full">
                      Tabela 6805
                    </span>
                    <span className="text-[10px] text-slate-400 font-medium">PLANSAB</span>
                  </div>
                  <h4 className="font-bold text-slate-900 text-xs sm:text-sm mb-1">
                    Déficit de Esgotamento Sanitário
                  </h4>
                  <p className="text-[11px] text-slate-600 leading-relaxed">
                    Percentual de domicílios particulares permanentes ocupados sem acesso à rede geral/pluvial ou fossa séptica/filtro,
                    segundo o critério de adequação do <strong>PLANSAB</strong> (Plano Nacional de Saneamento Básico).
                  </p>
                </div>
                <div className="mt-3 pt-2 border-t border-slate-200 text-[11px] font-mono text-slate-700">
                  pct_esgoto_inadequado
                </div>
              </div>

              {/* Dimensão 2: Água */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded-full">
                      Tabela 6803
                    </span>
                    <span className="text-[10px] text-slate-400 font-medium">Rede Geral</span>
                  </div>
                  <h4 className="font-bold text-slate-900 text-xs sm:text-sm mb-1">
                    Déficit de Abastecimento de Água
                  </h4>
                  <p className="text-[11px] text-slate-600 leading-relaxed">
                    Percentual de domicílios particulares permanentes ocupados sem ligação à rede geral de distribuição de água tratada.
                  </p>
                </div>
                <div className="mt-3 pt-2 border-t border-slate-200 text-[11px] font-mono text-slate-700">
                  pct_agua_inadequada
                </div>
              </div>

              {/* Dimensão 3: Analfabetismo */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded-full">
                      Tabela 9543
                    </span>
                    <span className="text-[10px] text-slate-400 font-medium">15 anos ou mais</span>
                  </div>
                  <h4 className="font-bold text-slate-900 text-xs sm:text-sm mb-1">
                    Taxa de Analfabetismo
                  </h4>
                  <p className="text-[11px] text-slate-600 leading-relaxed">
                    Percentual de pessoas residentes de 15 anos ou mais que não sabem ler e escrever um bilhete simples (complemento de 100% da alfabetização).
                  </p>
                </div>
                <div className="mt-3 pt-2 border-t border-slate-200 text-[11px] font-mono text-slate-700">
                  pct_analfabetismo_15mais
                </div>
              </div>
            </div>
          </section>

          {/* Seção 3: Normalização Min-Max e Composição do Índice */}
          <section className="space-y-3">
            <div className="flex items-center gap-2 text-slate-900 font-bold text-base">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-slate-900 text-white text-xs font-bold shrink-0">
                3
              </span>
              <h3>Normalização Min-Max e Média Composta (1/3 cada)</h3>
            </div>
            <p className="text-xs sm:text-sm text-slate-600">
              Para compatibilizar grandezas com diferentes dispersões estatísticas sem que uma dimensão domine artificialmente o índice,
              cada sub-indicador é normalizado na escala <code>0</code> a <code>1</code> pelo método <strong>min-max</strong> sobre o universo
              dos <strong>168 Bairros Oficiais</strong> residenciais:
            </p>

            <div className="bg-slate-900 text-emerald-300 font-mono text-xs sm:text-sm p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="text-slate-400 text-[11px]">
                {/* Fórmula de normalização min-max */}
                # 1. Normalização de cada indicador k nos 168 bairros residenciais:
              </div>
              <div className="font-bold">
                I_k,b = (x_k,b - min(x_k)) / (max(x_k) - min(x_k))
              </div>
              <div className="text-slate-400 text-[11px] pt-1">
                {/* Média aritmética simples de pesos iguais */}
                # 2. Composição por média aritmética simples com pesos iguais (1/3 cada):
              </div>
              <div className="font-bold">
                IVB_b = round((I_esgoto,b + I_agua,b + I_analf,b) / 3, 2)
              </div>
            </div>

            <p className="text-xs text-slate-500">
              O resultado é arredondado em 2 casas decimais e reflete fielmente a hierarquia socioeconômica observada pelo Censo 2022
              em Salvador (por exemplo, Pituba com <code>0,13</code> &lt; Cabula com <code>0,55</code> &lt; Liberdade com <code>0,78</code>).
            </p>
          </section>

          {/* Seção 4: Consolidação Regional das Prefeituras-Bairro */}
          <section className="space-y-2">
            <div className="flex items-center gap-2 text-slate-900 font-bold text-base">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-slate-900 text-white text-xs font-bold shrink-0">
                4
              </span>
              <h3>Consolidação das Prefeituras-Bairro por Média Ponderada Populacional</h3>
            </div>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              Para cada uma das 10 <strong>Prefeituras-Bairro</strong> (macrorregiões administrativas de Salvador), tanto o{" "}
              <code>indice_vulnerabilidade</code> regional quanto os seus 3 sub-indicadores percentuais são consolidados pela{" "}
              <strong>média ponderada populacional</strong> dos seus Bairros Oficiais residenciais constituintes (com pesos dados pela população
              residente apurada no Censo 2022):
            </p>

            <div className="bg-slate-100 font-mono text-xs text-slate-800 p-3 rounded-lg border border-slate-200">
              IVB_PrefeituraBairro = Σ(IVB_bairro × Pop_bairro) / Σ(Pop_bairro)
            </div>
            <p className="text-xs text-slate-500">
              Essa regra impede distorções em que bairros pequenos mas com indicadores atípicos dominem o índice consolidado da macrorregião inteira.
            </p>
          </section>

          {/* Seção 5: Exceções Territoriais (Zonas Especiais e Imputação por Contiguidade) */}
          <section className="space-y-3">
            <div className="flex items-center gap-2 text-slate-900 font-bold text-base">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-slate-900 text-white text-xs font-bold shrink-0">
                5
              </span>
              <h3>Regras de Exceção Territorial e Imputação Espacial</h3>
            </div>

            <div className="space-y-3 text-xs sm:text-sm">
              <div className="p-3.5 bg-amber-50/70 border border-amber-200 rounded-xl">
                <h4 className="font-bold text-amber-950 mb-1 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                  Zonas Especiais Não-Residenciais (Isenção Estatística)
                </h4>
                <p className="text-amber-900 leading-relaxed text-xs">
                  Os bairros <strong>Aeroporto</strong>, <strong>Porto Seco Pirajá</strong> e{" "}
                  <strong>Centro Administrativo da Bahia - CAB</strong> possuem ocupação predominantemente aeroportuária, logística e
                  institucional governamental, com população residente nula ou residual no Censo 2022. Por essa razão, são{" "}
                  <strong>isentos</strong> da normalização min-max e do cálculo de vulnerabilidade (exibindo o status <code>Isento</code> no
                  painel e no ranking), preservando a escala real dos bairros onde a população de Salvador efetivamente reside.
                </p>
              </div>

              <div className="p-3.5 bg-blue-50/70 border border-blue-200 rounded-xl">
                <h4 className="font-bold text-blue-950 mb-1 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                  Imputação Espacial por Contiguidade Territorial
                </h4>
                <p className="text-blue-900 leading-relaxed text-xs">
                  Três Bairros Oficiais residenciais delimitados pelo Decreto Municipal nº 32.791/2020 não possuem linha individual própria
                  na malha censitária <code>N102</code> do SIDRA/IBGE. Para evitar suposições arbitrárias, seus sub-indicadores foram
                  imputados pela <strong>média ponderada populacional dos bairros limítrofes contíguos da mesma zona homogênea</strong> no
                  Censo 2022 (e marcados com o selo transparente de estimativa por contiguidade no painel Raio-X):
                </p>
                <ul className="list-disc list-inside mt-2 text-xs text-blue-950 space-y-1">
                  <li>
                    <strong>Chame-Chame:</strong> imputado a partir dos bairros vizinhos contíguos <em>Graça</em>, <em>Barra</em> e{" "}
                    <em>Vitória</em> (Prefeitura-Bairro Barra/Pituba).
                  </li>
                  <li>
                    <strong>Colinas de Pituaçu:</strong> imputado a partir dos vizinhos contíguos <em>São Marcos</em> e{" "}
                    <em>Pau da Lima</em> (Prefeitura-Bairro Pau da Lima).
                  </li>
                  <li>
                    <strong>Ilha de Maré:</strong> imputado a partir das ilhas vizinhas do Censo <em>Ilha de Bom Jesus dos Passos</em> e{" "}
                    <em>Ilha dos Frades/Ilha de Santo Antônio</em> (Prefeitura-Bairro Subúrbio/Ilhas).
                  </li>
                </ul>
              </div>
            </div>
          </section>
        </div>

        {/* Rodapé do Modal com Botão de Concluir */}
        <div className="bg-slate-50 px-5 py-3.5 border-t border-slate-200 flex items-center justify-between shrink-0">
          <span className="text-xs text-slate-500">
            Auditabilidade cidadã garantida conforme <strong>ADR-0003</strong>.
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-slate-900"
          >
            Fechar Nota Metodológica
          </button>
        </div>
      </div>
    </div>
  );
};


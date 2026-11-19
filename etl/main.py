"""Interface de linha de comando para execução do pipeline ETL de Salvador.

Permite disparar a extração e geração de artefatos estáticos via terminal.
"""

import argparse
from pathlib import Path
import sys

from etl.runner import run_pipeline


def main() -> None:
    """Executa o pipeline ETL via linha de comando.

    Sumário:
        Ponto de entrada de linha de comando com parsing de argumentos.

    Descrição Estendida:
        Analisa os argumentos passados pelo terminal (`--output-dir` e `--year`),
        invoca o orquestrador `run_pipeline` e exibe no console o resumo dos arquivos
        gerados e totalizadores de entidades territoriais processadas.

    Argumentos:
        Nenhum (lê sys.argv).

    Retornos:
        None.

    Erros:
        Encerra o processo com código de saída 1 em caso de exceção durante a execução.
    """
    parser = argparse.ArgumentParser(description="Pipeline ETL de Obras e Território de Salvador")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="public/data",
        help="Diretório de saída para os artefatos estáticos (padrão: public/data)",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2025,
        help="Ano de referência das obras públicas (padrão: 2025)",
    )
    parser.add_argument(
        "--cache-file",
        type=str,
        default=None,
        help="Caminho opcional do arquivo de Cache Incremental (padrão: <output-dir>/geocoding_cache.json)",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        default=False,
        help="Força reconsulta completa de todos os mandatos e atualização de todas as fichas de obras (padrão: False)",
    )
    parser.add_argument("--recuperar", action="store_true", help="Retoma a tentativa pendente na janela diária de recuperação")
    parser.add_argument("--aguardar-publicacao", action="store_true", help="Mantém a tentativa pendente até a publicação externa")
    parser.add_argument("--marcador-sucesso", help="Arquivo criado somente após uma atualização concluída")
    parser.add_argument("--repositorio-progresso", help="Repositório Git cujo origin armazena o progresso em ref separado")
    args = parser.parse_args()

    cache_path = Path(args.cache_file) if args.cache_file else None
    print(f"Iniciando pipeline ETL para o ano {args.year} em '{args.output_dir}' (full_refresh={args.full_refresh})...")
    try:
        resultado = run_pipeline(
            output_dir=Path(args.output_dir),
            year=args.year,
            cache_file=cache_path,
            full_refresh=args.full_refresh,
            modo_recuperacao=args.recuperar,
            aguardar_publicacao=args.aguardar_publicacao,
            repositorio_progresso=Path(args.repositorio_progresso) if args.repositorio_progresso else None,
        )
        if args.marcador_sucesso and resultado.get("success"):
            Path(args.marcador_sucesso).write_text(resultado["tentativa"], encoding="utf-8")
        print(f"ETL concluído com sucesso: {resultado}")
    except Exception as exc:
        print(f"Erro ao executar ETL: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

# Arquitetura Estática Particionada no GitHub Pages com ETL Incremental em Python

O painel será hospedado no GitHub Pages como uma aplicação web 100% estática, alimentada por arquivos JSON e GeoJSON pré-processados por um pipeline ETL em Python (executado manualmente em ambiente local no início e posteriormente via GitHub Actions agendado), em vez de um backend com banco de dados consultado em tempo real.

## Contexto e Motivação

Os dados de obras públicas da Prefeitura de Salvador (`apitmptransparencia.salvador.ba.gov.br`), a malha do GeoSalvador e o Censo 2022 do IBGE possuem frequência de atualização baixa (diária ou estática), mas exigem processamento pesado de geocodificação e cruzamento espacial. Um backend tradicional exigiria custos de hospedagem contínua e exporia o usuário final à latência e eventuais instabilidades das APIs governamentais.

## Consequências

- **Cache Incremental no Repositório (`data/cache/geocoding_cache.json`):** O ETL salva o resultado da geocodificação por contrato para que novas execuções (locais ou via GitHub Actions) processem apenas contratos inéditos.
- **Particionamento dos Artefatos Estáticos (`public/data/`):** Para garantir carregamento rápido em dispositivos móveis sem paginação de servidor, os dados são divididos em malhas GeoJSON simplificadas (`geo/`), um arquivo de índice enxuto por ano (`index_<ano>.json`) para renderização imediata do mapa e tabela, e arquivos individuais por contrato (`obras/<id>.json`) carregados sob demanda (`fetch`) apenas quando o usuário abre a Ficha Limpa da Obra.

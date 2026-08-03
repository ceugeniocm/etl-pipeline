# Big Data ETL Pipeline

Este projeto é um pipeline de ETL de alta performance projetado para extrair dados de grandes arquivos Excel (.xlsx, .xls), transformá-los e validá-los, e carregá-los em um banco de dados MySQL.

## Principais Funcionalidades
- **Eficiência de Memória**: Utiliza streaming e chunked reads para lidar com milhões de linhas sem alto consumo de memória.
- **Validação Robusta**: Regras de validação configuráveis e rejection thresholds.
- **Carregamento Flexível**: Suporta os modos `append`, `truncate` e `upsert` com lógica de batching e retry.
- **Observabilidade**: Logging detalhado e relatórios de rejeição em CSV.

## Início Rápido
1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute o pipeline com um arquivo de configuração:
   ```bash
   python3 main.py config.json
   ```

## Documentação
Para informações detalhadas sobre instalação, configuração e uso, veja [docs/usage.md](docs/usage.md).
Para instruções de deploy (Docker e Host), veja [docs/deploy.md](docs/deploy.md).

## Requisitos
Veja [docs/requirements.md](docs/requirements.md) para a especificação completa.

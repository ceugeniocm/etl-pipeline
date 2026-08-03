# Documentação de Uso

Este documento descreve como instalar, configurar e executar o pipeline de ETL.

## Instalação

### Pré-requisitos
- Python 3.8 ou superior.
- Acesso a um banco de dados MySQL.

### Configuração
1. Clone o repositório.
2. Crie e ative um ambiente virtual (opcional, mas recomendado):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

## Uso Básico

O pipeline é executado via `main.py` usando um arquivo de configuração:

```bash
python3 main.py config.json
```

## Execução com Docker

Você também pode executar o pipeline usando Docker para evitar a instalação de dependências locais.

### Usando Docker Compose (Recomendado para desenvolvimento)

O projeto inclui um `docker-compose.yml` que sobe uma instância do MySQL e executa o pipeline automaticamente:

```bash
docker-compose up --build
```

### Usando Docker diretamente

1. Construa a imagem:
   ```bash
   docker build -t etl-pipeline .
   ```

2. Execute o container:
   ```bash
   docker run --env-file .env etl-pipeline config.json
   ```

Para instruções detalhadas de configuração e deploy, consulte o [Guia de Deploy](deploy.md).

## Opções da CLI

A CLI suporta diversos argumentos que sobrepõem os valores do arquivo de configuração:

| Opção | Descrição |
|--------|-------------|
| `config` | Caminho para o arquivo de configuração JSON (posicional, obrigatório). |
| `--source` | Caminho para o arquivo Excel de origem (`.xlsx` ou `.xls`). |
| `--sheet` | Nome da aba (sheet) a ser lida (o padrão é a primeira aba). |
| `--table` | Nome da tabela MySQL de destino. |
| `--chunk-size` | Número de linhas a serem lidas por bloco (eficiência de memória). |
| `--batch-size` | Número de registros a serem carregados por lote (performance). |
| `--mode` | Modo de carga (`append`, `truncate`, `upsert`). |
| `--log-level` | Nível de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |
| `--log-file` | Caminho para um arquivo para salvar os logs. |
| `--dry-run` | Executa a extração, transformação e validação sem gravar no banco de dados. |
| `--verbose` | Atalho para `--log-level DEBUG`. |
| `--resume` | Retoma a execução a partir da última posição registrada no arquivo de checkpoint. |
| `--workers` | Número de processos paralelos para a transformação. |
| `--help` | Mostra a mensagem de ajuda. |

## Arquivo de Configuração

A configuração é um arquivo JSON com as seguintes seções:

### `source`
- `path` (string, obrigatório): Caminho para o arquivo Excel.
- `sheet` (string, opcional): Nome da aba.
- `header_row` (integer, opcional): Índice (baseado em 1) da linha de cabeçalho (padrão: 1).
- `chunk_size` (integer, opcional): Linhas por bloco (padrão: 5000).

### `mapping`
- `columns` (object, obrigatório): Mapeamento dos nomes das colunas de origem para os nomes das colunas do banco de dados de destino.
- `types` (object, opcional): Mapeamento dos nomes das colunas de destino para tipos (`str`, `int`, `decimal`, `float`, `bool`, `date`, `datetime`).
- `normalizers` (object, opcional): Mapeamento dos nomes das colunas de destino para listas de normalizadores (`trim`, `upper`, `lower`, `strip_punctuation`, `collapse_spaces`).

### `validation`
- `required` (array, opcional): Lista de nomes de colunas de destino que não podem ser nulas.
- `ranges` (object, opcional): Mapeamento de nomes de colunas de destino para `{ "minimum": X, "maximum": Y }`.
- `max_lengths` (object, opcional): Mapeamento de nomes de colunas de destino para o comprimento máximo da string.
- `rejection_threshold` (string ou integer, opcional): Número máximo absoluto de linhas rejeitadas (ex: `100`) ou porcentagem (ex: `"5%"`).
- `business_key` (array, opcional): Lista de colunas de destino que formam uma chave de negócio para deduplicação.
- `on_duplicate` (string, opcional): Ação para chaves de negócio duplicadas (`discard` ou `report`). Padrão: `discard`.

### `database`
- `host` (string, obrigatório): Host do MySQL.
- `port` (integer, opcional): Porta do MySQL (padrão: 3306).
- `database` (string, obrigatório): Nome do banco de dados.
- `user` (string, obrigatório): Usuário do banco de dados.
- `password` (string, opcional): Senha do banco de dados.
- `connect_retries` (integer, opcional): Tentativas de reconexão (padrão: 3).
- `retry_backoff_seconds` (float, opcional): Backoff inicial em segundos (padrão: 1.0).

### `load`
- `table` (string, obrigatório): Nome da tabela de destino.
- `mode` (string, opcional): Modo de carga (`append`, `truncate`, `upsert`). Padrão: `append`.
- `batch_size` (integer, opcional): Registros por lote (padrão: 1000).
- `unique_key` (array, opcional): Colunas para `ON DUPLICATE KEY UPDATE` no modo `upsert`.
- `on_batch_error` (string, opcional): Ação em caso de falha no lote (`isolate` ou `abort`). Padrão: `isolate`.

### `run`
- `log_level` (string, opcional): Padrão: `INFO`.
- `log_file` (string, opcional): Caminho para o arquivo de log.
- `rejection_report` (string, opcional): Caminho para o relatório de rejeição CSV (padrão: `rejeicoes.csv`).
- `checkpoint_file` (string, opcional): Caminho para o arquivo de checkpoint JSON (padrão: `checkpoint.json`).
- `dry_run` (boolean, opcional): Padrão: `false`.
- `resume` (boolean, opcional): Padrão: `false`.
- `workers` (integer, opcional): Número de processos paralelos (padrão: 1).

## Variáveis de Ambiente

Variáveis de ambiente podem ser usadas para sobrepor os valores de configuração. Elas têm precedência sobre o arquivo JSON.

- `ETL_DB_PASSWORD`: Senha do banco de dados.
- `ETL_DB_USER`: Usuário do banco de dados.
- `ETL_DB_HOST`: Host do banco de dados.
- `ETL_DB_PORT`: Porta do banco de dados.
- `ETL_DB_NAME`: Nome do banco de dados.
- `ETL_SOURCE_PATH`: Caminho do arquivo de origem.
- `ETL_LOAD_TABLE`: Nome da tabela de destino.
- `ETL_LOG_LEVEL`: Nível de log.
- `ETL_DRY_RUN`: Habilita dry run (`true`/`1`).
- `ETL_RESUME`: Habilita o modo de retomada (`true`/`1`).
- `ETL_CHECKPOINT_FILE`: Caminho para o arquivo de checkpoint.
- `ETL_WORKERS`: Número de processos paralelos.

## Modos de Carga

| Modo | Descrição |
|------|-------------|
| `append` | Insere linhas na tabela de destino. Não afeta os dados existentes. |
| `truncate` | Exclui todos os dados da tabela de destino antes de iniciar a carga. |
| `upsert` | Atualiza as linhas existentes se uma chave única coincidir, caso contrário, insere. Requer que `unique_key` esteja configurado. |

## Códigos de Saída (Exit Codes)

A aplicação retorna os seguintes códigos de saída:

| Código | Significado |
|------|---------|
| 0 | SUCCESS |
| 1 | UNEXPECTED_ERROR |
| 2 | CONFIG_ERROR (Configuração inválida ou ausente) |
| 3 | EXTRACTION_ERROR (Falha ao ler o arquivo de origem) |
| 4 | MAPPING_ERROR (Mapeamento inconsistente com o cabeçalho) |
| 5 | VALIDATION_ERROR (Falha na validação estrutural) |
| 6 | REJECTION_THRESHOLD (Limite de rejeição atingido) |
| 7 | DATABASE_CONNECTION_ERROR (Falha ao conectar ao MySQL) |
| 8 | LOAD_ERROR (Falha ao gravar no banco de dados) |
| 70 | NOT_IMPLEMENTED (Funcionalidade ainda não implementada) |

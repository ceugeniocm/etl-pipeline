"""Catálogo central de mensagens voltadas ao usuário (NFR-007).

Todo texto exibido ao usuário — erros, ajuda da CLI, progresso e resumo — é
definido aqui em ``pt_BR``. Strings técnicas (identificadores, SQL, nomes de
exceções e níveis de log) permanecem em ``en_US``, assim como os nomes das
constantes deste módulo.

As mensagens são templates de :meth:`str.format`; os campos nomeados fazem
parte do contrato de cada mensagem e não devem ser renomeados sem atualizar
os pontos de uso.
"""

# --------------------------------------------------------------------------
# Genéricas
# --------------------------------------------------------------------------

#: Substituto exibido no lugar de qualquer credencial (NFR-004).
REDACTED_PLACEHOLDER = "***"

ERR_UNEXPECTED = "Erro inesperado durante a execução: {reason}"

# --------------------------------------------------------------------------
# Configuração (FR-011)
# --------------------------------------------------------------------------

ERR_CONFIG_FILE_NOT_FOUND = "Arquivo de configuração não encontrado: {path}"
ERR_CONFIG_FILE_UNREADABLE = (
    "Não foi possível ler o arquivo de configuração '{path}': {reason}"
)
ERR_CONFIG_INVALID_FORMAT = (
    "O arquivo de configuração '{path}' não contém um JSON válido: {reason}"
)
ERR_CONFIG_MISSING_KEY = (
    "Configuração inválida: a chave obrigatória '{key}' não foi informada."
)
ERR_CONFIG_INVALID_VALUE = (
    "Configuração inválida: o valor da chave '{key}' é inválido ({reason})."
)
ERR_CONFIG_INVALID_CHOICE = (
    "Configuração inválida: o valor '{value}' da chave '{key}' não é "
    "permitido. Use um destes: {allowed}."
)
ERR_CONFIG_UNKNOWN_KEY = (
    "Configuração inválida: a chave '{key}' não é reconhecida. Chaves "
    "aceitas nesta seção: {allowed}."
)
ERR_CONFIG_NOT_AN_OBJECT = (
    "Configuração inválida: a seção '{key}' deve ser um objeto."
)
ERR_CONFIG_UNKNOWN_COLUMN = (
    "Configuração inválida: a chave '{key}' referencia a coluna de destino "
    "'{column}', que não existe no mapeamento de colunas."
)
ERR_CONFIG_DUPLICATE_TARGET_COLUMN = (
    "Configuração inválida: a coluna de destino '{column}' foi mapeada mais "
    "de uma vez."
)
ERR_CONFIG_UNKNOWN_LOAD_MODE = (
    "Modo de carga desconhecido: '{mode}'. Use um destes: {allowed}."
)
ERR_CONFIG_INVALID_THRESHOLD = (
    "Configuração inválida: o limite de rejeições '{value}' da chave '{key}' "
    "deve ser um número inteiro de linhas ou um percentual como '5%'."
)

# --------------------------------------------------------------------------
# Extração (FR-001, FR-002)
# --------------------------------------------------------------------------

ERR_SOURCE_FILE_NOT_FOUND = "Arquivo de origem não encontrado: {path}"
ERR_SOURCE_UNREADABLE = (
    "Não foi possível ler a planilha '{path}': o arquivo está corrompido ou "
    "não é uma planilha válida."
)
ERR_SOURCE_UNSUPPORTED_FORMAT = (
    "Formato de arquivo não suportado: '{extension}'. Utilize .xlsx ou .xls."
)
ERR_SOURCE_MISSING_DEPENDENCY = (
    "A leitura de arquivos '{extension}' exige a biblioteca '{package}', que "
    "não está instalada. Execute: python3 -m pip install -r requirements.txt"
)
ERR_SHEET_NOT_FOUND = "A aba '{sheet}' não existe na planilha '{path}'."
ERR_SHEET_EMPTY = "A aba '{sheet}' está vazia: nenhuma linha de dados encontrada."
ERR_HEADER_MISSING = (
    "A aba '{sheet}' não possui linha de cabeçalho na posição {row}."
)
ERR_HEADER_DUPLICATE_COLUMN = (
    "A coluna '{column}' aparece mais de uma vez no cabeçalho da aba "
    "'{sheet}', o que torna o mapeamento ambíguo."
)
INFO_SHEET_SELECTED = (
    "Aba '{sheet}' selecionada em '{path}': {columns} colunas no cabeçalho."
)
INFO_ROWS_READ = "Leitura da aba '{sheet}' concluída: {count} linhas."

# --------------------------------------------------------------------------
# Mapeamento de colunas (FR-003)
# --------------------------------------------------------------------------

ERR_MAPPING_MISSING_COLUMNS = (
    "As seguintes colunas mapeadas não foram encontradas no cabeçalho da "
    "aba '{sheet}': {columns}."
)
ERR_MAPPING_EMPTY = (
    "Nenhum mapeamento de colunas foi definido na configuração."
)

# --------------------------------------------------------------------------
# Limpeza, conversão e validação (FR-004, FR-005, FR-006)
# --------------------------------------------------------------------------

ERR_UNKNOWN_NORMALIZER = (
    "Normalizador desconhecido '{normalizer}' configurado para a coluna "
    "'{column}'."
)
ERR_UNKNOWN_TYPE = (
    "Tipo desconhecido '{type_name}' declarado para a coluna '{column}'."
)
REJECT_REQUIRED_FIELD = "Campo obrigatório '{column}' não preenchido."
REJECT_TYPE_CONVERSION = (
    "Não foi possível converter o valor '{value}' da coluna '{column}' para "
    "o tipo {expected_type}."
)
REJECT_OUT_OF_RANGE = (
    "O valor '{value}' da coluna '{column}' está fora do intervalo permitido "
    "({minimum} a {maximum})."
)
REJECT_MAX_LENGTH = (
    "O valor da coluna '{column}' possui {length} caracteres e excede o "
    "limite de {maximum}."
)
REJECT_DUPLICATE_KEY = (
    "Registro duplicado: a chave de negócio {key} já apareceu na linha "
    "{first_row}."
)
ERR_REJECTION_THRESHOLD_EXCEEDED = (
    "Limite de registros rejeitados excedido: {rejected} rejeitados de "
    "{total} lidos (limite: {threshold})."
)

# --------------------------------------------------------------------------
# Banco de dados e carga (FR-008, FR-009, FR-010)
# --------------------------------------------------------------------------

ERR_DB_CONNECTION_FAILED = (
    "Não foi possível conectar ao banco de dados MySQL em {host}:{port}, "
    "base '{database}', usuário '{user}'."
)
ERR_DB_CONNECTION_LOST = (
    "A conexão com o banco de dados foi perdida durante a execução."
)
ERR_DB_RETRY = (
    "Falha na conexão com o banco de dados. Nova tentativa {attempt} de "
    "{total} em {delay:.1f}s."
)
ERR_DB_TABLE_NOT_FOUND = (
    "A tabela de destino '{table}' não existe na base de dados '{database}'."
)
ERR_DB_COLUMNS_NOT_FOUND = (
    "As seguintes colunas de destino não existem na tabela '{table}': "
    "{columns}."
)
ERR_LOAD_BATCH_FAILED = (
    "Falha ao gravar o lote iniciado na linha {first_row} ({size} "
    "registros): {reason}"
)
ERR_LOAD_ROW_FAILED = "Falha ao gravar a linha {row}: {reason}"
ERR_UPSERT_WITHOUT_KEY = (
    "O modo de carga 'upsert' exige a definição de uma chave única na "
    "configuração."
)

# --------------------------------------------------------------------------
# Interface de linha de comando (FR-012)
# --------------------------------------------------------------------------

CLI_DESCRIPTION = (
    "Pipeline ETL: extrai dados de planilhas Excel, transforma e carrega em "
    "um banco de dados MySQL."
)
CLI_EPILOG = (
    "Códigos de saída: 0 sucesso; 1 erro inesperado; 2 configuração "
    "inválida; 3 falha de extração; 4 falha de mapeamento; 5 falha de "
    "validação; 6 limite de rejeições excedido; 7 falha de conexão; "
    "8 falha de carga."
)
CLI_HELP_CONFIG = "Caminho do arquivo de configuração."
CLI_HELP_SOURCE = "Caminho da planilha de origem (sobrepõe a configuração)."
CLI_HELP_SHEET = "Nome da aba a ser lida (sobrepõe a configuração)."
CLI_HELP_TABLE = "Tabela de destino no MySQL (sobrepõe a configuração)."
CLI_HELP_CHUNK_SIZE = "Quantidade de linhas lidas por bloco."
CLI_HELP_BATCH_SIZE = "Quantidade de registros gravados por lote."
CLI_HELP_LOAD_MODE = "Modo de carga: append, truncate ou upsert."
CLI_HELP_LOG_LEVEL = "Nível de log: DEBUG, INFO, WARNING, ERROR ou CRITICAL."
CLI_HELP_LOG_FILE = "Caminho do arquivo de log."
CLI_HELP_DRY_RUN = (
    "Executa extração, transformação e validação sem gravar no banco."
)
CLI_HELP_VERBOSE = "Aumenta o detalhamento das mensagens (equivale a DEBUG)."
CLI_HELP_RESUME = "Retoma a execução a partir do último ponto salvo."
CLI_NOT_IMPLEMENTED = (
    "A execução do pipeline ainda não foi implementada (prevista para a "
    "Fase 6 em docs/tasks.md)."
)

# --------------------------------------------------------------------------
# Progresso e resumo da execução (FR-013, FR-014)
# --------------------------------------------------------------------------

INFO_RUN_STARTED = "Início da execução: planilha '{source}' -> tabela '{table}'."
INFO_RESUMING = "Retomando a execução a partir da linha {row}."
INFO_RUN_FINISHED = "Execução finalizada."
INFO_DRY_RUN = (
    "Modo simulação ativado: nenhum dado será gravado no banco de dados."
)
INFO_LOAD_MODE = "Modo de carga: {mode}."
INFO_DIMENSION_LOAD_STARTED = "Iniciando carga da tabela de dimensão '{table}'."
INFO_DIMENSION_LOAD_FINISHED = (
    "Carga da tabela de dimensão '{table}' finalizada: {count} registros."
)
INFO_TRUNCATING_TABLE = "Esvaziando a tabela de destino '{table}'."
INFO_REJECTION_REPORT_WRITTEN = (
    "Relatório de rejeições gravado em: {path} ({count} registros)."
)
PROGRESS_CHUNK = (
    "Progresso: {read} linhas lidas, {transformed} transformadas, "
    "{loaded} carregadas, {rejected} rejeitadas."
)
SUMMARY_TITLE = "Resumo da execução"
SUMMARY_ROWS_READ = "Linhas lidas: {count}"
SUMMARY_ROWS_TRANSFORMED = "Linhas transformadas: {count}"
SUMMARY_ROWS_LOADED = "Linhas carregadas: {count}"
SUMMARY_ROWS_REJECTED = "Linhas rejeitadas: {count}"
SUMMARY_ROWS_DUPLICATED = "Linhas duplicadas descartadas: {count}"
SUMMARY_ELAPSED = "Tempo total: {elapsed}"
SUMMARY_STATUS_SUCCESS = "Situação: concluída com sucesso"
SUMMARY_STATUS_FAILURE = "Situação: encerrada com erro"

#: Exporta todas as constantes de mensagem definidas acima.
__all__ = sorted(name for name in dict(globals()) if name.isupper())

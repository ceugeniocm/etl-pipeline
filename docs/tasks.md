# Lista de Tarefas Técnicas

Tarefas de implementação enumeradas derivadas de `docs/plan.md`, agrupadas em fases de desenvolvimento.
Cada tarefa vincula-se ao seu item do plano e ao(s) requisito(s) que satisfaz em `docs/requirements.md`.

Marque uma tarefa como concluída alterando `[ ]` para `[x]`.

---

## Fase 1 — Configuração e Fundação

- [x] **1.** Criar o pacote `etl/` com `__init__.py` e os módulos vazios `messages.py`, `errors.py`,
  `config.py`, `logging_setup.py`, `extract.py`, `pipeline.py`, `reporting.py`, `cli.py`, além dos
  subpacotes `transform/` e `load/`. — *Plano: A1 · Requisito: NFR-006*
- [x] **2.** Substituir o conteúdo de exemplo de `main.py` por um bootstrap que chama `etl.cli.main()` e sai
  com seu código de retorno. — *Plano: A1 · Requisito: FR-012, NFR-008*
- [x] **3.** Criar `requirements.txt` declarando `openpyxl` e o driver MySQL (`mysql-connector-python`),
  fixados em versões principais. — *Plano: A2 · Requisito: NFR-008*
- [x] **4.** Implementar `etl/messages.py` com constantes/templates de mensagens `pt_BR` nomeadas para erros, ajuda da CLI,
  linhas de progresso e o resumo da execução. — *Plano: A3 · Requisito: NFR-007*
- [x] **5.** Implementar `etl/errors.py` com `EtlError` e as subclasses `ConfigError`, `ExtractionError`,
  `MappingError`, `ValidationError`, `RejectionThresholdExceeded`, `DatabaseConnectionError`, `LoadError`,
  cada uma carregando uma mensagem `pt_BR` e uma dica de código de saída. — *Plano: A4 · Requisito: NFR-006, NFR-007, FR-012*
- [x] **6.** Implementar `etl/logging_setup.py`: handler de console, handler de arquivo opcional, nível configurável.
  — *Plano: A5 · Requisito: FR-013*
- [x] **7.** Adicionar um filtro/formatador de log que redija valores semelhantes a senhas de cada registro de log.
  — *Plano: A5 · Requisito: NFR-004, FR-013*
- [x] **8.** Escrever `../tests/test_logging_setup.py` assegurando o tratamento de nível, saída de arquivo e redação de senha.
  — *Plano: H2, H5 · Requisito: FR-013, NFR-004, NFR-005*

> **Notas da Fase 1**
> - A exceção de banco de dados é nomeada `DatabaseConnectionError` (não `ConnectionError`) para evitar sombrear o
>   built-in do Python; os itens A4 e E1 de `docs/plan.md` foram atualizados adequadamente.
> - `etl/cli.py` contém um placeholder `main()` que imprime `CLI_NOT_IMPLEMENTED` e retorna o código de saída `70`,
>   então `python3 main.py` já executa hoje; a tarefa 48 o substitui pela interface real `argparse`.
> - Os códigos de saída são definidos em `etl/errors.py`: `0` sucesso, `1` inesperado, `2` config, `3` extração,
>   `4` mapeamento, `5` validação, `6` limite de rejeição, `7` conexão, `8` carga, `70` não implementado.
> - As dependências estão declaradas, mas não instaladas; execute `python3 -m pip install -r requirements.txt` antes da
>   Fase 3.

## Fase 2 — Configuração

- [x] **9.** Definir as dataclasses de configuração `SourceConfig`, `MappingConfig`, `ValidationConfig`,
  `DatabaseConfig`, `LoadConfig` e `RunConfig` em `etl/config.py`. — *Plano: B1 · Requisito: FR-011*
- [x] **10.** Implementar o parser de arquivo de configuração produzindo essas dataclasses. — *Plano: B1 · Requisito: FR-011*
- [x] **11.** Implementar substituições por variáveis de ambiente com precedência sobre os valores do arquivo (incluindo
  `ETL_DB_PASSWORD`). — *Plano: B2 · Requisito: FR-011, NFR-004*
- [x] **12.** Implementar validação fail-fast de todas as chaves de configuração (presença, tipo, intervalo) lançando
  `ConfigError` nomeando a chave ofensiva em `pt_BR`, executada antes de qualquer acesso a arquivo ou banco de dados.
  — *Plano: B3 · Requisito: FR-011, NFR-003*
- [x] **13.** Definir e documentar valores padrão para tamanho de bloco e tamanho de lote. — *Plano: B3 · Requisito: FR-002, FR-009*
- [x] **14.** Escrever `../tests/test_config.py` cobrindo parsing, substituições de env, padrões e cada erro de chave inválida.
  — *Plano: H2 · Requisito: FR-011, NFR-005*

> **Notas da Fase 2**
> - O formato do arquivo de configuração é **JSON**: ele é coberto pela biblioteca padrão, portanto não adiciona
>   dependência (NFR-008), e representa o mapeamento de colunas aninhado diretamente.
> - A precedência é padrões < arquivo < variáveis de ambiente `ETL_*` < substituições explícitas. O dicionário de
>   substituição usa caminhos pontilhados (`{"load.batch_size": 500}`) e ignora `None`, para que a CLI da Fase 6 possa
>   encaminhar argumentos opcionais inalterados.
> - As mensagens de erro nomeiam a variável de ambiente (`ETL_DB_PORT`) em vez do caminho do arquivo quando o valor incorreto
>   veio do ambiente, para que o usuário saiba onde corrigir.
> - Chaves desconhecidas são rejeitadas em vez de ignoradas, o que transforma erros de digitação em erros de configuração fail-fast.
> - `parse_config` chama `logging_setup.register_secret` na senha do banco de dados, para que a senha seja
>   redigida de cada linha de log a partir desse ponto (NFR-004); `DatabaseConfig` também a oculta do `repr`.
> - Padrões (tarefa 13): tamanho do bloco `5000` linhas, tamanho do lote `1000` registros, linha de cabeçalho `1`, porta MySQL
>   `3306`, `3` retentativas de conexão com backoff inicial de `1.0 s`, modo de carga `append`, `isolate` em erro de lote,
>   `discard` em chave duplicada, `rejeicoes.csv` como o relatório de rejeição.

## Fase 3 — Extração

- [x] **15.** Implementar o leitor de `.xlsx` em streaming em `etl/extract.py` usando `openpyxl`
  `read_only=True, data_only=True`. — *Plano: C1 · Requisito: FR-001, NFR-001*
- [x] **16.** Implementar a seleção de planilha: nome da planilha configurado, usando como padrão a primeira planilha.
  — *Plano: C1 · Requisito: FR-001*
- [x] **17.** Derivar nomes de colunas da linha de cabeçalho e expor linhas como objetos carregando valores, nome da planilha
  e número da linha de origem. — *Plano: C1 · Requisito: FR-001, NFR-009*
- [x] **18.** Implementar o invólucro de fragmentação (chunking) gerando listas de no máximo `chunk_size` linhas.
  — *Plano: C2 · Requisito: FR-002, NFR-001*
- [x] **19.** Implementar tratamento de erros de origem para caminho ausente, pasta de trabalho ilegível/corrompida, extensão
  não suportada, planilha ausente e planilha vazia, lançando `ExtractionError`. — *Plano: C3 · Requisito: FR-001, NFR-007*
- [x] **20.** Escrever `../tests/test_extract.py` com fixtures geradas cobrindo o caminho feliz, limites de bloco, derivação de cabeçalho
  e cada caso de erro. — *Plano: H1, H2 · Requisito: FR-001, FR-002, NFR-005*
- [x] **21.** Adicionar suporte a `.xls` legado sob a mesma interface de iterador, ou um erro explícito de formato não suportado
  quando a dependência estiver ausente. — *Plano: C4 · Requisito: FR-001*

> **Notas da Fase 3**
> - As dependências são instaladas no ambiente virtual do projeto; execute a suite com
>   `.venv/bin/python -m unittest discover`. Sob um `python3` puro, os testes de `.xlsx`/`.xls` são ignorados em vez de
>   falhar, portanto, uma execução verde lá não significa cobertura total.
> - `SourceRow` carrega `sheet`, `number` (o número da linha conforme mostrado no Excel, base 1) e `values` indexados pelo
>   nome da coluna de origem, que é o que o relatório de rejeição precisa (NFR-009).
> - Linhas mais curtas que o cabeçalho são preenchidas com `None` e valores além da última coluna do cabeçalho são descartados,
>   para que cada linha exponha exatamente as colunas do cabeçalho.
> - Linhas totalmente em branco são puladas sem consumir um número de linha; uma planilha cujas linhas de dados estão todas em branco é
>   relatada como vazia.
> - Células de cabeçalho em branco recebem o nome reservado `__coluna_N__` (elas não podem ser mapeadas, mas mantêm as
>   colunas seguintes alinhadas); cabeçalhos em branco à direita são descartados; um nome de cabeçalho repetido é rejeitado como
>   `ExtractionError` porque tornaria o mapeamento ambíguo.
> - Um erro de planilha vazia surge quando o iterador de linhas é consumido, não quando o arquivo é aberto, porque o
>   leitor é preguiçoso por design (NFR-001).
> - O `.xls` legado (tarefa 21) é lido através do `xlrd`, que converte seriais de data e booleanos no momento da leitura para que
>   ambos os formatos entreguem os mesmos tipos Python para a Fase 4. O `xlrd` não pode *gravar* `.xls`, e o projeto não
>   depende de um gravador BIFF, portanto, os testes de `.xls` cobrem o roteamento de extensão, arquivos ilegíveis, a mensagem de
>   dependência ausente e a conversão de célula, mas não um round trip completo.
> - `.junie/AGENTS.md` foi atualizado com os comandos do ambiente virtual; a tarefa 65 permanece aberta para qualquer outra
>   mudança de layout.

## Fase 4 — Transformação

- [x] **22.** Implementar mapeamento de coluna origem→destino em `etl/transform/mapping.py`, descartando colunas não mapeadas.
  — *Plano: D1 · Requisito: FR-003*
- [x] **23.** Implementar a verificação inicial de que cada coluna de origem mapeada existe no cabeçalho, lançando
  `MappingError` listando todas as colunas ausentes antes de qualquer carga. — *Plano: D1 · Requisito: FR-003*
- [x] **24.** Implementar a remoção de espaços em branco e conversão de vazio/apenas espaços → `None` em
  `etl/transform/cleaning.py`. — *Plano: D2 · Requisito: FR-004*
- [x] **25.** Implementar o registro de normalizadores por coluna (maiúsculas, minúsculas, remover pontuação, colapsar
  espaços) aplicado apenas onde configurado. — *Plano: D2 · Requisito: FR-004*
- [x] **26.** Implementar coerção de tipo para `int`, `Decimal`, `date`, `datetime`, `bool` e `str` em
  `etl/transform/types.py`. — *Plano: D3 · Requisito: FR-005*
- [x] **27.** Implementar conversão de número de série do Excel → date/datetime e separadores decimais sensíveis ao locale.
  — *Plano: D3 · Requisito: FR-005*
- [x] **28.** Fazer com que as falhas de conversão retornem um resultado de falha tipado em vez de lançar exceção, para que a execução continue.
  — *Plano: D3, D4 · Requisito: FR-005, FR-006*
- [x] **29.** Implementar o mecanismo de validação em `etl/transform/validation.py` (campos obrigatórios, intervalos,
  comprimentos, resultados de conversão) produzindo um registro limpo ou uma `Rejection`. — *Plano: D4 · Requisito: FR-006*
- [x] **30.** Definir o registro `Rejection` com nome da planilha, número da linha de origem, coluna e motivo em `pt_BR`.
  — *Plano: D4 · Requisito: FR-006, NFR-009*
- [x] **31.** Implementar o contador de limite de rejeição abortando a execução com `RejectionThresholdExceeded`
  quando o limite absoluto/percentual configurado é ultrapassado. — *Plano: D5 · Requisito: FR-006*
- [x] **32.** Implementar deduplicação por chave de negócio em `etl/transform/dedup.py` com um conjunto de chaves vistas
  limitado em memória, e um caminho no-op quando nenhuma chave é configurada. — *Plano: D6 · Requisito: FR-007, NFR-001*
- [x] **33.** Escrever `../tests/test_mapping.py`, `../tests/test_cleaning.py`, `../tests/test_types.py`, `../tests/test_validation.py` e
  `../tests/test_dedup.py` cobrindo os caminhos felizes e cada motivo de rejeição. — *Plano: H2 · Requisito: FR-003…FR-007, NFR-005*

## Fase 5 — Loading

- [x] **34.** Implementar a fábrica de conexão MySQL em `etl/load/connection.py` atrás de uma interface pequena que
  os testes podem substituir. — *Plano: E1 · Requisito: FR-008, NFR-005*
- [x] **35.** Garantir que as falhas de conexão lancem `ConnectionError` com uma mensagem `pt_BR` que nunca contenha
  a senha. — *Plano: E1 · Requisito: FR-008, NFR-004*
- [x] **36.** Implementar retry configurável com backoff exponencial para conexão inicial e reconexão no meio da
  execução. — *Plano: E2 · Requisito: FR-008, NFR-003*
- [x] **37.** Implementar verificações pré-execução de que a tabela de destino e todas as colunas de destino mapeadas existem, abortando
  com uma mensagem `pt_BR` nomeando o que está ausente. — *Plano: E3 · Requisito: FR-010, FR-003*
- [x] **38.** Implementar o inseridor em lote em `etl/load/loader.py` usando `executemany` parametrizado /
  `INSERT` multi-linha com o tamanho do lote configurado. — *Plano: E4 · Requisito: FR-009, NFR-002, NFR-004*
- [x] **39.** Realizar o commit após cada lote inserido com sucesso. — *Plano: E4 · Requisito: FR-009, NFR-003*
- [x] **40.** Implementar tratamento de falha de lote: rollback e, em seguida, isolamento linha por linha da linha ofensiva ou
  abortar, conforme a configuração. — *Plano: E5 · Requisito: FR-009, FR-006, NFR-003*
- [x] **41.** Implementar modo de carga `append`. — *Plano: E6 · Requisito: FR-010*
- [x] **42.** Implementar modo de carga `truncate` (esvaziar o destino antes de inserir). — *Plano: E6 · Requisito: FR-010*
- [x] **43.** Implementar modo de carga `upsert` via `INSERT ... ON DUPLICATE KEY UPDATE` na chave única declarada.
  — *Plano: E6 · Requisito: FR-010, FR-015*
- [x] **44.** Construir o dublê de teste fake connection/cursor registrando instruções executadas e parâmetros.
  — *Plano: H1 · Requisito: NFR-005*
- [x] **45.** Escrever `../tests/test_connection.py` e `../tests/test_loader.py` cobrindo retries, verificações pré-execução, lotes,
  commit/rollback e todos os três modos de carga. — *Plano: H2 · Requisito: FR-008…FR-010, NFR-003, NFR-005*

## Fase 6 — Orquestração, CLI e Relatórios

- [x] **46.** Implementar `etl/pipeline.py` conectando extração → fragmentação → mapeamento → limpeza → coerção → validação → deduplicação → carga como uma cadeia de iteradores preguiçosos. — *Plano: F1 · Requisito: FR-001…FR-010, NFR-001*
- [x] **47.** Implementar o tratamento do ciclo de vida da execução no pipeline: contadores, propagação de erros, desconexão.
  — *Plano: F1 · Requisito: NFR-003, FR-014*
- [x] **48.** Implementar a CLI `argparse` em `etl/cli.py` com o caminho da configuração e sobreposições (arquivo de origem,
  tabela, tamanho do bloco/lote, nível de log, `--verbose`) e texto de ajuda em `pt_BR`. — *Plano: F2 · Requisito: FR-012, FR-011*
- [x] **49.** Definir e implementar os códigos de saída: `0` em caso de sucesso e um código não zero distinto por classe de falha.
  — *Plano: F2 · Requisito: FR-012*
- [x] **50.** Implementar `--dry-run`, substituindo o carregador por um no-op de contagem, mantendo a produção do
  relatório de rejeição e resumo. — *Plano: F3 · Requisito: FR-012, FR-006*
- [x] **51.** Implementar os contadores e a linha de progresso por bloco em `etl/reporting.py` (lido / transformado /
  carregado / rejeitado). — *Plano: F4 · Requisito: FR-014, FR-013*
- [x] **52.** Implementar o resumo de fim de execução em `pt_BR` com totais e tempo decorrido, impresso no sucesso e na
  falha. — *Plano: F5 · Requisito: FR-014, NFR-007*
- [x] **53.** Implementar o gravador de relatório de rejeição CSV (planilha, linha de origem, coluna, motivo) para o
  caminho configurado. — *Plano: F6 · Requisito: FR-006, NFR-009*
- [x] **54.** Escrever `../tests/test_cli.py` e `../tests/test_reporting.py` cobrindo análise de argumentos, códigos de saída, dry-run,
  saída de progresso e conteúdo do relatório. — *Plano: H2 · Requisito: FR-012, FR-014, NFR-005*

## Fase 7 — Testes e Garantia de Qualidade

- [x] **55.** Implementar o gerador de fixture produzindo pastas de trabalho `.xlsx` com linhas válidas, tipos incorretos, campos
  obrigatórios ausentes, chaves duplicadas e células vazias. — *Plano: H1 · Requisito: NFR-005*
- [x] **56.** Escrever o `../tests/test_pipeline.py` de ponta a ponta executando uma planilha de fixture através de toda a cadeia
  contra a conexão falsa, assegurando as contagens de carregados/rejeitados e o código de saída. — *Plano: H3 · Requisito: NFR-005, NFR-003*
- [x] **57.** Escrever o teste de memória opcional/lento assegurando o crescimento limitado da memória em um arquivo gerado grande.
  — *Plano: H4 · Requisito: NFR-001*
- [x] **58.** Escrever o teste de taxa de transferência opcional/lento medindo linhas/minuto contra a meta NFR-002.
  — *Plano: H4 · Requisito: NFR-002*
- [x] **59.** Escrever testes de segurança provando que as senhas nunca aparecem em logs, mensagens, resumos ou tracebacks.
  — *Plano: H5 · Requisito: NFR-004*
- [x] **60.** Escrever um teste assegurando que cada instrução SQL que transporta dados use placeholders de parâmetros em vez de
  valores interpolados. — *Plano: H5 · Requisito: NFR-004*
- [x] **61.** Verificar se `python3 -m unittest discover` executa toda a suite verde a partir da raiz do projeto.
  — *Plano: H2, H3 · Requisito: NFR-005*
- [x] **62.** Realizar a passagem PEP 8 sobre todo o pacote e adicionar docstrings a todas as funções e
  classes públicas. — *Plano: H6 · Requisito: NFR-006*

## Fase 8 — Documentação

- [x] **63.** Escrever a documentação de uso: instalação, chaves de configuração, variáveis de ambiente, opções de CLI,
  códigos de saída e modos de carga. — *Plano: I1 · Requisito: NFR-008, FR-011, FR-012*
- [x] **64.** Atualizar os status dos requisitos em `docs/requirements.md` para refletir a funcionalidade entregue.
  — *Plano: I2 · Requisito: NFR-010*
- [x] **65.** Atualizar `.junie/AGENTS.md` se os comandos de execução/teste mudarem como resultado do novo layout do pacote.
  — *Plano: I2 · Requisito: NFR-010*

## Fase 9 — Restartability

- [x] **66.** Implementar `etl/checkpoint.py` persistindo a última posição da linha de origem confirmada após cada
  commit de lote. — *Plano: G1 · Requisito: FR-015*
- [x] **67.** Implementar a flag `--resume` pulando as linhas de origem até o checkpoint gravado.
  — *Plano: G2 · Requisito: FR-015*
- [x] **68.** Escrever `../tests/test_checkpoint.py` cobrindo a persistência do checkpoint, retomada e a garantia de não duplicidade
  sob `upsert`. — *Plano: H2 · Requisito: FR-015, NFR-005*

## Fase 10 — Carga de Tabelas de Dimensão

- [x] **69.** Criar mapeamentos de configuração para `tb_beneficiarios`, `tb_especialidades`, `tb_profissionais` e `tb_usuarios`. — *Plano: J1 · Requisito: FR-016, FR-003*
- [x] **70.** Implementar a lógica para extrair registros únicos para cada tabela de dimensão a partir dos dados de origem. — *Plano: J2 · Requisito: FR-016, FR-007*
- [x] **71.** Atualizar o pipeline para sequenciar o carregamento das tabelas de dimensão antes ou juntamente com a tabela de fatos principal. — *Plano: J3 · Requisito: FR-016*
- [x] **72.** Adicionar testes unitários para a nova lógica de carregamento de tabelas de dimensão, garantindo deduplicação e mapeamento corretos. — *Plano: H2 · Requisito: FR-016, NFR-005*
- [x] **73.** Executar testes de integração para verificar o processo ETL completo com múltiplas tabelas de destino. — *Plano: H3 · Requisito: FR-016, NFR-003*

## Fase 11 — Paralelismo

- [x] **74.** Adicionar a chave `workers` em `RunConfig` no arquivo `etl/config.py` e atualizar o parser de configuração. — *Plano: K1 · Requisito: FR-017*
- [x] **75.** Refatorar `etl/pipeline.py` para isolar a lógica de transformação de uma linha em uma função top-level (padrão para ser serializável pelo `multiprocessing`). — *Plano: K2 · Requisito: FR-017*
- [x] **76.** Implementar o uso de `ProcessPoolExecutor` no orquestrador do pipeline para processar blocos de linhas em paralelo. — *Plano: K2 · Requisito: FR-017, NFR-001*
- [x] **77.** Escrever `../tests/test_parallel.py` garantindo que o pipeline funcione corretamente com múltiplos workers e que a deduplicação permaneça íntegra. — *Plano: H2 · Requisito: FR-017, NFR-005*

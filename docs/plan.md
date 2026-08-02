# Plano de Implementação

## Introdução

Este plano traduz `docs/requirements.md` em um conjunto ordenado e agrupado de itens de implementação para o
pipeline de ETL de Big Data (Excel → transformação → MySQL). Cada item está explicitamente vinculado aos requisitos
que satisfaz e possui uma prioridade.

Decisões norteadoras:

- **Linguagem/runtime**: Python 3, sem etapa de build, ponto de entrada `python3 main.py` (NFR-008).
- **Layout do pacote**: um único pacote `etl/` com um módulo por preocupação, mantendo extração, transformação,
  carga, config, mensagens e CLI separados (NFR-006).
- **Biblioteca de extração**: `openpyxl` no modo streaming `read_only=True` para `.xlsx`; `pandas` é evitado
  como leitor principal porque materializa planilhas inteiras (NFR-001).
- **Driver de banco de dados**: `mysql-connector-python` (ou `PyMySQL`) acessado apenas através de um adaptador fino, para que a
  escolha do driver permaneça substituível e os testes unitários possam injetar um fake (NFR-005).
- **Contrato de streaming**: a extração gera um iterador de blocos; cada etapa consome e produz
  iteradores, para que a memória permaneça proporcional ao tamanho do bloco (NFR-001).
- **Mensagens**: todo o texto voltado para o usuário vive em `etl/messages.py` como constantes `pt_BR`; strings técnicas permanecem
  em inglês (NFR-007).
- **Testes**: `unittest`, arquivos `test_<funcionalidade>.py` na raiz do projeto, sem necessidade de MySQL ativo (NFR-005).

### Layout de módulos planejado

```
main.py                     # bootstrap CLI fino -> etl.cli
requirements.txt
etl/
    __init__.py
    messages.py             # catálogo de mensagens pt_BR
    errors.py               # hierarquia de exceções
    config.py               # carregamento de config, substituições de env, validação
    logging_setup.py        # configuração de log + redação de credenciais
    extract.py              # leitor de Excel em streaming
    transform/
        __init__.py
        mapping.py          # mapeamento de colunas origem -> destino
        cleaning.py         # trim, vazio -> NULL, normalizadores por coluna
        types.py            # coerção de tipos (int, decimal, date, datetime, bool)
        validation.py       # avaliação de regras, registros de rejeição
        dedup.py            # deduplicação por chave de negócio
    load/
        __init__.py
        connection.py       # fábrica de conexões, retry/backoff
        loader.py           # carregamento em lote, commit/rollback, modos de carga
    pipeline.py             # orquestração extração -> transformação -> carga
    reporting.py            # contadores de progresso, resumo da execução, relatório de rejeição
    cli.py                  # argparse, códigos de saída, --dry-run
    checkpoint.py           # suporte a retomada (resume)
test_*.py                   # módulos unittest
```

---

## Grupo A — Fundação do Projeto

### A1. Criar esqueleto do pacote e ponto de entrada
Criar o pacote `etl/` com o layout de módulos acima (vazio, mas importável) e reduzir `main.py` a um
bootstrap fino que delega para `etl.cli.main()` e propaga seu código de saída.
- **Requisitos**: NFR-006, NFR-008, FR-012
- **Prioridade**: Alta

### A2. Declarar dependências
Adicionar `requirements.txt` com o leitor de Excel e o driver MySQL fixados em versões principais; documentar o
comando de instalação na documentação.
- **Requisitos**: NFR-008
- **Prioridade**: Alta

### A3. Catálogo de mensagens (`etl/messages.py`)
Centralizar cada string voltada ao usuário como uma constante/template `pt_BR` nomeada (erros, ajuda da CLI, progresso,
resumo). Tokens técnicos permanecem em inglês.
- **Requisitos**: NFR-007 e critérios relacionados a mensagens de FR-001, FR-003, FR-006, FR-008, FR-010, FR-011, FR-012, FR-014
- **Prioridade**: Alta

### A4. Hierarquia de exceções (`etl/errors.py`)
Definir `EtlError` e subclasses: `ConfigError`, `ExtractionError`, `MappingError`, `ValidationError`,
`RejectionThresholdExceeded`, `DatabaseConnectionError`, `LoadError`. Cada uma carrega uma mensagem `pt_BR` e uma
dica estável de código de saída. O erro de banco de dados é nomeado `DatabaseConnectionError` em vez de `ConnectionError`
para não sombrear o built-in do Python com esse nome (PEP 8, NFR-006).
- **Requisitos**: NFR-006, NFR-007, FR-001, FR-006, FR-008, FR-011, FR-012
- **Prioridade**: Alta

### A5. Configuração de log (`etl/logging_setup.py`)
Configurar o módulo `logging` padrão: handler de console, handler de arquivo opcional, nível configurável e um
filtro/formatador que redige valores semelhantes a senhas de qualquer registro.
- **Requisitos**: FR-013, NFR-004
- **Prioridade**: Alta

---

## Grupo B — Configuração

### B1. Modelo de configuração e carregador (`etl/config.py`)
Carregar um arquivo de configuração (INI/JSON/YAML — um formato, documentado) em dataclasses tipadas:
`SourceConfig` (caminho, planilha, linha de cabeçalho, tamanho do bloco), `MappingConfig` (mapa de colunas, tipos declarados,
normalizadores), `ValidationConfig` (campos obrigatórios, intervalos, limite de rejeição, chave de negócio),
`DatabaseConfig` (host, porta, banco de dados, usuário, senha, retentativas), `LoadConfig` (tabela, modo de carga, tamanho do
lote), `RunConfig` (nível de log, arquivo de log, caminho do relatório de rejeição, dry-run).
- **Requisitos**: FR-011, FR-002, FR-003, FR-006, FR-007, FR-008, FR-009, FR-010, FR-013
- **Prioridade**: Alta

### B2. Substituições por variáveis de ambiente
Aplicar variáveis de ambiente (ex: `ETL_DB_PASSWORD`) sobre os valores do arquivo, com o ambiente tendo precedência;
espera-se que as credenciais cheguem desta forma.
- **Requisitos**: FR-011, NFR-004
- **Prioridade**: Alta

### B3. Validação de configuração com fail-fast
Validar presença, tipos e intervalos de cada chave **antes** de abrir o arquivo de origem ou a conexão com o banco de dados;
lançar `ConfigError` nomeando a chave ofensiva em `pt_BR`. Aplicar padrões documentados para tamanho de bloco
e tamanho de lote.
- **Requisitos**: FR-011, FR-002, FR-009, NFR-003
- **Prioridade**: Alta

---

## Grupo C — Extração

### C1. Leitor de planilha em streaming (`etl/extract.py`)
Abrir `.xlsx` via `openpyxl` no modo `read_only=True` / `data_only=True`; selecionar a planilha configurada ou a
primeira; ler a linha de cabeçalho para derivar nomes de colunas; gerar objetos `Row` carregando valores mais o nome da planilha
e número da linha de origem.
- **Requisitos**: FR-001, NFR-001, NFR-009
- **Prioridade**: Alta

### C2. Fragmentação (Chunking)
Envolver o iterador de linhas para que ele gere listas de, no máximo, `chunk_size` linhas; usar o padrão documentado quando a
configuração o omitir.
- **Requisitos**: FR-002, NFR-001
- **Prioridade**: Alta

### C3. Tratamento de erros de origem
Detectar caminho ausente, pasta de trabalho ilegível/corrompida, extensão não suportada, planilha configurada ausente e
planilha vazia; lançar `ExtractionError` com a mensagem `pt_BR` e um código de saída diferente de zero.
- **Requisitos**: FR-001, NFR-007
- **Prioridade**: Alta

### C4. Suporte a `.xls` legado
Adicionar um caminho de leitor alternativo para `.xls` legado (ex: `xlrd`) sob a mesma interface de iterador, ou rejeitar
o formato explicitamente com uma mensagem clara se a dependência não estiver disponível.
- **Requisitos**: FR-001
- **Prioridade**: Baixa

---

## Grupo D — Transformação

### D1. Mapeamento de colunas (`etl/transform/mapping.py`)
Aplicar o mapa origem→destino configurado a cada linha; descartar colunas de origem não mapeadas; verificar na inicialização (a partir
da linha de cabeçalho) que cada coluna de origem mapeada existe e lançar `MappingError` listando as ausentes
antes de qualquer carga começar.
- **Requisitos**: FR-003
- **Prioridade**: Alta

### D2. Limpeza e normalização (`etl/transform/cleaning.py`)
Remover espaços em branco no texto (trim); converter células vazias/apenas com espaços para `None`; fornecer um registro de
normalizadores por coluna (maiúsculas, minúsculas, remover pontuação, colapsar espaços internos) aplicados apenas onde configurado.
- **Requisitos**: FR-004
- **Prioridade**: Alta

### D3. Coerção de tipos (`etl/transform/types.py`)
Converter valores para os tipos de destino declarados — `int`, `Decimal`, `date`, `datetime`, `bool`, `str` —
incluindo conversão de data serial do Excel e separadores decimais sensíveis ao locale. Uma conversão com falha produz um
resultado de falha de tipagem em vez de uma exceção que interrompe a execução.
- **Requisitos**: FR-005
- **Prioridade**: Alta

### D4. Mecanismo de validação (`etl/transform/validation.py`)
Avaliar campos obrigatórios, intervalo, comprimento e resultados de conversão de tipo por linha; produzir ou um registro limpo
ou um `Rejection(sheet, source_row, column, reason_pt_br)`; continuar processando as linhas subsequentes.
- **Requisitos**: FR-006, FR-005, NFR-009
- **Prioridade**: Alta

### D5. Limite de rejeição
Rastrear a contagem de linhas rejeitadas ao longo da execução e abortar com `RejectionThresholdExceeded` assim que o limite
absoluto/percentual configurado for ultrapassado.
- **Requisitos**: FR-006
- **Prioridade**: Média

### D6. Deduplicação (`etl/transform/dedup.py`)
Quando uma chave de negócio é configurada, manter um conjunto limitado em memória de chaves vistas e descartar ou sinalizar repetições
de acordo com a configuração; não realizar operação quando nenhuma chave for configurada.
- **Requisitos**: FR-007, NFR-001
- **Prioridade**: Média

---

## Grupo E — Carga

### E1. Fábrica de conexão (`etl/load/connection.py`)
Criar uma conexão MySQL a partir de `DatabaseConfig`; em caso de falha, lançar `DatabaseConnectionError` com uma mensagem `pt_BR`
que nunca contenha a senha; expor a conexão através de uma interface pequena para que os testes possam substituir por
um fake.
- **Requisitos**: FR-008, NFR-004, NFR-005
- **Prioridade**: Alta

### E2. Retry com backoff
Tentar novamente o estabelecimento da conexão e a reconexão no meio da execução um número configurável de vezes com backoff
exponencial antes de falhar a execução.
- **Requisitos**: FR-008, NFR-003
- **Prioridade**: Média

### E3. Verificações pré-execução do destino
Antes de carregar, verificar se a tabela de destino existe e se cada coluna de destino mapeada existe nela; abortar com
uma mensagem `pt_BR` nomeando a tabela/coluna ausente.
- **Requisitos**: FR-010, FR-003, NFR-003
- **Prioridade**: Alta

### E4. Inseridor em lote (`etl/load/loader.py`)
Acumular registros validados em lotes do tamanho configurado e inseri-los com um `executemany` parametrizado /
`INSERT` multi-linha; realizar o commit por lote bem-sucedido.
- **Requisitos**: FR-009, NFR-002, NFR-004
- **Prioridade**: Alta

### E5. Tratamento de falha de lote
Em caso de falha de lote, reverter a transação e então (a) tentar novamente o lote linha por linha para isolar e
rejeitar a linha ofensiva, ou (b) abortar — selecionado por configuração. Garantir que nenhum lote seja parcialmente confirmado.
- **Requisitos**: FR-009, NFR-003, FR-006
- **Prioridade**: Alta

### E6. Modos de carga
Implementar `append`, `truncate` (esvaziar o destino dentro da fronteira transacional da execução antes de inserir) e
`upsert` (`INSERT ... ON DUPLICATE KEY UPDATE` contra a chave única declarada).
- **Requisitos**: FR-010, FR-015
- **Prioridade**: Média

---

## Grupo F — Orquestração, CLI e Relatórios

### F1. Orquestrador do pipeline (`etl/pipeline.py`)
Conectar extração → blocos → mapeamento → limpeza → coerção → validação → deduplicação → carga como uma cadeia de iteradores preguiçosos; possuir o
ciclo de vida da execução, contadores, propagação de erros e desmontagem final.
- **Requisitos**: FR-001…FR-010, NFR-001, NFR-003
- **Prioridade**: Alta

### F2. CLI (`etl/cli.py`)
Interface baseada em `argparse` aceitando o caminho da config mais sobreposições (arquivo de origem, tabela, tamanho do bloco/lote,
nível de log, `--dry-run`, `--verbose`); texto de ajuda em `pt_BR`; sair com `0` em caso de sucesso e códigos diferentes de zero documentados
para cada classe de falha.
- **Requisitos**: FR-012, FR-011, NFR-007
- **Prioridade**: Alta

### F3. Modo Dry-run
Executar a extração, transformação e validação com o carregador substituído por um no-op que apenas conta, para que nenhuma
gravação no banco de dados ocorra; ainda assim, produzir o relatório de rejeição e o resumo.
- **Requisitos**: FR-012, FR-006
- **Prioridade**: Média

### F4. Relatório de progresso (`etl/reporting.py`)
Manter contadores para linhas lidas / transformadas / carregadas / rejeitadas e emitir uma linha de progresso após cada bloco.
- **Requisitos**: FR-014, FR-013
- **Prioridade**: Média

### F5. Resumo de execução
Na conclusão (sucesso ou falha), imprimir um resumo em `pt_BR`: totais por contador e tempo decorrido.
- **Requisitos**: FR-014, NFR-007
- **Prioridade**: Média

### F6. Gravador de relatório de rejeição
Gravar todos os registros de `Rejection` no arquivo de saída configurado (CSV) com planilha, linha de origem, coluna e motivo.
- **Requisitos**: FR-006, NFR-009
- **Prioridade**: Média

---

## Grupo G — Reinicialização

### G1. Checkpointing (`etl/checkpoint.py`)
Persistir a última posição da linha de origem confirmada após cada commit de lote bem-sucedido.
- **Requisitos**: FR-015
- **Prioridade**: Concluído

### G2. Opção de retomada (Resume)
Uma flag `--resume` que lê o checkpoint e pula as linhas de origem até a posição gravada.
- **Requisitos**: FR-015
- **Prioridade**: Concluído

---

## Grupo J — Carga de Tabelas de Dimensão

### J1. Mapeamento para tabelas de dimensão
Definir mapeamentos de colunas para `tb_beneficiarios`, `tb_especialidades`, `tb_profissionais` e `tb_usuarios` na configuração, garantindo que eles mapeiem para as colunas de origem corretas.
- **Requisitos**: FR-003, FR-016
- **Prioridade**: Alta

### J2. Deduplicação para tabelas de dimensão
Garantir que os dados carregados nas tabelas de dimensão sejam deduplicados com base em suas respectivas chaves primárias para manter a integridade dos dados.
- **Requisitos**: FR-007, FR-016
- **Prioridade**: Alta

### J3. Orquestração de carga multi-tabela
Estender o orquestrador do pipeline para suportar o carregamento de múltiplas tabelas em uma única execução ou sequencialmente, de acordo com a configuração.
- **Requisitos**: FR-016, F1
- **Prioridade**: Alta

---

## Grupo H — Testes e Garantia de Qualidade

### H1. Fixtures de teste
Gerar pequenas fixtures `.xlsx` programaticamente (linhas válidas, tipos incorretos, campos obrigatórios ausentes, chaves duplicadas,
células vazias) mais uma conexão/cursor MySQL falso registrando instruções executadas.
- **Requisitos**: NFR-005
- **Prioridade**: Alta

### H2. Testes unitários por módulo
`../tests/test_config.py`, `../tests/test_extract.py`, `../tests/test_mapping.py`, `../tests/test_cleaning.py`, `../tests/test_types.py`,
`../tests/test_validation.py`, `../tests/test_dedup.py`, `../tests/test_connection.py`, `../tests/test_loader.py`, `../tests/test_reporting.py`,
`../tests/test_cli.py` — cada um cobrindo o caminho feliz e os critérios de falha de seus requisitos.
- **Requisitos**: NFR-005 e o FR que ele cobre
- **Prioridade**: Alta

### H3. Teste de integração com banco de dados falso
End-to-end `../tests/test_pipeline.py` executando uma planilha de fixture através de toda a cadeia contra a conexão falsa,
assegurando contagens de carregados/rejeitados e código de saída.
- **Requisitos**: NFR-005, NFR-003, FR-001…FR-014
- **Prioridade**: Alta

### H4. Verificações de memória e taxa de transferência
Um teste de fixture grande gerado assegurando o crescimento limitado da memória e medindo linhas/minuto contra a
meta NFR-002; marcado como lento/opcional para que a suite padrão permaneça rápida.
- **Requisitos**: NFR-001, NFR-002
- **Prioridade**: Média

### H5. Asserções de segurança
Testes provando que senhas nunca aparecem em logs/mensagens/tracebacks e que todo SQL carregando dados usa
placeholders de parâmetros.
- **Requisitos**: NFR-004
- **Prioridade**: Alta

### H6. Passagem de estilo e docstring
Revisão PEP 8 de todo o pacote e docstrings em todas as funções/classes públicas.
- **Requisitos**: NFR-006
- **Prioridade**: Média

---

## Grupo I — Documentação

### I1. Documentação de uso
Documentar instalação, chaves de configuração, variáveis de ambiente, opções de CLI, códigos de saída e modos de carga.
- **Requisitos**: NFR-008, FR-011, FR-012
- **Prioridade**: Média

### I2. Manter documentos de especificação sincronizados
Atualizar os status de `docs/requirements.md` e os checkboxes de `docs/tasks.md` conforme o trabalho é entregue.
- **Requisitos**: NFR-010
- **Prioridade**: Média

---

## Matriz de Cobertura de Requisitos

| Requisito | Itens do Plano |
|---|---|
| FR-001 | C1, C3, C4, F1, H2 |
| FR-002 | B1, B3, C2, F1 |
| FR-003 | B1, D1, E3, F1, H2, J1 |
| FR-004 | D2, F1, H2 |
| FR-005 | D3, D4, F1, H2 |
| FR-006 | B1, D4, D5, E5, F3, F6, H2 |
| FR-007 | B1, D6, H2, J2 |
| FR-008 | A4, B1, E1, E2, H2 |
| FR-009 | B1, B3, E4, E5, H2 |
| FR-010 | B1, E3, E6, H2 |
| FR-011 | A4, B1, B2, B3, F2, I1 |
| FR-012 | A1, A4, F2, F3, I1 |
| FR-013 | A5, B1, F4 |
| FR-014 | A3, F4, F5 |
| FR-015 | E6, G1, G2 |
| FR-016 | J1, J2, J3 |
| NFR-001 | C1, C2, D6, F1, H4 |
| NFR-002 | E4, H4 |
| NFR-003 | B3, E2, E3, E5, F1, H3, J2 |
| NFR-004 | A5, B2, E1, E4, H5 |
| NFR-005 | E1, H1, H2, H3 |
| NFR-006 | A1, A4, H6 |
| NFR-007 | A3, A4, C3, F2, F5 |
| NFR-008 | A1, A2, I1 |
| NFR-009 | C1, D4, F6 |
| NFR-010 | I2 |

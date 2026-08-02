# Documento de Requisitos

## Introdução

Este documento define os requisitos de alto nível para um **pipeline de ETL de Big Data** cujo propósito é
extrair dados de grandes arquivos de planilha Excel, transformar/validar esses dados e carregá-los em um
banco de dados relacional MySQL.

O escopo é derivado de `docs/vision.md` e das convenções do projeto em `.junie/AGENTS.md`.

Funcionalidades principais:

- **Extrair**: ler pastas de trabalho `.xlsx`/`.xls` muito grandes sem esgotar a memória, usando leituras em fluxo/blocos (streaming/chunked).
- **Transformar**: normalizar, limpar, converter tipos (type-cast), validar e mapear colunas da planilha para o esquema de destino.
- **Carregar**: gravar registros no MySQL em lotes, de forma transacional, com suporte a reinício/idempotência.
- **Operar**: configuração, logging, relatório de erros (mensagens em `pt_BR`), feedback de progresso e um ponto de entrada CLI.

Convenções que restringem estes requisitos:

- Python 3, executado via `python3 main.py`.
- Testes usam o framework integrado `unittest` (`python3 -m unittest discover`), arquivos nomeados `test_<funcionalidade>.py`.
- O estilo de código segue a PEP 8.
- Strings voltadas para o usuário e mensagens de erro seguem por padrão o Português (`pt_BR`); strings técnicas (identificadores,
  nomes de níveis de log, SQL, nomes de classes de exceção) permanecem em Inglês (`en_US`).

Legenda de status: **Não Iniciado**, **Em Andamento**, **Concluído**, **Adiado**.

---

## Requisitos Funcionais

### FR-001 — Extração de arquivos Excel

> **História de Usuário**
> Como um usuário, quero apontar o pipeline para um arquivo Excel para que suas linhas sejam lidas no pipeline
> sem que eu precise escrever nenhum código de processamento (parsing).

**Critérios de Aceitação**

> QUANDO um caminho de arquivo `.xlsx` ou `.xls` válido for fornecido ENTÃO o sistema DEVE abrir a pasta de trabalho e expor suas linhas ao pipeline.
> QUANDO o caminho fornecido não existir ou não for uma planilha legível ENTÃO o sistema DEVE abortar com uma mensagem de erro clara em `pt_BR` e um código de saída diferente de zero.
> QUANDO a pasta de trabalho contiver várias planilhas ENTÃO o sistema DEVE ler a planilha nomeada na configuração, usando como padrão a primeira planilha quando nenhuma for nomeada.
> QUANDO a primeira linha for uma linha de cabeçalho ENTÃO o sistema DEVE usá-la para derivar os nomes das colunas.

- **Prioridade**: Alta
- **Status**: Concluído

### FR-002 — Leitura em fluxo / blocos de arquivos grandes

> **História de Usuário**
> Como um usuário, quero que arquivos com milhões de linhas sejam processados em blocos para que o pipeline não
> esgote a memória da máquina.

**Critérios de Aceitação**

> QUANDO uma pasta de trabalho maior que a memória disponível for processada ENTÃO o sistema DEVE lê-la em modo somente leitura/streaming e nunca materializar todas as linhas de uma vez.
> QUANDO um tamanho de bloco (chunk size) for configurado ENTÃO o sistema DEVE emitir lotes de, no máximo, esse número de linhas.
> QUANDO nenhum tamanho de bloco for configurado ENTÃO o sistema DEVE aplicar um tamanho de bloco padrão documentado.

- **Prioridade**: Alta
- **Status**: Concluído

### FR-003 — Mapeamento de colunas para o esquema de destino

> **História de Usuário**
> Como um usuário, quero declarar como as colunas da planilha se mapeiam para as colunas do banco de dados para que eu possa carregar arquivos
> cujos cabeçalhos não coincidam com a minha tabela.

**Critérios de Aceitação**

> QUANDO um mapeamento entre a coluna de origem e a coluna de destino for declarado na configuração ENTÃO o sistema DEVE aplicá-lo a cada linha extraída.
> QUANDO uma coluna de origem mapeada estiver ausente na pasta de trabalho ENTÃO o sistema DEVE abortar antes do carregamento e relatar a coluna ausente em `pt_BR`.
> QUANDO uma coluna de origem não estiver presente no mapeamento ENTÃO o sistema DEVE ignorar essa coluna.

- **Prioridade**: Alta
- **Status**: Concluído

### FR-004 — Limpeza e normalização de dados

> **História de Usuário**
> Como um usuário, quero que os valores brutos da planilha sejam limpos automaticamente para que entradas inconsistentes não
> corrompam o banco de dados.

**Critérios de Aceitação**

> QUANDO um valor de texto tiver espaços em branco no início ou no fim ENTÃO o sistema DEVE removê-los (trim).
> QUANDO uma célula estiver vazia ou contiver apenas espaços em branco ENTÃO o sistema DEVE convertê-la para `NULL`.
> QUANDO uma regra de normalização (ex: maiúsculas, remover pontuação) for configurada para uma coluna ENTÃO o sistema DEVE aplicá-la apenas a essa coluna.

- **Prioridade**: Alta
- **Status**: Concluído

### FR-005 — Conversão de tipos

> **História de Usuário**
> Como um usuário, quero que os valores da planilha sejam convertidos para os tipos de destino declarados para que o MySQL receba
> dados bem tipados.

**Critérios de Aceitação**

> QUANDO uma coluna for declarada como inteiro, decimal, data, data e hora (datetime) ou booleano ENTÃO o sistema DEVE converter cada valor para esse tipo Python antes do carregamento.
> QUANDO um valor não puder ser convertido para o tipo declarado ENTÃO o sistema DEVE rejeitar essa linha como inválida e continuar processando as linhas restantes.
> QUANDO uma data for armazenada como um número de série do Excel ENTÃO o sistema DEVE convertê-la em um valor de data adequado.

- **Prioridade**: Alta
- **Status**: Concluído

### FR-006 — Validação de linha e tratamento de rejeição

> **História de Usuário**
> Como um usuário, quero que as linhas inválidas sejam isoladas em vez de abortar a execução para que alguns registros ruins não
> bloqueiem todo o carregamento.

**Critérios de Aceitação**

> QUANDO uma linha violar uma regra de validação (campo obrigatório ausente, tipo incorreto, valor fora do intervalo) ENTÃO o sistema NÃO DEVE carregar essa linha e DEVE registrá-la em um relatório de rejeição com o número da linha de origem e o motivo em `pt_BR`.
> QUANDO a execução terminar ENTÃO o sistema DEVE gravar o relatório de rejeição em um arquivo de saída configurável.
> QUANDO o número de linhas rejeitadas exceder um limite configurado ENTÃO o sistema DEVE abortar a execução e relatar a violação do limite.

- **Prioridade**: Alta
- **Status**: Concluído

### FR-007 — Deduplicação

> **História de Usuário**
> Como um usuário, quero que registros duplicados sejam detectados para que o banco de dados não seja poluído por linhas repetidas.

**Critérios de Aceitação**

> QUANDO uma chave de negócio for configurada ENTÃO o sistema DEVE detectar linhas que repetem uma chave já vista na mesma execução e DEVE descartá-las ou relatá-las de acordo com a configuração.
> QUANDO nenhuma chave de negócio for configurada ENTÃO o sistema DEVE carregar todas as linhas válidas inalteradas.

- **Prioridade**: Média
- **Status**: Concluído

### FR-008 — Gerenciamento de conexão MySQL

> **História de Usuário**
> Como um usuário, quero que o pipeline se conecte à minha instância MySQL usando credenciais configuradas para que eu não
> precise codificá-las rigidamente (hardcode).

**Critérios de Aceitação**

> QUANDO host, porta, banco de dados, usuário e senha forem fornecidos pela configuração ENTÃO o sistema DEVE estabelecer uma conexão MySQL usando-os.
> QUANDO a conexão não puder ser estabelecida ENTÃO o sistema DEVE abortar com uma mensagem de erro em `pt_BR` e um código de saída diferente de zero, sem imprimir a senha.
> QUANDO a conexão cair no meio da execução ENTÃO o sistema DEVE tentar novamente um número configurável de vezes com backoff antes de falhar.

- **Prioridade**: Alta
- **Status**: Concluído

### FR-009 — Carregamento em lote no MySQL

> **História de Usuário**
> Como um usuário, quero que as linhas sejam gravadas em lotes para que o carregamento de milhões de registros seja concluído em um tempo razoável.

**Critérios de Aceitação**

> QUANDO as linhas válidas estiverem prontas ENTÃO o sistema DEVE inseri-las usando uma instrução de lote multi-linha/executemany de tamanho configurável.
> QUANDO um lote for inserido com sucesso ENTÃO o sistema DEVE confirmar (commit) esse lote.
> QUANDO uma inserção de lote falhar ENTÃO o sistema DEVE reverter (roll back) esse lote, relatar a falha e tentar novamente linha por linha para isolar a linha ofensiva ou abortar, de acordo com a configuração.

- **Prioridade**: Alta
- **Status**: Concluído

### FR-010 — Preparação da tabela de destino e modo de carga

> **História de Usuário**
> Como um usuário, quero escolher como a tabela de destino é preenchida para que eu possa fazer recargas totais ou cargas incrementais.

**Critérios de Aceitação**

> QUANDO o modo de carga for `append` ENTÃO o sistema DEVE inserir linhas deixando os dados existentes intocados.
> QUANDO o modo de carga for `truncate` ENTÃO o sistema DEVE esvaziar a tabela de destino antes de inserir.
> QUANDO o modo de carga for `upsert` e uma chave única existir ENTÃO o sistema DEVE atualizar as linhas existentes e inserir as novas.
> QUANDO a tabela de destino não existir ENTÃO o sistema DEVE abortar com um erro em `pt_BR` nomeando a tabela ausente.

- **Prioridade**: Média
- **Status**: Concluído

### FR-011 — Configuração

> **História de Usuário**
> Como um usuário, quero todas as configurações do pipeline em uma única fonte de configuração para que eu possa executar diferentes cargas
> sem alterar o código.

**Critérios de Aceitação**

> QUANDO um arquivo de configuração for fornecido ENTÃO o sistema DEVE carregar o caminho do arquivo de origem, planilha, mapeamento, tipos, regras de validação, configurações de banco de dados, tamanhos de bloco/lote e modo de carga a partir dele.
> QUANDO uma variável de ambiente substituir um valor de configuração ENTÃO o sistema DEVE preferir a variável de ambiente.
> QUANDO uma chave de configuração obrigatória estiver ausente ou for inválida ENTÃO o sistema DEVE abortar antes de qualquer gravação no banco de dados e relatar qual chave está errada em `pt_BR`.

- **Prioridade**: Alta
- **Status**: Concluído

### FR-012 — Interface de linha de comando (CLI)

> **História de Usuário**
> Como um usuário, quero iniciar o pipeline a partir do terminal para que eu possa executá-lo e automatizá-lo facilmente.

**Critérios de Aceitação**

> QUANDO `python3 main.py` for invocado com a configuração e/ou argumentos de entrada ENTÃO o sistema DEVE executar o ciclo completo de extração–transformação–carga.
> QUANDO `--help` for passado ENTÃO o sistema DEVE imprimir informações de uso em `pt_BR`.
> QUANDO uma flag `--dry-run` for passada ENTÃO o sistema DEVE executar a extração, transformação e validação, mas não realizar gravações no banco de dados.
> QUANDO a execução for concluída com sucesso ENTÃO o sistema DEVE sair com o código `0`, caso contrário, com um código diferente de zero.

- **Prioridade**: Alta
- **Status**: Concluído

### FR-013 — Logging

> **História de Usuário**
> Como um usuário, quero que o pipeline registre (log) o que está fazendo para que eu possa diagnosticar problemas após o fato.

**Critérios de Aceitação**

> QUANDO o pipeline for executado ENTÃO o sistema DEVE registrar o início, progresso por etapa, avisos, erros e conclusão usando o módulo `logging` padrão.
> QUANDO um nível de verbosidade de log for configurado ENTÃO o sistema DEVE respeitá-lo.
> QUANDO um caminho de arquivo de log for configurado ENTÃO o sistema DEVE gravar os logs nesse arquivo além do console.
> QUANDO credenciais fizerem parte da configuração ENTÃO o sistema NUNCA DEVE gravá-las nos logs.

- **Prioridade**: Alta
- **Status**: Concluído

### FR-014 — Relatórios de progresso e resumo de execução

> **História de Usuário**
> Como um usuário, quero feedback de progresso e um resumo final para saber como está indo uma carga de longa duração
> e como ela terminou.

**Critérios de Aceitação**

> QUANDO um bloco terminar o processamento ENTÃO o sistema DEVE relatar o número de linhas lidas, transformadas, carregadas e rejeitadas até o momento.
> QUANDO a execução terminar ENTÃO o sistema DEVE imprimir um resumo com o total de linhas lidas, carregadas, rejeitadas e o tempo total decorrido, em `pt_BR`.

- **Prioridade**: Média
- **Status**: Concluído

### FR-015 — Reinicialização / idempotência

> **História de Usuário**
> Como um usuário, quero retomar um carregamento interrompido para que eu não precise reprocessar um arquivo enorme inteiro.

**Critérios de Aceitação**

> QUANDO uma execução for interrompida após a confirmação (commit) de N lotes ENTÃO o sistema DEVE registrar a última posição da linha de origem confirmada.
> QUANDO a mesma execução for reiniciada com uma opção de retomada (resume) ENTÃO o sistema DEVE reiniciar a partir da posição registrada em vez do início.
> QUANDO o mesmo arquivo for totalmente recarregado no modo `upsert` ENTÃO o sistema NÃO DEVE criar linhas duplicadas.

- **Prioridade**: Baixa
- **Status**: Concluído

### FR-016 — Carregamento de tabelas de dimensão relacionadas

> **História de Usuário**
> Como um usuário, quero que o pipeline preencha as tabelas de dimensão relacionadas (beneficiários, especialidades, profissionais e usuários) a partir do mesmo arquivo de origem para que eu tenha um banco de dados normalizado para análise.

**Critérios de Aceitação**

> QUANDO o pipeline for executado ENTÃO o sistema DEVE ser capaz de extrair e carregar dados em `tb_beneficiarios`, `tb_especialidades`, `tb_profissionais` e `tb_usuarios` de acordo com seus respectivos mapeamentos.
> QUANDO carregar tabelas de dimensão ENTÃO o sistema DEVE realizar a deduplicação baseada em suas respectivas chaves primárias.
> QUANDO um carregamento de tabela de dimensão falhar ENTÃO o sistema DEVE relatar o erro e tratá-lo de acordo com a configuração `on_batch_error`.

- **Prioridade**: Alta
- **Status**: Concluído

---

## Requisitos Não Funcionais

### NFR-001 — Eficiência de memória

> **História de Usuário**
> Como um usuário, quero que o uso de memória permaneça limitado, independentemente do tamanho do arquivo, para que o pipeline seja executado em
> hardware comum.

**Critérios de Aceitação**

> QUANDO um arquivo de qualquer tamanho suportado for processado ENTÃO o sistema DEVE manter a memória residente proporcional ao tamanho do bloco e não à contagem total de linhas.

- **Prioridade**: Alta
- **Status**: Concluído

### NFR-002 — Taxa de transferência (Throughput)

> **História de Usuário**
> Como um usuário, quero que a carga seja rápida para que arquivos grandes terminem em uma janela aceitável.

**Critérios de Aceitação**

> QUANDO carregar um conjunto de dados bem formado em hardware de referência ENTÃO o sistema DEVE sustentar pelo menos 10.000 linhas por minuto de ponta a ponta.
> QUANDO o tamanho do lote for aumentado dentro dos limites configurados ENTÃO o sistema NÃO DEVE degradar a taxa de transferência.

- **Prioridade**: Média
- **Status**: Concluído

### NFR-003 — Confiabilidade e integridade dos dados

> **História de Usuário**
> Como um usuário, quero que as falhas deixem o banco de dados em um estado consistente para que eu possa confiar em cargas parciais.

**Critérios de Aceitação**

> QUANDO um lote falhar ENTÃO o sistema DEVE garantir que nenhum lote parcialmente aplicado permaneça confirmado.
> QUANDO o pipeline relatar N linhas carregadas ENTÃO a tabela de destino DEVE conter exatamente N linhas novas/atualizadas para essa execução.

- **Prioridade**: Alta
- **Status**: Concluído

### NFR-004 — Segurança de credenciais

> **História de Usuário**
> Como um usuário, quero que as credenciais do banco de dados sejam tratadas com segurança para que não sejam vazadas.

**Critérios de Aceitação**

> QUANDO credenciais forem fornecidas ENTÃO o sistema DEVE aceitá-las via variáveis de ambiente ou um arquivo de configuração não versionado.
> QUANDO qualquer log, mensagem de erro, traceback ou resumo for produzido ENTÃO o sistema DEVE redigir a senha.
> QUANDO SQL for executado ENTÃO o sistema DEVE usar apenas instruções parametrizadas, nunca interpolação de strings de valores de dados.

- **Prioridade**: Alta
- **Status**: Concluído

### NFR-005 — Testabilidade e cobertura de testes

> **História de Usuário**
> Como um desenvolvedor, quero o pipeline coberto por testes automatizados para que alterações não o quebrem silenciosamente.

**Critérios de Aceitação**

> QUANDO `python3 -m unittest discover` for executado a partir da raiz do projeto ENTÃO o sistema DEVE executar todos os testes e relatar sucesso ou falha.
> QUANDO uma nova funcionalidade for adicionada ENTÃO ela DEVE ser acompanhada por um módulo de teste `test_<funcionalidade>.py`.
> QUANDO os testes unitários forem executados ENTÃO eles NÃO DEVEM exigir um servidor MySQL ativo, usando fakes/mocks em seu lugar.

- **Prioridade**: Alta
- **Status**: Concluído

### NFR-006 — Manutenibilidade e estilo de código

> **História de Usuário**
> Como um desenvolvedor, quero uma base de código modular e limpa para que as preocupações de extração, transformação e carga possam evoluir
> independentemente.

**Critérios de Aceitação**

> QUANDO o código for escrito ENTÃO ele DEVE seguir a PEP 8 e separar extração, transformação, carga, configuração e CLI em módulos distintos.
> QUANDO uma função ou classe pública for adicionada ENTÃO ela DEVE conter uma docstring.

- **Prioridade**: Alta
- **Status**: Concluído

### NFR-007 — Internacionalização de mensagens

> **História de Usuário**
> Como um usuário brasileiro, quero mensagens em Português para que a ferramenta seja compreensível para minha equipe.

**Critérios de Aceitação**

> QUANDO uma mensagem voltada ao usuário ou erro for emitida ENTÃO o sistema DEVE renderizá-la em `pt_BR`.
> QUANDO uma string técnica (SQL, identificador, classe de exceção, nível de log) for emitida ENTÃO o sistema DEVE mantê-la em `en_US`.
> QUANDO uma mensagem for definida ENTÃO ela DEVE viver em um catálogo de mensagens central em vez de estar espalhada como literais no código.

- **Prioridade**: Média
- **Status**: Concluído

### NFR-008 — Portabilidade e dependências

> **História de Usuário**
> Como um usuário, quero um conjunto de dependências simples e documentado para que a instalação seja direta.

**Critérios de Aceitação**

> QUANDO o projeto for instalado ENTÃO suas dependências de terceiros DEVEM ser declaradas em um `requirements.txt`.
> QUANDO a aplicação for iniciada ENTÃO ela DEVE ser executada em Python 3 via `python3 main.py` sem etapa de build.

- **Prioridade**: Média
- **Status**: Concluído

### NFR-009 — Observabilidade de falhas

> **História de Usuário**
> Como um usuário, quero que as falhas sejam rastreáveis a uma linha de origem específica para que eu possa corrigir a planilha.

**Critérios de Aceitação**

> QUANDO uma linha for rejeitada ou um lote falhar ENTÃO o sistema DEVE relatar o nome da planilha de origem e o número da linha de origem.

- **Prioridade**: Média
- **Status**: Concluído

### NFR-010 — Documentação

> **História de Usuário**
> Como um desenvolvedor, quero que o diretório `docs/` permaneça atualizado para que a especificação coincida com o código.

**Critérios de Aceitação**

> QUANDO um requisito, item de plano ou tarefa mudar ENTÃO `docs/requirements.md`, `docs/plan.md` e `docs/tasks.md` DEVEM ser atualizados na mesma alteração.

- **Prioridade**: Média
- **Status**: Concluído

---

## Resumo de Rastreabilidade

| ID      | Título                                      | Prioridade | Status      |
|---------|---------------------------------------------|------------|-------------|
| FR-001  | Extração de arquivos Excel                  | Alta       | Concluído   |
| FR-002  | Leitura em fluxo / blocos                   | Alta       | Concluído   |
| FR-003  | Mapeamento de colunas                       | Alta       | Concluído   |
| FR-004  | Limpeza e normalização de dados             | Alta       | Concluído   |
| FR-005  | Conversão de tipos                          | Alta       | Concluído   |
| FR-006  | Validação de linha e tratamento de rejeição | Alta       | Concluído   |
| FR-007  | Deduplicação                                | Média      | Concluído   |
| FR-008  | Gerenciamento de conexão MySQL              | Alta       | Concluído   |
| FR-009  | Carregamento em lote no MySQL               | Alta       | Concluído   |
| FR-010  | Preparação da tabela e modo de carga        | Média      | Concluído   |
| FR-011  | Configuração                                | Alta       | Concluído   |
| FR-012  | Interface de linha de comando (CLI)         | Alta       | Concluído   |
| FR-013  | Logging                                     | Alta       | Concluído   |
| FR-014  | Relatórios de progresso e resumo            | Média      | Concluído   |
| FR-015  | Reinicialização / idempotência              | Baixa      | Concluído   |
| FR-016  | Carga de tabelas de dimensão relacionadas   | Alta       | Concluído   |
| NFR-001 | Eficiência de memória                       | Alta       | Concluído   |
| NFR-002 | Taxa de transferência                       | Média      | Concluído   |
| NFR-003 | Confiabilidade e integridade dos dados      | Alta       | Concluído   |
| NFR-004 | Segurança de credenciais                    | Alta       | Concluído   |
| NFR-005 | Testabilidade e cobertura de testes         | Alta       | Concluído   |
| NFR-006 | Manutenibilidade e estilo de código         | Alta       | Concluído   |
| NFR-007 | Internacionalização de mensagens            | Média      | Concluído   |
| NFR-008 | Portability e dependências                  | Média      | Concluído   |
| NFR-009 | Observabilidade de falhas                   | Média      | Concluído   |
| NFR-010 | Documentação                                | Média      | Concluído   |

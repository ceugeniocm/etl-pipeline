# Visão do Projeto

O objetivo do projeto é fornecer um pipeline de ETL (Extração, Transformação e Carga) robusto, modular e orientado por configuração para processar dados de agendamentos médicos em larga escala. Ele extrai informações de planilhas Excel, aplica regras de negócio complexas e normalização de dados, e carrega os resultados em um banco de dados relacional MySQL.

## Objetivos Principais

- **Alto Desempenho**: Processar grandes conjuntos de dados de forma eficiente usando extração em blocos e carga em lote.
- **Qualidade dos Dados**: Garantir a integridade dos dados por meio de validação rigorosa, coerção de tipos e regras de limpeza.
- **Resiliência**: Lidar com falhas de forma graciosa com retentativas de conexão, checkpointing para execução retomada e relatórios de erro detalhados.
- **Flexibilidade**: Permitir fácil adaptação a diferentes esquemas de origem e requisitos de negócio por meio de uma configuração abrangente baseada em JSON.

## Funcionalidades Principais

### 1. Extração
- Suporte para formatos Excel (`.xlsx`, `.xls`) usando `openpyxl` and `xlrd`.
- Leitura em blocos para minimizar o consumo de memória em arquivos grandes.
- Parâmetros de origem configuráveis (nome da planilha, linha de cabeçalho, tamanho do bloco).

### 2. Transformação
- **Mapeamento**: Mapeamento dinâmico de colunas de origem para campos do banco de dados de destino.
- **Normalização**: Funções integradas para limpeza de strings (trim, upper, etc.).
- **Coerção de Tipos**: Conversão estrita para tipos padrão (int, float, decimal, datetime, str).
- **Validação**: Aplicar campos obrigatórios, verificações de intervalo e comprimentos máximos.
- **Deduplicação**: Deduplicação inteligente baseada em chaves de negócio.

### 3. Carga
- **Suporte a Múltiplas Tabelas**: Carga simultânea de tabelas fato (ex: agendamentos) e tabelas dimensão (ex: pacientes, profissionais, especialidades).
- **Modos Flexíveis**: Suporte para estratégias de carga `truncate` (atualização total) e `upsert` (atualizar/inserir).
- **Processamento em Lote**: Tamanhos de lote configuráveis para inserção otimizada no banco de dados.
- **Gerenciamento de Conexão**: Retentativas automáticas e estratégias de backoff para estabilidade do banco de dados.

### 4. Observabilidade e Controle
- **Interface CLI**: Interface de linha de comando poderosa com suporte para sobreposições de configuração e modo dry-run.
- **Logging**: Log estruturado com níveis configuráveis (INFO, DEBUG, etc.).
- **Relatórios**: Geração de estatísticas de execução detalhadas e relatórios de rejeição para dados inválidos.
- **Checkpointing**: Capacidade de retomar trabalhos interrompidos a partir do último bloco bem-sucedido.

## Visão Geral da Arquitetura

O sistema segue um design modular, desacoplando as fases de extração, transformação e carga. O orquestrador `Pipeline` gerencia o ciclo de vida do processo ETL, garantindo a execução preguiçosa e o fluxo de dados consistente através das várias etapas.
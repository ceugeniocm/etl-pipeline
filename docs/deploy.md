# Guia de Deploy

Este documento fornece instruções detalhadas sobre como realizar o deploy do pipeline de ETL em ambientes de produção e desenvolvimento.

## Estratégias de Deploy

### 1. Deploy com Docker (Recomendado)

A forma mais simples e isolada de executar o pipeline é através do Docker.

#### Pré-requisitos
- Docker instalado.
- Docker Compose instalado (para orquestração com banco de dados).

#### Passos para Produção
1. Construa a imagem da aplicação:
   ```bash
   docker build -t etl-pipeline:latest .
   ```
2. Execute o container passando o arquivo de configuração e o arquivo `.env`:
   ```bash
   docker run --env-file .env -v $(pwd)/dados:/app/dados etl-pipeline:latest config.json
   ```

#### Desenvolvimento Local com Docker Compose
O projeto inclui um `docker-compose.yml` que sobe uma instância do MySQL e o pipeline:
```bash
# 1. Copie o exemplo de variáveis de ambiente
cp .env.example .env

# 2. Inicie os serviços
docker-compose up --build
```

### 2. Deploy Manual (Host Direto)

Para rodar diretamente no servidor sem Docker:

#### Pré-requisitos
- Python 3.8 ou superior.
- Banco de dados MySQL acessível.

#### Instalação
1. Clone o repositório no servidor.
2. Crie um ambiente virtual:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure as variáveis de ambiente no arquivo `.env` (baseado em `.env.example`).
5. Execute o pipeline:
   ```bash
   python3 main.py config.json
   ```

## Configuração de Variáveis de Ambiente

O pipeline suporta o carregamento de variáveis de ambiente via arquivo `.env` na raiz do projeto ou variáveis definidas no sistema. As variáveis de ambiente têm precedência sobre os valores no `config.json`.

| Variável | Descrição |
|----------|-----------|
| `ETL_DB_HOST` | Host do banco de dados MySQL. |
| `ETL_DB_PORT` | Porta do banco de dados (padrão 3306). |
| `ETL_DB_NAME` | Nome do banco de dados. |
| `ETL_DB_USER` | Usuário do banco de dados. |
| `ETL_DB_PASSWORD` | Senha do banco de dados. |
| `ETL_SOURCE_PATH` | Caminho para o arquivo Excel de origem. |
| `ETL_LOAD_TABLE` | Tabela de destino no MySQL. |

Consulte `.env.example` para a lista completa.

## Verificação e Monitoramento

### Logs
Por padrão, os logs são enviados para o console. Você pode configurar um arquivo de log via `config.json` ou pela variável `ETL_LOG_FILE`.

### Relatórios de Rejeição
Linhas que falham na validação são gravadas em `rejeicoes.csv` (ou no caminho configurado). Monitore este arquivo para garantir a qualidade dos dados.

### Pontos de Controle (Checkpoints)
O pipeline utiliza um arquivo `checkpoint.json` para permitir a retomada de cargas interrompidas. Em caso de falha, use a opção `--resume` ou defina `ETL_RESUME=true`.

## Considerações de Segurança
- **Segredos**: Nunca versione o arquivo `.env` com senhas reais.
- **Usuário**: O Dockerfile utiliza um usuário não-root (`etluser`) por segurança.
- **Rede**: Garanta que o banco de dados MySQL aceite conexões apenas das sub-redes autorizadas.

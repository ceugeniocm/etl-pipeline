# Use uma imagem base oficial do Python otimizada para tamanho
FROM python:3.11-slim

# Impede que o Python gere arquivos .pyc no container
ENV PYTHONDONTWRITEBYTECODE 1
# Garante que a saída do log seja enviada diretamente para o terminal sem buffer
ENV PYTHONUNBUFFERED 1

# Define o diretório de trabalho no container
WORKDIR /app

# Instala dependências de sistema se necessário (ex: libmariadb-dev para outros drivers)
# Para mysql-connector-python, dependências básicas de sistema costumam bastar.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de dependências
COPY requirements.txt .

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação
COPY . .

# Cria um usuário não-root para rodar a aplicação (segurança)
RUN useradd -m etluser && chown -R etluser /app
USER etluser

# Ponto de entrada padrão
ENTRYPOINT ["python", "main.py"]

# Comando padrão (pode ser sobrescrito)
CMD ["config.json"]

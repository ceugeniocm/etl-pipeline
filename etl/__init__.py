"""Pipeline ETL: extração de planilhas Excel, transformação e carga em MySQL.

Este pacote separa as responsabilidades do pipeline em módulos independentes
(NFR-006):

- :mod:`etl.messages`      catálogo de mensagens em ``pt_BR``.
- :mod:`etl.errors`        hierarquia de exceções e códigos de saída.
- :mod:`etl.config`        carga e validação da configuração.
- :mod:`etl.logging_setup` configuração de log e redação de credenciais.
- :mod:`etl.extract`       leitura em streaming das planilhas.
- :mod:`etl.transform`     mapeamento, limpeza, conversão, validação e dedup.
- :mod:`etl.load`          conexão com o MySQL e carga em lotes.
- :mod:`etl.pipeline`      orquestração das etapas.
- :mod:`etl.reporting`     contadores, progresso e relatórios.
- :mod:`etl.cli`           interface de linha de comando.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"

"""Gerenciamento de pontos de controle para retomada (FR-015, tarefa 66)."""

import json
import logging
import os

logger = logging.getLogger(__name__)


def save_checkpoint(path: str, row_number: int) -> None:
    """Salva o número da última linha processada com sucesso.

    :param path: Caminho do arquivo de checkpoint.
    :param row_number: Número da linha (1-based).
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"last_row": row_number}, f)
    except Exception as err:
        logger.warning("Falha ao salvar checkpoint em '%s': %s", path, err)


def load_checkpoint(path: str) -> int | None:
    """Carrega o número da última linha processada, se existir.

    :param path: Caminho do arquivo de checkpoint.
    :return: Número da linha ou None se o arquivo não existir ou for inválido.
    """
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("last_row")
    except Exception as err:
        logger.warning("Falha ao ler checkpoint em '%s': %s", path, err)
        return None


def delete_checkpoint(path: str) -> None:
    """Remove o arquivo de checkpoint após conclusão bem-sucedida.

    :param path: Caminho do arquivo de checkpoint.
    """
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception as err:
            logger.warning("Falha ao remover checkpoint em '%s': %s", path, err)

"""
src/utils/logger.py
===================
Configuración del sistema de logging.
"""

import logging
import sys


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Crea un logger con formato legible para consola.
    
    Parámetros
    ----------
    name : str
        Nombre del módulo (usar __name__ en cada módulo).
    level : int
        Nivel de logging (logging.DEBUG, INFO, WARNING, ERROR).
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    return logger

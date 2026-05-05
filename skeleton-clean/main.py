"""Точка входу: python main.py"""
import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Налаштовує формат логів."""
    # TODO:
    # 1. logging.basicConfig(level=..., format=..., datefmt=...)
    # 2. приглушити шум: googleapiclient.discovery_cache, urllib3
    raise NotImplementedError


def main() -> int:
    """Головна функція. Повертає exit code: 0 ОК, 1 конфіг, 2 інша помилка."""
    # TODO:
    # 1. from config import settings (після того як settings буде створюватись)
    # 2. setup_logging(settings.log_level)
    # 3. try:
    #      pipeline = CallProcessingPipeline(settings); pipeline.run(); return 0
    #    except ValueError as e: дружнє повідомлення про конфіг, return 1
    #    except Exception: logging.exception, return 2
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())

import logging
import sys

from config import settings
from src.pipeline import CallProcessingPipeline


def setup_logging(level: str = "INFO") -> None:
    """Налаштовує root logger і приглушує шум від сторонніх бібліотек."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    # приглушити шум від бібліотек
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def main() -> int:
    """Точка входу. Повертає exit code: 0=успіх, 1=помилка конфігурації, 2=непередбачена помилка."""
    setup_logging(settings.log_level)
    try:
        pipeline = CallProcessingPipeline(settings)
        pipeline.run()
        return 0
    except ValueError as e:
        print(f"\n❌ Помилка конфігурації:\n{e}\n", file=sys.stderr)
        print("Перевірте .env (зразок — у .env.example)", file=sys.stderr)
        return 1
    except Exception:
        logging.exception("Непередбачена помилка")
        return 2


if __name__ == "__main__":
    sys.exit(main())

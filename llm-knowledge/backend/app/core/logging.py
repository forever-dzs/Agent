import logging
import sys

from app.config.settings import get_settings


def configure_logging() -> None:
    """初始化统一日志配置，便于线上排查。"""
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

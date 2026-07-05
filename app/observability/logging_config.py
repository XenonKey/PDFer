import json
import logging
from datetime import datetime, timezone

# Attributes every LogRecord already has, i.e. NOT something passed via logger.info(..., extra={...}).
_STANDARD_LOG_RECORD_FIELDS = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__)


class JSONFormatter(logging.Formatter):
    """Renders one JSON object per log line, so Promtail/Loki can parse it without regex."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # Surface everything passed via extra={...} (e.g. template_slug, duration_seconds)
        # instead of hardcoding a fixed list of expected keys.
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_FIELDS:
                log_data[key] = value

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [handler]

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

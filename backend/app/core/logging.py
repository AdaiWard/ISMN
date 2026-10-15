import logging
import sys


SENSITIVE_KEYS = {"password", "token", "secret", "community", "private_key"}


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for key in SENSITIVE_KEYS:
            if key in message.lower():
                record.msg = "Sensitive event details were redacted"
                record.args = ()
                break
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


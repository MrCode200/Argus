import logging
from datetime import datetime
from typing import Optional

from rich.text import Text, Style
from textual.widgets import RichLog


def format_log_record(record: logging.LogRecord) -> Text:
    """
    Convert a logging record into a Rich Text object with consistent line styling.

    Args:
        record: The logging record to format

    Returns:
        A Rich Text object with appropriate styling
    """
    # Define styles for different log levels
    styles = {
        'DEBUG': Style(color='cyan'),
        'INFO': Style(color='green'),
        'WARNING': Style(color='yellow', bold=True),
        'ERROR': Style(color='red', bold=True),
        'CRITICAL': Style(color='red', bold=True, reverse=True),
    }

    log_style = styles.get(record.levelname, Style())

    # Format the log line
    timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
    log_line = (
        f"[{timestamp}] "
        f"[{record.levelname} | {record.filename} | "
        f"lineno({record.lineno}) | {record.funcName}()]"
    )

    text = Text()
    text.append(log_line, style=log_style)

    text.append("\nMessage:", style="bold underline")
    text.append(f" {record.getMessage()}")

    # Add exception info if present
    if record.exc_info:
        text.append(f" \n{record.exc_text or ''}", style=Style(color='red'))

    return text.append("\n")


class LogBufferHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.buffer = []

    def emit(self, record: logging.LogRecord) -> None:
        self.buffer.append(record)


class LoggingRichLog(logging.Handler):
    """
    A logging handler that outputs formatted logs to a RichLog widget.

    This handler bridges Python's logging system with Textual's RichLog widget,
    allowing for rich text formatted logs in Textual applications. It formats
    log records with color and style based on the log level and writes them
    to a RichLog instance.

    The handler can be configured with separate arguments for the base logging.Handler
    and the RichLog widget through the constructor parameters.

    Example:
        >>> import logging
        >>> from textual.app import App
        >>> logger = logging.getLogger('my_app')
        >>> app = App()
        >>> handler = LoggingRichLog(
        ...     logger=logger,
        ...     richlog_kwargs={'wrap': True, 'id': 'app-log'},
        ...     handler_kwargs={'level': logging.DEBUG}
        ... )
        >>> def compose(self) -> ComposeResult:
        >>>     yield self.richlog
        >>> # The RichLog widget is available as handler.richlog

    Note:
        The handler automatically adds itself to the provided logger.
        To prevent duplicate logs, ensure you don't add it to the logger elsewhere.
    """

    def __init__(
            self,
            logger: logging.Logger,
            log_buffer: Optional[LogBufferHandler] = None,
            handler_kwargs: Optional[dict] = None,
            richlog_kwargs: Optional[dict] = None):
        """
        Initialize the LoggingRichLog Widget.

        Args:
            logger: Logger instance to attach this handler to
            log_buffer: Optional LogBufferHandler instance to use for log buffering.
                NOTE: The LogBufferHandler instance must already be added to the logger.
            handler_kwargs: Optional dict of arguments for logging.Handler
            richlog_kwargs: Optional dict of arguments for RichLog widget
        """

        if handler_kwargs is None:
            handler_kwargs = {}
        if richlog_kwargs is None:
            richlog_kwargs = {}

        super().__init__(**handler_kwargs)
        self.richlog = RichLog(**richlog_kwargs)
        logger.addHandler(self)

        if log_buffer is not None:
            for record in log_buffer.buffer:
                self.emit(record)

        logger.removeHandler(log_buffer)

    def emit(self, record: logging.LogRecord) -> None:
        formatted = format_log_record(record)
        self.richlog.write(formatted)

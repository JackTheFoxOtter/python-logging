from typing import Any, Union
import logging
import sys
import os


def add_logging_level(level_name : str, level_value : int) -> None:
    """
    Adds a new logging level to the logging module.
    
    To achieve this, it adds a new level name and value,
    before injecting functions into the logger adapter, logger class and logging module itself.
    The added logging level will behave like the default ones.

    Parameters
    ----------
    level_name : str
        Name of new logging level.
        Will be converted into uppercase for the name of the logging level ('ERROR', 'INFO', etc.)
        Will be converted into lowercase for the method of the logging level ('.error("")', '.info("")', etc.)
    level_value : int
        Value of the new logging level. This needs to be a value that isn't already in use. Default values for the logging module are: 
        NOTSET (0) | DEBUG (10) | INFO (20) | WARNING (30) | ERROR (40) | CRITICAL (50)

    Warnings
    --------
    This function doesn't check if the logging level already exists!

    """
    def _for_logging_module(*args, **kwargs):
        kwargs.setdefault('exc_info', False)
        kwargs.setdefault('stack_info', False)
        logging.log(level_value, *args, **kwargs)

    def _for_logger_class(self, msg, *args, **kwargs):
        if self.isEnabledFor(level_value):
            kwargs.setdefault('exc_info', False)
            kwargs.setdefault('stack_info', False)
            self._log(level_value, msg, args, **kwargs)

    def _for_logger_adapter(self, msg, *args, **kwargs):
        self.log(level_value, msg, *args, **kwargs)

    level_name = level_name.upper() # Full uppercase, like INFO or ERROR
    method_name = level_name.lower() # Method name is always lowercase, like .info("") or .error("")

    logging._acquireLock()
    try:
        # Add level and property to logging
        logging.addLevelName(level_value, level_name)
        setattr(logging, level_name, level_value)
        
        # Add method to logging
        _for_logging_module.__name__ = method_name # Update __name__ property
        setattr(logging, method_name, _for_logging_module)
        
        # Add method to logger
        logger_class = logging.getLoggerClass()
        _for_logger_class.__name__ = method_name # Update __name__ property
        setattr(logger_class, method_name, _for_logger_class)
        
        # Add method to adapter
        logger_adapter = logging.LoggerAdapter
        _for_logger_adapter.__name__ = method_name # Update __name__ property
        setattr(logger_adapter, method_name, _for_logger_adapter)
    
    finally:
        logging._releaseLock()


class CustomFormatter(logging.Formatter):
    """
    Custom logging formatter without support for ANSI colour codes.

    Notes
    -----
    Logging format used is 'YYYY-mm-dd HH:MM:SS [<level>] <name>: <message>'
    Will print formatted exception using default formatting underneath the message, 
    prefixing two spaces before each line, with an additional newline at the end.
    If the extra-dictionary is present and contains a 'raw_msg' key with a string value, 
    it will be printed underneath the message formatted similarly to stacktraces,
    also prefixing two spaces before each line, with an additional newline at the end.

    """
    def __init__(self):
        """
        Constructor, calling super constructur of logging.Formatter class,
        passing the custom logging configuration as parameters.

        See Also
        --------
        logging.Formatter.__init__

        """
        super().__init__(
            '%(asctime)s [%(levelname)-8s] %(name)s: %(message)s',
            '%Y-%m-%d %H:%M:%S',
            style='%'
        )

    def format(self, record : logging.LogRecord):
        """
        Overrides format method from logging.Formatter and implements custom formatting logic as
        described in class docstring.

        Parameters
        ----------
        record : logging.LogRecord
            LogRecord instance containing the logging information to format.

        Returns
        -------
        str
            The formatted logging information as text.

        See Also
        --------
        logging.Formatter.format

        """
        exc_text = None
        if record.exc_info:
            exc_text = super().formatException(record.exc_info)
            exc_text = '  ' + '  '.join(exc_text.splitlines(True)) # Indent error text
            exc_text = exc_text + '\n' # Empty line after stacktrace
        
        raw_text = None
        if hasattr(record, 'raw_msg'):
            raw_text = record.raw_msg
            raw_text = '  ' + '  '.join(raw_text.splitlines(True)) # Indent raw text
            raw_text = '\n' + raw_text + '\n' # Empty line after raw text

        original_exc_text = record.exc_text
        original_msg = record.msg
        try:
            if exc_text: record.exc_text = exc_text # Set exc_text property to print formatted stacktrace
            if raw_text: record.msg += raw_text # Append additional raw text
            return super().format(record) # Format modified record state
        
        finally:
            # Restore original record state
            record.exc_text = original_exc_text
            record.msg = original_msg


class CustomColourFormatter(logging.Formatter):
    """
    Custom logging formatter with support for ANSI colour codes.

    Notes
    -----
    Logging format used is 'YYYY-mm-dd HH:MM:SS [<level>] <name>: <message>'
    Will print formatted exception using default formatting underneath the message, 
    prefixing two spaces before each line, with an additional newline at the end.
    If the extra-dictionary is present and contains a 'raw_msg' key with a string value, 
    it will be printed underneath the message formatted similarly to stacktraces,
    also prefixing two spaces before each line, with an additional newline at the end.

    The following ANSI colour codes are used to decorate the elements of the log messages:
        Timestamp and punctuation: '\\x1b[30;2m' (black text, dim)
        Log levels:
            NOTSET   (0) : '\\x1b[30;1m' (black text, bold)
            DEBUG    (10): '\\x1b[35;1m' (magenta text, bold)
            INFO     (20): '\\x1b[37;1m' (white text, bold)
            NOTICE   (25): '\\x1b[32;1m' (green text, bold)
            WARNING  (30): '\\x1b[33;1m' (yellow text, bold)
            ERROR    (40): '\\x1b[31;1m' (red text, bold)
            CRITICAL (50): '\\x1b[41;1m' (red background, bold)
        Logger name:    '\\x1b[34m' (blue text)
        Exception text: '\\x1b[31m' (red text)
        Notice text:    '\\x1b[36m' (cyan text)
        Log message:     default colour / no custom formatting

    ANSI codes are a bit weird to decipher if you're unfamiliar with them, so here's a refresher
    It starts off with a format like \\x1b[###m where ### is a semicolon separated list of commands
    The important ones here relate to colour.
    30-37 are black, red, green, yellow, blue, magenta, cyan and white in that order
    40-47 are the same except for the background
    90-97 are the same but "bright" foreground
    100-107 are the same as the bright ones but for the background.
    1 means bold, 2 means dim, 0 means reset, and 4 means underline.

    References
    ----------
    This class was taken from https://github.com/Rapptz/discord.py/blob/master/discord/utils.py and modified

    """
    def __init__(self):
        """
        Constructor, creating a formatter for each logging level using the specified ANSI colour codes.

        See Also
        --------
        logging.Formatter.__init__

        """
        c_levels = [
            (logging.NOTSET,   '\x1b[30;1m'),
            (logging.DEBUG,    '\x1b[35;1m'),
            (logging.INFO,     '\x1b[37;1m'),
            (logging.NOTICE,   '\x1b[32;1m'), # Custom logging level
            (logging.WARNING,  '\x1b[33;1m'),
            (logging.ERROR,    '\x1b[31;1m'),
            (logging.CRITICAL, '\x1b[41;1m'),
        ]
        c_accent = '\x1b[30;2m'
        c_name   = '\x1b[34m'
        c_reset  = '\x1b[0m'

        self._formatters = {}
        for level, c_level in c_levels:
            self._formatters[level] = logging.Formatter(
                f"{c_accent}%(asctime)s [{c_reset}{c_level}%(levelname)-8s{c_reset}{c_accent}] " \
                    f"{c_reset}{c_name}%(name)s{c_reset}{c_accent}: {c_reset}%(message)s",
                '%Y-%m-%d %H:%M:%S',
                style='%'
            )

    def format(self, record : logging.LogRecord) -> str:
        """
        Overrides format method from logging.Formatter and implements custom formatting logic as
        described in class docstring.

        Parameters
        ----------
        record : logging.LogRecord
            LogRecord instance containing the logging information to format.

        Returns
        -------
        str
            The formatted logging information as text.

        See Also
        --------
        logging.Formatter.format

        """
        formatter = self._formatters.get(record.levelno, self._formatters[logging.DEBUG])
        
        exc_text = None
        if record.exc_info:
            exc_text = formatter.formatException(record.exc_info)
            exc_text = '  ' + '  '.join(exc_text.splitlines(True)) # Indent error text
            exc_text = exc_text + '\n' # Empty line after stacktrace
            exc_text = f'\x1b[31m{exc_text}\x1b[0m' # Add color red
        
        raw_text = None
        if hasattr(record, 'raw_msg'):
            raw_text = record.raw_msg
            raw_text = '  ' + '  '.join(raw_text.splitlines(True)) # Indent raw text
            raw_text = '\n' + raw_text + '\n' # Empty line after raw text
            raw_text = f'\x1b[36m{raw_text}\x1b[0m' # Add color cyan

        original_exc_text = record.exc_text
        original_msg = record.msg
        try:
            if exc_text: record.exc_text = exc_text # Set exc_text property to print formatted stacktrace
            if raw_text: record.msg += raw_text # Append additional raw text

            return formatter.format(record) # Format modified record state
        
        finally:
            # Restore original record state
            record.exc_text = original_exc_text
            record.msg = original_msg


def stream_supports_colour(stream: Any) -> bool:
    """
    Determine if the provided stream supports ANSI color codes.

    Parameters
    ----------
    stream : Any
        The stream the check for color support.

    Returns
    -------
    bool
        Whether or not the stream supports color.

    References
    ----------
    This function was taken from https://github.com/Rapptz/discord.py/blob/master/discord/utils.py

    """
    # Pycharm and Vscode support colour in their inbuilt editors
    if 'PYCHARM_HOSTED' in os.environ or os.environ.get('TERM_PROGRAM') == 'vscode':
        return True

    is_a_tty = hasattr(stream, 'isatty') and stream.isatty()
    if sys.platform != 'win32':
        return is_a_tty

    # ANSICON checks for things like ConEmu
    # WT_SESSION checks if this is Windows Terminal
    return is_a_tty and ('ANSICON' in os.environ or 'WT_SESSION' in os.environ)


def get_handler():
    handler = logging.StreamHandler()
    if stream_supports_colour(handler.stream):
        formatter = CustomColourFormatter()
    else:
        formatter = CustomFormatter()
    handler.setFormatter(formatter)

    return handler


def setup_logging(file_path : Union[str, None] = None, file_log_level : int = logging.INFO) -> None:
    """
    Function to setup logging configuration. Should only be called once at startup.

    Info
    ----
    For root logger, sets up a logging handler with either _CustomColourFormatter as formatter 
    if the logging stream supports ANSI colour codes, or _CustomFormatter if it doesn't.
    Sets the logging level of the root logger to logging.DEFAULT. This is mainly for third-party packages.
    In our own code, we use logger instances returned from get_logger.
    Lastly, adds a callback for sys.excepthook to allow our modified root logger to log
    exceptions on root level using logging.CRITICAL as log level.

    """
    add_logging_level("NOTICE", 25) # Custom logging level. like INFO, but meant to be prominently displayed as a notification

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(get_handler())

    if file_path:
        # Also set up file logger
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(file_log_level)
        file_handler.setFormatter(CustomFormatter())
        root_logger.addHandler(file_handler)

    # Handle uncaught exceptions with logger as well
    def _handle_uncaught_exception(exc_type : Any, exc_value : Any, exc_traceback : Any) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            root_logger.critical("KeyboardInterrupt received.")
        else:
            root_logger.critical("App has encountered an unhandled exception!", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = _handle_uncaught_exception

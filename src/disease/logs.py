"""Configure application logging."""

import logging
import warnings


def initialize_logs(log_level: int = logging.INFO, silent: bool = False) -> None:
    """Configure logging.

    :param log_level: app log level to set
    :param silent: if True, expect all console output to be suppressed.
    """
    logging.basicConfig(
        filename=f"{__package__}.log",
        format="[%(asctime)s] - %(name)s - %(levelname)s : %(message)s",
    )
    logger = logging.getLogger(__package__)
    logger.setLevel(log_level)

    logging.captureWarnings(True)

    if silent:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.getLogger("py.warnings").propagate = False
    else:
        warnings.resetwarnings()
        warnings.simplefilter("default")

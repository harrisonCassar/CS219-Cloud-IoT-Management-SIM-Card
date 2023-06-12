"""Contains various utility/helper functions.

Author:
    Harrison Cassar, March 2023
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)


def setup_logger(log_level='INFO', file_log=None, logger=None):
    """Configures logging module with logging level, as well as logging to
    stdout (and file, if desired, at a specified logging directory)."""

    levels = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG
    }
    level = levels.get(log_level.upper())
    if level is None:
        raise ValueError(f"User-specified log level '{log_level}' invalid; must be one of: {' | '.join(levels.keys())}")

    if file_log:
        # check logging file doesnt already exist as a directory
        if os.path.exists(file_log) and os.path.isdir(file_log):
            raise Exception(f"Specified logging file '{file_log}' already exists as directory.")
        os.makedirs(os.path.dirname(file_log), exist_ok=True)

        console = logging.StreamHandler()
        console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        console.setFormatter(console_formatter)

        logging.basicConfig(
            filename=file_log,
            filemode='w+',
            format='%(asctime)s - %(levelname)s - %(message)s',
            level=level)

        logger.addHandler(console)

    else:
        logging.basicConfig(
            stream=sys.stderr,
            format='%(asctime)s - %(levelname)s - %(message)s',
            level=level)


def add_logging_arguments(parser):
    parser.add_argument(
        '--log',
        dest='log',
        help="Path to file for logging output (instead of only stdout).")
    parser.add_argument(
        '--log-level',
        dest='log_level',
        help="Provide logging level (i.e. DEBUG, INFO, WARNING, etc.). Default: %(default)s",
        default='INFO')

def get_device_nickname_by_id(id):

    id_to_nickname_map = {
        1 : 'imu',
        2 : 'gyro',
        3 : 'temp'
    }

    return id_to_nickname_map.get(id, 'unknown')
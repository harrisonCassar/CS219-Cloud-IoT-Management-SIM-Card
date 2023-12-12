#!/usr/bin/env python3

"""A basic proxy application used to forward UDP traffic from one IP addr/port to another.

Description:
- Utilizes two separate sockets.

Author:
    Harrison Cassar, Fall 2023
"""

import os
import sys
import logging
import argparse
import socket
import time

DEFAULT_SRC_ADDRESS = "127.0.0.1"
DEFAULT_SRC_PORT = 6002
DEFAULT_DEST_ADDRESS = "172.24.62.31"
DEFAULT_DEST_PORT = 6003
MESSAGE_MAX_SIZE = 1024 # Arbitrary max send message size.

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


def main():

    parser = argparse.ArgumentParser(description="Proxy, forwarding UDP traffic from a source to a destination.")
    add_logging_arguments(parser)
    parser.add_argument(
        '--src-address',
        dest='src_address',
        help="IP address of the source of UDP traffic. Default: %(default)s",
        default=DEFAULT_SRC_ADDRESS)
    parser.add_argument(
        '--src-port',
        dest='src_port',
        help="Port of the source of UDP traffic. Default: %(default)s",
        default=DEFAULT_SRC_PORT)
    parser.add_argument(
        '--dest-address',
        dest='dest_address',
        help="IP address to forward the UDP traffic to. Default: %(default)s",
        default=DEFAULT_DEST_ADDRESS)
    parser.add_argument(
        '--dest-port',
        dest='dest_port',
        help="Port to forward the UDP traffic to. Default: %(default)s",
        default=DEFAULT_DEST_PORT)

    args = parser.parse_args()

    src_address = args.src_address
    src_port = args.src_port
    dest_address = args.dest_address
    dest_port = args.dest_port
    log = args.log
    log_level = args.log_level

    setup_logger(log_level=log_level, file_log=log, logger=logger)

    # Setup receiving socket.
    receiving_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    receiving_sock.bind((src_address, src_port))
    receiving_sock.settimeout(0)

    # Setup sending socket.
    sending_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    sending_sock.settimeout(0)

    logger.info(f"Proxy began! Forwarding UDP traffic from ({src_address}, {src_port}) to ({dest_address}, {dest_port})...")

    debug_print = time.time()

    while True:
        try:
            # Receive up to specified number of bytes (if there are any).
            data, addr = receiving_sock.recvfrom(MESSAGE_MAX_SIZE)
        except BlockingIOError: # No data available to receive; Spin...
            if (debug_print + 10 < time.time()):
                logger.debug("Attempted to receive data but no data is available...")
                debug_print = time.time()
            time.sleep(0.1)
            continue

        # Send UDP traffic to destination.
        sending_sock.sendto(data, (dest_address, dest_port))


if __name__ == "__main__":
    sys.exit(main())
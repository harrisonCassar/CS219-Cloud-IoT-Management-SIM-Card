"""Basic 'cloud-based' UDP server that facilitates communication to/from the SIM + Modem client.

Author:
    Harrison Cassar, May 2023
"""

import sys
import logging
import argparse
import socket

from .util import setup_logger, add_logging_arguments

DEFAULT_SERVER_ADDRESS = "127.0.0.1"
DEFAULT_SERVER_PORT = 60001
DEFAULT_MODEM_ADDRESS = "127.0.0.1"
DEFAULT_MODEM_PORT = 60002

num_packets_sent = 0
num_packets_received = 0

logger = logging.getLogger(__name__)


def listen_for_incoming_packets():
    # TODO: Implement
    pass


def handle_incoming_packet():
    # TODO: Implement
    pass


def handle_carrier_switch_request():
    # TODO: Implement
    pass


def main():

    parser = argparse.ArgumentParser(description="Basic 'cloud-based' UDP server that facilitates communication to/from the SIM + Modem client.")
    add_logging_arguments(parser)
    parser.add_argument(
        '--server-address',
        dest='server_address',
        help="IP address to use for server to allow modem (connected to SIM) client to communicate. Default: %(default)s",
        default=DEFAULT_SERVER_ADDRESS)
    parser.add_argument(
        '--server-port',
        dest='server_port',
        type=int,
        help="Port to use for server to allow modem (connected to SIM) client to communicate. Default: %(default)s",
        default=DEFAULT_SERVER_PORT)
    parser.add_argument(
        '--modem-address',
        dest='modem_address',
        help="IP address of modem (connected to SIM) client to communicate with. Default: %(default)s",
        default=DEFAULT_MODEM_ADDRESS)
    parser.add_argument(
        '--modem-port',
        dest='modem_port',
        type=int,
        help="Port of modem (connected to SIM) client to communicate with. Default: %(default)s",
        default=DEFAULT_MODEM_PORT)

    args = parser.parse_args()

    server_address = args.server_address
    server_port = args.server_port
    modem_address = args.modem_address
    modem_port = args.modem_port
    log = args.log
    log_level = args.log_level

    setup_logger(log_level=log_level, file_log=log, logger=logger)

    # Setup UDP sending socket.
    with socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM) as sending_socket:

        sending_socket.settimeout(0)
        logger.debug(f"Init sending socket, with plans to send to modem address '{modem_address}' and port '{modem_port}'.")

        # Setup UDP receiving socket.
        with socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM) as receiving_socket:

            receiving_socket.bind((server_address, server_port))
            receiving_socket.settimeout(0)

            logger.debug(f"Init receiving server socket at server address '{server_address}' and port '{server_port}'.")

            logger.debug("Init complete!")

            # Setup threads
            # 1. Listen for + push all incoming UDP packets into (thread-safe) queue
            # 2. Drain queue of 1 UDP packet (if there is one present), decode packet, run handler(s)
            #    - Handlers include:
            #        - For IoT data, push to KafkaProducer + Grafana Live socket
            #        - For N/ACK, update internal state (NEED TO BE THREAD-SAFE...?)
            # 3. KafkaConsumer: listen for "carrier_switch" topic messages, and then send UDP carrier switch to modem client
            #    - send "in-progress" to state Flask endpoint
            #    - spin/block until either ACK is received OR timeout occurs (then perform re-try for X number of times before eventually giving up)
            #    - upon success/failure, send "success/failure" to state Flask endpoint, along with current carrier ID
            # TODO: Implement

            # Start thread executions
            # TODO: Implement


if __name__ == "__main__":
    sys.exit(main())
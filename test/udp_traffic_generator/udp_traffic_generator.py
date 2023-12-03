#!/usr/bin/env python3

"""A basic interactive UDP client capable of 2-way communication. Enables testing of a UDP client/server/user/interface.

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

DEFAULT_LOCAL_ADDRESS = "127.0.0.1"
DEFAULT_LOCAL_PORT = 6001
DEFAULT_REMOTE_ADDRESS = "127.0.0.1"
DEFAULT_REMOTE_PORT = 6002
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


def perform_send(client_socket, remote_addr_port):

    # Take in user input.
    data = input("Enter data to send: ")

    # Validate input.
    if len(data) > MESSAGE_MAX_SIZE:
        logger.error(f"Provided input data larger than max message size of {MESSAGE_MAX_SIZE}.")
        return 0 # 0 bytes sent.

    # Send UDP packet with data.
    data_encoded = str.encode(data)
    client_socket.sendto(data_encoded, remote_addr_port)

    logger.debug(f"SEND: {data}")

    # Notify user of status.
    print("Data sent!")
    print()

    # Return number of bytes sent.
    return len(data)


def perform_send_bytes(client_socket, remote_addr_port):

    # Take in user input.
    raw_hex_str = input("Enter hex bytes to send: ")
    hex_str = raw_hex_str.strip().replace(' ', '')

    data = bytes.fromhex(hex_str)

    # Validate input.
    if len(data) > MESSAGE_MAX_SIZE:
        logger.error(f"Provided input data larger than max message size of {MESSAGE_MAX_SIZE}.")
        return 0 # 0 bytes sent.

    # Send UDP packet with data.
    client_socket.sendto(data, remote_addr_port)

    logger.debug(f"SEND: {data}")

    # Notify user of status.
    print("Data sent!")
    print()

    # Return number of bytes sent.
    return len(data)


def perform_receive(server_socket):

    # Take in user input.
    num_bytes = input("Enter max number of bytes to receive: ")

    # Validate input.
    if not num_bytes.isnumeric():
        logger.error(f"Provided input '{num_bytes}' is not a non-negative integer.")
        return 0 # 0 bytes receieved.

    try:
        # Receive up to specified number of bytes (if there are any).
        raw_data, sender_addr = server_socket.recvfrom(int(num_bytes))
        data = raw_data.decode()
    except BlockingIOError: # No data available to receive.
        logger.warning("Attempted to recieve data but no data is available.")
        print("No data to receive.")
        print()
        return 0 # 0 byes received.

    logger.debug(f"RCV data from {sender_addr}.")
    logger.debug(f"RCV data: {data}")

    # Output to user.
    print(f"Received {len(data)} bytes of data:")
    print(data)
    print()

    # Return number of bytes received.
    return len(data)


def perform_receive_bytes(server_socket):

    # Take in user input.
    num_bytes = input("Enter max number of bytes to receive: ")

    # Validate input.
    if not num_bytes.isnumeric():
        logger.error(f"Provided input '{num_bytes}' is not a non-negative integer.")
        return 0 # 0 bytes receieved.

    try:
        # Receive up to specified number of bytes (if there are any).
        data, sender_addr = server_socket.recvfrom(int(num_bytes))
    except BlockingIOError: # No data available to receive.
        logger.warning("Attempted to recieve data but no data is available.")
        print("No data to receive.")
        print()
        return 0 # 0 byes received.

    logger.debug(f"RCV data from {sender_addr}.")
    logger.debug(f"RCV data: {data}")

    # Output to user.
    print(f"Received {len(data)} bytes of data:")
    print(data)
    print()

    # Return number of bytes received.
    return len(data)


def main():

    parser = argparse.ArgumentParser(description="Interactive UDP client capabale of 2-way communication.")
    add_logging_arguments(parser)
    parser.add_argument(
        '--local-address',
        dest='local_address',
        help="IP address of local user to allow remote users to communicate. Default: %(default)s",
        default=DEFAULT_LOCAL_ADDRESS)
    parser.add_argument(
        '--local-port',
        dest='local_port',
        type=int,
        help="Port of local user to allow remote users to communicate. Default: %(default)s",
        default=DEFAULT_LOCAL_PORT)
    parser.add_argument(
        '--remote-address',
        dest='remote_address',
        help="IP address of remote user/server to communicate with. Default: %(default)s",
        default=DEFAULT_REMOTE_ADDRESS)
    parser.add_argument(
        '--remote-port',
        dest='remote_port',
        type=int,
        help="Port of remote user/server to communicate with. Default: %(default)s",
        default=DEFAULT_REMOTE_PORT)

    args = parser.parse_args()

    local_address = args.local_address
    local_port = args.local_port
    remote_address = args.remote_address
    remote_port = args.remote_port
    log = args.log
    log_level = args.log_level

    setup_logger(log_level=log_level, file_log=log, logger=logger)

    num_bytes_sent = 0
    num_bytes_received = 0

    # Setup UDP client socket.
    with socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM) as client_socket:

        client_socket.settimeout(0)
        logger.debug(f"Init sending client socket, with plans to send to remote address '{remote_address}' and port '{remote_port}'.")

        # Setup UDP server socket.
        with socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM) as server_socket:

            server_socket.bind((local_address, local_port))
            server_socket.settimeout(0)

            logger.debug(f"Init receiving server socket at local address '{local_address}' and port '{local_port}'.")

            logger.debug("Init complete!")

            # Start interactive session.
            while True:

                command = input("Enter Command ('S' for send, 'SB' for send bytes, 'R' for receive, 'RB' for receive bytes, 'I' for info): ")

                # Handle command.
                if (command.upper() == "S"): # Send
                    num_bytes_sent += perform_send(client_socket, (remote_address, remote_port))

                elif (command.upper() == "SB"): # Send Bytes
                    num_bytes_sent += perform_send_bytes(client_socket, (remote_address, remote_port))

                elif (command.upper() == "R"): # Recieve
                    num_bytes_received += perform_receive(server_socket)
                
                elif (command.upper() == "RB"): # Recieve
                    num_bytes_received += perform_receive_bytes(server_socket)

                elif (command.upper() == "I"): # Info
                    print(f"Bytes Sent: {num_bytes_sent}")
                    print(f"Bytes Received: {num_bytes_received}")
                    print()

                elif (command.upper() == "Q"): # Quit
                    print("Session completed.")
                    break

                else: # Invalid command.
                    logger.error(f"Unrecognized/unsupported command '{command}' provided. Please try again.")
                    continue


if __name__ == "__main__":
    sys.exit(main())

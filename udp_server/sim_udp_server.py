"""Basic 'cloud-based' UDP server that facilitates communication to/from the SIM + Modem client.

Author:
    Harrison Cassar, May 2023
"""

import sys
import logging
import argparse
import socket
import time
import threading
import queue

from util import setup_logger, add_logging_arguments
from protocol_headers import decode_modem_packet, ModemPacket_FlowField, IotPacket_TopicField, CarrierSwitchPacket_TopicField

DEFAULT_SERVER_ADDRESS = "127.0.0.1"
DEFAULT_SERVER_PORT = 60001
DEFAULT_MODEM_ADDRESS = "127.0.0.1"
DEFAULT_MODEM_PORT = 60002
MODEM_MESSAGE_RCV_BUF_SIZE = 1024

modem_packets_queue = queue.Queue()
num_packets_sent = 0
num_packets_received = 0

logger = logging.getLogger(__name__)


#######################################################
# Helper Functions
#######################################################

def handle_iot_data_packet(packet):
    # TODO: Implement
    logger.debug("Handling IoT Data Packet...")


def handle_iot_status_packet(packet):
    # TODO: Implement
    logger.debug("Handling IoT Status Packet...")


def handle_carrier_switch_perform_packet(packet):
    # TODO: Implement
    logger.debug("Handling Carrier Switch Perform Packet...")


def handle_carrier_switch_ack_packet(packet):
    # TODO: Implement
    logger.debug("Handling Carrier Switch ACK Packet...")


#######################################################
# Thread Target Functions
#######################################################

def listen_from_modem(receiving_socket):
    '''Listen UDP socket, enqueue packets into Queue'''

    logger.info("'Listen From Modem' thread beginning...")

    global num_packets_received

    while True:

        # Receive up to specified number of bytes (if there are any).
        try:
            raw_data, sender_addr = receiving_socket.recvfrom(MODEM_MESSAGE_RCV_BUF_SIZE)
        except BlockingIOError:
            # No data to receive yet; spin!
            continue

        logger.debug(f"RCV: {len(raw_data)} bytes from sender {sender_addr}")
        num_packets_received += 1

        # Decode received data.
        packet = decode_modem_packet(raw_data)

        logger.debug(f"Decoded packet {type(packet)} from received bytes.")

        # Enqueue into Queue.
        modem_packets_queue.put(packet)


def handle_modem_packet():
    # Dequeue packet, decode, and call (blocking) handler
    logger.info("'Handle Modem Packet' thread beginning...")

    while True:

        # Get next modem packet to handle (blocks if Queue is empty).
        packet = modem_packets_queue.get(block=True)

        if packet.flow == ModemPacket_FlowField.IOT:
            if packet.topic == IotPacket_TopicField.DATA:
                handle_iot_data_packet(packet)
            elif packet.topic == IotPacket_TopicField.STATUS:
                handle_iot_status_packet(packet)
            else:
                logger.error(f"Unsupported IoT Flow Packet with Topic value {packet.topic}.")
                continue
        elif packet.flow == ModemPacket_FlowField.CARRIER_SWITCH:
            if packet.topic == CarrierSwitchPacket_TopicField.PERFORM:
                handle_carrier_switch_perform_packet(packet)
            elif packet.topic == CarrierSwitchPacket_TopicField.ACK:
                handle_carrier_switch_ack_packet(packet)
            else:
                logger.error(f"Unsupported Carrier Switch Flow Packet with Topic value {packet.topic}.")
                continue
        else:
            logger.error(f"Unsupported packet with Flow value {packet.flow}.")
            continue


def listen_and_handle_from_main_server():
    # TODO: Implement
    # KafkaConsumer of messages from main Flask Server, and call respective handler
    logger.info("'Listen and Handle from Main Server' thread beginning...")

    count = 0

    while True:
        time.sleep(5)
        logger.info(f"'Listen and Handle from Main Server' thread iteration {count}...")
        count += 1


#######################################################
# Main Entry Point
#######################################################

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

            logger.debug("Init complete.")

            # Setup threads.
            # 1. Listen for + push all incoming UDP packets into (thread-safe) queue
            # 2. Drain queue of 1 UDP packet (if there is one present), decode packet, run handler(s)
            #    - Handlers include:
            #        - For IoT data, push to KafkaProducer + Grafana Live socket
            #        - For N/ACK, update internal state (NEED TO BE THREAD-SAFE...?)
            # 3. KafkaConsumer: listen for "carrier_switch" topic messages, and then send UDP carrier switch to modem client
            #    - send "in-progress" to state Flask endpoint
            #    - spin/block until either ACK is received OR timeout occurs (then perform re-try for X number of times before eventually giving up)
            #    - upon success/failure, send "success/failure" to state Flask endpoint, along with current carrier ID

            threads = []

            thread_listen_from_modem = threading.Thread(target=listen_from_modem, args=(receiving_socket,), daemon=True)
            threads.append(thread_listen_from_modem)

            thread_handle_modem_packet = threading.Thread(target=handle_modem_packet, daemon=True)
            threads.append(thread_handle_modem_packet)

            thread_listen_and_handle_from_main_server = threading.Thread(target=listen_and_handle_from_main_server, daemon=True)
            threads.append(thread_listen_and_handle_from_main_server)

            # Start thread.
            for t in threads:
                t.start()

            logger.debug("All threads launched.")

            # Wait until all thread executions complete (effectively spin, as threads are daemon).
            for t in threads:
                t.join()


if __name__ == "__main__":
    sys.exit(main())
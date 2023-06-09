"""A basic mock of the Modem client. Enables testing of the UDP server.

Description:
- Utilizes two separate sockets for separate to/from communication data flows.

Authors:
    Harrison Cassar, May 2023
    Albert Stanley, June 2023
"""

import sys
import logging
import argparse
import socket
import time
import threading
import queue
import random
from datetime import datetime
from sim_helpers import SimpleSIMReader, is_open_channel_command, is_receive_data_command, is_send_data_command

from common.util import setup_logger, add_logging_arguments, get_device_nickname_by_id
from common.protocol_headers import decode_packet, ModemPacket_FlowField, IotPacket_TopicField, CarrierSwitchPacket_TopicField, CarrierIdField, CarrierSwitchAck, CarrierSwitchAck_StatusField, IoTData

DEFAULT_SERVER_ADDRESS = "127.0.0.1"
DEFAULT_SERVER_PORT = 6001
DEFAULT_MODEM_ADDRESS = "127.0.0.1"
DEFAULT_MODEM_PORT = 6002
SERVER_MESSAGE_RCV_BUF_SIZE = 1024 # Arbitrary max receive message size.
MODEM_MESSAGE_MAX_SIZE = 1024 # Arbitrary max send message size.
DEFAULT_FAIL_RATE_CARRIER_SWITCH = 3 # For every 2 successes, we get a fail (on the 3rd attempt)

# TODO: Modify sensors and their associated rategroups to reflect more "real-life" scenario.
SENSORS_MOCKED = {
    # Rategroup (Hz) : [(Device ID, Min Data Value, Max Data Value), ...]
    1   : [(1, -16, 16)], # Need to keep at 1Hz, or else Grafana + Kafka cannot keep up due to bottleneck somewhere in upstream of IoT data.
    10  : [],
    100 : []
}

incoming_packets_queue = queue.Queue()
outgoing_packets_queue = queue.Queue()
packets_for_sim = queue.Queue()
ssm = SimpleSIMReader()

num_packets_sent = 0
num_packets_received = 0

# SIM State
logger = logging.getLogger(__name__)


#######################################################
# Helper Functions
#######################################################


def handle_carrier_switch_perform_packet(packet, carrier_switch_fail_rate):
    logger.debug("Handling Carrier Switch Perform Packet...")
    logger.info(f"Received request to Carrier Switch to {packet.carrier_id}.")
    # Make request to carrier switch to SIM
    packets_for_sim.put(packet)
    

def poll_sim():
    while True:
        data,sw = ssm.ins_fetch()
        logger.info(f"Recieved FETCH from SIM: {data}")

        if is_send_data_command(data):
            logger.info("Parsed as SEND DATA proactive command")
        elif is_receive_data_command(data):
            logger.info("Parsed as RECEIVE DATA proactive command")

        time.sleep(0.1)




#######################################################
# Thread Target Functions
#######################################################

def listen_from_server(receiving_socket):
    '''Listen UDP receiving socket from server, enqueue packets into Incoming Queue.'''

    global num_packets_received

    logger.info("'Listen From Server' thread beginning...")

    while True:

        # Receive up to specified number of bytes (if there are any).
        try:
            raw_data, sender_addr = receiving_socket.recvfrom(SERVER_MESSAGE_RCV_BUF_SIZE)
        except BlockingIOError:
            # No data to receive yet; spin!
            continue

        logger.debug(f"RCV: {len(raw_data)} bytes from sender {sender_addr}")
        num_packets_received += 1

        # Decode received data.
        packet = decode_packet(raw_data)

        logger.debug(f"Decoded packet {type(packet)} from received bytes.")

        # Enqueue into Incoming Queue.
        incoming_packets_queue.put(packet)


def handle_server_packets(carrier_switch_fail_rate):
    '''Drain Incoming Queue, and run respective handler depending on packet type.'''

    logger.info("'Handle Server Packets' thread beginning...")

    while True:

        # Get next server packet to handle (blocks if Incoming Queue is empty).
        packet = incoming_packets_queue.get(block=True)

        if packet.flow == ModemPacket_FlowField.IOT:
            logger.warning(f"Did not expect to receive IoT Flow Packet from the server. Ignoring...")
        elif packet.flow == ModemPacket_FlowField.CARRIER_SWITCH:
            if packet.topic == CarrierSwitchPacket_TopicField.PERFORM:
                handle_carrier_switch_perform_packet(packet, carrier_switch_fail_rate)
            elif packet.topic == CarrierSwitchPacket_TopicField.ACK:
                logger.warning(f"Did not expect to receive Carrier Switch ACK Packet from the server. Ignoring...")
            else:
                logger.error(f"Unsupported Carrier Switch Flow Packet with Topic value {packet.topic}.")
                continue
        else:
            logger.error(f"Unsupported packet with Flow value {packet.flow}.")
            continue



def poll_iot_sensors():
    '''"Poll" IoT sensors for data at defined rate (fake, generate according to config), package, and enqueue into Outgoing Queue.'''

    logger.info("'Poll IoT Sensors' thread beginning...")

    # "generate" some fake data according to a pre-defined config with the current timestamp
    # and push it to the outgoing queue.

    def poll_and_enqueue(rategroup):
        '''Helper for polling, packaging, and enqueuing data generated for a mocked IoT device.'''
        for device_id, min_value, max_value in SENSORS_MOCKED.get(rategroup):

            nickname = get_device_nickname_by_id(device_id)
            timestamp = datetime.now()
            data_int = random.randint(min_value, max_value)
            data = data_int.to_bytes(4, 'big', signed=True)

            logger.debug(f"Polled sensor {nickname} with ID {device_id} for data value {data_int}.")

            # pass the polled data to the SIM

            packets_for_sim.put(IoTData(
                # General Modem Packet Fields
                flow=ModemPacket_FlowField.IOT,

                # General IOT Flow Packet Fields
                topic=IotPacket_TopicField.DATA,

                # IOT Data Packet-Specific Fields
                device_id=device_id,
                timestamp=timestamp,
                data_length=len(data),
                data=data
            ))


    cycle = 0

    while True:

        # Wait the minimum cycle duration.
        time.sleep(0.01)
        cycle += 1

        if cycle % 1 == 0: # 100 Hz rategroup
            poll_and_enqueue(100)
        if cycle % 10 == 0: # 10 Hz rategroup
            poll_and_enqueue(10)
        if cycle % 100 == 0: # 1 Hz rategroup
            poll_and_enqueue(1)


def transmit_outgoing_packets(sending_socket, server_addr_port):
    '''Drain Outgoing Queue of packets and send to the server.'''

    global num_packets_sent

    logger.info("'Transmit Outgoing Packets' thread beginning...")

    while True:

        # Get next outgoing packet to send (blocks if Outgoing Queue is empty).
        packet = outgoing_packets_queue.get(block=True)
        packet_bytes = packet.to_bytes()

        # Validate to-be-sent packet.
        if len(packet_bytes) > MODEM_MESSAGE_MAX_SIZE:
            logger.warning(f"Outgoing Packet of Flow {packet.flow} and Topic {packet.topic} larger than max message size of {MODEM_MESSAGE_MAX_SIZE}. Dropping...")
            continue

        # Send UDP packet.
        sending_socket.sendto(packet_bytes, server_addr_port)

        logger.debug(f"SENT: {packet_bytes}")

        # Update stats.
        num_packets_sent += 1


#######################################################
# Main Entry Point
#######################################################

def main():

    parser = argparse.ArgumentParser(description="Basic mock of the 'local' Modem client that communicates with the UDP server.")
    add_logging_arguments(parser)
    parser.add_argument(
        '--modem-address',
        dest='modem_address',
        help="IP address of this Modem (connected to SIM) client to allow server to communicate. Default: %(default)s",
        default=DEFAULT_MODEM_ADDRESS)
    parser.add_argument(
        '--modem-port',
        dest='modem_port',
        type=int,
        help="Port of this Modem (connected to SIM) client to allow server to communicate. Default: %(default)s",
        default=DEFAULT_MODEM_PORT)
    parser.add_argument(
        '--server-address',
        dest='server_address',
        help="IP address of server that modem (connected to SIM) client can communicate with. Default: %(default)s",
        default=DEFAULT_SERVER_ADDRESS)
    parser.add_argument(
        '--server-port',
        dest='server_port',
        type=int,
        help="Port of server that modem (connected to SIM) client can communicate with. Default: %(default)s",
        default=DEFAULT_SERVER_PORT)
    parser.add_argument(
        '--carrier-switch-fail-rate',
        dest='carrier_switch_fail_rate',
        type=int,
        help="Fail rate to mock for performing a carrier switch (given as fail on the Nth packet). Default: %(default)s",
        default=DEFAULT_FAIL_RATE_CARRIER_SWITCH)

    args = parser.parse_args()

    server_address = args.server_address
    server_port = args.server_port
    modem_address = args.modem_address
    modem_port = args.modem_port
    carrier_switch_fail_rate = args.carrier_switch_fail_rate
    log = args.log
    log_level = args.log_level

    setup_logger(log_level=log_level, file_log=log, logger=logger)

    # Setup UDP sending socket.
    with socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM) as sending_socket:

        sending_socket.settimeout(0)
        logger.debug(f"Init sending socket, with plans to send to server address '{server_address}' and port '{server_port}'.")

        # Setup UDP receiving socket.
        with socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM) as receiving_socket:
            print(modem_address, modem_port)
            receiving_socket.bind((modem_address, modem_port))
            receiving_socket.settimeout(0)

            logger.debug(f"Init receiving modem socket at modem address '{modem_address}' and port '{modem_port}'.")

            logger.debug("Init complete.")

            # Setup threads.
            # 1. Listen for + push all incoming UDP packets into (thread-safe) queue
            # 2. Drain incoming queue of 1 UDP packet (if there is one present), decode packet, run handler(s)
            #    - Handlers include:
            #        - For Carrier Switch Perform, perform + ACK
            # 3. Poll IoT sensors for data at a defined rate (depending on the device's assigned rategroup).
            #    - Package UDP packet and enqueue into outgoing queue.
            # 4. Drain outgoing queue of 1 UDP packet (if there is one present) and send to server.

            threads = []

            thread_listen_from_server = threading.Thread(target=listen_from_server, args=(receiving_socket,), daemon=True)
            threads.append(thread_listen_from_server)

            thread_handle_server_packets = threading.Thread(target=handle_server_packets, args=(carrier_switch_fail_rate,), daemon=True)
            threads.append(thread_handle_server_packets)

            thread_poll_iot_sensors = threading.Thread(target=poll_iot_sensors, daemon=True)
            threads.append(thread_poll_iot_sensors)

            thread_transmit_outgoing_packets = threading.Thread(target=transmit_outgoing_packets, args=(sending_socket,(server_address, server_port)), daemon=True)
            threads.append(thread_transmit_outgoing_packets)

            thread_sim_reader = threading.Thread(target=poll_sim, daemon=True)
            threads.append(thread_sim_reader)

            # Start thread.
            for t in threads:
                t.start()

            logger.debug("All threads launched.")

            # Wait until all thread executions complete (effectively spin, as threads are daemon).
            for t in threads:
                t.join()


if __name__ == "__main__":
    sys.exit(main())
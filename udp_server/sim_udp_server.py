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
import json

import requests
from confluent_kafka import Producer, Consumer
from websockets.sync.client import connect

from common.util import setup_logger, add_logging_arguments, get_device_nickname_by_id
from common.protocol_headers import gen_carrier_to_carrier_id_mapping, gen_carrier_id_to_carrier_mapping, decode_packet, ModemPacket_FlowField, IotPacket_TopicField, CarrierSwitchPacket_TopicField, CarrierSwitchPerform, CarrierSwitchAck_StatusField, CarrierIdField

DEFAULT_FLASK_SERVER_ADDRESS = "127.0.0.1"
DEFAULT_FLASK_SERVER_PORT= 8000
DEFAULT_SERVER_ADDRESS = "127.0.0.1"
DEFAULT_SERVER_PORT = 6001
DEFAULT_MODEM_ADDRESS = "127.0.0.1"
DEFAULT_MODEM_PORT = 6002
DEFAULT_KAFKA_ADDRESS = "127.0.0.1"
DEFAULT_KAFKA_PORT = 9092
DEFAULT_STREAMING_ADDRESS = "127.0.0.1"
DEFAULT_STREAMING_PORT = 8002

KAFKA_TOPIC_SERVER_MESSAGES = ['downstream-request']
FLASK_SERVER_ENDPOINT_CARRIER_SWITCH_STATUS = "carrier_switch_status"
MODEM_MESSAGE_RCV_BUF_SIZE = 1024

modem_packets_queue = queue.Queue()
num_packets_sent = 0
num_packets_received = 0

carrier_id_to_carrier_mapping = gen_carrier_id_to_carrier_mapping()
carrier_to_carrier_id_mapping = gen_carrier_to_carrier_id_mapping()

logger = logging.getLogger(__name__)


#######################################################
# Helper Functions
#######################################################

def producer_error_cb(err):
    logger.error(f'{err}')


def handle_producer_event_cb(err, msg):
    if err is not None:
        logger.error(f'{err}')
    else:
        logger.debug(f'Produced message on topic {msg.topic()} with value of {msg.value().decode("utf-8")}')


#######################################################
# Handler Functions
#######################################################

## Modem Packet Handlers

def handle_iot_data_packet(packet, producer, sending_socket, streaming_addr_port):
    '''Handler for IoT Data packets. Pushes data to Kafka, and send data to Grafana through Telegraf.'''

    logger.debug("Handling IoT Data Packet...")

    # TODO: See if we can integrate Grafana visualization as well. Tried, but having issues with Grafana's Kafka data source plugin + Grafana Live with Telegraf.

    # Get nickname for device (this will be the easy way we determine what type of data this is).
    nickname = get_device_nickname_by_id(packet.device_id)

    # Format our data in the way Kafka expects.
    data_dict = {
        'timestamp' : packet.timestamp.isoformat(),
        'data' : int.from_bytes(packet.data, 'big', signed=True)
    }
    msg = json.dumps(data_dict).encode('utf-8')

    # Push to Kafka, so downstream tasks can use!
    producer.poll(0)
    producer.produce(nickname, msg, callback=handle_producer_event_cb)
    producer.flush()

    time.sleep(0.01)


    # Format the data for Grafana input.
    formatted_streaming_data = nickname + ' ' + nickname + '=' + str(float(int.from_bytes(packet.data, 'big', signed=True))) + ' ' + str(int(packet.timestamp.timestamp() * 1000000000))

    logger.debug(formatted_streaming_data)
    logger.debug(streaming_addr_port)
    logger.debug(socket.gethostbyname(streaming_addr_port[0]))

    formatted_streaming_data_bytes = bytes(formatted_streaming_data, 'utf-8')

    logger.debug(type(formatted_streaming_data_bytes))

    # TODO: Setup data source in Grafana for Grafana Live.
    # Refer to:
    # - https://grafana.com/docs/grafana/latest/setup-grafana/set-up-grafana-live/
    # - https://grafana.com/tutorials/build-a-streaming-data-source-plugin/

    # with connect("ws://grafana:3000/api/live/push/cs") as websocket:
    #     websocket.send(formatted_streaming_data_bytes)
    #     msg = websocket.recv()
    #     logger.debug(msg)

    # Send to Grafana.
    sending_socket.sendto(formatted_streaming_data_bytes, streaming_addr_port)


def handle_iot_status_packet(packet):
    # TODO: Implement
    logger.info(f"IoT Status: Device ID ")


def handle_carrier_switch_ack_packet(packet, flask_server_addr_port):
    '''Handler for Carrier Switch ACK packets. Pushes status to Main Flask server endpoint.'''

    logger.debug("Handling Carrier Switch ACK Packet...")

    logger.info(f"Carrier Switch ACK Packet fields: {packet.status}, {carrier_id_to_carrier_mapping.get(packet.carrier_id)}")

    # Setup args.
    url = f'http://{flask_server_addr_port[0]}:{flask_server_addr_port[1]}/{FLASK_SERVER_ENDPOINT_CARRIER_SWITCH_STATUS}'

    status = 'ACK' if packet.status == CarrierSwitchAck_StatusField.ACK else 'NACK'
    carrier = carrier_id_to_carrier_mapping.get(packet.carrier_id, 'Unknown')
    args = {
        'status' : status,
        'carrier' : carrier
    }

    # Send POST request to Flask server to update Carrier Switch status.
    requests.post(url, json=args)


## Downstream Request Handlers

def handle_carrier_switch_perform(sending_socket, modem_addr_port, data_dict):

    logger.debug("Handling Carrier Switch Perform request...")

    # Determine new carrier.
    new_carrier = data_dict.get('metadata') # NOTE: Assume this new carrier is a valid option (validated upstream, and worst case: validated at Modem/SIM).
    new_carrier_id = carrier_to_carrier_id_mapping.get(new_carrier)

    # Make into packet to be sent to Modem.
    packet = CarrierSwitchPerform(
        # General Modem Packet Fields
        flow=ModemPacket_FlowField.CARRIER_SWITCH,

        # General Carrier Switch Flow Packet Fields
        topic=CarrierSwitchPacket_TopicField.PERFORM,

        # Carrier Switch Perform Packet-Specific Fields
        carrier_id=new_carrier_id
    )

    logger.info(f"Received Carrier Switch Perform request to carrier {new_carrier}. Sending to Modem...")

    # Send UDP packet.
    sending_socket.sendto(packet.to_bytes(), modem_addr_port)

    logger.debug(f"SENT: Carrier Switch Perform with New Carrier '{new_carrier}'")


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
        packet = decode_packet(raw_data)

        logger.debug(f"Decoded packet {type(packet)} from received bytes.")

        # Enqueue into Queue.
        modem_packets_queue.put(packet)


def handle_modem_packet(producer, flask_server_addr_port, sending_socket, streaming_addr_port):
    # Dequeue packet, decode, and call (blocking) handler
    logger.info("'Handle Modem Packet' thread beginning...")

    while True:

        # Get next modem packet to handle (blocks if Queue is empty).
        packet = modem_packets_queue.get(block=True)

        if packet.flow == ModemPacket_FlowField.IOT:
            if packet.topic == IotPacket_TopicField.DATA:
                handle_iot_data_packet(packet, producer, sending_socket, streaming_addr_port)
            elif packet.topic == IotPacket_TopicField.STATUS:
                handle_iot_status_packet(packet)
            else:
                logger.error(f"Unsupported IoT Flow Packet with Topic value {packet.topic}.")
                continue
        elif packet.flow == ModemPacket_FlowField.CARRIER_SWITCH:
            if packet.topic == CarrierSwitchPacket_TopicField.PERFORM:
                logger.warning(f"Did not expect to receive Carrier Switch Perform Packet from the Modem. Ignoring...")
            elif packet.topic == CarrierSwitchPacket_TopicField.ACK:
                handle_carrier_switch_ack_packet(packet, flask_server_addr_port)
            else:
                logger.error(f"Unsupported Carrier Switch Flow Packet with Topic value {packet.topic}.")
                continue
        else:
            logger.error(f"Unsupported packet with Flow value {packet.flow}.")
            continue


def listen_and_handle_from_main_server(sending_socket, modem_addr_port, consumer):
    # KafkaConsumer of messages from main Flask Server, and call respective handler
    logger.info("'Listen and Handle from Main Server' thread beginning...")

    while True:
        # Receive from Kafka.
        msg = consumer.poll(1.0) # 1 is the 'timeout': maximum time to block waiting for message, event or callback (default: infinite)

        if msg is None:
            logger.debug("Attempted to get a Downstream Request message from Kafka, but no message was to be found.")
            continue
        elif msg.error():
            logger.error(f'When reading a Downstream Request message from Kafka: {msg.error()}')
            continue

        # Decode message.
        data = msg.value().decode('utf-8')
        logger.info("Received a Downstream Request.")
        logger.debug(f"RCV data: {data}")
        data_dict = json.loads(data)

        # Determine type of request, and handle.
        request_type = data_dict.get('type')

        if request_type == 'carrier-switch-perform':
            handle_carrier_switch_perform(sending_socket, modem_addr_port, data_dict)
        else: # Unsupported or missing
            logger.error(f"Received malformed Downstream Request message: Unsupported or missing 'type' field: '{request_type if request_type else ''}'")
            continue


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
    parser.add_argument(
        '--kafka-address',
        dest='kafka_address',
        help="IP address of Kafka server to communicate with. Default: %(default)s",
        default=DEFAULT_KAFKA_ADDRESS)
    parser.add_argument(
        '--kafka-port',
        dest='kafka_port',
        type=int,
        help="Port of Kafka server to communicate with. Default: %(default)s",
        default=DEFAULT_KAFKA_PORT)
    parser.add_argument(
        '--flask-server-address',
        dest='flask_server_address',
        help="IP address of main Flask server to communicate with. Default: %(default)s",
        default=DEFAULT_FLASK_SERVER_ADDRESS)
    parser.add_argument(
        '--flask-server-port',
        dest='flask_server_port',
        type=int,
        help="Port of main Flask server to communicate with. Default: %(default)s",
        default=DEFAULT_FLASK_SERVER_PORT)
    parser.add_argument(
         '--streaming-address',
        dest='streaming_address',
        help="IP address of streaming instance to send data to for visualization. Default: %(default)s",
        default=DEFAULT_STREAMING_ADDRESS)
    parser.add_argument(
        '--streaming-port',
        dest='streaming_port',
        help="Port of streaming instance to send data to for visualization. Default: %(default)s",
        default=DEFAULT_STREAMING_PORT)

    args = parser.parse_args()

    server_address = args.server_address
    server_port = args.server_port
    modem_address = args.modem_address
    modem_port = args.modem_port
    kafka_address = args.kafka_address
    kafka_port = args.kafka_port
    flask_server_address = args.flask_server_address
    flask_server_port = args.flask_server_port
    streaming_address = args.streaming_address
    streaming_port = args.streaming_port
    log = args.log
    log_level = args.log_level

    setup_logger(log_level=log_level, file_log=log, logger=logger)

    # Setup Kafka Producer and Consumer.
    producer = Producer({
        'bootstrap.servers':f'{kafka_address}:{kafka_port}',
        "error_cb": producer_error_cb
    })

    consumer = Consumer({
        'bootstrap.servers':f'{kafka_address}:{kafka_port}',
        'group.id':'python-consumer',
        'auto.offset.reset':'latest'
    })
    consumer.subscribe(KAFKA_TOPIC_SERVER_MESSAGES)

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
            #        - For IoT data, push to KafkaProducer + Grafana Live socket (through Telegraf for streaming)
            #        - For N/ACK, update internal state (NEED TO BE THREAD-SAFE...?)
            # 3. KafkaConsumer: listen for "carrier_switch" topic messages, and then send UDP carrier switch to modem client
            #    - send "in-progress" to state Flask endpoint
            #    - spin/block until either ACK is received OR timeout occurs (then perform re-try for X number of times before eventually giving up)
            #    - upon success/failure, send "success/failure" to state Flask endpoint, along with current carrier ID

            threads = []

            thread_listen_from_modem = threading.Thread(target=listen_from_modem, args=(receiving_socket,), daemon=True)
            threads.append(thread_listen_from_modem)

            thread_handle_modem_packet = threading.Thread(target=handle_modem_packet, args=(producer, (flask_server_address, flask_server_port), sending_socket, (streaming_address, int(streaming_port))), daemon=True)
            threads.append(thread_handle_modem_packet)

            thread_listen_and_handle_from_main_server = threading.Thread(target=listen_and_handle_from_main_server, args=(sending_socket, (modem_address, modem_port), consumer), daemon=True)
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
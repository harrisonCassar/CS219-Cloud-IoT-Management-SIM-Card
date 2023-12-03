"""Basic 'cloud-based' UDP server that facilitates communication to/from the SIM + Modem client.

Author:
    Harrison Cassar, May 2023
"""

import sys
import logging
import argparse
import socket
import threading
import queue
import json

import requests
from confluent_kafka import Producer, Consumer

from common.util import setup_logger, add_logging_arguments, get_device_nickname_by_id
from common.protocol_headers import gen_carrier_to_carrier_id_mapping, gen_carrier_id_to_carrier_mapping, decode_packet, ModemPacket_FlowField, IotPacket_TopicField, CarrierSwitchPacket_TopicField, CarrierSwitchPerform, CarrierSwitchAck_StatusField, CarrierIdField

# SET HERE
IS_RUNNING_LOCALLY = False

DEFAULT_FLASK_SERVER_ADDRESS = "127.0.0.1"
DEFAULT_FLASK_SERVER_PORT= 8000
DEFAULT_SERVER_ADDRESS = "127.0.0.1"
DEFAULT_SERVER_PORT = 6001
DEFAULT_MODEM_ADDRESS = "127.0.0.1"
if IS_RUNNING_LOCALLY:
    DEFAULT_MODEM_ADDRESS = "gateway.docker.internal"
# DEFAULT_MODEM_ADDRESS = "127.0.0.1"
# Note on DEFAULT_MODEM_ADDRESS
# Assuming our UDP server is working locally?
# Can also try: host.docker.internal if this doesn't work for your machine
# https://docs.docker.com/desktop/networking/#i-want-to-connect-from-a-container-to-a-service-on-the-host
DEFAULT_MODEM_PORT = 6002
DEFAULT_KAFKA_ADDRESS = "127.0.0.1"
DEFAULT_KAFKA_PORT = 9092
DEFAULT_STREAMING_ADDRESS = "127.0.0.1"
DEFAULT_STREAMING_PORT = 8002

KAFKA_TOPIC_SERVER_MESSAGES = ['downstream-request']
KAFKA_TOPIC_CARRIER_SWITCH_ACK = 'carrier-switch-ack'
FLASK_SERVER_ENDPOINT_CARRIER_SWITCH_STATUS = "carrier_switch_status"
GRAFANA_API_KEY = "eyJrIjoiR3FkcGFkYkJwalVjSWxITWt3bGtDTjJxc3ZNM1lwd28iLCJuIjoiYWxiZXJ0X2tleSIsImlkIjoxfQ=="
MODEM_MESSAGE_RCV_BUF_SIZE = 1024

modem_packets_queue = queue.Queue()
num_packets_sent = 0
num_packets_received = 0
modem_address = None
modem_port = None
server_address = None
server_port = None

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
    '''Handler for IoT Data packets. Pushes data to Kafka, and send data to Grafana via Grafana Live.'''

    logger.debug("Handling IoT Data Packet...")

    # When handling IoT Data packets, we essentially push/route data to different places for
    # different purposes as follows:
    #
    # 1. Push to Kafka topic "<nickname>".
    #    This satisfies the requirement of the project, and is the "main" Kafka topic for this
    #    data. We expect, in the standard case, for downstream tasks to consume from/use this
    #    exclusively.
    #
    # 2. Push to Kafka topic "<nickname>-grafana".
    #    This is a special case to allow for the downstream task of visualization in Grafana.
    #    Essentially, there exists a Kafka data source plugin for Grafana that essentially
    #    connects to Kafka, consumes messages from specified topics, and streams that data
    #    live for display with Grafana.
    #    - Plugin: https://grafana.com/grafana/plugins/hamedkarbasi93-kafka-datasource/.
    #
    #    However, this plugin lacks some critical features
    #    that makes the live display not ideal for our purposes, including:
    #    - No support for selection of which data rows (in the Kafka message) to visualize
    #      (and which to simply ignore), instead opting for ALL data rows to visualize. This
    #      wouldn't work for our purposes, as we desire to have a "timestamp" field in our
    #      Kafka messages.
    #    - Only support to have data graphed with timestamp either determined by the message
    #      timestamp (when the Kafka message was pushed to Kafka) or when it was consumed from
    #      Kafka. This will not work for our purposes, as we desire to have the data graphed
    #      at the time that the IoT data was actually collected from the device, which is
    #      represented by the "timestamp" field that we've tagged our data with (in the Kafka
    #      message itself). In practice, we expect that the message timestamp is no more than
    #      a few seconds after the actual data timestamp, however this is fundamentally not ideal.
    #
    #    Therefore, if we want to use this plugin, we'd need to upgrade the plugin for our own
    #    purposes. In the meantime, however, just for a demonstration of functionality, we
    #    create this new Kafka topic that is meant JUST FOR THIS PLUGIN'S USE, stripping the
    #    "timestamp" field from our Kafka message, and having the plugin just graph with the
    #    message timestamp.
    #
    # 3. Stream data directly to Grafana via Grafana Live.
    #    Grafana v8 introduced Grafana Live, a new streaming capability that allows us to push
    #    data to the UI in "near real-time". This is extremely efficient and lightweight (not
    #    needing any plugin and/or assisting backend), and can be achieved by simply performing
    #    an HTTP POST request to a specific URL in a specific format.
    #    - https://grafana.com/docs/grafana/latest/setup-grafana/set-up-grafana-live/
    #    - https://grafana.com/tutorials/build-a-streaming-data-source-plugin/
    #
    #    For our project purposes, this does not need Kafka, and therefore does not satisfy
    #    project requirements. However, we still do this anyway just to demonstrate the
    #    functionality.

    # Get nickname for device (this will be the easy way we determine what type of data this is).
    nickname = get_device_nickname_by_id(packet.device_id)

    # 1. Push to Kafka topic "<nickname>".
    data_dict = {
        'timestamp' : packet.timestamp.isoformat(),
        'data' : int.from_bytes(packet.data, 'big', signed=True)
    }
    msg = json.dumps(data_dict).encode('utf-8')

    producer.poll(0)
    producer.produce(nickname, msg, callback=handle_producer_event_cb)
    producer.flush()
    logger.debug(f"Pushed to Kafka topic '{nickname}'.")

    # 2. Push to Kafka topic "<nickname>-grafana".
    data_dict = {
        f'{nickname}' : int.from_bytes(packet.data, 'big', signed=True)
    }
    msg = json.dumps(data_dict).encode('utf-8')

    producer.poll(0)
    producer.produce(f"{nickname}-grafana", msg, callback=handle_producer_event_cb)
    producer.flush()
    logger.debug(f"Pushed to Kafka topic '{nickname}-grafana'.")

    # 3. Stream data directly to Grafana via Grafana Live
    stream_id = f"cs219"
    url = f"http://{streaming_addr_port[0]}:{streaming_addr_port[1]}/api/live/push/{stream_id}"
    stream_data = f"{nickname} {nickname}={float(int.from_bytes(packet.data, 'big', signed=True))} {int(packet.timestamp.timestamp() * 1000000000)}"
    resp = requests.post(url, data=stream_data, headers={'Authorization' : f'Bearer {GRAFANA_API_KEY}'})
    logger.debug(f"Streamed to Grafana Live for stream '{stream_id}' (response: '{resp}').")


def handle_iot_status_packet(packet):
    # TODO: Implement
    logger.info(f"IoT Status: Device ID ")


def handle_carrier_switch_ack_packet(packet, producer, flask_server_addr_port):
    '''Handler for Carrier Switch ACK packets. Pushes status to Main Flask server endpoint.'''

    logger.debug("Handling Carrier Switch ACK Packet...")

    logger.info(f"Carrier Switch ACK Packet fields: {packet.status}, {carrier_id_to_carrier_mapping.get(packet.carrier_id)}")

    ## Push ACK to Flask endpoint

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

    ## Push ACK to Kafka topic

    data_dict = {
        'status' : status,
        'carrier' : carrier
    }
    msg = json.dumps(data_dict).encode('utf-8')

    producer.poll(0)
    producer.produce(KAFKA_TOPIC_CARRIER_SWITCH_ACK, msg, callback=handle_producer_event_cb)
    producer.flush()
    logger.debug(f"Pushed ACK ({status}, {carrier}) to Kafka topic '{KAFKA_TOPIC_CARRIER_SWITCH_ACK}'.")



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

    logger.info(f"Received Carrier Switch Perform request to carrier {new_carrier}. Sending to Modem at {modem_addr_port}...")

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
    global modem_address, modem_port
    global server_address, server_port

    receiving_socket.bind((server_address, server_port))  # Set it initially to bind to the given hostname:port
    receiving_socket.settimeout(0)
    logger.debug(f"Initialize listening server socket at server address '{server_address}' and port '{server_port}'.")

    while True:

        # Receive up to specified number of bytes (if there are any).
        try:
            raw_data, sender_addr = receiving_socket.recvfrom(MODEM_MESSAGE_RCV_BUF_SIZE)

            if not IS_RUNNING_LOCALLY:# cache the sender_addr as the modem address if we are not running locally
                modem_address, modem_port = sender_addr
                logger.info('Caching host:port {}:{}'.format(modem_address, modem_port))

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
                handle_carrier_switch_ack_packet(packet, producer, flask_server_addr_port)
            else:
                logger.error(f"Unsupported Carrier Switch Flow Packet with Topic value {packet.topic}.")
                continue
        else:
            logger.error(f"Unsupported packet with Flow value {packet.flow}.")
            continue


def listen_and_handle_from_main_server(bidirectional_socket, consumer):
    # KafkaConsumer of messages from main Flask Server, and call respective handler
    logger.info("'Listen and Handle from Main Server' thread beginning...")
    global modem_address, modem_port

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
            logger.info('Performing carrier switch: (modem address, modemp port): ({},{})'.format(modem_address, modem_port))
            handle_carrier_switch_perform(bidirectional_socket, (modem_address, modem_port), data_dict)
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

    global server_address, server_port
    global modem_address, modem_port

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

    # Setup UDP bidirectional socket.
    with socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM) as bidirectional_socket:
        # Setup threads.
        # 1. Listen for + push all incoming UDP packets into (thread-safe) queue
        # 2. Drain queue of 1 UDP packet (if there is one present), decode packet, run handler(s)
        #    - Handlers include:
        #        - For IoT data, push to Kafka topic(s) + Grafana Live
        #        - For N/ACK, update internal state (NEED TO BE THREAD-SAFE...?)
        # 3. KafkaConsumer: listen for "carrier_switch" topic messages, and then send UDP carrier switch to modem client
        #    - send "in-progress" to state Flask endpoint
        #    - spin/block until either ACK is received OR timeout occurs (then perform re-try for X number of times before eventually giving up)
        #    - upon success/failure, send "success/failure" to state Flask endpoint, along with current carrier ID

        threads = []

        thread_listen_from_modem = threading.Thread(target=listen_from_modem, args=(bidirectional_socket,), daemon=True)
        threads.append(thread_listen_from_modem)

        thread_handle_modem_packet = threading.Thread(
            target=handle_modem_packet,
            args=(
                producer,
                (flask_server_address, flask_server_port),
                bidirectional_socket, (streaming_address,
                                       int(streaming_port))),
            daemon=True)
        threads.append(thread_handle_modem_packet)

        thread_listen_and_handle_from_main_server = threading.Thread(
            target=listen_and_handle_from_main_server, args=(bidirectional_socket, consumer), daemon=True)
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
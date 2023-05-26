import sys
import logging
import argparse

from confluent_kafka import Consumer

#from common.util import setup_logger, add_logging_arguments

logger = logging.getLogger(__name__)

DEFAULT_KAFKA_ADDRESS = "127.0.0.1"
DEFAULT_KAFKA_PORT = 9092


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


def perform_receive_kafka(consumer):

    # Receive from Kafka.
    msg = consumer.poll(1.0) # 1 is the 'timeout': maximum time to block waiting for message, event or callback (default: infinite)

    if msg is None:
        logger.warning("Attempted to get message from Kafka, but no message was to be found.")
        return
    elif msg.error():
        logger.error(f'{msg.error()}')
        return

    # Do some downstream task (i.e. output to stdout the user).
    data = msg.value().decode('utf-8')
    logger.info(f"RCV data: {data}")


def main():
    
    parser = argparse.ArgumentParser(description="Interactive UDP client capabale of 2-way communication.")
    add_logging_arguments(parser)
    parser.add_argument(
        '-t', '--topics',
        dest='topics',
        nargs='+',
        help="The Kafka topics to subscribe to. These do not need to have data already present in Kafka. If this option is not provided, then the user will be prompted during run-time.",
        default=[])
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

    args = parser.parse_args()

    topics = args.topics
    kafka_address = args.kafka_address
    kafka_port = args.kafka_port
    log = args.log
    log_level = args.log_level

    setup_logger(log_level=log_level, file_log=log, logger=logger)

    # Get topics if user hasn't provided already
    if topics == []:
        while True:
            topic = input("Specify topic to subscribe to (if no more topics are desired, hit Enter): ")
            if topic == '':
                break
            topics.append(topic)

    # Setup Kafka Consumer.
    consumer = Consumer({
        'bootstrap.servers':f'{kafka_address}:{kafka_port}',
        'group.id':'python-consumer',
        'auto.offset.reset':'latest'
    })

    consumer.subscribe(topics)

    # Consume Kafka messages from subscriptions.
    while True:
        perform_receive_kafka(consumer)
    
    consumer.close()
        
if __name__ == '__main__':
    main()
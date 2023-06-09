"""Header definitions for custom UDP-empowered protocol.

Author:
    Harrison Cassar, May 2023
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum
from datetime import datetime
import logging

import bitstruct
import temporenc

logger = logging.getLogger(__name__)

# TODO: Add unit tests for decoding/parsing helpers.


class ModemPacket_FlowField(IntEnum):
    IOT = 0x00
    CARRIER_SWITCH = 0x01


class IotPacket_TopicField(IntEnum):
    DATA = 0x0
    STATUS = 0x1


class CarrierSwitchPacket_TopicField(IntEnum):
    PERFORM = 0x0
    ACK = 0x1


class IotStatus_StatusField(IntEnum):
    NOMINAL = 0x0
    IDLE = 0x1
    OFF_NOMINAL = 0x2


class CarrierSwitchAck_StatusField(IntEnum):
    ACK = 0x0
    NACK = 0x1


class CarrierIdField(IntEnum):
    ATNT = 0x0
    TMOBILE = 0x1
    VERIZON = 0x2
    INVALID = 0xF


@dataclass
class ModemPacket(ABC):
    """Struct representing shared data fields for all UDP Modem packets."""
    flow: ModemPacket_FlowField

    @abstractmethod
    def to_bytes(self):
        current = bitstruct.pack('>u4p4', self.flow)
        return current


@dataclass
class IoTPacket(ModemPacket, ABC):
    """Struct representing shared data fields for all IoT packets."""
    topic: IotPacket_TopicField

    @abstractmethod
    def to_bytes(self):
        # Get upper packet bytes.
        upper = super().to_bytes()
        # Pack current packet bytes.
        current = bitstruct.pack('>p4u4', self.topic)
        # Combine and return.
        return bytes([upper[0] | current[0]])


@dataclass
class CarrierSwitchPacket(ModemPacket, ABC):
    """Struct representing shared data fields for all CarrierSwitch packets."""
    topic: CarrierSwitchPacket_TopicField

    @abstractmethod
    def to_bytes(self):
        # Get upper packet bytes.
        upper = super().to_bytes()
        # Pack current packet bytes.
        current = bitstruct.pack('>p4u4', self.topic)
        # Combine and return.
        return bytes([upper[0] | current[0]])


@dataclass
class IoTData(IoTPacket):
    device_id: int
    timestamp: datetime
    data_length: int
    data: bytes

    def to_bytes(self):
        # Get upper packet bytes.
        upper = super().to_bytes()
        # Pack current packet bytes.
        timestamp_raw = temporenc.packb(self.timestamp, type='DTS')
        current = bitstruct.pack('>u32r64u8', self.device_id, timestamp_raw, self.data_length)
        # Combine and return.
        return upper + current + self.data


@dataclass
class IoTStatus(IoTPacket):
    status: IotStatus_StatusField

    def to_bytes(self):
        # Get upper packet bytes.
        upper = super().to_bytes()
        # Pack current packet bytes.
        current = bitstruct.pack('>u4p4', self.status)
        # Combine and return.
        return upper + current


@dataclass
class CarrierSwitchPerform(CarrierSwitchPacket):
    carrier_id: CarrierIdField

    def to_bytes(self):
        # Get upper packet bytes.
        upper = super().to_bytes()
        # Pack current packet bytes.
        current = bitstruct.pack('>u4p4', self.carrier_id)
        # Combine and return.
        return upper + current


@dataclass
class CarrierSwitchAck(CarrierSwitchPacket):
    status: CarrierSwitchAck_StatusField
    carrier_id: CarrierIdField

    def to_bytes(self):
        # Get upper packet bytes.
        upper = super().to_bytes()
        # Pack current packet bytes.
        current = bitstruct.pack('>u4u4', self.status, self.carrier_id)
        # Combine and return.
        return upper + current


def parse_iot_data_packet(raw_data):

    # Ensure the provided payload has minimal length.
    assert len(raw_data) >= 13

    # Unpack main header fields.
    device_id, timestamp_raw, data_length = bitstruct.unpack('>u32r64u8', raw_data[:13])

    # Validate and perform additional processing of fields.
    try:
        timestamp = temporenc.unpackb(timestamp_raw).datetime()
    except ValueError:
        logger.error(f"IoT Data Packet's timestamp '{timestamp_raw}' represents an invalid date/time.")
        return None

    if data_length != len(raw_data[13:]):
        logger.error(f"IoT Data Packet's data length ({data_length} bytes) does not reflect the actual length of data provided ({len(raw_data[15:])} bytes).")
        return None

    # Return specific dataclass instance.
    return IoTData(
        # General Modem Packet Fields
        flow=ModemPacket_FlowField.IOT,

        # General IOT Flow Packet Fields
        topic=IotPacket_TopicField.DATA,

        # IOT Data Packet-Specific Fields
        device_id=device_id,
        timestamp=timestamp,
        data_length=data_length,
        data=raw_data[13:]
    )


def parse_iot_status_packet(raw_data):

    # Ensure the provided payload has the correct length.
    assert len(raw_data) == 1

    # Unpack fields.
    status, = bitstruct.unpack('>u4p4', raw_data)

    # Validate and perform additional processing of fields.
    if status not in set(item.value for item in IotStatus_StatusField):
        logger.error(f"IoT Status Packet's status code '{status}' is invalid/unrecognized.")
        return None

    # Return specific dataclass instance.
    return IoTStatus(
        # General Modem Packet Fields
        flow=ModemPacket_FlowField.IOT,

        # General IOT Flow Packet Fields
        topic=IotPacket_TopicField.STATUS,

        # IOT Status Packet-Specific Fields
        status=status
    )


def parse_carrier_switch_perform_packet(raw_data):

    # Ensure the provided payload has the correct length.
    assert len(raw_data) == 1

    # Unpack fields.
    carrier_id, = bitstruct.unpack('>u4p4', raw_data)

    # Validate and perform additional processing of fields.
    if carrier_id not in set(item.value for item in CarrierIdField):
        logger.error(f"Carrier Switch Perform Packet's carrier ID '{carrier_id}' is invalid/unrecognized.")
        return None

    # Return specific dataclass instance.
    return CarrierSwitchPerform(
        # General Modem Packet Fields
        flow=ModemPacket_FlowField.CARRIER_SWITCH,

        # General Carrier Switch Flow Packet Fields
        topic=CarrierSwitchPacket_TopicField.PERFORM,

        # Carrier Switch Perform Packet-Specific Fields
        carrier_id=carrier_id
    )


def parse_carrier_switch_ack_packet(raw_data):

    # Ensure the provided payload has the correct length.
    assert len(raw_data) == 1

    # Unpack fields.
    status, carrier_id = bitstruct.unpack('>u4u4', raw_data)

    # Validate and perform additional processing of fields.
    if status not in set(item.value for item in CarrierSwitchAck_StatusField):
        logger.error(f"Carrier Switch ACK Packet's status code '{status}' is invalid/unrecognized.")
        return None

    if carrier_id not in set(item.value for item in CarrierIdField):
        logger.error(f"Carrier Switch ACK Packet's carrier ID '{carrier_id}' is invalid/unrecognized.")
        return None

    # Return specific dataclass instance.
    return CarrierSwitchAck(
        # General Modem Packet Fields
        flow=ModemPacket_FlowField.CARRIER_SWITCH,

        # General Carrier Switch Flow Packet Fields
        topic=CarrierSwitchPacket_TopicField.ACK,

        # Carrier Switch Perform Packet-Specific Fields
        status=status,
        carrier_id=carrier_id
    )


def decode_packet(raw_data):

    # Ensure the provided data has minimal length.
    assert len(raw_data) >= 1

    # Decode shared Type and Flow fields to know which packet we're working with.
    flow, topic = bitstruct.unpack('>u4u4', raw_data[0:1])

    # Launch respective handler based on specific packet type.
    if flow == ModemPacket_FlowField.IOT:
        if topic == IotPacket_TopicField.DATA:
            return parse_iot_data_packet(raw_data[1:])
        elif topic == IotPacket_TopicField.STATUS:
            return parse_iot_status_packet(raw_data[1:])
        else:
            logger.error(f"Packet's Topic value {topic} is unknown/invalid for the 'IOT' flow.")
            return None
    elif flow == ModemPacket_FlowField.CARRIER_SWITCH:
        if topic == CarrierSwitchPacket_TopicField.PERFORM:
            return parse_carrier_switch_perform_packet(raw_data[1:])
        elif topic == CarrierSwitchPacket_TopicField.ACK:
            return parse_carrier_switch_ack_packet(raw_data[1:])
        else:
            logger.error(f"Packet's Topic value {topic} is unknown/invalid for the 'CARRIER SWITCH' flow.")
            return None
    else:
        logger.error(f"Packet's Flow value {flow} is unknown/invalid.")
        return None


def gen_carrier_to_carrier_id_mapping():
    return {
        'AT&T'          : CarrierIdField.ATNT,
        'T-Mobile'      : CarrierIdField.TMOBILE,
        'Verizon'       : CarrierIdField.VERIZON,
        'Disconnect'    : CarrierIdField.INVALID,
        'Invalid'       : CarrierIdField.INVALID
    }


def gen_carrier_id_to_carrier_mapping():
    return {
        CarrierIdField.ATNT     : 'AT&T',
        CarrierIdField.TMOBILE  : 'T-Mobile',
        CarrierIdField.VERIZON  : 'Verizon',
        CarrierIdField.INVALID  : 'Disconnect',
    }
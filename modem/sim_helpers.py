from sim_reader import SIM_Reader
from common.protocol_headers import decode_packet
"""
Helper functions for working with SIM
"""
def int_to_hex_string(value):
    hex_string = format(value, '02x')
    return hex_string

def is_receive_data_command(command:str):
    return command[0:4].lower() == "D00E".lower()

def is_send_data_command(command:str):
    return command[0:4].lower() == "D029".lower()

def is_open_channel_command(command:str):
    return command[0:4].lower() == "D01E".lower()

def extract_send_data_packet(send_data_command):
    str_rep = send_data_command[30:]
    bytes_rep = bytes.fromhex(str_rep)
    return decode_packet(bytes_rep)

def int_to_hex_string(value):
    hex_string = format(value, '02x')
    return hex_string


class SimpleSIMReader:
    """
    Wrapper around SIMReader provided from eSIM-Loader repository: https://github.com/JinghaoZhao/eSIM-Loader/blob/master/sim_reader.py
    """

    INS_FETCH = "00F3000015"
    INS_TERMINAL_START = "00f40000"
    RESPONSE_TEST = "00f400002281030134000202828103010029140D0A2B435245473A20312C310D0A0D0A4F4B0D0A"

    def __init__(self):
        self.is_connected = False

    def attempt_connection(self):
        # Returns True if setup was successfull
        try:
            self.sr = SIM_Reader()
            self.sr.wait_for_card()
            self.is_connected = True
        except:
            self.is_connected = False

    
    def ins_response_test(self):
        (data, sw), parsed = self.sr.send_apdu_text(SimpleSIMReader.RESPONSE_TEST)
        return data, sw

    def ins_fetch(self):
        (data, sw), parsed = self.sr.send_apdu_text(SimpleSIMReader.INS_FETCH)
        return data, sw
    
    def send_packet(self, packet: str):
        length = int(len(packet) / 2)
        length_str = int_to_hex_string(length)
        command = SimpleSIMReader.INS_TERMINAL_START + length_str + packet
        (data, sw), parsed = self.sr.send_apdu_text(command)
        return data,sw
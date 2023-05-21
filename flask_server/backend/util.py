"""Contains UTIL functions for use by Flask server.

Author:
    Harrison Cassar, March 2023
"""


def send_change_carrier_message(new_carrier):
    # TODO: Implement communication with SIM via UDP server.
    print("Sending message to SIM card...")
    print("Waiting for ACK/NACK from SIM card...")

    # ...

    print("Received ACK from SIM card indicating successful carrier switch!")
    return True
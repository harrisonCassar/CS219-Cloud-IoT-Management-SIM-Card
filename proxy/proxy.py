import socket
import time

# TODO(hcassar): Generalize the IP/addr setting to not be hardcoded.

src_host_ip_addr = ("127.0.0.1", 6002)
dest_host_ip_addr = ("172.24.62.31", 6003) # `modem.py` in WSL: ("172.24.62.31", 6002); srsRAN UE in WSL: ("172.16.0.2", 6002)

receiving_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
sending_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

def main():
    receiving_sock.bind(src_host_ip_addr)
    receiving_sock.settimeout(0)
    sending_sock.settimeout(0)

    print("waiting for data...")

    while True:
        try:
            # Receive up to specified number of bytes (if there are any).
            data, addr = receiving_sock.recvfrom(1024)
        except BlockingIOError: # No data available to receive.
            #print("Attempted to recieve data but no data is available.")
            time.sleep(0.1)
            continue
        print(f"Received data at {src_host_ip_addr} from {addr}: {data.decode('utf-8')}")
        print(f"Sending data to {dest_host_ip_addr}")
        sending_sock.sendto(data, dest_host_ip_addr)

if __name__ == "__main__":
    main()
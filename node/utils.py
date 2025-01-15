import socket
import datetime

used_ports = set()


def init_udp_socket(ip_addr: str, port: int) -> socket.socket:
    """
    Initialize a UDP socket bound to the specified IP address and port.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((ip_addr, port))
    return sock


def remove_socket(sock: socket.socket) -> None:
    """
    Close the specified socket and remove its port from the used_ports set.
    """
    used_ports.remove(sock.getsockname()[1])
    sock.close()


def log(node_id: int, content: str) -> None:
    current_time = datetime.Now().strftime("%H:%M:%S")
    log_content = f"[{current_time}] Node {node_id}: {content}\n"
    print(log_content)

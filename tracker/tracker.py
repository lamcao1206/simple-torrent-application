import socket
from threading import Thread, Lock
from typing import Dict, Tuple
import argparse
import time
import json
import random

BUFFER_SIZE = 1024
REQUEST_TIMEOUT = 5


class Metainfo:
    pass


class Peer:
    def __init__(
        self,
        ip_address: str = None,
        peer_socket: socket.socket = None,
        peer_thread: Thread = None,
        upload_address: str = None,
        peer_listening_port: int = None,
        peer_upload_port: int = None,
        file_info: Dict[str, int] = None,
    ) -> None:
        self.ip_address = ip_address
        self.upload_address = None
        self.peer_socket = peer_socket
        self.peer_thread = peer_thread
        self.file_info = file_info
        self.upload_address = upload_address
        self.peer_listening_port = peer_listening_port
        self.peer_upload_port = peer_upload_port
        self.lock = Lock()

    def close(self):
        try:
            self.peer_socket.send(b"tracker close")
            self.peer_socket.close()
        except Exception as e:
            print(f"Error closing peer connection: {repr(e)}")


class Tracker:
    def __init__(
        self, host: str = "127.0.0.1", port: int = 8000, max_nodes: int = 10
    ) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(max_nodes)

        self.running: bool = True
        self.peers: Dict[str, Peer] = {}
        self.node_serving_thread: Thread = Thread(target=self.node_serve, daemon=True)

    def start(self) -> None:
        self.node_serving_thread.start()
        self.tracker_command_shell()

    def node_serve(self) -> None:
        while self.running:
            try:
                node_socket, node_addr = self.sock.accept()
                node_socket.settimeout(REQUEST_TIMEOUT)
            except Exception as e:
                return

            data: str = node_socket.recv(BUFFER_SIZE).decode()

            if not data:
                print(f"Connection closed by {node_addr}")
                self.remove_peer(node_addr)
                continue

            # Handle handshake from node
            if data == "First Connection":
                node_socket.send(b"ACK")
                # Get peer specific info
                peer_info: list[str] = (
                    node_socket.recv(BUFFER_SIZE).decode().split(" ", 2)
                )

                print(f"Received file info from {node_addr}: {peer_info}")
                peer_thread: Thread = Thread(
                    target=self.handle_node_request,
                    args=[node_socket, node_addr],
                    daemon=True,
                )

                self.peers[node_addr] = Peer(
                    ip_address=node_addr,
                    peer_socket=node_socket,
                    peer_thread=peer_thread,
                    peer_listening_port=int(peer_info[0]),
                    peer_upload_port=int(peer_info[1]),
                    file_info=json.loads(peer_info[2]),
                )
                peer_thread.start()

    def handle_node_request(self, node_socket: socket.socket, node_addr: str) -> None:
        while self.running:
            try:
                with self.peers[node_addr].lock:
                    data = node_socket.recv(BUFFER_SIZE).decode()
                    if not data:
                        self.remove_peer(node_addr)
                        continue

            except Exception as e:
                break
            with self.peers[node_addr].lock:
                node_socket.send(b"Received data!")

    def remove_peer(self, peer_addr: str) -> None:
        self.peers[peer_addr].close()
        self.peers.pop(peer_addr)

    def ping_command_shell(self, IP: str, port: int) -> None:
        node_addr = (IP, port)
        if node_addr in self.peers.keys():
            peer = self.peers[node_addr]
            try:
                with peer.lock:
                    peer.peer_socket.settimeout(REQUEST_TIMEOUT)
                    peer.peer_socket.send(b"PING")
                    start_time = time.time()
                    response = peer.peer_socket.recv(BUFFER_SIZE)
                    end_time = time.time()

                    latency = end_time - start_time
                    print(
                        f"Received from {node_addr}: {response.decode()} ({latency:.5f} secs)"
                    )
            except socket.timeout:
                print(f"Ping to {node_addr} timed out!!!")
            except Exception as e:
                print(f"Failed to ping {node_addr}: {repr(e)}")
            finally:
                peer.peer_socket.settimeout(None)
        else:
            print(f"Node {node_addr} is offline")

    def investigate_command_shell(self, IP: str, port: int) -> None:
        node_addr = (IP, port)
        if node_addr in self.peers.keys():
            peer = self.peers[node_addr]
            try:
                with peer.lock:
                    peer.peer_socket.send(b"INVESTIGATE")
                    response = peer.peer_socket.recv(BUFFER_SIZE)
                    peer_file_list = response.decode().split()
                    peer.files = peer_file_list
                    print(peer_file_list)
            except socket.timeout:
                print(f"Investigation to {node_addr} timed out!!!")
            except Exception as e:
                print(f"Node {node_addr} is offline")
                self.peers.pop(node_addr)
                return
        else:
            print(f"Node {node_addr} is offline")

    def list_command_shell(self) -> None:
        for index, peer_addr in enumerate(self.peers.keys()):
            print(f"- [{index}] {str(peer_addr)}")

    def tracker_command_shell(self) -> None:
        while True:
            sock_name, sock_port = self.sock.getsockname()
            cmd_input = input(f"\n{sock_name}:{sock_port} ~ ")
            cmd_parts = cmd_input.split()
            if not cmd_parts:
                continue

            match cmd_parts[0]:
                case "ping":
                    try:
                        IP, port = cmd_parts[1].split(":")
                        self.ping_command_shell(IP, int(port))
                    except IndexError:
                        print("Usage: ping <IP>:<port>")
                    except ValueError:
                        print("Invalid IP or port format.")
                case "list":
                    self.list_command_shell()
                case "investigate":
                    try:
                        IP, port = cmd_parts[2].split(":")
                        self.investigate_command_shell(IP, int(port))
                    except IndexError:
                        print("Usage: investigate <IP>:<port>")
                    except ValueError:
                        print("Invalid IP or port format.")
                case "exit":
                    break
                case _:
                    print("Unknown command")

    def close(self) -> None:
        self.running = False
        self.sock.close()
        for peer in self.peers.values():
            peer.close()


def cli_parser() -> Tuple[str, int, int]:
    parser = argparse.ArgumentParser(
        prog="Tracker", description="Init the tracker for file system"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Hostname of the tracker (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        default=8000,
        type=int,
        help="Port number of the tracker (default: 8000)",
    )
    parser.add_argument(
        "--max-nodes",
        type=int,
        default=10,
        help="Maximum number of clients (default: 10)",
    )
    args = parser.parse_args()
    return (args.host, args.port, args.max_nodes)


class TrackerUtil:
    @staticmethod
    def update_metainfo(file_info: Dict[str, int]) -> bool:
        # Update metainfo to by in sync with file_info data
        random_bit = random.choice([0, 1])
        print(random_bit)
        pass


def main() -> None:
    host, port, max_nodes = cli_parser()
    tracker = Tracker(host, port, max_nodes)
    try:
        tracker.start()
    except KeyboardInterrupt:
        print("\n[Exception]: Got Interrupt by Ctrl + C")
    except Exception as e:
        print(f"\n[Exception]: {e}")
    finally:
        tracker.close()


if __name__ == "__main__":
    main()

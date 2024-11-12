import socket
from threading import Thread, Lock
from typing import Dict, Tuple
import argparse
import time

BUFFER_SIZE = 1024
REQUEST_TIMEOUT = 5

"""
    ping 127.0.0.1:50082 OK
    investigate 127.0.0.1:50082 OK 
    list OK
    exit OK
"""


class Metainfo:
    pass


class Peer:
    def __init__(
        self,
        ip_address: str = None,
        peer_socket: socket.socket = None,
        peer_thread: Thread = None,
        files: list[str] = None,
        upload_address: str = None,
        metainfo: Metainfo = None,
    ) -> None:
        self.ip_address = ip_address
        self.upload_address = None
        self.peer_socket = peer_socket
        self.peer_thread = peer_thread
        self.files = files
        self.upload_address = upload_address
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
        """
        Starts the node-serving thread for interacting with nodes requests
        and start the tracker command shell loop (main process) for interacting with CLI
        """
        self.node_serving_thread.start()
        self.tracker_command_shell()

    def node_serve(self) -> None:
        """
        Run a loop for accepting incoming connections from nodes
        and handle them.
        """
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
                peer_thread: Thread = Thread(
                    target=self.handle_node_request,
                    args=[node_socket, node_addr],
                    daemon=True,
                )
                self.peers[node_addr] = Peer(
                    ip_address=node_addr,
                    peer_socket=node_socket,
                    peer_thread=peer_thread,
                )
                peer_thread.start()
                node_socket.send(b"ACK")

    def handle_node_request(self, node_socket: socket.socket, node_addr: str) -> None:
        """Handles communication with a single node."""
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

    def fetch_response(self, node_addr: str, file_names: list[str]) -> str:
        pass

    def push_response(self, node_addr: str, staging_file_name: list[str]) -> str:
        pass

    def remove_peer(self, peer_addr: str) -> None:
        """
        Remove a peer with peer_addr from the dictionary of connected peers (self.peers)

        Args:
            peer_addr (str): peer address of the peer to remove in form (IP, port)
        """
        self.peers[peer_addr].close()
        self.peers.pop(peer_addr)

    def ping_command_shell(self, IP: str, port: int) -> None:
        """
        Send a ping message to the peer at IP:Port and
        measure the latency of the response

        Args:
            IP (str): IP address
            port (int): port number
        """
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
        """
        Investigate the node at IP:Port for its local files' information

        Args:
            IP (str): IP address
            port (int): port number
        """
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
        """
        List all the connected peers information
        """
        for index, peer_addr in enumerate(self.peers.keys()):
            print(f"- [{index}] {str(peer_addr)}")

    def tracker_command_shell(self) -> None:
        """
        Command shell loop for the tracker CLI
        """
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
        """
        Close the tracker and all the peer
        """
        self.running = False
        self.sock.close()
        for peer in self.peers.values():
            peer.close()


def parser_magnet_link(file_name: str, file_size: int) -> str:
    pass


def cli_parser() -> Tuple[str, int, int]:
    """
    Parse the command line argumenst for the Tracker CLI

    Returns:
        Tuple[str, int, int]: Tracker's IP address, port number and maximum number of nodes connected to tracker
    """
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

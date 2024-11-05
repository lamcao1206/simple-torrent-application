import socket
from threading import Thread, Lock
from typing import Dict
import argparse
import time


class Peer:
    def __init__(
        self,
        ip_address: str = None,
        peer_socket: socket.socket = None,
        peer_thread: Thread = None,
    ):
        self.ip_address = ip_address
        self.peer_socket = peer_socket
        self.peer_thread = peer_thread
        self.lock = Lock()

    def close(self):
        try:
            with self.lock:
                self.peer_socket.close()
        except Exception as e:
            print(f"Error closing peer connection: {repr(e)}")


class Tracker:
    def __init__(self, host="127.0.0.1", port=8000, max_nodes=10) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(max_nodes)

        self.running = True
        self.peers: Dict[str, Peer] = {}
        self.node_serving_thread = Thread(target=self.node_serve, daemon=True)

    def start(self):
        self.node_serving_thread.start()
        self.tracker_command_shell()

    def node_serve(self) -> None:
        while self.running:
            try:
                node_socket, node_addr = self.sock.accept()
                node_socket.settimeout(5)
            except Exception as e:
                return

            data = node_socket.recv(1028).decode()

            if not data:
                print(f"Connection closed by {node_addr}")
                self.remove_peer(node_addr)
                continue

            # Handle handshake from node
            if data == "First Connection":
                peer_thread = Thread(
                    target=self.handle_node,
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

    def close(self):
        self.running = False
        self.sock.close()
        for peer in self.peers.values():
            with peer.lock:
                try:
                    peer.peer_socket.send(b"tracker close")
                except Exception:
                    pass
            peer.close()

    def handle_node(self, node_socket: socket.socket, node_addr: str) -> None:
        """Handles communication with a single node."""
        while self.running:
            try:
                with self.peers[node_addr].lock:
                    data = node_socket.recv(1024).decode()
                if not data:
                    self.remove_peer(node_addr)
                    continue
            except Exception as e:
                break
            print(f"Received data from {node_addr}: {data}")
            with self.peers[node_addr].lock:
                node_socket.send(b"Received data!")

    def remove_peer(self, peer_addr: str) -> None:
        self.peers[peer_addr].close()
        self.peers.pop(peer_addr)

    def ping(self, IP: str, port: int) -> None:
        node_addr = (IP, port)

        if node_addr in self.peers.keys():
            peer = self.peers[node_addr]
            try:
                with peer.lock:
                    peer.peer_socket.settimeout(2)
                    peer.peer_socket.send(b"PING")
                    start_time = time.time()
                    response = peer.peer_socket.recv(1024)
                    end_time = time.time()

                    latency = end_time - start_time
                    print(
                        f"Received from {node_addr}: {response.decode()} in {latency:.5f} seconds"
                    )
            except socket.timeout:
                print(f"Ping to {node_addr} timed out")
            except Exception as e:
                print(f"Failed to ping {node_addr}: {repr(e)}")
            finally:
                peer.peer_socket.settimeout(None)
        else:
            print(f"Node {node_addr} is offline")

    def tracker_command_shell(self) -> None:
        while True:
            sock_name, sock_port = self.sock.getsockname()
            cmd_input = input(f"{sock_name}:{sock_port} ~ ")
            cmd_parts = cmd_input.split()
            if not cmd_parts:
                continue

            match cmd_parts[0]:
                case "discover":
                    print("Discovering peers:")
                    for addr in self.peers:
                        print(f" - {addr}")
                case "ping":
                    try:
                        IP, port = cmd_parts[1].split(":")
                        self.ping(IP, int(port))
                    except IndexError:
                        print("Usage: ping <IP>:<port>")
                    except ValueError:
                        print("Invalid IP or port format.")
                case "list":
                    for index, peer_addr in enumerate(self.peers.keys()):
                        print(f"- [{index}] {str(peer_addr)}")
                case "exit":
                    break
                case _:
                    print("Unknown command")


def cli_parser():
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


def main():
    host, port, max_nodes = cli_parser()
    tracker = Tracker(host, port, max_nodes)
    try:
        tracker.start()
    except KeyboardInterrupt:
        print("\n[Exception]: Got Interrupt by Ctrl + C")
    finally:
        tracker.close()


if __name__ == "__main__":
    main()

import socket
import yaml
import threading
from typing import Dict


class Peer:
    def __init__(
        self,
        ip_address: str = None,
        peer_socket: socket.socket = None,
        peer_thread: threading.Thread = None,
        magnet_text: str = None,
    ):
        self.ip_address = ip_address
        self.peer_socket = peer_socket
        self.peer_thread = peer_thread
        self.magnet_text = None

    def close(self):
        try:
            if self.peer_socket:
                self.peer_socket.close()
            if self.peer_thread:
                self.peer_thread.join()
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
        self.node_serve_thread = threading.Thread(target=self.node_serve, daemon=True)
        print(f"Tracker listening on {host}:{port}")

    def start(self):
        self.node_serve_thread.start()
        self.tracker_command_shell()

    def node_serve(self) -> None:
        try:
            while self.running:
                try:
                    node_socket, node_addr = self.sock.accept()
                    print(f"Connection established with {node_addr}")

                    data = node_socket.recv(1028).decode()

                    if not data:
                        print(f"Connection closed by {node_addr}")
                        continue

                    # Handle handshake from node
                    if data == "First Connection":
                        peer_thread = threading.Thread(
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
                except ConnectionAbortedError:
                    print(f"Connection aborted by client.")
                except Exception as e:
                    print(f"Exception during connection handling: {repr(e)}")
        except KeyboardInterrupt:
            print("Keyboard interrupt, shutting down tracker...")
        finally:
            self.close()

    def close(self):
        self.running = False
        self.sock.close()
        for peer in self.peers.values():
            peer.close()

    def handle_node(self, node_socket: socket.socket, node_addr: str) -> None:
        """Handles communication with a single node."""
        print(f"Handling node {node_addr}")
        try:
            with node_socket:
                while self.running:
                    data = node_socket.recv(1024).decode()
                    if not data:
                        print(f"{node_addr} disconnected.")
                        break
                    print(f"Received data from {node_addr}: {data}")
                    node_socket.send(b"Received data!")
        except ConnectionResetError:
            print(f"Connection reset by {node_addr}")
        except Exception as e:
            print(f"Exception in handle_node for {node_addr}: {repr(e)}")
        finally:
            node_socket.close()
            self.peers.pop(node_addr, None)
            print(f"Connection with {node_addr} closed.")

    def tracker_command_shell(self) -> None:
        while True:
            cmd_input = input(">>> ")
            cmd_parts = cmd_input.split()
            if not cmd_parts:
                continue

            match cmd_parts[0]:
                case "discover":
                    print("Discovering peers:")
                    for addr in self.peers:
                        print(f" - {addr}")
                case "ping":
                    print("Pinging all peers")
                    for addr, peer in self.peers.items():
                        try:
                            peer.peer_socket.send(b"PING")
                            response = peer.peer_socket.recv(1024)
                            print(f"Received from {addr}: {response.decode()}")
                        except Exception as e:
                            print(f"Failed to ping {addr}: {repr(e)}")
                case "exit":
                    self.close()
                    break
                case _:
                    print("Unknown command")


def main():
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)

    host = config["server"]["host"]
    port = config["server"]["port"]
    max_nodes = config["server"]["max_nodes"]
    tracker = Tracker(host, port, max_nodes)
    try:
        tracker.start()
    except KeyboardInterrupt:
        print("Got Interrupt by Ctrl + C")
    finally:
        tracker.close()


if __name__ == "__main__":
    main()

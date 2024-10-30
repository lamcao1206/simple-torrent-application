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
    ):
        self.ip_address = ip_address
        self.peer_socket = peer_socket
        self.peer_thread = peer_thread


class Tracker:
    def __init__(self, host="localhost", port=8000, max_nodes=10) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Allow resuable port (temp fix for OSError: [Errno 48])
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.sock.bind((host, port))
        self.sock.listen(max_nodes)
        self.running = True
        self.peers: Dict[str, Peer] = {}
        print(f"Tracker listening on {host}:{port}")

    def start(self):
        while self.running:
            try:
                node_socket, node_addr = self.sock.accept()
            except Exception as e:
                print("Catch Exception while starting: ", repr(e))
                return
            data = node_socket.recv(1028).decode()
            if not data:
                print(f"Connection closed by {node_addr}")
                break

            # Handle handshake from node
            if data == "First Connection":
                new_peer = Peer(
                    ip_address=node_addr,
                    peer_socket=node_socket,
                    peer_thread=threading.Thread(
                        target=self.handle_node,
                        args=[node_socket, node_addr],
                        daemon=True,
                    ),
                )
                self.peers[node_addr] = new_peer
                node_socket.send(b"ACK")
            else:
                if not self.peers[node_addr].peer_thread.is_alive():
                    self.peers[node_addr].peer_thread.start()

    def close(self):
        self.running = False
        self.sock.close()
        for peer in self.peers.values():
            peer.peer_socket.send(b"Tracker closed")
            peer.peer_socket.close()

    def handle_node(self, node_socket: socket.socket, node_addr: str) -> None:
        """Handles communication with a single node."""
        with node_socket:
            while self.running:
                try:
                    data = node_socket.recv(1024).decode()
                except Exception as e:
                    break
                print(f"Received data from {node_addr}: {data}")
                node_socket.send(b"Received data!")


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
        print("Keyboard interrupt received. Shutting down tracker.")
    except Exception as e:
        print("Got exception:", repr(e))
    finally:
        tracker.close()


if __name__ == "__main__":
    main()

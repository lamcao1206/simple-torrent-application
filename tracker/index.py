import socket
import yaml
import threading


class Tracker:
    def __init__(self, host="localhost", port=8000, max_clients=10) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))
        self.sock.listen(max_clients)
        self.peers = {}
        print(f"Tracker listening on {host}:{port}")

    def handle_client(self, client, addr):
        """Handles communication with a single client."""
        try:
            print(f"Connected to {addr}")
            while True:
                data = client.recv(1024).decode()

                # Connection close
                if not data:
                    print(f"Connection closed by {addr}")
                    break

                # First connection of node client
                if data == "First Connection":
                    peer = Peer(ip_address=addr[0], sock=client)
                    self.peers[addr] = peer
                print(f"Received from client ${addr[0]}:", data)
                client.send(b"OK received")
        except ConnectionResetError:
            print(f"Connection reset by {addr}")
        finally:
            client.close()

    def start(self):
        try:
            while True:
                client, addr = self.sock.accept()

                # Create new thread for each socket
                client_thread = threading.Thread(
                    target=self.handle_client, args=(client, addr), daemon=True
                )
                client_thread.start()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.sock.close()


def main():
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)

    host = config["server"]["host"]
    port = config["server"]["port"]
    max_clients = config["server"]["max_clients"]
    tracker = Tracker(host, port, max_clients)
    tracker.start()


class Peer:
    def __init__(self, ip_address=None, sock=None):
        self.ip_address = ip_address
        self.sock = sock


if __name__ == "__main__":
    main()

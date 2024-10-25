import socket
import yaml
import threading


class Tracker:
    def __init__(self, host="localhost", port=8000, max_clients=10) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))
        self.sock.listen(max_clients)
        print(f"Tracker listening on {host}:{port}")

    def handle_client(self, client, addr):
        """Handles communication with a single client."""
        try:
            print(f"Connected to {addr}")
            while True:
                data = client.recv(1024).decode()
                if not data:  # Client closed connection
                    print(f"Connection closed by {addr}")
                    break
                print("Received from client:", data)
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


if __name__ == "__main__":
    main()

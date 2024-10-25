import socket
import yaml


class Tracker:
    def __init__(self, host="localhost", port=8000, max_clients=10) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))
        self.sock.listen(max_clients)
        print(f"Tracker listening on {host}:{port}")

    def start(self):
        while True:
            client, addr = self.sock.accept()
            print(f"Connect from {str(addr)}")
            client.send(b"Hello from Tracker")
            client.close()


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

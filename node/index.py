import socket
import time
import yaml


class Node:
    def __init__(self, host="localhost", port=8000) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sock.send("First Connection".encode())
        print(
            "Sending address: "
            + str(self.sock.getsockname()[0])
            + " "
            + str(self.sock.getsockname()[1])
        )

    def start(self):
        try:
            while True:
                time.sleep(0.5)
                data = self.sock.recv(1024).decode()
                print("Received from server: ", data)
                msg = input("Sending to server: ")
                self.sock.send(msg.encode())
        except KeyboardInterrupt:
            print("Got Interupted. End...")
        finally:
            self.sock.close()


def main():
    try:
        with open("config.yaml", "r") as file:
            config = yaml.safe_load(file)

        host = config["server"]["host"]
        port = config["server"]["port"]
        node = Node(host, port)
        node.start()
    except ConnectionRefusedError:
        print("Tracker refused to connect")


if __name__ == "__main__":
    main()

import socket
import time
import yaml


class Node:
    def __init__(self, tracker_host="localhost", tracker_port=8000) -> None:
        """
        Args:
            tracker_host (str): Hostname of tracker
            tracker_port (int): Port number of tracker
        """

        # Socket for interacting with tracker
        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_socket.connect((tracker_host, tracker_port))
        self.handshake()

        print(
            "Sending address: "
            + str(self.tracker_socket.getsockname()[0])
            + " "
            + str(self.tracker_socket.getsockname()[1])
        )

    def handshake(self):
        """
        Performs initial handshake with the tracker by sending "First Connection" message
        and waiting for acknowledgment
        """
        self.tracker_socket.send("First Connection".encode())
        ack = self.tracker_socket.recv(1024).decode()
        if ack == "ACK":
            print("Tracker acknowledge the connection.")
        else:
            raise ConnectionError("Unexpected response from tracker")

    def start(self):
        try:
            while True:
                time.sleep(0.5)
                data = self.tracker_socket.recv(1024).decode()
                print("Received from server: ", data)
                msg = input("Sending to server: ")
                self.tracker_socket.send(msg.encode())
        except KeyboardInterrupt:
            print("Got Interupted. End...")
        finally:
            self.tracker_socket.close()


def main():
    try:
        with open("config.yaml", "r") as file:
            config = yaml.safe_load(file)

        host = config["server"]["host"]
        port = config["server"]["port"]
        node = Node(host, port)
        node.start()
    except Exception as e:
        print(repr(e))


if __name__ == "__main__":
    main()

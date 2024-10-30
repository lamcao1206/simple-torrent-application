import socket
import yaml
import threading
import sys


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
        self.tracker_listening_thread = threading.Thread(
            target=self.tracker_listening, daemon=True
        )

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

    def tracker_listening(self):
        while True:
            try:
                data = self.tracker_socket.recv(1024).decode()
            except Exception as e:
                return

            if data == "tracker close":
                print("\nTracker closed!")
                return

            print("Received from tracker: ", data)

    def start(self):
        self.tracker_listening_thread.start()
        self.node_command_shell()

    def close(self):
        self.tracker_socket.close()
        sys.exit(0)

    def node_command_shell(self) -> None:
        while True:
            cmd_input = input(">>> ")
            cmd_parts = cmd_input.split()

            if not cmd_parts:
                continue

            match cmd_parts[0]:
                case "exit":
                    break
                case _:
                    print("Unknown command")


def main():
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)

    host = config["server"]["host"]
    port = config["server"]["port"]
    node = Node(host, port)
    try:
        node.start()
    except Exception as e:
        print(repr(e))
    finally:
        node.close()


if __name__ == "__main__":
    main()

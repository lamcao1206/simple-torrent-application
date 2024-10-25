import socket
import sys


class Client:
    def __init__(self, host="localhost", port=8000) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("localhost", 8000))

    def start(self):
        msg = self.sock.recv(1024)
        print(msg)

        while msg:
            print("Received ", msg.decode())
            msg = self.sock.recv(1024)


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    client = Client(host, port)
    client.start()


if __name__ == "__main__":
    main()

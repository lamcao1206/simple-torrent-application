import socket
from threading import Thread
from typing import Tuple
import sys
import os
import argparse
import shutil

"""
	add file1.txt file2.txt file3.txt 
	remove file1.txt file2.txt file3.txt 
	log 
	push 
	fetch
	exit
"""


class Metafile:
    def __init__(
        self, file_name: str, full_bytes_size: int, curr_bytes_size: int
    ) -> None:
        self.file_name = file_name
        self.full_bytes_size = full_bytes_size
        self.curr_bytes_size = curr_bytes_size


class Node:
    def __init__(self, tracker_host="127.0.0.1", tracker_port=8000) -> None:
        """
        Args:
            tracker_host (str): Hostname of tracker
            tracker_port (int): Port number of tracker
        """
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port
        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_listening_thread = Thread(
            target=self.tracker_listening, daemon=True
        )

    def start(self) -> None:
        """
        Start the Node step-by-step:
         - Handshake with tracker
         - Start tracker listening thread for receiving messages from tracker
         - Start the Node command shell loop (main process) for interacting with CLI
        """
        self.handshake()
        self.tracker_listening_thread.start()
        self.node_command_shell()

    def handshake(self) -> None:
        """
        This function performs initial handshake with the tracker by sending "First Connection" message
        and waiting for acknowledgment from tracker
        """
        self.tracker_socket.connect((self.tracker_host, self.tracker_port))
        self.tracker_socket.send("First Connection".encode())
        ack = self.tracker_socket.recv(1024).decode()
        if ack == "ACK":
            print("Tracker acknowledge the connection.")
        else:
            raise ConnectionError("Unexpected response from tracker")

    def tracker_listening(self) -> None:
        """
        Run a loop for receiving messages from tracker and handle them
        """
        while True:
            try:
                data = self.tracker_socket.recv(1024).decode()
            except Exception as e:
                return

            if data == "tracker close":
                print("\nTracker closed!")
                self.close()
                sys.exit(0)

            if data == "PING":
                self.ping_response()
            elif data == "INVESTIGATE":
                self.investigate_response()
            else:
                raise RuntimeError("Unknown message from tracker")

    def add(self, file_list: list[str]) -> None:
        """
        Add files from local to staging to the staging directory

        Args:
            file_list (List[str]): List of filename from CLI
        """

        for file_name in file_list:
            if file_name not in os.listdir("local"):
                print(f"[Error]: File {file_name} does not exist")
                return

        for file_name in file_list:
            if file_name in os.listdir("staging"):
                print(f"[Warning]: {file_name} already exists in staging folder")
                file_list.remove(file_name)

        for file_name in file_list:
            shutil.copy(f"local/{file_name}", "staging")

    def remove(self, file_list: list[str]) -> None:
        """
        Remove specific files from staging

        Args:
            file_list (list[str]): List of filenames
        """
        for file_name in file_list:
            if file_name not in os.listdir("staging"):
                print(f"[Warning]: {file_name} not exists in staging folder")
            else:
                os.remove(f"staging/{file_name}")

    def push(self) -> None:
        """
        Publish the metafile info to the tracker
        Args:
            metafile (Metafile): Metafile object to publish
        """
        staging_file_names = os.listdir("staging")
        self.tracker_socket.sendall(f"push {staging_file_names}".encode())

    def tracker_scrape(self) -> None:
        pass

    def node_command_shell(self) -> None:
        """
        Command shell loop for interacting with Node CLI
        """
        while True:
            sock_name, sock_port = self.tracker_socket.getsockname()
            cmd_input = input(f"{sock_name}:{sock_port} ~ ")
            cmd_parts = cmd_input.split()

            if not cmd_parts:
                continue

            match cmd_parts[0]:
                case "add":
                    self.add(cmd_parts[1:])
                case "remove":
                    self.remove(cmd_parts[1:])
                case "push":
                    self.push()
                case "tracker-scape":
                    break
                case "exit":
                    break
                case _:
                    print("Unknown command")

    def ping_response(self) -> None:
        """
        Send a response to tracker for "ping" message
        """
        self.tracker_socket.sendall(b"Alive")

    def investigate_response(self):
        """
        Return the list of filenames in the staging directory to the tracker
        """
        dir_list = os.listdir("staging")
        self.tracker_socket.sendall(" ".join(dir_list).encode())

    def close(self):
        """
        Close the Node
        """
        self.tracker_socket.close()
        os._exit(0)


def cli_parser() -> Tuple[str, int]:
    """
    Parse command line arguments for the Node CLI
    Returns:
        Tuple[str, int]: Tracker's IP address and port number
    """
    parser = argparse.ArgumentParser(
        prog="Node", description="Init the Node for file system"
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
    args = parser.parse_args()
    return (args.host, args.port)


def main() -> None:
    host, port = cli_parser()
    node = Node(host, port)
    try:
        node.start()
    except Exception as e:
        print(f"[Exception]: {repr(e)}")
    finally:
        node.close()


if __name__ == "__main__":
    main()

from utils import NodeUtils
from piece import Piece
from threading import Thread, Lock
from typing import Tuple, List, Dict
import socket
import sys
import os
import traceback
import mmap
import time

REPO_FOLDER = "repo"
LOCAL_FOLDER = "local"
PIECE_SIZE = 512 * 1024
REQUEST_TIMEOUT = 5


class Node:
    def __init__(
        self, tracker_host="127.0.0.1", tracker_port=8000, upload_IP="127.0.0.1"
    ) -> None:

        # socket for communicate with tracker
        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # socket for listening upload requests
        self.upload_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.upload_socket.bind((upload_IP, 0))
        self.upload_socket.listen(10)

        # Server info
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port

        # Thread for communicate with tracker
        self.tracker_listening_thread = Thread(
            target=self.tracker_listening, daemon=True
        )

        # Pieces Info
        self.pieces: List[Piece] = []

        # Lock
        self.lock = Lock()

    def start(self) -> None:
        self.setup()
        self.handshake()
        self.tracker_listening_thread.start()
        self.node_command_shell()

    def setup(self) -> None:
        # Make neccessary dirs
        directories = ["local", "repo", "temp"]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

        self.pieces = NodeUtils.generate_pieces_from_repo_files(
            folder_name=REPO_FOLDER, piece_size=PIECE_SIZE
        )

    def handshake(self) -> None:
        self.tracker_socket.connect((self.tracker_host, self.tracker_port))
        time.sleep(0.1)
        self.tracker_socket.send("First Connection".encode())

        # Generate the file info
        file_info: str = NodeUtils.generate_files_info_from(folder_name=REPO_FOLDER)

        # Tell the tracker info of original socket and tracker socket and its file info
        node_info = (
            self.tracker_socket.getsockname()[0]  # IP address
            + " "
            + str(self.tracker_socket.getsockname()[1])  # Port
            + " "
            + self.upload_socket.getsockname()[0]
            + " "
            + str(self.upload_socket.getsockname()[1])
            + " "
            + file_info
        )

        self.tracker_socket.sendall(node_info.encode())
        print(
            "Communicate Address: "
            + self.tracker_socket.getsockname()[0]
            + " "
            + str(self.tracker_socket.getsockname()[1])
        )

        print(
            "Upload Address: "
            + self.upload_socket.getsockname()[0]
            + " "
            + str(self.upload_socket.getsockname()[1])
        )

    def tracker_listening(self) -> None:
        while True:
            data = ""
            try:
                with self.lock:
                    data = self.tracker_socket.recv(1024).decode()
            except Exception as e:
                continue

            if len(data) == 0:
                continue
            elif data == "tracker close":
                print("\nTracker closed!")
                self.close()
                sys.exit(0)
            elif data == "PING":
                self.ping_response()

    def add(self, file_list_request: list[str], src_fold: str, dest_fold: str) -> None:
        # Check for unexists file in src folder
        for file_name in file_list_request:
            if file_name not in os.listdir(src_fold):
                print(f"[Error]: File {file_name} does not exist")
                return

        # Check for existing file in dest folder
        for file_name in file_list_request:
            if file_name in os.listdir(dest_fold):
                print(f"[Warning]: {file_name} already exists in repo folder")
                file_list_request.remove(file_name)

        for file_name in file_list_request:
            src_path = os.path.join(src_fold, file_name)
            dest_path = os.path.join(dest_fold, file_name)
            with open(src_path, "rb") as src_file, open(dest_path, "wb") as dest_file:
                # Memory-map the src file to move to dest file
                mmap_obj = mmap.mmap(
                    src_file.fileno(), length=0, access=mmap.ACCESS_READ
                )
                dest_file.write(mmap_obj)
                mmap_obj.close()
        if len(file_list_request) != 0:
            print("Add files to repo OK!")

    def remove(self, file_list_request: list[str]) -> None:
        for file_name in file_list_request:
            if file_name not in os.listdir(REPO_FOLDER):
                print(f"[Warning]: {file_name} not exists in repo folder")
                return
            else:
                os.remove(f"{REPO_FOLDER}/{file_name}")
                for piece in self.pieces:
                    if piece.original_filename == file_name:
                        self.pieces.remove(piece)
        print("Remove files from repo OK!")

    def publish(self, file_names: str) -> None:
        pass

    def fetch(self, message: str) -> None:
        def fetch_async():
            try:
                # Acquire lock to safely access the tracker socket
                with self.lock:
                    self.tracker_socket.sendall(message.encode())
                    data = self.tracker_socket.recv(1024).decode()
                    print(f"[Tracker Response]: {data}")
            except socket.error as e:
                print(f"[Error]: Socket communication failed: {e}")
            except Exception as e:
                print(f"[Error]: Unexpected error during fetch: {e}")

        fetch_thread = Thread(target=fetch_async, daemon=True)
        fetch_thread.start()
        time.sleep(1)

    def node_command_shell(self) -> None:
        while True:
            sock_name, sock_port = self.tracker_socket.getsockname()
            cmd_input = input(f"{sock_name}:{sock_port} ~ ")
            cmd_parts = cmd_input.split()

            if not cmd_parts:
                continue

            match cmd_parts[0]:
                case "add":
                    self.add(
                        cmd_parts[1:], src_fold=LOCAL_FOLDER, dest_fold=REPO_FOLDER
                    )
                case "remove":
                    self.remove(cmd_parts[1:])
                case "piece":
                    for piece in self.pieces:
                        print(piece)
                case "publish":
                    print(cmd_input)
                case "fetch":
                    self.fetch(cmd_input)
                    pass
                case "exit":
                    break
                case _:
                    print("Unknown command")

    def ping_response(self) -> None:
        self.tracker_socket.sendall(b"alive")

    def close_sockets(self):
        self.tracker_socket.close()
        self.upload_socket.close()

    def close(self):
        try:
            self.tracker_socket.settimeout(REQUEST_TIMEOUT)
            self.tracker_socket.sendall("close".encode())
        except Exception as e:
            print(f"[Error]: Failed to send close message to tracker: {e}")
        finally:
            self.close_sockets()
            print("Node closed")
            os._exit(0)


def main() -> None:
    host, port = NodeUtils.cli_parser()
    node = Node(host, port)
    try:
        node.start()
    except KeyboardInterrupt:
        print("\n[Exception]: Interrupted by user")
        node.close()
    except Exception as e:
        print(f"\n[Exception]: {traceback.format_exc()}")
        node.close()
    finally:
        node.close()


if __name__ == "__main__":
    main()

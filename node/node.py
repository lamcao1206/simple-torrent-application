import socket
from threading import Thread
from typing import Tuple, List, Dict
import sys
import os
import argparse
import shutil
import mmap
import math
import json
import traceback

STAGING_FOLDER = "staging"
PIECE_SIZE = 512 * 1024


class Piece:
    def __init__(
        self, piece_id: int, original_filename: str, start_index: int, end_index: int
    ) -> None:
        self.piece_id = piece_id
        self.original_filename = original_filename
        self.piece_name = f"{self.original_filename}_{self.piece_id}"
        self.start_index = start_index
        self.end_index = end_index

    def __str__(self) -> None:
        return f"Piece ID: {self.piece_id}, Filename: {self.original_filename}, Piecename: {self.piece_name}, Start Index: {self.start_index}, End Index: {self.end_index}"


class Node:
    def __init__(
        self, tracker_host="127.0.0.1", tracker_port=8000, upload_IP="127.0.0.1"
    ) -> None:
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port
        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.upload_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.upload_socket.bind((upload_IP, 0))
        self.upload_socket.listen(10)

        # Thread for communicate with tracker
        self.tracker_listening_thread = Thread(
            target=self.tracker_listening, daemon=True
        )

        # Pieces Info
        self.pieces: List[Piece] = []

    def start(self) -> None:
        self.setup()
        self.handshake()
        self.tracker_listening_thread.start()
        self.node_command_shell()

    def setup(self) -> None:
        # Make neccessary dirs
        directories = ["local", "staging", "temp"]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

        # Clean the temp directories
        temp_dir = "temp"
        for filename in os.listdir(temp_dir):
            os.remove(f"{temp_dir}/{filename}")

        # Parser the staging folder to generate self.pieces
        self.pieces = NodeUtils.generate_pieces_staging_files(
            folder_name=STAGING_FOLDER, piece_size=PIECE_SIZE
        )

        for piece in self.pieces:
            print(piece)

    def handshake(self) -> None:
        self.tracker_socket.connect((self.tracker_host, self.tracker_port))
        self.tracker_socket.send("First Connection".encode())
        ack = self.tracker_socket.recv(1024).decode()
        if ack == "ACK":
            print("Tracker acknowledge the connection.")
        else:
            raise ConnectionError("Unexpected response from tracker")

        # Generate the file info
        file_info: str = NodeUtils.generate_files_info(folder_name=STAGING_FOLDER)
        print(file_info)

        # Tell the tracker info of original socket and tracker socket and its file info
        node_info = (
            str(self.tracker_socket.getsockname()[1])
            + " "
            + str(self.upload_socket.getsockname()[1])
            + " "
            + file_info
        )

        self.tracker_socket.sendall(node_info.encode())

    def tracker_listening(self) -> None:
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
        for file_name in file_list:
            if file_name not in os.listdir("staging"):
                print(f"[Warning]: {file_name} not exists in staging folder")
            else:
                os.remove(f"staging/{file_name}")

    def push(self) -> None:
        staging_file_names = os.listdir("staging")
        self.tracker_socket.sendall(f"push {staging_file_names}".encode())

    def tracker_scrape(self) -> None:
        self.tracker_socket.send("TRACKER SCRAPE")
        pass

    def node_command_shell(self) -> None:
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
        self.tracker_socket.sendall(b"Alive")

    def investigate_response(self):
        dir_list = os.listdir("staging")
        self.tracker_socket.sendall(" ".join(dir_list).encode())

    def close(self):
        self.tracker_socket.close()
        os._exit(0)


def cli_parser() -> Tuple[str, int]:
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


class NodeUtils:
    @staticmethod
    def generate_pieces_staging_files(folder_name: str, piece_size: int) -> List[Piece]:
        file_names = os.listdir(folder_name)
        pieces = []
        for file_name in file_names:
            piece_id = 0
            file_path = os.path.join(STAGING_FOLDER, file_name)
            with open(file_path, "r+b") as file:
                mmap_obj = mmap.mmap(file.fileno(), length=0, access=mmap.ACCESS_READ)
                while True:
                    start_index = piece_id * PIECE_SIZE
                    end_index = start_index + PIECE_SIZE
                    piece_sliding_window = mmap_obj[start_index:end_index]
                    # End sliding window
                    if not piece_sliding_window:
                        break
                    # Create a new Piece object
                    piece = Piece(
                        piece_id=piece_id,
                        original_filename=os.path.basename(file_name).split(".")[0],
                        start_index=start_index,
                        end_index=end_index,
                    )
                    pieces.append(piece)
                    piece_id += 1
                mmap_obj.close()
        return pieces

    @staticmethod
    def generate_files_info(folder_name: str) -> str:
        file_info = {}
        file_names = os.listdir(folder_name)
        for file_name in file_names:
            file_path = os.path.join(folder_name, file_name)
            file_size = os.path.getsize(file_path)
            piece_size = PIECE_SIZE
            piece_count = math.ceil(file_size / piece_size)

            file_info[file_name] = {
                "file_size": file_size,
                "piece_size": piece_size,
                "piece_count": piece_count,
            }
        return json.dumps(file_info)


def main() -> None:
    host, port = cli_parser()
    node = Node(host, port)
    try:
        node.start()
    except Exception as e:
        print(traceback.format_exc())
    finally:
        node.close()


if __name__ == "__main__":
    main()

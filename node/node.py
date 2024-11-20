from threading import Thread
from typing import Tuple, List, Dict
import socket
import os
import traceback
import mmap
import json
import time
import math
import argparse
from tqdm import tqdm
from queue import Queue


REPO_FOLDER = "repo"
LOCAL_FOLDER = "local"
PIECES_FOLDER = "pieces"
PIECE_SIZE = 512 * 1024
REQUEST_TIMEOUT = 5


class Piece:
    def __init__(
        self, piece_id: int, original_filename: str, start_index: int, end_index: int
    ):
        self.piece_id = piece_id
        self.original_filename = original_filename
        self.start_index = start_index
        self.end_index = end_index

    def __repr__(self):
        return f"Piece({self.piece_id}, Original file: {self.original_filename}, {self.start_index} - {self.end_index})"


class Node:
    def __init__(
        self, tracker_host="127.0.0.1", tracker_port=8000, upload_IP="127.0.0.1"
    ) -> None:

        # socket for sending message to tracker
        self.tracker_send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # socket for listening upload requests
        self.upload_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.upload_socket.bind((upload_IP, 0))
        self.upload_socket.listen(10)

        # Server info
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port

        # Pieces Info
        self.pieces: List[Piece] = []

        # Thread for listening upload requests
        self.upload_listening_request_thread = Thread(
            target=self.upload_listening_request,
            args=(self.upload_socket,),
            daemon=True,
        )

    def upload_listening_request(self, upload_socket: socket.socket) -> None:
        while True:
            try:
                conn, addr = upload_socket.accept()
            except Exception as e:
                break
            upload_handler_thread = Thread(
                target=self.upload_request_handler, args=(conn, addr), daemon=True
            )
            upload_handler_thread.start()

    def upload_request_handler(
        self, conn: socket.socket, addr: Tuple[str, int]
    ) -> None:
        with conn:
            msg = conn.recv(1024).decode()
            print(msg)
            if msg.startswith("find"):
                self.explore_pieces_request_handler(msg, conn)
            elif msg.startswith("request"):
                self.transfer_pieces_request_handler(msg.split()[1], conn)

    def explore_pieces_request_handler(self, msg: str, conn: socket.socket) -> None:
        response = {}
        requested_files = msg.split()[1:]
        for file_name in requested_files:
            for piece in self.pieces:
                if piece.original_filename == file_name:
                    response.setdefault(file_name, []).append(f"{piece.piece_id}")
        conn.sendall(json.dumps(response).encode())

    def transfer_pieces_request_handler(
        self, piece_name: str, conn: socket.socket
    ) -> None:
        # Transfer the requested piece to the requesting node
        piece_path = os.path.join(PIECES_FOLDER, piece_name)
        with open(piece_path, "rb") as piece_file:
            with mmap.mmap(
                piece_file.fileno(), length=0, access=mmap.ACCESS_READ
            ) as mmapped_file:
                chunk = mmapped_file.read(PIECE_SIZE)
                conn.sendall(chunk)

    def start(self) -> None:
        self.setup()
        self.handshake()
        self.upload_listening_request_thread.start()
        self.node_command_shell()

    def setup(self) -> None:
        directories = ["local", "repo", "temp"]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

        self.pieces = NodeUtils.generate_pieces_from_repo_files(
            folder_name=REPO_FOLDER, piece_size=PIECE_SIZE
        )

    def handshake(self) -> None:
        self.tracker_send_socket.connect((self.tracker_host, self.tracker_port))
        time.sleep(0.1)
        self.tracker_send_socket.send("First Connection".encode())

        file_info: str = NodeUtils.generate_files_info_from(folder_name=REPO_FOLDER)

        # (IP Address) (Port for sending) (Port for uploading) (File info)

        node_info = (
            self.tracker_host
            + " "
            + str(self.tracker_send_socket.getsockname()[1])
            + " "
            + str(self.upload_socket.getsockname()[1])
            + " "
            + file_info
        )

        self.tracker_send_socket.sendall(node_info.encode())

        print(
            "Sending socket address: "
            + self.tracker_send_socket.getsockname()[0]
            + ":"
            + str(self.tracker_send_socket.getsockname()[1])
        )

        print(
            "Upload socket address: "
            + self.upload_socket.getsockname()[0]
            + ":"
            + str(self.upload_socket.getsockname()[1])
        )

    def add(self, file_list_request: list[str], src_fold: str, dest_fold: str) -> None:
        for file_name in file_list_request:
            if file_name not in os.listdir(src_fold):
                print(f"[Error]: File {file_name} does not exist")
                return

        for file_name in file_list_request:
            if file_name in os.listdir(dest_fold):
                print(f"[Warning]: {file_name} already exists in repo folder")
                file_list_request.remove(file_name)

        for file_name in file_list_request:
            src_path = os.path.join(src_fold, file_name)
            dest_path = os.path.join(dest_fold, file_name)
            with open(src_path, "rb") as src_file, open(dest_path, "wb") as dest_file:
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

    def fetch(self, message: str) -> None:
        try:
            requested_files = message.split()[1:]
            self.tracker_send_socket.sendall(message.encode())
            data = self.tracker_send_socket.recv(1024).decode()
            data = json.loads(data)
            print(data)
            # {'127.0.0.1:54782': {'ip_addr': '127.0.0.1', 'upload_port': 54781}, '127.0.0.1:54784': {'ip_addr': '127.0.0.1', 'upload_port': 54783}, 'tracker_ip': '127.0.0.1:8000'}
            request_pieces_obj = {}
            for _, peer_info in data.items():
                if (
                    isinstance(peer_info, dict)
                    and int(peer_info["upload_port"])
                    != self.upload_socket.getsockname()[1]
                ):
                    ip_addr = peer_info["ip_addr"]
                    upload_port = peer_info["upload_port"]
                    pieces_info = self.request_pieces_info_from(
                        ip_addr, upload_port, requested_files
                    )
                    request_pieces_obj[(ip_addr, upload_port)] = pieces_info

            print(request_pieces_obj)
        except Exception as e:
            print(f"[Error]: Unexpected error during fetch: {e}")

    def request_pieces_info_from(
        self, ip_addr: str, upload_port: str, requested_files: list[str]
    ) -> Dict[str, List[str]]:
        # Fetch to peer with ip_addr and upload_port with nessesary files and return list of pieces related to requested_files
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as pieces_request_socket:
            pieces_request_socket.connect((ip_addr, int(upload_port)))
            pieces_request_socket.sendall(f"find {' '.join(requested_files)}".encode())
            data = pieces_request_socket.recv(1024).decode()
        return data

    def download(
        self,
        target_ip: str = "127.0.0.1",
        target_port: int = 0,
        piece_queue: list[str] = None,
    ) -> None:
        try:
            for piece_name in tqdm(
                piece_queue,
                desc=f"{target_ip}:{target_port}",
                unit="piece",
                colour="yellow",
            ):
                with socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM
                ) as download_socket:
                    download_socket.connect((target_ip, target_port))
                    download_socket.sendall(f"request {piece_name}".encode())

                    piece_data = b""
                    while True:
                        chunk = download_socket.recv(PIECE_SIZE)
                        if not chunk:
                            break
                        piece_data += chunk

                    if piece_data:
                        piece_path = os.path.join("temp", f"{piece_name}.txt")
                        with open(piece_path, "wb") as piece_file:
                            piece_file.write(piece_data)
                    else:
                        print(
                            f"[Error]: Failed to download {piece_name}, no data received"
                        )
                        continue

        except Exception as e:
            print(f"[Error]: Unexpected error during download: {e}")

    def node_command_shell(self) -> None:
        while True:
            sock_name, sock_port = self.tracker_send_socket.getsockname()
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
                case "d":
                    self.download(
                        target_port=int(cmd_parts[1]), piece_queue=cmd_parts[2:]
                    )
                case "fetch":
                    self.fetch(cmd_input)
                case "exit":
                    break
                case _:
                    print("Unknown command")

    def close_sockets(self):
        self.tracker_send_socket.close()
        self.upload_socket.close()

    def close(self):
        try:
            self.tracker_send_socket.settimeout(REQUEST_TIMEOUT)
            self.tracker_send_socket.sendall("close".encode())
        except Exception as e:
            print(f"[Error]: Failed to send close message to tracker: {e}")
        finally:
            self.close_sockets()
            for filename in os.listdir(PIECES_FOLDER):
                os.unlink(os.path.join(PIECES_FOLDER, filename))
            os._exit(0)


class NodeUtils:
    @staticmethod
    def generate_pieces_from_repo_files(
        folder_name: str = None,
        file_list: str = None,
        piece_size: int = PIECE_SIZE,
    ) -> List[Piece]:
        # Generate Piece based on folder_name/{file_list}
        # If file_list is None, generate Piece of all files in folder_name

        file_names = file_list if file_list is not None else os.listdir(folder_name)

        pieces = []

        for file_name in file_names:
            piece_id = 0
            file_path = os.path.join(folder_name, file_name)
            with open(file_path, "r+b") as file:
                mmap_obj = mmap.mmap(file.fileno(), length=0, access=mmap.ACCESS_READ)
                while True:
                    # Start sliding window
                    start_index = piece_id * piece_size
                    end_index = start_index + piece_size
                    piece_sliding_window = mmap_obj[start_index:end_index]

                    # End sliding window
                    if not piece_sliding_window:
                        break

                    # Create a new piece file
                    piece_name = (
                        f"{os.path.basename(file_name).split('.')[0]}_{piece_id}.txt"
                    )

                    piece_path = f"{PIECES_FOLDER}/{piece_name}"
                    with open(piece_path, "wb") as piece_file:
                        piece_file.write(piece_sliding_window)

                    # Create a new Piece object
                    piece = Piece(
                        piece_id=piece_id,
                        original_filename=file_name,
                        start_index=start_index,
                        end_index=end_index,
                    )
                    pieces.append(piece)
                    piece_id += 1
                mmap_obj.close()
        return pieces

    @staticmethod
    def generate_files_info_from(
        folder_name: str = None, file_name: str = None, piece_size: int = 512 * 1024
    ) -> str:
        # Generate file info from folder_name/file_name.txt
        # If file_name is None, generate file infos from all files in folder_name

        file_info = {}
        file_names = [file_name] if file_name is not None else os.listdir(folder_name)

        for file_name in file_names:
            file_path = os.path.join(folder_name, file_name)
            file_size = os.path.getsize(file_path)
            piece_count = math.ceil(file_size / piece_size)

            file_info[file_name] = {
                "file_size": file_size,
                "piece_size": piece_size,
                "piece_count": piece_count,
            }

        return json.dumps(file_info)

    @staticmethod
    def metafile_convert(input: Dict[str, List[str]]) -> Dict[str, List[str]]:
        result = {}
        for key, peers in input.items():
            if key == "tracker ip":
                continue
            for peer in peers["nodes"]:
                result.setdefault(peer, []).append(key)
        return result

    @staticmethod
    def get_request_queue(
        filename: str,
        request_obj: dict[tuple[str, int], dict[str, list[str]]],
        curr_pieces_info: dict[str, list[str]],
    ) -> dict[tuple[str, int], list[str]]:
        def create_request_queue(filename: str, data: dict[int, list[str]]):

            # return key whose value has the minimum length
            def get_min_key(d, keys):
                # Initialize min_key as None and min_length as infinity to find the minimum
                min_key = None
                min_length = float("inf")

                for key in keys:
                    list_length = len(d[key])
                    if list_length < min_length:
                        min_length = list_length
                        min_key = key
                return min_key

            # Get the request queue
            result = {key: [] for key in data}
            keys = list(data.keys())
            total_value = 0
            for value in data.values():
                total_value += len(value)
            while total_value > 0:
                listkey = keys.copy()

                # Loop through remaining keys(node's port) to update correspond request queue
                while len(listkey) > 0:
                    min_key = get_min_key(data, listkey)

                    # Remove key whose value is an empty list
                    if len(data[min_key]) == 0:
                        keys.remove(min_key)
                        listkey.remove(min_key)
                        continue

                    # Append request queue of corresponding node
                    piece = data[min_key][0]
                    piece_name = f"{filename}_{piece}.txt"
                    result[min_key].append(piece_name)

                    # remove ${piece} in each of keys'value (if any) and decrease total_value
                    for eachkey in keys:
                        if piece in data[eachkey]:
                            data[eachkey].remove(piece)
                            total_value -= 1
                    listkey.remove(min_key)
            return result

        # Initialize dictionary in which keys are nodes address
        # and assign value with the list of pieces derived from ${filename} each nodes possesses
        data = {key: [] for key in request_obj}
        for key in list(request_obj.keys()):
            value = request_obj[key]
            if not value.get(filename):
                del data[key]
                continue
            data[key] = value[filename]

        # remove pieces in nodes that client already possesses (if any)
        if curr_pieces_info.get(filename):
            for key in list(data.keys()):
                duplicate_piece = curr_pieces_info.get(filename)
                for value in duplicate_piece:
                    if value in data[key]:
                        data[key].remove(value)

        # get request_queue for each node
        request_queue = {key: [] for key in data}
        file_name = filename.split(".")[0]
        request_queue = create_request_queue(file_name, data)
        return request_queue

    @staticmethod
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


def main() -> None:
    host, port = NodeUtils.cli_parser()
    node = Node(host, port)
    try:
        node.start()
    except KeyboardInterrupt:
        print("\n[Exception]: Interrupted by user")
        node.close()
    except Exception as e:
        print(f"\n[Exception]: {traceback.format_exc(e)}")
        node.close()
    finally:
        node.close()


if __name__ == "__main__":
    main()

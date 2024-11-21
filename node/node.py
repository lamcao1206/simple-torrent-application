# Author: Cao Ngoc Lam, Nguyen Chau Hoang Long
# Date modified: Thursday 21st Nov 2024

from typing import Tuple, List, Dict
import threading
import socket
import os
import traceback
import mmap
import json
import time
import math
import argparse
from queue import Queue
from tqdm import tqdm
import multiprocessing


REPO_FOLDER = "repo"
LOCAL_FOLDER = "local"
PIECES_FOLDER = "pieces"
TEMP_FOLDER = "temp"
PIECE_SIZE = 512 * 1024
REQUEST_TIMEOUT = 5


class Piece:
    """
    Represent an mapping info to real pieces in PIECES_FOLDER

    Args:
        - piece_id (int): Piece ID
        - original_filename (str): Original filename that the pieces belong to
        - start_index (int): Start index of the piece in byte array representation of file
        - end_index (int): End index of the piece in byte array representation of file
    """

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
    """
    Represent a single Node in P2P network

    Args:
        - tracker_ip (str): IP Address of the tracker
        - tracker_port (int): Port number of the tracker
        - tracker_send_socket (socket.socket): Socket for sending message to tracker
        - upload_socket (socket.socket): Socket for listening upload requests
        - pieces (List[Piece]): List of pieces that the node has
        - upload_listening_request_thread (threading.Thread): Thread for listening upload requests
    """

    def __init__(
        self, tracker_ip="127.0.0.1", tracker_port=8000, upload_IP="127.0.0.1"
    ) -> None:
        # socket for sending message to tracker
        self.tracker_send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # socket for listening upload requests
        self.upload_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.upload_socket.bind((upload_IP, 0))
        self.upload_socket.listen(10)

        # Server info
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port

        # Pieces Info
        self.pieces: List[Piece] = []

        # Thread for listening upload requests
        self.upload_listening_request_thread = threading.Thread(
            target=self.upload_listening_request,
            args=(self.upload_socket,),
            daemon=True,
        )

    def upload_listening_request(self, upload_socket: socket.socket) -> None:
        """
        Listen to the upload request connections from other nodes and create new threads to handle the them

        Args:
            - upload_socket (socket.socket): Socket for listening upload requests
        """
        while True:
            try:
                conn, addr = upload_socket.accept()
            except Exception as e:
                break
            upload_handler_thread = threading.Thread(
                target=self.upload_request_handler, args=(conn), daemon=True
            )
            upload_handler_thread.start()

    def upload_request_handler(self, conn: socket.socket) -> None:
        """
        Handle the upload request from corresponding node
        Args:
            conn (socket.socket): Socket connection
            addr (Tuple[str, int]):
        """
        with conn:
            msg = conn.recv(1024).decode()
            if msg.startswith("find"):
                self.explore_pieces_request_handler(msg, conn)
            elif msg.startswith("request"):
                self.transfer_pieces_request_handler(msg.split()[1], conn)

    def explore_pieces_request_handler(self, msg: str, conn: socket.socket) -> None:
        """
        Handle the explore pieces request from corresponding node
        Args:
            msg (str): message content
            conn (socket.socket): Socket connection
        """
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
        piece_path = os.path.join(PIECES_FOLDER, piece_name)
        with open(piece_path, "rb") as piece_file:
            with mmap.mmap(
                piece_file.fileno(), length=0, access=mmap.ACCESS_READ
            ) as mmapped_file:
                chunk = mmapped_file.read(PIECE_SIZE)
                conn.sendall(chunk)

    def start(self) -> None:
        # Start the Node by setting up the environment, handshake with the tracker, and start the command shell
        self.setup()
        self.handshake()
        self.upload_listening_request_thread.start()
        self.node_command_shell()

    def setup(self) -> None:
        # Set up neccessary folders and generate pieces from repo files
        directories = [LOCAL_FOLDER, REPO_FOLDER, TEMP_FOLDER, PIECES_FOLDER]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

        self.pieces = NodeUtils.generate_pieces_from_repo_files(
            folder_name=REPO_FOLDER, piece_size=PIECE_SIZE
        )

    def handshake(self) -> None:
        # Handshake with the tracker by sending the first connection message and node information (files, pieces information) to tracker
        self.tracker_send_socket.connect((self.tracker_ip, self.tracker_port))
        time.sleep(0.1)
        self.tracker_send_socket.send("First Connection".encode())

        file_info: str = NodeUtils.generate_files_info_from(folder_name=REPO_FOLDER)

        # (IP Address) (Port for sending) (Port for uploading) (File info)

        node_info = (
            self.tracker_ip
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
        # Fetch the files by sending the request to the tracker and get the pieces information from the peers
        try:
            requested_files = message.split()[1:]
            self.tracker_send_socket.sendall(message.encode())
            data = self.tracker_send_socket.recv(1024).decode()
            data = json.loads(data)
            print("[Tracker Response]")
            print(json.dumps(data, indent=4))
            # {'127.0.0.1:54782': {'ip_addr': '127.0.0.1', 'upload_port': 54781}, '127.0.0.1:54784': {'ip_addr': '127.0.0.1', 'upload_port': 54783}, 'tracker_ip': '127.0.0.1:8000'}
            request_pieces_obj: Dict[Tuple[str, int], Dict[str, List[str]]] = {}
            curr_pieces_info: Dict[str, List[str]] = {}
            display = {}
            request_queues: Dict[Tuple[str, int], List[str]] = {}
            for piece in self.pieces:
                curr_pieces_info.setdefault(piece.original_filename, []).append(
                    f"{piece.piece_id}"
                )

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
                    request_queues[(ip_addr, upload_port)] = []
                    display[str((ip_addr, upload_port))] = []
                    request_pieces_obj[(ip_addr, upload_port)] = pieces_info
            for file in requested_files:
                file_request_queue = NodeUtils.get_request_queue(
                    file, request_pieces_obj, curr_pieces_info
                )
                for peer, pieces in file_request_queue.items():
                    display[str(peer)].extend(pieces)
                    request_queues[peer].extend(pieces)

            print("[Final Request Queues]")
            print(json.dumps(display, indent=3))
            print("Downloading...")
            self.download_manager(request_queues)
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
        return json.loads(data)

    def download_manager(
        self, request_queues: Dict[Tuple[str, int], List[str]]
    ) -> None:
        progress_queue = Queue()
        download_threads = []

        for thread_id, (peer, request_queue) in enumerate(request_queues.items()):
            thread = threading.Thread(
                target=self.download,
                args=(thread_id, peer[0], peer[1], request_queue, progress_queue),
                daemon=True,
            )
            download_threads.append(thread)
            thread.start()

        max_queue_length = max(len(queue) for queue in request_queues.values())

        # Initialize tqdm progress bars for each peer
        bars = {
            peer: tqdm(
                total=len(request_queue),
                desc=f"{peer}",
                ncols=100,
                position=i,
                lock_args=False,
            )
            for i, (peer, request_queue) in enumerate(request_queues.items())
        }

        # Calculate total work
        total_work = sum(
            [len(request_queue) for request_queue in request_queues.values()]
        )

        completed_tasks = 0
        while completed_tasks < total_work:
            thread_id, progress = progress_queue.get(timeout=0.1)
            peer = list(request_queues.keys())[thread_id]
            if progress == 1:
                bars[peer].update(1)
                completed_tasks += 1

        for thread in download_threads:
            thread.join()

        for bar in bars.values():
            bar.close()

        print("Download completed")

    def download(
        self,
        thread_id: int,
        target_ip: str = "127.0.0.1",
        target_port: int = 0,
        piece_queue: list[str] = None,
        progress_queue: Queue = None,
    ) -> None:
        try:
            for piece_name in piece_queue:
                with socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM
                ) as download_socket:
                    piece_name = (
                        f"{piece_name}.txt"
                        if not piece_name.endswith(".txt")
                        else piece_name
                    )
                    download_socket.connect((target_ip, target_port))
                    download_socket.sendall(f"request {piece_name}".encode())

                    piece_data = b""
                    while True:
                        chunk = download_socket.recv(PIECE_SIZE)
                        if not chunk:
                            break
                        piece_data += chunk

                    if piece_data:
                        piece_path = os.path.join(TEMP_FOLDER, f"{piece_name}")
                        with open(piece_path, "wb") as piece_file:
                            piece_file.write(piece_data)
                        progress_queue.put((thread_id, 1))
                    else:
                        print(
                            f"[Error]: Failed to download {piece_name}, no data received"
                        )
                        continue

        except Exception as e:
            print(f"[Error]: Unexpected error during download: {e}")

    def node_command_shell(self) -> None:
        # Node command shell for user to interact with the node
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
                case "fetch":
                    self.fetch(cmd_input)
                case "exit":
                    break
                case _:
                    print("Unknown command")

    def close_sockets(self):
        # Closed all the sockets
        self.tracker_send_socket.close()
        self.upload_socket.close()

    def close(self):
        # Close the node by sending the close message to the tracker and remove all the pieces
        try:
            self.tracker_send_socket.settimeout(REQUEST_TIMEOUT)
            self.tracker_send_socket.sendall("close".encode())
        except Exception as e:
            print(f"[Error]: Failed to send close message to tracker: {e}")
        finally:
            self.close_sockets()
            for filename in os.listdir(PIECES_FOLDER):
                os.unlink(os.path.join(PIECES_FOLDER, filename))
            for filename in os.listdir(TEMP_FOLDER):
                os.unlink(os.path.join(TEMP_FOLDER, filename))
            multiprocessing.active_children()
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
    def get_request_queue(
        filename: str,
        request_obj: Dict[Tuple[str, int], Dict[str, List[str]]],
        curr_pieces_info: Dict[str, List[str]],
    ) -> Dict[tuple[str, int], List[str]]:
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
        # Command line parser for Node
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

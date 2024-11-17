import os
import json
import mmap
import math
import argparse
from piece import Piece
from typing import List, Tuple

DEFAULT_PIECE_SIZE = 512 * 1024


class NodeUtils:
    @staticmethod
    def generate_pieces_from_repo_files(
        folder_name: str = None,
        file_list: str = None,
        piece_size: int = DEFAULT_PIECE_SIZE,
    ) -> List[Piece]:
        # Generate Piece based on folder_name/{file_list}
        # If file_list is None, generate Piece of all files in folder_name

        file_names = (
            file_list
            if file_list is not None
            else [
                f
                for f in os.listdir(folder_name)
                if os.path.isfile(os.path.join(folder_name, f))
            ]
        )

        pieces = []

        for file_name in file_names:
            piece_id = 0
            file_path = os.path.join(folder_name, file_name)
            print(f"Generating pieces from {file_path}")
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
        file_names = (
            [file_name]
            if file_name is not None
            else [
                f
                for f in os.listdir(folder_name)
                if os.path.isfile(os.path.join(folder_name, f))
            ]
        )

        for file_name in file_names:
            file_path = os.path.join(folder_name, file_name)
            file_size = os.path.getsize(file_path)
            piece_count = math.ceil(file_size / piece_size)

            file_info[file_name] = {
                "file_size": file_size,
                "piece_size": piece_size,
                "piece_count": piece_count,
            }
            print(file_info)
        print("fasfsa")
        print(file_info)
        print("safasf")
        return json.dumps(file_info)

    @staticmethod
    def cli_parser() -> Tuple[str, int]:
        # Parser the args from command line and return (host, port) of tracker
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

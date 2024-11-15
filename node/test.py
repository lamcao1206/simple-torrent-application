import os
import math
from typing import Dict
import json

PIECE_SIZE = 512 * 1024


def generate_files_info(folder_name: str) -> Dict[str, int]:
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
    return file_info


res = generate_files_info("staging")
string = json.dumps(res)
result = json.loads(string)

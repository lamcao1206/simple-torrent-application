import os
import mmap

PIECE_SIZE = 512 * 1024  # 512KB
staging_folder = "staging"

file_names = os.listdir(staging_folder)

for file_name in file_names:
    print(file_name)
    piece_id = 0
    pieces = []

    file_path = os.path.join(staging_folder, file_name)
    with open(file_path, "r+b") as file:
        mmap_obj = mmap.mmap(file.fileno(), length=0, access=mmap.ACCESS_READ)
        while True:
            start = piece_id * PIECE_SIZE
            end = start + PIECE_SIZE
            piece = mmap_obj[start:end]
            # End sliding window
            if not piece:
                break
            piece_name = f"{os.path.basename(file_name).split('.')[0]}_{piece_id}.txt"
            pieces.append(piece_name)
            piece_id += 1
        mmap_obj.close()
    print(pieces)

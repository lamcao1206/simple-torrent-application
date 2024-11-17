import os
import mmap


def pieces_divine(file_name: str, piece_size: int, output_folder: str) -> None:
    """
    Make a copy of the file and divide the copy into pieces of specified size and store them in a folder.

    Args:
        file_name (str): The name of the file to divide.
        piece_size (int): The size of each piece in bytes.
        output_folder (str): The folder to store the pieces.
    """
    os.makedirs(output_folder, exist_ok=True)
    copy_file_name = f"copy_{os.path.basename(file_name)}"

    # Create a copy of the file using mmap
    with open(file_name, "r+b") as src_file:
        with open(copy_file_name, "wb") as dst_file:
            dst_file.write(src_file.read())

    piece_id = 0
    piece_names = []

    with open(copy_file_name, "r+b") as file:
        mmapped_obj = mmap.mmap(file.fileno(), length=0, access=mmap.ACCESS_READ)
        while True:
            start = piece_id * piece_size
            end = start + piece_size
            piece = mmapped_obj[start:end]
            if not piece:
                break
            piece_name = f"{os.path.basename(file_name).split('.')[0]}_{piece_id}.txt"
            piece_path = f"{output_folder}/{piece_name}"
            with open(piece_path, "wb") as piece_file:
                piece_file.write(piece)
            piece_names.append(piece_name)
            piece_id += 1
        mmapped_obj.close()

    print("Pieces created:")
    for name in piece_names:
        print(name)


def main() -> None:
    file_name = "400KB.txt"
    piece_size = 512 * 1024  # 512KB
    output_folder = "pieces"
    pieces_divine(file_name, piece_size, output_folder)


if __name__ == "__main__":
    main()

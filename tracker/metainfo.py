import hashlib
import yaml
import os


def create_metainfo(file_path, tracker_url, piece_length=512 * 1024):
    """
    Creates a metainfo (.torrent) file for the specified file.

    Args:
        file_path (str): The path to the file to be shared.
        tracker_url (str): The URL of the tracker.
        piece_length (int): The length of each piece in bytes.
    """
    pieces = []
    with open(file_path, "rb") as f:
        while chunk := f.read(piece_length):
            pieces.append(hashlib.sha1(chunk).hexdigest())

    metainfo = {
        "announce": tracker_url,
        "info": {
            "name": os.path.basename(file_path),
            "piece length": piece_length,
            "pieces": pieces,
            "length": os.path.getsize(file_path),
        },
    }

    with open(f"{file_path}.torrent", "w") as f:
        yaml.dump(metainfo, f)


if __name__ == "__main__":
    create_metainfo("file.txt", "http://localhost:8000")

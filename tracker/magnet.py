import hashlib


def generate_magnet(file_path):
    """
    Generates a magnet link for the specified file.

    Args:
        file_path (str): The path to the file to be shared.
    """
    with open(file_path, "rb") as f:
        file_hash = hashlib.sha1(f.read()).hexdigest()
    magnet_link = (
        f"magnet:?xt=urn:btih:{file_hash}&dn={file_path}&tr=http://localhost:8000"
    )
    print(magnet_link)


if __name__ == "__main__":
    generate_magnet("file.txt")

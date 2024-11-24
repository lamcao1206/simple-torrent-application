import os

REPO_FOLDER = "repo"
PIECES_FOLDER = "pieces"
TEMP_FOLDER = "temp"


def main() -> None:
    diretories = [REPO_FOLDER, TEMP_FOLDER, PIECES_FOLDER]
    for directory in diretories:
        os.makedirs(directory, exist_ok=True)

def combine_pieces(self, requested_files: List[str]) -> None:
    for file_name in requested_files:
        combined_file_path = os.path.join(REPO_FOLDER, file_name)
        with open(combined_file_path, "wb") as combined_file:
            piece_prefix = f"{file_name.split('.')[0]}_"  # e.g "1MB_"
            pieces = sorted(
                [f for f in os.listdir(TEMP_FOLDER) if f.startswith(piece_prefix)],
                key=lambda x: int(x.split("_")[1].split(".")[0]),
            )
            for piece in pieces:
                piece_path = os.path.join(TEMP_FOLDER, piece)
                with open(piece_path, "rb") as piece_file:
                    with mmap.mmap(
                        piece_file.fileno(), length=0, access=mmap.ACCESS_READ
                    ) as mmapped_file:
                        combined_file.write(mmapped_file)
        print(f"Combined file {file_name} created successfully in {REPO_FOLDER}")

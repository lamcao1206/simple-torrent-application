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

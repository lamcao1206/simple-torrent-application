import mmap
import random
import string

filename = "30MB.txt"
size = 30 * 1024 * 1024  # 400KB in bytes


def generate_random_text(size: int) -> str:
    num_chars = size // 2  # Each character is 1 byte in ASCII, so we divide by 2
    random_text = "".join(
        random.choices(string.ascii_letters + string.digits + " \n", k=num_chars)
    )
    return random_text


def generate_file(file_name: str, file_size: int) -> None:
    random_text = generate_random_text(file_size)

    # Create the file and write random text to it
    with open(file_name, "w") as file:
        file.write(random_text)

    # Open the file in read/write binary mode and ensure it is exactly the desired size
    with open(file_name, "r+b") as file:
        # Adjust the file size if necessary (truncate it to the exact size)
        file.truncate(file_size)

        # Memory-map the file with the exact size
        mmapped_obj = mmap.mmap(
            file.fileno(), length=file_size, access=mmap.ACCESS_WRITE
        )

        # Convert the random text to bytes
        encoded_text = random_text.encode("utf-8")

        # Ensure the encoded text matches the size of the file by truncating or padding
        if len(encoded_text) > file_size:
            encoded_text = encoded_text[:file_size]
        elif len(encoded_text) < file_size:
            # Pad the text with spaces or any other character to reach the desired file size
            encoded_text += b" " * (file_size - len(encoded_text))

        # Write the random text (converted to bytes) into the memory-mapped object
        mmapped_obj[:] = encoded_text

        # Close the memory-mapped object
        mmapped_obj.close()

    print(
        f"{file_name} of size {file_size} bytes has been created and filled with random text."
    )


def main():
    generate_file(filename, size)


if __name__ == "__main__":
    main()

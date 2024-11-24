import mmap
import random
import string


def generate_random_text(size: int) -> str:
    """
    Generate random text of a specified size.
    Each character is 1 byte in ASCII.
    """
    random_text = "".join(
        random.choices(string.ascii_letters + string.digits + " \n", k=size)
    )
    return random_text


def generate_file(file_name: str, file_size: int) -> None:
    """
    Generate a file of a specified size filled with random text using memory-mapping.
    """
    # Create the file and write placeholder data
    with open(file_name, "wb") as file:
        file.write(b"\0" * file_size)

    # Open the file in read/write binary mode
    with open(file_name, "r+b") as file:
        # Memory-map the file
        mmapped_obj = mmap.mmap(
            file.fileno(), length=file_size, access=mmap.ACCESS_WRITE
        )

        # Generate random text of the exact size
        random_text = generate_random_text(file_size).encode("utf-8")

        # Write the random text into the memory-mapped object
        mmapped_obj[:] = random_text

        # Close the memory-mapped object
        mmapped_obj.close()

    print(
        f"{file_name} of size {file_size} bytes has been created and filled with random text."
    )


def main():
    for i in range(1, 11):  # Generate files from 1MB to 10MB
        file_size = i * 1024 * 1024  # File size in bytes (1MB increments)
        filename = f"{i}MB.txt"  # Filename based on size
        generate_file(filename, file_size)


if __name__ == "__main__":
    main()

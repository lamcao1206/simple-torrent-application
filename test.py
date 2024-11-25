import socket

def is_socket_connected(sock):
    try:
        # If SO_ERROR is 0, no error is pending, and the socket is likely connected.
        err = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        return err == 0
    except Exception as e:
        return False

# Example usage
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    sock.connect(("172.20.10.7", 8000))
    print("Connected to tracker successfully.")
except Exception as e:
    print(f"Connection failed: {e}")

if is_socket_connected(sock):
    print("Socket is connected.")
else:
    print("Socket is not connected.")

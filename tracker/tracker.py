import socket
from threading import Thread
from typing import Dict, Tuple
import argparse
import json
import socket

BUFFER_SIZE = 1024
REQUEST_TIMEOUT = 3


class Peer:
    def __init__(
        self,
        ip_address: str = None,  # IP address for the peer
        peer_socket: socket.socket = None,
        peer_listening_port: int = None,
        peer_upload_port: int = None,
        peer_thread: Thread = None,
        file_info: Dict[str, int] = None,
    ) -> None:
        self.ip_address = ip_address
        self.peer_socket = peer_socket
        self.peer_listening_port = peer_listening_port
        self.peer_upload_port = peer_upload_port
        self.peer_thread = peer_thread
        self.file_info = file_info

    def close(self):
        self.peer_socket.close()
        with open("metainfo.json", "r+") as meta_file:
            meta_info = json.load(meta_file)

            # Loop through each file in the file_info dictionary to remove the peer from the nodes list
            for file_name in list(self.file_info.keys()):
                if file_name in meta_info:
                    node_address = f"{self.ip_address}:{self.peer_upload_port}"
                    # If the node address is in the nodes list, remove it
                    if node_address in meta_info[file_name]["nodes"]:
                        meta_info[file_name]["nodes"].remove(node_address)

                    # If no nodes are left for the file, remove the file entry
                    if len(meta_info[file_name]["nodes"]) == 0:
                        del meta_info[file_name]

            # Save the updated metadata back to the file
            meta_file.seek(0)
            json.dump(meta_info, meta_file, indent=3)
            meta_file.truncate()  # Remove any remaining data after the new content


class Tracker:
    def __init__(
        self, host: str = "127.0.0.1", port: int = 8000, max_nodes: int = 10
    ) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(max_nodes)

        self.peers: Dict[str, Peer] = {}
        self.node_serving_thread: Thread = Thread(target=self.node_serve, daemon=True)
        with open("metainfo.json", "w") as meta_file:
            tracker_addr = f"{self.sock.getsockname()[0]}:{self.sock.getsockname()[1]}"
            json.dump(
                {"tracker_addr": tracker_addr},
                meta_file,
                indent=3,
            )

    def start(self) -> None:
        self.node_serving_thread.start()
        self.tracker_command_shell()

    def node_serve(self) -> None:
        while True:
            try:
                node_socket, node_addr = self.sock.accept()
            except Exception as e:
                continue

            data = node_socket.recv(BUFFER_SIZE).decode()
            if data == "First Connection":
                peer_info: list[str] = (
                    node_socket.recv(BUFFER_SIZE).decode().split(" ", 3)
                )

                TrackerUtil.update_metainfo(
                    json.loads(peer_info[3]), peer_info[0], int(peer_info[2])
                )

                peer_thread: Thread = Thread(
                    target=self.handle_node_request,
                    args=[node_socket, node_addr],
                    daemon=True,
                )
                print(peer_info[3])

                self.peers[node_addr] = Peer(
                    ip_address=peer_info[0],  # IP Address of the peer
                    peer_socket=node_socket,  # Node socket for communication with that peer
                    peer_thread=peer_thread,  # Thread for handling that peer
                    peer_listening_port=int(peer_info[1]),  # Listening port of the peer
                    peer_upload_port=int(peer_info[2]),  # Upload port of the peer
                    file_info=json.loads(peer_info[3]),  # File information for the peer
                )

                print(f"[Connection]: {peer_info[0]}:{peer_info[1]} joined the network")
                peer_thread.start()

    def handle_node_request(self, node_socket: socket.socket, node_addr: str) -> None:
        print(node_addr)  # (IP, port)
        while True:
            data = ""
            try:
                data = node_socket.recv(BUFFER_SIZE).decode()
            except Exception as e:
                continue

            if data == "":
                continue

            command, *args = data.split()
            if command == "fetch":
                self.fetch_response(node_socket, args)
            elif command == "close":
                print(f"[Close]: {node_addr[0]}:{node_addr[1]} offline")
                self.remove_peer(node_addr)
                break
        node_socket.close()

    def fetch_response(self, node_socket: socket.socket, files_name: str) -> None:
        response = {}
        for file_name in files_name:  # fetch 3.txt 4.txt
            for peer in self.peers.values():
                if file_name in peer.file_info:
                    response[f"{peer.ip_address}:{peer.peer_listening_port}"] = {
                        "peer_ip": f"{peer.ip_address}:{peer.peer_listening_port}",
                        "ip_addr": peer.ip_address,
                        "upload_port": peer.peer_upload_port,
                    }
        tracker_ip = self.sock.getsockname()[0]
        tracker_port = self.sock.getsockname()[1]
        response["tracker_ip"] = f"{tracker_ip}:{tracker_port}"
        print(response)
        node_socket.send(json.dumps(response).encode())

    def remove_peer(self, peer_addr: str) -> None:
        if peer_addr in self.peers:
            try:
                self.peers[peer_addr].close()
            except Exception as e:
                print(f"[Error]: Failed to close peer at {peer_addr}: {e}")
            finally:
                del self.peers[peer_addr]
        else:
            print(f"[Warning]: Peer {peer_addr} not found")

    def list_command_shell(self) -> None:
        if len(self.peers) == 0:
            print("No peer connecting to tracker!")
            return

        for index, peer_addr in enumerate(self.peers.keys()):
            print(f"- [{index}] {str(peer_addr)}")

    def tracker_command_shell(self) -> None:
        while True:
            sock_name, sock_port = self.sock.getsockname()
            cmd_input = input()
            cmd_parts = cmd_input.split()

            if not cmd_parts:
                continue

            match cmd_parts[0]:
                case "list":
                    self.list_command_shell()
                case "exit":
                    break
                case _:
                    print("Unknown command")

    def close(self) -> None:
        self.sock.close()
        for peer in self.peers.values():
            peer.close()


class TrackerUtil:
    @staticmethod
    def update_metainfo(
        file_info: Dict[str, int], ip_address: str, upload_port: int
    ) -> bool:
        # Update file_info into meta_info:
        with open("metainfo.json", "r") as meta_file:
            meta_info = json.load(meta_file)
            for file_name, file_info in file_info.items():
                if file_name in meta_info:
                    meta_info[file_name]["nodes"].append(f"{ip_address}:{upload_port}")
                else:
                    meta_info[file_name] = file_info
                    meta_info[file_name]["nodes"] = [f"{ip_address}:{upload_port}"]

        with open("metainfo.json", "w") as meta_file:
            json.dump(meta_info, meta_file, indent=3)

    @staticmethod
    def cli_parser() -> Tuple[str, int, int]:
        parser = argparse.ArgumentParser(
            prog="Tracker", description="Init the tracker for file system"
        )
        parser.add_argument(
            "--host",
            default="127.0.0.1",
            help="Hostname of the tracker (default: 127.0.0.1)",
        )
        parser.add_argument(
            "--port",
            default=8000,
            type=int,
            help="Port number of the tracker (default: 8000)",
        )
        parser.add_argument(
            "--max-nodes",
            type=int,
            default=10,
            help="Maximum number of clients (default: 10)",
        )
        args = parser.parse_args()
        return (args.host, args.port, args.max_nodes)


def main() -> None:
    host, port, max_nodes = TrackerUtil.cli_parser()
    tracker = Tracker(host, port, max_nodes)
    try:
        tracker.start()
    except KeyboardInterrupt:
        print("\n[Exception]: Got Interrupt by Ctrl + C")
    except Exception as e:
        print(f"\n[Exception]: {e}")
    finally:
        tracker.close()


if __name__ == "__main__":
    main()

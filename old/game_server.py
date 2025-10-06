import threading
import socket
import time
from protocols import Protocols
from game import Game
from interactable import Interactable

class GameServer(Interactable):
    PORT = 13245
    def __init__(self):
        self.lobby_tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.shutdown_event = threading.Event()
        self.playing_games: list[Game] = []
        self.lobby_server_host_name: str = None

    def connect_to_lobby_server(self, host="127.0.0.1", port = 8888): 
        self.lobby_tcp_sock.connect((host, port))
        print(f"Connected to lobby server {host}:{port}")
        if self.receive_and_check_is_message_format_name(self.lobby_tcp_sock, Protocols.Response.WELCOME):
            print("Received welcome message from server.")  # Welcome message
        self.lobby_server_host_name = host
        
import threading
import socket
import time
from protocols import Protocols
from game import Game
from interactable import Interactable

class GameServer(Interactable):
    PORT = 13245
    def __init__(self):
        self.connection_tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.shutdown_event = threading.Event()
        self.playing_games: list[Game] = []

    def handle_lobby_server(self, lobby_sock: socket.socket):
        pass

    def handle_player(self, player_sock: socket.socket):
        pass

    def handle_connection(self, connect_socket: socket.socket, addr: tuple[str, int]):
        role, = self.receive_message_format_and_parse(connect_socket, Protocols.GameServerCommand.ROLE)
        if role == "LOBBY":
            self.handle_lobby_server(connect_socket)
        elif role == "PLAYER":
            self.handle_player(connect_socket)
        else:
            connect_socket.close()
    


    def start_server(self, host = "0.0.0.0", port = PORT):
        self.connection_tcp_sock.bind((host, port))
        self.connection_tcp_sock.listen(5)
        self.connection_tcp_sock.settimeout(1)  # 每 1 秒 timeout 一次
        print(f"[LISTENING] Server is listening on {host}:{port}")
        while not self.shutdown_event.is_set():
            try:
                connect_socket, addr = self.connection_tcp_sock.accept()
                client_handler = threading.Thread(target=self.handle_connection, args=(connect_socket, addr))
                client_handler.start()
                #print(f"[ACTIVE CONNECTIONS] {self.active_connections}")
            except socket.timeout:
                continue
        # for debug
        print("server stopping...")
        self.connection_tcp_sock.close()

    def start_server_and_listen_input(self, host = "0.0.0.0", port = PORT):
        server_thread = threading.Thread(target=self.start_server, args=(host, port,))
        server_thread.start()
        time.sleep(0.2)
        while True:
            cmd = input("Enter 'stop' to stop the server: ")
            if cmd == 'stop':
                self.shutdown_event.set()
                break
            else:
                print("invalid command.")
        server_thread.join()
        
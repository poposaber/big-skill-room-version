import socket
import threading
import json
import os
import time
from protocols import Protocols
from interactable import Interactable

USER_DB_FILE = 'user_db.json'
LOCK = threading.Lock()

USERNAME = "username"
IS_WAITING = "is_waiting"
IS_PLAYING = "is_playing"

class Server(Interactable):
    def __init__(self):
        self.lobby_tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.game_server_tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.active_connections = 0
        self.client_socket_user_dict = {} # client_socket: {USERNAME: <username>, IS_WAITING: bool, IS_PLAYING: bool}
        self.waiting_client_sockets = []
        self.user_db = self.load_user_db()
        self.shutdown_event = threading.Event()

    def load_user_db(self):
        if not os.path.exists(USER_DB_FILE):
            return {}
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
        
    def save_user_db(self):
        with open(USER_DB_FILE, 'w') as f:
            json.dump(self.user_db, f, indent=2)

    def help_register(self, client_socket: socket.socket, msg: str):
        username = self.parse_message(msg, Protocols.Command.REG_USERNAME)[0]
        #username = Protocols.Command.REG_USERNAME.parse(msg)[0]
        with LOCK:
            if username in self.user_db:
                self.send_message_format_args(client_socket, Protocols.Response.REG_USERNAME_RESULT, -1)
                return
                #client_socket.send(Protocols.Response.USERNAME_EXISTS.encode())
            self.send_message_format_args(client_socket, Protocols.Response.REG_USERNAME_RESULT, 0)

            rcvmsg, command = self.receive_and_get_format_name(client_socket)
            if command == Protocols.Command.REG_CANCEL.name:
                print("registration cancelled.")
                self.send_message_format(client_socket, Protocols.Response.REG_CANCELLED)
                return
            elif command == Protocols.Command.REG_PASSWORD.name:
                password = self.parse_message(rcvmsg, Protocols.Command.REG_PASSWORD)[0]
                self.user_db[username] = {"password": password, "games_played": 0, "games_won": 0}
                self.save_user_db()
                self.send_message_format(client_socket, Protocols.Response.REG_SUCCESS)
    
    def help_login(self, client_socket: socket.socket, msg: str):
        username, password = Protocols.Command.LOGIN.parse(msg)

        with LOCK:
            if username not in self.user_db or self.user_db[username]["password"] != password:
                self.send_message_format_args(client_socket, Protocols.Response.LOGIN_RESULT, -1)
            elif username in [self.client_socket_user_dict[sock][USERNAME] for sock in self.client_socket_user_dict.keys()]:
                self.send_message_format_args(client_socket, Protocols.Response.LOGIN_RESULT, -2)
            else:
                self.client_socket_user_dict[client_socket][USERNAME] = username
                self.send_message_format_args(client_socket, Protocols.Response.LOGIN_RESULT, 0)

    def help_logout(self, client_socket: socket.socket):
        self.client_socket_user_dict[client_socket] = None
        self.send_message_format(client_socket, Protocols.Response.LOGOUT_SUCCESS)

    def record_play(self, client_socket: socket.socket):
        self.user_db[self.client_socket_user_dict[client_socket][USERNAME]]["games_played"] += 1
        self.save_user_db()
        self.send_message_format(client_socket, Protocols.Response.PLAY_RECORD_DONE)

    def record_win(self, client_socket: socket.socket):
        self.user_db[self.client_socket_user_dict[client_socket][USERNAME]]["games_won"] += 1
        self.save_user_db()
        self.send_message_format(client_socket, Protocols.Response.WIN_RECORD_DONE)

    def send_status(self, client_socket: socket.socket):
        games_played = self.user_db[self.client_socket_user_dict[client_socket][USERNAME]]["games_played"]
        games_won = self.user_db[self.client_socket_user_dict[client_socket][USERNAME]]["games_won"]
        self.send_message_format_args(client_socket, Protocols.Response.STATUS_RESULT, games_played, games_won)

    def handle_client(self, client_socket: socket.socket, addr: tuple):
        self.client_socket_user_dict[client_socket] = {USERNAME: None, IS_WAITING: False, IS_PLAYING: False}
        self.active_connections += 1
        print(f"[NEW CONNECTION] {addr} connected.")
        self.send_message_format(client_socket, Protocols.Response.WELCOME)

        while True:
            try:
                msg, command = self.receive_and_get_format_name(client_socket)

                print(f"server msg: \"{msg}\"")
                print(f"command: \"{command}\"")

                match command:
                    case Protocols.Command.REG_USERNAME.name:
                        self.help_register(client_socket, msg)

                    case Protocols.Command.LOGIN.name:
                        self.help_login(client_socket, msg)

                    case Protocols.Command.LOGOUT.name:
                        self.help_logout(client_socket)

                    case Protocols.Command.EXIT.name:
                        self.send_message_format(client_socket, Protocols.Response.GOODBYE)
                        #client_socket.send(Protocols.Response.GOODBYE.encode())
                        break
                    case Protocols.Command.RECORD_WIN.name:
                        self.record_win(client_socket)
                        #client_socket.send(Protocols.Response.WIN_RECORD_DONE.encode())
                    case Protocols.Command.RECORD_PLAY.name:
                        self.record_play(client_socket)
                    case Protocols.Command.STATUS.name:
                        self.send_status(client_socket)
                    case _:
                        self.send_message_format(client_socket, Protocols.Response.UNKNOWN_COMMAND)
                        #client_socket.send(Protocols.Response.UNKNOWN_COMMAND.encode())
            except Exception as e:
                print(f"[EXCEPTION] {e}")
                break

        client_socket.close()
        self.client_socket_user_dict.pop(client_socket)
        self.active_connections -= 1
        print(f"[DISCONNECTED] {addr} disconnected.")
        print(f"[ACTIVE CONNECTIONS] {self.active_connections}")

    def start_server(self, host = "0.0.0.0", port = 8888):
        self.lobby_tcp_sock.bind((host, port))
        self.lobby_tcp_sock.listen(5)
        self.lobby_tcp_sock.settimeout(1)  # 每 1 秒 timeout 一次
        print(f"[LISTENING] Server is listening on {host}:{port}")
        while not self.shutdown_event.is_set():
            try:
                client_socket, addr = self.lobby_tcp_sock.accept()
                client_handler = threading.Thread(target=self.handle_client, args=(client_socket, addr))
                client_handler.start()
                print(f"[ACTIVE CONNECTIONS] {self.active_connections}")
            except socket.timeout:
                continue
        # for debug
        print("server stopping...")
        self.lobby_tcp_sock.close()

    def start_server_and_listen_input(self, host = "0.0.0.0", port = 8888):
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

import socket
import threading
import json
import os
import time
from protocols import Protocols
from interactable import Interactable
from user_info import UserInfo

USER_DB_FILE = 'user_db.json'
LOCK = threading.Lock()

class LobbyServer(Interactable):
    def __init__(self):
        self.connection_tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_user_dict: dict[socket.socket, UserInfo] = {}
        self.shutdown_event = threading.Event()
        self.user_db = self.load_user_db()

    def load_user_db(self):
        if not os.path.exists(USER_DB_FILE):
            return {}
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
        
    def save_user_db(self):
        with open(USER_DB_FILE, 'w') as f:
            json.dump(self.user_db, f, indent=2)

    def help_login(self, client_socket: socket.socket, msg: str):
        username, password = Protocols.UserToLobby.LOGIN.parse(msg)

        with LOCK:
            if username not in self.user_db or self.user_db[username]["password"] != password:
                self.send_message_format_args(client_socket, Protocols.LobbyToUser.LOGIN_RESULT, -1)
            elif username in [self.socket_user_dict[s].name for s in self.socket_user_dict.keys()]:
                self.send_message_format_args(client_socket, Protocols.LobbyToUser.LOGIN_RESULT, -2)
            else:
                self.socket_user_dict[client_socket].name = username
                self.send_message_format_args(client_socket, Protocols.LobbyToUser.LOGIN_RESULT, 0)

    def help_logout(self, client_socket: socket.socket):
        if self.socket_user_dict[client_socket].name is None:
            self.send_message_format_args(client_socket, Protocols.LobbyToUser.LOGOUT_RESULT, -1)
        else:
            self.socket_user_dict[client_socket].reset()
            self.send_message_format_args(client_socket, Protocols.LobbyToUser.LOGOUT_RESULT, 0)

    def help_register(self, client_socket: socket.socket, msg: str):
        username, = self.parse_message(msg, Protocols.UserToLobby.REG_NAME)
        with LOCK:
            if username in self.user_db:
                self.send_message_format_args(client_socket, Protocols.LobbyToUser.REG_NAME_RESULT, -1)
                return
                #client_socket.send(Protocols.Response.USERNAME_EXISTS.encode())
            self.send_message_format_args(client_socket, Protocols.LobbyToUser.REG_NAME_RESULT, 0)

            rcvmsg, command = self.receive_and_get_format_name(client_socket)
            if command == Protocols.UserToLobby.REG_CANCEL.name:
                print("registration cancelled.")
                self.send_message_format(client_socket, Protocols.LobbyToUser.REG_CANCELED)
                return
            elif command == Protocols.UserToLobby.REG_PASSWORD.name:
                password, = self.parse_message(rcvmsg, Protocols.UserToLobby.REG_PASSWORD)
                self.user_db[username] = {"password": password, "games_played": 0, "games_won": 0}
                self.save_user_db()
                self.send_message_format_args(client_socket, Protocols.LobbyToUser.REG_PASSWORD_RESULT, 0)

    def make_waiting(self, client_socket: socket.socket):
        if self.socket_user_dict[client_socket].name is None:
            self.send_message_format_args(client_socket, Protocols.LobbyToUser.WAIT_RESULT, -1)
        elif self.socket_user_dict[client_socket].is_waiting:
            self.send_message_format_args(client_socket, Protocols.LobbyToUser.WAIT_RESULT, -1)
        else:
            self.socket_user_dict[client_socket].is_waiting = True
            self.send_message_format_args(client_socket, Protocols.LobbyToUser.WAIT_RESULT, 0)

    def make_unwaiting(self, client_socket: socket.socket):
        if self.socket_user_dict[client_socket].name is None:
            self.send_message_format_args(client_socket, Protocols.LobbyToUser.UNWAIT_RESULT, -1)
        elif not self.socket_user_dict[client_socket].is_waiting:
            self.send_message_format_args(client_socket, Protocols.LobbyToUser.UNWAIT_RESULT, -1)
        else:
            self.socket_user_dict[client_socket].is_waiting = False
            self.send_message_format_args(client_socket, Protocols.LobbyToUser.UNWAIT_RESULT, 0)

    def handle_client(self, client_socket: socket.socket, addr: tuple[str, int]):
        try:
            role, = self.receive_message_format_and_parse(client_socket, Protocols.UserToLobby.ROLE)
            if role == "user":
                self.handle_user(client_socket, addr)
            elif role == "gameserver":
                self.handle_game_server(client_socket, addr)

        except Exception as e:
            print(f"Exception in handle_client: {e}")

        client_socket.close()
        
    def handle_user(self, user_socket: socket.socket, addr: tuple[str, int]):
        self.socket_user_dict[user_socket] = UserInfo()
        print(f"[NEW USER CONNECTION] {addr} connected.")
        print(f"[ACTIVE USER CONNECTIONS] {len(self.socket_user_dict)}")
        self.send_message_format(user_socket, Protocols.LobbyToUser.WELCOME_USER)

        while True:
            try:
                msg, command = self.receive_and_get_format_name(user_socket)

                print(f"server msg: \"{msg}\"")
                print(f"command: \"{command}\"")

                match command:
                    case Protocols.UserToLobby.LOGIN.name:
                        self.help_login(user_socket, msg)

                    case Protocols.UserToLobby.LOGOUT.name:
                        self.help_logout(user_socket)

                    case Protocols.UserToLobby.REG_NAME.name:
                        self.help_register(user_socket, msg)

                    case Protocols.UserToLobby.EXIT.name:
                        self.send_message_format(user_socket, Protocols.LobbyToUser.GOODBYE)
                        break

                    case Protocols.UserToLobby.WAIT.name:
                        self.make_waiting(user_socket)

                    case Protocols.UserToLobby.UNWAIT.name:
                        self.make_unwaiting(user_socket)

                    case _:
                        self.send_message_format(user_socket, Protocols.LobbyToUser.UNKNOWN_COMMAND)
            except Exception as e:
                print(f"[EXCEPTION] {e}")
                break
        
        self.socket_user_dict.pop(user_socket)
        print(f"[USER DISCONNECTED] {addr} disconnected.")
        print(f"[ACTIVE USER CONNECTIONS] {len(self.socket_user_dict)}")

    def handle_game_server(self, game_server_socket: socket.socket, addr: tuple[str, int]):
        pass

    def start_server(self, host = "0.0.0.0", port = 8888):
        self.connection_tcp_sock.bind((host, port))
        self.connection_tcp_sock.listen(5)
        self.connection_tcp_sock.settimeout(1)  # 每 1 秒 timeout 一次
        print(f"[LISTENING] Server is listening on {host}:{port}")
        while not self.shutdown_event.is_set():
            try:
                client_socket, addr = self.connection_tcp_sock.accept()
                client_handler = threading.Thread(target=self.handle_client, args=(client_socket, addr))
                client_handler.start()
            except socket.timeout:
                continue
        # for debug
        print("server stopping...")
        self.connection_tcp_sock.close()

    def start(self, host = "0.0.0.0", port = 8888):
        server_thread = threading.Thread(target=self.start_server, args=(host, port,))
        server_thread.start()
        time.sleep(0.2)
        try:
            while True:
                cmd = input("Enter 'stop' to stop the server: ")
                if cmd == 'stop':
                    self.shutdown_event.set()
                    break
                else:
                    print("invalid command.")
        except KeyboardInterrupt:
            self.shutdown_event.set()

        server_thread.join()
        
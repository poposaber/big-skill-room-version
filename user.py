import socket
import threading
import time
import getpass
from protocols import Protocols
from game import Game
from interactable import Interactable
from message_format import MessageFormat
from user_info import UserInfo
import os
import queue

class User(Interactable):
    def __init__(self):
        self.info = UserInfo()

        self.lobby_tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.game_tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.response_queue = queue.Queue()
        self.event_queue = queue.Queue()

    def connect_to_lobby_server(self, host="127.0.0.1", port = 8888): 
        self.lobby_tcp_sock.connect((host, port))
        print(f"Connected to lobby server {host}:{port}")
        self.send_message_format_args(self.lobby_tcp_sock, Protocols.UserToLobby.ROLE, "user")
        if self.receive_and_check_is_message_format_name(self.lobby_tcp_sock, Protocols.LobbyToUser.WELCOME_USER):
            print("Received welcome message from server.")

    def print_prompt(self):
        print()
        print()
        print("Commands you can type:")
        print()
        if not self.info.name:
            print("register: register an account")
            print("login: log in an account")
            print("exit: exit the lobby server and close.")
            print()
            print("You are not logged in yet. Enter command: >>>>>>>>>> ", end="")
        else:
            print("logout: log out your account")
            print("exit: exit the lobby server and close.")
            print()
            print(f"{self.info.name}, enter command: >>>>>>>>>> ", end="")

    def register(self):
        pass

    def login(self):
        pass

    def exit_lobby_server(self):
        self.send_message_format(self.lobby_tcp_sock, Protocols.UserToLobby.EXIT)
        if self.receive_and_check_is_message_format_name(self.lobby_tcp_sock, Protocols.LobbyToUser.GOODBYE):
            print("Exiting the client.")

    def logout(self):
        pass

    def get_from_event_queue(self) -> tuple[int, str]:
        try:
            event_num, username = self.event_queue.get()
            return event_num, username
        except Exception as e:
            print(f"Exception at get_from_event_queue: {e}")
            raise e
        
    def put_to_event_queue(self, event_num: int, username: str):
        try:
            self.event_queue.put((event_num, username))
        except Exception as e:
            print(f"Exception at put_to_event_queue: {e}")
            raise e
        
    def get_from_response_queue(self) -> str:
        try:
            msg = self.response_queue.get()
            return msg
        except Exception as e:
            print(f"Exception at get_from_response_queue: {e}")
            raise e
        
    def put_to_response_queue(self, msg: str):
        try:
            self.response_queue.put(msg)
        except Exception as e:
            print(f"Exception at put_to_response_queue: {e}")
            raise e

    def send_to_lobby(self, msg_fmt: MessageFormat, *args):
        try:
            print(f"sending {msg_fmt.name}, {list(args)} to lobby server.")
            self.send_message_format_args(self.lobby_tcp_sock, msg_fmt, *args)
        except Exception as e:
            print(f"exception in send_to_lobby: {e}")
            raise e

    def receive_from_lobby_and_separate(self):
        try:
            msg, name = self.receive_and_get_format_name(self.lobby_tcp_sock)
            if name == Protocols.LobbyToUser.EVENT.name:
                event_num, username = self.parse_message(msg, Protocols.LobbyToUser.EVENT)
                self.put_to_event_queue(event_num, username)
            else:
                self.put_to_response_queue(msg)
        except Exception as e:
            print(f"exception in receive_from_lobby_and_separate: {e}")
            raise e
        
    def receive_response_with_name(self) -> tuple[str, str]:
        msg = self.get_from_response_queue()
        name = self.check_message_format_name(msg)
        return msg, name
    
    def receive_response_and_parse(self, msg_fmt: MessageFormat) -> list:
        msg, _ = self.receive_response_with_name()
        return self.parse_message(msg, msg_fmt)
    
    def receive_event(self) -> tuple[int, str]:
        event_num, username = self.get_from_event_queue()
        return event_num, username
                


    def get_input(self):
        while True:
            self.print_prompt()
            cmd = input().strip().lower()
            if not cmd:
                print("Please enter a valid command.")
                continue
            match cmd:
                case "register":
                    if self.info.name:
                        print("Logged in users cannot register.")
                        continue
                    self.register()
                case "login":
                    if self.info.name:
                        print("You are already logged in.")
                        continue
                    self.login()
                case "exit":
                    self.exit_lobby_server()
                    break
                case "logout":
                    if not self.info.name:
                        print("You are not loggin in yet.")
                    self.logout()
    def start(self, host = "127.0.0.1", port = 8888):
        self.connect_to_lobby_server(host, port)
        lobby_msg_recver = threading.Thread(target=self.receive_from_lobby_and_separate)
        lobby_msg_recver.start()
        event_receiver = threading.Thread(target=self.receive_event)
        self.get_input()


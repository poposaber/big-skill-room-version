import socket
import threading
import time
import getpass
from protocols import Protocols
from game import Game
from interactable import Interactable
import os
import queue

class User(Interactable):
    def __init__(self):
        self.name = None
        self.is_waiting = False
        self.inviting_users: list[str] = None
        self.users_inviting_me: list[str] = None
        self.playing_game: Game = None

        self.lobby_tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.game_tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.send_queue = queue.Queue()
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
        if not self.name:
            print("register: register an account")
            print("login: log in an account")
            print("exit: exit the lobby server and close.")
            print()
            print("You are not logged in yet. Enter command: >>>>>>>>>> ", end="")
        else:
            print("logout: log out your account")
            print("exit: exit the lobby server and close.")
            print()
            print(f"{self.name}, enter command: >>>>>>>>>> ", end="")

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

    def get_input(self):
        while True:
            self.print_prompt()
            cmd = input().strip().lower()
            if not cmd:
                print("Please enter a valid command.")
                continue
            match cmd:
                case "register":
                    if self.name:
                        print("Logged in users cannot register.")
                        continue
                    self.register()
                case "login":
                    if self.name:
                        print("You are already logged in.")
                        continue
                    self.login()
                case "exit":
                    self.exit_lobby_server()
                    break
                case "logout":
                    if not self.name:
                        print("You are not loggin in yet.")
                    self.logout()
    def start(self, host = "127.0.0.1", port = 8888):
        self.connect_to_lobby_server(host, port)
        self.get_input()


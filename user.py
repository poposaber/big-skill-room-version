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

        self.response_queue: queue.Queue[str] = queue.Queue()
        self.event_queue: queue.Queue[tuple[int, str]] = queue.Queue()
        self.terminate_event = threading.Event()

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
            print()
            print("You are not logged in yet. Enter command: >>>>>>>>>> ", end="")
        else:
            print("logout: log out your account")
            print("exit: exit the lobby server and close.")
            print()
            print()
            print(f"{self.info.name}, enter command: >>>>>>>>>> ", end="")

    def register(self):
        name_registered = False
        try:
            while not name_registered:
                temp_user_name = input("Enter your user name (or press Ctrl+C to cancel): ")
                self.send_to_lobby(Protocols.UserToLobby.REG_NAME, temp_user_name)
                response, = self.receive_response_and_parse(Protocols.LobbyToUser.REG_NAME_RESULT)
                if response == 0: #register success
                    name_registered = True
                    print("Username accepted. Now please set your password.")
                elif response == -1:
                    print("Registration failed. Username taken.")
                else:
                    print("Received unknown server response")

            while True:
                temp_password = getpass.getpass("Enter your password (or press Ctrl+C to cancel): ")
                confirm_password = getpass.getpass("Confirm your password (or press Ctrl+C to cancel): ")
                if temp_password != confirm_password:
                    print("Passwords do not match.")
                    continue
                self.send_to_lobby(Protocols.UserToLobby.REG_PASSWORD, temp_password)
                response, = self.receive_response_and_parse(Protocols.LobbyToUser.REG_PASSWORD_RESULT)
                if response == 0: #register success
                    print("Registration successful. You can now log in with this account.")
                elif response == -1:
                    print("Registration failed. Weak password.")
                else:
                    print("Received unknown server response")
        except KeyboardInterrupt:
            if name_registered:
                print("\nCancelling registration. Deleting the partially registered account.")
                self.send_to_lobby(Protocols.UserToLobby.REG_CANCEL)
                _, name = self.receive_response_with_name()
                if name == Protocols.LobbyToUser.REG_CANCELED.name:
                    print("Registration cancelled.")
                else:
                    print("Received unknown server response")
            else:
                print("\nCancelling registration.")
        except Exception as e:
            print(f"exception in register: {e}")
            raise e

    def login(self):
        temp_user_name = input("Enter your user name: ")
        temp_password = getpass.getpass("Enter your password: ")
        try:
            self.send_to_lobby(Protocols.UserToLobby.LOGIN, temp_user_name, temp_password)
            response, = self.receive_response_and_parse(Protocols.LobbyToUser.LOGIN_RESULT)
            if response == 0: #login success
                self.info.name = temp_user_name
                print("Login successful. You can now do further actions to play games.")
            elif response == -1:
                print("Login failed. Invalid username or password.")
            elif response == -2:
                print("Login failed. Another client is using this account.")
            else:
                print("Received unknown server response")
        except Exception as e:
            print(f"exception in login: {e}")
            raise e

    def exit_lobby_server(self):
        self.send_to_lobby(Protocols.UserToLobby.EXIT)
        _, name = self.receive_response_with_name()
        if name == Protocols.LobbyToUser.GOODBYE.name:
            print("Exiting the client.")

    def logout(self):
        self.send_to_lobby(Protocols.UserToLobby.LOGOUT)
        response, = self.receive_response_and_parse(Protocols.LobbyToUser.LOGOUT_RESULT)
        if response == 0:
            print("Logout successful.")
            self.info.reset()
        elif response == -1:
            print("Logout failed. You are not logged in yet.")
        else:
            print("Received unknown server response")

    def send_to_lobby(self, msg_fmt: MessageFormat, *args):
        try:
            print(f"sending {msg_fmt.name}, {list(args)} to lobby server.")
            self.send_message_format_args(self.lobby_tcp_sock, msg_fmt, *args)
        except Exception as e:
            print(f"exception in send_to_lobby: {e}")

    def receive_from_lobby_and_separate(self):
        while not self.terminate_event.is_set():
            try:
                msg, name = self.receive_and_get_format_name(self.lobby_tcp_sock)
                if name == Protocols.LobbyToUser.EVENT.name:
                    event_num, username = self.parse_message(msg, Protocols.LobbyToUser.EVENT)
                    self.event_queue.put((event_num, username))
                else:
                    self.response_queue.put(msg)
            except ConnectionResetError as e:
                print(f"Connection to lobby server lost: {e}")
                break
            except Exception as e:
                print(f"exception in receive_from_lobby_and_separate: {e}")
        
    def receive_response_with_name(self) -> tuple[str, str]:
        """message, name"""
        msg = self.response_queue.get()
        name = self.check_message_format_name(msg)
        print(f"msg: {msg}, name: {name}")
        return msg, name
    
    def receive_response_and_parse(self, msg_fmt: MessageFormat) -> list:
        msg, _ = self.receive_response_with_name()
        return self.parse_message(msg, msg_fmt)
    
    def receive_event(self):
        while not self.terminate_event.is_set():
            try:
                event_num, username = self.event_queue.get(timeout=0.5)
                match event_num:
                    case 0:
                        print(f"Invitation from {username}")
                    case 1:
                        print(f"{username} accepted your invitation.")
                    case _:
                        print(f"Unknown event {event_num} from {username}")
            except queue.Empty:
                continue

    def get_input(self):
        while not self.terminate_event.is_set():
            try:
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
                        self.close()
                    case "logout":
                        if not self.info.name:
                            print("You are not loggin in yet.")
                            continue
                        self.logout()
                    case _:
                        print("Unknown command. Please try again.")
            except Exception as e:
                print(f"exception in get_input: {e}")
    
    def close(self):
        self.terminate_event.set()
        time.sleep(0.3)  # wait for threads to terminate
        self.lobby_tcp_sock.close()
        self.game_tcp_sock.close()


    def start(self, host = "127.0.0.1", port = 8888):
        self.connect_to_lobby_server(host, port)
        lobby_msg_separater = threading.Thread(target=self.receive_from_lobby_and_separate)
        lobby_msg_separater.start()
        event_receiver = threading.Thread(target=self.receive_event)
        event_receiver.start()

        self.get_input()
        print("Client stopping...")
        lobby_msg_separater.join()
        event_receiver.join()
        print("Client stopped.")
        #os.system("pause")



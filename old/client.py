import socket
import threading
import time
import getpass
from protocols import Protocols
from game import Game
from interactable import Interactable
import os
import queue

LOCK = threading.Lock()
MAX_CNP_COUNT = 100

class Client(Interactable):
    def __init__(self):
        self.user_name = None
        self.waiting_invitations = False
        self.acceptances_waiting = [] # list of user_names
        self.found_players = {} # player: (ip, port)
        self.received_invitations = {} # inviter: (ip, port)
        self.stop_waiting_invitation_event = threading.Event()
        self.stop_waiting_acceptance_event = threading.Event()

        self.lobby_server_host_name: str = None
        self.lobby_tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.game_server_tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.game_client_tcp_sock = None
        self.scan_udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.invite_udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.wait_udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.about_to_enter_game = False

        self.is_player_a = True  # True if player A, False if player B
        self.send_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.event_queue = queue.Queue()

    def connect_to_lobby_server(self, host="127.0.0.1", port = 8888): 
        self.lobby_tcp_sock.connect((host, port))
        print(f"Connected to lobby server {host}:{port}")
        self.send_message_format_args(self.lobby_tcp_sock, Protocols.Command.ROLE, "user")
        if self.receive_and_check_is_message_format_name(self.lobby_tcp_sock, Protocols.Response.WELCOME):
            print("Received welcome message from server.")  # Welcome message
        self.lobby_server_host_name = host

    def login(self):
        temp_user_name = input("Enter your user name: ")
        temp_password = getpass.getpass("Enter your password: ")
        try:
            self.send_message_format(self.lobby_tcp_sock, Protocols.Command.LOGIN, [temp_user_name, temp_password])
            response, = self.receive_message_format_and_parse(self.lobby_tcp_sock, Protocols.Response.LOGIN_RESULT)
            if response == 0: #login success
                self.user_name = temp_user_name
                print("Login successful. You can now do further actions to play games.")
            elif response == -1:
                print("Login failed. Invalid username or password.")
            elif response == -2:
                print("Login failed. Another client is using this account.")
            else:
                print("Received unknown server response")
            
        except Exception as e:
            raise e
        
    def logout(self):
        if self.waiting_invitations:
            self.stop_waiting_invitations()
        if self.acceptances_waiting:
            self.stop_waiting_acceptances()
        self.send_message_format(self.lobby_tcp_sock, Protocols.Command.LOGOUT)
        if self.receive_and_check_is_message_format_name(self.lobby_tcp_sock, Protocols.Response.LOGOUT_SUCCESS):
            self.user_name = None
            print("You have logged out successfully.")
        else:
            print("Received unknown server response")

        
    def register(self):
        while True:
            try:
                temp_user_name = input("Enter your user name (or type \'/cancel\' to cancel registration.): ")
                if temp_user_name == "/cancel":
                    print("registration cancelled.")
                    return
                self.send_message_format_args(self.lobby_tcp_sock, Protocols.Command.REG_USERNAME, temp_user_name)
                reg_result, = self.receive_message_format_and_parse(self.lobby_tcp_sock, Protocols.Response.REG_USERNAME_RESULT)
                if reg_result == 0:
                    #print("User name is usable!")
                    break
                elif reg_result == -1:
                    print("User name is used by others. Use another one.")
            except Exception as e:
                print(f"User name is not usable: {e}")

        while True:
            temp_password = getpass.getpass("Enter your password (or type \'/cancel\' to cancel registration.): ")
            if temp_password == "/cancel":
                self.send_message_format(self.lobby_tcp_sock, Protocols.Command.REG_CANCEL)
                if not self.receive_and_check_is_message_format_name(self.lobby_tcp_sock, Protocols.Response.REG_CANCELLED):
                    print("Unknown message. Expected REG_CANCELLED")
                print("registration cancelled.")
                return
            # not natural
            try:
                Protocols.Command.REG_PASSWORD.build_args(temp_password)
            except Exception as e:
                print(f"Invalid password: {e}")
                continue

            temp_confirm_password = getpass.getpass("Enter your password one more time: ")
            if temp_password == temp_confirm_password:
                break
            print("Password not the same.")
        try:
            #self.lobby_tcp_sock.send((Protocols.Command.REGISTER + f" {temp_user_name} {temp_password}").encode())
            self.send_message_format_args(self.lobby_tcp_sock, Protocols.Command.REG_PASSWORD, temp_password)
            reg_success = self.receive_and_check_is_message_format_name(self.lobby_tcp_sock, Protocols.Response.REG_SUCCESS)
            if reg_success:
                print("Register Success! Please login again.")
            else:
                print("Register failed. Please try again")
        except Exception as e:
            raise e
        
    def exit_server(self):
        if self.waiting_invitations:
            self.stop_waiting_invitations()
        if self.acceptances_waiting:
            self.stop_waiting_acceptances()
        self.send_message_format(self.lobby_tcp_sock, Protocols.Command.EXIT)
        if self.receive_and_check_is_message_format_name(self.lobby_tcp_sock, Protocols.Response.GOODBYE):
            print("Exiting the client.")

    def check_status(self):
        self.send_message_format(self.lobby_tcp_sock, Protocols.Command.STATUS)
        games_played, games_won = self.receive_message_format_and_parse(self.lobby_tcp_sock, Protocols.Response.STATUS_RESULT)
        print()
        print("===== Player Status =====")
        print(f"Player name: {self.user_name}")
        print(f"Games played: {games_played}")
        print(f"Games won: {games_won}")
        win_rate_text = f"{round(games_won / games_played * 100, ndigits=1)}%" if games_played != 0 else "undetermined"
        print(f"Win rate: {win_rate_text}")
        print("=========================")

    def close(self):
        self.lobby_tcp_sock.close()
        self.game_server_tcp_sock.close()
        self.invite_udp_sock.close()
        self.wait_udp_sock.close()

    def stop_waiting_invitations(self):
        self.received_invitations.clear()
        self.stop_waiting_invitation_event.set()
        time.sleep(1)
        self.stop_waiting_invitation_event.clear()
        #self.waiting_invitations = False
        print("You have stopped waiting for invitations.\n")

    def stop_waiting_acceptances(self):
        self.stop_waiting_acceptance_event.set()
        time.sleep(1)
        self.stop_waiting_acceptance_event.clear()
        self.acceptances_waiting.clear()
        #self.waiting_acceptances = False
        print("You have stopped waiting for acceptances.\n")

    # def stop_waiting_invitations_and_acceptances(self):
    #     with LOCK:
    #         self.received_invitations = {}
    #         #self.acceptances_waiting.clear()
    #     self.stop_waiting_invitation_event.set()
    #     self.stop_waiting_acceptance_event.set()
    #     time.sleep(1)
    #     self.stop_waiting_invitation_event.clear()
    #     self.stop_waiting_acceptance_event.clear()
    #     print("You have stopped waiting for invitations and acceptances.\n")

    def clear_messages(self, sock: socket.socket):
        while True:
            try:
                sock.settimeout(0.3)
                data, addr = sock.recvfrom(1024)
                msg = data.decode()
                # for debug
                #print(f"cleared msg: {msg} from {addr}.")
            except socket.timeout:
                sock.settimeout(None)
                #print("clean done.")
                return


    def wait_for_invitations_and_connect_game(self):
        try:
            self.send_message_format_to_lobby_server(Protocols.Command.WAIT)
            if not self.receive_check_is_format_name_from_lobby_server(Protocols.Response.WAIT_DONE):
                print("did not receive WAIT_DONE.")
            
        except Exception as e:
            print(f"Error in wait for invitation: {e}")

        # port = 10001
        # while True:
        #     try:
        #         self.wait_udp_sock.bind(("", port))
        #         break
        #     except OSError:
        #         port += 1
        #         if port > 65535:
        #             print("No available UDP ports to bind.")
        #             return
        # print(f"Listening for invitations on UDP port {port}. You can type 'unwait' to stop waiting.")
        # self.clear_messages(self.wait_udp_sock)
        # self.waiting_invitations = True
        # while not self.stop_waiting_invitation_event.is_set():
        #     try:
        #         self.wait_udp_sock.settimeout(0.5)
        #         msg, fname, addr = self.receive_and_get_format_name_from(self.wait_udp_sock)

        #         match fname:
        #             case Protocols.P2P.SCAN.name:
        #                 self.send_message_format_args_to(self.wait_udp_sock, Protocols.P2P.PLAYER_HERE, addr, self.user_name)
        #             case Protocols.P2P.INVITE.name:
        #                 inviter, = self.parse_message(msg, Protocols.P2P.INVITE)
        #                 self.received_invitations[inviter] = addr
        #                 print(f"\nReceived invitation from {inviter} at {addr}. Type \'accept\' or \'decline\' to accept or decline invitations .")
        #             case Protocols.P2P.CONNECT.name:
        #                 ip, tcp_port = self.parse_message(msg, Protocols.P2P.CONNECT)
        #                 print()
        #                 with LOCK:
        #                     self.game_client_tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #                     self.game_client_tcp_sock.connect((ip, tcp_port))
        #                 self.is_player_a = False

        #                 print(f"\nReceived game connection details: IP {ip}, TCP Port {tcp_port}. You can enter 'entergame' to start the game session.\n")
                        
        #                 self.send_message_format(self.lobby_tcp_sock, Protocols.Command.RECORD_PLAY)
        #                 if not self.receive_and_check_is_message_format_name(self.lobby_tcp_sock, Protocols.Response.PLAY_RECORD_DONE):
        #                     print("Did not receive PLAY_RECORD_DONE")
        #                 time.sleep(0.1)
        #                 self.about_to_enter_game = True
        #                 break
        #             case Protocols.P2P.ALREADY_IN_GAME.name:
        #                 decliner, = self.parse_message(msg, Protocols.P2P.ALREADY_IN_GAME)
        #                 print(f"{decliner} is already in game. Please invite later.")
        #             case _:
        #                 print(f"Unknown UDP message received: {msg} from {addr}")
        #     except socket.timeout:
        #         continue
        #     except Exception as e:
        #         print(f"Error receiving invitation: {e}")
        #         break
        # self.waiting_invitations = False
        # with LOCK:
        #     self.received_invitations.clear()
        # # if self.about_to_enter_game:
        # #     self.stop_waiting_invitations()
        # #for debug
        # #print("wait_udp_sock stopped waiting.")
        # self.wait_udp_sock.close()
        # self.wait_udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # #self.stop_waiting_invitation_event.clear()

    def scan(self, target_ip = "127.0.0.1", start_port=10001, end_port=65535):
        # scan_msg = "SCAN"
        port = start_port
        conti_no_player_count = 0
        self.found_players = {}
        while port <= end_port and conti_no_player_count < MAX_CNP_COUNT:
            try:
                self.scan_udp_sock.settimeout(0.1)
                self.send_message_format_to(self.scan_udp_sock, Protocols.P2P.SCAN, (target_ip, port))

                rcvmsg, fname, addr = self.receive_and_get_format_name_from(self.scan_udp_sock)
                if fname == Protocols.P2P.PLAYER_HERE.name: # if response.startswith("PLAYER"):
                    player_name, = self.parse_message(rcvmsg, Protocols.P2P.PLAYER_HERE)
                    self.found_players[player_name] = addr
                    print(f"Found player: {player_name} at {addr}")
                    conti_no_player_count = 0
                else:
                    conti_no_player_count += 1
            except socket.timeout:
                conti_no_player_count += 1
            except Exception as e:
                conti_no_player_count += 1

            port += 1
            # for debug
            #print(f"port: {port}, conti_no_player_count: {conti_no_player_count}")
        
        if self.found_players:
            print("Waiting player(s) found. Type \'invite\' to invite them. ")
        else:
            print("No players found.")

    def invite(self) -> str:
        if not self.found_players:
            print("No players found to invite. Please scan for players first.")
            return None
        invite_enum_list = list(self.found_players.items())
        print("Found players:")
        for i, (player, (ip, port)) in enumerate(invite_enum_list):
            print(f"{i + 1}. {player} at {ip}:{port}")

        while True:
            choice = input("Enter the number of the player you want to invite (or 'cancel' to go back): ")
            if choice.lower() == 'cancel':
                return None
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(invite_enum_list):
                    player, (ip, port) = invite_enum_list[choice_num - 1]
                    #invite_msg = f"INVITE {self.user_name}"
                    self.send_message_format_args_to(self.invite_udp_sock, Protocols.P2P.INVITE, (ip, port), self.user_name)
                    #self.invite_udp_sock.sendto(invite_msg.encode(), (ip, port))
                    print(f"Invitation sent to {player} at {ip}:{port}.")
                    #remove the invited player from found players
                    self.found_players.pop(player)
                    return player
                else:
                    print("Invalid choice number.")
            except ValueError:
                print("Please enter a valid number.")

    def wait_for_acceptance_and_start_game_tcp_server(self, invitee: str):
        with LOCK:
            self.acceptances_waiting.append(invitee)
        self.clear_messages(self.invite_udp_sock)
        while not self.stop_waiting_acceptance_event.is_set():
            try:
                self.invite_udp_sock.settimeout(0.5)
                msg, fname, addr = self.receive_and_get_format_name_from(self.invite_udp_sock)
                if fname == Protocols.P2P.ACCEPT.name:
                    accepter, = self.parse_message(msg, Protocols.P2P.ACCEPT)
                    if self.game_client_tcp_sock:
                        self.send_message_format_args_to(self.invite_udp_sock, Protocols.P2P.ALREADY_IN_GAME, addr, self.user_name)
                        # for debug
                        #print(f"{accepter} has accepted your invitation, but you are already in game.")
                        with LOCK:
                            self.acceptances_waiting.remove(invitee)
                        break
                    print(f"{accepter} has accepted your invitation from {addr}.")
                    # Start TCP server for game connection
                    self.game_server_tcp_sock.bind(('', 0)) # Bind to an available port
                    self.game_server_tcp_sock.listen(1)
                    game_tcp_port = self.game_server_tcp_sock.getsockname()[1]

                    print(f"Starting TCP server on port {game_tcp_port} for game connection...")
                    
                    game_ip = socket.gethostbyname(socket.gethostname())
                    self.send_message_format_args_to(self.invite_udp_sock, Protocols.P2P.CONNECT, addr, game_ip, game_tcp_port)
                    with LOCK:
                        self.game_client_tcp_sock, client_addr = self.game_server_tcp_sock.accept()
                    self.is_player_a = True
                    print(f"Accepted TCP connection from {client_addr}. Enter 'entergame' to start the game session.\n")
                    self.game_server_tcp_sock.close()
                    self.game_server_tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                    self.send_message_format(self.lobby_tcp_sock, Protocols.Command.RECORD_PLAY)
                    if not self.receive_and_check_is_message_format_name(self.lobby_tcp_sock, Protocols.Response.PLAY_RECORD_DONE):
                        print("Did not receive PLAY_RECORD_DONE")
                    self.about_to_enter_game = True
                    with LOCK:
                        self.acceptances_waiting.remove(invitee)
                    break
                elif fname == Protocols.P2P.DECLINE.name:
                    decliner, = self.parse_message(msg, Protocols.P2P.DECLINE)
                    print(f"{decliner} has declined your invitation from {addr}.")
                    with LOCK:
                        self.acceptances_waiting.remove(invitee)
                    break
                else:
                    print(f"Received unknown message when waiting for acceptance from {addr}")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error while waiting for acceptance: {e}")
                break
        
        if self.about_to_enter_game and self.waiting_invitations:
            self.stop_waiting_invitations()
        #self.waiting_acceptances = False # PROBLEM
        
        #for debug
        #print("invite_udp_sock stopped waiting.")
        #self.stop_waiting_acceptance_event.clear()
    
    def accept(self):
        if not self.received_invitations:
            print("No invitations received.")
            return
        print("Received invitations:")
        invite_enum_list = list(self.received_invitations.items())
        for i, (inviter, (ip, port)) in enumerate(invite_enum_list):
            print(f"{i + 1}. Invitation from {inviter} at {ip}:{port}")
        while True:
            choice = input("Enter the number of the invitation you want to accept (or 'cancel' to go back): ")
            if choice.lower() == 'cancel':
                return
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(invite_enum_list):
                    inviter, (ip, port) = invite_enum_list[choice_num - 1]
                    self.send_message_format_args_to(self.wait_udp_sock, Protocols.P2P.ACCEPT, (ip, port), self.user_name)
                    #accept_msg = f"ACCEPT {self.user_name}"
                    #self.wait_udp_sock.sendto(accept_msg.encode(), (ip, port))
                    print(f"Accepted invitation from {inviter} at {ip}:{port}.")
                    #remove the accepted invitation from received invitations
                    self.received_invitations.pop(inviter)
                    time.sleep(0.7)
                    return
                else:
                    print("Invalid choice number.")
            except ValueError:
                print("Please enter a valid number.")

    def decline(self):
        if not self.received_invitations:
            print("No invitations received.")
            return
        print("Received invitations:")
        invite_enum_list = list(self.received_invitations.items())
        for i, (inviter, (ip, port)) in enumerate(invite_enum_list):
            print(f"{i + 1}. Invitation from {inviter} at {ip}:{port}")
        while True:
            choice = input("Enter the number of the invitation you want to decline (or 'cancel' to go back): ")
            if choice.lower() == 'cancel':
                return
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(invite_enum_list):
                    inviter, (ip, port) = invite_enum_list[choice_num - 1]
                    self.send_message_format_args_to(self.wait_udp_sock, Protocols.P2P.DECLINE, (ip, port), self.user_name)
                    print(f"Declined invitation from {inviter} at {ip}:{port}.")
                    # remove the declined invitation from received invitations
                    self.received_invitations.pop(inviter)
                    return
                else:
                    print("Invalid choice number.")
            except ValueError:
                print("Please enter a valid number.")


    def play(self):
        self.about_to_enter_game = False
        game = Game(self.game_client_tcp_sock, self.lobby_tcp_sock, self.is_player_a)
        game.play_game()
        self.game_client_tcp_sock.close()
        self.game_client_tcp_sock = None
        self.found_players = {}


    def interact_to_lobby_server(self):
        while True:
            try:
                print()
                if not self.user_name:
                    # not logged in yet
                    print("Commands you can type:")
                    print("register: register an account")
                    print("login: log in an account")
                    print("exit: exit the lobby server and close.")

                    print()

                    msg = input("You are not logged in yet. Enter command: >>>>>>>>>> ") # (register/login) or 'exit' to quit
                    if not msg.strip():
                        print("Please enter a valid command.")
                        continue

                    match msg.strip().lower():
                        case 'login':
                            self.login()
                        case 'register':
                            self.register()
                        case 'exit':
                            self.exit_server()
                            break
                        case _:
                            print("Please enter a valid command.")
                else: 
                    # logged in
                    print("Commands you can type:")
                    #  and not self.found_players and not self.received_invitations
                    if not self.game_client_tcp_sock:
                        if not self.waiting_invitations:
                            print("wait: wait for invitations.")
                            print("scan: to scan players waiting for invitations.")
                        else:
                            print("unwait: cancel waiting.")

                        if self.found_players and not self.waiting_invitations:
                            print("invite: invite players scanned.")

                        if self.received_invitations and self.waiting_invitations:
                            print("accept: accept invitations from other players.")
                            print("decline: decline invitations from other players.")

                        print("logout: log out your account")
                        print("exit: exit the lobby server and close.")
                        print("status: view player status")
                    else:
                        print("entergame: enter the game.")

                    print()

                    msg = input(f"{self.user_name}, enter command: >>>>>>>>>> ")  # (logout/scan/wait/unwait/invite/accept/entergame/exit)
                    if not msg.strip():
                        print("Please enter a valid command.")
                        continue
                    match msg.strip().lower():
                        case 'status':
                            if self.game_client_tcp_sock:
                                print("You have found a game. You cannot view player status.")
                                continue
                            self.check_status()
                        case 'logout':
                            if self.game_client_tcp_sock:
                                print("You have found a game. You cannot log out.")
                                continue
                            self.logout()
                        case 'scan':
                            if self.game_client_tcp_sock:
                                print("You have found a game. You cannot scan.")
                                continue
                            if self.waiting_invitations:
                                print("You cannot scan while waiting invitations")
                                continue
                            self.scan(target_ip=self.lobby_server_host_name)
                        case 'wait':
                            if self.game_client_tcp_sock:
                                print("You have found a game. You cannot wait.")
                                continue
                            if self.waiting_invitations:
                                print("You are already waiting for invitations.")
                                continue

                            threading.Thread(target=self.wait_for_invitations_and_connect_game, daemon=True).start()
                            time.sleep(1)  # Give the thread a moment to start
                        case 'unwait':
                            if self.game_client_tcp_sock:
                                print("You have found a game. You cannot unwait.")
                                continue
                            if not self.waiting_invitations:
                                print("You are not waiting for invitations.")
                                continue

                            self.stop_waiting_invitations()
                        case 'invite':
                            if self.game_client_tcp_sock:
                                print("You have found a game. You cannot invite.")
                                continue
                            if self.waiting_invitations:
                                print("You cannot invite others when waiting")
                                continue                            
                            
                            client_invited = self.invite()
                            if client_invited and not client_invited in self.acceptances_waiting:
                                threading.Thread(target=self.wait_for_acceptance_and_start_game_tcp_server, args=(client_invited,), daemon=True).start()
                                time.sleep(1)  # Give the thread a moment to start
                            elif client_invited in self.acceptances_waiting:
                                print("test message: client_invited in self.acceptances_waiting.")
                        case 'accept':
                            if self.game_client_tcp_sock:
                                print("You have found a game. You cannot accept invitations anymore.")
                                continue
                            self.accept()
                        case 'decline':
                            if self.game_client_tcp_sock:
                                print("You have found a game. You cannot decline invitations anymore.")
                                continue
                            self.decline()
                        case 'exit':
                            if self.game_client_tcp_sock:
                                print("You have found a game. You cannot exit now.")
                                continue
                            self.exit_server()
                            break
                        case 'entergame':
                            if not self.game_client_tcp_sock:
                                print("No game session available. Please wait for an invitation or invite someone first.")
                                continue
                            self.play()
                        case _:
                            print("Please enter a valid command.")
            except Exception as e:
                print(f"Exception raised: {e}")

        # for debug        
        #os.system("pause")
        self.close()

    def send_message_format_to_lobby_server(self, msg_format, *args):
        self.send_message_format_args(self.lobby_tcp_sock, msg_format, *args)

    def receive_check_is_format_name_from_lobby_server(self, msg_format) -> bool:
        return self.receive_and_check_is_message_format_name(self.lobby_tcp_sock, msg_format)
    
    def connect_and_start_client_process(self, host="127.0.0.1", port = 8888):
        self.connect_to_lobby_server(host, port)
        self.interact_to_lobby_server()
        


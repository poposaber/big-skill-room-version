import socket
import threading
import time
import random
from protocols import Protocols



received_invitations = {}  # To store received invitations, key: username, value: (from_addr, from_port)
#game_over_event = threading.Event()  # To indicate if currently in a game session
#game_over_event.set()  # Initially not in a game
LOCK = threading.Lock()
client_game_socket = None # Global TCP socket for game session (obtained by player A)
tcp_game_socket = None # Global TCP socket for game session (obtained by player B)

# Helper function to convert card count to card list. For example, [0,3,2,1,0,0] -> ['1','1','1','2','2','3']
def card_count_to_card_list(card_count):
    card_list = []
    for card_value in range(1, 6):
        try:
            card_list.extend([str(card_value)] * int(card_count[card_value]))
        except ValueError:
            continue
    return card_list

def card_list_to_card_count(card_list):
    card_count = [0, 0, 0, 0, 0, 0]  # Index 0 unused, cards 1-5
    for card in card_list:
        try:
            card_val = int(card)
            if 1 <= card_val <= 5:
                card_count[card_val] += 1
        except ValueError:
            continue
    return card_count

def sum_of_card_count(card_count):
    result = 0
    for i in range(1, 6):
        result += i * int(card_count[i])
    return result

def game_session_A(self_sock):
    player_a_goes_first = random.choice([True, False])
    this_round_a_goes_first = player_a_goes_first
    msg = None
    data = None
    print("You are Player A.")
    print("Waiting for Player B to be ready...")
    # send check message to confirm player B entered the game session
    self_sock.send(Protocols.Ingame.READY.encode())
    
    try:
        data = self_sock.recv(1024)
    except Exception as e:
        print(f"Error receiving data: {e}")
        return
    if not data:
        print("player B disconnected.")
        return
    if data.decode().strip() != Protocols.Ingame.READY:
        print("Did not receive READY from Player B. Exiting game session.")
        return
    else:
        print("Player B is ready.")
    
    # Start the game rounds
    card_count = [0, 3, 3, 3, 3, 3]  # Index 0 unused, cards 1-5 each have 3 copies
    played_card_count = [0, 0, 0, 0, 0, 0]  # To track played cards in the current round.
    point_a = 0 #current round won by a
    point_b = 0 #current round won by b
    try:
        for round_num in range(1, 10):
            played_card_count = [0, 0, 0, 0, 0, 0]  # Reset played cards for the new round
            print()
            print(f"================== Starting round {round_num}. ==================")
            try:
                self_sock.send(Protocols.Ingame.ROUND_COUNT(round_num).encode())
            except Exception as e:
                print(f"Error sending data: {e}")
                return
            time.sleep(1)  # Give a moment for the message to be sent

            # wait for OK from player B
            try:
                data = self_sock.recv(1024)
            except Exception as e:
                print(f"Error receiving data: {e}")
                return
            if not data:
                print("player B disconnected.")
                return
            if data.decode().strip() != Protocols.Ingame.OK:
                print("Did not receive OK from Player B. Exiting game session.")
                return
            
            if this_round_a_goes_first:
                # A's turn first, send to B A goes first, requires B says OK
                self_sock.send("A goes first.".encode())
                print("You go first.")
                try:
                    data = self_sock.recv(1024)
                except Exception as e:
                    print(f"Error receiving data: {e}")
                    return
                if not data:
                    print("player B disconnected.")
                    return
                if data.decode().strip() != Protocols.Ingame.OK:
                    print("Did not receive OK from Player B. Exiting game session.")
                    return
                
                # after receiving OK, read input
                print()
                if round_num == 1:
                    print("You have 3 cards each of values 1 to 5.")
                    print("Try to play cards and have higher total than Player B to win the round.")
                    print("type 'playcard <cards>' to play cards, e.g., 'playcard 1 1 2' to play two 1s and one 2.")
                    print("you can play 1 to 3 cards each turn.")
                    print("Once you play a card, it cannot be used again in this game.")

                print()
                print("You now have:")
                for i in range(1, 6):
                    print(f"{card_count[i]} cards of value {i}")
                print()
                
                # This loop ensures valid input
                while True:
                    msg = input("Your turn (type playcard to play cards or 'ff' to forfeit): ")
                    if msg.startswith("playcard") or msg.strip().lower() == "ff":
                        parts = msg.split()
                        if msg.strip().lower() == "ff":
                            break
                        if len(parts) < 2 or len(parts) > 4:
                            print("You must play between 1 to 3 cards. Try again.")
                            continue
                        try:
                            if any(int(part) > 5 or int(part) < 1 for part in parts[1:]):
                                print("You only have card with values 1 to 5.")
                                continue
                            played_card_count = card_list_to_card_count(parts[1:])
                            if any(played_card_count[i] > card_count[i] for i in range(1, 6)):
                                print("You don't have enough of those cards. Try again.")
                                continue
                            # Valid play, update card_count
                            for i in range(1, 6):
                                card_count[i] -= played_card_count[i]
                            break  # Exit the input loop
                        except ValueError:
                            print("Invalid card values. Please enter numbers between 1 and 5.")
                            continue
                    print("Invalid command. Please use 'playcard <cards>' or 'ff' to forfeit.")
                try:
                    if msg.strip().lower() != "ff":
                        self_sock.send(Protocols.Ingame.PLAYCARD_DONE.encode()) # send A playcard done to B
                    else:
                        self_sock.send("ff".encode())
                        print("You forfeited the game.")
                        return
                except Exception as e:
                    print(f"Error sending data: {e}")
                    return
                
                # B's turn, wait for B's input
                try:
                    print("Waiting for Player B's move...")
                    data = self_sock.recv(1024)
                except Exception as e:
                    print(f"Error receiving data: {e}")
                    return
                if not data:
                    print("player B disconnected.")
                    return
                if data.decode().startswith(Protocols.Ingame.PLAYCARD_DONE):
                    print("Player B has played cards.")
                # if data says "ff", end the game
                if data.decode().strip().lower() == "ff":
                    print("Player B forfeited the game.")
                    return
            else:
                # B's turn first, wait for B's input first
                self_sock.send("B goes first.".encode())
                print("Player B goes first, waiting for B's move...")
                try:
                    data = self_sock.recv(1024)
                except Exception as e:
                    print(f"Error receiving data: {e}")
                    return
                if not data:
                    print("player B disconnected.")
                    return
                if data.decode().startswith(Protocols.Ingame.PLAYCARD_DONE):
                    print("Player B has played cards.")
                # if data says "ff", end the game
                if data.decode().strip().lower() == "ff":
                    print("Player B forfeited the game.")
                    return
                
                # A's turn, read input
                print()
                if round_num == 1:
                    print("You have 3 cards each of values 1 to 5.")
                    print("Try to play cards and have higher total than Player B to win the round.")
                    print("type 'playcard <cards>' to play cards, e.g., 'playcard 1 1 2' to play two 1s and one 2.")
                    print("you can play 1 to 3 cards each turn.")
                    print("Once you play a card, it cannot be used again in this game.")

                print()
                print("You now have:")
                for i in range(1, 6):
                    print(f"{card_count[i]} cards of value {i}")
                
                print()
                # This loop ensures valid input
                while True:
                    msg = input("Your turn (type playcard to play cards or 'ff' to forfeit): ")
                    if msg.startswith("playcard") or msg.strip().lower() == "ff":
                        parts = msg.split()
                        if msg.strip().lower() == "ff":
                            break
                        if len(parts) < 2 or len(parts) > 4:
                            print("You must play between 1 to 3 cards. Try again.")
                            continue
                        try:
                            if any(int(part) > 5 or int(part) < 1 for part in parts[1:]):
                                print("You only have card with values 1 to 5.")
                                continue
                            played_card_count = card_list_to_card_count(parts[1:])
                            if any(played_card_count[i] > card_count[i] for i in range(1, 6)):
                                print("You don't have enough of those cards. Try again.")
                                continue
                            # Valid play, update card_count
                            for i in range(1, 6):
                                card_count[i] -= played_card_count[i]
                            break  # Exit the input loop
                        except ValueError:
                            print("Invalid card values. Please enter numbers between 1 and 5.")
                            continue
                    print("Invalid command. Please use 'playcard <cards>' or 'ff' to forfeit.")

                try:
                    if msg.strip().lower() != "ff":
                        self_sock.send(Protocols.Ingame.PLAYCARD_DONE.encode()) # send A playcard done to B
                    else:
                        self_sock.send("ff".encode())
                        print("You forfeited the game.")
                        return
                except Exception as e:
                    print(f"Error sending data: {e}")
                    return
                
                # wait for B's OK
                try:
                    data = self_sock.recv(1024)
                except Exception as e:
                    print(f"Error receiving data: {e}")
                    return
                if not data:
                    print("player B disconnected.")
                    return
                if data.decode().strip() != Protocols.Ingame.OK:
                    print("Did not receive OK from Player B. Exiting game session.")
                    return
                
            # Calculate result of the round here
            print(f"Round {round_num} completed.")
            # Send ROUNDCOMPLETED to player B
            try:
                self_sock.send(Protocols.Ingame.ROUNDCOMPLETED.encode())
            except Exception as e:
                print(f"Error sending data: {e}")
                return
            
            time.sleep(2) # give a time for player B

            # receive B's REPORTCARD_CARDS message
            try:
                data = self_sock.recv(1024)
            except Exception as e:
                print(f"Error receiving data: {e}")
                return
            if not data:
                print("player B disconnected.")
                return
            if not data.decode().startswith(Protocols.Ingame.REPORTCARD):
                print("Did not receive REPORTCARD from Player B. Exiting game session.")
                return
            
            # calculate result and print
            cardsum_a = sum_of_card_count(played_card_count)
            cardsum_b = sum_of_card_count(data.decode().split()[1:])
            
            winner = None
            if this_round_a_goes_first:
                if cardsum_a < cardsum_b:
                    winner = 'B'
                    point_b += 1
                else:
                    winner = 'A'
                    point_a += 1
            else:
                if cardsum_a <= cardsum_b:
                    winner = 'B'
                    point_b += 1
                else:
                    winner = 'A'
                    point_a += 1

            print()
            print("sum of cards played by A: " + ' + '.join(card_count_to_card_list(played_card_count)) + f" = {cardsum_a}")
            print("sum of cards played by B: " + ' + '.join(card_count_to_card_list(data.decode().split()[1:])) + f" = {cardsum_b}")
            print(f"player {winner} wins this round!")

            # send MATCHRESULT_RESULT
            try:
                self_sock.send(Protocols.Ingame.MATCHRESULT_RESULT(played_card_count, winner).encode())
            except Exception as e:
                print(f"Error sending data: {e}")
                return
            
            time.sleep(3) # take a break
            
            # receive OK
            try:
                data = self_sock.recv(1024)
            except Exception as e:
                print(f"Error receiving data: {e}")
                return
            if not data:
                print("player B disconnected.")
                return
            if data.decode() != Protocols.Ingame.OK:
                print("Did not receive OK from Player B. Exiting game session.")
                return
            
            # print current points
            print()
            print(f"(YOU)      Player A won {point_a} round(s)!")
            print(f"(OPPONENT) Player B won {point_b} round(s)!")
            
            # send CURRENTPOINT_POINTS
            try:
                self_sock.send(Protocols.Ingame.CURRENTPOINT_POINTS(point_a, point_b).encode())
            except Exception as e:
                print(f"Error sending data: {e}")
                return
            
            time.sleep(2)

            # receive OK
            try:
                data = self_sock.recv(1024)
            except Exception as e:
                print(f"Error receiving data: {e}")
                return
            if not data:
                print("player B disconnected.")
                return
            if data.decode() != Protocols.Ingame.OK:
                print("Did not receive OK from Player B. Exiting game session.")
                return
            
            this_round_a_goes_first = not this_round_a_goes_first  # Alternate who goes first next round

        # After 9 rounds, end the game
        print("Game over after 9 rounds.")
        self_sock.send(Protocols.Ingame.GAMEOVER.encode())

    except Exception as e:
        print(f"Error in game session: {e}")
    finally:
        if self_sock:
            self_sock.close()
        #game_over_event.set()  # Indicate the game session is over

    

def game_session_B(self_sock):
    data = None
    print("You are Player B.")
    print("Waiting for Player A to be ready...")
    #wait for check message from player A
    try:
        data = self_sock.recv(1024)
    except Exception as e:
        print(f"Error receiving data: {e}")
        return
    if not data:
        print("player A disconnected.")
        return
    if data.decode().strip() != Protocols.Ingame.READY:
        print("Did not receive READY from Player A. Exiting game session.")
        return
    else:
        print("Player A is ready.")
        self_sock.send(Protocols.Ingame.READY.encode())
    
    # Start the game rounds
    round_num = 0
    card_count = [0, 3, 3, 3, 3, 3]
    played_card_count = [0, 0, 0, 0, 0, 0]
    point_a = 0
    point_b = 0
    try:
        # The loop goes until GAMEOVER or a player forfeits
        while True:
            # wait for ROUND message or GAMEOVER message from player A
            played_card_count = [0, 0, 0, 0, 0, 0] # clear played cards at the previous round
            try:
                data = self_sock.recv(1024)
            except Exception as e:
                print(f"Error receiving data: {e}")
                return
            if not data:
                print("player A disconnected.")
                return
            
            if data.decode().startswith(Protocols.Ingame.ROUND):
                round_num = int(data.decode().split()[1])
                print()
                print(f"================== Starting round {round_num}. ==================")   
            elif data.decode().strip() == Protocols.Ingame.GAMEOVER:
                print("Game over after 9 rounds.")
                return
            else:
                print("Did not receive ROUND from Player A. Exiting game session.")
                return
            
            # send OK to player A
            try:
                self_sock.send(Protocols.Ingame.OK.encode())
            except Exception as e:
                print(f"Error sending data: {e}")
                return
            
            # wait for who goes first message from player A
            try:
                data = self_sock.recv(1024)
            except Exception as e:
                print(f"Error receiving data: {e}")
                return
            if not data:
                print("player A disconnected.")
                return
            if data.decode().strip() == "A goes first.":
                # A's turn first
                print("Player A goes first, waiting for A's move...")
                # after receiving A goes first, send OK to A
                try:
                    self_sock.send(Protocols.Ingame.OK.encode())
                except Exception as e:
                    print(f"Error sending data: {e}")
                    return
                # wait for A's PLAYCARD_DONE or ff
                try:
                    data = self_sock.recv(1024)
                except Exception as e:
                    print(f"Error receiving data: {e}")
                    return
                if not data:
                    print("player A disconnected.")
                    return
                # if data says "ff", end the game
                if data.decode().strip().lower() == "ff":
                    print("Player A forfeited the game.")
                    return
                if data.decode().strip() == Protocols.Ingame.PLAYCARD_DONE:
                    print("Player A has played cards.")
                
                # B's turn, read input
                print()
                if round_num == 1:
                    print("You have 3 cards each of values 1 to 5.")
                    print("Try to play cards and have higher total than Player B to win the round.")
                    print("type 'playcard <cards>' to play cards, e.g., 'playcard 1 1 2' to play two 1s and one 2.")
                    print("you can play 1 to 3 cards each turn.")
                    print("Once you play a card, it cannot be used again in this game.")

                print()
                print("You now have:")
                for i in range(1, 6):
                    print(f"{card_count[i]} cards of value {i}")

                print()
                while True:
                    msg = input("Your turn (type playcard to play cards or 'ff' to forfeit): ")
                    if msg.startswith("playcard") or msg.strip().lower() == "ff":
                        parts = msg.split()
                        if msg.strip().lower() == "ff":
                            break
                        if len(parts) < 2 or len(parts) > 4:
                            print("You must play between 1 to 3 cards. Try again.")
                            continue
                        try:
                            if any(int(part) > 5 or int(part) < 1 for part in parts[1:]):
                                print("You only have card with values 1 to 5.")
                                continue
                            played_card_count = card_list_to_card_count(parts[1:])
                            if any(played_card_count[i] > card_count[i] for i in range(1, 6)):
                                print("You don't have enough of those cards. Try again.")
                                continue
                            # Valid play, update card_count
                            for i in range(1, 6):
                                card_count[i] -= played_card_count[i]
                            break  # Exit the input loop
                        except ValueError:
                            print("Invalid card values. Please enter numbers between 1 and 5.")
                            continue
                    print("Invalid command. Please use 'playcard <cards>' or 'ff' to forfeit.")

                try:
                    if msg.strip().lower() != "ff":
                        self_sock.send(Protocols.Ingame.PLAYCARD_DONE.encode()) # send A playcard done to B
                    else:
                        self_sock.send("ff".encode())
                        print("You forfeited the game.")
                        return
                except Exception as e:
                    print(f"Error sending data: {e}")
                    return
                
            elif data.decode().strip() == "B goes first.":
                # B's turn first, read input first
                print("You go first.")

                if round_num == 1:
                    print()
                    print("You have 3 cards each of values 1 to 5.")
                    print("Try to play cards and have higher total than Player B to win the round.")
                    print("type 'playcard <cards>' to play cards, e.g., 'playcard 1 1 2' to play two 1s and one 2.")
                    print("you can play 1 to 3 cards each turn.")
                    print("Once you play a card, it cannot be used again in this game.")

                print()
                print("You now have:")
                for i in range(1, 6):
                    print(f"{card_count[i]} cards of value {i}")

                print()
                while True:
                    msg = input("Your turn (type playcard to play cards or 'ff' to forfeit): ")
                    if msg.startswith("playcard") or msg.strip().lower() == "ff":
                        parts = msg.split()
                        if msg.strip().lower() == "ff":
                            break
                        if len(parts) < 2 or len(parts) > 4:
                            print("You must play between 1 to 3 cards. Try again.")
                            continue
                        try:
                            if any(int(part) > 5 or int(part) < 1 for part in parts[1:]):
                                print("You only have card with values 1 to 5.")
                                continue
                            played_card_count = card_list_to_card_count(parts[1:])
                            if any(played_card_count[i] > card_count[i] for i in range(1, 6)):
                                print("You don't have enough of those cards. Try again.")
                                continue
                            # Valid play, update card_count
                            for i in range(1, 6):
                                card_count[i] -= played_card_count[i]
                            break  # Exit the input loop
                        except ValueError:
                            print("Invalid card values. Please enter numbers between 1 and 5.")
                            continue
                    print("Invalid command. Please use 'playcard <cards>' or 'ff' to forfeit.")

                try:
                    if msg.strip().lower() != "ff":
                        self_sock.send(Protocols.Ingame.PLAYCARD_DONE.encode()) # send B playcard done to A
                    else:
                        self_sock.send("ff".encode())
                        print("You forfeited the game.")
                        return
                except Exception as e:
                    print(f"Error sending data: {e}")
                    return
                # A's turn, wait for A's PLAYCARD_DONE or ff
                print("Waiting for Player A's move...")
                try:
                    data = self_sock.recv(1024)
                except Exception as e:
                    print(f"Error receiving data: {e}")
                    return
                if not data:
                    print("player A disconnected.")
                    return
                # if data says "ff", end the game
                if data.decode().strip().lower() == "ff":
                    print("Player A forfeited the game.")
                    return
                if data.decode().strip() == Protocols.Ingame.PLAYCARD_DONE:
                    print("Player A has played cards.")
                
                # after receiving A's PLAYCARD_DONE, send OK to A
                try:
                    self_sock.send(Protocols.Ingame.OK.encode())
                except Exception as e:
                    print(f"Error sending data: {e}")
                    return
            else:
                print("Received unexpected message. Exiting game session.")
                return
            
            # wait for ROUNDCOMPLETED from player A
            try:
                data = self_sock.recv(1024)
            except Exception as e:
                print(f"Error receiving data: {e}")
                return
            if not data:
                print("player A disconnected.")
                return
            if data.decode() != Protocols.Ingame.ROUNDCOMPLETED:
                print("Did not receive ROUNDCOMPLETED from Player A. Exiting game session.")
                return
            
            print()
            print(f"Round {round_num} completed.")
            
            # send REPORTCARD_CARDS to player A
            try:
                self_sock.send(Protocols.Ingame.REPORTCARD_CARDS(played_card_count).encode())
            except Exception as e:
                print(f"Error sending data: {e}")
                return
            
            # receive MATCHRESULT_RESULT
            try:
                data = self_sock.recv(1024)
            except Exception as e:
                print(f"Error receiving data: {e}")
                return
            if not data:
                print("player A disconnected.")
                return
            if not data.decode().startswith(Protocols.Ingame.MATCHRESULT):
                print("Did not receive MATCHRESULT from Player A. Exiting game session.")
                return
            
            # print the result
            cardsum_a = sum_of_card_count(data.decode().split()[1:7])
            cardsum_b = sum_of_card_count(played_card_count)
            winner = data.decode().split()[7]

            print()
            print("sum of cards played by A: " + ' + '.join(card_count_to_card_list(data.decode().split()[1:7])) + f" = {cardsum_a}")
            print("sum of cards played by B: " + ' + '.join(card_count_to_card_list(played_card_count)) + f" = {cardsum_b}")
            print(f"player {winner} wins this round!")

            # send OK
            try:
                self_sock.send(Protocols.Ingame.OK.encode())
            except Exception as e:
                print(f"Error sending data: {e}")
                return
            
            # receive CURRENTPOINT_POINTS
            try:
                data = self_sock.recv(1024)
            except Exception as e:
                print(f"Error receiving data: {e}")
                return
            if not data:
                print("player A disconnected.")
                return
            if not data.decode().startswith(Protocols.Ingame.CURRENTPOINT):
                print("Did not receive MATCHRESULT from Player A. Exiting game session.")
                return
            point_a = int(data.decode().split()[1])
            point_b = int(data.decode().split()[2])
            
            # print current points
            print()
            print(f"(OPPONENT) Player A won {point_a} round(s)!")
            print(f"(YOU)      Player B won {point_b} round(s)!")
            
            # send OK
            try:
                self_sock.send(Protocols.Ingame.OK.encode())
            except Exception as e:
                print(f"Error sending data: {e}")
                return


    except Exception as e:
        print(f"Error in game session: {e}")
    finally:
        if self_sock:
            self_sock.close()
        #game_over_event.set()  # Indicate the game session is over

def scan_udp_ports(target_ip, start_port=10001, end_port=65535):
    found_players = []
    scan_msg = "SCAN"
    port = start_port
    conti_no_player_count = 0
    while port <= end_port and conti_no_player_count < 1000:
        try:
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.settimeout(0.05)
            udp_sock.sendto(scan_msg.encode(), (target_ip, port))
            #print("scanning port", port)
            data, addr = udp_sock.recvfrom(1024)
            if data.decode() == "LISTENING":
                print(f"Found player listening on UDP port {port}")
                found_players.append(port)
                conti_no_player_count = 0
        except socket.timeout:
            conti_no_player_count += 1
            #print(f"Port {port} timed out.")
            continue
        except Exception as e:
            conti_no_player_count += 1
            #print(f"Error scanning port {port}: {e}")
            continue
        finally:
            udp_sock.close()
            port += 1
    
    return found_players
        
# For player B who listens for invitations
def listen_udp_and_start_game(stop_event):
    global received_invitations
    global tcp_game_socket
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    port = 10001
    
    while True:
        try:
            udp_sock.bind(('', port))
            break
        except OSError:
            port += 1
            if port > 65535:
                print("No available UDP ports to bind.")
                return
    udp_sock.settimeout(0.5)  # 每 0.5 秒檢查一次是否需要停止
    print(f"Listening for UDP invitations on port {port}...")
    try:
        while not stop_event.is_set():
            try:
                data, addr = udp_sock.recvfrom(1024)
                if data.decode() == "SCAN":
                    udp_sock.sendto("LISTENING".encode(), addr)
                elif data.decode().startswith("INVITE"):
                    print(f"\nReceived invitation: {data.decode()} from {addr}\n")
                    # Store the invitation
                    received_invitations[data.decode().split()[2]] = addr
                    print("Received invitations:", received_invitations)
                elif data.decode().startswith("CONNECT"):
                    parts = data.decode().split()
                    if len(parts) == 3:
                        try:
                            target_ip = parts[1]
                            target_port = int(parts[2])
                            print(f"\nReceived connection details: Connect to {target_ip}:{target_port}\n")
                            # Start TCP connection to the provided IP and port
                            with LOCK:
                                tcp_game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                tcp_game_socket.connect((target_ip, target_port))
                            time.sleep(0.1)  # Give a moment for the connection to establish
                            print(f"Connected to game server at {target_ip}:{target_port}. Type 'entergame' to start the game session.\n")
                            #game_over_event.clear()  # Indicate we are now in a game session
                            break
                        except ValueError:
                            print(f"\nReceived malformed CONNECT message: {data.decode()}\n")
                    else:
                        print(f"\nReceived malformed CONNECT message: {data.decode()}\n")
            except socket.timeout:
                continue
    except Exception as e:
        print(f"UDP listener on port {port} stopped: {e}")
    finally:
        print(f"UDP listener on port {port} stopped.")
        udp_sock.close()
    #game_session_B(tcp_sock)

# For player A who sends invitation
def invite_and_listen_and_start_game(target_ip, target_port, user_name):
    global client_game_socket
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.settimeout(20)  # Wait up to 20 seconds for a response
    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #client_sock = None
    invite_msg = f"INVITE from {user_name}"
    try:
        udp_sock.sendto(invite_msg.encode(), (target_ip, target_port))
        print(f"Sent invitation to {target_ip}:{target_port}.")
        # Wait for acceptance
        data, addr = udp_sock.recvfrom(1024)
        if data.decode().startswith("ACCEPT"):
            print(f"\nInvitation accepted by {addr}: {data.decode()}")
            udp_sock.settimeout(None)
            # start TCP server and send connection details
            tcp_server.bind(('', 0))  # Bind to an available port
            tcp_server.listen(1)
            tcp_port = tcp_server.getsockname()[1]
            print(f"Starting TCP server on port {tcp_port} for game connection...")
            connection_details = f"CONNECT {socket.gethostbyname(socket.gethostname())} {tcp_port}"
            udp_sock.sendto(connection_details.encode(), (target_ip, target_port))
            with LOCK:
                client_game_socket, client_addr = tcp_server.accept()
            
            print(f"Accepted TCP connection from {client_addr}. Enter 'entergame' to start the game session.\n")
            #game_over_event.clear()  # Indicate we are now in a game session
        else:
            print(f"\nReceived unexpected response from {addr}: {data.decode()}")
    except socket.timeout:
        print(f"\nNo response received from {target_ip}:{target_port}.")
    except Exception as e:
        print(f"Failed to send invitation: {e}")
    finally:
        udp_sock.close()
        tcp_server.close()
    #game_session_A(client_sock)
    

def connect_to_server(host="127.0.0.1", port = 8888):
    global client_game_socket
    global tcp_game_socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    print(f"Connected to lobby server {host}:{port}")
    print(client_socket.recv(1024).decode())  # Welcome message

    logged_in = False
    user_name = None
    temp_user_name = None
    stop_event = threading.Event()
    waiting = False

    while True:
        #game_over_event.wait()  # Wait until not in a game session

        if not logged_in:
            msg = input("You are not logged in yet. Enter command (register/login) or 'exit' to quit: ")
            if not msg.strip() or msg.split()[0].lower() not in \
                    [Protocols.Command.REGISTER, Protocols.Command.LOGIN, Protocols.Command.EXIT]:
                print("Please enter a valid command.")
                continue
            elif msg.split()[0].lower() == Protocols.Command.LOGIN and len(msg.split()) == 3:
                temp_user_name = msg.split()[1]
        else:
            msg = input(str(user_name) + ", Enter command (logout/scan/wait/unwait/accept/invite/exit) or send game invitations: ")
            if not msg.strip() or msg.split()[0].lower() not in \
                    [Protocols.Command.LOGOUT, Protocols.Command.EXIT, Protocols.Special.SCAN, 
                    Protocols.Special.WAIT, Protocols.Special.INVITE, Protocols.Special.UNWAIT, 
                    Protocols.Special.ACCEPT, Protocols.Special.ENTERGAME]:
                print("Please enter a valid command.")
                continue
            elif msg.split()[0].lower() == Protocols.Special.WAIT:
                if waiting:
                    print("You are already waiting for invitations. Use 'unwait' to stop waiting first.\n")
                    continue
                try:
                    threading.Thread(target=listen_udp_and_start_game, args=(stop_event,), daemon=True).start()
                    waiting = True
                    print(f"You are now waiting for invitations. Use 'unwait' to stop waiting.\n")
                    time.sleep(0.1)  # Give the UDP listener a moment to start
                except ValueError:
                    print("Please enter a valid UDP port number.\n")
                continue
            elif msg.split()[0].lower() == Protocols.Special.UNWAIT:
                if not waiting:
                    print("You are not currently waiting for invitations.\n")
                    continue
                stop_event.set()
                time.sleep(1)  # Give the UDP listener a moment to stop
                stop_event.clear()
                waiting = False
                print("You have stopped waiting for invitations.\n")
                continue
            elif msg.split()[0].lower() == Protocols.Special.SCAN:
                if waiting:
                    print("You cannot scan for players while waiting for invitations. Use 'unwait' first.\n")
                    continue
                print("Scanning for players waiting for game invitations...")
                found_ports = scan_udp_ports(host)
                if found_ports:
                    print(f"Found players waiting on UDP ports: {', '.join(map(str, found_ports))}")
                else:
                    print("No players found waiting for game invitations.")
                continue
            elif msg.split()[0].lower() == Protocols.Special.INVITE:
                if waiting:
                    print("You cannot send invitations while waiting for invitations. Use 'unwait' first.\n")
                    continue
                if len(msg.split()) != 2:
                    print("Usage: invite <target UDP port>\n")
                    continue
                try:
                    target_port = int(msg.split()[1])
                    if target_port < 10001 or target_port > 65535:
                        print("Please enter a UDP port above 10000.\n")
                        continue
                    threading.Thread(target=invite_and_listen_and_start_game, args=(host, target_port, user_name), daemon=True).start()
                    time.sleep(0.1)  # Give the invitation thread a moment to start
                except ValueError:
                    print("Please enter a valid UDP port number.\n")
                continue
            elif msg.split()[0].lower() == Protocols.Special.ACCEPT:
                if not waiting:
                    print("You are not currently waiting for invitations.\n")
                    continue
                if len(msg.split()) != 2:
                    print("Usage: accept <username>\n")
                    continue
                invitee = msg.split()[1]
                if invitee not in received_invitations:
                    print(f"No invitation found from user '{invitee}'.\n")
                    continue
                addr = received_invitations[invitee]
                try:
                    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    accept_msg = f"ACCEPT from {user_name}"
                    udp_sock.sendto(accept_msg.encode(), addr)
                    print(f"Sent acceptance to {invitee} at {addr}.")
                    udp_sock.close()
                except Exception as e:
                    print(f"Failed to send acceptance: {e}\n")
                continue
            elif msg.split()[0].lower() == Protocols.Special.ENTERGAME:
                if client_game_socket:
                    print("Entering game session as Player A...")
                    waiting = False
                    game_session_A(client_game_socket)
                    # After game ends
                    client_game_socket = None
                elif tcp_game_socket:
                    print("Entering game session as Player B...")
                    waiting = False
                    game_session_B(tcp_game_socket)
                    # After game ends
                    tcp_game_socket = None
                else:
                    print("No active game session to enter. Make sure you have sent or accepted an invitation.\n")
                continue
            elif msg.split()[0].lower() == Protocols.Command.LOGOUT:
                if waiting:
                    stop_event.set()
                    time.sleep(1)  # Give the UDP listener a moment to stop
                    stop_event.clear()
                    waiting = False
                    print("You have stopped waiting for invitations.\n")
            elif msg.split()[0].lower() == Protocols.Command.EXIT:
                if waiting:
                    stop_event.set()
                    time.sleep(1)  # Give the UDP listener a moment to stop
                    stop_event.clear()
                    waiting = False
                    print("You have stopped waiting for invitations.\n")

        client_socket.send(msg.encode())

        response = client_socket.recv(1024).decode()
        print("Server response:", response)
        if response == Protocols.Response.SERVER_SHUTDOWN:
            print("Server is shutting down. Disconnecting...")
            break
        elif response == Protocols.Response.LOGIN_SUCCESS:
            logged_in = True
            user_name = temp_user_name
            print("Login successful. You can now send messages.")
        elif response == Protocols.Response.LOGOUT_SUCCESS:
            logged_in = False
            user_name = None
            temp_user_name = None
            print("You have been logged out.")
        elif response == Protocols.Response.GOODBYE:
            print("Exiting the client.")
            break

    client_socket.close()

if __name__ == "__main__":
    connect_to_server()
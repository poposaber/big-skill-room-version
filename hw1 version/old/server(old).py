import socket
import threading
import json
import os
from protocols import Protocols
#import time

USER_DB_FILE = 'user_db.json'
LOCK = threading.Lock()
active_connections = 0
client_sockets = []
#WAITING_PLAYERS = {}  # To keep track of players waiting for invitations

def load_user_db():
    if not os.path.exists(USER_DB_FILE):
        return {}
    with open(USER_DB_FILE, 'r') as f:
        return json.load(f)
    
def save_user_db(user_db):
    with open(USER_DB_FILE, 'w') as f:
        json.dump(user_db, f)

def handle_client(client_socket, addr, user_db):
    global active_connections
    client_sockets.append(client_socket)
    active_connections += 1
    print(f"[NEW CONNECTION] {addr} connected.")
    client_socket.send(Protocols.Response.WELCOME.encode())

    logged_in = False
    current_user = None
    #waiting_for_invite = False  # Indicates if the user is waiting for a game invitation
    
    while True:
        try:
            msg = client_socket.recv(1024).decode().strip()
            if not msg:
                client_socket.send(Protocols.Response.EMPTY_COMMAND.encode())
                continue
            
            parts = msg.split()
            command = parts[0].lower()
            
            if command == Protocols.Command.REGISTER:
                if logged_in:
                    client_socket.send(Protocols.Response.ALREADY_LOGGED_IN.encode())
                    continue

                if len(parts) != 3:
                    client_socket.send(Protocols.Response.USAGE_REGISTER.encode())
                    continue
                username, password = parts[1], parts[2]
                
                with LOCK:
                    if username in user_db:
                        client_socket.send(Protocols.Response.USERNAME_EXISTS.encode())
                    else:
                        user_db[username] = {"password": password}
                        save_user_db(user_db)
                        client_socket.send(Protocols.Response.REG_SUCCESS.encode())
            
            elif command == Protocols.Command.LOGIN:
                if logged_in:
                    client_socket.send(Protocols.Response.ALREADY_LOGGED_IN.encode())
                    continue

                if len(parts) != 3:
                    client_socket.send(Protocols.Response.USAGE_LOGIN.encode())
                    continue
                username, password = parts[1], parts[2]
                
                with LOCK:
                    if username not in user_db or user_db[username]['password'] != password:
                        client_socket.send(Protocols.Response.INVALID_CREDENTIALS.encode())
                    else:
                        client_socket.send(Protocols.Response.LOGIN_SUCCESS.encode())
                        logged_in = True
                        current_user = username
            elif command == Protocols.Command.LOGOUT:
                if not logged_in:
                    client_socket.send(Protocols.Response.NOT_LOGGED_IN.encode())
                    continue
                logged_in = False
                current_user = None
                client_socket.send(Protocols.Response.LOGOUT_SUCCESS.encode())
            elif command == Protocols.Command.EXIT:
                client_socket.send(Protocols.Response.GOODBYE.encode())
                break              
            else:
                client_socket.send(Protocols.Response.UNKNOWN_COMMAND.encode())
        
        except Exception as e:
            print(f"[ERROR] {e}")
            break
    
    client_socket.close()
    client_sockets.remove(client_socket)
    active_connections -= 1
    print(f"[DISCONNECTED] {addr} disconnected.")
    print(f"[ACTIVE CONNECTIONS] {active_connections}")

def start_server(host="0.0.0.0", port=8888):
    user_db = load_user_db()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)
    server.settimeout(1)  # 每 1 秒 timeout 一次
    print(f"[LISTENING] Server is listening on {host}:{port}")
    
    try:
        while True:
            try:
                client_socket, addr = server.accept()
                client_handler = threading.Thread(target=handle_client, args=(client_socket, addr, user_db))
                client_handler.start()
                print(f"[ACTIVE CONNECTIONS] {active_connections}")
            except socket.timeout:
                continue  # 沒有新連線就重試
    except KeyboardInterrupt:
        print("\n[SHUTTING DOWN] Server is shutting down.")
    finally:
        for cs in client_sockets[:]:
            try:
                cs.send(Protocols.Response.SERVER_SHUTDOWN.encode())
                cs.close()
            except:
                pass
        server.close()

if __name__ == "__main__":
    start_server()
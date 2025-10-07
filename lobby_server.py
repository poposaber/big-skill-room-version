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
        
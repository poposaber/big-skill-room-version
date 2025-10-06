from message_format import MessageFormat

class Protocols:
    class UserToLobby:
        ROLE = MessageFormat("ROLE", [str]) #ROLE|user or gameserver
        EXIT = MessageFormat("EXIT")
    class LobbyToUser:
        WELCOME_USER = MessageFormat("WELCOME_USER")
        GOODBYE = MessageFormat("GOODBYE")
    class UserToGame:
        pass
    class GameToUser:
        pass
    class LobbyToGame:
        WELCOME_GAMESERVER = MessageFormat("WELCOME_GAMESERVER")
    class GameToLobby:
        pass
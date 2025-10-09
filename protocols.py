from message_format import MessageFormat

class Protocols:
    class UserToLobby:
        ROLE = MessageFormat("ROLE", [str])
        """ROLE|user or gameserver"""

        EXIT = MessageFormat("EXIT")
        """EXIT"""

        LOGIN = MessageFormat("LOGIN", [str, str]) 
        """LOGIN|(username)|(password)"""

        LOGOUT = MessageFormat("LOGOUT")
        """LOGOUT"""


    class LobbyToUser:
        WELCOME_USER = MessageFormat("WELCOME_USER")
        """WELCOME_USER"""

        WELCOME_GAMESERVER = MessageFormat("WELCOME_GAMESERVER")
        """WELCOME_GAMESERVER"""

        GOODBYE = MessageFormat("GOODBYE")
        """GOODBYE"""

        EVENT = MessageFormat("EVENT", [int, str]) 
        """EVENT|0 for invitation; 1 for acceptance|username"""

        LOGIN_RESULT = MessageFormat("LOGIN_RESULT", [int])
        """LOGIN_RESULT|0 success; -1 fail (wrong username or password); -2 fail (already logged in)"""

        LOGOUT_RESULT = MessageFormat("LOGOUT_RESULT", [int])
        """LOGOUT_RESULT|0 success; -1 fail (not logged in)"""

        UNKNOWN_COMMAND = MessageFormat("UNKNOWN_COMMAND")
        """UNKNOWN_COMMAND"""


    class UserToGame:
        pass
    class GameToUser:
        pass
    class LobbyToGame:
        WELCOME_GAMESERVER = MessageFormat("WELCOME_GAMESERVER")
    class GameToLobby:
        pass
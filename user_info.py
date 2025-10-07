from game import Game
class UserInfo:
    def __init__(self):
        self.name: str | None = None
        self.is_waiting = False
        self.inviting_users: list[str] = []
        self.users_inviting_me: list[str] = []
        self.playing_game: Game | None = None
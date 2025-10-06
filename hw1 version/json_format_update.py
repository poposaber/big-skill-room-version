import json
import os
USER_DB_FILE = 'user_db.json'

def load_user_db():
    if not os.path.exists(USER_DB_FILE):
        return {}
    with open(USER_DB_FILE, 'r') as f:
        return json.load(f)
    
def save_user_db(user_db: dict):
    with open(USER_DB_FILE, 'w') as f:
        json.dump(user_db, f, indent=2)

user_db = load_user_db()
for username, info in user_db.items():
    if "games_played" not in info:
        info["games_played"] = 0
    if "games_won" not in info:
        info["games_won"] = 0

save_user_db(user_db)
print("updated user_db.json.")

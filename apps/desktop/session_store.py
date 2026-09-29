import os
import json

APP_DIR = os.path.expanduser("~/.libreria-desktop")
SESSION_PATH = os.path.join(APP_DIR, "session.json")

def save_session(user_data, cookies_dict):
    os.makedirs(APP_DIR, exist_ok=True)
    with open(SESSION_PATH, 'w') as f:
        json.dump({"user": user_data, "cookies": cookies_dict}, f)

def load_session():
    if not os.path.exists(SESSION_PATH):
        return None, None
    try:
        with open(SESSION_PATH, 'r') as f:
            data = json.load(f)
            return data.get("user"), data.get("cookies")
    except:
        return None, None

def clear_session():
    if os.path.exists(SESSION_PATH):
        os.remove(SESSION_PATH)

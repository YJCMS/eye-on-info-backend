import os
from config import Config

def ensure_directory_exists():
    if not os.path.exists(Config.SAVE_DIR):
        os.makedirs(Config.SAVE_DIR)
        
def get_headers():
    return {'User-Agent': Config.USER_AGENT}

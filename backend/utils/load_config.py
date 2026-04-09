import json
from backend.utils.global_var import CONFIG_PATH

def load_config(config_path: str) -> dict:
    path = CONFIG_PATH + config_path
    with open(path, 'r') as f:
        config = json.load(f)
    return config
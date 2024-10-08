import json
import os


CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

with open(CONFIG_PATH, 'r') as config_file:
    CONFIG = json.load(config_file)
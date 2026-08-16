import os
import tomli
import tomli_w
from common.constants import BASE_DIR
from common.file_utils import ensure_dir

CONFIG_PATH = os.path.join(BASE_DIR, "settings.toml")

DEFAULT_CONFIG = {
    "network": {
        "proxy": "",
        "timeout": 30
    },
    "runtime": {
        "auto_check_java": True
    },
    "servers": {
        "instance_list": []
    }
}


class AppConfig:
    def __init__(self):
        self.data = {}
        self.load()

    def load(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "rb") as f:
                self.data = tomli.load(f)
        else:
            self.data = DEFAULT_CONFIG
            self.save()

    def save(self):
        with open(CONFIG_PATH, "wb") as f:
            tomli_w.dump(self.data, f)


app_config = AppConfig()
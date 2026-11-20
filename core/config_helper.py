import sys
import os
import json
from typing import Dict, Literal, Optional
from datetime import datetime

MsgLevel = Literal["INFO", "WARN", "ERROR"]


def get_exe_dir() -> str:
    if hasattr(sys, '_MEIPASS'):
        exe_path = sys.executable
    else:
        exe_path = __file__
    return os.path.dirname(os.path.abspath(exe_path))


class UiConfigHelper:
    def __init__(self, cfg_name: str):
        self.json_path = os.path.join(get_exe_dir(), "config")
        self.log_path = os.path.join(
            get_exe_dir(), "log", datetime.now().strftime("%Y-%m-%d"))
        os.makedirs(self.json_path, exist_ok=True)
        os.makedirs(self.log_path, exist_ok=True)
        self.cfg_path = os.path.join(self.json_path, cfg_name)

    @property
    def config_root(self) -> str:
        return self.json_path

    @property
    def log_root(self) -> str:
        return self.log_path

    def save_params(self, param_dict: Dict):
        try:
            with open(self.cfg_path, "w", encoding="utf-8") as f:
                json.dump(param_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存参数失败: {e}")

    def load_params(self, default_dict: Dict) -> Dict:
        if not os.path.exists(self.cfg_path):
            return default_dict.copy()
        try:
            with open(self.cfg_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            out = default_dict.copy()
            out.update(loaded)
            return out
        except Exception as e:
            print(f"加载参数异常，使用默认: {e}")
            return default_dict.copy()

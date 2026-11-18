import sys
import os
import json
from typing import Dict, Literal, Optional

MsgLevel = Literal["INFO", "WARN", "ERROR"]

def get_exe_dir() -> str:
    if hasattr(sys, '_MEIPASS'):
        exe_path = sys.executable
    else:
        exe_path = __file__
    return os.path.dirname(os.path.abspath(exe_path))

class UiConfigHelper:
    def __init__(self, cfg_name: str):
        self.cfg_path = os.path.join(get_exe_dir(), cfg_name)

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
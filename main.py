from core.app_config import AppConfig
from ui.main_window import MainWindow
from PyQt5.QtWidgets import QApplication
import sys
import os
# ========== 新增：优先设置dll搜索路径，必须放在最前面 ==========


def setup_colorimeter_dll_path():
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller打包exe运行：_MEIPASS 就是 _internal 目录
        base_dir = sys._MEIPASS
    else:
        # 本地开发调试：main.py所在目录
        base_dir = os.path.dirname(os.path.abspath(__file__))

    core_dir = os.path.join(base_dir, "mlcolorimeter", "core")
    if os.path.isdir(core_dir):
        # 插到PATH最前面，优先加载本包dll
        os.environ["PATH"] = core_dir + os.pathsep + os.environ["PATH"]
        print(f"[PATH] 已添加色度计core目录：{core_dir}")
    else:
        print(f"[WARN] 找不到core目录：{core_dir}")


setup_colorimeter_dll_path()


if __name__ == "__main__":
    colorimeter = AppConfig.get_colorimeter()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())

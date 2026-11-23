from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QSizePolicy,
    QMessageBox,
    QGroupBox,
    QGridLayout,
    QSpacerItem,
    QDialog,
    QComboBox,
    QFormLayout,
    QListWidget,
    QPlainTextEdit
)
from PyQt5.QtGui import QIntValidator, QIcon, QColor, QTextCharFormat
from core.app_config import AppConfig
from core.config_helper import UiConfigHelper, MsgLevel
from PyQt5.QtCore import pyqtSignal, Qt, QThread
import mlcolorimeter as mlcm
from scripts.FFC_calculate_binn import FFC_calculate
from ui.grayrange_dialog import GrayRangeDialog
from datetime import datetime
import os


class FFCCalculateBinningThread(QThread):
    finished = pyqtSignal()  # 线程完成信号
    error = pyqtSignal(str)  # 错误信号
    status_update = pyqtSignal(str)  # 状态更新信号

    def __init__(self, parameters):
        super().__init__()
        self.parameters = parameters

    def run(self):
        try:
            # 包装回调：接受level，msg，拼接成字符串再发给信号
            def callback_wrapper(level: MsgLevel, msg: str):
                self.status_update.emit(msg)
            FFC_calculate(
                status_callback=callback_wrapper, **self.parameters)  # type: ignore
            self.finished.emit()  # 发送完成信号
        except Exception as e:
            self.error.emit(str(e))  # 发送错误信号


class FFCCalculateBinningWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ffc calculate binning")
        self.setGeometry(200, 200, 800, 500)
        self.setWindowFlags(Qt.Window | Qt.WindowMaximizeButtonHint |
                            Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)  # type: ignore
        self.setWindowIcon(QIcon(
            "D:/pythonObject/ML_AutoCalibration_GUI/ML_AutoCalibration_GUI/FingerPrintScanMTF.ico"))
        self.colorimeter = AppConfig.get_colorimeter()
        self.intValidator = QIntValidator()
        self.dialog_title = "选择文件夹"
        self.default_path = ""
        self.roi_list = []
        self.vrange = {}
        self.binning_selector = ['Logic', 'Sensor']
        self.binning = ['ONE_BY_ONE', 'TWO_BY_TWO', 'FOUR_BY_FOUR']
        self.binning_mode = ['AVERAGE', 'SUM']
        self.pixel_format = ['MLMono8', 'MLMono10', 'MLMono12',
                             'MLMono16', 'MLRGB24', 'MLBayer', 'MLBayerGB8', 'MLBayerGB12']
        self.log_file_path = ""
        self.cfg_helper = UiConfigHelper("ffc_calculate_binning_params.json")
        self._init_ui()

        # 标识当前流程是否正在进行
        self.is_running = False
        # =====================默认参数，加载历史参数并回填UI==============================
        self.default_ui_params = {
            "ffc_path": "",
            "xyz_text": "X Y Z",
            "binn": "ONE_BY_ONE",
            "half_size": "3600",
            "gray_range": "3mm",
            "step": "2",
            "vrange": {},
            "roi_map": {},
        }
        self.cur_ui_params = self.cfg_helper.load_params(
            self.default_ui_params)
        self.fill_ui_by_params(self.cur_ui_params)

    def _init_ui(self):
        grid_layout = QGridLayout()

        self.label_file_path = QLabel("FFC图像保存路径")
        grid_layout.addWidget(self.label_file_path, 0, 0)
        self.line_edit_path = QLineEdit()
        self.line_edit_path.setReadOnly(True)  # 设置为只读
        self.line_edit_path.setPlaceholderText("未选择文件夹")
        self.line_edit_path.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_path, 1, 0)

        self.btn_browse = QPushButton("浏览...")
        self.btn_browse.clicked.connect(self._open_folder_dialog)
        grid_layout.addWidget(self.btn_browse, 1, 1)

        self.label_xyz_list = QLabel("xyz滤光片，输入如X Y Z Clear YA，以空格分隔")
        grid_layout.addWidget(self.label_xyz_list, 2, 0)
        self.line_edit_xyzlist = QLineEdit()
        self.line_edit_xyzlist.setText("X Y Z")
        self.line_edit_xyzlist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_xyzlist, 3, 0)

        self.label_binn = QLabel(" binning：")
        grid_layout.addWidget(self.label_binn, 4, 0)
        self.line_edit_binn = QComboBox()
        self.line_edit_binn.addItems(self.binning)
        self.line_edit_binn.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_binn, 5, 0)

        self.label_half_size = QLabel("half_size：(根据FOV修改)")
        grid_layout.addWidget(self.label_half_size, 6, 0)
        self.line_edit_half_size = QLineEdit()
        self.line_edit_half_size.setValidator(self.intValidator)
        self.line_edit_half_size.setText("3600")
        self.line_edit_half_size.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_half_size, 7, 0)

        self.label_gray_range = QLabel(
            "灰度范围：(输入两个值表示灰度最小值和最大值，例如5 11，表示灰度范围为50%到110%)")
        grid_layout.addWidget(self.label_gray_range, 8, 0)
        self.line_edit_gray_range = QLineEdit()
        self.line_edit_gray_range.setText("5 11")
        self.line_edit_gray_range.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_gray_range, 9, 0)

        self.label_step_loop = QLabel("步长：")
        grid_layout.addWidget(self.label_step_loop, 10, 0)
        self.line_edit_step_loop = QLineEdit()
        self.line_edit_step_loop.setValidator(self.intValidator)
        self.line_edit_step_loop.setText("2")
        self.line_edit_step_loop.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_step_loop, 11, 0)

        self.loop_display = QListWidget()
        self.loop_display.setFixedHeight(100)
        self.loop_display.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.loop_display, 12, 0)
        self.btn_submit = QPushButton("提交")
        self.btn_submit.clicked.connect(self.submit)
        grid_layout.addWidget(self.btn_submit, 12, 1)

        group_box1 = QGroupBox("roi设置")
        from_layout1 = QFormLayout()

        self.label_x_input = QLabel("x_input: ")
        self.line_edit_x_input = QLineEdit()
        self.line_edit_x_input.setValidator(self.intValidator)
        self.line_edit_x_input.setText("0")
        self.line_edit_x_input.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_y_input = QLabel("y_input: ")
        self.line_edit_y_input = QLineEdit()
        self.line_edit_y_input.setValidator(self.intValidator)
        self.line_edit_y_input.setText("0")
        self.line_edit_y_input.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_width_input = QLabel("width_input: ")
        self.line_edit_width_input = QLineEdit()
        self.line_edit_width_input.setValidator(self.intValidator)
        self.line_edit_width_input.setText("100")
        self.line_edit_width_input.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_height_input = QLabel("height_input: ")
        self.line_edit_height_input = QLineEdit()
        self.line_edit_height_input.setValidator(self.intValidator)
        self.line_edit_height_input.setText("100")
        self.line_edit_height_input.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)

        horizontal_layout5 = QHBoxLayout()
        horizontal_layout5.addWidget(self.label_x_input)
        horizontal_layout5.addWidget(self.line_edit_x_input)
        horizontal_layout5.addWidget(self.label_y_input)
        horizontal_layout5.addWidget(self.line_edit_y_input)
        horizontal_layout5.addWidget(self.label_width_input)
        horizontal_layout5.addWidget(self.line_edit_width_input)
        horizontal_layout5.addWidget(self.label_height_input)
        horizontal_layout5.addWidget(self.line_edit_height_input)
        from_layout1.addRow(horizontal_layout5)

        self.add_button = QPushButton("Add ROI")
        self.add_button.clicked.connect(self.add_roi)
        self.delete_button = QPushButton("Delete ROI")
        self.delete_button.clicked.connect(self.delete_roi)
        from_layout1.addRow(self.add_button, self.delete_button)

        self.roi_display = QListWidget()
        self.roi_display.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        from_layout1.addRow(self.roi_display)

        group_box1.setLayout(from_layout1)
        grid_layout.addWidget(group_box1, 13, 0)

        self.btn_capture = QPushButton("开始计算")
        self.btn_capture.clicked.connect(self.start_ffc_calculate)
        grid_layout.addWidget(self.btn_capture, 14, 0)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        grid_layout.addWidget(self.log_box, 15, 0)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum,
                             QSizePolicy.Expanding)
        grid_layout.addItem(spacer)

        self.setLayout(grid_layout)

    # 回填UI
    def fill_ui_by_params(self, p):
        self.line_edit_path.setText(p["ffc_path"])
        self.line_edit_xyzlist.setText(p["xyz_text"])
        self.line_edit_binn.setCurrentText(p["binn"])
        self.line_edit_half_size.setText(p["half_size"])
        self.line_edit_gray_range.setText(p["gray_range"])
        self.line_edit_step_loop.setText(p["step"])

        roi_serial = p.get("roi_map", {})
        self.roi_list.clear()
        self.roi_display.clear()
        self.roi_dict = {}
        for (x, y, w, h) in roi_serial:
            roi = mlcm.pyCVRect(x, y, w, h)
            self.roi_list.append(roi)
            roi_str = f"{x},{y},{w},{h}"
            self.roi_display.addItem(roi_str)

        # ---------------- 回填vrange和loop_display ----------------
        self.vrange.clear()
        self.loop_display.clear()
        loaded_vrange = p.get("vrange", {})
        for loop_i_str, gray_tuple in loaded_vrange.items():
            # json key 会变成字符串，转回int
            loop_i = int(loop_i_str)
            min_g, max_g = gray_tuple
            self.vrange[loop_i] = (min_g, max_g)
            loop_str = f"{loop_i}0%：{min_g}-{max_g}"
            self.loop_display.addItem(loop_str)

    # 读取当前UI所有参数，序列化

    def read_ui_params(self):
        roi_serial = []
        for r in self.roi_list:
            roi_serial.append([r.x, r.y, r.width, r.height])

        return {
            "ffc_path": self.line_edit_path.text().strip(),
            "xyz_text": self.line_edit_xyzlist.text().strip(),
            "binn": self.line_edit_binn.currentText(),
            "half_size": self.line_edit_half_size.text().strip(),
            "gray_range": self.line_edit_gray_range.text().strip(),
            "step": self.line_edit_step_loop.text().strip(),
            "vrange": self.vrange,
            "roi_map": roi_serial
        }

    def _open_folder_dialog(self):
        # 打开文件夹选择对话框
        folder_path = QFileDialog.getExistingDirectory(
            self,
            self.dialog_title,
            self.default_path if self.default_path else "",  # 初始路径
            options=QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,  # type: ignore
        )

        if folder_path:
            self.line_edit_path.setText(folder_path)
        else:
            QMessageBox.critical(self, "MLColorimeter", "选择路径错误",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

    def add_roi(self):

        try:
            x = int(self.line_edit_x_input.text().strip())
            y = int(self.line_edit_y_input.text().strip())
            width = int(self.line_edit_width_input.text().strip())
            height = int(self.line_edit_height_input.text().strip())

            # 创建roi并添加到列表
            roi = mlcm.pyCVRect(x, y, width, height)
            self.roi_list.append(roi)
            # 显示在控件上
            roi_str = f"{x},{y},{width},{height}"
            self.roi_display.addItem(roi_str)
        except Exception as e:
            QMessageBox.critical(self, "MLColorimeter", "exception" +
                                 str(e), QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

    def delete_roi(self):
        try:

            current_item = self.roi_display.currentItem()
            if current_item is None:
                QMessageBox.warning(self, "警告", "请先选择要删除的ROI", QMessageBox.Ok)
                return

            roi_str = current_item.text()
            # 解析ROi
            roi_coords = list(map(int, roi_str.split(',')))
            roi_list = [int(roi) for roi in roi_coords]
            roi_x = roi_list[0]
            roi_y = roi_list[1]
            roi_w = roi_list[2]
            roi_h = roi_list[3]
            roi_remove = mlcm.pyCVRect(roi_x, roi_y, roi_w, roi_h)
            for index, roi in enumerate(self.roi_list):
                if (roi.x == roi_remove.x and roi.y == roi_remove.y and roi.width == roi_remove.width and roi.height == roi_remove.height):
                    # 只删除第一个匹配的roi
                    del self.roi_list[index]
                    break  # 找到并删除后退出循环

            row = self.roi_display.row(current_item)
            self.roi_display.takeItem(row)
        except Exception as e:
            QMessageBox.critical(self, "MLColorimeter", "exception" +
                                 str(e), QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

    def start_ffc_calculate(self):
        try:
            self.file_path = self.line_edit_path.text()
            if not self.file_path:
                QMessageBox.warning(self, "MLColorimeter", "请选择FFC图像保存路径",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                return
            self.xyz_list = self.line_edit_xyzlist.text().strip().split()
            self.half_size = int(self.line_edit_half_size.text())
            self.selected_binning = self.line_edit_binn.currentText()

            # 新建日志文件
            self.log_file_path = os.path.join(
                self.cfg_helper.log_path, f"ffc_calculate_binning_log.txt")
            self.btn_capture.setEnabled(False)
            self.is_running = True
            parameters = {
                'xyz_list': self.xyz_list,
                'filepath': self.file_path,
                'vrange': self.vrange,
                'binning': self.selected_binning,
                'half_size': self.half_size,
                'roi_list': self.roi_list
            }
            self.ffc_calculate_thread = FFCCalculateBinningThread(
                parameters)
            self.ffc_calculate_thread.finished.connect(
                self.on_ffccalculate_finish)
            self.ffc_calculate_thread.error.connect(
                self.on_ffccalculate_error)
            self.ffc_calculate_thread.status_update.connect(
                self.flush_log)
            self.ffc_calculate_thread.start()
        except Exception as e:
            QMessageBox.critical(self, "MLColorimeter", "exception" +
                                 str(e), QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            self.btn_capture.setEnabled(True)
            self.is_running = False

    def flush_log(self, msg):
        cursor = self.log_box.textCursor()
        cursor.movePosition(cursor.End)

        fmt = QTextCharFormat()
        # 文字固定黑色，只靠前面emoji区分等级
        fmt.setForeground(QColor("#000000"))
        if "info" in msg.lower():
            prefix = "🟢 "
        elif "error" in msg.lower():
            prefix = "🔴 "
        elif "warn" in msg.lower():
            prefix = "🟡 "
        else:
            prefix = "⚪ "
        full_text = f"{prefix}{datetime.now().strftime('%Y-%m-%d_%H-%M-%S.%f')[:-3]} {msg}\n"
        cursor.insertText(full_text, fmt)
        self.log_box.setTextCursor(cursor)
        # 自动滚动到底部
        sb = self.log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

        # 写入本地txt日志
        if self.log_file_path:
            try:
                with open(self.log_file_path, "a", encoding="utf-8") as f:
                    f.write(full_text)
            except Exception as log_err:
                # 日志写入失败不打断主流程
                print(f"write log file failed: {log_err}")

    def on_ffccalculate_finish(self):
        QMessageBox.information(self, "MLColorimeter", "计算完成!", QMessageBox.Ok)
        self.btn_capture.setEnabled(True)
        self.is_running = False  # 标识定标完成

    def on_ffccalculate_error(self, error_message):
        QMessageBox.critical(self, "MLColorimeter",
                             "发生错误: " + error_message, QMessageBox.Ok)
        self.btn_capture.setEnabled(True)
        self.is_running = False  # 标识定标完成

    def closeEvent(self, event):
        if self.is_running:
            # 如果正在进行定标，拦截关闭事件
            event.ignore()
            QMessageBox.warning(self, "警告", "程序运行中，请勿关闭窗口", QMessageBox.Ok)
        else:
            # ==============关闭窗口保存当前UI参数====================
            p = self.read_ui_params()
            self.cfg_helper.save_params(p)
            event.accept()

    def submit(self):
        try:
            self.loop_display.clear()
            gray_range_text = self.line_edit_gray_range.text().strip().split()
            if not gray_range_text:
                QMessageBox.warning(self, "MLColorimeter",
                                    "请输入灰度范围", QMessageBox.Ok)
                return
            else:
                gray_range = [int(gray) for gray in gray_range_text]
            min_loop = gray_range[0]
            max_loop = gray_range[1]
            step = int(self.line_edit_step_loop.text())
            # 清空之前的灰度范围
            self.vrange.clear()

            for loop_i in range(min_loop, max_loop, step):
                dialog = GrayRangeDialog(loop_i, self)
                if dialog.exec_() == QDialog.Accepted:
                    min_gray, max_gray = dialog.get_values()
                    self.vrange[loop_i] = (min_gray, max_gray)
                    loop_str = f"{loop_i}0%：{min_gray}-{max_gray}"
                    self.loop_display.addItem(loop_str)
        except Exception as e:
            QMessageBox.critical(self, "MLColorimeter", "exception" +
                                 str(e), QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

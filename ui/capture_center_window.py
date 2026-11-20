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
    QCheckBox,
    QDialog,
    QFormLayout,
    QPlainTextEdit
)
from PyQt5.QtGui import QIntValidator, QIcon, QColor, QTextCharFormat
from core.app_config import AppConfig
from core.config_helper import UiConfigHelper, MsgLevel
from PyQt5.QtCore import pyqtSignal, Qt, QThread
import mlcolorimeter as mlcm
from scripts.capture_colorfilter_center import capture_colorfilter_center
from scripts.capture_RX_center import capture_RX_center
from ui.exposureconfig_window import ExposureConfigWindow
import os
from datetime import datetime


class CaptureRXCenterThread(QThread):
    finished = pyqtSignal()  # 线程完成信号
    error = pyqtSignal(str)  # 错误信号
    status_update = pyqtSignal(str)  # 状态更新信号

    def __init__(self, parameters):
        super().__init__()
        self.parameters = parameters

    def run(self):
        try:
            def callback_wrapper(level: MsgLevel, msg: str):
                self.status_update.emit(msg)
            capture_RX_center(
                status_callback=callback_wrapper, **self.parameters)  # type: ignore
            self.finished.emit()  # 发送完成信号
        except Exception as e:
            self.error.emit(str(e))  # 发送错误信号


class CaptureColorfilterCenterThread(QThread):
    finished = pyqtSignal()  # 线程完成信号
    error = pyqtSignal(str)  # 错误信号
    status_update = pyqtSignal(str)  # 状态更新信号

    def __init__(self, parameters):
        super().__init__()
        self.parameters = parameters

    def run(self):
        try:
            def callback_wrapper(level: MsgLevel, msg: str):
                self.status_update.emit(msg)
            capture_colorfilter_center(
                status_callback=callback_wrapper, **self.parameters)  # type: ignore
            self.finished.emit()  # 发送完成信号
        except Exception as e:
            self.error.emit(str(e))  # 发送错误信号


class CaptureCenterWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Capture Center")
        self.setGeometry(200, 200, 400, 200)
        self.setWindowFlags(Qt.Window | Qt.WindowMaximizeButtonHint |
                            Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)  # type: ignore
        self.setWindowIcon(QIcon(
            "D:/pythonObject/ML_AutoCalibration_GUI/ML_AutoCalibration_GUI/FingerPrintScanMTF.ico"))
        self.colorimeter = AppConfig.get_colorimeter()
        self.intValidator = QIntValidator()
        self.dialog_title = "选择文件夹"
        self.default_path = ""
        self.file_name = ""
        self.exposure_map_obj = {}
        self.log_file_path = ""
        self.cfg_helper = UiConfigHelper("capture_center_params.json")
        self._init_ui()
        self.is_running = False
        # =====================默认参数，加载历史参数并回填UI==============================
        self.default_ui_params = {
            "nd_text": "4",
            "xyz_text": "1",
            "use_rx": False,
            "sph_text": "-6 -5 -4 -3 -2 -1 0 1 2 3 4 5 6",
            "cyl_text": "-4 -3.75 -3.5 -3.25 -3 -2.75 -2.5 -2.25 -2 -1.75 -1.5 -1.25 -1 -0.75 -0.5 -0.25 0",
            "axis_text": "0 15 30",
            "roi_x": "0",
            "roi_y": "0",
            "roi_w": "300",
            "roi_h": "300",
            "save_path": "",
            "exposure_map_serial": {}
        }
        self.cur_ui_params = self.cfg_helper.load_params(
            self.default_ui_params)
        self.fill_ui_by_params(self.cur_ui_params)

    def _init_ui(self):
        grid_layout = QGridLayout()

        self.label_ndlist = QLabel()
        self.label_ndlist.setText(
            "nd列表, (4: ND0, 5: ND1, 6: ND2, 7:ND3, 8:ND4), 以空格隔开")
        grid_layout.addWidget(self.label_ndlist, 0, 0)
        self.line_edit_ndlist = QLineEdit()
        self.line_edit_ndlist.setText("4")
        self.line_edit_ndlist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_ndlist, 1, 0)

        self.label_xyzlist = QLabel()
        self.label_xyzlist.setText(
            "xyz列表, (1: X, 2: Y, 3: Z, 10: Clear, 12: YA), 以空格隔开")
        grid_layout.addWidget(self.label_xyzlist, 2, 0)
        self.line_edit_xyzlist = QLineEdit()
        self.line_edit_xyzlist.setText("1")
        self.line_edit_xyzlist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_xyzlist, 3, 0)

        self.btn_load_config = QPushButton("曝光时间配置")
        self.btn_load_config.clicked.connect(self.load_exposure_config)
        grid_layout.addWidget(self.btn_load_config, 3, 1)

        self.cb_useRX = QCheckBox()
        self.cb_useRX.setText("启用RX")
        self.cb_useRX.setChecked(False)
        self.cb_useRX.stateChanged.connect(self._useRX_state_changed)
        grid_layout.addWidget(self.cb_useRX, 4, 0)

        self.label_sphlist = QLabel()
        self.label_sphlist.setText(
            "sph列表, (例如: -6 -5 -4 -3 -2 -1 0 1 2 3 4 5 6), 以空格隔开")
        grid_layout.addWidget(self.label_sphlist, 5, 0)

        self.line_edit_sphlist = QLineEdit()
        self.line_edit_sphlist.setText("-6 -5 -4 -3 -2 -1 0 1 2 3 4 5 6")
        self.line_edit_sphlist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_sphlist, 6, 0)

        self.label_cyllist = QLabel()
        self.label_cyllist.setText(
            "cyl列表, (例如: -4 -3.5 -3 -2.5 -2 -1.5 -1 -0.5 0), 以空格隔开")
        grid_layout.addWidget(self.label_cyllist, 7, 0)

        self.line_edit_cyllist = QLineEdit()
        self.line_edit_cyllist.setText(
            "-4 -3.75 -3.5 -3.25 -3 -2.75 -2.5 -2.25 -2 -1.75 -1.5 -1.25 -1 -0.75 -0.5 -0.25 0")
        self.line_edit_cyllist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_cyllist, 8, 0)

        self.label_axislist = QLabel()
        self.label_axislist.setText(
            "axis列表, (例如: 0 15 30 45 60 75 90 105 120 135 150 165), 以空格隔开")
        grid_layout.addWidget(self.label_axislist, 9, 0)

        self.line_edit_axislist = QLineEdit()
        self.line_edit_axislist.setText(
            "0 15 30 45 60 75 90 105 120 135 150 165")
        self.line_edit_axislist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_axislist, 10, 0)

        group_box1 = QGroupBox("roi设置(仅启用RX时设置)")
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
        self.line_edit_width_input.setText("300")
        self.line_edit_width_input.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_height_input = QLabel("height_input: ")
        self.line_edit_height_input = QLineEdit()
        self.line_edit_height_input.setValidator(self.intValidator)
        self.line_edit_height_input.setText("300")
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

        group_box1.setLayout(from_layout1)
        grid_layout.addWidget(group_box1, 11, 0)

        self.label_path = QLabel()
        self.label_path.setText("保存路径:")
        grid_layout.addWidget(self.label_path, 12, 0)

        self.line_edit_path = QLineEdit()
        self.line_edit_path.setReadOnly(True)  # 设置为只读
        self.line_edit_path.setPlaceholderText("未选择文件夹")
        self.line_edit_path.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_path, 13, 0)

        self.btn_browse = QPushButton("浏览...")
        self.btn_browse.clicked.connect(self._open_folder_dialog)
        grid_layout.addWidget(self.btn_browse, 13, 1)

        self.btn_capture = QPushButton("开始拍图")
        self.btn_capture.clicked.connect(self.start_capture)
        grid_layout.addWidget(self.btn_capture, 14, 0)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        grid_layout.addWidget(self.log_box, 15, 0)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum,
                             QSizePolicy.Expanding)
        grid_layout.addItem(spacer)

        self.setLayout(grid_layout)

        self.label_sphlist.hide()
        self.line_edit_sphlist.hide()
        self.label_cyllist.hide()
        self.line_edit_cyllist.hide()
        self.label_axislist.hide()
        self.line_edit_axislist.hide()

    # 回填UI

    def fill_ui_by_params(self, p):
        self.line_edit_ndlist.setText(p["nd_text"])
        self.line_edit_xyzlist.setText(p["xyz_text"])
        self.cb_useRX.setChecked(p["use_rx"])
        self.line_edit_sphlist.setText(p["sph_text"])
        self.line_edit_cyllist.setText(p["cyl_text"])
        self.line_edit_axislist.setText(p["axis_text"])
        self.line_edit_x_input.setText(p["roi_x"])
        self.line_edit_y_input.setText(p["roi_y"])
        self.line_edit_width_input.setText(p["roi_w"])
        self.line_edit_height_input.setText(p["roi_h"])
        self.line_edit_path.setText(p["save_path"])

        serial_map = p.get("exposure_map_serial", {})
        self.exposure_map_obj = {}
        for nd_name, xyz_dict in serial_map.items():
            nd_enum = mlcm.str_to_MLFilterEnum(nd_name)
            self.exposure_map_obj[nd_enum] = {}
            for xyz_name, setting_data in xyz_dict.items():
                xyz_enum = mlcm.str_to_MLFilterEnum(xyz_name)
                emode = mlcm.ExposureMode.Fixed if setting_data[
                    "exposure_mode"] == "Fixed" else mlcm.ExposureMode.Auto
                self.exposure_map_obj[nd_enum][xyz_enum] = mlcm.pyExposureSetting(
                    exposure_mode=emode,
                    exposure_time=setting_data["exposure_time"]
                )

    # 读取当前UI所有参数，序列化
    def read_ui_params(self):
        exp_serial = {}
        for nd_enum, xyz_dict in self.exposure_map_obj.items():
            exp_serial[nd_enum.name] = {}
            for xyz_enum, s in xyz_dict.items():
                exp_serial[nd_enum.name][xyz_enum.name] = {
                    "exposure_mode": s.exposure_mode.name,
                    "exposure_time": s.exposure_time
                }
        return {
            "nd_text": self.line_edit_ndlist.text().strip(),
            "xyz_text": self.line_edit_xyzlist.text().strip(),
            "use_rx": self.cb_useRX.isChecked(),
            "sph_text": self.line_edit_sphlist.text().strip(),
            "cyl_text": self.line_edit_cyllist.text().strip(),
            "axis_text": self.line_edit_axislist.text().strip(),
            "roi_x": self.line_edit_x_input.text().strip(),
            "roi_y": self.line_edit_y_input.text().strip(),
            "roi_w": self.line_edit_width_input.text().strip(),
            "roi_h": self.line_edit_height_input.text().strip(),
            "save_path": self.line_edit_path.text().strip(),
            "exposure_map_serial": exp_serial
        }

    def start_capture(self):
        try:
            nd_enum = [int(nd)
                       for nd in self.line_edit_ndlist.text().strip().split()]
            self.nd_list = [mlcm.MLFilterEnum(nd) for nd in nd_enum]
            xyz_enum = [int(xyz)
                        for xyz in self.line_edit_xyzlist.text().strip().split()]
            self.xyz_list = [mlcm.MLFilterEnum(xyz) for xyz in xyz_enum]
            self.save_path = self.line_edit_path.text().strip()
            if not self.save_path:
                QMessageBox.critical(self, "MLColorimeter", "请先选择保存路径",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                return
            # ========== 生成本次运行的时间戳，用于日志文件 ==========
            run_ts = datetime.now().strftime('%Y-%m-%d')
            self.log_file_path = os.path.join(
                self.save_path, f"{run_ts}_capture_center_log.txt")
            if self.cb_useRX.isChecked():
                self.sph_list = [
                    float(sph) for sph in self.line_edit_sphlist.text().strip().split()]
                self.cyl_list = [
                    float(cyl) for cyl in self.line_edit_cyllist.text().strip().split()]
                self.axis_list = [
                    int(axis) for axis in self.line_edit_axislist.text().strip().split()]
                x = int(self.line_edit_x_input.text())
                y = int(self.line_edit_y_input.text())
                width = int(self.line_edit_width_input.text())
                height = int(self.line_edit_height_input.text())
                self.roi = mlcm.pyCVRect(x, y, width, height)
                self.btn_capture.setEnabled(False)
                self.is_running = True
                parameters = {
                    'colorimeter': self.colorimeter,
                    'sph_list': self.sph_list,
                    'cyl_list': self.cyl_list,
                    'axis_list': self.axis_list,
                    'save_path': self.save_path,
                    'nd_list': self.nd_list,
                    'xyz_list': self.xyz_list,
                    'roi': self.roi,
                    'exposure_map_obj': self.exposure_map_obj
                }
                self.captureRXcenterThread = CaptureRXCenterThread(parameters)
                self.captureRXcenterThread.finished.connect(
                    self.on_captureCenter_finished)
                self.captureRXcenterThread.error.connect(
                    self.on_captureCenter_error)
                self.captureRXcenterThread.status_update.connect(
                    self.flush_log)
                self.captureRXcenterThread.start()

            else:
                self.btn_capture.setEnabled(False)
                self.is_running = True
                parameters = {
                    'colorimeter': self.colorimeter,
                    'save_path': self.save_path,
                    'nd_list': self.nd_list,
                    'xyz_list': self.xyz_list,
                    'exposure_map_obj': self.exposure_map_obj
                }
                self.captureColorfiltercenterThread = CaptureColorfilterCenterThread(
                    parameters)
                self.captureColorfiltercenterThread.finished.connect(
                    self.on_captureCenter_finished)
                self.captureColorfiltercenterThread.error.connect(
                    self.on_captureCenter_error)
                self.captureColorfiltercenterThread.status_update.connect(
                    self.flush_log)
                self.captureColorfiltercenterThread.start()

        except Exception as e:
            QMessageBox.critical(self, "MLColorimeter", "exception" + e,  # type: ignore
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            self.btn_capture.setEnabled(True)
            self.is_running = False

    def on_captureCenter_finished(self):
        QMessageBox.information(self, "MLColorimeter", "完成!", QMessageBox.Ok)
        self.btn_capture.setEnabled(True)
        self.is_running = False  # 标识定标完成

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

    def on_captureCenter_error(self, error_message):
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

    def _open_folder_dialog(self):
        # 打开文件夹选择对话框
        folder_path = QFileDialog.getExistingDirectory(
            self,
            self.dialog_title,
            self.default_path if self.default_path else "",  # 初始路径
            options=QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,  # type: ignore
        )

        if folder_path:
            self.save_path = folder_path
            self.line_edit_path.setText(folder_path)
        else:
            QMessageBox.critical(self, "MLColorimeter", "选择路径错误",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

    def load_exposure_config(self):
        try:
            self.nd_list = self.line_edit_ndlist.text().strip().split()
            self.xyz_list = self.line_edit_xyzlist.text().strip().split()
            self.exposure_config_window = ExposureConfigWindow(
                self.nd_list, self.xyz_list, exposure_map=self.exposure_map_obj)
            # 连接信号
            self.exposure_config_window.config_saved.connect(
                self.update_config)
            self.exposure_config_window.exec_()
        except Exception as e:
            QMessageBox.critical(self, "MLColorimeter", "exception" + e,  # type: ignore
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

    def update_config(self, exposure_map):
        # print("Received exposure map:", exposure_map)
        self.exposure_map_obj = {}
        for nd_str, xyz_dict in exposure_map.items():
            nd_enum = mlcm.str_to_MLFilterEnum(nd_str)
            self.exposure_map_obj[nd_enum] = {}
            for xyz_str, setting in xyz_dict.items():
                xyz_enum = mlcm.str_to_MLFilterEnum(xyz_str)
                exposure_mode = mlcm.ExposureMode.Fixed if setting[
                    'exposure_mode'] == 'Fixed' else mlcm.ExposureMode.Auto
                exposure_time = setting['exposure_time']
                self.exposure_map_obj[nd_enum][xyz_enum] = mlcm.pyExposureSetting(
                    exposure_mode=exposure_mode,
                    exposure_time=exposure_time
                )

    def _useRX_state_changed(self):
        if self.cb_useRX.isChecked():
            self.label_sphlist.show()
            self.line_edit_sphlist.show()
            self.label_cyllist.show()
            self.line_edit_cyllist.show()
            self.label_axislist.show()
            self.line_edit_axislist.show()
        else:
            self.label_sphlist.hide()
            self.line_edit_sphlist.hide()
            self.label_cyllist.hide()
            self.line_edit_cyllist.hide()
            self.label_axislist.hide()
            self.line_edit_axislist.hide()

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
    QPlainTextEdit
)
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QIcon, QColor, QTextCharFormat
from core.app_config import AppConfig
from core.config_helper import UiConfigHelper, MsgLevel
from PyQt5.QtCore import pyqtSignal, Qt, QThread
import mlcolorimeter as mlcm
from scripts.calculate_sph_cyl_coefficient_colorcamera import calculate_sph_cyl_coefficinet
import os
from datetime import datetime


class CalculateSphCylCoefficientColorCameraThread(QThread):
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
            calculate_sph_cyl_coefficinet(
                status_callback=callback_wrapper, **self.parameters)  # type: ignore
            self.finished.emit()  # 发送完成信号
        except Exception as e:
            self.error.emit(str(e))  # 发送错误信号


class CalculateSphCylCoefficientColorCameraWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CalculateSphCylCoefficient_ColorCamera")
        self.setGeometry(200, 200, 800, 500)
        self.setWindowFlags(Qt.Window | Qt.WindowMaximizeButtonHint |
                            Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)  # type: ignore
        self.setWindowIcon(QIcon(
            "D:/pythonObject/ML_AutoCalibration_GUI/ML_AutoCalibration_GUI/FingerPrintScanMTF.ico"))
        self.colorimeter = AppConfig.get_colorimeter()
        self.doubleValidator = QDoubleValidator()
        self.intValidator = QIntValidator()
        self.dialog_title = "选择文件夹"
        self.default_path = ""
        self.file_name = "sph_cyl_coefficient.xlsx"
        self.exposure_map_obj = {}
        self.nd_list = ['ND0', 'ND1', 'ND2', 'ND3', 'ND4', 'ND5']
        self.binning_selector = ['Logic', 'Sensor']
        self.binning_mode = ['AVERAGE', 'SUM']
        self.pixel_format = ['MLMono8', 'MLMono10', 'MLMono12',
                             'MLMono16', 'MLRGB24', 'MLBayer', 'MLBayerGB8', 'MLBayerGB12']
        self.log_file_path = ""
        self.cfg_helper = UiConfigHelper(
            "sph_cyl_coefficient_colorcamera_params.json")
        self._init_ui()
        # 标识当前流程是否正在运行
        self.is_running = False

        # =====================默认参数，加载历史参数并回填UI==============================
        self.default_ui_params = {
            "nd_text": "ND0",
            "exposure_time": "100",
            "avg_count": "10",
            "sph_text": "-6 -5 -4 -3 -2 -1 0 1 2 3 4 5 6",
            "cyl_text": "-4 -3.75 -3.5 -3.25 -3 -2.75 -2.5 -2.25 -2 -1.75 -1.5 -1.25 -1 -0.75 -0.5 -0.25 0",
            "roi_x": "0",
            "roi_y": "0",
            "roi_w": "300",
            "roi_h": "300",
            "save_path": "",
        }
        self.cur_ui_params = self.cfg_helper.load_params(
            self.default_ui_params)
        self.fill_ui_by_params(self.cur_ui_params)

    def _init_ui(self):
        grid_layout = QGridLayout()

        self.label_nd_selector = QLabel("ND:")
        grid_layout.addWidget(self.label_nd_selector, 0, 0)

        self.line_edit_nd_selector = QComboBox()
        self.line_edit_nd_selector.addItems(self.nd_list)
        self.line_edit_nd_selector.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_nd_selector, 1, 0)

        self.label_exposure_time = QLabel("曝光时间(ms):")
        grid_layout.addWidget(self.label_exposure_time, 2, 0)
        self.line_edit_exposure_time = QLineEdit()
        self.line_edit_exposure_time.setValidator(self.doubleValidator)
        self.line_edit_exposure_time.setText("100")
        self.line_edit_exposure_time.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_exposure_time, 3, 0)

        self.label_avg_count = QLabel("avg_count:")
        grid_layout.addWidget(self.label_avg_count, 4, 0)
        self.line_edit_avg_count = QLineEdit()
        self.line_edit_avg_count.setValidator(self.intValidator)
        self.line_edit_avg_count.setText("10")
        self.line_edit_avg_count.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_avg_count, 5, 0)

        self.label_sphlist = QLabel(
            "sph列表, (例如: -6 -5 -4 -3 -2 -1 0 1 2 3 4 5 6), 以空格隔开")
        grid_layout.addWidget(self.label_sphlist, 6, 0)
        self.line_edit_sphlist = QLineEdit()
        self.line_edit_sphlist.setText("-6 -5 -4 -3 -2 -1 0 1 2 3 4 5 6")
        self.line_edit_sphlist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_sphlist, 7, 0)

        self.label_cyllist = QLabel(
            "cyl列表, (例如: -4 -3.5 -3 -2.5 -2 -1.5 -1 -0.5 0), 以空格隔开")
        grid_layout.addWidget(self.label_cyllist, 8, 0)
        self.line_edit_cyllist = QLineEdit()
        self.line_edit_cyllist.setText(
            "-4 -3.75 -3.5 -3.25 -3 -2.75 -2.5 -2.25 -2 -1.75 -1.5 -1.25 -1 -0.75 -0.5 -0.25 0")
        self.line_edit_cyllist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_cyllist, 9, 0)

        group_box1 = QGroupBox("roi设置(calculate M matrix)")
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
        grid_layout.addWidget(group_box1, 10, 0)

        self.label_path = QLabel()
        self.label_path.setText("保存路径:")
        grid_layout.addWidget(self.label_path, 11, 0)

        self.line_edit_path = QLineEdit()
        self.line_edit_path.setReadOnly(True)  # 设置为只读
        self.line_edit_path.setPlaceholderText("未选择文件夹")
        self.line_edit_path.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_path, 12, 0)

        self.btn_browse = QPushButton("浏览...")
        self.btn_browse.clicked.connect(self._open_folder_dialog)
        grid_layout.addWidget(self.btn_browse, 12, 1)

        self.btn_capture = QPushButton("计算系数")
        self.btn_capture.clicked.connect(self.start_calculate)
        grid_layout.addWidget(self.btn_capture, 13, 0)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        grid_layout.addWidget(self.log_box, 14, 0)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum,
                             QSizePolicy.Expanding)
        grid_layout.addItem(spacer)

        self.setLayout(grid_layout)

    def fill_ui_by_params(self, p):
        self.line_edit_nd_selector.setItemText(0, p["nd_text"])
        self.line_edit_exposure_time.setText(p["exposure_time"])
        self.line_edit_avg_count.setText(p["avg_count"])
        self.line_edit_cyllist.setText(p["cyl_text"])
        self.line_edit_sphlist.setText(p["sph_text"])
        self.line_edit_x_input.setText(p["roi_x"])
        self.line_edit_y_input.setText(p["roi_y"])
        self.line_edit_width_input.setText(p["roi_w"])
        self.line_edit_height_input.setText(p["roi_h"])
        self.line_edit_path.setText(p["save_path"])

    # 读取当前UI所有参数，序列化

    def read_ui_params(self):
        return {
            "nd_text": self.line_edit_nd_selector.currentText(),
            "exposure_time": self.line_edit_exposure_time.text().strip(),
            "sph_text": self.line_edit_sphlist.text().strip(),
            "cyl_text": self.line_edit_cyllist.text().strip(),
            "avg_count": self.line_edit_avg_count.text().strip(),
            "roi_x": self.line_edit_x_input.text().strip(),
            "roi_y": self.line_edit_y_input.text().strip(),
            "roi_w": self.line_edit_width_input.text().strip(),
            "roi_h": self.line_edit_height_input.text().strip(),
            "save_path": self.line_edit_path.text().strip()
        }

    def start_calculate(self):
        try:
            self.nd = self.get_current_filter(
                self.line_edit_nd_selector.currentText())
            self.exposure_time = float(self.line_edit_exposure_time.text())
            self.exposure = mlcm.pyExposureSetting(
                mlcm.ExposureMode.Fixed, self.exposure_time)
            self.avg_count = int(self.line_edit_avg_count.text())
            self.sph_list = [
                float(sph) for sph in self.line_edit_sphlist.text().strip().split()]
            self.cyl_list = [
                float(cyl) for cyl in self.line_edit_cyllist.text().strip().split()]
            x = int(self.line_edit_x_input.text())
            y = int(self.line_edit_y_input.text())
            width = int(self.line_edit_width_input.text())
            height = int(self.line_edit_height_input.text())
            self.roi = mlcm.pyCVRect(x, y, width, height)
            self.save_path = self.line_edit_path.text()
            if not self.save_path:
                QMessageBox.critical(self, "MLColorimeter", "请先选择保存路径",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                return
            # ========== 生成本次运行的时间戳，用于日志文件 ==========
            run_ts = datetime.now().strftime('%Y-%m-%d')
            self.log_file_path = os.path.join(
                self.save_path, f"{run_ts}_sph_cyl_color_log.txt")

            self.btn_capture.setEnabled(False)
            self.is_running = True
            parameters = {
                'colorimeter': self.colorimeter,
                'save_path': self.save_path,
                'file_name': self.file_name,
                'nd': self.nd,
                'exposure': self.exposure,
                'avg_count': self.avg_count,
                'sph_list': self.sph_list,
                'cyl_list': self.cyl_list,
                'roi': self.roi
            }
            self.calculate_thread = CalculateSphCylCoefficientColorCameraThread(
                parameters)
            self.calculate_thread.finished.connect(self.on_calculate_finished)
            self.calculate_thread.error.connect(self.on_calculate_error)
            self.calculate_thread.status_update.connect(self.flush_log)
            self.calculate_thread.start()  # 启动线程
        except Exception as e:
            QMessageBox.critical(self, "MLColorimeter", "exception" + e,  # type: ignore
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
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

    def on_calculate_finished(self):
        QMessageBox.information(self, "MLColorimeter", "计算完成!", QMessageBox.Ok)

        self.btn_capture.setEnabled(True)
        self.is_running = False  # 标识定标完成

    def on_calculate_error(self, error_message):
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
            self.line_edit_path.setText(folder_path)
        else:
            QMessageBox.critical(self, "MLColorimeter", "选择路径错误",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

    def get_current_pixel_format(self):
        # 获取当前选择的项
        selected_format = self.line_edit_pixel_format.currentText()
        # 创建字符串到枚举值的映射
        format_mapping = {
            'MLMono8': mlcm.MLPixelFormat.MLMono8,
            'MLMono10': mlcm.MLPixelFormat.MLMono10,
            'MLMono12': mlcm.MLPixelFormat.MLMono12,
            'MLMono16': mlcm.MLPixelFormat.MLMono16,
            'MLRGB24': mlcm.MLPixelFormat.MLRGB24,
            'MLBayer': mlcm.MLPixelFormat.MLBayer,
            'MLBayerGB8': mlcm.MLPixelFormat.MLBayerGB8,
            'MLBayerGB12': mlcm.MLPixelFormat.MLBayerGB12,
        }
        # 获取对应的枚举值
        pixel_format_enum = format_mapping.get(selected_format)
        return pixel_format_enum

    def get_current_filter(self, selected_format):
        format_mapping = {
            'ND0': mlcm.MLFilterEnum.ND0,
            'ND1': mlcm.MLFilterEnum.ND1,
            'ND2': mlcm.MLFilterEnum.ND2,
            'ND3': mlcm.MLFilterEnum.ND3,
            'ND4': mlcm.MLFilterEnum.ND4,
            'X': mlcm.MLFilterEnum.X,
            'Y': mlcm.MLFilterEnum.Y,
            'Z': mlcm.MLFilterEnum.Z,
            'Clear': mlcm.MLFilterEnum.Clear,
        }
        filter_enum = format_mapping.get(selected_format)
        return filter_enum

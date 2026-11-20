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
    QCheckBox,
    QPlainTextEdit
)
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QIcon, QColor, QTextCharFormat
from core.app_config import AppConfig
from core.config_helper import UiConfigHelper, MsgLevel
from PyQt5.QtCore import pyqtSignal, Qt, QThread
import mlcolorimeter as mlcm
from scripts.fourcolor_calibration import fourcolor_calibration_capture, fourcolor_calibration_calculate
from ui.exposureconfig_window import ExposureConfigWindow
from datetime import datetime
import os


class FourColorCalibrationCaptureThread(QThread):
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
            fourcolor_calibration_capture(
                status_callback=callback_wrapper, **self.parameters)  # type: ignore
            self.finished.emit()  # 发送完成信号
        except Exception as e:
            self.error.emit(str(e))  # 发送错误信号


class FourColorCalibrationCalculateThread(QThread):
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
            fourcolor_calibration_calculate(
                status_callback=callback_wrapper, **self.parameters)  # type: ignore
            self.finished.emit()  # 发送完成信号
        except Exception as e:
            self.error.emit(str(e))  # 发送错误信号


class FourColorCalabrationWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("fourcolor calibration")
        self.setGeometry(200, 200, 800, 500)
        self.colorimeter = AppConfig.get_colorimeter()
        self.ml_mono = self.colorimeter.ml_bino_manage.ml_get_module_by_id(1)
        self.setWindowFlags(Qt.Window | Qt.WindowMaximizeButtonHint |
                            Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)  # type: ignore
        self.setWindowIcon(QIcon(
            "D:/pythonObject/ML_AutoCalibration_GUI/ML_AutoCalibration_GUI/FingerPrintScanMTF.ico"))
        self.intValidator = QIntValidator()
        self.doubleValidator = QDoubleValidator()
        self.dialog_title = "选择文件夹"
        self.default_path = ""
        self.exposure_mode = ['Auto', 'Fixed']
        self.binning_selector = ['Logic', 'Sensor']
        self.binning_mode = ['AVERAGE', 'SUM']
        self.pixel_format = ['MLMono8', 'MLMono10', 'MLMono12',
                             'MLMono16', 'MLRGB24', 'MLBayer', 'MLBayerGB8', 'MLBayerGB12']
        self.exposure_map_obj = {}
        self.log_file_path = ""
        self.cfg_helper = UiConfigHelper("fourcolor_calibration_params.json")
        self._init_ui()
        self.is_running = False

        # =====================默认参数，加载历史参数并回填UI==============================
        self.default_ui_params = {
            "binn_selector": "Logic",
            "binn_mode": "AVERAGE",
            "binn": "0",
            "pixel_format": "MLMono12",
            "nd_text": "4",
            "xyz_text": "1",
            "sph_text": "-6 -5 -4 -3 -2 -1 0 1 2 3 4 5 6",
            "cyl_text": "-4 -3.75 -3.5 -3.25 -3 -2.75 -2.5 -2.25 -2 -1.75 -1.5 -1.25 -1 -0.75 -0.5 -0.25 0",
            "count_text": "1",
            "roi_x": "0",
            "roi_y": "0",
            "roi_w": "300",
            "roi_h": "300",
            "is_do_ffc": False,
            "save_path": "",
            "nmatrix_path": "",
            "exposure_map_serial": {}
        }
        self.cur_ui_params = self.cfg_helper.load_params(
            self.default_ui_params)
        self.fill_ui_by_params(self.cur_ui_params)

    def _init_ui(self):
        grid_layout = QGridLayout()

        group_box0 = QGroupBox("相机设置")
        from_layout0 = QFormLayout()

        self.label_binn_selector = QLabel(" binning_selector：")
        self.line_edit_binn_selector = QComboBox()
        self.line_edit_binn_selector.addItems(self.binning_selector)
        self.line_edit_binn_selector.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_binn_mode = QLabel(" binning_mode：")
        self.line_edit_binn_mode = QComboBox()
        self.line_edit_binn_mode.addItems(self.binning_mode)
        self.line_edit_binn_mode.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)

        horizontal_layout = QHBoxLayout()
        horizontal_layout.addWidget(self.label_binn_selector)
        horizontal_layout.addWidget(self.line_edit_binn_selector)
        horizontal_layout.addWidget(self.label_binn_mode)
        horizontal_layout.addWidget(self.line_edit_binn_mode)
        from_layout0.addRow(horizontal_layout)

        self.label_binn = QLabel(" binning：")
        self.line_edit_binn = QLineEdit()
        self.line_edit_binn.setValidator(self.intValidator)
        self.line_edit_binn.setText("0")
        self.line_edit_binn.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.line_edit_binn.setPlaceholderText(
            "0: 1X1, 1: 2X2, 2: 4X4, 3: 8X8, 4: 16X16")
        from_layout0.addRow(self.label_binn, self.line_edit_binn)

        self.label_pixel_format = QLabel(" pixel_format：")
        self.line_edit_pixel_format = QComboBox()
        self.line_edit_pixel_format.addItems(self.pixel_format)  # type: ignore
        self.line_edit_pixel_format.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.line_edit_pixel_format.setCurrentText("MLMono12")
        from_layout0.addRow(self.label_pixel_format,
                            self.line_edit_pixel_format)

        group_box0.setLayout(from_layout0)
        grid_layout.addWidget(group_box0, 0, 0)

        self.label_ndlist = QLabel()
        self.label_ndlist.setText(
            "nd列表, (4: ND0, 5: ND1, 6: ND2, 7:ND3, 8:ND4), 以空格隔开")
        grid_layout.addWidget(self.label_ndlist, 1, 0)

        self.line_edit_ndlist = QLineEdit()
        self.line_edit_ndlist.setText("4")
        self.line_edit_ndlist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_ndlist, 2, 0)

        self.label_xyzlist = QLabel()
        self.label_xyzlist.setText(
            "xyz列表, (1: X, 2: Y, 3: Z, 10: Clear, 12: YA), 以空格隔开")
        grid_layout.addWidget(self.label_xyzlist, 3, 0)

        self.line_edit_xyzlist = QLineEdit()
        self.line_edit_xyzlist.setText("1")
        self.line_edit_xyzlist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_xyzlist, 4, 0)

        self.btn_load_config = QPushButton("曝光时间配置")
        self.btn_load_config.clicked.connect(self.load_exposure_config)
        grid_layout.addWidget(self.btn_load_config, 4, 1)

        self.label_avg_count = QLabel(
            "avg_count:(count to calculate average image for one color filter)")
        grid_layout.addWidget(self.label_avg_count, 5, 0)
        self.line_edit_avg_count = QLineEdit()
        self.line_edit_avg_count.setValidator(self.intValidator)
        self.line_edit_avg_count.setText("1")
        self.line_edit_avg_count.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_avg_count, 6, 0)

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

        group_box1.setLayout(from_layout1)
        grid_layout.addWidget(group_box1, 7, 0)

        self.label_is_do_ffc = QLabel("is_do_ffc:(是否在计算前进行平场矫正)")
        grid_layout.addWidget(self.label_is_do_ffc, 8, 0)
        self.checkbox_is_do_ffc = QCheckBox()
        self.checkbox_is_do_ffc.setChecked(True)
        self.checkbox_is_do_ffc.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.checkbox_is_do_ffc, 9, 0)

        self.label_path = QLabel()
        self.label_path.setText("保存路径:")
        grid_layout.addWidget(self.label_path, 10, 0)

        self.line_edit_path = QLineEdit()
        self.line_edit_path.setReadOnly(True)  # 设置为只读
        self.line_edit_path.setPlaceholderText("未选择文件夹")
        self.line_edit_path.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_path, 11, 0)

        self.btn_browse = QPushButton("浏览...")
        self.btn_browse.clicked.connect(self._open_folder_dialog)
        grid_layout.addWidget(self.btn_browse, 11, 1)

        self.label_NMatrix_path = QLabel()
        self.label_NMatrix_path.setText(
            "NMatrix路径:(NMatrix_xyL.json contains the specbos data of your light source)")
        grid_layout.addWidget(self.label_NMatrix_path, 12, 0)

        self.line_edit_NMatrix_path = QLineEdit()
        self.line_edit_NMatrix_path.setReadOnly(True)  # 设置为只读
        self.line_edit_NMatrix_path.setPlaceholderText("未选择文件夹")
        self.line_edit_NMatrix_path.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_NMatrix_path, 13, 0)

        self.btn_NMatrix_path = QPushButton("浏览...")
        self.btn_NMatrix_path.clicked.connect(self._open_file_dialog)
        grid_layout.addWidget(self.btn_NMatrix_path, 13, 1)

        self.btn_start_calibration = QPushButton("四色标定")
        self.btn_start_calibration.clicked.connect(self._start_calibration)
        grid_layout.addWidget(self.btn_start_calibration, 14, 0)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        grid_layout.addWidget(self.log_box, 15, 0)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum,
                             QSizePolicy.Expanding)
        grid_layout.addItem(spacer)

        self.setLayout(grid_layout)

    def fill_ui_by_params(self, params: dict):
        binn_sel_idx = self.line_edit_binn_selector.findText(
            params["binn_selector"])
        if binn_sel_idx >= 0:
            self.line_edit_binn_selector.setCurrentIndex(binn_sel_idx)
        binn_mode_idx = self.line_edit_binn_mode.findText(params["binn_mode"])
        if binn_mode_idx >= 0:
            self.line_edit_binn_mode.setCurrentIndex(binn_mode_idx)

        self.line_edit_binn.setText(params["binn"])
        pf_idx = self.line_edit_pixel_format.findText(params["pixel_format"])
        if pf_idx >= 0:
            self.line_edit_pixel_format.setCurrentIndex(pf_idx)

        self.line_edit_ndlist.setText(params["nd_text"])
        self.line_edit_xyzlist.setText(params["xyz_text"])
        self.line_edit_avg_count.setText(params["count_text"])

        self.line_edit_x_input.setText(params["roi_x"])
        self.line_edit_y_input.setText(params["roi_y"])
        self.line_edit_width_input.setText(params["roi_w"])
        self.line_edit_height_input.setText(params["roi_h"])

        self.checkbox_is_do_ffc.setChecked(int(params["is_do_ffc"]))

        self.line_edit_path.setText(params["save_path"])
        self.line_edit_NMatrix_path.setText(params["nmatrix_path"])
        serial_map = params.get("exposure_map_serial", {})
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

    def read_ui_params(self) -> dict:
        exp_serial = {}
        for nd_enum, xyz_dict in self.exposure_map_obj.items():
            exp_serial[nd_enum.name] = {}
            for xyz_enum, s in xyz_dict.items():
                exp_serial[nd_enum.name][xyz_enum.name] = {
                    "exposure_mode": s.exposure_mode.name,
                    "exposure_time": s.exposure_time
                }
        param_dict = {
            "binn_selector": self.line_edit_binn_selector.currentText(),
            "binn_mode": self.line_edit_binn_mode.currentText(),
            "binn": self.line_edit_binn.text().strip(),
            "pixel_format": self.line_edit_pixel_format.currentText(),
            "nd_text": self.line_edit_ndlist.text().strip(),
            "xyz_text": self.line_edit_xyzlist.text().strip(),
            "count_text": self.line_edit_avg_count.text().strip(),
            "roi_x": self.line_edit_x_input.text().strip(),
            "roi_y": self.line_edit_y_input.text().strip(),
            "roi_w": self.line_edit_width_input.text().strip(),
            "roi_h": self.line_edit_height_input.text().strip(),
            "is_do_ffc": self.checkbox_is_do_ffc.isChecked(),
            "save_path": self.line_edit_path.text().strip(),
            "nmatrix_path": self.line_edit_NMatrix_path.text().strip(),
            "exposure_map_serial": exp_serial
        }
        return param_dict

    def _start_calibration(self):
        try:
            self.pixel_format = self.get_current_pixel_format()
            self.binn_selector = self.get_current_binning_selector()
            self.binn_mode = self.get_current_binning_mode()
            self.binn = mlcm.Binning(int(self.line_edit_binn.text().strip()))
            nd_enum = [int(nd)
                       for nd in self.line_edit_ndlist.text().strip().split()]
            self.nd_list = [mlcm.MLFilterEnum(nd) for nd in nd_enum]
            xyz_enum = [int(xyz)
                        for xyz in self.line_edit_xyzlist.text().strip().split()]
            self.xyz_list = [mlcm.MLFilterEnum(xyz) for xyz in xyz_enum]
            self.avg_count = int(self.line_edit_avg_count.text().strip())
            x = int(self.line_edit_x_input.text().strip())
            y = int(self.line_edit_y_input.text().strip())
            width = int(self.line_edit_width_input.text().strip())
            height = int(self.line_edit_height_input.text().strip())
            self.roi = mlcm.pyCVRect(x, y, width, height)
            self.save_path = self.line_edit_path.text().strip()
            if not self.save_path:
                raise RuntimeError("请先选择保存文件夹！")
            self.nmatrix_path = self.line_edit_NMatrix_path.text().strip()
            if not self.nmatrix_path:
                raise RuntimeError("请选择NMatrix_xyL.json文件！")
            self.is_do_ffc = self.checkbox_is_do_ffc.isChecked()

            if not self.exposure_map_obj:
                QMessageBox.critical(self, "MLColorimeter", "请设置曝光",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                return

            # 新建日志文件
            self.log_file_path = os.path.join(
                self.cfg_helper.log_path, f"fourcolor_calibration_log.txt")

            self.light_source_list = ["R", "G", "B", "W"]
            self.btn_start_calibration.setEnabled(False)
            self.is_running = True
            if self.ml_mono.mono is None:
                raise RuntimeError(
                    "mono is None, Please connect mlcolorimeter")
            self.auto_cali = mlcm.pyMLAutoCalibration(self.ml_mono)

            # 从第一个ND开始捕获光源
            self.current_nd_index = 0
            self.start_capture_for_light_source(self.current_nd_index)
        except RuntimeError as e:
            QMessageBox.critical(self, "MLColorimeter", f"exception: {e}",  # type: ignore
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            self.btn_start_calibration.setEnabled(True)
            self.is_running = False
        except Exception as e:
            QMessageBox.critical(self, "MLColorimeter", f"exception: {e}",  # type: ignore
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            self.btn_start_calibration.setEnabled(True)
            self.is_running = False

    def start_capture_for_light_source(self, nd_index):
        if nd_index >= len(self.nd_list):
            self.btn_start_calibration.setEnabled(True)
            self.is_running = False
            return
        nd = self.nd_list[nd_index]
        light_source_index = 0

        # 开始捕获当前ND的所有光源
        self.capture_next_light_source(nd, light_source_index)

    def capture_next_light_source(self, nd, light_source_index):
        if light_source_index >= len(self.light_source_list):
            # 当前ND的所有光源已捕获，开始计算
            self.start_calculation(nd)
            return
        light_source = self.light_source_list[light_source_index]
        temp = QMessageBox.information(
            self, "提示", f"请先切换到{light_source}光", QMessageBox.Ok)
        if temp == QMessageBox.Ok:
            if nd not in self.exposure_map_obj:
                raise RuntimeError(
                    f"ND {mlcm.MLFilterEnum_to_str(nd)} 没有配置曝光参数，请先打开曝光配置窗口配置")
            exposure_map = self.exposure_map_obj[nd]
            capture_parameters = {
                'auto_cali': self.auto_cali,
                'ml_mono': self.ml_mono,
                'binn_selector': self.binn_selector,
                'binn_mode': self.binn_mode,
                'binn': self.binn,
                'pixel_format': self.pixel_format,
                'save_path': self.save_path,
                'light_source': light_source,
                'nd': nd,
                'avg_count': self.avg_count,
                'exposure_map': exposure_map,
                'roi': self.roi,
                'is_do_ffc': self.is_do_ffc
            }
            self.capture_thread = FourColorCalibrationCaptureThread(
                parameters=capture_parameters)

            # 连接信号
            self.capture_thread.finished.connect(
                lambda: self.on_capture_finished(nd, light_source_index))
            self.capture_thread.error.connect(self.on_calibration_error)
            self.capture_thread.status_update.connect(self.flush_log)

            # 启动线程
            self.capture_thread.start()

    def on_capture_finished(self, nd, light_source_index):

        # 捕获下一个光源
        self.capture_next_light_source(nd, light_source_index+1)

    def start_calculation(self, nd):
        calculate_parameters = {
            'auto_cali': self.auto_cali,
            'save_path': self.save_path,
            'nd': nd,
            'NMatrix_path': self.nmatrix_path
        }
        self.calculateThread = FourColorCalibrationCalculateThread(
            calculate_parameters)
        self.calculateThread.finished.connect(self.on_calculation_finished)
        self.calculateThread.error.connect(self.on_calibration_error)
        self.calculateThread.status_update.connect(self.flush_log)
        self.calculateThread.start()

    def on_calculation_finished(self):
        self.current_nd_index += 1
        self.start_capture_for_light_dource(
            self.current_nd_index)  # 开始下一个ND的捕获

    def on_calibration_error(self, error_message):
        QMessageBox.critical(self, "MLColorimeter",
                             "发生错误: " + error_message, QMessageBox.Ok)
        self.btn_start_calibration.setEnabled(True)
        self.is_running = False  # 标识完成

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

    def _open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择NMatrix JSON文件",
            self.default_path if self.default_path else "",
            "JSON Files (*.json);;All Files (*)"  # 文件过滤器，仅显示json文件
        )
        if file_path:
            self.line_edit_NMatrix_path.setText(file_path)
        else:
            QMessageBox.critical(self, "MLColorimeter", "选择路径错误",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

    def load_exposure_config(self):
        try:
            nd_list = self.line_edit_ndlist.text().strip().split()
            xyz_list = self.line_edit_xyzlist.text().strip().split()
            self.exposure_config_window = ExposureConfigWindow(
                nd_list, xyz_list, self.exposure_map_obj)
            # 连接信号
            self.exposure_config_window.config_saved.connect(
                self.update_config)
            self.exposure_config_window.exec_()
        except Exception as e:
            QMessageBox.critical(self, "MLColorimeter", f"exception: {e}",  # type: ignore
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

    def update_config(self, exposure_map):
        # print("Received exposure map:", exposure_map)
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

    def get_current_binning_selector(self):
        # 获取当前选择的项
        selected_selector = self.line_edit_binn_selector.currentText()
        if selected_selector == 'Logic':
            return mlcm.BinningSelector.Logic
        else:
            return mlcm.BinningSelector.Sensor

    def get_current_binning_mode(self):
        # 获取当前选择的项
        selected_mode = self.line_edit_binn_mode.currentText()
        if selected_mode == 'AVERAGE':
            return mlcm.BinningMode.AVERAGE
        else:
            return mlcm.BinningMode.SUM

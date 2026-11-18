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
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QIcon,QTextCharFormat,QColor
from core.app_config import AppConfig
from core.config_helper import UiConfigHelper,MsgLevel
from PyQt5.QtCore import pyqtSignal, Qt, QThread
import mlcolorimeter as mlcm
from scripts.capture_dark_heatmap import capture_dark_heatmap
import os
from datetime import datetime

class DarkHeatMapThread(QThread):
    finished = pyqtSignal()  # 线程完成信号
    error = pyqtSignal(str)  # 错误信号
    status_update = pyqtSignal(str)  # 状态更新信号

    def __init__(self, parameters):
        super().__init__()
        self.parameters = parameters

    def run(self):
        try:
            # 包装回调：接受level，msg，拼接成字符串再发给信号
            def callback_wrapper(level: MsgLevel,msg:str):
                self.status_update.emit(msg)
            capture_dark_heatmap(
                status_callback=callback_wrapper, **self.parameters) # type: ignore
            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))


class DarkHeatMapWindow(QDialog):
    path_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("capture dark heatmap")
        self.setGeometry(200, 200, 800, 500)
        self.colorimeter = AppConfig.get_colorimeter()
        self.setWindowFlags(Qt.Window | Qt.WindowMaximizeButtonHint |
                            Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint) # type: ignore
        self.setWindowIcon(QIcon(
            "D:/pythonObject/ML_AutoCalibration_GUI/ML_AutoCalibration_GUI/FingerPrintScanMTF.ico"))
        self.intValidator = QIntValidator()
        self.doubleValidator = QDoubleValidator()
        self.dialog_title = "选择文件夹"
        self.default_path = ""
        self.save_path = ""
        self.file_name = "dark_heatmap.xlsx"
        self.exposure_mode = ['Auto', 'Fixed']
        self.binning_selector = ['Logic', 'Sensor']
        self.binning_mode = ['AVERAGE', 'SUM']
        self.pixel_format = ['MLMono8', 'MLMono10', 'MLMono12',
                             'MLMono16', 'MLRGB24', 'MLBayer', 'MLBayerGB8', 'MLBayerGB12']
        self.log_file_path=""
        self.cfg_helper=UiConfigHelper("dark_heatmap_params.json")
        self._init_ui()
        self.is_running = False

        #=====================默认参数，加载历史参数并回填UI==============================
        self.default_ui_params={
            "binn_selector":"Logic",
            "binn_mode":"AVERAGE",
            "binn":"0",
            "pixel_format":"MLMono12",
            "avg_count":"1",
            "et_list":"1 10",
            "binn_list":"0",
            "nd_list":"4 5",
            "xyz_list":"1 2",
            "save_path":"",
            "file_name":"dark_heatmap"
        }
        self.cur_ui_params=self.cfg_helper.load_params(self.default_ui_params)
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
        self.line_edit_pixel_format.addItems(self.pixel_format) # type: ignore
        self.line_edit_pixel_format.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.line_edit_pixel_format.setCurrentText("MLMono12")

        horizontal_layout1 = QHBoxLayout()
        horizontal_layout1.addWidget(self.label_pixel_format)
        horizontal_layout1.addWidget(self.line_edit_pixel_format)
        from_layout0.addRow(horizontal_layout1)

        group_box0.setLayout(from_layout0)
        grid_layout.addWidget(group_box0, 0, 0)

        self.label_times = QLabel("多帧平均次数: ")
        grid_layout.addWidget(self.label_times, 1, 0)

        self.line_edit_times = QLineEdit()
        self.line_edit_times.setValidator(self.intValidator)
        self.line_edit_times.setText("1")
        self.line_edit_times.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_times, 2, 0)

        self.label_etlist = QLabel("曝光时间列表(ms), 例如: 1 10 20, 以空格隔开")
        grid_layout.addWidget(self.label_etlist, 3, 0)

        self.line_edit_etlist = QLineEdit()
        self.line_edit_etlist.setText("1 10")
        self.line_edit_etlist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_etlist, 4, 0)

        self.label_binnlist = QLabel(
            "binning列表, (0: 1X1, 1: 2X2, 2: 4X4, 3: 8X8, 4: 16X16), 以空格隔开")
        grid_layout.addWidget(self.label_binnlist, 5, 0)

        self.line_edit_binnlist = QLineEdit()
        self.line_edit_binnlist.setText("0")
        self.line_edit_binnlist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_binnlist, 6, 0)

        self.label_ndlist = QLabel(
            "nd列表, (4: ND0, 5: ND1, 6: ND2, 7:ND3, 8:ND4), 以空格隔开")
        grid_layout.addWidget(self.label_ndlist, 7, 0)

        self.line_edit_ndlist = QLineEdit()
        self.line_edit_ndlist.setText("4")
        self.line_edit_ndlist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_ndlist, 8, 0)

        self.label_xyzlist = QLabel(
            "xyz列表, (1: X, 2: Y, 3: Z, 10: Clear, 12: YA), 以空格隔开")
        grid_layout.addWidget(self.label_xyzlist, 9, 0)

        self.line_edit_xyzlist = QLineEdit()
        self.line_edit_xyzlist.setText("1")
        self.line_edit_xyzlist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_xyzlist, 10, 0)

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

        self.label_filename = QLabel()
        self.label_filename.setText("文件名:")
        grid_layout.addWidget(self.label_filename, 13, 0)

        self.line_edit_filename = QLineEdit()
        self.line_edit_filename.setReadOnly(True)  # 设置为只读
        self.line_edit_filename.setPlaceholderText("dark_heatmap")
        self.line_edit_filename.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_filename, 14, 0)

        self.btn_capture = QPushButton("开始拍图")
        self.btn_capture.clicked.connect(self.start_capture)
        grid_layout.addWidget(self.btn_capture, 15, 0)

        self.log_box=QPlainTextEdit()
        self.log_box.setReadOnly(True)
        grid_layout.addWidget(self.log_box,16,0)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum,
                             QSizePolicy.Expanding)
        grid_layout.addItem(spacer)

        self.setLayout(grid_layout)

    
    def fill_ui_by_params(self, params: dict):
        binn_sel_idx = self.line_edit_binn_selector.findText(params["binn_selector"])
        if binn_sel_idx >= 0:
            self.line_edit_binn_selector.setCurrentIndex(binn_sel_idx)
        binn_mode_idx = self.line_edit_binn_mode.findText(params["binn_mode"])
        if binn_mode_idx >= 0:
            self.line_edit_binn_mode.setCurrentIndex(binn_mode_idx)

        self.line_edit_binn.setText(params["binn"])
        pf_idx = self.line_edit_pixel_format.findText(params["pixel_format"])
        if pf_idx >= 0:
            self.line_edit_pixel_format.setCurrentIndex(pf_idx)

        self.line_edit_times.setText(params["avg_count"])
        self.line_edit_etlist.setText(params["et_list"])
        self.line_edit_binnlist.setText(params["binn_list"])

        self.line_edit_ndlist.setText(params["nd_list"])
        self.line_edit_xyzlist.setText(params["xyz_list"])
        self.line_edit_path.setText(params["save_path"])
        self.line_edit_filename.setText(params["file_name"])
    
    def read_ui_params(self) -> dict:
        param_dict = {
            "binn_selector": self.line_edit_binn_selector.currentText(),
            "binn_mode": self.line_edit_binn_mode.currentText(),
            "binn": self.line_edit_binn.text().strip(),
            "pixel_format": self.line_edit_pixel_format.currentText(),
            "avg_count": self.line_edit_times.text().strip(),
            "et_list": self.line_edit_etlist.text().strip(),
            "binn_list": self.line_edit_binnlist.text().strip(),
            "nd_list": self.line_edit_ndlist.text().strip(),
            "xyz_list": self.line_edit_xyzlist.text().strip(),
            "save_path": self.line_edit_path.text().strip(),
            "file_name": self.line_edit_filename.text().strip()
        }
        return param_dict

    def flush_log(self,msg):
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
        full_text=f"{prefix}{datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")[:-3]} {msg}\n"
        cursor.insertText(full_text, fmt)
        self.log_box.setTextCursor(cursor)
        # 自动滚动到底部
        sb=self.log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

        # 写入本地txt日志
        if self.log_file_path:
            try:
                with open(self.log_file_path, "a", encoding="utf-8") as f:
                    f.write(full_text)
            except Exception as log_err:
                # 日志写入失败不打断主流程
                print(f"write log file failed: {log_err}")
        
    def _open_folder_dialog(self):
        # 打开文件夹选择对话框
        folder_path = QFileDialog.getExistingDirectory(
            self,
            self.dialog_title,
            self.default_path if self.default_path else "",  # 初始路径
            options=QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks, # type: ignore
        )

        if folder_path:
            self.line_edit_path.setText(folder_path)
        else:
            QMessageBox.critical(self, "MLColorimeter", "选择路径错误",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

    def start_capture(self):
        try:
            binn_text = self.line_edit_binn.text().strip()
            if not binn_text:
                QMessageBox.warning(self, "输入错误", "请输入必填项：Binning 值不能为空。")
                return
            else:
                self.binn = mlcm.Binning(int(binn_text))
            self.save_path = self.line_edit_path.text().strip()
            if not self.save_path:
                QMessageBox.warning(self, "提示", "请选择保存路径")
                return
            self.pixel_format = self.get_current_pixel_format()
            self.binn_selector = self.get_current_binning_selector()
            self.binn_mode = self.get_current_binning_mode()
            self.capture_times = int(self.line_edit_times.text())
            self.etlist = [float(et)
                           for et in self.line_edit_etlist.text().split()]
            self.binnlist = [
                mlcm.Binning(int(binn)) for binn in self.line_edit_binnlist.text().strip().split()]
            # self.binnlist = [mlcm.Binning(B) for B in binn_enum]
            self.ndlist = [mlcm.MLFilterEnum(int(nd))
                           for nd in self.line_edit_ndlist.text().split()]
            self.xyzlist = [mlcm.MLFilterEnum(int(xyz))
                            for xyz in self.line_edit_xyzlist.text().split()]
            self.file_name = self.line_edit_filename.text() + ".xlsx"

            # ========== 生成本次运行的时间戳，用于日志文件 ==========
            run_ts = datetime.now().strftime('%Y-%m-%d')
            self.log_file_path = os.path.join(self.save_path, f"{run_ts}_dark_heatmap_log.txt")

            self.btn_capture.setEnabled(False)
            self.is_running = True
            parameters = {
                'colorimeter': self.colorimeter,
                'nd_list': self.ndlist,
                'xyz_list': self.xyzlist,
                'binning_list': self.binnlist,
                'et_list': self.etlist,
                'save_path': self.save_path,
                'capture_times': self.capture_times,
                'file_name': self.file_name,
                'binn_selector': self.binn_selector,
                'binn_mode': self.binn_mode,
                'binn': self.binn,
                'pixel_format': self.pixel_format,
            }
            self.darkheatmapThread = DarkHeatMapThread(parameters)
            self.darkheatmapThread.finished.connect(
                self.on_darkheatmap_finished)
            self.darkheatmapThread.error.connect(self.on_darkheatmap_error)
            self.darkheatmapThread.status_update.connect(self.flush_log)
            self.darkheatmapThread.start()
        except Exception as e:
            QMessageBox.critical(self, "MLColorimeter", "exception" + e, # type: ignore
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            self.btn_capture.setEnabled(True)
            self.is_running = False 

    def on_darkheatmap_finished(self):
        QMessageBox.information(self, "MLColorimeter", "完成!", QMessageBox.Ok)
        self.btn_capture.setEnabled(True)
        self.is_running = False  # 标识定标完成

    def on_darkheatmap_error(self, error_message):
        QMessageBox.critical(self, "MLColorimeter",
                             "发生错误: " + error_message, QMessageBox.Ok)
        self.btn_capture.setEnabled(True)
        self.is_running = False  # 标识定标完成

    def closeEvent(self, event):
        if self.is_running:
            # 如果正在进行定标，拦截关闭事件
            event.ignore()
            QMessageBox.warning(self, "警告", "定标进行中，请勿关闭窗口", QMessageBox.Ok)
        else:
            #==============关闭窗口保存当前UI参数====================
            p=self.read_ui_params()
            self.cfg_helper.save_params(p)
            event.accept()

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

    def get_current_exposure_mode(self):
        # 获取当前选择的项
        selected_mode = self.line_edit_exposure_mode.currentText()
        if selected_mode == 'Auto':
            return mlcm.ExposureMode.Auto
        else:
            return mlcm.ExposureMode.Fixed

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

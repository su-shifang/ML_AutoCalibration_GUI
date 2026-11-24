from PyQt5.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QSizePolicy,
    QMessageBox,
    QGroupBox,
    QGridLayout,
    QSpacerItem,
    QRadioButton,
    QButtonGroup,
    QCheckBox,
    QDialog,
    QComboBox,
    QFormLayout,
    QScrollArea,
    QFrame,
    QPlainTextEdit
)
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QIcon, QColor, QTextCharFormat
from core.app_config import AppConfig
from core.config_helper import UiConfigHelper, MsgLevel
from PyQt5.QtCore import pyqtSignal, Qt, QThread
import mlcolorimeter as mlcm
from scripts.mono_calibration import mono_calibration, mono_calibration_do_ffc
import configparser
from datetime import datetime
import os


class CalibrationThread(QThread):
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
            mono_calibration(
                status_callback=callback_wrapper, **self.parameters)  # type: ignore
            self.finished.emit()  # 发送完成信号
        except Exception as e:
            self.error.emit(str(e))  # 发送错误信号


class CalibrationDoFFCThread(QThread):
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
            mono_calibration_do_ffc(
                status_callback=callback_wrapper, **self.parameters)  # type: ignore
            self.finished.emit()  # 发送完成信号
        except Exception as e:
            self.error.emit(str(e))  # 发送错误信号


class MonoCalibrationWindow(QDialog):
    # path_changed = pyqtSignal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("mono calibration")
        self.setGeometry(200, 200, 800, 500)
        self.setWindowFlags(Qt.Window | Qt.WindowMaximizeButtonHint |
                            Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)  # type: ignore
        self.setWindowIcon(QIcon(
            "D:/pythonObject/ML_AutoCalibration_GUI/ML_AutoCalibration_GUI/FingerPrintScanMTF.ico"))
        self.colorimeter = AppConfig.get_colorimeter()
        self.doubleValidator = QDoubleValidator()
        self.dialog_title = "选择文件夹"
        self.default_path = ""
        self.select_path = path
        self.file_name = "mono_calibration.xlsx"
        self.binning_selector = ['Logic', 'Sensor']
        self.binning_mode = ['AVERAGE', 'SUM']
        self.pixel_format = ['MLMono8', 'MLMono10', 'MLMono12',
                             'MLMono16', 'MLRGB24', 'MLBayer', 'MLBayerGB8', 'MLBayerGB12']
        self.temp = False  # ini读取是否成功的标志
        self.lum_folder_rule = ""
        self.rad_folder_rule = ""
        self.log_file_path = ""
        self.cfg_helper = UiConfigHelper("mono_calibration_params.json")
        self._init_ui()

        # 标识当前是否正在定标
        self.is_calibrating = False

        # =====================默认参数，加载历史参数并回填UI==============================
        self.default_ui_params = {
            "binn_selector": "Logic",
            "binn_mode": "AVERAGE",
            "binn": "0",
            "pixel_format": "MLMono12",
            "aperture": "3mm",
            "no_nd": False,
            "nd_text": "4",
            "no_xyz": False,
            "xyz_text": "1",
            "luminance": "10000 2300",
            "radiance": "1000",
            "et_offset": "0",
            "gray_offset": "0",
            "gray_text": "0.5 0.8",
            "do_ffc": False,
            "do_rx": False,
            "sph_text": "-6 -5 -4 -3 -2 -1 0 1 2 3 4 5 6",
            "cyl_text": "-4 -3.75 -3.5 -3.25 -3 -2.75 -2.5 -2.25 -2 -1.75 -1.5 -1.25 -1 -0.75 -0.5 -0.25 0",
            "axis_text": "0 15 30 45 60 75 90 105 120 135 150 165",
            "center_xy": "6688 4764",
            "roi_wh": "200 200",
            "light_source": "W",
            "save_path": "",
            "do_ae": False,
            "auto_et": "10",
            "max_time": "5000",
            "rate": "1000000",
            "use_roi": False,
            "pixel_count": "200"

        }
        self.cur_ui_params = self.cfg_helper.load_params(
            self.default_ui_params)
        self.fill_ui_by_params(self.cur_ui_params)

    def _init_ui(self):
        # 创建一个 QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)  # 使滚动区域大小可变

        # 创建一个 QWidget 来放置所有控件
        scroll_area_content = QWidget()
        grid_layout = QGridLayout(scroll_area_content)

        group_box0 = QGroupBox("相机设置")
        from_layout0 = QFormLayout()

        self.label_binn_selector = QLabel(" binning_selector：")
        self.line_edit_binn_selector = QComboBox()
        self.line_edit_binn_selector.addItems(self.binning_selector)
        self.line_edit_binn_selector.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        from_layout0.addRow(self.label_binn_selector,
                            self.line_edit_binn_selector)

        self.label_binn_mode = QLabel(" binning_mode：")
        self.line_edit_binn_mode = QComboBox()
        self.line_edit_binn_mode.addItems(self.binning_mode)
        self.line_edit_binn_mode.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        from_layout0.addRow(self.label_binn_mode, self.line_edit_binn_mode)

        self.label_binn = QLabel(" binning：")
        self.line_edit_binn = QLineEdit()
        self.line_edit_binn.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        int_validator = QIntValidator(0, 4, self)
        self.line_edit_binn.setValidator(int_validator)
        self.line_edit_binn.setText("0")
        self.line_edit_binn.setPlaceholderText(
            "0: 1X1, 1: 2X2, 2: 4X4, 3: 8X8, 4: 16X16")
        self.line_edit_binn.textChanged.connect(self.validate_input)

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

        group_box1 = QGroupBox("AE参数设置")
        from_layout1 = QFormLayout()

        # 添加启用AE的复选框
        self.checkbox_enable_ae = QCheckBox("启用")
        self.checkbox_enable_ae.setChecked(False)
        self.checkbox_enable_ae.stateChanged.connect(
            self.on_ae_enabled_changed)
        from_layout1.addRow(self.checkbox_enable_ae)

        # 添加分隔线
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        from_layout1.addRow(self.separator)

        self.label_exposure_time = QLabel("自动曝光时间(ms): ")
        self.line_edit_exposure_time = QLineEdit()
        self.line_edit_exposure_time.setText("10")
        from_layout1.addRow(self.label_exposure_time,
                            self.line_edit_exposure_time)

        self.label_max_time = QLabel("max_time(ms): ")
        self.line_edit_max_time = QLineEdit()
        self.line_edit_max_time.setText("5000")
        from_layout1.addRow(self.label_max_time, self.line_edit_max_time)

        self.label_rate = QLabel("rate: ")
        self.line_edit_rate = QLineEdit()
        self.line_edit_rate.setText("1000000")
        self.checkbox_use_roi = QCheckBox("use roi")

        from_layout1.addRow(self.label_rate, self.line_edit_rate)
        from_layout1.addRow(self.checkbox_use_roi)

        self.label_pixel_count = QLabel("pixel_count: ")
        self.line_edit_pixel_count = QLineEdit()
        self.line_edit_pixel_count.setText("5000")
        from_layout1.addRow(self.label_pixel_count, self.line_edit_pixel_count)

        group_box1.setLayout(from_layout1)

        grid_layout.addWidget(group_box0, 0, 0)
        grid_layout.addWidget(group_box1, 0, 1)
        # 设置两列的占比
        grid_layout.setColumnStretch(0, 3)
        grid_layout.setColumnStretch(1, 1)

        self.label_aperture = QLabel()
        self.label_aperture.setText("光阑(mm): 例如：3mm")
        grid_layout.addWidget(self.label_aperture, 1, 0)
        self.line_edit_aperture = QLineEdit()
        self.line_edit_aperture.setText("3mm")
        self.line_edit_aperture.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_aperture, 2, 0)

        self.label_ndlist = QLabel()
        self.label_ndlist.setText(
            "nd列表, (4: ND0, 5: ND1, 6: ND2, 7:ND3, 8:ND4), 以空格隔开")
        grid_layout.addWidget(self.label_ndlist, 3, 0)
        self.checkbox_exist_nd = QCheckBox("无nd滤光片")
        self.checkbox_exist_nd.stateChanged.connect(
            self.on_nd_checkbox_changed)
        grid_layout.addWidget(self.checkbox_exist_nd, 3, 1)

        self.line_edit_ndlist = QLineEdit()
        self.line_edit_ndlist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_ndlist, 4, 0)

        self.label_xyzlist = QLabel()
        self.label_xyzlist.setText(
            "xyz列表, (1: X, 2: Y, 3: Z, 10: Clear, 12：YA), 以空格隔开")
        grid_layout.addWidget(self.label_xyzlist, 5, 0)
        self.checkbox_exist_xyz = QCheckBox("无xyz滤光片")
        self.checkbox_exist_xyz.stateChanged.connect(
            self.on_xyz_checkbox_changed)
        grid_layout.addWidget(self.checkbox_exist_xyz, 5, 1)

        self.line_edit_xyzlist = QLineEdit()
        self.line_edit_xyzlist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_xyzlist, 6, 0)

        self.label_xyzlist_lum = QLabel()
        self.label_xyzlist_lum.setText(
            "输入对应xyz列表下的亮度, 以空格隔开(无xyz滤光片时只输入一个亮度值即可)")
        grid_layout.addWidget(self.label_xyzlist_lum, 7, 0)
        self.line_edit_xyzlist_lum = QLineEdit()
        self.line_edit_xyzlist_lum.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_xyzlist_lum, 8, 0)

        self.label_radiance_lum = QLabel()
        self.label_radiance_lum.setText("Radiance：")
        grid_layout.addWidget(self.label_radiance_lum, 9, 0)
        self.line_edit_radiance_lum = QLineEdit()
        self.line_edit_radiance_lum.setText("1000")
        self.line_edit_radiance_lum.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_radiance_lum, 10, 0)

        self.label_exposure_offset = QLabel()
        self.label_exposure_offset.setText("exposure offset：")
        grid_layout.addWidget(self.label_exposure_offset, 11, 0)
        self.line_edit_exposure_offset = QLineEdit()
        self.line_edit_exposure_offset.setValidator(self.doubleValidator)
        self.line_edit_exposure_offset.setText("0.0")
        self.line_edit_exposure_offset.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_exposure_offset, 12, 0)

        self.label_gray_offset = QLabel()
        self.label_gray_offset.setText("gray offset：")
        grid_layout.addWidget(self.label_gray_offset, 13, 0)
        self.line_edit_gray_offset = QLineEdit()
        self.line_edit_gray_offset.setValidator(self.doubleValidator)

        self.line_edit_gray_offset.setText("0.0")
        self.line_edit_gray_offset.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_gray_offset, 14, 0)

        self.label_gray_range = QLabel()
        self.label_gray_range.setText("灰度值(例如: 0.5,0.8)，多个灰度值以空格隔开")
        grid_layout.addWidget(self.label_gray_range, 15, 0)
        self.line_edit_gray_range = QLineEdit()
        self.line_edit_gray_range.setText("0.8")
        self.line_edit_gray_range.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_gray_range, 16, 0)

        self.label_image_size = QLabel()
        self.label_image_size.setText(
            "图像中心点坐标x y（打开相机软件查看）：例如像素为13376 9528，则中心点为6688 4764以空格隔开")
        grid_layout.addWidget(self.label_image_size, 17, 0)
        self.line_edit_image_size = QLineEdit()
        self.line_edit_image_size.setText("6688 4764")
        self.line_edit_image_size.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_image_size, 18, 0)

        self.label_roi_size = QLabel()
        self.label_roi_size.setText("ROI宽高：例如200 200，以空格隔开")
        grid_layout.addWidget(self.label_roi_size, 19, 0)
        self.checkbox_do_ffc = QCheckBox("FFC校正")
        self.checkbox_do_ffc.stateChanged.connect(self.do_ffc_checkbox_changed)
        grid_layout.addWidget(self.checkbox_do_ffc, 19, 1)

        self.line_edit_roi_size = QLineEdit()
        self.line_edit_roi_size.setText("200 200")
        self.line_edit_roi_size.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_roi_size, 20, 0)
        self.checkbox_is_rx = QCheckBox("RX")
        self.checkbox_is_rx.stateChanged.connect(self.do_rx_checkbox_changed)
        grid_layout.addWidget(self.checkbox_is_rx, 20, 1)

        h_layout = QHBoxLayout()
        self.cb_R = QRadioButton()
        self.cb_R.setText("R")
        self.cb_R.setChecked(False)

        h_layout = QHBoxLayout()
        self.cb_G = QRadioButton()
        self.cb_G.setText("G")
        self.cb_G.setChecked(False)

        h_layout = QHBoxLayout()
        self.cb_B = QRadioButton()
        self.cb_B.setText("B")
        self.cb_B.setChecked(False)

        h_layout = QHBoxLayout()
        self.cb_W = QRadioButton()
        self.cb_W.setText("W")
        self.cb_W.setChecked(True)

        self.rgbw_btngroup = QButtonGroup(self)
        self.rgbw_btngroup.addButton(self.cb_R, 1)
        self.rgbw_btngroup.addButton(self.cb_G, 2)
        self.rgbw_btngroup.addButton(self.cb_B, 3)
        self.rgbw_btngroup.addButton(self.cb_W, 4)

        h_layout.addWidget(self.cb_R)
        h_layout.addWidget(self.cb_G)
        h_layout.addWidget(self.cb_B)
        h_layout.addWidget(self.cb_W)
        grid_layout.addLayout(h_layout, 21, 0)

        self.label_sphlist = QLabel()
        self.label_sphlist.setText(
            "平场图像采集 sph列表, (例如: -6 -5 -4 -3 -2 -1 0 1 2 3 4 5 6), 以空格隔开")
        grid_layout.addWidget(self.label_sphlist, 22, 0)

        self.line_edit_sphlist = QLineEdit()
        self.line_edit_sphlist.setText("-6 -5 -4 -3 -2 -1 0 1 2 3 4 5 6")
        self.line_edit_sphlist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_sphlist, 23, 0)

        self.label_cyllist = QLabel()
        self.label_cyllist.setText(
            "平场图像采集 cyl列表, (例如: -4 -3.5 -3 -2.5 -2 -1.5 -1 -0.5 0), 以空格隔开")
        grid_layout.addWidget(self.label_cyllist, 24, 0)

        self.line_edit_cyllist = QLineEdit()
        self.line_edit_cyllist.setText(
            "-4 -3.75 -3.5 -3.25 -3 -2.75 -2.5 -2.25 -2 -1.75 -1.5 -1.25 -1 -0.75 -0.5 -0.25 0")
        self.line_edit_cyllist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_cyllist, 25, 0)

        self.label_axislist = QLabel()
        self.label_axislist.setText(
            "平场图像采集 axis列表, (例如: 0 15 30 45 60 75 90 105 120 135 150 165), 以空格隔开")
        grid_layout.addWidget(self.label_axislist, 26, 0)

        self.line_edit_axislist = QLineEdit()
        self.line_edit_axislist.setText(
            "0 15 30 45 60 75 90 105 120 135 150 165")
        self.line_edit_axislist.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_axislist, 27, 0)

        self.label_path = QLabel()
        self.label_path.setText("保存路径(excel保存位置):")
        grid_layout.addWidget(self.label_path, 28, 0)

        self.line_edit_path = QLineEdit()
        self.line_edit_path.setReadOnly(True)  # 设置为只读
        self.line_edit_path.setPlaceholderText("未选择文件夹")
        self.line_edit_path.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_path, 29, 0)

        self.btn_browse = QPushButton("浏览...")
        self.btn_browse.clicked.connect(self._open_folder_dialog)
        grid_layout.addWidget(self.btn_browse, 29, 1)

        self.label_path = QLabel()
        self.label_path.setText("配置路径（eye1）")
        grid_layout.addWidget(self.label_path, 30, 0)
        self.line_edit_eye1_path = QLineEdit()
        self.line_edit_eye1_path.setReadOnly(True)
        self.line_edit_eye1_path.setText(self.select_path)
        grid_layout.addWidget(self.line_edit_eye1_path, 31, 0)

        self.btn_capture = QPushButton("单色定标")
        self.btn_capture.clicked.connect(self.start_mono_calibration)
        grid_layout.addWidget(self.btn_capture, 32, 0)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        grid_layout.addWidget(self.log_box, 33, 0)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum,
                             QSizePolicy.Expanding)
        grid_layout.addItem(spacer)

        # 将布局添加到 scroll_area_content 并将其设置为 scroll_area 的子部件
        scroll_area.setWidget(scroll_area_content)

        # 最后设置主窗口的布局
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

        self.checkbox_is_rx.setEnabled(False)
        self.label_sphlist.setVisible(False)
        self.line_edit_sphlist.setVisible(False)
        self.label_cyllist.setVisible(False)
        self.line_edit_cyllist.setVisible(False)
        self.label_axislist.setVisible(False)
        self.line_edit_axislist.setVisible(False)
        self.checkbox_enable_ae.setChecked(False)
        self.line_edit_exposure_time.setEnabled(False)
        self.line_edit_max_time.setEnabled(False)
        self.line_edit_rate.setEnabled(False)
        self.checkbox_use_roi.setEnabled(False)
        self.line_edit_pixel_count.setEnabled(False)
        self.label_exposure_offset.setVisible(False)
        self.line_edit_exposure_offset.setVisible(False)
        self.label_gray_offset.setVisible(False)
        self.line_edit_gray_offset.setVisible(False)

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

        self.line_edit_aperture.setText(params["aperture"])
        self.checkbox_exist_nd.setChecked(params["no_nd"])
        self.line_edit_ndlist.setText(params["nd_text"])
        self.checkbox_exist_xyz.setChecked(params["no_xyz"])
        self.line_edit_xyzlist.setText(params["xyz_text"])
        self.line_edit_xyzlist_lum.setText(params["luminance"])
        self.line_edit_radiance_lum.setText(params["radiance"])
        self.line_edit_exposure_offset.setText(params["et_offset"])
        self.line_edit_gray_offset.setText(params["gray_offset"])
        self.line_edit_gray_range.setText(params["gray_text"])
        self.checkbox_do_ffc.setChecked(params["do_ffc"])
        self.checkbox_is_rx.setChecked(params["do_rx"])
        self.line_edit_sphlist.setText(params["sph_text"])
        self.line_edit_cyllist.setText(params["cyl_text"])
        self.line_edit_axislist.setText(params["axis_text"])
        self.line_edit_image_size.setText(params["center_xy"])
        self.line_edit_roi_size.setText(params["roi_wh"])
        light_id_map = {
            "R": 1,
            "G": 2,
            "B": 3,
            "W": 4
        }
        light_val = params["light_source"]
        btn_id = light_id_map[light_val]
        self.rgbw_btngroup.button(btn_id).setChecked(True)
        self.line_edit_path.setText(params["save_path"])
        self.checkbox_enable_ae.setChecked(params["do_ae"])
        self.line_edit_exposure_time.setText(params["auto_et"])
        self.line_edit_max_time.setText(params["max_time"])
        self.line_edit_rate.setText(params["rate"])
        self.checkbox_use_roi.setChecked(params["use_roi"])
        self.line_edit_pixel_count.setText(params["pixel_count"])

    def read_ui_params(self) -> dict:
        param_dict = {
            "binn_selector": self.line_edit_binn_selector.currentText(),
            "binn_mode": self.line_edit_binn_mode.currentText(),
            "binn": self.line_edit_binn.text().strip(),
            "pixel_format": self.line_edit_pixel_format.currentText(),
            "aperture": self.line_edit_aperture.text().strip(),
            "no_nd": self.checkbox_exist_nd.isChecked(),
            "nd_text": self.line_edit_ndlist.text().strip(),
            "no_xyz": self.checkbox_exist_xyz.isChecked(),
            "xyz_text": self.line_edit_xyzlist.text().strip(),
            "luminance": self.line_edit_xyzlist_lum.text().strip(),
            "radiance": self.line_edit_radiance_lum.text().strip(),
            "et_offset": self.line_edit_exposure_offset.text().strip(),
            "gray_offset": self.line_edit_gray_offset.text().strip(),
            "gray_text": self.line_edit_gray_range.text().strip(),
            "do_ffc": self.checkbox_do_ffc.isChecked(),
            "do_rx": self.checkbox_is_rx.isChecked(),
            "sph_text": self.line_edit_sphlist.text().strip(),
            "cyl_text": self.line_edit_cyllist.text().strip(),
            "axis_text": self.line_edit_axislist.text().strip(),
            "center_xy": self.line_edit_image_size.text().strip(),
            "roi_wh": self.line_edit_roi_size.text().strip(),
            "light_source": self.rgbw_btngroup.checkedButton().text(),
            "save_path": self.line_edit_path.text().strip(),
            "do_ae": self.checkbox_enable_ae.isChecked(),
            "auto_et": self.line_edit_exposure_time.text().strip(),
            "max_time": self.line_edit_max_time.text().strip(),
            "rate": self.line_edit_rate.text().strip(),
            "use_roi": self.checkbox_use_roi.isChecked(),
            "pixel_count": self.line_edit_pixel_count.text().strip()
        }
        return param_dict

    def validate_input(self):
        text = self.line_edit_binn.text()
        if text:
            value = int(text)
            if value < 0 or value > 4:
                self.line_edit_binn.setText("")

    def on_ae_enabled_changed(self):
        if self.checkbox_enable_ae.isChecked():
            self.line_edit_exposure_time.setEnabled(True)
            self.line_edit_max_time.setEnabled(True)
            self.line_edit_rate.setEnabled(True)
            self.checkbox_use_roi.setEnabled(True)
            self.line_edit_pixel_count.setEnabled(True)
        else:
            self.line_edit_exposure_time.setEnabled(False)
            self.line_edit_max_time.setEnabled(False)
            self.line_edit_rate.setEnabled(False)
            self.checkbox_use_roi.setEnabled(False)
            self.line_edit_pixel_count.setEnabled(False)

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

    def on_xyz_checkbox_changed(self):
        is_checked = self.checkbox_exist_xyz.isChecked()
        self.line_edit_xyzlist.setEnabled(not is_checked)
        self.line_edit_xyzlist.setText("") if is_checked else None

    def on_nd_checkbox_changed(self):
        is_checked = self.checkbox_exist_nd.isChecked()
        self.line_edit_ndlist.setEnabled(not is_checked)
        self.line_edit_ndlist.setText("") if is_checked else None

    def do_ffc_checkbox_changed(self):
        is_checked = self.checkbox_do_ffc.isChecked()
        if is_checked:
            QMessageBox.information(
                self, "MLColorimeter", "请确保模组已定标并保存FFC图在配置中，若没有，请不要勾选", QMessageBox.Ok)
            self.checkbox_is_rx.setEnabled(True)
        else:
            self.checkbox_is_rx.setEnabled(False)

    def do_rx_checkbox_changed(self):
        is_checked = self.checkbox_is_rx.isChecked()
        if is_checked:
            self.label_sphlist.setVisible(True)
            self.line_edit_sphlist.setVisible(True)
            self.label_cyllist.setVisible(True)
            self.line_edit_cyllist.setVisible(True)
            self.label_axislist.setVisible(True)
            self.line_edit_axislist.setVisible(True)
        else:
            self.label_sphlist.setVisible(False)
            self.line_edit_sphlist.setVisible(False)
            self.label_cyllist.setVisible(False)
            self.line_edit_cyllist.setVisible(False)
            self.label_axislist.setVisible(False)
            self.line_edit_axislist.setVisible(False)

    def start_mono_calibration(self):
        try:
            self.eye1_path = self.line_edit_eye1_path.text()
            if os.path.exists(self.eye1_path):
                self.get_lum_rad_folder_rule(self.eye1_path)
            else:
                QMessageBox.warning(self, "MLColorimeter",
                                    "EYE1路径不存在", QMessageBox.Ok)
                return
            if not self.temp:
                QMessageBox.warning(self, "MLColorimeter",
                                    "config.ini读取失败", QMessageBox.Ok)
                return
            self.out_path = self.line_edit_path.text()
            if self.out_path is None or self.out_path == "":
                QMessageBox.warning(self, "MLColorimeter",
                                    "请先选择保存路径", QMessageBox.Ok)
                return
            self.pixel_format = self.get_current_pixel_format()
            self.binn_selector = self.get_current_binning_selector()
            self.binn_mode = self.get_current_binning_mode()
            self.binn = mlcm.Binning(int(self.line_edit_binn.text().strip()))
            self.lum_dict = {}
            self.luminance_no_xyz = 0.0
            if (self.checkbox_exist_xyz.isChecked()):
                self.xyz_list = []
                lum_list = self.line_edit_xyzlist_lum.text().split()
                self.luminance_no_xyz = float(
                    lum_list[0]) if len(lum_list) > 0 else 0.0
            else:
                xyz_text = [int(xyz)
                            for xyz in self.line_edit_xyzlist.text().split()]
                self.xyz_list = [mlcm.MLFilterEnum(xyz) for xyz in xyz_text]
                if self.generate_luminance_dict():
                    self.lum_dict = self.generate_luminance_dict()
                else:
                    return
            self.aperture = self.line_edit_aperture.text()
            if self.checkbox_exist_nd.isChecked():
                self.nd_list = []
            else:
                nd_text = [int(nd)
                           for nd in self.line_edit_ndlist.text().split()]
                self.nd_list = [mlcm.MLFilterEnum(nd) for nd in nd_text]
            self.light_source = self.rgbw_btngroup.checkedButton().text()
            self.radiance = float(self.line_edit_radiance_lum.text())
            self.gray_list = [
                float(gray) for gray in self.line_edit_gray_range.text().split()]
            self.image_point = self.line_edit_image_size.text().split()
            self.roi_size = self.line_edit_roi_size.text().split()
            self.expusure_offset = float(self.line_edit_exposure_offset.text())
            self.gray_offset = float(self.line_edit_gray_offset.text())

            # 新建日志文件
            self.log_file_path = os.path.join(
                self.cfg_helper.log_path, f"mono_calibration_log.txt")

            if self.checkbox_enable_ae.isChecked():
                self.exposure_time = float(self.line_edit_exposure_time.text())
                self.max_time = float(self.line_edit_max_time.text())
                self.rate = int(self.line_edit_rate.text())
                self.pixel_count = int(self.line_edit_pixel_count.text())
                self.use_roi = self.checkbox_use_roi.isChecked()

            self.btn_capture.setEnabled(False)
            self.is_calibrating = True
            # 将参数打包到字典中
            parameters = {
                'colorimeter': self.colorimeter,
                'nd_list': self.nd_list,
                'xyz_list': self.xyz_list,
                'gray_range': self.gray_list,
                'aperture': self.aperture,
                'light_source': self.light_source,
                'luminance_values': self.lum_dict,
                'luminance_no_xyz': self.luminance_no_xyz,
                'radiance': self.radiance,
                'eye1_path': self.eye1_path,
                'out_path': self.out_path,
                'image_point': self.image_point,
                'roi_size': self.roi_size,
                'lum_folder_rule': self.lum_folder_rule,
                'rad_folder_rule': self.rad_folder_rule,
                'binn_selector': self.binn_selector,
                'binn_mode': self.binn_mode,
                'binn': self.binn,
                'pixel_format': self.pixel_format,
                'do_nd': self.checkbox_exist_nd.isChecked(),
                'do_xyz': self.checkbox_exist_xyz.isChecked(),
                'expusure_offset': self.expusure_offset,
                'gray_offset': self.gray_offset,
            }
            if self.checkbox_enable_ae.isChecked():
                parameters['exposure_time'] = self.exposure_time
                parameters['max_time'] = self.max_time
                parameters['rate'] = self.rate
                parameters['pixel_count'] = self.pixel_count
                parameters['use_roi'] = self.use_roi
            if self.checkbox_do_ffc.isChecked():
                self.is_rx = self.checkbox_is_rx.isChecked()
                if self.is_rx:
                    self.sph_list = [
                        float(sph) for sph in self.line_edit_sphlist.text().split()]
                    self.cyl_list = [
                        float(cyl) for cyl in self.line_edit_cyllist.text().split()]
                    self.axis_list = [
                        int(axis) for axis in self.line_edit_axislist.text().split()]
                else:
                    self.sph_list = [0.0]
                    self.cyl_list = [0.0]
                    self.axis_list = [0]
                parameters['sph_list'] = self.sph_list
                parameters['cyl_list'] = self.cyl_list
                parameters['axis_list'] = self.axis_list
                self.calibration_doffc_thread = CalibrationDoFFCThread(
                    parameters)
                self.calibration_doffc_thread.finished.connect(
                    self.on_calibration_finished)
                self.calibration_doffc_thread.error.connect(
                    self.on_calibration_error)
                self.calibration_doffc_thread.status_update.connect(
                    self.flush_log)
                self.calibration_doffc_thread.start()  # 启动线程
            else:
                self.calibration_thread = CalibrationThread(parameters)
                self.calibration_thread.finished.connect(
                    self.on_calibration_finished)
                self.calibration_thread.error.connect(
                    self.on_calibration_error)
                self.calibration_thread.status_update.connect(
                    self.flush_log)
                self.calibration_thread.start()  # 启动线程

        except Exception as e:
            QMessageBox.critical(self, "MLColorimeter", "exception" + e,  # type: ignore
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            self.btn_capture.setEnabled(True)
            self.is_calibrating = False  # 标识定标完成

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

    def get_lum_rad_folder_rule(self, config_path):
        self.ini_path = config_path+"/"+"config.ini"
        if not os.path.exists(self.ini_path):
            QMessageBox.critical(self, "MLColorimeter", "config.ini文件不存在，请检查eye1路径下的文件",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            self.temp = False
            return

        config = configparser.ConfigParser()
        try:
            config.read(self.ini_path, encoding='utf-8')

            if 'Luminance' in config:
                self.lum_folder_rule = config['Luminance'].get(
                    'Folder_Rule', '').strip()
                self.lum_suffix = config['Luminance'].get('Suffix', '').strip()
                self.temp = True
            else:
                QMessageBox.critical(self, "MLColorimeter", "config.ini文件中缺少Luminance部分，请检查eye1路径下的文件",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                self.temp = False
                return

            if 'Radiance' in config:
                self.rad_folder_rule = config['Radiance'].get(
                    'Folder_Rule', '').strip()
                self.rad_suffix = config['Radiance'].get('Suffix', '').strip()
                self.temp = True
            else:
                QMessageBox.critical(self, "MLColorimeter", "config.ini文件中缺少Radiance部分，请检查eye1路径下的文件",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                self.temp = False
                return

        except Exception as e:
            QMessageBox.critical(self, "MLColorimeter", f"读取config.ini文件失败: {str(e)}",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            self.temp = False
            return

    def on_calibration_finished(self):
        QMessageBox.information(self, "MLColorimeter",
                                "单色定标完成!", QMessageBox.Ok)
        self.btn_capture.setEnabled(True)
        self.is_calibrating = False  # 标识定标完成

    def on_calibration_error(self, error_message):
        QMessageBox.critical(self, "MLColorimeter",
                             "发生错误: " + error_message, QMessageBox.Ok)
        self.btn_capture.setEnabled(True)
        self.is_calibrating = False  # 标识定标完成

    def closeEvent(self, event):
        if self.is_calibrating:
            # 如果正在进行定标，拦截关闭事件
            event.ignore()
            QMessageBox.warning(self, "警告", "定标进行中，请勿关闭窗口", QMessageBox.Ok)
        else:
            # ==============关闭窗口保存当前UI参数====================
            p = self.read_ui_params()
            self.cfg_helper.save_params(p)
            self.deleteLater()
            event.accept()

    def generate_luminance_dict(self):
        lum_dict = {}
        try:
            xyzlist = self.line_edit_xyzlist.text().strip().split()
            xyzlist_lum = self.line_edit_xyzlist_lum.text().strip().split()
            if len(xyzlist) != len(xyzlist_lum):
                QMessageBox.warning(self, "MLColorimeter",
                                    "亮度个数与xyz滤光片不相同，请检查并保持一一对应", QMessageBox.Ok)
                return lum_dict
            for i, xyz in enumerate(xyzlist):
                if xyz == '1':
                    lum_dict[mlcm.MLFilterEnum.X] = float(xyzlist_lum[i])
                elif xyz == '2':
                    lum_dict[mlcm.MLFilterEnum.Y] = float(xyzlist_lum[i])
                elif xyz == '3':
                    lum_dict[mlcm.MLFilterEnum.Z] = float(xyzlist_lum[i])
                elif xyz == '10':
                    lum_dict[mlcm.MLFilterEnum.Clear] = float(xyzlist_lum[i])
                elif xyz == "12":
                    lum_dict[mlcm.MLFilterEnum.YA] = float(xyzlist_lum[i])
        except Exception as e:
            QMessageBox.critical(self, "MLColorimeter", "生成亮度字典异常" + e,  # type: ignore
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        return lum_dict

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

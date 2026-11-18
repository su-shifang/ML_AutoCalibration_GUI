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
    QFormLayout,
    QCheckBox,
    QListWidget,
    QComboBox,
    QPlainTextEdit
)
from PyQt5.QtGui import QIntValidator,QDoubleValidator,QColor,QTextCharFormat
from core.app_config import AppConfig
from core.config_helper import UiConfigHelper,MsgLevel
from PyQt5.QtCore import pyqtSignal, Qt,QThread
import mlcolorimeter as mlcm
import numpy as np
import matplotlib.pyplot as plt
from openpyxl import Workbook, load_workbook
from openpyxl.drawing.image import Image
from scripts.field_curve import field_curve
import json,os
from datetime import datetime

class FiledCurveThread(QThread):
    finished=pyqtSignal() # 线程完成信号
    error=pyqtSignal(str) # 错误信号
    status_update=pyqtSignal(str) # 状态更新信号

    def __init__(self, parameters):
        super().__init__()
        self.parameters=parameters
    
    def run(self):
        try:
            # 包装回调：接受level，msg，拼接成字符串再发给信号
            def callback_wrapper(level: MsgLevel,msg:str):
                self.status_update.emit(msg)
            field_curve(status_callback=callback_wrapper, **self.parameters) # type: ignore
            self.finished.emit() # 发送完成信号
        except Exception as e:
            self.error.emit(str(e)) # 发送错误信号

class FiledCurveWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("capture field curve")
        self.setGeometry(200, 200, 800, 500)
        self.colorimeter = AppConfig.get_colorimeter()
        self.setWindowFlags(Qt.Window | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint) # type: ignore

        self.double_validator=QDoubleValidator()
        self.int_validator=QIntValidator()
        
        self.dialog_title = "选择文件夹"
        self.default_path = ""
        self.file_name = "field_curve.xlsx"
        self.roi_list=[]
        self.exposure_mode=['Auto','Fixed']
        self.binning_selector=['Logic','Sensor']
        self.binning_mode=['AVERAGE','SUM']
        self.pixel_format=['MLMono8','MLMono10','MLMono12','MLMono16','MLRGB24','MLBayer','MLBayerGB8','MLBayerGB12']     
        self.log_file_path=""
        self.cfg_helper=UiConfigHelper("field_curve_params.json")
        self._init_ui()

        self.is_running=False
        # 默认参数模板
        self.default_ui_params = {
            "binn_selector": "Logic",
            "binn_mode": "AVERAGE",
            "binn": "0",
            "pixel_format": "MLMono12",
            "exposure_mode": "Auto",
            "exposure_time": "100",
            "focus_max": "37",
            "focus_min": "12",
            "inf_pos": "25.22",
            "focal_length": "39.7",
            "pixel_size": "0.0035",
            "focal_space": "-2.92",
            "use_chess_mode": True,
            "use_lpmm_unit": True,
            "rough_step": "0.5",
            "use_fine_adjust": False,
            "fine_step": "0.1",
            "average_count": "1",
            "save_result_image": False,
            "save_roi_text": "6000 6000 500 500",
            "image_save_path": "",
            "freq_list_text": "6.75",
            "roi_x": "0",
            "roi_y": "0",
            "roi_w": "100",
            "roi_h": "100",
            "out_path": "",
            "roi_serial": []
        }
        self.cur_ui_params=self.cfg_helper.load_params(self.default_ui_params)
        self.fill_ui_by_params(self.cur_ui_params)
    
    def _init_ui(self):
        grid_layout = QGridLayout()

        group_box0=QGroupBox("相机设置")
        from_layout0=QFormLayout()

        self.label_binn_selector = QLabel(" binning_selector：")
        self.line_edit_binn_selector = QComboBox()
        self.line_edit_binn_selector.addItems(self.binning_selector)
        self.line_edit_binn_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_binn_mode = QLabel(" binning_mode：")
        self.line_edit_binn_mode = QComboBox()
        self.line_edit_binn_mode.addItems(self.binning_mode)
        self.line_edit_binn_mode.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        horizontal_layout=QHBoxLayout()
        horizontal_layout.addWidget(self.label_binn_selector)
        horizontal_layout.addWidget(self.line_edit_binn_selector)
        horizontal_layout.addWidget(self.label_binn_mode)
        horizontal_layout.addWidget(self.line_edit_binn_mode)
        from_layout0.addRow(horizontal_layout)

        self.label_binnlist = QLabel(" binning：")
        self.line_edit_binnlist = QLineEdit()
        self.line_edit_binnlist.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        int_validator=QIntValidator(0,4,self)
        self.line_edit_binnlist.setValidator(int_validator)
        self.line_edit_binnlist.setPlaceholderText("0: 1X1, 1: 2X2, 2: 4X4, 3: 8X8, 4: 16X16")
        self.line_edit_binnlist.setText("0")
        self.line_edit_binnlist.textChanged.connect(self.validate_input)
        from_layout0.addRow(self.label_binnlist, self.line_edit_binnlist)

        self.label_exposure_mode = QLabel(" exposure_mode：")
        self.line_edit_exposure_mode = QComboBox()
        self.line_edit_exposure_mode.addItems(self.exposure_mode)
        self.line_edit_exposure_mode.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_exposure_time = QLabel(" exposure_time(ms)：")
        self.line_edit_exposure_time = QLineEdit()
        self.line_edit_exposure_time.setValidator(self.double_validator)
        self.line_edit_exposure_time.setText("100")
        self.line_edit_exposure_time.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_pixel_format = QLabel(" pixel_format：")
        self.line_edit_pixel_format = QComboBox()
        self.line_edit_pixel_format.addItems(self.pixel_format) # type: ignore
        self.line_edit_pixel_format.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.line_edit_pixel_format.setCurrentText("MLMono12")


        horizontal_layout1=QHBoxLayout()
        horizontal_layout1.addWidget(self.label_exposure_mode)
        horizontal_layout1.addWidget(self.line_edit_exposure_mode)
        horizontal_layout1.addWidget(self.label_exposure_time)
        horizontal_layout1.addWidget(self.line_edit_exposure_time)
        horizontal_layout1.addWidget(self.label_pixel_format)
        horizontal_layout1.addWidget(self.line_edit_pixel_format)
        from_layout0.addRow(horizontal_layout1)

        group_box0.setLayout(from_layout0)
        grid_layout.addWidget(group_box0, 0, 0)

        group_box=QGroupBox("过焦参数")
        from_layout=QFormLayout()

        self.label_focus_max=QLabel("focus_max: ")
        self.line_edit_focus_max = QLineEdit()
        self.line_edit_focus_max.setValidator(self.double_validator)
        self.line_edit_focus_max.setText("37")
        self.line_edit_focus_max.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_focus_min=QLabel("focus_min: ")
        self.line_edit_focus_min = QLineEdit()
        self.line_edit_focus_min.setValidator(self.double_validator)
        self.line_edit_focus_min.setText("12")
        self.line_edit_focus_min.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_inf_pos=QLabel("inf_pos: ")
        self.line_edit_inf_pos = QLineEdit()
        self.line_edit_inf_pos.setValidator(self.double_validator)
        self.line_edit_inf_pos.setText("25.22")
        self.line_edit_inf_pos.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_focal_length=QLabel("focal_length: ")
        self.line_edit_focal_length = QLineEdit()
        self.line_edit_focal_length.setValidator(self.double_validator)
        self.line_edit_focal_length.setText("39.7")
        self.line_edit_focal_length.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        horizontal_layout2=QHBoxLayout()
        horizontal_layout2.addWidget(self.label_focus_max)
        horizontal_layout2.addWidget(self.line_edit_focus_max)
        horizontal_layout2.addWidget(self.label_focus_min)
        horizontal_layout2.addWidget(self.line_edit_focus_min)
        horizontal_layout2.addWidget(self.label_inf_pos)
        horizontal_layout2.addWidget(self.line_edit_inf_pos)
        horizontal_layout2.addWidget(self.label_focal_length)
        horizontal_layout2.addWidget(self.line_edit_focal_length)
        from_layout.addRow(horizontal_layout2)

        self.label_pixel_size=QLabel("pixel_size: ")
        self.line_edit_pixel_size = QLineEdit()
        self.line_edit_pixel_size.setValidator(self.double_validator)
        self.line_edit_pixel_size.setText("0.0035")
        self.line_edit_pixel_size.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_focal_space=QLabel("focal_space: ")
        self.line_edit_focal_space = QLineEdit()
        self.line_edit_focal_space.setValidator(self.double_validator)
        self.line_edit_focal_space.setText("-2.92")
        self.line_edit_focal_space.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_use_chess_mode=QLabel("use_chess_mode: ")
        self.line_edit_use_chess_mode = QCheckBox()
        self.line_edit_use_chess_mode.setChecked(True)
        self.line_edit_use_chess_mode.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_use_lpmm_unit=QLabel("use_lpmm_unit: ")
        self.line_edit_use_lpmm_unit = QCheckBox()
        self.line_edit_use_lpmm_unit.setChecked(True)
        self.line_edit_use_lpmm_unit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        horizontal_layout3=QHBoxLayout()
        horizontal_layout3.addWidget(self.label_pixel_size)
        horizontal_layout3.addWidget(self.line_edit_pixel_size)
        horizontal_layout3.addWidget(self.label_focal_space)
        horizontal_layout3.addWidget(self.line_edit_focal_space)
        horizontal_layout3.addWidget(self.label_use_chess_mode)
        horizontal_layout3.addWidget(self.line_edit_use_chess_mode)
        horizontal_layout3.addWidget(self.label_use_lpmm_unit)
        horizontal_layout3.addWidget(self.line_edit_use_lpmm_unit)
        from_layout.addRow(horizontal_layout3)

        self.label_rough_step=QLabel("coarse_step: ")
        self.line_edit_rough_step = QLineEdit()
        self.line_edit_rough_step.setValidator(self.double_validator)
        self.line_edit_rough_step.setText("0.5")
        self.line_edit_rough_step.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_use_fine_adjust=QLabel("use_fine_adjust: ")
        self.line_edit_use_fine_adjust = QCheckBox()
        self.line_edit_use_fine_adjust.setChecked(False)
        self.line_edit_use_fine_adjust.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_fine_step=QLabel("fine_step: ")
        self.line_edit_fine_step = QLineEdit()
        self.line_edit_fine_step.setValidator(self.double_validator)
        self.line_edit_fine_step.setText("0.1")
        self.line_edit_fine_step.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_average_count=QLabel("average_count: ")
        self.line_edit_average_count = QLineEdit()
        self.line_edit_average_count.setValidator(self.int_validator)
        self.line_edit_average_count.setText("1")
        self.line_edit_average_count.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        horizontal_layout4=QHBoxLayout()
        horizontal_layout4.addWidget(self.label_rough_step)
        horizontal_layout4.addWidget(self.line_edit_rough_step)
        horizontal_layout4.addWidget(self.label_use_fine_adjust)
        horizontal_layout4.addWidget(self.line_edit_use_fine_adjust)
        horizontal_layout4.addWidget(self.label_fine_step)
        horizontal_layout4.addWidget(self.line_edit_fine_step)
        horizontal_layout4.addWidget(self.label_average_count)
        horizontal_layout4.addWidget(self.line_edit_average_count)
        from_layout.addRow(horizontal_layout4)

        self.label_save_result_image=QLabel("save_result_image: ")
        self.line_edit_save_result_image = QCheckBox()
        self.line_edit_save_result_image.setChecked(False)
        self.line_edit_save_result_image.stateChanged.connect(self._use_state_changed)
        self.line_edit_save_result_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        from_layout.addRow(self.label_save_result_image,self.line_edit_save_result_image)

        self.label_save_roi=QLabel("save_roi(input: x y width height): ")
        self.line_edit_save_roi = QLineEdit()
        self.line_edit_save_roi.setText("6000 6000 500 500")
        self.line_edit_save_roi.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        from_layout.addRow(self.label_save_roi,self.line_edit_save_roi)

        self.label_image_save_path = QLabel("image_save_path:")

        self.line_edit_image_save_path = QLineEdit()
        self.line_edit_image_save_path.setReadOnly(True)  # 设置为只读
        self.line_edit_image_save_path.setPlaceholderText("未选择文件夹")
        self.line_edit_image_save_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.btn_select = QPushButton("浏览...")
        self.btn_select.clicked.connect(self._open__image_folder_dialog)

        horizontal_layout5=QHBoxLayout()
        horizontal_layout5.addWidget(self.label_image_save_path)
        horizontal_layout5.addWidget(self.line_edit_image_save_path)
        horizontal_layout5.addWidget(self.btn_select)
        from_layout.addRow(horizontal_layout5)


        group_box.setLayout(from_layout)
        grid_layout.addWidget(group_box, 1, 0)

        self.label_freq_list = QLabel()
        self.label_freq_list.setText("频率列表, 例如: 6.75 13.5, 以空格隔开")
        grid_layout.addWidget(self.label_freq_list, 2, 0)
        self.line_edit_freq_list = QLineEdit()
        self.line_edit_freq_list.setText("6.75")
        self.line_edit_freq_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_freq_list, 3, 0)

        group_box1=QGroupBox("roi设置")
        from_layout1=QFormLayout()

        self.label_x_input=QLabel("x_input: ")
        self.line_edit_x_input = QLineEdit()
        self.line_edit_x_input.setValidator(self.int_validator)
        self.line_edit_x_input.setText("0")
        self.line_edit_x_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_y_input=QLabel("y_input: ")
        self.line_edit_y_input = QLineEdit()
        self.line_edit_y_input.setValidator(self.int_validator)
        self.line_edit_y_input.setText("0")
        self.line_edit_y_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_width_input=QLabel("width_input: ")
        self.line_edit_width_input = QLineEdit()
        self.line_edit_width_input.setValidator(self.int_validator)
        self.line_edit_width_input.setText("100")
        self.line_edit_width_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.label_height_input=QLabel("height_input: ")
        self.line_edit_height_input = QLineEdit()
        self.line_edit_height_input.setValidator(self.int_validator)
        self.line_edit_height_input.setText("100")
        self.line_edit_height_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        horizontal_layout5=QHBoxLayout()
        horizontal_layout5.addWidget(self.label_x_input)
        horizontal_layout5.addWidget(self.line_edit_x_input)
        horizontal_layout5.addWidget(self.label_y_input)
        horizontal_layout5.addWidget(self.line_edit_y_input)
        horizontal_layout5.addWidget(self.label_width_input)
        horizontal_layout5.addWidget(self.line_edit_width_input)
        horizontal_layout5.addWidget(self.label_height_input)
        horizontal_layout5.addWidget(self.line_edit_height_input)
        from_layout1.addRow(horizontal_layout5)

        self.label_roi_count=QLabel("roi_count: ")
        self.line_edit_roi_count = QLineEdit()
        self.line_edit_roi_count.setReadOnly(True)
        self.line_edit_roi_count.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        from_layout1.addRow(self.label_roi_count,self.line_edit_roi_count)


        self.add_button = QPushButton("Add ROI")
        self.add_button.clicked.connect(self.add_roi)
        self.delete_button=QPushButton("Delete ROI")
        self.delete_button.clicked.connect(self.delete_roi)
        from_layout1.addRow(self.add_button,self.delete_button)

        self.load_config_button=QPushButton("Load Config")
        self.load_config_button.clicked.connect(self.load_config)
        self.save_config_button=QPushButton("Save Config")
        self.save_config_button.clicked.connect(self.save_config)
        from_layout1.addRow(self.load_config_button,self.save_config_button)

        self.roi_display=QListWidget()
        self.roi_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.roi_display.itemDoubleClicked.connect(self.on_roi_double_click)
        from_layout1.addRow(self.roi_display)

        group_box1.setLayout(from_layout1)
        grid_layout.addWidget(group_box1, 4, 0)

        self.label_path = QLabel()
        self.label_path.setText("保存路径:")
        grid_layout.addWidget(self.label_path, 5, 0)

        self.line_edit_path = QLineEdit()
        self.line_edit_path.setReadOnly(True)  # 设置为只读
        self.line_edit_path.setPlaceholderText("未选择文件夹")
        self.line_edit_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_path, 6, 0)

        self.btn_browse = QPushButton("浏览...")
        self.btn_browse.clicked.connect(self._open_folder_dialog)
        grid_layout.addWidget(self.btn_browse, 6, 1)

        self.btn_capture = QPushButton("开始拍图")
        self.btn_capture.clicked.connect(self.start_capture)
        grid_layout.addWidget(self.btn_capture, 7, 0)

        self.log_box=QPlainTextEdit()
        self.log_box.setReadOnly(True)
        grid_layout.addWidget(self.log_box,8,0)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        grid_layout.addItem(spacer)

        self.setLayout(grid_layout)
        self.label_save_roi.setEnabled(False)
        self.line_edit_save_roi.setEnabled(False)
        self.label_image_save_path.setEnabled(False)
        self.line_edit_image_save_path.setEnabled(False)
        self.btn_select.setEnabled(False)
    def on_roi_double_click(self,item):
        x,y,w,h=map(int,item.text().split(","))
        self.line_edit_x_input.setText(str(x))
        self.line_edit_y_input.setText(str(y))
        self.line_edit_width_input.setText(str(w))
        self.line_edit_height_input.setText(str(h))
        
    def fill_ui_by_params(self, params: dict):
        # 回填下拉框
        idx = self.line_edit_binn_selector.findText(params["binn_selector"])
        if idx >=0:
            self.line_edit_binn_selector.setCurrentIndex(idx)
        idx = self.line_edit_binn_mode.findText(params["binn_mode"])
        if idx >=0:
            self.line_edit_binn_mode.setCurrentIndex(idx)
        idx = self.line_edit_exposure_mode.findText(params["exposure_mode"])
        if idx >=0:
            self.line_edit_exposure_mode.setCurrentIndex(idx)
        idx = self.line_edit_pixel_format.findText(params["pixel_format"])
        if idx >=0:
            self.line_edit_pixel_format.setCurrentIndex(idx)

        self.line_edit_binnlist.setText(params["binn"])
        self.line_edit_exposure_time.setText(params["exposure_time"])
        self.line_edit_focus_max.setText(params["focus_max"])
        self.line_edit_focus_min.setText(params["focus_min"])
        self.line_edit_inf_pos.setText(params["inf_pos"])
        self.line_edit_focal_length.setText(params["focal_length"])
        self.line_edit_pixel_size.setText(params["pixel_size"])
        self.line_edit_focal_space.setText(params["focal_space"])
        self.line_edit_rough_step.setText(params["rough_step"])
        self.line_edit_fine_step.setText(params["fine_step"])
        self.line_edit_average_count.setText(params["average_count"])
        self.line_edit_save_roi.setText(params["save_roi_text"])
        self.line_edit_image_save_path.setText(params["image_save_path"])
        self.line_edit_freq_list.setText(params["freq_list_text"])
        self.line_edit_x_input.setText(params["roi_x"])
        self.line_edit_y_input.setText(params["roi_y"])
        self.line_edit_width_input.setText(params["roi_w"])
        self.line_edit_height_input.setText(params["roi_h"])
        self.line_edit_path.setText(params["out_path"])

        self.line_edit_use_chess_mode.setChecked(params["use_chess_mode"])
        self.line_edit_use_lpmm_unit.setChecked(params["use_lpmm_unit"])
        self.line_edit_use_fine_adjust.setChecked(params["use_fine_adjust"])
        self.line_edit_save_result_image.setChecked(params["save_result_image"])

        # 回填ROI列表
        self.roi_list.clear()
        self.roi_display.clear()
        for item in params.get("roi_serial", []):
            rect = mlcm.pyCVRect(item["x"], item["y"], item["width"], item["height"])
            self.roi_list.append(rect)
            self.roi_display.addItem(f"{rect.x},{rect.y},{rect.width},{rect.height}")
        self.line_edit_roi_count.setText(str(len(self.roi_list)))
        self._use_state_changed()

    def collect_ui_params(self) -> dict:
        roi_serial = []
        for r in self.roi_list:
            roi_serial.append(self.serialize_pyCVRect(r))
        param_dict = {
            "binn_selector": self.line_edit_binn_selector.currentText(),
            "binn_mode": self.line_edit_binn_mode.currentText(),
            "binn": self.line_edit_binnlist.text().strip(),
            "pixel_format": self.line_edit_pixel_format.currentText(),
            "exposure_mode": self.line_edit_exposure_mode.currentText(),
            "exposure_time": self.line_edit_exposure_time.text().strip(),
            "focus_max": self.line_edit_focus_max.text().strip(),
            "focus_min": self.line_edit_focus_min.text().strip(),
            "inf_pos": self.line_edit_inf_pos.text().strip(),
            "focal_length": self.line_edit_focal_length.text().strip(),
            "pixel_size": self.line_edit_pixel_size.text().strip(),
            "focal_space": self.line_edit_focal_space.text().strip(),
            "use_chess_mode": self.line_edit_use_chess_mode.isChecked(),
            "use_lpmm_unit": self.line_edit_use_lpmm_unit.isChecked(),
            "rough_step": self.line_edit_rough_step.text().strip(),
            "use_fine_adjust": self.line_edit_use_fine_adjust.isChecked(),
            "fine_step": self.line_edit_fine_step.text().strip(),
            "average_count": self.line_edit_average_count.text().strip(),
            "save_result_image": self.line_edit_save_result_image.isChecked(),
            "save_roi_text": self.line_edit_save_roi.text().strip(),
            "image_save_path": self.line_edit_image_save_path.text().strip(),
            "freq_list_text": self.line_edit_freq_list.text().strip(),
            "roi_x": self.line_edit_x_input.text().strip(),
            "roi_y": self.line_edit_y_input.text().strip(),
            "roi_w": self.line_edit_width_input.text().strip(),
            "roi_h": self.line_edit_height_input.text().strip(),
            "out_path": self.line_edit_path.text().strip(),
            "roi_serial": roi_serial
        }
        return param_dict

    def _use_state_changed(self):
        if self.line_edit_save_result_image.isChecked():
            self.label_save_roi.setEnabled(True)
            self.line_edit_save_roi.setEnabled(True)
            self.label_image_save_path.setEnabled(True)
            self.line_edit_image_save_path.setEnabled(True)
            self.btn_select.setEnabled(True)
        else:
            self.label_save_roi.setEnabled(False)
            self.line_edit_save_roi.setEnabled(False)
            self.label_image_save_path.setEnabled(False)
            self.line_edit_image_save_path.setEnabled(False)
            self.btn_select.setEnabled(False)

    def validate_input(self):
        text=self.line_edit_binnlist.text()
        if text:
            value=int(text)
            if value <0 or value > 4:
                self.line_edit_binnlist.setText("")
    def _open_folder_dialog(self):
        # 打开文件夹选择对话框
        folder_path = QFileDialog.getExistingDirectory(
            self,
            self.dialog_title,
            self.default_path if self.default_path else "",  # 初始路径
            options=QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks, # type: ignore
        )

        if folder_path:
            self.save_path = folder_path
            self.line_edit_path.setText(folder_path)
        else:
            QMessageBox.critical(self,"MLColorimeter","选择路径错误",QMessageBox.Yes | QMessageBox.No,QMessageBox.Yes)

    def _open__image_folder_dialog(self):
        # 打开文件夹选择对话框
        folder_path = QFileDialog.getExistingDirectory(
            self,
            self.dialog_title,
            self.default_path if self.default_path else "",  # 初始路径
            options=QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks, # type: ignore
        )

        if folder_path:
            self.line_edit_image_save_path.setText(folder_path)
        else:
            QMessageBox.critical(self,"MLColorimeter","选择路径错误",QMessageBox.Yes | QMessageBox.No,QMessageBox.Yes)


    def add_roi(self):

        try:
            x=int(self.line_edit_x_input.text().strip())
            y=int(self.line_edit_y_input.text().strip())
            width=int(self.line_edit_width_input.text().strip())
            height=int(self.line_edit_height_input.text().strip())

            # 创建roi并添加到列表
            roi=mlcm.pyCVRect(x,y,width,height)
            self.roi_list.append(roi)
            self.line_edit_roi_count.setText(str(len(self.roi_list)))
            # 显示在控件上
            roi_str=f"{x},{y},{width},{height}"
            self.roi_display.addItem(roi_str)
            
        except Exception as e:
            QMessageBox.critical(self,"MLColorimeter","exception" + str(e), QMessageBox.Yes | QMessageBox.No,QMessageBox.Yes)

    def delete_roi(self):
        try:

            current_item=self.roi_display.currentItem()
            if current_item is None:
                QMessageBox.warning(self,"警告","请先选择要删除的ROI",QMessageBox.Ok)
                return
            
            roi_str=current_item.text()
            # 解析ROi
            roi_coords=list(map(int,roi_str.split(',')))
            roi_list=[int(roi) for roi in roi_coords]
            roi_x=roi_list[0]
            roi_y=roi_list[1]
            roi_w=roi_list[2]
            roi_h=roi_list[3]
            roi_remove=mlcm.pyCVRect(roi_x,roi_y,roi_w,roi_h)
            for index,roi in enumerate(self.roi_list):
                if (roi.x == roi_remove.x and roi.y==roi_remove.y and roi.width==roi_remove.width and roi.height==roi_remove.height):
                    # 只删除第一个匹配的roi
                    del self.roi_list[index]
                    break # 找到并删除后退出循环
            self.line_edit_roi_count.setText(str(len(self.roi_list)))
            
            row=self.roi_display.row(current_item)
            self.roi_display.takeItem(row)
        except Exception as e:
            QMessageBox.critical(self,"MLColorimeter","exception" + str(e), QMessageBox.Yes | QMessageBox.No,QMessageBox.Yes)

    def load_config(self):
        try:
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getOpenFileName(self, "Load ROI Config", "", "JSON Files (*.json);;All Files (*)", options=options)
            if file_name:
                # 读取json文件
                with open(file_name,'r') as f:
                    serialized_data=json.load(f)
                # 清空现有的roi_list
                self.roi_list.clear()
                self.roi_display.clear()

                # 将每个字典转换为pyCVRect对象并添加到roi_list
                for item in serialized_data:
                    rect=mlcm.pyCVRect(item['x'],item['y'],item['width'],item['height'])
                    self.roi_list.append(rect)
                    roi_str=f"{rect.x},{rect.y},{rect.width},{rect.height}"
                    self.roi_display.addItem(roi_str)
                self.line_edit_roi_count.setText(str(len(self.roi_list)))
                

        except Exception as e:
            QMessageBox.critical(self,"MLColorimeter","exception" + str(e), QMessageBox.Yes | QMessageBox.No,QMessageBox.Yes)

    def save_config(self):
        try:
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(self, "Save ROI Config", "", "JSON Files (*.json);;All Files (*)", options=options)
            if file_name:
                # 序列化
                serialized_dict=[]
                for value in self.roi_list:
                    serialized_dict.append(self.serialize_pyCVRect(value))
                with open(file_name,'w') as f:
                    json.dump(serialized_dict,f,ensure_ascii=False,indent=4)
                QMessageBox.information(self,"成功","保存成功！",QMessageBox.Ok)
        except Exception as e:
            QMessageBox.critical(self,"MLColorimeter","exception" + str(e), QMessageBox.Yes | QMessageBox.No,QMessageBox.Yes)
    def serialize_pyCVRect(self,rect:mlcm.pyCVRect):
        return{
            'x':rect.x,
            'y':rect.y,
            'width':rect.width,
            'height':rect.height
        }
    def start_capture(self):
        try:
            self.pixel_format=self.get_current_pixel_format()
            self.binn_selector=self.get_current_binning_selector()
            self.binn_mode=self.get_current_binning_mode()
            self.binn=mlcm.Binning(int(self.line_edit_binnlist.text().strip()))
            self.exposure_mode=self.get_current_exposure_mode()
            self.exposure_time=float(self.line_edit_exposure_time.text().strip())
            self.exposure=mlcm.pyExposureSetting(exposure_mode=self.exposure_mode,exposure_time=self.exposure_time)
            self.focus_max=float(self.line_edit_focus_max.text().strip())
            self.focus_min=float(self.line_edit_focus_min.text().strip())
            if self.focus_min>=self.focus_max:
                QMessageBox.warning(self,"参数错误", "focus_min必须小于focus_max")
                return
            self.inf_pos=float(self.line_edit_inf_pos.text().strip())
            self.focal_length=float(self.line_edit_focal_length.text().strip())
            self.pixel_size=float(self.line_edit_pixel_size.text().strip())
            self.focal_space=float(self.line_edit_focal_space.text().strip())
            self.use_chess_mode=self.line_edit_use_chess_mode.isChecked()
            self.use_lpmm_unit=self.line_edit_use_lpmm_unit.isChecked()
            self.coarse_step=float(self.line_edit_rough_step.text().strip())
            self.fine_step=float(self.line_edit_fine_step.text())

            self.use_fine_adjust=self.line_edit_use_fine_adjust.isChecked()
            self.average_count=int(self.line_edit_average_count.text().strip())
            self.save_result_img=self.line_edit_save_result_image.isChecked()
            self.save_roi=mlcm.pyCVRect(-1,-1,-1,-1)
            self.image_save_path=""
            if self.save_result_img:
                save_roi_text=self.line_edit_save_roi.text().strip().split()
                if len(save_roi_text)!=4:
                    QMessageBox.warning(self,"MLColorimeter","请正确填写roi参数，格式：x y width height",QMessageBox.Ok)
                    return
                save_roi_text=[int(value) for value in save_roi_text]
                self.save_roi=mlcm.pyCVRect(save_roi_text[0],save_roi_text[1],save_roi_text[2],save_roi_text[3])
                self.image_save_path=self.line_edit_image_save_path.text().strip()
                if not self.image_save_path:
                    QMessageBox.warning(self,"MLColorimeter","请选择图片保存路径",QMessageBox.Ok)
                    return
            self.freq_list=[float(freq) for freq in self.line_edit_freq_list.text().strip().split()]
            if not self.freq_list:
                QMessageBox.critical(self,"MLColorimeter","请填写频率列表",QMessageBox.Yes | QMessageBox.No,QMessageBox.Yes)
                return
            if not self.roi_list:
                QMessageBox.critical(self,"MLColorimeter","请添加roi",QMessageBox.Yes | QMessageBox.No,QMessageBox.Yes)
                return
            self.out_path=self.line_edit_path.text().strip()
            if not self.out_path:
                QMessageBox.critical(self,"MLColorimeter","请选择保存路径",QMessageBox.Yes | QMessageBox.No,QMessageBox.Yes)
                return
            
            # ========== 生成本次运行的时间戳，用于日志文件 ==========
            run_ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S.%f')[:-3]
            self.log_file_path = os.path.join(self.out_path, f"{run_ts}_field_curve_log.txt")
            
            self.focus_config=mlcm.pyFocusScanConfig_(
                focus_max=self.focus_max,
                focus_min=self.focus_min,
                inf_position=self.inf_pos,
                focal_length=self.focal_length,
                pixel_size=self.pixel_size,
                focal_space=self.focal_space,
                coarse_step=self.coarse_step,
                use_fine_adjust=self.use_fine_adjust,
                fine_step=self.fine_step,
                roi_list=self.roi_list,
                use_checkboard=self.use_chess_mode,
                use_lpmm_unit=self.use_lpmm_unit,
                save_result_img=self.save_result_img,
                save_roi=self.save_roi,
                image_save_path=self.image_save_path,
                average_count=self.average_count
                
            )
            
            self.btn_capture.setEnabled(False)
            self.is_running=True
            parameters={
                'colorimeter': self.colorimeter,
                'exposure':self.exposure,
                'out_path':self.out_path,
                'focus_config':self.focus_config,
                'freq_list':self.freq_list,
                'binn_selector': self.binn_selector,
                'binn_mode': self.binn_mode,
                'binn': self.binn,
                'pixel_format': self.pixel_format,
            }

            self.filed_curve_thread=FiledCurveThread(parameters)
            self.filed_curve_thread.finished.connect(self.on_filed_curve_finished)
            self.filed_curve_thread.error.connect(self.on_filed_curve_error)
            self.filed_curve_thread.status_update.connect(self.flush_log)
            self.filed_curve_thread.start()

        except Exception as e:
            QMessageBox.critical(self,"MLColorimeter","exception" + str(e), QMessageBox.Yes | QMessageBox.No,QMessageBox.Yes)
            self.btn_capture.setEnabled(True)
            self.is_running=False

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

    def on_filed_curve_finished(self):
        QMessageBox.information(self,"MLColorimeter","拍图完成!",QMessageBox.Ok)
        self.btn_capture.setEnabled(True)
        self.is_running=False # 标识定标完成

    def on_filed_curve_error(self,error_message):
        QMessageBox.critical(self, "MLColorimeter", "发生错误: " + error_message, QMessageBox.Ok)
        self.btn_capture.setEnabled(True)
        self.is_running=False # 标识定标完成

    def closeEvent(self, event):
        if self.is_running:
            # 如果正在进行定标，拦截关闭事件
            event.ignore()
            QMessageBox.warning(self,"警告","程序运行中，请勿关闭窗口",QMessageBox.Ok)
        else:
            #==============关闭窗口保存当前UI参数====================
            p=self.read_ui_params()
            self.cfg_helper.save_params(p)
            event.accept()

    def get_current_pixel_format(self):
        # 获取当前选择的项
        selected_format=self.line_edit_pixel_format.currentText()
        # 创建字符串到枚举值的映射
        format_mapping={
            'MLMono8':mlcm.MLPixelFormat.MLMono8,
            'MLMono10':mlcm.MLPixelFormat.MLMono10,
            'MLMono12':mlcm.MLPixelFormat.MLMono12,
            'MLMono16':mlcm.MLPixelFormat.MLMono16,
            'MLRGB24':mlcm.MLPixelFormat.MLRGB24,
            'MLBayer':mlcm.MLPixelFormat.MLBayer,
            'MLBayerGB8':mlcm.MLPixelFormat.MLBayerGB8,
            'MLBayerGB12':mlcm.MLPixelFormat.MLBayerGB12,
        }
        # 获取对应的枚举值
        pixel_format_enum=format_mapping.get(selected_format)
        return pixel_format_enum
    
    def get_current_exposure_mode(self):
        # 获取当前选择的项
        selected_mode=self.line_edit_exposure_mode.currentText()
        if selected_mode=='Auto':
            return mlcm.ExposureMode.Auto
        else:
            return mlcm.ExposureMode.Fixed
    
    def get_current_binning_selector(self):
        # 获取当前选择的项
        selected_selector=self.line_edit_binn_selector.currentText()
        if selected_selector=='Logic':
            return mlcm.BinningSelector.Logic
        else:
            return mlcm.BinningSelector.Sensor
        
    def get_current_binning_mode(self):
        # 获取当前选择的项
        selected_mode=self.line_edit_binn_mode.currentText()
        if selected_mode=='AVERAGE':
            return mlcm.BinningMode.AVERAGE
        else:
            return mlcm.BinningMode.SUM
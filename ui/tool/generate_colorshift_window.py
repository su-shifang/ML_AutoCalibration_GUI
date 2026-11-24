from PyQt5.QtWidgets import (
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QSizePolicy,
    QMessageBox,
    QGridLayout,
    QSpacerItem,
    QDialog,
)
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QIcon
from core.app_config import AppConfig
from PyQt5.QtCore import pyqtSignal, Qt
import os
import configparser
import json
import itertools
import pandas as pd
import win32com.client
import pythoncom
import ctypes


class GenerateColorShift(QDialog):
    path_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("generate colorshift")
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
        self._init_ui()
        self.is_running = False
        self.temp = False

    def _init_ui(self):
        grid_layout = QGridLayout()
        self.label_path = QLabel()
        self.label_path.setText("EYE1路径:")
        grid_layout.addWidget(self.label_path, 0, 0)

        self.line_edit_path = QLineEdit()
        self.line_edit_path.setReadOnly(True)  # 设置为只读
        self.line_edit_path.setPlaceholderText("例如：F:/config/EYE1")
        self.line_edit_path.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_path, 1, 0)

        self.btn_browse = QPushButton("浏览...")
        self.btn_browse.clicked.connect(self._open_folder_dialog)
        grid_layout.addWidget(self.btn_browse, 1, 1)

        self.out_path = QLabel()
        self.out_path.setText("表格保存路径:")
        grid_layout.addWidget(self.out_path, 2, 0)

        self.line_edit_out_path = QLineEdit()
        self.line_edit_out_path.setReadOnly(True)  # 设置为只读
        self.line_edit_out_path.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid_layout.addWidget(self.line_edit_out_path, 3, 0)

        self.btn_out = QPushButton("浏览...")
        self.btn_out.clicked.connect(self._open_folder_out)
        grid_layout.addWidget(self.btn_out, 3, 1)

        self.label_filename = QLabel()
        self.label_filename.setText("文件名:")
        grid_layout.addWidget(self.label_filename, 4, 0)

        self.line_edit_filename = QLineEdit()
        self.line_edit_filename.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.line_edit_filename.setText("colorshift")
        grid_layout.addWidget(self.line_edit_filename, 5, 0)

        self.label_aperature = QLabel()
        self.label_aperature.setText("Aperture:(多个输入以空格分隔，例如3mm 4mm)")
        grid_layout.addWidget(self.label_aperature, 6, 0)

        self.line_edit_aperature = QLineEdit()
        self.line_edit_aperature.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.line_edit_aperature.setText("3mm 4mm")
        grid_layout.addWidget(self.line_edit_aperature, 7, 0)

        self.label_nd = QLabel()
        self.label_nd.setText("NDFilter:(多个输入以空格分隔，例如ND0 ND1 ND2)")
        grid_layout.addWidget(self.label_nd, 8, 0)

        self.line_edit_nd = QLineEdit()
        self.line_edit_nd.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.line_edit_nd.setText("ND0 ND1")
        grid_layout.addWidget(self.line_edit_nd, 9, 0)

        self.label_xyz = QLabel()
        self.label_xyz.setText("ColorFilter:(多个输入以空格分隔，例如X Y Z)")
        grid_layout.addWidget(self.label_xyz, 10, 0)

        self.line_edit_xyz = QLineEdit()
        self.line_edit_xyz.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.line_edit_xyz.setText("X Y Z")
        grid_layout.addWidget(self.line_edit_xyz, 11, 0)

        self.btn_write = QPushButton("写入")
        self.btn_write.clicked.connect(self.start_write)
        grid_layout.addWidget(self.btn_write, 12, 0)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum,
                             QSizePolicy.Expanding)
        grid_layout.addItem(spacer)

        self.setLayout(grid_layout)

    def start_write(self):
        self.file_name = self.output_path = self.json_path = ""
        self.eye1_path = self.line_edit_path.text()
        self.get_colorshift_folder_rule(self.eye1_path)
        if not self.temp:
            return
        self.output_path = self.line_edit_out_path.text()
        if not self.output_path:
            QMessageBox.critical(self, "MLColorimeter",
                                 "请选择表格保存路径", QMessageBox.Yes)
            return
        self.file_name = self.line_edit_filename.text()
        self.colorshift_path = self.eye1_path+"/ColorShift"
        os.makedirs(self.colorshift_path, exist_ok=True)
        self.aperture = self.line_edit_aperature.text().split()
        self.nd = self.line_edit_nd.text().split()
        self.xyz = self.line_edit_xyz.text().split()
        self.mapping = {
            "Aperture": self.aperture,
            "NDFilter": self.nd,
            "ColorFilter": self.xyz
        }

        self.lists_to_combine = []

        if self.folder_rule:
            rules = self.folder_rule.split("_")
            for rule in rules:
                if rule in self.mapping:
                    self.lists_to_combine.append(self.mapping[rule])
                else:
                    QMessageBox.critical(self, "MLColorimeter", f"Folder_Rule格式不符合规定: {self.folder_rule}",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                    return
        if self.lists_to_combine:
            self.combinations = list(itertools.product(*self.lists_to_combine))
        else:
            self.combinations = [()]
            return
        self.result = ["_".join(item) for item in self.combinations] # type: ignore

        self.save_path = os.path.join(self.output_path, self.file_name+".xlsx")

        df = pd.DataFrame({
            'Rule': self.result,
            'x': ['']*len(self.result), # type: ignore
            'y': ['']*len(self.result) # type: ignore
        })
        df.set_index('Rule', inplace=True)
        df.to_excel(self.save_path)
        # os.startfile(self.save_path)
        self.open_excel_and_wait(self.save_path)

        # 将表格中的数据写入配置文件中
        df = pd.read_excel(self.save_path, header=0)

        for index, row in df.iterrows():
            file_name = row['Rule']
            if self.validate_coordinates(row, index) == False:
                return
            data = {
                "ColorShift": [
                    [
                        int(row['x']),
                        int(row['y'])
                    ]
                ]
            }
            out_path = os.path.join(self.colorshift_path, file_name)
            os.makedirs(out_path, exist_ok=True)
            json_path = os.path.join(out_path, "ColorShift.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        QMessageBox.information(self, "MLColorimeter",
                                "写入配置完成，请查看配置文件", QMessageBox.Yes)

    def validate_coordinates(self, row, index):
        file_name = row['Rule']
        if 'x' not in row or 'y' not in row:
            QMessageBox.critical(
                self, "MLColorimeter", f"第{index}行，缺少x或y列。Rule：{file_name}", QMessageBox.Yes)
            return False
        if pd.isna(row['x']) or pd.isna(row['y']):
            QMessageBox.critical(
                self, "MLColorimeter", f"第{index}行，x或y值为空。Rule：{file_name}", QMessageBox.Yes)
            return False
        return True

    def open_excel_and_wait(self, file_path):
        pythoncom.CoInitialize()  # 初始化COM环境
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = True
        workbook = excel.Workbooks.Open(file_path)

        # 2. 显示友好提示
        filename = os.path.basename(file_path)
        response = ctypes.windll.user32.MessageBoxW(
            0,
            f"文件 '{filename}' 已打开\n\n"
            "请在Excel中编辑并保存，然后：\n"
            "• 关闭文件\n"
            "• 点击'确定'继续程序\n\n"
            "注意：表格需要填完整",
            "编辑提示",
            0x40 | 0x1  # 信息图标 + 确定按钮
        )

        # 释放COM对象
        del workbook
        del excel

    def get_colorshift_folder_rule(self, config_path):
        self.ini_path = config_path+"/"+"config.ini"
        if not os.path.exists(self.ini_path):
            QMessageBox.critical(self, "MLColorimeter", "config.ini文件不存在，请检查eye1路径下的文件",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            self.temp = False
            return

        config = configparser.ConfigParser()
        try:
            config.read(self.ini_path, encoding='utf-8')

            if 'ColorShift' in config:
                self.folder_rule = config['ColorShift'].get(
                    'Folder_Rule', '').strip()
                self.suffix = config['ColorShift'].get('Suffix', '').strip()
                self.temp = True
            else:
                QMessageBox.critical(self, "MLColorimeter", "config.ini文件中缺少ColorShift部分，请检查eye1路径下的文件",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                self.temp = False
                return
        except Exception as e:
            QMessageBox.critical(self, "MLColorimeter", f"读取config.ini文件失败: {str(e)}",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            self.temp = False
            return

    def _open_folder_dialog(self):
        # 打开文件夹选择对话框
        folder_path = QFileDialog.getExistingDirectory(
            self,
            self.dialog_title,
            self.default_path if self.default_path else "",  # 初始路径
            options=QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks, # type: ignore
        )

        if folder_path:
            self.eye1_path = folder_path
            self.line_edit_path.setText(folder_path)
        else:
            QMessageBox.critical(self, "MLColorimeter", "选择路径错误",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

    def _open_folder_out(self):
        # 打开文件夹选择对话框
        folder_path = QFileDialog.getExistingDirectory(
            self,
            self.dialog_title,
            self.default_path if self.default_path else "",  # 初始路径
            options=QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks, # type: ignore
        )

        if folder_path:
            self.line_edit_out_path.setText(folder_path)
        else:
            QMessageBox.critical(self, "MLColorimeter", "选择路径错误",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

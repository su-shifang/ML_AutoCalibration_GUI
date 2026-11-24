from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QSizePolicy,
    QMessageBox,
    QCheckBox,
    QGridLayout,
    QSpacerItem,
    QDialog,
    QWidget,
    QVBoxLayout,
    QTextEdit
)
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QIcon
from core.app_config import AppConfig
from PyQt5.QtCore import pyqtSignal, Qt, QThread
from scripts.config_detection import config_detection
import json
from ui.dialog.ruleeditor_dialog import RuleEditorDialog


class ConfigDetectionThread(QThread):
    finished = pyqtSignal()  # 线程完成信号
    error = pyqtSignal(str)  # 错误信号
    status_update = pyqtSignal(str)  # 状态更新信号

    def __init__(self, parameters):
        super().__init__()
        self.parameters = parameters

    def run(self):
        try:
            cb = self.status_update.emit
            print(f"[DEBUG] cb is None? {cb is None}")
            config_detection(**self.parameters,
                             status_callback=self.status_update.emit)  # type: ignore
            self.finished.emit()  # 发送完成信号
        except Exception as e:
            self.error.emit(str(e))  # 发送错误信号


# class ConfigDetectionWindow(QDialog):
#     path_changed = pyqtSignal(str)

#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("config detection")
#         self.setGeometry(200, 200, 800, 500)
#         self.colorimeter = AppConfig.get_colorimeter()
#         self.setWindowFlags(Qt.Window | Qt.WindowMaximizeButtonHint |
#                             Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint) # type: ignore
#         self.setWindowIcon(QIcon(
#             "D:/pythonObject/ML_AutoCalibration_GUI/ML_AutoCalibration_GUI/FingerPrintScanMTF.ico"))
#         self.intValidator = QIntValidator()
#         self.doubleValidator = QDoubleValidator()
#         self.dialog_title = "选择文件夹"
#         self.default_path = ""
#         self.save_path = ""
#         self._init_ui()
#         self.is_running = False
#         self.temp = False

#     def _init_ui(self):
#         grid_layout = QGridLayout()
#         self.label_path = QLabel()
#         self.label_path.setText("EYE1路径:")
#         grid_layout.addWidget(self.label_path, 0, 0)

#         self.line_edit_path = QLineEdit()
#         self.line_edit_path.setReadOnly(True)  # 设置为只读
#         self.line_edit_path.setPlaceholderText("例如：F:/config/EYE1")
#         self.line_edit_path.setSizePolicy(
#             QSizePolicy.Expanding, QSizePolicy.Fixed)
#         grid_layout.addWidget(self.line_edit_path, 0, 1)

#         self.btn_browse = QPushButton("浏览...")
#         self.btn_browse.clicked.connect(self._open_folder_dialog)
#         grid_layout.addWidget(self.btn_browse, 0, 2)

#         self.output_path = QLabel()
#         self.output_path.setText("输出路径:")
#         grid_layout.addWidget(self.output_path, 1, 0)

#         self.line_output_path = QLineEdit()
#         self.line_output_path.setReadOnly(True)  # 设置为只读
#         self.line_output_path.setPlaceholderText("选择文件夹")
#         self.line_output_path.setSizePolicy(
#             QSizePolicy.Expanding, QSizePolicy.Fixed)
#         grid_layout.addWidget(self.line_output_path, 1, 1)

#         self.btn_output = QPushButton("浏览...")
#         self.btn_output.clicked.connect(self._open_folder_dialog1)
#         grid_layout.addWidget(self.btn_output, 1, 2)

#         self.label_file_name = QLabel()
#         self.label_file_name.setText("保存文件名:")
#         grid_layout.addWidget(self.label_file_name, 2, 0)

#         self.line_edit_file_name = QLineEdit()
#         self.line_edit_file_name.setSizePolicy(
#             QSizePolicy.Expanding, QSizePolicy.Fixed)
#         self.line_edit_file_name.setText("moduleName")
#         grid_layout.addWidget(self.line_edit_file_name, 2, 1)

#         self.label_detect_folder = QLabel("选择检测项: ")
#         grid_layout.addWidget(self.label_detect_folder, 3, 0)

#         checkbox_layout = QHBoxLayout()

#         self.checkbox_dark = QCheckBox("Dark")
#         self.checkbox_dark.setChecked(True)
#         self.checkbox_dark.setEnabled(False)
#         self.checkbox_colorshift = QCheckBox("ColorShift")
#         self.checkbox_colorshift.setChecked(True)

#         self.checkbox_luminance = QCheckBox("Luminance")
#         self.checkbox_luminance.setChecked(True)
#         self.checkbox_radiance = QCheckBox("Radiance")
#         self.checkbox_radiance.setChecked(True)
#         self.checkbox_offset = QCheckBox("Offset")
#         self.checkbox_offset.setChecked(True)
#         self.checkbox_darklist = QCheckBox("DarkList")
#         self.checkbox_darklist.setChecked(True)
#         self.checkbox_ffc = QCheckBox("FFC")
#         self.checkbox_ffc.setChecked(True)
#         self.checkbox_distortion = QCheckBox("Distortion")
#         self.checkbox_distortion.setChecked(True)
#         checkbox_layout.addWidget(self.checkbox_dark)
#         checkbox_layout.addWidget(self.checkbox_distortion)
#         checkbox_layout.addWidget(self.checkbox_colorshift)
#         checkbox_layout.addWidget(self.checkbox_luminance)
#         checkbox_layout.addWidget(self.checkbox_radiance)
#         checkbox_layout.addWidget(self.checkbox_offset)
#         checkbox_layout.addWidget(self.checkbox_darklist)
#         checkbox_layout.addWidget(self.checkbox_ffc)
#         grid_layout.addLayout(checkbox_layout, 3, 1, 1, 8)

#         self.btn_write = QPushButton("开始检测")
#         self.btn_write.clicked.connect(self.start_detect)
#         grid_layout.addWidget(self.btn_write, 4, 0)

#         self.status_label = QLabel("状态：等待开始")
#         self.status_label.setWordWrap(True)  # 设置自动换行
#         grid_layout.addWidget(self.status_label, 4, 1)

#         spacer = QSpacerItem(20, 40, QSizePolicy.Minimum,
#                              QSizePolicy.Expanding)
#         grid_layout.addItem(spacer)

#         self.setLayout(grid_layout)

#     def start_detect(self):
#         try:
#             self.eye1_path = self.line_edit_path.text()
#             self.output_path = self.line_output_path.text()
#             self.file_name = self.line_edit_file_name.text()
#             if not self.eye1_path or not self.output_path or not self.file_name:
#                 QMessageBox.critical(self, "MLColorimeter", "请确保所有路径和文件名都已填写",
#                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
#                 return

#             self.select_folders = ['Dark']
#             if self.checkbox_colorshift.isChecked():
#                 self.select_folders.append("ColorShift")
#             if self.checkbox_luminance.isChecked():
#                 self.select_folders.append("Luminance")
#             if self.checkbox_radiance.isChecked():
#                 self.select_folders.append("Radiance")
#             if self.checkbox_offset.isChecked():
#                 self.select_folders.append("Offset")
#             if self.checkbox_distortion.isChecked():
#                 self.select_folders.append("Distortion")
#             if self.checkbox_darklist.isChecked():
#                 self.select_folders.append("DarkList")
#             if self.checkbox_ffc.isChecked():
#                 self.select_folders.append("FFC")

#             config_detection(
#                 eye1_path=self.eye1_path,
#                 out_path=self.output_path,
#                 file_name=self.file_name,
#                 folder_name=self.select_folders)
#             self.status_label.setText(
#                 "<span style='color: green;'>状态: 正在进行检测...</span>")  # 更新状态
#             self.btn_write.setEnabled(False)
#             self.is_running = True
#             parameters = {
#                 'eye1_path': self.eye1_path,
#                 'out_path': self.output_path,
#                 'file_name': self.file_name,
#                 'folder_name': self.select_folders
#             }
#             self.config_detection_thread = ConfigDetectionThread(parameters)
#             self.config_detection_thread.finished.connect(
#                 self.on_thread_finished)
#             self.config_detection_thread.error.connect(self.on_thread_error)
#             self.config_detection_thread.status_update.connect(
#                 self.update_status)
#             self.config_detection_thread.start()

#         except Exception as e:
#             QMessageBox.critical(self, "MLColorimeter", "exception" +
#                                  str(e), QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
#             self.btn_write.setEnabled(True)
#             self.is_running = False

#     def update_status(self, message):
#         self.status_label.setText(
#             f"<span style='color: green;'>检测: {message}</span>")

#     def on_thread_finished(self):
#         QMessageBox.information(self, "MLColorimeter", "检测完成!", QMessageBox.Ok)
#         self.status_label.setText(
#             "<span style='color: green;'>状态: 检测完成！</span>")  # 更新状态
#         self.btn_write.setEnabled(True)
#         self.is_running = False

#     def on_thread_error(self, error_message):
#         QMessageBox.critical(self, "MLColorimeter",
#                              "发生错误: " + error_message, QMessageBox.Ok)
#         self.status_label.setText(
#             f"<span style='color: red;'>状态: 发生错误: {error_message}</span>")  # 更新状态为红色
#         self.btn_write.setEnabled(True)
#         self.is_running = False

#     def closeEvent(self, event):
#         if self.is_running:
#             event.ignore()
#             QMessageBox.warning(self, "警告", "程序运行中，请勿关闭窗口", QMessageBox.Ok)
#         else:
#             event.accept()

#     def _open_folder_dialog(self):
#         # 打开文件夹选择对话框
#         folder_path = QFileDialog.getExistingDirectory(
#             self,
#             self.dialog_title,
#             self.default_path if self.default_path else "",  # 初始路径
#             options=QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks, # type: ignore
#         )

#         if folder_path:
#             self.line_edit_path.setText(folder_path)
#         else:
#             QMessageBox.critical(self, "MLColorimeter", "选择路径错误",
#                                  QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

#     def _open_folder_dialog1(self):
#         # 打开文件夹选择对话框
#         folder_path = QFileDialog.getExistingDirectory(
#             self,
#             self.dialog_title,
#             self.default_path if self.default_path else "",  # 初始路径
#             options=QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks, # type: ignore
#         )

#         if folder_path:
#             self.line_output_path.setText(folder_path)
#         else:
#             QMessageBox.critical(self, "MLColorimeter", "选择路径错误",
#                                  QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)


# 主窗口UI
class ConfigDetectionWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("config detection")
        self.setGeometry(200, 200, 800, 500)
        self.colorimeter = AppConfig.get_colorimeter()
        self.setWindowFlags(Qt.Window | Qt.WindowMaximizeButtonHint |
                            Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)  # type: ignore
        self.setWindowIcon(QIcon(
            "D:/pythonObject/ML_AutoCalibration_GUI/ML_AutoCalibration_GUI/FingerPrintScanMTF.ico"))
        self.intValidator = QIntValidator()
        self.doubleValidator = QDoubleValidator()
        self.dialog_title = "选择文件夹"
        self.default_path = ""
        self.save_path = ""
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # EYE1目录选择
        lay1 = QHBoxLayout()
        lay1.addWidget(QLabel("EYE1根目录："))
        self.edt_eye1 = QLineEdit()
        lay1.addWidget(self.edt_eye1)
        btn_eye1 = QPushButton("选择文件夹")
        btn_eye1.clicked.connect(self.select_eye1)
        lay1.addWidget(btn_eye1)
        layout.addLayout(lay1)

        # 输出目录
        lay2 = QHBoxLayout()
        lay2.addWidget(QLabel("Excel输出目录："))
        self.edt_out = QLineEdit()
        lay2.addWidget(self.edt_out)
        btn_out = QPushButton("选择文件夹")
        btn_out.clicked.connect(self.select_out)
        lay2.addWidget(btn_out)
        layout.addLayout(lay2)

        # 输出文件名输入框
        lay3 = QHBoxLayout()
        lay3.addWidget(QLabel("输出Excel文件名："))
        self.edt_filename = QLineEdit()
        self.edt_filename.setText("M26538S2604003B003_config")
        lay3.addWidget(self.edt_filename)
        layout.addLayout(lay3)

        # RuleMap JSON 配置文件按钮行
        layout.addWidget(QLabel("关键字映射 rule_map（从JSON配置文件加载，预览只读）:"))
        btn_json_layout = QHBoxLayout()
        # 新增：打开独立编辑器弹窗按钮
        self.btn_open_editor = QPushButton("打开模块规则编辑器")
        self.btn_load_json = QPushButton("加载JSON配置文件")
        self.btn_save_json = QPushButton("保存JSON配置文件")
        self.btn_validate_json = QPushButton("校验JSON语法")
        btn_json_layout.addWidget(self.btn_open_editor)
        btn_json_layout.addWidget(self.btn_load_json)
        btn_json_layout.addWidget(self.btn_save_json)
        btn_json_layout.addWidget(self.btn_validate_json)
        btn_json_layout.addStretch(1)
        layout.addLayout(btn_json_layout)

        self.txt_rule_map = QTextEdit()
        # 默认空白，需要手动加载json
        self.txt_rule_map.setReadOnly(True)
        self.txt_rule_map.setMaximumHeight(200)
        layout.addWidget(self.txt_rule_map)

        # 内存存储模块规则
        self.section_rule_dict = {}
        # 绑定弹窗按钮事件
        self.btn_open_editor.clicked.connect(self.open_rule_editor_dialog)

        # 绑定按钮事件
        self.btn_load_json.clicked.connect(self.load_rule_json)
        self.btn_save_json.clicked.connect(self.save_rule_json)
        self.btn_validate_json.clicked.connect(self.check_json_syntax)

        # 开始按钮
        self.btn_start = QPushButton("开始扫描校验并生成Excel")
        self.btn_start.clicked.connect(self.start_scan)
        layout.addWidget(self.btn_start)

        # 日志框
        layout.addWidget(QLabel("运行日志："))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

    def select_eye1(self):
        p = QFileDialog.getExistingDirectory(self, "选择EYE1文件夹")
        if p:
            self.edt_eye1.setText(p)

    def select_out(self):
        p = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if p:
            self.edt_out.setText(p)

    # 加载外部rule_map json文件
    def load_rule_json(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "加载rule_map json", "", "JSON文件(*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 自动格式化显示
            formatted = json.dumps(data, indent=4, ensure_ascii=False)
            self.txt_rule_map.setPlainText(formatted)
            QMessageBox.information(self, "加载成功", f"✅ 配置文件加载完成：\n{path}")
        except json.JSONDecodeError as err:
            QMessageBox.critical(
                self, "JSON语法错误", f"❌ 文件解析失败\n行{err.lineno}, 列{err.colno}\n{err.msg}")
        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"❌ {str(e)}")

    # 保存当前预览内容到json文件
    def save_rule_json(self):
        text = self.txt_rule_map.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "警告", "当前预览框为空，无法保存！")
            return
        try:
            data = json.loads(text)
        except json.JSONDecodeError as err:
            QMessageBox.critical(
                self, "JSON语法错误", f"❌ 语法错误，不能保存\n行{err.lineno}, 列{err.colno}\n{err.msg}")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存rule_map json", "rule_map.json", "JSON文件(*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "保存成功", f"✅ 配置已保存到：\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"❌ {str(e)}")

    # 校验JSON语法
    def check_json_syntax(self):
        text = self.txt_rule_map.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "提示", "预览框为空，请先加载JSON文件！")
            return
        try:
            json.loads(text)
            QMessageBox.information(self, "校验成功", "✅ JSON语法正确！")
        except json.JSONDecodeError as err:
            QMessageBox.critical(
                self, "JSON语法错误", f"❌ JSON解析失败\n位置：行{err.lineno}, 列{err.colno}\n详情：{err.msg}")

    def preview_generated_json(self):
        """把内存模块规则生成JSON，填充到上方txt_rule_map预览框"""
        if not self.section_rule_dict:
            self.txt_rule_map.setPlainText("")
            return
        json_str = json.dumps(self.section_rule_dict,
                              indent=4, ensure_ascii=False)
        self.txt_rule_map.setPlainText(json_str)

    def open_rule_editor_dialog(self):
        # 打开独立弹窗编辑器，直接引用当前的规则字典
        dlg = RuleEditorDialog(self, self.section_rule_dict)
        dlg.exec_()
        # 弹窗关闭后，自动刷新预览框
        self.preview_generated_json()

    def start_scan(self):
        eye1 = self.edt_eye1.text().strip()
        outp = self.edt_out.text().strip()
        filename = self.edt_filename.text().strip()
        if not eye1 or not outp:
            self.log_text.append("⚠️ 请先选择EYE1目录和输出目录！")
            return
        if not filename:
            self.log_text.append("⚠️ 输出文件名不能为空！")
            return
        rule_text = self.txt_rule_map.toPlainText()
        if not rule_text.strip():
            self.log_text.append("⚠️ 请先加载 rule_map JSON配置文件！")
            return
        # 解析rule map JSON
        try:
            rule_map = json.loads(rule_text)
            if not isinstance(rule_map, dict):
                raise ValueError("JSON根节点必须是对象{}")
        except json.JSONDecodeError as e:
            QMessageBox.critical(
                self, "JSON解析失败", f"rule_map JSON语法错误：\n行{e.lineno} 列{e.colno}\n{e.msg}")
            return
        except Exception as e:
            QMessageBox.critical(
                self, "JSON解析失败", f"rule_map JSON格式错误：\n{str(e)}")
            return
        self.btn_start.setEnabled(False)

        parameters = {
            'eye1_path': eye1,
            'out_path': outp,
            'rule_map': rule_map,
            'out_filename': filename
        }
        self.log_text.append("===== 开始扫描 =====")

        self.thread = ConfigDetectionThread(parameters)
        self.thread.finished.connect(self.on_finish)
        self.thread.error.connect(self.on_error)
        self.thread.status_update.connect(self.on_log)
        self.thread.start()

    def on_log(self, msg):
        self.log_text.append(msg)
        # 自动滚动到最新一行
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)

    def on_finish(self):
        self.btn_start.setEnabled(True)
        self.log_text.append(f"✅ 检测完成!")

    def on_error(self, error_message):
        self.btn_start.setEnabled(True)
        self.log_text.append(f"❌ 扫描失败！{error_message}")

    def closeEvent(self, event):
        if hasattr(self, "thread") and self.thread.isRunning():
            QMessageBox.warning(self, "警告", "扫描任务正在运行，无法关闭窗口！")
            event.ignore()
        else:
            event.accept()

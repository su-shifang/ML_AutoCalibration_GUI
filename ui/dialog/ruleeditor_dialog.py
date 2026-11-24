from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QListWidget, QListWidgetItem, QAbstractItemView,
                             QPushButton, QLineEdit, QLabel, QMessageBox, QDialog)

from typing import List
# ==================== 独立弹窗：模块规则编辑器 ====================


class RuleEditorDialog(QDialog):
    def __init__(self, parent, rule_dict: dict):
        super().__init__(parent)
        self.setWindowTitle("模块规则编辑器")
        self.resize(750, 650)
        self.section_rule_dict = rule_dict  # 引用主窗口的规则字典，双向同步
        w = QWidget()
        lay = QVBoxLayout(w)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(w)

        # 模块名下拉
        comb_layout = QHBoxLayout()
        comb_layout.addWidget(QLabel("模块名(Section)【单选下拉】:"))
        self.cb_section = QComboBox()
        self.cb_section.setEditable(True)
        comb_layout.addWidget(self.cb_section)
        lay.addLayout(comb_layout)

        # Aperture
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Aperture【多选】"))
        self.lw_aperture = QListWidget()
        self.lw_aperture.setSelectionMode(QAbstractItemView.MultiSelection)
        self.lw_aperture.addItems(["2mm", "3mm", "4mm", "2.65mm"])
        row1.addWidget(self.lw_aperture)
        self.edt_ap = QLineEdit()
        self.edt_ap.setPlaceholderText("自定义选项，如5mm")
        self.btn_add_ap = QPushButton("+")
        self.btn_add_ap.clicked.connect(
            lambda: self.add_item_to_list(self.lw_aperture, self.edt_ap))
        row1.addWidget(self.edt_ap)
        row1.addWidget(self.btn_add_ap)
        lay.addLayout(row1)

        # NDFilter
        row1b = QHBoxLayout()
        row1b.addWidget(QLabel("NDFilter【多选】"))
        self.lw_ndfilter = QListWidget()
        self.lw_ndfilter.setSelectionMode(QAbstractItemView.MultiSelection)
        self.lw_ndfilter.addItems(["ND0", "ND1", "ND2", "ND3", "ND4"])
        row1b.addWidget(self.lw_ndfilter)
        self.edt_nd = QLineEdit()
        self.edt_nd.setPlaceholderText("自定义，如ND5")
        self.btn_add_nd = QPushButton("+")
        self.btn_add_nd.clicked.connect(
            lambda: self.add_item_to_list(self.lw_ndfilter, self.edt_nd))
        row1b.addWidget(self.edt_nd)
        row1b.addWidget(self.btn_add_nd)
        lay.addLayout(row1b)

        # ColorFilter
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("ColorFilter【多选】"))
        self.lw_colorfilter = QListWidget()
        self.lw_colorfilter.setSelectionMode(QAbstractItemView.MultiSelection)
        self.lw_colorfilter.addItems(["X", "Y", "Z", "Clear", "YA"])
        row2.addWidget(self.lw_colorfilter)
        self.edt_cf = QLineEdit()
        self.edt_cf.setPlaceholderText("自定义，如YB")
        self.btn_add_cf = QPushButton("+")
        self.btn_add_cf.clicked.connect(
            lambda: self.add_item_to_list(self.lw_colorfilter, self.edt_cf))
        row2.addWidget(self.edt_cf)
        row2.addWidget(self.btn_add_cf)
        lay.addLayout(row2)

        # LightSource
        row2b = QHBoxLayout()
        row2b.addWidget(QLabel("LightSource【多选】"))
        self.lw_lightsource = QListWidget()
        self.lw_lightsource.setSelectionMode(QAbstractItemView.MultiSelection)
        self.lw_lightsource.addItems(["R", "G", "B", "W"])
        row2b.addWidget(self.lw_lightsource)
        self.edt_ls = QLineEdit()
        self.edt_ls.setPlaceholderText("自定义，如IR")
        self.btn_add_ls = QPushButton("+")
        self.btn_add_ls.clicked.connect(
            lambda: self.add_item_to_list(self.lw_lightsource, self.edt_ls))
        row2b.addWidget(self.edt_ls)
        row2b.addWidget(self.btn_add_ls)
        lay.addLayout(row2b)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self.btn_add_sec = QPushButton("添加/更新模块")
        self.btn_del_sec = QPushButton("删除模块")
        self.btn_clear_sel = QPushButton("清空选择")
        btn_layout.addWidget(self.btn_add_sec)
        btn_layout.addWidget(self.btn_del_sec)
        btn_layout.addWidget(self.btn_clear_sel)
        btn_layout.addStretch(1)
        lay.addLayout(btn_layout)

        # 底部关闭按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch(1)
        self.btn_close = QPushButton("关闭编辑器")
        bottom_layout.addWidget(self.btn_close)
        lay.addLayout(bottom_layout)

        # 绑定事件
        self.cb_section.currentTextChanged.connect(self.on_section_selected)
        self.btn_add_sec.clicked.connect(self.add_section_rule)
        self.btn_del_sec.clicked.connect(self.delete_section_rule)
        self.btn_clear_sel.clicked.connect(self.clear_editor_selection)
        self.btn_close.clicked.connect(self.accept)

        self.refresh_section_combobox()

    def add_item_to_list(self, list_widget: QListWidget, edit: QLineEdit):
        txt = edit.text().strip()
        if not txt:
            QMessageBox.warning(self, "提示", "输入不能为空！")
            return
        for i in range(list_widget.count()):
            if list_widget.item(i).text() == txt:
                QMessageBox.information(self, "提示", f"{txt} 已存在")
                return
        item = QListWidgetItem(txt)
        list_widget.addItem(item)
        item.setSelected(True)
        edit.clear()

    def refresh_section_combobox(self):
        self.cb_section.blockSignals(True)
        self.cb_section.clear()
        # sec_list = list(self.section_rule_dict.keys())
        sec_list = ["ColorShift", "FFC", "FourColor", "Luminance", "Radiance"]
        # if not sec_list:
        #     sec_list=["ColorShift", "FFC", "FourColor","Luminance","Radiance"]
        self.cb_section.addItems(sec_list)
        self.cb_section.blockSignals(False)

    def on_section_selected(self, sec_name):
        if sec_name not in self.section_rule_dict:
            self.clear_editor_selection()
            return
        rule_data = self.section_rule_dict[sec_name]
        self.set_list_selected(self.lw_aperture, rule_data.get("Aperture", []))
        self.set_list_selected(self.lw_ndfilter, rule_data.get("NDFilter", []))
        self.set_list_selected(self.lw_colorfilter,
                               rule_data.get("ColorFilter", []))
        self.set_list_selected(self.lw_lightsource,
                               rule_data.get("LightSource", []))

    def set_list_selected(self, list_widget: QListWidget, target_list: List[str]):
        list_widget.clearSelection()
        for idx in range(list_widget.count()):
            item = list_widget.item(idx)
            if item.text() in target_list:
                item.setSelected(True)

    def get_list_selected_text(self, list_widget: QListWidget) -> List[str]:
        return [item.text() for item in list_widget.selectedItems()]

    def add_section_rule(self):
        sec_name = self.cb_section.currentText().strip()
        if not sec_name:
            QMessageBox.warning(self, "警告", "请填写模块名！")
            return
        ap = self.get_list_selected_text(self.lw_aperture)
        nd = self.get_list_selected_text(self.lw_ndfilter)
        cf = self.get_list_selected_text(self.lw_colorfilter)
        ls = self.get_list_selected_text(self.lw_lightsource)
        self.section_rule_dict[sec_name] = {
            "Aperture": ap,
            "NDFilter": nd,
            "ColorFilter": cf,
            "LightSource": ls
        }
        self.refresh_section_combobox()
        QMessageBox.information(self, "成功", f"模块【{sec_name}】已更新")

    def delete_section_rule(self):
        sec_name = self.cb_section.currentText().strip()
        if sec_name in self.section_rule_dict:
            del self.section_rule_dict[sec_name]
            self.refresh_section_combobox()
            self.clear_editor_selection()
            QMessageBox.information(self, "成功", f"模块【{sec_name}】已删除")

    def clear_editor_selection(self):
        self.lw_aperture.clearSelection()
        self.lw_ndfilter.clearSelection()
        self.lw_colorfilter.clearSelection()
        self.lw_lightsource.clearSelection()

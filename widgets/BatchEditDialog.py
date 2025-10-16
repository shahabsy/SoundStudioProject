from PyQt5.QtWidgets import QComboBox, QCheckBox, QPushButton, QLabel, QDialog, QSlider, QPlainTextEdit
from core.utils import resource_path
from PyQt5 import uic
import os, sys, re
from PyQt5.QtWidgets import QStyleFactory
class BatchEditDialog(QDialog):
    def __init__(self, current_theme):
        super().__init__()
        self.current_theme = current_theme
        ui_file_light = resource_path("ui/group_edit_dialog.ui")
        ui_file_dark = resource_path("ui/group_edit_dialog_dark.ui")
        if self.current_theme == 'dark':
            ui_path = os.path.abspath(ui_file_dark)
        else:
            ui_path = os.path.abspath(ui_file_light)

        uic.loadUi(ui_path, self)
        self.setWindowTitle("Group Edit Sound Item(s)")

        self.asset_type_combo = self.findChild(QComboBox, "AssetTypeComboBox")
        self.asset_type_combo.addItems(["None","Game Object", "UI Function", "Ambience", "Animation", "Music"])
        if self.current_theme == 'dark':
            self.asset_type_combo.setStyleSheet("""
                                                QComboBox {
                                                background-color: #141414;
                                                color:white;
                                                }
                                                QComboBox::drop-down {
                                                border-left: 1px solid #ccc;
                                                width: 20px;
                                                }
                                                QComboBox QAbstractItemView {
                                                background-color: #282828;
                                                color: white;
                                                selection-background-color: #282828;
                                                selection-color: white;
                                                }
                                                """)
        else:
            self.asset_type_combo.setStyleSheet("""
                                                QComboBox {
                                                background-color: white;
                                                color:black;
                                                }
                                                QComboBox::drop-down {
                                                border-left: 1px solid #ccc;
                                                width: 20px;
                                                }
                                                QComboBox QAbstractItemView {
                                                background-color: white;
                                                color: black;
                                                selection-background-color: #0078d7;
                                                selection-color: white;
                                                }
                                                """)
        self.asset_type_combo.setStyle(QStyleFactory.create("Fusion"))
        
        self.isSingleInstance = self.findChild(QCheckBox, "isSingleInstanceCheckbox")
        self.loop_checkbox = self.findChild(QCheckBox, "isLoppingCheckBox")
        
        self.volume_slider = self.findChild(QSlider, "MainVolumeSlider")
        self.volume_slider.setStyle(QStyleFactory.create("Fusion"))
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(75)
        self.MainVolumeValueLabel = self.findChild(QLabel, "MainVolumeValueLabel")
        self.volume_slider.valueChanged.connect(self.update_volume_value)

        self.fade_in_value = 0.0
        self.fade_out_value = 0.0
        
        self.FadeInPTextEdit = self.findChild(QPlainTextEdit, "FadeInPTextEdit")
        self.FadeOutPTextEdit = self.findChild(QPlainTextEdit, "FadeOutPTextEdit")

        self.FadeInPTextEdit.textChanged.connect(self.on_fade_in_changed)
        self.FadeOutPTextEdit.textChanged.connect(self.on_fade_out_changed)
        
        self.apply_btn = self.findChild(QPushButton, "ApplySettingToSelectedBtn")
        self.apply_btn.clicked.connect(self.accept)
        self.discard_btn = self.findChild(QPushButton, "KeepExistingSettingsBtn")
        self.discard_btn.clicked.connect(self.reject)
    
    def update_volume_value(self, value):
        print(value)
        volume_value = value / 100.0
        self.MainVolumeValueLabel.setText(f"{str(volume_value)}")

    def on_fade_in_changed(self):
        text = self.sanitize_input(self.FadeInPTextEdit)
        try:
            self.fade_in_value = float(text) if text else 0.0
        except ValueError:
            self.fade_in_value = 0.0

    def on_fade_out_changed(self):
        text = self.sanitize_input(self.FadeOutPTextEdit)
        try:
            self.fade_out_value = float(text) if text else 0.0
        except ValueError:
            self.fade_out_value = 0.0

    def sanitize_input(self, editor: QPlainTextEdit) -> str:
        text = editor.toPlainText()
        clean = re.sub(r'[^0-9.]', '', text) # remove all non-digits and accept only float values
        if clean.count('.') > 1:
            first, rest = clean.split('.', 1)
            clean = first + '.' + rest.replace('.', '')
        
        if text != clean:
            cursor = editor.textCursor()
            pos = cursor.position()

            editor.blockSignals(True)
            editor.setPlainText(clean)
            editor.blockSignals(False)

            cursor.setPosition(min(pos, len(clean)))
            editor.setTextCursor(cursor)
        
        return clean
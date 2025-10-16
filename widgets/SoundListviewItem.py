from PyQt5.QtWidgets import QWidget, QLabel, QStyledItemDelegate, QTextBrowser, QComboBox, QCheckBox, QSlider, QPushButton, QFrame, QProgressBar, QLineEdit, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen
from PyQt5 import uic
import os, sys
from PyQt5.QtCore import pyqtSignal, Qt, QEvent
from pydub import AudioSegment
from pydub.playback import play, _play_with_simpleaudio
#from pydub.utils import get_array_type
import numpy as np
from numpy import linspace, interp
#import wave, tempfile, uuid
from core.utils import resource_path
from core.audio_meter import BarMeter
from PyQt5.QtWidgets import QStyleFactory


class SoundListViewItem(QWidget):
    clicked = pyqtSignal(str) # emit project_name and project_path
    
    asset_type_changed = pyqtSignal(str)
    single_instance_toggled = pyqtSignal(bool)
    volume_changed = pyqtSignal(float)
    loop_toggled = pyqtSignal(bool)
    reveal_clicked = pyqtSignal(str)
    play_requested = pyqtSignal(bool)
    repeat_changed = pyqtSignal(bool)
    fade_in_changed = pyqtSignal(float)
    fade_out_changed = pyqtSignal(float)
    error = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self, audio_id, file_path, audio_player, current_theme):
        super().__init__()
        self.current_theme = current_theme
        # load recent project item widget ui file
        if self.current_theme == 'dark':    
            ui_file = resource_path("ui/audio_listview_model_ui_dark.ui")
        else:
            ui_file = resource_path("ui/audio_listview_model_ui.ui")
        #ui_file = os.path.join(os.path.dirname(__file__), "../ui/audio_listview_model_ui.ui")
        ui_path = os.path.abspath(ui_file)
        #print("recent project item widget:", ui_path)
        uic.loadUi(ui_path, self)

        self.audio_id = audio_id
        self.audio_player = audio_player
        self.is_playing = False
        self._peak_left = -60
        self._peak_right = -60
        self.duration_str = ""
        
        self.file_path = os.path.join(file_path)
        self.file_path = os.path.abspath(self.file_path)
        self.sound_file_name = os.path.basename(file_path)
        #print(f"path to reveal in explorer: {self.file_path}, {self.sound_file_name}")

        self.setMouseTracking(True)
        MainFrame = self.findChild(QWidget, "MainFrame")
        
        # Set audio file name to the label and generate waveform
        self.SoundFileNameLabel = self.findChild(QLabel, "audio_listview_filepath")
        self.SoundFileWaveLabel = self.findChild(QLabel, "audio_listview_item_waveform")
        self.audio_listview_FileDuration = self.findChild(QLabel, "audio_listview_fileduration")

        # Reference ComboBoxes here
        self.AssetTypeComboBox = self.findChild(QComboBox, "AssetTypeComboBox")
        self.AssetTypeComboBox.addItems(["None","Game Object", "UI Function", "Ambience", "Animation", "Music"])
        if self.current_theme == 'dark':
            self.AssetTypeComboBox.setStyleSheet("""
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
            self.AssetTypeComboBox.setStyleSheet("""
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
        self.AssetTypeComboBox.setStyle(QStyleFactory.create("Fusion"))
        self.AssetTypeComboBox.currentTextChanged.connect(self.asset_type_changed)

        # Reference Looping CheckBox
        self.isLooping = self.findChild(QCheckBox, "isLoppingCheckBox")
        self.isLooping.stateChanged.connect(self.on_loop_toggled)

        # Reference Single Instance Checkbox
        self.isSingleInstance = self.findChild(QCheckBox, "isSingleInstanceCheckbox")
        self.isSingleInstance.stateChanged.connect(self.on_single_instance_toggled)

        # Reference Volume Slider and its Label Value
        self.MainVolumeValueLabel = self.findChild(QLabel, "MainVolumeValueLabel")
        self.MainVolumeSlider = self.findChild(QSlider, "MainVolumeSlider")
        self.MainVolumeSlider.setStyle(QStyleFactory.create("Fusion"))
        if self.current_theme == 'dark':
            self.MainVolumeSlider.setStyleSheet("""
                                                QSlider::groove:horizonal {
                                                border: 1px solid #141414;
                                                height: 3px;
                                                background: #2b2b2b;
                                                border-radius: 6px;
                                                }
                                                QSlider::handle:horizontal {
                                                background: #4caf50;
                                                border: 1px solid #222;
                                                width: 14px;
                                                height: 14px;
                                                margin: -5px 1;
                                                border-radius: 7px;
                                                }
                                                QSlider::handle:horizontal:hover {
                                                background: #3b99fc;
                                                }
                                                """)
        else:
            self.MainVolumeSlider.setStyleSheet("""
                                                QSlider::groove:horizonal {
                                                border: 1px solid #999999;
                                                height: 3px;
                                                background: #dbdbdb;
                                                border-radius: 6px;
                                                }
                                                QSlider::handle:horizontal {
                                                background: #4caf50;
                                                border: 1px solid #222;
                                                width: 14px;
                                                height: 14px;
                                                margin: -5px 1;
                                                border-radius: 7px;
                                                }
                                                QSlider::handle:horizontal:hover {
                                                background: #66bb6a;
                                                }
                                                """)
        self.MainVolumeSlider.setValue(1)
        self.MainVolumeSlider.setMinimum(0)
        self.MainVolumeSlider.setMaximum(100)
        self.MainVolumeSlider.setValue(75) # defualt volume 1.0 -------------- >> 0.75
        self.normalized_volume = 0.75
        self.MainVolumeValueLabel.setText(str(self.normalized_volume))
        self.MainVolumeSlider.valueChanged.connect(self.on_volume_changed)
        self.on_volume_changed(75)
        self.audio_player.set_volume(self.audio_id, 75)
        

        self.FadeInSlider = self.findChild(QSlider, "FadeInSlider")
        self.FadeInSlider.setValue(0)
        self.FadeInSlider.setMinimum(0)
        self.FadeInSlider.setMaximum(500)
        if self.current_theme == 'dark':
            self.FadeInSlider.setStyleSheet("""
                                        QSlider::groove:horizontal {
                                        border: 1px solid #999999;
                                        height: 20px;
                                        background: #141414;
                                        
                                        }
                                        QSlider::handle:horizontal {
                                        background: transparent;
                                        width: 10px;
                                        }
                                        QSlider::sub-page:horizontal {
                                        background: #3b99fc;
                                        
                                        }
                                        """)
        else:    
            self.FadeInSlider.setStyleSheet("""
                                        QSlider::groove:horizontal {
                                        border: 1px solid #999999;
                                        height: 20px;
                                        background: #e0e0e0;
                                        
                                        }
                                        QSlider::handle:horizontal {
                                        background: transparent;
                                        width: 10px;
                                        }
                                        QSlider::sub-page:horizontal {
                                        background: #3b99fc;
                                        
                                        }
                                        """)
        self.FadeInSlider.valueChanged.connect(self.on_fade_in_changed)
        self.FadeInLabel = self.findChild(QLabel, "FadeInLabel")

        self.FadeOutSlider = self.findChild(QSlider, "FadeOutSlider")
        self.FadeOutSlider.setValue(0)
        self.FadeOutSlider.setMinimum(0)
        self.FadeOutSlider.setMaximum(500)
        if self.current_theme == 'dark':
            self.FadeOutSlider.setStyleSheet("""
                                        QSlider::groove:horizontal {
                                        border: 1px solid #999999;
                                        height: 20px;
                                        background: #141414;
                                        
                                        }
                                        QSlider::handle:horizontal {
                                        background: transparent;
                                        width: 10px;
                                        }
                                        QSlider::sub-page:horizontal {
                                        background: none;
                                        
                                        }
                                        QSlider::add-page:horizontal {
                                         background: #3b99fc;
                                         }
                                         """)
        else:
            self.FadeOutSlider.setStyleSheet("""
                                        QSlider::groove:horizontal {
                                        border: 1px solid #999999;
                                        height: 20px;
                                        background: #e0e0e0;
                                        
                                        }
                                        QSlider::handle:horizontal {
                                        background: transparent;
                                        width: 10px;
                                        }
                                        QSlider::sub-page:horizontal {
                                        background: none;
                                        
                                        }
                                        QSlider::add-page:horizontal {
                                         background: #3b99fc;
                                         }
                                         """)
        self.FadeOutSlider.valueChanged.connect(self.on_fade_out_changed)
        self.FadeOutLabel = self.findChild(QLabel, "FadeOutLabel")

        ##################################################################################
        # here is the individual audio meter bars to use - need to improve its look UI
        self.Left_dB_Text = self.findChild(QLabel, "Left_dB_Text")
        self.Right_dB_Text = self.findChild(QLabel, "Right_dB_Text")
        self.meterL = BarMeter(
            width=240, height=10,
            bg_color=QColor(100,100,100),
            bar_bg=QColor(100,100,100),
            bar_color_start=QColor(0,200,0),
            bar_color_mid=QColor(200,200,0),
            bar_color_end=QColor(200,0,0),
            text_color=QColor(200,200,210),
            min_db=-60.0, max_db=0.0
        )
        self.meterR = BarMeter(
            width=240, height=10,
            bg_color=QColor(100,100,100),
            bar_bg=QColor(100,100,100),
            bar_color_start=QColor(0,200,0),
            bar_color_mid=QColor(200,200,0),
            bar_color_end=QColor(200,0,0),
            text_color=QColor(200,200,210),
            min_db=-60.0, max_db=0.0
        )
        self.SoundMeterFrame = self.findChild(QFrame, "SoundMeterFrame")
        self.meter_layout = self.SoundMeterFrame.layout()
        self.meter_layout.setContentsMargins(0,0,0,0)
        self.meter_layout.addWidget(self.meterL)
        self.meter_layout.addWidget(self.meterR)
        self.audio_player.worker.levels_updated.connect(self.update_meter)
        ##############################################################
        self.audio_player.worker.playback_finished.connect(self.on_playback_stopped)
        self.meterL.peak_level_value.connect(self.set_left_peak_level_value)
        self.meterR.peak_level_value.connect(self.set_right_peak_level_value)

        # Reference Button to locate the item item in explorer
        self.ShowFileInExplorerButton = self.findChild(QPushButton, "ShowFileInExplorerButton")
        self.ShowFileInExplorerButton.clicked.connect(self.reveal_file_location)
        #self.ShowFileInExplorerButton.hide()
        
        # Reference Player and Repeat Buttons of List Item
        self.audio_listview_play_btn = self.findChild(QPushButton, "audio_listview_play_btn")
        self.audio_listview_play_btn.clicked.connect(self.play_sound)

        self.audio_listview_stop_btn = self.findChild(QPushButton, "audio_listview_stop_btn")
        self.audio_listview_stop_btn.clicked.connect(self.stop_sound)
        
        self.audio_listview_repeat_btn = self.findChild(QPushButton, "audio_listview_repeat_btn")
        self.audio_listview_repeat_btn.clicked.connect(self.repeat_toggle)

        self.SoundItemUrlFrame = self.findChild(QFrame, "SoundItemUrlFrame")
        self.SoundItemUrl = self.findChild(QLabel, "SoundItemUrl")
        self.SoundItemUrl.setText(self.file_path)
        self.SoundItemUrlFrame.hide()

        self.audio = AudioSegment.from_file(file_path)
        self.durationInSeconds = self.audio.duration_seconds
        self.durationInMs = len(self.audio)

        self.repeat_enabled = False
        self.normalized_volume = 0.75 # range 0-1 default 0.75
        self.stop = False
        self.fade_in_value = 0.0
        self.fade_out_value = 0.0
        self.play_thread = None

        self.generate_waveform(file_path)
        
        #self.update_item_data()

        # Initialize Default values for the widget components
        self.SoundFileNameLabel.setText(f"{self.sound_file_name}")

    
    def on_any_change(self):
        print("change detected")
        data = {
            "audio_id": self.audio_id,
            "filename": self.SoundFileNameLabel.text(),
            "asset_type": self.AssetTypeComboBox.currentText(),
            "singleInstance": self.isSingleInstance.isChecked(),
            "volume": self.MainVolumeSlider.value(),
            "loop": self.isLooping.isChecked(),
            "item_url": self.SoundItemUrl.text(),
            "fade_in": 0.0,
            "fade_out": 0.0,
        }
        #self.data_changed.emit(data)
        #print(self.data_changed, data)


    def mousePressEvent(self, event):
        self.clicked.emit(self.sound_file_name)
        return super().mousePressEvent(event)
    
    def update_item_data(self):
        self.data = {
            "filename": self.sound_file_name,
            "asset_type": self.AssetTypeComboBox.currentText(),
            "calegory": self.CategoryComboBox.currentText(),
            "singleInstance": ("True" if self.isSingleInstance.isChecked() else "False"),
            "volume": self.MainVolumeSlider.value(),
            "loop": ("True" if self.isLooping.isChecked() else "False"),
            "fade_in": self.FadeInProgressBar.value(),
            "fade_out": self.FadeOutProgressBar.value(),
            "item_url": self.SoundItemUrl.text(),
        }
        #print(self.data)
        self.current_item_changed.emit(self.data)
    
    def on_asset_type_changed(self, text):
        #self.data["asset_type"] = text
        self.asset_type_changed.emit(text )

    
    def on_single_instance_toggled(self, state):
        is_checked = state == Qt.Checked
        print(str(is_checked))
        #self.data["single_instance"] = is_checked
        self.single_instance_toggled.emit(is_checked)

    def on_volume_changed(self, value):
        self.normalized_volume = round(value / 100.0, 2) # assuming slider is 0-100
        self.volume_changed.emit(self.normalized_volume)
        self.MainVolumeValueLabel.setText(str(self.normalized_volume))
        self.audio_player.set_volume(self.audio_id, value)
    
    def on_fade_in_changed(self, value):
        self.fade_in_value = round(value / 100.0, 2) # assuming slider is 0-100
        self.fade_in_changed.emit(self.fade_in_value)
        self.FadeInLabel.setText(f"{str(self.fade_in_value)} (Secs)")

    def on_fade_out_changed(self, value):
        self.fade_out_value = round(value / 100.0, 2) # assuming slider is 0-100
        self.fade_out_changed.emit(self.fade_out_value)
        self.FadeOutLabel.setText(f"{str(self.fade_out_value)} (Secs)")

    def update_meter(self, audio_id, left_db, right_db):
        if audio_id == self.audio_id:
            self.meterL.setValue(left_db)
            self.meterR.setValue(right_db)
            self.Left_dB_Text.setText(f"{self._peak_left:5.1f} dB")
            self.Right_dB_Text.setText(f"{self._peak_right:5.1f} dB")

    
    def set_left_peak_level_value(self, value):
        #print(f"Left peak level value: {value}")
        self._peak_left = value
    def set_right_peak_level_value(self, value):
        #print(f"Right peak level value: {value}")
        self._peak_right = value
        
        
    def on_loop_toggled(self, state):
        is_checked = state == Qt.Checked
        self.loop_toggled.emit(is_checked)
    
    def repeat_toggle(self):
        self.repeat_enabled = not self.repeat_enabled
        self.repeat_changed.emit(self.repeat_enabled)
        print(f"repeat enabled: {self.repeat_enabled}")
        child = self.sender()
        widget = child
        while widget and not isinstance(widget, SoundListViewItem):
            widget = widget.parent()
        if not widget:
            return
            
        if self.repeat_enabled:
            self.audio_listview_repeat_btn.setStyleSheet("background-color: #3b99fc;")
            widget.setStyleSheet("background-color: #3b99fc;")
        else:
            self.audio_listview_repeat_btn.setStyleSheet("")
            widget.setStyleSheet("")
            self.stop_sound()
    
    def play_sound(self):
        self.audio_player.set_volume(self.audio_id, self.MainVolumeSlider.value())
        fade_in = self.FadeInSlider.value() / 100
        fade_out = self.FadeOutSlider.value() / 100
        print(f"calculated fade in { fade_in}, fade out { fade_out}")
        self.audio_player.play(self.audio_id, loop = self.repeat_enabled, fade_in=fade_in, fade_out=fade_out)
        self.audio_listview_play_btn.setStyleSheet("background-color: #3b99fc;")
        self.is_playing = True
        

    
    def stop_sound(self):
        self.audio_player.stop(self.audio_id)
        self.audio_listview_play_btn.setStyleSheet("")
        self.is_playing = False
    
    def on_playback_stopped(self, audio_id):
        #print(f"on_playback_stopped to reset the play button: {audio_id}")
        if audio_id == self.audio_id:
            self.reset_play_button()
            self.is_playing = False
    
    def reset_play_button(self):
        self.audio_listview_play_btn.setStyleSheet("")
    
    def reveal_file_location(self):
        #print(f"emitting this path so file can be revealed: {self.file_path}")
        self.reveal_clicked.emit(self.file_path)
    
    def get_data(self):
        return {
            "audio_id": self.audio_id,
            "filename": self.sound_file_name,
            "asset_type": self.AssetTypeComboBox.currentText(),
            "singleInstance": self.isSingleInstance.isChecked(),
            "volume": self.normalized_volume,
            "loop": self.isLooping.isChecked(),
            "item_url": self.file_path,
            "fade_in": self.FadeInSlider.value(),
            "fade_out": self.FadeOutSlider.value(),
        }
    
    


    def generate_waveform(self, file_path):
        self.SoundFileWaveLabel.clear()
        # Now ready the .wav file
        audio = AudioSegment.from_file(file_path)

        samples = np.array(audio.get_array_of_samples())
        # Normalize samples to range -1 and 1
        normalized = samples / np.max(np.abs(samples))
        # Resize waveform to Qlabel width
        label_width = self.SoundFileWaveLabel.size().width()
        label_height = self.SoundFileWaveLabel.size().height()

        interpolated = np.interp(np.linspace(0, len(normalized), label_width), np.arange(len(normalized)), normalized)

        # create a pixmap and draw waveform
        pixmap = QPixmap(label_width, label_height)
        if self.current_theme == 'dark':
            pixmap.fill(QColor(30, 30, 30))
        else:
            pixmap.fill(QColor("white"))
        painter = QPainter(pixmap)
        pen = QPen(QColor("blue"), 1)
        pen.setWidth(1)
        painter.setPen(pen)

        mid = label_height / 2
        for x, value in enumerate(interpolated):
            y = mid - (value * mid)
            painter.drawLine(int(x), int(mid), int(x), int(y))
        
        painter.end()
        self.SoundFileWaveLabel.setPixmap(pixmap)

        # calculate sound file duration
        duration_ms = len(audio)
        duration = duration_ms / 1000

        if duration < 1.0:
            self.duration_str = f"{duration:.3f}".rstrip('0').rstrip('.') + "s"
        else:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            self.duration_str = f"{minutes:02d}:{seconds:02d}"
        
        self.audio_listview_FileDuration.setText(f"Duration: {self.duration_str}")
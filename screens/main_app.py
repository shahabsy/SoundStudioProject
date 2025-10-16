import sys, platform
import os, re
import PyQt5
import numpy as np
from PyQt5.QtCore import Qt, QUrl, QModelIndex, QAbstractListModel, QSize, QDir, QPoint, QPropertyAnimation, QEasingCurve, QFileInfo
from PyQt5.QtGui import QIcon, QPixmap, QImage, QPainter, QFont, QColor, QBrush, QDesktopServices
from PyQt5.QtWidgets import QApplication, QMainWindow, QListView, QFrame, QSizePolicy, QComboBox, QMenu, QAction, QProgressBar, QCheckBox, QInputDialog, QMessageBox, QTreeView, QListWidget, QFileSystemModel, QListWidgetItem, QFileDialog, QWidget, QStyledItemDelegate, QPushButton, QHBoxLayout, QLabel, QStyle, QAction, QDialog, QVBoxLayout, QSlider, QAbstractItemView
from PyQt5.Qt import QStandardItemModel, QStandardItem
from PyQt5 import uic, QtCore
from pydub import AudioSegment
import resources
import shutil
import json
import pygame
from datetime import datetime
from pathlib import Path
from PyQt5 import uic
from ffmpeg.ffmpeg_converter import convert_wave_to_mp3, convert_wav_to_webm
from core.utils import resource_path
from core.master_meter import MasterMeter
from widgets.BatchEditDialog import BatchEditDialog
from core.project_manager import ProjectManager
from core.audio_player import AudioPlayer
from widgets.SoundListviewItem import SoundListViewItem

class MainWindow(QMainWindow):
    def __init__(self, project_path, current_theme):
        super().__init__()
        self.current_theme = current_theme
        if self.current_theme == 'dark':
            ui_file = resource_path("ui/ui_main_dark.ui")
        else:
            ui_file = resource_path("ui/ui_main.ui")
        uic.loadUi(ui_file, self)
        self.resize(1800, 800)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

        if sys.platform == "darwin":
            from PyQt5.QtWidgets import QShortcut
            from PyQt5.QtGui import QKeySequence
            quit_shortcut = QShortcut(QKeySequence("Meta+Q"), self)
            quit_shortcut.activated.connect(self.close)
        print(f"i am now loading MainWindow UI: {ui_file}")
        self.project_manager = ProjectManager()
        self.project_path = project_path
        self.project_name = os.path.basename(project_path)
        self._master_peak_left = -60
        self._master_peak_right = -60
        self.audio_player = AudioPlayer()
        self.exportSelected = False
        
        # list array for sound items in the QListWidget
        project_json_path = self.get_project_json_path(self.project_path)
        self.sound_items = {}
        self.next_id = self.get_audio_id(project_json_path)

        
        # Reference the QPushButtons from the UI 
        self.leftPanelCollapseBtn = self.findChild(QPushButton, "leftPanelCollapseBtn")
        self.RightPanelCollapseBtn = self.findChild(QPushButton, "RightPanelCollapseBtn")


        # Reference Export All Sounds Button
        self.ExportProjectButtonTbar = self.findChild(QPushButton, "ExportProjectButtonTbar")
        print("ExportProjectButtonTbar", self.ExportProjectButtonTbar)
        self.ExportProjectButtonTbar.clicked.connect(self.export_all_for_game)

        # Reference SoundListItemsCount
        self.SoundListItemsCount = self.findChild(QLabel, "SoundListItemsCount")
        

        # Reference Left side Project Explorer Panel QFrame
        self.ProjectExplorerFrame = self.findChild(QFrame, "ProjectExplorerFrame")
        # connect button click event for Toggle
        self.leftPanelCollapseBtn.clicked.connect(self.toggle_project_explorer)
        self.project_explorer_visible = True
        self.project_explorer_width = 300

        # Reference Right side Details Panel QFrame
        self.RightPanelFrame = self.findChild(QFrame, "RightPanelFrame")
        self.RightPanelFrame.hide()
        
        # connect button click even for Toggle
        self.RightPanelCollapseBtn.clicked.connect(self.toggle_Details_Panel)
        self.details_panel_visible = False
        self.details_panel_width = 300
        
        # Reference the QListView from the UI
        self.SoundsListWidget = self.findChild(QListWidget, "SoundsListWidget")
        #self.SoundsListWidget.itemClicked.connect(self.sound_item_clicked)
        #self.SoundsListWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        #self.SoundsListWidget.customContextMenuRequested.connect(self.on_list_widget_context_menu)
        self.SoundsListWidget.setSelectionMode(QListWidget.ExtendedSelection)
        self.SoundsListWidget.setDragDropMode(QListWidget.InternalMove)
        self.SoundsListWidget.setDefaultDropAction(Qt.MoveAction)
        self.SoundsListWidget.installEventFilter(self)

        #self.SoundsListWidget.setAcceptDrops(True)
        #self.SoundsListWidget.setDragDropMode(QAbstractItemView.DropOnly)
        
        self.SoundsListWidget.itemSelectionChanged.connect(self.on_list_selection_changed)
        #self.SoundsListWidget.customContextMenuRequested.connect(self.on_list_widget_context_menu)
        #self.SoundsListWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.SoundsListWidget.mousePressEvent = self.sounds_list_mouse_press_event
        
        # Reference the Labels of main layout here
        self.SelectedSoundFileNameLabel = self.findChild(QLabel, "SelectedSoundFileNameLabel")
        
        self.ProjectNameLabel = self.findChild(QLabel, "ProjectNameLabel")
        self.ProjectNameLabel.setText(self.project_name)

        self.ProjectPathLabel = self.findChild(QLabel, "ProjectPathLabel")
        self.ProjectPathLabel.setText(self.project_path)

        self.AssetTypeLabel = self.findChild(QLabel, "AssetTypeLabel")

        self.UrlLable = self.findChild(QLabel, "UrlPathLable")
        self.UrlLable.setWordWrap(True)
        
        # Reference teh QCheckBoxes from the UI
        self.LoopValue = self.findChild(QLabel, "LoopValue")
        self.SingleInstanceValue = self.findChild(QLabel, "SingleInstanceValue")

        # Reference the QProgressBars from the UI
        self.VolumeValue = self.findChild(QLabel, "VolumeValue")
        ##############################################################
        # here is the master audio meter bars to use
        #Create Master Meter here
        self.master_meterL = MasterMeter(
            width=300, height=10,
            bg_color=QColor(100,100,100),
            bar_bg=QColor(100,100,100),
            bar_color_start=QColor(0,200,0),
            bar_color_mid=QColor(200,200,0),
            bar_color_end=QColor(200,0,0),
            text_color=QColor(200,200,210),
            min_db=-60.0, max_db=0.0
        )
        
        self.master_meterR = MasterMeter(
            width=300, height=10,
            bg_color=QColor(100,100,100),
            bar_bg=QColor(100,100,100),
            bar_color_start=QColor(0,200,0),
            bar_color_mid=QColor(200,200,0),
            bar_color_end=QColor(200,0,0),
            text_color=QColor(200,200,210),
            min_db=-60.0, max_db=0.0
        )
        
        self.MasterMeterFrame = self.findChild(QFrame, "dbMeterFrame")
        self.master_meter_layout = self.MasterMeterFrame.layout()
        self.master_meter_layout.setContentsMargins(0,0,0,0)
        self.master_meter_layout.addWidget(self.master_meterL)
        self.master_meter_layout.addWidget(self.master_meterR)
        self.audio_player.worker.levels_updated.connect(self.update_master_meter)
        self.audio_player.worker.playback_stopped.connect(self.on_playback_stopped)
        self.MasterLeftDBText = self.findChild(QLabel, "MasterLeftDBText")
        self.MasterRightDBText = self.findChild(QLabel, "MasterRightDBText")
        ##############################################################
        self.master_meterL.master_peak_value.connect(self.set_left_master_peak_value)
        self.master_meterR.master_peak_value.connect(self.set_right_master_peak_value)

        # Reference the QProgressBars for Fade In and Fade Out here fro the UI
        self.FadeInValueDetails = self.findChild(QLabel, "FadeInValueDetails")
        
        self.FadeOutValueDetails = self.findChild(QLabel, "FadeOutValueDetails")
        
        # Reference the QTreeView from the UI and create model
        self.model = QFileSystemModel()
        self.model.setRootPath(project_path)
        self.model.setReadOnly(False)
        self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Files)
        self.model.fileRenamed.connect(self.rename_file_item)
        self.model.setReadOnly(False)

        self.ProjectExplorerTreeView = self.findChild(QTreeView, "ProjectExplorerTreeView")
        if self.current_theme == 'dark':
            print("dark asset")
            self.ProjectExplorerTreeView.setStyleSheet("""
                                                       QTreeView {
                                                       background-color: #1e1e1e;
                                                       color: white;
                                                       }
                                                       QTreeView::branch:has-children:closed
                                                       {
                                                       border-image: none;
                                                       image: url(:/icons/collapse_dark.png);
                                                       }
                                                       QTreeView::branch:open:has-children:open
                                                       {
                                                       border-image: none;
                                                       image: url(:/icons/expand_dark.png)
                                                       }
                                                       QTreeView::branch:!has-children 
                                                       {
                                                       image: none;
                                                       }
                                                       """)
        else:
            self.ProjectExplorerTreeView.setStyleSheet("""
                                                       QTreeView {
                                                       background-color: white;
                                                       color: black;
                                                       }
                                                       QTreeView::branch:has-children:closed
                                                       {
                                                       border-image: none;
                                                       image: url(:/icons/collapse.png);
                                                       }
                                                       QTreeView::branch:open:has-children:open
                                                       {
                                                       border-image: none;
                                                       image: url(:/icons/expand.png)
                                                       }
                                                       QTreeView::branch:!has-children 
                                                       {
                                                       image: none;
                                                       }
                                                       """)
        self.ProjectExplorerTreeView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ProjectExplorerTreeView.setSelectionMode(QTreeView.ExtendedSelection)
        self.ProjectExplorerTreeView.customContextMenuRequested.connect(self.show_context_menu)
        self.ProjectExplorerTreeView.installEventFilter(self)
        self.ProjectExplorerTreeView.viewport().installEventFilter(self)
        

        self.SaveProjectButtonTBar = self.findChild(QPushButton, "SaveProjectButtonTBar")
        if self.SaveProjectButtonTBar:
            self.SaveProjectButtonTBar.clicked.connect(self.save_project)
        
        self.actionSave_Project = self.findChild(QAction, "actionSave_Project")
        if self.actionSave_Project:
            self.actionSave_Project.triggered.connect(self.save_project)
        
        self.ExitProjectWindowButton = self.findChild(QPushButton, "ExitProjectWindowButton")
        if self.ExitProjectWindowButton:
            self.ExitProjectWindowButton.clicked.connect(self.close)
        
        self.load_project_in_explorer(project_path)
        
        #metadata = self.load_project_metadata(project_json_path)
        #self.populate_sound_items_from_metadata(metadata)

        # Check if project JSON exists and is valid, else create/repair it
        
        if not os.path.exists(project_json_path):
            metadata = {
                "project_name": self.project_name,
                "created": datetime.now().isoformat(),
                "last_saved": datetime.now().isoformat(),
                "imported_files": [],
                "imported_sounds": [],
                "project_path": self.project_path
            }
            self.save_project_metadata(project_json_path, metadata)
        else:
            # Try to load and validate metadata
            metadata = self.load_project_metadata(project_json_path)
            # if missing required fields, repair
            changed = False
            if "imported_files" not in metadata or not isinstance(metadata["imported_files"], list):
                metadata["imported_files"] = []
                changed = True
            if "imported_sounds" not in metadata or not isinstance(metadata["imported_sounds"], list):
                metadata["imported_sounds"] = []
                changed = True
            if "project_name" not in metadata:
                metadata["project_name"] = self.project_name
                changed = True
            if "project_path" not in metadata:
                metadata["project_path"] = self.project_path
                changed = True
            if 'created' not in metadata:
                metadata["created"] = datetime.now().isoformat()
                changed = True
            if "last_saved" not in metadata:
                metadata["last_saved"] = datetime.now().isoformat()
                changed = True
            if changed:
                self.save_project_metadata(project_json_path, metadata)
        
        # Only populate sounds items if there are any
        if metadata.get("imported_sounds"):
            self.populate_sound_items_from_metadata(metadata)
            self.update_sounds_list_count()
        else:
            self.SoundsListWidget.clear()
    
    def get_audio_id(self, json_path):
        if not os.path.isfile(json_path):
            return 1
        
        with open(json_path, 'r') as f:
            try:
                data = json.load(f)
            except Exception as e:
                return 1
        
        max_index = 0

        for sound_data in data.get("imported_sounds", []):
            audio_id = sound_data.get("audio_id", "")
            match = re.match(r"sound_(\d+)", audio_id)
            if match:
                index = int(match.group(1))
                if index > max_index:
                    max_index = index
        return max_index + 1 if max_index >= 1 else 1

    def on_explorer_selection_changed(self, selected, deselected):
        self.SoundsListWidget.clearSelection()
        indexes = self.ProjectExplorerTreeView.selectedIndexes()
        if not indexes:
            return
        model = self.ProjectExplorerTreeView.model()

        if indexes.count == 1:
            index = indexes[0]
            file_path = model.filePath(index)
            info = QFileInfo(file_path)
            if info.isFile():
                self.reveal_sound_in_list(file_path)
        else:
            wav_files = []
            for index in indexes:
                file_path = model.filePath(index)
                info = QFileInfo(file_path)
                if info.isFile() and file_path.lower().endswith('wav'):
                    wav_files.append(file_path)

    def save_project(self):
        imported_sounds = []
        for i in range(self.SoundsListWidget.count()):
            item = self.SoundsListWidget.item(i)
            widget = self.SoundsListWidget.itemWidget(item)
            if widget and hasattr(widget, 'get_data'):
                data = widget.get_data()
                audio_id = getattr(widget, 'audio_id', f"sound_{i+1}")
                file_path = getattr(widget, 'file_path', "")
                url = os.path.relpath(file_path, self.project_path).replace("\\", "/")
                options = {
                    'name' : os.path.splitext(os.path.basename(file_path))[0],
                    'asset_type' : widget.AssetTypeComboBox.currentText() if hasattr(widget, 'AssetTypeComboBox') else "",
                    'loop' : widget.isLooping.isChecked() if hasattr(widget, 'isLooping') else False,
                    'singleInstance' : widget.isSingleInstance.isChecked() if hasattr(widget, 'isSingleInstance') else False,
                    'volume' : widget.MainVolumeSlider.value() if hasattr(widget, 'MainVolumeSlider') else 0.75, # volume slider value default 75
                    'fade_in' : widget.FadeInSlider.value() if hasattr(widget, 'FadeInSlider') else "0",
                    'fade_out' : widget.FadeOutSlider.value() if hasattr(widget, 'FadeOutSlider') else "0"
                }
                imported_sounds.append({
                    "audio_id": audio_id,
                    "url": url,
                    "data": {
                        "resourceType": 'sound',
                        "options": options
                    }
                })
        # Gather project metadata
        project_json_path = self.get_project_json_path(self.project_path)
        metadata = self.load_project_metadata(project_json_path)
        changed = False
        if 'imported_files' not in metadata or not isinstance(metadata['imported_files'], list):
            metadata['imported_files'] = []
            changed = True
        if 'imported_sounds' not in metadata or not isinstance(metadata['imported_sounds'], list):
            metadata['imported_sounds'] = []
            changed = True
        if 'project_name' not in metadata:
            metadata['project_name'] = self.project_name
            changed = True
        if 'project_path' not in metadata:
            metadata['project_path'] = self.project_path
            changed = True
        if 'created' not in metadata:
            metadata['created'] = datetime.now().isoformat()
            changed = True
        if 'last_saved' not in metadata:
            metadata['last_saved'] = datetime.now().isoformat()
        
        for sound in imported_sounds:
            if 'data' not in sound or not isinstance(sound['data'], dict):
                sound['data'] = {"resourceType" : "sound", "options" : {}}
            if 'resourceType' not in sound['data']:
                sound['data']['resourceType'] = "sound"
            if 'options' not in sound['data']:
                sound['data']['options'] = {}
            # Ensure data options
            if 'name' not in sound['data']['options']:
                sound['data']['options']['name'] = os.path.splitext(os.path.basename(sound.get('url', 'sound')))[0]
            if 'asset_type' not in sound['data']['options']:
                sound['data']['options']['asset_type'] = ''
            if 'loop' not in sound['data']['options']:
                sound['data']['options']['loop'] = False
            if 'singleInstance' not in sound['data']['options']:
                sound['data']['options']['singleInstance'] = False
            if 'volume' not in sound['data']['options']:
                sound['data']['options']['volume'] = 0.75
            if 'fade_in' not in sound['data']['options']:
                sound['data']['options']['fade_in'] = '0'
            if 'fade_out' not in sound['data']['options']:
                sound['data']['options']['fade_out'] = '0'
        metadata['imported_sounds'] = imported_sounds
        metadata['last_saved'] = datetime.now().isoformat()
        self.save_project_metadata(project_json_path, metadata)
        self.show_information("Project Saved", f"Project data saved to:\n {project_json_path}")
    
    def show_information(self, title, message):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Ok)

    # Apply dark or light theme
        if self.current_theme == 'dark':
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b2b;
                    color: white;
                }
                QLabel {
                              color: white;
                              background-color: transparent;
                              }
                QPushButton {
                    background-color: #444;
                    color: white;
                    padding: 5px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #666;
                }
            """)
        else:
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #ffffff;
                    color: black;
                }
                QLabel {
                              color: black;
                              background-color: transparent;
                              }
                QPushButton {
                    background-color: #ddd;
                    color: black;
                    padding: 5px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #bbb;
                }
            """)

        msg.exec_()

    
    def update_master_meter(self, audio_id, left_db, right_db):
        self.master_meterL.master_update_level(audio_id, left_db)
        self.master_meterR.master_update_level(audio_id, right_db)
        #self.MasterLeftDBText.setText(f"{left_db:5.1f} dB")
        self.MasterLeftDBText.setText(f"{self._master_peak_left:5.1f} dB")
        #self.MasterRightDBText.setText(f"{right_db:5.1f} dB")
        self.MasterRightDBText.setText(f"{self._master_peak_right:5.1f} dB")
    
    def set_left_master_peak_value(self, value):
        #print(f"Left peak level value: {value}")
        self._master_peak_left = value
    def set_right_master_peak_value(self, value):
        #print(f"Right peak level value: {value}")
        self._master_peak_right = value

    
    def on_playback_stopped(self, audio_id):
        self.master_meterL.remove_level(audio_id)
        self.master_meterR.remove_level(audio_id)
    # In case we need to call it from other classes
    def get_project_json_path(self, project_path):
        #project_file = os.path.join(project_path, f"{self.project_name}.json")
        project_file = os.path.join(project_path, f"{self.project_name}.sds")
        #print(f"source file: {project_file}")
        return project_file

    def load_project_metadata(self, project_json_path):
        from core.project_schema import validate_project_metadata
        project_json_path = os.path.abspath(project_json_path)
        if not os.path.exists(project_json_path):
            return {"project_name": "", "created": "", "imported_files": [], "imported_sounds": [], "project_path": ""}
        with open(project_json_path, "r") as f:
            try:
                metadata = json.load(f)
            except Exception:
                QMessageBox.critical(self, "Error", "Project file is corrupted or invalid.")
                return {"project_name": "", "created": "", "imported_files": [], "imported_sounds": [], "project_path": ""}
        is_valid, error = validate_project_metadata(metadata)
        if not is_valid:
            QMessageBox.critical(self, "Error", f"Project file structure is invalid:\n{error}")
            return {"project_name": "", "created": "", "imported_files": [], "imported_sounds": [], "project_path": ""}
        return metadata
        
    def populate_sound_items_from_metadata(self, metadata):
        self.SoundsListWidget.clear()
        imported_sounds = metadata.get("imported_sounds", [])
        for sound in imported_sounds:
            audio_id = sound.get("audio_id")
            url = sound.get("url")
            file_path = os.path.join(self.project_path, url) if url else None
            options = sound.get("data", {}).get("options", {})
            if file_path and os.path.exists(file_path):
                data = {
                    "audio_id": audio_id,
                    "filename": options.get("name", ""),
                    "asset_type": options.get("asset_type", ""),
                    "loop": options.get("loop", False),
                    "singleInstance": options.get("singleInstance", False),
                    "volume": options.get("volume", 0.75),
                    "fade_in": options.get("fade_in", "0"),
                    "fade_out": options.get("fade_out", "0"),
                    "item_url": file_path
                }
                self.add_sound_to_list(audio_id, file_path, self.audio_player, data=data)
                print(f"Loaded sound: {data['filename']} with ID: {audio_id}")

    
    def save_project_metadata(self, project_json_path, metadata):
        with open(project_json_path, 'w') as f:
            json.dump(metadata, f, indent=4)
            print("imported file's log saved in metadata")
    
    def log_import_to_project(self, project_path, imported_file_path):
        if not project_path or not imported_file_path:
            print("invalid paths")
            return
        
        project_json_path = self.get_project_json_path(os.path.abspath(self.project_path))
        project_metadata = self.load_project_metadata(os.path.abspath(project_json_path))

        new_entry = {
            "file_name": os.path.basename(imported_file_path),
            #"file_path": os.path.relpath(imported_file_path, project_json_path),
            "file_path": os.path.abspath(imported_file_path),
            "imported_time": datetime.now().isoformat()
        }

        if "imported_files" not in project_metadata:
            project_metadata["imported_files"] = []
        else:
            print("imported_files element not found")
        
        project_metadata["imported_files"].append(new_entry)
        self.save_project_metadata(project_json_path, project_metadata)

    
    def load_sound_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Sound", "", "Sound Files (*.wav *.mp3 *.ogg *.flac *.acc *.mda *.wma);; All Files (*)")
        audio_id = f"sound_{self.next_id}"
        self.next_id += 1
        
        if file_path:
            self.add_sound_to_list(audio_id, file_path, self.audio_player)

    def delete_sound_file(self):
        print("Delete sound item from the list")

    def toggle_project_explorer(self):
        left_panel_animation = QPropertyAnimation(self.ProjectExplorerFrame, b"maximumWidth")
        left_panel_animation.setDuration(100)
        left_panel_animation.setEasingCurve(QEasingCurve.InOutCubic)

        if self.project_explorer_visible:
            left_panel_animation.setStartValue(self.ProjectExplorerFrame.width())
            left_panel_animation.setEndValue(0)
        else:
            left_panel_animation.setStartValue(self.ProjectExplorerFrame.width())
            left_panel_animation.setEndValue(self.project_explorer_width)
        left_panel_animation.start()

        self.ProjectExplorerFrame.animation = left_panel_animation
        self.project_explorer_visible = not self.project_explorer_visible
    
    def toggle_Details_Panel(self):
        right_panel_animation = QPropertyAnimation(self.RightPanelFrame, b"maximumWidth")
        right_panel_animation.setDuration(100)
        right_panel_animation.setEasingCurve(QEasingCurve.InOutCubic)

        if self.details_panel_visible:
            self.RightPanelFrame.hide()
            right_panel_animation.setStartValue(self.RightPanelFrame.width())
            right_panel_animation.setEndValue(100)
        else:
            self.RightPanelFrame.show()
            right_panel_animation.setStartValue(self.RightPanelFrame.width())
            right_panel_animation.setEndValue(self.details_panel_width)
        right_panel_animation.start()

        self.RightPanelFrame.animation = right_panel_animation
        self.details_panel_visible = not self.details_panel_visible
    
    def add_sound_to_list(self, audio_id, file_path, audio_player, data=None):
        # check for duplicates by file path
        for i in range(self.SoundsListWidget.count()):
            widget = self.SoundsListWidget.itemWidget(self.SoundsListWidget.item(i))
            if widget and os.path.abspath(widget.file_path) == os.path.abspath(file_path):
                print(f"Duplicate file skipped: {file_path}")
                return
        try:
            item_widget = SoundListViewItem(audio_id, file_path, audio_player, self.current_theme)
            self.audio_player.load_file(audio_id, file_path)
            # Restore properties if data is provided
            if data:
                # Set all properties if present in data
                if 'asset_type' in data:
                    item_widget.AssetTypeComboBox.setCurrentText(data['asset_type'])
                if 'volume' in data:
                    item_widget.MainVolumeSlider.setValue(data['volume'])
                if 'loop' in data:
                    item_widget.isLooping.setChecked(data['loop'] in [True, 'True', 1, '1'])
                if 'singleInstance' in data:
                    item_widget.isSingleInstance.setChecked(data['singleInstance'] in [True, 'True', 1, '1'])
                if 'fade_in' in data:
                    item_widget.FadeInSlider.setValue(data['fade_in'])
                if 'fade_out' in data:
                    item_widget.FadeOutSlider.setValue(data['fade_out'])
                if 'item_url' in data:
                    item_widget.SoundItemUrl.setText(data['item_url'])
                if 'filename' in data:
                    item_widget.sound_file_name = data['filename']
        except Exception as e:
            QMessageBox.critical(self, "Error loading sound", f"Could not load the sound file:\n{file_path}\n\nError: {e}")
            print(f"Error loading sound file {file_path} : {e}")
            return

        list_item = QListWidgetItem(self.SoundsListWidget)
        list_item.setSizeHint(item_widget.sizeHint())
        self.SoundsListWidget.addItem(list_item)
        self.SoundsListWidget.setItemWidget(list_item, item_widget)
        self.SoundsListWidget.setSpacing(8)

        item_widget.audio_listview_play_btn.clicked.connect(self.on_child_clicked)
        item_widget.audio_listview_repeat_btn.clicked.connect(self.on_child_clicked)
        item_widget.ShowFileInExplorerButton.clicked.connect(self.on_child_clicked)
        item_widget.AssetTypeComboBox.currentTextChanged.connect(self.on_child_clicked)
        item_widget.isLooping.clicked.connect(self.on_child_clicked)
        item_widget.isSingleInstance.clicked.connect(self.on_child_clicked)
        item_widget.MainVolumeSlider.valueChanged.connect(self.on_child_clicked)
        item_widget.FadeInSlider.valueChanged.connect(self.on_child_clicked)
        item_widget.FadeOutSlider.valueChanged.connect(self.on_child_clicked)
        item_widget.asset_type_changed.connect(self.update_asset_type_label)
        item_widget.loop_toggled.connect(self.update_loop)
        item_widget.single_instance_toggled.connect(self.update_single_instance)
        item_widget.volume_changed.connect(self.update_volume)
        item_widget.reveal_clicked.connect(self.reveal_file_in_project_explorer)
        item_widget.play_requested.connect(self.play_sound_item)
        item_widget.repeat_changed.connect(self.repeat_sound_item_enabled)

        
    def on_child_clicked(self):
        print("item clicked using mouse")
        child = self.sender()
        widget = child
        while widget and not isinstance(widget, SoundListViewItem):
            widget = widget.parent()
        if not widget:
            return
        self.SoundsListWidget.clearSelection()
        for i in range(self.SoundsListWidget.count()):
            item = self.SoundsListWidget.item(i)
            if self.SoundsListWidget.itemWidget(item) == widget:
                self.SoundsListWidget.setCurrentItem(item)
                item.setSelected(True)
                #self.sound_item_clicked(item)
                break
    
    
    def sound_item_clicked(self, item):
        print("Sound item clicked", item)
        widget = self.SoundsListWidget.itemWidget(item)
        if widget:
            self.update_details_panel(item)
            print(widget.get_data())
            file_path = getattr(widget, 'file_path', None)
            if file_path:
                file_index = self.model.index(file_path)
                if file_index.isValid():
                    self.ProjectExplorerTreeView.setCurrentIndex(file_index)
                    self.ProjectExplorerTreeView.scrollTo(file_index)
                    print("i am selecting its folder here")
            
        


    def on_sound_item_changed(self, data):
        #print("sound item data changed here")
        audio_id = data["audio_id"]
        # Repace Existing or append
        for i, e in enumerate(self.sound_items_data):
            if e.get("audio_id") == audio_id:
                self.sound_items_data[i] = data
                break
            else:
                self.sound_items_data.append(data)
            #self.save_items()
    
    def save_items(self):
        #need to work on this function
        project_json_path = self.get_project_json_path(os.path.abspath(self.project_path))
        project_metadata = self.load_project_metadata(os.path.abspath(project_json_path))
        #need to work on this function
    
    def update_item_data(self, widget):
        print(f"{self.sound_items}")
        widget.data = {
            "filename": widget.sound_file_name,
            "asset_type": widget.AssetTypeComboBox.currentText(),
            "calegory": widget.CategoryComboBox.currentText(),
            "single_instance": ("True" if widget.isSingleInstance.isChecked() else "False"),
            "volume": widget.MainVolumeSlider.value(),
            "loop": ("True" if widget.isLooping.isChecked() else "False"),
            "fade_in": widget.FadeInProgressBar.value(),
            "fade_out": widget.FadeOutProgressBar.value(),
            "item_url": widget.SoundItemUrl.text(),
        }
        print(widget, widget.data)

    def load_project_in_explorer(self, project_path):
        self.model.setRootPath(self.project_path)
        self.ProjectExplorerTreeView.setModel(self.model)
        self.ProjectExplorerTreeView.setRootIndex(self.model.index(project_path))
        #from PyQt5.QtWidgets import QAbstractItemView
        self.ProjectExplorerTreeView.setEditTriggers(QAbstractItemView.EditKeyPressed | QAbstractItemView.SelectedClicked)
        #self.ProjectExplorerTreeView.setHeaderHidden(True)
        self.ProjectExplorerTreeView.setColumnWidth(0, 250)
        self.ProjectExplorerTreeView.setDragEnabled(True)
        self.ProjectExplorerTreeView.hideColumn(1)
        self.ProjectExplorerTreeView.hideColumn(2)
        self.ProjectExplorerTreeView.hideColumn(3)
        
        #self.ProjectExplorerTreeView.setColumnWidth(0, max(250, self.ProjectExplorerTreeView.sizeHintForColumn(0)))
        #self.ProjectExplorerTreeView.resizeColumnToContents(0)
        self.ProjectExplorerTreeView.selectionModel().selectionChanged.connect(self.on_explorer_selection_changed)
    
    def replace_item(self, index):
        project_json_path = self.get_project_json_path(os.path.abspath(self.project_path))
        project_metadata = self.load_project_metadata(os.path.abspath(project_json_path))

        model = self.ProjectExplorerTreeView.model()

        old_file = model.filePath(index)
        parent_dir = os.path.dirname(old_file)
        replacement_file, _ = QFileDialog.getOpenFileName(self, "Select Replacement WAV", parent_dir, "Sound Files (*.wav);; All Files (*)")

        if not replacement_file:
            return
        
        new_name = os.path.basename(replacement_file)
        new_file = os.path.join(parent_dir, new_name)
        
        print("replace this with old", replacement_file)
        try:
            shutil.copyfile(replacement_file, new_file)
            os.remove(old_file)
            model.layoutChanged.emit()
        except Exception as e:
            QMessageBox.critical(self, "Replace Failed", str(e))
            return

        for i in range(self.SoundsListWidget.count()):
            item = self.SoundsListWidget.item(i)
            widget = self.SoundsListWidget.itemWidget(item)
            if widget and os.path.abspath(widget.file_path) == os.path.abspath(old_file):
                widget.file_path = os.path.abspath(new_file)
                widget.sound_file_name = new_name
                widget.SoundItemUrl.setText(new_file)
                widget.SoundFileNameLabel.setText(new_name)
                #print("updated path: ", widget.SoundItemUrl.text(), "updated name: ", widget.SoundFileNameLabel.text())
                widget.data = {
                "filename": widget.sound_file_name,
                "item_url": widget.SoundItemUrl.text(),
                }
                # we need to update the waveform and player/worker corressponding data
                widget.generate_waveform(new_file)
                widget.audio_player.load_file(widget.audio_id, new_file)
        if "imported_files" not in project_metadata:
            return
        
        for entry in project_metadata["imported_files"]:
            entry_rel_path = entry.get("file_path")
            if not entry_rel_path:
                continue
            abs_entry_path = os.path.abspath(os.path.join(os.path.dirname(project_json_path), entry_rel_path))
            if abs_entry_path == old_file:
                entry["file_name"] = new_name
                entry["file_path"] =  new_file
                entry["imported_time"] = datetime.now().isoformat()        
        self.save_project_metadata(project_json_path, project_metadata)
        
                
    
    def rename_file_item(self, path, old_name, new_name):
        print(old_name)
        print(new_name)
        old_file = os.path.join(path, old_name)
        new_file = os.path.join(path, new_name)
        #print("old name: ", old_name, "new name: ", new_name)
        #print("old file: ", old_file)
        #print("new file: ", new_file)
        for i in range(self.SoundsListWidget.count()):
            item = self.SoundsListWidget.item(i)
            widget = self.SoundsListWidget.itemWidget(item)
            if widget and os.path.abspath(widget.file_path) == os.path.abspath(old_file):
                widget.file_path = os.path.abspath(new_file)
                widget.sound_file_name = new_name
                widget.SoundItemUrl.setText(new_file)
                widget.SoundFileNameLabel.setText(new_name)
                #print("updated path: ", widget.SoundItemUrl.text(), "updated name: ", widget.SoundFileNameLabel.text())
                widget.data = {
                "filename": widget.sound_file_name,
                "item_url": widget.SoundItemUrl.text(),
                }
                
        project_json_path = self.get_project_json_path(os.path.abspath(self.project_path))
        project_metadata = self.load_project_metadata(os.path.abspath(project_json_path))

        if "imported_files" not in project_metadata:
            return
        
        for entry in project_metadata["imported_files"]:
            #print("imported_files > entey: file_name", entry.get("file_name"))
            #print("imported_files > entey: file_path", entry.get("file_path"))
            #print("imported_files > entey: imported_time", entry.get("imported_time"))
            entry_rel_path = entry.get("file_path")
            if not entry_rel_path:
                continue
            abs_entry_path = os.path.abspath(os.path.join(os.path.dirname(project_json_path), entry_rel_path))
            #print("getting file path by new name:", new_name)
            if abs_entry_path == old_file:
                #print("absolute path from entery_rel_path:", abs_entry_path)
                #print("old path loaded:", old_file)
                entry["file_name"] = new_name
                entry["file_path"] =  new_file
                entry["imported_time"] = datetime.now().isoformat()
                #print("updated entey: file_name", entry.get("file_name"))
                #print("updated entey: file_path", entry.get("file_path"))
                #print("updated entey: imported_time", entry.get("imported_time"))

        self.save_project_metadata(project_json_path, project_metadata)


        
    
    def update_asset_type_label(self, asset_type_text):
        print(f"asset type text changed to:{asset_type_text}")

    def update_category_label(self, category_text):
        print(f"category type text changed to: {category_text}")

    def update_volume(self, volume):
        # update volume bars and its values
        self.VolumeValue.setText(f"{volume}")

    def update_loop(self, is_checked):
        print(f"loop toggled to: {is_checked}")

    def update_single_instance(self, is_checked):
        print(f"single instance toggled to: {is_checked}")

    def reveal_file_in_project_explorer(self, file_path):
        print(f"revealed path comming from button: {file_path}")
        file_index = self.model.index(file_path)
        if file_index.isValid():
            info = QFileInfo(file_path)
            if info.isFile():
                self.ProjectExplorerTreeView.setCurrentIndex(file_index)
                self.ProjectExplorerTreeView.scrollTo(file_index)
                self.ProjectExplorerTreeView.expand(file_index.parent())
    
    def play_sound_item(self, file_path):
        print(f"play sound: {file_path}")
    
    def repeat_sound_item_enabled(self, is_checked):
        print(f"repeat toggled to: {is_checked}")

    def refersh_project_explorer(self):
        self.model = QFileSystemModel()
        self.model.setRootPath(self.project_path)
        self.ProjectExplorerTreeView.setModel(self.model)
        self.ProjectExplorerTreeView.setRootIndex(self.model.index(self.project_path))
        self.ProjectExplorerTreeView.selectionModel().selectionChanged.connect(self.on_explorer_selection_changed)
        self.update_sounds_list_count()

    def show_context_menu(self, position:QPoint):
        index = self.ProjectExplorerTreeView.indexAt(position)
        if not index.isValid(): # Empty space clicked
            menu = QMenu()
            new_action = QAction("New Folder")
            new_action.triggered.connect(lambda: self.new_folder(self.project_path))
            menu.addAction(new_action)
            menu.exec_(self.ProjectExplorerTreeView.viewport().mapToGlobal(position))
            #print("Creating folder on project root.")
        else:
            file_path = self.model.filePath(index)
            menu = QMenu()
            if os.path.isdir(file_path):
                new_action = QAction("New Folder")
                new_action.triggered.connect(lambda: self.new_folder(file_path))
                menu.addAction(new_action)

                load_action = QAction("Load File")
                load_action.triggered.connect(lambda: self.open_item(file_path))

                multi_load_action = QAction("Load File(s)")
                multi_load_action.triggered.connect(lambda: self.load_multiple_files(file_path))

                add_all_files_action = QAction("Add all files in folder to list")
                def add_all_files():
                    files = [os.path.join(file_path) for f in os.listdir(file_path) if os.path.isfile(os.path.join(file_path, f))]
                    if files:
                        self.add_multiple_files_to_list(files)
                add_all_files_action.triggered.connect(add_all_files)

                rename_action = QAction("Rename")
                rename_action.triggered.connect(lambda: self.rename_file_item(index))

                delete_action = QAction("Delete")
                delete_action.triggered.connect(lambda: self.delete_item(file_path))

                menu.addAction(new_action)
                #menu.addAction(load_action)
                menu.addAction(multi_load_action)
                #menu.addAction(add_all_files_action)
                #menu.addAction(rename_action)
                menu.addAction(delete_action)

            elif os.path.isfile(file_path):       
                add_to_list_action = QAction("Add to list")
                def add_selected_files_to_list():
                    selected_indexes = self.ProjectExplorerTreeView.selectedIndexes()
                    model = self.ProjectExplorerTreeView.model()
                    selected_files = set()
                    for index in selected_indexes:
                        if index.column() == 0:
                            path = model.filePath(index)
                            if os.path.isfile(path):
                                selected_files.add(path)
                    # if the user right-clicked a file that is not in the selection, just add that file
                    if not selected_files or file_path not in selected_files:
                        selected_files = {file_path}
                    self.add_multiple_files_to_list(list(selected_files))
                add_to_list_action.triggered.connect(add_selected_files_to_list)

                rename_action = QAction("Rename")
                rename_action.triggered.connect(lambda: self.rename_item(index))

                replace_action = QAction("Replace File")
                replace_action.triggered.connect(lambda: self.replace_item(index))

                delete_action = QAction("Delete")
                delete_action.triggered.connect(lambda: self.delete_item(file_path))

                reveal_in_list_action = QAction("Reveal in List")
                reveal_in_list_action.triggered.connect(lambda: self.reveal_sound_in_list(file_path))

                show_in_external_explorer_action = QAction("Show in External Explorer")
                show_in_external_explorer_action.triggered.connect(lambda: self.show_in_external_explorer(file_path))


                menu.addAction(add_to_list_action)
                menu.addAction(rename_action)
                menu.addAction(replace_action)
                menu.addAction(delete_action)
                menu.addAction(reveal_in_list_action)
                menu.addAction(show_in_external_explorer_action)

            menu.exec_(self.ProjectExplorerTreeView.viewport().mapToGlobal(position))
    
    def reveal_sound_in_list(self, file_path):
        for i in range(self.SoundsListWidget.count()):
            item = self.SoundsListWidget.item(i)
            widget = self.SoundsListWidget.itemWidget(item)
            if widget and hasattr(widget, 'file_path'):
                if os.path.abspath(widget.file_path) == os.path.abspath(file_path):
                    self.SoundsListWidget.setCurrentItem(item)
                    self.SoundsListWidget.scrollToItem(item)
                    self.sound_item_clicked(item)
                    item.setSelected(True)
                    return
        QMessageBox.information(self, "Reveal in list", "Sound file not found in the list.")

    def show_in_external_explorer(self, file_path):
        if os.path.exists(file_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(file_path)))
        else:
            QMessageBox.information(self, "Show in explorer", "File does not.")

    def on_list_widget_context_menu(self, position:QPoint, groupSelection=False):
        item = self.SoundsListWidget.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        if groupSelection:
            edit_action = QAction("Edit Selected", self)
            edit_action.triggered.connect(self.batch_edit_selected_items)
            export_action = QAction("Export Selected", self)
            export_action.triggered.connect(lambda: self.export_list_item())
            delete_action = QAction("Delete Selected", self)
            delete_action.triggered.connect(lambda: self.delete_selected_list_items())
            menu.addAction(edit_action)
            menu.addAction(export_action)
            menu.addAction(delete_action)
        else:
            export_action = QAction("Export Selected", self)
            export_action.triggered.connect(lambda: self.export_list_item())
            delete_action = QAction("Delete Selected", self)
            delete_action.triggered.connect(lambda: self.delete_selected_list_items())
            menu.addAction(export_action)
            menu.addAction(delete_action)
        

        menu.exec(self.SoundsListWidget.mapToGlobal(position))
    
    def batch_edit_selected_items(self):
        selected_items = self.SoundsListWidget.selectedItems()
        if not selected_items:
            return

        dialog = BatchEditDialog(self.current_theme)
        result = dialog.exec_()
        if result == 1:
            asset_type = dialog.asset_type_combo.currentText()
            loop = dialog.loop_checkbox.isChecked()
            volume = dialog.volume_slider.value()
            isSingleInstance = dialog.isSingleInstance.isChecked()
            fade_in = dialog.fade_in_value * 100
            fade_out = dialog.fade_out_value * 100
            for item in selected_items:
                widget = self.SoundsListWidget.itemWidget(item)
                if widget:
                    widget.AssetTypeComboBox.setCurrentText(asset_type)
                    widget.isSingleInstance.setChecked(isSingleInstance)
                    widget.isLooping.setChecked(loop)
                    widget.MainVolumeSlider.setValue(volume)
                    widget.FadeInSlider.setValue(int(fade_in))
                    widget.FadeOutSlider.setValue(int(fade_out))
            current = self.SoundsListWidget.currentItem()
            if current:
                self.update_details_panel(current)
        elif result == 0:
            current = self.SoundsListWidget.currentItem()
            if current:
                self.update_details_panel(current)
                    

        

    
    def delete_selected_list_items(self):
        selected_items = self.SoundsListWidget.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            widget = self.SoundsListWidget.itemWidget(item)
            if widget and hasattr(widget, "audio_id"):
                self.audio_player.stop(widget.audio_id)
            row = self.SoundsListWidget.row(item)
            self.SoundsListWidget.takeItem(row) # removes the item form the list
        # reset the details panel here
        self.update_sounds_list_count()
            
    
    def export_list_item(self):
        all_items = self.SoundsListWidget.selectedItems()
        if not all_items:
            return
        #print(f"selected items: {len(all_items)}")
        # ask user for export folder
        msg = QMessageBox(self)
        msg.setWindowTitle("Export Options")
        msg.setText("Where do you want to export the selected files?")
        default_btn = msg.addButton("Default Location", QMessageBox.AcceptRole)
        custom_btn = msg.addButton("Custom Location", QMessageBox.AcceptRole)
        cancel_btn = msg.addButton(QMessageBox.Cancel)
        msg.setDefaultButton(default_btn)
        msg.exec_()
        # Determine ffmpeg binary path based on OS:
        if sys.platform == "darwin":
            ffmpeg_bin = resource_path("ffmpeg/ffmpeg")
            if not os.access(ffmpeg_bin, os.X_OK):
                try:
                    os.chmod(ffmpeg_bin, 0o755)
                except Exception as e:
                    QMessageBox.critical(self, "FFmpeg Error", f"Failed to set executable permission for ffmpeg: {e}")
                    return
        else:
            ffmpeg_bin = resource_path("ffmpeg/ffmpeg.exe")
        
        errors = []

        if msg.clickedButton() == cancel_btn:
            return
        if msg.clickedButton() == default_btn:
            export_folder = os.path.join(self.project_path, "Export") # need to set default path here
            webm_folder = os.path.join(export_folder, "webm")
            mp3_folder = os.path.join(export_folder, "mp3")
            os.makedirs(webm_folder, exist_ok=True)
            os.makedirs(mp3_folder, exist_ok=True)

            for item in all_items:
                widget = self.SoundsListWidget.itemWidget(item)
                if not widget:
                    continue

                src = widget.file_path
                base_project_dir = self.project_path
                try:
                    relative_path = os.path.relpath(src, base_project_dir)
                except ValueError:
                    errors.append(f"{src}: File is outside of the base project directory.")
                    continue
                
                # get file name with extension
                base_name = os.path.splitext(os.path.basename(src))[0]
                relative_dir = os.path.dirname(relative_path)

                webm_target_dir = os.path.join(webm_folder, relative_dir)
                mp3_target_dir = os.path.join(mp3_folder, relative_dir)
                os.makedirs(webm_target_dir, exist_ok=True)
                os.makedirs(mp3_target_dir, exist_ok=True)

                webm_out = os.path.join(webm_target_dir, f"{base_name}.webm")
                mp3_out = os.path.join(mp3_target_dir, f"{base_name}.mp3")
                try:
                    convert_wav_to_webm(src, webm_out, ffmpeg_path=ffmpeg_bin)
                    convert_wave_to_mp3(src, mp3_out, ffmpeg_path=ffmpeg_bin)
                except Exception as e:
                    errors.append(f"{base_name}: {e}")

        else:
            export_folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
            if not export_folder:
                return

            for item in all_items:
                widget = self.SoundsListWidget.itemWidget(item)
                if not widget:
                    continue

                src = widget.file_path
                # get relative path from base directory
                base_project_dir = self.project_path
                #print(f"base project director: {base_project_dir}")
                try:
                    relative_path = os.path.relpath(src, base_project_dir)
                except ValueError:
                    errors.append(f"{src}: File is outside of the base project directory")
                    continue

                # get file name without extension
                base_name = os.path.splitext(os.path.basename(src))[0]
                relative_dir = os.path.dirname(relative_path)

                # create target directory preserving original folder structure
                target_dir = os.path.join(export_folder, relative_dir)
                os.makedirs(target_dir, exist_ok=True)

                # define out paths
                mp3_out = os.path.join(target_dir, f"{base_name}.mp3")
                webm_out = os.path.join(target_dir, f"{base_name}.webm")

                try:
                    convert_wave_to_mp3(src, mp3_out, ffmpeg_path=ffmpeg_bin)
                    convert_wav_to_webm(src, webm_out, ffmpeg_path=ffmpeg_bin)
                except Exception as e:
                    errors.append(f"{base_name}: {e}")
                
        if errors:
            QMessageBox.warning(self, "Export Errors", "Some files failed to export:\n" + "\n".join(errors))
        else:
            QMessageBox.information(self, "Export Complete", "All selected files were exported successfully!")
    

    def new_folder(self, path):
        #print(f"Craeting a new folder. {path}")
        #Creating a new Folder on the item selected
        folder_name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and folder_name:
            new_folder_path = os.path.join(path, folder_name)
            if not os.path.exists(new_folder_path):
                os.makedirs(new_folder_path)
                self.refersh_project_explorer()

    def open_item(self, path):
        print(f'Opening: {path}')
        #Open File or Folder depending on the item selected
        file_dialog = QFileDialog()
        #file_path, _ = file_dialog.getOpenFileName(self, "Select a File", "", "Sound Files (*.wav *.mp3 *.ogg *.flac *.acc *.mda *.wma);; All Files (*)")
        file_path, _ = file_dialog.getOpenFileName(self, "Select a File", "", "Sound Files (*.wav);; All Files (*)")

        if file_path:
            file_name = os.path.basename(file_path)
            target_path = os.path.join(path, file_name)
            try:
                shutil.copy(file_path, target_path)
                print(f"Copied {file_path} to {target_path}")

                index = self.ProjectExplorerTreeView.model().index(target_path)
                self.ProjectExplorerTreeView.expand(index)
                if index.isValid():
                    self.ProjectExplorerTreeView.setCurrentIndex(index)
                    self.ProjectExplorerTreeView.scrollTo(index)

                audio_id = f"sound_{self.next_id}"
                self.next_id += 1
                self.add_sound_to_list(audio_id, target_path, self.audio_player)
                self.log_import_to_project(path, os.path.basename(file_path))
                self.refersh_project_explorer()
            except Exception as e:
                print("Error copying file:", e)
    
    def load_multiple_files(self, path):
        print(f"loading multiple files from the folder: {path}")
        #files, _ = QFileDialog.getOpenFileNames(self, "Import Audio Files", "", "Sound Files (*.wav *.mp3 *.ogg *.flac *.acc *.mda *.wma);; All Files (*)")
        files, _ = QFileDialog.getOpenFileNames(self, "Import Audio Files", "", "Sound Files (*.wav);; All Files (*)")
        if not files:
            return
        
        index = self.ProjectExplorerTreeView.currentIndex()
        model: QFileSystemModel = self.ProjectExplorerTreeView.model()
        target_folder = model.filePath(index)

        if not os.path.isdir(target_folder):
            QMessageBox.warning(self, "Invalid Folder", "Please select a valid folder...")
            return
        
        last_file_path = None
        for file in files:
            audio_id = f"sound_{self.next_id}"
            self.next_id += 1
            target_path = os.path.join(target_folder, os.path.basename(file))
            if os.path.abspath(file) != os.path.abspath(target_path):
                shutil.copy(file, target_folder)
            last_file_path = target_path
            #self.add_sound_to_list(audio_id, target_path, self.audio_player)
            self.log_import_to_project(target_folder, target_path)
        
        #self.refersh_project_explorer()
        if last_file_path:
            last_file_index = model.index(last_file_path)
            if last_file_index.isValid():
                parent_index = last_file_index.parent()
                self.ProjectExplorerTreeView.expand(parent_index)
                self.ProjectExplorerTreeView.setCurrentIndex(last_file_index)
                self.ProjectExplorerTreeView.scrollTo(last_file_index)
                self.ProjectExplorerTreeView.setFocus()
    
    def update_sounds_list_count(self):
        count = self.SoundsListWidget.count()
        self.SoundListItemsCount.setText(f"List Items Count ({count})")
    
    def add_multiple_files_to_list(self, file_paths=None):
        files = set()
        target_folder = None
        model: QFileSystemModel = self.ProjectExplorerTreeView.model()
        if files is not None:
            for file_path in file_paths:
                if os.path.isfile(file_path):
                    files.add(file_path)
                elif os.Path.isdir(file_path) and target_folder is None:
                    target_folder = file_path
        else:
            selected_indexes = self.ProjectExplorerTreeView.selectedIndexes()
            if not selected_indexes:
                QMessageBox.warning(self, "No Selection", "Please select one or more files")
                return
            for index in selected_indexes:
                if index.column() != 0:
                    continue
                file_path = model.filePath(index)
                if os.path.isfile(file_path):
                    files.add(file_path)
                elif os.path.isdir(file_path) and target_folder is None:
                    target_folder == file_path
        
        if not files:
            QMessageBox.warning(self, "No Files", "No files selected in the project explorer")
            return
        
        for file in files:
            audio_id = f"sound_{self.next_id}"
            self.next_id += 1
            target_path = os.path.abspath(file)
            self.add_sound_to_list(audio_id, target_path, self.audio_player)
            self.log_import_to_project(target_folder, target_path)
        
        #self.refersh_project_explorer()
    
    # Load sound item list when project opens, if its an existing project
    def load_sound_items_from_json(self, project_path):
        
        data = self.load_project_metadata(project_path)
        if data:
            for sound in data.get("imported_sounds", []):
                file_path = Path(project_path) / sound["relative_path"]
                if file_path.exists():
                    widget = SoundListViewItem()
                    widget.set_sound_file(file_path)
                    list_item = QListWidgetItem()
                    list_item.setSizeHint(widget.sizeHint)
                    self.sound_list.addItem(list_item)
                    self.sound_list.setItemWidget(list_item, widget)


    def rename_item(self, index):
        self.ProjectExplorerTreeView.edit(index)
    

    
    def delete_item(self, path):
        confirm = QMessageBox.question(
            self, "Delete File",
            f"Are you sure you want to delete:\n{path}",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    # Remove from sound list widget if present
                    self.remove_sound_from_list_by_path(path)
                    self.delete_item_json_entry(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                    # Remove all sounds in this folder from the list widget
                    self.remove_sounds_from_list_by_folder(path)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
    
    def delete_item_json_entry(self, path):
        print("I will delete file entry in json: ", path)
        project_json_path = self.get_project_json_path(os.path.abspath(self.project_path))
        project_metadata = self.load_project_metadata(os.path.abspath(project_json_path))

        if "imported_files" not in project_metadata:
            return
        target_abs_path = os.path.abspath(path)
        #for entry in project_metadata["imported_files"]:
        for i, entry in enumerate(project_metadata["imported_files"]):
            #print("imported_files > entey: file_name", entry.get("file_name"))
            #print("imported_files > entey: imported_time", entry.get("imported_time"))
            entry_rel_path = entry.get("file_path")
            
            if not entry_rel_path:
                continue

            abs_entry_path = os.path.abspath(os.path.join(os.path.dirname(project_json_path), entry_rel_path))
            #print("getting file path by new name:", new_name)
            if abs_entry_path == target_abs_path:
                print("imported_files > json entey: ", entry.get("file_path"))
                print("deleting deleted file entry: ", abs_entry_path)
                del project_metadata["imported_files"][i]
                self.save_project_metadata(project_json_path, project_metadata)
                return

    
    def remove_sound_from_list_by_path(self, file_path):
        for i in reversed(range(self.SoundsListWidget.count())):
            item = self.SoundsListWidget.item(i)
            widget = self.SoundsListWidget.itemWidget(item)
            if widget and os.path.abspath(widget.file_path) == os.path.abspath(file_path):
                self.SoundsListWidget.takeItem(i)
        self.update_sounds_list_count()
    
    def remove_sounds_from_list_by_folder(self, folder_path):
        for i in reversed(range(self.SoundsListWidget.count())):
            item = self.SoundsListWidget.item(i)
            widget = self.SoundsListWidget.itemWidget(item)
            if widget and os.path.abspath(widget.file_path).startswith(os.path.abspath(folder_path) + os.sep):
                self.SoundsListWidget.takeItem(i)
        self.update_sounds_list_count()
    
    
            
    
    #def sound_item_double_clicked(self, event):
        #print("Double Clicked:")

    # optional function call for selected sound item widget
    def on_list_selection_changed(self):
        print("on_list_selection_changed called")
        for i in range(self.SoundsListWidget.count()):
            item = self.SoundsListWidget.item(i)
            widget = self.SoundsListWidget.itemWidget(item)
            if not widget:
                continue
            frame = widget.findChild(QFrame, "MainFrame")
            if not frame:
                continue

            if item.isSelected():
                if self.current_theme == 'dark':
                    frame.setStyleSheet("""
                                QWidget#MainFrame {
                                    background-color: #323232;
                                    border: 2px solid #3399FF;
                                    border-radius: 4px;
                                    }
                                    QFrame#MainFrame * {
                                    background: transparent;
                                    }
                                    QFrame#MainFrame QPushButton {
                                    border: 1px solid #434343;
                                    border-radius: 1px;
                                    padding: 4px 4px;
                                    }
                                    QFrame#MainFrame QPushButton:pressed {
                                    background: #d0d7e5;
                                    }
                                    """)
                else:
                    frame.setStyleSheet("""
                                QWidget#MainFrame {
                                    background-color: #cce6ff;
                                    border: 2px solid #3399FF;
                                    border-radius: 4px;
                                    }
                                    QFrame#MainFrame * {
                                    background: transparent;
                                    }
                                    QFrame#MainFrame QPushButton {
                                    border: 1px solid #434343;
                                    border-radius: 1px;
                                    padding: 4px 4px;
                                    }
                                    QFrame#MainFrame QPushButton:pressed {
                                    background: #d0d7e5;
                                    }
                                    """)
            else:
                frame.setStyleSheet("")
        
        current = self.SoundsListWidget.currentItem()
        if current:
            self.update_details_panel(current)
            

    
    def update_details_panel(self, current):
        if current:
            widget = self.SoundsListWidget.itemWidget(current)
            data = widget.get_data()
            #print(f"updated data: {data}")
            self.SelectedSoundFileNameLabel.setText(data["filename"])
            self.AssetTypeLabel.setText(data["asset_type"])
            self.SingleInstanceValue.setText(str(data["singleInstance"]))
            self.VolumeValue.setText(str(data["volume"]))
            self.LoopValue.setText(str(data["loop"]))
            self.UrlLable.setText(data["item_url"])
            self.FadeInValueDetails.setText(f"{str(data["fade_in"] / 100)} (Secs)")
            self.FadeOutValueDetails.setText(f"{str(data["fade_out"] / 100)} (Secs)")
    
    def clear_sounds(self):
        self.audio_player.stop_all()
        self.SoundsListWidget.clear()
        self.sound_items.clear()
    
    
    def closeEvent(self, event):
        print("Close event triggered.")
        self.audio_player.cleanup()

        msg = QMessageBox(self)
        msg.setWindowTitle("Save Project?")
        msg.setText("Do you want to save your project before closing?")
        msg.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        msg.setDefaultButton(QMessageBox.Save)

        if self.current_theme == 'dark':
            msg.setStyleSheet("""
                              QMessageBox {
                                background-color: #2b2b2b;
                                color: white;
                              }
                              QLabel {
                              color: white;
                              background-color: transparent;
                              }
                              QPushButton {
                              background-color: #444;
                              color: white;
                              padding: 5px 12px;
                              border-radius: 4px;
                              }
                              QPushButton:hover {
                              background-color: #666;
                              }
                              """)
        else:
            msg.setStyleSheet("""
                              QMessageBox {
                                background-color: #ffffff;
                                color: black;
                              }
                              QLabel {
                              color: black;
                              background-color: transparent;
                              }
                              QPushButton {
                              background-color: #ddd;
                              color: black;
                              padding: 5px 12px;
                              border-radius: 4px;
                              }
                              QPushButton:hover {
                              background-color: #bbb;
                              }
                              """)
        
        reply = msg.exec_()

        if reply == QMessageBox.Save:
            self.save_project()
            event.accept()
        elif reply == QMessageBox.Discard:
            event.accept()
        else:
            event.ignore()
        
    
    def export_all_for_game(self):
        all_items = [self.SoundsListWidget.item(i) for i in range(self.SoundsListWidget.count())]
        if not all_items:
            return

        #self.export_all_to_webm(all_items)
        export_folder = os.path.join(self.project_path, "Export")
        webm_folder = os.path.join(export_folder, "webm")
        os.makedirs(webm_folder, exist_ok=True)
        if not export_folder:
            return
        # Determine ffmpeg binary path based on OS:
        if sys.platform == "darwin":
            ffmpeg_bin = resource_path("ffmpeg/ffmpeg")
            if not os.access(ffmpeg_bin, os.X_OK):
                try:
                    os.chmod(ffmpeg_bin, 0o755)
                except Exception as e:
                    QMessageBox.critical(self, "FFmpeg Error", f"Failed to set executable permission for ffmpeg: {e}")
                    return
        else:
            ffmpeg_bin = resource_path("ffmpeg/ffmpeg.exe")

        errors = []
        export_json = []
        for item in all_items:
            widget = self.SoundsListWidget.itemWidget(item)
            if not widget:
                continue

            src = widget.file_path
            # get relative path from base directory
            base_project_dir = self.project_path
            #print(f"base project director: {base_project_dir}")
            try:
                relative_path = os.path.relpath(src, base_project_dir)
            except ValueError:
                errors.append(f"{src}: File is outside of the base project directory")
                continue

            # get file name without extension
            base_name = os.path.splitext(os.path.basename(src))[0]
            relative_dir = os.path.dirname(relative_path)

            # create target directory preserving original folder structure
            #target_dir = os.path.join(export_folder, relative_dir)
            #os.makedirs(target_dir, exist_ok=True)
            webm_target_dir = os.path.join(webm_folder, relative_dir)
            os.makedirs(webm_target_dir, exist_ok=True)
            print(f"webm output path: {webm_target_dir}")
            # define out paths
            webm_out = os.path.join(webm_target_dir, f"{base_name}.webm")

            try:
                convert_wav_to_webm(src, webm_out, ffmpeg_path=ffmpeg_bin)
            except Exception as e:
                errors.append(f"{base_name}: {e}")
            
            # Export JSON File
            webm_relative_path = os.path.relpath(webm_out, export_folder).replace("\\", "/")
            if webm_relative_path.startswith('webm/'):
                relative_path = webm_relative_path

            url = f'/assets/sound/{relative_path}'
            data = widget.get_data() if hasattr(widget, 'get_data') else {}
            fade_in = data.get('fade_in', 0)
            fade_out = data.get('fade_out', 0)
            options = {
                'name': data.get('filename', base_name),
                'loop': data.get('loop', False),
                'group': data.get('asset_type', 'None'),
                'singleInstance': data.get('singleInstance', False),
                'volume': data.get('volume', 0.75),
                'fade_in': float(fade_in / 100),
                'fade_out': float(fade_out / 100)
            }
            #print("export file name: ", base_name)
            export_json.append({
                'url': url,
                'data': {
                    'resourceType': 'sound',
                    'options': options
                }
            })
        
        #self.export_all_to_mp3(all_items)
        mp3_folder = os.path.join(export_folder, "mp3")
        os.makedirs(mp3_folder, exist_ok=True)
        if not export_folder:
            return

        for item in all_items:
            widget = self.SoundsListWidget.itemWidget(item)
            if not widget:
                continue

            src = widget.file_path
            # get relative path from base directory
            base_project_dir = self.project_path
            #print(f"base project director: {base_project_dir}")
            try:
                relative_path = os.path.relpath(src, base_project_dir)
            except ValueError:
                errors.append(f"{src}: File is outside of the base project directory")
                continue

            # get file name without extension
            base_name = os.path.splitext(os.path.basename(src))[0]
            relative_dir = os.path.dirname(relative_path)

            # create target directory preserving original folder structure
            #target_dir = os.path.join(export_folder, relative_dir)
            #os.makedirs(target_dir, exist_ok=True)
            mp3_target_dir = os.path.join(mp3_folder, relative_dir)
            os.makedirs(mp3_target_dir, exist_ok=True)
            print(f"mp3 output path: {mp3_target_dir}")
            # define out paths
            mp3_out = os.path.join(mp3_target_dir, f"{base_name}.mp3")

            try:
                convert_wave_to_mp3(src, mp3_out, ffmpeg_path=ffmpeg_bin)
            except Exception as e:
                errors.append(f"{base_name}: {e}")
            
            # Export JSON File
            mp3_relative_path = os.path.relpath(mp3_out, export_folder).replace("\\", "/")
            if mp3_relative_path.startswith('mp3/'):
                relative_path = mp3_relative_path

            url = f'/assets/sound/{relative_path}'
            data = widget.get_data() if hasattr(widget, 'get_data') else {}
            fade_in = data.get('fade_in', 0)
            fade_out = data.get('fade_out', 0)
            options = {
                'name': data.get('filename', base_name),
                'loop': data.get('loop', False),
                'group': data.get('asset_type', 'None'),
                'singleInstance': data.get('singleInstance', False),
                'volume': data.get('volume', 0.75),
                'fade_in': float(fade_in / 100),
                'fade_out': float(fade_out / 100)
            }
            #print("export file name: ", base_name)
            export_json.append({
                'url': url,
                'data': {
                    'resourceType': 'sound',
                    'options': options
                }
            })
        # write JSON file
        json_path = os.path.join(export_folder, 'sounds_export.json')
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(export_json, f, indent=4)
        except Exception as e:
            errors.append(f"Failed to write JSON file: {e}")
        
        if errors:
            QMessageBox.warning(self, "Export Errors", "Some files failed to export:\n" + "\n".join(errors))
        else:
            #QMessageBox.information(self, "Export Complete", "All selected files were exported successfully!")
            self.show_information("Export Complete", "All selected files were exported successfully!")
        
    
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.KeyPress:
            print(f"event filter key pressed {event.key()}")
            if event.key() == QtCore.Qt.Key_Q and event.modifiers() & QtCore.Qt.MetaModifier:
                print(f"Meta+Q pressed - quitting application {event.key()} and {event.modifiers()}")
                QApplication.quit()
                return True
        if obj == self.SoundsListWidget and event.type() == QtCore.QEvent.KeyPress:
            if event.key() == Qt.Key_Space:
                print("Space key pressed.")
                selected_item = self.SoundsListWidget.selectedItems()
                
                if selected_item:
                    any_playing = False
                    for item in selected_item:
                        widget = self.SoundsListWidget.itemWidget(item)
                        if widget and hasattr(widget, 'audio_id'):
                            if widget.is_playing:
                                any_playing = True
                                break
                    if any_playing:
                        for item in selected_item:
                            widget = self.SoundsListWidget.itemWidget(item)
                            if widget and hasattr(widget, 'audio_id'):
                                widget.stop_sound()
                                widget.audio_listview_play_btn.setStyleSheet("")
                    else:
                        for item in selected_item:
                            widget = self.SoundsListWidget.itemWidget(item)
                            if widget and hasattr(widget, 'audio_id'):
                                widget.play_sound()
                                widget.audio_listview_play_btn.setStyleSheet("background-color: #3b99fc;")
                            else:
                                QMessageBox.warning(self, "Play Sound", "Selected item is invalid.")
                else:
                    QMessageBox.warning(self, "No Selection", "No sound item selected.")
                return True
            elif event.key() in (Qt.Key_Up, Qt.Key_Down):
                current_row = self.SoundsListWidget.currentRow()
                if event.key() == Qt.Key_Up:
                    new_row = max(0, current_row - 1)
                else:
                    new_row = min(self.SoundsListWidget.count() - 1, current_row + 1)
                if new_row != current_row:
                    item = self.SoundsListWidget.item(new_row)
                    self.SoundsListWidget.setCurrentItem(item)
                    self.SoundsListWidget.scrollToItem(item)
                    self.sound_item_clicked(item)
                return True
        if (obj == self.ProjectExplorerTreeView or obj == self.ProjectExplorerTreeView.viewport()) and event.type() == QtCore.QEvent.KeyPress:
            if event.key() == Qt.Key_Space:
                indexes = self.ProjectExplorerTreeView.selectedIndexes()
                if indexes:
                    index = indexes[0]
                    model = self.ProjectExplorerTreeView.model()
                    file_path = model.filePath(index)
                    info = QFileInfo(file_path)
                    if info.isFile() and file_path.lower().endswith('.wav'):
                        try:
                            if not pygame.mixer.get_init():
                                pygame.mixer.init()
                            if pygame.mixer.music.get_busy():
                                pygame.mixer.music.stop()
                            else:
                                pygame.mixer.music.load(file_path)
                                pygame.mixer.music.play()
                        except Exception as e:
                            QMessageBox.warning(self, "Playback Error", f"Could not play/stop sound: \n{e}")
                return True
        return super().eventFilter(obj, event)
    
    def play_wav_with_pygame(self, file_path):
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
        except Exception as e:
            QMessageBox.warning(self, "Playback Error", f"Could not play sound:\n{e}")
    
    def sounds_list_mouse_press_event(self, event):
        item = self.SoundsListWidget.itemAt(event.pos())
        if event.button() == Qt.RightButton and item:
            print("mouse right click on widget")
            selected_items = self.SoundsListWidget.selectedItems()
            if item.isSelected():
                if selected_items and len(selected_items) > 1:
                    self.on_list_widget_context_menu(event.pos(), True)
                else:
                    self.on_list_widget_context_menu(event.pos(), False)
            else:
                self.SoundsListWidget.setCurrentItem(item)
                self.SoundsListWidget.clearSelection()
                item.setSelected(True)
                self.on_list_widget_context_menu(event.pos())
            return
        
        super(QListWidget, self.SoundsListWidget).mousePressEvent(event)

    # this function will be used to optimize for file replace function
    def update_sound_widget_and_metadata(self, old_file, new_file, new_name):
        for i in range(self.SoundsListWidget.count()):
            item = self.SoundsListWidget.item(i)
            widget = self.SoundsListWidget.itemWidget(item)
            if widget and os.path.abspath(widget.file_path) == os.path.abspath(old_file):
                widget.file_path = os.path.abspath(new_file)
                widget.sound_file_name = new_name
                widget.SoundFileNameLabel.setText(new_name)
                widget.data["filename"] = new_name
                widget.data["item_url"] = new_file
                widget.generate_waveform(new_file)
                if hasattr(widget, "audio_id"):
                    widget.audio_player.load_file(widget.audio_id, new_file)

        project_json_path = self.get_project_json_path(os.path.abspath(self.project_path))
        project_metadata = self.load_project_metadata(os.path.abspath(project_json_path))

        if "imprted_files" in project_metadata:
            for entry in project_metadata["imported_files"]:
                entry_path = entry.get("file_path")
                abs_entry_path = os.path.abspath(entry_path) if entry_path else None
                if abs_entry_path == os.path.abspath(old_file):
                    entry["file_name"] = new_name
                    entry["file_path"] = new_file
                    entry["imported_time"] = datetime.now().isoformat()
        
        if "imported_sounds" in project_metadata:
            for sound in project_metadata["imported_sounds"]:
                url = sound.get("url")
                abs_url_path = os.path.abspath(os.path.join(self.project_path, url)) if url else None
                if abs_url_path == os.path.abspath(old_file):
                    sound["url"] = os.path.relpath(new_file, self.project_path)
                    if "data" in sound and "options" in sound["data"]:
                        sound["data"]["options"]["name"] = new_name
        
        self.save_project_metadata(project_json_path, project_metadata)
    

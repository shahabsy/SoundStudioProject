from PyQt5.QtCore import Qt, QStandardPaths, QDir, QModelIndex, QAbstractListModel, QSize, pyqtSignal, QEvent, QTimer, QProcess
from PyQt5.QtGui import QIcon, QPixmap, QImage, QPainter, QKeySequence
from PyQt5.QtWidgets import QApplication, QMainWindow, QListView, QWidget, QStyledItemDelegate, QPushButton, QHBoxLayout, QLabel, QStyle, QAction
from PyQt5 import uic
from pydub import AudioSegment
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QListView, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QFrame, QMenu
from PyQt5 import uic
from PyQt5.QtGui import QStandardItem, QImageReader
import os, sys, subprocess, platform
import json
import traceback
from datetime import datetime
from core.utils import resource_path

from core.project_manager import ProjectManager
from widgets.RecentProjectItem import RecentProjectItem
from screens.main_app import MainWindow

CONFIG_FILE = "theme_config.txt"
REQQUIRED_SUBFOLDERS = ["Bet", "Bonus", "Play", "Resolution", "Shared"]

class HomeScreen(QMainWindow):
    def __init__(self):
        super().__init__()
        # load home screen ui file
        self.CURRENT_THEME = self.read_theme()
        self.ui_file_dark = resource_path("ui/ui_main_home_dark.ui")
        self.ui_file_light = resource_path("ui/ui_main_home.ui")
        self.ui_path_dark = os.path.abspath(self.ui_file_dark)
        self.ui_path_light = os.path.abspath(self.ui_file_light)

        self.setFixedSize(self.size())
        if sys.platform == "darwin":
            from PyQt5.QtWidgets import QShortcut
            from PyQt5.QtGui import QKeySequence
            quit_shortcut = QShortcut(QKeySequence("Meta+Q"), self)
            quit_shortcut.activated.connect(self.close)
        #self.setup_quit_action()

        self.project_manager = ProjectManager()
        self.current_theme = self.read_theme()
        if self.current_theme == 'dark':
            self.load_ui(self.ui_file_dark)
        else:
            self.load_ui(self.ui_file_light)
        # reference menu action items
        
        self.lightMode = self.findChild(QAction, "actionLight_Mode")
        if self.lightMode:
            self.lightMode.triggered.connect(self.light_mode_theme)
        
        self.darkMode = self.findChild(QAction, "actionDark_Mode")
        if self.darkMode:
            self.darkMode.triggered.connect(self.dark_mode_theme)

        # reference clear recent projects button
        self.ClearRecentProjectsBtn = self.findChild(QPushButton, "ClearRecentProjectsBtn")
        self.ClearRecentProjectsBtn.clicked.connect(self.clear_recent_projects)
        self.ClearRecentProjectsBtn.setToolTip("Remove all recent projects from this list")

        #Reference ListView
        self.RecentProjectsListWidget = self.findChild(QListWidget, "RecentProjectsListWidget")
        #self.RecentProjectsListWidget.itemDoubleClicked.connect(self.on_project_item_clicked)
        #self.RecentProjectListView.setModel(self.projects_model)

        #Reference Create New Project Widget Button
        self.CreateNewProjectButton = self.findChild(QFrame, "CreateNewProjectWidgetBtn")
        self.CreateNewProjectButton.installEventFilter(self)
        self.CreateNewProjectButton.setCursor(Qt.PointingHandCursor)
        #Reference Create New Project Widget Button
        self.OpenAProjectButton = self.findChild(QFrame, "OpenAProjectWidgetBtn")
        self.OpenAProjectButton.installEventFilter(self)
        self.OpenAProjectButton.setCursor(Qt.PointingHandCursor)
        # reference search bar frame
        self.SearchBarPanel = self.findChild(QFrame, "SearchBarPanel")
        self.ProjectSearchBarLineEdit = self.findChild(QLineEdit, "ProjectSearchBarLineEdit")
        self.ProjectSearchBarLineEdit.setPlaceholderText("Search recent projects...")
        self.ProjectSearchBarLineEdit.setClearButtonEnabled(True)
        self.ProjectSearchBarLineEdit.textChanged.connect(self.filter_recent_projects)
        self.ProjectSearchBarLineEdit.setFocus()
        QTimer.singleShot(0, self.ProjectSearchBarLineEdit.setFocus)
        
    def get_config_path(self):
        config_dir = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)

        QDir().mkpath(config_dir)

        return os.path.join(config_dir, CONFIG_FILE)

    def load_ui(self, ui_file):
        uic.loadUi(ui_file, self)
        self.load_recent_projects_widget_items()

    def light_mode_theme(self):
        print("enable light mode color theme.")
        if self.current_theme != 'light':
            self.save_theme("light")
            self.restart_app()

    def dark_mode_theme(self):
        print("enable dark mode color theme.")
        if self.current_theme != 'dark':
            self.save_theme("dark")
            self.restart_app()
    
    def read_theme(self):
        config_path = self.get_config_path()
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            print(f"Error reading theme: {e}")

        return "dark" # Default

    def save_theme(self, theme):
        print("saving updated theme value.")
        config_path = self.get_config_path()
        try:
            with open(config_path, 'w') as f:
                f.write(theme)
                os.fsync(f.fileno())
        except Exception as e:
            print(f"Error Saving theme: {e}")
    
    def restart_app(self):
        self.show_information("Theme Changed", "Changes will take effect after restarting the app. Do you want to restart?")

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
        try:
            #ok_button = msg.button(QMessageBox.Ok)
            #ok_button.clicked.connect(self.close)
            #msg.exec_()
            response = msg.exec_()

            if response == QMessageBox.Ok:
                QApplication.quit()
                self.do_relaunch_immediately()
            
        except Exception as e:
            self.show_information(self, "Issue", "theme change and exit code not working.")
            
    
    def do_relaunch_immediately(self):
        if getattr(sys, 'frozen', False):
            app_bundle = os.path.abspath(os.path.join(sys.executable, "..", "..", ".."))
            subprocess.Popen(["open", "-n", app_bundle])
            sys.exit(0)
        else:
            os.execv(sys.executable, [sys.executable] + sys.argv)
    
    
    def eventFilter(self, source, event):
        if event.type() == QEvent.MouseButtonPress:
            if source == self.CreateNewProjectButton:
                self.create_project()
                return True
            elif source == self.OpenAProjectButton:
                self.open_exiting_project()
                return True
        return super().eventFilter(source, event)
    
    def create_project(self):
        folder = QFileDialog.getExistingDirectory(self, "Create new Project")
        if folder:
            self.project_manager.add_to_recent_project(folder)
            QMessageBox.information(self, "Project Created", f"Project folder created at: {folder}")
            print(folder)
            self.create_project_folder_structure(folder)
            #self.save_project_metadata(folder)
            self.load_recent_projects_widget_items()
            self.open_project(folder)

    def create_project_folder_structure(self, project_path):
        print(project_path)
        try:
            sounds_folder = os.path.join(project_path, "Sounds")
            os.makedirs(sounds_folder, exist_ok=True)
            export_folder = os.path.join(project_path, "Export")
            os.makedirs(export_folder, exist_ok=True)
            for folder_name in REQQUIRED_SUBFOLDERS:
                subfolder_path = os.path.join(sounds_folder, folder_name)
                os.makedirs(subfolder_path, exist_ok=True)
        except Exception as e:
            print(f"Error creating project folder structure: {e}")
    
    def save_project_metadata(self, project_path):
        project_name = os.path.basename(project_path)
        print(project_name)
        metadata = {
            "project_name": project_name,
            "create_at": datetime.now().isoformat(),
            "version": "1.0.0",
            "folders": ["Bet", "Bonus", "Play", "Resolution", "Shared"],
        }

        #metadata_path = os.path.join(project_path, f"{project_name}.json")
        metadata_path = os.path.join(project_path, f"{project_name}.sds")
        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=4)
            print(f"Project file is saved at {metadata_path}")
        except Exception as e:
            print(f"Error Saving project file: {e}")

    def open_project(self, project_path):
        print(f" opening project {project_path}")
        self.main_app = MainWindow(project_path, self.current_theme)
        print("I will now load interface.")
        self.main_app.setWindowTitle(f"SDS Sound Studio 2025 - {os.path.basename(project_path)}")
        self.main_app.show()
        #elf.close()

    
    def open_exiting_project(self):
        result = QFileDialog.getOpenFileName(self, "Open Project File", "", "SDS Project Files(*.sds)")
        file_path = result[0] if isinstance(result, tuple) else result
        if file_path:
            project_folder = os.path.dirname(file_path)
            self.project_manager.add_to_recent_project(project_folder)
            self.load_recent_projects_widget_items()
            self.main_app = MainWindow(project_folder, self.current_theme)
            self.main_app.show()
            print("i will now open existing project.")
            #self.close()
        else:
            print("couldn't open existing project.")

    def filter_recent_projects(self, text):
        text = text.lower().strip()
        for index in range(self.RecentProjectsListWidget.count()):
            item = self.RecentProjectsListWidget.item(index)
            widget = self.RecentProjectsListWidget.itemWidget(item)

            match = (text in widget.project_name.lower()) or (text in widget.project_path.lower())
            item.setHidden(not match)
        
    def load_recent_projects(self):
        self.projects_model.clear()
        try:
            recent_projects = self.project_manager.get_recent_projects()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load recent projects: {e}")
            recent_projects = []

        for path in recent_projects:
            if os.path.exists(path):
                item = QStandardItem(path)
                item.setEditable(False)
                self.projects_model.appendRow(item)
    
    # This function is for custom widget list item for QListWidgets
    def on_project_item_clicked(self, name, path):
        mouse_buttons = QApplication.mouseButtons()
        if mouse_buttons == Qt.LeftButton:
            print(f"Project Clicked: {name} at {path}")
            self.open_project(path)

    def load_recent_projects_widget_items(self):
        self.RecentProjectsListWidget.clear()
        recent_projects = self.project_manager.get_recent_projects()
        valid_projects = []
        for path in recent_projects:
            if os.path.exists(path):
                name = os.path.basename(path)
                widget = RecentProjectItem(name, path, self.current_theme) # add icon path here
                widget.clicked.connect(self.on_project_item_clicked)

                item = QListWidgetItem()
                item.setSizeHint(widget.sizeHint())
                self.RecentProjectsListWidget.addItem(item)
                self.RecentProjectsListWidget.setItemWidget(item, widget)
                valid_projects.append(path)
        # Auto-remove non-existent projects from recent list
        if valid_projects != recent_projects:
            try:
                self.project_manager.save_recent_projects(valid_projects)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to updated recent projects: {e}")
        
        # Add context menu for removing single project
        self.RecentProjectsListWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.RecentProjectsListWidget.customContextMenuRequested.connect(self.show_recent_project_context_menu)
    
    def show_recent_project_context_menu(self, pos):
        item = self.RecentProjectsListWidget.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        remove_action = menu.addAction("Remove from Recent")
        action = menu.exec_(self.RecentProjectsListWidget.mapToGlobal(pos))
        if action == remove_action:
            row = self.RecentProjectsListWidget.row(item)
            widget = self.RecentProjectsListWidget.itemWidget(item)
            if widget:
                path = widget.project_path
                try:
                    self.project_manager.remove_from_recent_projects(path)
                    self.load_recent_projects_widget_items()
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to remove projects: {e}")
    
    def clear_recent_projects(self):
        reply = QMessageBox.question(
            self,
            "Clear Recent Projects",
            "Are you sure you want to clear the recent projects list?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.project_manager.clear_recent_projects()
            self.load_recent_projects_widget_items()


    
    
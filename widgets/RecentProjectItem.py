from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtGui import QPixmap
from PyQt5 import uic
import os
from PyQt5.QtCore import pyqtSignal
from core.utils import resource_path

class RecentProjectItem(QWidget):
    clicked = pyqtSignal(str, str) # emit project_name and project_path
    def __init__(self, project_name, project_path, current_theme):
        super().__init__()
        # load recent project item widget ui file
        if current_theme == 'dark':
            ui_file = resource_path("ui/ui_recent_project_item_widget_dark.ui")
        else:
            ui_file = resource_path("ui/ui_recent_project_item_widget.ui")
        #ui_file = os.path.join(os.path.dirname(__file__), "../ui/ui_recent_project_item_widget.ui")
        ui_path = os.path.abspath(ui_file)
        #print("recent project item widget:", ui_path)
        uic.loadUi(ui_path, self)

        self.project_name = project_name
        self.project_path = project_path

        self.NameLabel = self.findChild(QLabel, "NameLabel")
        self.PathLabel = self.findChild(QLabel, "PathLabel")

        self.NameLabel.setText(project_name)
        self.PathLabel.setText(project_path)



    def mousePressEvent(self, event):
        self.clicked.emit(self.project_name, self.project_path)
        return super().mousePressEvent(event)
        

        

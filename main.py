import sys
import os, subprocess
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QPixmap
from core.utils import resource_path
from screens.home_screen import HomeScreen

ffmpeg_env_path = resource_path("ffmpeg")
path_list = os.environ.get("PATH", "").split(os.pathsep)
if ffmpeg_env_path not in path_list:
    os.environ["PATH"] += os.pathsep + resource_path("ffmpeg")        

if __name__ == "__main__":
    app = QApplication(sys.argv)

    pixmap = QPixmap(resource_path("icons/waves-icon.png")) # path to splash image
    print(resource_path("icons/waves-icon.png"))
    splash = QSplashScreen(pixmap)
    splash.show()
    app.processEvents()
    # simulation loading process

    window = HomeScreen()
    window.setWindowTitle("SDS Sound Studio 2025")
    window.show()
    
    splash.finish(window)

    sys.exit(app.exec_())

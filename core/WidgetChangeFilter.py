from PyQt5.QtCore import QObject, QEvent, pyqtSignal

class WidgetChangeFilter(QObject):
    any_change = pyqtSignal()

    
    def eventFilter(self, watched, event):
        # QLineEdit: on key press or focus out
        if event.type() in (QEvent.KeyPress, QEvent.FocusOut):
            if watched.metaObject().className() == "QLineEdit":
                self.any_change.emit()
                return False
    
        # QSlider: on mouse move
        if event.type() == QEvent.MouseMove and watched.metaObject().className() == "QSlider":
            if watched.isSliderDown():
                self.any_change.emit()
            return False
    
        # Qcheckbox and QComboBox: on mouse release
        if event.type() == QEvent.MouseButtonRelease and watched.metaObject().className() in ("QCheckBox", "QComboBox"):
            self.any_change.emit()
            return False
        
        # QLabel : dynamic property change when setText() is called
        if event.type() == QEvent.DynamicPropertyChange and watched.metaObject().className() == "QLabel":
            self.any_change.emit()
            return False
        
        return super().eventFilter(watched, event)
            
from core.audio_meter import BarMeter
import numpy as np
import time
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QFont, QLinearGradient
from PyQt5.QtCore import Qt, QRectF, pyqtSignal

class MasterMeter(BarMeter):
    master_peak_value = pyqtSignal(float)
    def __init__(self, parent=None,
                 width=300, height=100,
                 bg_color=QColor(30,30,35),
                 bar_bg=QColor(15,15,15),
                 bar_color_start=QColor(0,255,0),
                 bar_color_mid=QColor(255,255,0),
                 bar_color_end=QColor(255,0,0),
                 text_color=QColor(100,100,110),
                 min_db=-60, max_db=0):
        super().__init__(parent)
        # Fixed dimensions
        self.setMinimumSize(width, height)
        self.setMaximumSize(width, height)
        self._w, self._h = width, height
        # Meter state
        self._value = min_db
        self._peak = min_db
        self.peak_value = min_db
        self._peak_hold = 0
        # Range Settings
        self._min_db = min_db
        self._max_db = max_db
        # Meter Appearance
        self._gradient_colors = [bar_color_start, bar_color_mid, bar_color_end]
        self._bg = bg_color
        self._bar_bg = bar_bg
        self._text_color = text_color

        # Timing and decay
        self._decay_rate = 0.3 # db per second
        self._last_time = time.time()

        # Font for digital readout
        self.active_levels = {}
        self.combined = self._min_db
        self.peak = self._min_db
        self.peak_right = self._min_db
        self.peak_hold = 0
    
    def setMasterValue(self, value):
        now = time.time()
        elapsed = now - self._last_time
        self._last_time = now
        self._peak = max(self._min_db, self._peak - self._decay_rate * elapsed)
        #Clamp and update current value
        v = float(value)
        self._value = max(self._min_db, min(self._max_db, v))
        if self._value > self._peak:
            self._peak = self._value
            self._peak_hold = 30
        # Hold new peak
        if self._value >= -0.5 and not self._clip:
            self._clip = True
            self._clip_Hold = 30
            self.clipDetected.emit()
        self.master_peak_value.emit(self._peak)                                                                                                                                                                                     
        self.update()
    
    #def mastet_update_level(self, audio_id, left_db, right_db):
    def master_update_level(self, audio_id, value):
        self.active_levels[audio_id] = (value)
        self._calculate_peak_levels()
    
    def remove_level(self, audio_id):
        if audio_id in self.active_levels:
            del self.active_levels[audio_id]
            self._calculate_peak_levels()
    
    def _calculate_peak_levels(self):
        if not self.active_levels:
            self.peak_value = self._min_db
            self.setValue(self._min_db)
            return
        # Get all peak values
        values = list(self.active_levels.values())
        # only use float and int values
        values = [v if isinstance(v, (int, float)) else v[0] for v in values]
        self.peak_value = max(self._min_db, min(self._max_db, max(values)))
        self.setMasterValue(self.peak_value)
        # peak hold logic and update peaks
        if self.peak_value > self._peak:
            self._peak = self.peak_value
            self.peak_hold = 30
        elif self.peak_hold > 0:
            self.peak_hold = -1
        else:
            self._peak = max(self._min_db, self._peak - 0.5)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self._bg)

        # Bar dimensions
        pad_x, pad_y = 2, 2
        bar_w = self._w - 2 * pad_x
        bar_h = self._h - 2 * pad_y
        # Draw bar background
        meter_rect = QRectF(pad_x, pad_y, bar_w, bar_h)
        bar_height = meter_rect.height()
        gradient = QLinearGradient(meter_rect.topLeft(), meter_rect.topRight())
        gradient.setColorAt(0.0, self._gradient_colors[0])
        gradient.setColorAt(0.7, self._gradient_colors[1])
        gradient.setColorAt(1.0, self._gradient_colors[2])

        def db_to_norm(db): return max(0.0, min(1.0, (db + 60.0) / 60.0))

        peak_width = db_to_norm(self._value) * meter_rect.width()
        peak_rect = QRectF(meter_rect.left(), meter_rect.top(), peak_width, bar_height)
        painter.fillRect(peak_rect, gradient)

        peak_hold_x = meter_rect.left() + db_to_norm(self._peak) * meter_rect.width()
        painter.setPen(QColor(255, 255, 255, 100))
        painter.drawLine(int(peak_hold_x), int(meter_rect.top()), int(peak_hold_x), int(meter_rect.bottom()))

        if self._clip:
            painter.setPen(Qt.NoPen)
            painter.setBrush(self._clip_color)
            painter.drawRect(QRectF(meter_rect.left(), meter_rect.top() - 8, meter_rect.width(), 6))
        
        
        if self._peak_hold > 0:
            self._peak_hold -= 1
        else:
            self._peak = max(self._min_db, self._peak - 0.5)
        if self._clip_Hold > 0:
            self._clip_Hold -= 1
        else:
            self._clip = False
        
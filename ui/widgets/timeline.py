from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

class TimelineRuler(QWidget):
    position_changed = Signal(int)
    zoom_request = Signal(float, object) # delta, global_pos

    def __init__(self):
        super().__init__()
        self.setFixedHeight(30)
        self.setMinimumWidth(3000)
        self.playhead_x = 0
        self.pixels_per_second = 10
        self.duration = 60
        self.bpm = 120

    def set_playhead(self, x):
        self.playhead_x = x
        self.update()

    def set_zoom(self, px_per_sec):
        self.pixels_per_second = px_per_sec
        self.update_width()
        self.update()

    def set_duration(self, duration):
        self.duration = duration
        self.update_width()
        self.update()

    def update_width(self):
        width = int(self.duration * self.pixels_per_second)
        self.setMinimumWidth(width)

    def wheelEvent(self, event):
        # Delegate zoom to parent/controller
        delta = event.angleDelta().y()
        self.zoom_request.emit(delta, event.globalPosition())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = max(0, event.pos().x())
            self.position_changed.emit(x)
            self.set_playhead(x)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            x = max(0, event.pos().x())
            self.position_changed.emit(x)
            self.set_playhead(x)

    def set_bpm(self, bpm):
        self.bpm = bpm
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QColor(150, 150, 150))
        
        # Calculations
        seconds_per_beat = 60 / self.bpm
        pixels_per_beat = self.pixels_per_second * seconds_per_beat
        
        # Decide interval (beats)
        if pixels_per_beat > 100:
            beat_interval = 1 # Every beat
        elif pixels_per_beat > 50:
            beat_interval = 2 # Every 2 beats
        elif pixels_per_beat > 20:
            beat_interval = 4 # Every bar (4/4)
        elif pixels_per_beat > 5:
            beat_interval = 16 # Every 4 bars
        else:
            beat_interval = 32 # Every 8 bars

        # Draw Beats/Bars
        # 4/4 assumption
        beats_total = int(self.duration / seconds_per_beat) + 1
        
        for beat_idx in range(0, beats_total, beat_interval):
             x = int(beat_idx * pixels_per_beat)
             if x > self.width(): break
             
             is_bar_start = (beat_idx % 4 == 0)
             
             if is_bar_start:
                 height = 15
                 bar_num = (beat_idx // 4) + 1
                 painter.drawText(x + 5, 15, str(bar_num))
             else:
                 height = 8
                 
             painter.drawLine(x, 30, x, 30 - height)

        painter.setPen(QPen(QColor(255, 50, 50), 2))
        playhead_x_int = int(self.playhead_x)
        painter.drawLine(playhead_x_int, 0, playhead_x_int, 30)
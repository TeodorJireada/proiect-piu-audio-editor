from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPalette
from PySide6.QtCore import Qt

class TrackContainer(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("TrackContainer")
        self.pixels_per_second = 10
        self.duration = 60
        self.bpm = 120
        self.setMinimumWidth(3000)

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

    def set_bpm(self, bpm):
        self.bpm = bpm
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        palette = self.palette()
        
        seconds_per_beat = 60 / getattr(self, "bpm", 120)
        pixels_per_beat = self.pixels_per_second * seconds_per_beat
        
        # Decide interval (beats) for grid
        if pixels_per_beat > 100:
            beat_interval = 1 
        elif pixels_per_beat > 50:
            beat_interval = 2 
        elif pixels_per_beat > 20:
            beat_interval = 4 
        elif pixels_per_beat > 5:
            beat_interval = 16 
        else:
            beat_interval = 32 

        beats_total = int(self.duration / seconds_per_beat) + 1
        
        major_color = palette.color(QPalette.WindowText)
        major_color.setAlpha(100)
        
        minor_color = palette.color(QPalette.WindowText)
        minor_color.setAlpha(40)
        
        for beat_idx in range(0, beats_total, beat_interval):
             x = int(beat_idx * pixels_per_beat)
             if x > self.width(): break
             
             is_bar_start = (beat_idx % 4 == 0)
             
             if is_bar_start:
                 painter.setPen(major_color) # Major line
             else:
                 painter.setPen(minor_color) # Minor line
                 
             painter.drawLine(x, 0, x, self.height())

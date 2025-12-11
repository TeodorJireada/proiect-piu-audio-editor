from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt

class TrackContainer(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("TrackContainer")
        self.pixels_per_second = 10
        self.duration = 60
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

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Draw Background Grid
        painter.setPen(QColor(40, 40, 40))
        
        # Determine grid interval based on zoom (similar to timeline)
        if self.pixels_per_second > 10:
            grid_interval = 1
        elif self.pixels_per_second > 2:
            grid_interval = 10
        elif self.pixels_per_second > 0.5:
            grid_interval = 30
        else:
            grid_interval = 60

        # Draw grid lines
        max_sec = int(self.width() / self.pixels_per_second) + 1
        for sec in range(0, max_sec, grid_interval):
            x = int(sec * self.pixels_per_second)
            if x > self.width(): break
            
            # Main tick line
            painter.setPen(QColor(60, 60, 60))
            painter.drawLine(x, 0, x, self.height())

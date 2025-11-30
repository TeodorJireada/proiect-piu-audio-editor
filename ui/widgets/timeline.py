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
        self.pixels_per_second = 100
        self.duration = 60

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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QColor(150, 150, 150))
        
        # Determine tick interval based on zoom level
        if self.pixels_per_second > 150:
            tick_interval = 1
        elif self.pixels_per_second > 50:
            tick_interval = 2
        elif self.pixels_per_second > 20:
            tick_interval = 5
        elif self.pixels_per_second > 10:
            tick_interval = 10
        elif self.pixels_per_second > 2:
            tick_interval = 30
        elif self.pixels_per_second > 0.5:
            tick_interval = 60
        else:
            tick_interval = 300 # 5 mins

        # Draw seconds
        max_sec = int(self.width() / self.pixels_per_second) + 1
        for sec in range(0, max_sec, tick_interval):
            x = int(sec * self.pixels_per_second)
            if x > self.width(): break
            
            height = 15
            painter.drawLine(x, 30, x, 30 - height)
            
            # Format text
            if sec >= 60:
                mins = sec // 60
                secs = sec % 60
                text = f"{mins}m{secs}s" if secs > 0 else f"{mins}m"
            else:
                text = f"{sec}s"
                
            painter.drawText(x + 5, 15, text)
            
            # Draw sub-ticks
            if tick_interval > 1:
                sub_step = 1
                if tick_interval >= 300: sub_step = 60
                elif tick_interval >= 60: sub_step = 10
                elif tick_interval >= 10: sub_step = 5
                
                for sub_sec in range(sec + sub_step, sec + tick_interval, sub_step):
                    x_sub = int(sub_sec * self.pixels_per_second)
                    if x_sub > self.width(): break
                    painter.drawLine(x_sub, 30, x_sub, 30 - 5)
            
            # If zoomed in enough (> 50 px/s), draw half seconds
            elif self.pixels_per_second > 50:
                x_half = int((sec + 0.5) * self.pixels_per_second)
                painter.drawLine(x_half, 30, x_half, 30 - 5)

        painter.setPen(QPen(QColor(255, 50, 50), 2))
        playhead_x_int = int(self.playhead_x)
        painter.drawLine(playhead_x_int, 0, playhead_x_int, 30)
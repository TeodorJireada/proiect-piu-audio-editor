from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

class TimelineRuler(QWidget):
    position_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self.setFixedHeight(30)
        self.setMinimumWidth(3000)
        self.playhead_x = 0

    def set_playhead(self, x):
        self.playhead_x = x
        self.update()

    def mousePressEvent(self, event):
        self.position_changed.emit(event.pos().x())
        self.set_playhead(event.pos().x())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QColor(150, 150, 150))
        for i in range(0, self.width(), 50):
            height = 15 if i % 100 == 0 else 5
            painter.drawLine(i, 30, i, 30 - height)
            if i % 100 == 0 and i > 0:
                painter.drawText(i + 5, 15, str(i // 50))
        painter.setPen(QPen(QColor(255, 50, 50), 2))
        painter.drawLine(self.playhead_x, 0, self.playhead_x, 30)
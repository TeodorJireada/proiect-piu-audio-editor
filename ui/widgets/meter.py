from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt

class StereoMeter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 34)
        self.level_L = 0.0
        self.level_R = 0.0
        
        self.color_normal = QColor("#44aa66") 
        self.color_warning = QColor("#ff8800") 
        self.color_critical = QColor("#FF0000")
        self.bg_color = QColor(30, 30, 30)

    def set_levels(self, left, right):
        self.level_L = min(1.5, max(0.0, left))
        self.level_R = min(1.5, max(0.0, right))
        self.update()

    def get_color(self, level):
        if level > 0.9:
            return self.color_critical
        elif level > 0.7:
            return self.color_warning
        else:
            return self.color_normal

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing) # Enable Antialiasing for rounded corners
        
        # Draw Background (Rounded)
        painter.setBrush(self.bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 4, 4)
        
        # Dimensions
        w = self.width()
        h = self.height()
        bar_h = (h - 2) // 2
        
        # Draw Left (Top)
        l_ratio = min(1.0, self.level_L)
        l_width = int(l_ratio * w)
        color_L = self.get_color(self.level_L)
        
        painter.setBrush(color_L)
        painter.drawRoundedRect(0, 0, l_width, bar_h, 4, 4)
        
        # Draw Right (Bottom)
        r_ratio = min(1.0, self.level_R)
        r_width = int(r_ratio * w)
        color_R = self.get_color(self.level_R)
        
        painter.setBrush(color_R)
        painter.drawRoundedRect(0, bar_h + 2, r_width, bar_h, 4, 4)
        
        # Clip Indicators (Red line at end if > 1.0)
        if self.level_L > 1.0:
            painter.setBrush(self.color_critical)
            painter.drawRoundedRect(w - 5, 0, 5, bar_h, 2, 2)
            
        if self.level_R > 1.0:
            painter.setBrush(self.color_critical)
            painter.drawRoundedRect(w - 5, bar_h + 2, 5, bar_h, 2, 2)

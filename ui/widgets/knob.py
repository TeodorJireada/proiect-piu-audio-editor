from PySide6.QtWidgets import QDial, QMenu
from PySide6.QtGui import QAction, QPainter, QPen, QColor, QPainterPath, QPalette
from PySide6.QtCore import Qt, QRectF

class DraggableDial(QDial):
    def __init__(self, parent=None, default_value=0):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.last_y = 0
        self.drag_sensitivity = 4 # Pixels per step
        self.default_value = default_value

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.last_y = event.y()
            self.sliderPressed.emit()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            delta_y = self.last_y - event.y() 
            # Up means positive change (Right/Increase)
            # Down means negative change (Left/Decrease)
            
            if abs(delta_y) > 0:
                # Direct mapping or sensitivity
                # Let's try 1 unit per 'drag_sensitivity' pixels
                 steps = int(delta_y / self.drag_sensitivity)
                 if steps != 0:
                     self.setValue(self.value() + steps)
                     self.last_y = event.y()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.sliderReleased.emit()
            event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        reset_action = QAction("Reset", self)
        reset_action.triggered.connect(self.reset_to_default)
        menu.addAction(reset_action)
        menu.exec(event.globalPos())

    def reset_to_default(self):
        if self.value() != self.default_value:
             self.sliderPressed.emit() # Simulate start of interaction
             self.setValue(self.default_value)
             self.sliderReleased.emit() # Simulate end of interaction

class BaseModernKnob(DraggableDial):
    def get_normalized_value(self):
        if self.maximum() == self.minimum():
            return 0.0
        return (self.value() - self.minimum()) / (self.maximum() - self.minimum())

class ModernKnobChunky(BaseModernKnob):
    """Bold chunky aesthetics."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        palette = self.palette()

        w, h = self.width(), self.height()
        side = min(w, h)
        painter.translate(w / 2, h / 2)
        scale = side / 100.0
        painter.scale(scale, scale)

        norm = self.get_normalized_value()
        start_angle = 240
        span_angle = -300

        # Background Arc
        painter.setBrush(Qt.NoBrush)
        # Use darker window color
        bg_color = palette.color(QPalette.Window).darker(150)
        painter.setPen(QPen(bg_color, 10, Qt.SolidLine, Qt.FlatCap))
        path_bg = QPainterPath()
        path_bg.arcMoveTo(QRectF(-40, -40, 80, 80), start_angle)
        path_bg.arcTo(QRectF(-40, -40, 80, 80), start_angle, span_angle)
        painter.drawPath(path_bg)

        # Active Arc
        is_bipolar = self.minimum() < 0 and self.maximum() > 0
        
        # Colors - Semantic (Keep distinct or use Highlight)
        # We'll use Highlight for standard, and custom for bipolar to distinguish L/R
        active_color = palette.color(QPalette.Highlight)
        
        if is_bipolar:
            # Bipolar Mode (Center Zero)
            center_angle = start_angle + (span_angle / 2)
            current_angle = start_angle + (span_angle * norm)
            draw_span = current_angle - center_angle
            
            # Colors: Left (val < 0) = Orange, Right (val > 0) = Cyan/Blue
            # Note: norm < 0.5 means Left, norm > 0.5 means Right
            color = QColor("#ff8800") if norm < 0.5 else active_color # Use Highlight for right/positive
            
            if abs(norm - 0.5) > 0.01: # Don't draw if at center
                painter.setPen(QPen(color, 10, Qt.SolidLine, Qt.FlatCap))
                path_val = QPainterPath()
                path_val.arcMoveTo(QRectF(-40, -40, 80, 80), center_angle)
                path_val.arcTo(QRectF(-40, -40, 80, 80), center_angle, draw_span)
                painter.drawPath(path_val)
                
        else:
            # Standard Unipolar Mode
            if norm > 0:
                painter.setPen(QPen(active_color, 10, Qt.SolidLine, Qt.FlatCap))
                path_val = QPainterPath()
                path_val.arcMoveTo(QRectF(-40, -40, 80, 80), start_angle)
                path_val.arcTo(QRectF(-40, -40, 80, 80), start_angle, span_angle * norm)
                painter.drawPath(path_val)

        # Knob Body
        painter.setPen(Qt.NoPen)
        # Use Button color
        painter.setBrush(palette.color(QPalette.Button))
        painter.drawEllipse(-30, -30, 60, 60)

         # Indicator Bar
        painter.save()
        painter.rotate(-150 + (norm * 300))
        # Use BrightText or Text for contrast
        painter.setBrush(palette.color(QPalette.ButtonText))
        painter.drawRoundedRect(QRectF(-2.5, -25, 5, 12), 2, 2) 
        painter.restore()

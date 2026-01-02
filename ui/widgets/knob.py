from PySide6.QtWidgets import QDial, QMenu
from PySide6.QtGui import QAction, QAction
from PySide6.QtCore import Qt

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

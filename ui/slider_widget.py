from PyQt6.QtWidgets import QSlider
from PyQt6.QtCore import Qt

class ClickableSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.orientation() == Qt.Orientation.Horizontal:
                value = self.minimum() + (self.maximum()-self.minimum()) * event.position().x() / self.width()
            else:
                value = self.minimum() + (self.maximum()-self.minimum()) * event.position().y() / self.height()
            self.setValue(int(value))
            self.sliderMoved.emit(int(value))
        super().mousePressEvent(event)

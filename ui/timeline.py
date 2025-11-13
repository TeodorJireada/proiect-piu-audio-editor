from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

class Timeline(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.addWidget(QLabel("Timeline (global position here)"))

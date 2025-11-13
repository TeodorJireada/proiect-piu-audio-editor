from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from PyQt6.QtCore import Qt
from .track_widget import TrackWidget

class TrackArea(QWidget):
    def __init__(self):
        super().__init__()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        vlayout = QVBoxLayout(container)
        vlayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(container)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll)

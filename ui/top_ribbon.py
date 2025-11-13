from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout

class TopRibbon(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        self.play_btn = QPushButton("▶️")
        self.pause_btn = QPushButton("⏸️")
        self.stop_btn = QPushButton("⏹️")

        layout.addWidget(self.play_btn)
        layout.addWidget(self.pause_btn)
        layout.addWidget(self.stop_btn)
        layout.addStretch()

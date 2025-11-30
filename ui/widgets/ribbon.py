from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton
from PySide6.QtCore import Signal

class Ribbon(QFrame):
    play_clicked = Signal()
    stop_clicked = Signal()
    undo_clicked = Signal()
    redo_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("Ribbon")
        self.setFixedHeight(60)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        
        self.btn_undo = QPushButton("Undo")
        self.btn_undo.clicked.connect(self.undo_clicked.emit)
        self.btn_undo.setEnabled(False)

        self.btn_redo = QPushButton("Redo")
        self.btn_redo.clicked.connect(self.redo_clicked.emit)
        self.btn_redo.setEnabled(False)

        btn_stop = QPushButton("Stop")
        btn_stop.clicked.connect(self.stop_clicked.emit)

        self.btn_play = QPushButton("Play")
        self.btn_play.clicked.connect(self.play_clicked.emit)

        layout.addWidget(self.btn_undo)
        layout.addWidget(self.btn_redo)
        layout.addWidget(btn_stop)
        layout.addWidget(self.btn_play)
        layout.addStretch()

    def set_play_state(self, is_playing):
        self.btn_play.setText("Pause" if is_playing else "Play")

    def update_undo_redo_state(self, can_undo, can_redo):
        self.btn_undo.setEnabled(can_undo)
        self.btn_redo.setEnabled(can_redo)

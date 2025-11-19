from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QHBoxLayout, QGridLayout, QWidget

class TrackHeader(QFrame):
    mute_clicked = Signal()
    solo_clicked = Signal()
    delete_clicked = Signal()

    def __init__(self, name, color_hex):
        super().__init__()
        self.setObjectName("TrackHeader")
        self.setFixedHeight(80)
        self.is_muted = False
        self.is_soloed = False
        
        grid = QGridLayout(self)
        grid.setContentsMargins(5, 5, 5, 5)
        grid.setSpacing(5)
        
        # Color Strip
        strip = QFrame()
        strip.setFixedWidth(5)
        strip.setStyleSheet(f"background-color: {color_hex};")
        
        # Name Label
        lbl_name = QLabel(name)
        lbl_name.setStyleSheet("font-weight: bold; font-size: 12px; color: #e0e0e0;")
        
        # Buttons Container
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(2)
        
        self.btn_mute = QPushButton("M")
        self.btn_mute.setFixedSize(24, 24)
        self.btn_mute.clicked.connect(self.toggle_mute_visual)
        
        self.btn_solo = QPushButton("S")
        self.btn_solo.setFixedSize(24, 24)
        self.btn_solo.clicked.connect(self.toggle_solo_visual)
        
        self.btn_delete = QPushButton("X")
        self.btn_delete.setFixedSize(24, 24)
        self.btn_delete.setStyleSheet("""
            QPushButton { background-color: #444; color: #aaa; border: none; }
            QPushButton:hover { background-color: #ff3333; color: white; }
        """)
        self.btn_delete.clicked.connect(self.delete_clicked.emit)

        btn_layout.addWidget(self.btn_mute)
        btn_layout.addWidget(self.btn_solo)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch() 
        
        self.update_styles()

        # Layout widgets
        grid.addWidget(strip, 0, 0, 2, 1, Qt.AlignLeft)
        grid.addWidget(lbl_name, 0, 1)
        grid.addWidget(btn_container, 1, 1)

        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)

    def toggle_mute_visual(self):
        self.is_muted = not self.is_muted
        self.update_styles()
        self.mute_clicked.emit()

    def toggle_solo_visual(self):
        self.is_soloed = not self.is_soloed
        self.update_styles()
        self.solo_clicked.emit() 

    def update_styles(self):
        if self.is_muted:
            self.btn_mute.setStyleSheet("background-color: #ff4444; color: white; border: 1px solid #ff0000;")
        else:
            self.btn_mute.setStyleSheet("background-color: #442222; color: #ffaaaa; border: 1px solid #331111;")

        if self.is_soloed:
            self.btn_solo.setStyleSheet("background-color: #44ff44; color: black; border: 1px solid #00ff00;")
        else:
            self.btn_solo.setStyleSheet("background-color: #224422; color: #aaffaa; border: 1px solid #113311;")
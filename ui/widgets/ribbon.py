from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QButtonGroup, QProgressBar
from PySide6.QtCore import Signal

class Ribbon(QFrame):
    play_clicked = Signal()
    stop_clicked = Signal()
    undo_clicked = Signal()
    redo_clicked = Signal()
    tool_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("Ribbon")
        self.setFixedHeight(60)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        
        # Transport Controls
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
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Tools
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)
        self.tool_group.buttonClicked.connect(self.on_tool_clicked)
        
        tools = ["Move", "Split", "Duplicate", "Delete"]
        for tool in tools:
            btn = QPushButton(tool)
            btn.setCheckable(True)
            if tool == "Move":
                btn.setChecked(True)
            self.tool_group.addButton(btn)
            layout.addWidget(btn)

        # Loading Indicator
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 100)
        self.loading_bar.setValue(0)
        self.loading_bar.setFixedWidth(200)
        self.loading_bar.setVisible(False)
        self.loading_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                text-align: center;
                background-color: #222;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4466aa;
            }
        """)
        layout.addWidget(self.loading_bar)

        layout.addStretch()
    
    def show_loading(self, message="Loading..."):
        self.loading_bar.setFormat(f"{message} %p%")
        self.loading_bar.setValue(0)
        self.loading_bar.setVisible(True)
        
    def update_loading(self, current, total):
        if total > 0:
            percent = int((current / total) * 100)
            self.loading_bar.setValue(percent)
            
    def hide_loading(self):
        self.loading_bar.setVisible(False)

    def on_tool_clicked(self, btn):
        tool_name = btn.text().upper()
        self.tool_changed.emit(tool_name)

    def set_play_state(self, is_playing):
        self.btn_play.setText("Pause" if is_playing else "Play")

    def update_undo_redo_state(self, can_undo, can_redo):
        self.btn_undo.setEnabled(can_undo)
        self.btn_redo.setEnabled(can_redo)

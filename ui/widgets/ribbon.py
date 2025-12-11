from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QButtonGroup, QProgressBar
from PySide6.QtCore import Signal, QSize
from PySide6.QtGui import QIcon

class Ribbon(QFrame):
    save_clicked = Signal()
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
        
        # Helper to create icon buttons
        def create_icon_btn(icon_name, tooltip):
            btn = QPushButton()
            btn.setIcon(QIcon(f"assets/icons/{icon_name}.svg"))
            btn.setIconSize(QSize(24, 24))
            btn.setToolTip(tooltip)
            btn.setObjectName("TransportButton") # For QSS
            btn.setFlat(True)
            return btn

        # Save
        self.btn_save = create_icon_btn("save", "Save Project (Ctrl+S)")
        self.btn_save.clicked.connect(self.save_clicked.emit)
        layout.addWidget(self.btn_save)

        # Separator
        self._add_separator(layout)

        # Transport Controls
        self.btn_undo = create_icon_btn("undo", "Undo (Ctrl+Z)")
        self.btn_undo.clicked.connect(self.undo_clicked.emit)
        self.btn_undo.setEnabled(False)

        self.btn_redo = create_icon_btn("redo", "Redo (Ctrl+Y)")
        self.btn_redo.clicked.connect(self.redo_clicked.emit)
        self.btn_redo.setEnabled(False)

        btn_stop = create_icon_btn("stop", "Stop")
        btn_stop.clicked.connect(self.stop_clicked.emit)

        self.btn_play = create_icon_btn("play", "Play (Space)")
        self.btn_play.clicked.connect(self.play_clicked.emit)

        layout.addWidget(self.btn_undo)
        layout.addWidget(self.btn_redo)
        layout.addWidget(btn_stop)
        layout.addWidget(self.btn_play)
        
        # Separator
        self._add_separator(layout)
        
        # Tools
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)
        self.tool_group.buttonClicked.connect(self.on_tool_clicked)
        
        # Tool Map: (Name, Icon, Tooltip)
        tools = [
            ("Move", "move", "Move Tool (M)"),
            ("Split", "split", "Split Tool (S)"),
            ("Duplicate", "duplicate", "Duplicate Tool (D)"),
            ("Delete", "delete", "Delete Tool (Del)")
        ]
        
        for name, icon, tooltip in tools:
            btn = QPushButton()
            btn.setIcon(QIcon(f"assets/icons/{icon}.svg"))
            btn.setIconSize(QSize(24, 24))
            btn.setToolTip(tooltip)
            btn.setObjectName("ToolButton")
            btn.setCheckable(True)
            # Store tool name in property for retrieval
            btn.setProperty("tool_name", name.upper())
            
            if name == "Move":
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
    
    def _add_separator(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
    
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
        tool_name = btn.property("tool_name")
        self.tool_changed.emit(tool_name)

    def set_play_state(self, is_playing):
        if is_playing:
            self.btn_play.setIcon(QIcon("assets/icons/pause.svg"))
            self.btn_play.setToolTip("Pause (Space)")
        else:
            self.btn_play.setIcon(QIcon("assets/icons/play.svg"))
            self.btn_play.setToolTip("Play (Space)")

    def update_undo_redo_state(self, can_undo, can_redo):
        self.btn_undo.setEnabled(can_undo)
        self.btn_redo.setEnabled(can_redo)

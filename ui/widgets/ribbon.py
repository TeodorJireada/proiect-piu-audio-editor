from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QButtonGroup, QProgressBar, QLabel, QSpacerItem, QSizePolicy, QToolButton, QDialog, QColorDialog, QSpinBox, QCheckBox, QGridLayout, QMenu
from PySide6.QtCore import Signal, QSize, Qt, QTimer, QEvent
from PySide6.QtGui import QIcon, QFontMetrics, QAction

class DraggableSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QSpinBox.NoButtons)
        self.setCursor(Qt.SizeVerCursor)
        self.lineEdit().installEventFilter(self)
        self.last_y = 0
        self.is_dragging = False
        self.drag_start_pos = None

    def eventFilter(self, source, event):
        if source == self.lineEdit():
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self.is_dragging = False
                self.drag_start_pos = event.globalPosition().toPoint()
                self.last_y = event.globalPosition().y()
            
            elif event.type() == QEvent.MouseMove and (event.buttons() & Qt.LeftButton):
                if not self.drag_start_pos: return False
                
                # Check for drag threshold
                if not self.is_dragging:
                    delta_move = (event.globalPosition().toPoint() - self.drag_start_pos).manhattanLength()
                    if delta_move > 5:
                        self.is_dragging = True
                
                if self.is_dragging:
                    delta_y = self.last_y - event.globalPosition().y()
                    if abs(delta_y) >= 2: # Sensitivity
                        steps = int(delta_y / 2)
                        self.setValue(self.value() + steps)
                        self.last_y = event.globalPosition().y()
                    return True # Consume event
            
            elif event.type() == QEvent.MouseButtonRelease:
                if self.is_dragging:
                    self.is_dragging = False
                    return True # Consume event
        
        return super().eventFilter(source, event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        for bpm in range(100, 210, 10):
            action = QAction(f"{bpm} BPM", self)
            action.triggered.connect(lambda checked=False, val=bpm: self.setValue(val))
            menu.addAction(action)
        
        menu.exec(event.globalPos())

class Ribbon(QFrame):
    new_clicked = Signal()
    open_clicked = Signal()
    save_clicked = Signal()
    save_as_clicked = Signal()
    export_clicked = Signal()
    theme_switched = Signal(str) # "DARK", "HIGH_CONTRAST"
    bpm_changed = Signal(int)
    snap_toggled = Signal(bool)

    play_clicked = Signal()
    stop_clicked = Signal()
    loop_toggled = Signal(bool)
    undo_clicked = Signal()
    redo_clicked = Signal()
    tool_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("Ribbon")
        self.setFixedHeight(60)
        
        # Status Timer to reset message
        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self.reset_status)
        
        self.setup_ui()

    def setup_ui(self):
        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(10, 0, 10, 0)
        
        # Define Containers
        left_container = QFrame()
        left_layout = QHBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setAlignment(Qt.AlignLeft)
        
        center_container = QFrame()
        center_layout = QHBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setAlignment(Qt.AlignCenter)
        
        right_container = QFrame()
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setAlignment(Qt.AlignRight)

        # Helper to create text buttons
        def create_text_btn(text, tooltip):
            btn = QPushButton(text)
            btn.setToolTip(tooltip)
            btn.setObjectName("TransportButton") # Reuse styling for transparency/hover
            btn.setFlat(True)
            return btn

        # Helper to create icon buttons
        def create_icon_btn(icon_name, tooltip):
            btn = QPushButton()
            btn.setIcon(QIcon(f"assets/icons/{icon_name}.svg"))
            btn.setIconSize(QSize(24, 24))
            btn.setToolTip(tooltip)
            btn.setObjectName("TransportButton") 
            btn.setFlat(True)
            return btn

        # --- LEFT GROUP ---
        btn_file = create_text_btn("File", "File Operations")
        
        file_menu = QMenu(btn_file)
        
        a_new = QAction("New Project", self)
        a_new.triggered.connect(self.new_clicked.emit)
        file_menu.addAction(a_new)
        
        a_open = QAction("Open Project", self)
        a_open.triggered.connect(self.open_clicked.emit)
        file_menu.addAction(a_open)
        
        file_menu.addSeparator()
        
        a_save = QAction("Save Project (Ctrl+S)", self)
        a_save.triggered.connect(self.save_clicked.emit)
        file_menu.addAction(a_save)
        
        a_save_as = QAction("Save Project As... (Ctrl+Shift+S)", self)
        a_save_as.triggered.connect(self.save_as_clicked.emit)
        file_menu.addAction(a_save_as)
        
        file_menu.addSeparator()
        
        a_export = QAction("Export Audio (WAV)", self)
        a_export.triggered.connect(self.export_clicked.emit)
        file_menu.addAction(a_export)
        
        btn_file.setMenu(file_menu)
        left_layout.addWidget(btn_file)

        self._add_separator(left_layout)
        
        # Theme
        
        btn_theme = create_text_btn("Theme", "Switch Theme")
        theme_menu = QMenu(btn_theme)
        
        a_dark = QAction("Dark", self)
        a_dark.triggered.connect(lambda: self.theme_switched.emit("dark"))
        theme_menu.addAction(a_dark)
        
        a_hc = QAction("High Contrast", self)
        a_hc.triggered.connect(lambda: self.theme_switched.emit("high_contrast"))
        theme_menu.addAction(a_hc)
        
        btn_theme.setMenu(theme_menu)
        left_layout.addWidget(btn_theme)
        
        
        # --- CENTER GROUP ---
        
        # BPM
        lbl_bpm = QLabel("BPM:")
        self.spin_bpm = DraggableSpinBox()
        self.spin_bpm.setRange(20, 300)
        self.spin_bpm.setValue(120)
        self.spin_bpm.setFixedWidth(60)
        self.spin_bpm.valueChanged.connect(self.bpm_changed.emit)
        
        center_layout.addWidget(lbl_bpm)
        center_layout.addWidget(self.spin_bpm)
        
        # Snap
        self.btn_snap = create_text_btn("Snap", "Toggle Snap to Grid")
        self.btn_snap.setCheckable(True)
        self.btn_snap.setChecked(True) # Default ON
        self.btn_snap.clicked.connect(lambda c: self.snap_toggled.emit(c))
        self.btn_snap.setStyleSheet("""
            QPushButton:checked {
                background-color: #4466aa;
                border-radius: 4px;
            }
        """)
        
        center_layout.addSpacing(10)
        center_layout.addWidget(self.btn_snap)
        
        self._add_separator(center_layout)

        # Transport
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

        # Loop
        # Loop
        self.btn_loop = create_icon_btn("loop", "Toggle Loop")
        self.btn_loop.setCheckable(True)
        self.btn_loop.setChecked(True)
        self.btn_loop.clicked.connect(lambda c: self.loop_toggled.emit(c))
        self.btn_loop.setStyleSheet("""
            QPushButton:checked {
                background-color: #4466aa;
                border-radius: 4px;
            }
        """)

        center_layout.addWidget(self.btn_undo)
        center_layout.addWidget(self.btn_redo)
        center_layout.addWidget(btn_stop)
        center_layout.addWidget(self.btn_play)
        center_layout.addWidget(self.btn_loop)
        
        self._add_separator(center_layout)

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
            btn.setProperty("tool_name", name.upper())
            
            if name == "Move":
                btn.setChecked(True)
                
            self.tool_group.addButton(btn)
            center_layout.addWidget(btn)


        # --- RIGHT GROUP ---
        # Loading Indicator (Right side)
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 100)
        self.loading_bar.setValue(0)
        self.loading_bar.setFixedWidth(200)
        self.loading_bar.setFormat(" STATUS: READY")
        self.loading_bar.setVisible(True) # Always visible
        self.loading_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 4px;
                text-align: left; /* Left align */
                background-color: #111;
                color: #88ccff;
                font-family: monospace;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #4466aa;
            }
        """)
        right_layout.addWidget(self.loading_bar)


        # Add containers to Grid
        main_layout.addWidget(left_container, 0, 0, Qt.AlignLeft)
        main_layout.addWidget(center_container, 0, 1, Qt.AlignCenter)
        main_layout.addWidget(right_container, 0, 2, Qt.AlignRight)
        
        # Stretch factors
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 0)
        main_layout.setColumnStretch(2, 1)

    def _add_separator(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
    
    def show_loading(self, message="Loading..."):
        self.loading_bar.setFormat(f" {message} %p%")
        self.loading_bar.setValue(0)
        self.loading_bar.setVisible(True)
        
    def update_loading(self, current, total):
        if total > 0:
            percent = int((current / total) * 100)
            self.loading_bar.setValue(percent)
            
    def hide_loading(self):
        # Reset to ready state instead of hiding
        self.loading_bar.setValue(0)
        self.loading_bar.setFormat(" STATUS: READY")

    def set_status(self, message, timeout=3000):
        # Ellipsize text if too long
        metrics = QFontMetrics(self.loading_bar.font())
        prefix = " "
        prefix_width = metrics.horizontalAdvance(prefix)
        # Subtract padding/borders
        available = self.loading_bar.width() - 20 - prefix_width
        
        elided_message = metrics.elidedText(message, Qt.ElideRight, available)
        
        self.loading_bar.setFormat(prefix + elided_message)
        self.status_timer.start(timeout)
        
    def reset_status(self):
        self.loading_bar.setFormat(" STATUS: READY")

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

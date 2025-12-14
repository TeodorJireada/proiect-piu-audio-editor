from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QButtonGroup, QProgressBar, QLabel, QSpacerItem, QSizePolicy, QToolButton, QDialog, QColorDialog, QSpinBox, QCheckBox
from PySide6.QtCore import Signal, QSize
from PySide6.QtGui import QIcon

class Ribbon(QFrame):
    new_clicked = Signal()
    open_clicked = Signal()
    save_clicked = Signal()
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
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0) # Add margins
        
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

        # --- File Group ---
        btn_new = create_text_btn("New", "New Project")
        btn_new.clicked.connect(self.new_clicked.emit)
        layout.addWidget(btn_new)

        btn_open = create_text_btn("Open", "Open Project")
        btn_open.clicked.connect(self.open_clicked.emit)
        layout.addWidget(btn_open)

        # Save (Icon + Text or just Icon? User said remove current save btn. 
        # But implies integrating it. I'll make it consistent with New/Open for now, 
        # or stick to Icon if I have it. Let's use Text to match others or Icon? 
        # 'Check assets/icons': we have save.svg.
        # Let's use the icon for Save since we have it, but maybe add text? 
        # Or just keep it simple. Mixed is okay. 
        # User said "remove current save button... integrate them...". 
        # I will use text for all "File" operations for consistency.)
        btn_save = create_text_btn("Save", "Save Project (Ctrl+S)")
        btn_save.clicked.connect(self.save_clicked.emit)
        layout.addWidget(btn_save)

        btn_export = create_text_btn("Export", "Export Audio (WAV)")
        btn_export.clicked.connect(self.export_clicked.emit)
        layout.addWidget(btn_export)

        self._add_separator(layout)
        
        # --- View Group ---
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        
        btn_theme = create_text_btn("Theme", "Switch Theme")
        theme_menu = QMenu(btn_theme)
        
        a_dark = QAction("Dark", self)
        a_dark.triggered.connect(lambda: self.theme_switched.emit("dark"))
        theme_menu.addAction(a_dark)
        
        a_hc = QAction("High Contrast", self)
        a_hc.triggered.connect(lambda: self.theme_switched.emit("high_contrast"))
        theme_menu.addAction(a_hc)
        
        btn_theme.setMenu(theme_menu)
        layout.addWidget(btn_theme)

        self._add_separator(layout)

        # --- Transport Controls ---
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

        # Loop Toggle
        self.btn_loop = QPushButton("Loop")
        self.btn_loop.setCheckable(True)
        self.btn_loop.setChecked(True) # Default ON
        self.btn_loop.clicked.connect(lambda c: self.loop_toggled.emit(c))
        self.btn_loop.setFixedHeight(30)
        # Style for active state
        self.btn_loop.setStyleSheet("""
            QPushButton:checked {
                background-color: #4466aa;
                color: white;
                border-radius: 4px;
            }
        """)

        layout.addWidget(self.btn_undo)
        layout.addWidget(self.btn_redo)
        layout.addWidget(btn_stop)
        layout.addWidget(self.btn_play)
        layout.addWidget(self.btn_loop)
        
        # Separator
        self._add_separator(layout)
        
        # --- BPM Control ---
        bpm_container = QFrame()
        bpm_layout = QHBoxLayout(bpm_container)
        bpm_layout.setContentsMargins(5, 5, 5, 5)
        
        lbl_bpm = QLabel("BPM:")
        self.spin_bpm = QSpinBox()
        self.spin_bpm.setRange(20, 300)
        self.spin_bpm.setValue(120)
        self.spin_bpm.setFixedWidth(60)
        self.spin_bpm.valueChanged.connect(self.bpm_changed.emit)
        
        bpm_layout.addWidget(lbl_bpm)
        bpm_layout.addWidget(self.spin_bpm)
        
        # Snap Checkbox
        self.chk_snap = QCheckBox("Snap")
        self.chk_snap.setChecked(True) # Default ON
        self.chk_snap.toggled.connect(self.snap_toggled.emit)
        bpm_layout.addSpacing(10)
        bpm_layout.addWidget(self.chk_snap)
        
        layout.addWidget(bpm_container)

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

from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QButtonGroup, QProgressBar, QLabel, QSpacerItem, QSizePolicy, QToolButton, QDialog, QColorDialog, QSpinBox, QCheckBox, QGridLayout, QMenu
from PySide6.QtCore import Signal, QSize, Qt, QTimer, QEvent, QPointF
from PySide6.QtGui import QIcon, QFontMetrics, QAction, QPixmap, QPainter, QPolygonF, QColor, QPen, QFontDatabase

from ui.theme_manager import ThemeManager
from ui.widgets.timeline_slider import TimelineSlider
from ui.widgets.meter import StereoMeter

class DraggableSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        QFontDatabase.addApplicationFont("assets/fonts/digital-7/digital-7.ttf")
        QFontDatabase.addApplicationFont("assets/fonts/digital-7/digital-7 (italic).ttf")
        
        self.setButtonSymbols(QSpinBox.NoButtons)
        self.setCursor(Qt.SizeVerCursor)
        self.lineEdit().installEventFilter(self)
        self.drag_start_pos = None
        self.setFixedHeight(34) # Match buttons
        self.setStyleSheet("""
            DraggableSpinBox {
                font-family: 'Digital-7'; 
                font-size: 24px; 
                font-weight: bold;
                background-color: #cccccc;
                color: #222222;
                border: 1px solid #999999;
                border-radius: 4px;
            }
        """)

    def eventFilter(self, source, event):
        if source == self.lineEdit():
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self.is_dragging = False
                self.drag_start_pos = event.globalPosition().toPoint()
                self.last_y = event.globalPosition().y()
            
            elif event.type() == QEvent.MouseMove and (event.buttons() & Qt.LeftButton):
                if not self.drag_start_pos: return False
                
                if not self.is_dragging:
                    delta_move = (event.globalPosition().toPoint() - self.drag_start_pos).manhattanLength()
                    if delta_move > 5:
                        self.is_dragging = True
                
                if self.is_dragging:
                    delta_y = self.last_y - event.globalPosition().y()
                    if abs(delta_y) >= 2: 
                        steps = int(delta_y / 2)
                        self.setValue(self.value() + steps)
                        self.last_y = event.globalPosition().y()
                    return True
            
            elif event.type() == QEvent.MouseButtonRelease:
                if self.is_dragging:
                    self.is_dragging = False
                    return True
                
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
    theme_switched = Signal(str)
    bpm_changed = Signal(int)
    snap_toggled = Signal(bool)

    play_clicked = Signal()
    stop_clicked = Signal()
    loop_toggled = Signal(bool)
    undo_clicked = Signal()
    redo_clicked = Signal()
    tool_changed = Signal(str)
    
    playhead_seeked = Signal(float)

    def __init__(self):
        super().__init__()
        self.setObjectName("Ribbon")
        self.setFixedHeight(60)
        
        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self.reset_status)
        
        self.current_theme = ThemeManager.get_saved_theme()
        self.setup_ui()

    def update_playhead_position(self, current_time, total_duration):
        self.timeline_slider.set_duration(total_duration)
        self.timeline_slider.update_position(current_time)

    def update_master_levels(self, left, right):
        if hasattr(self, 'meter'):
            self.meter.set_levels(left, right)

    def load_icon(self, icon_name, theme_name=None, color_override=None):
        if theme_name is None:
             theme_name = self.current_theme
             
        if color_override:
            color = color_override
        else:
            color = ThemeManager.get_icon_color(theme_name)
        
        path = f"assets/icons/{icon_name}.svg"
        try:
            with open(path, "r") as f:
                svg_content = f.read()
            
            colored_svg_normal = svg_content.replace("#e0e0e0", color)
            colored_svg_normal = colored_svg_normal.replace("#000000", color)
            
            colored_svg_normal = colored_svg_normal.replace('width="24"', 'width="128"')
            colored_svg_normal = colored_svg_normal.replace('height="24"', 'height="128"')
            
            pixmap = QPixmap()
            pixmap.loadFromData(colored_svg_normal.encode("utf-8"))
            
            icon = QIcon()
            icon.addPixmap(pixmap, QIcon.Normal, QIcon.Off)
            
            dark_color = "#111111"
            dark_svg = svg_content.replace("#e0e0e0", dark_color)
            dark_svg = dark_svg.replace("#000000", dark_color)
            dark_svg = dark_svg.replace('width="24"', 'width="128"')
            dark_svg = dark_svg.replace('height="24"', 'height="128"')
            
            pixmap_on = QPixmap()
            pixmap_on.loadFromData(dark_svg.encode("utf-8"))
            
            icon.addPixmap(pixmap_on, QIcon.Normal, QIcon.On)
            
            disabled_color = "#555555"
            disabled_svg = svg_content.replace("#e0e0e0", disabled_color)
            disabled_svg = disabled_svg.replace("#000000", disabled_color)
            disabled_svg = disabled_svg.replace('width="24"', 'width="128"')
            disabled_svg = disabled_svg.replace('height="24"', 'height="128"')
            
            pixmap_disabled = QPixmap()
            pixmap_disabled.loadFromData(disabled_svg.encode("utf-8"))
            
            icon.addPixmap(pixmap_disabled, QIcon.Disabled, QIcon.Off)
            icon.addPixmap(pixmap_disabled, QIcon.Disabled, QIcon.On)
            
            return icon
        except Exception as e:
            print(f"Error loading icon {icon_name}: {e}")
            return QIcon(path) # Fallback

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

        def create_icon_btn(icon_name, tooltip):
            btn = QPushButton()
            btn.setIcon(self.load_icon(icon_name))
            btn.setIconSize(QSize(24, 24))
            btn.setToolTip(tooltip)
            btn.setObjectName("TransportButton") 
            btn.setFlat(True)
            btn.setFixedSize(34, 34)
            return btn

        # LEFT GROUP
        
        # File
        self.btn_file = create_icon_btn("file", "File Operations")
        self.btn_file.setFixedWidth(50)
        
        file_menu = QMenu(self.btn_file)
        
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
        
        self.btn_file.setMenu(file_menu)
        left_layout.addWidget(self.btn_file)
        
        # Theme
        self.btn_theme = create_icon_btn("theme", "Switch Theme")
        self.btn_theme.setFixedWidth(50)
        theme_menu = QMenu(self.btn_theme)
        
        a_dark = QAction("Dark", self)
        a_dark.triggered.connect(lambda: self.on_theme_switched("dark"))
        theme_menu.addAction(a_dark)

        a_light = QAction("Light", self)
        a_light.triggered.connect(lambda: self.on_theme_switched("light"))
        theme_menu.addAction(a_light)
        
        a_hc = QAction("High Contrast", self)
        a_hc.triggered.connect(lambda: self.on_theme_switched("high_contrast"))
        theme_menu.addAction(a_hc)
        
        self.btn_theme.setMenu(theme_menu)
        left_layout.addWidget(self.btn_theme)
        
        left_layout.addSpacing(10)

        # Undo/Redo
        self.btn_undo = create_icon_btn("undo", "Undo (Ctrl+Z)")
        self.btn_undo.clicked.connect(self.undo_clicked.emit)
        self.btn_undo.setEnabled(False)

        self.btn_redo = create_icon_btn("redo", "Redo (Ctrl+Y)")
        self.btn_redo.clicked.connect(self.redo_clicked.emit)
        self.btn_redo.setEnabled(False)
        
        left_layout.addWidget(self.btn_undo)
        left_layout.addWidget(self.btn_redo)
        
        left_layout.addSpacing(10)

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
            btn.setIcon(self.load_icon(icon))
            btn.setIconSize(QSize(24, 24))
            btn.setToolTip(tooltip)
            btn.setObjectName("ToolButton")
            btn.setCheckable(True)
            btn.setProperty("tool_name", name.upper())
            btn.setFixedSize(34, 34) # Square
            
            if name == "Move":
                btn.setChecked(True)
                
            self.tool_group.addButton(btn)
            left_layout.addWidget(btn)
            
        left_layout.addSpacing(10)
        
        # Snap
        self.btn_snap = create_icon_btn("magnet", "Toggle Snap to Grid")
        self.btn_snap.setCheckable(True)
        self.btn_snap.setChecked(True)
        self.btn_snap.clicked.connect(lambda c: self.snap_toggled.emit(c))
        left_layout.addWidget(self.btn_snap)


        # CENTER GROUP

        # Transport
        self.btn_loop = create_icon_btn("loop", "Toggle Loop")
        self.btn_loop.setCheckable(True)
        self.btn_loop.setChecked(True)
        self.btn_loop.clicked.connect(lambda c: self.loop_toggled.emit(c))

        self.btn_stop = create_icon_btn("stop", "Stop")
        self.btn_stop.clicked.connect(self.stop_clicked.emit)

        self.btn_play = create_icon_btn("play", "Play (Space)")
        self.btn_play.clicked.connect(self.play_clicked.emit)
        
        center_layout.addWidget(self.btn_loop)
        center_layout.addWidget(self.btn_stop)
        center_layout.addWidget(self.btn_play)
        
        center_layout.addSpacing(15)
        
        # BPM
        self.spin_bpm = DraggableSpinBox()
        self.spin_bpm.setRange(20, 300)
        self.spin_bpm.setValue(120)
        self.spin_bpm.setFixedWidth(60)
        self.spin_bpm.valueChanged.connect(self.bpm_changed.emit)
        
        center_layout.addWidget(self.spin_bpm)
        
        center_layout.addSpacing(15)

        # Timeline Slider
        self.timeline_slider = TimelineSlider()
        self.timeline_slider.seek_requested.connect(self.playhead_seeked.emit)
        self.timeline_slider.setToolTip("Timeline Pointer")
        self.timeline_slider.setFixedWidth(200)
        center_layout.addWidget(self.timeline_slider)
        
        
        # RIGHT GROUP
        
        # Stereo Meter
        self.meter = StereoMeter()
        self.meter.setToolTip("Master Output Levels")
        right_layout.addWidget(self.meter)
        
        # Loading Indicator (Right side)
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 100)
        self.loading_bar.setValue(0)
        self.loading_bar.setFixedWidth(200)
        self.loading_bar.setFixedHeight(34)
        self.loading_bar.setFormat(" STATUS: READY")
        self.loading_bar.setVisible(True) # Always visible
        self.loading_bar.setStyleSheet("""
            QProgressBar {
                font-family: 'Digital-7';
                font-size: 20px;
                font-weight: bold;
                font-style: italic;
                text-align: left;
                border-radius: 4px;
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

    def refresh_icons(self, theme_name):
        self.current_theme = theme_name
        
        # Update Main Buttons
        self.btn_file.setIcon(self.load_icon("file", theme_name))
        self.btn_theme.setIcon(self.load_icon("theme", theme_name))
        self.btn_undo.setIcon(self.load_icon("undo", theme_name))
        self.btn_redo.setIcon(self.load_icon("redo", theme_name))
        self.btn_stop.setIcon(self.load_icon("stop", theme_name))
        self.btn_loop.setIcon(self.load_icon("loop", theme_name))
        self.btn_snap.setIcon(self.load_icon("magnet", theme_name))
        
        # Play/Pause needs logic check
        is_playing = self.btn_play.toolTip().startswith("Pause")
        icon_name = "pause" if is_playing else "play"
        self.btn_play.setIcon(self.load_icon(icon_name, theme_name))
        
        # Tool Buttons
        for btn in self.tool_group.buttons():
            name = btn.property("tool_name").lower()
            btn.setIcon(self.load_icon(name, theme_name))

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

    def on_theme_switched(self, theme_name):
        self.refresh_icons(theme_name)
        self.theme_switched.emit(theme_name)

    def set_play_state(self, is_playing):
        if is_playing:
            self.btn_play.setIcon(self.load_icon("pause", color_override="#44aa66"))
            self.btn_play.setToolTip("Pause (Space)")
        else:
            self.btn_play.setIcon(self.load_icon("play"))
            self.btn_play.setToolTip("Play (Space)")

    def update_undo_redo_state(self, can_undo, can_redo):
        self.btn_undo.setEnabled(can_undo)
        self.btn_redo.setEnabled(can_redo)

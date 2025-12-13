from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QHBoxLayout, QGridLayout, QWidget, QSizePolicy, QMenu
from PySide6.QtGui import QAction, QColor

class ColorStrip(QFrame):
    clicked = Signal()
    color_selected = Signal(str)

    def __init__(self, color_hex):
        super().__init__()
        self.setFixedWidth(8) # Slightly wider for better clickability
        self.setCursor(Qt.PointingHandCursor)
        self.current_color = color_hex
        self.update_color(color_hex)
        
    def update_color(self, color_hex):
        self.current_color = color_hex
        self.setStyleSheet(f"background-color: {color_hex}; border: none;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.show_color_menu(event.globalPos())
            self.clicked.emit()

    def show_color_menu(self, pos):
        menu = QMenu(self)
        
        # Consistent Palette
        colors = {
            "Blue": "#4466aa",
            "Red": "#aa4444",
            "Green": "#44aa66",
            "Orange": "#cc8833",
            "Purple": "#8844aa",
            "Teal": "#339999",
            "Yellow": "#aaaa33",
            "Gray": "#666666"
        }
        
        for name, hex_code in colors.items():
            action = QAction(name, self)
            # Create a small pixmap or icon for color? 
            # For now, just text, maybe color the text or background?
            # Standard QAction doesn't easily support colored background without styling the whole menu.
            # We'll just stick to names for simplicity/consistency, user can try them.
            
            action.triggered.connect(lambda checked=False, c=hex_code: self.handle_color_selection(c))
            menu.addAction(action)
            
        menu.exec(pos)

    def handle_color_selection(self, color_hex):
        self.update_color(color_hex)
        self.color_selected.emit(color_hex)

class TrackHeader(QFrame):
    mute_clicked = Signal()
    solo_clicked = Signal()
    delete_clicked = Signal()
    color_changed = Signal(str) # New Signal

    def __init__(self, name, color_hex):
        super().__init__()
        self.setObjectName("TrackHeader")
        self.setFixedHeight(80)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.is_muted = False
        self.is_soloed = False
        
        # Main Layout (Horizontal to put Strip on far left)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0) # NO MARGINS for flush fit
        main_layout.setSpacing(0)
        
        # Color Strip
        self.color_strip = ColorStrip(color_hex)
        self.color_strip.color_selected.connect(self.color_changed.emit)
        main_layout.addWidget(self.color_strip)
        
        # Content Container (for the rest of the header)
        content_widget = QWidget()
        main_layout.addWidget(content_widget)
        
        # Grid for content
        grid = QGridLayout(content_widget)
        grid.setContentsMargins(5, 5, 5, 5)
        grid.setSpacing(5)
        
        # Name Label
        self.lbl_name = QLabel(name)
        self.lbl_name.setObjectName("TrackNameLabel")
        self.lbl_name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        
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
        self.btn_delete.setObjectName("TrackDeleteButton")
        self.btn_delete.setFixedSize(24, 24)
        self.btn_delete.clicked.connect(self.delete_clicked.emit)

        btn_layout.addWidget(self.btn_mute)
        btn_layout.addWidget(self.btn_solo)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch() 
        
        self.update_styles()

        # Layout widgets in Grid
        grid.addWidget(self.lbl_name, 0, 0)
        grid.addWidget(btn_container, 1, 0)

    def toggle_mute_visual(self):
        self.is_muted = not self.is_muted
        self.update_styles()
        self.mute_clicked.emit()

    def toggle_solo_visual(self):
        self.is_soloed = not self.is_soloed
        self.update_styles()
        self.solo_clicked.emit() 

    def update_styles(self):
        self.btn_mute.setProperty("muted", self.is_muted)
        self.btn_mute.style().unpolish(self.btn_mute)
        self.btn_mute.style().polish(self.btn_mute)

        self.btn_solo.setProperty("soloed", self.is_soloed)
        self.btn_solo.style().unpolish(self.btn_solo)
        self.btn_solo.style().polish(self.btn_solo)

    def set_title(self, title):
        self.lbl_name.setText(title)

    def set_muted(self, muted):
        self.is_muted = muted
        self.update_styles()

    def set_soloed(self, soloed):
        self.is_soloed = soloed
        self.update_styles()
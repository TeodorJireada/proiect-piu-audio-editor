from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QHBoxLayout, QGridLayout, QWidget, QSizePolicy, QMenu, QSlider, QDial
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
            action.triggered.connect(lambda checked=False, c=hex_code: self.handle_color_selection(c))
            menu.addAction(action)
            
        menu.exec(pos)

    def handle_color_selection(self, color_hex):
        self.update_color(color_hex)
        self.color_selected.emit(color_hex)

from ui.widgets.knob import DraggableDial

class TrackHeader(QFrame):
    mute_clicked = Signal()
    solo_clicked = Signal()
    delete_clicked = Signal()
    slider_pressed = Signal() # New signal for undo start state
    
    pan_changed = Signal(float)
    pan_set = Signal(float)
    dial_pressed = Signal()
    
    volume_changed = Signal(float) # Emitted on drag (real-time)
    volume_set = Signal(float)     # Emitted on release (undo)
    color_changed = Signal(str) # New Signal
    clicked = Signal()
    fx_requested = Signal() # New Signal
    fx_bypass_toggled = Signal(bool)

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
        
        # FX Button
        self.btn_fx = QPushButton("FX")
        self.btn_fx.setCheckable(False)
        self.btn_fx.setFixedSize(40, 20) # Made wider (30 -> 40)
        self.btn_fx.setStyleSheet("""
            QPushButton { background-color: #333; border: 1px solid #555; border-radius: 2px; font-size: 10px; }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """)
        self.btn_fx.clicked.connect(self.on_fx_clicked)
        btn_layout.addWidget(self.btn_fx)

        # FX Bypass
        self.btn_fx_bypass = QPushButton("Ø")
        self.btn_fx_bypass.setFixedSize(20, 20)
        self.btn_fx_bypass.setCheckable(True)
        self.btn_fx_bypass.setToolTip("Bypass All Effects")
        self.btn_fx_bypass.setStyleSheet("""
            QPushButton { background-color: #333; border: 1px solid #555; border-radius: 2px; color: #aaa; font-size: 10px; font-weight: bold; }
            QPushButton:checked { background-color: #aa4444; color: #fff; border: 1px solid #cc5555; }
            QPushButton:hover { background-color: #444; }
        """)
        self.btn_fx_bypass.clicked.connect(self.on_bypass_clicked)
        btn_layout.addWidget(self.btn_fx_bypass)

        self.btn_delete = QPushButton("X")
        self.btn_delete.setObjectName("TrackDeleteButton")
        self.btn_delete.setFixedSize(24, 24)
        self.btn_delete.clicked.connect(self.delete_clicked.emit)

        btn_layout.addWidget(self.btn_mute)
        btn_layout.addWidget(self.btn_solo)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch() # Push slider to right
        
        # Pan Dial
        self.dial_pan = DraggableDial(default_value=0)
        self.dial_pan.setRange(-100, 100)
        self.dial_pan.setValue(0)
        self.dial_pan.setFixedSize(30, 30)
        self.dial_pan.setToolTip("Pan: Center")
        
        self.dial_pan.valueChanged.connect(self.on_dial_value_changed)
        self.dial_pan.sliderPressed.connect(self.dial_pressed.emit)
        self.dial_pan.sliderReleased.connect(self.on_dial_released)
        
        btn_layout.addWidget(self.dial_pan)
        
        # Volume Slider
        self.slider_volume = QSlider(Qt.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(100)
        self.slider_volume.setFixedWidth(80) 
        self.slider_volume.setToolTip("Volume: 100%")
        
        # Connect signals
        self.slider_volume.valueChanged.connect(self.on_slider_value_changed)
        self.slider_volume.sliderPressed.connect(self.slider_pressed.emit)
        self.slider_volume.sliderReleased.connect(self.on_slider_released)

        btn_layout.addWidget(self.slider_volume) 
        
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

    def on_slider_value_changed(self, value):
        volume = value / 100.0
        self.slider_volume.setToolTip(f"Volume: {value}%")
        self.volume_changed.emit(volume)

    def on_slider_released(self):
        volume = self.slider_volume.value() / 100.0
        self.volume_set.emit(volume)

    def set_volume(self, volume):
        self.slider_volume.blockSignals(True)
        val = int(volume * 100)
        self.slider_volume.setValue(val)
        self.slider_volume.setToolTip(f"Volume: {val}%")
        self.slider_volume.blockSignals(False)

    def on_dial_value_changed(self, value):
        pan = value / 100.0
        text = "Center"
        if pan < 0: text = f"Left {int(abs(pan)*100)}%"
        elif pan > 0: text = f"Right {int(abs(pan)*100)}%"
        
        self.dial_pan.setToolTip(f"Pan: {text}")
        self.pan_changed.emit(pan)

    def on_dial_released(self):
        pan = self.dial_pan.value() / 100.0
        self.pan_set.emit(pan)

    def set_pan(self, pan):
        self.dial_pan.blockSignals(True)
        val = int(pan * 100)
        self.dial_pan.setValue(val)
        
        text = "Center"
        self.dial_pan.setToolTip(f"Pan: {text}")
        
        self.dial_pan.blockSignals(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            super().mousePressEvent(event)

    def on_fx_clicked(self):
        self.fx_requested.emit()

    def on_bypass_clicked(self, checked):
        self.fx_bypass_toggled.emit(checked)
    
    def set_bypass(self, bypassed):
        self.btn_fx_bypass.setChecked(bypassed)

    def update_fx_count(self, count):
        if count > 0:
            self.btn_fx.setText(f"FX ({count})")
            # Optional: Highlight color if active effects?
            self.btn_fx.setStyleSheet("""
                QPushButton { background-color: #445566; border: 1px solid #667788; border-radius: 2px; font-size: 10px; }
                QPushButton:hover { background-color: #556677; }
                QPushButton:pressed { background-color: #334455; }
            """)
        else:
            self.btn_fx.setText("FX")
            self.btn_fx.setStyleSheet("""
                QPushButton { background-color: #333; border: 1px solid #555; border-radius: 2px; font-size: 10px; }
                QPushButton:hover { background-color: #444; }
                QPushButton:pressed { background-color: #666; }
            """)
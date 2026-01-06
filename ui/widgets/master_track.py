from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QHBoxLayout, QGridLayout, QWidget, QSizePolicy
from ui.widgets.slider import ModernSlider
from ui.widgets.knob import ModernKnobChunky

class MasterTrackWidget(QFrame):
    # Signals identical to TrackHeader where possible for compatibility
    pan_changed = Signal(float)
    pan_set = Signal(float)
    dial_pressed = Signal()
    
    volume_changed = Signal(float)
    volume_set = Signal(float)
    slider_pressed = Signal()
    fx_requested = Signal()
    fx_bypass_toggled = Signal(bool)

    def __init__(self, audio_track, parent=None):
        super().__init__(parent)
        self.audio_track = audio_track
        self.setObjectName("MasterTrackWidget")
        self.setFixedHeight(40) # Matches top-left corner height
        self.setMinimumWidth(0) 
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Styles
        # self.setStyleSheet(...) -> Moved to QSS

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Label
        self.lbl_name = QLabel("MASTER")
        self.lbl_name.setFixedWidth(60)
        layout.addWidget(self.lbl_name)
        
        # FX Button
        self.btn_fx = QPushButton("FX")
        self.btn_fx.setObjectName("FXButton")
        self.btn_fx.setFixedSize(40, 20)
        self.btn_fx.clicked.connect(self.fx_requested.emit)
        layout.addWidget(self.btn_fx)
        
        # FX Bypass
        self.btn_fx_bypass = QPushButton("Ø")
        self.btn_fx_bypass.setObjectName("FXBypassButton")
        self.btn_fx_bypass.setFixedSize(20, 20)
        self.btn_fx_bypass.setCheckable(True)
        self.btn_fx_bypass.setToolTip("Bypass Master Effects")
        self.btn_fx_bypass.clicked.connect(self.on_bypass_clicked)
        layout.addWidget(self.btn_fx_bypass)
        
        layout.addStretch() # Push controls to right
        
        # Pan Dial
        self.dial_pan = ModernKnobChunky(default_value=0)
        self.dial_pan.setRange(-100, 100)
        self.dial_pan.setValue(0)
        self.dial_pan.setFixedSize(30, 30) # Match TrackHeader
        self.dial_pan.setToolTip("Master Pan: Center")
        
        self.dial_pan.valueChanged.connect(self.on_dial_value_changed)
        self.dial_pan.sliderPressed.connect(self.dial_pressed.emit)
        self.dial_pan.sliderReleased.connect(self.on_dial_released)
        
        layout.addWidget(self.dial_pan)
        
        # Volume Slider
        self.slider_volume = ModernSlider(Qt.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(100) # Default full volume
        self.slider_volume.setFixedWidth(80) # Match TrackHeader
        self.slider_volume.setToolTip("Master Volume: 100%")
        
        self.slider_volume.valueChanged.connect(self.on_slider_value_changed)
        self.slider_volume.sliderPressed.connect(self.slider_pressed.emit)
        self.slider_volume.sliderReleased.connect(self.on_slider_released)
        
        layout.addWidget(self.slider_volume)
        

        
    def on_dial_value_changed(self, value):
        pan = value / 100.0
        text = "Center"
        if pan < 0: text = f"Left {int(abs(pan)*100)}%"
        elif pan > 0: text = f"Right {int(abs(pan)*100)}%"
        
        self.dial_pan.setToolTip(f"Master Pan: {text}")
        
        # Update Audio Backend
        self.audio_track.pan = pan
        self.pan_changed.emit(pan)

    def on_dial_released(self):
        pan = self.dial_pan.value() / 100.0
        self.pan_set.emit(pan) # Signal for Undo stack if needed

    def on_slider_value_changed(self, value):
        volume = value / 100.0
        self.slider_volume.setToolTip(f"Master Volume: {value}%")
        
        # Update Audio Backend
        self.audio_track.volume = volume
        self.volume_changed.emit(volume)

    def on_slider_released(self):
        volume = self.slider_volume.value() / 100.0
        self.volume_set.emit(volume)
        
    def on_bypass_clicked(self, checked):
        self.fx_bypass_toggled.emit(checked)
        
    def set_bypass(self, bypassed):
        self.btn_fx_bypass.setChecked(bypassed)
        
    def update_fx_count(self, count):
        if count > 0:
            self.btn_fx.setText(f"FX ({count})")
            self.btn_fx.setProperty("active_fx", True)
        else:
            self.btn_fx.setText("FX")
            self.btn_fx.setProperty("active_fx", False)
        
        self.btn_fx.style().unpolish(self.btn_fx)
        self.btn_fx.style().polish(self.btn_fx)

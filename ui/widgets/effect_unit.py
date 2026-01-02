
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QDial, QComboBox
from PySide6.QtCore import Qt
from core.commands import ToggleEffectCommand, ChangeEffectParamCommand

from ui.widgets.knob import DraggableDial

class EffectUnit(QGroupBox):
    def __init__(self, effect, undo_stack, parent=None):
        super().__init__(parent)
        self.effect = effect
        self.undo_stack = undo_stack
        self.dials = {} # name -> DraggableDial

        self.setTitle(effect.name)
        self.setCheckable(True)
        self.setChecked(effect.active)
        self.toggled.connect(self.on_toggle)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 15, 5, 5) # Top margin for title
        
        self.setup_ui()
        
    def on_toggle(self, active):
        # We need to distinguish between user click and command update
        # QGroupBox emits toggled even if setChecked called programmatically?
        # Yes. To avoid loop, usually verify state.
        if self.effect.active != active:
             cmd = ToggleEffectCommand(self, self.effect)
             self.undo_stack.push(cmd)
             # But the checkbox is already toggled. If undo happens, we toggle it back.
        
    def setup_ui(self):
        for name, value in self.effect.parameters.items():
            container = QWidget()
            vbox = QVBoxLayout(container)
            vbox.setContentsMargins(0,0,0,0)
            
            lbl_name = QLabel(name.replace("_", " ").title())
            lbl_name.setAlignment(Qt.AlignCenter)
            
            # Determine Default
            default_val = 0
            if "gain" in name: default_val = 50
            if "mix" in name: default_val = 100
             
            dial = DraggableDial(default_value=default_val)
            dial.setFixedSize(40, 40)
            dial.setNotchesVisible(True)
            self.dials[name] = dial
            
            # Store initial state for drag
            dial._start_val = 0
            
            # Determine range
            if "freq" in name:
                dial.setRange(0, 100)
                dial.setValue(self.map_freq_to_dial(value))
                dial.valueChanged.connect(lambda v, n=name: self.on_freq_change(n, v))
            elif "gain" in name:
                dial.setRange(0, 100) # 50 is 0dB
                dial.setValue(int((value + 12) / 24 * 100))
                dial.valueChanged.connect(lambda v, n=name: self.on_gain_change(n, v))
            elif "time" in name:
                dial.setRange(0, 200)
                dial.setValue(int(value * 100))
                dial.valueChanged.connect(lambda v, n=name: self.on_val_change(n, v, 0.01))
            else:
                dial.setRange(0, 100)
                dial.setValue(int(value * 100))
                dial.valueChanged.connect(lambda v, n=name: self.on_val_change(n, v, 0.01))
                
            # Connect Press/Release for Undo
            dial.sliderPressed.connect(lambda n=name: self.on_dial_pressed(n))
            dial.sliderReleased.connect(lambda n=name: self.on_dial_released(n))
            
            vbox.addWidget(dial, 0, Qt.AlignCenter)
            vbox.addWidget(lbl_name, 0, Qt.AlignCenter)
            
            self.layout.addWidget(container)

    def on_val_change(self, name, value, scale):
        real_val = value * scale
        self.effect.parameters[name] = real_val
        
    def on_gain_change(self, name, value):
        fraction = value / 100.0
        db = (fraction * 24) - 12
        self.effect.parameters[name] = db
        
    def on_freq_change(self, name, value):
        freq = 20 + (value * 100)
        self.effect.parameters[name] = freq

    def map_freq_to_dial(self, freq):
        return int((freq - 20) / 100)

    # Undo Logic
    def on_dial_pressed(self, name):
        # Capture start value from effect (source of truth)
        self.dials[name]._start_val = self.effect.parameters[name]

    def on_dial_released(self, name):
        # Push command
        new_val = self.effect.parameters[name]
        old_val = self.dials[name]._start_val
        
        if abs(new_val - old_val) > 0.0001:
            cmd = ChangeEffectParamCommand(self, self.effect, name, old_val, new_val)
            self.undo_stack.push(cmd)

    def update_ui_from_param(self, name, value):
        # Called by Undo/Redo to sync UI
        dial = self.dials.get(name)
        if not dial: return
        
        dial.blockSignals(True)
        if "freq" in name:
            dial.setValue(self.map_freq_to_dial(value))
        elif "gain" in name:
             dial.setValue(int((value + 12) / 24 * 100))
        elif "time" in name:
             dial.setValue(int(value * 100))
        else:
             dial.setValue(int(value * 100))
        dial.blockSignals(False)

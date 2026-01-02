
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtCore import Qt
from ui.effects_rack import EffectsRack

class EffectsWindow(QWidget):
    def __init__(self, track_data, undo_stack, main_window, parent=None):
        super().__init__(parent)
        self.track_data = track_data
        self.undo_stack = undo_stack
        self.main_window = main_window
        
        self.setWindowTitle(f"FX: {track_data.name}")
        self.resize(400, 500)
        
        # Setup Shortcuts to forward to Main Window
        self.setup_forwarding_shortcuts()
        
        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Embed Rack
        self.rack = EffectsRack(self.undo_stack)
        self.rack.set_track(track_data)
        
        self.layout.addWidget(self.rack)
        
    def setup_forwarding_shortcuts(self):
        # Play/Pause (Space)
        self.shortcut_play = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.shortcut_play.activated.connect(self.main_window.toggle_playback)
        self.shortcut_play.setContext(Qt.WindowShortcut)

        # Undo (Ctrl+Z)
        self.shortcut_undo = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.shortcut_undo.activated.connect(self.main_window.undo_action)
        self.shortcut_undo.setContext(Qt.WindowShortcut)

        # Redo (Ctrl+Y)
        self.shortcut_redo = QShortcut(QKeySequence("Ctrl+Y"), self)
        self.shortcut_redo.activated.connect(self.main_window.redo_action)
        self.shortcut_redo.setContext(Qt.WindowShortcut)
        
        # Redo Alt (Ctrl+Shift+Z)
        self.shortcut_redo_alt = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        self.shortcut_redo_alt.activated.connect(self.main_window.redo_action)
        self.shortcut_redo_alt.setContext(Qt.WindowShortcut)
        
        # Save (Ctrl+S)
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.main_window.on_save_project)
        self.shortcut_save.setContext(Qt.WindowShortcut)
        
    def closeEvent(self, event):
        # Just hide, don't destroy? Or let TrackManager handle it.
        # If we destroy, we lose state? No, state is in track_data.
        # But for window management, TrackManager needs to know.
        super().closeEvent(event)

import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QScrollArea, QSplitter, 
                               QFrame, QFileDialog, QMessageBox, QCheckBox, QSizePolicy)
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtCore import Qt, QTimer

from styles import DARK_THEME
from core.audio_engine import AudioEngine
from core.track_loader import TrackLoader
from ui.widgets.timeline import TimelineRuler
from ui.widgets.track_header import TrackHeader
from ui.widgets.track_lane import TrackLane
from ui.widgets.track_container import TrackContainer
from ui.widgets.ribbon import Ribbon
from ui.track_manager import TrackManager
from core.command_stack import UndoStack
from core.project_manager import ProjectManager
from PySide6.QtGui import QAction

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Qt DAW - Audio Engine Active")
        self.resize(1200, 800)
        self.setStyleSheet(DARK_THEME)

        # AUDIO ENGINE
        self.audio = AudioEngine() 
        self.undo_stack = UndoStack()
        self.undo_stack.stack_changed.connect(self.update_undo_redo_buttons)
        
        self.ui_timer = QTimer()
        self.ui_timer.interval = 30 # 30ms refresh rate
        self.ui_timer.timeout.connect(self.update_ui)

        # UI SETUP
        self.lanes = [] 
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.setup_ribbon()
        self.setup_workspace()
        self.setup_menu()
        
        self.project_manager = ProjectManager()
        self.current_project_path = None
        self.clean_command = None
        self.undo_stack.stack_changed.connect(self.update_dirty_state)

        self.confirm_delete = True
        
        # Global Shortcuts
        self.shortcut_play = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.shortcut_play.activated.connect(self.toggle_playback)
        self.shortcut_play.setContext(Qt.WindowShortcut)

        self.shortcut_undo = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.shortcut_undo.activated.connect(self.undo_action)
        self.shortcut_undo.setContext(Qt.WindowShortcut)

        self.shortcut_redo = QShortcut(QKeySequence("Ctrl+Y"), self)
        self.shortcut_redo.activated.connect(self.redo_action)
        self.shortcut_redo.setContext(Qt.WindowShortcut)
        
        # Alternative Redo (Ctrl+Shift+Z)
        self.shortcut_redo_alt = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        self.shortcut_redo_alt.activated.connect(self.redo_action)
        self.shortcut_redo_alt.setContext(Qt.WindowShortcut)

    def setup_ribbon(self):
        self.ribbon = Ribbon()
        self.ribbon.play_clicked.connect(self.toggle_playback)
        self.ribbon.stop_clicked.connect(self.stop_playback)
        self.ribbon.undo_clicked.connect(self.undo_action)
        self.ribbon.redo_clicked.connect(self.redo_action)
        self.ribbon.tool_changed.connect(self.on_tool_changed)
        self.main_layout.addWidget(self.ribbon)

    def on_tool_changed(self, tool_name):
        self.track_manager.set_active_tool(tool_name)

    def setup_workspace(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        # splitter style is now in styles.py
        self.main_layout.addWidget(splitter)

        # LEFT PANEL (headers)
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.left_scroll.setFrameShape(QFrame.NoFrame)

        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(0)

        # Margin fix
        self.top_left_corner = QFrame()
        self.top_left_corner.setObjectName("TopLeftCorner")
        self.top_left_corner.setFixedHeight(30)
        
        self.left_layout.addWidget(self.top_left_corner)
        
        # Add Track Button
        self.btn_add_track = QPushButton("+")
        self.btn_add_track.setObjectName("AddTrackButton")
        self.btn_add_track.setFixedHeight(80)
        self.btn_add_track.clicked.connect(self.import_track)
        self.btn_add_track.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.left_layout.addWidget(self.btn_add_track)
        
        self.left_layout.addStretch()
        
        self.left_scroll.setWidget(self.left_container)
        
        # Limit resizing
        self.left_scroll.setMinimumWidth(200)
        self.left_scroll.setMaximumWidth(500)
        
        splitter.addWidget(self.left_scroll)
        splitter.setCollapsible(0, False)

        # RIGHT PANEL (Timeline + Lanes)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidgetResizable(True)
        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.timeline_scroll.setFrameShape(QFrame.NoFrame)
        self.timeline_scroll.setFixedHeight(30)

        self.timeline = TimelineRuler()
        self.timeline.position_changed.connect(self.user_seek)
        self.timeline.zoom_request.connect(self.handle_timeline_zoom) # Connect new signal
        self.timeline_scroll.setWidget(self.timeline)
        right_layout.addWidget(self.timeline_scroll)

        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setFrameShape(QFrame.NoFrame)
        
        self.right_container = TrackContainer()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)
        self.right_layout.addStretch()
        self.right_scroll.setWidget(self.right_container)

        right_layout.addWidget(self.right_scroll)
        splitter.addWidget(right_widget)
        splitter.setSizes([200, 1000])

        self.sync_scrollbars()

        # Initialize Track Manager
        self.track_manager = TrackManager(
            self, 
            self.audio, 
            self.undo_stack, 
            self.timeline, 
            self.left_layout, 
            self.right_layout, 
            self.btn_add_track,
            self.right_container
        )
        
        # Connect Loading Signals
        self.track_manager.loading_started.connect(lambda: self.ribbon.show_loading("Loading Project..."))
        self.track_manager.loading_progress.connect(self.ribbon.update_loading)
        self.track_manager.loading_finished.connect(self.ribbon.hide_loading)


    def sync_scrollbars(self):
        # Sync Vertical Scroll
        self.left_scroll.verticalScrollBar().valueChanged.connect(
            self.right_scroll.verticalScrollBar().setValue
        )
        self.right_scroll.verticalScrollBar().valueChanged.connect(
            self.left_scroll.verticalScrollBar().setValue
        )

        # Sync Horizontal Scroll
        self.right_scroll.horizontalScrollBar().valueChanged.connect(
            self.timeline_scroll.horizontalScrollBar().setValue
        )
        self.timeline_scroll.horizontalScrollBar().valueChanged.connect(
            self.right_scroll.horizontalScrollBar().setValue
        )

    def update_zoom(self, px_per_sec):
        self.track_manager.update_zoom(px_per_sec)
            
        # Update playhead position visually
        current_time = self.audio.get_playhead_time()
        x_pixel = int(current_time * px_per_sec)
        self.update_playhead_visuals(x_pixel)

    def update_global_duration(self):
        self.track_manager.update_global_duration()

    # THREADED IMPORT LOGIC

    def import_track(self):
        self.track_manager.import_track()

    def undo_action(self):
        self.undo_stack.undo()

    def redo_action(self):
        self.undo_stack.redo()

    def update_undo_redo_buttons(self):
        self.ribbon.update_undo_redo_state(self.undo_stack.can_undo(), self.undo_stack.can_redo())




    def toggle_playback(self):
        if self.audio.is_playing:
            self.pause_playback()
        else:
            self.audio.start_playback()
            self.ribbon.set_play_state(True)
            self.ui_timer.start()


    def pause_playback(self):
        self.audio.pause_playback()
        self.ribbon.set_play_state(False)
        self.ui_timer.stop()


    def stop_playback(self):
        self.audio.stop_playback()
        self.ribbon.set_play_state(False)
        self.ui_timer.stop()

        self.update_playhead_visuals(0)
        self.right_scroll.horizontalScrollBar().setValue(0)

    def user_seek(self, x_pixels):
        # Convert pixels to time using current zoom
        time_sec = x_pixels / self.timeline.pixels_per_second
        # Audio engine expects pixels at di100px/s ? No, let's check auo engine.
        # The previous code was: self.audio.set_playhead(x_pixels, px_per_second=100)
        # So audio engine handles time conversion if we pass px_per_second.
        # But wait, set_playhead in audio_engine might just take time?
        # Let's assume we should pass the new pixels_per_second or just calculate time here.
        # Actually, looking at user_seek signature in previous file content:
        # self.audio.set_playhead(x_pixels, px_per_second=100)
        # So I should update this call.
        
        self.audio.set_playhead(x_pixels, px_per_second=self.timeline.pixels_per_second)
        self.update_playhead_visuals(x_pixels)

    def update_ui(self):
        current_time = self.audio.get_playhead_time()
        
        # Auto-expand if near end
        if current_time > self.timeline.duration - 5:
             self.update_global_duration()
             
        x_pixel = int(current_time * self.timeline.pixels_per_second)
        self.update_playhead_visuals(x_pixel)

    def update_playhead_visuals(self, x):
        self.timeline.set_playhead(x)
        self.track_manager.update_playhead_visuals(x)
            
        if x > self.right_scroll.horizontalScrollBar().value() + self.right_scroll.viewport().width() - 50:
             self.right_scroll.horizontalScrollBar().setValue(x - 50)

    def handle_timeline_zoom(self, delta, global_pos):
        self.perform_zoom(delta, global_pos)

    def perform_zoom(self, delta, global_pos):
        # Map global pos to viewport
        viewport_pos = self.right_scroll.viewport().mapFromGlobal(global_pos.toPoint())
        mouse_x_screen = viewport_pos.x()
        
        current_scroll = self.right_scroll.horizontalScrollBar().value()
        current_zoom = self.timeline.pixels_per_second
        
        # Calculate time under mouse
        absolute_x = current_scroll + mouse_x_screen
        time_under_mouse = absolute_x / current_zoom
        
        # Calculate new zoom
        if delta > 0:
            new_zoom = current_zoom * 1.1
        else:
            new_zoom = current_zoom / 1.1
        
        new_zoom = max(1.0, min(1000.0, new_zoom))
        
        if new_zoom == current_zoom: return

        # Apply new zoom
        self.timeline.set_zoom(new_zoom)
        self.update_zoom(new_zoom)
        
        # Calculate new scroll to keep time_under_mouse at mouse_x_screen
        new_absolute_x = time_under_mouse * new_zoom
        new_scroll = int(new_absolute_x - mouse_x_screen)
        
        self.right_scroll.horizontalScrollBar().setValue(new_scroll)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            self.perform_zoom(delta, event.globalPosition())
            event.accept()
        else:
            super().wheelEvent(event)

    def update_dirty_state(self):
        is_dirty = self.undo_stack.current_command != self.clean_command
        
        title = "Python Qt DAW"
        if self.current_project_path:
            title += f" - {os.path.basename(self.current_project_path)}"
        else:
            title += " - Untitled"
            
        if is_dirty:
            title = "* " + title
            
        self.setWindowTitle(title)

    def check_save_changes(self):
        is_dirty = self.undo_stack.current_command != self.clean_command
        if not is_dirty:
            return True
            
        reply = QMessageBox.question(
            self, 
            "Unsaved Changes", 
            "You have unsaved changes. Do you want to save them?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Save:
            self.on_save_project()
            # Check if save was successful (clean command updated)
            return self.undo_stack.current_command == self.clean_command
        elif reply == QMessageBox.Discard:
            return True
        else:
            return False

    def on_new_project(self):
        if not self.check_save_changes():
            return
            
        self.track_manager.clear_all_tracks()
        self.undo_stack.clear()
        self.current_project_path = None
        self.clean_command = None
        self.update_dirty_state()

    def closeEvent(self, event):
        if self.check_save_changes():
            event.accept()
        else:
            event.ignore()

    def setup_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        
        action_new = QAction("New Project", self)
        action_new.triggered.connect(self.on_new_project)
        file_menu.addAction(action_new)

        action_open = QAction("Open Project", self)
        action_open.triggered.connect(self.on_open_project)
        file_menu.addAction(action_open)
        
        action_save = QAction("Save Project", self)
        action_save.triggered.connect(self.on_save_project)
        file_menu.addAction(action_save)

        action_save_as = QAction("Save Project As...", self)
        action_save_as.triggered.connect(self.on_save_project_as)
        file_menu.addAction(action_save_as)
        
        file_menu.addSeparator()
        
        action_export = QAction("Export Audio (WAV)", self)
        action_export.triggered.connect(self.on_export_audio)
        file_menu.addAction(action_export)

    def on_save_project(self):
        if self.current_project_path:
            success = self.project_manager.save_project(self.current_project_path, self.audio)
            if success:
                self.ribbon.show_loading(f"Saved to {os.path.basename(self.current_project_path)}")
                QTimer.singleShot(2000, self.ribbon.hide_loading)
                self.clean_command = self.undo_stack.current_command
                self.update_dirty_state()
            else:
                QMessageBox.critical(self, "Error", "Failed to save project.")
        else:
            self.on_save_project_as()

    def on_save_project_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Project As", "", "Project Files (*.json)")
        if file_path:
            if not file_path.endswith(".json"):
                file_path += ".json"
            
            self.current_project_path = file_path
            success = self.project_manager.save_project(file_path, self.audio)
            
            if success:
                self.setWindowTitle(f"Python Qt DAW - {os.path.basename(file_path)}")
                QMessageBox.information(self, "Success", f"Project saved to {file_path}")
                self.clean_command = self.undo_stack.current_command
                self.update_dirty_state()
            else:
                QMessageBox.critical(self, "Error", "Failed to save project.")

    def on_open_project(self):
        if not self.check_save_changes():
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "Project Files (*.json)")
        if file_path:
            # Use TrackManager's async loader
            self.track_manager.load_project(file_path)
            self.current_project_path = file_path
            self.undo_stack.clear()
            self.clean_command = None
            self.update_dirty_state()

    def on_export_audio(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Audio", "", "WAV Files (*.wav)")
        if file_path:
            if not file_path.endswith(".wav"):
                file_path += ".wav"
            
            # Determine duration
            duration = self.timeline.duration
            
            max_end = 0
            for track in self.audio.tracks:
                for clip in track.clips:
                    end = clip.start_time + clip.duration
                    if end > max_end: max_end = end
            
            if max_end == 0:
                QMessageBox.warning(self, "Warning", "Project is empty.")
                return

            # Add a small tail (e.g. 1 second)
            export_duration = max_end + 1.0
            
            self.audio.export_audio(file_path, export_duration)
            QMessageBox.information(self, "Success", f"Audio exported to {file_path}")

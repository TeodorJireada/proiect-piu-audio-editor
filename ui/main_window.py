import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QScrollArea, QSplitter, 
                               QFrame, QFileDialog, QMessageBox, QCheckBox, QSizePolicy, QApplication, QScrollBar)
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtCore import Qt, QTimer

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
from core.commands import ChangeBPMCommand, ToggleLoopCommand, ToggleSnapCommand
from ui.theme_manager import ThemeManager
from PySide6.QtGui import QAction

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Qt DAW - Audio Engine Active")
        self.resize(1200, 800)
        # self.setStyleSheet(DARK_THEME) # Handled by ThemeManager

        # AUDIO ENGINE
        self.audio = AudioEngine() 
        self.undo_stack = UndoStack()
        self.undo_stack.stack_changed.connect(self.update_undo_redo_buttons)
        
        self.ui_timer = QTimer()
        self.ui_timer.interval = 30 # 30ms refresh rate
        self.ui_timer.timeout.connect(self.update_ui)

        self.scroll_timer = QTimer()
        self.scroll_timer.setInterval(30)
        self.scroll_timer.timeout.connect(self.check_edge_scroll)

        # UI SETUP
        self.lanes = [] 
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.setup_ribbon()
        self.setup_workspace()
        # self.setup_menu() # Menu removed
        
        self.project_manager = ProjectManager()
        self.current_project_path = None
        self.clean_command = None
        self.undo_stack.stack_changed.connect(self.update_dirty_state)

        self.confirm_delete = True
        self.confirm_delete = True
        self.edit_cursor_time = 0.0
        
        self.master_vol_at_press = 1.0
        self.master_pan_at_press = 0.0
        
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

        # Save (Ctrl+S)
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.on_save_project)
        self.shortcut_save.setContext(Qt.WindowShortcut)

        # Save As (Ctrl+Shift+S)
        self.shortcut_save_as = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self.shortcut_save_as.activated.connect(self.on_save_project_as)
        self.shortcut_save_as.setContext(Qt.WindowShortcut)

        # Zoom Shortcuts
        self.shortcut_zoom_in = QShortcut(QKeySequence.ZoomIn, self)
        self.shortcut_zoom_in.activated.connect(self.zoom_in_step)
        self.shortcut_zoom_in.setContext(Qt.WindowShortcut)

        # Handle Ctrl+= as well manually if ZoomIn doesn't cover it on some platforms
        self.shortcut_zoom_in_alt = QShortcut(QKeySequence("Ctrl+="), self)
        self.shortcut_zoom_in_alt.activated.connect(self.zoom_in_step)
        self.shortcut_zoom_in_alt.setContext(Qt.WindowShortcut)

        self.shortcut_zoom_out = QShortcut(QKeySequence.ZoomOut, self)
        self.shortcut_zoom_out.activated.connect(self.zoom_out_step)
        self.shortcut_zoom_out.setContext(Qt.WindowShortcut)

    def setup_ribbon(self):
        self.ribbon = Ribbon()
        self.ribbon.new_clicked.connect(self.on_new_project)
        self.ribbon.open_clicked.connect(self.on_open_project)
        self.ribbon.save_clicked.connect(self.on_save_project)
        self.ribbon.export_clicked.connect(self.on_export_audio)
        self.ribbon.theme_switched.connect(lambda t: self.switch_theme(t))
        self.ribbon.bpm_changed.connect(self.on_bpm_changed)
        self.ribbon.snap_toggled.connect(self.on_snap_toggled)
        
        self.ribbon.play_clicked.connect(self.toggle_playback)
        self.ribbon.stop_clicked.connect(self.stop_playback)
        self.ribbon.loop_toggled.connect(self.on_loop_toggled)

        self.ribbon.undo_clicked.connect(self.undo_action)
        self.ribbon.redo_clicked.connect(self.redo_action)
        self.ribbon.tool_changed.connect(self.on_tool_changed)
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

        # Margin fix / Master Track
        from ui.widgets.master_track import MasterTrackWidget
        self.master_track_widget = MasterTrackWidget(self.audio.master_track)
        self.master_track_widget.fx_requested.connect(self.open_master_fx)
        self.master_track_widget.volume_set.connect(self.on_master_volume_set)
        self.master_track_widget.pan_set.connect(self.on_master_pan_set)
        self.master_track_widget.slider_pressed.connect(self.capture_master_vol)
        self.master_track_widget.dial_pressed.connect(self.capture_master_pan)
        self.master_track_widget.fx_bypass_toggled.connect(self.on_master_bypass_toggled)
        
        self.left_layout.addWidget(self.master_track_widget)
        
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
        self.right_layout = QVBoxLayout(right_widget)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)
        
        # 1. Custom Horizontal Scrollbar (Top)
        self.h_scrollbar = QScrollBar(Qt.Horizontal)
        self.h_scrollbar.setFixedHeight(20)
        self.right_layout.addWidget(self.h_scrollbar)

        # 2. Timeline Ruler
        self.timeline = TimelineRuler()
        self.timeline.set_bpm(self.audio.bpm)
        self.timeline.position_changed.connect(self.user_seek)
        self.timeline.zoom_request.connect(self.perform_zoom)
        self.timeline.drag_started.connect(self.handle_drag_started)
        self.timeline.drag_finished.connect(self.handle_drag_finished)
        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidgetResizable(True)
        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.timeline_scroll.setFrameShape(QFrame.NoFrame)
        self.timeline_scroll.setFixedHeight(30)
        self.timeline_scroll.setWidget(self.timeline)
        self.right_layout.addWidget(self.timeline_scroll)

        # 3. Track Container (for grid lines and holding lanes)
        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setFrameShape(QFrame.NoFrame)
        self.right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Use custom top scrollbar
        self.right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.right_content = TrackContainer() # This is the widget that draws the grid and holds the track lanes
        self.right_content.pixels_per_second = self.timeline.pixels_per_second
        self.right_content.set_bpm(self.audio.bpm)
        
        self.right_inner_layout = QVBoxLayout(self.right_content) # This layout will hold the actual TrackLane widgets
        self.right_inner_layout.setContentsMargins(0, 0, 0, 0)
        self.right_inner_layout.setSpacing(0)
        self.right_inner_layout.addStretch()
        
        self.right_scroll.setWidget(self.right_content)
        self.right_layout.addWidget(self.right_scroll) # Add the scroll area to the main right_layout
        
        self.track_container = self.right_content # Alias for compatibility
        
        splitter.addWidget(right_widget) # Add the main right_widget to the splitter
        splitter.setSizes([200, 1000])

        self.sync_scrollbars_custom()

        # Initialize Track Manager
        self.track_manager = TrackManager(
            self, 
            self.audio, 
            self.undo_stack, 
            self.timeline, 
            self.left_layout, 
            self.right_inner_layout, 
            self.btn_add_track,
            self.track_container
        )
        
        # Connect Grid Painting
        self.track_manager.track_container = self.track_container

        # Initialize Logic States from UI Defaults
        # (Directly set values to match UI, do not push to undo stack)
        self.audio.set_looping(self.ribbon.btn_loop.isChecked())
        self.track_manager.set_snap_enabled(self.ribbon.chk_snap.isChecked())
        
        # Connect Loading Signals
        self.track_manager.loading_started.connect(lambda: self.ribbon.show_loading("Loading Project..."))
        self.track_manager.loading_progress.connect(self.ribbon.update_loading)
        self.track_manager.loading_finished.connect(self.on_project_loaded)
        self.track_manager.status_update.connect(self.ribbon.set_status)
        
        # Connect Selection (Legacy/Other usage?)
        # self.track_manager.track_selected.connect(...)

    def on_project_loaded(self):
        self.ribbon.hide_loading()
        self.zoom_to_fit()
        
    def zoom_to_fit(self):
        # Calculate max duration from tracks
        max_duration = 0
        for track in self.audio.tracks:
            for clip in track.clips:
                end = clip.start_time + clip.duration
                if end > max_duration: max_duration = end
        
        if max_duration <= 0: max_duration = 60 # Default if empty
        
        # Get available width
        available_width = self.right_scroll.viewport().width() - 50 # padding
        if available_width <= 0: available_width = 800
        
        # Calculate required pixels per second
        required_pps = available_width / max_duration
        
        # Clamp
        required_pps = max(1.0, min(1000.0, required_pps))
        
        # Apply
        self.timeline.set_zoom(required_pps)
        self.update_zoom(required_pps)
        self.right_scroll.horizontalScrollBar().setValue(0)


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
        self.update_playhead_visuals(x_pixel, scroll_to_view=False)

    def update_global_duration(self):
        self.track_manager.update_global_duration()

    # THREADED IMPORT LOGIC

    def import_track(self):
        self.track_manager.import_track()

    def undo_action(self):
        self.undo_stack.undo()
        self.ribbon.set_status("Undo Performed")

    def redo_action(self):
        self.undo_stack.redo()
        self.ribbon.set_status("Redo Performed")

    def update_undo_redo_buttons(self):
        can_undo = self.undo_stack.can_undo()
        can_redo = self.undo_stack.can_redo()
        self.ribbon.update_undo_redo_state(can_undo, can_redo)
        
        # Heuristic feedback
        if can_undo: self.ribbon.set_status("Action Performed")




    def toggle_playback(self):
        if self.audio.is_playing:
            self.pause_playback()
        else:
            # If at end (rough check), restart from cursor or 0
            # if self.audio.get_playhead_time() >= self.timeline.duration:
            #    self.audio.playhead = 0
            
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

        # SNAP BACK TO CURSOR
        cursor_x_pixels = int(getattr(self, 'edit_cursor_time', 0.0) * self.timeline.pixels_per_second)
        self.audio.set_playhead(cursor_x_pixels, px_per_second=self.timeline.pixels_per_second)

        self.update_playhead_visuals(cursor_x_pixels, scroll_to_view=False)
        # self.right_scroll.horizontalScrollBar().setValue(0) # Remove reset to 0


    def user_seek(self, x_pixels):
        # Check if we should clamp to viewport (if dragging)
        if hasattr(self.timeline, 'is_dragging') and self.timeline.is_dragging:
             viewport_start = self.right_scroll.horizontalScrollBar().value()
             viewport_end = viewport_start + self.right_scroll.viewport().width()
             x_pixels = max(viewport_start, min(x_pixels, viewport_end))

        # Convert pixels to time using current zoom
        time_sec = x_pixels / self.timeline.pixels_per_second
        
        # KEY CHANGE: User seek primarily sets the EDIT CURSOR
        self.edit_cursor_time = time_sec
        self.timeline.set_cursor(x_pixels)
        
        self.audio.set_playhead(x_pixels, px_per_second=self.timeline.pixels_per_second)
        self.update_playhead_visuals(x_pixels, scroll_to_view=False)


    def update_ui(self):
        current_time = self.audio.get_playhead_time()
        
        # Auto-expand if near end
        if current_time > self.timeline.duration - 5:
             self.update_global_duration()
             
        x_pixel = int(current_time * self.timeline.pixels_per_second)
        self.update_playhead_visuals(x_pixel, scroll_to_view=True)

    def update_playhead_visuals(self, x, scroll_to_view=False):
        self.timeline.set_playhead(x)
        self.track_manager.update_playhead_visuals(x)
            
        if scroll_to_view:
             viewport_width = self.right_scroll.viewport().width()
             current_scroll = self.right_scroll.horizontalScrollBar().value()
             
             # "Page" logic: If playhead goes off screen to the right, jump view to it
             # This aligns the playhead to the beginning (left) of the new view
             if x > current_scroll + viewport_width:
                 target_scroll = x
                 self.right_scroll.horizontalScrollBar().setValue(int(target_scroll))

    def zoom_in_step(self):
        self.perform_zoom_step(1)

    def zoom_out_step(self):
        self.perform_zoom_step(-1)

    def perform_zoom_step(self, direction):
        # Zoom to center of viewport
        viewport_width = self.right_scroll.viewport().width()
        center_x_screen = viewport_width / 2
        
        current_scroll = self.right_scroll.horizontalScrollBar().value()
        current_zoom = self.timeline.pixels_per_second
        
        # Calculate time at center
        absolute_x = current_scroll + center_x_screen
        time_at_center = absolute_x / current_zoom
        
        # Calculate new zoom
        if direction > 0:
            new_zoom = current_zoom * 1.5
        else:
            new_zoom = current_zoom / 1.5
        
        new_zoom = max(1.0, min(1000.0, new_zoom))
        
        if new_zoom == current_zoom: return

        # Apply new zoom
        self.timeline.set_zoom(new_zoom)
        self.update_zoom(new_zoom)
        
        # Calculate new scroll to keep time_at_center at center_x_screen
        new_absolute_x = time_at_center * new_zoom
        new_scroll = int(new_absolute_x - center_x_screen)
        
        self.right_scroll.horizontalScrollBar().setValue(new_scroll)

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
            new_zoom = current_zoom * 1.5
        else:
            new_zoom = current_zoom / 1.5
        
        new_zoom = max(1.0, min(1000.0, new_zoom))
        
        if new_zoom == current_zoom: return

        # Apply new zoom
        self.timeline.set_zoom(new_zoom)
        self.update_zoom(new_zoom)
        
        # Calculate new scroll to keep time_under_mouse at mouse_x_screen
        new_absolute_x = time_under_mouse * new_zoom
        new_scroll = int(new_absolute_x - mouse_x_screen)
        
        self.right_scroll.horizontalScrollBar().setValue(new_scroll)

    def sync_scrollbars_custom(self):
        # 1. Vertical Sync: Left Scroll <-> Right Scroll
        self.left_scroll.verticalScrollBar().valueChanged.connect(
            self.right_scroll.verticalScrollBar().setValue
        )
        self.right_scroll.verticalScrollBar().valueChanged.connect(
            self.left_scroll.verticalScrollBar().setValue
        )
        
        # 2. Horizontal Sync: Top HBuffer <-> Timeline Scroll <-> Right Scroll
        # We process 'valueChanged' for 2-way sync
        
        # Function to update others without loop
        def sync_h(val):
            if self.timeline_scroll.horizontalScrollBar().value() != val:
                self.timeline_scroll.horizontalScrollBar().setValue(val)
            if self.right_scroll.horizontalScrollBar().value() != val:
                self.right_scroll.horizontalScrollBar().setValue(val)
            if self.h_scrollbar.value() != val:
                self.h_scrollbar.setValue(val)
                
        self.h_scrollbar.valueChanged.connect(sync_h)
        self.timeline_scroll.horizontalScrollBar().valueChanged.connect(sync_h)
        self.right_scroll.horizontalScrollBar().valueChanged.connect(sync_h)
        
        # IMPORTANT: Sync RANGES too
        # When timeline/track grows, scrollbar range must update
        def update_range(min_val, max_val):
             self.h_scrollbar.setRange(min_val, max_val)
             self.h_scrollbar.setPageStep(self.right_scroll.horizontalScrollBar().pageStep())
             
        self.right_scroll.horizontalScrollBar().rangeChanged.connect(update_range)

    def update_zoom(self, px_per_sec):
        # Propagate zoom to track manager/lanes
        self.track_manager.update_zoom(px_per_sec)

    def open_master_fx(self):
        # We need a unique ID for master track window
        # TrackManager usually takes a lane_index.
        # We can reuse TrackManager logic or handle it here.
        # Let's ask TrackManager to handle it with a special ID or method.
        self.track_manager.open_master_fx_window(self.audio.master_track)

    def capture_master_vol(self):
        self.master_vol_at_press = self.audio.master_track.volume

    def capture_master_pan(self):
        self.master_pan_at_press = self.audio.master_track.pan

    def on_master_volume_set(self, new_vol):
        from core.commands import ChangeMasterVolumeCommand
        
        old_vol = getattr(self, 'master_vol_at_press', new_vol)
        if abs(new_vol - old_vol) > 0.001:
             cmd = ChangeMasterVolumeCommand(
                 self.audio.master_track,
                 self.master_track_widget,
                 old_vol,
                 new_vol
             )
             self.undo_stack.push(cmd)

    def on_master_pan_set(self, new_pan):
        from core.commands import ChangeMasterPanCommand
        
        old_pan = getattr(self, 'master_pan_at_press', new_pan)
        if abs(new_pan - old_pan) > 0.001:
             cmd = ChangeMasterPanCommand(
                 self.audio.master_track,
                 self.master_track_widget,
                 old_pan,
                 new_pan
             )
             self.undo_stack.push(cmd)

    def on_master_bypass_toggled(self, checked):
        from core.commands import ToggleFXBypassCommand
        # Master track index is -1
        cmd = ToggleFXBypassCommand(self.track_manager, -1, checked)
        self.undo_stack.push(cmd)

    def handle_drag_started(self):
        self.scroll_timer.start()

    def handle_drag_finished(self):
        self.scroll_timer.stop()

    def check_edge_scroll(self):
        # Determine global mouse pos
        global_mouse = self.cursor().pos()
        
        # Map to timeline viewport
        viewport = self.timeline_scroll.viewport()
        mouse_pos = viewport.mapFromGlobal(global_mouse)
        
        # Define areas
        scroll_margin = 50
        scroll_step = 20
        
        current_scroll = self.right_scroll.horizontalScrollBar().value()
        viewport_width = viewport.width()
        
        new_scroll = current_scroll
        
        # Check Right Edge
        if mouse_pos.x() > viewport_width - scroll_margin:
            # Scroll Right
            new_scroll += scroll_step
            
        # Check Left Edge (of the track container viewport)
        elif mouse_pos.x() < scroll_margin:
            # Scroll Left
            new_scroll -= scroll_step
        
        if new_scroll != current_scroll:
            new_scroll = max(0, new_scroll)
            self.right_scroll.horizontalScrollBar().setValue(new_scroll)
            
            # Update Playhead to match new position under mouse
            new_absolute_x = new_scroll + mouse_pos.x()
            new_absolute_x = max(0, new_absolute_x)
            
            # Signal user seek
            self.user_seek(new_absolute_x)


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

    # setup_menu removed


    def switch_theme(self, theme_name):
        app = QApplication.instance()
        ThemeManager.save_theme(theme_name)
        ThemeManager.apply_theme(app, theme_name)

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

    def on_bpm_changed(self, new_bpm):
        old_bpm = self.audio.bpm
        if old_bpm == new_bpm: return
        
        cmd = ChangeBPMCommand(self, old_bpm, new_bpm)
        self.undo_stack.push(cmd)

    def perform_bpm_change(self, new_bpm):
        # Update UI without triggering signal loop
        self.ribbon.spin_bpm.blockSignals(True)
        self.ribbon.spin_bpm.setValue(new_bpm)
        self.ribbon.spin_bpm.blockSignals(False)

        old_bpm = self.audio.bpm
        
        # Scaling Logic
        if old_bpm != new_bpm and old_bpm > 0:
            scale_factor = old_bpm / new_bpm
            self.track_manager.scale_project_time(scale_factor)
            
        self.audio.set_bpm(new_bpm)
        self.timeline.set_bpm(new_bpm)
        if hasattr(self, 'track_container'):
             self.track_container.set_bpm(new_bpm)
        self.track_manager.set_bpm(new_bpm) 
             
        self.update_dirty_state()

    def on_snap_toggled(self, enabled):
        # Prevent recursion if updated programmatically
        if self.ribbon.chk_snap.isChecked() != enabled: return 
        
        cmd = ToggleSnapCommand(self, enabled)
        self.undo_stack.push(cmd)

    def perform_snap_toggle(self, enabled):
        self.ribbon.chk_snap.blockSignals(True)
        self.ribbon.chk_snap.setChecked(enabled)
        self.ribbon.chk_snap.blockSignals(False)
        self.track_manager.set_snap_enabled(enabled)

    def on_loop_toggled(self, enabled):
        cmd = ToggleLoopCommand(self, enabled)
        self.undo_stack.push(cmd)

    def perform_loop_toggle(self, enabled):
        self.ribbon.btn_loop.blockSignals(True)
        self.ribbon.btn_loop.setChecked(enabled)
        self.ribbon.btn_loop.blockSignals(False)
        self.audio.set_looping(enabled)

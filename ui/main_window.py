import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QScrollArea, QSplitter, 
                               QFrame, QSizePolicy, QApplication, QScrollBar, QStyle)
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtCore import Qt, QTimer, QEvent

from core.audio_engine import AudioEngine
from ui.widgets.timeline import TimelineRuler
from ui.widgets.track_container import TrackContainer
from ui.widgets.ribbon import Ribbon
from ui.tracks.manager import TrackManager
from core.command_stack import UndoStack
from core.project_manager import ProjectManager
from core.commands import ChangeBPMCommand, ToggleLoopCommand, ToggleSnapCommand
from ui.theme_manager import ThemeManager

# Controllers
from ui.controllers.viewport_controller import ViewportController
from ui.controllers.project_io import ProjectIO

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

        # UI SETUP
        self.lanes = [] 
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.project_manager = ProjectManager()

        self.setup_ribbon()
        self.setup_workspace()
        # self.setup_menu() # Menu removed
        
        self.edit_cursor_time = 0.0
        
        self.master_vol_at_press = 1.0
        self.master_pan_at_press = 0.0
        
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
        self.track_manager.track_container = self.track_container

        # Initialize Controllers
        self.viewport_controller = ViewportController(self)
        self.project_io = ProjectIO(self)
        
        # Connect Ribbon Signals to IO
        self.ribbon.new_clicked.connect(self.project_io.on_new_project)
        self.ribbon.open_clicked.connect(self.project_io.on_open_project)
        self.ribbon.save_clicked.connect(self.project_io.on_save_project)
        self.ribbon.save_as_clicked.connect(self.project_io.on_save_project_as)
        self.ribbon.export_clicked.connect(self.project_io.on_export_audio)

        # Connect Ribbon Signals to Viewport
        # (Zoom shortcuts are handled via QShortcut below)

        # Initialize Logic States from UI Defaults
        self.audio.set_looping(self.ribbon.btn_loop.isChecked())
        self.track_manager.set_snap_enabled(self.ribbon.btn_snap.isChecked())
        
        # Connect Loading Signals
        self.track_manager.loading_started.connect(lambda: self.ribbon.show_loading("Loading Project..."))
        self.track_manager.loading_progress.connect(self.ribbon.update_loading)
        self.track_manager.loading_finished.connect(self.on_project_loaded)
        self.track_manager.status_update.connect(self.ribbon.set_status)

        # Setup Shortcuts
        self.setup_shortcuts()
        
        # Initial Dirty State
        self.project_io.update_dirty_state()
        
        # Initialize Zoom to fit logic
        QTimer.singleShot(50, lambda: self.viewport_controller.zoom_to_fit())

    def setup_shortcuts(self):
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
        self.shortcut_save.activated.connect(self.project_io.on_save_project)
        self.shortcut_save.setContext(Qt.WindowShortcut)

        # Save As (Ctrl+Shift+S)
        self.shortcut_save_as = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self.shortcut_save_as.activated.connect(self.project_io.on_save_project_as)
        self.shortcut_save_as.setContext(Qt.WindowShortcut)
        
        # Duplicate Clip (Ctrl+B)
        self.shortcut_duplicate = QShortcut(QKeySequence("Ctrl+B"), self)
        self.shortcut_duplicate.activated.connect(self.duplicate_selection)
        self.shortcut_duplicate.setContext(Qt.WindowShortcut)

        # Zoom Shortcuts
        self.shortcut_zoom_in = QShortcut(QKeySequence.ZoomIn, self)
        self.shortcut_zoom_in.activated.connect(self.zoom_in_step)
        self.shortcut_zoom_in.setContext(Qt.WindowShortcut)

        # Handle Ctrl+= as well manually
        self.shortcut_zoom_in_alt = QShortcut(QKeySequence("Ctrl+="), self)
        self.shortcut_zoom_in_alt.activated.connect(self.zoom_in_step)
        self.shortcut_zoom_in_alt.setContext(Qt.WindowShortcut)

        self.shortcut_zoom_out = QShortcut(QKeySequence.ZoomOut, self)
        self.shortcut_zoom_out.activated.connect(self.zoom_out_step)
        self.shortcut_zoom_out.setContext(Qt.WindowShortcut)

    def duplicate_selection(self):
        # Iterate lanes to find selection
        for lane in self.track_manager.lanes:
            if lane.selected_clip_index != -1:
                lane.handle_duplicate(lane.selected_clip_index)
                break # Only duplicate one selection at a time

    def setup_ribbon(self):
        self.ribbon = Ribbon()
        self.ribbon.theme_switched.connect(lambda t: self.switch_theme(t))
        self.ribbon.bpm_changed.connect(self.on_bpm_changed)
        self.ribbon.snap_toggled.connect(self.on_snap_toggled)
        
        self.ribbon.play_clicked.connect(self.toggle_playback)
        self.ribbon.stop_clicked.connect(self.stop_playback)
        self.ribbon.loop_toggled.connect(self.on_loop_toggled)

        self.ribbon.undo_clicked.connect(self.undo_action)
        self.ribbon.redo_clicked.connect(self.redo_action)
        self.ribbon.tool_changed.connect(self.on_tool_changed)
        self.main_layout.addWidget(self.ribbon)

    def on_tool_changed(self, tool_name):
        self.track_manager.set_active_tool(tool_name)

    def setup_workspace(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        self.main_layout.addWidget(splitter)

        # LEFT PANEL (headers)
        left_panel = QWidget()
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setContentsMargins(0, 0, 0, 0)
        left_panel_layout.setSpacing(0)
        
        # Margin fix / Master Track
        from ui.widgets.master_track import MasterTrackWidget
        self.master_track_widget = MasterTrackWidget(self.audio.master_track)
        self.master_track_widget.fx_requested.connect(self.open_master_fx)
        self.master_track_widget.volume_set.connect(self.on_master_volume_set)
        self.master_track_widget.pan_set.connect(self.on_master_pan_set)
        self.master_track_widget.slider_pressed.connect(self.capture_master_vol)
        self.master_track_widget.dial_pressed.connect(self.capture_master_pan)
        self.master_track_widget.fx_bypass_toggled.connect(self.on_master_bypass_toggled)
        
        left_panel_layout.addWidget(self.master_track_widget)

        # Scroll Area for Tracks
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.left_scroll.setFrameShape(QFrame.NoFrame)
        self.left_scroll.viewport().installEventFilter(self) # Intercept Ctrl+Scroll

        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(0)
        
        # Add Track Button (Inside Scroll)
        self.btn_add_track = QPushButton("+")
        self.btn_add_track.setObjectName("AddTrackButton")
        self.btn_add_track.setFixedHeight(80)
        self.btn_add_track.clicked.connect(self.import_track)
        self.btn_add_track.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.left_layout.addWidget(self.btn_add_track)
        
        self.left_layout.addStretch()
        
        self.left_scroll.setWidget(self.left_container)
        left_panel_layout.addWidget(self.left_scroll)
        
        # Limit resizing (Apply to the panel, not just scroll)
        left_panel.setMinimumWidth(320)
        left_panel.setMaximumWidth(500)
        
        splitter.addWidget(left_panel)
        splitter.setCollapsible(0, False)

        # RIGHT PANEL (Timeline + Lanes)
        right_widget = QWidget()
        self.right_layout = QVBoxLayout(right_widget)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)
        
        # 1. Custom Horizontal Scrollbar (Top)
        self.h_scrollbar = QScrollBar(Qt.Horizontal)
        self.h_scrollbar.setFixedHeight(15)
        self.right_layout.addWidget(self.h_scrollbar)

        # 2. Timeline Ruler
        self.timeline = TimelineRuler()
        self.timeline.set_bpm(self.audio.bpm)
        
        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidgetResizable(True)
        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.timeline_scroll.setFrameShape(QFrame.NoFrame)
        self.timeline_scroll.setFixedHeight(25)
        self.timeline_scroll.setWidget(self.timeline)
        
        # Wrapper to align timeline with track container (compensate for V-Scrollbar)
        timeline_wrapper = QWidget()
        timeline_wrapper.setFixedHeight(25)
        timeline_layout = QHBoxLayout(timeline_wrapper)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        timeline_layout.setSpacing(0)
        timeline_layout.addWidget(self.timeline_scroll)
        
        # Spacer
        sb_width = self.style().pixelMetric(QStyle.PM_ScrollBarExtent)
        self.timeline_spacer = QWidget()
        self.timeline_spacer.setFixedWidth(sb_width)
        self.timeline_spacer.setFixedHeight(25)
        timeline_layout.addWidget(self.timeline_spacer)
        
        self.right_layout.addWidget(timeline_wrapper)

        # 3. Track Container (for grid lines and holding lanes)
        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setFrameShape(QFrame.NoFrame)
        self.right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Use custom top scrollbar
        self.right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.right_scroll.viewport().installEventFilter(self) # Intercept Ctrl+Scroll

        self.right_content = TrackContainer() # This is the widget that draws the grid and holds the track lanes
        self.right_content.pixels_per_second = self.timeline.pixels_per_second
        self.right_content.set_bpm(self.audio.bpm)
        
        self.right_inner_layout = QVBoxLayout(self.right_content) # This layout will hold the actual TrackLane widgets
        self.right_inner_layout.setContentsMargins(0, 0, 0, 0)
        self.right_inner_layout.setSpacing(0)
        
        # Bottom Spacer to match AddTrackButton height (80px)
        self.right_bottom_spacer = QWidget()
        self.right_bottom_spacer.setFixedHeight(80)
        self.right_inner_layout.addWidget(self.right_bottom_spacer)

        self.right_inner_layout.addStretch()
        
        self.right_scroll.setWidget(self.right_content)
        self.right_layout.addWidget(self.right_scroll) # Add the scroll area to the main right_layout
        
        self.track_container = self.right_content # Alias for compatibility
        
        splitter.addWidget(right_widget) # Add the main right_widget to the splitter
        
        # Fixed Left Panel behavior
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([340, 1000])

    def on_project_loaded(self):
        self.ribbon.hide_loading()
        self.viewport_controller.zoom_to_fit()

    def update_zoom(self, px_per_sec):
        # Delegated to ViewportController
        self.viewport_controller.update_zoom(px_per_sec)

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

        self.viewport_controller.update_playhead_visuals(cursor_x_pixels, scroll_to_view=False)

    def update_ui(self):
        current_time = self.audio.get_playhead_time()
        
        # Auto-expand if near end
        if current_time > self.timeline.duration - 5:
             self.update_global_duration()
             
        x_pixel = int(current_time * self.timeline.pixels_per_second)
        self.viewport_controller.update_playhead_visuals(x_pixel, scroll_to_view=True)
        
        self.track_manager.update_meters()

    def zoom_in_step(self):
        self.viewport_controller.perform_zoom_step(1)

    def zoom_out_step(self):
        self.viewport_controller.perform_zoom_step(-1)

    def perform_zoom(self, delta, global_pos):
        self.viewport_controller.perform_zoom(delta, global_pos)

    def open_master_fx(self):
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

    def eventFilter(self, source, event):
        if event.type() == QEvent.Wheel:
            if event.modifiers() & Qt.ControlModifier:
                # Intercept Zoom here to prevent ScrollArea from scrolling
                delta = event.angleDelta().y()
                self.viewport_controller.perform_zoom(delta, event.globalPosition())
                return True # Consume event
        return super().eventFilter(source, event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            self.viewport_controller.perform_zoom(delta, event.globalPosition())
            event.accept()
        else:
            super().wheelEvent(event)

    def closeEvent(self, event):
        if self.project_io.check_save_changes():
            event.accept()
        else:
            event.ignore()

    def switch_theme(self, theme_name):
        app = QApplication.instance()
        ThemeManager.save_theme(theme_name)
        ThemeManager.apply_theme(app, theme_name)

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
             
        self.project_io.update_dirty_state()

    def on_snap_toggled(self, enabled):
        # Prevent recursion if updated programmatically
        if self.ribbon.btn_snap.isChecked() != enabled: return 
        
        cmd = ToggleSnapCommand(self, enabled)
        self.undo_stack.push(cmd)

    def perform_snap_toggle(self, enabled):
        self.ribbon.btn_snap.blockSignals(True)
        self.ribbon.btn_snap.setChecked(enabled)
        self.ribbon.btn_snap.blockSignals(False)
        self.track_manager.set_snap_enabled(enabled)

    def on_loop_toggled(self, enabled):
        cmd = ToggleLoopCommand(self, enabled)
        self.undo_stack.push(cmd)

    def perform_loop_toggle(self, enabled):
        self.ribbon.btn_loop.blockSignals(True)
        self.ribbon.btn_loop.setChecked(enabled)
        self.ribbon.btn_loop.blockSignals(False)
        self.audio.set_looping(enabled)
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Qt DAW - Audio Engine Active")
        self.resize(1200, 800)
        self.setStyleSheet(DARK_THEME)

        # AUDIO ENGINE
        self.audio = AudioEngine() 
        
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

        self.confirm_delete = True
        
        # Global Shortcuts
        self.shortcut_play = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.shortcut_play.activated.connect(self.toggle_playback)
        self.shortcut_play.setContext(Qt.WindowShortcut)

    def setup_ribbon(self):
        ribbon = QFrame()
        ribbon.setObjectName("Ribbon")
        ribbon.setFixedHeight(60)
        layout = QHBoxLayout(ribbon)
        
        self.btn_play = QPushButton("Play")
        self.btn_play.clicked.connect(self.toggle_playback)
        
        btn_stop = QPushButton("Stop")
        btn_stop.clicked.connect(self.stop_playback)

        layout.addWidget(btn_stop)
        layout.addWidget(self.btn_play)
        layout.addStretch()
        self.main_layout.addWidget(ribbon)

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
        self.timeline.zoom_changed.connect(self.update_zoom)
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
        # Update all lanes
        for lane in self.lanes:
            lane.set_zoom(px_per_sec)
        self.right_container.set_zoom(px_per_sec)
            
        # Update playhead position visually
        current_time = self.audio.get_playhead_time()
        x_pixel = int(current_time * px_per_sec)
        self.update_playhead_visuals(x_pixel)

    def update_global_duration(self):
        max_duration = 60 # Minimum duration
        
        for lane in self.lanes:
            for clip in lane.clips:
                end_time = clip['start_time'] + clip['duration']
                if end_time > max_duration:
                    max_duration = end_time
        
        # Check playhead
        current_playhead = self.audio.get_playhead_time()
        if current_playhead > max_duration:
            max_duration = current_playhead
        
        # Add some padding
        max_duration += 5
        
        self.timeline.set_duration(max_duration)
        for lane in self.lanes:
            lane.set_duration(max_duration)
        self.right_container.set_duration(max_duration)

    # THREADED IMPORT LOGIC

    def import_track(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Audio", "", "Audio Files (*.wav *.mp3 *.ogg *.flac *.opus)")
        if file_path:
            self.btn_add_track.setText("Loading...") 
            self.btn_add_track.setEnabled(False) 
            
            # Use Thread
            self.loader_thread = TrackLoader(file_path, self.audio.sample_rate)
            self.loader_thread.loaded.connect(self.on_track_loaded)
            self.loader_thread.failed.connect(self.on_import_failed)
            self.loader_thread.start()

    def on_import_failed(self, error_msg):
        QMessageBox.critical(self, "Import Failed", f"Could not load audio:\n{error_msg}")
        self.btn_add_track.setText("+")
        self.btn_add_track.setEnabled(True)

    def on_track_loaded(self, track_data):
        # Pass data to Audio Engine
        self.audio.add_track_data(track_data)
        
        # Create Header
        filename = os.path.basename(track_data.name)
        
        header = TrackHeader(filename, "#4466aa")
        header.delete_clicked.connect(self.delete_track)
        header.mute_clicked.connect(self.handle_mute)
        header.solo_clicked.connect(self.handle_solo)
        
        # Create Lane with Waveform
        lane = TrackLane()
        lane.set_zoom(self.timeline.pixels_per_second)
        lane.clip_moved.connect(self.on_clip_moved)
        
        waveform = track_data.waveform
        duration_sec = len(track_data.data) / track_data.sample_rate
        
        lane.add_clip(filename, 0, duration_sec, "#5577cc", waveform)
        
        self.lanes.append(lane)

        # Insert before the Add button (which is at count() - 2 because of stretch at end)
        # Actually, let's find the index of btn_add_track
        idx_add = self.left_layout.indexOf(self.btn_add_track)
        self.left_layout.insertWidget(idx_add, header)

        idx_right = self.right_layout.count() - 1
        self.right_layout.insertWidget(idx_right, lane)
        
        self.btn_add_track.setText("+")
        self.btn_add_track.setEnabled(True)
        
        self.update_global_duration()
        
    def delete_track(self):
        sender_header = self.sender()
        layout_index = self.left_layout.indexOf(sender_header)
        if layout_index == -1: return 

        if self.confirm_delete:
            msg = QMessageBox(self)
            msg.setWindowTitle("Delete Track")
            msg.setText("Are you sure you want to delete this track?")
            msg.setInformativeText("This action cannot be undone.")
            msg.setIcon(QMessageBox.Warning)
            
            # Add buttons
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            
            cb = QCheckBox("Don't ask me again")
            msg.setCheckBox(cb)
            
            response = msg.exec()
            
            if cb.isChecked():
                self.confirm_delete = False
            
            if response == QMessageBox.No:
                return
        
        track_index = layout_index - 1
        print(f"Deleting Track Index: {track_index}")

        self.audio.remove_track(track_index)
        
        item_right = self.right_layout.itemAt(track_index)
        widget_lane = item_right.widget()
        
        if widget_lane in self.lanes:
            self.lanes.remove(widget_lane)
            
        self.left_layout.takeAt(layout_index).widget().deleteLater()
        self.right_layout.takeAt(track_index).widget().deleteLater()
        
        self.update_global_duration()

    def handle_mute(self):
        sender = self.sender()
        idx = self.left_layout.indexOf(sender) - 1 
        self.audio.toggle_mute(idx)
        
    def handle_solo(self):
        sender = self.sender()
        idx = self.left_layout.indexOf(sender) - 1
        self.audio.toggle_solo(idx)
        self.ui_timer.start()

    def on_clip_moved(self, clip_index, new_start_time):
        sender_lane = self.sender()
        if sender_lane in self.lanes:
            track_index = self.lanes.index(sender_lane)
            self.audio.set_track_start_time(track_index, new_start_time)
            self.update_global_duration()

    def toggle_playback(self):
        if self.audio.is_playing:
            self.pause_playback()
        else:
            self.audio.start_playback()
            self.btn_play.setText("Pause")
            self.ui_timer.start()

    def pause_playback(self):
        self.audio.pause_playback()
        self.btn_play.setText("Play")
        self.ui_timer.stop()

    def stop_playback(self):
        self.audio.stop_playback()
        self.btn_play.setText("Play")
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
        for lane in self.lanes:
            lane.set_playhead(x)
            
        if x > self.right_scroll.horizontalScrollBar().value() + self.right_scroll.viewport().width() - 50:
             self.right_scroll.horizontalScrollBar().setValue(x - 50)

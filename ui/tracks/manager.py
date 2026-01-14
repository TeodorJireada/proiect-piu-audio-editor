import os
from PySide6.QtCore import QObject, Slot, Signal
from PySide6.QtWidgets import QFileDialog, QMessageBox

from ui.widgets.track_header import TrackHeader
from ui.widgets.track_lane import TrackLane
from core.track_loader import TrackLoader
from core.commands import AddTrackCommand, DeleteTrackCommand
from core.models import AudioClip

from ui.tracks.clip_ops import ClipOperations
from ui.tracks.channel_ops import ChannelOperations
from ui.tracks.session import SessionHandler

class TrackManager(QObject):
    loading_started = Signal()
    loading_progress = Signal(int, int) # current, total
    loading_finished = Signal()
    status_update = Signal(str)
    track_selected = Signal(object) # Emits AudioTrackData

    def __init__(self, main_window, audio_engine, undo_stack, timeline, left_layout, right_layout, btn_add_track, track_container):
        super().__init__()
        self.main_window = main_window
        self.audio = audio_engine
        self.undo_stack = undo_stack
        self.timeline = timeline
        self.left_layout = left_layout
        self.right_layout = right_layout
        self.btn_add_track = btn_add_track
        self.track_container = track_container
        
        self.lanes = []
        self.confirm_delete = True
        self.current_tool = "MOVE"
        self.snap_enabled = False
        
        self.clip_ops = ClipOperations(self)
        self.channel_ops = ChannelOperations(self)
        self.session_handler = SessionHandler(self)

    def set_active_tool(self, tool_name):
        self.current_tool = tool_name
        for lane in self.lanes:
            lane.set_tool(tool_name)

    def set_snap_enabled(self, enabled):
        self.snap_enabled = enabled
        for lane in self.lanes:
            lane.set_snap_enabled(enabled)

    def set_bpm(self, bpm):
        for lane in self.lanes:
            lane.set_bpm(bpm)

    def scale_project_time(self, scale_factor):
        # Update Model
        for track in self.audio.tracks:
            for clip in track.clips:
                clip.start_time *= scale_factor
                
        # Update UI Lanes
        for lane in self.lanes:
            for clip in lane.clips:
                clip['start_time'] *= scale_factor
            lane.update()

    def import_track(self):
        file_path, _ = QFileDialog.getOpenFileName(self.main_window, "Import Audio", "", "Audio Files (*.wav *.mp3 *.ogg *.flac *.opus)")
        if file_path:
            self.btn_add_track.setText("Loading...") 
            self.btn_add_track.setEnabled(False) 
            
            # Use Thread
            self.loader_thread = TrackLoader(file_path, self.audio.sample_rate)
            self.loader_thread.loaded.connect(self.on_track_loaded)
            self.loader_thread.failed.connect(self.on_import_failed)
            self.loader_thread.start()

    def on_import_failed(self, error_msg):
        QMessageBox.critical(self.main_window, "Import Failed", f"Could not load audio:\n{error_msg}")
        self.btn_add_track.setText("+")
        self.btn_add_track.setEnabled(True)

    def on_track_loaded(self, track_data):
        # Use Command
        cmd = AddTrackCommand(self, track_data)
        self.undo_stack.push(cmd)

    def perform_add_track(self, track_data, index=None):
        # Create initial clip
        duration_sec = len(track_data.source_data) / track_data.sample_rate
        
        if not track_data.clips:
            initial_clip = AudioClip(
                data=track_data.source_data,
                start_time=0.0,
                start_offset=0.0,
                duration=duration_sec,
                name=track_data.name,
                waveform=track_data.waveform
            )
            track_data.clips.append(initial_clip)

        # Pass data to Audio Engine
        if index is not None:
            self.audio.tracks.insert(index, track_data) 
        else:
            self.audio.add_track_data(track_data)
            index = len(self.audio.tracks) - 1

        # Create Header
        filename = os.path.basename(track_data.name)
        
        color = getattr(track_data, "color", "#4466aa")
        
        header = TrackHeader(filename, color)
        header.set_muted(track_data.is_muted)
        header.set_soloed(track_data.is_soloed)
        
        # Connect Header Signals to ChannelOperations
        header.delete_clicked.connect(self.delete_track_request)
        header.mute_clicked.connect(self.channel_ops.handle_mute)
        header.solo_clicked.connect(self.channel_ops.handle_solo)
        header.color_changed.connect(self.channel_ops.handle_track_color_change) 
        header.volume_changed.connect(self.channel_ops.handle_volume_change)
        header.slider_pressed.connect(self.channel_ops.handle_slider_press)
        header.volume_set.connect(self.channel_ops.handle_volume_set)
        
        header.fx_requested.connect(lambda t=track_data: self.on_fx_requested(t))
        header.fx_bypass_toggled.connect(lambda c, t=track_data: self.channel_ops.on_fx_bypass_toggled(t, c))
        
        header.update_fx_count(len(track_data.effects))
        
        # Connect Pan Signals
        header.pan_changed.connect(self.channel_ops.handle_pan_change)
        header.dial_pressed.connect(self.channel_ops.handle_dial_press)
        header.pan_set.connect(self.channel_ops.handle_pan_set)
        header.clicked.connect(lambda: self.channel_ops.on_track_header_clicked(header))
        
        # Set initial volume and pan
        header.set_volume(track_data.volume)
        header.set_pan(track_data.pan)
        header.set_bypass(getattr(track_data, 'fx_bypass', False))
        
        # Create Lane with Waveform
        lane = TrackLane()
        lane.set_zoom(self.timeline.pixels_per_second)
        lane.set_duration(self.timeline.duration)
        lane.set_tool(self.current_tool)
        lane.set_snap_enabled(self.snap_enabled)
        lane.set_bpm(self.audio.bpm)
        
        # Connect Lane Signals to ClipOperations
        lane.clip_moved.connect(self.clip_ops.on_clip_moved)
        lane.clip_trimmed.connect(self.clip_ops.on_clip_trimmed)
        lane.clip_split.connect(self.clip_ops.on_clip_split)
        lane.clip_duplicated.connect(self.clip_ops.on_clip_duplicated)
        lane.clip_deleted.connect(self.clip_ops.on_clip_deleted)
        lane.clip_selected.connect(self.clip_ops.on_clip_selected)
        lane.paste_requested.connect(self.clip_ops.on_paste_requested)
        
        # Add clips to lane
        for clip in track_data.clips:
            lane.add_clip(
                clip.name, 
                clip.start_time, 
                clip.duration, 
                clip.start_offset,
                color, 
                clip.waveform,
                clip.data,
                track_data.sample_rate
            )
        
        self.lanes.insert(index, lane)
        
        header_insert_idx = index
        self.left_layout.insertWidget(header_insert_idx, header)

        lane_insert_idx = index 
        self.right_layout.insertWidget(lane_insert_idx, lane)
        
        self.btn_add_track.setText("+")
        self.btn_add_track.setEnabled(True)
        
        self.update_global_duration()
        return index

    def get_track_data(self, index):
        if 0 <= index < len(self.audio.tracks):
            return self.audio.tracks[index]
        return None

    def perform_delete_track(self, index):
        if not (0 <= index < len(self.audio.tracks)): return

        self.audio.remove_track(index)
        
        # Remove from lanes list
        if 0 <= index < len(self.lanes):
            self.lanes.pop(index)

        # Remove widgets
        header_item = self.left_layout.takeAt(index)
        if header_item: header_item.widget().deleteLater()

        # Lane index: index 
        lane_item = self.right_layout.takeAt(index)
        if lane_item: lane_item.widget().deleteLater()
        
        self.update_global_duration()

    def clear_all_tracks(self):
        # Remove all tracks from last to first
        for i in range(len(self.audio.tracks) - 1, -1, -1):
            self.perform_delete_track(i)
        self.undo_stack.clear()

    def delete_track_request(self):
        sender_header = self.sender()
        # Find index based on layout position
        layout_index = self.left_layout.indexOf(sender_header)
        if layout_index == -1: return 
        
        track_index = layout_index 
        
        cmd = DeleteTrackCommand(self, track_index)
        self.undo_stack.push(cmd)

    # Delegated Methods (Facade for Commands)
    
    # Clip Operations
    def perform_move_clip(self, *args):
        self.clip_ops.perform_move_clip(*args)

    def perform_trim_clip(self, *args):
        self.clip_ops.perform_trim_clip(*args)
        
    def perform_split_clip(self, *args):
        self.clip_ops.perform_split_clip(*args)
        
    def perform_undo_split(self, *args):
        self.clip_ops.perform_undo_split(*args)
        
    def perform_duplicate_clip(self, *args):
        return self.clip_ops.perform_duplicate_clip(*args)
        
    def perform_delete_clip(self, *args):
        self.clip_ops.perform_delete_clip(*args)
        
    def perform_restore_clip(self, *args):
        self.clip_ops.perform_restore_clip(*args)
        
    def perform_paste_clip(self, *args):
        return self.clip_ops.perform_paste_clip(*args)

    def perform_add_clip_internal(self, lane_index, new_clip):
        # Add to AudioEngine
        if 0 <= lane_index < len(self.audio.tracks):
            track = self.audio.tracks[lane_index]
            track.clips.append(new_clip)
            
            # Add to UI
            if 0 <= lane_index < len(self.lanes):
                lane = self.lanes[lane_index]
                lane.add_clip(
                    new_clip.name,
                    new_clip.start_time,
                    new_clip.duration,
                    new_clip.start_offset,
                    getattr(track, "color", "#4466aa"),
                    new_clip.waveform,
                    new_clip.data,
                    track.sample_rate
                )
            self.update_global_duration()
            return len(track.clips) - 1
        return -1


    # Track Controls
    def perform_volume_change(self, *args):
        self.channel_ops.perform_volume_change(*args)

    def perform_pan_change(self, *args):
        self.channel_ops.perform_pan_change(*args)
        
    def perform_color_change(self, *args):
        self.channel_ops.perform_color_change(*args)
        
    def perform_toggle_mute(self, *args):
        self.channel_ops.perform_toggle_mute(*args)
        
    def perform_toggle_solo(self, *args):
        self.channel_ops.perform_toggle_solo(*args)
        
    def perform_toggle_fx_bypass(self, *args):
        self.channel_ops.perform_toggle_fx_bypass(*args)

    def load_project(self, file_path):
        self.session_handler.load_project(file_path)

    def on_fx_requested(self, track_data):
        from ui.effects.window import EffectsWindow
        
        # specific window management in ChannelOperations
        if track_data in self.channel_ops.fx_windows:
            win = self.channel_ops.fx_windows[track_data]
            win.show()
            win.raise_()
            win.activateWindow()
        else:
            win = EffectsWindow(track_data, self.undo_stack, self.main_window)
            self.channel_ops.fx_windows[track_data] = win
            
            # Connect invalidation signal
            win.rack.effects_changed.connect(lambda: self.update_track_fx_count(track_data))
            
            win.show()

    def update_track_fx_count(self, track_data):
        # Find index
        try:
            track_index = self.audio.tracks.index(track_data)
        except ValueError:
            return
        
        item = self.left_layout.itemAt(track_index) # Adjusted index
        if item and item.widget():
            header = item.widget()
            if isinstance(header, TrackHeader):
                header.update_fx_count(len(track_data.effects))

    def open_master_fx_window(self, master_track):
        # Unique key for Master Track
        window_key = "MASTER"
        
        if window_key in self.channel_ops.fx_windows:
            window = self.channel_ops.fx_windows[window_key]
            window.show()
            window.raise_()
            window.activateWindow()
        else:
            from ui.effects.window import EffectsWindow
            window = EffectsWindow(master_track, self.undo_stack, self.main_window)
            window.setWindowTitle("Master Track Effects")
            self.channel_ops.fx_windows[window_key] = window
            window.show()

    # Helpers

    def get_header_widget(self, track_index):
        item = self.left_layout.itemAt(track_index)
        if item and item.widget():
            return item.widget()
        return None

    def refresh_lane(self, lane_index):
        if 0 <= lane_index < len(self.lanes):
            lane = self.lanes[lane_index]
            track = self.audio.tracks[lane_index]
            
            lane.clear_clips() 
            
            # Retrieve current color from header
            header_item = self.left_layout.itemAt(lane_index)
            color = "#5577cc" # Default fallback
            if header_item and header_item.widget():
                header = header_item.widget()
                if hasattr(header, 'color_strip'):
                     color = header.color_strip.current_color
            
            for clip in track.clips:
                lane.add_clip(
                    clip.name, 
                    clip.start_time, 
                    clip.duration, 
                    clip.start_offset,
                    color, 
                    clip.waveform,
                    clip.data,
                    track.sample_rate
                )

    def update_global_duration(self):
        bpm = getattr(self.timeline, 'bpm', 120)
        if bpm <= 0: bpm = 120
        
        seconds_per_beat = 60.0 / bpm
        seconds_per_bar = seconds_per_beat * 4
        
        # Minimum duration: 4 bars
        max_duration = seconds_per_bar * 4 
        
        for lane in self.lanes:
            for clip in lane.clips:
                end_time = clip['start_time'] + clip['duration']
                if end_time > max_duration:
                    max_duration = end_time
        
        # Check playhead
        current_playhead = self.audio.get_playhead_time()
        
        if current_playhead > max_duration:
            max_duration = current_playhead
        
        # Add padding (1 bar)
        max_duration += seconds_per_bar
        
        self.timeline.set_duration(max_duration)
        for lane in self.lanes:
            lane.set_duration(max_duration)
        self.track_container.set_duration(max_duration)

    def update_zoom(self, px_per_sec):
        for lane in self.lanes:
            lane.set_zoom(px_per_sec)
        self.track_container.set_zoom(px_per_sec)

    def update_playhead_visuals(self, x):
        for lane in self.lanes:
            lane.set_playhead(x)

    def update_meters(self):
        # Master Track
        if hasattr(self.audio, 'master_peak') and hasattr(self.main_window, 'master_track_widget'):
            self.main_window.master_track_widget.slider_volume.set_meter_level(self.audio.master_peak)
            
        # Individual Tracks
        for i, track in enumerate(self.audio.tracks):
            peak = self.audio.track_peaks.get(track, 0.0)
            
            # Find associated header
            header = self.get_header_widget(i)
            if header and hasattr(header, 'slider_volume'):
                 header.slider_volume.set_meter_level(peak)

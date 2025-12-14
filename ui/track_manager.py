import os
from PySide6.QtCore import QObject, Slot, Signal
from PySide6.QtWidgets import QFileDialog, QMessageBox, QCheckBox

from ui.widgets.track_header import TrackHeader
from ui.widgets.track_lane import TrackLane
from core.track_loader import TrackLoader
from core.commands import AddTrackCommand, DeleteTrackCommand, MoveClipCommand, TrimClipCommand, SplitClipCommand, DuplicateClipCommand, DeleteClipCommand, ChangeColorCommand, ToggleMuteCommand, ToggleSoloCommand, ChangeVolumeCommand, ChangePanCommand, PasteClipCommand

from core.models import AudioClip

class TrackManager(QObject):
    loading_started = Signal()
    loading_progress = Signal(int, int) # current, total
    loading_finished = Signal()

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
        self.active_loaders = []
        self.pending_tracks = []
        self.loaded_count = 0
        self.current_tool = "MOVE"
        self.temp_volumes = {} # Track index -> start volume
        self.temp_pans = {}    # Track index -> start pan
        self.temp_volumes = {} # Track index -> start volume
        self.temp_pans = {}    # Track index -> start pan
        self.snap_enabled = False
        self.clipboard_clip = None # Stores data of copied clip

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
        """
        Scales the start time of all clips by the given factor.
        Used when BPM changes to maintain musical grid position.
        """
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
        
        # Create Header

        
        # Use saved color or default if not present
        color = getattr(track_data, "color", "#4466aa")
        
        header = TrackHeader(filename, color)
        header.set_muted(track_data.is_muted)
        header.set_soloed(track_data.is_soloed)
        header.delete_clicked.connect(self.delete_track_request)
        header.mute_clicked.connect(self.handle_mute)
        header.solo_clicked.connect(self.handle_solo)
        header.color_changed.connect(self.handle_track_color_change) 
        header.volume_changed.connect(self.handle_volume_change)
        header.slider_pressed.connect(self.handle_slider_press)
        header.volume_set.connect(self.handle_volume_set)
        
        header.pan_changed.connect(self.handle_pan_change)
        header.dial_pressed.connect(self.handle_dial_press)
        header.pan_set.connect(self.handle_pan_set)
        
        # Set initial volume and pan
        header.set_volume(track_data.volume)
        header.set_pan(track_data.pan)
        
        # Create Lane with Waveform
        lane = TrackLane()
        lane.set_zoom(self.timeline.pixels_per_second)
        lane.set_duration(self.timeline.duration)
        lane.set_tool(self.current_tool)
        lane.set_snap_enabled(self.snap_enabled) # Apply Snap
        lane.set_bpm(self.audio.bpm) # Apply BPM
        lane.clip_moved.connect(self.on_clip_moved)
        lane.clip_trimmed.connect(self.on_clip_trimmed)
        lane.clip_split.connect(self.on_clip_split)
        lane.clip_duplicated.connect(self.on_clip_duplicated)
        lane.clip_duplicated.connect(self.on_clip_duplicated)
        lane.clip_deleted.connect(self.on_clip_deleted)
        lane.clip_selected.connect(self.on_clip_selected)
        lane.paste_requested.connect(self.on_paste_requested)
        
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
        
        header_insert_idx = 1 + index
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
        # Header index: 1 + index
        header_item = self.left_layout.takeAt(1 + index)
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
        
        track_index = layout_index - 1 # 1 is offset for top corner
        
        cmd = DeleteTrackCommand(self, track_index)
        self.undo_stack.push(cmd)

    def handle_mute(self):
        sender = self.sender()
        idx = self.left_layout.indexOf(sender) - 1 
        cmd = ToggleMuteCommand(self, idx)
        self.undo_stack.push(cmd)
        
    def handle_solo(self):
        sender = self.sender()
        idx = self.left_layout.indexOf(sender) - 1
        cmd = ToggleSoloCommand(self, idx)
        self.undo_stack.push(cmd)

    def handle_track_color_change(self, new_color):
        sender_header = self.sender()
        layout_index = self.left_layout.indexOf(sender_header)
        if layout_index == -1: return 
        
        track_index = layout_index - 1
        
        # Get old color
        old_color = "#5577cc"
        if 0 <= track_index < len(self.audio.tracks):
             old_color = getattr(self.audio.tracks[track_index], "color", "#5577cc")

        cmd = ChangeColorCommand(self, track_index, old_color, new_color)
        self.undo_stack.push(cmd)

    def handle_volume_change(self, volume):
        sender_header = self.sender()
        layout_index = self.left_layout.indexOf(sender_header)
        if layout_index == -1: return 
        
        track_index = layout_index - 1
        
        if 0 <= track_index < len(self.audio.tracks):
             self.audio.set_track_volume(track_index, volume)

    def handle_slider_press(self):
        sender_header = self.sender()
        layout_index = self.left_layout.indexOf(sender_header)
        if layout_index == -1: return 
        
        track_index = layout_index - 1
        
        if 0 <= track_index < len(self.audio.tracks):
            self.temp_volumes[track_index] = self.audio.tracks[track_index].volume

    def handle_volume_set(self, new_volume):
        sender_header = self.sender()
        layout_index = self.left_layout.indexOf(sender_header)
        if layout_index == -1: return 
        
        track_index = layout_index - 1
        
        old_volume = self.temp_volumes.get(track_index, 1.0)
        # Clean up
        if track_index in self.temp_volumes:
            del self.temp_volumes[track_index]

        if abs(new_volume - old_volume) > 0.001:
            cmd = ChangeVolumeCommand(self, track_index, old_volume, new_volume)
            self.undo_stack.push(cmd)

    def perform_volume_change(self, track_index, volume):
        if 0 <= track_index < len(self.audio.tracks):
            # Update Model
            self.audio.tracks[track_index].volume = volume
            
            # Update Engine
            self.audio.set_track_volume(track_index, volume)
            
            # Update UI
            header_item = self.left_layout.itemAt(track_index + 1)
            if header_item and header_item.widget():
                header = header_item.widget()
                header.set_volume(volume)

    def handle_pan_change(self, pan):
        sender_header = self.sender()
        layout_index = self.left_layout.indexOf(sender_header)
        if layout_index == -1: return 
        
        track_index = layout_index - 1
        
        if 0 <= track_index < len(self.audio.tracks):
             self.audio.set_track_pan(track_index, pan)

    def handle_dial_press(self):
        sender_header = self.sender()
        layout_index = self.left_layout.indexOf(sender_header)
        if layout_index == -1: return 
        
        track_index = layout_index - 1
        
        if 0 <= track_index < len(self.audio.tracks):
            self.temp_pans[track_index] = self.audio.tracks[track_index].pan

    def handle_pan_set(self, new_pan):
        sender_header = self.sender()
        layout_index = self.left_layout.indexOf(sender_header)
        if layout_index == -1: return 
        
        track_index = layout_index - 1
        
        old_pan = self.temp_pans.get(track_index, 0.0)
        if track_index in self.temp_pans:
            del self.temp_pans[track_index]

        if abs(new_pan - old_pan) > 0.001:
            cmd = ChangePanCommand(self, track_index, old_pan, new_pan)
            self.undo_stack.push(cmd)

    def perform_pan_change(self, track_index, pan):
        if 0 <= track_index < len(self.audio.tracks):
            # Update Model
            self.audio.tracks[track_index].pan = pan
            
            # Update Engine
            self.audio.set_track_pan(track_index, pan)
            
            # Update UI
            header_item = self.left_layout.itemAt(track_index + 1)
            if header_item and header_item.widget():
                header = header_item.widget()
                header.set_pan(pan)

    def perform_color_change(self, track_index, color):
        if 0 <= track_index < len(self.audio.tracks):
            # Update Model
            self.audio.tracks[track_index].color = color
            
            # Update Header Strip (Visually)
            header_item = self.left_layout.itemAt(track_index + 1)
            if header_item and header_item.widget():
                header = header_item.widget()
                if hasattr(header, 'color_strip'):
                     # Avoid re-emitting signal if possible or just set it
                     header.color_strip.update_color(color)

            # Update Lane Clips
            if 0 <= track_index < len(self.lanes):
                lane = self.lanes[track_index]
                lane.update_color(color)

    def perform_toggle_mute(self, track_index):
        if 0 <= track_index < len(self.audio.tracks):
            self.audio.toggle_mute(track_index)
            
            # Sync UI
            is_muted = self.audio.tracks[track_index].is_muted
            header_item = self.left_layout.itemAt(track_index + 1)
            if header_item and header_item.widget():
                header_item.widget().set_muted(is_muted)

    def perform_toggle_solo(self, track_index):
        if 0 <= track_index < len(self.audio.tracks):
             self.audio.toggle_solo(track_index)
             
             # Sync UI
             is_soloed = self.audio.tracks[track_index].is_soloed
             header_item = self.left_layout.itemAt(track_index + 1)
             if header_item and header_item.widget():
                 header_item.widget().set_soloed(is_soloed)
             
             self.main_window.ui_timer.start()

    def on_clip_moved(self, clip_index, old_start_time, new_start_time):
        sender_lane = self.sender()
        if sender_lane in self.lanes:
            track_index = self.lanes.index(sender_lane)
            
            if abs(new_start_time - old_start_time) > 0.001:
                cmd = MoveClipCommand(self, track_index, clip_index, old_start_time, new_start_time)
                self.undo_stack.push(cmd)

    def on_clip_trimmed(self, clip_index, old_start, old_dur, old_offset, new_start, new_dur, new_offset):
        sender_lane = self.sender()
        if sender_lane in self.lanes:
            track_index = self.lanes.index(sender_lane)
            
            # Check if meaningful change
            if abs(new_start - old_start) > 0.001 or abs(new_dur - old_dur) > 0.001:
                cmd = TrimClipCommand(
                    self, 
                    track_index, 
                    clip_index, 
                    old_start, 
                    old_dur, 
                    old_offset, 
                    new_start, 
                    new_dur, 
                    new_offset
                )
                self.undo_stack.push(cmd)

    def on_clip_split(self, clip_index, split_time):
        sender_lane = self.sender()
        if sender_lane in self.lanes:
            track_index = self.lanes.index(sender_lane)
            
            if 0 <= track_index < len(self.audio.tracks):
                track = self.audio.tracks[track_index]
                if 0 <= clip_index < len(track.clips):
                    clip = track.clips[clip_index]
                    
                    relative_split = split_time - clip.start_time
                    split_offset = clip.start_offset + relative_split
                    
                    cmd = SplitClipCommand(self, track_index, clip_index, split_time, split_offset)
                    self.undo_stack.push(cmd)

    def on_clip_duplicated(self, clip_index, new_start_time):
        sender_lane = self.sender()
        if sender_lane in self.lanes:
            track_index = self.lanes.index(sender_lane)
            
            cmd = DuplicateClipCommand(self, track_index, clip_index, new_start_time)
            self.undo_stack.push(cmd)

    def on_clip_deleted(self, clip_index):
        sender_lane = self.sender()
        if sender_lane in self.lanes:
            track_index = self.lanes.index(sender_lane)
            
            cmd = DeleteClipCommand(self, track_index, clip_index)
            self.undo_stack.push(cmd)

    def perform_move_clip(self, lane_index, clip_index, new_start):
        if 0 <= lane_index < len(self.lanes):
            lane = self.lanes[lane_index]
            lane.set_clip_start_time(clip_index, new_start)
            
            # Update Audio Engine Data
            if 0 <= lane_index < len(self.audio.tracks):
                track = self.audio.tracks[lane_index]
                if 0 <= clip_index < len(track.clips):
                    track.clips[clip_index].start_time = new_start
            
            self.update_global_duration()

    def perform_trim_clip(self, lane_index, clip_index, new_start, new_duration, new_offset):
        if 0 <= lane_index < len(self.lanes):
            lane = self.lanes[lane_index]
            # Update UI
            lane.update_clip(clip_index, new_start, new_duration) 
            
            # Update Audio Engine Data
            if 0 <= lane_index < len(self.audio.tracks):
                track = self.audio.tracks[lane_index]
                if 0 <= clip_index < len(track.clips):
                    clip = track.clips[clip_index]
                    clip.start_time = new_start
                    clip.duration = new_duration
                    clip.start_offset = new_offset
            
            self.update_global_duration()

    def perform_split_clip(self, lane_index, clip_index, split_time, split_offset):
        if 0 <= lane_index < len(self.lanes):
            lane = self.lanes[lane_index]
            
            # Update Audio Engine Data
            if 0 <= lane_index < len(self.audio.tracks):
                track = self.audio.tracks[lane_index]
                if 0 <= clip_index < len(track.clips):
                    original_clip = track.clips[clip_index]
                    
                    # Calculate split point relative to clip start
                    relative_split = split_time - original_clip.start_time
                    
                    if relative_split <= 0 or relative_split >= original_clip.duration:
                        return # Invalid split
                        
                    # Create second clip
                    new_clip = AudioClip(
                        data=original_clip.data,
                        start_time=split_time,
                        start_offset=original_clip.start_offset + relative_split,
                        duration=original_clip.duration - relative_split,
                        name=original_clip.name,
                        waveform=original_clip.waveform
                    )
                    
                    # Update first clip
                    original_clip.duration = relative_split
                    
                    # Insert new clip
                    track.clips.insert(clip_index + 1, new_clip)
                    
                    # Update UI
                    self.refresh_lane(lane_index)

            self.update_global_duration()

    def perform_undo_split(self, lane_index, clip_index):
        if 0 <= lane_index < len(self.lanes):
            # Update Audio Engine Data
            if 0 <= lane_index < len(self.audio.tracks):
                track = self.audio.tracks[lane_index]
                if 0 <= clip_index < len(track.clips) - 1:
                    first_clip = track.clips[clip_index]
                    second_clip = track.clips[clip_index + 1]
                    
                    # Merge
                    first_clip.duration += second_clip.duration
                    
                    # Remove second clip
                    track.clips.pop(clip_index + 1)
                    
                    # Update UI
                    self.refresh_lane(lane_index)
            
            self.update_global_duration()

    def perform_duplicate_clip(self, lane_index, clip_index, new_start_time):
        if 0 <= lane_index < len(self.lanes):
            # Update Audio Engine Data
            if 0 <= lane_index < len(self.audio.tracks):
                track = self.audio.tracks[lane_index]
                if 0 <= clip_index < len(track.clips):
                    original_clip = track.clips[clip_index]
                    
                    new_clip = AudioClip(
                        data=original_clip.data,
                        start_time=new_start_time,
                        start_offset=original_clip.start_offset,
                        duration=original_clip.duration,
                        name=original_clip.name + " (Copy)",
                        waveform=original_clip.waveform
                    )
                    
                    track.clips.append(new_clip)
                    new_index = len(track.clips) - 1
                    
                    self.refresh_lane(lane_index)
                    
                    self.update_global_duration()
                    return new_index
        return -1

    def perform_delete_clip(self, lane_index, clip_index):
        if 0 <= lane_index < len(self.lanes):
            # Update Audio Engine Data
            if 0 <= lane_index < len(self.audio.tracks):
                track = self.audio.tracks[lane_index]
                if 0 <= clip_index < len(track.clips):
                    track.clips.pop(clip_index)
                    
                    # Update UI
                    self.refresh_lane(lane_index)
            
            self.update_global_duration()

    def perform_restore_clip(self, lane_index, clip_index, clip_obj):
        if 0 <= lane_index < len(self.lanes):
            # Update Audio Engine Data
            if 0 <= lane_index < len(self.audio.tracks):
                track = self.audio.tracks[lane_index]
                track.clips.insert(clip_index, clip_obj)
                
                # Update UI
                self.refresh_lane(lane_index)
            
            self.update_global_duration()

    def refresh_lane(self, lane_index):
        if 0 <= lane_index < len(self.lanes):
            lane = self.lanes[lane_index]
            track = self.audio.tracks[lane_index]
            
            lane.clear_clips() 
            
            # Retrieve current color from header
            header_item = self.left_layout.itemAt(lane_index + 1)
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
        max_duration = 3600 # Minimum duration (1 hour) to ensure scroll/zoom works consistently
        
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
        self.track_container.set_duration(max_duration)

    def update_zoom(self, px_per_sec):
        for lane in self.lanes:
            lane.set_zoom(px_per_sec)
        self.track_container.set_zoom(px_per_sec)

    def update_playhead_visuals(self, x):
        for lane in self.lanes:
            lane.set_playhead(x)

    def load_project(self, file_path):
        from core.project_manager import ProjectManager
        import numpy as np
        import os # Added import for os module

        pm = ProjectManager()
        project_data = pm.parse_project_file(file_path)
        
        if not project_data:
            return

        # Set BPM
        bpm = project_data.get("bpm", 120)
        if hasattr(self.main_window, 'perform_bpm_change'):
            self.main_window.perform_bpm_change(bpm)

        self.clear_all_tracks()
        
        tracks_list = project_data.get("tracks", [])
        total_tracks = len(tracks_list)
        
        if total_tracks == 0:
            return

        self.pending_tracks = [None] * total_tracks
        self.loaded_count = 0
        self.loading_started.emit()
        self.loading_progress.emit(0, total_tracks)
        
        for i, track_info in enumerate(tracks_list):
            file_path = track_info.get("file_path")
            
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                # Treat as loaded but empty/error
                self.on_project_track_loaded(None, track_info, i, None)
                continue
                
            loader = TrackLoader(file_path, self.audio.sample_rate)
            # Pass index 'i' to callback
            loader.loaded.connect(lambda data, info=track_info, idx=i, l=loader: self.on_project_track_loaded(data, info, idx, l))
            loader.failed.connect(lambda err, info=track_info, idx=i, l=loader: self.on_project_track_loaded(None, info, idx, l))
            loader.start()
            self.active_loaders.append(loader)

    def on_project_track_loaded(self, loaded_track_data, track_info, track_index, loader):
        if loader and loader in self.active_loaders:
            self.active_loaders.remove(loader)
            
        # Store result
        self.pending_tracks[track_index] = (loaded_track_data, track_info)
        self.loaded_count += 1
        
        total_tracks = len(self.pending_tracks)
        self.loading_progress.emit(self.loaded_count, total_tracks)
        
        if self.loaded_count == total_tracks:
            self.finalize_batch_load()

    def finalize_batch_load(self):
        import numpy as np


        for i, item in enumerate(self.pending_tracks):
            if item is None: continue
            
            loaded_track_data, track_info = item
            
            if loaded_track_data is None:
                # Handle error case
                dummy_data = np.zeros((1, 2), dtype='float32')
                track = AudioTrackData(
                    name=track_info.get("name", "Error Loading"),
                    file_path=track_info.get("file_path"),
                    data=dummy_data,
                    sample_rate=self.audio.sample_rate
                )
            else:
                track = loaded_track_data
                track.name = track_info.get("name", track.name)

            # Apply saved state
            track.is_muted = track_info.get("is_muted", False)
            track.is_soloed = track_info.get("is_soloed", False)
            track.volume = track_info.get("volume", 1.0) 
            track.pan = track_info.get("pan", 0.0)
            track.color = track_info.get("color", "#4466aa") # Load saved color
            
            # Reconstruct Clips
            track.clips = []
            for clip_info in track_info.get("clips", []):
                clip = AudioClip(
                    data=track.source_data,
                    start_time=clip_info.get("start_time", 0),
                    start_offset=clip_info.get("start_offset", 0),
                    duration=clip_info.get("duration", 0),
                    name=clip_info.get("name", "Clip"),
                    waveform=track.waveform
                )
                track.clips.append(clip)
            
            self.perform_add_track(track)
            
        self.loading_finished.emit()
        self.pending_tracks = []
        self.loaded_count = 0

    def on_clip_selected(self, clip_index):
        # Determine sender lane
        sender_lane = self.sender()
        if sender_lane not in self.lanes: return
        lane_index = self.lanes.index(sender_lane)

        # Clear selection in ALL lanes (including sender first, to be safe, or just others)
        for lane in self.lanes:
            if lane == sender_lane:
                lane.set_selection(clip_index)
            else:
                lane.set_selection(-1)

        # Get clip data from AudioEngine
        track = self.audio.tracks[lane_index]
        if 0 <= clip_index < len(track.clips):
            self.clipboard_clip = track.clips[clip_index]
            print(f"Clip copied: {self.clipboard_clip.name}")

    def on_paste_requested(self, start_time):
        if not self.clipboard_clip: return
        
        sender_lane = self.sender()
        if sender_lane not in self.lanes: return
        lane_index = self.lanes.index(sender_lane)
        
        cmd = PasteClipCommand(self, lane_index, self.clipboard_clip, start_time)
        self.undo_stack.push(cmd)

    def perform_paste_clip(self, lane_index, clip_data, start_time):
        # Create new AudioClip instance
        new_clip = AudioClip(
            data=clip_data.data, # Shared ref to data
            start_time=start_time,
            start_offset=clip_data.start_offset,
            duration=clip_data.duration,
            name=clip_data.name,
            waveform=clip_data.waveform
        )
        
        # Add to AudioEngine
        track = self.audio.tracks[lane_index]
        track.clips.append(new_clip)
        new_clip_index = len(track.clips) - 1
        
        # Add to UI
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
        
        return new_clip_index

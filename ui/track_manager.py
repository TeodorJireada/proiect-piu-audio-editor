import os
from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QFileDialog, QMessageBox, QCheckBox

from ui.widgets.track_header import TrackHeader
from ui.widgets.track_lane import TrackLane
from core.track_loader import TrackLoader
from core.commands import AddTrackCommand, DeleteTrackCommand, MoveClipCommand, TrimClipCommand, SplitClipCommand, DuplicateClipCommand, DeleteClipCommand

from core.models import AudioClip

class TrackManager(QObject):
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
        self.loader_thread = None

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
        
        # If track_data was restored from Undo, it might already have clips?
        # Our current Undo implementation stores the whole track_data object.
        # If we delete a track, we save the track_data.
        # If we add it back, we reuse track_data.
        # So if it already has clips, we should respect them.
        
        if not track_data.clips:
            initial_clip = AudioClip(
                data=track_data.source_data,
                start_time=0.0, # Will be updated if we insert at specific time? No, usually 0.
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
        
        header = TrackHeader(filename, "#4466aa")
        header.delete_clicked.connect(self.delete_track_request)
        header.mute_clicked.connect(self.handle_mute)
        header.solo_clicked.connect(self.handle_solo)
        
        # Create Lane with Waveform
        lane = TrackLane()
        lane.set_zoom(self.timeline.pixels_per_second)
        lane.clip_moved.connect(self.on_clip_moved)
        lane.clip_trimmed.connect(self.on_clip_trimmed)
        lane.clip_split.connect(self.on_clip_split)
        lane.clip_duplicated.connect(self.on_clip_duplicated)
        lane.clip_deleted.connect(self.on_clip_deleted)
        
        # Add clips to lane
        for clip in track_data.clips:
            lane.add_clip(
                clip.name, 
                clip.start_time, 
                clip.duration, 
                clip.start_offset,
                "#5577cc", 
                clip.waveform
            )
        
        self.lanes.insert(index, lane) # Maintain lanes list sync

        # Insert into Layouts
        # Left Layout: Headers. 
        # The left_layout has: TopLeftCorner (0), [Headers...], AddButton, Stretch
        # So headers start at index 1.
        
        header_insert_idx = 1 + index
        self.left_layout.insertWidget(header_insert_idx, header)

        # Right Layout: Lanes.
        # right_layout has: [Lanes...], Stretch
        # So lanes start at index 0.
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
        self.audio.toggle_mute(idx)
        
    def handle_solo(self):
        sender = self.sender()
        idx = self.left_layout.indexOf(sender) - 1
        self.audio.toggle_solo(idx)
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
            
            # We need split_offset (offset in source data)
            # We can calculate it from the current clip state
            if 0 <= track_index < len(self.audio.tracks):
                track = self.audio.tracks[track_index]
                if 0 <= clip_index < len(track.clips):
                    clip = track.clips[clip_index]
                    
                    # relative_split = split_time - clip.start_time
                    # split_offset = clip.start_offset + relative_split
                    # But we can let the Command or perform_split_clip handle calculation?
                    # The Command takes split_offset.
                    # Let's calculate it here.
                    
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
            lane.update_clip(clip_index, new_start, new_duration) # We need to add this method to TrackLane
            
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
                    
                    # Insert at end for now, or try to keep sorted?
                    # If we just append, the index will be len(clips)-1
                    track.clips.append(new_clip)
                    new_index = len(track.clips) - 1
                    
                    # Update UI
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
            
            for clip in track.clips:
                lane.add_clip(
                    clip.name, 
                    clip.start_time, 
                    clip.duration, 
                    clip.start_offset,
                    "#5577cc", 
                    clip.waveform
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

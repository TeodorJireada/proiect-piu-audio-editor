from PySide6.QtCore import QObject, Signal
import os
from core.models import AudioClip
from core.commands import (
    MoveClipCommand, TrimClipCommand, SplitClipCommand, 
    DuplicateClipCommand, DeleteClipCommand, PasteClipCommand
)

class ClipOperations(QObject):
    def __init__(self, track_manager):
        super().__init__()
        self.tm = track_manager
        self.clipboard_clip = None
        self.clipboard_source_lane = -1

    @property
    def audio(self):
        return self.tm.audio
    
    @property
    def lanes(self):
        return self.tm.lanes

    # Signal Handlers (Connected by TrackManager)

    def on_clip_moved(self, clip_index, old_start_time, new_start_time):
        sender_lane = self.sender()
        if sender_lane in self.lanes:
            track_index = self.lanes.index(sender_lane)
            
            if abs(new_start_time - old_start_time) > 0.001:
                cmd = MoveClipCommand(self, track_index, clip_index, old_start_time, new_start_time)
                self.tm.undo_stack.push(cmd)

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
                self.tm.undo_stack.push(cmd)

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
                    self.tm.undo_stack.push(cmd)
                    self.tm.status_update.emit("Split Clip")

    def on_clip_duplicated(self, clip_index, new_start_time):
        sender_lane = self.sender()
        if sender_lane in self.lanes:
            track_index = self.lanes.index(sender_lane)
            
            cmd = DuplicateClipCommand(self, track_index, clip_index, new_start_time)
            self.tm.undo_stack.push(cmd)
            
            # Select the newly created clip to enable daisy-chain duplication
            if cmd.new_clip_index != -1:
                sender_lane.set_selection(cmd.new_clip_index)
            
            self.tm.status_update.emit("Duplicated Clip")

    def on_clip_deleted(self, clip_index):
        sender_lane = self.sender()
        if sender_lane in self.lanes:
            track_index = self.lanes.index(sender_lane)
            
            cmd = DeleteClipCommand(self, track_index, clip_index)
            self.tm.undo_stack.push(cmd)
            self.tm.status_update.emit("Deleted Clip")

    def on_clip_selected(self, clip_index):
        # Determine sender lane
        sender_lane = self.sender()
        if sender_lane not in self.lanes: return
        lane_index = self.lanes.index(sender_lane)

        for lane in self.lanes:
            if lane == sender_lane:
                lane.set_selection(clip_index)
            else:
                lane.set_selection(-1)

        # Get clip data from AudioEngine
        track = self.audio.tracks[lane_index]
        if 0 <= clip_index < len(track.clips):
            self.clipboard_clip = track.clips[clip_index]
            self.clipboard_source_lane = lane_index
            
            display_name = os.path.basename(self.clipboard_clip.name)
            self.tm.status_update.emit(f"Copied Clip: {display_name}")

    def on_paste_requested(self, start_time):
        if not self.clipboard_clip: return
        
        sender_lane = self.sender()
        if sender_lane not in self.lanes: return
        lane_index = self.lanes.index(sender_lane)
        
        if self.clipboard_source_lane != -1 and lane_index != self.clipboard_source_lane:
            self.tm.status_update.emit("Cannot paste to a different track")
            return

        cmd = PasteClipCommand(self, lane_index, self.clipboard_clip, start_time)
        self.tm.undo_stack.push(cmd)
        self.tm.status_update.emit("Pasted Clip")


    # Performers (Called by Commands)

    def perform_move_clip(self, lane_index, clip_index, new_start):
        if 0 <= lane_index < len(self.lanes):
            lane = self.lanes[lane_index]
            lane.set_clip_start_time(clip_index, new_start)
            
            # Update Audio Engine Data
            if 0 <= lane_index < len(self.audio.tracks):
                track = self.audio.tracks[lane_index]
                if 0 <= clip_index < len(track.clips):
                    track.clips[clip_index].start_time = new_start
            
            self.tm.update_global_duration()

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
            
            self.tm.update_global_duration()

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
                    
                    original_clip.duration = relative_split
                    track.clips.insert(clip_index + 1, new_clip)
                    self.tm.refresh_lane(lane_index)

            self.tm.update_global_duration()

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
                    
                    self.tm.refresh_lane(lane_index)
            
            self.tm.update_global_duration()

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
                    
                    self.tm.refresh_lane(lane_index)
                    
                    self.tm.update_global_duration()
                    return new_index
        return -1

    def perform_delete_clip(self, lane_index, clip_index):
        if 0 <= lane_index < len(self.lanes):
            # Update Audio Engine Data
            if 0 <= lane_index < len(self.audio.tracks):
                track = self.audio.tracks[lane_index]
                if clip_index is not None and 0 <= clip_index < len(track.clips):
                    track.clips.pop(clip_index)
                    
                    # Update UI
                    self.tm.refresh_lane(lane_index)
            
            self.tm.update_global_duration()

    def perform_restore_clip(self, lane_index, clip_index, clip_obj):
        if 0 <= lane_index < len(self.lanes):
            # Update Audio Engine Data
            if 0 <= lane_index < len(self.audio.tracks):
                track = self.audio.tracks[lane_index]
                track.clips.insert(clip_index, clip_obj)
                
                # Update UI
                self.tm.refresh_lane(lane_index)
            
            self.tm.update_global_duration()

    def perform_paste_clip(self, lane_index, clip_data, start_time):
        # Create new AudioClip instance
        new_clip = AudioClip(
            data=clip_data.data, # Shared ref to data
            start_time=start_time,
            start_offset=clip_data.start_offset,
            duration=clip_data.duration,
            name=clip_data.name + " (Pasted)",
            waveform=clip_data.waveform
        )
        
        return self.tm.perform_add_clip_internal(lane_index, new_clip)

from core.command_stack import Command

class AddTrackCommand(Command):
    def __init__(self, track_manager, track_data):
        self.track_manager = track_manager
        self.track_data = track_data
        self.track_index = -1 # Will be set after execution

    def execute(self):
        # We need a method in TrackManager that adds the track and returns the index
        self.track_index = self.track_manager.perform_add_track(self.track_data)

    def undo(self):
        self.track_manager.perform_delete_track(self.track_index)

class DeleteTrackCommand(Command):
    def __init__(self, track_manager, track_index):
        self.track_manager = track_manager
        self.track_index = track_index
        self.track_data = None # To save state

    def execute(self):
        # We need to retrieve data before deleting to support Undo
        self.track_data = self.track_manager.get_track_data(self.track_index)
        self.track_manager.perform_delete_track(self.track_index)

    def undo(self):
        self.track_manager.perform_add_track(self.track_data, self.track_index)

class MoveClipCommand(Command):
    def __init__(self, track_manager, lane_index, clip_index, old_start, new_start):
        self.track_manager = track_manager
        self.lane_index = lane_index
        self.clip_index = clip_index
        self.old_start = old_start
        self.new_start = new_start

    def execute(self):
        self.track_manager.perform_move_clip(self.lane_index, self.clip_index, self.new_start)

    def undo(self):
        self.track_manager.perform_move_clip(self.lane_index, self.clip_index, self.old_start)

class TrimClipCommand(Command):
    def __init__(self, track_manager, lane_index, clip_index, old_start, old_duration, old_offset, new_start, new_duration, new_offset):
        self.track_manager = track_manager
        self.lane_index = lane_index
        self.clip_index = clip_index
        self.old_start = old_start
        self.old_duration = old_duration
        self.old_offset = old_offset
        self.new_start = new_start
        self.new_duration = new_duration
        self.new_offset = new_offset

    def execute(self):
        self.track_manager.perform_trim_clip(self.lane_index, self.clip_index, self.new_start, self.new_duration, self.new_offset)

    def undo(self):
        self.track_manager.perform_trim_clip(self.lane_index, self.clip_index, self.old_start, self.old_duration, self.old_offset)

class SplitClipCommand(Command):
    def __init__(self, track_manager, lane_index, clip_index, split_time, split_offset):
        self.track_manager = track_manager
        self.lane_index = lane_index
        self.clip_index = clip_index
        self.split_time = split_time
        self.split_offset = split_offset # Offset in source where split happens

    def execute(self):
        self.track_manager.perform_split_clip(self.lane_index, self.clip_index, self.split_time, self.split_offset)

    def undo(self):
        # Undo split = Merge back? 
        # Or just delete the second clip and restore the first one's duration?
        # Simpler: perform_merge_clip or perform_undo_split
        self.track_manager.perform_undo_split(self.lane_index, self.clip_index)

class DuplicateClipCommand(Command):
    def __init__(self, track_manager, lane_index, clip_index, new_start_time):
        self.track_manager = track_manager
        self.lane_index = lane_index
        self.clip_index = clip_index # Index of source clip
        self.new_start_time = new_start_time
        self.new_clip_index = -1 # Will be set after execution

    def execute(self):
        self.new_clip_index = self.track_manager.perform_duplicate_clip(self.lane_index, self.clip_index, self.new_start_time)

    def undo(self):
        # Undo duplicate = delete the new clip
        # But perform_duplicate_clip might insert it anywhere?
        # Usually duplicate places it right after the original or at the end?
        # Let's assume perform_duplicate_clip returns the index of the new clip.
        self.track_manager.perform_delete_clip(self.lane_index, self.new_clip_index)

class DeleteClipCommand(Command):
    def __init__(self, track_manager, lane_index, clip_index):
        self.track_manager = track_manager
        self.lane_index = lane_index
        self.clip_index = clip_index
        self.clip_data = None # To save state

    def execute(self):
        # Save state before deleting
        # We need to get the clip data.
        # TrackManager needs a get_clip_data method?
        # Or we can access it via track_manager.audio.tracks...
        # Let's add get_clip_data to TrackManager or access directly if possible.
        # Accessing directly is easier for now.
        track = self.track_manager.audio.tracks[self.lane_index]
        self.clip_data = track.clips[self.clip_index]
        
        self.track_manager.perform_delete_clip(self.lane_index, self.clip_index)

    def undo(self):
        # Restore clip
        # We need perform_add_clip method?
        # Or perform_restore_clip?
        # perform_duplicate_clip creates a NEW clip.
        # We want to restore the EXACT clip object (or equivalent).
        # Let's add perform_restore_clip(lane_index, clip_index, clip_obj)
        self.track_manager.perform_restore_clip(self.lane_index, self.clip_index, self.clip_data)

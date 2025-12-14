from core.command_stack import Command

class AddTrackCommand(Command):
    def __init__(self, track_manager, track_data):
        self.track_manager = track_manager
        self.track_data = track_data
        self.track_index = -1 # Will be set after execution

    def execute(self):
        self.track_index = self.track_manager.perform_add_track(self.track_data)

    def undo(self):
        self.track_manager.perform_delete_track(self.track_index)

class DeleteTrackCommand(Command):
    def __init__(self, track_manager, track_index):
        self.track_manager = track_manager
        self.track_index = track_index
        self.track_data = None # To save state

    def execute(self):
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
        self.track_manager.perform_delete_clip(self.lane_index, self.new_clip_index)

class DeleteClipCommand(Command):
    def __init__(self, track_manager, lane_index, clip_index):
        self.track_manager = track_manager
        self.lane_index = lane_index
        self.clip_index = clip_index
        self.clip_data = None # To save state

    def execute(self):
        track = self.track_manager.audio.tracks[self.lane_index]
        self.clip_data = track.clips[self.clip_index]
        
        self.track_manager.perform_delete_clip(self.lane_index, self.clip_index)

    def undo(self):
        self.track_manager.perform_restore_clip(self.lane_index, self.clip_index, self.clip_data)

class ChangeColorCommand(Command):
    def __init__(self, track_manager, track_index, old_color, new_color):
        self.track_manager = track_manager
        self.track_index = track_index
        self.old_color = old_color
        self.new_color = new_color

    def execute(self):
        self.track_manager.perform_color_change(self.track_index, self.new_color)

    def undo(self):
        self.track_manager.perform_color_change(self.track_index, self.old_color)

class ToggleMuteCommand(Command):
    def __init__(self, track_manager, track_index):
        self.track_manager = track_manager
        self.track_index = track_index

    def execute(self):
        self.track_manager.perform_toggle_mute(self.track_index)

    def undo(self):
        self.track_manager.perform_toggle_mute(self.track_index)

class ToggleSoloCommand(Command):
    def __init__(self, track_manager, track_index):
        self.track_manager = track_manager
        self.track_index = track_index

    def execute(self):
        self.track_manager.perform_toggle_solo(self.track_index)

    def undo(self):
        self.track_manager.perform_toggle_solo(self.track_index)

class ChangeVolumeCommand(Command):
    def __init__(self, track_manager, track_index, old_volume, new_volume):
        self.track_manager = track_manager
        self.track_index = track_index
        self.old_volume = old_volume
        self.new_volume = new_volume

    def execute(self):
        self.track_manager.perform_volume_change(self.track_index, self.new_volume)

    def undo(self):
        self.track_manager.perform_volume_change(self.track_index, self.old_volume)

class ChangePanCommand(Command):
    def __init__(self, track_manager, track_index, old_pan, new_pan):
        self.track_manager = track_manager
        self.track_index = track_index
        self.old_pan = old_pan
        self.new_pan = new_pan

    def execute(self):
        self.track_manager.perform_pan_change(self.track_index, self.new_pan)

    def undo(self):
        self.track_manager.perform_pan_change(self.track_index, self.old_pan)

class ChangeBPMCommand(Command):
    def __init__(self, main_window, old_bpm, new_bpm):
        self.main_window = main_window
        self.old_bpm = old_bpm
        self.new_bpm = new_bpm

    def execute(self):
        self.main_window.perform_bpm_change(self.new_bpm)

    def undo(self):
        self.main_window.perform_bpm_change(self.old_bpm)

class ToggleLoopCommand(Command):
    def __init__(self, main_window, enabled):
        self.main_window = main_window
        self.enabled = enabled

    def execute(self):
        self.main_window.perform_loop_toggle(self.enabled)

    def undo(self):
        self.main_window.perform_loop_toggle(not self.enabled)

class ToggleSnapCommand(Command):
    def __init__(self, main_window, enabled):
        self.main_window = main_window
        self.enabled = enabled

    def execute(self):
        self.main_window.perform_snap_toggle(self.enabled)

    def undo(self):
        self.main_window.perform_snap_toggle(not self.enabled)

class PasteClipCommand(Command):
    def __init__(self, track_manager, lane_index, clip_data, start_time):
        self.track_manager = track_manager
        self.lane_index = lane_index
        self.clip_data = clip_data  # Source AudioClip object (or similar data)
        self.start_time = start_time
        self.new_clip_index = -1

    def execute(self):
        self.new_clip_index = self.track_manager.perform_paste_clip(self.lane_index, self.clip_data, self.start_time)

    def undo(self):
        self.track_manager.perform_delete_clip(self.lane_index, self.new_clip_index)

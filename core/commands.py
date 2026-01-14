from core.command_stack import Command

class AddTrackCommand(Command):
    def __init__(self, track_manager, track_data):
        self.track_manager = track_manager
        self.track_data = track_data
        self.track_index = -1 

    def execute(self):
        self.track_index = self.track_manager.perform_add_track(self.track_data)

    def undo(self):
        self.track_manager.perform_delete_track(self.track_index)

class DeleteTrackCommand(Command):
    def __init__(self, track_manager, track_index):
        self.track_manager = track_manager
        self.track_index = track_index
        self.track_data = None 

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

class AddEffectCommand(Command):
    def __init__(self, effects_rack, track, effect):
        self.effects_rack = effects_rack
        self.track = track
        self.effect = effect
        
    def execute(self):
        self.track.effects.append(self.effect)
        self.effects_rack.refresh_rack() # Refresh UI
        
    def undo(self):
        if self.effect in self.track.effects:
            self.track.effects.remove(self.effect)
            self.effects_rack.refresh_rack()

class RemoveEffectCommand(Command):
    def __init__(self, effects_rack, track, effect):
        self.effects_rack = effects_rack
        self.track = track
        self.effect = effect
        self.index = -1
        
    def execute(self):
        if self.effect in self.track.effects:
            self.index = self.track.effects.index(self.effect)
            self.track.effects.remove(self.effect)
            self.effects_rack.refresh_rack()
            
    def undo(self):
        if self.index != -1:
            self.track.effects.insert(self.index, self.effect)
            self.effects_rack.refresh_rack()

class ToggleEffectCommand(Command):
    def __init__(self, effect_unit, effect):
        self.effect_unit = effect_unit
        self.effect = effect
        
    def execute(self):
        self.effect.active = not self.effect.active
        self.effect_unit.setChecked(self.effect.active)
        
    def undo(self):
        self.effect.active = not self.effect.active
        self.effect_unit.setChecked(self.effect.active)

class ChangeEffectParamCommand(Command):
    def __init__(self, effect_unit, effect, param_name, old_value, new_value):
        self.effect_unit = effect_unit
        self.effect = effect
        self.param_name = param_name
        self.old_value = old_value
        self.new_value = new_value
        
    def execute(self):
        self.effect.parameters[self.param_name] = self.new_value
        try:
            self.effect_unit.update_ui_from_param(self.param_name, self.new_value)
        except RuntimeError:
            pass 
        
    def undo(self):
        self.effect.parameters[self.param_name] = self.old_value
        try:
            self.effect_unit.update_ui_from_param(self.param_name, self.old_value)
        except RuntimeError:
            pass

class ReorderEffectCommand(Command):
    def __init__(self, effects_rack, track, old_index, new_index):
        self.effects_rack = effects_rack
        self.track = track
        self.old_index = old_index
        self.new_index = new_index

    def execute(self):
        if self.old_index < 0 or self.old_index >= len(self.track.effects): return
        if self.new_index < 0 or self.new_index >= len(self.track.effects): return
        
        effect = self.track.effects.pop(self.old_index)
        self.track.effects.insert(self.new_index, effect)
        self.effects_rack.refresh_rack()

    def undo(self):
        self.track.effects.insert(self.old_index, effect)
        self.effects_rack.refresh_rack()

class ChangeMasterVolumeCommand(Command):
    def __init__(self, master_track, master_widget, old_vol, new_vol):
        self.master_track = master_track
        self.master_widget = master_widget
        self.old_vol = old_vol
        self.new_vol = new_vol

    def execute(self):
        self.master_track.volume = self.new_vol
        if self.master_widget:
            try:
                self.master_widget.slider_volume.blockSignals(True)
                self.master_widget.slider_volume.setValue(int(self.new_vol * 100))
                self.master_widget.slider_volume.blockSignals(False)
            except RuntimeError:
                pass

    def undo(self):
        self.master_track.volume = self.old_vol
        if self.master_widget:
            try:
                self.master_widget.slider_volume.blockSignals(True)
                self.master_widget.slider_volume.setValue(int(self.old_vol * 100))
                self.master_widget.slider_volume.blockSignals(False)
            except RuntimeError:
                pass

class ChangeMasterPanCommand(Command):
    def __init__(self, master_track, master_widget, old_pan, new_pan):
        self.master_track = master_track
        self.master_widget = master_widget
        self.old_pan = old_pan
        self.new_pan = new_pan

    def execute(self):
        self.master_track.pan = self.new_pan
        if self.master_widget:
            try:
                self.master_widget.dial_pan.blockSignals(True)
                self.master_widget.dial_pan.setValue(self.new_pan * 100)
                self.master_widget.dial_pan.blockSignals(False)
            except RuntimeError:
                pass

    def undo(self):
        self.master_track.pan = self.old_pan
        if self.master_widget:
            try:
                self.master_widget.dial_pan.blockSignals(True)
                self.master_widget.dial_pan.setValue(self.old_pan * 100)
                self.master_widget.dial_pan.blockSignals(False)
            except RuntimeError:
                pass

class ToggleFXBypassCommand(Command):
    def __init__(self, track_manager, track_index, new_state):
        self.track_manager = track_manager
        self.track_index = track_index # -1 for master
        self.new_state = new_state
    
    def execute(self):
        self.track_manager.perform_toggle_fx_bypass(self.track_index, self.new_state)
        
    def undo(self):
        self.track_manager.perform_toggle_fx_bypass(self.track_index, not self.new_state)

from PySide6.QtCore import QObject, Signal
from core.commands import (
    ToggleMuteCommand, ToggleSoloCommand, ChangeColorCommand, 
    ChangeVolumeCommand, ChangePanCommand, ToggleFXBypassCommand
)
from ui.widgets.track_header import TrackHeader

class ChannelOperations(QObject):
    def __init__(self, track_manager):
        super().__init__()
        self.tm = track_manager
        self.temp_volumes = {} # Track index -> start volume
        self.temp_pans = {}    # Track index -> start pan

        # FX Window Management (Delegated here)
        self.fx_windows = {}

    @property
    def audio(self):
        return self.tm.audio
    
    @property
    def left_layout(self):
        return self.tm.left_layout

    # --- Signal Handlers ---

    def handle_mute(self):
        sender = self.sender()
        idx = self.left_layout.indexOf(sender) 
        # Layout index matches track index because of how we add them (insertWidget)
        
        cmd = ToggleMuteCommand(self, idx)
        self.tm.undo_stack.push(cmd)
        
    def handle_solo(self):
        sender = self.sender()
        idx = self.left_layout.indexOf(sender)
        cmd = ToggleSoloCommand(self, idx)
        self.tm.undo_stack.push(cmd)

    def handle_track_color_change(self, new_color):
        sender_header = self.sender()
        layout_index = self.left_layout.indexOf(sender_header)
        if layout_index == -1: return 
        
        track_index = layout_index
        
        # Get old color
        old_color = "#5577cc"
        if 0 <= track_index < len(self.audio.tracks):
             old_color = getattr(self.audio.tracks[track_index], "color", "#5577cc")

        cmd = ChangeColorCommand(self, track_index, old_color, new_color)
        self.tm.undo_stack.push(cmd)

    def handle_volume_change(self, volume):
        sender_header = self.sender()
        layout_index = self.left_layout.indexOf(sender_header)
        if layout_index == -1: return 
        
        track_index = layout_index
        
        if 0 <= track_index < len(self.audio.tracks):
             self.audio.set_track_volume(track_index, volume)

    def handle_slider_press(self):
        sender_header = self.sender()
        layout_index = self.left_layout.indexOf(sender_header)
        if layout_index == -1: return 
        
        track_index = layout_index
        
        if 0 <= track_index < len(self.audio.tracks):
            self.temp_volumes[track_index] = self.audio.tracks[track_index].volume

    def handle_volume_set(self, new_volume):
        sender_header = self.sender()
        layout_index = self.left_layout.indexOf(sender_header)
        if layout_index == -1: return 
        
        track_index = layout_index
        
        old_volume = self.temp_volumes.get(track_index, 1.0)
        # Clean up
        if track_index in self.temp_volumes:
            del self.temp_volumes[track_index]

        if abs(new_volume - old_volume) > 0.001:
            cmd = ChangeVolumeCommand(self, track_index, old_volume, new_volume)
            self.tm.undo_stack.push(cmd)

    def handle_pan_change(self, pan):
        sender_header = self.sender()
        layout_index = self.left_layout.indexOf(sender_header)
        if layout_index == -1: return 
        
        track_index = layout_index 
        
        if 0 <= track_index < len(self.audio.tracks):
             self.audio.set_track_pan(track_index, pan)

    def handle_dial_press(self):
        sender_header = self.sender()
        layout_index = self.left_layout.indexOf(sender_header)
        if layout_index == -1: return 
        
        track_index = layout_index
        
        if 0 <= track_index < len(self.audio.tracks):
            self.temp_pans[track_index] = self.audio.tracks[track_index].pan

    def handle_pan_set(self, new_pan):
        sender_header = self.sender()
        layout_index = self.left_layout.indexOf(sender_header)
        if layout_index == -1: return 
        
        track_index = layout_index
        
        old_pan = self.temp_pans.get(track_index, 0.0)
        if track_index in self.temp_pans:
            del self.temp_pans[track_index]

        if abs(new_pan - old_pan) > 0.001:
            cmd = ChangePanCommand(self, track_index, old_pan, new_pan)
            self.tm.undo_stack.push(cmd)

    def on_track_header_clicked(self, header):
        layout_index = self.left_layout.indexOf(header)
        if layout_index == -1: return
        
        track_index = layout_index
        if 0 <= track_index < len(self.audio.tracks):
             track_data = self.audio.tracks[track_index]
             self.tm.track_selected.emit(track_data)
             self.tm.status_update.emit(f"Selected Track: {track_data.name}")

    def on_fx_bypass_toggled(self, track_data, checked):
        if track_data in self.audio.tracks:
            index = self.audio.tracks.index(track_data)
            cmd = ToggleFXBypassCommand(self, index, checked)
            self.tm.undo_stack.push(cmd)
        else:
            print(f"DEBUG: Track {track_data.name} not found in audio.tracks")

    # --- Performers (Called by Commands) ---

    def perform_volume_change(self, track_index, volume):
        if 0 <= track_index < len(self.audio.tracks):
            # Update Model
            self.audio.tracks[track_index].volume = volume
            
            # Update Engine
            self.audio.set_track_volume(track_index, volume)
            
            # Update UI
            header_item = self.left_layout.itemAt(track_index) 
            if header_item and header_item.widget():
                header = header_item.widget()
                header.set_volume(volume)

    def perform_pan_change(self, track_index, pan):
        if 0 <= track_index < len(self.audio.tracks):
            # Update Model
            self.audio.tracks[track_index].pan = pan
            
            # Update Engine
            self.audio.set_track_pan(track_index, pan)
            
            # Update UI
            header_item = self.left_layout.itemAt(track_index)
            if header_item and header_item.widget():
                header = header_item.widget()
                header.set_pan(pan)

    def perform_color_change(self, track_index, color):
        if 0 <= track_index < len(self.audio.tracks):
            # Update Model
            self.audio.tracks[track_index].color = color
            
            # Update Header Strip (Visually)
            header_item = self.left_layout.itemAt(track_index)
            if header_item and header_item.widget():
                header = header_item.widget()
                if hasattr(header, 'color_strip'):
                     header.color_strip.update_color(color)

            # Update Lane Clips
            if 0 <= track_index < len(self.tm.lanes):
                lane = self.tm.lanes[track_index]
                lane.update_color(color)

    def perform_toggle_mute(self, track_index):
        if 0 <= track_index < len(self.audio.tracks):
            self.audio.toggle_mute(track_index)
            
            # Sync UI
            is_muted = self.audio.tracks[track_index].is_muted
            header_item = self.left_layout.itemAt(track_index)
            if header_item and header_item.widget():
                header_item.widget().set_muted(is_muted)

    def perform_toggle_solo(self, track_index):
        if 0 <= track_index < len(self.audio.tracks):
             self.audio.toggle_solo(track_index)
             
             # Sync UI
             is_soloed = self.audio.tracks[track_index].is_soloed
             header_item = self.left_layout.itemAt(track_index)
             if header_item and header_item.widget():
                 header_item.widget().set_soloed(is_soloed)
             
             self.tm.main_window.ui_timer.start()

    def perform_toggle_fx_bypass(self, track_index, bypass_state):
        # -1 for Master Track
        if track_index == -1:
             if hasattr(self.audio, 'master_track'):
                 self.audio.master_track.fx_bypass = bypass_state
                 if hasattr(self.tm.main_window, 'master_track_widget'):
                      self.tm.main_window.master_track_widget.set_bypass(bypass_state)
        elif 0 <= track_index < len(self.audio.tracks):
             track = self.audio.tracks[track_index]
             track.fx_bypass = bypass_state
             
             # UI Update
             header = self.tm.get_header_widget(track_index)
             if header:
                 header.set_bypass(bypass_state)

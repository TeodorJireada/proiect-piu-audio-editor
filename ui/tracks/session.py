from PySide6.QtCore import QObject, Signal
import os
import numpy as np
from core.project_manager import ProjectManager
from core.track_loader import TrackLoader
from core.models import AudioClip, AudioTrackData
from core.effects.eq import EQ3Band
from core.effects.delay import SimpleDelay
from core.effects.distortion import Distortion

class SessionHandler(QObject):
    def __init__(self, track_manager):
        super().__init__()
        self.tm = track_manager
        self.active_loaders = []
        self.pending_tracks = []
        self.loaded_count = 0

    @property
    def audio(self):
        return self.tm.audio
    
    @property
    def main_window(self):
        return self.tm.main_window

    def load_project(self, file_path):
        pm = ProjectManager()
        project_data = pm.parse_project_file(file_path)
        
        if not project_data:
            return

        # Set BPM
        bpm = project_data.get("bpm", 120)
        if hasattr(self.main_window, 'perform_bpm_change'):
            self.main_window.perform_bpm_change(bpm)

        self.tm.clear_all_tracks()

        master_data = project_data.get("master")
        if master_data and hasattr(self.main_window, 'master_track_widget'):
            # Model
            self.audio.master_track.volume = master_data.get("volume", 1.0)
            self.audio.master_track.pan = master_data.get("pan", 0.0)
            self.audio.master_track.fx_bypass = master_data.get("fx_bypass", False)
            
            # Effects
            self.audio.master_track.effects.clear()
            for fx_data in master_data.get("effects", []):
                fx_type = fx_data.get("type")
                effect = self.create_effect(fx_type)
                
                if effect:
                    effect.active = fx_data.get("active", True)
                    effect.parameters = fx_data.get("parameters", {})
                    self.audio.master_track.effects.append(effect)
            
            # GUI
            try:
                self.main_window.master_track_widget.blockSignals(True)
                self.main_window.master_track_widget.slider_volume.setValue(int(self.audio.master_track.volume * 100))
                self.main_window.master_track_widget.dial_pan.setValue(self.audio.master_track.pan * 100)
                self.main_window.master_track_widget.set_bypass(self.audio.master_track.fx_bypass)
                self.main_window.master_track_widget.update_fx_count(len(self.audio.master_track.effects))
                self.main_window.master_track_widget.blockSignals(False)
            except Exception as e:
                print(f"Error updating master widget: {e}")
        
        tracks_list = project_data.get("tracks", [])
        total_tracks = len(tracks_list)
        
        if total_tracks == 0:
            return

        self.pending_tracks = [None] * total_tracks
        self.loaded_count = 0
        self.tm.loading_started.emit()
        self.tm.loading_progress.emit(0, total_tracks)
        
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
        self.tm.loading_progress.emit(self.loaded_count, total_tracks)
        
        if self.loaded_count == total_tracks:
            self.finalize_batch_load()

    def finalize_batch_load(self):
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
            track.fx_bypass = track_info.get("fx_bypass", False)
            
            # Restore Effects
            effects_data = track_info.get("effects", [])
            for fx_data in effects_data:
                fx_type = fx_data.get("type")
                effect = self.create_effect(fx_type)
                    
                if effect:
                    effect.active = fx_data.get("active", True)
                    # Restore parameters
                    for k, v in fx_data.get("parameters", {}).items():
                        if k in effect.parameters:
                            effect.parameters[k] = v
                    track.effects.append(effect)

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
            
            self.tm.perform_add_track(track)
            
        self.tm.loading_finished.emit()
        self.pending_tracks = []
        self.loaded_count = 0

    def create_effect(self, fx_type):
        if fx_type == "EQ3Band": return EQ3Band()
        elif fx_type == "SimpleDelay": return SimpleDelay()
        elif fx_type == "Distortion": return Distortion()
        return None

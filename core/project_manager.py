import json
import os
from core.models import AudioTrackData
from core.track_loader import TrackLoader

class ProjectManager:
    def __init__(self):
        pass

    def save_project(self, file_path, audio_engine):
        project_data = {
            "version": "1.0",
            "bpm": getattr(audio_engine, "bpm", 120),
            "master": {
                "volume": getattr(audio_engine.master_track, "volume", 1.0),
                "pan": getattr(audio_engine.master_track, "pan", 0.0),
                "fx_bypass": getattr(audio_engine.master_track, "fx_bypass", False),
                "effects": []
            },
            "tracks": []
        }
        
        # Serialize Master Effects
        if hasattr(audio_engine.master_track, 'effects'):
            for effect in audio_engine.master_track.effects:
                effect_data = {
                    "type": effect.__class__.__name__,
                    "active": effect.active,
                    "parameters": effect.parameters
                }
                project_data["master"]["effects"].append(effect_data)

        for track in audio_engine.tracks:
            track_data = {
                "name": track.name,
                "file_path": track.file_path,
                "is_muted": track.is_muted,
                "is_soloed": track.is_soloed,
                "volume": getattr(track, "volume", 1.0), 
                "pan": getattr(track, "pan", 0.0),
                "fx_bypass": getattr(track, "fx_bypass", False),
                "color": getattr(track, "color", "#4466aa"), # Save color
                "effects": [],
                "clips": []
            }
            
            # Serialize Effects
            if hasattr(track, 'effects'):
                for effect in track.effects:
                    effect_data = {
                        "type": effect.__class__.__name__,
                        "active": effect.active,
                        "parameters": effect.parameters
                    }
                    track_data["effects"].append(effect_data)

            for clip in track.clips:
                clip_data = {
                    "name": clip.name,
                    "start_time": clip.start_time,
                    "start_offset": clip.start_offset,
                    "duration": clip.duration
                }
                track_data["clips"].append(clip_data)

            project_data["tracks"].append(track_data)

        try:
            with open(file_path, 'w') as f:
                json.dump(project_data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving project: {e}")
            return False

    def load_project(self, file_path):
        return self.parse_project_file(file_path)

    def parse_project_file(self, file_path):
        try:
            with open(file_path, 'r') as f:
                project_data = json.load(f)
            return project_data
        except Exception as e:
            print(f"Error parsing project file: {e}")
            return None

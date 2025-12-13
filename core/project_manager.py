import json
import os
from core.models import AudioTrackData, AudioClip
from core.track_loader import TrackLoader

class ProjectManager:
    def __init__(self):
        pass

    def save_project(self, file_path, audio_engine):
        project_data = {
            "version": "1.0",
            "tracks": []
        }

        for track in audio_engine.tracks:
            track_data = {
                "name": track.name,
                "file_path": track.file_path,
                "is_muted": track.is_muted,
                "is_muted": track.is_muted,
                "is_soloed": track.is_soloed,
                "color": getattr(track, "color", "#4466aa"), # Save color
                "clips": []
            }

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

    def parse_project_file(self, file_path):
        try:
            with open(file_path, 'r') as f:
                project_data = json.load(f)
            return project_data
        except Exception as e:
            print(f"Error parsing project file: {e}")
            return None

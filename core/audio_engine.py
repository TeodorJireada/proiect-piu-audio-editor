import sounddevice as sd
import numpy as np
from PySide6.QtCore import QObject

class AudioEngine(QObject):
    def __init__(self):
        super().__init__()

        self.sample_rate = 44100 
        print(f"Audio Engine initialized at: {self.sample_rate} Hz")

        self.tracks = [] 
        self.playhead = 0 
        self.is_playing = False
        self.stream = None

    def add_track_data(self, track_obj):
        self.tracks.append(track_obj)

    def remove_track(self, index):
        if 0 <= index < len(self.tracks):
            del self.tracks[index]

    def toggle_mute(self, index):
        if 0 <= index < len(self.tracks): 
            self.tracks[index].is_muted = not self.tracks[index].is_muted

    def toggle_solo(self, index):
        if 0 <= index < len(self.tracks): 
            self.tracks[index].is_soloed = not self.tracks[index].is_soloed

    def _kill_stream(self):
        if self.is_playing:
            self.is_playing = False
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

    def pause_playback(self):
        self._kill_stream()

    def stop_playback(self):
        self._kill_stream()
        self.playhead = 0

    def start_playback(self):
        if self.is_playing: return
        self.is_playing = True
        self.stream = sd.OutputStream(
            samplerate=self.sample_rate, channels=2,
            callback=self.audio_callback, blocksize=2048
        )
        self.stream.start()

    # MIXING ENGINE 
    
    def audio_callback(self, outdata, frames, time, status):
        if status: print(status)
        mix_buffer = np.zeros((frames, 2), dtype='float32')
        
        any_solo = any(t.is_soloed for t in self.tracks)

        for track in self.tracks:
            if any_solo:
                if not track.is_soloed: continue
            else:
                if track.is_muted: continue

            track_data = track.data
            start_s = track.start_sample
            
            track_pos = self.playhead - start_s
            
            if track_pos + frames > 0 and track_pos < len(track_data):
                offset_in_track = max(0, track_pos)
                offset_in_buffer = max(0, -track_pos)
                chunk_len = min(len(track_data) - offset_in_track, frames - offset_in_buffer)
                
                mix_buffer[offset_in_buffer : offset_in_buffer + chunk_len] += \
                    track_data[offset_in_track : offset_in_track + chunk_len]
                
        outdata[:] = mix_buffer
        self.playhead += frames

    def set_playhead(self, pixel_x, px_per_second=100):
        seconds = pixel_x / px_per_second
        self.playhead = int(seconds * self.sample_rate)

    def get_playhead_time(self):
        return self.playhead / self.sample_rate
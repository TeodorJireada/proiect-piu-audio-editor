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

    # set_track_start_time removed - use clip.start_time instead

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
    
    def set_playhead(self, pixel_x, px_per_second=100):
        seconds = pixel_x / px_per_second
        self.playhead = int(seconds * self.sample_rate)

    def get_playhead_time(self):
        return self.playhead / self.sample_rate

    def mix_chunk(self, start_sample, num_frames):
        mix_buffer = np.zeros((num_frames, 2), dtype='float32')
        
        any_solo = any(t.is_soloed for t in self.tracks)

        for track in self.tracks:
            if any_solo:
                if not track.is_soloed: continue
            else:
                if track.is_muted: continue

            for clip in track.clips:
                clip_start_sample = int(clip.start_time * self.sample_rate)
                clip_end_sample = clip_start_sample + int(clip.duration * self.sample_rate)
                
                buffer_start = start_sample
                buffer_end = start_sample + num_frames
                
                start_overlap = max(clip_start_sample, buffer_start)
                end_overlap = min(clip_end_sample, buffer_end)
                
                if start_overlap < end_overlap:
                    overlap_len = end_overlap - start_overlap
                    buffer_offset = start_overlap - buffer_start
                    
                    offset_in_visible_clip = start_overlap - clip_start_sample
                    offset_in_source_data = int(clip.start_offset * self.sample_rate) + offset_in_visible_clip
                    
                    source_len = len(clip.data)
                    if offset_in_source_data < source_len:
                        read_len = min(overlap_len, source_len - offset_in_source_data)
                        
                        mix_buffer[buffer_offset : buffer_offset + read_len] += \
                            clip.data[offset_in_source_data : offset_in_source_data + read_len]
        
        return mix_buffer

    def export_audio(self, file_path, duration_sec):
        import soundfile as sf
        
        total_samples = int(duration_sec * self.sample_rate)
        block_size = 4096
        
        print(f"Exporting to {file_path} ({duration_sec}s)")
        
        with sf.SoundFile(file_path, mode='w', samplerate=self.sample_rate, channels=2, subtype='PCM_16') as file:
            for start in range(0, total_samples, block_size):
                frames = min(block_size, total_samples - start)
                mix = self.mix_chunk(start, frames)
                file.write(mix)
        
        print("Export complete.")

    def audio_callback(self, outdata, frames, time, status):
        if status: print(status)
        
        mix_buffer = self.mix_chunk(self.playhead, frames)
        
        outdata[:] = mix_buffer
        self.playhead += frames

    def set_playhead(self, pixel_x, px_per_second=100):
        seconds = pixel_x / px_per_second
        self.playhead = int(seconds * self.sample_rate)

    def get_playhead_time(self):
        return self.playhead / self.sample_rate
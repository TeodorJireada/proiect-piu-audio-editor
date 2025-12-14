import sounddevice as sd
import numpy as np
from PySide6.QtCore import QObject

class AudioEngine(QObject):
    def __init__(self):
        super().__init__()

        self.sample_rate = 44100
        self.channels = 2
        self.playhead = 0 # in samples
        self.bpm = 120
        self.time_signature = (4, 4) # (numerator, denominator)
        
        print(f"Audio Engine initialized at: {self.sample_rate} Hz")

        self.tracks = [] 
        self.is_playing = False
        self.stream = None
        self.is_looping = False
        self.loop_end_sample = 0

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

    def set_track_volume(self, index, volume):
        if 0 <= index < len(self.tracks):
            self.tracks[index].volume = max(0.0, min(1.0, volume))

    def set_track_pan(self, index, pan):
        if 0 <= index < len(self.tracks):
            self.tracks[index].pan = max(-1.0, min(1.0, pan))

    def set_bpm(self, bpm):
        self.bpm = max(20, min(999, bpm))

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
        
        if self.is_looping:
            self.calculate_loop_end()
            
        self.is_playing = True
        self.stream = sd.OutputStream(
            samplerate=self.sample_rate, channels=2,
            callback=self.audio_callback, blocksize=2048
        )
        self.stream.start()



    def set_looping(self, enabled):
        self.is_looping = enabled
        if enabled:
            self.calculate_loop_end()

    def calculate_loop_end(self):
        max_end_time = 0.0
        for track in self.tracks:
            for clip in track.clips:
                end = clip.start_time + clip.duration
                if end > max_end_time:
                    max_end_time = end
        
        if max_end_time == 0:
            self.loop_end_sample = 0
            return

        # Convert to Bars
        beats_per_bar = self.time_signature[0]
        seconds_per_beat = 60 / self.bpm
        bar_duration = beats_per_bar * seconds_per_beat
        
        total_bars = max_end_time / bar_duration
        import math
        next_free_bar = math.ceil(total_bars)
        if next_free_bar == 0: next_free_bar = 1 # Minimum 1 bar
        
        loop_end_time = next_free_bar * bar_duration
        self.loop_end_sample = int(loop_end_time * self.sample_rate)
        # print(f"Loop end calculated: {loop_end_time}s (Bar {next_free_bar+1})")

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
                        
                        # Calculate gains
                        pan = track.pan
                        left_gain = 1.0 if pan <= 0 else (1.0 - pan)
                        right_gain = 1.0 if pan >= 0 else (1.0 + pan)
                        
                        # Apply volume and pan
                        # efficient numpy broadcasting: (N, 2) * (1, 2)
                        gains = np.array([left_gain, right_gain], dtype='float32') * track.volume
                        
                        mix_buffer[buffer_offset : buffer_offset + read_len] += \
                            clip.data[offset_in_source_data : offset_in_source_data + read_len] * gains
        
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

        # Loop Check
        if self.is_looping and self.loop_end_sample > 0:
            if self.playhead >= self.loop_end_sample:
                self.playhead = 0 # Wrap around

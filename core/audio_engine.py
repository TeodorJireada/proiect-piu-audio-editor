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
        self.time_signature = (4, 4)
        
        print(f"Audio Engine initialized at: {self.sample_rate} Hz")

        from core.models import AudioTrackData
        self.master_track = AudioTrackData("Master", None, None, self.sample_rate)

        self.tracks = [] 
        self.is_playing = False
        self.stream = None
        self.is_looping = False
        self.loop_end_sample = 0
        
        # Metering
        self.track_peaks = {} # Map track object to float 0.0-1.0
        self.master_peak = 0.0
        self.master_peak_L = 0.0
        self.master_peak_R = 0.0

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

            # Sum Clips into Track Buffer
            track_buffer = np.zeros((num_frames, 2), dtype='float32')
            
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
                        
                        # Add raw clip audio to track buffer
                        track_buffer[buffer_offset : buffer_offset + read_len] += \
                            clip.data[offset_in_source_data : offset_in_source_data + read_len]
            
            # Process Effects Chain
            if hasattr(track, 'effects') and not getattr(track, 'fx_bypass', False):
                for effect in track.effects:
                    if effect.active:
                        track_buffer = effect.process(track_buffer, self.sample_rate)

            # Apply Track Volume & Pan
            pan = track.pan
            left_gain = 1.0 if pan <= 0 else (1.0 - pan)
            right_gain = 1.0 if pan >= 0 else (1.0 + pan)
            
            gains = np.array([left_gain, right_gain], dtype='float32') * track.volume
            
            # Mix to Master
            mix_buffer += track_buffer * gains
            
            # Capture Peak Metering
            peak = np.max(np.abs(track_buffer)) * track.volume
            self.track_peaks[track] = float(peak)
            
            
        # MASTER TRACK PROCESSING
        if hasattr(self, 'master_track'):
             if not getattr(self.master_track, 'fx_bypass', False):
                 for effect in self.master_track.effects:
                     if effect.active:
                         mix_buffer = effect.process(mix_buffer, self.sample_rate)
             
             mix_buffer *= self.master_track.volume
             
             pan = self.master_track.pan
             left_gain = 1.0 if pan <= 0 else (1.0 - pan)
             right_gain = 1.0 if pan >= 0 else (1.0 + pan)
             
             master_gains = np.array([left_gain, right_gain], dtype='float32')
             
             mix_buffer[:, 0] *= master_gains[0]
             mix_buffer[:, 1] *= master_gains[1]
             
             if len(mix_buffer) > 0:
                 max_vals = np.max(np.abs(mix_buffer), axis=0)
                 self.master_peak_L = float(max_vals[0])
                 self.master_peak_R = float(max_vals[1])
                 self.master_peak = max(self.master_peak_L, self.master_peak_R) 
             else:
                 self.master_peak_L = 0.0
                 self.master_peak_R = 0.0
                 self.master_peak = 0.0

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

        if self.is_looping and self.loop_end_sample > 0:
            if self.playhead >= self.loop_end_sample:
                self.playhead = 0
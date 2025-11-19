import numpy as np

class AudioTrackData:
    # Simple track data container
    def __init__(self, name, file_path, data, sample_rate):
        self.name = name
        self.file_path = file_path
        self.data = data             # Numpy Array (Audio)
        self.sample_rate = sample_rate
        self.waveform = None         # List of peaks for UI
        
        # State
        self.is_muted = False
        self.is_soloed = False
        self.start_sample = 0
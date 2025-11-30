class AudioClip:
    def __init__(self, data, start_time, start_offset, duration, name, waveform=None):
        self.data = data # Source numpy array
        self.start_time = start_time # Global start time in seconds
        self.start_offset = start_offset # Offset into source data in seconds
        self.duration = duration # Visible duration in seconds
        self.name = name
        self.waveform = waveform

class AudioTrackData:
    def __init__(self, name, file_path, data, sample_rate):
        self.name = name
        self.file_path = file_path
        self.source_data = data
        self.sample_rate = sample_rate
        self.waveform = None
        self.is_muted = False
        self.is_soloed = False
        self.clips = [] # List of AudioClip
